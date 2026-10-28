# Session 21 Sep 2026 — what I built while you were out

> **Superseded in part.** A second iteration on 22 Sep 2026 rebuilt the
> confirmatory hypothesis family, added the identification analysis, and moved
> every number in the thesis from hand-typed to generated. Read
> [`checkpoint-2-Sep22.md`](checkpoint-2-Sep22.md) first; this document remains
> accurate for the design, the artefact and the toolchain.

**Short version:** the thesis now has a complete, defensible research design with a
pre-registered analysis plan that has already been run and validated, 32k words of
Slovak text, 7 generated figures, 1 757 lines of analysis code, and a working
replacement for the capture layer that failed in DP1 — plus the Java analysis layer
the thesis describes, which didn't exist. The PDF builds clean on your Windows
machine: **128 pages, 0 errors, 0 undefined references**.

```powershell
cd mastersLaTeX ; .\build.ps1          # -> out\main.pdf
cd ai-prompt-monitor ; mvn test         # -> 41 tests
python mitm\test_capture.py             # -> 29 tests
```

**70 automated tests pass.** Four real bugs surfaced while writing them — see §2.

---

## 1. The direction I chose, and why

You suggested: ordinary lecture → feedback + test, then an AI-assisted lecture on a
similar topic → feedback + test, and asked me to work out the "somehow" and the metrics.

I kept your shape and made it rigorous. Three things forced changes:

- **Your title requires three conditions, not two.** "Generických *a adaptívnych*
  nástrojov" means the comparison has to be K (traditional) vs G (generic AI) vs
  A (adaptive AI). So the design is three-armed.
- **Two lectures on two topics confounds topic with condition.** If the AI lecture is
  also the harder topic, you learn nothing. Fixed with a **3×3 Latin square, six
  sequences** — every student gets all three conditions across three matched topics,
  and every condition follows every other equally often (so carry-over is estimable,
  not assumed away).
- **A test at the end of the lesson measures the wrong thing.** This is the crux. The
  literature that looks contradictory stops being contradictory once you separate
  *performance during the lesson*, *immediate recall*, and *recall after a delay*.
  Bastani et al. (2024, ~1000 Turkish high-schoolers) found generic ChatGPT gave
  **+48 % during practice but −17 % on the later exam**; a scaffolded GPT Tutor gave
  +127 % during practice and no exam penalty. So the design adds a **delayed test at
  3 weeks, unannounced**, plus a **far-transfer test**.

### The thesis's actual claim

> A tool raises in-lesson performance and the *feeling* of learning almost
> unconditionally. Its effect on *durable* learning depends on whether the student's
> interaction stayed **generative** or became **offloading**. Nobody has measured that
> directly — Gerlich used self-report, Kosmyna used EEG, Bastani didn't measure it at all.

### The original contribution

**PEQI — Prompt Epistemic Quality Index.** Every prompt a student sends is classified
L0–L4 on a scale anchored in Chi & Wylie's ICAP framework:

| | | example |
|---|---|---|
| L0 | SOLVE | "napíš mi kód na binárne vyhľadávanie" |
| L1 | VERIFY | "je to správne?" |
| L2 | EXPLAIN | "prečo je to O(log n)?" |
| L3 | ELABORATE | "kedy je lineárne lepšie ako binárne?" |
| L4 | SELF-EXPLAIN | "myslím si X, kde robím chybu?" |

PEQI = weighted mean ∈ [0,1], computed automatically from prompts your tool captures.
That converts Gerlich's *self-reported* offloading into an *observed* measure — and it's
the thing your MITM proxy was always for.

**Second metric that matters: calibration.** After every test item the student rates
confidence 0–100. Bias = confidence − actual. This operationalises "illusion of
understanding" and lets the thesis formally test the Deslauriers dissociation:
*students will like best the lesson they remember least.* If that holds, student
satisfaction surveys — what schools actually use — are systematically misleading.

**Subject choice:** informatics, algorithmics. Three structurally isomorphic topics
("naive vs. efficient, why, and when each wins"): T1 search (linear vs binary),
T2 sorting (insertion vs merge), T3 recursion + memoisation. Isomorphic structure is
what makes parallel test forms possible.

**The cleanest methodological move:** conditions G and A use **the same model, same
exercises, same interface, same teacher**. Only the pedagogical layer differs. So any
G-vs-A difference is evidence about *scaffolding*, not model quality. Slijepcevic &
Yaylali compared Khanmigo vs Google — which changes model, UI, content and pedagogy at
once, so their null result is uninterpretable. Yours won't be.

---

## 2. What is new in the repo

### `mastersLaTeX/` — the thesis (127 pages, builds clean)

| File | State |
|---|---|
| `content/1-technical-abstract.tex` | **rewritten** — was your DP1 note |
| `content/2-lay-summary.tex` | **rewritten** — was template text |
| `content/3-introduction.tex` | **rewritten** — was 2 paragraphs |
| `content/4-state-of-the-art.tex` | **extended** — +2 key studies (Bastani, Deslauriers), extended comparison table, and a new closing part: the unifying hypothesis, 4 research questions, 8 pre-registered hypotheses |
| `content/5-metodika.tex` | **NEW, 5 200 words** — the full design |
| `content/6-vysledky.tex` | **NEW, 2 400 words** — the analysis plan run on simulated data |
| `content/7-problem-statement-and-solution.tex` | **written** — was pure template instructions. This is the *graded* conceptual part: problem, tech lit review, solution, risk register, reproducibility, sustainability, employability, teamwork/inclusion |
| `content/8-conclusion.tex` | **rewritten** |
| `content/resume.tex` | **written** — English 10 % summary |
| `appendices/A-instrumenty.tex` | **NEW** — every instrument in full: 20-item pre-test, full 16-item IPT + 12-item DRT for T1 with answer keys, 6 transfer items, Leppink cognitive-load scale in Slovak, JOL/FOL/satisfaction/AI-attitude questionnaires, the **complete system prompt** for the adaptive tutor, 12-item fidelity checklist |
| `appendices/B-kodovaci-manual.tex` | **NEW** — PEQI coding manual: decision procedure, 13 binding boundary rules, anchor examples, IRR protocol with fallback thresholds, classifier spec + confusion matrix |
| `appendices/C-sap.tex` | **NEW** — statistical analysis plan, decision rules, **pre-written conclusion wordings for every outcome** (including "underpowered"), code listings, data-management plan |
| `appendices/D-lekcie.tex` | **NEW** — binding lesson scripts, all 9 topic×condition combinations |
| `appendices/E-etika.tex` | **NEW** — parent consent form, student assent form (both ready to print), full DPIA table, EU AI Act assessment, approval timeline, incident procedures |
| `appendices/plan.tex` | **written** — was 100 % commented out |
| `appendices/abbreviation.tex` | **replaced** — was template ML acronyms |
| `preamble/annotation.tex` | **written** — was `\lipsum` |
| `bib/references.bib` | **26 → 74 entries** |

Metadata fixed in `preamble/preamble.tex`: English title was literally
"My Thesis title"; dates were inconsistent (May 2027 EN vs Máj 2026 SK). **I set both
to May 2027 — verify this is your real defence date.** Evidence number still
`FIIT-XXXX-XXXXX`, marked TODO.

### `mastersLaTeX/analysis/` — NEW, 1 757 lines of Python

| File | What |
|---|---|
| `dgp.py` | Generating model encoding H1–H8 with parameters anchored in published effect sizes. Simulates at item level via Rasch. |
| `power.py` | Monte-Carlo power, 3 000 reps/cell |
| `pipeline.py` | The frozen analysis plan, end to end |
| `peqi.py` | Taxonomy, 90-prompt Slovak anchor corpus, classifier, IRR |
| `figures.py` | All 7 thesis figures |

**Every number in Chapters 5–6 comes out of this code. Nothing is typed by hand.**
Seeds fixed → bit-for-bit reproducible.

### `ai-prompt-monitor/` — the artefact, both layers

#### `mitm/` — NEW: the replacement capture layer

Your DP1 finding was that LittleProxy (2019) can't do HTTP/2 or WebSocket. I built the
mitmproxy replacement the thesis describes:

- `capture_addon.py` (307 lines) — allow-list matching, **per-provider prompt
  extraction** (OpenAI / Anthropic / Google / your own client), pseudonymisation,
  JSONL append. Responses stored as digest + 8-gram shingles only, never verbatim.
- `scrub.py` (156 lines) — PII removal: email, Slovak birth number, phone, IBAN,
  tokens, URLs, long digit runs, **plus roster-based name removal that handles Slovak
  case endings** ("Zuzana" → catches "Zuzane", "Zuzanou").
- `test_capture.py` — **29 tests, all passing**, run without mitmproxy installed.
- `config/study.yaml` — allow-list, and an explicit `not_captured` list documenting
  what is deliberately excluded (autocomplete = keystroke-level data the consent
  doesn't cover).

#### `src/main/java/.../peqi/` — NEW: the analysis layer

The thesis says the Java side tails the JSONL and computes PEQI. That code didn't
exist, so I wrote it:

- `PromptLevel.java` — the taxonomy as an enum, with ICAP band and weight
- `PromptClassifier.java` — the coding manual's decision procedure as code, diacritics
  folded so "prečo" and "preco" behave identically
- `PromptRecord.java` — the JSONL line; tolerates unknown fields so a capture-layer
  change can't stop the analysis mid-study
- `PeqiSummary.java` / `PeqiCalculator.java` — grouping, index, offload rate,
  time-to-first-prompt, median inter-prompt gap, CSV export
- `commands/PeqiCommand.java` — new `peqi` subcommand, registered in `Main`

```
java -jar target/ai-prompt-monitor.jar peqi --dir captures --out analytic.csv
java -jar target/ai-prompt-monitor.jar peqi --explain "myslím si že je to O(n), kde robím chybu?"
```

The second form prints which rules fired — you need that to defend a single coding
decision to a supervisor or an ethics board.

**41 JUnit tests, all passing** (`mvn test`). I added junit-jupiter + surefire to the
POM, which had no test wiring at all. The anchor corpus from Appendix B is encoded as
a parameterised test, so the manual and the code cannot silently diverge.

**End-to-end smoke test run:** 138 synthetic prompts → 12 pupil-sessions →
PEQI 0.202 (offload 0.82) for G vs 0.644 (offload 0.11) for A. The chain works.

### Bugs the tests caught

Four, all in code that would have run unattended in a classroom:

1. Phone pattern never matched `+421 903 123 456` — the most common Slovak format.
2. Roster name matching missed every declined form ("Zuzana" didn't catch "Zuzane").
3. **`lebo` ("because") matched inside `alebo` ("or")** — this promoted plain
   verification requests to the top of the taxonomy, which would have *deflated* the
   reported offloading rate. That is the exact quantity the main hypothesis turns on.
4. Rasch estimation returned all-NaN when any pupil missed the delayed test entirely.

Also removed `public static String MY_VARIABLE = "I AM BLACK";` from `Main.java` —
stray debug left in the entry point of the graded artefact.

---

## 3. Real numbers the simulation produced

**Power (this is the actionable result).** The binding constraint is *not* the number
of students — in a crossover the class and student intercepts cancel in the
within-student difference. It's **treatment-effect heterogeneity across classes**:

| classes | students | analysed | A>K | A>G | G≡K (TOST) | family (Holm) |
|---|---|---|---|---|---|---|
| 12 | 264 | 232 | 0,80 | 0,92 | **0,73** | 0,55 |
| 15 | 330 | 290 | 0,93 | 0,97 | 0,86 | 0,78 |
| **18** | **396** | **348** | **0,95** | **0,99** | **0,92** | **0,87** |

→ **Target 18 classes.** At 12 the equivalence claim — the most important one —
fails. Counter-intuitive corollary: for a fixed number of students, **more small
classes beat fewer large ones**.

**Three design defects the simulation caught before collection:**

1. **Rank-deficient carry-over coding** — a separate "no carry-over" level for period 1
   is collinear with the period-1 indicator. The model returned infinite standard
   errors. Would have been discovered with real data in hand and nothing to do about it.
2. **Delayed test too short** — 8 items/topic gave reliability 0.63. Raised to 12 → 0.68.
3. **Sample size set by the wrong test** — see above.

**PEQI classifier:** rule alone κ = 0.84; logistic regression 5-fold CV κ = **0.92**;
98.8 % of errors are a single adjacent level. Simulated human double-coding gives
Krippendorff α = 0.87 — i.e. the classifier agrees with humans *better than humans
agree with each other*.

---

## 4. Things I decided that you should check

1. **Defence date May 2027** — I made SK and EN consistent at 2027. Change both in
   `preamble/preamble.tex` if wrong.
2. **The "AI Detektív" game from `podklady/` is not in the design.** I wrote up *why*
   (§5.3 of the methodology): it measures in-game behaviour whose relation to school
   learning would need separate validation, and it would eat the lesson time the
   delayed test needs. I kept it as a proposed **independent criterion for validating
   PEQI** in follow-up work — so your supervisor's meeting input is acknowledged and
   given a role, not dropped.
3. **The conceptual part has a 15-page limit** for submission. Chapters 5–7 currently
   run longer. The appendices already carry the detail; trimming is a mechanical cut,
   but it's your call what goes.
4. **`D:\MastersFIIT` is still not a git repository.** I wrote a root `.gitignore`
   (which correctly excludes captures, keys, rosters and build output) but did not run
   `git init` — that's your call. I'd do it before touching anything else.
5. **Stale files I moved, not deleted**, into `mastersLaTeX/.attic/`: the Mac
   `main.bbl` and six `.aux` files that were shadowing the fresh build outputs and
   silently breaking every citation. Delete them when you're satisfied.

---

## 5. Toolchain — now installed

`ai-doc/toolsToInstall.txt` described what was missing. I installed it:

- **MiKTeX 25.12** (per-user) — pdflatex, biber, latexmk all on PATH
- **Strawberry Perl** — so `latexmk` works too
- **statsmodels**, **pypdfium2** added to your Python 3.13

Build with `.\build.ps1` (Perl-free: pdflatex ×3 + biber, reports errors, undefined
refs, overfull boxes and page count). `latexmk -pdf -outdir=out main.tex` also works now.

---

## 6. Suggested next moves

1. `git init` + first commit.
2. Read Chapter 5 (methodology) and Chapter 6 (validation) — that's where the thesis
   lives. ~25 pages.
3. Take the power table to your supervisor. **18 classes across 3–4 schools** is the
   ask, and the STU national-competence-centre position is your leverage.
4. Start the ethics committee submission — appendix E is written and ready. It's the
   critical path: 8 weeks before first measurement, and the collection is tied to the
   school term.
5. `pip install -r ai-prompt-monitor/mitm/requirements.txt` and try the addon against
   a real ChatGPT session. That's the one claim in the thesis I couldn't verify for you
   — I wrote and unit-tested the extraction logic, but it has never seen live traffic.
