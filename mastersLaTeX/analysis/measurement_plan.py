"""measurement_plan.py -- can the plan actually measure what it says it measures?

The problem with the phrase "cognitive abilities"
-------------------------------------------------
"Changes in pupils' cognitive abilities" is not one measurable thing. It names
at least four constructs that differ by two orders of magnitude in how fast they
change, and the difference decides everything about how they can be measured:

  L0  TRAIT          fluid reasoning              changes over years
  L1  GENERAL SKILL  computational thinking       changes over months
  L2  DOMAIN KNOWLEDGE  the three lesson topics   changes within one lesson
  L3  STRATEGY       offloading habit, calibration  changes within one task

From which one rule follows, and it is the rule this module enforces:

    THE MEASUREMENT INTERVAL MUST MATCH THE CONSTRUCT'S CHANGE RATE.

A three-week study cannot measure change in L0. Nothing about the instrument
fixes that -- it is a property of the construct. A design that claims otherwise
is not underpowered, it is measuring the wrong thing. So L0 is not an outcome
here: it is a covariate and a negative control, which is a claim that it does
NOT change, and that claim has its own precision requirement.

What this module checks
-----------------------
Three things the thesis asserts and has never verified:

  1. RELIABILITY BY ROLE. Each instrument has a job, and each job has a
     different precision requirement. An outcome needs to detect change. A
     covariate needs to remove confounding -- and an unreliable covariate
     removes only a fraction of it. A negative control needs to be able to
     CLEAR, and an unreliable one cannot: it does not produce false alarms, it
     produces permanent inability to certify. Each is computed separately,
     because "reliability >= 0.7" is not a requirement, it is a slogan.

  2. THE TIME BUDGET -- now DELEGATED to `assessment/sessions.py`, which
     computes it from the item bank rather than from one average per instrument.
     This module used to compute its own, and for a while the thesis had two
     budgets that disagreed. See the note above `time_budget()`.

  3. LONGITUDINAL INVARIANCE. A change score is meaningless unless the item
     parameters are stable across occasions. The thesis tests DIF by condition
     and not by occasion, which leaves the primary contrast -- a change over
     three weeks -- resting on an untested assumption.

Run:  python measurement_plan.py      -> out/measurement_plan.json
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from pathlib import Path

import numpy as np
from console import use_utf8

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"

# The item bank is the single source of truth for how long a test is. Hard-coded
# lengths here survived the immediate form being shortened from sixteen items to
# twelve, so the reliability and the time budget were computed for an instrument
# the study does not administer -- the same defect as in dgp.py, found the same
# way and fixed the same way.
import sys as _sys
_sys.path.insert(0, str(HERE.parents[1] / "assessment"))


def _bank_items(bank_id: str) -> int:
    from bank import load_all
    return load_all()[bank_id].n_items
OUT.mkdir(exist_ok=True)


# ===========================================================================
# 1.  The construct hierarchy, as data rather than as prose.
# ===========================================================================
@dataclass
class Instrument:
    layer: str
    construct: str
    name: str
    source: str
    n_items: int
    sec_per_item: float
    role: str                    # outcome | covariate | negative_control
    change_horizon: str
    occasions: tuple[str, ...]
    licence: str
    slovak: str
    notes: str = ""

    def minutes(self) -> float:
        """Administration time including instructions and settling."""
        return round(self.n_items * self.sec_per_item / 60.0 + 3.0, 1)


PLAN: list[Instrument] = [
    Instrument(
        layer="L0", construct="fluidné uvažovanie (g_f)",
        name="ICAR matrix reasoning + letter/number series",
        source="International Cognitive Ability Resource (Condon & Revelle, 2014)",
        n_items=20, sec_per_item=45, role="covariate+negative_control",
        change_horizon="years",
        occasions=("T0", "T4"),
        licence="public domain, no fee",
        slovak="items are figural/numeric; only the instruction needs translating",
        notes=("Chosen over Raven's SPM, which is licensed and priced per "
               "booklet. Figural items carry no language load, which matters in "
               "a bilingual-adjacent population.")),
    Instrument(
        layer="L1", construct="algoritmické a informatické myslenie",
        name="iBobor / Bebras task set",
        source="iBobor, FMFI UK Bratislava",
        n_items=8, sec_per_item=100, role="covariate+exploratory_outcome",
        change_horizon="months",
        occasions=("T0", "T4", "T6 (optional semester arm)"),
        licence="ask the organisers; tasks are published after each round",
        slovak="native Slovak, age-graded, already in EduPage",
        notes=("The decisive practical asset. Over 600 past tasks sit in "
               "EduPage, the system most Slovak schools already run, calibrated "
               "on a cohort of roughly 140,000 pupils a year. No other "
               "instrument in this plan has a Slovak norming base of that size.")),
    Instrument(
        layer="L2", construct="vedomosti k téme (T1/T2/T3)",
        name="IPT / DRT / TT, purpose-built, Rasch-calibrated",
        source="this thesis, blueprint in Chapter 5",
        n_items=_bank_items("T1_IPT"), sec_per_item=55, role="outcome",
        change_horizon="one lesson",
        occasions=("+0 min", "+3 weeks"),
        licence="own",
        slovak="own",
        notes="The primary outcome. Six anchor items link the two forms."),
    Instrument(
        layer="L3", construct="kalibrácia sebadôvery",
        name="item-level JOL slider",
        source="Schraw (2009); Nelson (1984) gamma",
        n_items=_bank_items("T1_IPT"), sec_per_item=6, role="outcome",
        change_horizon="within a task",
        occasions=("+0 min", "+3 weeks"),
        licence="own",
        slovak="own",
        notes="Rides on the knowledge test; costs no separate session."),
    Instrument(
        layer="L3", construct="epistemická kvalita interakcie",
        name="PEQI from captured prompts",
        source="this thesis",
        n_items=0, sec_per_item=0, role="outcome",
        change_horizon="within a task",
        occasions=("during each AI lesson",),
        licence="own",
        slovak="own",
        notes="Observed, not administered: costs zero lesson time."),
    Instrument(
        layer="L3", construct="metakognitívna uvedomelosť (trait)",
        name="Jr. MAI version B, shortened",
        source="Sperling et al. (2002)",
        n_items=_bank_items("JRMAI"), sec_per_item=12, role="covariate",
        change_horizon="months",
        occasions=("T0",),
        licence="free for research use",
        slovak="requires forward/back translation and a pilot",
        notes=("A self-report instrument in a thesis whose premise is that "
               "self-report mismeasures cognitive offloading. It is admissible "
               "only as a trait COVARIATE and never as an outcome; the tension "
               "is stated rather than hidden.")),
]


# ===========================================================================
# 2.  Reliability, computed per role rather than against a slogan.
# ===========================================================================
def rasch_reliability(n_items: int, ability_sd: float = 1.0,
                      item_sd: float = 0.9, n_persons: int = 4000,
                      seed: int = 21) -> float:
    """Person separation reliability of an n-item dichotomous test.

    Simulated rather than taken from KR-20 on an assumed p, because the
    quantity that matters is how well the test orders PEOPLE at the spread of
    ability actually present, and that depends on how item difficulty is spread
    against it.
    """
    rng = np.random.default_rng(seed + n_items)
    theta = rng.normal(0, ability_sd, n_persons)
    b = np.linspace(-1.6, 1.6, n_items) + rng.normal(0, item_sd * 0.3, n_items)
    p = 1.0 / (1.0 + np.exp(-(theta[:, None] - b[None, :])))
    x = (rng.random((n_persons, n_items)) < p).astype(float)

    score = x.sum(axis=1)
    # KR-20 as the observed-score reliability of this simulated test
    pj = x.mean(axis=0)
    var_total = score.var(ddof=1)
    if var_total <= 0:
        return 0.0
    kr20 = (n_items / (n_items - 1)) * (1 - (pj * (1 - pj)).sum() / var_total)
    return float(max(0.0, min(kr20, 0.999)))


def reliability_curve(grid=(4, 6, 8, 10, 12, 16, 20, 24, 30)) -> list[dict]:
    return [{"n_items": n, "reliability": round(rasch_reliability(n), 3)}
            for n in grid]


# --- what each role actually requires -------------------------------------
def covariate_adjustment_recovered(reliability: float) -> float:
    """Share of confounding an imperfectly measured covariate removes.

    Classical result: regressing on a covariate measured with reliability rho
    removes only rho of the confounding it would remove if measured perfectly.
    A covariate at 0.60 leaves 40% of its own confounding in place, and the
    residual looks exactly like an effect.
    """
    return round(reliability, 3)


def negative_control_clearance(reliability: float, n_pupils: int = 330,
                               n_classes: int = 18, bound: float = 0.30,
                               n_sim: int = 2000, seed: int = 88) -> float:
    """Probability the trait control can CLEAR, given its reliability.

    This is the direction people get wrong. An unreliable negative control does
    not raise false alarms -- it widens the interval, and a wide interval cannot
    be certified as lying inside the equivalence band. So an unreliable control
    fails by NEVER CLEARING, which reads in a results table as an unexplained
    anomaly rather than as a measurement problem.

    The estimand matches `falsification.trait_control`: a BETWEEN-pupil
    comparison, keyed on the condition of the pupil's last period, on the
    CHANGE T4 - T0 rather than on the level. Both details matter and both were
    got wrong first:

      * a trait is measured once per occasion, so no within-pupil condition
        contrast exists for it -- attempting one yields an identically
        mean-zero quantity that clears everything and tests nothing;
      * on the LEVEL, the between-pupil standard deviation is about 1 plus a
        class component, and eighteen clusters cannot fit that inside the band:
        the control then clears barely half the time with nothing wrong. The
        change cancels the stable part and leaves sd = sqrt(2(1-rho)), which is
        what makes the control usable at all -- and it is available only
        because the trait is administered twice.
    """
    from scipy import stats
    rng = np.random.default_rng(seed)
    sd_change = np.sqrt(2.0 * (1.0 - reliability))
    g = np.arange(n_pupils) % n_classes
    grp = np.arange(n_pupils) % 3          # last-period condition, K / G / A
    keep = grp < 2                         # two of the three are compared
    gk = g[keep]
    X = np.column_stack([np.ones(int(keep.sum())),
                         (grp[keep] == 0).astype(float)])
    XtX_inv = np.linalg.pinv(X.T @ X)
    uniq = np.unique(gk)
    J = len(uniq)
    masks = [gk == j for j in uniq]

    hits = 0
    for _ in range(n_sim):
        y = rng.normal(0.0, sd_change, int(keep.sum()))
        beta = XtX_inv @ X.T @ y
        u = y - X @ beta
        meat = np.zeros((2, 2))
        for m in masks:
            s = X[m].T @ u[m]
            meat += np.outer(s, s)
        V = (J / max(J - 1, 1)) * XtX_inv @ meat @ XtX_inv
        se = float(np.sqrt(max(V[1, 1], 1e-12)))
        est, dfree = float(beta[1]), J - 1
        p = max(float(stats.t.sf((est + bound) / se, dfree)),
                float(stats.t.cdf((est - bound) / se, dfree)))
        hits += p < 0.05
    return round(hits / n_sim, 3)


def items_for_role(role: str, target: float, grid=range(4, 41)) -> int | None:
    """Fewest items at which the role's requirement is met."""
    for n in grid:
        if rasch_reliability(n) >= target:
            return n
    return None


# ===========================================================================
# 3.  Longitudinal invariance: is a change score even interpretable?
# ===========================================================================
def drift_precision(n_pupils: int = 330, n_anchor: int = 6,
                    n_sim: int = 400, seed: int = 909) -> dict:
    """How precisely can a single item's difficulty shift be estimated?

    This decides which drift criterion is even available. A Bonferroni-corrected
    significance test over sixteen items needs |z| > 3.3, and at this sample the
    standard error of a per-item shift is about 0.2 logits, so it would only
    flag drift beyond roughly 0.7 -- larger than the ETS "large" band the thesis
    uses everywhere else. Testing significance is therefore the wrong tool: the
    right one is the ETS band applied to the estimate, with the standard error
    reported so the reader can see how much of the band is noise.
    """
    rng = np.random.default_rng(seed)
    ses = []
    for _ in range(n_sim):
        theta = rng.normal(0, 1, n_pupils)
        b = np.linspace(-1.2, 1.2, n_anchor)
        def draw():
            p = 1 / (1 + np.exp(-(theta[:, None] - b[None, :])))
            return (rng.random((n_pupils, n_anchor)) < p).astype(float)
        x0, x1 = draw(), draw()
        eps = 1e-6
        p0 = np.clip(x0.mean(axis=0), eps, 1 - eps)
        p1 = np.clip(x1.mean(axis=0), eps, 1 - eps)
        se = np.sqrt(1 / (n_pupils * p0 * (1 - p0))
                     + 1 / (n_pupils * p1 * (1 - p1)))
        ses.append(se.mean())
    se_mean = float(np.mean(ses))
    return {
        "n_pupils": n_pupils,
        "n_anchor_items": n_anchor,
        "se_of_item_shift_logits": round(se_mean, 3),
        "detectable_at_80pct_power_uncorrected": round(2.80 * se_mean, 2),
        "detectable_with_bonferroni_over_anchors":
            round(3.20 * se_mean, 2),
        "ets_large_band": 0.64,
        "criterion": (
            "flag an anchor item whose difficulty shifts by more than the ETS "
            "large band (0.64 logits) between occasions, and report the "
            "standard error alongside so the band is not mistaken for "
            "certainty. Significance testing is not used: at this sample it "
            "would only catch drift larger than the band it is meant to police."),
        "band_is_reachable": bool(0.64 >= 2.80 * se_mean),
    }


def item_drift_power(n_pupils: int = 330, n_items: int = 16,
                     drift: float = 0.5, n_drifting: int = 2,
                     n_sim: int = 600, seed: int = 404) -> dict:
    """Can the design detect an item that changed difficulty between occasions?

    If an item gets easier at the delayed test for reasons unrelated to the
    pupils -- it was discussed in another lesson, it leaked, it was reworded --
    then the change score confounds learning with item drift. The thesis tests
    DIF between CONDITIONS and not between OCCASIONS, which leaves precisely the
    contrast it cares about untested.

    Detection here is the ETS large band applied to the occasion shift, with a
    Bonferroni correction over items.
    """
    rng = np.random.default_rng(seed)
    detected, false_flags = 0, 0
    for _ in range(n_sim):
        theta = rng.normal(0, 1, n_pupils)
        b0 = np.linspace(-1.4, 1.4, n_items)
        b1 = b0.copy()
        b1[:n_drifting] -= drift                       # got easier
        def draw(bb):
            p = 1 / (1 + np.exp(-(theta[:, None] - bb[None, :])))
            return (rng.random((n_pupils, n_items)) < p).astype(float)
        x0, x1 = draw(b0), draw(b1)
        # difficulty shift per item, holding person measures fixed
        eps = 1e-6
        p0 = np.clip(x0.mean(axis=0), eps, 1 - eps)
        p1 = np.clip(x1.mean(axis=0), eps, 1 - eps)
        shift = np.log(p0 / (1 - p0)) - np.log(p1 / (1 - p1))
        se = np.sqrt(1 / (n_pupils * p0 * (1 - p0)) + 1 / (n_pupils * p1 * (1 - p1)))
        # ETS large band on the estimate, not a significance test; see
        # drift_precision() for why significance is the wrong tool here.
        flagged = np.abs(shift) > 0.64
        detected += int(flagged[:n_drifting].sum())        # per ITEM, not per study
        false_flags += int(flagged[n_drifting:].sum())
    return {
        "drift_logits": drift,
        "n_drifting_items": n_drifting,
        "per_item_power": round(detected / (n_sim * n_drifting), 3),
        "mean_false_flags_per_study": round(false_flags / n_sim, 3),
        "criterion": "|shift| > 0.64 logits, the ETS large band",
        "note": ("run on the anchor items, which are the only ones that appear "
                 "on both occasions and therefore the only ones on which drift "
                 "is identifiable at all"),
    }


# ===========================================================================
# 4.  The time budget, in the units a school works in.
# ===========================================================================
# ===========================================================================
# 2b.  The time budget is NOT computed here.
# ===========================================================================
# It used to be, with one average seconds-per-item per instrument, and it
# reported that every session fits. Computed from the items instead
# (`assessment/sessions.py`) three of five supervised sessions overran, because
# the average understated every instrument with rubric items -- and those sit in
# the session that carries the primary outcome.
#
# When the item-level budget was added, this module kept its own. For a while the
# thesis therefore had TWO time budgets that disagreed: one saying everything
# fits, one saying it does not. That is the defect this project has now paid for
# four times -- one specification, two implementations, repaired in one of them --
# and the fix is the same as the other three: delete the second copy rather than
# keep it in step.
#
# So this module delegates. Its own contribution, which the other budget does not
# duplicate, is reliability BY ROLE (an outcome, a covariate and a negative
# control need different precision) and longitudinal invariance.

def time_budget() -> dict:
    """The one budget, reshaped to the keys this module's consumers expect.

    Keys are kept stable because `export_macros.py` emits macros from them and
    `verify_thesis.py` checks them; the numbers now come from the item bank.
    """
    import sessions as _sessions           # the deployable layer owns this

    res = _sessions.budget()
    out: dict = {}
    for s in res["sessions"]:
        out[s["code"]] = {
            "label": s["label"],
            "mode": "supervised lesson" if s["supervised"] else "asynchronous",
            "blocks": [{"what": b["label"], "items": b["items"],
                        "minutes": b["minutes"]} for b in s["blocks"]],
            "lesson_minutes": s["teaching_min"] or None,
            "admin_minutes": s["handover_min"],
            "break_minutes": s["break_min"],
            "total_minutes": s["total_min"],
            "budget_minutes": s["budget_min"],
            "slack_minutes": s["slack_min"],
            "longest_unbroken_minutes": s["longest_run_min"],
            "fits": s["fits"],
            "within_fatigue_cap": s["within_fatigue_cap"],
        }
    out["all_sessions_fit"] = res["all_fit"]
    out["supervised_lesson_count"] = res["measurement_lessons_excl_teaching"]
    out["computed_by"] = "assessment/sessions.py, from the item bank"
    out["violations"] = res["violations"]
    return out


# ===========================================================================
def main() -> int:
    curve = reliability_curve()

    # Role-specific requirements, each argued rather than asserted.
    roles = {
        "outcome": {
            "requirement": 0.80,
            "why": ("a change score's reliability is roughly the average of the "
                    "two occasion reliabilities minus their correlation; below "
                    "0.80 per occasion the change score stops ordering pupils"),
        },
        "covariate": {
            "requirement": 0.75,
            "why": ("adjustment removes only `reliability` of the confounding; "
                    "at 0.75 a quarter of it survives, and survives looking "
                    "exactly like an effect"),
        },
        "negative_control": {
            "requirement": 0.70,
            "why": ("an unreliable control cannot CLEAR: the interval is too "
                    "wide to fit inside the equivalence band, so the control "
                    "fails by never certifying rather than by false alarm"),
        },
    }
    for r, d in roles.items():
        d["items_needed"] = items_for_role(r, d["requirement"])

    clearance = {f"{rho:.2f}": negative_control_clearance(rho)
                 for rho in (0.50, 0.60, 0.70, 0.80, 0.85, 0.90)}
    attenuation = {f"{rho:.2f}": covariate_adjustment_recovered(rho)
                   for rho in (0.50, 0.60, 0.70, 0.80, 0.90)}

    res = {
        "principle": ("the measurement interval must match the construct's "
                      "change rate; an instrument cannot repair a mismatch"),
        "hierarchy": [asdict(i) | {"minutes": i.minutes()} for i in PLAN],
        "reliability_by_length": curve,
        "roles": roles,
        "negative_control_clearance_by_reliability": clearance,
        "covariate_confounding_removed_by_reliability": attenuation,
        "drift_precision": drift_precision(),
        "item_drift": item_drift_power(drift=0.8),
        "time_budget": time_budget(),
    }

    # The verdicts the plan has to pass.
    gf = next(i for i in PLAN if i.layer == "L0")
    gf_rel = rasch_reliability(gf.n_items)
    res["verdict"] = {
        "gf_items": gf.n_items,
        "gf_reliability": round(gf_rel, 3),
        "gf_fit_for_negative_control":
            bool(gf_rel >= roles["negative_control"]["requirement"]),
        "gf_fit_for_covariate":
            bool(gf_rel >= roles["covariate"]["requirement"]),
        "gf_clearance_at_that_reliability":
            negative_control_clearance(gf_rel),
        "twelve_item_reliability": round(rasch_reliability(12), 3),
        "why_twelve_was_not_enough": (
            "the thesis specified twelve matrix items. At that length the test "
            "orders pupils well enough to be a rough covariate and NOT well "
            "enough to clear as a negative control, which is the harder of the "
            "two jobs it was given."),
        "every_session_fits": res["time_budget"]["all_sessions_fit"],
        "supervised_lessons_required": res["time_budget"]["supervised_lesson_count"],
        "drift_band_reachable": res["drift_precision"]["band_is_reachable"],
        "drift_per_item_power_at_point_eight": res["item_drift"]["per_item_power"],
    }

    (OUT / "measurement_plan.json").write_text(
        json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    use_utf8()
    raise SystemExit(main())
