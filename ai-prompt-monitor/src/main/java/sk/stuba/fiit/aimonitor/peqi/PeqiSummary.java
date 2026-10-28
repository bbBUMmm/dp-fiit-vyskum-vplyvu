package sk.stuba.fiit.aimonitor.peqi;

import java.time.Duration;
import java.time.Instant;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;

/**
 * The per-pupil, per-session row of the analytic dataset.
 *
 * <p>This is the only thing that leaves the tool: counts and derived measures, never
 * free text. Publishing prompts written by minors is not possible even after
 * pseudonymisation, because free text cannot be reliably anonymised; publishing this
 * row is, which is what makes the analysis reproducible by someone who will never be
 * allowed to see the corpus.
 */
public record PeqiSummary(
        String pseudonym,
        String session,
        String condition,
        Integer period,
        int nPrompts,
        int nOnTask,
        Map<PromptLevel, Integer> counts,
        double peqi,
        double offloadRate,
        double generativeRate,
        double offTaskRate,
        Double secondsToFirstPrompt,
        Double medianInterPromptSeconds,
        int scrubbedItems,
        boolean unstable
) {

    /** Fewer than this many on-task prompts makes the index unstable; see Appendix B. */
    public static final int MIN_STABLE_PROMPTS = 3;

    public static PeqiSummary of(String pseudonym, String session, String condition,
                                 Integer period, List<PromptRecord> records,
                                 Instant exerciseStart) {
        Map<PromptLevel, Integer> counts = new EnumMap<>(PromptLevel.class);
        for (PromptLevel l : PromptLevel.values()) {
            counts.put(l, 0);
        }

        double weightSum = 0.0;
        int onTask = 0;
        int scrubbed = 0;
        for (PromptRecord r : records) {
            PromptLevel level = PromptClassifier.classify(r.promptText());
            counts.merge(level, 1, Integer::sum);
            scrubbed += r.scrubbedCount();
            if (level.onTask()) {
                weightSum += level.weight();
                onTask++;
            }
        }

        int n = records.size();
        double peqi = onTask == 0 ? Double.NaN : weightSum / onTask;
        double offload = onTask == 0 ? Double.NaN
                : (counts.get(PromptLevel.L0) + counts.get(PromptLevel.L1)) / (double) onTask;
        double generative = onTask == 0 ? Double.NaN : 1.0 - offload;
        double offTask = n == 0 ? Double.NaN : counts.get(PromptLevel.OFF_TASK) / (double) n;

        List<Instant> times = records.stream()
                .map(PromptRecord::timestamp)
                .filter(java.util.Objects::nonNull)
                .sorted()
                .toList();

        Double toFirst = null;
        if (exerciseStart != null && !times.isEmpty()) {
            toFirst = Duration.between(exerciseStart, times.get(0)).toMillis() / 1000.0;
        }

        Double medianGap = null;
        if (times.size() >= 2) {
            double[] gaps = new double[times.size() - 1];
            for (int i = 1; i < times.size(); i++) {
                gaps[i - 1] = Duration.between(times.get(i - 1), times.get(i)).toMillis() / 1000.0;
            }
            java.util.Arrays.sort(gaps);
            int m = gaps.length;
            medianGap = m % 2 == 1 ? gaps[m / 2] : (gaps[m / 2 - 1] + gaps[m / 2]) / 2.0;
        }

        return new PeqiSummary(pseudonym, session, condition, period, n, onTask, counts,
                peqi, offload, generative, offTask, toFirst, medianGap, scrubbed,
                onTask < MIN_STABLE_PROMPTS);
    }

    public static String csvHeader() {
        return "pseudonym,session,condition,period,n_prompts,n_on_task,"
                + "n_L0,n_L1,n_L2,n_L3,n_L4,n_off_task,"
                + "peqi,offload_rate,generative_rate,off_task_rate,"
                + "t_first_prompt_s,median_inter_prompt_s,scrubbed_items,unstable";
    }

    public String toCsvRow() {
        return String.join(",",
                pseudonym, session, condition, period == null ? "" : period.toString(),
                Integer.toString(nPrompts), Integer.toString(nOnTask),
                c(PromptLevel.L0), c(PromptLevel.L1), c(PromptLevel.L2),
                c(PromptLevel.L3), c(PromptLevel.L4), c(PromptLevel.OFF_TASK),
                num(peqi), num(offloadRate), num(generativeRate), num(offTaskRate),
                num(secondsToFirstPrompt), num(medianInterPromptSeconds),
                Integer.toString(scrubbedItems), Boolean.toString(unstable));
    }

    private String c(PromptLevel l) {
        return Integer.toString(counts.getOrDefault(l, 0));
    }

    private static String num(Double v) {
        return v == null || v.isNaN() ? "" : String.format(java.util.Locale.ROOT, "%.4f", v);
    }

    private static String num(double v) {
        return Double.isNaN(v) ? "" : String.format(java.util.Locale.ROOT, "%.4f", v);
    }
}
