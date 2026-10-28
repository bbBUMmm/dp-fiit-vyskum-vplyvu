"""validate_plan.py -- operating characteristics of the whole analysis plan.

The problem with one simulated study
------------------------------------
Chapter 6 originally reported a single draw from the generating model. That is
enough to show the pipeline runs and recovers the injected parameters, but it is
the wrong basis for any sentence of the form "the generic tool fell below the
control". In one draw a contrast whose true value is -0.06 will land on either
side of zero about as often as a coin. Writing prose around the sign of such an
estimate produces claims that flip the next time the code is run -- which is
exactly what happened during development, twice.

So the decision-level claims are based on the DISTRIBUTION over many draws, and
the single draw is kept only to show what the output looks like.

What is reported
----------------
  * how often the plan reaches each of the three confirmatory decisions;
  * how often it reaches all three, which is the result the thesis argues for;
  * whether the 95 % intervals actually cover the true values (calibration);
  * the bias of each estimate against the value that was injected;
  * how often the mechanism analyses agree, and the distribution of rho*.

The reduced pipeline used here contains exactly the decision logic of
pipeline.py -- Rasch calibration, cluster-robust within-student contrasts, TOST,
Holm, the mediation and instrumental-variable estimates -- but omits the
mixed-model fits, which are slow and affect none of the decisions.

Run:  python validate_plan.py [n_reps]    ->  out/plan_validation.json
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from dgp import simulate, Params
from identification import iv_2sls, mediation_lsem, sensitivity_rho
from pipeline import (ALPHA, SESOI, cluster_contrast, concurrent_calibration,
                      holm, tost)
from console import use_utf8

warnings.filterwarnings("ignore")
OUT = Path(__file__).resolve().parent / "out"


def one_draw(seed: int, n_classes: int) -> dict:
    p = Params(n_classes=n_classes, seed=seed)
    sim = simulate(p)
    df = sim["long"].copy()

    th_i, th_d, _, _, _ = concurrent_calibration(
        sim["x_imm"], sim["x_del"], int(sim["n_anchor"]))
    df["theta_imm"] = th_i
    df["theta_del"] = np.where(df["dropout"], np.nan, th_d)

    sub = df.dropna(subset=["theta_del"])
    sd = float(sub["theta_del"].std())

    ak = cluster_contrast(sub, "theta_del", "A", "K")
    ag = cluster_contrast(sub, "theta_del", "A", "G")
    gk = cluster_contrast(sub, "theta_del", "G", "K")
    eq = tost(gk)

    p_ak, p_ag = ak["p_one"], ag["p_one"]
    adj = holm({"AK": p_ak, "AG": p_ag, "GKeq": eq["p_tost"]})

    out = dict(
        # --- decisions ---------------------------------------------------
        decide_AK=bool(adj["AK"] < ALPHA / 2),
        decide_AG=bool(adj["AG"] < ALPHA / 2),
        decide_equiv=bool(adj["GKeq"] < ALPHA),
        # --- estimates in d units, comparable to the injected values -----
        d_AK=ak["est"] / sd, d_AG=ag["est"] / sd, d_GK=gk["est"] / sd,
        # --- interval coverage against the truth -------------------------
        sd=sd,
        ci_AK=(ak["ci_lo"] / sd, ak["ci_hi"] / sd),
        ci_GK=(gk["ci_lo"] / sd, gk["ci_hi"] / sd),
        # --- sign of the generic-tool point estimate ---------------------
        sign_GK=int(np.sign(gk["est"])),
    )
    out["decide_all_three"] = (out["decide_AK"] and out["decide_AG"]
                               and out["decide_equiv"])

    # --- mechanism ------------------------------------------------------
    ai = df[df.cond.isin(["G", "A"])].dropna(subset=["theta_del", "peqi_z"]).copy()
    ai["is_A"] = (ai["cond"] == "A").astype(float)
    pre = ["theta_pre", "gf"]
    try:
        med = mediation_lsem(ai, "is_A", "peqi_z", "theta_del", pre)
        iv = iv_2sls(ai, "is_A", "peqi_z", "theta_del", pre)
        sens = sensitivity_rho(ai, "is_A", "peqi_z", "theta_del", pre)
        out.update(
            b_med=med["b_path"]["est"], b_iv=iv["estimate"],
            indirect=med["indirect"],
            indirect_excludes_zero=bool(med["indirect_ci95"][0] > 0
                                        or med["indirect_ci95"][1] < 0),
            rho_star=sens["rho_star"],
            spread=abs(med["b_path"]["est"] - iv["estimate"]),
            first_stage_F=iv["first_stage_F"],
        )
    except Exception:
        out.update(b_med=np.nan, b_iv=np.nan, indirect=np.nan,
                   indirect_excludes_zero=False, rho_star=np.nan,
                   spread=np.nan, first_stage_F=np.nan)
    return out


def main(n_reps: int = 300, n_classes: int = 18) -> None:
    p0 = Params()
    sd_true = None
    rows = []
    for i in range(n_reps):
        rows.append(one_draw(seed=90000 + i, n_classes=n_classes))
        if (i + 1) % 25 == 0:
            print(f"  {i + 1}/{n_reps}", flush=True)
    d = pd.DataFrame(rows)

    # injected values, expressed in the same (observed-sd) metric as the
    # estimates so that bias and coverage mean something
    sd_true = float(d["sd"].mean())
    true = {"AK": p0.d_del_A / sd_true, "GK": p0.d_del_G / sd_true,
            "AG": (p0.d_del_A - p0.d_del_G) / sd_true}

    cover_ak = float(np.mean([lo <= true["AK"] <= hi for lo, hi in d["ci_AK"]]))
    cover_gk = float(np.mean([lo <= true["GK"] <= hi for lo, hi in d["ci_GK"]]))

    res = dict(
        n_reps=n_reps, n_classes=n_classes,
        decisions=dict(
            A_beats_K=round(float(d.decide_AK.mean()), 3),
            A_beats_G=round(float(d.decide_AG.mean()), 3),
            G_equivalent_K=round(float(d.decide_equiv.mean()), 3),
            all_three=round(float(d.decide_all_three.mean()), 3)),
        estimates=dict(
            d_AK=dict(mean=round(float(d.d_AK.mean()), 3),
                      sd=round(float(d.d_AK.std()), 3),
                      injected=round(true["AK"], 3),
                      bias=round(float(d.d_AK.mean()) - true["AK"], 3)),
            d_GK=dict(mean=round(float(d.d_GK.mean()), 3),
                      sd=round(float(d.d_GK.std()), 3),
                      injected=round(true["GK"], 3),
                      bias=round(float(d.d_GK.mean()) - true["GK"], 3)),
            d_AG=dict(mean=round(float(d.d_AG.mean()), 3),
                      sd=round(float(d.d_AG.std()), 3),
                      injected=round(true["AG"], 3),
                      bias=round(float(d.d_AG.mean()) - true["AG"], 3))),
        interval_coverage=dict(A_minus_K=cover_ak, G_minus_K=cover_gk,
                               nominal=0.95),
        sign_instability=dict(
            share_G_above_K=round(float((d.sign_GK > 0).mean()), 3),
            note=("the point estimate of a near-null contrast changes sign "
                  "across draws; no sentence in the thesis may depend on it")),
        mechanism=dict(
            b_mediation=dict(mean=round(float(d.b_med.mean()), 3),
                             sd=round(float(d.b_med.std()), 3)),
            b_iv=dict(mean=round(float(d.b_iv.mean()), 3),
                      sd=round(float(d.b_iv.std()), 3)),
            indirect_excludes_zero=round(float(d.indirect_excludes_zero.mean()), 3),
            rho_star=dict(mean=round(float(d.rho_star.mean()), 3),
                          sd=round(float(d.rho_star.std()), 3),
                          share_below_0_15=round(
                              float((d.rho_star.abs() < 0.15).mean()), 3)),
            estimator_spread=dict(
                median=round(float(d.spread.median()), 3),
                p90=round(float(d.spread.quantile(0.90)), 3)),
            weak_instrument_rate=round(float((d.first_stage_F < 10).mean()), 3)),
    )

    (OUT / "plan_validation.json").write_text(
        json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    d.to_csv(OUT / "plan_validation_draws.csv", index=False)
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    use_utf8()
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 300)
