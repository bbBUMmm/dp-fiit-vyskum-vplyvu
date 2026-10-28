"""power.py -- Monte-Carlo power analysis for the 3 x 3 cross-over classroom trial.

Why a dedicated simulation instead of a closed-form formula
-----------------------------------------------------------
Three features of the design have no convenient analytic power formula:

1. The condition contrast is estimated WITHIN student (every student meets K, G
   and A exactly once).  The class-level intercept u_c and the student-level
   intercept u_i both cancel in the within-student difference, so the usual
   cluster-randomisation design effect  1 + (m-1)*ICC  does NOT apply to the
   treatment contrast.  Power is therefore driven by the number of STUDENTS,
   not by the number of classes -- the decisive practical advantage of the
   cross-over over a parallel cluster-randomised trial.

2. That advantage is bounded by treatment-effect heterogeneity across classes
   (a random class x condition component, tau2_ct).  As soon as tau2_ct > 0 the
   number of CLASSES becomes the binding constraint (Raudenbush, 1997).  The
   simulation therefore sweeps tau2_ct instead of assuming it away.

3. The primary claim about generic AI is an ABSENCE of benefit.  That is tested
   by two one-sided tests (TOST; Lakens, 2017) against a smallest effect size of
   interest, and equivalence testing needs materially more power than the
   corresponding superiority test.

Inference matches the pre-registered analysis plan: the within-student
difference is averaged with a cluster-robust variance estimator over classes and
referred to a t distribution on J - 1 degrees of freedom (J = number of classes),
which is the conservative small-sample choice for few clusters.

Usage:  python power.py            (writes out/power_grid.csv, out/power.tex)
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from console import use_utf8

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)

SEQUENCES = [("K", "G", "A"), ("K", "A", "G"), ("G", "K", "A"),
             ("G", "A", "K"), ("A", "K", "G"), ("A", "G", "K")]
COND_IDX = {"K": 0, "G": 1, "A": 2}

# --- fixed design assumptions -------------------------------------------------
ICC_CLASS = 0.12        # Hedges and Hedberg (2007)
R_WITHIN = 0.55         # correlation of two occasions of the same student
CLASS_SIZE = 22
ATTRITION = 0.12        # by the delayed test (week 6)
ALPHA = 0.05
SESOI = 0.30            # smallest effect size of interest, in SD units


def _components(tau2_ct: float) -> tuple[float, float, float]:
    """Return (sd_class, sd_student, sd_resid) for unit total variance."""
    v_class = ICC_CLASS
    v_stud = max(R_WITHIN - ICC_CLASS, 1e-6)
    v_res = max(1.0 - R_WITHIN - tau2_ct, 1e-6)
    return np.sqrt(v_class), np.sqrt(v_stud), np.sqrt(v_res)


def simulate_trial(n_classes: int, effects: dict, tau2_ct: float,
                   rng: np.random.Generator, period_eff=(0.0, 0.10, 0.16)):
    """Return a (n_students, 3) matrix of outcomes indexed by CONDITION, plus class id."""
    sd_c, sd_s, sd_e = _components(tau2_ct)
    ys, cls = [], []
    for c in range(n_classes):
        seq = SEQUENCES[c % 6]
        n = CLASS_SIZE
        u_c = rng.normal(0, sd_c)
        # random class x condition effect: the class-specific deviation of each
        # condition's effect (fidelity, teacher, room, time of day)
        v_ct = rng.normal(0, np.sqrt(tau2_ct), 3) if tau2_ct > 0 else np.zeros(3)
        u_i = rng.normal(0, sd_s, n)
        y = np.full((n, 3), np.nan)
        for p, cond in enumerate(seq):
            k = COND_IDX[cond]
            y[:, k] = (u_c + u_i + effects[cond] + v_ct[k] + period_eff[p]
                       + rng.normal(0, sd_e, n))
        drop = rng.random(n) < ATTRITION
        y[drop, :] = np.nan
        ys.append(y)
        cls.append(np.full(n, c))
    return np.vstack(ys), np.concatenate(cls)


def contrast_test(y: np.ndarray, cls: np.ndarray, a: str, b: str):
    """Within-student contrast a - b with a cluster-robust (CR1) variance over classes.

    Returns (estimate, se, df).  Clusters are classes; df = J - 1.
    """
    d = y[:, COND_IDX[a]] - y[:, COND_IDX[b]]
    ok = ~np.isnan(d)
    d, g = d[ok], cls[ok]
    n = d.size
    est = d.mean()
    groups = np.unique(g)
    J = groups.size
    # CR1 sandwich for the sample mean: sum of squared cluster sums / n^2
    r = d - est
    s = np.array([r[g == j].sum() for j in groups])
    correction = J / max(J - 1, 1) * (n - 1) / max(n - 1, 1)
    var = correction * (s ** 2).sum() / n ** 2
    return est, np.sqrt(max(var, 1e-12)), J - 1


def p_superiority(est, se, df, direction=+1):
    t = est / se
    return stats.t.sf(direction * t, df)          # one-sided


def p_tost(est, se, df, sesoi=SESOI):
    """Two one-sided tests: reject non-equivalence if BOTH are significant."""
    t_lo = (est + sesoi) / se
    t_hi = (est - sesoi) / se
    return max(stats.t.sf(t_lo, df), stats.t.cdf(t_hi, df))


def holm(pvals: dict) -> dict:
    """Holm-Bonferroni adjusted p-values for the confirmatory family."""
    keys = sorted(pvals, key=lambda k: pvals[k])
    m = len(keys)
    adj, running = {}, 0.0
    for i, k in enumerate(keys):
        running = max(running, (m - i) * pvals[k])
        adj[k] = min(running, 1.0)
    return adj


def run_cell(n_classes: int, tau2_ct: float, effects: dict, n_rep: int, seed: int):
    rng = np.random.default_rng(seed)
    hit = dict(AK=0, AG=0, GK_equiv=0, GK_super=0, family=0)
    for _ in range(n_rep):
        y, cls = simulate_trial(n_classes, effects, tau2_ct, rng)
        e_ak, s_ak, df = contrast_test(y, cls, "A", "K")
        e_ag, s_ag, _ = contrast_test(y, cls, "A", "G")
        e_gk, s_gk, _ = contrast_test(y, cls, "G", "K")
        p_ak = p_superiority(e_ak, s_ak, df)
        p_ag = p_superiority(e_ag, s_ag, df)
        p_eq = p_tost(e_gk, s_gk, df)
        p_gk = 2 * stats.t.sf(abs(e_gk / s_gk), df)
        hit["AK"] += p_ak < ALPHA / 2
        hit["AG"] += p_ag < ALPHA / 2
        hit["GK_equiv"] += p_eq < ALPHA
        hit["GK_super"] += p_gk < ALPHA
        # The confirmatory family is exactly the three claims that randomisation
        # identifies and that can fail: A beats K, G is equivalent to K, and A
        # beats G on durable retention. "Family" counts replications in which
        # ALL THREE survive Holm -- the probability of the complete result the
        # thesis argues for, not of its most convenient part.
        adj = holm({"AK": p_ak, "AG": p_ag, "GKeq": p_eq})
        hit["family"] += ((adj["AK"] < ALPHA / 2) and (adj["AG"] < ALPHA / 2)
                          and (adj["GKeq"] < ALPHA))
    return {k: v / n_rep for k, v in hit.items()}


def power_mechanism(n_rep: int = 1000, b_true: float = 0.22,
                    a_true: float = 1.45, seed: int = 4242) -> list[dict]:
    """Power and precision for the mechanism estimate (the PEQI pathway).

    Two questions, not one. *Power* asks whether the instrumental-variable
    estimate of the PEQI pathway will be distinguishable from zero. *Precision*
    asks whether it will be narrow enough to be worth anything: an interval
    from 0.02 to 0.60 excludes zero and still tells a school nothing, so the
    pre-specified criterion is a 95 % interval no wider than 0.20 -- roughly
    the difference between "prompt quality matters a little" and "prompt
    quality matters as much as the lesson itself".

    Only the two AI conditions contribute, so the effective sample is two
    thirds of the students; the instrument is the randomised pedagogical layer.
    """
    rng = np.random.default_rng(seed)
    sd_c, sd_s, sd_e = _components(0.03)
    rows = []
    for n_classes in (9, 12, 15, 18, 24):
        sig = prec = 0
        ses = []
        for _ in range(n_rep):
            # two AI observations per student: one under G, one under A
            n = n_classes * CLASS_SIZE
            cls = np.repeat(np.arange(n_classes), CLASS_SIZE)
            u_c = rng.normal(0, sd_c, n_classes)[cls]
            u_i = rng.normal(0, sd_s, n)
            m_g = rng.normal(0, 1, n)
            m_a = m_g * 0.0 + a_true + rng.normal(0, 1, n)   # first stage
            y_g = u_c + u_i + b_true * m_g + rng.normal(0, sd_e, n)
            y_a = u_c + u_i + b_true * m_a + rng.normal(0, sd_e, n)
            keep = rng.random(n) > ATTRITION
            dm = (m_a - m_g)[keep]
            dy = (y_a - y_g)[keep]
            g = cls[keep]
            # Wald ratio on within-student differences, cluster-robust by class
            a_hat, y_hat = dm.mean(), dy.mean()
            groups = np.unique(g)
            J, nn = groups.size, dm.size
            r = dy - y_hat
            s = np.array([r[g == j].sum() for j in groups])
            se_y = np.sqrt((J / max(J - 1, 1)) * (s ** 2).sum() / nn ** 2)
            est = y_hat / a_hat
            se = se_y / abs(a_hat)
            t = est / se
            crit = stats.t.ppf(1 - ALPHA / 2, J - 1)
            sig += abs(t) > crit
            width = 2 * crit * se
            prec += width < 0.20
            ses.append(se)
        rows.append(dict(n_classes=n_classes, n_students=n_classes * CLASS_SIZE,
                         power_iv=sig / n_rep, power_precision=prec / n_rep,
                         median_se=float(np.median(ses)), b_true=b_true))
    return rows


def main(n_rep: int = 3000):
    # effects in SD units, anchored on the literature (see dgp.py)
    effects = {"K": 0.0, "G": -0.05, "A": 0.30}
    grid = []
    for n_classes, tau2 in itertools.product([6, 9, 12, 15, 18, 24], [0.0, 0.015, 0.03, 0.06]):
        res = run_cell(n_classes, tau2, effects, n_rep, seed=1000 + n_classes * 7 + int(tau2 * 1000))
        n_stud = n_classes * CLASS_SIZE
        grid.append(dict(n_classes=n_classes, n_students=n_stud,
                         n_analysed=int(round(n_stud * (1 - ATTRITION))),
                         tau2_ct=tau2, **res))
        print(f"J={n_classes:3d} N={n_stud:4d} tau2={tau2:.3f} | "
              f"A-K {res['AK']:.3f}  A-G {res['AG']:.3f}  "
              f"G=K(TOST) {res['GK_equiv']:.3f}  family {res['family']:.3f}")
    df = pd.DataFrame(grid)
    df.to_csv(OUT / "power_grid.csv", index=False)

    # ---- sensitivity: which true effect can we detect at 80 % with J = 12? ---
    sens = []
    for d in np.arange(0.10, 0.65, 0.05):
        r = run_cell(12, 0.03, {"K": 0.0, "G": -0.05, "A": float(d)},
                     n_rep, seed=777 + int(d * 100))
        sens.append(dict(d=round(float(d), 2), power_AK=r["AK"]))
        print(f"  d={d:.2f} -> power(A-K) = {r['AK']:.3f}")
    pd.DataFrame(sens).to_csv(OUT / "power_sensitivity.csv", index=False)

    # ---- equivalence: power to declare G == K as a function of the true delta
    eqv = []
    for d in [-0.25, -0.20, -0.15, -0.10, -0.05, 0.0, 0.05]:
        r = run_cell(12, 0.03, {"K": 0.0, "G": float(d), "A": 0.30},
                     n_rep, seed=555 + int(abs(d) * 100))
        eqv.append(dict(true_delta_GK=round(float(d), 2), power_equiv=r["GK_equiv"],
                        power_super=r["GK_super"]))
        print(f"  true G-K={d:+.2f} -> P(declare equivalence)={r['GK_equiv']:.3f}"
              f"  P(declare difference)={r['GK_super']:.3f}")
    pd.DataFrame(eqv).to_csv(OUT / "power_equivalence.csv", index=False)

    # ---- mechanism: can the PEQI pathway be estimated precisely enough? ----
    mech = power_mechanism(n_rep=max(n_rep // 3, 400))
    pd.DataFrame(mech).to_csv(OUT / "power_mechanism.csv", index=False)
    for row in mech:
        print(f"  J={row['n_classes']:3d}  P(IV significant)={row['power_iv']:.3f}  "
              f"median SE={row['median_se']:.3f}  "
              f"P(CI width < 0.20)={row['power_precision']:.3f}")

    summary = dict(n_rep=n_rep, alpha=ALPHA, sesoi=SESOI, icc_class=ICC_CLASS,
                   r_within=R_WITHIN, class_size=CLASS_SIZE, attrition=ATTRITION,
                   effects=effects,
                   confirmatory_family=["A>K delayed", "A>G delayed",
                                        "G==K delayed (TOST)"])
    (OUT / "power_settings.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\nwritten:", OUT)


if __name__ == "__main__":
    use_utf8()
    main()
