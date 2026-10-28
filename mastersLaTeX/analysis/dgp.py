"""dgp.py -- Data-generating process for the thesis experiment.

Design
------
3 x 3 replicated Latin square (cross-over / switching replications).

  Within-subject factor : instructional condition
                          K (traditional), G (generic AI), A (adaptive/Socratic AI)
  Period (= topic)      : P1 binary search, P2 sorting, P3 recursion + memoisation
  Sequences             : all 6 permutations of {K, G, A}
                          -> balanced for first-order carry-over (Williams-equivalent, t = 3)
  Assignment unit       : intact class (cluster)
  Analysis unit         : student x period  (3 observations per student)

The DGP encodes the pre-registered hypotheses H1-H8 as explicit parameters so that
(a) statistical power can be simulated and (b) the analysis pipeline can be validated
against a known ground truth before a single real datum is collected.

Effect sizes are anchored in:
  Bastani et al. (2024)   practice gain G +48 %, A +127 %; exam G -17 %
  Kestin et al. (2025)    AI tutor > in-class active learning, large immediate effect
  Deslauriers et al.(2019) feeling-of-learning / actual-learning dissociation
  Gerlich (2025)          cognitive offloading -> lower critical thinking
  Chi and Wylie (2014)    ICAP: passive < active < constructive < interactive

All latent outcomes live on a standardised logit ("theta") metric.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from console import use_utf8

# The item bank is the single source of truth for how long each test is.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assessment"))


@lru_cache(maxsize=1)
def _banks():
    from bank import load_all          # noqa: PLC0415 -- optional at import time
    return load_all()


def _bank_items(bank_id: str) -> int:
    return _banks()[bank_id].n_items


def _bank_anchors(bank_id: str) -> int:
    return len(_banks()[bank_id].anchors)

CONDITIONS = ("K", "G", "A")
SEQUENCES = [
    ("K", "G", "A"), ("K", "A", "G"), ("G", "K", "A"),
    ("G", "A", "K"), ("A", "K", "G"), ("A", "G", "K"),
]
TOPICS = ("T1_vyhladavanie", "T2_triedenie", "T3_rekurzia")


@dataclass
class Params:
    # ---- structure ------------------------------------------------------
    n_classes: int = 12              # a multiple of 6 keeps the square replicated
    class_size_mean: float = 22.0
    class_size_sd: float = 3.0
    attrition: float = 0.12          # lost by the delayed test in week 6

    # ---- variance components (theta metric) -----------------------------
    icc_class: float = 0.12          # Hedges and Hedberg (2007), science achievement
    var_student: float = 0.45        # stable between-student component
    var_resid: float = 0.35          # occasion-specific residual

    # ---- covariates -----------------------------------------------------
    beta_pre: float = 0.55           # prior knowledge -> outcomes
    beta_gf: float = 0.18            # fluid reasoning (matrix short form)
    beta_mai: float = 0.12           # metacognitive awareness

    # ---- H1 in-session practice accuracy (proportion correct) -----------
    practice_K: float = 0.46
    practice_G: float = 0.68         # about +48 % relative
    practice_A: float = 0.79         # about +127 % relative, ceiling-damped
    practice_sd: float = 0.16

    # ---- H2 immediate post-test (theta) ---------------------------------
    d_imm_G: float = 0.18
    d_imm_A: float = 0.46

    # ---- H3 delayed retention at 3 weeks (theta) -- PRIMARY -------------
    d_del_G: float = -0.08           # H3 predicts equivalence to slightly worse
    d_del_A: float = 0.34

    # ---- H4 far transfer (theta) ----------------------------------------
    d_tt_G: float = -0.19
    d_tt_A: float = 0.27

    # ---- H6 mechanism: PEQI (prompt epistemic quality index) ------------
    peqi_G_mean: float = 0.31        # generic AI -> mostly L0/L1 prompts
    peqi_A_mean: float = 0.72        # Socratic scaffold forces L2-L4
    peqi_sd: float = 0.15
    peqi_beta_pre: float = 0.09      # stronger students prompt better anyway
    peqi_beta_mai: float = 0.07
    b_peqi_on_del: float = 0.22      # per 1 SD of PEQI, controlling immediate
    b_peqi_on_tt: float = 0.18       # per 1 SD of PEQI -> far transfer

    # ---- H7 moderation by prior knowledge -------------------------------
    mod_G_pre: float = 0.22          # weak students are harmed most by generic AI
    mod_A_pre: float = -0.10         # the adaptive scaffold is compensatory

    # ---- H5 metacognition / illusion of understanding -------------------
    jol_bias_K: float = 0.07         # additive inflation of item-level JOL
    jol_bias_G: float = 0.23
    jol_bias_A: float = 0.11
    jol_noise: float = 0.16
    fol_K: float = 0.0               # "feeling of learning", theta metric
    fol_G: float = 0.62
    fol_A: float = 0.71
    fol_sd: float = 0.9

    # ---- H8 cognitive load (Leppink 0-10) -------------------------------
    cl_sd: float = 1.6
    cl_intrinsic: dict = field(default_factory=lambda: {"K": 5.6, "G": 5.5, "A": 5.7})
    cl_extraneous: dict = field(default_factory=lambda: {"K": 3.9, "G": 2.7, "A": 2.9})
    cl_germane: dict = field(default_factory=lambda: {"K": 5.4, "G": 4.6, "A": 6.3})

    # ---- first-order carry-over and period effects ----------------------
    carry: dict = field(default_factory=lambda: {"K": 0.0, "G": -0.04, "A": 0.06})
    period_effect: tuple = (0.0, 0.10, 0.16)

    # ---- test construction ----------------------------------------------
    # READ FROM THE ITEM BANK, not typed here. The generating model simulates at
    # the item level, so the measurement error in every simulated outcome depends
    # on how long the test is -- and therefore so does the power analysis, the
    # plan validation, and every number Chapter 6 reports.
    #
    # This was hard-coded as 16 and 12 until the immediate form was shortened to
    # twelve items to fit the lesson. The instrument changed and the generating
    # model did not, so the thesis would have reported power for a test it does
    # not administer. Reading the counts removes that failure mode rather than
    # fixing this instance of it.
    n_items_ipt: int = field(default_factory=lambda: _bank_items("T1_IPT"))
    n_items_drt_per_topic: int = field(
        default_factory=lambda: _bank_items("T1_DRT"))
    n_items_tt: int = field(default_factory=lambda: _bank_items("TT"))
    n_anchor_items: int = field(default_factory=lambda: _bank_anchors("T1_IPT"))
    item_b_sd: float = 0.9       # the anchors link the two scales

    # ---- nuisances the analysis plan promises to check for ---------------
    dropout_beta_pre: float = 0.45   # MAR: weaker pupils drop out more often
    contamination_rate: float = 0.06  # pupils using an assistant during condition K
    contamination_effect: float = 0.5  # how much of the G effect they pick up
    fidelity_floor: float = 0.90      # threshold for the robustness analysis
    fidelity_attenuation: float = 0.8  # effect shrinkage per unit of lost fidelity

    # ---- process measures ------------------------------------------------
    n_prompts_G: float = 14.0
    n_prompts_A: float = 21.0
    t_first_G: float = 42.0          # seconds to first prompt (lognormal median)
    t_first_A: float = 96.0
    vtr_G: float = 0.58              # verbatim transfer ratio
    vtr_A: float = 0.17
    abhr_G: float = 0.34             # attempt-before-help ratio
    abhr_A: float = 0.71

    seed: int = 20260921

    def var_class(self) -> float:
        total = self.var_student + self.var_resid
        return self.icc_class * total / (1.0 - self.icc_class)


def _map(cond: np.ndarray, table: dict) -> np.ndarray:
    return np.array([table[c] for c in cond], dtype=float)


def _anchor(y: np.ndarray, cond: np.ndarray, targets: dict,
            ref: str = "K") -> np.ndarray:
    """Shift each condition's mean so that the realised contrast against `ref`
    equals the pre-specified target exactly.

    This is a deterministic location shift. It removes sampling noise from the
    condition MEANS while leaving every variance component, every interaction
    and every source of heterogeneity untouched -- so the recovery check tests
    the estimator rather than the luck of the draw, and the robustness analyses
    still have the heterogeneity they are meant to detect.
    """
    out = y.copy()
    realised = {c: float(np.mean(y[cond == c])) for c in np.unique(cond)}
    for c, want in targets.items():
        if c in realised:
            out[cond == c] += (realised[ref] + want) - realised[c]
    return out


def build_frame(p: Params, rng: np.random.Generator) -> pd.DataFrame:
    """Skeleton: one row per student x period, with covariates and design codes.

    Three nuisances are generated here rather than assumed away, because the
    analysis plan promises to check for each of them and a check against data
    that cannot contain the problem is not a check:

      * dropout is MAR, not MCAR -- weaker pupils are likelier to miss the
        delayed test, so the missing-data machinery has something to correct;
      * lesson fidelity varies by class, so the "exclude lessons below 90 %"
        robustness analysis has something to exclude;
      * a minority of pupils use an assistant during the control condition,
        so the intention-to-treat / per-protocol distinction is real.
    """
    rows = []
    sid = 0
    for c in range(p.n_classes):
        seq = SEQUENCES[c % len(SEQUENCES)]
        n = max(8, int(round(rng.normal(p.class_size_mean, p.class_size_sd))))
        u_class = rng.normal(0.0, np.sqrt(p.var_class()))
        # fidelity is a property of the class-and-teacher, mostly high with a
        # left tail: the occasional lesson that overruns or drifts off script
        fidelity = float(np.clip(1.0 - rng.gamma(1.6, 0.045), 0.55, 1.0))
        for _ in range(n):
            sid += 1
            u_stud = rng.normal(0.0, np.sqrt(p.var_student))
            theta_pre = rng.normal(0.0, 1.0) * 0.85 + u_class * 0.5
            gf = 0.35 * theta_pre + rng.normal(0.0, np.sqrt(1 - 0.35 ** 2))
            mai = 0.25 * theta_pre + rng.normal(0.0, np.sqrt(1 - 0.25 ** 2))
            # MAR: P(drop) rises as prior knowledge falls
            lin = np.log(p.attrition / (1 - p.attrition)) - p.dropout_beta_pre * theta_pre
            drops = rng.random() < 1.0 / (1.0 + np.exp(-lin))
            for per in range(3):
                cond_here = seq[per]
                contaminated = (cond_here == "K") and (rng.random() < p.contamination_rate)
                rows.append(dict(
                    student=sid, klass=c, sequence="".join(seq), period=per + 1,
                    topic=TOPICS[per], cond=cond_here,
                    prev_cond=(seq[per - 1] if per > 0 else "none"),
                    u_class=u_class, u_stud=u_stud,
                    theta_pre=theta_pre, gf=gf, mai=mai, dropout=drops,
                    fidelity=fidelity, contaminated=contaminated,
                ))
    return pd.DataFrame(rows)


def simulate(p: Params | None = None, item_level: bool = True) -> dict:
    """Return the long frame and, optionally, item-response matrices."""
    p = p or Params()
    rng = np.random.default_rng(p.seed)
    df = build_frame(p, rng)

    cond = df["cond"].to_numpy()
    pre = df["theta_pre"].to_numpy()
    base = (df["u_class"].to_numpy() + df["u_stud"].to_numpy()
            + p.beta_pre * pre
            + p.beta_gf * df["gf"].to_numpy()
            + p.beta_mai * df["mai"].to_numpy()
            + np.array([p.period_effect[i - 1] for i in df["period"]]))
    carry = np.array([p.carry.get(c, 0.0) for c in df["prev_cond"]])
    ai = np.isin(cond, ("G", "A"))

    # Fidelity attenuates whatever the condition would otherwise have done: a
    # lesson that drifted off script delivers a diluted version of itself. This
    # is what the "exclude lessons below 90 %" robustness analysis is checking.
    shrink = 1.0 - p.fidelity_attenuation * (1.0 - df["fidelity"].to_numpy())

    # A pupil who opens an assistant during the control condition has, in
    # effect, been partially treated. Their assigned condition is still K --
    # that is exactly why intention-to-treat and per-protocol differ.
    contam = df["contaminated"].to_numpy()

    # ---- H6 mediator: PEQI ---------------------------------------------
    peqi_mu = np.where(cond == "G", p.peqi_G_mean,
                       np.where(cond == "A", p.peqi_A_mean, np.nan))
    peqi = (peqi_mu
            + p.peqi_beta_pre * pre
            + p.peqi_beta_mai * df["mai"].to_numpy()
            + rng.normal(0, p.peqi_sd, len(df)))
    peqi = np.clip(peqi, 0.0, 1.0)
    df["peqi"] = peqi
    peqi_z = np.full(len(df), np.nan)
    peqi_z[ai] = (peqi[ai] - np.nanmean(peqi[ai])) / np.nanstd(peqi[ai])
    df["peqi_z"] = peqi_z

    # ---- H1 in-session practice accuracy --------------------------------
    pr_mu = _map(cond, {"K": p.practice_K, "G": p.practice_G, "A": p.practice_A})
    df["practice_acc"] = np.clip(
        pr_mu + 0.10 * pre + rng.normal(0, p.practice_sd, len(df)), 0.02, 0.99)

    # ---- H2 immediate post-test theta -----------------------------------
    # Fidelity shrinks the effect and contamination leaks part of it into the
    # control condition; both create the heterogeneity the robustness analyses
    # are meant to find. The condition MEANS are then shifted so that the
    # realised contrast equals the pre-specified target exactly -- otherwise
    # the recovery check would be measuring sampling noise rather than whether
    # the estimator works.
    d_imm = _map(cond, {"K": 0.0, "G": p.d_imm_G, "A": p.d_imm_A})
    d_imm = d_imm * shrink + np.where(contam, p.contamination_effect * p.d_imm_G, 0.0)
    th_imm = base + carry + d_imm + rng.normal(0, np.sqrt(p.var_resid), len(df))
    th_imm = _anchor(th_imm, cond, {"K": 0.0, "G": p.d_imm_G, "A": p.d_imm_A})
    df["theta_imm_true"] = th_imm

    # ---- H3 + H7 delayed retention theta --------------------------------
    # d_del_G / d_del_A are TOTAL effects -- that is what the literature reports.
    # Retention is built from three additive parts: what the pupil knew right
    # after the lesson (0.62), their stable level (0.38), a common forgetting
    # constant, and the mediated path through PEQI. The condition means are
    # then anchored so that the TOTAL contrast equals the target, whatever the
    # upstream paths happened to contribute.
    mod = np.where(cond == "G", p.mod_G_pre * pre,
                   np.where(cond == "A", p.mod_A_pre * pre, 0.0))
    d_del = mod * shrink + np.where(contam, p.contamination_effect * p.d_del_G, 0.0)
    med = np.where(ai, p.b_peqi_on_del * np.nan_to_num(peqi_z), 0.0)
    th_del = (0.62 * th_imm + 0.38 * base) - 0.55 + d_del + med \
        + rng.normal(0, np.sqrt(p.var_resid * 1.15), len(df))
    th_del = _anchor(th_del, cond, {"K": 0.0, "G": p.d_del_G, "A": p.d_del_A})
    df["theta_del_true"] = th_del

    # ---- H4 far transfer -------------------------------------------------
    th_tt = 0.45 * th_imm + 0.30 * base \
        + p.b_peqi_on_tt * np.nan_to_num(peqi_z) \
        - 0.45 + rng.normal(0, np.sqrt(p.var_resid * 1.3), len(df))
    th_tt = _anchor(th_tt, cond, {"K": 0.0, "G": p.d_tt_G, "A": p.d_tt_A})
    df["theta_tt_true"] = th_tt

    # ---- H5 feeling of learning and satisfaction ------------------------
    fol = _map(cond, {"K": p.fol_K, "G": p.fol_G, "A": p.fol_A}) \
        + 0.15 * pre + rng.normal(0, p.fol_sd, len(df))
    df["fol"] = fol
    df["satisfaction"] = np.clip(4.2 + 0.55 * fol + rng.normal(0, 0.8, len(df)), 1, 7)

    # ---- H8 cognitive load (Leppink subscales) --------------------------
    for name, table in (("cl_intrinsic", p.cl_intrinsic),
                        ("cl_extraneous", p.cl_extraneous),
                        ("cl_germane", p.cl_germane)):
        df[name] = np.clip(_map(cond, table) + rng.normal(0, p.cl_sd, len(df)), 0, 10)

    # ---- process measures (AI conditions only) --------------------------
    lam = np.where(cond == "G", p.n_prompts_G, np.where(cond == "A", p.n_prompts_A, 0.0))
    df["n_prompts"] = np.where(ai, rng.poisson(np.maximum(lam, 1e-6)), np.nan)
    tfm = np.where(cond == "G", p.t_first_G, np.where(cond == "A", p.t_first_A, 1.0))
    df["t_first_prompt"] = np.where(
        ai, np.exp(np.log(tfm) + rng.normal(0, 0.55, len(df))), np.nan)
    vtr_mu = np.where(cond == "G", p.vtr_G, np.where(cond == "A", p.vtr_A, 0.0))
    df["vtr"] = np.where(ai, np.clip(vtr_mu - 0.25 * np.nan_to_num(peqi_z)
                                     + rng.normal(0, 0.12, len(df)), 0, 1), np.nan)
    df["offload_rate"] = np.where(ai, np.clip(0.95 - 1.05 * peqi
                                              + rng.normal(0, 0.08, len(df)), 0, 1), np.nan)
    # Attempt-before-help ratio: the share of exercises on which the pupil made
    # a genuine attempt before the first prompt. This is the help-seeking /
    # help-avoidance distinction (Aleven et al., 2003), and it is the process
    # measure a teacher can act on most directly -- it says whether the pupil
    # tried, not merely what they typed.
    abhr_mu = np.where(cond == "G", p.abhr_G, np.where(cond == "A", p.abhr_A, 0.0))
    df["abhr"] = np.where(ai, np.clip(abhr_mu + 0.18 * np.nan_to_num(peqi_z)
                                      + rng.normal(0, 0.14, len(df)), 0, 1), np.nan)

    out = {"long": df, "params": p}
    if item_level:
        out.update(_item_responses(df, p, rng))
    return out


def _item_responses(df: pd.DataFrame, p: Params, rng: np.random.Generator) -> dict:
    """Rasch item responses plus item-level judgements of learning.

    The immediate and the delayed form share `n_anchor_items` items with
    identical difficulties. Those anchors are what makes the two forms
    commensurable: without them, a difference between the immediate and the
    delayed score confounds forgetting with a difference in test difficulty,
    and the retention claim the thesis rests on would be uninterpretable.
    The anchors are emitted as an explicit index map so that the analysis can
    calibrate both forms concurrently instead of assuming the equating.
    """
    n_anchor = min(p.n_anchor_items, p.n_items_drt_per_topic, p.n_items_ipt)
    b_anchor = rng.normal(0.0, p.item_b_sd, n_anchor)
    b_ipt = np.concatenate([b_anchor,
                            rng.normal(0.0, p.item_b_sd, p.n_items_ipt - n_anchor)])
    b_drt = np.concatenate([b_anchor,
                            rng.normal(0.0, p.item_b_sd,
                                       p.n_items_drt_per_topic - n_anchor)])
    b_tt = rng.normal(0.30, p.item_b_sd, p.n_items_tt)     # transfer items are harder

    def rasch(theta: np.ndarray, b: np.ndarray):
        pr = 1.0 / (1.0 + np.exp(-(theta[:, None] - b[None, :])))
        return (rng.random(pr.shape) < pr).astype(np.int8), pr

    x_imm, pr_imm = rasch(df["theta_imm_true"].to_numpy(), b_ipt)
    x_del, pr_del = rasch(df["theta_del_true"].to_numpy(), b_drt)
    x_tt, _ = rasch(df["theta_tt_true"].to_numpy(), b_tt)

    # ---- item-level JOL: cue utilisation -> subjective fluency ----------
    bias = _map(df["cond"].to_numpy(),
                {"K": p.jol_bias_K, "G": p.jol_bias_G, "A": p.jol_bias_A})
    jol = np.clip(pr_imm + bias[:, None] + rng.normal(0, p.jol_noise, pr_imm.shape), 0, 1)
    jol_del = np.clip(pr_del + 0.6 * bias[:, None]
                      + rng.normal(0, p.jol_noise, pr_del.shape), 0, 1)

    keep = ~df["dropout"].to_numpy()
    return dict(
        n_anchor=n_anchor,
        x_imm=x_imm,
        x_del=np.where(keep[:, None], x_del, -1),
        x_tt=np.where(keep[:, None], x_tt, -1),
        jol_imm=jol,
        jol_del=np.where(keep[:, None], jol_del, np.nan),
        b_ipt=b_ipt, b_drt=b_drt, b_tt=b_tt,
    )


if __name__ == "__main__":
    use_utf8()
    s = simulate()
    d = s["long"]
    print(f"students = {d.student.nunique()}, classes = {d.klass.nunique()}, rows = {len(d)}")
    cols = ["practice_acc", "theta_imm_true", "theta_del_true",
            "theta_tt_true", "fol", "peqi", "cl_germane"]
    print(d.groupby("cond")[cols].mean().round(3))
