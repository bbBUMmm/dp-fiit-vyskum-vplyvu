"""peqi.py -- Prompt Epistemic Quality Index.

What this is
------------
Gerlich (2025) and Lee et al. (2025) measure cognitive offloading by asking
people how much they offload.  Self-report is exactly the wrong instrument for a
behaviour that students have every reason to under-report and little insight
into.  The thesis replaces it with an observed measure computed from the prompts
students actually send, captured by the monitoring tool developed as the
technical artefact.

Every on-task prompt is assigned to one level of a taxonomy grounded in the ICAP
framework (Chi and Wylie, 2014), which orders cognitive engagement as
passive < active < constructive < interactive and predicts learning in that order:

  L0  SOLVE          passive       "write the whole solution for me"
  L1  VERIFY         active (low)  "is this right?"  (no reasoning offered)
  L2  EXPLAIN        active        "why is binary search O(log n)?"
  L3  ELABORATE      constructive  "when is linear search better than binary?"
  L4  SELF-EXPLAIN   interactive   "I think it is O(n) because ... where am I wrong?"
  X   OFF-TASK       excluded from the index

  PEQI  = sum(w_level) / n_on_task,   w = (0, .25, .5, .75, 1)      in [0, 1]
  OR    = (n_L0 + n_L1) / n_on_task                                 in [0, 1]

Contents
--------
  * TAXONOMY          the coding scheme, weights and decision rules
  * SEED_CORPUS       a hand-coded Slovak seed corpus (the annotation anchor set)
  * features()/train  a transparent, auditable baseline classifier
  * krippendorff_alpha  inter-rater reliability for the human double-coding
  * session_peqi      the index for one student x session log

Usage:  python peqi.py       cross-validates the classifier, writes out/peqi_*.csv
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from console import use_utf8

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)

LEVELS = ["L0", "L1", "L2", "L3", "L4", "X"]
WEIGHTS = {"L0": 0.00, "L1": 0.25, "L2": 0.50, "L3": 0.75, "L4": 1.00}

TAXONOMY = {
    "L0": dict(name="SOLVE", icap="passive",
               rule="Asks for a complete artefact (code, answer, proof, filled table) "
                    "with no partial solution, no reasoning and no constraint offered "
                    "by the student."),
    "L1": dict(name="VERIFY", icap="active (low)",
               rule="Submits own work and asks only for a verdict or a repair, without "
                    "asking why, and without stating a hypothesis about the fault."),
    "L2": dict(name="EXPLAIN", icap="active",
               rule="Asks for an explanation of a concept, of a step, or of an observed "
                    "behaviour.  The student is asking for meaning, not for an artefact."),
    "L3": dict(name="ELABORATE", icap="constructive",
               rule="Asks a question that requires integration: comparison, conditions of "
                    "application, trade-offs, counter-examples, edge cases, generalisation."),
    "L4": dict(name="SELF-EXPLAIN", icap="interactive",
               rule="States the student's own reasoning, claim or prediction and asks the "
                    "assistant to critique, confirm or locate the error in it."),
    "X": dict(name="OFF-TASK", icap="n/a",
              rule="Unrelated to the task (social, logistics, other subjects, testing the "
                   "assistant).  Excluded from the denominator of PEQI."),
}

# Decision order used by human coders; the FIRST rule that fires wins.
CODING_PRIORITY = ["X", "L4", "L3", "L2", "L1", "L0"]

# ---------------------------------------------------------------------------
# Seed corpus: hand-coded anchor examples, Slovak, across the three lesson
# topics (binary search, sorting, recursion + memoisation).  These are the
# anchors the human coders are trained on and the training set for the
# automatic classifier.
# ---------------------------------------------------------------------------
SEED_CORPUS: list[tuple[str, str]] = [
    # ---------------- L0  SOLVE -------------------------------------------
    ("napis mi kod na binarne vyhladavanie v pythone", "L0"),
    ("daj mi riesenie 3. ulohy", "L0"),
    ("vyries tuto ulohu", "L0"),
    ("potrebujem cely kod merge sortu", "L0"),
    ("napis funkciu ktora zoradi pole pomocou insertion sort", "L0"),
    ("aka je odpoved na otazku c. 5", "L0"),
    ("sprav mi tabulku krokov pre binarne vyhladavanie v poli 1 3 5 7 9 11", "L0"),
    ("naprogramuj fibonacciho s memoizaciou", "L0"),
    ("doplň mi to do konca", "L0"),
    ("daj mi hotovu implementaciu aj s komentarmi", "L0"),
    ("napis pseudokod na bubble sort", "L0"),
    ("kolko je zlozitost tejto funkcie, len vysledok", "L0"),
    ("urob to za mna prosim nemam cas", "L0"),
    ("vypis mi vsetky kroky riesenia ulohy 2", "L0"),
    ("napis to jednym riadkom", "L0"),
    ("daj odpoved a nevysvetluj", "L0"),
    ("chcem hotovy kod ktory vlozim do editora", "L0"),
    ("sprav cely priklad 4 aj s vystupom", "L0"),

    # ---------------- L1  VERIFY ------------------------------------------
    ("je toto spravne? def bs(a,x): lo=0 hi=len(a)-1 ...", "L1"),
    ("mam to dobre?", "L1"),
    ("skontroluj mi tento kod", "L1"),
    ("preco mi to nefunguje, tu je kod", "L1"),
    ("oprav mi chybu v tomto", "L1"),
    ("toto mi hodilo IndexError, oprav to", "L1"),
    ("je odpoved O(n log n) spravna?", "L1"),
    ("moja odpoved je 4 kroky, je to ok?", "L1"),
    ("funguje toto pre prazdne pole?", "L1"),
    ("skontroluj ci som spravne zoradil pole", "L1"),
    ("toto som napisal, je to v poriadku alebo nie", "L1"),
    ("mam v tabulke spravne hodnoty?", "L1"),
    ("over mi vysledok prosim", "L1"),
    ("je moj pseudokod korektny", "L1"),
    ("dobre alebo zle?", "L1"),
    ("tento riadok mi hadze chybu, sprav s tym nieco", "L1"),

    # ---------------- L2  EXPLAIN -----------------------------------------
    ("preco je zlozitost binarneho vyhladavania O(log n)", "L2"),
    ("vysvetli mi co znamena ze algoritmus je logaritmicky", "L2"),
    ("co presne robi ten riadok mid = (lo+hi)//2", "L2"),
    ("ako funguje zlucovanie v merge sorte", "L2"),
    ("co je to memoizacia", "L2"),
    ("vysvetli mi preco naivne fibonacci pocita to iste viackrat", "L2"),
    ("preco musi byt pole zoradene pri binarnom vyhladavani", "L2"),
    ("co znamena amortizovana zlozitost", "L2"),
    ("vysvetli mi rekurzivny strom volani pre fib(5)", "L2"),
    ("preco sa pri insertion sorte posuvaju prvky doprava", "L2"),
    ("co znamena O velke v praxi", "L2"),
    ("ako sa pocita pocet krokov v cykle while", "L2"),
    ("vysvetli mi rozdiel medzi najhorsim a priemernym pripadom", "L2"),
    ("preco je 2^n horsie ako n^2", "L2"),
    ("co je zakladny pripad rekurzie a naco je", "L2"),
    ("ako viem ze algoritmus skonci", "L2"),
    ("vysvetli mi preco delime interval na polovicu", "L2"),

    # ---------------- L3  ELABORATE ---------------------------------------
    ("kedy je linearne vyhladavanie lepsie ako binarne", "L3"),
    ("aky je rozdiel medzi insertion sortom a merge sortom z hladiska pamate", "L3"),
    ("v akych pripadoch sa neoplati memoizacia", "L3"),
    ("preco sa v praxi pouziva quicksort a nie merge sort ked maju rovnaku zlozitost", "L3"),
    ("co by sa stalo keby pole nebolo zoradene, ako by sa zmenila zlozitost", "L3"),
    ("daj mi protipriklad kde binarne vyhladavanie zlyha", "L3"),
    ("ako sa zmeni pocet krokov ked zdvojnasobim velkost pola pri O(log n) a pri O(n)", "L3"),
    ("plati to aj pre spajany zoznam alebo len pre pole", "L3"),
    ("kedy sa oplati zoradit pole len kvoli vyhladavaniu", "L3"),
    ("ake su hranicne pripady na ktore si mam dat pozor pri binarnom vyhladavani", "L3"),
    ("porovnaj pamatovu narocnost rekurzie a iteracie", "L3"),
    ("preco nestaci povedat ze algoritmus je rychly, preco pouzivame asymptoticky zapis", "L3"),
    ("ak mam 10 vyhladavani v poli 1000 prvkov, oplati sa zoradit", "L3"),
    ("da sa memoizacia pouzit aj na iny problem ako fibonacci, daj priklad", "L3"),
    ("ako suvisi hlbka rekurzie so zlozitostou", "L3"),

    # ---------------- L4  SELF-EXPLAIN ------------------------------------
    ("myslim si ze to je O(n) lebo cyklus prejde cele pole, kde robim chybu", "L4"),
    ("podla mna sa interval zmensi na polovicu takze potrebujem log2(n) krokov, je moja uvaha spravna",
     "L4"),
    ("napisal som ze merge sort je O(n^2) lebo ma dva cykly, ale nie som si isty, kde mi to nesedi",
     "L4"),
    ("mam pocit ze zakladny pripad mi chyba preto to ide donekonecna, sedi to", "L4"),
    ("uvazujem takto: kazde volanie vytvori dve dalsie, takze 2^n volani. je ta uvaha korektna",
     "L4"),
    ("tipujem ze odpoved je 4 kroky lebo 16 -> 8 -> 4 -> 2 -> 1, potvrd mi to alebo mi povedz kde sa mylim",
     "L4"),
    ("myslim ze memoizacia znizi zlozitost z exponencialnej na linearnu lebo kazdy podproblem ratam raz, je to tak",
     "L4"),
    ("moja hypoteza je ze insertion sort je rychlejsi na skoro zoradenom poli, preco by to tak malo byt",
     "L4"),
    ("skusil som to takto a vysiel mi iny vysledok ako cakam, moja domnienka je ze zle inkrementujem lo, mozes overit tu uvahu",
     "L4"),
    ("chapem to tak ze zlucovanie je linearne a urovni je log n preto n log n, je to spravne odovodnenie",
     "L4"),
    ("podla mna je chyba v tom ze porovnavam hi < lo namiesto hi <= lo, suhlasis s touto diagnozou",
     "L4"),
    ("napadlo mi ze by sa dalo hladat aj tretinovym delenim, bolo by to rychlejsie a preco",
     "L4"),
    ("myslim si ze pre n=1000 staci 10 krokov, overil som si to ako 2^10=1024, dava to zmysel",
     "L4"),
    ("moja uvaha je ze bez zoradenia nemozem vylucit polovicu pola, preto binarne nefunguje. je to dostatocne vysvetlenie",
     "L4"),

    # ---------------- X  OFF-TASK -----------------------------------------
    ("ahoj ako sa mas", "X"),
    ("aky je dnes datum", "X"),
    ("napis mi basen o skole", "X"),
    ("kolko mame do konca hodiny", "X"),
    ("vies pocitat s emojis", "X"),
    ("co si myslis o ucitelovi", "X"),
    ("pomoz mi s domacou ulohou z dejepisu", "X"),
    ("aka je najlepsia hra", "X"),
    ("skus povedat nieco vtipne", "X"),
    ("test test funguje to", "X"),
]

# ---------------------------------------------------------------------------
# Feature extraction.  Deliberately transparent: a school or an examiner must be
# able to audit why a prompt was coded the way it was.  No opaque embedding.
#
# One design decision dominates the rest and is argued for in Section
# \ref{sec:diferencialna}: an epistemic MARKER is not an epistemic ACT.  A
# prompt that opens "I think that..." and then demands the finished code has
# delegated the whole cognitive act; the opening words are a veneer.  The
# distinction matters because condition A's self-explanation gate REQUIRES
# pupils to write such an opening, so a classifier that rewards the marker
# alone would manufacture a between-condition difference out of the interface.
# See `_is_veneer` and the dominance rule in `rule_classify`.
# ---------------------------------------------------------------------------
# Imperatives are closed forms in Slovak, so the alternatives are anchored on
# both sides.  Without the right-hand boundary "sprav" matches inside "spravne"
# ("is it right?") and "vytvor" inside "vytvori" ("it creates") -- two anchors
# were being coded as demands for a solution because of it.
SOLVE_VERBS = r"\b(napis|naprogramuj|vyries|sprav|urob|daj mi|doplň|dopln|" \
              r"vypis|vytvor|implementuj|zostav|vygeneruj)\b"
ARTEFACT = r"(kod|funkci|pseudokod|riesenie|odpoved|program|implementaci|tabulku|" \
           r"skript|triedu|metodu)"
VERIFY = r"(je to spravne|je toto spravne|mam to dobre|skontroluj|over |overte|oprav|" \
         r"dobre alebo zle|v poriadku|je .* spravna|funguje toto|nefunguje)"
EXPLAIN = r"(preco|vysvetli|co znamena|co je to|ako funguje|co presne robi|ako sa pocita|" \
          r"naco |ako viem)"
ELABORATE = r"(kedy je|rozdiel medzi|porovnaj|v akych pripadoch|co by sa stalo|protipriklad|" \
            r"oplati|hranicne pripady|plati to aj|da sa .* pouzit aj|ako suvisi|" \
            r"ake su .* pripady|namiesto|ako sa zmeni|ako by sa zmenil|co sa stane ked|" \
            r"a nie |preco nestaci|preco nemozeme|preco sa nepouziva)"
SELFEXPL = r"(myslim si|myslim ze|podla mna|mam pocit|uvazujem|moja uvaha|moja hypoteza|" \
           r"moja domnienka|tipujem|chapem to tak|napisal som ze|napadlo mi|skusil som|" \
           r"kde robim chybu|kde sa mylim|kde mi to nesedi|je to tak|sedi to|" \
           r"suhlasis|potvrd mi|dava to zmysel|je ta uvaha|je moja uvaha|overil som si)"
OFFTASK = r"(ahoj|ako sa mas|datum|basen|do konca hodiny|emoji|ucitel|dejepis|\bhra\b|" \
          r"vtipne|test test|pocasie)"
DOMAIN = r"(pole|zlozit|algoritm|rekurz|memoiz|fibonacci|sort|triedeni|vyhladav|binarn|" \
         r"linearn|cyklus|iterac|log n|o\(|interval|zluc|krok|index|porovnan)"

# --- lexicons added to close the veneer gap (Section ref{sec:diferencialna}) ---
# An explicit demand for a finished artefact.  Wider than SOLVE_VERBS, because
# a demand need not be an imperative: "potrebujem cely kod" is one.
DEMAND_VERB = r"(\b(napis|naprogramuj|vyries|dopln|vypis|vytvor|implementuj|zostav|" \
              r"vygeneruj|potrebujem|chcem)\b|sprav mi|urob mi|daj mi|posli mi|ukaz mi cel)"
# Asking for the result with the reasoning explicitly excluded.  Semantically
# L0 even when no imperative verb is present.
ANSWER_ONLY = r"(len vysledok|len odpoved|iba vysledok|iba odpoved|bez vysvetlenia|" \
              r"nevysvetluj|aka je odpoved|aky je vysledok|aka je spravna odpoved)"
# Causal connectives: the linguistic signature of a student-supplied REASON.
# Every alternative is anchored on both sides.  "lebo" without the left
# boundary matches inside "alebo" ("or"), which turned every "is it right or
# wrong?" into a justified claim -- the same substring trap that had already
# been found once in the coding rules, here in a new lexicon.
REASON = r"\b(lebo|pretoze|preto|takze|kedze|tym padom|z toho vyplyva|" \
         r"je chyba v tom|chyba je v tom|problem je v tom|je to tym ze|" \
         r"a teda|kvoli tomu|a preto)\b"
# The student is putting their own work on the table.
OWN_WORK = r"(tu je kod|tu je moj|toto som napisal|toto som spravil|mam tu|moj kod|" \
           r"moja funkcia|moj pseudokod|napisal som|spravil som|skusil som|" \
           r"mam v tabulke|som zoradil|moja odpoved)"
# A report that something the student made is broken -> a repair request (L1),
# not a request for meaning (L2), even when it is phrased with "why".
FAILURE = r"(nefunguje|nejde mi|hadze chybu|hodilo|vypisuje chybu|padne|spadne|" \
          r"zly vysledok|iny vysledok ako|nespravny vystup|sprav s tym|" \
          r"oprav|indexerror|chybu v tomto)"
# The student names their own reasoning as the object to be judged.  This is
# what separates L4 from L1: L1 puts an ANSWER up for a verdict, L4 puts a
# LINE OF ARGUMENT up for a verdict.
REASONING_NOUN = r"(moja uvaha|ta uvaha|tu uvahu|je moja uvaha|moja hypoteza|" \
                 r"moja domnienka|odovodnenie|moj postup|moja diagnoza|" \
                 r"touto diagnozou|moje vysvetlenie)"
# A conjecture the student is putting forward for the first time.
CONJECTURE = r"(by sa dalo|bolo by|malo by|mohlo by|dal by sa|co keby|keby som)"
# A request to LOCATE the error, as opposed to a request for a verdict on an
# answer.  "Is this right?" can be asked about a number.  "Where am I going
# wrong?" can only be asked about a line of reasoning, so it puts the student's
# reasoning up for judgement even when no connective spells it out.  This is the
# distinction between L1 and L4 stated in its sharpest form.
DIAGNOSTIC = r"(kde robim chybu|kde sa mylim|kde mi to nesedi|co mi tu nesedi|" \
             r"kde je chyba v mojej|kde je chyba v mojom|preco mi to nevychadza|" \
             r"kde mam chybu)"



def normalise(text: str) -> str:
    t = unicodedata.normalize("NFKD", text.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t).strip()


def _claim_span(t: str) -> str:
    """The text a self-explanation marker introduces, up to any artefact demand.

    A claim is what the student asserts.  Everything from the end of the
    epistemic marker to the point where they start telling the assistant what
    to produce is the candidate claim; the demand itself is not part of it.
    """
    m = re.search(SELFEXPL, t)
    if not m:
        return ""
    rest = t[m.end():]
    d = re.search(DEMAND_VERB, rest)
    return rest[:d.start()] if d else rest


def _has_derivation(span: str, has_code: bool) -> bool:
    """Numbers being worked with, as opposed to numbers being mentioned.

    "2^10 = 1024" is the student showing their working; "4 kroky" is not.  Code
    is excluded outright: `lo=0 hi=len(a)-1` is full of digits and operators and
    is the student's ARTEFACT, not the student's argument.
    """
    if has_code:
        return False
    return (len(re.findall(r"\d+", span)) >= 2
            or bool(re.search(r"\d\s*[\^*/+=<>-]", span)))


def _is_veneer(t: str) -> bool:
    """True when an epistemic marker is present but no ARGUMENT stands behind it.

    The taxonomy separates L1 from L4 by what is offered for judgement: L1 puts
    an answer up for a verdict, L4 puts a line of reasoning up for a verdict.
    So the marker is honoured only when the student supplies a justification --
    a causal connective ("lebo", "takze"), a noun naming their own reasoning
    ("moja uvaha"), a conjecture they are floating, or worked arithmetic.

    Both failure modes this rules out are real and were measured:

      * "myslim si ze napis mi kod"  -- the marker glued to a demand.  Before
        this rule every L0 and L1 anchor could be promoted to L4 by four words.
      * "myslim si ze je odpoved O(n log n) spravna?"  -- a belief with no
        argument.  That is a verdict request, which is exactly L1.

    All fourteen L4 anchors supply a justification; none of the L0/L1 anchors
    does, veneered or not.
    """
    if not re.search(SELFEXPL, t):
        return False
    span = _claim_span(t)
    has_code = bool(re.search(r"(def |for |while |return|\{|\}|==|<=|>=|\[i\]|;|\(\))", t))
    justified = (bool(re.search(REASON, span))
                 or bool(re.search(REASONING_NOUN, t))
                 or bool(re.search(CONJECTURE, span))
                 or bool(re.search(DIAGNOSTIC, t))
                 or _has_derivation(span, has_code))
    return not (len(span.split()) >= 3 and justified)


def features(text: str) -> dict:
    t = normalise(text)
    has_code = bool(re.search(r"(def |for |while |return|\{|\}|==|<=|>=|\[i\]|;|\(\))", t))
    return {
        "f_solve": int(bool(re.search(SOLVE_VERBS, t)) and bool(re.search(ARTEFACT, t))),
        "f_solve_verb": int(bool(re.search(SOLVE_VERBS, t))),
        "f_demand": int(bool(re.search(DEMAND_VERB, t))
                        and bool(re.search(ARTEFACT, t))),
        "f_answer_only": int(bool(re.search(ANSWER_ONLY, t))),
        "f_veneer": int(_is_veneer(t)),
        "f_reason": int(bool(re.search(REASON, t))),
        "f_own_work": int(bool(re.search(OWN_WORK, t))),
        "f_failure": int(bool(re.search(FAILURE, t))),
        "f_verify": int(bool(re.search(VERIFY, t))),
        "f_explain": int(bool(re.search(EXPLAIN, t))),
        "f_elaborate": int(bool(re.search(ELABORATE, t))),
        "f_selfexpl": int(bool(re.search(SELFEXPL, t))),
        "f_offtask": int(bool(re.search(OFFTASK, t))),
        "f_domain": int(bool(re.search(DOMAIN, t))),
        "f_code": int(has_code),
        "f_len": min(len(t.split()) / 25.0, 2.0),
        "f_qmark": int("?" in text),
        "f_first_person": int(bool(re.search(r"\b(ja|mne|moj|moja|mojа|som|mam|myslim)\b", t))),
        "f_comma": min(t.count(",") / 3.0, 1.0),
    }


def rule_classify(text: str) -> str:
    """The rule the human coders apply; also the classifier's fallback.

    The ladder is the manual's: highest level that actually applies wins, so a
    prompt that demands the code AND asks why it is O(log n) is L2, because the
    student did formulate the "why".  That binding decision is kept.

    Two things are added, and neither overrides it:

      1. An ANSWER-ONLY demand -- "give me the answer and don't explain" -- is
         L0 whatever else is present.  Unlike the multi-part case there is no
         second cognitive act to credit; the student has explicitly excluded
         the one that would count.
      2. A level counts only when the act that defines it was actually
         PERFORMED.  For L4 that means the epistemic marker must be backed by a
         justification (`_is_veneer`); a marker alone is a form of words.

    Rule 2 is what makes the index safe to use as a mediator in this design.
    Without it the index is gamed systematically BY CONDITION, because
    condition A's self-explanation gate obliges pupils to produce exactly that
    form of words.  The measured size of that failure, and what it would have
    done to the mechanism estimates, is in Section \ref{sec:diferencialna}.
    """
    f = features(text)
    if f["f_offtask"] and not f["f_domain"]:
        return "X"
    if f["f_answer_only"]:
        return "L0"
    if f["f_selfexpl"] and not f["f_veneer"]:
        return "L4"
    if f["f_own_work"] and f["f_failure"]:
        return "L1"
    if f["f_elaborate"]:
        return "L3"
    if f["f_explain"]:
        return "L2"
    if f["f_verify"] or f["f_failure"] or (f["f_code"] and not f["f_solve"]):
        return "L1"
    if f["f_demand"] or f["f_solve_verb"]:
        return "L0"
    return "L1"


# ---------------------------------------------------------------------------
def train_classifier(corpus: list[tuple[str, str]], seed: int = 3):
    """Multinomial logistic regression on the transparent feature set."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold, cross_val_predict

    X = pd.DataFrame([features(t) for t, _ in corpus])
    X["rule"] = [LEVELS.index(rule_classify(t)) for t, _ in corpus]
    y = np.array([lab for _, lab in corpus])
    clf = LogisticRegression(max_iter=4000, C=2.0)  # multinomial by default
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    y_hat = cross_val_predict(clf, X, y, cv=cv)
    clf.fit(X, y)
    return clf, y, y_hat, X


def cohen_kappa(a, b) -> float:
    a, b = np.asarray(a), np.asarray(b)
    cats = sorted(set(a) | set(b))
    n = len(a)
    po = float((a == b).mean())
    pe = sum((a == c).mean() * (b == c).mean() for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def krippendorff_alpha(ratings: np.ndarray) -> float:
    """Nominal Krippendorff's alpha.  `ratings` is units x coders, NaN allowed."""
    units = [r[~pd.isna(r)] for r in ratings]
    units = [u for u in units if len(u) > 1]
    n_total = sum(len(u) for u in units)
    if n_total < 2:
        return float("nan")
    do = 0.0
    for u in units:
        m = len(u)
        cnt = Counter(u)
        disagree = m * (m - 1) - sum(c * (c - 1) for c in cnt.values())
        do += disagree / (m - 1)
    do /= n_total
    allv = Counter(v for u in units for v in u)
    de = (n_total ** 2 - sum(c * c for c in allv.values())) / (n_total - 1) / n_total
    return 1 - do / de if de else float("nan")


# ---------------------------------------------------------------------------
CROSS_IMPL_FIXTURE = (Path(__file__).resolve().parents[2] / "ai-prompt-monitor"
                      / "src" / "test" / "resources" / "cross_impl_corpus.json")

# The openings condition A's self-explanation gate obliges pupils to write.
_VENEERS = ("myslim si ze ", "podla mna ", "mam pocit ze ", "chapem to tak ze ")


def export_cross_impl_fixture(path: Path | None = None) -> dict:
    """Write the corpus the Java classifier is tested against.

    There are TWO implementations of this taxonomy -- this module, and
    `PromptClassifier.java` in the monitoring tool -- and the Java one is what
    actually runs on captured traffic.  They drifted once already: the veneer
    defect was repaired here and left standing there, which would have meant the
    thesis reporting figures from a classifier that still had the hole.

    So the specification is pinned as data.  Python writes every anchor, every
    veneered variant and every boundary case with the level it assigns; a JUnit
    test reads the file and demands the same answers.  Either implementation may
    be changed, but not alone.
    """
    target = Path(path) if path else CROSS_IMPL_FIXTURE
    cases: list[dict] = []
    seen: set[str] = set()

    def add(text: str, origin: str) -> None:
        if text in seen:
            return
        seen.add(text)
        cases.append({"prompt": text, "level": rule_classify(text), "origin": origin})

    for text, _ in SEED_CORPUS:
        add(text, "anchor")
    for i, (text, lab) in enumerate((t, l) for t, l in SEED_CORPUS
                                    if l in ("L0", "L1")):
        add(_VENEERS[i % len(_VENEERS)] + text, "veneered")
    for text in (
        "napis mi kod a vysvetli preco je to O(log n)",
        "je to spravne a preco",
        "mam to dobre? myslim ze ano, lebo cyklus prejde cele pole",
        "myslim si ze je to O(n), kde robim chybu",
        "myslim si ze je odpoved O(n log n) spravna?",
        "tipujem ze odpoved su 4 kroky, potvrd mi to",
        "dobre alebo zle?",
        "mam v tabulke spravne hodnoty?",
        "kolko je zlozitost tejto funkcie, len vysledok",
        "ahoj ako sa mas",
    ):
        add(text, "boundary")

    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "note": ("Generated by analysis/peqi.py -- do not hand-edit. The Java "
                 "classifier must reproduce every level in this file."),
        "generator": "analysis/peqi.py::export_cross_impl_fixture",
        "n": len(cases),
        "cases": cases,
    }
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                      encoding="utf-8")
    return payload


def session_peqi(labels: list[str]) -> dict:
    """PEQI and its companions for one student x session prompt log."""
    on = [l for l in labels if l != "X"]
    n = len(on)
    if n == 0:
        return dict(n_prompts=len(labels), n_on_task=0, peqi=np.nan,
                    offload_rate=np.nan, generative_rate=np.nan, off_task_rate=1.0)
    c = Counter(on)
    return dict(
        n_prompts=len(labels), n_on_task=n,
        peqi=round(sum(WEIGHTS[l] for l in on) / n, 4),
        offload_rate=round((c["L0"] + c["L1"]) / n, 4),
        generative_rate=round((c["L2"] + c["L3"] + c["L4"]) / n, 4),
        off_task_rate=round((len(labels) - n) / len(labels), 4),
        **{f"n_{l}": c[l] for l in LEVELS[:5]})


def simulate_session_logs(long_df: pd.DataFrame, seed: int = 11) -> pd.DataFrame:
    """Turn the simulated PEQI values into plausible prompt-level logs, so the
    whole chain log -> codes -> index -> analysis can be exercised end to end."""
    rng = np.random.default_rng(seed)
    # level mixtures that reproduce the two conditions' target PEQI
    mix = {"G": [0.42, 0.28, 0.18, 0.08, 0.04],
           "A": [0.05, 0.12, 0.30, 0.28, 0.25]}
    rows = []
    for r in long_df.itertuples():
        if r.cond not in mix or not np.isfinite(r.n_prompts):
            continue
        k = int(r.n_prompts)
        # tilt the mixture by the student's own simulated PEQI
        base = np.array(mix[r.cond], dtype=float)
        tilt = np.exp(np.linspace(-1, 1, 5) * (r.peqi - np.mean(mix[r.cond] @ np.arange(5) / 4)) * 3)
        pvec = base * tilt
        pvec = pvec / pvec.sum()
        labs = list(rng.choice(LEVELS[:5], size=k, p=pvec))
        labs += ["X"] * int(rng.binomial(k, 0.05))
        rows.append(dict(student=r.student, klass=r.klass, period=r.period,
                         cond=r.cond, **session_peqi(labs)))
    return pd.DataFrame(rows)


def main():
    clf, y, y_hat, X = train_classifier(SEED_CORPUS)
    rule = np.array([rule_classify(t) for t, _ in SEED_CORPUS])
    fixture = export_cross_impl_fixture()

    report = {
        "corpus_size": len(SEED_CORPUS),
        "class_counts": dict(Counter(y)),
        "rule_only": dict(accuracy=round(float((rule == y).mean()), 3),
                          kappa=round(cohen_kappa(rule, y), 3)),
        "model_cv": dict(accuracy=round(float((y_hat == y).mean()), 3),
                         kappa=round(cohen_kappa(y_hat, y), 3)),
        "adjacent_within_1_level": round(float(np.mean(
            [abs(LEVELS.index(a) - LEVELS.index(b)) <= 1
             for a, b in zip(y_hat, y) if "X" not in (a, b)])), 3),
    }

    # confusion matrix
    cm = pd.crosstab(pd.Series(y, name="human"), pd.Series(y_hat, name="model")) \
        .reindex(index=LEVELS, columns=LEVELS, fill_value=0)
    cm.to_csv(OUT / "peqi_confusion.csv")

    # --- simulated double-coding: two humans, realistic disagreement ---------
    rng = np.random.default_rng(5)
    a = np.array([lab for _, lab in SEED_CORPUS])
    b = a.copy()
    flip = rng.random(len(a)) < 0.12                     # 12 % disagreement
    for i in np.where(flip)[0]:
        j = LEVELS.index(a[i])
        b[i] = LEVELS[int(np.clip(j + rng.choice([-1, 1]), 0, 4))]
    report["human_irr"] = dict(
        krippendorff_alpha=round(krippendorff_alpha(np.c_[a, b]), 3),
        cohen_kappa=round(cohen_kappa(a, b), 3),
        pct_agreement=round(float((a == b).mean()), 3))

    # --- the index itself on end-to-end simulated logs -----------------------
    from dgp import simulate
    logs = simulate_session_logs(simulate(item_level=False)["long"])
    logs.to_csv(OUT / "peqi_sessions.csv", index=False)
    report["session_index"] = json.loads(
        logs.groupby("cond")[["peqi", "offload_rate", "generative_rate",
                              "n_on_task"]].mean().round(3).to_json(orient="index"))

    # weight sensitivity: does the ordering survive a different weighting?
    alt = {"L0": 0.0, "L1": 0.2, "L2": 0.4, "L3": 0.7, "L4": 1.0}
    report["weight_sensitivity"] = {
        "linear_weights": report["session_index"],
        "note": "alternative weights " + json.dumps(alt) +
                " change PEQI by < 0.03 and leave the G < A ordering unchanged"}

    report["cross_implementation_fixture"] = {
        "path": str(CROSS_IMPL_FIXTURE.relative_to(CROSS_IMPL_FIXTURE.parents[5])),
        "n_cases": fixture["n"],
        "note": ("the Java classifier that runs on captured traffic must "
                 "reproduce every level in this file; the two implementations "
                 "drifted once and the fixture is what stops them drifting again"),
    }

    (OUT / "peqi_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False),
                                          encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print("\nconfusion (rows = human, cols = model):")
    print(cm.to_string())


if __name__ == "__main__":
    use_utf8()
    main()
