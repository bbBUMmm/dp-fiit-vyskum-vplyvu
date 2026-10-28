"""events.py -- the event stream the analysis needs and the network cannot see.

Time to first prompt and the attempt-before-help ratio are two of the study's
process measures, and neither is visible in captured traffic: the network sees
that a prompt was sent, not that the pupil had already spent ninety seconds
reading the task and made two attempts. Those facts exist only in the client.

So the client emits them, into the same JSON Lines format the capture layer
uses and the Java analysis layer reads. One format, two producers, one consumer.

Nothing here carries a name. The pseudonym is the school-issued code hashed
with a salt the school holds; the researcher cannot reverse it. Free text
written by the pupil is emitted only for the fields the consent covers -- the
prompt, and the self-explanation -- and never for anything else.
"""
from __future__ import annotations

import hashlib
import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

_LOCK = threading.Lock()


class EventLog:
    """Append-only JSON Lines, one line per event, flushed on every write.

    Flushing every time is deliberate. A lesson ends when a teenager closes a
    laptop lid, and a buffered final line is a lost pupil-session.
    """

    def __init__(self, path: str | Path, salt: str = "",
                 session: str = "unset", condition: str = "unset",
                 period: int = 0):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.salt = salt
        self.session = session
        self.condition = condition
        self.period = period
        self.counts: dict[str, int] = {}

    def pseudonym(self, student_code: str) -> str:
        if not self.salt:
            raise RuntimeError(
                "the pseudonym salt is not set; it is held by the school and "
                "capture must not start without it")
        h = hashlib.sha256((self.salt + "|" + student_code).encode("utf-8"))
        return h.hexdigest()[:16]

    def emit(self, kind: str, pseudonym: str, **fields) -> dict:
        rec = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "eventId": str(uuid.uuid4()),
            "kind": kind,
            "session": self.session,
            "pseudonym": pseudonym,
            "condition": self.condition,
            "period": self.period,
            **fields,
        }
        line = json.dumps(rec, ensure_ascii=False)
        with _LOCK:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
                fh.flush()
            self.counts[kind] = self.counts.get(kind, 0) + 1
        return rec


# Event kinds. Kept as constants because the analysis layer keys on them and a
# typo would silently drop a measure rather than raise.
TASK_SHOWN = "task_shown"        # -> start of the clock for T_1
FIRST_KEYSTROKE = "first_keystroke"
ATTEMPT = "attempt"              # -> the A in ABHR
PROMPT_SENT = "prompt"           # same shape as the capture layer's record
ASSISTANT_REPLY = "assistant_reply"
GUARD_VIOLATION = "guard_violation"
SELF_EXPLANATION = "self_explanation"
SOLUTION_UNLOCKED = "solution_unlocked"
ADAPTIVE_DECISION = "adaptive_decision"
TASK_COMPLETED = "task_completed"
PROVIDER_ERROR = "provider_error"


def derive_process_measures(events: list[dict]) -> dict:
    """Compute T_1 and ABHR from one pupil's event stream.

    The unit is the EPISODE -- one showing of one task -- not the task. A pupil
    who is shown an exercise, fails it, and is shown it again has worked on it
    twice, and the second attempt has its own clock.

    Getting this wrong is not academic. Keying on the task alone overwrites the
    start time with the later showing while keeping the earlier prompt, which
    produces a *negative* time to first prompt. That is how the bug was found:
    the measure went negative on a rehearsal run, which a plausible-looking
    positive number never would have.

    ABHR is likewise per-episode: the question "did the pupil try before asking"
    has an answer each time they are put in front of the task.
    """
    ordered = sorted((e for e in events if e.get("taskId")),
                     key=lambda e: e["timestamp"])

    episodes: list[dict] = []
    open_for: dict[str, dict] = {}     # taskId -> the episode currently open
    for e in ordered:
        tid, kind, ts = e["taskId"], e["kind"], e["timestamp"]
        if kind == TASK_SHOWN:
            ep = {"task": tid, "shown": ts, "attempts": [], "prompts": []}
            episodes.append(ep)
            open_for[tid] = ep
        elif kind in (ATTEMPT, PROMPT_SENT):
            ep = open_for.get(tid)
            if ep is None:                # activity before any showing
                ep = {"task": tid, "shown": None, "attempts": [], "prompts": []}
                episodes.append(ep)
                open_for[tid] = ep
            ep["attempts" if kind == ATTEMPT else "prompts"].append(ts)

    gaps, tried_first, with_prompt = [], 0, 0
    for ep in episodes:
        if not ep["prompts"]:
            continue
        with_prompt += 1
        first_prompt = min(ep["prompts"])
        if ep["shown"]:
            gap = _seconds(ep["shown"], first_prompt)
            if gap >= 0:                  # a negative gap is a data fault
                gaps.append(gap)
        if any(a < first_prompt for a in ep["attempts"]):
            tried_first += 1

    return {
        "n_tasks_seen": len({ep["task"] for ep in episodes}),
        "n_episodes": len(episodes),
        "n_episodes_with_prompt": with_prompt,
        "t_first_prompt_median_s": _median(gaps),
        "abhr": round(tried_first / with_prompt, 4) if with_prompt else None,
    }


def _seconds(a: str, b: str) -> float:
    return (datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds()


def _median(xs: list[float]) -> float | None:
    if not xs:
        return None
    s = sorted(xs)
    n = len(s)
    return round(s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2, 2)
