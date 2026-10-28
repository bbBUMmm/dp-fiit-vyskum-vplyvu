"""sesoi.py -- what does the equivalence bound actually buy?

The thesis sets SESOI = 0.30 SD and uses that one number for two jobs that pull
in opposite directions:

  * SUPERIORITY (A > K). A large SESOI is CONSERVATIVE: the study is powered
    only for effects at least that big, and a real effect of 0.15 is missed.
  * EQUIVALENCE (G == K, by TOST). A large SESOI is PERMISSIVE: the wider the
    band, the easier it is to declare two conditions equivalent. Declaring
    "generic AI is as good as traditional teaching" with a band of +/-0.30 is a
    much weaker statement than it sounds.

The second use is the one that needs defending, and the thesis does not defend
it: it justifies 0.30 as "about a third of a standard year's growth" and stops.
That justification is on the wrong metric and in the wrong direction -- it says
what 0.30 is, not why an effect smaller than 0.30 would not matter.

The argument is in ai-doc/sesoi-equivalence-bound.md. This module supplies the
numbers it turns on:

  1. `equivalence_operating_characteristics` -- for each candidate bound, how
     often equivalence is declared when the truth is exactly zero, and how often
     it is declared when the truth is a real effect that Kraft (2020) would call
     LARGE on standardized outcomes. The second is the false-equivalence rate,
     and it is the number the thesis owes its reader.
  2. `classes_needed` -- how many classes each bound would require to keep the
     declaration rate at 0.80 under a true null.

Run:  python sesoi.py       -> out/sesoi.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy import stats

from power import simulate_trial, contrast_test
from console import use_utf8

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)

ALPHA = 0.05
TAU2 = 0.03

# Candidate bounds. 0.30 is the thesis's; the others come from the benchmark
# literature and are argued for in the note.
BOUNDS = (0.15, 0.20, 0.25, 0.30, 0.40)

# True G-K differences to simulate under. 0.00 is the null the test is supposed
# to detect; the rest are effects that would matter if they were real.
TRUTHS = (0.00, 0.10, 0.15, 0.20, 0.25)


def _tost(est: float, se: float, dfree: int, bound: float) -> bool:
    p_lo = float(stats.t.sf((est + bound) / se, dfree))
    p_hi = float(stats.t.cdf((est - bound) / se, dfree))
    return max(p_lo, p_hi) < ALPHA


def equivalence_operating_characteristics(n_classes: int = 18,
                                          n_sim: int = 3000,
                                          seed: int = 515) -> dict:
    """Declaration rate for every (bound, true effect) pair.

    The diagonal reading is the one that matters. Along a row (fixed bound),
    the rate should fall away fast as the true effect grows; if it does not,
    the bound is wide enough to swallow effects the study should not be calling
    equivalent.
    """
    rng = np.random.default_rng(seed)
    grid: dict[str, dict[str, float]] = {}
    for truth in TRUTHS:
        row: dict[str, float] = {}
        counts = {b: 0 for b in BOUNDS}
        for _ in range(n_sim):
            y, cls = simulate_trial(
                n_classes, {"K": 0.0, "G": truth, "A": 0.34}, TAU2, rng)
            est, se, dfree = contrast_test(y, cls, "G", "K")
            for b in BOUNDS:
                if _tost(est, se, dfree, b):
                    counts[b] += 1
        for b in BOUNDS:
            row[f"{b:.2f}"] = round(counts[b] / n_sim, 3)
        grid[f"{truth:.2f}"] = row
    return grid


def classes_needed(bound: float, target: float = 0.80, n_sim: int = 1200,
                   seed: int = 707, grid=(12, 18, 24, 36, 48, 72, 96)) -> dict:
    """Smallest J at which a TRUE null is declared equivalent `target` of the time."""
    rng = np.random.default_rng(seed)
    out = []
    for J in grid:
        hits = 0
        for _ in range(n_sim):
            y, cls = simulate_trial(
                J, {"K": 0.0, "G": 0.0, "A": 0.34}, TAU2, rng)
            est, se, dfree = contrast_test(y, cls, "G", "K")
            hits += _tost(est, se, dfree, bound)
        out.append({"n_classes": J, "declaration_rate": round(hits / n_sim, 3)})
        if hits / n_sim >= target:
            break
    reached = next((r["n_classes"] for r in out
                    if r["declaration_rate"] >= target), None)
    return {"bound": bound, "curve": out, "classes_for_80pct": reached,
            "reached": reached is not None}


def main() -> int:
    grid = equivalence_operating_characteristics()
    needed = {f"{b:.2f}": classes_needed(b) for b in (0.15, 0.20, 0.30)}

    # The quantity the thesis owes its reader: with the planned bound and the
    # planned sample, how often is a genuinely large effect (by Kraft's
    # standardized-outcome benchmark, >= 0.20) waved through as equivalence?
    false_equiv = {
        "truth_0.20_bound_0.30": grid["0.20"]["0.30"],
        "truth_0.25_bound_0.30": grid["0.25"]["0.30"],
        "truth_0.20_bound_0.20": grid["0.20"]["0.20"],
        "truth_0.15_bound_0.30": grid["0.15"]["0.30"],
    }

    res = {
        "question": ("SESOI = 0.30 is conservative for the superiority test "
                     "and permissive for the equivalence test. How permissive?"),
        "design": dict(n_classes=18, tau2_ct=TAU2, alpha=ALPHA,
                       bounds=list(BOUNDS), truths=list(TRUTHS)),
        "declaration_rate": grid,
        "false_equivalence": false_equiv,
        "classes_needed_for_80pct_under_true_null": {
            k: v["classes_for_80pct"] for k, v in needed.items()},
        "classes_curves": needed,
        "reading": (
            "Read the row for a true effect of 0.20 -- an effect Kraft (2020) "
            "calls LARGE for standardized achievement outcomes. If the rate at "
            "bound 0.30 is not near zero, the planned equivalence test can "
            "certify as 'no difference' an effect that the field would "
            "consider substantial. Narrowing the bound fixes that and costs "
            "classes; the second table says how many."),
    }
    (OUT / "sesoi.json").write_text(
        json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    use_utf8()
    raise SystemExit(main())
