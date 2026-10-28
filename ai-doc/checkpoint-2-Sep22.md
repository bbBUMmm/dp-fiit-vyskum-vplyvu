# Checkpoint 2 — 22 Sep 2026

Second iteration. The brief was: *test your own text with proofs, find
inconsistencies and gaps, then go deeper.* That is what this iteration did, and
what it found turned out to matter more than what I added.

---

## State

| | |
|---|---|
| Thesis PDF | **148 pages**, 0 errors, 0 undefined refs, **0 overfull boxes above 15 pt** |
| Slovak text | ~38 500 words (was ~32 100) |
| Bibliography | 87 entries (was 74) |
| Figures | 10, all generated |
| Analysis code | 3 574 lines across 10 modules (was 1 757 / 5) |
| **Automated tests** | **161 passing** — 91 thesis-consistency, 29 capture, 41 Java |

Reproduce everything:

```powershell
cd mastersLaTeX\analysis ; python run_all.py   # ~2 min, ends with 91/91 verified
cd ..                    ; .\build.ps1         # -> out\main.pdf
```

---

## 1. What the self-testing found

I wrote `analysis/verify_thesis.py` to check every number in the thesis against
the outputs that were supposed to have produced it. On its first run: **84 of 88
claims verified, 4 mismatches.** Two were cosmetic. Two were the same real
defect, and it was the most serious problem in the thesis.

### The defect: a confirmatory hypothesis the design cannot identify

The state-of-the-art chapter declared H3 and H6 (the mediation hypothesis)
"confirmatory". The analysis plan's confirmatory family was a *different* set.
Chasing why exposed something worse than a bookkeeping error:

> **Randomisation assigns the condition, not prompt quality.**

So the total effect of A vs G on retention is identified by design; the a-path
(condition → PEQI) is identified by design; but the claim that the effect *runs
through* PEQI is not. It rests on "no unmeasured common cause of prompt quality
and retention" — an assumption that is almost certainly false in a classroom,
where conscientiousness plausibly drives both. The thesis was asserting
something it had not earned, and had put it in the confirmatory family.

**Fix, in three parts:**

1. **The confirmatory family was rebuilt** from the three claims randomisation
   *does* identify and that *can* fail: A > K, G ≡ K, and A > G on delayed
   retention. All three now agree across the three places they appear, and
   `verify_thesis.py` checks that agreement on every run.
2. **The mechanism was moved out of the family** and split: H6a (A > G, the
   reduced form — randomisation-identified, confirmatory) and H6b (the effect
   runs through PEQI — assumption-dependent, reported but not claimed).
3. **H6b is now triangulated** across three estimators resting on three
   *different* assumption sets, plus a sensitivity analysis.

### The triangulation, and its honest verdict

| Estimator | Assumption that must hold |
|---|---|
| Mediation (LSEM) | no unmeasured mediator–outcome confounding |
| **Instrumental variable** | the condition reaches retention *only* via PEQI |
| Dose–response within G | none — identifies nothing, but its absence would be damaging |

Using the randomised pedagogical layer as an **instrument** for prompt quality
is the key move. The exclusion restriction is plausible here precisely because
the design holds model, exercises, interface and teacher constant — the
remaining channels are few enough to enumerate (there are two, and one of them
is arguably part of prompt quality). The three estimates agree closely.

The sensitivity analysis is where honesty costs something. Over 1000 simulated
studies, the threshold ρ\* at which the indirect effect vanishes averages
**0.13**, and falls below the pre-set fragility line of 0.15 in **68.5 %** of
studies. Translated: a confounder explaining roughly an eighth of the residual
variance in *both* prompt quality and retention would wipe out the mediation
result — and that is entirely plausible.

So the thesis now says: **that** the adaptive layer works is established by the
design; **how** it works is supported by triangulation, with the fragility
quantified rather than hidden. The mediation claim does not appear among the
conclusions.

### An unexpected result worth keeping

Across 1000 studies the **instrumental-variable estimate is about twice as
precise as the mediation estimate** (SD 0.045 vs 0.092). That is the opposite of
the usual expectation — IV is normally inefficient because the first stage is
weak. Here the first stage is enormous (the pedagogical layer moves prompt
quality by ~1.5 SD) and a weak instrument never occurred in any of the 1000
runs.

This generalises into a recommendation the thesis now states: **if an experiment
already contains a randomised manipulation acting mostly on one process
variable, use it as an instrument rather than relying on a mediation model.**
The estimate is tighter, and its identifying assumption is at least partly under
the designer's control — the mediation model's assumption is under nobody's.

---

## 2. Five further gaps the audit found

| Gap | Fix |
|---|---|
| Thesis promised anchor-item equating; code calibrated each form **separately** | Concurrent calibration implemented. It recovers the true forgetting drop to within **0.044 logits** and raised delayed-test reliability 0.68 → 0.73. Without it the retention claim — the thesis's whole point — was an artefact of test difficulty. |
| Item-fit and DIF rules were stated but never computed | Both implemented (infit/outfit, ETS bands). The exclusion rules now have something to exclude. |
| Dropout was MCAR in the DGP, so the MAR check checked nothing | Dropout now depends on prior knowledge. MCAR is correctly **rejected** (t = −5.28). Multiple imputation and an adversarial worst case added. |
| Plan named **five** robustness analyses, implemented **one** | All five now run: fidelity floor, per-protocol vs ITT, raw scores, random slopes, period-1-only. The random-slope model estimates τ²\_ct — the very parameter the power analysis showed to be binding. |
| VTR and ABHR declared as secondary outcomes, never analysed; ABHR not even simulated | Both simulated and analysed with FDR correction. |
| No precision criterion for the mechanism | Added. Significance is near-certain at 9 classes (0.96); a *usefully narrow* interval is not (0.31). At 18 classes: 0.97. |

That last one gave a **second, independent reason for 18 classes**, from a
completely different direction than the equivalence test. Two unrelated
constraints breaking at the same sample size is a much stronger argument than
either alone.

---

## 3. The failure that repeated, and the structural fix

Twice, adding a single variable to the generating model shifted the random
stream and silently invalidated dozens of numbers in the prose. The checker
caught it both times — 20 mismatches the first time, 19 the second — but
catching is not preventing.

So the numbers are no longer written. `export_macros.py` emits **315
`\newcommand`s**; the prose references them by name. Re-running updates the
document. The checker's job changed accordingly: it now verifies that every
referenced macro exists, that no decimal has been typed back into a volatile
table, and that the confirmatory family matches in all three places.

Then a subtler version of the same problem appeared. With the numbers
auto-updating, two *sentences* went false: "the generic tool fell below the
control" and "the effect does not survive the worst case". Both had been true of
one random draw.

**Fix:** `validate_plan.py` runs the whole decision logic over 1000 simulated
studies and reports operating characteristics. The narrative now rests on those:

- all three confirmatory decisions reached together in **84 %** of studies
  (the independent power simulation says 86 % — two separately written
  simulations agreeing to two decimal places);
- bias under 0.02 on every contrast;
- interval coverage 0.98 against nominal 0.95 — **conservative**, consistent
  with the Type-I rate of 0.040;
- the near-null G − K contrast comes out **positive in 15.8 %** of studies,
  which is exactly why no sentence may depend on its sign.

`run_all.py` now runs the chain in dependency order and stops on failure rather
than producing downstream outputs from stale inputs.

---

## Sub-conclusion

Three things are worth stating plainly.

**First, the self-testing was worth more than the additions.** The largest
single improvement was not new analysis but discovering that a hypothesis
labelled "confirmatory" was one the design could not identify. No amount of
extra content would have fixed that; only checking the work against itself did.
Six design defects have now surfaced this way, two of them in the formulation of
the hypotheses themselves — and every one surfaced while correction is still
free.

**Second, the thesis became more careful and therefore weaker, which is
correct.** The mediation claim moved out of the conclusions. Sentences about the
direction of a near-null effect were deleted rather than rewritten. The
instrumental-variable estimate is reported as an *upper* bound because the
exclusion restriction is only partly satisfied. Each of these makes the thesis
claim less — and each makes what remains defensible. An examiner who probes the
mechanism claim will find it already qualified, with the fragility quantified,
rather than find it undefended.

**Third, the reproducibility story is now a real contribution rather than a
promise.** "No number is typed by hand" stopped being a discipline and became an
impossibility. That is a small piece of engineering, but it is the difference
between a claim that holds until someone edits the file and one that holds by
construction — and the thesis now documents the two failures that forced it,
because the failures are the argument.

**What has not changed:** the mitmproxy capture layer has still never seen live
traffic. Extraction is unit-tested against four payload shapes but never against
a real ChatGPT session. That remains the one claim in the thesis I cannot verify
from here, and it should be the first thing tried.

---

## Next

1. `git init` — still not a repository. The `.gitignore` is written and correct.
2. Run the mitmproxy addon against a live session (§5 above).
3. Take the power table to the supervisor: **18 classes**, now with two
   independent justifications.
4. Ethics submission — appendix E is complete and is the critical path.
5. Decide what to trim: the conceptual part has a 15-page limit and chapters
   5–7 exceed it. The appendices already carry the detail, so trimming is
   mechanical — but it is your call what goes.
