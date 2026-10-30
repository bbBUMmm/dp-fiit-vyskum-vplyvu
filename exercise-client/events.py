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
prompt, and the self-explanation -- and never for anything else, unless the
server is started with --log-answer-text (see server.py).

The code is put into canonical form BEFORE it is hashed. Without that, "gy-k7m4p-q"
and "GYK7M4PQ" are two pupils, and the same child typed both ways on two
occasions loses the change score the study exists to measure. The canonical
form is the one `assessment/linkage.normalise` defines, so a lesson pseudonym
and a test pseudonym of the same pupil are the same string.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

_LOCK = threading.Lock()


def canonical_code(student_code: str) -> str:
    """Strip what a pupil may add: spaces, dashes, lower case.

    Identical to `assessment/linkage.normalise`; `test_server.py` pins the two
    together so that a lesson and a test hash the same pupil to the same value.
    """
    return "".join((student_code or "").split()).replace("-", "") \
        .replace("—", "").upper()


def pseudonymise(salt: str, student_code: str) -> str:
    if not salt:
        raise RuntimeError(
            "the pseudonym salt is not set; it is held by the school and "
            "capture must not start without it")
    h = hashlib.sha256((salt + "|" + canonical_code(student_code)).encode("utf-8"))
    return h.hexdigest()[:16]


class EventLog:
    """Append-only JSON Lines, one line per event, flushed AND synced on every
    write.

    Flushing every time is deliberate. A lesson ends when a teenager closes a
    laptop lid, and a buffered final line is a lost pupil-session. A flush only
    hands the line to the operating system; `fsync` is what puts it on the disk
    of a laptop whose battery is about to run out.
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
        # The consent gate: given a pseudonym, may anything about it be written?
        # None writes everything (the analysis tools and the tests); the lesson
        # server sets it, and a pupil who has not said yes is never on disk.
        self.allow = None

    def pseudonym(self, student_code: str) -> str:
        return pseudonymise(self.salt, student_code)

    def emit(self, kind: str, pseudonym: str, force: bool = False, **fields) -> dict:
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
        if not force and self.allow is not None and pseudonym != CLASS \
                and not self.allow(pseudonym):
            return rec                     # the caller goes on; nothing is written
        line = json.dumps(rec, ensure_ascii=False)
        with _LOCK:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
                fh.flush()
                try:
                    os.fsync(fh.fileno())
                except OSError:            # some network drives refuse; the
                    pass                   # flush above still happened
            self.counts[kind] = self.counts.get(kind, 0) + 1
        return rec

    def read(self) -> list[dict]:
        """Every well-formed event already in the file (for crash recovery)."""
        if not self.path.exists():
            return []
        out = []
        with _LOCK:
            text = self.path.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                continue                   # a torn last line from a power cut
        return out

    def purge(self, pseudonym: str, keep: tuple[str, ...] = ()) -> bool:
        """Delete every event of one pupil in this session, except the kinds in
        `keep` (the withdrawal marker). Used when a pupil withdraws consent.

        Written to a temporary file and swapped in, under the lock `emit` uses,
        so no event is lost in between. False when the swap fails -- on Windows
        another program holding the file open is enough; the marker is then in
        the log, and the same-day data check deletes the rest.
        """
        with _LOCK:
            if not self.path.exists():
                return True
            kept, counts = [], {}
            for line in self.path.read_text(encoding="utf-8", errors="replace").splitlines():
                try:
                    r = json.loads(line)
                except ValueError:
                    kept.append(line)
                    continue
                if (r.get("pseudonym") == pseudonym and r.get("session") == self.session
                        and r.get("kind") not in keep):
                    continue
                kept.append(line)
                if r.get("session") == self.session:
                    counts[r.get("kind")] = counts.get(r.get("kind"), 0) + 1
            tmp = self.path.with_name(self.path.name + ".tmp")
            try:
                with tmp.open("w", encoding="utf-8") as fh:
                    fh.write("".join(x + "\n" for x in kept))
                    fh.flush()
                    os.fsync(fh.fileno())
                os.replace(tmp, self.path)
            except OSError:
                try:
                    tmp.unlink()
                except OSError:
                    pass
                return False
            self.counts = counts
            return True


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

# Added with the interaction metrics of chapter 5 ---------------------------
LOGIN = "login"                  # a device joined with a valid code
LOGOUT = "logout"
TASK_SKIPPED = "task_skipped"    # honest exit from a task, instead of a false "correct"
FIRST_IDEA = "first_idea"        # the pupil's own draft at their first move
COPY = "copy"                    # text copied (e.g. out of the assistant panel)
PASTE = "paste"                  # text pasted (e.g. into the answer box)
INTERACTION = "interaction"      # periodic counters: clicks, keys, focus, activity
SOLUTION_REQUESTED = "solution_requested"
PHASE = "phase"                  # the teacher moved the lesson to another phase
ACTIVITY_DEFINED = "activity_defined"
ACTIVITY_STARTED = "activity_started"
ACTIVITY_REVEALED = "activity_revealed"
ACTIVITY_CLOSED = "activity_closed"
ACTIVITY_VIEW = "activity_view"
ACTIVITY_RESPONSE = "activity_response"
ACTIVITY_ENGAGEMENT = "activity_engagement"
SERVER_START = "server_start"

# Consent on screen (consent.py) -------------------------------------------
CONSENT = "consent"                    # the pupil said yes; the first event of theirs
CONSENT_WITHDRAWN = "consent_withdrawn"  # the marker that stays after the purge

# The only kinds a pupil's browser may report through /api/event. Everything
# else is emitted by the server itself. Without this list a client could write
# a "prompt" or a "task_completed" into the research log.
CLIENT_KINDS = (FIRST_KEYSTROKE, COPY, PASTE)

# Pseudonym used for class-level events (teacher actions, server start).
CLASS = "class"


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
                     key=lambda e: _ts(e["timestamp"]))

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
        first_prompt = min(ep["prompts"], key=_ts)
        if ep["shown"]:
            gap = _seconds(ep["shown"], first_prompt)
            if gap >= 0:                  # a negative gap is a data fault
                gaps.append(gap)
        if any(_ts(a) < _ts(first_prompt) for a in ep["attempts"]):
            tried_first += 1

    return {
        "n_tasks_seen": len({ep["task"] for ep in episodes}),
        "n_episodes": len(episodes),
        "n_episodes_with_prompt": with_prompt,
        "t_first_prompt_median_s": _median(gaps),
        "abhr": round(tried_first / with_prompt, 4) if with_prompt else None,
    }


def _ts(s: str) -> datetime:
    # Parsed rather than compared as strings: isoformat() drops the fraction
    # when it is zero, and "09:00:01" vs "09:00:00.5" is only safe by luck.
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _seconds(a: str, b: str) -> float:
    return (_ts(b) - _ts(a)).total_seconds()


def _median(xs: list[float]) -> float | None:
    if not xs:
        return None
    s = sorted(xs)
    n = len(s)
    return round(s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2, 2)
