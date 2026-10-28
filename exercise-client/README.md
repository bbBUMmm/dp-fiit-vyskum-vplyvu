# Exercise client — the experimental manipulation

One codebase serves all three conditions. That is not a convenience, it is the
control: if the control condition ran on different software, any difference
between conditions would confound pedagogy with everything else the software
does, and the design's central claim would be untestable.

| | assistant | system prompt | knowledge tracing | self-explanation gate |
|---|---|---|---|---|
| **K** control | refused *at the server* | — | — | — |
| **G** generic | yes | **none** | no | no |
| **A** adaptive | yes | full | yes | yes |

Conditions G and A differ in exactly two lines of `server._ask`: which message
list is built, and whether the reply passes the output guard. Everything
else — tasks, layout, timing, event log — is shared and identical. A test
asserts this by comparing what each condition actually sends to the model.

## Run

```bash
python server.py --condition A --session 2026-10-07-2A-P1 --salt <school salt>
# then open http://127.0.0.1:5173/
```

Standard library only — no packages to install on a locked-down school laptop.
The default provider is a deterministic stub, so a whole lesson can be
rehearsed with no internet, no API key and no cost. For live use:

```bash
STUDY_PROVIDER=openai STUDY_MODEL=gpt-4o-mini STUDY_API_KEY=... \
STUDY_BASE_URL=https://...   # an EU endpoint, as the DPIA requires
```

The server **refuses to start without a salt**. It is held by the school, so
the researcher cannot reverse a pseudonym back to a pupil.

## Files

| File | What it is |
|---|---|
| `pedagogy.py` | The manipulation itself: system prompt, BKT, sequencing, hint ladder, self-explanation gate, output guard. |
| `providers.py` | One model behind one interface, so both AI conditions provably use the same one. Stub / echo / OpenAI-compatible. |
| `events.py` | The event stream the network cannot see, in the same JSON Lines format the capture layer writes and the Java layer reads. |
| `server.py` | Three conditions, one codebase. |
| `static/` | The pupil-facing client. Deliberately plain. |
| `tasks/t1_search.json` | Lesson T1 with skills, scaffolds and harder variants. |
| `test_pedagogy.py` | 67 unit tests, including the 40-prompt deployment gate. |
| `test_server.py` | 35 end-to-end tests against the real server in all three conditions. |

## The three mechanisms of condition A

**System prompt.** Forbids a finished solution, requires a diagnostic question
first, releases help in four graded steps. Full text in Appendix A of the
thesis.

**Knowledge tracing.** Four-parameter BKT per sub-skill. Mastery drives both
which exercise comes next (skip what is mastered, insert a smaller step where
the pupil is stuck) and which rung of the hint ladder the assistant may start
from. This is what makes the condition adaptive in the strict sense: it adapts
the *sequence*, not merely the wording.

A rule worth stating because it was got wrong first: the sequencing rules fire
only **after evidence**. The BKT prior (0.25) sits below the struggling
threshold (0.40) by construction, so without that guard every pupil would be
classified as struggling before answering anything and handed a scaffold on the
first exercise. Adapting means adapting to evidence, not to a prior.

**Self-explanation gate.** The worked solution does not unlock until the pupil
has written, in their own words, why their approach is right or where they
think it went wrong. The gate is permissive about *correctness* and strict
about *effort* — rejecting a wrong explanation would turn it into a second
assessment and teach pupils to guess what the system wants, when the point is
that they articulate something at all.

## Why the output guard exists

A system prompt is a request, not a constraint. Models comply with it most of
the time, and "most of the time" is not good enough when the difference between
two experimental conditions depends on it. So every reply in condition A is
also checked mechanically for code blocks, full function definitions,
answer-announcing phrases and the reference answer itself. A violation is
replaced with a question — and **logged**, because the rate at which the prompt
fails is a number the thesis has to report rather than a detail to hide.

The deployment gate in the thesis says the layer must be tested against 40
adversarial prompts with zero leaks before the study runs. That suite is in
`test_pedagogy.py` and currently passes.

## Tests

```bash
python test_pedagogy.py   # 67 — pedagogy, guard, gate, process measures
python test_server.py     # 35 — all three conditions, end to end
```

Three real defects were found by writing them, all of which would have
corrupted the study silently:

1. **Every pupil was scaffolded before answering anything** — the BKT prior is
   below the struggling threshold, so the sequencing rule fired on the prior.
   Fixed by requiring evidence.
2. **Scaffolds and harder variants leaked into the fixed sequence**, so K and G
   would have seen exercises only A was meant to reach — the conditions would
   have differed in *content* as well as in pedagogy.
3. **Time to first prompt went negative.** A task shown twice overwrote its
   start time while keeping the earlier prompt. Found because the number was
   impossible; a plausible-looking wrong number would have survived. The unit
   is now the *episode* — one showing of one task — not the task.

## Integration

The client writes the same JSON Lines the mitmproxy capture layer writes, so the
Java analysis layer reads either without knowing which produced it. Verified end
to end: 10 simulated pupils → 654 events → `ai-prompt-monitor peqi` → PEQI 0.56,
0 malformed lines.

```
exercise-client  ─┐
                  ├─→  captures-*.jsonl  ─→  ai-prompt-monitor peqi  ─→  analytic.csv
mitmproxy addon  ─┘
```

Two measures exist **only** here and are invisible in captured traffic: time to
first prompt (the network cannot see that a pupil read the task for ninety
seconds first) and the attempt-before-help ratio (it cannot see that they had
already tried twice). Both are among the study's process outcomes.

## Known limits

- Correctness of an attempt is **self-assessed** by the pupil. Automatic marking
  of free text would be unreliable, and the graded outcome comes from the paper
  test, not from here; what this feeds is the knowledge estimate, for which a
  pupil's own judgement is adequate and cheap. It does mean the BKT estimate
  inherits any systematic optimism — which is itself a measured quantity in this
  study (calibration bias), so it can be checked rather than assumed away.
- BKT parameters are conventional, not fitted. Fitting them needs pilot data,
  and the design depends on the sequence adapting at all, not on the precision
  of the estimate.
- Sessions are held in memory. The log is the record; a restart mid-lesson loses
  the knowledge state but no data.
