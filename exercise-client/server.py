"""server.py -- the exercise client, in all three conditions.

One codebase serves K, G and A. That is not a convenience: it is the control.
If the control condition ran on different software, any difference between the
conditions would confound pedagogy with everything else the software does, and
the design's central claim -- that only the pedagogical layer varies -- would be
untestable.

So the three conditions differ in exactly two places, both in `_ask`:

    K : the assistant endpoint refuses; the panel is hidden client-side
    G : messages = history + user text                (no system prompt)
    A : messages = system prompt + knowledge state + history + user text,
        the reply passes the output guard, and the worked solution is behind
        the self-explanation gate

Everything else -- the tasks, the layout, the timing, the event log -- is
shared and identical.

Standard library only. It has to run on a locked-down school laptop.

    python server.py --condition A --session 2026-10-07-2A-P1 --port 5173
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import secrets
import sys
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import events as ev
from events import EventLog
from pedagogy import (Task, KnowledgeState, build_messages,
                      build_messages_generic, check_self_explanation,
                      guard_output, load_tasks, next_task)
from providers import get_provider

HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"


class Session:
    """One pupil's state for one lesson. Held in memory; the log is the record."""

    def __init__(self, pseudonym: str, skills: list[str], tasks: list[Task]):
        self.pseudonym = pseudonym
        self.state = KnowledgeState(skills)
        self.tasks = tasks
        self.completed: set[str] = set()
        self.turns: list[dict] = []
        self.explained: set[str] = set()
        self.token = secrets.token_urlsafe(12)


class Handler(BaseHTTPRequestHandler):
    server_version = "exercise-client/1.0"

    # --- plumbing ---------------------------------------------------------
    def log_message(self, fmt, *args):   # quieter console during a lesson
        if self.path.startswith("/api/"):
            super().log_message(fmt, *args)

    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except ValueError:
            return {}

    def _session(self, code: str) -> Session:
        cfg = self.server.cfg
        pseudo = cfg["log"].pseudonym(code)
        s = cfg["sessions"].get(pseudo)
        if s is None:
            s = Session(pseudo, cfg["skills"], cfg["tasks"])
            cfg["sessions"][pseudo] = s
        return s

    # --- static -----------------------------------------------------------
    def do_GET(self):
        if self.path.startswith("/api/config"):
            cfg = self.server.cfg
            return self._json({
                "condition": cfg["condition"],
                "session": cfg["log"].session,
                "topic": cfg["topic"],
                "assistantEnabled": cfg["condition"] in ("G", "A"),
                "adaptive": cfg["condition"] == "A",
                "nTasks": len(cfg["tasks"]),
            })
        rel = "index.html" if self.path in ("/", "") else self.path.lstrip("/")
        f = (STATIC / rel).resolve()
        if not str(f).startswith(str(STATIC)) or not f.is_file():
            return self._json({"error": "not found"}, 404)
        data = f.read_bytes()
        ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # --- api --------------------------------------------------------------
    def do_POST(self):
        routes = {
            "/api/next": self._next,
            "/api/event": self._event,
            "/api/attempt": self._attempt,
            "/api/ask": self._ask,
            "/api/explain": self._explain,
        }
        fn = routes.get(self.path.split("?")[0])
        if fn is None:
            return self._json({"error": "not found"}, 404)
        try:
            fn(self._body())
        except Exception as e:                       # never 500 a classroom
            self._json({"error": type(e).__name__, "detail": str(e)}, 500)

    # ----------------------------------------------------------------------
    def _next(self, b):
        """Hand out the next exercise. In condition A the choice is adaptive."""
        cfg = self.server.cfg
        s = self._session(b.get("student", "anon"))
        by_id = {t.id: t for t in cfg["tasks"]}

        if cfg["condition"] == "A":
            d = next_task(cfg["tasks"], s.state, s.completed)
            cfg["log"].emit(ev.ADAPTIVE_DECISION, s.pseudonym,
                            **d.as_dict(), mastery_all=s.state.summary())
            while d.action == "skip_mastered" and d.task_id:
                s.completed.add(d.task_id)
                d = next_task(cfg["tasks"], s.state, s.completed)
                cfg["log"].emit(ev.ADAPTIVE_DECISION, s.pseudonym,
                                **d.as_dict(), mastery_all=s.state.summary())
            task_id, hint_level = d.task_id, d.hint_level
        else:
            # K and G walk the fixed sequence: the exercises are identical, the
            # ORDER is part of the manipulation and must not adapt here
            remaining = [t for t in cfg["tasks"]
                         if t.id not in s.completed and not t.scaffold_for_only]
            task_id = remaining[0].id if remaining else None
            hint_level = 1

        if task_id is None:
            return self._json({"done": True})
        t = by_id[task_id]
        s.turns = []                                  # new task, new thread
        cfg["log"].emit(ev.TASK_SHOWN, s.pseudonym, taskId=t.id, skill=t.skill,
                        hintLevel=hint_level)
        self._json({"done": False, "taskId": t.id, "prompt": t.prompt,
                    "skill": t.skill, "hintLevel": hint_level,
                    "explained": t.id in s.explained})

    def _event(self, b):
        """Client-side signals the network cannot see (first keystroke)."""
        cfg = self.server.cfg
        s = self._session(b.get("student", "anon"))
        kind = b.get("kind", ev.FIRST_KEYSTROKE)
        cfg["log"].emit(kind, s.pseudonym, taskId=b.get("taskId"))
        self._json({"ok": True})

    def _attempt(self, b):
        """A genuine attempt. Feeds BKT and the attempt-before-help ratio."""
        cfg = self.server.cfg
        s = self._session(b.get("student", "anon"))
        by_id = {t.id: t for t in cfg["tasks"]}
        t = by_id.get(b.get("taskId", ""))
        if t is None:
            return self._json({"error": "unknown task"}, 400)

        correct = bool(b.get("correct"))
        mastery = s.state.update(t.skill, correct) if cfg["condition"] == "A" \
            else s.state.mastery(t.skill)
        cfg["log"].emit(ev.ATTEMPT, s.pseudonym, taskId=t.id, skill=t.skill,
                        correct=correct, answerChars=len(b.get("answer", "")),
                        mastery=round(mastery, 4))
        if correct:
            s.completed.add(t.id)
            cfg["log"].emit(ev.TASK_COMPLETED, s.pseudonym, taskId=t.id,
                            skill=t.skill, mastery=round(mastery, 4))
        self._json({"ok": True, "correct": correct,
                    "mastery": round(mastery, 4)})

    def _ask(self, b):
        """The assistant. This is where the three conditions actually differ."""
        cfg = self.server.cfg
        if cfg["condition"] == "K":
            # not merely hidden in the UI: the endpoint refuses, so a pupil who
            # finds it cannot use it, and the attempt is recorded
            s = self._session(b.get("student", "anon"))
            cfg["log"].emit(ev.GUARD_VIOLATION, s.pseudonym,
                            reason="assistant_requested_in_control")
            return self._json({"error": "assistant disabled in this lesson"}, 403)

        s = self._session(b.get("student", "anon"))
        by_id = {t.id: t for t in cfg["tasks"]}
        t = by_id.get(b.get("taskId", ""))
        user_text = (b.get("prompt") or "").strip()
        if not user_text:
            return self._json({"error": "empty prompt"}, 400)

        cfg["log"].emit(ev.PROMPT_SENT, s.pseudonym, taskId=b.get("taskId"),
                        promptText=user_text, promptChars=len(user_text),
                        turn=len(s.turns) // 2 + 1)

        if cfg["condition"] == "A" and t is not None:
            hint_level = b.get("hintLevel") or 1
            msgs = build_messages(cfg["topic"], t, s.state, hint_level,
                                  s.turns, user_text)
        else:
            msgs = build_messages_generic(s.turns, user_text)

        reply = cfg["provider"].complete(msgs)
        if reply.error:
            cfg["log"].emit(ev.PROVIDER_ERROR, s.pseudonym,
                            taskId=b.get("taskId"), detail=reply.error)
            return self._json({"text": "Asistent je práve nedostupný. Skús "
                                       "pokračovať sám a povedz to učiteľovi.",
                               "degraded": True})

        text = reply.text
        if cfg["condition"] == "A":
            g = guard_output(text, t.answer if t else None)
            if not g.passed:
                # a system prompt is a request, not a constraint; the rate at
                # which it fails is a number the thesis has to report
                cfg["log"].emit(ev.GUARD_VIOLATION, s.pseudonym,
                                taskId=b.get("taskId"),
                                violations=g.violations,
                                originalChars=len(text))
            text = g.text

        s.turns.append({"role": "user", "content": user_text})
        s.turns.append({"role": "assistant", "content": text})
        cfg["log"].emit(ev.ASSISTANT_REPLY, s.pseudonym,
                        taskId=b.get("taskId"), replyChars=len(text),
                        latencyMs=reply.latency_ms, model=reply.model)
        self._json({"text": text})

    def _explain(self, b):
        """The self-explanation gate. Only condition A has one."""
        cfg = self.server.cfg
        s = self._session(b.get("student", "anon"))
        task_id = b.get("taskId", "")
        text = b.get("text", "")

        if cfg["condition"] != "A":
            s.explained.add(task_id)
            return self._json({"accepted": True, "reason": ""})

        r = check_self_explanation(text)
        cfg["log"].emit(ev.SELF_EXPLANATION, s.pseudonym, taskId=task_id,
                        accepted=r.accepted, checks=r.checks,
                        text=text, chars=len(text))
        if r.accepted:
            s.explained.add(task_id)
            cfg["log"].emit(ev.SOLUTION_UNLOCKED, s.pseudonym, taskId=task_id)
        self._json({"accepted": r.accepted, "reason": r.reason})


# allow the fixed sequence to skip scaffolding-only exercises
def _mark_scaffold_only(tasks: list[Task]) -> None:
    scaffolds = {t.scaffold_for for t in tasks if t.scaffold_for}
    harder = {t.harder_variant for t in tasks if t.harder_variant}
    for t in tasks:
        t.scaffold_for_only = t.id in scaffolds or t.id in harder


def main() -> int:
    # Force UTF-8 on the console streams before anything is printed.
    #
    # This is not cosmetic. Every lesson topic is Slovak, so the startup banner
    # contains characters cp1252 cannot encode -- and on Windows, Python picks
    # cp1252 for stdout whenever it is NOT an interactive UTF-8 console, which
    # includes a redirected stream, a logged session, and any school laptop
    # whose console code page was never changed. The server then dies with a
    # UnicodeEncodeError *before serving anything*, and the lesson is over
    # before it starts. errors="replace" so a stray glyph degrades to a question
    # mark rather than taking the process down.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--condition", choices=["K", "G", "A"], required=True)
    ap.add_argument("--session", default="rehearsal")
    ap.add_argument("--period", type=int, default=0)
    ap.add_argument("--tasks", default=str(HERE / "tasks" / "t1_search.json"))
    ap.add_argument("--log", default=str(HERE / "events" / "events.jsonl"))
    ap.add_argument("--salt", default=os.environ.get("STUDY_SALT", ""))
    ap.add_argument("--provider", default=os.environ.get("STUDY_PROVIDER", "stub"))
    ap.add_argument("--port", type=int, default=5173)
    a = ap.parse_args()

    if not a.salt:
        print("refusing to start: --salt (or STUDY_SALT) is required.\n"
              "The salt is held by the school so that the researcher cannot "
              "reverse a pseudonym back to a pupil.")
        return 2

    topic, skills, tasks = load_tasks(a.tasks)
    _mark_scaffold_only(tasks)
    log = EventLog(a.log, salt=a.salt, session=a.session,
                   condition=a.condition, period=a.period)

    httpd = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    httpd.cfg = {
        "condition": a.condition, "topic": topic, "skills": skills,
        "tasks": tasks, "log": log, "sessions": {},
        "provider": get_provider(a.provider),
    }
    print(f"condition {a.condition} | topic: {topic} | {len(tasks)} tasks | "
          f"provider {a.provider}")
    print(f"log -> {a.log}")
    print(f"open http://127.0.0.1:{a.port}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print(f"\nevents written: {log.counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
