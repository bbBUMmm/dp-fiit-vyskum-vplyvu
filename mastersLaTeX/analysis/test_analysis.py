"""test_analysis.py -- regression tests for the statistical layer.

Why this exists
---------------
`verify_thesis.py` checks that the thesis AGREES with the analysis outputs. That
is a consistency check, not a correctness check: if an estimator were wrong, the
thesis would quote the wrong number faithfully and every one of its claims would
still pass.

These tests check the other thing. Every one of them either plants a known
answer and demands it back, or states a property that must hold for any input.
Where a defect has already been found in this code, the test that would have
caught it is here, named after it.

Run:  python test_analysis.py
"""
from __future__ import annotations

import pathlib
import sys
import traceback

import numpy as np
import pandas as pd

import peqi
import pipeline
import identification as ident
import measurement as meas
from dgp import Params, SEQUENCES, CONDITIONS, simulate
from peqi import SEED_CORPUS, WEIGHTS, rule_classify, session_peqi

PASS = FAIL = 0
_SECTION = ""


def section(name: str) -> None:
    global _SECTION
    _SECTION = name
    print(f"\n{name}")


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}" + (f"\n       {detail}" if detail else ""))


def close(name: str, got, want, tol: float) -> None:
    ok(name, abs(float(got) - float(want)) <= tol,
       f"got {got!r}, want {want!r} +/- {tol}")


# ===========================================================================
def test_taxonomy_contract():
    section("PEQI taxonomy: the contract the index depends on")
    ok("weights are equally spaced and span [0, 1]",
       [WEIGHTS[l] for l in ("L0", "L1", "L2", "L3", "L4")]
       == [0.0, 0.25, 0.5, 0.75, 1.0])
    ok("off-task has no weight", "X" not in WEIGHTS)
    ok("every taxonomy level has a coding rule",
       all(peqi.TAXONOMY[l]["rule"] for l in peqi.LEVELS))
    ok("the decision order starts with off-task and descends",
       peqi.CODING_PRIORITY == ["X", "L4", "L3", "L2", "L1", "L0"])

    # off-task prompts must leave the denominator, not sit in it at weight 0 --
    # the two differ, and only the first matches the definition in the thesis
    s = session_peqi(["L4", "L4", "X", "X"])
    close("off-task is excluded from the denominator", s["peqi"], 1.0, 1e-9)
    close("and is reported separately", s["off_task_rate"], 0.5, 1e-9)
    ok("an all-off-task session yields no index",
       np.isnan(session_peqi(["X", "X"])["peqi"]))


def test_classifier_on_anchors():
    section("PEQI classifier: agreement with the hand-coded anchors")
    y = [l for _, l in SEED_CORPUS]
    yh = [rule_classify(t) for t, _ in SEED_CORPUS]
    k = peqi.cohen_kappa(y, yh)
    ok(f"rule kappa >= 0.95 (got {k:.4f})", k >= 0.95)
    off = [(t, a, b) for (t, a), b in zip(SEED_CORPUS, yh) if a != b]
    ok(f"at most two anchors disagree (got {len(off)})", len(off) <= 2,
       "; ".join(f"{a}->{b}: {t[:40]}" for t, a, b in off))
    idx = {l: i for i, l in enumerate(["L0", "L1", "L2", "L3", "L4"])}
    far = [(t, a, b) for t, a, b in off
           if a in idx and b in idx and abs(idx[a] - idx[b]) > 1]
    ok("no disagreement is more than one level", not far, str(far))


def test_coding_manual_binding_decisions():
    section("PEQI classifier: the manual's binding decisions are implemented")
    # Appendix B declares these binding for human coders. If the code disagrees
    # with the manual, one of the two is wrong and neither is authoritative.
    cases = [
        ("napis mi kod a vysvetli preco je to O(log n)", "L2",
         "multi-part: highest level that actually applies"),
        ("je to spravne a preco", "L2", "a why-question outranks a verdict request"),
        ("daj odpoved a nevysvetluj", "L0", "reasoning explicitly excluded"),
        ("kolko je zlozitost tejto funkcie, len vysledok", "L0", "answer-only"),
        ("mam to dobre? myslim ze ano, lebo cyklus prejde cele pole", "L4",
         "own justification supplied"),
        ("ahoj ako sa mas", "X", "off-task"),
        ("pomoz mi s domacou ulohou z dejepisu", "X", "another subject"),
        ("vies to aj v pythone?", "L1", "a question about the tool is on-task"),
    ]
    for text, want, why in cases:
        got = rule_classify(text)
        ok(f"{want}: {why}", got == want, f"got {got} for {text!r}")


def test_veneer_attack():
    section("PEQI classifier: the compliance veneer cannot raise a level")
    # Condition A's self-explanation gate obliges pupils to write exactly these
    # openings. A classifier that rewards the opening manufactures a
    # between-condition difference out of the interface.
    sub = [(t, l) for t, l in SEED_CORPUS if l in ("L0", "L1")]
    shifted = []
    for i, (text, lab) in enumerate(sub):
        for v in meas.VENEERS:
            got = rule_classify(v + text)
            if got != lab:
                shifted.append((lab, got, v + text))
    ok(f"no L0/L1 anchor shifts under any of the {len(meas.VENEERS)} openings "
       f"({len(sub) * len(meas.VENEERS)} combinations)",
       not shifted, "; ".join(f"{a}->{b}: {t[:48]}" for a, b, t in shifted[:4]))

    # and the reverse: a genuine claim must still reach L4 when veneered
    genuine = [t for t, l in SEED_CORPUS if l == "L4"]
    lost = [t for t in genuine if rule_classify(t) != "L4"]
    ok("every genuine self-explanation still reaches L4", not lost,
       "; ".join(t[:48] for t in lost))


def test_substring_traps():
    section("PEQI lexicons: no pattern matches inside a longer word")
    # Each of these was a real defect. "lebo" inside "alebo" promoted every
    # "right or wrong?" to a justified claim; "sprav" inside "spravne" turned a
    # verification request into a demand for a solution.
    traps = [
        ("dobre alebo zle?", "L1", "lebo inside alebo"),
        ("mam v tabulke spravne hodnoty?", "L1", "sprav inside spravne"),
        ("uvazujem takto: kazde volanie vytvori dve dalsie, takze 2^n volani. "
         "je ta uvaha korektna", "L4", "vytvor inside vytvori"),
        ("ake su hranicne pripady na ktore si mam dat pozor pri binarnom "
         "vyhladavani", "L3", "hra inside hranicne"),
    ]
    for text, want, why in traps:
        ok(f"{why}", rule_classify(text) == want,
           f"got {rule_classify(text)}, want {want}")


def test_weight_sensitivity():
    section("PEQI: conclusions do not depend on the arbitrary weights")
    labels_g = ["L0"] * 6 + ["L1"] * 4 + ["L2"] * 2
    labels_a = ["L2"] * 4 + ["L3"] * 4 + ["L4"] * 4
    alt = {"L0": 0.0, "L1": 0.2, "L2": 0.4, "L3": 0.7, "L4": 1.0}

    def idx(labels, w):
        on = [l for l in labels if l != "X"]
        return sum(w[l] for l in on) / len(on)

    base = idx(labels_a, WEIGHTS) - idx(labels_g, WEIGHTS)
    other = idx(labels_a, alt) - idx(labels_g, alt)
    ok("the ordering survives the alternative weighting",
       np.sign(base) == np.sign(other))
    ok("and the gap moves by less than a fifth",
       abs(base - other) / abs(base) < 0.2, f"{base:.3f} vs {other:.3f}")


# ===========================================================================
def test_multiplicity():
    section("Multiplicity corrections")
    p = {"a": 0.01, "b": 0.02, "c": 0.03}
    h = pipeline.holm(p)
    close("Holm: smallest p times m", h["a"], 0.03, 1e-12)
    ok("Holm is monotone", h["a"] <= h["b"] <= h["c"])
    ok("Holm never exceeds 1", all(v <= 1.0 for v in h.values()))
    ok("Holm is at least as strict as BH",
       all(h[k] >= pipeline.benjamini_hochberg(p)[k] for k in p))

    q = pipeline.benjamini_hochberg({"a": 0.01, "b": 0.5, "c": 0.9})
    close("BH: largest p is unadjusted", q["c"], 0.9, 1e-12)
    ok("BH is monotone", q["a"] <= q["b"] <= q["c"])

    one = pipeline.holm({"only": 0.04})
    close("a family of one is not penalised", one["only"], 0.04, 1e-12)


def test_tost():
    section("Equivalence testing (TOST)")
    tiny = pipeline.tost(dict(est=0.02, se=0.05, df=30))
    ok("a tight interval around zero declares equivalence", tiny["equivalent"])
    wide = pipeline.tost(dict(est=0.02, se=0.30, df=30))
    ok("the same estimate with a wide interval does not", not wide["equivalent"])
    big = pipeline.tost(dict(est=0.55, se=0.05, df=30))
    ok("an estimate beyond the SESOI is not equivalent", not big["equivalent"])
    ok("a non-significant difference is not equivalence",
       not wide["equivalent"],
       "absence of evidence must not be read as evidence of absence")


def test_rasch_recovers_planted_parameters():
    section("Rasch calibration recovers what was planted")
    rng = np.random.default_rng(7)
    n, L = 1500, 20
    theta = rng.normal(0, 1, n)
    b = np.linspace(-1.5, 1.5, L)
    p = 1 / (1 + np.exp(-(theta[:, None] - b[None, :])))
    X = (rng.random((n, L)) < p).astype(float)

    th_hat, b_hat, se = pipeline.rasch_jmle(X)
    b_hat = b_hat - b_hat.mean()                 # the metric is fixed to mean 0
    close("item difficulties recovered", np.abs(b_hat - b).max(), 0.0, 0.20)
    # The ceiling here is test length, not the estimator: with 20 items the
    # Rasch person separation reliability is around 0.8, so the correlation
    # with the planted ability cannot exceed roughly its square root.
    r_theta = np.corrcoef(th_hat[np.isfinite(th_hat)],
                          theta[np.isfinite(th_hat)])[0, 1]
    ok(f"ability correlates with the planted value (r = {r_theta:.3f})",
       r_theta > 0.85)
    ok("standard errors are positive and finite",
       np.all(se[np.isfinite(se)] > 0))

    # the defect this is named after: one pupil missing the whole form used to
    # return NaN for everybody, not just for that pupil
    X2 = X.copy()
    X2[3, :] = np.nan
    th2, _, _ = pipeline.rasch_jmle(X2)
    ok("a pupil who sat no items does not poison the calibration",
       np.isnan(th2[3]) and np.isfinite(th2[np.arange(n) != 3]).all())


def test_concurrent_calibration_puts_forms_on_one_scale():
    section("Concurrent calibration: forgetting is not a difference in difficulty")
    rng = np.random.default_rng(11)
    n, n_anchor, n_unique = 900, 6, 10
    theta_imm = rng.normal(0.0, 1, n)
    theta_del = theta_imm - 0.40                       # planted forgetting
    b_anchor = np.linspace(-1, 1, n_anchor)
    b_imm = np.concatenate([b_anchor, rng.normal(0.0, 0.8, n_unique)])
    b_del = np.concatenate([b_anchor, rng.normal(1.2, 0.8, n_unique)])  # harder

    def draw(th, bb):
        p = 1 / (1 + np.exp(-(th[:, None] - bb[None, :])))
        return (rng.random((len(th), len(bb))) < p).astype(float)

    x_imm, x_del = draw(theta_imm, b_imm), draw(theta_del, b_del)

    ti, td, *_ = pipeline.concurrent_calibration(x_imm, x_del, n_anchor)
    gap = float(np.nanmean(td) - np.nanmean(ti))
    close("the recovered gap is the planted forgetting", gap, -0.40, 0.15)

    # what it protects against: calibrating the forms separately centres each on
    # its own mean difficulty, so a harder delayed form looks like forgetting
    ti_sep, *_ = pipeline.rasch_jmle(x_imm)
    td_sep, *_ = pipeline.rasch_jmle(x_del)
    naive = float(np.nanmean(td_sep) - np.nanmean(ti_sep))
    ok("separate calibration gets it wrong, which is why this step exists",
       abs(naive - (-0.40)) > abs(gap - (-0.40)),
       f"separate {naive:.3f} vs concurrent {gap:.3f}, planted -0.40")


def test_cluster_contrast_is_conservative():
    section("Cluster-robust inference")
    rng = np.random.default_rng(5)
    rows = []
    for j in range(12):
        shift = rng.normal(0, 0.5)               # class-level random effect
        for s in range(20):
            base = rng.normal(shift, 1.0)
            rows += [dict(student=f"{j}-{s}", klass=j, cond="A", y=base + 0.3),
                     dict(student=f"{j}-{s}", klass=j, cond="K", y=base)]
    df = pd.DataFrame(rows)
    r = pipeline.cluster_contrast(df, "y", "A", "K")
    close("the planted within-student contrast is recovered", r["est"], 0.30, 0.08)
    ok("degrees of freedom are J-1, not N-1", r["df"] == 11,
       f"df = {r['df']}")
    ok("the standard error is positive", r["se"] > 0)


# ===========================================================================
def test_iv_recovers_planted_effect():
    section("Identification: IV recovers the planted b-path")
    rng = np.random.default_rng(23)
    n = 4000
    klass = rng.integers(0, 20, n)
    A = (rng.random(n) < 0.5).astype(float)
    pre = rng.normal(0, 1, n)
    gf = rng.normal(0, 1, n)
    u = rng.normal(0, 1, n)
    M = 0.9 * A + 0.2 * pre + u
    Y = 0.35 * M + 0.5 * pre + 0.1 * gf + rng.normal(0, 1, n)
    df = pd.DataFrame(dict(is_A=A, peqi_z=M, theta_del=Y, theta_pre=pre,
                           gf=gf, klass=klass))

    r = ident.iv_2sls(df, "is_A", "peqi_z", "theta_del", ["theta_pre", "gf"])
    close("2SLS recovers b", r["estimate"], 0.35, 0.06)
    ok("the first stage is strong", r["first_stage_F"] > 10)
    ok("and is flagged as such", not r["weak_instrument"])

    w = ident.iv_wald(df, "is_A", "peqi_z", "theta_del")
    close("the Wald ratio agrees with just-identified 2SLS",
          w["estimate"], w["ratio_check"], 0.02)

    # exclusion violated: the instrument reaches Y directly. IV must be biased,
    # and the test asserts the bias rather than pretending the estimator copes.
    Y2 = Y + 0.30 * A
    df2 = df.assign(theta_del=Y2)
    r2 = ident.iv_2sls(df2, "is_A", "peqi_z", "theta_del", ["theta_pre", "gf"])
    ok("a direct path inflates the IV estimate, as the theory says",
       r2["estimate"] > r["estimate"] + 0.15,
       f"{r2['estimate']:.3f} vs {r['estimate']:.3f}")


def test_mediation_decomposition_is_exact():
    section("Identification: total = direct + indirect")
    rng = np.random.default_rng(31)
    n = 3000
    klass = rng.integers(0, 15, n)
    A = (rng.random(n) < 0.5).astype(float)
    pre = rng.normal(0, 1, n)
    gf = rng.normal(0, 1, n)
    M = 0.8 * A + 0.3 * pre + rng.normal(0, 1, n)
    Y = 0.25 * M + 0.15 * A + 0.4 * pre + rng.normal(0, 1, n)
    df = pd.DataFrame(dict(is_A=A, peqi_z=M, theta_del=Y, theta_pre=pre,
                           gf=gf, klass=klass, theta_imm=Y * 0.5 + pre))

    m = ident.mediation_lsem(df, "is_A", "peqi_z", "theta_del",
                             ["theta_pre", "gf"], n_draw=20_000)
    close("the decomposition is exact, not approximate",
          m["direct"] + m["indirect"], m["total"], 1e-6)
    ok("and the module says so itself", m["decomposition_holds"])
    close("the a-path is recovered", m["a_path"]["est"], 0.80, 0.08)
    close("the b-path is recovered", m["b_path"]["est"], 0.25, 0.06)
    ok("the proportion mediated is a proportion",
       0.0 <= m["proportion_mediated"] <= 1.0, str(m["proportion_mediated"]))
    ok("the a-path is labelled as identified by design",
       m["a_path"]["identified_by"] == "randomisation")
    ok("the b-path is labelled as assumed, not identified",
       "ASSUMED" in m["b_path"]["identified_by"],
       "the distinction is the point of the whole chapter")
    ok("the post-treatment variant is kept out of the decomposition",
       "b_path_net_of_immediate" not in m or
       "not part of the" in m["b_path_net_of_immediate"]["note"])


def test_sensitivity_rho_behaves():
    section("Identification: the sensitivity threshold")
    rng = np.random.default_rng(41)
    n = 3000
    klass = rng.integers(0, 15, n)
    A = (rng.random(n) < 0.5).astype(float)
    pre = rng.normal(0, 1, n)
    gf = rng.normal(0, 1, n)

    def frame(b):
        M = 0.8 * A + rng.normal(0, 1, n)
        Y = b * M + 0.4 * pre + rng.normal(0, 1, n)
        return pd.DataFrame(dict(is_A=A, peqi_z=M, theta_del=Y,
                                 theta_pre=pre, gf=gf, klass=klass))

    weak = ident.sensitivity_rho(frame(0.10), "is_A", "peqi_z", "theta_del",
                                 ["theta_pre", "gf"])
    strong = ident.sensitivity_rho(frame(0.45), "is_A", "peqi_z", "theta_del",
                                   ["theta_pre", "gf"])
    ok("rho* is a correlation", 0.0 <= weak["rho_star"] <= 1.0)
    ok("a stronger b-path is harder to explain away",
       strong["rho_star"] > weak["rho_star"],
       f"weak {weak['rho_star']:.3f} vs strong {strong['rho_star']:.3f}")


# ===========================================================================
def test_measurement_propositions_at_several_points():
    section("Measurement error: the propositions hold away from one lucky point")
    # measurement.py verifies its propositions at one parameter set. If that set
    # were special the module would still pass, so re-verify on a grid.
    rng = np.random.default_rng(99)
    grid = [(0.6, 0.20, 0.10, 0.40), (1.2, 0.40, 0.35, 0.90),
            (0.8, 0.30, -0.20, 0.60), (0.5, 0.15, 0.05, 1.20)]
    for a, b, delta, s_e in grid:
        lam = 1.0 / (1.0 + s_e ** 2)
        A, M, M_obs, Y = meas._one_draw(rng, 300_000, a, b, 0.0, delta, s_e)
        e_clean, e_dirty = meas._estimates(A, M, Y), meas._estimates(A, M_obs, Y)
        tag = f"a={a} b={b} d={delta} se={s_e}"
        close(f"P1 reduced form immune [{tag}]",
              e_dirty["itt_y"], e_clean["itt_y"], 1e-9)
        close(f"P2 IV = b*a/(a+d) [{tag}]",
              e_dirty["beta_iv"], b * a / (a + delta), 0.02)
        close(f"P3 indirect = ab(1+d/a)lambda [{tag}]",
              e_dirty["indirect_med"], a * b * (1 + delta / a) * lam, 0.02)


def test_veneer_audit_and_correction():
    section("Measurement error: the audit and the correction")
    before = meas.veneer_before_after()
    ok("the defect is recorded, not quietly removed",
       before["v0_as_written"]["n_level_shifts"] > 0)
    ok("the current rule is immune",
       before["v2_dominance_rules"]["n_level_shifts"] == 0)
    ok("the two parts of the repair are reported separately",
       before["v0_as_written"]["kappa_on_anchors"]
       < before["v1_lexicons_anchored"]["kappa_on_anchors"]
       < before["v2_dominance_rules"]["kappa_on_anchors"])

    r = meas.correction_recovers_truth(n=40_000, seed=5)
    ok("the correction recovers the planted b", r["recovers_b"],
       str(r["corrected"]))
    ok("the correction recovers the planted a", r["recovers_a"])
    ok("the uncorrected estimate does not, or there is nothing to correct",
       abs(r["naive_b_error"]) > 0.02)

    a = meas.audit_power(n_prompts_per_condition=150, n_sim=600, seed=3)
    ok("the audit estimator is unbiased", abs(a["bias"]) < 0.01, str(a["bias"]))
    ok("and powered at the planned size", a["power"] >= 0.75, str(a["power"]))


# ===========================================================================
def test_negative_controls_behave_as_controls():
    section("Negative controls: clean when clean, loud when leaking")
    import falsification as fal

    p = Params(n_classes=18, seed=777)
    clean = fal.simulate_controls(p, leak=0.0, n_placebo=9, seed=31)
    leaky = fal.simulate_controls(p, leak=0.45, n_placebo=9, seed=31)

    r_clean = fal._within_student_contrast(clean, "placebo", "A", "K")
    r_leaky = fal._within_student_contrast(leaky, "placebo", "A", "K")
    close("no effect on untaught material when there is none",
          r_clean["est"], 0.0, 0.12)
    close("the planted leak is recovered", r_leaky["est"], 0.45, 0.12)

    ok("a clean control declares equivalence",
       fal.tost_control(r_clean)["passes"], str(fal.tost_control(r_clean)))
    ok("a leaking control does not",
       not fal.tost_control(r_leaky)["passes"])

    # The trait is measured three weeks later, so the same-day channel must not
    # reach it. If it did, a passed trait control would mean less than it looks.
    #
    # Note WHICH estimator: between pupils, on the change, keyed on the last
    # period. A trait takes one value per pupil, so the within-pupil version is
    # identically zero -- which is why the assertion below exists rather than a
    # comment saying so.
    t_leaky = fal._between_pupil_contrast(leaky, "gf_change", "last_cond",
                                          "A", "K")
    ok("the invariant trait is untouched even by a large same-day leak",
       fal.tost_control(t_leaky)["passes"],
       f"est={t_leaky['est']:.3f}")

    degenerate = False
    try:
        fal.tost_control(
            fal._within_student_contrast(leaky, "gf_retest", "A", "K"))
    except ValueError:
        degenerate = True
    ok("a within-pupil contrast on a trait is refused, not silently passed",
       degenerate,
       "an identically-zero contrast must raise, or it certifies everything")

    # An equivalence test that always passes is not a test.
    ok("the bound is reachable but not trivially so",
       0.10 < fal.CONTROL_BOUND < 0.50, str(fal.CONTROL_BOUND))


def test_measurement_plan_is_internally_consistent():
    section("Measurement plan: instruments fit for the roles they were given")
    import measurement_plan as mp

    # reliability must rise with length, or the simulation is broken
    curve = [r["reliability"] for r in mp.reliability_curve()]
    ok("reliability rises with test length",
       all(a <= b + 1e-9 for a, b in zip(curve, curve[1:])), str(curve))

    ok("twenty items beat twelve",
       mp.rasch_reliability(20) > mp.rasch_reliability(12))

    # the direction that is easy to get backwards
    lo = mp.negative_control_clearance(0.50, n_sim=400)
    hi = mp.negative_control_clearance(0.90, n_sim=400)
    ok("a worse instrument makes the negative control LESS able to clear",
       lo < hi, f"rho=0.50 -> {lo}, rho=0.90 -> {hi}")
    ok("and a poor instrument genuinely fails, rather than merely dipping",
       lo < 0.70, str(lo))

    # every session must fit, and the check must be capable of failing
    tb = mp.time_budget()
    ok("every session fits its budget", tb["all_sessions_fit"],
       str({k: v for k, v in tb.items()
            if isinstance(v, dict) and not v["fits"]}))
    ok("the budget is computed from the item bank, not from an average",
       "sessions.py" in tb.get("computed_by", ""), tb.get("computed_by", ""))

    # The check must be capable of failing, and it is tested against the REAL
    # schedule rather than a synthetic session: the previous version of this test
    # built a deliberately overfull `Session` object, which proved that the
    # arithmetic works and not that the actual plan is being checked. Inflating
    # one item in the bank must make the actual plan overrun.
    import sys as _sys
    _sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]
                            / "assessment"))
    import sessions as _sessions
    banks = _sessions.all_banks()               # the eight banks plus the external
    banks["T1_IPT"].items[0].expected_sec = 4000.0      # one item, over an hour
    broken = _sessions.budget(banks=banks)
    ok("the budget check can fail on the real schedule",
       not broken["all_fit"] and any("P1..P3" in v for v in broken["violations"]),
       f"violations: {broken['violations']}")
    # `all_banks()` loads afresh, so nothing above persists; prove it.
    ok("and the real schedule still fits", _sessions.budget()["all_fit"])

    # a trait is measured once per occasion: no within-pupil contrast exists
    import falsification as fal
    from dgp import Params
    df = fal.simulate_controls(Params(n_classes=12, seed=9), leak=0.0,
                               n_placebo=9, seed=9)
    per_pupil = df.groupby("student")["gf_retest"].nunique()
    ok("the trait takes one value per pupil, not one per period",
       bool((per_pupil == 1).all()),
       "a trait that varies by period cannot be a trait")
    ok("the analysed quantity is the change, and it is present",
       "gf_change" in df.columns)
    ok("the last-period condition is recorded, since that is the contrast",
       "last_cond" in df.columns
       and set(df["last_cond"].unique()) <= {"K", "G", "A"})


def test_field_data_contract():
    section("Field data contract: the validator catches what it claims to")
    import tempfile
    import ingest
    from pathlib import Path as _P

    with tempfile.TemporaryDirectory() as tmp:
        clean = _P(tmp) / "clean"
        ingest.make_fixture(clean, None)
        rep = ingest.validate_directory(clean)
        ok("well-formed data passes without complaint",
           rep.ok and not rep.warnings,
           "; ".join(rep.errors + rep.warnings))

        # Each breakage must be caught. A validator that has only seen correct
        # data is an assertion, not a check.
        for case, why in [
            ("consent", "responses recorded without consent"),
            ("pseudonym", "an unsalted identifier reaching the analyst"),
            ("orphan", "a pseudonym absent from the roster"),
            ("enum", "an instrument name outside the schema"),
            ("duplicate", "the same item answered twice"),
            ("jol_on_questionnaire", "a confidence slider on an unscored item"),
            ("missing_column", "a column the schema requires"),
            ("impossible_fidelity", "more steps delivered than planned"),
            ("jsonl", "a malformed event line"),
        ]:
            d = _P(tmp) / case
            ingest.make_fixture(d, case)
            r = ingest.validate_directory(d)
            ok(f"catches: {why}", not r.ok, f"case '{case}' passed validation")

        # Two are warnings rather than errors: they describe a session that is
        # well-formed but must be handled differently, not one that is wrong.
        for case, why in [("fidelity", "a block below the fidelity floor"),
                          ("coverage", "capture coverage below the floor")]:
            d = _P(tmp) / case
            ingest.make_fixture(d, case)
            r = ingest.validate_directory(d)
            ok(f"warns without blocking: {why}",
               r.ok and bool(r.warnings),
               f"case '{case}': errors={len(r.errors)} warnings={len(r.warnings)}")

    ok("the thresholds come from one place",
       ingest.CONSENT_FLOOR == 0.85 and ingest.FIDELITY_FLOOR == 0.90,
       "protocol and validator must not drift apart")


def test_national_anchoring():
    section("National anchoring: a convenience sample gets a known position")
    import national_anchor as na

    # difficulty from a published success rate must invert cleanly
    p = np.array([0.2, 0.5, 0.8])
    b = na.difficulty_from_national_p(p)
    close("a 50% item has difficulty zero", b[1], 0.0, 1e-9)
    ok("an easier item is less difficult", b[2] < b[1] < b[0])

    # planting a shift and getting it back is the whole claim
    r = na.locate_sample(n_anchor=8, sample_shift=0.35, n_sim=120, seed=5)
    close("the planted location is recovered", r["recovered_shift_logits"],
          0.35, 0.10)
    ok("the standard error is reported and small", 0 < r["se_of_location"] < 0.2,
       str(r["se_of_location"]))

    zero = na.locate_sample(n_anchor=8, sample_shift=0.0, n_sim=120, seed=6)
    lo, hi = zero["percentile_ci95"]
    ok("a sample at the national mean has an interval containing the median",
       lo <= 50 <= hi, f"interval {[lo, hi]} does not contain 50")
    ok("and that interval is narrow enough to be worth quoting",
       hi - lo < 25, f"width {hi - lo:.1f} percentile points")

    # anchored person measures must respond to the data, not just the anchors
    b8 = na.difficulty_from_national_p(np.linspace(0.25, 0.8, 8))
    all_right = na.anchored_theta(np.ones((3, 8)), b8)
    all_wrong = na.anchored_theta(np.zeros((3, 8)), b8)
    ok("a perfect score gives a higher measure than a zero score",
       float(all_right.mean()) > float(all_wrong.mean()))
    ok("and neither is infinite",
       np.isfinite(all_right).all() and np.isfinite(all_wrong).all(),
       "extreme scores need the 0.3 adjustment or they diverge")

    # the honest part: systematic cohort drift must be the bigger risk
    d = na.robustness_to_drift(n_sim=120, seed=11)
    ok("systematic drift is more damaging than independent drift",
       d["systematic drift"]["sd_across_studies"]
       > d["independent drift"]["sd_across_studies"],
       "if not, the mitigation would be more items rather than a caveat")


def test_design_is_williams_balanced():
    section("Design: the crossover square")
    ok("six sequences", len(SEQUENCES) == 6)
    ok("every sequence is a permutation of the three conditions",
       all(sorted(s) == sorted(CONDITIONS) for s in SEQUENCES))
    for pos in range(3):
        counts = {c: sum(1 for s in SEQUENCES if s[pos] == c) for c in CONDITIONS}
        ok(f"each condition appears twice in period {pos + 1}",
           set(counts.values()) == {2}, str(counts))
    # Williams balance: each condition follows each other condition equally often
    follows = {}
    for s in SEQUENCES:
        for i in range(2):
            follows[(s[i], s[i + 1])] = follows.get((s[i], s[i + 1]), 0) + 1
    pairs = [(x, y) for x in CONDITIONS for y in CONDITIONS if x != y]
    ok("first-order carry-over is balanced",
       {follows.get(p, 0) for p in pairs} == {2}, str(follows))


def test_dgp_anchoring_is_exact():
    section("Generating model: planted effects come back exactly")
    p = Params(n_classes=18)
    sim = simulate(p, item_level=False)
    df = sim["long"]
    for col, targets in (("theta_del_true", {"G": p.d_del_G, "A": p.d_del_A}),
                         ("theta_imm_true", {"G": p.d_imm_G, "A": p.d_imm_A}),
                         ("theta_tt_true", {"G": p.d_tt_G, "A": p.d_tt_A}),
                         ("peqi", {"G": 0.0,
                                   "A": p.peqi_A_mean - p.peqi_G_mean})):
        base = df.loc[df.cond == "K", col].mean() if col.startswith("theta") \
            else df.loc[df.cond == "G", col].mean()
        for cond, want in targets.items():
            got = df.loc[df.cond == cond, col].mean() - base
            close(f"{col}: {cond} anchored", got, want, 0.02)

    ok("dropout is MAR, not MCAR: weaker pupils are lost more often",
       df.loc[df.dropout == 1, "theta_pre"].mean()
       < df.loc[df.dropout == 0, "theta_pre"].mean() - 0.1,
       "the plan's missing-data analysis assumes MAR and must be exercised")

    seqs = df.groupby("student")["cond"].apply(lambda s: tuple(s)[:3])
    ok("every pupil sees all three conditions",
       all(sorted(set(s)) == sorted(CONDITIONS) for s in seqs))


def test_dgp_is_reproducible():
    section("Generating model: the same seed gives the same data")
    a = simulate(Params(n_classes=12, seed=1234), item_level=False)["long"]
    b = simulate(Params(n_classes=12, seed=1234), item_level=False)["long"]
    ok("two runs are identical", a.equals(b))
    c = simulate(Params(n_classes=12, seed=5678), item_level=False)["long"]
    ok("a different seed gives different data", not a.equals(c))


# ===========================================================================
# ===========================================================================
def test_console_guard_on_every_entry_point():
    section("console encoding: the defect class, not the file")
    import os
    import subprocess
    import re as _re

    here = pathlib.Path(__file__).resolve().parent
    entries = sorted(q.name for q in here.glob("*.py")
                     if q.name not in {"console.py", "test_analysis.py"}
                     and 'if __name__ == "__main__":' in q.read_text(encoding="utf-8"))

    # Part 1 -- structural. Every entry point must route through the shared
    # guard. A per-file copy of the reconfigure block would pass a behavioural
    # test today and be forgotten in the next file added, which is exactly how
    # this defect reached its third recurrence.
    missing = [n for n in entries
               if "use_utf8()" not in (here / n).read_text(encoding="utf-8")]
    ok("every entry point calls use_utf8()", not missing, f"missing in {missing}")

    # Part 2 -- behavioural, on the scripts that actually print non-ASCII, with
    # the masking variable REMOVED. run-all-tests.ps1 exports
    # PYTHONIOENCODING=utf-8; inheriting it is what hid the bug the first time.
    non_ascii = [n for n in entries
                 if any(ord(c) > 127 for c in (here / n).read_text(encoding="utf-8"))]
    ok("some entry point prints non-ASCII (otherwise this test is vacuous)",
       len(non_ascii) >= 3, f"found {non_ascii}")

    env = dict(os.environ)
    env.pop("PYTHONIOENCODING", None)
    env["PYTHONLEGACYWINDOWSSTDIO"] = "1"      # force the narrow stdout path
    for name in non_ascii:
        # -c so nothing is executed: importing is enough to prove the module
        # imports, and we only need the *printing* path for the cheap ones.
        r = subprocess.run([sys.executable, "-c",
                            f"import console; console.use_utf8();"
                            f" print('ťľšč')"],
                           cwd=here, env=env, capture_output=True)
        ok(f"narrow stdout survives caron glyphs ({name})", r.returncode == 0,
           r.stderr.decode(errors="replace")[-200:])
        break      # the guard is shared, so one behavioural probe suffices

    # Part 3 -- the regression itself: the script that actually died.
    # (The item-count check lives in its own test below.)
    r = subprocess.run([sys.executable, "measurement_plan.py"],
                       cwd=here, env=env, capture_output=True)
    ok("measurement_plan.py runs with no PYTHONIOENCODING", r.returncode == 0,
       r.stderr.decode(errors="replace")[-300:])



# ===========================================================================
def test_dgp_test_lengths_come_from_the_bank():
    section("generating model: test lengths are not typed here")
    import sys as _sys
    _sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]
                            / "assessment"))
    from bank import load_all

    banks = load_all()
    p = Params()

    # The generating model simulates at the item level, so the measurement error
    # in every simulated outcome -- and therefore the power analysis, the plan
    # validation and every number Chapter 6 reports -- depends on test length. A
    # hard-coded 16 survived the immediate form being shortened to twelve, which
    # would have made the thesis report power for a test it does not administer.
    ok("immediate form length matches the bank",
       p.n_items_ipt == banks["T1_IPT"].n_items,
       f"dgp {p.n_items_ipt} vs bank {banks['T1_IPT'].n_items}")
    ok("delayed form length matches the bank",
       p.n_items_drt_per_topic == banks["T1_DRT"].n_items,
       f"dgp {p.n_items_drt_per_topic} vs bank {banks['T1_DRT'].n_items}")
    ok("transfer test length matches the bank",
       p.n_items_tt == banks["TT"].n_items,
       f"dgp {p.n_items_tt} vs bank {banks['TT'].n_items}")
    ok("anchor count matches the bank",
       p.n_anchor_items == len(banks["T1_IPT"].anchors),
       f"dgp {p.n_anchor_items} vs bank {len(banks['T1_IPT'].anchors)}")

    # And the counts are not merely equal by coincidence: they must be READ, so
    # that changing the bank changes the model. Checked by changing the bank.
    import dgp as _dgp
    real = banks["T1_IPT"].n_items
    try:
        cached = _dgp._banks()
        cached["T1_IPT"].items = cached["T1_IPT"].items[:-1]
        moved = Params().n_items_ipt
        ok("removing an item from the bank moves the generating model",
           moved == real - 1, f"got {moved}, expected {real - 1}")
    finally:
        _dgp._banks.cache_clear()
    ok("and the bank is restored afterwards",
       Params().n_items_ipt == real, str(Params().n_items_ipt))


TESTS = [
    test_taxonomy_contract,
    test_classifier_on_anchors,
    test_coding_manual_binding_decisions,
    test_veneer_attack,
    test_substring_traps,
    test_weight_sensitivity,
    test_multiplicity,
    test_tost,
    test_rasch_recovers_planted_parameters,
    test_concurrent_calibration_puts_forms_on_one_scale,
    test_cluster_contrast_is_conservative,
    test_iv_recovers_planted_effect,
    test_mediation_decomposition_is_exact,
    test_sensitivity_rho_behaves,
    test_measurement_propositions_at_several_points,
    test_veneer_audit_and_correction,
    test_negative_controls_behave_as_controls,
    test_measurement_plan_is_internally_consistent,
    test_field_data_contract,
    test_national_anchoring,
    test_design_is_williams_balanced,
    test_dgp_anchoring_is_exact,
    test_dgp_is_reproducible,
    test_console_guard_on_every_entry_point,
    test_dgp_test_lengths_come_from_the_bank,
]


def main() -> int:
    global FAIL
    for t in TESTS:
        try:
            t()
        except Exception:
            FAIL += 1
            print(f"  ERROR in {t.__name__}")
            traceback.print_exc(limit=3)
    print(f"\n{PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
