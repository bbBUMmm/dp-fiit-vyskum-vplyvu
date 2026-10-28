package sk.stuba.fiit.aimonitor.peqi;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * The two implementations of the PEQI taxonomy must agree, prompt for prompt.
 *
 * <p>There are two: {@code analysis/peqi.py}, which produces every classifier figure
 * printed in the thesis, and {@link PromptClassifier}, which is what actually runs on
 * captured traffic. One specification, two programs, and no mechanism keeping them
 * together except this test.
 *
 * <p>The mechanism was needed. The Python side was repaired for a defect that let a
 * four-word epistemic opening promote any request for a finished solution to the top of
 * the scale; the Java side was not, and stayed broken. Since the Java side is the one
 * that scores real pupils, the thesis would have reported numbers from a classifier that
 * still had the hole, while its own validation -- run against the repaired Python --
 * reported that the hole was closed.
 *
 * <p>So the specification is pinned as data. {@code analysis/peqi.py} writes
 * {@code cross_impl_corpus.json}: every anchor, every anchor with a compliance veneer in
 * front of it, and the boundary cases the coding manual declares binding, each with the
 * level Python assigns. This test demands the same answers here. Either implementation
 * may change; neither may change alone.
 */
class CrossImplementationTest {

    private static final String FIXTURE = "/cross_impl_corpus.json";

    private record Case(String prompt, String level, String origin) {
    }

    private static List<Case> load() throws Exception {
        try (InputStream in = CrossImplementationTest.class.getResourceAsStream(FIXTURE)) {
            assertTrue(in != null,
                    FIXTURE + " is missing. Run: python analysis/peqi.py");
            JsonNode root = new ObjectMapper().readTree(
                    new String(in.readAllBytes(), StandardCharsets.UTF_8));
            List<Case> out = new ArrayList<>();
            for (JsonNode n : root.get("cases")) {
                out.add(new Case(n.get("prompt").asText(),
                        n.get("level").asText(),
                        n.get("origin").asText()));
            }
            return out;
        }
    }

    /** "L0".."L4" and "X" on the Python side; PromptLevel on this side. */
    private static PromptLevel parse(String level) {
        return switch (level) {
            case "L0" -> PromptLevel.L0;
            case "L1" -> PromptLevel.L1;
            case "L2" -> PromptLevel.L2;
            case "L3" -> PromptLevel.L3;
            case "L4" -> PromptLevel.L4;
            case "X" -> PromptLevel.OFF_TASK;
            default -> throw new IllegalArgumentException("unknown level: " + level);
        };
    }

    @Test
    @DisplayName("the Java classifier reproduces every level the Python one assigns")
    void agreesWithPython() throws Exception {
        List<Case> cases = load();
        assertTrue(cases.size() >= 120,
                "fixture looks truncated: " + cases.size() + " cases");

        List<String> disagreements = new ArrayList<>();
        for (Case c : cases) {
            PromptLevel got = PromptClassifier.classify(c.prompt());
            PromptLevel want = parse(c.level());
            if (got != want) {
                disagreements.add(String.format("[%s] %s%n    python=%s java=%s%n    %s",
                        c.origin(), c.prompt(), want, got,
                        String.join(", ", PromptClassifier.explain(c.prompt()))));
            }
        }
        assertEquals(List.of(), disagreements,
                () -> disagreements.size() + " of " + cases.size()
                        + " prompts are coded differently by the two implementations:\n"
                        + String.join("\n", disagreements));
    }

    @Test
    @DisplayName("the fixture actually exercises the veneer attack")
    void fixtureCoversTheVeneer() throws Exception {
        // A test that passes because the fixture is empty of hard cases is worse than
        // no test: it reports safety it has not checked.
        List<Case> cases = load();
        long veneered = cases.stream().filter(c -> "veneered".equals(c.origin())).count();
        assertTrue(veneered >= 30,
                "only " + veneered + " veneered prompts in the fixture");
        boolean anyL4 = cases.stream()
                .filter(c -> "veneered".equals(c.origin()))
                .anyMatch(c -> "L4".equals(c.level()));
        assertTrue(!anyL4,
                "a veneered L0/L1 prompt is recorded as L4 in the fixture itself, "
                        + "which means the Python side regressed");
    }
}
