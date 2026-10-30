# Exercise client — the experimental manipulation, the classroom server, the interactive part

One codebase serves all three conditions. That is not a convenience, it is the
control: if the control condition ran on different software, any difference
between conditions would confound pedagogy with everything else the software
does, and the design's central claim would be untestable.

| | assistant | system prompt | knowledge tracing | self-explanation gate |
|---|---|---|---|---|
| **K** control | refused *at the server* | — | — | — |
| **G** generic | yes | **none** | no | no |
| **A** adaptive | yes | full | yes | yes (unlocks the worked solution) |

Conditions G and A differ in exactly two places in `server._ask`: which message
list is built, and whether the reply passes the output guard. Everything
else — tasks, layout, timing, event log, interactive activities, interaction
counters — is shared and identical. Tests assert this by comparing what each
condition sends to the model and what each pupil's device receives.

## What it is now (chapter 6 of the thesis)

One machine in the classroom runs `server.py`. Pupils open its address in a
browser on a school PC **or a phone**; every event lands in one log on that
machine. The teacher opens `/teacher` on the same server.

```
pupil PCs / phones ──HTTP──▶ server.py (one laptop) ──▶ data/events_<hodina>.jsonl
teacher (browser)  ──/teacher, PIN──┘        └── model API (G, A only)
```

- **Pupil app** (`/`): code login with check-digit verification, the task, an
  inline self-assessment with a confidence slider (no default value), an honest
  "skip", the assistant panel (G/A), the self-explanation gate that unlocks the
  worked solution (A), and the interactive activity sheet. Works on a 360-px
  phone, in light and dark mode, with no network fonts.
- **Teacher dashboard** (`/teacher`, PIN printed at start-up): join address and
  QR code, connected / finished counts, where in the task sequence the class is
  (anonymous), lesson phase, technical health of the collection, and the
  **interactive part**: an activity library per subject, live launch, live class
  results, reveal, close, and creating a quick question during the lesson.
- **Researcher view**: per-pupil process measures and CSV export, switched off
  unless the server is started with `--researcher-view` — Appendix E forbids
  looking at results during collection.

## Run

```bash
# rehearsal on one computer (stub model, no internet, no key)
python server.py --condition A --session rehearsal --salt test

# a real lesson for the whole class (pupils connect over the school network)
python server.py --condition G --session 2026-10-07-2A-P1 --salt <school salt> \
    --host 0.0.0.0 --school GY --codes ../data/kody-GY.txt --tasks tasks/t1_search.json
```

The school kit's `RUN.cmd` asks for all of this. Standard library only — no
packages to install on a locked-down school laptop. For a live model:

```bash
STUDY_PROVIDER=openai STUDY_MODEL=gpt-4o-mini STUDY_API_KEY=... \
STUDY_BASE_URL=https://...   # an EU endpoint, as the DPIA requires
```

| option | meaning |
|---|---|
| `--condition K\|G\|A` | required |
| `--salt` | required; held by the school. The server refuses to start without it |
| `--tasks` | lesson file: `t1_search.json` (informatics), `m1_interest.json`, `f1_circuits.json` (drafts) |
| `--host 0.0.0.0` | serve the whole class; default `127.0.0.1` = this computer only |
| `--school GY --codes file` | enforce the check digit and the class list at login |
| `--consent-list file` | codes with BOTH signed paper consents; any other code is never recorded |
| `--teacher-pin` | otherwise a random 6-digit PIN is printed |
| `--log-answer-text` | also store the TEXT of answers and drafts (only if the consent covers it) |
| `--researcher-view` | enable the metrics tab; not during collection |

A restart loses nothing: the server rebuilds every pupil's state (completed
tasks, knowledge state, unlocked solutions, activities created during the
lesson) from the log, and pupils log in again with the same code. A session id
can never be reused for a different condition.

## Consent on screen

After the code, the pupil sees the consent screen (`static/consent.js`; the
words and rules are in `../assessment/consent.py`, shared with the test runner).
Until the answer is yes, **nothing about the pupil is written** — the log's gate
(`EventLog.allow`) drops their events, the login included. A pupil who says no
works exactly like everyone else, and the dashboard never shows the choice. The
**Súhlas** button in the top bar lets the pupil agree later or withdraw; a
withdrawal deletes everything this lesson recorded about them at once
(`EventLog.purge`) and leaves a `consent_withdrawn` marker. Every yes is logged
with the version (hash) of the exact text on the screen. With `--consent-list`,
codes without a signed paper consent are never recorded and their pupils are
told so. A restart forgets a "no" (it was never written): the pupil is asked again.

| endpoint | |
|---|---|
| `POST /api/login` | also returns `consent: {state, version, text}`; state `pending`, `yes`, `no` or `none` (no paper consent) |
| `POST /api/consent` | `{"choice": "yes" \| "no"}` changes it, `{}` reads it; a withdrawal returns `purged` |

## Interactive activities

Activities live in `activities/<pack>.json` — one pack per subject plus a
general one — and are validated at start-up (`activities.validate`). The teacher
can also create a quick question, a numeric prediction or a reflection during
the lesson, or paste a JSON definition.

| type | what the pupil does | scored by |
|---|---|---|
| `poll` | picks an option (+ optional confidence 0–100) | `key` |
| `predict` | predicts (choice or number), then *observes* a widget, then explains | `answer` (+ `tolerance`) |
| `order` | puts steps in order (drag or ↑/↓, works on touch) | position match |
| `animation` | steps through a widget, predicting at checkpoints | widget result |
| `handson` | experiments with a simulation, reports a result | widget result |
| `reflect` | exit ticket / muddiest point (+ "how well do you understand") | — |

Widgets: `binary-search` (also `mode: linear`; `predict: true` asks the pupil to
click the next compared element; `allowUnsorted` for the counter-example),
`search-race`, `guess-number`, `interest`, `circuit` (series/parallel, bulbs can
be "unscrewed"), `frames` (any animation as a sequence of text/SVG frames).

```json
{"id": "INF-ANIM-16", "type": "animation", "phase": "vyklad",
 "title": "Binárne vyhľadávanie na poli 16 prvkov",
 "widget": "binary-search",
 "params": {"array": [3, 7, 11, 14, 19, 23, 27, 31, 38, 42, 47, 53, 58, 64, 71, 79],
            "target": 58, "predict": true}}
```

The key, the answer and the explanation are not sent to pupils until the teacher
reveals the result; a `note` is shown only on the dashboard. The informatics pack
uses arrays and numbers that differ from every test item, and a test asserts it.

## What it measures (chapter 5 of the thesis)

`metrics.py` computes these per pupil and lesson from the log, after collection:

| measure | fields |
|---|---|
| did the pupil try first | `abhr`, `attempt_first_rate` |
| first ideas when answering | `first_idea_chars_median`, `first_idea_latency_median_s`, `help_with_own_draft_rate` |
| what they ask | `peqi`, `offload_rate`, `generative_rate`, `n_L0`…`n_L4`, `n_X` |
| time to first prompt / keystroke | `t_first_prompt_median_s`, `t_first_keystroke_median_s` |
| did they just copy the answer | `copy_from_assistant`, `paste_from_assistant`, `answer_assistant_overlap_mean`, `copied_answer_rate` |
| number of clicks | `clicks`, `keystrokes`, `focus_losses` |
| self-estimation | `confidence_mean`, `lesson_calibration_bias`, `lesson_brier`, `self_auto_agreement` |
| engagement | `active_ratio`, `focus_ratio`, `activity_participation`, `activity_correct_share`, `engagement_index` |
| what the tool handed over | `reply_solution_exposure`, `reply_question_rate`, `guard_violations` |

```bash
python metrics.py ../data/events_*.jsonl --out metrics.csv --json summary.json
```

The PEQI label is attached to each `prompt` event when it is sent
(`peqi_live.py`), a port of `analysis/peqi.py::rule_classify` held to the same
pinned corpus as the Java implementation. The assistant's replies are never
stored — only their features (did it ask a question, give a final answer, show
code) — and the overlap between an answer and the replies is computed in memory.
Answer and draft texts are stored only with `--log-answer-text`.

Knowledge before, immediately after and three weeks after the lesson, transfer,
and per-item confidence come from the test runner in `../assessment/`.

## Files

| File | What it is |
|---|---|
| `server.py` | Classroom server: three conditions, pupil API, teacher API, recovery from the log. |
| `pedagogy.py` | The manipulation: system prompt, BKT, sequencing, hint ladder, self-explanation gate, output guard, mechanical answer checks, reply features. |
| `providers.py` | One model behind one interface. Stub / echo / OpenAI-compatible. |
| `events.py` | The event log (JSON Lines, fsync per line) and the canonical pseudonym. |
| `activities.py` | The interactive part: activity validation, live state, aggregation. |
| `peqi_live.py` | The PEQI coding rule, applied as prompts are sent. |
| `metrics.py` | Chapter-5 process measures from the log; CLI and researcher view. |
| `qr.py` | QR code for the join address (standard library). |
| `static/` | Pupil app (`index.html`, `app.js`), teacher dashboard (`teacher.html`, `teacher.js`), widgets (`widgets.js`), shared design (`style.css`). |
| `tasks/` | Lessons: T1 informatics; M1 mathematics and F1 physics are drafts to check with the teachers. |
| `activities/` | Activity packs: informatika, matematika, fyzika, vseobecne. |
| `test_pedagogy.py` | Pedagogy, guard, gate, the 40-prompt deployment gate, regressions. |
| `test_features.py` | Activities, metrics, PEQI pinning, QR. |
| `test_server.py` | End to end in all three conditions, activities, recovery, keep-alive, codes. |

## Tests

```bash
python test_pedagogy.py
python test_features.py
python test_server.py
```

Defects found by writing them, all of which would have corrupted the study
silently:

1. **Every pupil was scaffolded before answering anything** — the BKT prior is
   below the struggling threshold. Fixed by requiring evidence.
2. **Scaffolds and harder variants leaked into the fixed sequence.**
3. **Time to first prompt went negative.** The unit is now the episode.
4. **A mastered pupil looped on a completed harder variant forever.**
5. **One pupil, several pseudonyms.** The code was hashed as typed, so
   `gy-k7m4p-q` and `GY-K7M4P-Q` were two pupils — and the test runner logged the
   raw code, so lesson and test could not be joined at all.
6. **Condition A without its pedagogy.** A prompt with an unknown task id fell
   through to the generic message list; the hint level came from the browser.
7. **The research log accepted any event kind the browser sent.**
8. **The self-explanation gate unlocked nothing**, and its advice contained
   LaTeX markup (`~---`) that pupils saw verbatim.
9. **A browser's reused connection broke the test runner**: `/api/item` left its
   body unread, and the next request (the answer) was refused with a 501.

## Technology

Python 3.11+ standard library only (`http.server`, `json`, `hashlib`,
`threading`, `urllib`); plain HTML, CSS and JavaScript in the browser, no
framework and no build step; JSON Lines on disk; any OpenAI-compatible chat API
for the model. Runs on Windows (launchers are `.cmd` files) and is used from any
modern browser, including phones.

## Known limits

- Correctness of an attempt is self-assessed by the pupil, as designed; the
  mechanical check (`autoCorrect`) exists only to measure calibration and is
  never shown or used for sequencing.
- BKT parameters are conventional, not fitted.
- Serving the whole class needs the Windows firewall to allow Python on the
  private network, and phones on the same network as the teacher's laptop.
- The consent text (Appendix E) says nothing is recorded from pupils' phones;
  using pupils' own phones needs that text changed first.
