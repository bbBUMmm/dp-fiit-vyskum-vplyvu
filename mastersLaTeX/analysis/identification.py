"""identification.py -- what randomisation does and does not buy for H6.

The problem
-----------
The design randomises the *condition*, not the *mediator*. So:

  * the total effect of A versus G on retention is identified by design;
  * the effect of condition on PEQI (the a-path) is identified by design;
  * the claim that the effect *runs through* PEQI is NOT identified by design.

The last one is the mechanism claim, and it rests on an assumption randomisation
does not deliver: no unmeasured common cause of prompt quality and retention.
That assumption is almost certainly false in a classroom -- conscientiousness,
prior interest and reading speed all plausibly drive both.  A thesis that states
the indirect effect and moves on is asserting something it has not earned.

What this module does instead
-----------------------------
It estimates the same quantity three times under three different assumption
sets, and quantifies how wrong the weakest one would have to be:

  1. `mediation_lsem`    -- product-of-coefficients under sequential ignorability.
                            Assumption: no unmeasured M-Y confounding.
  2. `iv_wald` / `iv_2sls` -- the randomised pedagogical layer as an INSTRUMENT
                            for prompt quality.  Assumption: exclusion
                            restriction (condition reaches retention only
                            through prompt quality).
  3. `dose_response`     -- the PEQI-retention slope within a single condition.
                            Assumption: none beyond linearity; identifies
                            nothing causally, but if the association vanished
                            here the mechanism story would be in trouble.

  4. `sensitivity_rho`   -- how strong unmeasured M-Y confounding would have to
                            be to drive the indirect effect to zero.

Assumptions 1 and 2 are not nested and are violated by different things, which
is the point: agreement across them is evidence, and disagreement localises the
problem.  None of this makes the mechanism claim causal on its own; it makes the
strength of the claim measurable instead of asserted.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats


# ---------------------------------------------------------------------------
def _cluster_ols(y: np.ndarray, X: np.ndarray, clusters: np.ndarray):
    """OLS with a CR1 cluster-robust covariance matrix. Returns (beta, V, df)."""
    XtX_inv = np.linalg.pinv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    resid = y - X @ beta
    groups = np.unique(clusters)
    J, n, k = groups.size, X.shape[0], X.shape[1]
    meat = np.zeros((k, k))
    for g in groups:
        m = clusters == g
        u = X[m].T @ resid[m]
        meat += np.outer(u, u)
    scale = (J / max(J - 1, 1)) * ((n - 1) / max(n - k, 1))
    V = scale * XtX_inv @ meat @ XtX_inv
    return beta, V, J - 1


def _design(df: pd.DataFrame, cols: list[str]) -> np.ndarray:
    return np.column_stack([np.ones(len(df))] + [df[c].to_numpy(float) for c in cols])


@dataclass
class Estimate:
    name: str
    est: float
    se: float
    df: int

    @property
    def t(self) -> float:
        return self.est / self.se if self.se > 0 else np.nan

    @property
    def p(self) -> float:
        return float(2 * stats.t.sf(abs(self.t), self.df))

    def ci(self, level: float = 0.95) -> tuple[float, float]:
        q = float(stats.t.ppf(1 - (1 - level) / 2, self.df))
        return self.est - q * self.se, self.est + q * self.se

    def as_dict(self) -> dict:
        lo, hi = self.ci()
        return dict(estimate=round(float(self.est), 4), se=round(float(self.se), 4),
                    df=int(self.df), p=round(float(self.p), 5),
                    ci95=[round(float(lo), 4), round(float(hi), 4)])


# ===========================================================================
def iv_2sls(df: pd.DataFrame, instrument: str, mediator: str, outcome: str,
            controls: list[str], cluster: str = "klass") -> dict:
    """Two-stage least squares with a cluster-robust sandwich.

    Controls must be PRE-treatment. Conditioning on a post-treatment variable
    such as the immediate post-test would block part of the very path being
    estimated, so the immediate score is deliberately absent here even though
    it appears in the adjusted mediation model for a different reason.

    The variance is the proper 2SLS sandwich: the bread is built from the
    FITTED regressor matrix, the meat from residuals computed with the OBSERVED
    mediator. Using second-stage residuals for both -- the mistake that a naive
    two-step implementation makes -- understates the standard error.
    """
    d = df.dropna(subset=[instrument, mediator, outcome] + controls).copy()
    cl = d[cluster].to_numpy()
    y = d[outcome].to_numpy(float)

    # --- first stage ----------------------------------------------------
    Z = _design(d, [instrument] + controls)
    b1, V1, dfree = _cluster_ols(d[mediator].to_numpy(float), Z, cl)
    m_hat = Z @ b1
    f_stat = float((b1[1] / np.sqrt(V1[1, 1])) ** 2)

    # --- second stage ---------------------------------------------------
    Xhat = np.column_stack([np.ones(len(d)), m_hat] +
                           [d[c].to_numpy(float) for c in controls])
    Xobs = _design(d, [mediator] + controls)
    bread = np.linalg.pinv(Xhat.T @ Xhat)
    beta = bread @ Xhat.T @ y
    u = y - Xobs @ beta                      # residuals use the OBSERVED mediator

    groups = np.unique(cl)
    J, n, k = groups.size, Xhat.shape[0], Xhat.shape[1]
    meat = np.zeros((k, k))
    for g in groups:
        m = cl == g
        s = Xhat[m].T @ u[m]
        meat += np.outer(s, s)
    scale = (J / max(J - 1, 1)) * ((n - 1) / max(n - k, 1))
    V = scale * bread @ meat @ bread

    est = Estimate("IV (2SLS)", float(beta[1]), float(np.sqrt(V[1, 1])), J - 1)
    out = est.as_dict()
    out.update(first_stage=round(float(b1[1]), 4),
               first_stage_se=round(float(np.sqrt(V1[1, 1])), 4),
               first_stage_F=round(f_stat, 1),
               weak_instrument=bool(f_stat < 10),
               n=int(n), controls=list(controls))
    return out


def iv_wald(df: pd.DataFrame, instrument: str, mediator: str, outcome: str,
            cluster: str = "klass") -> dict:
    """Just-identified Wald ratio, reported for transparency.

    With one binary randomised instrument and no controls this is simply the
    difference in outcome means divided by the difference in mediator means:
    how much retention one unit of prompt quality buys, IF prompt quality is
    the only channel. It is numerically identical to 2SLS without controls, so
    the interval is taken from that estimator rather than from a delta-method
    approximation that would have to assume the two regressions independent.
    """
    d = df.dropna(subset=[instrument, mediator, outcome]).copy()
    X = np.column_stack([np.ones(len(d)), d[instrument].to_numpy(float)])
    cl = d[cluster].to_numpy()

    b_first, V_first, _ = _cluster_ols(d[mediator].to_numpy(float), X, cl)
    b_red, V_red, _ = _cluster_ols(d[outcome].to_numpy(float), X, cl)
    a, se_a = float(b_first[1]), float(np.sqrt(V_first[1, 1]))
    r, se_r = float(b_red[1]), float(np.sqrt(V_red[1, 1]))
    if abs(a) < 1e-8:
        return dict(error="first stage is zero; the instrument does nothing")

    out = iv_2sls(d, instrument, mediator, outcome, controls=[], cluster=cluster)
    out["name"] = "IV (Wald ratio = just-identified 2SLS)"
    out.update(first_stage=round(a, 4), first_stage_se=round(se_a, 4),
               reduced_form=round(r, 4), reduced_form_se=round(se_r, 4),
               ratio_check=round(r / a, 4))
    return out


# ===========================================================================
def mediation_lsem(df: pd.DataFrame, treat: str, mediator: str, outcome: str,
                   controls: list[str], cluster: str = "klass",
                   adjust_for: str | None = None,
                   n_draw: int = 200_000, seed: int = 11) -> dict:
    """Product-of-coefficients with a Monte-Carlo interval for the indirect effect.

    `controls` must be PRE-treatment. All three equations use the same
    conditioning set, so that total = direct + indirect actually holds and the
    proportion mediated means something. Mixing conditioning sets -- estimating
    the b-path with a post-treatment control and the total without it -- yields
    a "proportion mediated" above one and is a decomposition of nothing.

    `adjust_for` optionally adds ONE post-treatment covariate (in practice the
    immediate post-test) to the outcome equation. That variant answers a
    different and substantively important question -- does prompt quality
    predict what SURVIVES, over and above what was known at the end of the
    lesson -- and is reported separately, never folded into the decomposition.
    """
    need = [treat, mediator, outcome] + controls + ([adjust_for] if adjust_for else [])
    d = df.dropna(subset=need).copy()
    cl = d[cluster].to_numpy()
    y = d[outcome].to_numpy(float)

    Xa = _design(d, [treat] + controls)
    ba, Va, dfree = _cluster_ols(d[mediator].to_numpy(float), Xa, cl)
    a, se_a = float(ba[1]), float(np.sqrt(Va[1, 1]))

    Xb = _design(d, [mediator, treat] + controls)
    bb, Vb, _ = _cluster_ols(y, Xb, cl)
    b, se_b = float(bb[1]), float(np.sqrt(Vb[1, 1]))
    c_prime = float(bb[2])

    Xt = _design(d, [treat] + controls)
    bt, _, _ = _cluster_ols(y, Xt, cl)
    total = float(bt[1])

    rng = np.random.default_rng(seed)
    draws = rng.normal(a, se_a, n_draw) * rng.normal(b, se_b, n_draw)
    lo, hi = np.percentile(draws, [2.5, 97.5])

    prop = None
    if abs(total) > 1e-8 and np.sign(a * b) == np.sign(total):
        prop = round(a * b / total, 3)

    out = dict(
        conditioning_set=list(controls),
        a_path=dict(est=round(a, 4), se=round(se_a, 4),
                    p=round(float(2 * stats.t.sf(abs(a / se_a), dfree)), 5),
                    identified_by="randomisation"),
        b_path=dict(est=round(b, 4), se=round(se_b, 4),
                    p=round(float(2 * stats.t.sf(abs(b / se_b), dfree)), 5),
                    identified_by="sequential ignorability (ASSUMED)"),
        direct=round(c_prime, 4),
        total=round(total, 4),
        indirect=round(a * b, 4),
        indirect_ci95=[round(float(lo), 4), round(float(hi), 4)],
        decomposition_holds=bool(abs(c_prime + a * b - total) < 1e-6),
        proportion_mediated=prop,
        df=dfree)

    if adjust_for:
        Xb2 = _design(d, [mediator, treat] + controls + [adjust_for])
        bb2, Vb2, _ = _cluster_ols(y, Xb2, cl)
        out["b_path_net_of_immediate"] = dict(
            est=round(float(bb2[1]), 4), se=round(float(np.sqrt(Vb2[1, 1])), 4),
            p=round(float(2 * stats.t.sf(abs(bb2[1] / np.sqrt(Vb2[1, 1])), dfree)), 5),
            adjusted_for=adjust_for,
            note=("post-treatment adjustment; answers 'does prompt quality predict "
                  "what survives beyond immediate learning', not part of the "
                  "total/direct/indirect decomposition"))
    return out


def sensitivity_rho(df: pd.DataFrame, treat: str, mediator: str, outcome: str,
                    controls: list[str], cluster: str = "klass") -> dict:
    """How strong would unmeasured mediator-outcome confounding have to be?

    In the linear model  M = a*T + e_M,  Y = c'*T + g*M + e_Y  with
    corr(e_M, e_Y) = rho, regressing Y on (T, M) returns

        g_hat = g + rho * sigma_Y / sigma_M

    so the bias-corrected path is  g(rho) = g_hat - rho*s_res/(sqrt(1-rho^2)*s_M),
    where s_res is the residual sd of the fitted outcome model (which equals
    sigma_Y*sqrt(1-rho^2)) and s_M the residual sd of the mediator model. The
    indirect effect vanishes at

        rho* = k / sqrt(1 + k^2),     k = g_hat * s_M / s_res.

    Interpretation: a confounder that explained a fraction R2_M of the residual
    variance of the mediator and R2_Y of the residual variance of the outcome
    induces |rho| = sqrt(R2_M * R2_Y). Reporting rho* therefore says exactly how
    much unmeasured common cause would be needed to explain the whole result,
    instead of pretending none exists.
    """
    d = df.dropna(subset=[treat, mediator, outcome] + controls).copy()
    cl = d[cluster].to_numpy()

    Xa = _design(d, [treat] + controls)
    ba, _, _ = _cluster_ols(d[mediator].to_numpy(float), Xa, cl)
    res_m = d[mediator].to_numpy(float) - Xa @ ba
    s_m = float(np.std(res_m, ddof=Xa.shape[1]))

    Xb = _design(d, [mediator, treat] + controls)
    bb, _, _ = _cluster_ols(d[outcome].to_numpy(float), Xb, cl)
    g_hat = float(bb[1])
    res_y = d[outcome].to_numpy(float) - Xb @ bb
    s_res = float(np.std(res_y, ddof=Xb.shape[1]))

    k = g_hat * s_m / s_res
    rho_star = float(k / np.sqrt(1 + k * k))

    grid = np.linspace(-0.6, 0.6, 25)
    curve = []
    for rho in grid:
        g_rho = g_hat - rho * s_res / (np.sqrt(max(1 - rho ** 2, 1e-9)) * s_m)
        curve.append(dict(rho=round(float(rho), 3),
                          b_path=round(float(g_rho), 4),
                          indirect=round(float(ba[1] * g_rho), 4)))

    return dict(
        b_path_observed=round(g_hat, 4),
        rho_star=round(rho_star, 4),
        r2_symmetric=round(abs(rho_star), 4),
        interpretation=(
            f"an unmeasured confounder would have to explain about "
            f"{abs(rho_star) * 100:.0f} % of the residual variance of BOTH the "
            f"mediator and the outcome to reduce the indirect effect to zero"),
        curve=curve)


def dose_response(df: pd.DataFrame, mediator: str, outcome: str,
                  controls: list[str], cluster: str = "klass") -> dict:
    """The mediator-outcome slope inside a single condition.

    Purely observational: nothing here is randomised, and the estimate is
    confounded by whatever makes a pupil prompt well. It is reported because
    its ABSENCE would be damaging -- if prompt quality predicted nothing where
    the design did not force it, the mechanism story would rest entirely on the
    manipulation having worked for some other reason.
    """
    d = df.dropna(subset=[mediator, outcome] + controls).copy()
    X = _design(d, [mediator] + controls)
    b, V, dfree = _cluster_ols(d[outcome].to_numpy(float), X, d[cluster].to_numpy())
    est = Estimate("dose-response (observational)", float(b[1]),
                   float(np.sqrt(V[1, 1])), dfree)
    out = est.as_dict()
    out.update(n=int(len(d)), controls=controls,
               caveat="observational; not identified by the design")
    return out


# ===========================================================================
def triangulate(df: pd.DataFrame, cond_col: str = "cond",
                mediator: str = "peqi_z", outcome: str = "theta_del",
                pre_controls: tuple[str, ...] = ("theta_pre", "gf"),
                post_control: str = "theta_imm") -> dict:
    """Run all four analyses on the AI conditions and collect them side by side."""
    d = df[df[cond_col].isin(["G", "A"])].dropna(subset=[outcome, mediator]).copy()
    d["is_A"] = (d[cond_col] == "A").astype(float)
    pre = list(pre_controls)

    res = {
        "sample": dict(n=int(len(d)), n_classes=int(d["klass"].nunique()),
                       conditions=["G", "A"]),
        "1_mediation_lsem": mediation_lsem(
            d, "is_A", mediator, outcome, pre, adjust_for=post_control),
        "2_iv_wald": iv_wald(d, "is_A", mediator, outcome),
        "2b_iv_2sls": iv_2sls(d, "is_A", mediator, outcome, pre),
        "3_dose_response_within_G": dose_response(
            d[d[cond_col] == "G"], mediator, outcome, pre + [post_control]),
        "4_sensitivity": sensitivity_rho(d, "is_A", mediator, outcome, pre),
    }

    ests = [res["1_mediation_lsem"]["b_path"]["est"],
            res["2b_iv_2sls"]["estimate"],
            res["3_dose_response_within_G"]["estimate"]]
    spread = max(ests) - min(ests)
    res["agreement"] = dict(
        b_path_estimates=[round(e, 4) for e in ests],
        spread=round(float(spread), 4),
        all_positive=bool(all(e > 0 for e in ests)),
        note=("three estimators resting on three different assumption sets; "
              "agreement is evidence, disagreement localises which assumption fails"))
    return res
