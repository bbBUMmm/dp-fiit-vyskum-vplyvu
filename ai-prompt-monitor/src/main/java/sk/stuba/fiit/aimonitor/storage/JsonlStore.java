package sk.stuba.fiit.aimonitor.storage;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;

/**
 * Append-only JSON-lines (.jsonl) store with daily file rotation.
 *
 * <p>Each captured request becomes one JSON object on its own line. The file is rotated daily
 * ({@code captures-YYYY-MM-DD.jsonl}). This format was chosen over SQLite for the walking
 * skeleton because:
 * <ul>
 *     <li>Trivially inspectable with {@code less} / {@code jq};</li>
 *     <li>Append-only, crash-safe (no half-written rows);</li>
 *     <li>Easy to ship / archive / hash for audit;</li>
 *     <li>Trivial to load into pandas / R for later analysis.</li>
 * </ul>
 * Switch to SQLite later if needed for richer reporting.
 */
public class JsonlStore implements AutoCloseable {
    private static final Logger log = LoggerFactory.getLogger(JsonlStore.class);
    private static final DateTimeFormatter DATE_FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd");

    private final Path outputDir;
    private final ObjectMapper mapper;
    private BufferedWriter writer;
    private String currentDate;

    public JsonlStore(Path outputDir) throws IOException {
        this.outputDir = outputDir;
        Files.createDirectories(outputDir);
        this.mapper = new ObjectMapper()
                .registerModule(new JavaTimeModule())
                .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
        log.info("JSONL store ready at {}", outputDir.toAbsolutePath());
    }

    public synchronized void write(CapturedRequest req) {
        try {
            rotateIfNeeded();
            writer.write(mapper.writeValueAsString(req));
            writer.newLine();
            writer.flush();
        } catch (IOException e) {
            log.error("Failed to write captured request", e);
        }
    }

    private void rotateIfNeeded() throws IOException {
        String today = LocalDate.now().format(DATE_FMT);
        if (writer == null || !today.equals(currentDate)) {
            if (writer != null) writer.close();
            currentDate = today;
            Path file = outputDir.resolve("captures-" + today + ".jsonl");
            writer = Files.newBufferedWriter(
                    file,
                    StandardOpenOption.CREATE,
                    StandardOpenOption.APPEND
            );
            log.info("Writing captures to {}", file.toAbsolutePath());
        }
    }

    @Override
    public synchronized void close() throws IOException {
        if (writer != null) {
            writer.close();
            writer = null;
        }
    }
}
