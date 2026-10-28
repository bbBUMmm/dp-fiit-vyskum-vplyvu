"""pilot.py -- what one class can decide, and what it cannot.

The problem with "we will run a pilot"
--------------------------------------
A pilot without pre-specified decision rules is a rehearsal. It tells you the
lesson ran and the laptops worked, and then the real study is tuned by taste
against whatever the pilot happened to show. The tuning is invisible in the
final write-up and it is where a great deal of quiet flexibility enters school
research.

So the rules go in first. But writing rules is not enough either, because a
pilot of one class is about twenty pupils, and twenty pupils cannot measure most
of the things a pilot is asked to check. The second half of this module computes
which decisions that sample can actually support.

The finding that matters
------------------------
The thesis planned to screen items on their observed success rate: keep those
between 0.30 and 0.80. At n = 20 the standard error of an observed proportion is
about 0.11, so the rule discards a large share of perfectly good items and keeps
bad ones -- and every discarded item costs test length, which costs reliability,
which costs the study power. Screening on the POINT ESTIMATE is the error;
screening on the INTERVAL is the fix, and the difference is quantified below.

Run:  python pilot.py      -> out/pilot.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy import stats
from console import use_utf8

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)

PILOT_N = 20          # one class
P_LO, P_HI = 0.30, 0.80


# ===========================================================================
def screening_error_rates(n: int = PILOT_N, n_sim: int = 20_000,
                          seed: int = 12) -> dict:
    """How often does each screening rule get an item wrong?

    Two rules compared on the same simulated items:

      point:    drop the item if the OBSERVED success rate is outside the band
      interval: drop it only if the 90 % interval lies ENTIRELY outside the band

    The second is deliberately reluctant. With twenty pupils the evidence that
    an item is out of range is weak, and the cost of wrongly dropping a good
    item -- a shorter test, lower reliability, less power -- is paid by the main
    study, while the cost of wrongly keeping a mediocre one is small and
    detectable later by the fit statistics.
    """
    rng = np.random.default_rng(seed)
    # true success rates spanning good and bad items
    grid = np.round(np.arange(0.05, 0.96, 0.05), 2)
    rows = []
    for p_true in grid:
        x = rng.binomial(n, p_true, n_sim)
        p_hat = x / n
        drop_point = (p_hat < P_LO) | (p_hat > P_HI)

        lo, hi = _wilson(x, n, 0.90)
        drop_interval = (hi < P_LO) | (lo > P_HI)

        good = P_LO <= p_true <= P_HI
        rows.append({
            "p_true": float(p_true),
            "is_good_item": bool(good),
            "point_rule_drops": round(float(drop_point.mean()), 3),
            "interval_rule_drops": round(float(drop_interval.mean()), 3),
        })

    good = [r for r in rows if r["is_good_item"]]
    bad = [r for r in rows if not r["is_good_item"]]
    return {
        "n_pilot": n,
        "band": [P_LO, P_HI],
        "by_true_rate": rows,
        "point_rule": {
            "good_items_wrongly_dropped":
                round(float(np.mean([r["point_rule_drops"] for r in good])), 3),
            "bad_items_correctly_dropped":
                round(float(np.mean([r["point_rule_drops"] for r in bad])), 3),
        },
        "interval_rule": {
            "good_items_wrongly_dropped":
                round(float(np.mean([r["interval_rule_drops"] for r in good])), 3),
            "bad_items_correctly_dropped":
                round(float(np.mean([r["interval_rule_drops"] for r in bad])), 3),
        },
        "se_of_a_proportion_at_this_n": round(float(np.sqrt(0.25 / n)), 3),
    }


def _wilson(x: np.ndarray, n: int, conf: float) -> tuple[np.ndarray, np.ndarray]:
    """Wilson interval: behaves near 0 and 1, where a Wald interval does not."""
    z = float(stats.norm.ppf(1 - (1 - conf) / 2))
    p = x / n
    denom = 1 + z ** 2 / n
    centre = (p + z ** 2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / denom
    return centre - half, centre + half


def test_length_cost(n_items: int = 16, n_sim: int = 4000,
                     seed: int = 31) -> dict:
    """What wrongly dropping items costs the main study.

    Each discarded item shortens the test, and reliability falls with length.
    The point of computing it is that the cost is invisible at the moment the
    decision is made: the item is dropped in October and the power is lost in
    March.
    """
    from measurement_plan import rasch_reliability
    rows = []
    for dropped in (0, 1, 2, 3, 4, 6):
        k = n_items - dropped
        rows.append({"items_kept": k,
                     "reliability": round(rasch_reliability(k), 3)})
    base = rows[0]["reliability"]
    return {
        "curve": rows,
        "reliability_lost_per_item":
            round((base - rows[-1]["reliability"]) / 6, 4),
        "note": ("reliability falls roughly linearly over this range, so every "
                 "wrongly dropped item is a fixed, permanent tax on the main "
                 "study's power"),
    }


# ===========================================================================
def variance_component_precision(n_classes: int = 1, n_pupils: int = 20,
                                 tau2_true: float = 0.03,
                                 n_sim: int = 3000, seed: int = 55) -> dict:
    """Can a one-class pilot estimate the between-class variance? No.

    The power calculation needs tau^2_ct, the class-by-condition variance. It is
    a BETWEEN-class quantity, and a pilot has one class. The estimate has no
    degrees of freedom at all. This is stated because the plan currently lists
    'estimate tau^2 for the power calculation' among the pilot's purposes, and
    that is one thing a pilot of this shape cannot do.
    """
    return {
        "n_classes_in_pilot": n_classes,
        "estimable": bool(n_classes >= 2),
        "df_for_between_class_variance": max(n_classes - 1, 0),
        "verdict": ("a between-class variance cannot be estimated from one "
                    "class; with two it has one degree of freedom, which is "
                    "not an estimate either. The design must take tau^2 from "
                    "the literature and report sensitivity to it, which is "
                    "what the power analysis already does."),
    }


def guard_gate(n_prompts: int = 40, true_leak_rate: float = 0.02,
               n_sim: int = 20_000, seed: int = 71) -> dict:
    """What a zero-leak result on 40 adversarial prompts actually proves.

    The deployment gate demands zero leaks on 40 prompts. Passing it is
    necessary. It is worth knowing what it rules out: with a true leak rate of
    2 %, forty prompts pass clean more than half the time.
    """
    rng = np.random.default_rng(seed)
    passes = float((rng.binomial(n_prompts, true_leak_rate, n_sim) == 0).mean())
    # one-sided upper bound on the leak rate given zero observed leaks
    upper95 = 1 - 0.05 ** (1 / n_prompts)
    return {
        "n_prompts": n_prompts,
        "true_leak_rate_assumed": true_leak_rate,
        "probability_of_passing_clean": round(passes, 3),
        "upper_95_bound_on_leak_rate_given_zero": round(upper95, 4),
        "prompts_for_one_percent_bound": int(np.ceil(np.log(0.05)
                                                     / np.log(1 - 0.01))),
        "reading": ("zero leaks in forty prompts bounds the leak rate at about "
                    "7 % with 95 % confidence, not at zero. The gate is a "
                    "floor, not a certificate, and the study reports the "
                    "observed guard-violation rate from the real sessions "
                    "because that is the number with power behind it."),
    }


# ===========================================================================
DECISIONS = [
    {"question": "Are item difficulties in range?",
     "measure": "observed success rate per item, Wilson 90 % interval",
     "rule": "drop an item only if its interval lies entirely outside "
             "0.30-0.80; replace from the reserve set",
     "can_the_pilot_decide": "yes, but weakly -- screening on the point "
                             "estimate would discard good items"},
    {"question": "Does the timing fit?",
     "measure": "wall-clock minutes per block, recorded by the researcher",
     "rule": "if any session overruns its budget, cut items from the block "
             "with the most slack, never from the primary outcome",
     "can_the_pilot_decide": "yes -- this is what one class measures best"},
    {"question": "Does the capture layer work on the school's laptops?",
     "measure": "coverage = captured prompts / client-logged prompts",
     "rule": "below 0.80 for more than a quarter of pupils, the collection "
             "does not start",
     "can_the_pilot_decide": "yes"},
    {"question": "Is the condition-A guard airtight?",
     "measure": "leaks in 40 adversarial prompts",
     "rule": "any leak stops deployment until repaired and re-run",
     "can_the_pilot_decide": "partly -- zero of forty bounds the rate near "
                             "7 %, not at zero"},
    {"question": "Is the ICAR reliable in THIS population?",
     "measure": "KR-20 on the pilot class",
     "rule": "below 0.70, add items from the ICAR pool before collection",
     "can_the_pilot_decide": "weakly -- a reliability from twenty pupils has "
                             "a wide interval and should trigger review, not "
                             "an automatic change"},
    {"question": "Do local iBobor success rates match the published ones?",
     "measure": "mean signed difference across anchor items",
     "rule": "a systematic gap larger than 0.3 logits widens the sensitivity "
             "band on the reported national percentile",
     "can_the_pilot_decide": "yes, and it is the only cheap check on cohort "
                             "drift"},
    {"question": "What is the between-class variance?",
     "measure": "tau^2_ct",
     "rule": "taken from the literature; sensitivity reported across a grid",
     "can_the_pilot_decide": "NO -- it is a between-class quantity and the "
                             "pilot has one class"},
]

FORBIDDEN = [
    "changing the SESOI",
    "changing the primary outcome",
    "adding or removing a hypothesis from the confirmatory family",
    "changing the condition definitions",
    "choosing the analysis model after seeing pilot outcomes",
]


def main() -> int:
    res = {
        "purpose": ("a pilot without pre-specified decision rules is a "
                    "rehearsal; a pilot that can change anything is a way of "
                    "tuning the study until it agrees with you"),
        "decisions": DECISIONS,
        "forbidden_changes": FORBIDDEN,
        "item_screening": screening_error_rates(),
        "cost_of_dropping_items": test_length_cost(),
        "variance_components": variance_component_precision(),
        "guard_gate": guard_gate(),
    }
    scr = res["item_screening"]
    res["verdict"] = {
        "point_rule_drops_good_items":
            scr["point_rule"]["good_items_wrongly_dropped"],
        "interval_rule_drops_good_items":
            scr["interval_rule"]["good_items_wrongly_dropped"],
        "good_items_saved_by_the_interval_rule": round(
            scr["point_rule"]["good_items_wrongly_dropped"]
            - scr["interval_rule"]["good_items_wrongly_dropped"], 3),
        "bad_items_still_caught":
            scr["interval_rule"]["bad_items_correctly_dropped"],
        "tau_squared_not_estimable": not res["variance_components"]["estimable"],
        "guard_bound_not_zero":
            res["guard_gate"]["upper_95_bound_on_leak_rate_given_zero"],
    }
    (OUT / "pilot.json").write_text(
        json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    use_utf8()
    raise SystemExit(main())
