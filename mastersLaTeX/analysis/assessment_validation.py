"""assessment_validation.py -- does the assessment layer measure what it claims?

The pattern is the one the rest of this directory uses: plant a known answer in a
generating model, run the frozen procedure, and demand the answer back. Anything
the procedure cannot recover from data it was handed cannot be recovered from a
school either.

Five questions, in order of how much rests on them:

  1. EQUATING. Six items are supposed to be identical in both test forms, and the
     whole immediate-versus-delayed contrast rests on it. The appendix claimed
     identity and delivered six items with different numbers, different arrays
     and, in one case, a different response format. How much forgetting does that
     cost -- quantitatively?

  2. THE TESTING EFFECT ON ANCHORS. Identical anchors are the right answer for
     equating and they bring their own cost: a pupil has seen those six items
     three weeks earlier, so answering them again is retrieval practice. Does
     that bias the condition contrast, which is what the thesis claims, or only
     the absolute level, which it does not?

  3. THE RULE CLASSIFIER. The thesis categorises pupils with latent profile
     analysis; the tool ships a deterministic rule. How far apart are their
     answers at the study's own sample size, and what happens to each at one
     class?

  4. PROFILE VALIDITY BEYOND PRIOR ATTAINMENT. If "blindly trusting" is a
     relabelling of "low prior score", the typology adds nothing. Tested against
     a planted null in which the profile is pure noise given attainment.

  5. OPERATING CHARACTERISTICS of the effort and integrity detectors: detection
     rate at a planted contamination rate, and the false-positive rate where
     contamination is impossible by construction.

Run:  python assessment_validation.py      -> out/assessment.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from console import use_utf8
from pipeline import concurrent_calibration, rasch_jmle

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

# the deployable layer is the source of truth for cut points and thresholds
sys.path.insert(0, str(HERE.parent.parent / "assessment"))
import effort as eff            # noqa: E402
import profiles as prof         # noqa: E402
import sessions as sess         # noqa: E402
from bank import load_all       # noqa: E402

N_ITEMS = 12
N_ANCHOR = 6


# ===========================================================================
# 1.  Equating: what the broken anchor set would have cost
# ===========================================================================
def equating_recovery(n: int = 330, forgetting: float = 0.45,
                      drift: float = 0.0, n_sim: int = 60,
                      seed: int = 101) -> dict:
    """Plant a known amount of forgetting and try to recover it.

    `drift` is the thing the defect introduced. An anchor item whose wording,
    array or n differs between the two forms is a DIFFERENT item with a different
    difficulty, but the calibration is told they are the same. Every such pair
    contributes a difficulty discrepancy, and because the pairs were all
    "simplified" in the delayed form -- 512 where the immediate form had 1024, a
    shorter array, a numeric answer instead of four options -- the discrepancies
    point the same way rather than cancelling.

    drift = 0.0 is the repaired instrument; drift > 0 is the instrument as the
    appendix had it, with the delayed "anchors" easier by that many logits.
    """
    rng = np.random.default_rng(seed)
    b_true = np.linspace(-1.4, 1.4, N_ITEMS)
    out = []
    for s in range(n_sim):
        r = np.random.default_rng(seed + 7919 * s)
        theta0 = r.normal(0, 1.0, n)
        theta1 = theta0 - forgetting

        def respond(th, b):
            p = 1 / (1 + np.exp(-(th[:, None] - b[None, :])))
            return (r.random((len(th), len(b))) < p).astype(float)

        x_imm = respond(theta0, b_true)
        # the delayed form: anchors first, then the form-specific items
        b_del = b_true.copy()
        b_del[:N_ANCHOR] -= drift          # the "anchors" are in fact easier
        x_del = respond(theta1, b_del)

        ti, td, _, _, _ = concurrent_calibration(x_imm, x_del, N_ANCHOR)
        out.append(float(ti.mean() - td.mean()))

    est = np.array(out)
    bias = float(est.mean() - forgetting)
    return dict(planted_forgetting=forgetting, anchor_drift_logits=drift,
                estimated=round(float(est.mean()), 4),
                bias=round(bias, 4),
                relative_bias=round(bias / forgetting, 4),
                sd=round(float(est.std(ddof=1)), 4),
                n_sim=n_sim)


def equating_comparison() -> dict:
    """The repaired instrument against the instrument as written.

    The drift grid is not arbitrary. One logit is roughly the difference between
    an item 73% of pupils pass and one 50% pass. The appendix's six "anchors"
    differed by: 1024 vs 512 (one halving step -- easier), a ten-element array vs
    an eight-element array, four options vs a free numeric answer (harder), and
    two rubric items whose wording was narrowed. Calling the net effect half a
    logit in the easy direction is a conservative reading, so 0.3 and 0.5 are the
    numbers to look at and 0.8 is the pessimistic case.
    """
    rows = [equating_recovery(drift=d) for d in (0.0, 0.3, 0.5, 0.8)]
    clean, mid = rows[0], rows[2]
    return dict(
        grid=rows,
        repaired_bias=clean["bias"],
        broken_bias_at_half_logit=mid["bias"],
        inflation_factor=round(abs(mid["bias"]) / max(abs(clean["bias"]), 1e-6), 1),
        reading=(
            f"S kotviacimi položkami, ktoré sú skutočne totožné, sa vložené "
            f"zabúdanie {clean['planted_forgetting']} obnoví so skreslením "
            f"{clean['bias']:+.3f} logitu. Ak sa šesť „kotviacich“ položiek v "
            f"odloženej forme líši a sú o pol logitu ľahšie — čo je pri rozdiele "
            f"1024 oproti 512 striedmy odhad — skreslenie je {mid['bias']:+.3f}, "
            f"teda {abs(mid['bias'] / clean['planted_forgetting']):.0%} vloženej "
            f"hodnoty. Zabúdanie by sa vykázalo ako podstatne menšie, než aké "
            f"naozaj je, a chyba by sa nijako neprejavila: model by konvergoval, "
            f"zhoda položiek s modelom by vyšla v poriadku a číslo by bolo "
            f"nesprávne."))


# ===========================================================================
# 2.  The cost of identical anchors: retrieval practice
# ===========================================================================
def testing_effect(n: int = 330, forgetting: float = 0.45,
                   practice: float = 0.25, effect: float = 0.30,
                   n_sim: int = 60, seed: int = 202) -> dict:
    """Identical anchors mean the pupil has met those six items before.

    That is retrieval practice, and it raises delayed performance ON THE ANCHORS
    relative to the fresh items. The question that matters is not whether it
    happens -- it does -- but whether it biases the BETWEEN-CONDITION contrast,
    which is what the thesis claims, or only the absolute retention level, which
    it does not claim.

    Every pupil in every condition sits both forms, so the practice applies
    equally. The prediction is therefore: absolute retention is overstated, the
    condition contrast is untouched. Worth verifying rather than asserting,
    because "it cancels" is the kind of statement that is usually true and
    occasionally catastrophically false.
    """
    rng = np.random.default_rng(seed)
    b_true = np.linspace(-1.4, 1.4, N_ITEMS)
    gaps, contrasts, anchor_minus_fresh = [], [], []
    for s in range(n_sim):
        r = np.random.default_rng(seed + 104729 * s)
        theta0 = r.normal(0, 1.0, n)
        cond = r.integers(0, 2, n)                 # 0 = K, 1 = A, effect on A
        theta1 = theta0 - forgetting + effect * cond

        def respond(th, b):
            p = 1 / (1 + np.exp(-(th[:, None] - b[None, :])))
            return (r.random((len(th), len(b))) < p).astype(float)

        x_imm = respond(theta0, b_true)
        b_del = b_true.copy()
        b_del[:N_ANCHOR] -= practice               # practised items feel easier
        x_del = respond(theta1, b_del)

        ti, td, _, _, _ = concurrent_calibration(x_imm, x_del, N_ANCHOR)
        gaps.append(float(ti.mean() - td.mean()))
        contrasts.append(float(td[cond == 1].mean() - td[cond == 0].mean()))
        anchor_minus_fresh.append(
            float(x_del[:, :N_ANCHOR].mean() - x_del[:, N_ANCHOR:].mean()))

    g, c = np.array(gaps), np.array(contrasts)
    return dict(
        planted_forgetting=forgetting, planted_contrast=effect,
        practice_logits=practice,
        estimated_forgetting=round(float(g.mean()), 4),
        forgetting_bias=round(float(g.mean()) - forgetting, 4),
        estimated_contrast=round(float(c.mean()), 4),
        contrast_bias=round(float(c.mean()) - effect, 4),
        contrast_bias_as_share_of_effect=round(
            (float(c.mean()) - effect) / effect, 4),
        anchor_minus_fresh_proportion=round(float(np.mean(anchor_minus_fresh)), 4),
        contrast_is_protected=bool(abs(float(c.mean()) - effect) < 0.05),
        reading=(
            "Opakovanie tých istých kotviacich položiek po troch týždňoch je "
            "vybavovacie precvičenie, a jeho dôsledok je väčší, než sa dalo "
            f"tušiť: pri precvičení 0,25 logitu sa vložené zabúdanie "
            f"{forgetting} odhadne na {float(g.mean()):.3f}, teda takmer celé "
            "zmizne. Kontrast medzi podmienkami je chránený, pretože obe formy "
            "píše každý žiak v každej podmienke rovnako, ale absolútna úroveň "
            "zadržania nie. To je cena totožného kotvenia a nie je malá — preto "
            "nasleduje rotované kotvenie, ktoré ju odhadne namiesto toho, aby ju "
            "predpokládalo."))


# ===========================================================================
# 2b.  Rotated anchors: identifying the practice effect by randomisation
# ===========================================================================
def theta_given_b(X, b, lo: float = -4.0, hi: float = 4.0, iters: int = 60):
    """Person measures with item difficulties held FIXED.

    Used instead of a joint estimation on purpose. Estimating theta, b and a
    practice parameter together looked like the elegant move and is not: a pupil
    who answers every administered item correctly has no finite maximum-likelihood
    measure, the Newton step for that pupil runs to the bound, and with a practice
    parameter in the same likelihood the bounded persons push it. The first
    version of this function did exactly that and returned a practice effect of
    -378 logits, which is the useful kind of wrong -- obviously wrong.

    Fixing b removes the problem at its source and is also the correct thing
    statistically: b comes from the immediate occasion, where every item in the
    pool is answered by a random subset of pupils, so the difficulties are
    estimated on a sample that has no practice in it at all.

    Returns (theta, n_bounded) -- bounded persons are counted, not hidden.
    """
    X = np.asarray(X, float)
    mask = ~np.isnan(X)
    Xf = np.where(mask, X, 0.0)
    n = X.shape[0]
    theta = np.zeros(n)
    for _ in range(iters):
        P = 1.0 / (1.0 + np.exp(-(theta[:, None] - b[None, :])))
        g = ((Xf - P) * mask).sum(axis=1)
        h = (P * (1 - P) * mask).sum(axis=1)
        step = g / np.maximum(h, 1e-9)
        theta = np.clip(theta + np.clip(step, -1.5, 1.5), lo, hi)
    n_bounded = int(np.sum((theta <= lo + 1e-6) | (theta >= hi - 1e-6)))
    return theta, n_bounded


def rotated_anchor_design(n: int = 330, forgetting: float = 0.45,
                          practice: float = 0.25, n_sim: int = 40,
                          seed: int = 250) -> dict:
    """The repair for the repair.

    Identical anchors fix the equating and break the absolute retention estimate.
    An item met three weeks ago is easier the second time, a fixed anchor set has
    no way to know by how much, and the calibration reads the ease as ability:
    with a practice effect of a quarter of a logit, planted forgetting of 0.45
    came back as 0.07. The condition contrast survives -- every pupil in every
    condition sits both forms -- but the absolute retention figure does not, and
    the thesis does make statements about absolute retention.

    A fixed anchor set cannot measure the practice effect, because every pupil has
    met every anchor and there is no comparison group. Randomisation supplies one.

    THE DESIGN. Each topic has a pool of eighteen calibrated items, composed so
    that any admissible draw satisfies the blueprint:

        zapamatanie 3, porozumenie 3, aplikacia 6, analyza 5, hodnotenie 1

    For each pupil, six items are drawn at random as that pupil's SHARED set
    (1/1/2/1/1 by level). The immediate form is the shared set plus enough of the
    remaining pool to complete 2/2/4/3/1; the delayed form is the shared set plus
    the complement. Both forms are twelve items and both satisfy the blueprint,
    for every pupil.

    TWO QUANTITIES THE FIXED DESIGN CANNOT PRODUCE follow from the draw:

      delta   at the delayed occasion each item is answered both by pupils who met
              it and by pupils who did not, and the two groups are equivalent by
              assignment. The difference in log-odds IS the practice effect.
      theta   delayed ability is estimated from each pupil's UNSEEN delayed items
              only, with difficulties fixed from the immediate occasion. It is
              therefore practice-free by construction rather than corrected
              afterwards -- and a correction applied afterwards was what went
              wrong on the first attempt, because the crude version
              double-counted the half of the practice effect the shift had
              already absorbed.

    THE COST, stated plainly. The eighteen items per topic already exist -- the
    current banks hold exactly that many distinct items. What does not exist is
    the pilot: the pool must be calibrated before a draw from it can be treated as
    blueprint-neutral. And the pool has a single evaluation-level item, which is
    therefore shared by every pupil, so practice is not estimable at that level.
    This is a recommended design change with a pilot attached, not a change
    already made.
    """
    LEVELS_POOL = dict(zapamatanie=3, porozumenie=3, aplikacia=6,
                       analyza=5, hodnotenie=1)
    FORM = dict(zapamatanie=2, porozumenie=2, aplikacia=4, analyza=3,
                hodnotenie=1)
    SHARED = dict(zapamatanie=1, porozumenie=1, aplikacia=2, analyza=1,
                  hodnotenie=1)

    idx, start = {}, 0
    for lv, cnt in LEVELS_POOL.items():
        idx[lv] = list(range(start, start + cnt))
        start += cnt
    K = start
    b_true = np.linspace(-1.5, 1.5, K)

    est_delta, est_forget, naive_forget, bounded = [], [], [], []
    for s in range(n_sim):
        r = np.random.default_rng(seed + 7907 * s)
        theta0 = r.normal(0, 1.0, n)
        theta1 = theta0 - forgetting

        in_imm = np.zeros((n, K), bool)
        in_del = np.zeros((n, K), bool)
        shared = np.zeros((n, K), bool)
        for i in range(n):
            for lv, pool in idx.items():
                perm = list(r.permutation(pool))
                sh = perm[:SHARED[lv]]
                rest = perm[SHARED[lv]:]
                need = FORM[lv] - SHARED[lv]
                shared[i, sh] = True
                in_imm[i, sh] = True
                in_imm[i, rest[:need]] = True
                in_del[i, sh] = True
                in_del[i, rest[need:need + need]] = True

        def respond(th, present, seen):
            z = th[:, None] - b_true[None, :] + practice * seen
            P = 1.0 / (1.0 + np.exp(-z))
            return np.where(present, (r.random((n, K)) < P).astype(float), np.nan)

        x_imm = respond(theta0, in_imm, np.zeros((n, K)))
        seen_del = (shared & in_del)
        x_del = respond(theta1, in_del, seen_del.astype(float))

        # 1. difficulties from the immediate occasion, where there is no practice
        _, b_hat, _ = rasch_jmle(x_imm)

        # 2. the practice effect, from the randomised within-item contrast
        d_item = []
        for j in range(K):
            a = x_del[seen_del[:, j], j]
            c = x_del[in_del[:, j] & ~seen_del[:, j], j]
            a, c = a[~np.isnan(a)], c[~np.isnan(c)]
            if len(a) < 25 or len(c) < 25:
                continue
            pa = np.clip(a.mean(), 1e-3, 1 - 1e-3)
            pc = np.clip(c.mean(), 1e-3, 1 - 1e-3)
            d_item.append(float(np.log(pa / (1 - pa)) - np.log(pc / (1 - pc))))
        est_delta.append(float(np.mean(d_item)) if d_item else np.nan)

        # 3. delayed ability from the UNSEEN items only: practice-free by design
        x_unseen = np.where(in_del & ~seen_del, x_del, np.nan)
        # Both occasions are measured on SIX items, not twelve against six. A
        # person measure from six items is noisier than one from twelve, and the
        # bounded extreme scores are not symmetric around a mean that has moved,
        # so an unequal item count puts a bias into the difference that has
        # nothing to do with forgetting. The immediate measure therefore uses the
        # pupil's six shared items -- the ones that recur -- and the delayed
        # measure their six unseen ones.
        x_imm_six = np.where(shared, x_imm, np.nan)
        th_i, nb_i = theta_given_b(x_imm_six, b_hat)
        th_d, nb_d = theta_given_b(x_unseen, b_hat)
        bounded.append((nb_i + nb_d) / (2 * n))
        est_forget.append(float(th_i.mean() - th_d.mean()))

        # 4. and what the fixed design is forced to do: use every delayed item,
        #    practice included, with no way to separate it from ability
        # the fixed-anchor comparison uses the pupil's six shared items at both
        # occasions, which is exactly what a fixed anchor set gives you
        th_naive, _ = theta_given_b(np.where(seen_del, x_del, np.nan), b_hat)
        naive_forget.append(float(th_i.mean() - th_naive.mean()))

    d_ = np.array(est_delta, float)
    f_ = np.array(est_forget, float)
    nf = np.array(naive_forget, float)
    bias_rot = float(np.nanmean(f_)) - forgetting
    bias_fix = float(np.nanmean(nf)) - forgetting
    return dict(
        pool_items=K, pool_by_level=LEVELS_POOL, shared_by_level=SHARED,
        planted_forgetting=forgetting, planted_practice=practice,
        estimated_practice=round(float(np.nanmean(d_)), 4),
        practice_bias=round(float(np.nanmean(d_)) - practice, 4),
        practice_sd=round(float(np.nanstd(d_, ddof=1)), 4),
        forgetting_rotated=round(float(np.nanmean(f_)), 4),
        bias_rotated=round(bias_rot, 4),
        forgetting_fixed_anchors=round(float(np.nanmean(nf)), 4),
        bias_fixed_anchors=round(bias_fix, 4),
        rotation_helps=bool(abs(bias_rot) < abs(bias_fix)),
        share_bounded=round(float(np.mean(bounded)), 4),
        n_sim=n_sim,
        reading=(
            f"Rotovaný dizajn odhadne precvičenie na "
            f"{float(np.nanmean(d_)):.3f} logitu pri vložených {practice}, a "
            f"odhad je identifikovaný náhodným pridelením, nie predpokladom. "
            f"Zabúdanie potom vyjde {float(np.nanmean(f_)):.3f} oproti vloženým "
            f"{forgetting} (skreslenie {bias_rot:+.3f}), pretože odložená "
            f"schopnosť sa odhaduje len z položiek, ktoré žiak predtým nevidel. "
            f"Pri pevnej sade kotviacich položiek vyjde "
            f"{float(np.nanmean(nf)):.3f} (skreslenie {bias_fix:+.3f}): "
            f"precvičenie sa od schopnosti oddeliť nedá. Cena je pilot — "
            f"zásobník 18 položiek na tému treba najprv nakalibrovať — a na "
            f"úrovni hodnotenia je v zásobníku jediná položka, takže tam "
            f"precvičenie odhadnuteľné nie je."))


# ===========================================================================
# 3.  The rule classifier against latent profile analysis
# ===========================================================================
def _simulate_profiles(n: int, seed: int) -> tuple[dict, list[str]]:
    """Draw pupils from the four pre-named profiles, on the ABSOLUTE scales the
    rule uses rather than in standard units, because a rule with fixed cut points
    can only be tested against data that has a location."""
    rng = np.random.default_rng(seed)
    # (peqi, abhr, bias, reliance, critical), share
    centres = {
        "slepo doverujuci": ((0.14, 0.18, 0.26, 6.0, 0.36), 0.22),
        "kriticky pouzivatel": ((0.62, 0.78, -0.04, 4.6, 0.76), 0.28),
        "vyhybajuci sa": ((0.42, 0.88, 0.02, 2.2, 0.58), 0.20),
        "priemerny": ((0.36, 0.52, 0.08, 4.1, 0.56), 0.30),
    }
    names = list(centres)
    shares = np.array([centres[k][1] for k in names])
    shares = shares / shares.sum()
    which = rng.choice(len(names), size=n, p=shares)

    pupils, truth = {}, []
    for i in range(n):
        name = names[which[i]]
        mu = centres[name][0]
        peqi = float(np.clip(rng.normal(mu[0], 0.09), 0, 1))
        abhr = float(np.clip(rng.normal(mu[1], 0.13), 0, 1))
        bias = float(np.clip(rng.normal(mu[2], 0.09), -1, 1))
        rely = float(np.clip(rng.normal(mu[3], 0.75), 1, 7))
        crit = float(np.clip(rng.normal(mu[4], 0.12), 0, 1))
        # an avoider sends few prompts BY DEFINITION of avoiding
        nprompt = int(rng.integers(0, 3)) if name == "vyhybajuci sa" \
            else int(rng.integers(8, 26))
        pupils[f"P{i:04d}"] = prof.Indicators(
            peqi=peqi, n_prompts=nprompt, abhr=abhr, n_tasks=8,
            calib_bias=bias, reliance=rely, critical=crit, n_ct_items=12,
            condition="G" if i % 2 else "A")
        truth.append(name)
    return pupils, truth


def _ari(a: list, b: list) -> float:
    """Adjusted Rand index between two labellings."""
    la, lb = sorted(set(a)), sorted(set(b))
    ia = {v: i for i, v in enumerate(la)}
    ib = {v: i for i, v in enumerate(lb)}
    m = np.zeros((len(la), len(lb)))
    for x, y in zip(a, b):
        m[ia[x], ib[y]] += 1

    def c2(x):
        return x * (x - 1) / 2
    sij = c2(m).sum()
    sa = c2(m.sum(axis=1)).sum()
    sb = c2(m.sum(axis=0)).sum()
    n = c2(m.sum())
    exp = sa * sb / n
    mx = (sa + sb) / 2
    return float((sij - exp) / (mx - exp)) if mx != exp else 1.0


def _lpa(X: np.ndarray, k: int, seed: int = 3, iters: int = 160):
    """Gaussian mixture with a TIED covariance -- the structure the thesis chose
    after testing four of them against planted truth and planted absence of it."""
    rng = np.random.default_rng(seed)
    n, d = X.shape
    if n < k * (d + 2):
        return None, np.inf
    mu = X[rng.choice(n, k, replace=False)].copy()
    S = np.cov(X.T) + 1e-6 * np.eye(d)
    pi = np.full(k, 1.0 / k)
    for _ in range(iters):
        Si = np.linalg.pinv(S)
        logp = np.empty((n, k))
        for j in range(k):
            dv = X - mu[j]
            logp[:, j] = np.log(pi[j] + 1e-12) - 0.5 * np.einsum(
                "ij,jk,ik->i", dv, Si, dv)
        m = logp.max(axis=1, keepdims=True)
        w = np.exp(logp - m)
        w /= w.sum(axis=1, keepdims=True)
        nk = w.sum(axis=0) + 1e-9
        pi = nk / n
        mu = (w.T @ X) / nk[:, None]
        S = np.zeros((d, d))
        for j in range(k):
            dv = X - mu[j]
            S += (w[:, j, None] * dv).T @ dv
        S = S / n + 1e-6 * np.eye(d)
    lab = w.argmax(axis=1)
    # BIC with a tied covariance: k means, k-1 weights, one covariance
    npar = k * d + (k - 1) + d * (d + 1) / 2
    Si = np.linalg.pinv(S)
    sign, logdet = np.linalg.slogdet(S)
    ll = 0.0
    for j in range(k):
        dv = X - mu[j]
        q = -0.5 * (np.einsum("ij,jk,ik->i", dv, Si, dv) + logdet
                    + d * np.log(2 * np.pi))
        ll += (w[:, j] * (q + np.log(pi[j] + 1e-12))).sum()
    return lab, float(-2 * ll + npar * np.log(n))


def rule_vs_lpa(sizes=(22, 66, 330, 900), n_sim: int = 12,
                seed: int = 303) -> dict:
    rows = []
    for n in sizes:
        rule_ari, lpa_ari, lpa_k, lpa_failed = [], [], [], 0
        for s in range(n_sim):
            pupils, truth = _simulate_profiles(n, seed + 31 * s + n)
            assigned = prof.classify_many(pupils)
            rl = [assigned[k].profile for k in pupils]
            rule_ari.append(_ari(truth, rl))

            X = np.array([[p.peqi, p.abhr, p.calib_bias, p.reliance, p.critical]
                          for p in pupils.values()])
            X = (X - X.mean(0)) / (X.std(0) + 1e-9)
            best, bk, bbic = None, 0, np.inf
            for k in range(1, 7):
                lab, bic = _lpa(X, k, seed=seed + s)
                if lab is not None and bic < bbic:
                    best, bk, bbic = lab, k, bic
            if best is None:
                lpa_failed += 1
                continue
            lpa_ari.append(_ari(truth, [str(v) for v in best]))
            lpa_k.append(bk)
        rows.append(dict(
            n=n,
            rule_ari=round(float(np.mean(rule_ari)), 3),
            rule_undetermined=round(float(np.mean(
                [sum(1 for v in prof.classify_many(
                    _simulate_profiles(n, seed + 31 * s + n)[0]).values()
                    if v.profile == "neurceny") / n for s in range(3)])), 3),
            lpa_ari=round(float(np.mean(lpa_ari)), 3) if lpa_ari else None,
            lpa_components=round(float(np.mean(lpa_k)), 1) if lpa_k else None,
            lpa_could_not_fit=lpa_failed))

    one_class = rows[0]
    return dict(
        grid=rows,
        agreement_at_study_n=round(
            float(np.mean([r["rule_ari"] for r in rows if r["n"] == 330])), 3),
        reading=(
            f"Pravidlo dosahuje rovnakú zhodu s vloženou pravdou pri jednej "
            f"triede ({one_class['rule_ari']}) ako pri 900 žiakoch "
            f"({rows[-1]['rule_ari']}), pretože nezávisí od veľkosti vzorky. "
            f"Zmesový model pri jednej triede buď nedobehne, alebo vyberie "
            f"nesprávny počet komponentov; pri 330 žiakoch sa jeho zhoda "
            f"približuje pravidlu a pri 900 ho prekoná. To je presne rozdelenie "
            f"úloh, ktoré práca navrhuje: zmes je výskumná otázka o populácii, "
            f"pravidlo je to, čo dostane škola."))


def label_is_sample_independent(n: int = 400, seed: int = 404) -> dict:
    """The property that distinguishes the rule from the mixture. Tested by
    reclassifying the same pupil inside 40 different random cohorts."""
    rng = np.random.default_rng(seed)
    pupils, _ = _simulate_profiles(n, seed)
    keys = list(pupils)
    target = keys[0]
    labels = set()
    for t in range(40):
        sub = rng.choice(keys[1:], size=rng.integers(5, n - 1), replace=False)
        cohort = {target: pupils[target], **{k: pupils[k] for k in sub}}
        labels.add(prof.classify_many(cohort)[target].profile)
    return dict(cohorts=40, distinct_labels=len(labels),
                stable=len(labels) == 1,
                label=sorted(labels)[0] if len(labels) == 1 else sorted(labels))


def cut_point_sensitivity(n: int = 330, n_sim: int = 8, seed: int = 505) -> dict:
    """Move every cut point by +-20% and see what the typology does.

    A typology that only exists at one setting of five thresholds is a typology
    about the thresholds.
    """
    base = dict(PEQI_LOW=prof.PEQI_LOW, PEQI_HIGH=prof.PEQI_HIGH,
                ABHR_MID=prof.ABHR_MID, BIAS_OVER=prof.BIAS_OVER,
                CRIT_MID=prof.CRIT_MID)
    def measure() -> float:
        aris = []
        for s in range(n_sim):
            pupils, truth = _simulate_profiles(n, seed + 17 * s)
            got = prof.classify_many(pupils)
            aris.append(_ari(truth, [got[k2].profile for k2 in pupils]))
        return round(float(np.mean(aris)), 3)

    joint, single = [], []
    try:
        # All five at once and in the same direction: the harshest version, and
        # not a realistic one. A reviewer who disputes these cut points disputes
        # one of them, not all five simultaneously and in agreement.
        for mult in (0.8, 0.9, 1.0, 1.1, 1.2):
            for k, v in base.items():
                setattr(prof, k, v * mult)
            joint.append(dict(multiplier=mult, ari=measure()))
        for k, v in base.items():
            setattr(prof, k, v)
        # One at a time, which is what a disagreement about a cut point is.
        for k, v in base.items():
            rowd = dict(cut=k, base=round(v, 3))
            for mult, tag in ((0.8, "ari_minus20"), (1.2, "ari_plus20")):
                setattr(prof, k, v * mult)
                rowd[tag] = measure()
                setattr(prof, k, v)
            single.append(rowd)
    finally:
        for k, v in base.items():
            setattr(prof, k, v)

    ja = [r["ari"] for r in joint]
    joint_spread = round(max(ja) - min(ja), 3)
    bl = joint[2]["ari"]

    def dev(r):
        return max(abs(r["ari_minus20"] - bl), abs(r["ari_plus20"] - bl))

    worst = max(single, key=dev)
    single_spread = round(dev(worst), 3)
    return dict(
        joint=joint, one_at_a_time=single, baseline_ari=bl,
        joint_spread=joint_spread,
        worst_single_cut=worst["cut"],
        worst_single_spread=single_spread,
        robust_to_single_cut=bool(single_spread < 0.10),
        robust_to_joint_shift=bool(joint_spread < 0.15),
        reading=(
            f"Posun jednej hranice o ±20 % mení zhodu najviac o "
            f"{single_spread:.3f} (najcitlivejšia je {worst['cut']}), takže "
            f"nezhoda o jednu hranicu typológiu nerozvráti. Posun všetkých "
            f"piatich naraz a v tom istom smere ju mení o {joint_spread:.3f}, a "
            f"to málo nie je: pravidlo s absolútnymi hranicami je citlivé na ich "
            f"spoločné nastavenie. Práve preto musia byť hranice odvodené z "
            f"významu škály a stanovené vopred, nie z dát. Predregistrácia tu "
            f"nie je formalita, ale nosný prvok: bez nej by sa päť hraníc dalo "
            f"ladiť, kým typológia nepovie to, čo sa od nej čaká."))


# ===========================================================================
# 4.  Does the profile add anything beyond prior attainment?
# ===========================================================================
def incremental_validity(n: int = 330, n_sim: int = 200, seed: int = 606) -> dict:
    """Two planted worlds, and the test must tell them apart.

    REAL:  the profile carries its own effect on the delayed outcome, over and
           above prior attainment and fluid reasoning.
    NULL:  the profile is a deterministic relabelling of prior attainment, with
           no effect of its own. Here the correct answer is "adds nothing", and a
           procedure that finds an effect anyway is a procedure that would have
           dressed up prior attainment as a typology.
    """
    def run(real: bool, s: int) -> float:
        r = np.random.default_rng(seed + 977 * s + int(real))
        theta_pre = r.normal(0, 1, n)
        gf = 0.5 * theta_pre + r.normal(0, 0.87, n)
        # "blind truster" membership is driven by prior attainment in BOTH worlds
        p_blind = 1 / (1 + np.exp(1.2 * theta_pre))
        blind = (r.random(n) < p_blind).astype(float)
        y = 0.55 * theta_pre + 0.18 * gf + r.normal(0, 0.8, n)
        if real:
            y = y - 0.45 * blind                 # its own effect
        # partial F-test of blind, given theta_pre and gf
        X0 = np.column_stack([np.ones(n), theta_pre, gf])
        X1 = np.column_stack([X0, blind])
        r0 = y - X0 @ np.linalg.lstsq(X0, y, rcond=None)[0]
        r1 = y - X1 @ np.linalg.lstsq(X1, y, rcond=None)[0]
        ss0, ss1 = float(r0 @ r0), float(r1 @ r1)
        f = (ss0 - ss1) / (ss1 / (n - 4))
        return f

    # critical value of F(1, n-4) at 0.05
    crit = 3.871
    power = float(np.mean([run(True, s) > crit for s in range(n_sim)]))
    false_pos = float(np.mean([run(False, s) > crit for s in range(n_sim)]))
    return dict(n=n, n_sim=n_sim, planted_profile_effect=-0.45,
                power=round(power, 3), false_positive_rate=round(false_pos, 3),
                usable=bool(power > 0.80 and false_pos < 0.10),
                reading=("Test má silu "
                         f"{power:.0%} nájsť vlastný účinok profilu, keď tam je, "
                         f"a v {false_pos:.0%} prípadov ho nájde, keď profil je "
                         "len inak pomenovaná vstupná úroveň. Bez tohto testu by "
                         "typológia mohla byť preznačkovaná vstupná úroveň a "
                         "nikto by to z výsledku nerozlíšil."))


# ===========================================================================
# 5.  Operating characteristics of the two detectors
# ===========================================================================
def effort_detection(n: int = 330, n_sim: int = 200, seed: int = 707) -> dict:
    """Can the effort contrast see a differential that would matter?

    "Would matter" is defined, not asserted: a difference in RTE of d translates
    into roughly d * 12 items answered at chance instead of at ability, which on
    a twelve-item test moves the score by about 0.5 * d * 12 * (1/12) = d/2 of a
    proportion. The study's SESOI is 0.20 of a standard deviation, so an RTE gap
    able to fake it is around 0.08.
    """
    rows = []
    for gap in (0.0, 0.02, 0.05, 0.08, 0.15):
        hits = []
        for s in range(n_sim):
            r = np.random.default_rng(seed + 61 * s + int(gap * 1000))
            k = np.clip(r.normal(0.97, 0.05, n // 3), 0, 1)
            g = np.clip(r.normal(0.97 - gap, 0.05, n // 3), 0, 1)
            a = np.clip(r.normal(0.97, 0.05, n // 3), 0, 1)
            res = eff.condition_contrast({"K": list(k), "G": list(g),
                                          "A": list(a)})
            hits.append(res["differential_effort_detected"])
        rows.append(dict(planted_gap=gap, detected=round(float(np.mean(hits)), 3)))
    return dict(grid=rows,
                false_positive_rate=rows[0]["detected"],
                detects_the_gap_that_matters=rows[3]["detected"],
                reading=("Rozdiel v úsilí 0,08, teda taký, ktorý by vedel "
                         "predstierať najmenší zaujímavý účinok, sa odhalí "
                         f"v {rows[3]['detected']:.0%} prípadov. Pri nulovom "
                         f"rozdiele je falošná pozitivita "
                         f"{rows[0]['detected']:.0%}."))


def integrity_power(n: int = 22, n_sim: int = 300, seed: int = 808) -> dict:
    """Detection rate against contamination rate, in ONE class.

    One class, because that is the unit a teacher and a school have, and because
    the detector's job is not to produce a national estimate but to tell a
    researcher that this particular sitting cannot be used.
    """
    sys.path.insert(0, str(HERE.parent.parent / "assessment"))
    import integrity as intg

    def row(i, sec, exp, corr, diff, **kw):
        d = dict(item_id=i, seconds=sec, expected_sec=exp, correct=corr,
                 difficulty=diff, raw="", is_open=False, blur_seconds=0.0,
                 paste_events=0)
        d.update(kw)
        return d

    rows = []
    for rate in (0.0, 0.05, 0.10, 0.20):
        det, fp = [], []
        for s in range(n_sim):
            r = np.random.default_rng(seed + 29 * s + int(rate * 100))
            pupils = []
            truth = []
            for i in range(n):
                dirty = r.random() < rate
                truth.append(dirty)
                # A realistic lookup is PARTIAL. A pupil who consults a phone
                # does it on the two or three items they cannot do, not on all
                # twelve. The first version of this simulation made every
                # contaminated pupil answer every item in 3.5 seconds with 18
                # seconds of focus loss, and the detector scored a perfect 100%
                # against it -- which says nothing, because nothing that obvious
                # happens in a room with a teacher in it.
                n_items = 12
                k_lookup = int(r.integers(2, 5)) if dirty else 0
                which = (set(r.choice(n_items, k_lookup, replace=False).tolist())
                         if k_lookup else set())
                items = []
                for k in range(n_items):
                    exp = 30 + 6 * k
                    if k in which:
                        items.append(row(
                            f"I{k}", max(2.0, r.normal(0.30 * exp, 0.08 * exp)),
                            exp, 1, -1 + 0.2 * k,
                            blur_seconds=max(0.0, r.normal(11.0, 5.0))))
                    else:
                        items.append(row(
                            f"I{k}", max(4.0, r.normal(exp, 0.3 * exp)), exp,
                            int(r.random() < 0.6), -1 + 0.2 * k,
                            blur_seconds=max(0.0, r.normal(1.2, 1.2))))
                pupils.append(intg.examine(f"P{i}", "T4a", items))
            flagged = [p.excluded for p in pupils]
            tp = sum(1 for f, t in zip(flagged, truth) if f and t)
            pos = sum(truth)
            neg = len(truth) - pos
            if pos:
                det.append(tp / pos)
            fp.append(sum(1 for f, t in zip(flagged, truth)
                          if f and not t) / max(neg, 1))
        rows.append(dict(contamination_rate=rate,
                         detection=round(float(np.mean(det)), 3) if det else None,
                         false_positive=round(float(np.mean(fp)), 4)))
    det10 = next(r["detection"] for r in rows
                 if r["contamination_rate"] == 0.10)
    return dict(grid=rows, class_size=n,
                false_positive_rate=rows[0]["false_positive"],
                detection_at_10pct=det10,
                reading=(
                    "Detektor je zámerne konzervatívny: vylúčenie vyžaduje dva "
                    "príznaky z rôznych rodín. Pri realistickom nazeraní — žiak "
                    "si pozrie dve až štyri položky z dvanástich, nie všetky — "
                    f"zachytí {det10:.0%} kontaminovaných žiakov pri falošnej "
                    f"pozitivite {rows[0]['false_positive']:.1%}. To nie je "
                    "dozor a nemá ním byť: je to dolná hranica, ktorá z "
                    "nemerateľného tvrdenia („žiaci nemali prístup k "
                    "asistentovi“) robí vykazovateľný podiel. A čítať sa dá len "
                    "proti hodnote z T0a, kde kontaminácia nie je možná."))


# ===========================================================================
def instrument_summary() -> dict:
    banks = load_all()
    res = sess.budget()
    cmp_ = sess.naive_budget_comparison()
    return dict(
        banks=len(banks),
        items=sum(b.n_items for b in banks.values()),
        form_items=banks["T1_IPT"].n_items,
        anchors=len(banks["T1_IPT"].anchors),
        open_per_form=sum(1 for i in banks["T1_IPT"].items if i.is_open),
        distractors_diagnosed=sum(
            len(i.distractor_dx) for b in banks.values() for i in b.items),
        measurement_lessons=res["measurement_lessons_excl_teaching"],
        all_sessions_fit=res["all_fit"],
        budget_understated_by_flat_average=cmp_["total_understated"],
        worst_understated=cmp_["worst"],
        worst_understated_by=cmp_["worst_by"])


def main() -> int:
    res = {
        "instrument": instrument_summary(),
        "equating": equating_comparison(),
        "testing_effect": testing_effect(),
        "rotated_anchors": rotated_anchor_design(),
        "rule_vs_lpa": rule_vs_lpa(),
        "label_stability": label_is_sample_independent(),
        "cut_point_sensitivity": cut_point_sensitivity(),
        "incremental_validity": incremental_validity(),
        "effort_detection": effort_detection(),
        "integrity_power": integrity_power(),
    }
    (OUT / "assessment.json").write_text(
        json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")

    print("instrument:", json.dumps(res["instrument"], ensure_ascii=False))
    print("\nequating, planted forgetting 0.45:")
    for r in res["equating"]["grid"]:
        print(f"   drift {r['anchor_drift_logits']:.1f} logitu -> "
              f"estimate {r['estimated']:.3f}  bias {r['bias']:+.3f} "
              f"({r['relative_bias']:+.1%} of planted)")
    print("\nrule vs latent profile analysis:")
    for r in res["rule_vs_lpa"]["grid"]:
        print(f"   n={r['n']:4}  rule ARI {r['rule_ari']:.3f}   "
              f"LPA ARI {r['lpa_ari']}   k={r['lpa_components']}   "
              f"undetermined {r['rule_undetermined']:.2f}")
    print(f"\nlabel stable across 40 cohorts: {res['label_stability']['stable']}")
    cs = res["cut_point_sensitivity"]
    print(f"cut-point sensitivity: one cut +-20% moves ARI by "
          f"{cs['worst_single_spread']} (worst: {cs['worst_single_cut']}); "
          f"all five at once by {cs['joint_spread']}")
    ra = res["rotated_anchors"]
    print(f"rotated anchors: practice {ra['estimated_practice']} "
          f"(planted {ra['planted_practice']}); forgetting rotated "
          f"{ra['forgetting_rotated']} vs fixed anchors "
          f"{ra['forgetting_fixed_anchors']} "
          f"(planted {ra['planted_forgetting']})")
    ip = res["integrity_power"]
    print(f"integrity: detection at 10% contamination "
          f"{ip['detection_at_10pct']}, false positive "
          f"{ip['false_positive_rate']}")
    print(f"incremental validity: power {res['incremental_validity']['power']}, "
          f"false positive {res['incremental_validity']['false_positive_rate']}")
    print(f"\nwritten: {OUT / 'assessment.json'}")
    return 0


if __name__ == "__main__":
    use_utf8()
    raise SystemExit(main())
