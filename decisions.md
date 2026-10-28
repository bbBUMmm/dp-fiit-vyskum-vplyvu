# Decisions log

Scope changes, methodological choices, and excluded options, with the reason.
Append; do not rewrite. Dates are absolute.

---

## 2026-10-09 — The assessment layer: how the tool checks and evaluates pupils

Context: the design, the analysis plan and the capture layer were complete; the
chain from *a pupil sitting a test* to *a row in the analytic file* was not. The
instruments existed only as LaTeX prose in Appendix A. Everything below either
closes that gap or is a consequence of closing it.

Code: `assessment/` (standard library only, 75 tests in 10 sections).
Validation: `mastersLaTeX/analysis/assessment_validation.py` → `out/assessment.json`.
Thesis: new §5 "Ako nástroj overuje a vyhodnocuje žiakov", new Appendix H.

### D1. The item bank is the single source of truth. Appendix A is generated.

**Decided:** items live in `assessment/banks/*.json`. The runner, the scorer and
the printed appendix all read from there. `tex_export.py --check` fails the build
if the appendix on disk is not what the bank produces.

**Why:** two copies of one specification have already drifted twice in this
project (PEQI in Python vs Java; the UTF-8 console guard in one entry point out
of eighteen), and the repair went into one copy each time. Here the losing copy
would have been the one the thesis is marked on.

**Cost:** the appendix can no longer be hand-edited. Prose rationale stays
hand-written and is kept in separate sections, so the two kinds of content are
visibly distinct.

### D2. The six anchor items are now identical across forms. They were not.

**Found:** §5 claimed "šesť položiek je v oboch formách totožných" and Appendix A
claimed the anchors appear "v nezmenenej podobe". Not one of the six was
identical — 1024 vs 512 elements, a ten- vs eight-element array, four options vs
a free numeric answer, two rubric items reworded.

**Consequence, quantified** (`equating_recovery`): with planted forgetting of
0.45 logits, identical anchors recover 0.508 (bias +0.058). With the delayed
"anchors" half a logit easier — a conservative reading of 1024 vs 512 — the
estimate is **−0.048**. The sign flips: the study would have reported pupils
*improving* over three weeks when the planted truth was that they forgot. Nothing
would have signalled it; the model converges, item fit passes, the interval is
narrow.

**Decided:** anchors are character-identical, closed-format only, and span at
least three cognitive levels. `bank.cross_validate()` refuses to load a bank that
violates any of those.

**Why closed-format only:** an open item's link would carry the inter-rater error
of its scoring into the equating, turning a scoring error into a scale error.

### D3. Both test forms are 12 items with one blueprint.

**Decided:** the immediate form drops from 16 items to 12. Both forms now have 12
items, 15 points, one blueprint (2/2/4/3/1), and 3 rubric items each.

**Why:** forced by the time budget (D5). But it is a methodological gain, not a
concession: isomorphy of forms is the assumption the primary contrast rests on,
and two forms of different length with a different format mix are not isomorphic
in any sense a reader can check. Equal length + one blueprint + six genuinely
common items is the textbook common-item design, and the validator can enforce
all three.

**Cost, stated:** reliability falls from about 0.78 to about 0.73 — the same as
the delayed form, which is the primary outcome.

### D4. Identical anchors cost the absolute retention estimate. Declared, not hidden.

**Found** (`testing_effect`): identical anchors mean the pupil meets those six
items twice, which is retrieval practice. At 0.25 logits of practice, planted
forgetting of 0.45 is estimated at 0.069 — it nearly vanishes. The between-
condition contrast *is* protected (0.346 against a planted 0.30), because every
pupil in every condition sits both forms.

**Decided:** the confirmatory family is unaffected and stays. Absolute retention
is reported as overstated by the size of the practice effect — a declared
limitation, in §5 and in Appendix H.

### D5. A rotated-anchor design is recommended, with a pilot. Not adopted yet.

A fixed anchor set cannot measure the practice effect: every pupil has met every
anchor, so there is no comparison group. Randomisation supplies one. Each topic
has a pool of 18 calibrated items (3/3/6/5/1 by level); six are drawn per pupil
as *that pupil's* shared set (1/1/2/1/1); both forms are then 12 items and both
satisfy the blueprint, for every pupil.

**Result** (`rotated_anchor_design`): practice recovered at 0.210 against a
planted 0.25. Forgetting 0.522 against a planted 0.45 (bias +0.072) versus 0.237
with fixed anchors (bias −0.213). Rotation cuts the bias roughly threefold *and*
yields an estimate of the practice effect.

**Decided: recommended, not adopted.** The 18 items per topic already exist, but
the pool must be calibrated in a pilot before a draw from it is blueprint-neutral,
and the single evaluation-level item is shared by every pupil, so practice is not
estimable at that level. Primary design stays fixed-anchor with the D4 limitation.

**Two failed attempts, recorded because they were instructive:**
- correcting after the fact double-counted the half of the practice effect the
  mean-difficulty shift had already absorbed, and made the estimate worse;
- estimating ability, difficulty and practice jointly returned a practice effect
  of −378 logits, because a pupil who answers every administered item correctly
  has no finite ML measure, the Newton step runs to the bound, and the bounded
  pupils push the shared parameter.
What works: difficulties fixed from the immediate occasion (no practice there by
construction), delayed ability measured only on items the pupil had not met.

### D6. The time budget is computed from items. Three sessions did not fit.

**Found:** `measurement_plan.py` computed each block as *items × one average
seconds-per-item*. That is sound when items cost the same and wrong here: the
immediate test had ten closed items at ~40 s and six rubric items at ~150 s, and
the flat 55 s/item understated it by five minutes. The transfer test is six
rubric items that Appendix A itself specifies at 25 minutes; the average gave it
6.5. The errors all point one way, because every understated instrument is one
with open items, and those sit in session T4 — which carries the primary outcome.

Total understatement: **25.6 minutes**, worst case the transfer test by **18.5**.
Recomputed from items, three of five supervised sessions overran.

**Decided — four changes:**
1. the immediate form is 12 items (D3);
2. the topic pre-check moves to the end of the *previous* informatics lesson
   (4 min, supervised, 2–3 days ahead) — prerequisite knowledge does not change
   in two days without instruction, so the covariate loses nothing;
3. the lesson is **64 minutes, not 75**. The fidelity checklist V1–V3 summed to
   35+40+15 = 90 minutes of teaching inside a 90-minute block that also has to
   hold a test and a questionnaire. The schedule and the checklist contradicted
   each other by fifteen minutes, in the same appendix;
4. **T4 splits into T4a and T4b.** Together they are 92 minutes of measurement,
   and transfer is the measurement fatigue damages most.

**Cost:** measurement lessons the school gives rise from 3 to **4**. Accepted: a
lesson is cheaper than a measurement that does not fit into one.

**Also added:** a fatigue cap of 45 minutes on the longest *unbroken* stretch
(not on the session total), and per-session handover cost. Fatigue interacts with
motivation, which the conditions plausibly affect, so an over-long session adds
noise correlated with treatment — a validity requirement, not a courtesy.

### D7. Pupil codes get a check character. A mistyped code was silent data loss.

**Found:** the protocol has the school hold the code↔pupil roster, which solves
re-identification. It left correct *entry* to the pupil's fingers: ~1650 code
entries across the study. A typo produces two errors at once — one pupil silently
loses an occasion (and with it the change score the study exists to measure), and
a pupil who does not exist silently gains a row. Worse than visible missing data,
because the analysis plan imputes.

**Decided:** three layers — ISO 7064 MOD 37,36 check character; an alphabet with
no confusable characters (O/0, I/1/L, S/5, Z/2, B/8), so an excluded character
yields a *specific* message rather than a blank refusal; and one-code-one-sitting,
which is the only layer that catches a pupil entering someone else's **valid**
code.

**A standard's claim that is not true:** ISO 7064 MOD 37,36 is usually described
as detecting every adjacent transposition. Measured exhaustively, about one in two
thousand survives (`GY-YEDET-R` → `GY-YDEET-R`; both verify). Since the code space
is 9 765 625 and a school needs ~30, `issue()` discards any candidate with such a
weakness (about one in six), and the test re-derives the property exhaustively.
100% by construction rather than 99.95% by citation.

**Rejected:** self-generated identification codes (initials, mother's birth
month). Weaker *and* worse — recall at three weeks is imperfect, and the
components are quasi-identifiers, so the "anonymous" code is re-identifiable by
anyone holding a class list.

### D8. Test-taking effort is measured. The negative control was not enough.

The thesis already names the confound ("learned more" vs "tried harder after the
lesson they enjoyed") and answers with a negative control. A negative control
says *that* something is wrong, not *what*. Effort is measurable from per-item
response times, and it is plausibly differential here: condition G removes effort
during the lesson and is predicted to be the most pleasant.

**Decided:** three rapid-guessing thresholds (10% of expected time; an absolute
floor; the trough of the response-time distribution where there is one), all three
reported. The bimodal rule returns *no threshold* on a unimodal sample — a method
that always returns a number would invent rapid guessing in a class that did none.
An effort gap of 0.08, large enough to fake the SESOI, is detected in 100% of
simulations at a 0% false-positive rate.

**Decided:** flagged responses are **not deleted**. Deletion would silently change
the estimand from "what pupils scored" to "what they scored when trying", and those
differ by condition exactly when it matters. Primary analysis on everything;
effort-filtered analysis as a declared robustness check; both always reported.

### D9. Contamination during the test is measured, not asserted.

Fidelity item V12 ("during the test pupils had no access to the assistant") was an
observer's assertion about twenty screens, in a study about AI and learning whose
outcome is a test a pupil could take with AI.

**Decided:** five signal families from three independent sources; exclusion only
on two signals from *different* families; and the detector is calibrated on
session T0a, where contamination is impossible by construction, so its
false-positive rate is known. A field rate quoted without that baseline is the
same error as a positive rate quoted without specificity.

**Decided:** no pupil is ever named to the school. A flag that could reach a grade
would change the pupil's incentive to take the test honestly and destroy the
measurement it was introduced to protect. The school report carries a class rate.

**Honest number:** at a realistic lookup (2–4 items of 12, not all 12) detection
is **0.61** at a 0.0% false-positive rate. The first version of the simulation made
every contaminated pupil answer every item in 3.5 s with 18 s of focus loss and
scored a perfect 1.00 — which says nothing. A flattering number is worse than a
modest one.

### D10. A rule-based classifier ships alongside the mixture model.

LPA is a statement about a *sample*: hundreds of pupils, and a pupil's label
depends on who else is in the file. A teacher with 22 pupils gets nothing — so the
assignment's "categorise users" deliverable was unusable by the tool's actual user.

**Decided:** a deterministic rule over *absolute*, pre-registered cut points, each
placed where the construct changes rather than where the sample splits (PEQI 0.25
and 0.50 are the taxonomy's own L1 and L2 boundaries; ABHR 0.50 is the only
non-arbitrary point on a proportion; bias 0.15 exceeds the measurement error of a
12-item test).

**Results:** one class (22 pupils) — rule ARI 0.764, LPA finds no profiles at all
(k=1, ARI 0.0). At 330 — rule 0.749, LPA 0.910. At 900 — 0.756 vs 0.924. The same
pupil reclassified inside 40 random cohorts always gets the same label.

*Not comparable* with the ARI ≈ 0.5 in §5: that simulation is in standard units
with a within-profile SD of 0.62; this one is on the absolute scales the rule
needs, with less spread. The two columns of the new table compare to each other.

**Decided:** both. The mixture stays as the research question "is this population
a mixture, and of what"; the rule is what the school gets. The rule cannot
discover an unanticipated profile and the mixture can; they are not competitors.

**Honest limitation, reported:** shifting one cut point by ±20% moves agreement by
at most 0.179 (worst: PEQI_HIGH), but shifting all five at once and in the same
direction moves it by 0.227. The rule *is* sensitive to its joint setting — which
is exactly why the cut points must be derived from the scale's meaning and fixed
in advance. Pre-registration here is load-bearing, not a formality.

**Also added:** an incremental-validity test against a planted null in which the
profile is prior attainment relabelled. Power 1.00, false-positive rate 0.07.
Without it the typology could have been a renamed covariate and no reader could
have told.

### D11. A pupil with too little evidence is "undetermined".

**Decided:** an indicator below its minimum evidence is *absent*, not merely noted.
The first version listed it as missing and then used it anyway, and misclassified
the one pupil the distinction exists for: a pupil with a single prompt had a PEQI
of 0.50 computed from that prompt, cleared the "asks for explanations" gate, and
was labelled a critical user on the strength of one question.

Condition K has no assistant, so a tool-use profile is undefined for it — not
missing data, but a condition in which the construct does not exist.

### D12. Open items are never machine-scored.

**Decided:** closed items are scored automatically; rubric items leave as
`pending` and return double-coded. `finalise()` refuses to write the analytic file
while any rubric item is uncoded, because a silent zero looks like a wrong answer.
Coder disagreements are resolved by consensus and never averaged; the
disagreement rate is itself reported.

**Why not automate:** automatic marking of free Slovak prose about algorithmic
reasoning would be unreliable *differentially*. A pupil who spent a lesson reading
fluent assistant prose writes more fluent prose, and any surface-feature marker
would reward that — manufacturing part of the effect it is measuring. This is the
defect the PEQI classifier already had once and had to be repaired for.

### D13. Three reports, three audiences, suppression applied by code.

**Decided:** teacher — misconception counts by item, class level, **no condition
breakdown** (useless pedagogically, and it is what creates cells of two pupils).
School — a few aggregates, cells below 5 suppressed, no comparison for a class
under 12 pupils or a cohort under 3 classes. Pupil — **no individual score**,
because reliability around 0.73 supports comparing groups and not a statement
about one person; handing a pupil a number the instrument cannot justify is the
error the thesis criticises elsewhere. Pupils receive the full item set and keys
after the study.

A `disclosure_audit` walks the actual reports looking for sub-threshold counts,
anything resembling a pseudonym, and any crossing with condition.

### D14. The UTF-8 console guard is now shared, not copied.

**Found:** `run_all.py` failed on a clean shell — `measurement_plan.py` died with
UnicodeEncodeError while printing a result it had already computed. The fix had
been applied to `server.py` and to nothing else, and `run-all-tests.ps1` exports
`PYTHONIOENCODING=utf-8`, so the harness masked the bug it existed to catch.

**Decided:** one shared `analysis/console.py`, called by all 18 entry points, plus
a test that asserts every entry point calls it *and* runs the affected scripts with
the masking variable removed. Third recurrence of this defect class; the repair is
now to the class, not to the file.

### D15. Appendix A no longer documents instruments the study does not administer.

**Found and fixed:**
- a 20-item entry knowledge test that the protocol had already replaced with
  five-item per-topic pre-checks (F-protokol, improvement 2). It appeared in no
  session budget. The appendix documented an instrument the study does not use and
  omitted the one it does. The 20 items are kept as the pool the pre-checks draw
  from, and the three pre-checks are now written out;
- **Jr. MAI declared as 18 items in five places and listed with 19.** Reliability
  and time were therefore computed for an instrument that did not exist. Dropped
  "Po skončení premyslím, či by sa to dalo urobiť lepšie" — within the evaluation
  subscale it overlapped M8 (checking completeness) and M16 (summarising at the
  end), and dropping it leaves a clean 6/6/6 split.

### D16. Test lengths are read from the bank, not typed into the model.

**Found:** after shortening the immediate form (D3), `dgp.py` still had
`n_items_ipt = 16` and `measurement_plan.py` still declared a 16-item outcome
instrument. The generating model simulates at the item level, so the measurement
error in every simulated outcome — and therefore the power analysis, the plan
validation and every number Chapter 6 reports — depends on test length. The
thesis would have reported power for a test it does not administer.

**Decided:** both modules read the counts from `assessment/banks/`, and a test
asserts they match *and* that changing the bank moves the model.

**What it cost, measured:** nothing the confirmatory family depends on. The
mechanism precision at 18 classes is unchanged (P(CI width < 0.20) = 0.965,
median SE 0.035), because the primary outcome is the *delayed* test, which was
already 12 items, and the mechanism runs PEQI → delayed. The shortened immediate
form affects only the immediate-recall layer, a secondary outcome. Worth stating:
the change was forced by minutes and paid for in a place the design does not lean
on.

### D17. One time budget. I had created a second one.

**Found:** adding the item-level budget (D6) did not remove the flat-average one.
For part of a day the thesis had two time budgets that disagreed — the old one
reporting that every session fits, the new one reporting that three do not.

This is the fourth instance of the defect this session kept finding, and the only
one I introduced myself: one specification, two implementations, repaired in one.
I had spent the day writing about that pattern and then reproduced it.

**Decided:** `measurement_plan.time_budget()` delegates to
`assessment/sessions.py`. Its own contribution — reliability *by role*, and
longitudinal invariance — is not duplicated anywhere and stays. 3 524 bytes of
duplicate budget deleted.

**How it was found:** by running both and reading the two answers side by side.
Not by reasoning about it.

### D18. The homework is not budgeted as a lesson.

`sessions.py` modelled the EduPage questionnaire as one 45-minute lesson, giving
it 38 minutes of slack and making an instrument look comfortable because it was
compared against the wrong thing. An unsupervised session is bounded by how much
of a pupil's evening it is reasonable to ask for: **15 minutes**, declared
explicitly rather than inherited from the lesson length.

### D19. The pre-registered rules are in the SAP, not only in the code.

Appendix C now carries the five profile cut points with their derivations, the
minimum-evidence thresholds, the three rapid-guessing rules, the two-family
exclusion rule, the coder-agreement rules, and the anchoring/practice decisions —
including what happens when each is missed. They were in the code with their
reasoning; a plan that lives only in code is not pre-registered.

### D20. `expected_sec` is an estimate. The pilot converts it.

The item-level budget is better than the flat average and it is **not a
measurement**: the per-item times are the author's judgement about what an
attentive pupil needs. The whole decision to split session T4 rests on numbers
nobody has yet observed.

Stated in Appendix H, because otherwise the budget reads as a finding when it is
a hypothesis. Two consequences recorded there: the pilot replaces the estimates
with observed medians and the budget is recomputed; and even if every estimate
were a third too high, the *ordering* of instruments by cost would not change —
which is what actually drove the redesign. The flat average got the ordering
wrong, putting the most demanding instrument in the plan behind the cheapest. An
error in level is a different thing from an error in order, and only the second
is fixed so far.

### D21. The kit administers tests, and the school issues the codes.

The school receives a folder, not a repository. `build-school-kit.ps1` now
includes the assessment module plus two launchers:

* **`KODY.cmd`** issues the pupil codes and is run **by the school**. It writes
  two files: the codes, which go to the researcher, and a roster with a column
  for names, which stays. A kit that made the researcher issue the codes would
  put the code-to-pupil mapping on the researcher's laptop, and no protocol prose
  would undo that.
* **`TEST.cmd`** administers a test, deliberately separate from `RUN.cmd` for the
  lesson. The lesson and the test have different rules — during the test the
  assistant must be unreachable — and one entry point that could start either is
  one keystroke away from invalidating the measurement.

**And the kit is verified by running, not by listing.** The build imports every
module from inside the assembled folder, loads the banks, issues a code and
checks that a typo in it is refused; the build fails if any of that fails. A file
list proves nothing about a folder whose imports break when files are copied to a
flatter directory than the one they were written in.

### D22. One contamination family is not available on collection day.

**Found by actually running the kit** as a classroom would — school issues codes,
six pupils sit the 12-item test through the real runner, output goes to the
scorer with no translation layer. It worked, and it surfaced something unit tests
could not: the time-versus-difficulty family needs *calibrated item
difficulties*, which do not exist before the Rasch calibration. Families B, T, S
and C run the same afternoon; family I runs only in the analysis.

**Decided:** the class report the school receives on the day rests on four
families of five, and says so. In the unit tests the difficulties came from a
fixture, which is exactly why the gap was invisible there.

### D23. Three subjects, one topic each (2026-10-16) — draft, not yet in LaTeX

**Decided by the author:** the design moves from one subject with three topics
to three subjects with one topic each. Draft: `drafts/temy-troch-predmetov.md`;
the thesis carries only a `% TODO` reference at `sec:temy`.

| Subject | Topic |
|---|---|
| Informatics | searching in an array, linear vs binary (existing T1, fully built) |
| Mathematics | compound interest and exponential growth |
| Physics | DC circuits, series vs parallel |

**Why these:** all three share one structure — a linear or additive intuition
that fails, against the correct model — so one blueprint (2/2/4/3/1) serves all
three and the crossover keeps comparable content. Both new topics are in the
innovated ŠVP for gymnázium (verified against the statpedu.sk PDFs). Sequences
were rejected for maths because the ŠVP lists them among topics outside its scope.

**Excluded:** FCI (mechanics). It has a Slovak translation, but mechanics is
usually taught early, so in years 2–3 it would not be new learning. DIRECT
(circuits) has no Slovak or Czech translation and takes 30 min, too long for the
immediate-test slot, so the physics test is built in-house with DIRECT's
documented misconceptions as distractors.

**New risks, recorded in the draft:** a different teacher per subject (possible
teacher × condition interaction); recruitment narrowed to gymnázium and technical
SOŠ; year placement is set by each school's ŠkVP, not the ŠVP, and must be
checked per school.

### D24. The informatics topics are not in the gymnázium ŠVP (2026-10-23) — finding, recruitment filter

**Finding (checked in the text of the innovated ŠVP, informatika_g_4_5_r.pdf):**
algorithmics covers command sequences, variables, loops, branching and debugging.
Arrays, searching in an array, binary search, recursion and memoization do not
appear. D23 said both *new* topics were verified against the ŠVP; the informatics
topic was never checked, and it fails. Physics (Newton's laws; series/parallel
resistors) and maths (compound interest, probability) are in the ŠVP;
conditional probability and arithmetic/geometric sequences are not.

**Consequence:** the informatics arm can run only in schools that teach
informatics beyond the ŠVP (informatics-focused gymnázia, programming seminars,
IT fields at technical SOŠ). Candidate list with sources:
`drafts/kandidatske-skoly.md`.

**Open for the author/supervisor:** keep the topic and accept a sample of
above-average schools (narrower generalisation), or choose an informatics topic
that is in the ŠVP (e.g. loops and debugging) and recruit from any gymnázium.

### Open — for the supervisor

1. **Rotated anchors (D5):** adopt with a pilot, or keep fixed anchors and declare
   the absolute-retention limitation? My recommendation: declare it now, pilot the
   rotation, decide before collection.
2. **One extra measurement lesson (D6):** the split of T4 costs the school a fourth
   lesson. Is that acceptable in recruitment, or should the transfer test shrink?
3. **Cut-point pre-registration (D10):** the five cut points need to be fixed in
   writing before any data exist. They are in `assessment/profiles.py` with their
   derivations; they should go into the SAP (Appendix C) as well.
4. Unchanged from the previous consultation: schools, ethics approval, pilot vs
   full study, the `hariyanto2025adaptive` authorship question, and whether the
   physics/FCI arm is worth keeping.
