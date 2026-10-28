package sk.stuba.fiit.aimonitor.peqi;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class PeqiCalculatorTest {

    private static String line(String pseudonym, String session, String cond, int period,
                               String ts, String prompt) {
        return """
               {"timestamp":"%s","captureId":"c-%s","kind":"prompt","session":"%s",\
               "pseudonym":"%s","condition":"%s","period":%d,"host":"chatgpt.com",\
               "url":"https://chatgpt.com/backend-api/conversation","method":"POST",\
               "promptText":"%s","promptChars":%d,"truncated":false,"scrubbed":{}}"""
                .formatted(ts, ts, session, pseudonym, cond, period, prompt, prompt.length());
    }

    @Test
    @DisplayName("index on a hand-computable session")
    void computesIndexCorrectly(@TempDir Path dir) throws IOException {
        // L0 (w=0), L2 (w=.5), L4 (w=1), plus one off-task that must not count.
        String body = String.join("\n",
                line("aaaa", "S1", "G", 1, "2026-10-07T09:00:00Z", "napis mi kod na binarne vyhladavanie"),
                line("aaaa", "S1", "G", 1, "2026-10-07T09:02:00Z", "preco je to O(log n)"),
                line("aaaa", "S1", "G", 1, "2026-10-07T09:10:00Z", "myslim si ze je to O(n), kde robim chybu"),
                line("aaaa", "S1", "G", 1, "2026-10-07T09:11:00Z", "kolko mame do konca hodiny"));
        Files.writeString(dir.resolve("captures-2026-10-07.jsonl"), body, StandardCharsets.UTF_8);

        PeqiCalculator calc = new PeqiCalculator();
        List<PromptRecord> records = calc.readDirectory(dir);
        assertEquals(4, records.size());

        List<PeqiSummary> rows = calc.summarise(records,
                Map.of("S1", Instant.parse("2026-10-07T08:59:00Z")));
        assertEquals(1, rows.size());
        PeqiSummary s = rows.get(0);

        assertEquals(4, s.nPrompts());
        assertEquals(3, s.nOnTask(), "off-task must leave the denominator");
        assertEquals(0.5, s.peqi(), 1e-9, "(0 + 0.5 + 1) / 3");
        assertEquals(1.0 / 3.0, s.offloadRate(), 1e-9, "one of three prompts was L0/L1");
        assertEquals(2.0 / 3.0, s.generativeRate(), 1e-9);
        assertEquals(0.25, s.offTaskRate(), 1e-9, "one of four prompts overall");
        assertEquals(60.0, s.secondsToFirstPrompt(), 1e-9, "09:00:00 minus 08:59:00");
        assertEquals(120.0, s.medianInterPromptSeconds(), 1e-9, "gaps are 120, 480, 60 s");
        assertFalse(s.unstable(), "three on-task prompts is exactly the stability threshold");
    }

    @Test
    @DisplayName("time to first prompt is left empty rather than guessed")
    void noExerciseStartMeansNoMeasure(@TempDir Path dir) throws IOException {
        Files.writeString(dir.resolve("c.jsonl"),
                line("bbbb", "S1", "A", 2, "2026-10-07T09:00:00Z", "preco je to tak"),
                StandardCharsets.UTF_8);
        PeqiCalculator calc = new PeqiCalculator();
        PeqiSummary s = calc.summarise(calc.readDirectory(dir), Map.of()).get(0);
        assertNull(s.secondsToFirstPrompt(),
                "deriving it from the first captured request would be circular");
        assertNull(s.medianInterPromptSeconds(), "a single prompt has no gaps");
    }

    @Test
    @DisplayName("a session with too few prompts is flagged, not dropped")
    void fewPromptsAreFlagged(@TempDir Path dir) throws IOException {
        Files.writeString(dir.resolve("c.jsonl"), String.join("\n",
                line("cccc", "S1", "G", 1, "2026-10-07T09:00:00Z", "mam to dobre"),
                line("cccc", "S1", "G", 1, "2026-10-07T09:05:00Z", "a teraz")),
                StandardCharsets.UTF_8);
        PeqiCalculator calc = new PeqiCalculator();
        PeqiSummary s = calc.summarise(calc.readDirectory(dir), Map.of()).get(0);
        assertTrue(s.unstable(), "fewer than three on-task prompts makes the index unstable");
        assertFalse(Double.isNaN(s.peqi()), "but the value is still reported");
    }

    @Test
    @DisplayName("an all-off-task session yields no index instead of zero")
    void allOffTaskIsNotZero(@TempDir Path dir) throws IOException {
        Files.writeString(dir.resolve("c.jsonl"),
                line("dddd", "S1", "G", 1, "2026-10-07T09:00:00Z", "ahoj ako sa mas"),
                StandardCharsets.UTF_8);
        PeqiCalculator calc = new PeqiCalculator();
        PeqiSummary s = calc.summarise(calc.readDirectory(dir), Map.of()).get(0);
        assertTrue(Double.isNaN(s.peqi()),
                "zero would claim the pupil offloaded; they simply did something else");
        assertEquals(1.0, s.offTaskRate(), 1e-9);
    }

    @Test
    @DisplayName("a truncated final line loses one prompt, not the lesson")
    void malformedLineIsSkipped(@TempDir Path dir) throws IOException {
        String body = line("eeee", "S1", "G", 1, "2026-10-07T09:00:00Z", "preco je to O(log n)")
                + "\n{\"timestamp\":\"2026-10-07T09:01:00Z\",\"kind\":\"prom";
        Files.writeString(dir.resolve("c.jsonl"), body, StandardCharsets.UTF_8);

        PeqiCalculator calc = new PeqiCalculator();
        List<PromptRecord> records = calc.readDirectory(dir);
        assertEquals(1, records.size());
        assertEquals(1, calc.malformedLines());
    }

    @Test
    @DisplayName("response digests are counted but never treated as prompts")
    void responseDigestsAreIgnored(@TempDir Path dir) throws IOException {
        String body = line("ffff", "S1", "A", 3, "2026-10-07T09:00:00Z", "preco je to tak")
                + "\n{\"kind\":\"response_digest\",\"session\":\"S1\",\"pseudonym\":\"ffff\","
                + "\"bodySha256\":\"deadbeef\",\"bodyBytes\":1234}";
        Files.writeString(dir.resolve("c.jsonl"), body, StandardCharsets.UTF_8);

        PeqiCalculator calc = new PeqiCalculator();
        assertEquals(1, calc.readDirectory(dir).size());
        assertEquals(1, calc.nonPromptRecords());
        assertEquals(0, calc.malformedLines());
    }

    @Test
    @DisplayName("unknown fields from a future capture version do not break the run")
    void unknownFieldsAreTolerated(@TempDir Path dir) throws IOException {
        Files.writeString(dir.resolve("c.jsonl"),
                """
                {"timestamp":"2026-10-07T09:00:00Z","kind":"prompt","session":"S1",\
                "pseudonym":"gggg","condition":"G","period":1,"promptText":"preco je to tak",\
                "someFieldAddedNextSemester":42,"nested":{"a":1}}""",
                StandardCharsets.UTF_8);
        PeqiCalculator calc = new PeqiCalculator();
        assertEquals(1, calc.readDirectory(dir).size());
        assertEquals(0, calc.malformedLines());
    }

    @Test
    @DisplayName("pupils and sessions are grouped separately")
    void groupsByPupilAndSession(@TempDir Path dir) throws IOException {
        Files.writeString(dir.resolve("c.jsonl"), String.join("\n",
                line("aaaa", "S1", "G", 1, "2026-10-07T09:00:00Z", "preco je to tak"),
                line("aaaa", "S2", "A", 2, "2026-10-14T09:00:00Z", "preco je to tak"),
                line("bbbb", "S1", "G", 1, "2026-10-07T09:00:00Z", "preco je to tak")),
                StandardCharsets.UTF_8);
        PeqiCalculator calc = new PeqiCalculator();
        List<PeqiSummary> rows = calc.summarise(calc.readDirectory(dir), Map.of());
        assertEquals(3, rows.size());
    }

    @Test
    @DisplayName("the CSV carries no free text")
    void csvContainsNoPromptText(@TempDir Path dir) throws IOException {
        String secret = "moje meno je Jakub a bývam na Hlavnej 5";
        Files.writeString(dir.resolve("c.jsonl"),
                line("hhhh", "S1", "G", 1, "2026-10-07T09:00:00Z", secret),
                StandardCharsets.UTF_8);
        PeqiCalculator calc = new PeqiCalculator();
        List<PeqiSummary> rows = calc.summarise(calc.readDirectory(dir), Map.of());

        Path csv = dir.resolve("analytic.csv");
        calc.writeCsv(rows, csv);
        String text = Files.readString(csv, StandardCharsets.UTF_8);

        assertFalse(text.contains("Jakub"), "the analytic dataset must never carry free text");
        assertFalse(text.contains("Hlavnej"));
        assertTrue(text.startsWith(PeqiSummary.csvHeader()));
        assertEquals(2, text.strip().split("\n").length, "header plus one row");
    }

    @Test
    @DisplayName("only pupil prompts are scored; the exercise client's other events are not")
    void onlyPromptEventsEnterTheIndex(@TempDir Path dir) throws IOException {
        // The exercise client writes the same JSON Lines format as the capture layer,
        // and one of the kinds it writes is `self_explanation` -- the text condition A
        // REQUIRES a pupil to type before the worked solution unlocks.
        //
        // If that text were scored as a prompt, condition A would score higher on the
        // mediator purely because the interface made pupils write it, which is the
        // differential measurement error the design has to avoid. Hence this test: it
        // is a property of the study, not a detail of the parser.
        String selfExplanation = """
                {"timestamp":"2026-10-07T09:05:00Z","eventId":"e1","kind":"self_explanation",\
                "session":"S1","pseudonym":"iiii","condition":"A","period":1,\
                "promptText":"myslim si ze interval sa zmensi na polovicu lebo delim stred",\
                "promptChars":62}""";
        String body = String.join("\n",
                line("iiii", "S1", "A", 1, "2026-10-07T09:00:00Z", "napis mi kod na binarne vyhladavanie"),
                selfExplanation);
        Files.writeString(dir.resolve("captures-2026-10-07.jsonl"), body, StandardCharsets.UTF_8);

        PeqiCalculator calc = new PeqiCalculator();
        List<PeqiSummary> rows = calc.summarise(calc.readDirectory(dir), Map.of());
        assertEquals(1, rows.size());
        PeqiSummary s = rows.get(0);

        assertEquals(1, s.nPrompts(), "the self-explanation is not a prompt");
        assertEquals(0.0, s.peqi(), 1e-9,
                "scoring it would have made this session look like L4 work");
    }
}
