"""user_profiles.py -- kategorizacia pouzivatelov: who is in the room?

Why this exists
---------------
The thesis assignment asks for three things from the proposed solution, and the
second is "kategorizaciu pouzivatelov" -- categorisation of users. The thesis
categorises PROMPTS (that is PEQI) and has never categorised PUPILS.

The supervisor's own notes ask the same question from the other direction, in
layer C of the three-layer measurement model:

    "Existuje skupina ziakov, ktora slepo doveruje a ma slabsie myslenie?"

That is not a question about averages. It is a question about whether the
population is a MIXTURE -- whether there is a subgroup for whom the generic
tool is actively harmful while the class mean looks fine. A mean can hide a
mixture completely: two profiles moving in opposite directions average to
nothing, and the study would report "no effect" about a population in which
half the pupils were harmed.

How
---
Latent profile analysis (a Gaussian mixture on continuous indicators) over the
layer-C measures plus the observed behaviour:

    reliance        self-reported reliance on the tool          (Hou et al.)
    ai_literacy     what the pupil understands about the tool   (Ng et al.)
    peqi            OBSERVED epistemic quality of their prompts (this thesis)
    calib_bias      overconfidence: judged minus actual         (this thesis)
    abhr            did they try before asking                  (this thesis)
    critical        transferable critical thinking              (layer B)

Two of those are self-reported and four are observed, and that mix is
deliberate: a typology built only from self-report measures what pupils say
about themselves, which is the thing this thesis exists to stop doing.

What the module checks
----------------------
  1. Can profiles be recovered when they are really there? (plant and refit)
  2. Does the procedure invent profiles when there are none? (fit a single
     homogeneous population and see what BIC says)
  3. How many pupils are needed before the answer is trustworthy?
  4. The payoff: does profile membership predict a DIFFERENT response to the
     conditions? A typology that does not interact with treatment is a
     description; one that does is a finding.

Run:  python user_profiles.py      -> out/user_profiles.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from console import use_utf8

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)

INDICATORS = ["reliance", "ai_literacy", "peqi", "calib_bias", "abhr", "critical"]

# The profiles the literature and the notes lead us to expect. These are
# PRE-SPECIFIED: naming them after the analysis would be naming clusters after
# whatever the data happened to produce, which is how cluster analysis earns its
# reputation. Values are in standard units.
EXPECTED_PROFILES = {
    # the one the notes ask about: leans on the tool, trusts it, thinks less
    "slepo doverujuci": dict(reliance=+1.1, ai_literacy=-0.7, peqi=-0.9,
                             calib_bias=+0.9, abhr=-0.9, critical=-0.7,
                             share=0.22),
    # uses the tool, but checks it
    "kriticky pouzivatel": dict(reliance=+0.5, ai_literacy=+0.9, peqi=+1.0,
                                calib_bias=-0.2, abhr=+0.8, critical=+0.9,
                                share=0.28),
    # avoids the tool; not the same as using it well
    "vyhybajuci sa": dict(reliance=-1.2, ai_literacy=-0.3, peqi=-0.1,
                          calib_bias=-0.1, abhr=+0.6, critical=+0.1,
                          share=0.20),
    # the middle, which is most pupils and is not a defect
    "priemerny": dict(reliance=0.0, ai_literacy=0.0, peqi=0.0,
                      calib_bias=0.0, abhr=0.0, critical=0.0,
                      share=0.30),
}


# ===========================================================================
def simulate_population(n: int = 330, profiles: dict | None = None,
                        within_sd: float = 0.62, seed: int = 404
                        ) -> pd.DataFrame:
    """Draw pupils from a known mixture, so recovery can be checked."""
    profiles = profiles or EXPECTED_PROFILES
    rng = np.random.default_rng(seed)
    names = list(profiles)
    shares = np.array([profiles[k]["share"] for k in names], float)
    shares = shares / shares.sum()
    which = rng.choice(len(names), size=n, p=shares)

    rows = []
    for i in range(n):
        p = profiles[names[which[i]]]
        row = {k: float(rng.normal(p[k], within_sd)) for k in INDICATORS}
        row["true_profile"] = names[which[i]]
        rows.append(row)
    return pd.DataFrame(rows)


def simulate_homogeneous(n: int = 330, seed: int = 405) -> pd.DataFrame:
    """One population, correlated indicators, NO latent groups.

    The hard case. Correlated continuous data will happily yield "clusters"
    that are slices of a single cloud, and a procedure that cannot tell the
    difference will find profiles in every dataset it is ever given.
    """
    rng = np.random.default_rng(seed)
    k = len(INDICATORS)
    # one general factor plus noise: the realistic null
    g = rng.normal(0, 1, n)
    loadings = np.array([-0.55, 0.60, 0.70, -0.45, 0.50, 0.65])
    x = g[:, None] * loadings[None, :] + rng.normal(0, 0.75, (n, k))
    df = pd.DataFrame(x, columns=INDICATORS)
    df["true_profile"] = "jednotna populacia"
    return df


# ===========================================================================
def fit_profiles(df: pd.DataFrame, k_range=range(1, 7), seed: int = 7,
                 covariance_type: str = "tied") -> dict:
    """Gaussian mixture over standardised indicators, model chosen by BIC.

    BIC rather than AIC: AIC over-extracts in mixtures, and over-extraction is
    the specific failure this analysis must avoid. Reporting an invented
    subgroup of harmed pupils would be worse than reporting none.

    COVARIANCE STRUCTURE IS NOT A DETAIL. The first version of this used
    `diag`, which forces each component's indicators to be uncorrelated. The
    indicators here are strongly correlated through a general factor -- a pupil
    who relies more also understands less and prompts worse -- and a diagonal
    model cannot represent that with one component. So it represents it by
    ADDING COMPONENTS: on a deliberately homogeneous population, BIC selected
    three profiles in 100 % of simulated datasets. Every one of them was an
    artefact of the covariance assumption.

    With `full` covariance a single component can absorb the correlation, and
    extra components have to earn their place. `compare_covariance_types()`
    reports both so the difference is visible rather than asserted.
    """
    from sklearn.mixture import GaussianMixture

    x = df[INDICATORS].to_numpy(float)
    x = (x - x.mean(axis=0)) / x.std(axis=0, ddof=1)

    rows = []
    best, best_bic = None, np.inf
    for k in k_range:
        gm = GaussianMixture(n_components=k, covariance_type=covariance_type,
                             n_init=8, random_state=seed, reg_covar=1e-4)
        gm.fit(x)
        bic = float(gm.bic(x))
        post = gm.predict_proba(x)
        # entropy: how cleanly pupils are assigned. Below ~0.8 the profiles
        # overlap so much that calling them groups is a stretch.
        ent = 1.0 - (-(post * np.log(post + 1e-12)).sum()
                     / (len(x) * np.log(max(k, 2))))
        rows.append({"k": k, "bic": round(bic, 1),
                     "entropy": round(float(ent), 3),
                     "smallest_share": round(float(post.argmax(1)
                                                   .astype(int)
                                                   .__len__() and
                                                   min(np.bincount(
                                                       post.argmax(1),
                                                       minlength=k))
                                                   / len(x)), 3)})
        if bic < best_bic:
            best, best_bic = gm, bic

    k_best = int(best.n_components)
    labels = best.predict(x)
    means = pd.DataFrame(best.means_, columns=INDICATORS)
    return {
        "k_selected": k_best,
        "by_k": rows,
        "entropy": next(r["entropy"] for r in rows if r["k"] == k_best),
        "profile_means": means.round(2).to_dict(orient="records"),
        "shares": [round(float(v), 3)
                   for v in np.bincount(labels, minlength=k_best) / len(x)],
        "labels": labels,
    }


def name_profiles(means: list[dict]) -> list[str]:
    """Attach the pre-specified names by nearest centroid, not by inspection.

    Naming clusters after looking at them is how a typology becomes
    unfalsifiable. The names are fixed in EXPECTED_PROFILES before any fit; a
    fitted profile that is far from every expected one is labelled
    'nezaradeny' rather than being given a new name on the spot.
    """
    out = []
    for m in means:
        best, bestd = "nezaradeny", np.inf
        for name, spec in EXPECTED_PROFILES.items():
            d = float(np.sqrt(sum((m[k] - spec[k]) ** 2 for k in INDICATORS)))
            if d < bestd:
                best, bestd = name, d
        out.append(best if bestd < 2.2 else "nezaradeny")
    return out


# ===========================================================================
def recovery_check(n: int = 330, n_sim: int = 40, seed: int = 11,
                   covariance_type: str = "full") -> dict:
    """Are planted profiles recovered, and are absent ones left alone?"""
    from sklearn.metrics import adjusted_rand_score
    found_k, agree = [], []
    for s in range(n_sim):
        df = simulate_population(n=n, seed=seed + s)
        fit = fit_profiles(df, seed=s, covariance_type=covariance_type)
        found_k.append(fit["k_selected"])
        agree.append(float(adjusted_rand_score(df["true_profile"],
                                               fit["labels"])))

    null_k = []
    for s in range(n_sim):
        df = simulate_homogeneous(n=n, seed=900 + s)
        null_k.append(fit_profiles(df, seed=s,
                                   covariance_type=covariance_type)["k_selected"])

    return {
        "n_pupils": n,
        "covariance_type": covariance_type,
        "true_k": len(EXPECTED_PROFILES),
        "recovered_k_mode": int(pd.Series(found_k).mode()[0]),
        "recovered_k_correct_rate": round(
            float(np.mean(np.array(found_k) == len(EXPECTED_PROFILES))), 3),
        "adjusted_rand_mean": round(float(np.mean(agree)), 3),
        "null_k_mode": int(pd.Series(null_k).mode()[0]),
        "null_finds_structure_rate": round(
            float(np.mean(np.array(null_k) > 1)), 3),
        "note": ("the second block is the one that matters: a homogeneous "
                 "population with correlated indicators must NOT be split. "
                 "Any procedure can find groups; the question is whether it "
                 "finds them when they are not there."),
    }


def compare_covariance_types(n: int = 330, n_sim: int = 25) -> dict:
    """Choose the covariance structure on evidence, not on habit.

    This comparison exists because the first two attempts both failed, in
    opposite directions, and the failures are instructive:

      diag   cannot represent correlated indicators within one component, so
             BIC represents the correlation by ADDING COMPONENTS. A
             deliberately homogeneous population was split every single time.
             The subgroups were an artefact of the model assumption.
      full   fixes that completely -- and then costs 21 free parameters per
             component, so BIC refuses to add components that are really
             there. No false profiles, but no true ones either.
      tied   one covariance matrix shared across components: correlation is
             represented once, and each extra component costs only its mean.
             This is what classical latent-profile analysis does, and the
             reason is exactly the trade-off above.

    Two criteria, and both must be met. A procedure that finds structure in
    noise is worse than useless here, because the finding it would produce --
    "there is a subgroup of harmed pupils" -- is precisely the claim a school
    would act on.
    """
    out = {}
    for cov in ("diag", "tied", "full", "spherical"):
        r = recovery_check(n=n, n_sim=n_sim, covariance_type=cov)
        out[cov] = {
            "null_finds_structure_rate": r["null_finds_structure_rate"],
            "null_k_mode": r["null_k_mode"],
            "adjusted_rand_mean": r["adjusted_rand_mean"],
            "recovered_k_mode": r["recovered_k_mode"],
            "usable": bool(r["null_finds_structure_rate"] <= 0.10
                           and r["adjusted_rand_mean"] >= 0.45),
        }
    usable = [c for c in ("tied", "full", "diag", "spherical")
              if out[c]["usable"]]
    out["chosen"] = usable[0] if usable else None
    out["lesson"] = (
        "the covariance assumption is not a technical detail: diag "
        "manufactured subgroups out of a homogeneous population in 100 % of "
        "simulated datasets, and full suppressed real ones. Neither failure "
        "would have been visible from a single fit to real data, which is why "
        "the choice is made against planted truth and a planted null.")
    return out


def sample_size_curve(sizes=(80, 150, 220, 330, 500), n_sim: int = 25,
                      seed: int = 21) -> list[dict]:
    """How many pupils before the typology is trustworthy?"""
    from sklearn.metrics import adjusted_rand_score
    rows = []
    for n in sizes:
        ks, ar = [], []
        for s in range(n_sim):
            df = simulate_population(n=n, seed=seed + s)
            fit = fit_profiles(df, seed=s, covariance_type="tied")
            ks.append(fit["k_selected"])
            ar.append(float(adjusted_rand_score(df["true_profile"],
                                                fit["labels"])))
        rows.append({"n": n,
                     "correct_k_rate": round(float(np.mean(
                         np.array(ks) == len(EXPECTED_PROFILES))), 3),
                     "adjusted_rand": round(float(np.mean(ar)), 3)})
    return rows


# ===========================================================================
def profile_by_condition(n: int = 330, harm_to_trusters: float = -0.45,
                         benefit_to_critical: float = 0.15,
                         seed: int = 33) -> dict:
    """The payoff: does the typology predict a different response to condition?

    A typology that merely describes is a table. A typology that moderates the
    treatment effect changes what a school should do -- it says WHICH pupils
    the generic tool hurts, and that is a different recommendation from "the
    tool hurts on average".

    Planted here: the blind-truster profile is harmed by the generic condition
    while the critical profile is mildly helped. The class mean can be near
    zero while both are true, which is exactly the situation the design must
    be able to see.
    """
    rng = np.random.default_rng(seed)
    df = simulate_population(n=n, seed=seed)
    effect = {
        "slepo doverujuci": harm_to_trusters,
        "kriticky pouzivatel": benefit_to_critical,
        "vyhybajuci sa": 0.0,
        "priemerny": -0.05,
    }
    df["gain_G_minus_K"] = [
        rng.normal(effect[p], 0.8) for p in df["true_profile"]]

    overall = float(df["gain_G_minus_K"].mean())
    se_overall = float(df["gain_G_minus_K"].std(ddof=1) / np.sqrt(len(df)))

    by = (df.groupby("true_profile")["gain_G_minus_K"]
            .agg(["mean", "std", "count"]).round(3))
    rows = [{"profile": p, "mean_gain": float(r["mean"]),
             "n": int(r["count"]),
             "se": round(float(r["std"] / np.sqrt(r["count"])), 3)}
            for p, r in by.iterrows()]

    spread = max(r["mean_gain"] for r in rows) - min(r["mean_gain"] for r in rows)
    return {
        "overall_mean_gain": round(overall, 3),
        "overall_se": round(se_overall, 3),
        "overall_significant": bool(abs(overall / se_overall) > 1.96),
        "by_profile": rows,
        "spread_across_profiles": round(float(spread), 3),
        "reading": ("the overall effect is small and the spread across "
                    "profiles is large: averaging over a mixture reports "
                    "'no effect' about a population in which one group was "
                    "clearly harmed. This is the concrete reason the "
                    "assignment's 'kategorizacia pouzivatelov' is not "
                    "decoration."),
    }


# ===========================================================================
def main() -> int:
    df = simulate_population()
    fit = fit_profiles(df)
    names = name_profiles(fit["profile_means"])

    res = {
        "purpose": ("assignment clause: 'kategorizacia pouzivatelov'; "
                    "supervisor's layer C: is there a group that blindly "
                    "trusts and thinks less?"),
        "indicators": INDICATORS,
        "self_reported": ["reliance", "ai_literacy"],
        "observed": ["peqi", "calib_bias", "abhr", "critical"],
        "expected_profiles": {k: {kk: vv for kk, vv in v.items()}
                              for k, v in EXPECTED_PROFILES.items()},
        "illustrative_fit": {
            "k_selected": fit["k_selected"],
            "entropy": fit["entropy"],
            "shares": fit["shares"],
            "named": names,
            "profile_means": fit["profile_means"],
        },
        "covariance_choice": compare_covariance_types(),
        "recovery": recovery_check(covariance_type="tied"),
        "sample_size": sample_size_curve(),
        "moderation": profile_by_condition(),
    }
    rec = res["recovery"]
    mod = res["moderation"]
    n_needed = next((r["n"] for r in res["sample_size"]
                     if r["adjusted_rand"] >= 0.60), None)
    res["verdict"] = {
        "covariance_chosen": res["covariance_choice"]["chosen"],
        "adjusted_rand_at_planned_n": rec["adjusted_rand_mean"],
        "does_not_invent_profiles": bool(rec["null_finds_structure_rate"] < 0.10),
        "entropy_adequate": bool(fit["entropy"] >= 0.70),
        "typology_moderates_the_effect": bool(
            mod["spread_across_profiles"] > 0.30),
        "mean_would_have_missed_it": bool(not mod["overall_significant"]),
        "n_for_confirmatory_typology": n_needed,
        "status_at_planned_sample": (
            "confirmatory" if rec["adjusted_rand_mean"] >= 0.60
            else "exploratory"),
        "reading": (
            "At the planned sample the typology recovers planted profiles "
            "only moderately (adjusted Rand around %.2f), so it is reported "
            "as EXPLORATORY and never as a confirmatory claim. It would need "
            "roughly %s pupils to be confirmatory. That is not a reason to "
            "drop it: the moderation result shows the class mean is near zero "
            "while one profile is clearly harmed, so a design that reports "
            "only means would describe that population wrongly."
            % (rec["adjusted_rand_mean"], n_needed)),
    }
    (OUT / "user_profiles.json").write_text(
        json.dumps({k: v for k, v in res.items()}, indent=2,
                   ensure_ascii=False, default=float), encoding="utf-8")
    print(json.dumps(res["verdict"], indent=2, ensure_ascii=False))
    print("\nrecovery:", json.dumps(rec, indent=1, ensure_ascii=False))
    print("\nmoderation:", json.dumps(mod, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    use_utf8()
    raise SystemExit(main())
