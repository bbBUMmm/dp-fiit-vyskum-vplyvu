"""pipeline.py -- the complete pre-registered analysis, executed end-to-end.

The point of this file is falsifiability of the *method*, not of the hypotheses:
it is written and frozen BEFORE data collection, run against data simulated from
a known ground truth (dgp.py), and checked for whether it recovers that truth.
Anything the pipeline cannot recover on simulated data it will not recover on
real data either.

Sections follow the statistical analysis plan (Appendix C of the thesis):

  S0  psychometrics      Rasch calibration, WLE person measures, reliability
  S1  descriptives       per condition, per outcome
  S2  primary model      delayed retention, mixed model on the cross-over
  S3  contrasts          A-K, A-G superiority; G-K equivalence (TOST); Holm
  S4  moderation  (H7)   condition x prior knowledge
  S5  metacognition (H5) calibration bias, absolute accuracy, resolution (gamma)
  S6  dissociation  (H5) condition x outcome-type interaction
  S7  mediation     (H6) PEQI as mediator, Monte-Carlo confidence interval
  S8  load          (H8) Leppink subscales
  S9  robustness         period-1-only parallel-group analysis (carry-over free)

Usage:  python pipeline.py        writes out/results_*.csv and out/results.json
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

import statsmodels.formula.api as smf

from dgp import simulate, Params
from identification import triangulate
from console import use_utf8

warnings.filterwarnings("ignore")
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)
ALPHA = 0.05
SESOI = 0.30


# =============================================================== S0 psychometrics
def rasch_jmle(X: np.ndarray, n_iter: int = 200, tol: float = 1e-6):
    """Joint maximum likelihood Rasch calibration with the standard (L-1)/L bias
    correction on the item difficulties.  Extreme scores are handled by the
    0.3 / L-0.3 score adjustment (Wright and Douglas).  Returns (theta, b, se)."""
    X_all = np.asarray(X, dtype=float)
    present = (~np.isnan(X_all) & (X_all >= 0)).sum(axis=1) > 0
    if not present.all():                       # people who never sat the test
        th, b, se = rasch_jmle(X_all[present], n_iter, tol)
        full_th = np.full(X_all.shape[0], np.nan)
        full_se = np.full(X_all.shape[0], np.nan)
        full_th[present], full_se[present] = th, se
        return full_th, b, full_se

    X = X_all
    mask = ~np.isnan(X) & (X >= 0)
    X = np.where(mask, X, 0.0)
    L = mask.sum(axis=1).astype(float)          # items answered per person
    N = mask.sum(axis=0).astype(float)          # persons per item
    r = (X * mask).sum(axis=1)                  # person raw score
    s = (X * mask).sum(axis=0)                  # item raw score
    r = np.clip(r, 0.3, L - 0.3)
    s = np.clip(s, 0.3, N - 0.3)

    theta = np.log(r / (L - r))
    b = -np.log(s / (N - s))
    b -= b.mean()

    for _ in range(n_iter):
        p = 1.0 / (1.0 + np.exp(-(theta[:, None] - b[None, :])))
        p = np.clip(p, 1e-9, 1 - 1e-9) * mask
        w = p * (1 - p) * mask
        dth = (r - p.sum(axis=1)) / np.maximum(w.sum(axis=1), 1e-9)
        theta_new = theta + np.clip(dth, -1.0, 1.0)
        p = 1.0 / (1.0 + np.exp(-(theta_new[:, None] - b[None, :])))
        p = np.clip(p, 1e-9, 1 - 1e-9) * mask
        w = p * (1 - p) * mask
        db = -(s - p.sum(axis=0)) / np.maximum(w.sum(axis=0), 1e-9)
        b_new = b + np.clip(db, -1.0, 1.0)
        b_new -= b_new.mean()
        if max(np.abs(theta_new - theta).max(), np.abs(b_new - b).max()) < tol:
            theta, b = theta_new, b_new
            break
        theta, b = theta_new, b_new

    n_items = mask.shape[1]
    b *= (n_items - 1) / n_items                     # JMLE bias correction
    p = np.clip(1.0 / (1.0 + np.exp(-(theta[:, None] - b[None, :]))), 1e-9, 1 - 1e-9)
    info = (p * (1 - p) * mask).sum(axis=1)
    se = 1.0 / np.sqrt(np.maximum(info, 1e-9))
    return theta, b, se


def concurrent_calibration(x_imm: np.ndarray, x_del: np.ndarray, n_anchor: int):
    """Place the immediate and the delayed form on ONE scale via common items.

    Without this the two forms are calibrated separately, each is centred on its
    own mean difficulty by construction, and the difference between immediate
    and delayed measures is meaningless -- it would confound forgetting with a
    difference in how hard the two tests happened to be. The whole retention
    claim rests on this step, so it cannot be assumed; it has to be done.

    The two response matrices are stacked into one calibration in which the
    first `n_anchor` columns are the SAME items in both forms. Items that appear
    in only one form are simply not administered to the other occasions, which
    the Rasch likelihood handles as missing by design.

    Returns (theta_imm, theta_del, b_all, se_imm, se_del) with both person
    measures on the common metric.
    """
    xi = np.asarray(x_imm, float)
    xd = np.asarray(x_del, float)
    xd = np.where(xd < 0, np.nan, xd)
    n, k_i, k_d = xi.shape[0], xi.shape[1], xd.shape[1]
    k_unique = k_i + (k_d - n_anchor)

    stacked = np.full((2 * n, k_unique), np.nan)
    stacked[:n, :k_i] = xi                                    # immediate occasions
    stacked[n:, :n_anchor] = xd[:, :n_anchor]                 # shared anchors
    stacked[n:, k_i:] = xd[:, n_anchor:]                      # delayed-only items

    theta, b, se = rasch_jmle(stacked)
    return theta[:n], theta[n:], b, se[:n], se[n:]


def item_fit(X: np.ndarray, theta: np.ndarray, b: np.ndarray):
    """Infit and outfit mean-square for every item.

    The analysis plan says items outside 0.7--1.3 are dropped. That rule is
    empty unless the statistic is actually computed, so here it is. Outfit is
    the unweighted mean of squared standardised residuals and is sensitive to
    lucky guesses by weak pupils; infit weights by information and is sensitive
    to misfit among pupils the item is actually targeted at.
    """
    X = np.asarray(X, float)
    X = np.where(X < 0, np.nan, X)
    ok = np.isfinite(theta)
    X, th = X[ok], theta[ok]
    P = 1.0 / (1.0 + np.exp(-(th[:, None] - b[None, :])))
    W = P * (1 - P)
    mask = np.isfinite(X)
    Z2 = np.where(mask, (X - P) ** 2 / np.maximum(W, 1e-9), np.nan)
    outfit = np.nanmean(Z2, axis=0)
    infit = (np.nansum(np.where(mask, (X - P) ** 2, 0.0), axis=0)
             / np.maximum(np.nansum(np.where(mask, W, 0.0), axis=0), 1e-9))
    return infit, outfit


def item_dif(X: np.ndarray, theta: np.ndarray, groups: np.ndarray,
             ref: str, foc: str):
    """Differential item functioning between two conditions.

    Calibrates the item separately in each group with person measures held
    fixed on the common metric, and reports the difficulty shift. A large shift
    means the item behaves differently depending on which lesson the pupil sat,
    which would make a condition contrast partly an artefact of the instrument.
    Interpretation follows the usual ETS bands (|shift| < 0.43 negligible,
    0.43--0.64 moderate, > 0.64 large).
    """
    X = np.asarray(X, float)
    X = np.where(X < 0, np.nan, X)
    out = []
    for j in range(X.shape[1]):
        row = {}
        for label, g in (("ref", ref), ("foc", foc)):
            m = (groups == g) & np.isfinite(X[:, j]) & np.isfinite(theta)
            if m.sum() < 20:
                row[label] = np.nan
                continue
            # one-parameter conditional estimate of b given fixed theta
            lo, hi = -6.0, 6.0
            for _ in range(60):
                mid = (lo + hi) / 2
                pr = 1.0 / (1.0 + np.exp(-(theta[m] - mid)))
                if pr.mean() > X[m, j].mean():
                    lo = mid
                else:
                    hi = mid
            row[label] = (lo + hi) / 2
        shift = row["ref"] - row["foc"] if np.isfinite(row.get("ref", np.nan)) \
            and np.isfinite(row.get("foc", np.nan)) else np.nan
        band = ("negligible" if abs(shift) < 0.43 else
                "moderate" if abs(shift) < 0.64 else "large") \
            if np.isfinite(shift) else "n/a"
        out.append(dict(item=j, b_ref=row.get("ref"), b_foc=row.get("foc"),
                        shift=shift, band=band))
    return out


def person_separation(theta: np.ndarray, se: np.ndarray):
    """Rasch person-separation reliability = (SD_obs^2 - MSE) / SD_obs^2."""
    var_obs = float(np.var(theta, ddof=1))
    mse = float(np.mean(se ** 2))
    rel = max((var_obs - mse) / var_obs, 0.0)
    sep = np.sqrt(rel / max(1 - rel, 1e-9))
    return rel, sep


def cronbach_alpha(X: np.ndarray) -> float:
    X = np.asarray(X, dtype=float)
    X = X[~np.isnan(X).any(axis=1)]
    k = X.shape[1]
    return float(k / (k - 1) * (1 - X.var(axis=0, ddof=1).sum() / X.sum(axis=1).var(ddof=1)))


# ============================================================ inference helpers
def cluster_contrast(df: pd.DataFrame, value: str, a: str, b: str,
                     unit="student", cluster="klass"):
    """Within-student difference a - b, CR1 cluster-robust over classes."""
    w = df.pivot_table(index=[unit, cluster], columns="cond", values=value)
    w = w.dropna(subset=[a, b])
    d = (w[a] - w[b]).to_numpy()
    g = w.index.get_level_values(cluster).to_numpy()
    n, est = d.size, float(d.mean())
    groups = np.unique(g)
    J = groups.size
    r = d - est
    ssum = np.array([r[g == j].sum() for j in groups])
    var = (J / max(J - 1, 1)) * (ssum ** 2).sum() / n ** 2
    se = float(np.sqrt(max(var, 1e-12)))
    df_t = J - 1
    t = est / se
    return dict(contrast=f"{a}-{b}", n=int(n), J=int(J), est=est, se=se, df=df_t,
                t=float(t), p_two=float(2 * stats.t.sf(abs(t), df_t)),
                p_one=float(stats.t.sf(t, df_t)),
                ci_lo=float(est - stats.t.ppf(1 - ALPHA / 2, df_t) * se),
                ci_hi=float(est + stats.t.ppf(1 - ALPHA / 2, df_t) * se),
                d=float(est / df.groupby("cond")[value].std().mean()))


def tost(res: dict, sesoi: float = SESOI) -> dict:
    est, se, df_t = res["est"], res["se"], res["df"]
    p_lo = float(stats.t.sf((est + sesoi) / se, df_t))
    p_hi = float(stats.t.cdf((est - sesoi) / se, df_t))
    tcrit = stats.t.ppf(1 - ALPHA, df_t)
    return dict(sesoi=sesoi, p_tost=max(p_lo, p_hi),
                equivalent=bool(max(p_lo, p_hi) < ALPHA),
                ci90_lo=float(est - tcrit * se), ci90_hi=float(est + tcrit * se))


def holm(pvals: dict) -> dict:
    keys = sorted(pvals, key=lambda k: pvals[k])
    m, adj, run = len(keys), {}, 0.0
    for i, k in enumerate(keys):
        run = max(run, (m - i) * pvals[k])
        adj[k] = min(run, 1.0)
    return adj


def benjamini_hochberg(pvals: dict) -> dict:
    """FDR-adjusted q-values for a family of secondary outcomes.

    Secondary outcomes get FDR rather than Holm because the cost of a false
    positive among them is lower and the cost of missing a real signal in a
    descriptive family is higher; the confirmatory family keeps Holm.
    """
    keys = sorted(pvals, key=lambda k: pvals[k])
    m = len(keys)
    out, running = {}, 1.0
    for i in range(m - 1, -1, -1):
        running = min(running, pvals[keys[i]] * m / (i + 1))
        out[keys[i]] = min(running, 1.0)
    return out


def goodman_kruskal_gamma(x: np.ndarray, y: np.ndarray) -> float:
    """Resolution of metacognitive monitoring: gamma between confidence and
    correctness (Nelson, 1984), computed within a person."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    conc = disc = 0
    n = x.size
    for i in range(n - 1):
        dx = x[i + 1:] - x[i]
        dy = y[i + 1:] - y[i]
        conc += int(np.sum((dx > 0) & (dy > 0)) + np.sum((dx < 0) & (dy < 0)))
        disc += int(np.sum((dx > 0) & (dy < 0)) + np.sum((dx < 0) & (dy > 0)))
    return (conc - disc) / (conc + disc) if (conc + disc) else np.nan


def mc_mediation(a: float, sa: float, b: float, sb: float,
                 n_draw: int = 200_000, seed: int = 7) -> dict:
    """Monte-Carlo confidence interval for the indirect effect a*b
    (Preacher and Selig, 2012) -- equivalent to the bootstrap but deterministic."""
    rng = np.random.default_rng(seed)
    draws = rng.normal(a, sa, n_draw) * rng.normal(b, sb, n_draw)
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return dict(indirect=float(a * b), ci_lo=float(lo), ci_hi=float(hi),
                excludes_zero=bool(lo > 0 or hi < 0))


def _imputation_sensitivity(df: pd.DataFrame, n_imp: int = 20,
                            seed: int = 23) -> dict:
    """Two sensitivity analyses for the missing delayed test.

    Multiple imputation under MAR, and a deliberately adversarial worst case in
    which every missing value in the adaptive condition is set to the worst
    observed quartile and every missing value in the control condition to the
    best. If the conclusion survives that, it is not an artefact of who dropped
    out; if it does not, the honest report is that the data cannot settle it.
    """
    rng = np.random.default_rng(seed)
    obs = df.dropna(subset=["theta_del"])
    X = obs[["theta_pre", "gf", "mai", "theta_imm"]].to_numpy(float)
    X = np.column_stack([np.ones(len(X)), X])
    y = obs["theta_del"].to_numpy(float)
    beta = np.linalg.pinv(X.T @ X) @ X.T @ y
    sigma = float(np.std(y - X @ beta, ddof=X.shape[1]))

    miss = df["theta_del"].isna().to_numpy()
    Xm = df.loc[miss, ["theta_pre", "gf", "mai", "theta_imm"]].to_numpy(float)
    Xm = np.column_stack([np.ones(len(Xm)), Xm])

    ests = {"A-K": [], "G-K": []}
    for _ in range(n_imp):
        filled = df["theta_del"].to_numpy(float).copy()
        filled[miss] = Xm @ beta + rng.normal(0, sigma, miss.sum())
        tmp = df.assign(theta_del_imp=filled)
        for k in ests:
            a, b = k.split("-")
            ests[k].append(cluster_contrast(tmp, "theta_del_imp", a, b)["est"])

    lo_q = obs.groupby("cond")["theta_del"].quantile(0.25)
    hi_q = obs.groupby("cond")["theta_del"].quantile(0.75)
    worst = df["theta_del"].to_numpy(float).copy()
    cond = df["cond"].to_numpy()
    worst[miss & (cond == "A")] = lo_q.get("A", np.nan)
    worst[miss & (cond == "K")] = hi_q.get("K", np.nan)
    worst[miss & (cond == "G")] = hi_q.get("G", np.nan)
    wdf = df.assign(theta_del_worst=worst)

    return dict(
        multiple_imputation={k: round(float(np.mean(v)), 4) for k, v in ests.items()},
        worst_case={f"{a}-{b}": round(cluster_contrast(
            wdf.dropna(subset=["theta_del_worst"]), "theta_del_worst", a, b)["est"], 4)
            for a, b in [("A", "K"), ("G", "K")]},
        n_imputations=n_imp)


# ====================================================================== pipeline
def main(n_classes: int = 12, tag: str = "") -> dict:
    p = Params(n_classes=n_classes)
    sim = simulate(p)
    df = sim["long"].copy()
    results: dict = {"design": dict(
        n_students=int(df.student.nunique()), n_classes=int(df.klass.nunique()),
        n_rows=int(len(df)), attrition=float(p.attrition))}

    # ---------------------------------------------------------- S0 psychometrics
    # The immediate and the delayed form are calibrated CONCURRENTLY through the
    # anchor items, so both person measures land on one metric. Calibrating them
    # separately would centre each on its own mean difficulty and make the
    # immediate-to-delayed difference -- the quantity the thesis is about --
    # uninterpretable.
    n_anchor = int(sim["n_anchor"])
    th_i, th_d, b_all, se_i, se_d = concurrent_calibration(
        sim["x_imm"], sim["x_del"], n_anchor)
    xd = sim["x_del"].astype(float); xd[xd < 0] = np.nan
    xt = sim["x_tt"].astype(float); xt[xt < 0] = np.nan
    th_t, b_t, se_t = rasch_jmle(xt)          # transfer shares no items, so separate
    b_i = b_all[:sim["x_imm"].shape[1]]
    b_d = np.concatenate([b_all[:n_anchor], b_all[sim["x_imm"].shape[1]:]])

    df["theta_imm"] = th_i
    df["theta_del"] = np.where(df["dropout"], np.nan, th_d)
    df["theta_tt"] = np.where(df["dropout"], np.nan, th_t)
    df["acc_imm"] = np.nanmean(np.where(sim["x_imm"] >= 0, sim["x_imm"], np.nan), axis=1)
    df["acc_del"] = np.nanmean(xd, axis=1)
    df["jol_imm"] = sim["jol_imm"].mean(axis=1)
    # retention on the common metric: what was lost between the two occasions
    df["retention_drop"] = df["theta_imm"] - df["theta_del"]

    rel_i, sep_i = person_separation(th_i, se_i)
    ok_d = np.isfinite(th_d)
    rel_d, sep_d = person_separation(th_d[ok_d], se_d[ok_d])

    infit_i, outfit_i = item_fit(sim["x_imm"], th_i, b_i)
    misfit = [int(j) for j in range(len(infit_i))
              if not (0.7 <= infit_i[j] <= 1.3 and 0.7 <= outfit_i[j] <= 1.3)]
    dif = item_dif(sim["x_imm"], th_i, df["cond"].to_numpy(), "A", "G")
    dif_bands = {b: sum(1 for d in dif if d["band"] == b)
                 for b in ("negligible", "moderate", "large")}

    results["psychometrics"] = dict(
        calibration="concurrent, %d common anchor items" % n_anchor,
        ipt=dict(n_items=int(sim["x_imm"].shape[1]), alpha=round(cronbach_alpha(sim["x_imm"]), 3),
                 person_reliability=round(rel_i, 3), separation=round(sep_i, 2),
                 b_range=[round(float(b_i.min()), 2), round(float(b_i.max()), 2)],
                 p_mean=round(float(np.mean(sim["x_imm"])), 3)),
        drt=dict(n_items=int(xd.shape[1]), person_reliability=round(rel_d, 3),
                 separation=round(sep_d, 2),
                 b_range=[round(float(b_d.min()), 2), round(float(b_d.max()), 2)],
                 p_mean=round(float(np.nanmean(xd)), 3)),
        tt=dict(n_items=int(xt.shape[1]), p_mean=round(float(np.nanmean(xt)), 3),
                b_range=[round(float(b_t.min()), 2), round(float(b_t.max()), 2)]),
        item_fit=dict(infit_range=[round(float(infit_i.min()), 2), round(float(infit_i.max()), 2)],
                      outfit_range=[round(float(outfit_i.min()), 2), round(float(outfit_i.max()), 2)],
                      n_outside_0_7_1_3=len(misfit), items_dropped=misfit),
        dif_A_vs_G=dict(max_abs_shift=round(float(np.nanmax(np.abs(
            [d["shift"] for d in dif]))), 3), bands=dif_bands),
        equating_check=dict(
            estimated_drop=round(float(np.nanmean(df["retention_drop"])), 3),
            true_drop=round(float(np.mean(df.theta_imm_true[ok_d])
                                  - np.mean(df.theta_del_true[ok_d])), 3)),
        recovery_corr_theta_imm=round(float(np.corrcoef(th_i, df.theta_imm_true)[0, 1]), 3),
        recovery_corr_b_imm=round(float(np.corrcoef(
            b_i, sim["b_ipt"] - sim["b_ipt"].mean())[0, 1]), 3),
    )

    # ------------------------------------------------------------ S1 descriptives
    desc_cols = ["practice_acc", "theta_imm", "theta_del", "theta_tt", "acc_imm",
                 "acc_del", "jol_imm", "fol", "satisfaction", "peqi",
                 "cl_intrinsic", "cl_extraneous", "cl_germane",
                 "n_prompts", "t_first_prompt", "vtr", "offload_rate"]
    desc = df.groupby("cond")[desc_cols].agg(["mean", "std"]).round(3)
    desc.to_csv(OUT / f"results_descriptives{tag}.csv")
    results["descriptives"] = json.loads(
        df.groupby("cond")[desc_cols].mean().round(3).to_json(orient="index"))

    # ----------------------------------------------- S2 primary mixed-effects model
    md = df.dropna(subset=["theta_del"]).copy()
    md["cond"] = pd.Categorical(md["cond"], categories=["K", "G", "A"])
    # Carry-over coding.  In a 3-period square, an explicit "no carry-over" level
    # for period 1 is perfectly collinear with the period-1 indicator, which makes
    # the design matrix rank deficient.  The standard remedy (Senn, 2002, ch. 10)
    # assigns period 1 the reference treatment level, so the two estimable
    # carry-over parameters are G and A relative to K.
    md["prev"] = pd.Categorical(md["prev_cond"].replace({"none": "K"}),
                                categories=["K", "G", "A"])
    md["sid"] = md["student"].astype(str)
    fit = smf.mixedlm(
        "theta_del ~ C(cond) + C(period) + C(prev) + theta_pre + gf",
        md, groups=md["klass"], re_formula="1",
        vc_formula={"student": "0 + C(sid)"},
    ).fit(reml=True, method="lbfgs")
    results["primary_model"] = dict(
        formula="theta_del ~ cond + period + prev_cond + theta_pre + gf + (1|class) + (1|student:class)",
        n=int(fit.nobs), loglike=round(float(fit.llf), 2),
        coefs={k: [round(float(v), 4), round(float(fit.bse[k]), 4),
                   round(float(fit.pvalues[k]), 5)]
               for k, v in fit.params.items() if k != "Group Var"},
        var_class=round(float(fit.cov_re.iloc[0, 0]), 4),
        var_student=round(float(fit.vcomp[0]) if len(fit.vcomp) else float("nan"), 4),
        scale=round(float(fit.scale), 4),
        icc_class=round(float(fit.cov_re.iloc[0, 0])
                        / (float(fit.cov_re.iloc[0, 0])
                           + (float(fit.vcomp[0]) if len(fit.vcomp) else 0.0)
                           + float(fit.scale)), 4),
    )

    # unconditional variance decomposition (reported as the design ICC, whereas
    # the ICC of the fitted model is conditional on the covariates)
    unc = smf.mixedlm("theta_del ~ 1", md, groups=md["klass"], re_formula="1",
                      vc_formula={"student": "0 + C(sid)"}).fit(reml=True, method="lbfgs")
    vc_, vs_, ve_ = (float(unc.cov_re.iloc[0, 0]),
                     float(unc.vcomp[0]) if len(unc.vcomp) else 0.0, float(unc.scale))
    results["variance_decomposition"] = dict(
        var_class=round(vc_, 4), var_student=round(vs_, 4), var_residual=round(ve_, 4),
        icc_class=round(vc_ / (vc_ + vs_ + ve_), 4),
        icc_student_within_class=round(vs_ / (vc_ + vs_ + ve_), 4),
        repeatability=round((vc_ + vs_) / (vc_ + vs_ + ve_), 4))

    # carry-over test (joint on prev_cond levels)
    prev_terms = [k for k in fit.params.index if k.startswith("C(prev)")]
    if prev_terms:
        R = np.zeros((len(prev_terms), len(fit.params)))
        idx = {k: i for i, k in enumerate(fit.params.index)}
        for i, k in enumerate(prev_terms):
            R[i, idx[k]] = 1.0
        wt = fit.wald_test(R, scalar=True)
        results["carryover_test"] = dict(
            terms=prev_terms, stat=round(float(np.ravel(wt.statistic)[0]), 3),
            p=round(float(np.ravel(wt.pvalue)[0]), 4))

    # ----------------------------------------------------------- S3 contrasts
    contrasts, prim_p = {}, {}
    for outcome in ["theta_imm", "theta_del", "theta_tt", "practice_acc",
                    "fol", "satisfaction", "cl_extraneous", "cl_germane"]:
        sub = df.dropna(subset=[outcome])
        for a, b in [("A", "K"), ("G", "K"), ("A", "G")]:
            r = cluster_contrast(sub, outcome, a, b)
            contrasts[f"{outcome}|{a}-{b}"] = r
    results["contrasts"] = {k: {kk: (round(vv, 4) if isinstance(vv, float) else vv)
                                for kk, vv in v.items()} for k, v in contrasts.items()}

    prim_p["H3a_A-K_delayed"] = contrasts["theta_del|A-K"]["p_one"]
    prim_p["H2_A-K_immediate"] = contrasts["theta_imm|A-K"]["p_one"]
    eq = tost(contrasts["theta_del|G-K"])
    prim_p["H3b_G=K_equivalence"] = eq["p_tost"]
    results["equivalence_G_vs_K_delayed"] = {k: (round(v, 4) if isinstance(v, float) else v)
                                             for k, v in eq.items()}
    results["holm_primary"] = {k: round(v, 5) for k, v in holm(prim_p).items()}
    results["holm_primary_raw"] = {k: round(v, 5) for k, v in prim_p.items()}

    # ------------------------------------------------------- S4 moderation (H7)
    mod = smf.mixedlm(
        "theta_del ~ C(cond) * theta_pre + C(period) + gf",
        md, groups=md["klass"], re_formula="1",
        vc_formula={"student": "0 + C(sid)"},
    ).fit(reml=False, method="lbfgs")
    results["moderation_H7"] = {
        k: [round(float(mod.params[k]), 4), round(float(mod.bse[k]), 4),
            round(float(mod.pvalues[k]), 5)]
        for k in mod.params.index if ":theta_pre" in k}
    # simple slopes: effect of G vs K at -1 SD and +1 SD of prior knowledge
    lo = df.dropna(subset=["theta_del"]).query("theta_pre < -0.5")
    hi = df.dropna(subset=["theta_del"]).query("theta_pre > 0.5")
    results["simple_slopes_G_vs_K"] = dict(
        low_prior=cluster_contrast(lo, "theta_del", "G", "K")["est"],
        high_prior=cluster_contrast(hi, "theta_del", "G", "K")["est"])

    # -------------------------------------------------- S5 metacognition (H5)
    jol_item, x_item = sim["jol_imm"], sim["x_imm"]
    bias = jol_item.mean(axis=1) - x_item.mean(axis=1)
    absacc = np.abs(jol_item - x_item).mean(axis=1)
    gamma = np.array([goodman_kruskal_gamma(jol_item[i], x_item[i])
                      for i in range(jol_item.shape[0])])
    df["calib_bias"], df["calib_abs"], df["calib_gamma"] = bias, absacc, gamma
    meta = {}
    for outcome in ["calib_bias", "calib_abs", "calib_gamma"]:
        sub = df.dropna(subset=[outcome])
        for a, b in [("G", "K"), ("A", "K"), ("G", "A")]:
            r = cluster_contrast(sub, outcome, a, b)
            meta[f"{outcome}|{a}-{b}"] = dict(est=round(r["est"], 4), se=round(r["se"], 4),
                                              p=round(r["p_two"], 5))
    results["metacognition_H5"] = meta
    results["metacognition_means"] = json.loads(
        df.groupby("cond")[["calib_bias", "calib_abs", "calib_gamma",
                            "jol_imm", "acc_imm"]].mean().round(3).to_json(orient="index"))

    # ------------------------------------------------- S6 dissociation test (H5)
    z = df.dropna(subset=["theta_del"]).copy()
    z["sid"] = z["student"].astype(str)
    for c in ["fol", "theta_del"]:
        z[c + "_z"] = (z[c] - z[c].mean()) / z[c].std()
    lng = z.melt(id_vars=["student", "sid", "klass", "cond", "period"],
                 value_vars=["fol_z", "theta_del_z"],
                 var_name="outcome_type", value_name="z")
    lng["cond"] = pd.Categorical(lng["cond"], categories=["K", "G", "A"])
    lng["outcome_type"] = pd.Categorical(lng["outcome_type"],
                                         categories=["fol_z", "theta_del_z"])
    dis = smf.mixedlm("z ~ C(cond) * C(outcome_type) + C(period)", lng,
                      groups=lng["klass"], re_formula="1",
                      vc_formula={"student": "0 + C(sid)"}
                      ).fit(reml=False, method="lbfgs")
    results["dissociation_H5"] = {
        k: [round(float(dis.params[k]), 4), round(float(dis.bse[k]), 4),
            round(float(dis.pvalues[k]), 5)]
        for k in dis.params.index if ":" in k and "outcome_type" in k}

    # ------------------------------------------------------ S7 mechanism (H6)
    # There used to be a second, separately specified mediation model here. It
    # produced a different b-path from the one in identification.py -- a
    # different estimator on a different conditioning set -- and two numbers for
    # one quantity in one results file is a defect, not a robustness check.
    # The properly specified version is the only one now.
    #
    # Randomisation identifies the condition effect, not the mediator effect, so
    # the mechanism is estimated three ways under three different assumption
    # sets and the weakest of them is stress-tested.
    results["identification_H6"] = triangulate(df)
    ident = results["identification_H6"]
    results["mediation_H6"] = dict(
        superseded_by="identification_H6",
        a_path=ident["1_mediation_lsem"]["a_path"],
        b_path=ident["1_mediation_lsem"]["b_path"],
        indirect=ident["1_mediation_lsem"]["indirect"],
        ci95=ident["1_mediation_lsem"]["indirect_ci95"],
        truth_b_path=p.b_peqi_on_del)
    results["dose_response_within_G"] = [
        ident["3_dose_response_within_G"]["estimate"],
        ident["3_dose_response_within_G"]["se"],
        ident["3_dose_response_within_G"]["p"]]

    # ------------------------------------------ S7c process measures (A vs G)
    # These are declared as secondary outcomes in the plan, so they have to be
    # estimated and FDR-corrected like any other secondary outcome. Declaring a
    # measure and never reporting it is the quiet version of selective
    # reporting.
    proc = {}
    raw_p = {}
    for col, label in [("peqi", "PEQI"), ("offload_rate", "miera offloadingu"),
                       ("vtr", "doslovne prevzatie"),
                       ("abhr", "vlastny pokus pred pomocou"),
                       ("t_first_prompt", "cas do prveho promptu"),
                       ("n_prompts", "pocet promptov")]:
        sub = df.dropna(subset=[col])
        if sub.empty:
            continue
        r = cluster_contrast(sub, col, "A", "G")
        proc[col] = dict(label=label,
                         mean_G=round(float(df.loc[df.cond == "G", col].mean()), 3),
                         mean_A=round(float(df.loc[df.cond == "A", col].mean()), 3),
                         diff=round(r["est"], 4), se=round(r["se"], 4),
                         d=round(r["d"], 3), p=round(r["p_two"], 6))
        raw_p[col] = r["p_two"]
    for col, q in benjamini_hochberg(raw_p).items():
        proc[col]["q_fdr"] = round(q, 5)
    results["process_measures"] = proc

    # -------------------------------------------------- S8 cognitive load (H8)
    results["load_H8"] = {
        f"{o}|{a}-{b}": round(cluster_contrast(df, o, a, b)["est"], 3)
        for o in ["cl_intrinsic", "cl_extraneous", "cl_germane"]
        for a, b in [("G", "K"), ("A", "K"), ("A", "G")]}

    # --------------------------------------------------------- S9 robustness
    p1 = df[df.period == 1].dropna(subset=["theta_del"])
    rob = {}
    for a, b in [("A", "K"), ("G", "K"), ("A", "G")]:
        ga = p1[p1.cond == a]["theta_del"].to_numpy()
        gb = p1[p1.cond == b]["theta_del"].to_numpy()
        t, pv = stats.ttest_ind(ga, gb, equal_var=False)
        sd = np.sqrt((ga.var(ddof=1) + gb.var(ddof=1)) / 2)
        rob[f"{a}-{b}"] = dict(n_a=int(ga.size), n_b=int(gb.size),
                               est=round(float(ga.mean() - gb.mean()), 4),
                               d=round(float((ga.mean() - gb.mean()) / sd), 3),
                               p=round(float(pv), 4))
    results["robustness_period1_only"] = rob

    # The analysis plan names five robustness analyses. A plan that names them
    # and implements one is a plan that has not been tested, so the other four
    # are here.
    rb: dict = {}

    # (ii) lessons delivered with fidelity below the pre-set floor
    hi_fid = df[df.fidelity >= p.fidelity_floor]
    rb["fidelity_above_floor"] = dict(
        n_rows=int(len(hi_fid)), n_excluded=int(len(df) - len(hi_fid)),
        **{f"{a}-{b}": round(cluster_contrast(hi_fid.dropna(subset=["theta_del"]),
                                              "theta_del", a, b)["est"], 4)
           for a, b in [("A", "K"), ("G", "K")]})

    # (iii) per-protocol: pupils who used an assistant during the control lesson
    clean_ids = set(df.loc[df.contaminated, "student"].unique())
    pp = df[~df.student.isin(clean_ids)].dropna(subset=["theta_del"])
    rb["per_protocol"] = dict(
        n_students_excluded=len(clean_ids),
        contamination_rate=round(float(df[df.cond == "K"].contaminated.mean()), 4),
        **{f"{a}-{b}": round(cluster_contrast(pp, "theta_del", a, b)["est"], 4)
           for a, b in [("A", "K"), ("G", "K")]})

    # (iv) raw proportion correct instead of the Rasch measure
    rb["raw_scores"] = {
        f"{a}-{b}": round(cluster_contrast(df.dropna(subset=["acc_del"]),
                                           "acc_del", a, b)["est"], 4)
        for a, b in [("A", "K"), ("G", "K")]}

    # (v) random slope for condition by class: lets the effect differ between
    # classes instead of assuming it constant, which is the assumption the power
    # analysis showed to be the binding one
    try:
        rs = smf.mixedlm("theta_del ~ C(cond) + C(period) + theta_pre + gf", md,
                         groups=md["klass"], re_formula="1 + C(cond)"
                         ).fit(reml=True, method="lbfgs")
        rb["random_slope_by_class"] = {
            k: [round(float(v), 4), round(float(rs.bse[k]), 4)]
            for k, v in rs.params.items() if "cond" in k and "Var" not in k}
        rb["random_slope_by_class"]["class_effect_variances"] = [
            round(float(x), 4) for x in np.diag(rs.cov_re)]
    except Exception as e:  # singular fits are informative, not fatal
        rb["random_slope_by_class"] = {"error": type(e).__name__}

    results["robustness"] = rb

    # ------------------------------------------------- S10 missing data (MAR)
    df["missing_drt"] = ~np.isfinite(df["theta_del"])
    miss = df.groupby("missing_drt")[["theta_pre", "gf", "mai", "theta_imm"]].mean()
    t_pre, p_pre = stats.ttest_ind(
        df.loc[df.missing_drt, "theta_pre"], df.loc[~df.missing_drt, "theta_pre"],
        equal_var=False)
    results["missing_data"] = dict(
        rate=round(float(df.missing_drt.mean()), 4),
        means_by_missingness=json.loads(miss.round(3).to_json(orient="index")),
        mcar_rejected=bool(p_pre < 0.05),
        test_theta_pre=dict(t=round(float(t_pre), 3), p=round(float(p_pre), 5)),
        note=("dropout is related to prior knowledge, so it is not MCAR; the "
              "mixed model is unbiased under MAR given the modelled covariates, "
              "which is why prior knowledge is in the model and not merely "
              "reported"),
        **_imputation_sensitivity(df))

    # ground-truth recovery check
    # Recovery is judged in standardised units: the JMLE person metric is only
    # identified up to scale, so raw logits of the estimated and the generating
    # model are not directly comparable, whereas Cohen's d is.
    sd_true = float(df["theta_del_true"].std())
    sd_est = float(df["theta_del"].std())
    results["truth_recovery"] = dict(
        sd_true_theta_del=round(sd_true, 3), sd_estimated_theta_del=round(sd_est, 3),
        A_K_target_d=round(p.d_del_A / sd_true, 3),
        A_K_estimated_d=round(contrasts["theta_del|A-K"]["est"] / sd_est, 3),
        G_K_target_d=round(p.d_del_G / sd_true, 3),
        G_K_estimated_d=round(contrasts["theta_del|G-K"]["est"] / sd_est, 3),
        A_K_imm_target_d=round(p.d_imm_A / float(df["theta_imm_true"].std()), 3),
        A_K_imm_estimated_d=round(contrasts["theta_imm|A-K"]["est"]
                                  / float(df["theta_imm"].std()), 3),
        b_peqi_target=p.b_peqi_on_del,
        b_peqi_estimated=ident["1_mediation_lsem"]["b_path"]["est"],
        b_peqi_estimated_d=round(
            ident["1_mediation_lsem"]["b_path"]["est"] / sd_est, 3),
        jol_bias_target=[p.jol_bias_G - p.jol_bias_K, p.jol_bias_A - p.jol_bias_K],
        jol_bias_estimated=[meta["calib_bias|G-K"]["est"], meta["calib_bias|A-K"]["est"]])

    (OUT / f"results{tag}.json").write_text(json.dumps(results, indent=2, ensure_ascii=False),
                                      encoding="utf-8")
    df.to_csv(OUT / f"simulated_long{tag}.csv", index=False)
    return results


if __name__ == "__main__":
    use_utf8()
    import sys
    J = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    r = main(J, tag=("" if J == 12 else f"_J{J}"))
    print(json.dumps({k: r[k] for k in
                      ["design", "psychometrics", "holm_primary_raw", "holm_primary",
                       "equivalence_G_vs_K_delayed", "mediation_H6",
                       "metacognition_means", "truth_recovery"]},
                     indent=2, ensure_ascii=False))
