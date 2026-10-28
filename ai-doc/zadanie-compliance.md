# Thesis assignment: what was missing, and what now covers it

*1 October 2026 — after reading the zadanie and QuestionsNotes.png*

## The honest starting position

The thesis was strong on methodology and **had never been checked against its own
assignment**. Reading the two together found six gaps, one of which was a
straight compliance failure.

| Assignment clause | Before | Now |
|---|---|---|
| Mandatory ref: Garzón et al. (2025) | cited | cited |
| **Mandatory ref: Discover Education (2025)** | **in the bib, never cited** | cited in §Slovensko |
| 1. How AI tools are *currently deployed*, quant **and** qual | literature review of *experiments*, not deployments | §`sec:nasadenie` |
| 2. **Kategorizácia používateľov** | categorised *prompts*, never *pupils* | §`sec:kategorizacia` + `user_profiles.py` |
| 2. Change in selected abilities before/after | present | realigned to your 3-layer model |
| 3. Deployable to a school | repo only | `build-school-kit.ps1` + §`sec:nasaditelnost` |
| 4. Comparison with available solutions | absent | §`sec:porovnanie` |
| 4. Recommendations | scattered in the conclusion | §`sec:odporucania`, 14 of them |
| Topic text: Slovak research context | "no Slovak studies exist" and stopped | §`sec:slovensko` |
| Topic text: impacts on **teachers** | students only | §`sec:ucitelia` |

A check (`check_assignment_compliance`, 16 claims) now fails the build if any
clause stops being discharged.

---

## Your notes, worked through

### The three-layer model replaced my four-layer one

Your diagram asked for **A vedomosti / B prenositeľné myslenie / C vzťah k AI**.
I had built computational thinking (iBobor) and matrix reasoning — but your note
says **"iq nie"**, and layer B is *critical* thinking, not computational.

Realigned. Fluid reasoning now appears **only** as covariate and negative
control, with the reason stated: it changes over years, so a three-week study
claiming to move it is measuring something else.

### Layer B — the instrument you asked for exists now

HCTA is licensed, paid, and normed **18+** while your sample is 14–19, so it
cannot be used as-is. You wrote *"skúsiť ale jednoduchšie"*.

**Appendix G**: 12 Slovak scenario items, everyday reasoning, closed response,
four subareas (source/evidence, cause vs correlation, probability/sample,
completeness of argument). Free, publishable, age-appropriate — with
pre-specified validation criteria **including what happens if it fails** (below
ten surviving items it drops out of confirmatory analysis; it is never topped up
after results are seen).

### Layer C — validated instruments found

- **Ng et al. (2024)** AI Literacy Questionnaire, validated for secondary pupils
- **Hou et al. (2025)** reliance scale — four factors: reflective, cautious,
  thoughtless, collaborative
- plus PEQI and the process measures, which are *observed* rather than reported

Two self-reported sources mixed with four observed ones, deliberately: a typology
built only from self-report measures what pupils say about themselves.

### Layer C's question answered properly

*"Existuje skupina žiakov, ktorá slepo dôveruje a má slabšie myslenie?"* — this
is also the assignment's **kategorizácia používateľov**, so one piece of work
discharges both.

Latent profile analysis, four pre-specified profiles (named **before** fitting,
so the typology stays falsifiable). The payoff on simulated data:

| Profile | Effect of generic tool | n |
|---|---|---|
| kritický používateľ | +0.17 | 94 |
| priemerný | +0.05 | 94 |
| vyhýbajúci sa | −0.02 | 68 |
| **slepo dôverujúci** | **−0.53** | 74 |
| **overall** | **−0.06, not significant** | 330 |

**The class mean says "no effect" about a population where one group was clearly
harmed.** That is the concrete reason the clause is not decoration.

**A methodological trap found and documented.** My first fit used `diag`
covariance and split a deliberately *homogeneous* population into three profiles
**100% of the time** — the subgroups were pure artefacts of the covariance
assumption, and would have looked entirely convincing. `full` fixed that and then
suppressed real structure (ARI 0.57→0.17). Only `tied` passes both tests. All
four are reported in the thesis.

Honest status: at your planned sample the typology recovers planted profiles at
ARI ≈ 0.59 — **exploratory, not confirmatory**. It would need ~500 pupils to be
confirmatory.

---

## Your four decisions, implemented

**Physics + FCI.** A **Slovak FCI translation exists** (PhysPort, by J. Hanč and
J. Tóth), so no translating needed. Two caveats now in the thesis: PhysPort
explicitly does not warrant translation validity, so the Slovak version is
re-validated in the pilot; and FCI is access-restricted, so unlike everything
else here it **cannot** be published with the data. Physics enters as a
*parallel crossover*, not a fourth topic — the new term is subject × condition.
Stated upfront: SOŠ physics coverage is thin, so that interaction is partly
confounded with school type.

**Teacher strand.** Pre-survey (expectations per condition), fidelity checklist
reused as qualitative data at zero extra burden, post-survey, 6 interviews —
stratified by the *gap between expectation and observation*, which is the
informative quantity. Explicitly descriptive, not confirmatory: 18 teachers is
not a sample for claims about Slovak teaching.

**Deployment-ready.** `build-school-kit.ps1` assembles a hand-over folder and
**refuses to build if anything is missing** — a 90%-complete kit is worse than
none because it looks ready. Verified: the client starts from inside the kit,
standalone, and responds correctly.

```
school-kit\
  RUN.cmd              double-click; asks condition, session, salt
  client\              stdlib only — nothing to install but Python
  kontrola\SKONTROLUJ.cmd   run the SAME DAY
  tlac\CO-VYTLACIT.txt      what must be printed, and from which appendix
  data\                     hand this back
  PRECITAJ-MA.txt           procedure in Slovak, incl. every failure mode
```

Small things that decide whether a session happens: `.cmd` not `.ps1`
(double-clicking a `.ps1` opens Notepad); Python checked with a Slovak error
message; **refuses to start without the salt**, because the school holds it.

---

## Slovak context (your supervisor's topic text asked for this)

- **97%** of students use some AI; ~43% exclusively ChatGPT
- **~25%** of Slovak teachers use it in teaching; **28%** have had training
  (vs 60% in Czechia); ~5% use it to personalise instruction
- a third of teachers say they could not tell AI work from pupil work
- AI literacy entering the ŠVP; ChatGPT Edu for ~80,000 teachers; national
  project running — **adoption is outpacing domestic evidence**

## Deployment evidence (assignment clause 1)

Khanmigo's two-year cluster RCT in 18 schools: **0.06–0.08 SD per school year**,
**gains matching Khan Academy *without* AI**, **only 15% of pupils with access
used it**, and pupils repeatedly demanded direct answers instead of answering
Socratic questions.

That last one is your thesis's offloading hypothesis, observed at scale. And
0.06–0.08 SD sits right on Kraft's median of 0.10 — so it is not a failure of
that tool, it is the normal size of an educational effect.

---

**198 pages · 479 tests · 166 checks · clean build**

## Still open

- `hariyanto2025adaptive` author list is `{Hariyanto, Didik and others}` — verify
  the real author list before submission; I could not confirm it from the DOI page.
- The 12 critical-thinking items are written but **not piloted**. They are a
  draft instrument, and the thesis says so.
- FCI access must be requested from PhysPort with a verified account.
- iBobor task reuse still needs permission from FMFI UK.
