# Analysis

Every number, table and figure in Chapters 5 and 6 of the thesis is produced by
the code in this directory. Nothing in the text is typed in by hand.

The point of running this *before* data collection is that an analysis plan is
as prone to defects as any other software, and can be tested the same way: write
down the hypotheses as an explicit generating model with known parameters, run
the frozen plan against data from it, and check that the plan recovers what was
put in. Anything the plan cannot recover on simulated data it will not recover
on real data either.

## Files

| File | What it does |
|---|---|
| `dgp.py` | Generating model. Encodes hypotheses H1–H8 as explicit parameters anchored in published effect sizes. Simulates at the item level (Rasch), so the analysis sees the same kind of input it will see in reality — measurement error, MAR dropout, variable lesson fidelity and control-condition contamination included. |
| `pipeline.py` | The frozen analysis plan, end to end: concurrent Rasch calibration through anchor items, item fit, DIF, the mixed model, cluster-robust contrasts, TOST, Holm, moderation, calibration metrics, process measures, five robustness analyses, missing-data sensitivity. |
| `identification.py` | What randomisation buys and what it does not. Three estimators of the mechanism under three different assumption sets — mediation, instrumental variable, dose-response — plus a sensitivity analysis for unmeasured mediator–outcome confounding. |
| `power.py` | Monte-Carlo power. Sweeps classes against treatment-effect heterogeneity, for superiority, for equivalence, and for the *precision* of the mechanism estimate. |
| `validate_plan.py` | Operating characteristics of the whole plan over 1000 simulated studies: decision rates, bias, interval coverage, sign stability. |
| `peqi.py` | The prompt taxonomy, the anchor corpus, the classifier, inter-rater reliability. |
| `export_macros.py` | Emits every volatile number as a LaTeX macro. |
| `figures.py` | All nine thesis figures, print-safe, greyscale-legible. |
| `verify_thesis.py` | 91 consistency checks across the analysis outputs and the thesis source. |
| `run_all.py` | Runs the whole chain in dependency order. |

## Running

```bash
pip install -r requirements.txt
python run_all.py           # everything, in order (~2 min)
python run_all.py --quick   # skips the two long simulations
cd .. && ./build.ps1        # then rebuild the PDF
```

All seeds are fixed, so repeated runs are bit-for-bit identical. Running the
steps individually leaves the rest stale, which is exactly how numbers in a
thesis go wrong — hence `run_all.py`.

## Why the thesis contains no hand-typed numbers

Not as a discipline, but as an impossibility. `export_macros.py` writes 315
`\newcommand`s into `out/thesis_numbers.tex`; the prose references them by name.
Re-running updates the document, so there is nothing to forget.

This replaced an earlier approach — write the numbers, check them afterwards —
which failed twice in exactly the same way: adding one variable to the
generating model shifted the random stream and silently invalidated dozens of
values at once. `verify_thesis.py` now checks what generation cannot: that every
referenced macro exists, that no decimal has been typed back into a volatile
table, that the hypotheses declared confirmatory are the same three in all three
places they appear, and that every cross-reference and citation resolves.

## What the simulations changed about the design

Six defects surfaced here that would otherwise have surfaced after collection,
when correction is impossible:

1. **Rank-deficient carry-over coding.** A separate "no carry-over" level for
   period 1 is collinear with the period-1 indicator; the model returned
   infinite standard errors.
2. **Delayed test too short.** Eight items per topic gave a person reliability
   of 0.63. Twelve give 0.73 and still fit one lesson.
3. **Sample size set by the wrong test.** Twelve classes suffice for
   superiority but not for the equivalence claim, which matters more.
4. **A hypothesis in the confirmatory family that the design cannot identify.**
   Randomisation assigns the condition, not prompt quality, so the mediation
   claim rests on an assumption the design does not deliver. The family was
   rebuilt from three claims randomisation *does* identify.
5. **Test forms were never actually equated.** The text promised linking
   through anchor items; the code calibrated each form separately, which would
   have made the immediate-to-delayed difference an artefact of test difficulty.
6. **No precision criterion for the mechanism.** Significance is near-certain
   at nine classes; a usefully narrow interval is not (0.31 vs 0.97 at
   eighteen).

## What the simulation changed about the design

Three defects surfaced here that would otherwise have surfaced after collection,
when correction is impossible:

1. **Rank-deficient carry-over coding.** A separate "no carry-over" level for
   period 1 is perfectly collinear with the period-1 indicator; the model
   returned infinite standard errors. Fixed by assigning period 1 the reference
   condition, the standard cross-over remedy.
2. **Delayed test too short.** Eight items per topic gave a person reliability of
   0.63 — unacceptable for the primary outcome. Twelve items give 0.68 and still
   fit one lesson.
3. **Sample size set by the wrong test.** Twelve classes suffice for the
   superiority test (power 0.80) but not for the equivalence claim (0.73), which
   is the more important of the two. Target raised to 18 classes.

The simulation also quantified two things the write-up has to state: effects are
attenuated by roughly a fifth through measurement error, and the cluster-robust
test on *J* − 1 degrees of freedom is mildly conservative (rejection rate 0.040
against a nominal 0.05).

## After data collection

Exactly two things change: the input file, and the deletion of the warning
paragraph at the top of Chapter 6. The code, the table structure, the figures
and the section order stay as they are. Anything not in the plan gets labelled
exploratory in the text and its *p*-values are not interpreted confirmatorily.
