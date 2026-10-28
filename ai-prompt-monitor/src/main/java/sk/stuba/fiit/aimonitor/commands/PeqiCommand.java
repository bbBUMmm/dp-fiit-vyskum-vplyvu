package sk.stuba.fiit.aimonitor.commands;

import picocli.CommandLine;
import sk.stuba.fiit.aimonitor.peqi.PeqiCalculator;
import sk.stuba.fiit.aimonitor.peqi.PeqiSummary;
import sk.stuba.fiit.aimonitor.peqi.PromptClassifier;
import sk.stuba.fiit.aimonitor.peqi.PromptLevel;
import sk.stuba.fiit.aimonitor.peqi.PromptRecord;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.Callable;

/**
 * Computes the Prompt Epistemic Quality Index from captured JSON Lines files and writes
 * the analytic dataset.
 *
 * <pre>
 *   java -jar ai-prompt-monitor.jar peqi --dir captures --out analytic.csv
 *   java -jar ai-prompt-monitor.jar peqi --explain "myslim si ze to je O(n), kde robim chybu"
 * </pre>
 */
@CommandLine.Command(
        name = "peqi",
        mixinStandardHelpOptions = true,
        description = "Classifies captured prompts and writes the per-pupil analytic dataset."
)
public class PeqiCommand implements Callable<Integer> {

    @CommandLine.Option(names = {"-d", "--dir"},
            description = "Directory holding captures-*.jsonl files.")
    Path dir;

    @CommandLine.Option(names = {"-o", "--out"},
            description = "Where to write the analytic CSV. Default: <dir>/analytic.csv")
    Path out;

    @CommandLine.Option(names = {"--explain"},
            description = "Classify a single prompt and show which rules fired, then exit.")
    String explain;

    @Override
    public Integer call() throws Exception {
        if (explain != null) {
            return explainOne(explain);
        }
        if (dir == null) {
            System.err.println("Either --dir or --explain is required.");
            return 2;
        }
        if (!Files.isDirectory(dir)) {
            System.err.println("Not a directory: " + dir);
            return 2;
        }

        PeqiCalculator calc = new PeqiCalculator();
        List<PromptRecord> records = calc.readDirectory(dir);
        if (records.isEmpty()) {
            System.out.println("No prompt records found in " + dir);
            System.out.println("  (" + calc.nonPromptRecords() + " non-prompt records, "
                    + calc.malformedLines() + " malformed lines)");
            return 1;
        }

        List<PeqiSummary> rows = calc.summarise(records, Map.of());
        Path target = out != null ? out : dir.resolve("analytic.csv");
        calc.writeCsv(rows, target);

        report(records, rows, calc, target);
        return 0;
    }

    private void report(List<PromptRecord> records, List<PeqiSummary> rows,
                        PeqiCalculator calc, Path target) {
        System.out.printf(Locale.ROOT,
                "%d prompts, %d pupil-sessions, %d malformed lines skipped%n",
                records.size(), rows.size(), calc.malformedLines());

        System.out.println();
        System.out.println("  condition   n     PEQI   offload   on-task/pupil   unstable");
        System.out.println("  ---------------------------------------------------------");
        rows.stream()
                .collect(java.util.stream.Collectors.groupingBy(
                        r -> r.condition() == null ? "?" : r.condition()))
                .forEach((cond, group) -> {
                    double peqi = group.stream().mapToDouble(PeqiSummary::peqi)
                            .filter(v -> !Double.isNaN(v)).average().orElse(Double.NaN);
                    double off = group.stream().mapToDouble(PeqiSummary::offloadRate)
                            .filter(v -> !Double.isNaN(v)).average().orElse(Double.NaN);
                    double n = group.stream().mapToInt(PeqiSummary::nOnTask).average().orElse(0);
                    long unstable = group.stream().filter(PeqiSummary::unstable).count();
                    System.out.printf(Locale.ROOT, "  %-10s %3d   %6.3f   %6.3f   %12.1f   %8d%n",
                            cond, group.size(), peqi, off, n, unstable);
                });

        long scrubbed = rows.stream().mapToInt(PeqiSummary::scrubbedItems).sum();
        System.out.printf(Locale.ROOT,
                "%n  %d personal-data items were removed before storage.%n", scrubbed);
        System.out.println("  Written: " + target.toAbsolutePath());
    }

    private Integer explainOne(String prompt) {
        PromptLevel level = PromptClassifier.classify(prompt);
        System.out.println("prompt : " + prompt);
        System.out.println("folded : " + PromptClassifier.normalise(prompt));
        System.out.printf(Locale.ROOT, "level  : %s (%s, ICAP %s, weight %.2f)%n",
                level.name(), level.label(), level.icap(), level.weight());
        System.out.println("rules  :");
        PromptClassifier.explain(prompt).forEach(s -> System.out.println("         " + s));
        return 0;
    }
}
