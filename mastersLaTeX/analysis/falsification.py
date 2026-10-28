"""falsification.py -- the negative controls, and how large they have to be.

The interpretive problem
------------------------
The design shows that pupils score higher after the adaptive lesson than after
the traditional one. It does not, on its own, show that they LEARNED more.

At least three alternatives produce the same contrast without any learning:

  * **Demand characteristics.** Pupils know which lesson was the "special" one,
    and the researcher wants it to win. Trying harder on the test that follows
    it raises every score on that test.
  * **Differential test-taking effort.** The adaptive lesson is less tiring --
    the assistant carries part of the load -- so pupils arrive at the test with
    more left. That raises scores on anything, including material never taught.
  * **State affect.** A lesson pupils enjoyed leaves them in a better mood, and
    mood moves performance on unrelated cognitive tasks.

All three are indistinguishable from learning in the primary contrast, and all
three predict something learning does NOT: an effect on material the lesson
never covered.

The controls
------------
So the design pre-specifies two outcomes on which the condition must have NO
effect, and treats a detected effect as evidence against the learning
interpretation rather than as a curiosity:

  1. **Placebo items.** `n_placebo` items on a topic outside the study's three,
     administered inside the same immediate test. Nothing in any lesson touches
     them. Learning predicts zero; all three alternatives predict a shift.
  2. **Invariant trait.** The matrix-reasoning short form, re-administered at
     the delayed session. A 90-minute lesson cannot move fluid reasoning. An
     effect here means something is wrong with the assignment, the analysis or
     the administration, not with the pupils.

Why the test is an EQUIVALENCE test
-----------------------------------
"We looked and found nothing" is not a negative control; it is a small sample.
A negative control is only informative if it can *rule out* an effect of a size
that would matter, so the analysis is TOST against a bound, not a null-hypothesis
test -- and the honest question is what bound a few extra items can actually
buy. `control_precision()` answers it, and the answer decides how many items to
print: with too few the control cannot exclude anything worth excluding, and
printing it would buy reassurance rather than evidence.

Run:  python falsification.py       -> out/falsification.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from dgp import Params, simulate
from console import use_utf8

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)

# Pre-specified equivalence bound for the negative controls, set equal to the
# SESOI of the primary outcome rather than tighter.
#
# The temptation is to pick something small and strict. Resisting it is the
# honest move, because the bound has to be one the design can actually reach:
# with 18 classes the 90 % interval on the control is about +/- 0.14 wide, so a
# bound of 0.20 would leave only +/- 0.05 of slack and would fail to declare
# equivalence roughly half the time WHEN THE TRUTH IS EXACTLY ZERO. A control
# that cries wolf on half of all clean studies is not a control.
#
# At 0.30 the claim the control supports is precise and worth having: a
# non-learning channel large enough to account for the WHOLE primary effect is
# excluded. One large enough to account for part of it is not, and the thesis
# says so rather than implying otherwise.
CONTROL_BOUND = 0.30
ALPHA = 0.05


# ---------------------------------------------------------------------------
def simulate_controls(p: Params, leak: float = 0.0, n_placebo: int = 6,
                      seed: int | None = None,
                      test_retest: float = 0.85) -> pd.DataFrame:
    """Add the two negative-control outcomes to a simulated study.

    `leak` is the size, in theta units, of a non-learning advantage that the
    adaptive condition confers on everything the pupil does that day -- the
    demand/effort/affect channel. At leak = 0 the controls are what the design
    assumes; at leak > 0 they are what the design is built to detect.

    Note what the leak does and does not touch. It moves the placebo items,
    because they are answered in the same sitting and the same state of mind. It
    does NOT move the matrix trait, which is re-administered three weeks later:
    that control is there for assignment and administration faults, not for
    same-day motivation, and conflating the two would make a passed control mean
    less than it appears to.
    """
    rng = np.random.default_rng(p.seed + 977 if seed is None else seed)
    df = simulate(p, item_level=False)["long"].copy()
    bump = {"K": 0.0, "G": leak * 0.5, "A": leak}

    # Placebo: never taught, so ability on it is the pupil's general level plus
    # noise -- plus whatever the leak adds on the day.
    base = 0.45 * df["theta_pre"] + 0.20 * df["gf"]
    item_noise = 1.0 / np.sqrt(max(n_placebo, 1))     # shorter test, noisier score
    df["placebo"] = (base
                     + df["cond"].map(bump).astype(float)
                     + rng.normal(0.0, 0.85 + item_noise, len(df)))

    # Invariant trait re-administered at week 6.
    #
    # It is measured ONCE per pupil, not once per period, and that changes what
    # can be asked of it. A within-pupil contrast across conditions on a
    # quantity measured once is mean-zero by construction: it clears any
    # equivalence test trivially and tests nothing. (The first version of this
    # module drew it per row and did exactly that.)
    #
    # The estimable contrast is BETWEEN pupils, keyed on the condition of the
    # LAST period before the delayed session -- which differs by sequence, and
    # sequence is randomised. That is a real comparison, it uses the design's
    # own randomisation, and unlike the within-pupil version it is sensitive to
    # how reliably the trait is measured.
    per_pupil = (df.drop_duplicates("student")
                   .set_index("student")["gf"])
    retest = (test_retest * per_pupil
              + rng.normal(0.0, np.sqrt(1 - test_retest ** 2), len(per_pupil)))
    df["gf_retest"] = df["student"].map(retest)

    # The analysed quantity is the CHANGE, not the level, and the difference is
    # not cosmetic. Between pupils, g_f has a standard deviation of about 1 and
    # a class component on top; with eighteen clusters that leaves an interval
    # too wide to fit inside the equivalence band, and the control clears only
    # about half the time even when nothing is wrong. The change T4 - T0 cancels
    # the stable part -- including the class component -- and leaves a residual
    # of sd = sqrt(2(1-rho)). That is the estimator that makes the control
    # usable, and it is available only because the trait is measured twice.
    df["gf_change"] = df["gf_retest"] - df["gf"]

    last = (df.sort_values(["student", "period"])
              .groupby("student")["cond"].last())
    df["last_cond"] = df["student"].map(last)
    return df


def _within_student_contrast(df: pd.DataFrame, value: str,
                             a: str, b: str) -> dict:
    """Same estimator as the primary analysis, so the comparison is like for like."""
    w = df.pivot_table(index=["student", "klass"], columns="cond", values=value)
    w = w.dropna(subset=[a, b])
    d = (w[a] - w[b]).to_numpy()
    g = w.index.get_level_values("klass").to_numpy()
    n, est = d.size, float(d.mean())
    groups = np.unique(g)
    J = groups.size
    r = d - est
    ssum = np.array([r[g == j].sum() for j in groups])
    var = (J / max(J - 1, 1)) * (ssum ** 2).sum() / n ** 2
    se = float(np.sqrt(var))
    return dict(est=est, se=se, df=J - 1, n=int(n), d=est / d.std(ddof=1))


def tost_control(res: dict, bound: float = CONTROL_BOUND) -> dict:
    """Two one-sided tests against +/- bound, on J-1 degrees of freedom."""
    from scipy import stats
    est, se, dfree = res["est"], res["se"], res["df"]
    if not se > 0:
        # A contrast with no variance is not a precise measurement, it is a
        # degenerate one: the usual cause is taking a within-pupil contrast on
        # a quantity measured once per pupil, which is identically zero. Saying
        # so beats dividing by zero, and beats returning "equivalent".
        raise ValueError(
            "contrast has zero standard error -- the quantity does not vary "
            "within the contrasted units. A trait measured once per pupil "
            "admits no within-pupil condition contrast; use the between-pupil "
            "estimator keyed on the last period instead.")
    p_lo = float(stats.t.sf((est + bound) / se, dfree))
    p_hi = float(stats.t.cdf((est - bound) / se, dfree))
    tcrit = float(stats.t.ppf(1 - ALPHA, dfree))
    p = max(p_lo, p_hi)
    return dict(bound=bound, p_tost=p, passes=bool(p < ALPHA),
                ci90=[round(est - tcrit * se, 4), round(est + tcrit * se, 4)],
                est=round(est, 4), se=round(se, 4))


# ---------------------------------------------------------------------------
def control_precision(n_placebo_grid=(3, 6, 9, 12, 16), n_classes: int = 18,
                      n_sim: int = 400) -> list[dict]:
    """What bound can a negative control of each length actually exclude?

    This is the calculation that decides whether the control is worth printing.
    A control that can only exclude d > 0.6 does not distinguish learning from
    motivation for any effect this study could find, and including it would buy
    the appearance of rigour instead of the thing.
    """
    rows = []
    for k in n_placebo_grid:
        halfwidths, passes = [], 0
        for s in range(n_sim):
            p = Params(n_classes=n_classes, seed=4000 + s)
            df = simulate_controls(p, leak=0.0, n_placebo=k, seed=9000 + s)
            r = _within_student_contrast(df, "placebo", "A", "K")
            t = tost_control(r)
            halfwidths.append((t["ci90"][1] - t["ci90"][0]) / 2)
            passes += t["passes"]
        rows.append({
            "n_placebo_items": k,
            "median_halfwidth": round(float(np.median(halfwidths)), 4),
            "excludes_effects_above": round(float(np.median(halfwidths)), 2),
            "pass_rate_when_truly_null": round(passes / n_sim, 3),
        })
    return rows


def control_power(leaks=(0.0, 0.10, 0.20, 0.30, 0.45), n_placebo: int = 9,
                  n_classes: int = 18, n_sim: int = 400) -> list[dict]:
    """How often the control CATCHES a leak of each size.

    Two numbers per row and they answer different questions. `detects` is the
    probability of a significant effect on the control -- the alarm going off.
    `passes_equivalence` is the probability of declaring the control clean. A
    good control has the first rising and the second falling as the leak grows;
    if `passes_equivalence` stayed high at a large leak, a passed control would
    mean nothing.
    """
    from scipy import stats
    rows = []
    for leak in leaks:
        detects = passes = 0
        ests = []
        for s in range(n_sim):
            p = Params(n_classes=n_classes, seed=5000 + s)
            df = simulate_controls(p, leak=leak, n_placebo=n_placebo,
                                   seed=11000 + s)
            r = _within_student_contrast(df, "placebo", "A", "K")
            ests.append(r["est"])
            t_stat = r["est"] / r["se"]
            if abs(t_stat) > stats.t.ppf(1 - ALPHA / 2, r["df"]):
                detects += 1
            if tost_control(r)["passes"]:
                passes += 1
        rows.append({
            "leak": leak,
            "mean_estimate": round(float(np.mean(ests)), 4),
            "detects": round(detects / n_sim, 3),
            "passes_equivalence": round(passes / n_sim, 3),
        })
    return rows


def _between_pupil_contrast(df: pd.DataFrame, value: str, group: str,
                            a: str, b: str) -> dict:
    """Difference in means between pupils, cluster-robust over classes.

    One row per pupil: the value is a trait measured once, so it must be
    de-duplicated before anything else or every pupil counts three times and
    the standard error comes out a factor of sqrt(3) too small.
    """
    d = df.drop_duplicates("student")
    d = d[d[group].isin([a, b])].dropna(subset=[value])
    y = d[value].to_numpy(float)
    x = (d[group] == a).astype(float).to_numpy()
    g = d["klass"].to_numpy()
    X = np.column_stack([np.ones(len(d)), x])
    XtX_inv = np.linalg.pinv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    u = y - X @ beta
    uniq = np.unique(g)
    meat = np.zeros((2, 2))
    for j in uniq:
        m = g == j
        s = X[m].T @ u[m]
        meat += np.outer(s, s)
    J = len(uniq)
    V = (J / max(J - 1, 1)) * XtX_inv @ meat @ XtX_inv
    se = float(np.sqrt(max(V[1, 1], 1e-12)))
    return dict(est=float(beta[1]), se=se, df=J - 1, n=int(len(d)),
                d=float(beta[1] / y.std(ddof=1)))


def trait_control(n_classes: int = 18, n_sim: int = 200,
                  test_retest: float = 0.85) -> dict:
    """The invariant trait: it must be clean, and it must be ABLE to clear.

    Nothing in the model moves fluid reasoning, so a failure here is a fault in
    the analysis or the assignment rather than a finding. That is what makes it
    worth running: it checks the machinery, and the machinery produces every
    other number.

    The contrast is between pupils, on the condition of the pupil's LAST period
    before the delayed session. A trait is measured once, so no within-pupil
    condition contrast exists for it; sequence randomisation is what makes the
    between-pupil comparison legitimate.

    `test_retest` is the reliability of the instrument, and it matters in a
    direction that is easy to get backwards: a poorly measured control does not
    raise false alarms, it widens the interval until the control can never be
    certified clean.
    """
    passes, false_alarms = 0, 0
    from scipy import stats
    for s in range(n_sim):
        p = Params(n_classes=n_classes, seed=6000 + s)
        df = simulate_controls(p, leak=0.30, n_placebo=9, seed=12000 + s,
                               test_retest=test_retest)
        r = _between_pupil_contrast(df, "gf_change", "last_cond", "A", "K")
        passes += tost_control(r)["passes"]
        if abs(r["est"] / r["se"]) > stats.t.ppf(1 - ALPHA / 2, r["df"]):
            false_alarms += 1
    return {
        "note": ("between-pupil, keyed on the condition of the last period; a "
                 "trait measured once admits no within-pupil contrast. Run "
                 "WITH a same-day leak of 0.30 present: the trait must stay "
                 "clean anyway, because it is measured three weeks later."),
        "test_retest_reliability": test_retest,
        "passes_equivalence": round(passes / n_sim, 3),
        "false_alarm_rate": round(false_alarms / n_sim, 3),
        "nominal_alpha": ALPHA,
    }


def trait_control_by_reliability(levels=(0.60, 0.70, 0.80, 0.85, 0.92),
                                 n_sim: int = 150) -> list[dict]:
    """How good the instrument has to be for the control to be usable at all."""
    return [{"test_retest": r,
             "passes_equivalence": trait_control(n_sim=n_sim,
                                                 test_retest=r)["passes_equivalence"]}
            for r in levels]


# ---------------------------------------------------------------------------
def main() -> int:
    precision = control_precision()

    # How many placebo items to print. Returns diminish fast, and the reason is
    # worth stating: the contrast is within-pupil, so the residual is the
    # pupil-by-occasion component and item sampling is only one part of it.
    # Lengthening the test shrinks that one part. Choose the shortest length
    # whose half-width is within 0.01 of the best any length achieves; the rest
    # of the lesson is better spent on the outcome that matters.
    best = min(r["median_halfwidth"] for r in precision)
    chosen = next(r["n_placebo_items"] for r in precision
                  if r["median_halfwidth"] <= best + 0.01)
    longest = max(precision, key=lambda r: r["n_placebo_items"])
    shortest = min(precision, key=lambda r: r["n_placebo_items"])
    power = control_power(n_placebo=chosen)

    res = {
        "design": dict(bound=CONTROL_BOUND, alpha=ALPHA, n_classes=18,
                       chosen_n_placebo=chosen),
        "precision_by_length": precision,
        "diminishing_returns_in_length": {
            "halfwidth_at_%d_items" % shortest["n_placebo_items"]:
                shortest["median_halfwidth"],
            "halfwidth_at_%d_items" % chosen: next(
                r["median_halfwidth"] for r in precision
                if r["n_placebo_items"] == chosen),
            "halfwidth_at_%d_items" % longest["n_placebo_items"]:
                longest["median_halfwidth"],
            "ratio_shortest_to_longest": round(shortest["median_halfwidth"]
                                               / longest["median_halfwidth"], 3),
            "why": ("the contrast is within-pupil, so the residual is the "
                    "pupil-by-occasion component and item sampling is only one "
                    "part of it; more items shrink that one part"),
            "practical": ("nearly four fifths of the reachable precision is "
                          "there by the ninth item, and the remaining items "
                          "cost lesson time that the primary outcome needs"),
        },
        "power_against_leak": power,
        "trait_control": trait_control(),
        "trait_control_by_reliability": trait_control_by_reliability(),
        "decision_rule": (
            "Both controls are tested for equivalence to zero against a bound "
            "of %.2f. If either fails, the primary contrast is reported with "
            "the non-learning explanation stated alongside it and the "
            "mechanism claim is withdrawn, because a same-day advantage on "
            "untaught material is not learning." % CONTROL_BOUND),
        "what_it_cannot_do": (
            "The bound the design can reach excludes a non-learning channel "
            "large enough to explain the whole primary effect, not one large "
            "enough to explain part of it. Reaching a bound of 0.15 would need "
            "roughly four times the classes, which is not a trade this study "
            "can make."),
    }
    (OUT / "falsification.json").write_text(
        json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res, indent=2, ensure_ascii=False))

    ok = (chosen is not None
          and res["trait_control"]["passes_equivalence"] >= 0.80
          and power[0]["passes_equivalence"] >= 0.80          # clean when null
          and power[-1]["detects"] >= 0.70)                   # alarms on a big leak
    print("\n" + ("negative controls are usable" if ok
                  else "NEGATIVE CONTROLS ARE NOT INFORMATIVE AT THIS SIZE"))
    return 0 if ok else 1


if __name__ == "__main__":
    use_utf8()
    raise SystemExit(main())
