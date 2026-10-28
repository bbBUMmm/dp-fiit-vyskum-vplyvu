# Is SESOI = 0.30 defensible?

*A focused review of one number in this thesis — 22 September 2026*

---

## The question

The thesis fixes the smallest effect size of interest at **0.30 SD** and uses
that single number twice:

- to power the **superiority** test (A > K),
- as the **equivalence** bound for the claim `G ≡ K` — one of the three
  confirmatory claims.

The justification given is one clause: *"roughly one third of a standard year's
growth."*

> **Is 0.30 the right bound — and can one number do both jobs?**

It matters because the two uses pull in opposite directions. For superiority a
large SESOI is **conservative**: you are powered only for big effects. For
equivalence a large SESOI is **permissive**: the wider the band, the easier it
is to declare two things the same. A number chosen to be safe for the first use
is automatically unsafe for the second.

---

## Direction 1 — The benchmark literature says 0.30 is enormous

**Cohen's conventions (0.2 / 0.5 / 0.8)** are still the default, and Kraft
(2020) shows they are the wrong ruler for education:

> "effects that are small by Cohen's standards are large relative to the impacts
> of most field-based interventions."

**Kraft's empirical benchmarks**, built from **1,942 effect sizes across 747
RCTs** of pre-K–12 interventions with standardized achievement outcomes:

| Kraft (2020) | effect size |
|---|---|
| Small | < 0.05 |
| Medium | 0.05 – < 0.20 |
| **Large** | **≥ 0.20** |

Median across the 747 RCTs: **0.10 SD**. The cut-points are the 37th and 69th
percentiles of the actual distribution. **One in four effects is zero or
negative.** Lortie-Forgues & Inglis (2019) found a mean of **0.06 SD** across
141 IES- and EEF-funded RCTs.

Kraft's own defence of calling 0.20 "large" is the relevant one here:

> "by 5th grade, student achievement improves about 0.40 SD or less over the
> course of an academic year (Bloom et al., 2008), and schools only account for
> around 40 percent of these achievement gains… Formal schooling, our society's
> defining education intervention, is delivered over more than 1,000 hours a
> year, costs over \$10,000 per student, and barely qualifies as producing large
> effects in middle and high school."

On this ruler, the thesis's SESOI of 0.30 is not "a third of a year's growth"
in any meaningful sense — it is **half again larger than the threshold at which
a whole-school intervention counts as large.**

**Why the old numbers were wrong.** Lipsey & Wilson (1993) found a mean of
0.50 across 300+ meta-analyses, which appeared to vindicate Cohen. Kraft
attributes that to "small samples, weak research designs, and proximal outcomes
highly-aligned to the interventions," and names Hattie's reviews as continuing
to propagate it. Bloom's "2 sigma" studies — three-to-four-week experiments on
probability and cartography — anchored a generation's expectations at 1.0–2.0
SD.

---

## Direction 2 — …but the thesis is not measuring what Kraft measured

This is the strongest counter-argument, and it is a good one.

Kraft's benchmarks are explicitly and only for **"causal research that
evaluates the effect of education interventions on standardized student
achievement."** The thesis measures a **researcher-built, topic-aligned,
Rasch-scaled 12–16 item test**, administered three weeks after a 90-minute
lesson on exactly that topic. Different instrument, different metric.

Cheung & Slavin (2016), from 645 studies across 12 reviews, quantify the gap:

> effect sizes were "roughly twice as large for published articles, small-scale
> trials, and experimenter-made measures, compared to unpublished documents,
> large-scale studies, and independent measures"

with researcher-designed aligned tests often **two to four times** larger than
broad standardized tests.

So 0.20 standardized ≈ 0.40–0.80 on this thesis's metric, and a bound of 0.30
here translates to roughly **0.08–0.15 standardized** — squarely inside Kraft's
*medium* band, and defensible.

**Which leaves the actual defect.** Not that 0.30 is too big, but that the
thesis's justification for it — *"a third of a standard year's growth"* — is
stated on the **standardized** metric (annual-growth norms come from Bloom et
al. 2008, which are standardized-test norms) while the study measures on the
**proximal** metric. The two are silently mixed in a single clause. The number
may be right; the reason given for it is not.

---

## Direction 3 — The AI-education literature can't referee this

Recent meta-analyses of generative AI on learning report pooled effects of
**g = 0.254** (Chen & Xu 2024, 28 studies), **0.573** (22 studies), **0.577**
(Liu et al. 2025, 37 studies), and **1.14** (66 studies, 5,708 cases). One
review puts personalised tutoring at **g = 1.858** with a 95% CI of
**[−1.24, 4.96]** — an interval so wide it excludes nothing.

That five-fold spread is not a finding about AI. It is Cheung & Slavin's
methodological-features result showing up again: small published trials with
experimenter-made measures produce large numbers. **The literature cannot
supply a defensible SESOI for this study, and a thesis that borrowed one from
it would be borrowing an artefact.**

---

## Direction 4 — What a SESOI is supposed to be

Lakens, Scheel & Isager (2018) are explicit that a SESOI must answer a
*normative* question, not a descriptive one — not "what size is this?" but
**"why would an effect smaller than this not matter?"** They list justifiable
routes: cost-benefit analysis, anchor-based methods (Anvari & Lakens 2021),
Simonsohn's "small telescopes" (the effect an earlier study had 33% power to
detect), and literature-based bounds. And:

> "Some researchers state, but do not justify, the SESOI used in their
> equivalence tests… researchers should always explain why they chose a
> particular SESOI."

The thesis's clause is descriptive. It says what 0.30 *is*. It does not say why
a difference of 0.25 between having a chatbot and not having one would be
educationally uninteresting — which, given the policy question the thesis opens
with, is not obvious at all.

---

## What the bound actually buys: computed

`analysis/sesoi.py`, 3,000 simulated studies per cell, J = 18 classes,
τ²_ct = 0.03, the design's own estimator.

**Probability of declaring `G ≡ K`:**

| true G−K | bound 0.15 | 0.20 | 0.25 | **0.30** | 0.40 |
|---|---|---|---|---|---|
| **0.00** (true null) | 0.175 | 0.567 | 0.847 | **0.959** | 1.000 |
| 0.10 | 0.076 | 0.288 | 0.556 | **0.777** | 0.977 |
| 0.15 | 0.028 | 0.130 | 0.314 | **0.563** | 0.928 |
| 0.20 | 0.008 | 0.046 | 0.139 | **0.318** | 0.789 |
| 0.25 | 0.001 | 0.008 | 0.040 | **0.134** | 0.544 |

Read the 0.20 row. **With the planned bound and the planned sample, a true
difference of 0.20 SD is certified as "no difference" about one time in three.**
At 0.15 it is better than a coin flip. This is not a flaw in TOST; it is what a
bound of 0.30 means, stated in the only terms that matter.

**And the cost of narrowing it** — classes needed for an 80% declaration rate
when the truth is *exactly* zero:

| bound | classes needed |
|---|---|
| 0.30 | **18** (the current plan) |
| 0.20 | **36** |
| 0.15 | **48** |

So this is a real trade, not a free improvement. Halving the bound doubles the
study. The thesis cannot afford 36 classes, and saying so plainly is better
than choosing a bound because it fits the sample.

---

## What should change

Three things, none of which requires more classes:

1. **Justify the bound normatively and on the right metric.** Replace "a third
   of a standard year's growth" with (a) an explicit statement that the outcome
   is a proximal researcher-built test, not a standardized one, (b) the
   translated standardized equivalent (≈ 0.08–0.15 using Cheung & Slavin's
   2–4× factor), and (c) a reason why a smaller difference would not change the
   decision a school faces. Cite Kraft (2020) and Lakens et al. (2018) rather
   than leaving the number bare.

2. **Report the operating characteristics of the equivalence claim, not just
   its outcome.** The table above belongs in the thesis. A reader is entitled
   to know that the declared band admits a 0.20 effect one time in three. This
   costs nothing and converts an overstated claim into an exact one.

3. **Split the two uses of the number.** Keep 0.30 for superiority, where it is
   conservative. For the equivalence claim, state the conclusion as what the
   data support — *"a difference larger than 0.30 SD on this metric can be ruled
   out"* — and never as *"G is equivalent to K."* The SAP's own wording is
   already close to this; the abstract and conclusion are not.

A fourth, for the pilot: the bound should ideally be anchored empirically —
ask teachers what difference in retention would change what they do. That is
Lakens' anchor-based route and it is cheap to run on one class.

---

## Sources

- [Kraft, M. A. (2020). *Interpreting Effect Sizes of Education Interventions*. Educational Researcher 49(4), 241–253](https://www.matthewakraft.com/s/Kraft-2020-Interpreting-Effect-Sizes-ER.pdf) — the 747-RCT benchmarks, the median of 0.10, the critique of Cohen, Hattie, Lipsey & Wilson and Bloom
- [Kraft, M. A. (2023). *The Effect Size Benchmark That Matters Most: Education Interventions Often Fail*. Educational Researcher](https://www.matthewakraft.com/s/Kraft-2023-The-Effect-Size-Benchmark-that-Matters-Most-ER.pdf) — the failure-rate framing
- [Cheung, A. C. K. & Slavin, R. E. (2016). *How Methodological Features Affect Effect Sizes in Education*. Educational Researcher 45(5), 283–292](https://journals.sagepub.com/doi/10.3102/0013189X16656615) — 645 studies; experimenter-made measures roughly twice as large
- [Lakens, D., Scheel, A. M. & Isager, P. M. (2018). *Equivalence Testing for Psychological Research: A Tutorial*. AMPPS 1(2), 259–269](https://journals.sagepub.com/doi/10.1177/2515245918770963) — what justifies a SESOI; anchor-based and small-telescopes routes
- [Lakens, D. *Equivalence Testing and Interval Hypotheses*, in *Improving Your Statistical Inferences*](https://lakens.github.io/statistical_inferences/09-equivalencetest.html) — the justification requirement
- [Bloom, H. S., Hill, C. J., Black, A. R. & Lipsey, M. W. (2008)](https://journals.sagepub.com/doi/10.3102/0013189X16656615) — annual growth norms, the source of the "year's growth" comparison (via Kraft 2020)
- [Lortie-Forgues, H. & Inglis, M. (2019)](https://journals.sagepub.com/doi/10.3102/0013189X19832850) — mean 0.06 SD across 141 IES/EEF RCTs (via Kraft 2020)
- [*Undergraduate students' learning outcomes with ChatGPT: A meta-analytic study* (2025)](https://www.sciencedirect.com/science/article/pii/S2666920X25001766) and [*A Meta-Analysis of ChatGPT's Influence on Learning Achievement*, IRRODL](https://www.irrodl.org/index.php/irrodl/article/view/8775) — the spread of pooled AI effects
- [*Generative AI in higher education: a meta-analysis of intellectual and social–emotional outcomes*. Frontiers in Psychology (2026)](https://www.frontiersin.org/articles/10.3389/fpsyg.2026.1848745/full) — the tutoring estimate with the uninformative interval
