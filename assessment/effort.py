"""effort.py -- did the pupil try? And did they try equally in all three conditions?

The threat this module exists to measure
----------------------------------------
The thesis already names the confound: "pupils learned more" and "pupils tried
harder on the test after the lesson they enjoyed" are the same contrast unless
something separates them. Its answer so far is a negative control -- an outcome
forbidden to move. That is the right kind of answer and it is incomplete, because
a negative control tells you *that* something is wrong, not *what*. If the
control fails, the study is left with an unexplained failure and no way to say
whether it was effort, fatigue or a broken instrument.

Test-taking effort is directly measurable, and it is the single most plausible
candidate here, for a reason specific to this design: condition G removes effort
during the lesson. Satisfaction in condition G is predicted to be highest. A
pupil who has just had the most pleasant lesson sits a test that does not count
for a grade. Whether they then invest is an empirical question, and the answer
plausibly differs by condition -- which makes it differential, and differential
effort on the outcome is not noise. It is bias in the direction of the
hypothesis, or against it, and nobody can say which without measuring it.

Measuring it requires per-item response times, which requires digital delivery.
This is the strongest single argument for the runner: a paper test cannot produce
this number at all.

How rapid guessing is identified
--------------------------------
A response faster than any reading of the item can be is not an answer. The
standard move (Wise & Kong) is a per-item time threshold below which a response
is classified as rapid-guessing and the item is treated as not attempted. The
threshold is where the method is usually fudged, so three rules are implemented
and all three reported:

    NT10   10% of the item's expected time -- the common convention
    FIXED  a flat floor; defensible only for short closed items
    BIMODAL the trough between the two modes of the observed time distribution,
            when there is one; this is the only rule that uses the data

They disagree, and the disagreement is the point: a result that holds under all
three is robust to the threshold, and a result that appears under one is a result
about the threshold. The thesis reports the effort-by-condition contrast under
each.

What is NOT done
----------------
Rapid-guessing responses are flagged, not deleted, and the flag is a variable in
its own right. Deleting them would quietly change the estimand from "what pupils
scored" to "what pupils scored when they were trying", and those differ by
condition precisely when it matters most. The pre-registered rule is: report the
primary analysis on all responses, and the effort-filtered analysis as a declared
robustness check, both always.

Run:  python effort.py        self-test with planted effort differences
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass

# 10% of the expected time. Below this, no reading of the stem has happened.
NT_FRACTION = 0.10
# No closed item can be read and answered in under this, whatever its expected
# time says. Guards against an item whose expected_sec was set too low.
ABSOLUTE_FLOOR_SEC = 3.0
# A pupil who rapid-guesses more than this share of a test did not take the test.
SOLUTION_BEHAVIOUR_FLOOR = 0.90


@dataclass
class ItemEffort:
    item_id: str
    seconds: float
    expected_sec: float
    rapid_nt10: bool
    rapid_fixed: bool
    rapid_bimodal: bool


def nt10_threshold(expected_sec: float) -> float:
    return max(NT_FRACTION * expected_sec, ABSOLUTE_FLOOR_SEC)


def bimodal_threshold(times: list[float], grid: int = 60) -> float | None:
    """The trough between two modes of log response time, if there are two.

    Returns None when the distribution is single-peaked -- which is the healthy
    case and must not be forced into a threshold. A method that always returns a
    number would invent rapid guessing in a class that did not do any.
    """
    xs = [math.log(max(t, 0.25)) for t in times if t > 0]
    if len(xs) < 40:
        return None
    lo, hi = min(xs), max(xs)
    if hi - lo < 0.5:
        return None
    h = 0.35                                    # kernel width in log seconds
    pts = [lo + (hi - lo) * i / (grid - 1) for i in range(grid)]
    dens = []
    for p in pts:
        s = sum(math.exp(-0.5 * ((p - x) / h) ** 2) for x in xs)
        dens.append(s / (len(xs) * h * math.sqrt(2 * math.pi)))
    # find a local minimum strictly between two local maxima
    peaks = [i for i in range(1, grid - 1)
             if dens[i] > dens[i - 1] and dens[i] >= dens[i + 1]]
    if len(peaks) < 2:
        return None
    a, b = peaks[0], peaks[-1]
    trough = min(range(a + 1, b), key=lambda i: dens[i])
    # a trough that is not actually a dip is not a trough
    if dens[trough] > 0.6 * min(dens[a], dens[b]):
        return None
    return math.exp(pts[trough])


def classify(responses, expected: dict[str, float]) -> list[ItemEffort]:
    """responses: iterable of objects with .item_id and .seconds"""
    by_item: dict[str, list[float]] = {}
    for r in responses:
        by_item.setdefault(r.item_id, []).append(r.seconds)
    bim = {k: bimodal_threshold(v) for k, v in by_item.items()}

    out = []
    for r in responses:
        exp = expected.get(r.item_id, 30.0)
        t_nt = nt10_threshold(exp)
        t_bi = bim.get(r.item_id)
        out.append(ItemEffort(
            item_id=r.item_id, seconds=r.seconds, expected_sec=exp,
            rapid_nt10=r.seconds < t_nt,
            rapid_fixed=r.seconds < ABSOLUTE_FLOOR_SEC,
            rapid_bimodal=bool(t_bi is not None and r.seconds < t_bi)))
    return out


def response_time_effort(flags: list[ItemEffort], rule: str = "nt10") -> float:
    """RTE: the share of items the pupil engaged with. 1.0 = engaged throughout."""
    if not flags:
        return float("nan")
    attr = {"nt10": "rapid_nt10", "fixed": "rapid_fixed",
            "bimodal": "rapid_bimodal"}[rule]
    rapid = sum(1 for f in flags if getattr(f, attr))
    return round(1.0 - rapid / len(flags), 4)


def pupil_summary(flags: list[ItemEffort]) -> dict:
    out = {f"rte_{r}": response_time_effort(flags, r)
           for r in ("nt10", "fixed", "bimodal")}
    out["n_items"] = len(flags)
    out["median_seconds"] = round(sorted(f.seconds for f in flags)
                                  [len(flags) // 2], 1) if flags else None
    # the pre-registered exclusion, declared here and applied nowhere else
    out["below_solution_behaviour_floor"] = bool(
        out["rte_nt10"] < SOLUTION_BEHAVIOUR_FLOOR)
    out["rules_agree"] = bool(
        out["below_solution_behaviour_floor"]
        == (out["rte_fixed"] < SOLUTION_BEHAVIOUR_FLOOR)
        == (out["rte_bimodal"] < SOLUTION_BEHAVIOUR_FLOOR))
    return out


# ===========================================================================
def condition_contrast(by_condition: dict[str, list[float]]) -> dict:
    """Mean RTE per condition, with the contrast the design actually cares about.

    Reported even -- especially -- when it is null, because the null is what
    licenses reading the outcome contrast as learning rather than as effort. An
    unreported effort check is an assumption; a reported null is evidence.
    """
    means = {k: round(sum(v) / len(v), 4) for k, v in by_condition.items() if v}
    out = {"mean_rte": means, "n": {k: len(v) for k, v in by_condition.items()}}
    if {"G", "K"} <= set(means):
        out["G_minus_K"] = round(means["G"] - means["K"], 4)
    if {"A", "K"} <= set(means):
        out["A_minus_K"] = round(means["A"] - means["K"], 4)
    if {"A", "G"} <= set(means):
        out["A_minus_G"] = round(means["A"] - means["G"], 4)
    spread = max(means.values()) - min(means.values()) if means else 0.0
    out["spread"] = round(spread, 4)
    # 0.02 of RTE is about a quarter of an item on a twelve-item test; below that
    # a difference in effort cannot carry a difference in score worth reporting.
    out["differential_effort_detected"] = bool(spread > 0.02)
    out["reading"] = (
        "Ak je rozpätie pod 0,02, úsilie pri teste sa medzi podmienkami nelíši "
        "natoľko, aby mohlo nesť rozdiel vo výsledku — a rozdiel vo výsledku sa "
        "dá čítať ako učenie. Ak je nad, nedá sa, a hlavná analýza musí úsilie "
        "zahrnúť ako kovariát. Toto rozhodnutie je stanovené vopred."
        if spread <= 0.02 else
        "Rozpätie je nad hranicou: úsilie pri teste sa medzi podmienkami líši a "
        "hlavná analýza ho musí zahrnúť ako kovariát. Rozdiel vo výsledku sa "
        "nedá čítať ako samotné učenie.")
    return out


# ===========================================================================
def self_test() -> list[str]:
    import random
    fails = []

    class R:
        def __init__(self, i, s):
            self.item_id, self.seconds = i, s

    expected = {"I1": 40.0, "I2": 160.0}

    # 1. an attentive pupil is not flagged
    rs = [R("I1", 35.0), R("I2", 150.0)]
    f = classify(rs, expected)
    if response_time_effort(f) != 1.0:
        fails.append("attentive responses flagged as rapid guessing")

    # 2. a 1.2-second answer to a 40-second item is flagged by every rule
    f = classify([R("I1", 1.2)], expected)
    if not (f[0].rapid_nt10 and f[0].rapid_fixed):
        fails.append("1.2 s on a 40 s item not flagged")

    # 3. the absolute floor catches an item whose expected_sec was set too low
    f = classify([R("I1", 2.0)], {"I1": 8.0})   # NT10 would be 0.8 s
    if not f[0].rapid_nt10:
        fails.append("absolute floor did not back up a too-low NT10 threshold")

    # 4. bimodal returns None on a single-peaked distribution -- it must not
    #    invent rapid guessing where there is none
    rng = random.Random(4)
    single = [R("I1", max(3.0, rng.gauss(38, 8))) for _ in range(200)]
    if bimodal_threshold([r.seconds for r in single]) is not None:
        fails.append("bimodal threshold invented a trough in a unimodal sample")

    # 5. and finds one when the sample really is two populations
    mixed = single + [R("I1", max(0.6, rng.gauss(2.0, 0.6))) for _ in range(60)]
    thr = bimodal_threshold([r.seconds for r in mixed])
    if thr is None or not 3 < thr < 30:
        fails.append(f"bimodal threshold missed a planted trough: {thr}")

    # 6. a planted differential effort is detected; equal effort is not
    eq = condition_contrast({"K": [0.99] * 40, "G": [0.99] * 40, "A": [0.99] * 40})
    if eq["differential_effort_detected"]:
        fails.append("equal effort reported as differential")
    df = condition_contrast({"K": [0.99] * 40, "G": [0.90] * 40, "A": [0.98] * 40})
    if not df["differential_effort_detected"] or abs(df["spread"] - 0.09) > 1e-9:
        fails.append(f"planted differential effort not recovered: {df}")
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
    print("effort self-test: " + ("ok" if not fails else f"{len(fails)} failures"))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
