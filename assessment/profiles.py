"""profiles.py -- naming one pupil's way of using the tool, from one pupil's data.

Why the thesis's existing answer is not enough
----------------------------------------------
The assignment asks the tool to CATEGORISE USERS. The thesis answers with latent
profile analysis over six indicators, and the answer is a good one: the profiles
are pre-named, the covariance structure was chosen against planted truth and
planted absence of structure, and the typology is honestly reported as
exploratory because at 330 pupils it recovers planted truth only moderately
(ARI about 0.5), needing roughly 900 to be confirmatory.

But look at what that means for the person who would actually use this tool.
Latent profile analysis is a statement about a SAMPLE. It needs hundreds of
pupils, it fits a mixture to whatever spread the sample happens to have, and a
pupil's label depends on who else is in the file. A teacher with one class of
twenty-two cannot run it at all, and if two schools each ran it they would get
two different, incomparable typologies.

So the thesis delivers a categorisation that only the study can use. For the
assignment's own purpose -- a tool a school can deploy -- that is the wrong
object.

What this module is instead
---------------------------
A DETERMINISTIC, PRE-REGISTERED RULE over ABSOLUTE cut points. Four consequences,
each of which the mixture model cannot have:

  * it works at n = 1. One pupil, one lesson, one label;
  * the label does not depend on the rest of the class, so two schools in
    different years get comparable labels;
  * every cut point is written down before any data exist, so there is no
    freedom left to tune the typology until it says something interesting;
  * a teacher can be told WHY a pupil was labelled, in one sentence, which a
    posterior probability from a six-dimensional Gaussian mixture cannot do.

The cost, stated plainly: a rule cannot discover a profile nobody anticipated,
and a mixture can. They are not competitors. The mixture stays in the thesis as
the exploratory question "is this population a mixture, and of what?"; the rule
is what the tool ships. `assessment_validation.py` measures how far apart their
answers are, and the rule is only defensible if that distance is small.

Where the cut points come from
------------------------------
Not from the data, and not from convention. Each is a point on a scale that
already has a meaning:

  PEQI   the index is the mean of per-prompt levels weighted L0=0, L1=0.25,
         L2=0.50, L3=0.75, L4=1.00. So 0.25 is a pupil whose average prompt is
         a bare verification request and 0.50 one who on average asks for an
         explanation. The two cuts are placed exactly there, because that is
         where the construct changes, not where the sample splits.
  ABHR   the share of tasks attempted before the first prompt. 0.50 is "as often
         as not" -- the only non-arbitrary point on a proportion.
  BIAS   confidence minus accuracy. 0.15 is the smallest overestimate that
         exceeds the measurement error of a twelve-item test (SE of a proportion
         at p = 0.6, n = 12, is about 0.14).
  RELY   the reliance scale is 1-7; 4.0 is its own midpoint.
  CRIT   proportion correct on the twelve critical-thinking items; 0.50 is the
         blueprint's own target difficulty band midpoint.

Run:  python profiles.py        self-test, including the refusal cases
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field

# --- the pre-registered cut points, on their own scales --------------------
PEQI_LOW = 0.25          # average prompt is a bare verification request
PEQI_HIGH = 0.50         # average prompt asks for an explanation
ABHR_MID = 0.50          # tried first as often as not
BIAS_OVER = 0.15         # overconfidence beyond the test's own measurement error
RELY_MID = 4.0           # midpoint of the 1-7 reliance scale
CRIT_MID = 0.50          # midpoint of the critical-thinking blueprint band

# A label needs enough evidence to be worth printing. Below this the answer is
# "undetermined", which is a real answer: a rule that always produces a label is
# a rule that guesses, and a guess printed next to a pupil's name is worse than
# a blank.
MIN_PROMPTS = 5          # fewer prompts than this and PEQI is not a measurement
MIN_TASKS = 3            # fewer tasks than this and ABHR is not a proportion
MIN_CT_ITEMS = 8         # after item exclusions

PROFILES = ("slepo doverujuci", "kriticky pouzivatel", "vyhybajuci sa",
            "priemerny", "neurceny")

SLOVAK = {
    "slepo doverujuci": "slepo dôverujúci",
    "kriticky pouzivatel": "kritický používateľ",
    "vyhybajuci sa": "vyhýbajúci sa",
    "priemerny": "priemerný",
    "neurceny": "neurčený",
}


@dataclass
class Indicators:
    """One pupil, one lesson. `None` means not measured, never zero."""
    peqi: float | None = None
    n_prompts: int = 0
    abhr: float | None = None            # attempt-before-help ratio
    n_tasks: int = 0
    calib_bias: float | None = None      # confidence - accuracy
    reliance: float | None = None        # 1-7 self-report
    critical: float | None = None        # proportion correct, CT test
    n_ct_items: int = 0
    condition: str = ""                  # K pupils have no prompts, by design


@dataclass
class Assignment:
    profile: str
    reason: str
    confidence: str                      # "jednoznačný" | "hraničný"
    missing: list[str] = field(default_factory=list)
    gates: dict = field(default_factory=dict)

    @property
    def label(self) -> str:
        return SLOVAK[self.profile]


# ===========================================================================
def classify(ind: Indicators) -> Assignment:
    """Assign one pupil to one profile, or refuse.

    The order of the rules is the order of evidential strength: observed
    behaviour first, self-report last. A pupil who says they are reflective and
    sends L0 prompts is classified on the prompts -- which is the whole reason
    this thesis measures prompts at all.
    """
    # An indicator below its minimum evidence is ABSENT, not merely noted. The
    # first version of this function listed it in `missing` and then used it
    # anyway, which misclassified the one pupil the distinction exists for: a
    # pupil who sent a single prompt had a PEQI of 0.50 computed from that one
    # prompt, cleared the "asks for explanations" gate, and was labelled a
    # critical user on the strength of one question. Nulling is the only reading
    # of a minimum that a later rule cannot ignore.
    peqi = ind.peqi if ind.n_prompts >= MIN_PROMPTS else None
    abhr = ind.abhr if ind.n_tasks >= MIN_TASKS else None
    crit = ind.critical if ind.n_ct_items >= MIN_CT_ITEMS else None

    missing = []
    if peqi is None:
        missing.append(f"PEQI (promptov {ind.n_prompts}, treba {MIN_PROMPTS})")
    if abhr is None:
        missing.append(f"ABHR (úloh {ind.n_tasks}, treba {MIN_TASKS})")
    if crit is None:
        missing.append(f"kritické myslenie (položiek {ind.n_ct_items}, "
                       f"treba {MIN_CT_ITEMS})")

    # Condition K has no assistant, so it has no prompts and no PEQI. That is not
    # missing data; it is a condition in which the construct does not exist. Such
    # a pupil cannot be given a tool-use profile, and pretending otherwise would
    # put the control group into a typology about using a tool they never had.
    if ind.condition == "K":
        return Assignment("neurceny",
                          "Podmienka K nemá asistenta, takže profil používania "
                          "nástroja preň nie je definovaný.",
                          "jednoznačný", missing=[])

    # Two of the three observed indicators must be present. One indicator can
    # name a tendency, not a profile.
    observed = sum(x is not None for x in (peqi, abhr, crit))
    if observed < 2 or (peqi is None and abhr is None):
        return Assignment("neurceny",
                          "Nedostatok pozorovaných údajov; profil sa neuvádza. "
                          "Chýba: " + "; ".join(missing),
                          "jednoznačný", missing)

    gates = {}
    if peqi is not None:
        gates["peqi_low"] = peqi < PEQI_LOW
        gates["peqi_high"] = peqi >= PEQI_HIGH
    if abhr is not None:
        gates["tries_first"] = abhr >= ABHR_MID
    if ind.calib_bias is not None:
        gates["overconfident"] = ind.calib_bias >= BIAS_OVER
    if ind.reliance is not None:
        gates["leans_on_tool"] = ind.reliance >= RELY_MID
    if crit is not None:
        gates["critical_ok"] = crit >= CRIT_MID

    # --- rule 1: the profile the whole thesis is about.
    # Offloading prompts, little own attempt, and confidence that outruns
    # accuracy. All three are about behaviour or calibration; none is self-report.
    if (gates.get("peqi_low") and not gates.get("tries_first", True)
            and gates.get("overconfident", False)):
        return Assignment(
            "slepo doverujuci",
            f"Priemerný prompt je na úrovni žiadosti o hotové riešenie "
            f"(PEQI {peqi:.2f} < {PEQI_LOW}), vlastný pokus pred prvou "
            f"otázkou urobil v {abhr:.0%} úloh, a sebadôvera prevyšuje "
            f"úspešnosť o {ind.calib_bias:+.2f}.",
            "jednoznačný", missing, gates)

    # --- rule 2: barely uses it. Checked BEFORE the critical-user rule, because
    # how often a pupil asked is decided before how well they asked -- "well"
    # averaged over three prompts is not a measurement of how well. Avoidance is
    # also not a skill, and must not be rewarded with the flattering label.
    if ind.n_prompts <= 2 and gates.get("tries_first", False):
        return Assignment(
            "vyhybajuci sa",
            f"Asistenta použil {ind.n_prompts}× a úlohy riešil sám. "
            f"Vyhýbanie sa nástroju nie je to isté ako jeho dobré používanie.",
            "jednoznačný", missing, gates)

    # --- rule 3: uses the tool, and checks it
    if (gates.get("peqi_high") and gates.get("tries_first", False)
            and gates.get("critical_ok", True)):
        return Assignment(
            "kriticky pouzivatel",
            f"Priemerný prompt žiada vysvetlenie alebo posúdenie úvahy "
            f"(PEQI {peqi:.2f} ≥ {PEQI_HIGH}) a vlastný pokus urobil "
            f"v {abhr:.0%} úloh.",
            "jednoznačný", missing, gates)

    # --- rule 4: the middle, which is most pupils and is not a defect
    borderline = (peqi is not None
                  and (abs(peqi - PEQI_LOW) < 0.05
                       or abs(peqi - PEQI_HIGH) < 0.05))
    bits = []
    if peqi is not None:
        bits.append(f"PEQI {peqi:.2f}")
    if abhr is not None:
        bits.append(f"vlastný pokus v {abhr:.0%} úloh")
    return Assignment(
        "priemerny",
        "Ukazovatele nespadajú ani do jedného krajného profilu ("
        + ", ".join(bits) + ").",
        "hraničný" if borderline else "jednoznačný", missing, gates)


# ===========================================================================
def classify_many(pupils: dict[str, Indicators]) -> dict[str, Assignment]:
    return {k: classify(v) for k, v in pupils.items()}


def distribution(assignments: dict[str, Assignment]) -> dict:
    counts = {p: 0 for p in PROFILES}
    for a in assignments.values():
        counts[a.profile] += 1
    n = max(len(assignments), 1)
    return dict(n=len(assignments),
                counts={SLOVAK[k]: v for k, v in counts.items()},
                shares={SLOVAK[k]: round(v / n, 3) for k, v in counts.items()},
                undetermined_rate=round(counts["neurceny"] / n, 3))


def stability_claim() -> dict:
    """The property that distinguishes this from a mixture model, stated as a
    testable claim rather than as an advantage in prose."""
    return dict(
        claim="A pupil's label depends only on that pupil's own indicators.",
        consequence=("Adding, removing or reordering other pupils cannot change "
                     "any label. A latent profile model has no such property: "
                     "its labels are a function of the whole sample."),
        tested_in="assessment_validation.py::test_label_is_sample_independent")


# ===========================================================================
def self_test() -> list[str]:
    fails = []

    # 1. the profile the thesis is about
    a = classify(Indicators(peqi=0.14, n_prompts=18, abhr=0.10, n_tasks=8,
                            calib_bias=0.28, reliance=6.1, critical=0.33,
                            n_ct_items=12, condition="G"))
    if a.profile != "slepo doverujuci":
        fails.append(f"blind truster misclassified as {a.profile}")
    if "PEQI" not in a.reason or "sebadôvera" not in a.reason:
        fails.append("reason does not name the evidence")

    # 2. the critical user
    a = classify(Indicators(peqi=0.71, n_prompts=14, abhr=0.88, n_tasks=8,
                            calib_bias=-0.03, reliance=4.4, critical=0.83,
                            n_ct_items=12, condition="A"))
    if a.profile != "kriticky pouzivatel":
        fails.append(f"critical user misclassified as {a.profile}")

    # 3. the avoider -- and it must not be called critical
    a = classify(Indicators(peqi=0.50, n_prompts=1, abhr=1.0, n_tasks=8,
                            calib_bias=0.02, reliance=1.6, critical=0.58,
                            n_ct_items=12, condition="G"))
    if a.profile != "vyhybajuci sa":
        fails.append(f"avoider misclassified as {a.profile}")

    # 4. it refuses when there is not enough evidence
    a = classify(Indicators(peqi=0.3, n_prompts=2, abhr=None, n_tasks=0,
                            condition="G"))
    if a.profile != "neurceny":
        fails.append("classified a pupil with two prompts and no tasks")

    # 5. condition K is undetermined by design, not by missingness
    a = classify(Indicators(condition="K", critical=0.6, n_ct_items=12,
                            calib_bias=0.1))
    if a.profile != "neurceny" or "Podmienka K" not in a.reason:
        fails.append("condition K was given a tool-use profile")

    # 6. self-report never overrides observed behaviour
    a = classify(Indicators(peqi=0.10, n_prompts=20, abhr=0.05, n_tasks=8,
                            calib_bias=0.30, reliance=1.2,     # claims no reliance
                            critical=0.9, n_ct_items=12, condition="G"))
    if a.profile != "slepo doverujuci":
        fails.append("a low self-reported reliance overrode L0 prompt behaviour")

    # 7. the defining property: the label does not depend on anyone else
    one = Indicators(peqi=0.14, n_prompts=18, abhr=0.10, n_tasks=8,
                     calib_bias=0.28, reliance=6.1, critical=0.33,
                     n_ct_items=12, condition="G")
    alone = classify_many({"P": one})["P"].profile
    with_peers = classify_many({
        "P": one,
        **{f"Q{i}": Indicators(peqi=0.9, n_prompts=30, abhr=1.0, n_tasks=8,
                               calib_bias=-0.2, reliance=2.0, critical=1.0,
                               n_ct_items=12, condition="A") for i in range(60)}
    })["P"].profile
    if alone != with_peers:
        fails.append("a pupil's label changed when other pupils were added")

    # 8. a borderline PEQI is marked borderline rather than asserted
    a = classify(Indicators(peqi=0.27, n_prompts=12, abhr=0.6, n_tasks=8,
                            calib_bias=0.05, reliance=4.0, critical=0.5,
                            n_ct_items=12, condition="G"))
    if a.confidence != "hraničný":
        fails.append("a PEQI 0.02 from a cut point was reported as clear-cut")
    return fails


def main() -> int:
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    fails = self_test()
    for f in fails:
        print("  FAIL " + f)
    if not fails:
        demo = classify(Indicators(peqi=0.14, n_prompts=18, abhr=0.10, n_tasks=8,
                                   calib_bias=0.28, reliance=6.1, critical=0.33,
                                   n_ct_items=12, condition="G"))
        print(f"ukážka:  {demo.label}  ({demo.confidence})\n  {demo.reason}")
    print("\nprofiles self-test: " + ("ok" if not fails
                                      else f"{len(fails)} failures"))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
