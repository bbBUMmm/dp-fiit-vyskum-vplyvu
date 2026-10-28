"""measurement.py -- what error in the MEDIATOR does to the mechanism claim.

The problem this module exists for
---------------------------------
`identification.py` asks what randomisation buys.  It assumes throughout that
PEQI is observed.  It is not: PEQI is *estimated* by a classifier, and the
classifier's error is not innocent noise, because it can depend on the very
condition the design randomises.

The dependence is not hypothetical here.  Condition A's self-explanation gate
REQUIRES pupils to write "I think that ..." before the worked solution unlocks.
A classifier that reads that opening as evidence of reasoning will therefore
score condition-A prompts higher than condition-G prompts *for interface
reasons*, on top of any real difference.  Measured on the anchor corpus, the
first version of the classifier in this thesis promoted 34 of 34 L0/L1 prompts
to L4 on a four-word prefix, worth +0.88 of PEQI per prompt -- more than twice
the entire between-condition effect the study is powered to find.  The fix is
in `peqi.py`; `veneer_audit()` below is the measurement, before and after.

The model
---------
Let A in {0,1} be the randomised pedagogical layer, M the true prompt quality,
Y retention.  Write

    M  = a*A + u,        Y = c'*A + b*M + eps,      cov(u, eps) = s_ue
    M~ = M + d*A + e,    e independent of everything,   var(e) = s_e^2

so `d` is DIFFERENTIAL error (condition-dependent bias) and `e` is CLASSICAL
error (condition-independent noise).  Write lambda = var(u)/(var(u)+var(e)) for
the reliability of M~ within condition.

Three propositions, each proved in two lines and verified by simulation in
`verify_propositions()`:

  P1  The reduced form cov(Y,A)/var(A) = c' + a*b contains no M~ at all, so it
      is untouched by d and by e.  Under the exclusion restriction (c' = 0) the
      indirect effect IS the reduced form.  ==> The quantity "how much of the
      A-vs-G effect runs through prompt quality" is ROBUST to any amount of
      mediator measurement error.  This is the single most useful fact in the
      module, and it says which number the thesis should lead with.

  P2  beta_IV = ITT_Y / (a + d) = b * a/(a+d).  Differential error inflates the
      first stage, so it ATTENUATES the per-unit IV estimate.  The direction is
      the opposite of the naive intuition, which reads a bigger first stage as
      a stronger manipulation.

  P3  indirect_med = (a+d) * b_hat, with b_hat = (b*var(u) + s_ue)/(var(u)+var(e)).
      With no M-Y confounding this is ITT_Y * (1 + d/a) * lambda: inflated by
      the differential part, attenuated by the classical part.  The two can
      cancel exactly, at d/a = (1-lambda)/lambda, giving the right answer for
      the wrong reason.

  Corollary (the diagnostic).  indirect_med / indirect_IV = (1 + d/a) * lambda,
      and both factors are ESTIMABLE -- lambda from the reliability study, d
      from a blinded audit.  A gap between the two estimators larger than that
      product is not measurement error; it is the M-Y confounding that
      `sensitivity_rho` quantifies.  The triangulation in `identification.py`
      therefore gains a calibrated expectation instead of an eyeball.

What follows for the design
---------------------------
`audit_power()` sizes the blinded double-coding audit that estimates d, and
`correct_differential()` applies the correction.  The audit is the only part of
this that costs anything, and it is cheap: the numbers below put it at a few
hundred prompts.

Run:  python measurement.py      -> out/measurement.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import peqi
from peqi import SEED_CORPUS, WEIGHTS, rule_classify
from console import use_utf8

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)

# The four openings condition A's self-explanation gate effectively dictates.
VENEERS = ("myslim si ze ", "podla mna ", "mam pocit ze ", "chapem to tak ze ")


# ===========================================================================
# 1.  The propositions, verified numerically rather than asserted.
# ===========================================================================
def _ols(y: np.ndarray, X: np.ndarray) -> np.ndarray:
    return np.linalg.lstsq(X, y, rcond=None)[0]


def _one_draw(rng, n, a, b, c_prime, delta, s_e, s_u=1.0, s_eps=1.0,
              rho_u_eps=0.0):
    """One population draw under the model in the docstring."""
    A = rng.integers(0, 2, n).astype(float)
    # correlated (u, eps) to allow M-Y confounding
    z1, z2 = rng.standard_normal(n), rng.standard_normal(n)
    u = s_u * z1
    eps = s_eps * (rho_u_eps * z1 + np.sqrt(1 - rho_u_eps ** 2) * z2)
    M = a * A + u
    Y = c_prime * A + b * M + eps
    M_obs = M + delta * A + s_e * rng.standard_normal(n)
    return A, M, M_obs, Y


def _estimates(A, M_obs, Y):
    ones = np.ones(len(A))
    itt_y = _ols(Y, np.column_stack([ones, A]))[1]
    a_hat = _ols(M_obs, np.column_stack([ones, A]))[1]
    b_hat = _ols(Y, np.column_stack([ones, A, M_obs]))[2]
    return dict(itt_y=itt_y, a_hat=a_hat, b_hat=b_hat,
                beta_iv=itt_y / a_hat,
                indirect_med=a_hat * b_hat,
                indirect_iv=a_hat * (itt_y / a_hat))   # == itt_y, kept explicit


def verify_propositions(n: int = 400_000, seed: int = 4242) -> dict:
    """Simulate the error process and check each proposition to 3 decimals.

    The point of doing this numerically as well as algebraically is that the
    algebra is easy to get right on paper and easy to get wrong in code, and it
    is the code that the thesis actually runs.
    """
    rng = np.random.default_rng(seed)
    a, b, c_prime = 0.80, 0.30, 0.0          # exclusion holds: c' = 0
    s_u, s_e, delta = 1.0, 0.60, 0.25
    lam = s_u ** 2 / (s_u ** 2 + s_e ** 2)

    A, M, M_obs, Y = _one_draw(rng, n, a, b, c_prime, delta, s_e, s_u)
    clean = _estimates(A, M, Y)
    dirty = _estimates(A, M_obs, Y)

    pred_beta_iv = b * a / (a + delta)
    pred_indirect_med = a * b * (1 + delta / a) * lam

    out = {
        "setup": dict(a=a, b=b, c_prime=c_prime, delta=delta, sigma_e=s_e,
                      reliability_lambda=round(lam, 4), n=n),
        "P1_reduced_form_is_immune": {
            "itt_y_true_mediator": round(clean["itt_y"], 4),
            "itt_y_error_ridden": round(dirty["itt_y"], 4),
            "target_a_times_b": round(a * b, 4),
            "holds": bool(abs(clean["itt_y"] - dirty["itt_y"]) < 1e-9
                          and abs(dirty["itt_y"] - a * b) < 0.005),
        },
        "P2_iv_attenuates": {
            "beta_iv_observed": round(dirty["beta_iv"], 4),
            "beta_iv_predicted": round(pred_beta_iv, 4),
            "attenuation_factor": round(a / (a + delta), 4),
            "holds": bool(abs(dirty["beta_iv"] - pred_beta_iv) < 0.006),
        },
        "P3_mediation_inflates_then_attenuates": {
            "indirect_observed": round(dirty["indirect_med"], 4),
            "indirect_predicted": round(pred_indirect_med, 4),
            "inflation_from_delta": round(1 + delta / a, 4),
            "attenuation_from_noise": round(lam, 4),
            "holds": bool(abs(dirty["indirect_med"] - pred_indirect_med) < 0.006),
        },
    }

    # The cancellation case: delta/a = (1-lambda)/lambda gives the right answer
    # for the wrong reason.  Worth showing, because it is the case in which no
    # diagnostic based on the point estimate alone can detect the problem.
    delta_cancel = a * (1 - lam) / lam
    A2, M2, Mo2, Y2 = _one_draw(rng, n, a, b, c_prime, delta_cancel, s_e, s_u)
    d2 = _estimates(A2, Mo2, Y2)
    out["P3b_exact_cancellation"] = {
        "delta_that_cancels": round(delta_cancel, 4),
        "indirect_observed": round(d2["indirect_med"], 4),
        "indirect_true": round(a * b, 4),
        "note": ("with this much differential error the mediation estimate is "
                 "unbiased while every coefficient in it is wrong; only the "
                 "audit can tell the two situations apart"),
        "holds": bool(abs(d2["indirect_med"] - a * b) < 0.006),
    }

    # The diagnostic ratio, including a case WITH M-Y confounding so that the
    # residual gap is shown to isolate confounding rather than measurement.
    #
    # The ratio divides two sample quantities, so its Monte-Carlo error is
    # roughly the sum of theirs.  Averaging over independent replicates buys the
    # precision needed to test the prediction at three decimals instead of
    # loosening the tolerance until it passes.
    predicted_ratio = (1 + delta / a) * lam
    clean_ratios, conf_ratios = [], []
    for _ in range(8):
        Aa, _, Mo, Yy = _one_draw(rng, n, a, b, c_prime, delta, s_e, s_u)
        e = _estimates(Aa, Mo, Yy)
        clean_ratios.append(e["indirect_med"] / e["indirect_iv"])
        Ab, _, Mo2_, Yy2 = _one_draw(rng, n, a, b, c_prime, delta, s_e, s_u,
                                     rho_u_eps=0.35)
        e2 = _estimates(Ab, Mo2_, Yy2)
        conf_ratios.append(e2["indirect_med"] / e2["indirect_iv"])
    obs_clean = float(np.mean(clean_ratios))
    obs_conf = float(np.mean(conf_ratios))
    mc_se = float(np.std(clean_ratios, ddof=1) / np.sqrt(len(clean_ratios)))
    out["corollary_diagnostic_ratio"] = {
        "predicted_ratio_no_confounding": round(predicted_ratio, 4),
        "observed_ratio_no_confounding": round(obs_clean, 4),
        "monte_carlo_se": round(mc_se, 4),
        "observed_ratio_with_rho_0_35": round(obs_conf, 4),
        "note": ("the first two agree to within Monte-Carlo error; the third "
                 "departs, and the departure is the confounding that "
                 "sensitivity_rho is there to bound"),
        "holds": bool(abs(obs_clean - predicted_ratio) < max(3 * mc_se, 0.004)
                      and obs_conf > predicted_ratio + 0.20),
    }
    out["all_propositions_hold"] = bool(
        all(v["holds"] for k, v in out.items() if isinstance(v, dict) and "holds" in v))
    return out


# ===========================================================================
# 2.  How large could delta actually be?  Measure it, do not guess it.
# ===========================================================================
def veneer_audit(classify=rule_classify) -> dict:
    """Score the classifier's susceptibility to a condition-induced veneer.

    Every L0 and L1 anchor is prefixed with one of the four epistemic openings
    condition A's gate obliges pupils to write.  The prefix adds no reasoning,
    so a correct classifier leaves the level alone.  The mean change in PEQI
    weight IS delta per veneered prompt: it is the bias the interface would
    inject into the mediator with no change in the underlying behaviour.
    """
    sub = [(t, l) for t, l in SEED_CORPUS if l in ("L0", "L1")]
    shifted, moves = 0, []
    w_true = w_ven = 0.0
    for i, (text, lab) in enumerate(sub):
        veneered = VENEERS[i % len(VENEERS)] + text
        got = classify(veneered)
        w_true += WEIGHTS[lab]
        w_ven += WEIGHTS[got]
        if got != lab:
            shifted += 1
            moves.append({"true": lab, "coded": got, "prompt": veneered})
    n = len(sub)
    return {
        "n_prompts": n,
        "n_level_shifts": shifted,
        "share_shifted": round(shifted / n, 4),
        "mean_weight_true": round(w_true / n, 4),
        "mean_weight_veneered": round(w_ven / n, 4),
        "delta_per_prompt": round((w_ven - w_true) / n, 4),
        "examples": moves[:5],
    }


# The lexicons exactly as they stood before the repair, kept verbatim so that
# the "before" numbers in the thesis are reproducible from the current source
# rather than quoted from a run log that no one can re-execute.
_ORIG_SOLVE = r"(napis|napis mi|naprogramuj|vyries|sprav|urob|daj mi|doplň|doplň mi|" \
              r"dopln|vypis|vytvor|implementuj|zostav|vygeneruj)"
_ORIG_OFFTASK = r"(ahoj|ako sa mas|datum|basen|do konca hodiny|emoji|ucitel|dejepis|" \
                r"hra|vtipne|test test|pocasie)"
_ORIG_ELABORATE = r"(kedy je|rozdiel medzi|porovnaj|v akych pripadoch|co by sa stalo|" \
                  r"protipriklad|oplati|hranicne pripady|plati to aj|" \
                  r"da sa .* pouzit aj|ako suvisi|ake su .* pripady|namiesto)"


def _legacy_rule(text: str, orig_lexicons: bool) -> str:
    """The decision rule as it stood BEFORE the dominance rules were added.

    Only the legacy variants are reimplemented here.  The current rule is not:
    the audit calls `peqi.rule_classify` itself, so the "after" column cannot
    drift away from the code the study will actually run -- which is the exact
    failure this whole module is about.

    Two independent things were wrong and are separated, because a single
    before/after number would let one take credit for the other:

      * the LEXICONS matched inside longer words -- "sprav" inside "spravne",
        "lebo" inside "alebo", "hra" inside "hranicne";
      * the PRIORITY rule promoted any prompt carrying an epistemic marker to
        L4, whatever the prompt went on to demand.

    Only the second is the differential-error threat; the first is ordinary
    sloppiness.  Reporting them apart is what makes the claim checkable.
    """
    import re as _re
    t = peqi.normalise(text)
    solve = _ORIG_SOLVE if orig_lexicons else peqi.SOLVE_VERBS
    offt = _ORIG_OFFTASK if orig_lexicons else peqi.OFFTASK
    elab = _ORIG_ELABORATE if orig_lexicons else peqi.ELABORATE

    f_offtask = bool(_re.search(offt, t))
    f_domain = bool(_re.search(peqi.DOMAIN, t))
    f_selfexpl = bool(_re.search(peqi.SELFEXPL, t))
    f_solve_verb = bool(_re.search(solve, t))
    f_solve = f_solve_verb and bool(_re.search(peqi.ARTEFACT, t))
    f_code = bool(_re.search(r"(def |for |while |return|\{|\}|==|<=|>=|\[i\]|;|\(\))", t))

    if f_offtask and not f_domain:
        return "X"
    if f_selfexpl:                     # <- the defect: the marker alone sufficed
        return "L4"
    if _re.search(elab, t):
        return "L3"
    if _re.search(peqi.EXPLAIN, t):
        return "L2"
    if _re.search(peqi.VERIFY, t) or (f_code and not f_solve):
        return "L1"
    if f_solve_verb:
        return "L0"
    return "L1"


def veneer_before_after() -> dict:
    """The audit at each of the three stages of the repair."""
    y = [l for _, l in SEED_CORPUS]
    stages = {
        "v0_as_written": lambda s: _legacy_rule(s, True),
        "v1_lexicons_anchored": lambda s: _legacy_rule(s, False),
        "v2_dominance_rules": rule_classify,
    }
    out = {}
    for name, rule in stages.items():
        audit = veneer_audit(rule)
        out[name] = {
            "kappa_on_anchors": round(float(
                peqi.cohen_kappa(y, [rule(t) for t, _ in SEED_CORPUS])), 4),
            "n_level_shifts": audit["n_level_shifts"],
            "share_shifted": audit["share_shifted"],
            "delta_per_prompt": audit["delta_per_prompt"],
        }
    out["n_prompts"] = veneer_audit(rule_classify)["n_prompts"]
    out["v0_examples"] = veneer_audit(stages["v0_as_written"])["examples"][:3]
    out["delta_removed"] = round(out["v0_as_written"]["delta_per_prompt"]
                                 - out["v2_dominance_rules"]["delta_per_prompt"], 4)
    out["note"] = ("the repair raises agreement AND closes the attack; that is "
                   "not automatic -- a rule can buy robustness with accuracy")
    return out


# ===========================================================================
# 3.  The audit that estimates delta in the field, and its power.
# ===========================================================================
def audit_power(n_prompts_per_condition: int = 150, prompts_per_pupil: int = 10,
                icc: float = 0.25, kappa_field: float = 0.75,
                delta_true: float = 0.05, n_sim: int = 4000,
                alpha: float = 0.05, seed: int = 909) -> dict:
    """Power of the blinded double-coding audit to detect differential bias.

    Design.  A stratified random sample of prompts is drawn from conditions G
    and A, stripped of every cue to condition, shuffled together and coded by
    two humans blind to condition.  The estimate is

        delta_hat = mean(classifier - human | A) - mean(classifier - human | G)

    on the PEQI weight scale.  Blinding is what makes it an estimate of the
    classifier's condition-dependent bias rather than of a real difference: a
    human who can see which condition a prompt came from is exposed to exactly
    the bias being measured.

    Prompts are nested in pupils, so the standard error is cluster-robust at
    the pupil.  With kappa in the field at the SAP's acceptance floor of 0.75
    and all errors adjacent -- which is what the anchor confusion matrix shows
    -- a disagreement moves the weight by one step of 0.25.
    """
    rng = np.random.default_rng(seed)
    p_err = 1.0 - kappa_field                      # conservative: kappa ~ accuracy here
    step = 0.25
    n_pupils = max(int(np.ceil(n_prompts_per_condition / prompts_per_pupil)), 2)
    sig = np.sqrt(icc), np.sqrt(1 - icc)

    hits = 0
    ests = np.empty(n_sim)
    for s in range(n_sim):
        rows = []
        for cond, shift in (("G", 0.0), ("A", delta_true)):
            pupil_eff = rng.normal(0, sig[0], n_pupils)
            for j in range(n_pupils):
                k = prompts_per_pupil
                # disagreement: one adjacent step, signed, plus the differential
                # bias in condition A, plus a pupil-level random effect
                err = step * np.sign(rng.standard_normal(k)) * \
                    (rng.random(k) < p_err)
                err = err + shift + pupil_eff[j] * 0.05 + \
                    rng.normal(0, sig[1] * 0.05, k)
                rows.append(pd.DataFrame(
                    {"d": err, "cond": cond, "pupil": f"{cond}{j}"}))
        d = pd.concat(rows, ignore_index=True)
        est, se = _cluster_diff(d)
        ests[s] = est
        if se > 0 and abs(est / se) > 1.96:
            hits += 1
    return {
        "design": dict(n_prompts_per_condition=n_prompts_per_condition,
                       prompts_per_pupil=prompts_per_pupil,
                       n_pupils_per_condition=n_pupils, icc=icc,
                       kappa_field=kappa_field, alpha=alpha),
        "delta_true": delta_true,
        "power": round(hits / n_sim, 3),
        "mean_estimate": round(float(ests.mean()), 4),
        "bias": round(float(ests.mean() - delta_true), 4),
        "se_empirical": round(float(ests.std(ddof=1)), 4),
        "detectable_delta_80pct": None,     # filled by audit_curve()
    }


def _cluster_diff(d: pd.DataFrame) -> tuple[float, float]:
    """Difference in means with a pupil-clustered standard error."""
    X = np.column_stack([np.ones(len(d)), (d["cond"] == "A").astype(float)])
    y = d["d"].to_numpy(float)
    XtX_inv = np.linalg.pinv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    u = y - X @ beta
    groups = d["pupil"].to_numpy()
    uniq = np.unique(groups)
    meat = np.zeros((2, 2))
    for g in uniq:
        m = groups == g
        s = X[m].T @ u[m]
        meat += np.outer(s, s)
    J = len(uniq)
    V = (J / max(J - 1, 1)) * XtX_inv @ meat @ XtX_inv
    return float(beta[1]), float(np.sqrt(max(V[1, 1], 0.0)))


def audit_curve(sizes=(60, 100, 150, 200, 300), delta_true: float = 0.05,
                n_sim: int = 1500) -> list[dict]:
    """Power against audit size, so the design can be chosen rather than argued."""
    rows = []
    for n in sizes:
        r = audit_power(n_prompts_per_condition=n, delta_true=delta_true,
                        n_sim=n_sim, seed=1000 + n)
        rows.append({"n_per_condition": n, "power": r["power"],
                     "se": r["se_empirical"]})
    return rows


# ===========================================================================
# 4.  The correction, and what it costs.
# ===========================================================================
def correct_differential(df: pd.DataFrame, treat: str, mediator: str,
                         outcome: str, delta_hat: float, lambda_hat: float,
                         se_delta: float = 0.0, se_lambda: float = 0.0,
                         n_boot: int = 2000, seed: int = 77) -> dict:
    """Debias the mediator, then de-attenuate the b-path.

    Two steps, in this order:

      1. M* = M~ - delta_hat * A          removes the condition-dependent bias
      2. b* = b_hat / lambda_hat          undoes classical attenuation

    Step 2 is regression calibration, and it is the step that must not be
    applied without step 1: dividing a differentially biased coefficient by a
    reliability makes it more wrong, not less.

    The interval propagates the uncertainty in delta_hat and lambda_hat by
    bootstrap, because treating estimated nuisance parameters as known is how
    a corrected estimate ends up with a narrower interval than the uncorrected
    one it was derived from.
    """
    d = df.dropna(subset=[treat, mediator, outcome]).copy()
    A = d[treat].to_numpy(float)
    M = d[mediator].to_numpy(float)
    Y = d[outcome].to_numpy(float)
    ones = np.ones(len(d))

    def _fit(A_, M_, Y_, dl, lm):
        Ms = M_ - dl * A_
        a_hat = _ols(Ms, np.column_stack([np.ones(len(A_)), A_]))[1]
        b_raw = _ols(Y_, np.column_stack([np.ones(len(A_)), A_, Ms]))[2]
        b_cal = b_raw / lm if lm > 0 else np.nan
        return a_hat, b_raw, b_cal, a_hat * b_cal

    naive = _fit(A, M, Y, 0.0, 1.0)
    corr = _fit(A, M, Y, delta_hat, lambda_hat)

    rng = np.random.default_rng(seed)
    n = len(d)
    boot = np.empty((n_boot, 2))
    for i in range(n_boot):
        idx = rng.integers(0, n, n)
        dl = rng.normal(delta_hat, se_delta) if se_delta > 0 else delta_hat
        lm = rng.normal(lambda_hat, se_lambda) if se_lambda > 0 else lambda_hat
        lm = float(np.clip(lm, 0.05, 1.0))
        _, _, b_cal, ind = _fit(A[idx], M[idx], Y[idx], dl, lm)
        boot[i] = (b_cal, ind)
    lo, hi = np.percentile(boot, [2.5, 97.5], axis=0)

    return {
        "inputs": dict(delta_hat=delta_hat, lambda_hat=lambda_hat,
                       se_delta=se_delta, se_lambda=se_lambda, n=int(n)),
        "naive": dict(a_path=round(naive[0], 4), b_path=round(naive[1], 4),
                      indirect=round(naive[0] * naive[1], 4)),
        "corrected": dict(a_path=round(corr[0], 4), b_path_raw=round(corr[1], 4),
                          b_path_calibrated=round(corr[2], 4),
                          indirect=round(corr[3], 4)),
        "ci95_b_calibrated": [round(float(lo[0]), 4), round(float(hi[0]), 4)],
        "ci95_indirect": [round(float(lo[1]), 4), round(float(hi[1]), 4)],
        "width_naive_vs_corrected": None,
    }


def correction_recovers_truth(n: int = 20_000, seed: int = 31) -> dict:
    """End-to-end check: inject known delta and noise, correct, recover b.

    If the correction did not return the planted value this whole section
    would be decoration.
    """
    rng = np.random.default_rng(seed)
    a, b, delta, s_e, s_u = 0.80, 0.30, 0.25, 0.60, 1.0
    lam = s_u ** 2 / (s_u ** 2 + s_e ** 2)
    A, M, M_obs, Y = _one_draw(rng, n, a, b, 0.0, delta, s_e, s_u)
    d = pd.DataFrame({"A": A, "M": M_obs, "Y": Y})
    r = correct_differential(d, "A", "M", "Y", delta_hat=delta,
                             lambda_hat=lam, n_boot=400)
    return {
        "planted": dict(a=a, b=b, delta=delta, reliability_lambda=round(lam, 4),
                        indirect=round(a * b, 4)),
        "naive": r["naive"],
        "corrected": r["corrected"],
        "recovers_a": bool(abs(r["corrected"]["a_path"] - a) < 0.02),
        "recovers_b": bool(abs(r["corrected"]["b_path_calibrated"] - b) < 0.02),
        "recovers_indirect": bool(abs(r["corrected"]["indirect"] - a * b) < 0.02),
        "naive_b_error": round(r["naive"]["b_path"] - b, 4),
        "naive_indirect_error": round(r["naive"]["indirect"] - a * b, 4),
    }


# ===========================================================================
def main() -> int:
    res = {
        "propositions": verify_propositions(),
        "veneer": veneer_before_after(),
        "audit_power": audit_power(),
        "audit_curve": audit_curve(),
        "correction": correction_recovers_truth(),
    }
    res["audit_power"]["detectable_delta_80pct"] = next(
        (r["n_per_condition"] for r in res["audit_curve"] if r["power"] >= 0.80),
        None)

    (OUT / "measurement.json").write_text(
        json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res, indent=2, ensure_ascii=False))

    ok = (res["propositions"]["all_propositions_hold"]
          and res["correction"]["recovers_b"]
          and res["veneer"]["v2_dominance_rules"]["n_level_shifts"] == 0
          )
    print("\n" + ("all checks pass" if ok else "CHECKS FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    use_utf8()
    raise SystemExit(main())
