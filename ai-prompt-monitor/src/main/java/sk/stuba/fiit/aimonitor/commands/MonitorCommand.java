package sk.stuba.fiit.aimonitor.commands;

import org.littleshoot.proxy.HttpProxyServer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import picocli.CommandLine.Command;
import picocli.CommandLine.Option;
import sk.stuba.fiit.aimonitor.config.Config;
import sk.stuba.fiit.aimonitor.proxy.ProxyRunner;
import sk.stuba.fiit.aimonitor.storage.JsonlStore;

import java.nio.file.Path;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;

/**
 * {@code monitor} subcommand — starts the HTTPS MITM proxy and runs until killed.
 *
 * <pre>
 *   java -jar ai-prompt-monitor.jar monitor --config config/urls.yaml
 * </pre>
 */
@Command(
        name = "monitor",
        description = "Start the local MITM proxy and capture matching requests until Ctrl+C."
)
public class MonitorCommand implements Callable<Integer> {
    private static final Logger log = LoggerFactory.getLogger(MonitorCommand.class);

    @Option(
            names = {"-c", "--config"},
            required = true,
            description = "Path to YAML config file (see config/urls.example.yaml)."
    )
    private Path configPath;

    @Override
    public Integer call() throws Exception {
        Config config = Config.load(configPath);
        JsonlStore store = new JsonlStore(config.outputDir());
        HttpProxyServer server = ProxyRunner.start(config, store);

        CountDownLatch shutdownLatch = new CountDownLatch(1);
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            log.info("Shutdown requested — stopping proxy...");
            try {
                server.stop();
            } catch (Exception e) {
                log.warn("Error stopping proxy", e);
            }
            try {
                store.close();
            } catch (Exception e) {
                log.warn("Error closing store", e);
            }
            shutdownLatch.countDown();
        }, "shutdown-hook"));

        log.info("Configure your browser to use HTTP/HTTPS proxy {}:{}.",
                config.proxyBind(), config.proxyPort());
        log.info("Make sure the proxy's CA certificate is trusted (see README).");
        log.info("Press Ctrl+C to stop.");
        shutdownLatch.await();
        log.info("Stopped.");
        return 0;
    }
}
