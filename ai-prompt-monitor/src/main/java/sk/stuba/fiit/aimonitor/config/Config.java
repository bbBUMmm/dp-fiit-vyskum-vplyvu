package sk.stuba.fiit.aimonitor.config;

import org.yaml.snakeyaml.Yaml;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

/**
 * Loads configuration from a YAML file.
 *
 * <p>Expected schema:
 * <pre>
 * proxy:
 *   port: 8080
 *   bind: 127.0.0.1
 * capture:
 *   output_dir: ./captures
 *   max_body_size_kb: 1024
 * url_patterns:
 *   - "chatgpt.com/backend-api/conversation"
 *   - "claude.ai/api/organizations/"
 * </pre>
 */
public record Config(
        int proxyPort,
        String proxyBind,
        Path outputDir,
        int maxBodySizeKb,
        List<String> urlPatterns
) {

    @SuppressWarnings("unchecked")
    public static Config load(Path file) throws IOException {
        try (InputStream in = Files.newInputStream(file)) {
            Map<String, Object> root = new Yaml().load(in);
            if (root == null) {
                throw new IOException("Config file is empty: " + file);
            }

            Map<String, Object> proxy = (Map<String, Object>) root.getOrDefault("proxy", Map.of());
            int port = ((Number) proxy.getOrDefault("port", 8080)).intValue();
            String bind = (String) proxy.getOrDefault("bind", "127.0.0.1");

            Map<String, Object> capture = (Map<String, Object>) root.getOrDefault("capture", Map.of());
            Path outDir = Path.of((String) capture.getOrDefault("output_dir", "./captures"));
            int maxKb = ((Number) capture.getOrDefault("max_body_size_kb", 1024)).intValue();

            List<String> patterns = (List<String>) root.getOrDefault("url_patterns", List.of());
            if (patterns.isEmpty()) {
                throw new IOException("No url_patterns configured — nothing would be captured.");
            }

            return new Config(port, bind, outDir, maxKb, patterns);
        }
    }
}
