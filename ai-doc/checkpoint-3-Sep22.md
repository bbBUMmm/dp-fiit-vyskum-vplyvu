# Checkpoint 3 — 22 September 2026

State: thesis builds clean at **163 pages**, 0 errors, 0 undefined references.
**398 automated tests across 6 suites**, all passing. **117 consistency checks**,
all passing. **391 generated LaTeX macros** — still no hand-typed number in the
thesis, and now no hand-typed number *about* the thesis either.

```
analysis layer        105 passed     mastersLaTeX/analysis/test_analysis.py   (NEW)
thesis consistency    117 verified   mastersLaTeX/analysis/verify_thesis.py
capture layer          29 passed     ai-prompt-monitor/mitm/test_capture.py
PEQI analysis (Java)   45 passed     ai-prompt-monitor  (incl. cross-impl)     (NEW)
pedagogy               67 passed     exercise-client/test_pedagogy.py
exercise client e2e    35 passed     exercise-client/test_server.py
```

---

## Sub-conclusion for this iteration

The previous two iterations asked *is the design identified?* and *is the
manipulation real?* This one asked a narrower and more uncomfortable question:
**is the instrument that measures the mediator safe to use as a mediator in this
particular design?**

The answer was no, and the reason is specific to the design rather than to the
code. Condition A's self-explanation gate *requires* pupils to write "I think
that…" before a worked solution unlocks. The classifier read that opening as
evidence of reasoning. So the manipulation was manufacturing the mediator out of
the interface, on every single prompt, and the index would have confirmed a
mechanism that was partly an artefact of its own measurement.

Three things follow, and they are the substance of this iteration:

1. **The defect is measurable, and was measured.** Four words in front of every
   L0/L1 anchor moved 34 of 34 to the top of the scale — **+0.88 of PEQI per
   prompt**, more than twice the between-condition effect the study is powered
   to find.
2. **What such an error does to each estimator is not obvious, and is now
   derived.** The reduced form is completely immune; the IV estimate is
   *attenuated* by differential error that *inflates* the first stage; the
   mediation estimate is inflated and attenuated at once and the two can cancel
   exactly, giving the right answer from wrong coefficients.
3. **A study cannot verify its own instrument from inside.** Hence a blinded,
   condition-stratified audit, sized to detect δ = 0.05 with power 0.80.

The second-largest finding is organisational rather than statistical: **the same
specification implemented twice drifted, silently.** The repair went into the
Python analysis layer and not into the Java layer that scores real traffic. The
thesis would have reported figures from a repaired classifier while pupils were
scored by a broken one.

The third is methodological: the design had **no outcome that was forbidden to
move**. Without one, "pupils learned more" and "pupils tried harder on the test
after the lesson they enjoyed" are the same contrast.

---

## What was added

### 1. `mastersLaTeX/analysis/measurement.py` — differential measurement error (NEW)

Model: `M̃ = M + δ·A + e`, where δ is condition-dependent bias and `e` is
classical noise; `λ = var(u)/(var(u)+var(e))`.

| Claim | Consequence | Verified |
|---|---|---|
| **P1** Reduced form contains no mediator | Immune to *any* amount of δ and e | identical to 1e-9 |
| **P2** `β_IV = ITT_Y/(a+δ)` | Differential error **attenuates** the per-unit IV estimate | 0.231 vs 0.229 predicted |
| **P3** `indirect = ITT_Y·(1+δ/a)·λ` | Inflated *and* attenuated | 0.229 vs 0.232 predicted |
| **P3b** Exact cancellation at `δ/a = (1−λ)/λ` | Unbiased estimate from wrong coefficients | at δ = 0.288 |
| **Corollary** `med/IV = (1+δ/a)·λ` | Both factors estimable → calibrated expectation for the triangulation | 0.964 vs 0.965 predicted; jumps to 2.10 under ρ = 0.35 |

**The practical upshot**: P1 dictates the *reporting order*. The primary
mechanism quantity is the reduced form, because no classifier error can touch
it. The per-unit effect on PEQI comes second, corrected and uncorrected. Leading
with `b` would be leading with the most fragile number.

**The audit**: blinded, condition-stratified double coding of 150 prompts per
condition (~15 pupils each), pupil-clustered SE. Power 0.80 at δ = 0.05, SE
0.018, unbiased. Full power curve 60 → 300 prompts.

**The correction**: `M* = M̃ − δ̂·A`, *then* `b* = b̂/λ̂`. Order matters —
dividing a differentially biased coefficient by a reliability makes it worse.
Bootstrap propagates uncertainty in both nuisance parameters. Verified to
recover planted `a = 0.80` and `b = 0.30` (naive gives 1.05 and 0.224).

### 2. PEQI classifier repaired, in two independent parts

Reported separately so neither takes credit for the other:

| Stage | κ on anchors | Veneer shifts | δ per prompt |
|---|---|---|---|
| v0 as written | 0.839 | 34/34 | +0.88 |
| v1 lexicons anchored on word boundaries | 0.893 | 34/34 | +0.88 |
| v2 justification requirement for L4 | **0.987** | **0/34** | **0.00** |

The repair raised agreement *and* closed the attack. That is not automatic — a
rule can buy robustness with accuracy.

**Lexical bugs found** (all substring traps): `sprav` inside `spravne`,
`vytvor` inside `vytvori`, `lebo` inside `alebo`, `hra` inside `hranicne`.
The `alebo` one is notable as a *recurrence*: the same trap had already been
found once, in a different lexicon, in an earlier session.

**Boundary moved deliberately, and documented**: L4 now requires that the pupil
put an *argument* up for judgement, not merely a value. "I think the answer is
O(n log n), is it right?" is L1. "I think it's O(n), where am I going wrong?" is
L4 — a request to *locate* an error can only be made about reasoning. This moves
the boundary *against* the thesis's own hypothesis, which is the direction that
needs less defending.

### 3. Cross-implementation agreement (NEW)

`analysis/peqi.py` writes `cross_impl_corpus.json` — 129 cases (90 anchors,
34 veneered, 5 boundary) each with the level Python assigns.
`CrossImplementationTest.java` demands the same answers.

On first run it found **9 disagreements from 6 distinct causes**. All were
ported; none would have raised an error, all would have produced slightly
different numbers.

Also added: a test that a `self_explanation` event is **not** scored as a
prompt. That is the concrete realisation of the whole differential-error
threat, and it is now a property of the study rather than a detail of a parser.

### 4. `mastersLaTeX/analysis/falsification.py` — negative controls (NEW)

Two pre-specified outcomes on which the condition must have **no** effect:

- **9 placebo items** on an untaught topic, inside the same immediate test.
- **Matrix short form** re-administered at week 6.

Tested by **equivalence (TOST)**, not by failing to reject — "we looked and
found nothing" is a small sample, not a control.

| Leak | control alarms | declares equivalence |
|---|---|---|
| 0.00 | 0.05 | 0.91 |
| 0.10 | 0.19 | 0.73 |
| 0.20 | 0.61 | 0.35 |
| 0.30 | **0.92** | 0.05 |
| 0.45 | 1.00 | 0.00 |

**The honest part.** The bound had to be set at 0.30, not tighter. At 0.20 the
control fails to declare equivalence **about half the time when the truth is
exactly zero** — a control that cries wolf on half of all clean studies is not a
control. So the claim it supports is stated precisely: *a non-learning channel
large enough to explain the whole primary effect is excluded; one large enough
to explain part of it is not.* Reaching 0.15 needs ~4× the classes.

**Non-obvious practical result**: lengthening the placebo test helps much less
than expected — half-width 0.171 (3 items) → 0.142 (9) → 0.132 (16). The
contrast is within-pupil, so the residual is the pupil × occasion component and
item sampling is only one part of it. Nine items; the other seven are wasted
lesson time.

### 5. `mastersLaTeX/analysis/test_analysis.py` — 105 tests (NEW)

The statistical layer had **no tests of its own**. `verify_thesis.py` checks
that the thesis *agrees with* the analysis — a wrong estimator would be quoted
faithfully and all 117 checks would still pass.

Every test either plants a known answer and demands it back, or states a
property that must hold for any input:

- Rasch recovers planted item difficulties (max error < 0.20) and abilities
  (r = 0.90; ceiling is test length, not the estimator)
- Concurrent calibration recovers planted forgetting (−0.40) where separate
  calibration does not — the test asserts that separate calibration is *worse*
- 2SLS recovers planted b; a violated exclusion restriction visibly inflates it
- `total = direct + indirect` exact to 1e-6; a-path labelled identified,
  b-path labelled ASSUMED
- Holm monotone, never > 1, at least as strict as BH; a family of one unpenalised
- Williams balance: each condition follows each other exactly twice
- DGP anchoring exact to 0.02 on every outcome; dropout MAR not MCAR;
  bit-identical under the same seed
- Measurement propositions re-verified on a **4-point parameter grid**, so they
  cannot be passing at one lucky point

### 6. Source-corruption class found and closed

**Three real defects, invisible to everything:** `\ref` → `<CR>ef` twice, and
`\footnotesize` → `<FF>ootnotesize` once — a tool had interpreted `\r` and `\f`
as escapes. The PDF printed `ef{sec:rozhovory}` as body text.

Neither the build nor the 91 existing checks saw them. The build had nothing to
warn about: TeX prints the orphaned tail as text and no reference is missing.
The cross-reference check verifies that every `\ref` *resolves* — and a
destroyed `\ref` is not a `\ref`.

> **A check that a command resolves cannot see a command that stopped existing.**

Two detectors added: any control byte in a `.tex` source (catches the cause
exactly), and orphaned command tails before `{`, with the tail list derived from
the commands the thesis actually uses so it grows with the document.

### 7. The thesis's numbers about itself are now generated too

Macro count, module count, check count, test counts per suite — all generated
and cross-checked. A thesis claiming it types no numbers by hand while
hand-typing its own statistics contradicts itself in the same sentence.

Added checks caught two live inconsistencies: the conclusion said "six design
faults" when chapter 6 listed nine, and "eight contributions" when it had nine
paragraphs.

The loop is genuinely self-referential (the consistency checker is one of the
suites, so its check count is part of the total it verifies), so `run-all-tests.ps1`
refreshes the macros and says so when a count moves.

---

## Thesis changes

| Where | What |
|---|---|
| §5 `sec:diferencialna` (NEW) | Differential mediator error: model, 3 propositions, cancellation case, diagnostic ratio, audit design + power table, two-step correction, residual limitation |
| §5 `sec:negativne-kontroly` (NEW) | Three non-learning channels, two controls, why TOST, power table, why the bound is 0.30 and not tighter, decision rule |
| §6 `sec:vysledky-merania` (NEW) | Propositions verified; what each estimator returns; the case no diagnostic sees; correction recovers truth |
| §6 `sec:vysledky-negkontroly` (NEW) | Controls behave; what the bound does and does not license; diminishing returns in test length |
| §6 `sec:co-odhalila-simulacia` | 6 → 9 design faults; new paragraph on the *three different ways* faults were found (running the plan, writing about it, attacking it — the third was most productive and is rarest in the literature) |
| §7 `sec:dve-implementacie` (NEW) | The drift, its 6 causes, and pinning the spec as data |
| §7 `sec:testy` (NEW) | 398 tests in 6 suites; why checks ≠ tests |
| §7 reproducibility | Escape-damage class; generated self-description |
| App. B `sec:dominancia` (NEW) | The veneer attack measured, the two-part repair, what it does not catch |
| App. B coding rules | Justification requirement; answer-only dominance; 3 new binding boundary cases |
| App. B tables | Now macro-driven (they had gone stale on the classifier repair — which the old literal-matching check failed to prevent) |
| App. C | Module table + "checks are not tests" |
| §1 abstract, §2 lay summary, §8 conclusion | 7 → 9 contributions; veneer story in plain language; two new limitations |

---

## Known limits of this iteration

- The veneer attack is closed **on 90 anchors**, and cross-implementation
  agreement is verified **on 129 cases**. Neither proves a real classroom leaves
  no differential error. That is what the blinded audit is for.
- One residual anchor disagreement remains (`vysvetli mi rozdiel medzi…`,
  L2 coded L3). Left deliberately: a rule tuned to fix it would be overfitting
  to 90 examples, which is the failure mode the thesis criticises elsewhere.
- Neither control catches the case where **human coders err in the same
  direction as the machine**. Stated in the thesis rather than papered over.
- BKT parameters still conventional, not fitted (needs pilot data).
- 16 overfull hboxes remain, all < 15pt and pre-existing.

## Next

1. Pilot on one class; fit BKT parameters from it.
2. Ethics approval — critical path.
3. Write the placebo items for the negative control (9 items, topic outside the
   three, matched in format).
4. Consider: does the veneer problem generalise to other ICAP-anchored
   instruments? If any interface that *requires* an epistemic form is scored by
   an instrument that *rewards* it, the same artefact appears. That is a paper.
