package sk.stuba.fiit.aimonitor.peqi;

import java.text.Normalizer;
import java.util.List;
import java.util.regex.Pattern;

/**
 * Assigns a {@link PromptLevel} to one prompt.
 *
 * <p>This is the decision procedure from Appendix B of the thesis, executed as code.
 * The rules are applied <em>in order</em> and the first one that fires wins. The fixed
 * order is the whole point: without it, a prompt containing several elements would be
 * coded differently by different people, and the inter-rater reliability the index
 * depends on would collapse.
 *
 * <p>Two design decisions are worth stating because they cost accuracy on purpose.
 *
 * <p><b>Transparent features, not a language model.</b> A school, a supervisor or an
 * opponent must be able to check <em>why</em> a given prompt was coded the way it was.
 * That is possible with a handful of named patterns and impossible with an opaque
 * classifier. Using a language model to measure how pupils use a language model would
 * also make the measurement depend on an external service that can change under us
 * mid-study.
 *
 * <p><b>Diacritics are folded before matching.</b> Pupils type without diacritics far
 * more often than not, and a rule that only fires on "prečo" but not on "preco" would
 * systematically under-detect exactly the population that types fastest.
 *
 * <p>Errors this classifier makes are, by construction, shifts to an adjacent level
 * (measured at 98.8&nbsp;% on the anchor corpus). On an ordinal scale that attenuates an
 * effect rather than reversing its sign, which is the failure mode we can live with.
 */
public final class PromptClassifier {

    private static final int FLAGS = Pattern.CASE_INSENSITIVE | Pattern.UNICODE_CASE;

    /** Verbs that request production of something. */
    private static final Pattern SOLVE_VERB = Pattern.compile(
            "\\b(napis|naprogramuj|vyries|sprav|urob|dokonci|dopln|vypis|vytvor"
                    + "|implementuj|zostav|vygeneruj|daj mi|chcem)\\b", FLAGS);

    /** Nouns naming a deliverable. */
    private static final Pattern ARTEFACT = Pattern.compile(
            "\\b(kod|funkci\\w*|pseudokod|riesenie|odpoved\\w*|program|implementaci\\w*"
                    + "|tabulku|skript|triedu|metodu|vystup)\\b", FLAGS);

    private static final Pattern VERIFY = Pattern.compile(
            "(je to spravne|je toto spravne|mam to dobre|skontroluj|over |overte|oprav"
                    + "|dobre alebo zle|v poriadku|funguje toto|nefunguje|je .{0,20}spravn\\w*)",
            FLAGS);

    private static final Pattern EXPLAIN = Pattern.compile(
            "(preco|vysvetli|co znamena|co je to|ako funguje|co presne robi|ako sa pocita"
                    + "|naco |ako viem|povedz to jednoduchsie|co si myslel)", FLAGS);

    // Kept in step with analysis/peqi.py::ELABORATE. The two lists were allowed to
    // differ once, and four anchors came out one level apart depending on which
    // program scored them; CrossImplementationTest exists to stop that recurring.
    // Note what is ABSENT: "lepsie ako" / "horsie ako" used to be here and coded
    // "preco je 2^n horsie ako n^2" as L3. A comparison of two things the lesson
    // already covered is a request for meaning, not integration, and the hand-coded
    // anchor says L2.
    private static final Pattern ELABORATE = Pattern.compile(
            "(kedy je|rozdiel medzi|porovnaj|v akych pripadoch|co by sa stalo"
                    + "|protipriklad|oplati|hranicne pripady|plati to aj|da sa .{0,30}pouzit aj"
                    + "|ako suvisi|ake su .{0,30}pripady|namiesto|ako sa zmeni|ako by sa zmenil"
                    + "|co sa stane ked|a nie |preco nestaci|preco nemozeme"
                    + "|preco sa nepouziva)", FLAGS);

    /**
     * The pupil is putting their own work on the table. Combined with {@link #FAILURE}
     * this is a repair request (L1), not a request for meaning (L2), even when it is
     * phrased with "why": "preco mi to nefunguje, tu je kod" is the pupil asking for
     * their code to be fixed.
     */
    private static final Pattern OWN_WORK = Pattern.compile(
            "(tu je kod|tu je moj|toto som napisal|toto som spravil|mam tu|moj kod"
                    + "|moja funkcia|moj pseudokod|napisal som|spravil som|skusil som"
                    + "|mam v tabulke|som zoradil|moja odpoved)", FLAGS);

    /** A report that something the pupil made is broken. */
    private static final Pattern FAILURE = Pattern.compile(
            "(nefunguje|nejde mi|hadze chybu|hodilo|vypisuje chybu|padne|spadne"
                    + "|zly vysledok|iny vysledok ako|nespravny vystup|sprav s tym"
                    + "|oprav|indexerror|chybu v tomto)", FLAGS);

    private static final Pattern SELF_EXPLAIN = Pattern.compile(
            "(myslim si|myslim ze|podla mna|mam pocit|uvazujem|moja uvaha|moja hypoteza"
                    + "|moja domnienka|tipujem|chapem to tak|napisal som ze|napadlo mi"
                    + "|skusil som|kde robim chybu|kde sa mylim|kde mi to nesedi|je to tak"
                    + "|sedi to|suhlasis|potvrd mi|dava to zmysel|je ta uvaha|je moja uvaha"
                    + "|overil som si)", FLAGS);
    // Note: "lebo" ("because") is not in this list. It is not a MARKER of the pupil
    // speaking about their own thinking; it is a marker of a REASON, and it belongs in
    // REASON below, where it decides whether a marker that did fire is backed by an
    // argument. It must also be anchored on both sides: unanchored it matches inside
    // "alebo" ("or"), which promoted "dobre alebo zle?" to the top of the scale.

    // "hra" is anchored on both sides: unanchored it matches inside "hranicne",
    // and an off-task match on a genuine edge-case question is only prevented by
    // the domain-vocabulary override, which is one safeguard too few.
    private static final Pattern OFF_TASK = Pattern.compile(
            "(ahoj|ako sa mas|datum|basen|do konca hodiny|emoji|ucitel\\w*"
                    + "|dejepis|pocasie|\\bhra\\b|vtip\\w*|test test|nudi ma)", FLAGS);

    /** Domain vocabulary; its presence overrides a weak off-task signal. */
    private static final Pattern DOMAIN = Pattern.compile(
            "(pole|zlozit\\w*|algoritm\\w*|rekurz\\w*|memoiz\\w*|fibonacci|sort\\w*"
                    + "|triedeni\\w*|vyhladav\\w*|binarn\\w*|linearn\\w*|cykl\\w*|iterac\\w*"
                    + "|log n|o\\(|interval|zluc\\w*|krok\\w*|index|porovnan\\w*|ulohu|uloha)",
            FLAGS);

    private static final Pattern CODE = Pattern.compile(
            "(\\bdef \\b|\\bfor \\b|\\bwhile \\b|\\breturn\\b|\\{|\\}|==|<=|>=|\\[i\\]|;|\\(\\))");

    /**
     * Asking for the result with the reasoning explicitly excluded. Semantically L0 even
     * when no imperative verb is present, and it outranks everything except off-task:
     * unlike an ordinary multi-part prompt there is no second cognitive act to credit,
     * because the pupil has ruled out the one that would have counted.
     */
    private static final Pattern ANSWER_ONLY = Pattern.compile(
            "(len vysledok|len odpoved|iba vysledok|iba odpoved|bez vysvetlenia"
                    + "|nevysvetluj|aka je odpoved|aky je vysledok|aka je spravna odpoved)",
            FLAGS);

    /** Causal connectives: the linguistic signature of a pupil-supplied REASON. */
    private static final Pattern REASON = Pattern.compile(
            "\\b(lebo|pretoze|preto|takze|kedze|tym padom|z toho vyplyva|je chyba v tom"
                    + "|chyba je v tom|problem je v tom|je to tym ze|a teda|kvoli tomu)\\b",
            FLAGS);

    /** The pupil names their own reasoning as the thing to be judged. */
    private static final Pattern REASONING_NOUN = Pattern.compile(
            "(moja uvaha|ta uvaha|tu uvahu|je moja uvaha|moja hypoteza|moja domnienka"
                    + "|odovodnenie|moj postup|moja diagnoza|touto diagnozou|moje vysvetlenie)",
            FLAGS);

    /** A conjecture the pupil is putting forward for the first time. */
    private static final Pattern CONJECTURE = Pattern.compile(
            "(by sa dalo|bolo by|malo by|mohlo by|dal by sa|co keby|keby som)", FLAGS);

    /**
     * A request to LOCATE the error, as opposed to a request for a verdict on an answer.
     * "Is this right?" can be asked about a number; "where am I going wrong?" can only be
     * asked about a line of reasoning, so it puts the pupil's reasoning up for judgement
     * even when no connective spells it out. This is the L1/L4 boundary in its sharpest
     * form.
     */
    private static final Pattern DIAGNOSTIC = Pattern.compile(
            "(kde robim chybu|kde sa mylim|kde mi to nesedi|co mi tu nesedi"
                    + "|kde je chyba v mojej|kde je chyba v mojom|preco mi to nevychadza"
                    + "|kde mam chybu)", FLAGS);

    /** A demand for a finished artefact, wider than SOLVE_VERB (see isVeneer). */
    private static final Pattern DEMAND_VERB = Pattern.compile(
            "(\\b(napis|naprogramuj|vyries|dopln|vypis|vytvor|implementuj|zostav"
                    + "|vygeneruj|potrebujem|chcem)\\b|sprav mi|urob mi|daj mi|posli mi"
                    + "|ukaz mi cel)", FLAGS);

    private static final Pattern TWO_NUMBERS = Pattern.compile("\\d+\\D+\\d+");
    private static final Pattern NUMBER_OPERATOR = Pattern.compile("\\d\\s*[\\^*/+=<>-]");

    private PromptClassifier() {
    }

    /**
     * The text a self-explanation marker introduces, up to any artefact demand.
     *
     * <p>A claim is what the pupil asserts. Everything from the end of the epistemic
     * marker to the point where they start saying what to produce is the candidate
     * claim; the demand itself is not part of it.
     */
    private static String claimSpan(String t) {
        var m = SELF_EXPLAIN.matcher(t);
        if (!m.find()) {
            return "";
        }
        String rest = t.substring(m.end());
        var d = DEMAND_VERB.matcher(rest);
        return d.find() ? rest.substring(0, d.start()) : rest;
    }

    /**
     * True when an epistemic marker is present but no ARGUMENT stands behind it.
     *
     * <p>The taxonomy separates L1 from L4 by what is offered for judgement: L1 puts an
     * answer up for a verdict, L4 puts a line of reasoning up for a verdict. So the
     * marker counts only when the pupil supplies a justification -- a causal connective,
     * a noun naming their own reasoning, a conjecture they are floating, or worked
     * arithmetic.
     *
     * <p>This rule is not cosmetic and it is not about gaming by pupils. Condition A's
     * self-explanation gate <em>requires</em> pupils to write exactly such an opening
     * before the worked solution unlocks. Without this check the index would score
     * condition A higher for interface reasons, on every prompt, and the study's
     * mediator would be biased by the manipulation it is supposed to measure. Measured
     * on the anchor corpus the bias was +0.88 of PEQI per prompt -- more than twice the
     * effect the study is powered to detect. See Section 5 of the thesis,
     * "Diferencialna chyba merania mediatora".
     */
    static boolean isVeneer(String t) {
        if (!SELF_EXPLAIN.matcher(t).find()) {
            return false;
        }
        String span = claimSpan(t);
        boolean hasCode = CODE.matcher(t).find();
        boolean derivation = !hasCode
                && (TWO_NUMBERS.matcher(span).find() || NUMBER_OPERATOR.matcher(span).find());
        boolean justified = REASON.matcher(span).find()
                || REASONING_NOUN.matcher(t).find()
                || CONJECTURE.matcher(span).find()
                || DIAGNOSTIC.matcher(t).find()
                || derivation;
        int words = span.trim().isEmpty() ? 0 : span.trim().split("\\s+").length;
        return !(words >= 3 && justified);
    }

    /**
     * Fold to lower case and strip diacritics, so that "prečo" and "preco" match alike.
     */
    public static String normalise(String text) {
        if (text == null) {
            return "";
        }
        String folded = Normalizer.normalize(text.toLowerCase(), Normalizer.Form.NFKD)
                .replaceAll("\\p{M}+", "");
        return folded.replaceAll("\\s+", " ").trim();
    }

    /**
     * Classify one prompt. Rules are evaluated in the order of the coding manual and the
     * first match wins; a prompt containing several elements is therefore coded at its
     * <em>highest</em> level, because a pupil who also offered their own reasoning did
     * the cognitive work of that higher level.
     */
    public static PromptLevel classify(String prompt) {
        String t = normalise(prompt);
        if (t.isEmpty()) {
            return PromptLevel.OFF_TASK;
        }

        boolean domain = DOMAIN.matcher(t).find();
        if (OFF_TASK.matcher(t).find() && !domain) {
            return PromptLevel.OFF_TASK;
        }
        if (ANSWER_ONLY.matcher(t).find()) {
            return PromptLevel.L0;
        }
        if (SELF_EXPLAIN.matcher(t).find() && !isVeneer(t)) {
            return PromptLevel.L4;
        }
        if (OWN_WORK.matcher(t).find() && FAILURE.matcher(t).find()) {
            return PromptLevel.L1;
        }
        if (ELABORATE.matcher(t).find()) {
            return PromptLevel.L3;
        }
        if (EXPLAIN.matcher(t).find()) {
            return PromptLevel.L2;
        }
        boolean wantsArtefact = SOLVE_VERB.matcher(t).find() && ARTEFACT.matcher(t).find();
        if (VERIFY.matcher(t).find() || FAILURE.matcher(t).find()
                || (CODE.matcher(t).find() && !wantsArtefact)) {
            return PromptLevel.L1;
        }
        if (DEMAND_VERB.matcher(t).find() && ARTEFACT.matcher(t).find()) {
            return PromptLevel.L0;
        }
        if (SOLVE_VERB.matcher(t).find()) {
            return PromptLevel.L0;
        }
        // Not recognisably anything else. The manual sends this to L1 rather than L0:
        // an unclassifiable prompt is more often a clumsy verification than a demand
        // for a finished solution, and guessing low would inflate the offloading rate.
        return PromptLevel.L1;
    }

    /**
     * Which named patterns fired, for auditing a single coding decision. The index must
     * be inspectable case by case or a school cannot defend it.
     */
    public static List<String> explain(String prompt) {
        String t = normalise(prompt);
        return List.of(
                "off_task=" + OFF_TASK.matcher(t).find(),
                "domain=" + DOMAIN.matcher(t).find(),
                "answer_only=" + ANSWER_ONLY.matcher(t).find(),
                "self_explain=" + SELF_EXPLAIN.matcher(t).find(),
                "veneer=" + isVeneer(t),
                "claim_span=" + claimSpan(t).trim(),
                "elaborate=" + ELABORATE.matcher(t).find(),
                "explain=" + EXPLAIN.matcher(t).find(),
                "verify=" + VERIFY.matcher(t).find(),
                "solve_verb=" + SOLVE_VERB.matcher(t).find(),
                "demand_verb=" + DEMAND_VERB.matcher(t).find(),
                "artefact=" + ARTEFACT.matcher(t).find(),
                "code=" + CODE.matcher(t).find());
    }
}
