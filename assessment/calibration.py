"""calibration.py -- how well a pupil knows whether they answered correctly.

Chapter 5 of the thesis lists self-estimation among the measures: "ako presne
žiak odhaduje, či odpovedal správne". The runner collects the raw material -- a
0-100 confidence after every closed item -- and until now the numbers that turn
it into a measure existed only in the numpy analysis pipeline, which a school
cannot run. This module computes them with the standard library, per pupil and
sitting, from scored responses:

  bias                 mean confidence - proportion correct. Positive is
                       overconfidence. The quantity hypothesis 3 is about.
  absolute_accuracy    mean |confidence - correctness|; 0 is perfect.
  brier                mean (confidence - correctness)^2; the proper scoring
                       rule, for comparison with the literature.
  gamma                Goodman-Kruskal gamma between confidence and
                       correctness: does the pupil know WHICH answers are right
                       (resolution), independent of their overall level.
  sensitivity          mean confidence on correct minus on incorrect items.

Items with no confidence (open items, questionnaires) or no score are left out,
and every statistic is None -- never zero -- when it cannot be computed: a
pupil who answered everything correctly has no gamma, which is not the same as
a gamma of zero.

Run:  python calibration.py        self-test on planted pupils
"""
from __future__ import annotations

import sys


def pupil_calibration(pairs: list[tuple[float, int]]) -> dict:
    """pairs: (confidence 0-100, correct 0/1) for one pupil and sitting."""
    pairs = [(float(c) / 100.0, int(k)) for c, k in pairs
             if c is not None and k is not None]
    n = len(pairs)
    out = dict(n=n, mean_confidence=None, accuracy=None, bias=None,
               absolute_accuracy=None, brier=None, gamma=None, sensitivity=None)
    if not n:
        return out
    conf = sum(c for c, _ in pairs) / n
    acc = sum(k for _, k in pairs) / n
    out.update(mean_confidence=round(conf, 4), accuracy=round(acc, 4),
               bias=round(conf - acc, 4),
               absolute_accuracy=round(sum(abs(c - k) for c, k in pairs) / n, 4),
               brier=round(sum((c - k) ** 2 for c, k in pairs) / n, 4))
    right = [c for c, k in pairs if k == 1]
    wrong = [c for c, k in pairs if k == 0]
    if right and wrong:
        out["sensitivity"] = round(sum(right) / len(right) - sum(wrong) / len(wrong), 4)
    out["gamma"] = goodman_kruskal_gamma([c for c, _ in pairs], [k for _, k in pairs])
    return out


def goodman_kruskal_gamma(x: list[float], y: list[float]) -> float | None:
    conc = disc = 0
    for i in range(len(x)):
        for j in range(i + 1, len(x)):
            dx, dy = x[i] - x[j], y[i] - y[j]
            if dx * dy > 0:
                conc += 1
            elif dx * dy < 0:
                disc += 1
    if conc + disc == 0:
        return None
    return round((conc - disc) / (conc + disc), 4)


# ===========================================================================
def self_test() -> list[str]:
    fails = []
    # perfectly calibrated and perfectly resolving
    p = pupil_calibration([(100, 1), (100, 1), (0, 0), (0, 0)])
    if p["bias"] != 0 or p["absolute_accuracy"] != 0 or p["gamma"] != 1.0:
        fails.append(f"perfect pupil not perfect: {p}")
    # the overconfident pupil hypothesis 3 is about
    p = pupil_calibration([(90, 1), (90, 0), (85, 0), (95, 0)])
    if not p["bias"] > 0.5:
        fails.append(f"overconfidence not detected: {p}")
    # confidence that runs against correctness
    p = pupil_calibration([(10, 1), (20, 1), (80, 0), (90, 0)])
    if p["gamma"] != -1.0:
        fails.append(f"inverted resolution not detected: {p}")
    # all correct: no gamma, no sensitivity -- None, not 0
    p = pupil_calibration([(70, 1), (80, 1), (90, 1)])
    if p["gamma"] is not None or p["sensitivity"] is not None:
        fails.append("gamma or sensitivity invented for a pupil with no errors")
    # no usable items
    if pupil_calibration([(None, 1), (50, None)])["n"] != 0:
        fails.append("items without confidence or score were counted")
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
    print("calibration self-test: " + ("ok" if not fails else f"{len(fails)} failures"))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
