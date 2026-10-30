"""metrics.py -- the process measures of chapter 5, computed from the event log.

What it computes, per pupil and lesson
--------------------------------------
Chapter 5 of the thesis lists what the tool must measure about the lesson
itself (the outcomes -- knowledge before, immediately after and three weeks
after, and transfer -- come from the test runner in `assessment/`):

  how the pupil works with the tool
    * did they try first            abhr, own-draft-before-help rate
    * did they just copy the answer copy/paste from the assistant panel,
                                    textual overlap of the answer with the
                                    assistant's replies (computed in memory at
                                    attempt time; the replies themselves are
                                    never stored, as the consent promises)
    * what they ask                 PEQI, offload rate, level counts
    * time to first prompt          t_first_prompt_median_s
    * number of clicks              clicks, keystrokes
    * first ideas when answering    size and latency of the pupil's own draft
                                    at their first move on each task
  self-estimation                   confidence per attempt; where a task can be
                                    checked mechanically, confidence against
                                    that check (calibration bias)
  engagement with the material      active-time ratio, focus ratio, participation
                                    and accuracy in the interactive activities,
                                    and a declared composite index

When it may be run
------------------
AFTER collection. Appendix E forbids looking at outcome-related data while the
study is running, because interim looks with a possibility of stopping inflate
the type-I error. The live dashboard therefore shows only technical counts; this
module is what the researcher runs on the collected logs.

    python metrics.py data/events_*.jsonl --out metrics.csv --json summary.json

Standard library only, like everything that ships to a school.
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import sys
from pathlib import Path

import events as ev
import peqi_live

# --- declared thresholds ---------------------------------------------------
OWN_DRAFT_CHARS = 15        # a draft this long is a start, not a stray keystroke
COPIED_OVERLAP = 0.60       # share of the answer's phrases found in the replies

ENGAGEMENT_COMPONENTS = ("active_ratio", "focus_ratio", "activity_participation")


def load(paths: list[str]) -> tuple[list[dict], int]:
    out, bad = [], 0
    for p in paths:
        for line in Path(p).read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                bad += 1
    return out, bad


def _median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    n = len(xs)
    return round(xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2, 3)


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 4) if xs else None


def _share(flags):
    flags = [bool(f) for f in flags if f is not None]
    return round(sum(flags) / len(flags), 4) if flags else None


# ===========================================================================
def pupil_metrics(evs: list[dict]) -> dict:
    """All process measures for one pupil in one lesson."""
    evs = sorted(evs, key=lambda e: ev._ts(e["timestamp"]))
    by = {}
    for e in evs:
        by.setdefault(e["kind"], []).append(e)
    get = lambda k: by.get(k, [])            # noqa: E731

    base = ev.derive_process_measures(evs)
    m: dict = dict(base)

    # --- reading/thinking time before the first own keystroke, per episode
    shown_at: dict[str, str] = {}
    key_gaps = []
    for e in evs:
        if e["kind"] == ev.TASK_SHOWN:
            shown_at[e.get("taskId")] = e["timestamp"]
        elif e["kind"] == ev.FIRST_KEYSTROKE and e.get("taskId") in shown_at:
            g = ev._seconds(shown_at.pop(e["taskId"]), e["timestamp"])
            if g >= 0:
                key_gaps.append(g)
    m["t_first_keystroke_median_s"] = _median(key_gaps)

    # --- progress
    m["n_completed"] = len({e.get("taskId") for e in get(ev.TASK_COMPLETED)})
    m["n_skipped"] = len({e.get("taskId") for e in get(ev.TASK_SKIPPED)})
    att = get(ev.ATTEMPT)
    m["n_attempts"] = len(att)

    # --- first ideas
    fi = get(ev.FIRST_IDEA)
    m["first_idea_n"] = len(fi)
    m["first_idea_chars_median"] = _median([e.get("draftChars") for e in fi])
    m["first_idea_latency_median_s"] = _median(
        [e["msSinceShown"] / 1000 for e in fi if isinstance(e.get("msSinceShown"), (int, float))])
    asked_first = [e for e in fi if e.get("trigger") == "prompt"]
    m["help_with_own_draft_rate"] = _share(
        [(e.get("draftChars") or 0) >= OWN_DRAFT_CHARS for e in asked_first])
    m["attempt_first_rate"] = _share([e.get("trigger") == "attempt" for e in fi])

    # --- prompts and their quality
    pr = get(ev.PROMPT_SENT)
    levels = [e.get("peqiLevel") or peqi_live.classify(e.get("promptText", ""))
              for e in pr]
    idx = peqi_live.session_index(levels)
    m["n_prompts"] = idx["n_prompts"]
    m["peqi"] = idx["peqi"]
    m["offload_rate"] = idx["offload_rate"]
    m["generative_rate"] = idx["generative_rate"]
    m["off_task_rate"] = idx["off_task_rate"]
    for lv in peqi_live.LEVELS:
        m[f"n_{lv}"] = idx["counts"][lv]
    m["prompt_chars_median"] = _median([e.get("promptChars") for e in pr])

    # --- the assistant's side (features only; the text is never stored)
    rep = get(ev.ASSISTANT_REPLY)
    feats = [e.get("replyFeatures") or {} for e in rep]
    m["n_replies"] = len(rep)
    m["reply_solution_exposure"] = _share(
        [f.get("finalAnswer") or f.get("codeBlock") or f.get("containsReference")
         for f in feats]) if feats else None
    m["reply_question_rate"] = _share([f.get("question") for f in feats]) if feats else None

    # --- copying
    cp = get(ev.COPY)
    ps = get(ev.PASTE)
    m["copy_from_assistant"] = sum(1 for e in cp if e.get("source") == "assistant")
    m["paste_into_answer"] = sum(1 for e in ps if e.get("target") == "answer")
    m["paste_from_assistant"] = sum(1 for e in ps if e.get("fromAssistant"))
    m["paste_from_assistant_chars"] = sum(e.get("chars", 0) for e in ps
                                          if e.get("fromAssistant"))
    ov = [e.get("assistantOverlap") for e in att if e.get("assistantOverlap") is not None]
    m["answer_assistant_overlap_mean"] = _mean(ov)
    m["copied_answer_rate"] = _share(
        [(e.get("assistantOverlap") or 0) >= COPIED_OVERLAP or bool(e.get("pastedFromAssistant"))
         for e in att if e.get("assistantOverlap") is not None or e.get("pastedFromAssistant")]
    ) if att else None

    # --- self-estimation during the lesson
    m["self_correct_rate"] = _share([e.get("correct") for e in att])
    conf = [e.get("confidence") for e in att if isinstance(e.get("confidence"), (int, float))]
    m["confidence_mean"] = _mean(conf)
    auto = [e for e in att if e.get("autoCorrect") is not None]
    m["n_auto_checked"] = len(auto)
    m["auto_correct_rate"] = _share([e["autoCorrect"] for e in auto])
    paired = [(e["confidence"] / 100.0, 1.0 if e["autoCorrect"] else 0.0) for e in auto
              if isinstance(e.get("confidence"), (int, float))]
    m["lesson_calibration_bias"] = round(
        sum(c - a for c, a in paired) / len(paired), 4) if paired else None
    m["lesson_brier"] = round(
        sum((c - a) ** 2 for c, a in paired) / len(paired), 4) if paired else None
    m["self_auto_agreement"] = _share([bool(e.get("correct")) == bool(e["autoCorrect"])
                                       for e in auto])

    # --- interaction counters
    it = get(ev.INTERACTION)
    tot = lambda k: sum(int(e.get(k) or 0) for e in it)   # noqa: E731
    m["clicks"] = tot("clicks")
    m["keystrokes"] = tot("keys")
    m["focus_losses"] = tot("focusLoss")
    hidden, active, idle = tot("hiddenMs"), tot("activeMs"), tot("idleMs")
    present = hidden + active + idle
    m["present_s"] = round(present / 1000, 1)
    m["active_s"] = round(active / 1000, 1)
    m["hidden_s"] = round(hidden / 1000, 1)
    m["active_ratio"] = round(active / present, 4) if present else None
    m["focus_ratio"] = round(1 - hidden / present, 4) if present else None

    # --- interactive activities
    seen = {(e.get("activityId"), e.get("version")) for e in get(ev.ACTIVITY_VIEW)}
    resp = {}
    for e in get(ev.ACTIVITY_RESPONSE):          # the last answer counts
        resp[(e.get("activityId"), e.get("version"))] = e
    m["activities_seen"] = len(seen)
    m["activities_answered"] = len(resp)
    m["activity_participation"] = round(len(set(resp) & seen) / len(seen), 4) \
        if seen else None
    m["activity_correct_share"] = _share([e.get("correct") for e in resp.values()])
    m["activity_confidence_mean"] = _mean([e.get("confidence") for e in resp.values()])
    m["activity_latency_median_s"] = _median(
        [e["latencyMs"] / 1000 for e in resp.values()
         if isinstance(e.get("latencyMs"), (int, float))])
    eng = get(ev.ACTIVITY_ENGAGEMENT)
    m["activity_steps"] = sum(int(e.get("steps") or 0) for e in eng)

    # --- composite engagement: the mean of the components that exist. Declared
    # here, before any data, and exported with its components so the analysis
    # can use them separately if the composite does not hold together.
    comps = [m[c] for c in ENGAGEMENT_COMPONENTS if m.get(c) is not None]
    m["engagement_index"] = round(sum(comps) / len(comps), 4) if comps else None

    # --- the pedagogical layer (condition A) and protocol deviations
    m["guard_violations"] = len(get(ev.GUARD_VIOLATION))
    se = get(ev.SELF_EXPLANATION)
    m["self_explanations"] = len(se)
    m["self_explanations_accepted"] = sum(1 for e in se if e.get("accepted"))
    m["solutions_requested"] = len(get(ev.SOLUTION_REQUESTED))
    m["solutions_unlocked"] = len(get(ev.SOLUTION_UNLOCKED))
    m["devices"] = len({e.get("device") for e in get(ev.LOGIN) if e.get("device")})
    return m


# ===========================================================================
def compute(events: list[dict]) -> list[dict]:
    """One row per pupil and lesson session. Class-level events are skipped."""
    groups: dict[tuple, list[dict]] = {}
    for e in events:
        p = e.get("pseudonym")
        if not p or p in (ev.CLASS, "unset"):
            continue
        groups.setdefault((e.get("session"), e.get("condition"),
                           e.get("period"), p), []).append(e)
    rows = []
    for (session, cond, period, p), evs in sorted(groups.items(), key=lambda kv: str(kv[0])):
        row = dict(session=session, condition=cond, period=period, pseudonym=p)
        row.update(pupil_metrics(evs))
        rows.append(row)
    return rows


SUMMARY_KEYS = ("peqi", "offload_rate", "abhr", "t_first_prompt_median_s",
                "t_first_keystroke_median_s", "help_with_own_draft_rate",
                "copied_answer_rate", "answer_assistant_overlap_mean",
                "confidence_mean", "lesson_calibration_bias", "clicks",
                "active_ratio", "activity_participation", "engagement_index")


def summary(rows: list[dict]) -> dict:
    """Means per condition. For the researcher, after collection."""
    out: dict = {}
    for cond in sorted({r["condition"] for r in rows}):
        rs = [r for r in rows if r["condition"] == cond]
        out[cond] = dict(n=len(rs), **{k: _mean([r.get(k) for r in rs])
                                       for k in SUMMARY_KEYS})
    return out


def write_csv(rows: list[dict], path: str | Path) -> None:
    cols: list[str] = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in cols})


def main(argv: list[str]) -> int:
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("logs", nargs="+", help="events_*.jsonl (globs allowed)")
    ap.add_argument("--out", default="metrics.csv")
    ap.add_argument("--json", default="")
    a = ap.parse_args(argv)
    paths = sorted({p for pat in a.logs for p in (glob.glob(pat) or [pat])})
    events, bad = load(paths)
    rows = compute(events)
    write_csv(rows, a.out)
    s = dict(files=len(paths), events=len(events), malformed_lines=bad,
             pupils=len(rows), by_condition=summary(rows))
    if a.json:
        Path(a.json).write_text(json.dumps(s, indent=2, ensure_ascii=False),
                                encoding="utf-8")
    print(json.dumps(s, indent=2, ensure_ascii=False))
    print(f"\n{len(rows)} riadkov -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
