package sk.stuba.fiit.aimonitor.peqi;

/**
 * Levels of the prompt taxonomy underlying the Prompt Epistemic Quality Index.
 *
 * <p>The ordering is not arbitrary. It follows the ICAP framework (Chi &amp; Wylie, 2014),
 * which ranks cognitive engagement as passive &lt; active &lt; constructive &lt; interactive
 * and predicts learning outcomes in that order. The weights turn that ordinal scale into
 * an index on [0, 1].
 *
 * <p>{@link #OFF_TASK} is excluded from the index denominator rather than scored zero:
 * a pupil who asks about the weather has not offloaded, they have simply done something
 * else, and conflating the two would make PEQI a measure of attention instead of
 * epistemic quality.
 *
 * <p>The authoritative definitions, the decision procedure and the binding boundary
 * rules live in Appendix B of the thesis; this enum is that appendix as code.
 */
public enum PromptLevel {

    /** Asks for a complete artefact with no contribution from the pupil. */
    L0("SOLVE", "passive", 0.00),

    /** Submits own work and asks only for a verdict or a repair, never for a reason. */
    L1("VERIFY", "active (low)", 0.25),

    /** Asks for the meaning of a concept, a step, or an observed behaviour. */
    L2("EXPLAIN", "active", 0.50),

    /** Asks a question that requires integration: comparison, conditions, counter-example. */
    L3("ELABORATE", "constructive", 0.75),

    /** States the pupil's own reasoning and asks for it to be critiqued. */
    L4("SELF_EXPLAIN", "interactive", 1.00),

    /** Unrelated to the task. Excluded from the index denominator. */
    OFF_TASK("OFF_TASK", "n/a", Double.NaN);

    private final String label;
    private final String icap;
    private final double weight;

    PromptLevel(String label, String icap, double weight) {
        this.label = label;
        this.icap = icap;
        this.weight = weight;
    }

    public String label() {
        return label;
    }

    /** The ICAP band this level corresponds to. */
    public String icap() {
        return icap;
    }

    /** Weight in the index; NaN for {@link #OFF_TASK}, which is excluded instead. */
    public double weight() {
        return weight;
    }

    public boolean onTask() {
        return this != OFF_TASK;
    }

    /** True for the two levels that count towards the offloading rate. */
    public boolean offloading() {
        return this == L0 || this == L1;
    }
}
