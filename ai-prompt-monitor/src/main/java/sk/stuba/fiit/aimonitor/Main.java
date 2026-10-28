package sk.stuba.fiit.aimonitor;

import picocli.CommandLine;
import sk.stuba.fiit.aimonitor.commands.MonitorCommand;
import sk.stuba.fiit.aimonitor.commands.PeqiCommand;
import sk.stuba.fiit.aimonitor.commands.ReportCommand;

/**
 * Root CLI entry point.
 *
 * <p>Usage:
 * <pre>
 *   java -jar ai-prompt-monitor.jar monitor --config config/urls.yaml   # superseded by mitm/
 *   java -jar ai-prompt-monitor.jar report  --dir captures
 *   java -jar ai-prompt-monitor.jar peqi    --dir captures --out analytic.csv
 * </pre>
 *
 * <p>The {@code monitor} subcommand runs the original LittleProxy capture layer, which
 * cannot intercept HTTP/2 or WebSocket and is retained only so the DP1 finding stays
 * reproducible. New collection uses the mitmproxy addon in {@code mitm/}; the Java side
 * reads its output with {@code peqi}.
 */
@CommandLine.Command(
        name = "ai-prompt-monitor",
        mixinStandardHelpOptions = true,
        version = "ai-prompt-monitor 0.2.0",
        description = "Captures prompts sent to AI services and derives the PEQI dataset.",
        subcommands = { MonitorCommand.class, ReportCommand.class, PeqiCommand.class }
)
public class Main implements Runnable {

    @Override
    public void run() {
        // No subcommand → show help.
        new CommandLine(this).usage(System.out);
    }

    public static void main(String[] args) {
        System.setProperty("io.netty.maxHeaderSize", "65536");

        int exitCode = new CommandLine(new Main()).execute(args);
        System.exit(exitCode);
    }
}
