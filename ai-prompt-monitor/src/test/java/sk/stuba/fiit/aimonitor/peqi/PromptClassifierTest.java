package sk.stuba.fiit.aimonitor.peqi;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * The anchor corpus from Appendix B, as a test.
 *
 * <p>These cases are the coding manual's binding decisions. If one of them fails, the
 * manual and the code have diverged, and the index no longer measures what the thesis
 * says it measures — so this file is as much a specification as it is a test.
 */
class PromptClassifierTest {

    @ParameterizedTest(name = "[{index}] {0} -> {1}")
    @DisplayName("anchor corpus: each level")
    @CsvSource(delimiter = '|', value = {
            // ---- L0 SOLVE: wants an artefact, contributes nothing --------
            "napis mi kod na binarne vyhladavanie v pythone | L0",
            "naprogramuj fibonacciho s memoizaciou          | L0",
            "vypis mi vsetky kroky riesenia ulohy 2         | L0",
            "chcem hotovy kod ktory vlozim do editora       | L0",

            // ---- L1 VERIFY: own work in, verdict out ---------------------
            "mam to dobre?                                  | L1",
            "skontroluj mi tento kod                        | L1",
            "je odpoved O(n log n) spravna?                 | L1",
            "dobre alebo zle?                               | L1",

            // ---- L2 EXPLAIN: asks for meaning ----------------------------
            "preco je zlozitost binarneho vyhladavania O(log n) | L2",
            "vysvetli mi co znamena ze algoritmus je logaritmicky | L2",
            "co je to memoizacia                            | L2",
            "povedz to jednoduchsie                         | L2",

            // ---- L3 ELABORATE: needs integration -------------------------
            "kedy je linearne vyhladavanie lepsie ako binarne | L3",
            "aky je rozdiel medzi insertion sortom a merge sortom | L3",
            "v akych pripadoch sa neoplati memoizacia       | L3",
            "plati to aj pre spajany zoznam alebo len pre pole | L3",

            // ---- L4 SELF-EXPLAIN: own reasoning, up for critique ---------
            "myslim si ze to je O(n) lebo cyklus prejde cele pole, kde robim chybu | L4",
            "podla mna je chyba v tom ze porovnavam hi < lo, suhlasis | L4",
            "chapem to tak ze zlucovanie je linearne, je to spravne odovodnenie | L4",
            // A guess plus "confirm it" is a verdict request on an ANSWER, so L1.
            // This case used to be coded L4 on the strength of "tipujem" alone.
            // The boundary was moved deliberately: L4 now requires that the pupil
            // put an ARGUMENT up for judgement, not merely a value. See isVeneer.
            // The corresponding anchor in the Slovak corpus carries the reason
            // ("... lebo 16 -> 8 -> 4 -> 2 -> 1 ...") and is still L4.
            "tipujem ze odpoved su 4 kroky, potvrd mi to    | L1",
            "tipujem ze su to 4 kroky lebo 16 8 4 2 1, potvrd mi to | L4",

            // ---- X OFF-TASK ---------------------------------------------
            "ahoj ako sa mas                                | OFF_TASK",
            "kolko mame do konca hodiny                     | OFF_TASK",
            "pomoz mi s domacou ulohou z dejepisu           | OFF_TASK",
    })
    void classifiesAnchorCorpus(String prompt, PromptLevel expected) {
        assertEquals(expected, PromptClassifier.classify(prompt.trim()),
                () -> "misclassified: " + prompt);
    }

    @Test
    @DisplayName("binding rule: a prompt with several elements takes the highest level")
    void highestLevelWins() {
        // The pupil asked for the code AND for a reason. They did the L2 work, so L2.
        assertEquals(PromptLevel.L2,
                PromptClassifier.classify("napis mi kod a vysvetli preco je to O(log n)"));
        // Verification plus a reason is L2, not L1.
        assertEquals(PromptLevel.L2, PromptClassifier.classify("je to spravne a preco?"));
        // Verification plus the pupil's own reasoning is L4.
        assertEquals(PromptLevel.L4,
                PromptClassifier.classify("mam to dobre? myslim ze ano lebo cyklus prejde pole"));
    }

    @Test
    @DisplayName("binding rule: diacritics must not change the coding")
    void diacriticsAreIrrelevant() {
        assertEquals(PromptClassifier.classify("preco je to O(log n)?"),
                PromptClassifier.classify("prečo je to O(log n)?"));
        assertEquals(PromptClassifier.classify("kedy je linearne lepsie ako binarne"),
                PromptClassifier.classify("kedy je lineárne lepšie ako binárne"));
        assertEquals(PromptLevel.L4,
                PromptClassifier.classify("myslím si, že je to O(n), kde robím chybu?"));
    }

    @Test
    @DisplayName("regression: 'lebo' inside 'alebo' must not promote to L4")
    void aleboIsNotReasoning() {
        // "alebo" ("or") contains "lebo" ("because"). Treating the substring as a
        // reasoning marker promoted plain verification requests to the top of the
        // scale, which would have deflated the reported offloading rate.
        assertEquals(PromptLevel.L1, PromptClassifier.classify("dobre alebo zle?"));
        assertEquals(PromptLevel.L3,
                PromptClassifier.classify("plati to aj pre spajany zoznam alebo len pre pole"));
    }

    @Test
    @DisplayName("binding rule: bare pasted code is a verification request")
    void bareCodeIsVerification() {
        assertEquals(PromptLevel.L1,
                PromptClassifier.classify("def bs(a,x): lo=0; hi=len(a)-1; return -1"));
    }

    @Test
    @DisplayName("binding rule: off-task wording plus domain vocabulary stays on task")
    void domainVocabularyOverridesWeakOffTaskSignal() {
        // "ucitel" alone reads off-task, but this is plainly about the exercise.
        assertEquals(PromptLevel.L2,
                PromptClassifier.classify("ucitel povedal ze pole musi byt zoradene, preco?"));
    }

    @Test
    @DisplayName("unrecognisable prompts fall to L1, not L0")
    void unknownFallsToVerification() {
        // Guessing L0 would inflate the offloading rate, which is the measure the
        // thesis reports; the conservative default is the middle of the low band.
        assertEquals(PromptLevel.L1, PromptClassifier.classify("hmm"));
        assertEquals(PromptLevel.L1, PromptClassifier.classify("a co dalej"));
    }

    @Test
    @DisplayName("empty and null input are off-task, never a crash")
    void emptyIsSafe() {
        assertEquals(PromptLevel.OFF_TASK, PromptClassifier.classify(""));
        assertEquals(PromptLevel.OFF_TASK, PromptClassifier.classify("   "));
        assertEquals(PromptLevel.OFF_TASK, PromptClassifier.classify(null));
    }

    @Test
    @DisplayName("weights are monotone and bounded, and off-task is excluded")
    void weightsAreWellFormed() {
        assertEquals(0.00, PromptLevel.L0.weight());
        assertEquals(1.00, PromptLevel.L4.weight());
        assertTrue(PromptLevel.L0.weight() < PromptLevel.L1.weight());
        assertTrue(PromptLevel.L1.weight() < PromptLevel.L2.weight());
        assertTrue(PromptLevel.L2.weight() < PromptLevel.L3.weight());
        assertTrue(PromptLevel.L3.weight() < PromptLevel.L4.weight());
        assertTrue(Double.isNaN(PromptLevel.OFF_TASK.weight()));
        assertTrue(PromptLevel.L0.offloading() && PromptLevel.L1.offloading());
        assertTrue(!PromptLevel.L2.offloading());
    }

    @Test
    @DisplayName("a coding decision can be audited")
    void explainIsInspectable() {
        var rules = PromptClassifier.explain("myslim si ze to je O(n), kde robim chybu");
        assertTrue(rules.contains("self_explain=true"),
                () -> "expected the self-explanation rule to fire: " + rules);
    }
}
