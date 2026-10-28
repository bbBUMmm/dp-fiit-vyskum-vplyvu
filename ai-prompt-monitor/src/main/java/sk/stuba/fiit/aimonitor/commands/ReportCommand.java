package sk.stuba.fiit.aimonitor.commands;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import picocli.CommandLine.Command;
import picocli.CommandLine.Option;

import java.io.BufferedReader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Callable;
import java.util.stream.Stream;

/**
 * {@code report} subcommand — basic summary of captures. Intentionally minimal: total count,
 * date range, and per-host breakdown.
 *
 * <p>Future extensions (for thesis chapter 5): cohort comparisons, prompt-length distributions,
 * inter-prompt intervals (the "short memory span" behavioural indicator from section 8 of the
 * handover document), etc.
 */
@Command(
        name = "report",
        description = "Print a summary report of captured requests."
)
public class ReportCommand implements Callable<Integer> {

    @Option(
            names = {"-d", "--dir"},
            required = true,
            description = "Captures directory (e.g. ./captures)."
    )
    private Path dir;

    @Override
    public Integer call() throws Exception {
        if (!Files.isDirectory(dir)) {
            System.err.println("Not a directory: " + dir);
            return 1;
        }

        ObjectMapper mapper = new ObjectMapper().registerModule(new JavaTimeModule());

        long total = 0;
        long withBody = 0;
        Map<String, Long> byHost = new HashMap<>();
        String earliest = null;
        String latest = null;

        try (Stream<Path> files = Files.list(dir)) {
            List<Path> jsonlFiles = files
                    .filter(p -> p.getFileName().toString().endsWith(".jsonl"))
                    .sorted()
                    .toList();
            for (Path f : jsonlFiles) {
                try (BufferedReader r = Files.newBufferedReader(f)) {
                    String line;
                    while ((line = r.readLine()) != null) {
                        if (line.isBlank()) continue;
                        JsonNode node = mapper.readTree(line);
                        total++;
                        String host = node.path("host").asText("(unknown)");
                        byHost.merge(host, 1L, Long::sum);
                        if (!node.path("body").isMissingNode() && !node.path("body").asText().isEmpty()) {
                            withBody++;
                        }
                        String ts = node.path("timestamp").asText();
                        if (!ts.isEmpty()) {
                            if (earliest == null || ts.compareTo(earliest) < 0) earliest = ts;
                            if (latest == null || ts.compareTo(latest) > 0) latest = ts;
                        }
                    }
                }
            }
        }

        System.out.println();
        System.out.println("=== AI Prompt Monitor — capture report ===");
        System.out.println("Directory:       " + dir.toAbsolutePath());
        System.out.println("Total captures:  " + total);
        System.out.println("With body:       " + withBody);
        System.out.println("Earliest:        " + (earliest == null ? "-" : earliest));
        System.out.println("Latest:          " + (latest == null ? "-" : latest));
        System.out.println();
        System.out.println("By host:");
        byHost.entrySet().stream()
                .sorted(Map.Entry.<String, Long>comparingByValue().reversed())
                .forEach(e -> System.out.printf("  %-50s %d%n", e.getKey(), e.getValue()));
        System.out.println();

        return 0;
    }
}
