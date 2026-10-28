# Does ICAP's top rung survive a machine partner?

*A focused review of one assumption in this thesis — 22 September 2026*

---

## The question

PEQI weights its five levels `0, .25, .50, .75, 1.00`. The top step — L4 above
L3 — is not a design choice. It is a claim borrowed from ICAP: that
**Interactive** engagement produces more learning than **Constructive**
engagement. The thesis currently asserts it in one sentence and cites Chi &
Wylie (2014).

The question this note asks, and only this one:

> **Does the Interactive > Constructive ordering hold when the interactive
> partner is a language model rather than a person?**

It matters because if the answer is no, the top weight is wrong, and PEQI —
the thesis's main methodological contribution — is mis-ordered at exactly the
level the adaptive condition is designed to produce.

---

## Direction 1 — What ICAP actually claims, and why

Chi's Interactive mode is not "a conversation happened". It has two stated
criteria (Chi et al., 2018, §3.1.4):

> "(a) both partners' utterances must be primarily generative/Constructive,
> that is, adding ideas beyond what is already presented in the learning
> materials, and (b) each partner's contributions address or engage the other
> partner's contributions, thereby they are mutually and reciprocally
> generating or co-generating."

And the *mechanism* by which I is supposed to beat C is stated equally
precisely:

> "each speaker can not only infer from their own knowledge, but they can also
> infer from the knowledge articulated by the partner… collaborative
> interactions involve the knowledge-change processes of store, activate, link,
> **infer-from-own, and infer-from-other**. This suggests that interactive
> collaboration has the potential of creating innovative knowledge that
> **neither partner could have generated alone**."

Two things follow that the thesis had not noticed.

**First**, ICAP mode is a property of *the dyad*, not of one utterance. PEQI
codes a single student prompt. So PEQI's L4 cannot be Chi's Interactive — it is
at most the student's half of it.

**Second**, Chi gives an explicit rule for mapping published studies onto ICAP
modes, and it cuts against the intuitive reading of AI tutoring:

> "the mapping of interventions in published results to ICAP modes often
> requires that we transfer the focus of an intervention in terms of **what the
> learners did**… rather than what the instructors/experimenters did."

By Chi's own rule, a sophisticated partner does not raise the learner's mode.
A pupil who receives a brilliant Socratic reply and does nothing generative
with it is not in the Interactive mode. That is an argument *for* PEQI's
decision to code only student utterances — and simultaneously an argument that
doing so cannot measure Interactive engagement at all.

---

## Direction 2 — Is I > C even supported with humans?

Weakly, and the framework's own authors say so more plainly than its users do.

**The critics.** Thurn, Edelsbrunner, Berkowitz, Deiglmayr & Schalk (2023),
commenting in *npj Science of Learning*, are blunt:

> "To the best of our knowledge, there has been **no systematic evaluation** of
> the hierarchy of modes of engagement as the central hypothesis derived from
> the ICAP framework (i.e. I > C > A > P)… Chi and Wylie explicitly state that
> their review of evidence is **selective** and that it only refers to research
> in favor of the framework."

On Menekse et al. (2013) — the study Chi puts forward as the strongest test —
they report:

> "the interactive and constructive modes showed a **negligible and
> non-significant difference**, which does not support the ICAP hypothesis."

**The counter-reading.** Menekse et al.'s own abstract claims the opposite:
"all the increases from condition to condition were significant." The conflict
is not fabricated by either side. Menekse ran two studies; the critics' charge
attaches to Study 1 (42 undergraduates, within-group, one engagement mode per
whole day), while the supportive claim rests largely on Study 2 (120
undergraduates, between-group). The critics' objection to Study 2 is different
and about validity: the Passive condition had learners **read text aloud**, "an
artificial task that undermines basic self-regulation strategies such as the
rereading of difficult passages."

**Meta-analytic counter-evidence.** In the scientific-reasoning domain,
Engelmann, Neuhaus & Fischer (2016) found no significant difference between
constructive and interactive interventions, and moderator analyses reportedly
favoured *constructive*. (Reported at second hand — via Frontiers in Education,
2022 — not read in the original for this note.)

**The framework's own flagship study did not test it.** Chi et al.'s (2018)
five-year translation project is the largest ICAP field study there is. It
confirmed C > A. It did not test I > C, and the paper says why:

> "if a class was intended by teachers to be a Constructive class, only 53% of
> the written directives pertains to using generative verbs, and **only 7% of
> the written directives pertains to collaborative co-construction for intended
> Interactive classes**."

The Interactive condition was never realised. The rung PEQI's top weight
encodes has, on its own authors' account, not been cleanly tested even with
human partners.

---

## Direction 3 — Does the mechanism transfer to a machine?

This is where the disagreement becomes substantive rather than evidential,
because Chi's mechanism makes a prediction that the AI case can falsify.

**The transfer argument (optimistic).** The knowledge-change processes are in
the *learner's* head. `infer-from-other` does not care about the ontology of
the other. An LLM reliably produces contributions that engage the learner's own
and contain information they did not have — more reliably than a randomly
assigned classmate. So I > C should hold, perhaps more strongly.

**The symmetry objection.** Chi's mechanism is *co-generation* producing
"innovative knowledge that **neither partner could have generated alone**".
With an LLM there is no such quantity: the model can generate the whole
solution alone, and usually will if asked. What looks like co-construction is
one party retrieving and the other receiving, with turn-taking. On this reading
an AI dialogue has a ceiling set entirely by the learner's own generative
contribution — which is the **Constructive** ceiling. L4 should then be
weighted equal to L3, not above it.

**The repair objection.** A large share of why peer dialogue works is
*breakdown and repair*: the partner misunderstands, you must re-explain, and
re-explaining is where the learning happens — the protégé effect. An LLM does
not genuinely misunderstand and reliably signals comprehension whether or not
it has any. The repair loop never fires. This predicts
`I(with AI) < I(with peer)`, and possibly `< C`.

**The over-supply objection.** This one is specific to the study's own
hypothesis. If the partner supplies the inference the learner would otherwise
have had to generate, the interaction does not add `infer-from-other` on top of
`infer-from-own` — it **substitutes** for it. That is the offloading hypothesis
in ICAP's vocabulary, and it makes the top rung not merely unearned but
possibly inverted.

**Where they can be told apart.** The three objections make different
predictions about the *assistant's reply*, which PEQI does not currently look
at. The symmetry objection says the reply is irrelevant. The repair objection
says a reply that fails to understand helps more than one that succeeds. The
over-supply objection says a reply that supplies content hurts. Coding the
reply is cheap — it is already captured — and it discriminates.

---

## Direction 4 — What pupils actually do with a chatbot

An ICAP-informed rubric applied to 784 undergraduate–ChatGPT interactions
(Interactive Learning Environments, 2026) found **most questions were Passive
or Active**; Constructive and Interactive questions appeared mainly in longer
multi-turn conversations.

Two readings, both defensible:

- *The top rung is rare, so its weight scarcely matters.* If almost nothing
  lands at L4 in ordinary use, mis-weighting it barely moves the index.
- *The top rung is exactly what the manipulation produces, so its weight
  matters more here than anywhere.* Condition A is built to push prompts up the
  scale. In this study's simulated data, 28% of condition-A on-task prompts sit
  at L4 against 6% in condition G. The rung is rare in the wild and common
  under the intervention — the worst case for an uncertain weight.

---

## Direction 5 — The design answer: make the machine fallible

If the missing ingredient is breakdown and repair, supply it deliberately.
Kucharavy, Vallez & Percia David (2025) invert the tutoring relation: the LLM
is the *mentee*, prompted to err on course material, and students diagnose the
error. Students who successfully diagnosed the planted error gained on average
**0.72 points on a 1–6 scale**; the authors project a reduction in second-midterm
failure from 28% to 8%.

This is the only position in the debate that is *constructive rather than
diagnostic*: it accepts the asymmetry objection and engineers around it. It is
also directly relevant to condition A, whose current design does the opposite —
it makes the assistant maximally competent and constrains only what it says.

---

## What this means for PEQI

**The reframing.** PEQI's L4 is defined as: *states the student's own
reasoning, claim or prediction and asks the assistant to critique, confirm or
locate the error in it.* Against Chi's criteria that is **a Constructive act
addressed to a partner** — a precondition for Interactive, not an instance of
it. The honest description of the PEQI scale is therefore:

> a gradient of *constructive* engagement, ordered by how much of the cognitive
> act the pupil retains, with L4 the point at which their construction becomes
> available for external critique.

That ordering needs only `C > A > P` plus a within-Constructive gradient. It
does **not** need `I > C` — the one rung that is disputed. The thesis has been
claiming more support than it needs.

**Does anything depend on the disputed rung?** Computed, not argued
(`analysis/icap_weights.py`, J = 12 simulated classes, 265 pupil-sessions per
condition):

| Weighting | L4 weight | PEQI G | PEQI A | gap A−G | t | d |
|---|---|---|---|---|---|---|
| ICAP standard | 1.00 | 0.292 | 0.662 | **0.369** | 43.5 | 2.48 |
| Flat top (L4 = L3) | 0.75 | 0.277 | 0.591 | **0.314** | 44.0 | 2.52 |
| Demoted top | 0.60 | 0.267 | 0.548 | **0.281** | 41.2 | 2.46 |
| Ordinal (median level) | — | 0.231 | 0.679 | **0.448** | 38.0 | 2.09 |

- The ordering and its significance survive **every** weighting, including one
  that penalises L4 below L3.
- **Only 15% of the A−G gap is carried by the disputed rung.** The other 85%
  comes from the bottom of the scale: condition G produces L0/L1 prompts that
  condition A does not. The index separates the conditions by *how much
  offloading it prevents*, not by *how much co-construction it creates*.
- The IV mechanism estimate moves from 0.247 to 0.261 across all four — but for
  a weaker reason: the mediator is standardised before it enters the model, so
  any re-weighting that preserves the rank ordering of pupils leaves the
  z-scored mediator nearly unchanged. That robustness would not survive a
  re-weighting that *reordered* pupils.

---

## What should change in the thesis

Three things, all small:

1. **Stop asserting `I > C`.** Replace the one-sentence ICAP citation with the
   weaker claim actually required (`C > A > P` plus a within-Constructive
   gradient), and say openly that the top rung is disputed, citing Thurn et al.
   (2023) against Chi & Wylie (2014). This *strengthens* the thesis: it rests
   the instrument on the better-supported part of the framework.

2. **Add the flattened-weight sensitivity.** The existing weight-sensitivity
   analysis only tried a monotone alternative, which cannot test the
   theoretically contested question. The `flat_top` and `demoted_top`
   weightings do, and they pass.

3. **Pre-register the dyadic test.** Code the assistant's *reply* as generative
   or not, and the pupil's *next* prompt as engaging it or not. Then ask
   whether a true-Interactive indicator (both generative, mutually addressing —
   Chi's actual criteria) predicts retention over and above PEQI. If it does,
   the top rung earns its weight in this setting. If it does not, ICAP's I
   level is doing no work with a machine partner, and that is a finding worth
   reporting on its own.

A fourth, for future work rather than this thesis: condition A makes the
assistant maximally competent. The protégé literature suggests a condition in
which it is deliberately fallible might beat it. That is a different
experiment, and a better one to run next.

---

## Sources

- [Chi, M. T. H. et al. (2018). *Translating the ICAP Theory of Cognitive Engagement Into Practice*. Cognitive Science 42, 1777–1832](https://education.asu.edu/sites/default/files/lcl/chi_et_al-2018-cognitive_science.pdf) — definition of the Interactive mode, the `infer-from-other` mechanism, the "map by what the learner did" rule, and the 7% co-construction figure
- [Thurn, C. M., Edelsbrunner, P. A., Berkowitz, M., Deiglmayr, A. & Schalk, L. (2023). *Questioning central assumptions of the ICAP framework*. npj Science of Learning 8, 49](https://www.nature.com/articles/s41539-023-00197-4) — no systematic evaluation of the hierarchy; selective review; the Menekse critique
- [Menekse, M., Stump, G. S., Krause, S. & Chi, M. T. H. (2013). *Differentiated Overt Learning Activities for Effective Instruction in Engineering Classrooms*. Journal of Engineering Education 102(3), 346–374](https://onlinelibrary.wiley.com/doi/abs/10.1002/jee.20021) — the two studies at the centre of the dispute
- [Chi, M. T. H. & Wylie, R. (2014). *The ICAP Framework: Linking Cognitive Engagement to Active Learning Outcomes*. Educational Psychologist 49(4), 219–243](https://education.asu.edu/sites/g/files/litvpz656/files/lcl/chiwylie2014icap_2.pdf) — the framework as cited by the thesis
- [*An ICAP-informed rubric for analyzing students' questions to generative AI*. Interactive Learning Environments (2026)](https://www.tandfonline.com/doi/full/10.1080/10494820.2026.2702559) — 784 student–chatbot interactions; ICAP modes in practice
- [Kucharavy, A., Vallez, C. & Percia David, D. (2025). *LLMs Protégés: Tutoring LLMs with Knowledge Gaps Improves Student Learning Outcome*. BEA @ ACL 2025](https://aclanthology.org/2025.bea-1.19/) — the deliberately fallible partner
- [*Testing an intervention of different learning activities…* Frontiers in Education (2022)](https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2022.977788/full) — reports the Engelmann, Neuhaus & Fischer (2016) meta-analytic finding that constructive activities yielded larger effects than interactive ones
- [*Putting ICAP to the test: how technology-enhanced learning activities are related to cognitive and affective-motivational learning outcomes in higher education*. Scientific Reports (2024)](https://www.nature.com/articles/s41598-024-66069-y) — recent direct test (abstract only; full text paywalled at time of writing)
- [Gürses, G. & İnceelli, A. (2024). *Evaluation of Studies Based on the ICAP Framework in Learning Environments*. TOJET 23(2)](https://files.eric.ed.gov/fulltext/EJ1422395.pdf) — descriptive review of 71 ICAP-based articles
