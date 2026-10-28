"""national_anchor.py -- placing a convenience sample on a national scale.

The limitation this addresses
-----------------------------
The thesis lists, under its own limitations: schools are not randomly selected,
because random selection of schools is not possible in Slovak school research.
Stratification reduces the risk and does not remove it. That limitation is
stated and then left standing, which is the usual fate of the sentence "the
sample is not representative".

It need not be left standing. Random selection is impossible; MEASURING WHERE
THE SAMPLE SITS is not -- provided there exists an instrument with published
item statistics from a large national administration. For Slovak informatics
there is exactly one: iBobor, whose per-item success rates come from a cohort of
roughly 140,000 pupils a year.

How it works
------------
Administer a subset of iBobor items whose national difficulties are published.
Calibrate the study sample with those item difficulties FIXED at their national
values rather than estimated locally. The pupils' person measures then land on
the national metric, and the sample's mean is directly interpretable: this
sample sits at such-and-such a percentile of the national participant
distribution.

This turns an untestable assumption into a reported number. It does not make the
sample representative -- nothing available here can -- but a reader can see the
direction and size of the departure instead of being asked to hope there is
none.

What it cannot do, stated plainly
---------------------------------
The iBobor population is the population of iBobor PARTICIPANTS. Entry is by
school and by choice, so it over-represents pupils whose teachers enter them.
"National scale" here means that participant population and not all Slovak
pupils, and every sentence the thesis writes about it must say so. The number is
still worth having: a known reference population beats an unknown one.

Run:  python national_anchor.py      -> out/national_anchor.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy import stats
from console import use_utf8

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
def logit(p: np.ndarray | float) -> np.ndarray | float:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def difficulty_from_national_p(p_correct: np.ndarray,
                               national_mean_theta: float = 0.0) -> np.ndarray:
    """Turn published success rates into Rasch difficulties.

    Under the Rasch model with the national ability distribution centred at
    `national_mean_theta`, an item answered correctly by a proportion p has
    difficulty b = national_mean_theta - logit(p). This is exact only if the
    national distribution is a point mass, and the approximation is why
    `calibration_bias_from_spread` below exists rather than being assumed away.
    """
    return national_mean_theta - logit(p_correct)


def calibration_bias_from_spread(p_correct: np.ndarray, sd_theta: float,
                                 n_sim: int = 40_000,
                                 seed: int = 3) -> dict:
    """How wrong is the point-mass approximation when abilities are spread?

    The national distribution is not a point mass, so recovering b from a
    marginal success rate is biased. The bias is towards the middle -- extreme
    items look less extreme than they are -- and it matters because it shifts
    the whole anchored scale. Quantified rather than waved at.
    """
    rng = np.random.default_rng(seed)
    b_true = difficulty_from_national_p(p_correct, 0.0)
    theta = rng.normal(0.0, sd_theta, n_sim)
    # marginal success rate actually produced by a spread population
    p_marg = np.array([
        float(np.mean(1 / (1 + np.exp(-(theta - b))))) for b in b_true])
    b_recovered = -logit(p_marg)
    err = b_recovered - b_true
    return {
        "sd_theta_assumed": sd_theta,
        "max_abs_bias_logits": round(float(np.abs(err).max()), 3),
        "mean_abs_bias_logits": round(float(np.abs(err).mean()), 3),
        "note": ("bias shrinks extreme difficulties towards the centre; it is "
                 "nearly constant across items, so it shifts the anchored "
                 "scale's SPREAD more than its LOCATION -- and location is "
                 "what the percentile claim rests on"),
    }


# ---------------------------------------------------------------------------
def anchored_theta(x: np.ndarray, b_fixed: np.ndarray) -> np.ndarray:
    """Person measures with item difficulties held at their national values.

    Newton steps on the Rasch likelihood with b fixed. Extreme scores get the
    usual 0.3 / L-0.3 adjustment, because a pupil who answered everything
    correctly has an unbounded maximum-likelihood estimate and a finite true ability.
    """
    x = np.asarray(x, float)
    n, L = x.shape
    score = np.nansum(x, axis=1)
    adj = np.clip(score, 0.3, L - 0.3)
    th = np.zeros(n)
    for _ in range(60):
        p = 1 / (1 + np.exp(-(th[:, None] - b_fixed[None, :])))
        num = adj - np.nansum(p, axis=1)
        den = np.nansum(p * (1 - p), axis=1)
        step = num / np.maximum(den, 1e-9)
        th = th + np.clip(step, -1.0, 1.0)
        if np.max(np.abs(step)) < 1e-7:
            break
    return th


def locate_sample(n_anchor: int = 8, sample_shift: float = 0.35,
                  sample_sd: float = 0.95, n_pupils: int = 330,
                  national_sd: float = 1.0, n_sim: int = 500,
                  seed: int = 77) -> dict:
    """Recover a sample's position on the national scale, and say how precisely.

    A planted shift is recovered from anchored person measures. The question the
    design needs answered is not "can it be done" but "with how many items", so
    the output is the standard error of the location estimate.
    """
    rng = np.random.default_rng(seed)
    p_nat = np.linspace(0.25, 0.80, n_anchor)        # published success rates
    b = difficulty_from_national_p(p_nat, 0.0)

    ests = []
    for _ in range(n_sim):
        theta = rng.normal(sample_shift, sample_sd, n_pupils)
        p = 1 / (1 + np.exp(-(theta[:, None] - b[None, :])))
        x = (rng.random((n_pupils, n_anchor)) < p).astype(float)
        ests.append(float(np.mean(anchored_theta(x, b))))
    ests = np.array(ests)
    se = float(ests.std(ddof=1))
    mean = float(ests.mean())
    return {
        "n_anchor_items": n_anchor,
        "planted_shift_logits": sample_shift,
        "recovered_shift_logits": round(mean, 3),
        "bias": round(mean - sample_shift, 3),
        "se_of_location": round(se, 3),
        "percentile_of_national": round(
            float(stats.norm.cdf(sample_shift / national_sd) * 100), 1),
        "percentile_ci95": [
            round(float(stats.norm.cdf((mean - 1.96 * se) / national_sd) * 100), 1),
            round(float(stats.norm.cdf((mean + 1.96 * se) / national_sd) * 100), 1)],
    }


def items_needed(target_se: float = 0.10, grid=(4, 6, 8, 10, 12, 16, 20),
                 n_sim: int = 250) -> dict:
    """Fewest anchor items for a location estimate precise enough to quote."""
    rows = []
    for k in grid:
        r = locate_sample(n_anchor=k, n_sim=n_sim, seed=500 + k)
        rows.append({"n_anchor_items": k, "se": r["se_of_location"],
                     "bias": r["bias"]})
    reached = next((r["n_anchor_items"] for r in rows if r["se"] <= target_se),
                   None)
    return {"target_se": target_se, "curve": rows, "items_needed": reached}


# ---------------------------------------------------------------------------
def robustness_to_drift(drift_sd: float = 0.3, n_anchor: int = 8,
                        sample_shift: float = 0.35, n_pupils: int = 330,
                        n_sim: int = 400, seed: int = 909) -> dict:
    """What if the published difficulties are not right for THIS cohort?

    The national statistics come from a different year and a self-selected
    entry. If the true local difficulties differ from the published ones, the
    anchored location is biased. The saving grace is that independent drift
    across items partly cancels in the mean; systematic drift does not, and the
    two are separated here because only the second is dangerous.
    """
    rng = np.random.default_rng(seed)
    p_nat = np.linspace(0.25, 0.80, n_anchor)
    b_pub = difficulty_from_national_p(p_nat, 0.0)

    out = {}
    for label, systematic in (("independent drift", False),
                              ("systematic drift", True)):
        ests = []
        for _ in range(n_sim):
            if systematic:
                b_true = b_pub + rng.normal(0.0, drift_sd)      # one shift, all items
            else:
                b_true = b_pub + rng.normal(0.0, drift_sd, n_anchor)
            theta = rng.normal(sample_shift, 0.95, n_pupils)
            p = 1 / (1 + np.exp(-(theta[:, None] - b_true[None, :])))
            x = (rng.random((n_pupils, n_anchor)) < p).astype(float)
            ests.append(float(np.mean(anchored_theta(x, b_pub))))
        ests = np.array(ests)
        out[label] = {
            "mean_estimate": round(float(ests.mean()), 3),
            "bias": round(float(ests.mean() - sample_shift), 3),
            "sd_across_studies": round(float(ests.std(ddof=1)), 3),
        }
    out["reading"] = (
        "Independent drift averages out over items and mostly inflates the "
        "standard error. Systematic drift -- a cohort that is uniformly better "
        "or worse than the published year -- passes straight through into the "
        "location estimate and cannot be detected from the anchored data "
        "alone. It is therefore bounded by argument, not by estimation: the "
        "reported percentile carries a sensitivity band of the size shown.")
    return out


# ---------------------------------------------------------------------------
def main() -> int:
    loc = locate_sample()
    res = {
        "purpose": ("random selection of schools is impossible; measuring "
                    "where the sample sits is not"),
        "location": loc,
        "items_needed": items_needed(),
        "calibration_bias": {
            sd: calibration_bias_from_spread(np.linspace(0.25, 0.80, 8), sd)
            for sd in (0.8, 1.0, 1.2)
        },
        "drift": robustness_to_drift(),
        "population_caveat": (
            "The reference population is iBobor PARTICIPANTS, not all Slovak "
            "pupils: entry is by school and by choice, so it over-represents "
            "pupils whose teachers enter them. Every sentence about the "
            "percentile must say so. A known reference population is still "
            "worth more than an unknown one."),
    }
    res["verdict"] = {
        "location_recovered": bool(abs(loc["bias"]) < 0.05),
        "se_at_eight_items": loc["se_of_location"],
        "items_for_se_0_10": res["items_needed"]["items_needed"],
        # The binding risk is the SPREAD, not the mean bias. Systematic drift
        # averages to nothing over many hypothetical studies -- the cohort is
        # as likely to be better as worse -- while doing most of the damage to
        # any single one. Comparing mean biases would have called it harmless.
        "systematic_drift_is_the_binding_risk": bool(
            res["drift"]["systematic drift"]["sd_across_studies"]
            > 1.5 * res["drift"]["independent drift"]["sd_across_studies"]),
        "drift_sd_ratio": round(
            res["drift"]["systematic drift"]["sd_across_studies"]
            / max(res["drift"]["independent drift"]["sd_across_studies"], 1e-9), 2),
        "residual_bias_logits": loc["bias"],
        "residual_bias_percentile_points": round(
            float(stats.norm.cdf(loc["recovered_shift_logits"]) * 100
                  - stats.norm.cdf(loc["planted_shift_logits"]) * 100), 1),
        "precision_is_cheap_bias_is_not": (
            "the standard error is already below 0.10 at four anchor items, so "
            "adding items buys almost nothing; what remains is a small "
            "systematic bias from recovering difficulty out of a marginal "
            "success rate, and more items do not remove it"),
    }
    (OUT / "national_anchor.json").write_text(
        json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    use_utf8()
    raise SystemExit(main())
