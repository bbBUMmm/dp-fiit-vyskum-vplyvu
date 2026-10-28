# Measuring "changes in pupils' cognitive abilities": a methodology

*23 September 2026*

## The short answer to the question asked

**No — the thesis did not have a concrete methodology for this, and the reason is
that the question as posed cannot be answered as posed.** "Kognitívne schopnosti"
is not one measurable thing, and the design was quietly assuming two
contradictory things about it:

- it listed fluid reasoning as a **covariate**, implying it is stable;
- my own negative control asserted a 90-minute lesson **cannot move it**;
- and neither statement had ever been checked against the instrument that was
  supposed to carry them.

So the first thing this work does is replace the container term with a hierarchy
that says what changes, how fast, and therefore what can be measured at all.

---

## 1. The construct hierarchy and the rule that follows

| Layer | Construct | Change horizon | Role in the design |
|---|---|---|---|
| **L0** | fluid reasoning (g_f) | **years** | covariate + negative control |
| **L1** | computational thinking | **months** | covariate (+ optional outcome) |
| **L2** | knowledge of the lesson topic | **one lesson** | **primary outcome** |
| **L3** | offloading strategy, calibration | **one task** | mechanism, H5, H6 |

> **The measurement interval must match the construct's change rate.**

A three-week study cannot measure change at L0, and no instrument repairs that —
it is a property of the construct, not of the test. A design claiming otherwise
is not underpowered; it is measuring something else. The brain-training
literature is unambiguous here: near transfer yes, far transfer essentially no.

**So the honest answer is**: this study measures *change* at L2 and L3, and
measures *stability* at L0 and L1. "Nothing changed" is a claim like any other
and carries its own precision requirement — which is where the validation began.

---

## 2. Validation: three things the thesis asserted and had never checked

### (a) Reliability is not one number, it is three requirements

"α ≥ 0.7" is a slogan, not a requirement. Each role needs something different:

| Role | Needs | Why |
|---|---|---|
| Outcome | ≥ 0.80 | a change score's reliability is far below either occasion's |
| Covariate | ≥ 0.75 | adjustment removes only *reliability* of the confounding — at 0.75, a quarter survives, looking exactly like an effect |
| Negative control | ≥ 0.80 | **an unreliable control does not raise false alarms — it widens the interval until it can never clear** |

That last direction is the one people get backwards, and it matters: a control
that never certifies reads in a results table as an unexplained anomaly rather
than as a measurement problem.

**The thesis specified 12 matrix items. That gives reliability 0.67 — not enough
for either job it was given.** At 20 items it reaches 0.786 and clears 90% of the
time when the truth is zero. Below 0.80 the control degrades fast:

| test-retest | 0.50 | 0.60 | 0.70 | 0.80 | 0.85 | 0.90 |
|---|---|---|---|---|---|---|
| control clears | 0.40 | 0.55 | 0.73 | 0.92 | 0.98 | 1.00 |

### (b) A defect in my own earlier work

The trait negative control I built last session did not test anything. `g_f` was
drawn per pupil × period, but **a trait is measured once**, so the within-pupil
condition contrast on it is mean-zero by construction — it cleared 100% of the
time and could not have failed.

Two fixes, both substantive:

1. **The contrast must be between pupils**, keyed on the condition of the
   *last period* before the delayed test — which differs by sequence, and
   sequence is randomised.
2. **The quantity must be the change, not the level.** On the level, `g_f` has
   SD ≈ 1 plus a class component; with 18 clusters that cannot fit inside the
   equivalence band, and the control clears barely half the time with nothing
   wrong. The change T4 − T0 cancels the stable part and leaves
   sd = √(2(1−ρ)). That is what makes the control usable — and it exists only
   because the trait is administered twice.

`tost_control` now *raises* on a zero-variance contrast instead of dividing by
zero or, worse, returning "equivalent".

### (c) Longitudinal invariance was never tested

The thesis tested DIF between **conditions** and not between **occasions** —
leaving the contrast it actually cares about resting on an untested assumption.
An anchor item that drifts between T0 and T4 confounds learning with item drift.

The criterion is the ETS large band (0.64 logits) applied to the estimate, **not
a significance test**, and the reason is computed: with 330 pupils the SE of a
per-item shift is 0.165 logits, so a Bonferroni-corrected test would only catch
drift beyond 0.53 — larger than the band it is meant to police. Per-item power at
0.8 logits is 0.64, with 0.003 false flags per study.

---

## 3. Instruments that actually exist in Slovakia

An instrument with no Slovak version, no licence and no administration time is
an intention, not an instrument.

| Layer | Instrument | Items | Licence / Slovak availability |
|---|---|---|---|
| L0 | **ICAR** matrices + series | 20 | **public domain, no fee**; figural/numeric, only the instruction needs translating |
| L1 | **iBobor / Bebras** | 8 (15 in semester arm) | native Slovak, age-graded, **600+ tasks already in EduPage**; needs organisers' consent |
| L2 | own IPT/DRT/TT | 16/12/6 | own, Rasch-calibrated, 6 anchor items |
| L3 | JOL slider | per item | own, rides on the knowledge test |
| L3 | PEQI from prompts | — | own, observed — costs **zero** lesson time |
| L3 | Jr. MAI version B | 18 | free for research; needs forward/back translation |

**ICAR over Raven's**: Raven's SPM is licensed and priced per booklet — at 330
pupils × 2 occasions that is a real budget line, and it blocks publishing the
instrument with the data. ICAR is public domain with no publication restriction.

**iBobor is the decisive find.** Run by FMFI UK: **141,146 pupils from 1,634
schools** in 2025, delivered through **EduPage** — the system most Slovak schools
already run — with 600+ past tasks available to teachers year-round, age-graded,
tagged with the informatics concepts they contain, and with per-item success
rates known from a cohort of that size. **No instrument we could build has a
Slovak norming base remotely comparable.**

One thing not adopted: iBobor's **competition scoring** (negative marking plus an
initial bonus). That confuses knowledge with risk appetite — two pupils who know
the same and differ in caution get different scores. Items are scored 0/1 and
Rasch-calibrated like any other test.

**A tension stated rather than hidden**: Jr. MAI is a self-report instrument in a
thesis whose premise is that self-report mismeasures offloading. It is admissible
only as a trait covariate, never as an outcome.

---

## 4. The time budget — where the plan was fiction

Instruments are specified in items; schools deliver them in minutes. Reconciling
the two killed the original T0: **~73 minutes of content against a 45-minute
lesson.**

Three changes fix it, and each is a methodological *improvement*:

1. **T0 splits.** The trait questionnaire is not a test and needs no supervision
   — it goes out as EduPage homework and stops competing for lesson time with
   timed instruments.
2. **Prior knowledge moves** from one 20-item global pre-test to a 5-item
   topic-specific pre-check at the start of each period. A global test three
   weeks before the third topic is a *worse* covariate than five items taken
   minutes before the lesson that needs them — and costs a quarter as much room.
3. **The iBobor block shrinks** in the main arm, where it is a covariate. It
   returns at full length only in the optional semester arm, where it *is* the
   outcome and the horizon finally matches.

| Session | Mode | Used | Budget | Slack |
|---|---|---|---|---|
| T0a | supervised | 36.3 | 45 | 8.7 |
| T0b | **EduPage homework** | 8.6 | 15 | 6.4 |
| P1–P3 | supervised | 101.4 | 110 | 8.6 |
| T4 | supervised | 62.5 | 70 | 7.5 |
| T6 (optional) | supervised | 30.0 | 45 | 15.0 |

**Three supervised measurement lessons**, plus the three teaching blocks.

---

## 5. The executable protocol (Appendix F, new)

Written so a teacher can run it after one briefing, and so it can be checked
afterwards that they did:

- **What the school gives and gets** — including what it explicitly does *not*
  give: no network changes, no server install, no pupil data.
- **Minute-by-minute** for every session. T4's order is deliberate: delayed test
  first while attention is highest, ICAR last because it is the most
  fatigue-resistant.
- **Roles**: teacher (same person across all three conditions — that is part of
  the control), researcher (present at T0a and T4, does not teach), school
  contact (holds the salt; the only person who can map code to pupil).
- **Consent**: written guardian consent under Act 18/2018 and GDPR for under-18s;
  the **pupil's own refusal is decisive even when the guardian consented**;
  revocable, with deletion in 30 days.
- **Failure modes, decided in advance** — internet loss, absence at one period,
  absence at T4, missing consent, fidelity breach, phone use. Improvisation
  during collection is what makes data incomparable.
- **Pre-flight checklist**, including the 85%-consent floor below which a class
  is not enrolled.

---

## 6. The field data contract (`analysis/ingest.py`, new)

Appendix F said what data each session produces. Saying is not enforcing, and
the failure mode is specific: a missing column or a mistyped code surfaces at
analysis time, months later, when the school is unreachable — at which point a
fixable clerical error has become permanent missing data.

So the schema is machine-readable and the validator runs **on collection day**,
against that session's files, while the teacher is still in the room. Every
message names the file, the row, and what to do.

Two classes of finding, deliberately separated:

- **Errors** block analysis: a response recorded without consent (delete, do not
  analyse); an identifier that is not 16 hex characters (the salt was not
  applied — *the file must not leave the school*); a pseudonym not in the
  roster; an instrument outside the schema; an item answered twice; a confidence
  slider on a questionnaire item; more lesson steps delivered than planned.
- **Warnings** do not block but change handling: fidelity < 90%, capture
  coverage < 80%, consent < 85%.

Thresholds live in one place in the code, so the protocol and the validator
cannot drift apart. **The validator is itself tested against 11 deliberately
broken fixtures**; clean data must pass without a single note. A validator that
has only seen correct data is an assertion, not a check.

## 7. Placing a convenience sample on a national scale (`national_anchor.py`, new)

The thesis lists, and then leaves standing, the limitation that schools cannot
be randomly selected. Random selection is impossible; **measuring where the
sample sits is not** — given an instrument with published national item
statistics. iBobor is the only one for Slovak informatics.

Administer iBobor items with published success rates, calibrate with those
difficulties **fixed** at their national values, and the pupils land on the
national metric.

| | |
|---|---|
| SE of the location estimate (8 anchor items) | **0.079 logits** |
| Items needed for SE ≤ 0.10 | **4** — precision is cheap |
| Residual bias | 0.046 logits ≈ **1.7 percentile points** |
| Systematic cohort drift inflates study-to-study SD by | **2.4×** |

So: precision is cheap, bias is small and reportable, and **the binding risk is
cohort drift** — a year that was uniformly better or worse passes straight into
the estimate and cannot be detected from anchored data. The reported percentile
therefore carries a sensitivity band, not a point.

**The caveat that must travel with every sentence**: the reference population is
iBobor *participants*, not all Slovak pupils. Entry is by school and by choice.
A known reference population still beats an unknown one.

## 8. What one class can decide (`pilot.py`, new)

"We will run a pilot" without decision rules is a rehearsal — and then the study
gets tuned by taste against whatever the pilot happened to show. Rules first.
But rules are not enough either, because **20 pupils cannot measure most of what
a pilot is asked to check**.

**The screening error.** The plan was to keep items with success rate in
0.30–0.80. At n = 20 the SE of a proportion is 0.112, so that rule discards
**15% of good items** — and each discarded item is a permanent tax on power
(reliability 0.75 at 16 items → 0.66 at 10). Screening on the **interval**
instead — drop only if the 90% CI lies entirely outside the band — cuts wrongly
dropped good items to **1.4%**, at the cost of catching 45% rather than 85% of
genuinely bad ones. That trade is right: a bad item surviving the pilot is
caught later by infit/outfit on the full sample; a good item dropped in the
pilot is gone for good.

**Two claims the thesis was making that it cannot support:**

1. *"Estimate τ²_ct from the pilot."* τ² is a **between-class** quantity and the
   pilot has **one class** — zero degrees of freedom. Corrected: taken from the
   literature, with sensitivity reported across a grid.
2. *"Zero leaks on 40 adversarial prompts"* reads as a certificate. It bounds
   the true leak rate at **7.2%**, not at zero; at a true 2% rate the set passes
   clean **44%** of the time. A 1% bound would need **299** prompts. Corrected:
   the gate is a floor, and the number the thesis reports is the *observed*
   guard-violation rate from real sessions, which has the sample behind it.

**And what the pilot may never change**: SESOI, primary outcome, confirmatory
family, condition definitions, analysis model.

## What changed in the thesis

| Where | What |
|---|---|
| §5 `sec:konstrukty` (NEW) | the hierarchy, the change-rate rule, role-specific reliability, the change-not-level estimand, longitudinal invariance, instrument selection with Slovak availability |
| §5 measurement table | 12 matrices → 20 ICAR; iBobor added; prior knowledge moved to per-topic |
| §5 schedule | T0 → T0a (supervised) + T0b (EduPage) |
| App. A | ICAR and iBobor specified with licence, length and the reason for each; the competition-scoring warning |
| App. F (NEW) | the executable protocol |
| §5 `sec:pilot` (NEW) | what one class decides, the interval screening rule, what the pilot may never change |
| §5 `sec:narodne-ukotvenie` (NEW) | placing the sample on the national scale, with its caveat |
| §8 limitations | the non-random-schools limitation now points to its partial mitigation |
| App. A | the guard set reframed as a floor, not a certificate |
| App. F | the data contract; interval screening in the pre-flight checklist |
| `analysis/measurement_plan.py` (NEW) | reliability by role, session budget, drift precision |
| `analysis/ingest.py` (NEW) | the field data contract, self-tested against 11 breakages |
| `analysis/national_anchor.py` (NEW) | fixed-anchor calibration to the national scale |
| `analysis/pilot.py` (NEW) | pilot decision rules and what one class cannot decide |
| `analysis/falsification.py` | trait control rewritten: between-pupil, on the change; zero-variance contrast now raises |

**180 pages, clean build. 463 tests across 6 suites, 150 consistency checks, all
passing.**

## Honest limits

- The reliability figures are simulated from a Rasch model, not measured on
  Slovak pupils. The pilot must confirm them; if ICAR-20 comes in below 0.75 in
  this population, the item count goes up before the study runs.
- iBobor task reuse **requires permission** that has not been sought yet.
- Jr. MAI has no validated Slovak version; forward/back translation and a pilot
  are required, and the thesis says so rather than assuming a translation is
  free.
- The semester arm (T6) is specified but unfunded — it is the only part of the
  plan that could address L1 as an outcome, and it needs a second school year.

## Sources

- [Condon, D. M. & Revelle, W. (2014). *The International Cognitive Ability Resource*. Intelligence 43, 52–64](https://www.personality-project.org/revelle/publications/condon.icar.14.pdf)
- [iBobor — final report 2023/24, FMFI UK](https://www.informatika.sk/web/sk/app/aktivity/podpora_mladych/text/iB23sprava/_getFile/sprava_iBobor_2023.pdf) — scoring scheme, EduPage delivery, 600+ task bank
- [iBobor 2025, FMFI UK](https://fmph.uniba.sk/detail-novinky/back_to_page/uspechy-fakulty/article/ibobor-2025/) — 141,146 participants, 1,634 schools
- [Sperling, R. A. et al. (2002). *Measures of Children's Knowledge and Regulation of Cognition*. Contemporary Educational Psychology 27(1), 51–79](https://www.sciencedirect.com/science/article/abs/pii/S0361476X01910911) — Jr. MAI
- [Zákon č. 18/2018 Z. z. o ochrane osobných údajov](https://www.epi.sk/zz/2018-18)
