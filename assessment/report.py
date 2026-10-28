"""report.py -- what comes back out, and to whom.

The thing that gets forgotten
-----------------------------
The protocol promises the school "an aggregated report for the class (not for the
pupil), compared against the other participating classes". Nothing specified what
is in it. That omission is not cosmetic: a school that receives nothing useful
does not let the study back next year, and a measurement instrument that returns
nothing to the people measured is extractive. The assignment asks for a tool
schools can use. A tool whose only output is a CSV for the researcher is not one.

But there is a sharper reason to specify it carefully. A class report is a
disclosure. Twenty-two pupils, three conditions, four profiles -- a table of
counts crossed by condition has cells of two and three pupils, and a teacher who
knows which pupils sat which condition can often read an individual out of a
small cell. So the report needs suppression rules that are applied by code, not
by good intentions, and the rules need to be testable.

Three audiences, three different documents
------------------------------------------
TEACHER     what to teach next lesson. Misconception counts by item, at class
            level, with no condition breakdown at all -- the condition is the
            researcher's variable and is of no pedagogical use to the teacher,
            while adding it is precisely what creates the small cells.
SCHOOL      how this class compares with the others, on a small number of
            aggregates, with suppression and with no pupil-level anything.
RESEARCHER  the full pseudonymous analytic file, which is `scoring.finalise`.

The pupil gets no individual score, and that is a decision with a reason, stated
in the thesis: the critical-thinking instrument has a reliability around 0.73,
which supports comparing groups and does not support a statement about one
person. Handing a pupil a number the instrument cannot justify would be the same
error the thesis criticises elsewhere -- reporting a figure whose meaning is not
known.

Run:  python report.py        self-test, including the disclosure checks
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field

# A cell smaller than this is not published, in any report, ever.
MIN_CELL = 5
# A class smaller than this gets no comparison against other classes: with few
# pupils the class mean is its own pupils, and "your class is below average" is
# then a statement about three identifiable children.
MIN_CLASS_FOR_COMPARISON = 12
SUPPRESSED = "< 5"


@dataclass
class ClassData:
    """Everything the two reports may draw on. Assembled by the caller so that
    this module cannot reach for anything that was not handed to it."""
    klass: str
    n_pupils: int
    # item_id -> {chosen_option_index: count}
    distractors: dict[str, dict[int, int]] = field(default_factory=dict)
    # item_id -> (correct_count, attempted_count)
    item_correct: dict[str, tuple[int, int]] = field(default_factory=dict)
    # item_id -> diagnosis text per option
    diagnoses: dict[str, dict[str, str]] = field(default_factory=dict)
    # profile label -> count
    profiles: dict[str, int] = field(default_factory=dict)
    # aggregate means for the school report
    means: dict[str, float] = field(default_factory=dict)
    # the same means across all participating classes, for context
    cohort_means: dict[str, float] = field(default_factory=dict)
    cohort_classes: int = 0


# ===========================================================================
def _suppress(count: int) -> object:
    return count if count >= MIN_CELL else SUPPRESSED


def teacher_report(d: ClassData, top_n: int = 5) -> dict:
    """What to teach on Monday. No conditions, no pupils, no comparisons.

    Ranked by how many pupils hold the misconception, not by how hard the item
    was: an item nineteen pupils failed in nineteen different ways is a bad item,
    while an item eleven pupils failed in the SAME way is a lesson.
    """
    rows = []
    for item_id, counts in d.distractors.items():
        dx = d.diagnoses.get(item_id, {})
        for opt, n in counts.items():
            text = dx.get(str(opt), "")
            if not text:
                continue                     # the key, or an undiagnosed option
            rows.append(dict(item_id=item_id, pupils=n,
                             share=round(n / d.n_pupils, 2),
                             misconception=text))
    rows.sort(key=lambda r: -r["pupils"])
    shown = [r for r in rows if r["pupils"] >= MIN_CELL][:top_n]

    hard = []
    for item_id, (c, a) in sorted(d.item_correct.items(),
                                  key=lambda kv: kv[1][0] / max(kv[1][1], 1)):
        if a >= MIN_CELL:
            hard.append(dict(item_id=item_id, correct=round(c / a, 2),
                             attempted=a))

    return dict(
        audience="učiteľ", klass=d.klass, pupils=d.n_pupils,
        misconceptions=shown,
        suppressed_rows=len(rows) - len(shown),
        hardest_items=hard[:top_n],
        condition_breakdown=None,
        note=("Zoradené podľa toho, koľko žiakov drží tú istú mylnú predstavu, "
              "nie podľa obtiažnosti položky. Položka, ktorú 19 žiakov pokazilo "
              "19 rôznymi spôsobmi, je zlá položka; položka, ktorú 11 žiakov "
              "pokazilo rovnako, je učivo na ďalšiu hodinu. "
              "Rozpis podľa podmienky tu nie je zámerne: učiteľovi na nič "
              "neslúži a práve on vytvára bunky s dvoma žiakmi, z ktorých sa dá "
              "prečítať jednotlivec."))


def school_report(d: ClassData) -> dict:
    """How this class compares. Aggregates only, suppressed, no conditions."""
    comparable = d.n_pupils >= MIN_CLASS_FOR_COMPARISON and d.cohort_classes >= 3
    comp = {}
    if comparable:
        for k, v in d.means.items():
            if k in d.cohort_means:
                comp[k] = dict(klass=round(v, 2),
                               cohort=round(d.cohort_means[k], 2),
                               difference=round(v - d.cohort_means[k], 2))

    prof = {k: _suppress(v) for k, v in sorted(d.profiles.items())}
    return dict(
        audience="škola", klass=d.klass, pupils=d.n_pupils,
        comparison=comp,
        comparable=comparable,
        comparison_withheld_reason=(
            None if comparable else
            f"Porovnanie s ostatnými triedami sa neuvádza: trieda má "
            f"{d.n_pupils} žiakov (potrebných {MIN_CLASS_FOR_COMPARISON}) alebo "
            f"je zapojených menej než tri triedy. Pri malej triede je priemer "
            f"triedy tvorený niekoľkými konkrétnymi žiakmi."),
        profile_mix=prof,
        pupil_level_data=None,
        note=("Žiadne individuálne výsledky. Spoľahlivosť nástroja (okolo 0,73) "
              "postačuje na porovnanie skupín a nie na výrok o jednom žiakovi; "
              "oznámiť žiakovi číslo, ktoré nástroj neunesie, by bola tá istá "
              "chyba, akú práca kritizuje inde."))


def pupil_report() -> dict:
    """Deliberately empty, and documented as such so its absence is a decision."""
    return dict(
        audience="žiak", content=None,
        reason=("Žiak nedostáva individuálne skóre. Dôvod je uvedený v metodike: "
                "nástroje tejto štúdie majú spoľahlivosť vhodnú na porovnanie "
                "skupín, nie na výrok o jednotlivcovi. Žiak dostáva po skončení "
                "štúdie prístup k úlohám a správne odpovede, čo je informácia, "
                "ktorú meranie unesie."))


# ===========================================================================
def disclosure_audit(reports: list[dict]) -> dict:
    """Would any published cell let a reader name a pupil?

    Run over the actual reports rather than over the intention. Checks three
    things: that no numeric count below MIN_CELL survives anywhere in the
    structure; that nothing resembling a pseudonym appears; and that no report
    crosses condition with anything, since that is where the small cells come
    from.
    """
    blob = json.dumps(reports, ensure_ascii=False)
    small = []

    def walk(o, path=""):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, f"{path}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{path}[{i}]")
        elif isinstance(o, int) and not isinstance(o, bool):
            # counts live under these keys; a mean or a minute is not a count
            if any(path.endswith(s) for s in (".pupils", ".count")) \
                    or ".profile_mix" in path or ".misconceptions" in path:
                if 0 < o < MIN_CELL:
                    small.append((path, o))
    for r in reports:
        walk(r)

    return dict(
        reports=len(reports),
        small_cells_published=small,
        looks_like_a_pseudonym=[t for t in ("pseudonym", "GY-", "kod_ziaka")
                                if t in blob],
        condition_crossed=[r.get("audience") for r in reports
                           if r.get("condition_breakdown") is not None],
        clean=not small and "pseudonym" not in blob,
    )


# ===========================================================================
def self_test() -> list[str]:
    fails = []
    d = ClassData(
        klass="2.A", n_pupils=22,
        distractors={"T1-6": {1: 11, 2: 3, 3: 1}, "T1-4": {1: 6, 2: 2}},
        item_correct={"T1-6": (7, 22), "T1-4": (14, 22), "T1-1": (20, 22)},
        diagnoses={"T1-6": {"1": "prenáša lineárnu intuíciu na logaritmický rast",
                            "2": "zamieňa logaritmický rast s konštantným",
                            "3": "zamieňa s kvadratickým rastom"},
                   "T1-4": {"1": "počíta o jedno polenie viac",
                            "2": "polí interval len raz"}},
        profiles={"slepo dôverujúci": 6, "kritický používateľ": 7,
                  "vyhýbajúci sa": 3, "priemerný": 6},
        means={"peqi": 0.41, "ipt_correct": 0.58},
        cohort_means={"peqi": 0.47, "ipt_correct": 0.61},
        cohort_classes=9)

    t = teacher_report(d)
    if not t["misconceptions"]:
        fails.append("teacher report found no misconception in a class that has one")
    top = t["misconceptions"][0]
    if top["pupils"] != 11 or "lineárnu" not in top["misconception"]:
        fails.append(f"wrong top misconception: {top}")
    if any(r["pupils"] < MIN_CELL for r in t["misconceptions"]):
        fails.append("teacher report published a cell below the minimum")
    if t["suppressed_rows"] < 1:
        fails.append("nothing was suppressed although small cells existed")
    if t["condition_breakdown"] is not None:
        fails.append("teacher report crossed condition")

    s = school_report(d)
    if s["profile_mix"]["vyhýbajúci sa"] != SUPPRESSED:
        fails.append("a profile count of 3 was published")
    if s["profile_mix"]["slepo dôverujúci"] != 6:
        fails.append("a profile count of 6 was suppressed")
    if not s["comparable"] or "peqi" not in s["comparison"]:
        fails.append("comparison withheld from a class that qualifies")

    # a small class gets no comparison at all
    small = ClassData(klass="2.B", n_pupils=8, means={"peqi": 0.2},
                      cohort_means={"peqi": 0.47}, cohort_classes=9,
                      profiles={"priemerný": 8})
    s2 = school_report(small)
    if s2["comparable"] or s2["comparison"]:
        fails.append("a class of 8 was compared against the cohort")
    if not s2["comparison_withheld_reason"]:
        fails.append("withholding was not explained")

    # too few classes in the cohort: comparison identifies the other classes
    lone = ClassData(klass="2.C", n_pupils=24, means={"peqi": 0.2},
                     cohort_means={"peqi": 0.47}, cohort_classes=2,
                     profiles={"priemerný": 24})
    if school_report(lone)["comparable"]:
        fails.append("compared against a cohort of two classes")

    aud = disclosure_audit([t, s, s2, pupil_report()])
    if not aud["clean"]:
        fails.append(f"disclosure audit failed: {aud}")
    if aud["condition_crossed"]:
        fails.append("a report crossed condition")
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
    print("report self-test: " + ("ok" if not fails else f"{len(fails)} failures"))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
