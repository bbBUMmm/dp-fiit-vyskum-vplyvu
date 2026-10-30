"""server.py -- the exercise client, in all three conditions, for one classroom.

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

Everything else -- the tasks, the layout, the timing, the event log, the
interactive activities, the interaction counters -- is shared and identical.

How it is deployed (chapter 6 of the thesis)
--------------------------------------------
One machine in the classroom runs this server; pupils open it in a browser on
a school PC or a phone (`--host 0.0.0.0`), and every event lands in one log on
that machine. The teacher opens /teacher on the same server: a PIN-protected
dashboard that launches the interactive activities and shows the technical
state of the class. Run with the default `--host 127.0.0.1` it is the original
one-laptop setup.

What the dashboard deliberately does NOT show: any pupil's prompts, and any
process or outcome measure while the study is running. Appendix E promises
both -- prompts are not read in real time, and interim results are not looked
at. The measures exist; they are computed after collection (`metrics.py`), or
in the researcher view, which must be switched on explicitly. Nor does it show
who agreed to be recorded.

Consent (`consent.py`, `static/consent.js`): after the code, the pupil is asked
on screen. Until they say yes NOTHING about them is written -- the log's gate
drops their events, the login included -- and a pupil who says no works exactly
like everyone else. A withdrawal deletes what this lesson recorded about them.
With --consent-list, codes without a signed paper consent are never recorded.

Standard library only. It has to run on a locked-down school laptop.

    python server.py --condition A --session 2026-10-07-2A-P1 --salt <school salt>
    python server.py --condition G --host 0.0.0.0 --school GY --codes kody-GY.txt ...
"""
from __future__ import annotations

import argparse
import hmac
import json
import mimetypes
import os
import secrets
import socket
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"

# linkage.py (the code check digit) lives in assessment/ in the repository and
# next to this file in the school kit.
for _p in (HERE, HERE.parent / "assessment"):
    if (_p / "linkage.py").exists() and str(_p) not in sys.path:
        sys.path.append(str(_p))
import linkage                                                  # noqa: E402
import consent as cs                                            # noqa: E402

import activities as act                                        # noqa: E402
import events as ev                                             # noqa: E402
import metrics                                                  # noqa: E402
import peqi_live                                                # noqa: E402
import qr                                                       # noqa: E402
from events import EventLog                                     # noqa: E402
from pedagogy import (Task, KnowledgeState, auto_check,         # noqa: E402
                      build_messages, build_messages_generic,
                      check_self_explanation, guard_output, hint_level_for,
                      load_lesson, next_task, overlap, reply_features,
                      side_tasks)
from providers import PROVIDERS, get_provider                   # noqa: E402

MAX_BODY = 64 * 1024            # a pupil's program is a few kB; 64 kB is generous
MAX_PROMPT = 4000
ASK_MIN_INTERVAL = 1.0          # seconds between two prompts of one pupil
CONNECTED_WINDOW = 15.0         # seconds since the last pulse that count as online


# ===========================================================================
class Session:
    """One pupil's state for one lesson. Held in memory; the log is the record,
    and on a restart the state is rebuilt from the log (`Classroom.replay`)."""

    def __init__(self, pseudonym: str, skills: list[str]):
        self.pseudonym = pseudonym
        self.state = KnowledgeState(skills)
        self.completed: set[str] = set()
        self.skipped: set[str] = set()
        self.explained: set[str] = set()
        self.turns: list[dict] = []
        self.replies: list[str] = []      # this episode's replies, memory only
        self.current: str | None = None
        self.shown_at = 0.0
        self.first_idea_logged = False
        self.first_key_logged = False
        self.devices: set[str] = set()
        self.last_seen = 0.0
        self.asking = False
        self.last_ask = 0.0
        self.login_info: dict | None = None   # held back until consent is yes
        self.lock = threading.RLock()


class Classroom:
    """Everything the server knows, behind locks.

    `ThreadingHTTPServer` answers each request on its own thread, and a class of
    thirty pupils on one host produces concurrent requests for the same pupil
    (a double click, a telemetry beat during a slow model reply). Every mutable
    structure is therefore guarded; the first version had none.
    """

    def __init__(self, a: argparse.Namespace):
        self.lock = threading.RLock()
        self.condition = a.condition
        self.lesson = load_lesson(a.tasks)
        self.tasks = self.lesson.tasks
        self.by_id = {t.id: t for t in self.tasks}
        self.side = side_tasks(self.tasks)
        for t in self.tasks:          # K and G walk only the main sequence
            t.scaffold_for_only = t.id in self.side
        self.main = [t.id for t in self.tasks if t.id not in self.side]
        self.log = EventLog(a.log, salt=a.salt, session=a.session,
                            condition=a.condition, period=a.period)
        self.provider = get_provider(a.provider)
        self.provider_name = a.provider
        self.sessions: dict[str, Session] = {}
        self.tokens: dict[str, str] = {}
        self.teacher_tokens: set[str] = set()
        self.teacher_pin = a.teacher_pin
        self.school = (a.school or "").upper() or None
        self.allowed = self._read_codes(a.codes)
        self.log_answer_text = a.log_answer_text
        # consent: pseudonym -> state; `paper` = pseudonyms whose signed consent
        # the school listed (None = no list, the screen is the only gate)
        self.consent: dict[str, str] = {}
        listed = getattr(a, "consent_list", "")
        self.paper = ({self.log.pseudonym(c) for c in cs.read_list(listed)}
                      if listed else None)
        self.consent_version = cs.view("lesson", cs.PENDING, self.log_answer_text)["version"]
        self.log.allow = self.recording
        self.researcher_view = a.researcher_view
        self.host, self.port = a.host, a.port
        self.started = time.time()
        self.phase = "uvod"
        packs = act.load_packs(a.activities) if Path(a.activities).is_dir() else {}
        self.live = act.Live(packs)
        self.latencies: list[int] = []

    @staticmethod
    def _read_codes(path: str) -> set[str]:
        if not path:
            return set()
        return {linkage.normalise(x) for x in
                Path(path).read_text(encoding="utf-8").splitlines() if x.strip()}

    # --- pupils ---------------------------------------------------------------
    def session_for(self, pseudonym: str) -> Session:
        with self.lock:
            s = self.sessions.get(pseudonym)
            if s is None:
                s = Session(pseudonym, self.lesson.skills)
                self.sessions[pseudonym] = s
            return s

    def consent_of(self, pseudonym: str) -> str:
        """A pupil seen for the first time is asked -- unless the school's list
        says there is no signed consent, and then they are never recorded."""
        with self.lock:
            st = self.consent.get(pseudonym)
            if st is None:
                st = (cs.NONE if self.paper is not None and pseudonym not in self.paper
                      else cs.PENDING)
                self.consent[pseudonym] = st
            return st

    def consent_view(self, pseudonym: str) -> dict:
        return cs.view("lesson", self.consent_of(pseudonym), self.log_answer_text)

    def recording(self, pseudonym: str) -> bool:
        """The log's gate: only a pupil who said yes is ever written."""
        return self.consent.get(pseudonym) == cs.YES

    def verify_code(self, raw: str) -> str:
        """The canonical code, or a CodeError with a message for the pupil.

        With --school the check character is enforced, exactly as in the test
        runner: a mistyped code is refused at the keyboard instead of becoming a
        phantom pupil whose lesson cannot be joined to their tests.
        """
        raw = (raw or "").strip()
        if self.school:
            code = linkage.verify(raw, self.school)
        else:
            code = linkage.normalise(raw)
            if not code:
                raise linkage.CodeError("Zadaj kód, ktorý si dostal od učiteľa.")
            if len(code) > 32 or not code.isalnum():
                raise linkage.CodeError("Kód môže obsahovať len písmená a číslice.")
        if self.allowed and code not in self.allowed:
            raise linkage.CodeError("Tento kód nie je na zozname pre túto triedu. "
                                    "Zavolaj vyučujúceho.")
        return code

    # --- crash recovery ---------------------------------------------------------
    def replay(self) -> int:
        """Rebuild every pupil's state from the events already in the log.

        A lesson survives a restart: the pupil logs in again with the same code
        and continues at the task they were on, with the knowledge state and the
        completed set they had. Only the chat thread of the current task is gone
        -- the replies were never stored, as the consent promises.
        """
        n = 0
        for e in self.log.read():
            if e.get("session") != self.log.session:
                continue
            if e.get("condition") != self.condition:
                raise SystemExit(
                    f"V zázname {self.log.path} už je relácia '{self.log.session}' "
                    f"v podmienke {e.get('condition')}, nie {self.condition}. "
                    f"Jedna relácia = jedna podmienka; zvoľte iné označenie hodiny.")
            n += 1
            kind, p = e.get("kind"), e.get("pseudonym")
            if p == ev.CLASS:
                if kind == ev.PHASE and e.get("phase") in act.PHASES:
                    self.phase = e["phase"]
                elif kind == ev.ACTIVITY_DEFINED and isinstance(e.get("definition"), dict):
                    try:
                        self.live.add(e["definition"], adhoc=False)
                    except act.ActivityError:
                        pass
                continue
            if not p:
                continue
            if kind == ev.CONSENT:
                self.consent[p] = cs.YES
            elif kind == ev.CONSENT_WITHDRAWN:
                self.consent[p] = cs.NO
            s = self.session_for(p)
            tid = e.get("taskId")
            if kind == ev.ATTEMPT and self.condition == "A" and e.get("skill"):
                s.state.update(e["skill"], bool(e.get("correct")))
            elif kind == ev.TASK_COMPLETED and tid:
                s.completed.add(tid)
            elif kind == ev.TASK_SKIPPED and tid:
                s.completed.add(tid)
                s.skipped.add(tid)
            elif kind == ev.ADAPTIVE_DECISION and e.get("action") == "skip_mastered" \
                    and e.get("task_id"):
                s.completed.add(e["task_id"])
            elif kind == ev.SOLUTION_UNLOCKED and tid:
                s.explained.add(tid)
            elif kind == ev.LOGIN and e.get("device"):
                s.devices.add(e["device"])
        if self.paper is not None:     # a consent the school has since withdrawn
            for p in self.consent:
                if p not in self.paper:
                    self.consent[p] = cs.NONE
        return n

    # --- what the teacher may see -------------------------------------------
    def progress_label(self, s: Session) -> str:
        if s.current is None and s.completed and self._finished(s):
            return "hotovo"
        if s.current in self.main:
            return f"Ú{self.main.index(s.current) + 1}"
        return "medzikrok" if s.current else "—"

    def _finished(self, s: Session) -> bool:
        return all(t in s.completed for t in self.main)

    def overview(self) -> dict:
        now = time.time()
        with self.lock:
            sess = list(self.sessions.values())
        counts = dict(pupils=len(sess),
                      online=sum(1 for s in sess if now - s.last_seen < CONNECTED_WINDOW),
                      finished=sum(1 for s in sess if self._finished(s)),
                      multi_device=sum(1 for s in sess if len(s.devices) > 1))
        hist = {f"Ú{i + 1}": 0 for i in range(len(self.main))}
        hist["medzikrok"] = 0
        hist["hotovo"] = 0
        grid = []
        for s in sorted(sess, key=lambda x: x.pseudonym):
            label = self.progress_label(s)
            if label in hist:
                hist[label] += 1
            grid.append(dict(id=s.pseudonym[:4], task=label,
                             online=now - s.last_seen < CONNECTED_WINDOW))
        c = self.log.counts
        lat = sorted(self.latencies[-50:])
        return dict(
            lesson=dict(topic=self.lesson.topic, subject=self.lesson.subject,
                        lessonId=self.lesson.lesson_id, status=self.lesson.status,
                        condition=self.condition, session=self.log.session,
                        period=self.log.period, provider=self.provider_name,
                        started=self.started, now=now, phase=self.phase,
                        phases=[dict(id=p, label=act.PHASE_LABELS[p]) for p in act.PHASES],
                        nTasks=len(self.main)),
            join=dict(urls=join_urls(self.host, self.port),
                      local=self.host in ("127.0.0.1", "localhost")),
            counts=counts, progress=hist, grid=grid,
            health=dict(events=sum(c.values()), prompts=c.get(ev.PROMPT_SENT, 0),
                        replies=c.get(ev.ASSISTANT_REPLY, 0),
                        provider_errors=c.get(ev.PROVIDER_ERROR, 0),
                        guard_violations=c.get(ev.GUARD_VIOLATION, 0),
                        latency_ms_median=lat[len(lat) // 2] if lat else None),
            live=self.live_state(),
            history=self.live.history[-12:],
            researcherView=self.researcher_view)

    def live_state(self) -> dict | None:
        with self.live.lock:
            cur = self.live.current
            if not cur:
                return None
            return dict(cur, activity=self.live.library[cur["id"]],
                        results=self.live.results())


def join_urls(host: str, port: int) -> list[str]:
    if host not in ("0.0.0.0", "::", ""):
        return [f"http://{host}:{port}/"]
    ips: set[str] = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))        # no packet is sent
        ips.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        ips.update(socket.gethostbyname_ex(socket.gethostname())[2])
    except OSError:
        pass
    good = sorted(ip for ip in ips if not ip.startswith(("127.", "169.254.")))
    return [f"http://{ip}:{port}/" for ip in good] or [f"http://127.0.0.1:{port}/"]


# ===========================================================================
class HttpError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


def _int(v, lo: int, hi: int, default: int = 0) -> int:
    try:
        x = int(v)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, x))


class Handler(BaseHTTPRequestHandler):
    server_version = "vyskum-ai-trieda/2.0"
    protocol_version = "HTTP/1.1"
    timeout = 30                      # drop idle keep-alive connections

    @property
    def room(self) -> Classroom:
        return self.server.room       # type: ignore[attr-defined]

    # --- plumbing ---------------------------------------------------------
    def log_message(self, fmt, *args):    # the console belongs to the teacher
        pass

    def _headers(self, status: int, ctype: str, length: int) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; img-src 'self' data: blob:; "
                         "style-src 'self' 'unsafe-inline'; script-src 'self'; "
                         "connect-src 'self'; frame-ancestors 'none'")
        self.end_headers()

    def _json(self, obj, status: int = 200) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self._headers(status, "application/json; charset=utf-8", len(body))
        self.wfile.write(body)

    def _read_raw(self) -> None:
        """Consume the request body BEFORE anything else happens.

        With HTTP/1.1 keep-alive, a handler that answers without reading the
        body (a 401, or an endpoint that ignores its `{}`) leaves those bytes in
        the socket, and the browser's next request on the same connection is
        parsed as "{}POST /api/..." -- a 501 for a request that was fine. The
        stdlib test client opens a new connection per request, so no test saw
        it; every browser reuses connections.
        """
        self._raw, self._raw_error = b"", None
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            self.close_connection = True
            self._raw_error = HttpError(400, "neplatná dĺžka požiadavky")
            return
        if n > MAX_BODY:
            self.close_connection = True        # do not read megabytes to discard them
            self._raw_error = HttpError(413, "požiadavka je príliš veľká")
            return
        if n > 0:
            self._raw = self.rfile.read(n)

    def _body(self) -> dict:
        if self._raw_error:
            raise self._raw_error
        if not self._raw:
            return {}
        try:
            data = json.loads(self._raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise HttpError(400, "neplatný JSON")
        if not isinstance(data, dict):
            raise HttpError(400, "očakáva sa objekt JSON")
        return data

    def _pupil(self) -> Session:
        tok = self.headers.get("X-Token") or ""
        with self.room.lock:
            p = self.room.tokens.get(tok)
        if not p:
            raise HttpError(401, "Prihlásenie vypršalo. Zadaj kód znova.")
        s = self.room.session_for(p)
        s.last_seen = time.time()
        return s

    def _teacher(self) -> None:
        tok = self.headers.get("X-Teacher") or ""
        if not tok or tok not in self.room.teacher_tokens:
            raise HttpError(401, "Panel učiteľa vyžaduje PIN.")

    def _dispatch(self, routes: dict, path: str) -> None:
        fn = routes.get(path)
        if fn is None:
            raise HttpError(404, "nenájdené")
        fn()

    def _guarded(self, fn) -> None:
        try:
            fn()
        except HttpError as e:
            self._json({"error": e.message}, e.status)
        except linkage.CodeError as e:
            self._json({"error": str(e)}, 400)
        except act.ActivityError as e:
            self._json({"error": str(e)}, 400)
        except cs.ConsentError as e:
            self._json({"error": str(e)}, e.status)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:                       # never 500 a classroom silently
            traceback.print_exc()
            try:
                self._json({"error": type(e).__name__, "detail": str(e)}, 500)
            except OSError:
                pass

    # --- GET ----------------------------------------------------------------
    def do_GET(self):
        u = urlsplit(self.path)
        self.query = parse_qs(u.query)
        self._raw, self._raw_error = b"", None
        if u.path.startswith("/api/"):
            return self._guarded(lambda: self._dispatch({
                "/api/config": self._config,
                "/api/pulse": self._pulse,
                "/api/activity": self._activity,
                "/api/teacher/state": self._t_state,
                "/api/teacher/library": self._t_library,
                "/api/teacher/qr.svg": self._t_qr,
                "/api/teacher/metrics": self._t_metrics,
                "/api/teacher/export.csv": self._t_export,
            }, u.path))
        self._guarded(lambda: self._static(u.path))

    def _static(self, path: str) -> None:
        rel = {"/": "index.html", "": "index.html",
               "/teacher": "teacher.html", "/ucitel": "teacher.html"}.get(path, path.lstrip("/"))
        f = (STATIC / rel).resolve()
        # is_relative_to, not startswith: "static_old/x" starts with "static"
        if not f.is_relative_to(STATIC.resolve()) or not f.is_file():
            raise HttpError(404, "nenájdené")
        data = f.read_bytes()
        ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript",
                                                  "application/json", "image/svg+xml"):
            ctype += "; charset=utf-8"
        self._headers(200, ctype, len(data))
        self.wfile.write(data)

    # --- POST ---------------------------------------------------------------
    def do_POST(self):
        path = urlsplit(self.path).path
        self._read_raw()
        self._guarded(lambda: self._dispatch({
            "/api/login": self._login,
            "/api/logout": self._logout,
            "/api/consent": self._consent,
            "/api/next": self._next,
            "/api/event": self._event,
            "/api/attempt": self._attempt,
            "/api/skip": self._skip,
            "/api/ask": self._ask,
            "/api/solution": self._solution,
            "/api/explain": self._explain,
            "/api/telemetry": self._telemetry,
            "/api/activity/respond": self._activity_respond,
            "/api/activity/engage": self._activity_engage,
            "/api/teacher/login": self._t_login,
            "/api/teacher/phase": self._t_phase,
            "/api/teacher/activity/start": self._t_start,
            "/api/teacher/activity/reveal": self._t_reveal,
            "/api/teacher/activity/close": self._t_close,
            "/api/teacher/activity/create": self._t_create,
        }, path))

    # ======================================================================
    # pupil
    # ======================================================================
    def _config(self):
        r = self.room
        self._json({
            "condition": r.condition,
            "session": r.log.session,
            "topic": r.lesson.topic,
            "subject": r.lesson.subject,
            "lessonId": r.lesson.lesson_id,
            "assistantEnabled": r.condition in ("G", "A"),
            "adaptive": r.condition == "A",
            "nTasks": len(r.main),
            "codeFormat": (f"{r.school}-XXXXX-X" if r.school else ""),
        })

    def _login(self):
        b = self._body()
        r = self.room
        code = r.verify_code(str(b.get("code") or ""))
        p = r.log.pseudonym(code)
        s = r.session_for(p)
        device = str(b.get("device") or "")[:40]
        ua = (self.headers.get("User-Agent") or "").lower()
        token = secrets.token_urlsafe(18)
        with r.lock:
            r.tokens[token] = p
        with s.lock:
            resumed = bool(s.completed or s.current)
            if device:
                s.devices.add(device)
            s.last_seen = time.time()
            # written now only if the pupil already said yes; otherwise held
            # until they do (`_consent`) -- the login is data about them too
            s.login_info = dict(
                device=device,
                mobile=any(k in ua for k in ("mobile", "android", "iphone", "ipad")),
                resumed=resumed, devices=len(s.devices))
            r.log.emit(ev.LOGIN, p, **s.login_info)
        self._json({"token": token, "resumed": resumed, "consent": r.consent_view(p)})

    def _consent(self):
        """Read the pupil's consent (no `choice`), or change it.

        yes -> the consent record, the login that was held back, and from then
               on everything the pupil does;
        no  -> nothing is written. After a yes it is a withdrawal: the marker is
               written and every other event of this pupil in this lesson is
               deleted at once (`EventLog.purge`).
        """
        r = self.room
        s = self._pupil()
        choice = self._body().get("choice")
        purged = None
        if choice is not None:
            with s.lock:
                new, action = cs.transition(r.consent_of(s.pseudonym), choice)
                with r.lock:
                    r.consent[s.pseudonym] = new
                if action == cs.START:
                    r.log.emit(ev.CONSENT, s.pseudonym, version=r.consent_version,
                               scope="lesson", paperList=r.paper is not None)
                    if s.login_info:
                        r.log.emit(ev.LOGIN, s.pseudonym, **s.login_info)
                elif action == cs.WITHDRAW:
                    r.log.emit(ev.CONSENT_WITHDRAWN, s.pseudonym, force=True,
                               version=r.consent_version)
                    purged = r.log.purge(s.pseudonym, keep=(ev.CONSENT_WITHDRAWN,))
        out = r.consent_view(s.pseudonym)
        if purged is not None:
            out["purged"] = purged
        self._json(out)

    def _logout(self):
        s = self._pupil()
        tok = self.headers.get("X-Token") or ""
        with self.room.lock:
            self.room.tokens.pop(tok, None)
        self.room.log.emit(ev.LOGOUT, s.pseudonym)
        self._json({"ok": True})

    def _next(self):
        """Hand out the next exercise. In condition A the choice is adaptive."""
        r = self.room
        s = self._pupil()
        log = r.log
        with s.lock:
            kind = None
            if r.condition == "A":
                d = next_task(r.tasks, s.state, s.completed)
                log.emit(ev.ADAPTIVE_DECISION, s.pseudonym,
                         **d.as_dict(), mastery_all=s.state.summary())
                while d.action == "skip_mastered" and d.task_id:
                    s.completed.add(d.task_id)
                    d = next_task(r.tasks, s.state, s.completed)
                    log.emit(ev.ADAPTIVE_DECISION, s.pseudonym,
                             **d.as_dict(), mastery_all=s.state.summary())
                task_id, hint_level = d.task_id, d.hint_level
                kind = {"insert_scaffold": "scaffold", "harder": "harder"}.get(d.action)
            else:
                # K and G walk the fixed sequence: the exercises are identical, the
                # ORDER is part of the manipulation and must not adapt here
                remaining = [t for t in r.tasks
                             if t.id not in s.completed and not t.scaffold_for_only]
                task_id = remaining[0].id if remaining else None
                hint_level = 1

            done_main = sum(1 for t in r.main if t in s.completed)
            if task_id is None:
                s.current = None
                return self._json({"done": True, "total": len(r.main),
                                   "completed": done_main,
                                   "skipped": len(s.skipped & set(r.main))})
            t = r.by_id[task_id]
            s.current, s.shown_at = t.id, time.time()
            s.turns, s.replies = [], []                  # new task, new thread
            s.first_idea_logged = s.first_key_logged = False
            index = (r.main.index(t.id) + 1) if t.id in r.main else min(done_main + 1, len(r.main))
            log.emit(ev.TASK_SHOWN, s.pseudonym, taskId=t.id, skill=t.skill,
                     hintLevel=hint_level, index=index, total=len(r.main))
            self._json({"done": False, "taskId": t.id, "prompt": t.prompt,
                        "skill": t.skill,
                        "skillLabel": r.lesson.skill_labels.get(t.skill, ""),
                        "hintLevel": hint_level, "kind": kind,
                        "explained": t.id in s.explained,
                        "index": index, "total": len(r.main),
                        "completed": done_main})

    def _task(self, b: dict) -> Task:
        t = self.room.by_id.get(str(b.get("taskId") or ""))
        if t is None:
            raise HttpError(400, "unknown task")
        return t

    def _first_idea(self, s: Session, t: Task, trigger: str, draft: str) -> None:
        """The pupil's own draft at their first move on a task -- the operational
        form of "prvé nápady pri odpovedi". Logged once per episode, on whichever
        comes first: an attempt, or a question to the assistant."""
        if s.first_idea_logged or s.current != t.id:
            return
        s.first_idea_logged = True
        draft = draft or ""
        extra = {"draftText": draft[:4000]} if self.room.log_answer_text else {}
        self.room.log.emit(ev.FIRST_IDEA, s.pseudonym, taskId=t.id, trigger=trigger,
                           draftChars=len(draft.strip()),
                           draftWords=len(draft.split()),
                           msSinceShown=int((time.time() - s.shown_at) * 1000)
                           if s.shown_at else None, **extra)

    def _event(self):
        """Client-side signals the network cannot see. Only the kinds in
        CLIENT_KINDS are accepted: the first version wrote any `kind` the
        browser sent, so a client could put a fake prompt into the research log."""
        r = self.room
        s = self._pupil()
        b = self._body()
        kind = b.get("kind")
        if kind not in ev.CLIENT_KINDS:
            raise HttpError(400, "neznámy druh udalosti")
        tid = str(b.get("taskId") or "") or None
        with s.lock:
            if kind == ev.FIRST_KEYSTROKE:
                if s.first_key_logged or tid != s.current:
                    return self._json({"ok": True, "dedup": True})
                s.first_key_logged = True
                r.log.emit(kind, s.pseudonym, taskId=tid)
            elif kind == ev.COPY:
                src = b.get("source") if b.get("source") in (
                    "assistant", "task", "answer", "activity", "other") else "other"
                r.log.emit(kind, s.pseudonym, taskId=tid, source=src,
                           chars=_int(b.get("chars"), 0, 100000))
            else:
                tgt = b.get("target") if b.get("target") in (
                    "answer", "prompt", "explanation", "activity", "other") else "other"
                r.log.emit(kind, s.pseudonym, taskId=tid, target=tgt,
                           chars=_int(b.get("chars"), 0, 100000),
                           fromAssistant=bool(b.get("fromAssistant")))
        self._json({"ok": True})

    def _attempt(self):
        """A genuine attempt. Feeds BKT and the attempt-before-help ratio."""
        r = self.room
        s = self._pupil()
        b = self._body()
        t = self._task(b)
        answer = str(b.get("answer") or "")
        correct = bool(b.get("correct"))
        conf = b.get("confidence")
        conf = _int(conf, 0, 100) if conf is not None else None
        with s.lock:
            self._first_idea(s, t, "attempt", answer)
            if r.condition == "A":
                mastery = round(s.state.update(t.skill, correct), 4)
            else:
                mastery = None      # there is no adaptive layer to have an estimate
            extra = {"answerText": answer[:4000]} if r.log_answer_text else {}
            r.log.emit(ev.ATTEMPT, s.pseudonym, taskId=t.id, skill=t.skill,
                       correct=correct, confidence=conf,
                       answerChars=len(answer), answerWords=len(answer.split()),
                       autoCorrect=auto_check(t, answer),
                       assistantOverlap=overlap(answer, s.replies),
                       pastedFromAssistant=bool(b.get("pastedFromAssistant")),
                       mastery=mastery, **extra)
            if correct:
                s.completed.add(t.id)
                r.log.emit(ev.TASK_COMPLETED, s.pseudonym, taskId=t.id,
                           skill=t.skill, mastery=mastery)
        # NOTE: autoCorrect is never returned. A tool that tells the pupil whether
        # they were right is giving feedback the protocol does not allow.
        self._json({"ok": True, "correct": correct, "mastery": mastery})

    def _skip(self):
        """An honest way out of a task. Without it a pupil stuck in condition K
        could move on only by claiming the answer was correct -- which is what the
        self-assessment would then have recorded."""
        r = self.room
        s = self._pupil()
        t = self._task(self._body())
        with s.lock:
            s.completed.add(t.id)
            s.skipped.add(t.id)
            r.log.emit(ev.TASK_SKIPPED, s.pseudonym, taskId=t.id, skill=t.skill,
                       msSinceShown=int((time.time() - s.shown_at) * 1000)
                       if s.current == t.id and s.shown_at else None)
        self._json({"ok": True})

    def _ask(self):
        """The assistant. This is where the three conditions actually differ."""
        r = self.room
        s = self._pupil()
        b = self._body()
        if r.condition == "K":
            # not merely hidden in the UI: the endpoint refuses, so a pupil who
            # finds it cannot use it, and the attempt is recorded
            r.log.emit(ev.GUARD_VIOLATION, s.pseudonym,
                       reason="assistant_requested_in_control")
            raise HttpError(403, "assistant disabled in this lesson")

        user_text = str(b.get("prompt") or "").strip()
        if not user_text:
            raise HttpError(400, "empty prompt")
        if len(user_text) > MAX_PROMPT:
            raise HttpError(400, "Správa je príliš dlhá. Skráť ju, prosím.")
        # In condition A a prompt without a known task used to fall through to
        # the GENERIC message list -- no system prompt, no guard. One stale
        # taskId and a pupil in A was in condition G.
        t = self._task(b)

        with s.lock:
            now = time.time()
            if s.asking or now - s.last_ask < ASK_MIN_INTERVAL:
                raise HttpError(429, "Počkaj na odpoveď asistenta.")
            self._first_idea(s, t, "prompt", str(b.get("draft") or ""))
            level = peqi_live.classify(user_text)
            r.log.emit(ev.PROMPT_SENT, s.pseudonym, taskId=t.id,
                       promptText=user_text, promptChars=len(user_text),
                       turn=len(s.turns) // 2 + 1, peqiLevel=level,
                       peqiWeight=peqi_live.WEIGHTS.get(level))
            if r.condition == "A":
                # the hint level comes from the knowledge state, here, and not
                # from the browser -- the first version trusted a client field
                hint = hint_level_for(s.state.mastery(t.skill))
                msgs = build_messages(r.lesson.topic, t, s.state, hint,
                                      s.turns, user_text, subject=r.lesson.subject,
                                      grade=r.lesson.grade)
            else:
                msgs = build_messages_generic(s.turns, user_text)
            # set last, so a failure above cannot leave the pupil locked out
            s.asking, s.last_ask = True, now

        try:
            reply = r.provider.complete(msgs)       # outside the lock: may take seconds
        finally:
            with s.lock:
                s.asking = False

        with s.lock:
            if reply.error:
                r.log.emit(ev.PROVIDER_ERROR, s.pseudonym, taskId=t.id,
                           detail=reply.error)
                return self._json({"text": "Asistent je práve nedostupný. Skús "
                                           "pokračovať sám a povedz to učiteľovi.",
                                   "degraded": True})
            text, guarded = reply.text, False
            if r.condition == "A":
                g = guard_output(text, t.answer)
                if not g.passed:
                    # a system prompt is a request, not a constraint; the rate at
                    # which it fails is a number the thesis has to report
                    r.log.emit(ev.GUARD_VIOLATION, s.pseudonym, taskId=t.id,
                               violations=g.violations, originalChars=len(text))
                    guarded = True
                text = g.text
            s.turns.append({"role": "user", "content": user_text})
            s.turns.append({"role": "assistant", "content": text})
            s.replies.append(text)
            r.latencies.append(reply.latency_ms)
            r.log.emit(ev.ASSISTANT_REPLY, s.pseudonym, taskId=t.id,
                       replyChars=len(text), latencyMs=reply.latency_ms,
                       model=reply.model, guarded=guarded,
                       replyFeatures=reply_features(text, t.answer))
        self._json({"text": text})

    def _solution(self):
        """The pupil asked to see the solution. Recorded in every condition --
        asking for the answer is itself help-seeking behaviour."""
        r = self.room
        s = self._pupil()
        t = self._task(self._body())
        with s.lock:
            r.log.emit(ev.SOLUTION_REQUESTED, s.pseudonym, taskId=t.id)
            if r.condition != "A":
                return self._json({"mode": "later"})
            if t.id in s.explained:
                return self._json({"mode": "unlocked",
                                   "solution": t.solution or t.answer})
        self._json({"mode": "gate"})

    def _explain(self):
        """The self-explanation gate. Only condition A has one."""
        r = self.room
        s = self._pupil()
        b = self._body()
        t = self._task(b)
        text = str(b.get("text") or "")[:4000]
        with s.lock:
            if r.condition != "A":
                s.explained.add(t.id)
                return self._json({"accepted": True, "reason": ""})
            res = check_self_explanation(text)
            r.log.emit(ev.SELF_EXPLANATION, s.pseudonym, taskId=t.id,
                       accepted=res.accepted, checks=res.checks,
                       text=text, chars=len(text))
            out = {"accepted": res.accepted, "reason": res.reason}
            if res.accepted:
                s.explained.add(t.id)
                r.log.emit(ev.SOLUTION_UNLOCKED, s.pseudonym, taskId=t.id)
                out["solution"] = t.solution or t.answer
        self._json(out)

    def _telemetry(self):
        """Interaction counters since the last beat: clicks, keystrokes, focus
        losses, and how the time divided into active, idle and hidden. The raw
        material of the engagement measures; never any content."""
        r = self.room
        s = self._pupil()
        b = self._body()
        win = 10 * 60 * 1000
        fields = dict(clicks=_int(b.get("clicks"), 0, 5000),
                      keys=_int(b.get("keys"), 0, 50000),
                      focusLoss=_int(b.get("focusLoss"), 0, 500),
                      hiddenMs=_int(b.get("hiddenMs"), 0, win),
                      activeMs=_int(b.get("activeMs"), 0, win),
                      idleMs=_int(b.get("idleMs"), 0, win))
        if any(fields.values()):
            r.log.emit(ev.INTERACTION, s.pseudonym,
                       taskId=str(b.get("taskId") or "") or None,
                       view=str(b.get("view") or "")[:20], phase=r.phase, **fields)
        self._json({"ok": True})

    def _pulse(self):
        s = self._pupil()
        self._json({"activity": self.room.live.pulse(), "phase": self.room.phase,
                    "now": time.time(), "me": s.pseudonym[:4]})

    def _activity(self):
        r = self.room
        s = self._pupil()
        v = r.live.view_for(s.pseudonym)
        if v is None:
            return self._json({"activity": None})
        if v.pop("first_view"):
            r.log.emit(ev.ACTIVITY_VIEW, s.pseudonym, activityId=v["activity"]["id"],
                       version=v["version"], activityType=v["activity"]["type"],
                       phase=r.phase)
        self._json(v)

    def _activity_respond(self):
        r = self.room
        s = self._pupil()
        b = self._body()
        aid = str(b.get("activityId") or "")
        version = _int(b.get("version"), 0, 10 ** 9)
        resp = b.get("response")
        checked = r.live.respond(s.pseudonym, aid, version,
                                 resp if isinstance(resp, dict) else {})
        logged = {k: v for k, v in checked.items() if k != "text"}
        if checked.get("text"):
            logged["textChars"] = len(checked["text"])
            if r.log_answer_text:
                logged["text"] = checked["text"]
        r.log.emit(ev.ACTIVITY_RESPONSE, s.pseudonym, activityId=aid, version=version,
                   activityType=r.live.library[aid]["type"], phase=r.phase,
                   latencyMs=checked.get("latency_ms"),
                   **{k: v for k, v in logged.items() if k != "latency_ms"})
        self._json({"ok": True, "mine": checked})

    def _activity_engage(self):
        r = self.room
        s = self._pupil()
        b = self._body()
        r.log.emit(ev.ACTIVITY_ENGAGEMENT, s.pseudonym,
                   activityId=str(b.get("activityId") or "")[:40],
                   version=_int(b.get("version"), 0, 10 ** 9),
                   steps=_int(b.get("steps"), 0, 10000),
                   plays=_int(b.get("plays"), 0, 1000),
                   msVisible=_int(b.get("msVisible"), 0, 3 * 3600 * 1000),
                   predictions=_int(b.get("predictions"), 0, 1000),
                   predictionsCorrect=_int(b.get("predictionsCorrect"), 0, 1000))
        self._json({"ok": True})

    # ======================================================================
    # teacher
    # ======================================================================
    def _t_login(self):
        b = self._body()
        pin = str(b.get("pin") or "")
        if not hmac.compare_digest(pin.encode(), self.room.teacher_pin.encode()):
            time.sleep(0.6)                 # slows guessing; costs a teacher nothing
            raise HttpError(403, "Nesprávny PIN.")
        tok = secrets.token_urlsafe(18)
        self.room.teacher_tokens.add(tok)
        self._json({"token": tok})

    def _t_state(self):
        self._teacher()
        self._json(self.room.overview())

    def _t_library(self):
        self._teacher()
        r = self.room
        with r.live.lock:
            packs = {}
            for a in r.live.library.values():
                packs.setdefault(a.get("pack", "vlastne"), []).append(a)
        titles = {k: v["title"] for k, v in r.live.packs.items()}
        titles.setdefault("vlastne", "Vytvorené počas hodiny")
        self._json({"packs": [dict(pack=k, title=titles.get(k, k), activities=v)
                              for k, v in packs.items()],
                    "subject": r.lesson.subject,
                    "types": [dict(id=t, label=act.TYPE_LABELS[t]) for t in act.TYPES],
                    "phases": [dict(id=p, label=act.PHASE_LABELS[p]) for p in act.PHASES]})

    def _t_qr(self):
        self._teacher()
        text = (self.query.get("text") or [""])[0][:200]
        if not text:
            raise HttpError(400, "chýba text")
        svg = qr.svg(text).encode("utf-8")
        self._headers(200, "image/svg+xml; charset=utf-8", len(svg))
        self.wfile.write(svg)

    def _t_phase(self):
        self._teacher()
        ph = self._body().get("phase")
        if ph not in act.PHASES:
            raise HttpError(400, "neznáma fáza")
        self.room.phase = ph
        self.room.log.emit(ev.PHASE, ev.CLASS, phase=ph)
        self._json({"ok": True, "phase": ph})

    def _t_start(self):
        self._teacher()
        aid = str(self._body().get("id") or "")
        cur = self.room.live.start(aid)
        a = self.room.live.library[aid]
        self.room.log.emit(ev.ACTIVITY_STARTED, ev.CLASS, activityId=aid,
                           version=cur["version"], activityType=a["type"],
                           pack=a.get("pack"), phase=self.room.phase)
        self._json({"ok": True, "live": self.room.live_state()})

    def _t_reveal(self):
        self._teacher()
        cur = self.room.live.reveal()
        res = self.room.live.results(public=True)
        self.room.log.emit(ev.ACTIVITY_REVEALED, ev.CLASS, activityId=cur["id"],
                           version=cur["version"], n=res.get("n"),
                           viewers=res.get("viewers"),
                           correctShare=res.get("correct_share"))
        self._json({"ok": True, "live": self.room.live_state()})

    def _t_close(self):
        self._teacher()
        closed = self.room.live.close()
        if closed:
            self.room.log.emit(ev.ACTIVITY_CLOSED, ev.CLASS, activityId=closed["id"],
                               version=closed["version"])
        self._json({"ok": True})

    def _t_create(self):
        self._teacher()
        b = self._body()
        d = b.get("definition")
        if not isinstance(d, dict):
            raise HttpError(400, "chýba definícia aktivity")
        a = self.room.live.add(d, adhoc=True)
        # the definition is logged, so the analysis knows exactly what was asked
        self.room.log.emit(ev.ACTIVITY_DEFINED, ev.CLASS, activityId=a["id"],
                           definition=a)
        out = {"ok": True, "activity": a}
        if b.get("start"):
            cur = self.room.live.start(a["id"])
            self.room.log.emit(ev.ACTIVITY_STARTED, ev.CLASS, activityId=a["id"],
                               version=cur["version"], activityType=a["type"],
                               pack=a.get("pack"), phase=self.room.phase)
            out["live"] = self.room.live_state()
        self._json(out)

    def _t_metrics(self):
        self._teacher()
        if not self.room.researcher_view:
            raise HttpError(403, "Výskumné metriky sú počas zberu vypnuté "
                                 "(spustite server s --researcher-view).")
        rows = metrics.compute(self.room.log.read())
        self._json({"rows": rows, "summary": metrics.summary(rows),
                    "warning": "Priebežná analýza počas zberu je v protokole "
                               "zakázaná (príloha E). Používajte až po zbere."})

    def _t_export(self):
        self._teacher()
        if not self.room.researcher_view:
            raise HttpError(403, "Export je dostupný len vo výskumnom režime.")
        import io
        import csv
        rows = metrics.compute(self.room.log.read())
        buf = io.StringIO()
        cols: list[str] = []
        for row in rows:
            cols += [k for k in row if k not in cols]
        w = csv.DictWriter(buf, fieldnames=cols or ["pseudonym"])
        w.writeheader()
        for row in rows:
            w.writerow({k: ("" if row.get(k) is None else row.get(k)) for k in cols})
        data = buf.getvalue().encode("utf-8-sig")
        self._headers(200, "text/csv; charset=utf-8", len(data))
        self.wfile.write(data)


# ===========================================================================
class Server(ThreadingHTTPServer):
    # http.server asks for SO_REUSEADDR, and on Windows that lets a second server
    # bind a port an older one still holds: the new window starts, the pupils'
    # browsers keep reaching the old lesson. The bind must fail instead.
    allow_reuse_address = os.name != "nt"


def build_server(a: argparse.Namespace) -> ThreadingHTTPServer:
    room = Classroom(a)
    replayed = room.replay()
    httpd = Server((a.host, a.port), Handler)
    httpd.daemon_threads = True
    httpd.room = room                         # type: ignore[attr-defined]
    room.log.emit(ev.SERVER_START, ev.CLASS, host=a.host, port=a.port,
                  provider=a.provider, lessonId=room.lesson.lesson_id,
                  subject=room.lesson.subject, replayedEvents=replayed,
                  activities=len(room.live.library),
                  logAnswerText=bool(a.log_answer_text),
                  consentVersion=room.consent_version,
                  consentList=room.paper is not None)
    return httpd


def parse_args(argv: list[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--condition", choices=["K", "G", "A"], required=True)
    ap.add_argument("--session", default="rehearsal")
    ap.add_argument("--period", type=int, default=0)
    ap.add_argument("--tasks", default=str(HERE / "tasks" / "t1_search.json"),
                    help="lesson file (tasks/*.json)")
    ap.add_argument("--activities", default=str(HERE / "activities"),
                    help="folder with interactive activity packs")
    ap.add_argument("--log", default=str(HERE / "events" / "events.jsonl"))
    ap.add_argument("--salt", default=os.environ.get("STUDY_SALT", ""))
    ap.add_argument("--provider", default=os.environ.get("STUDY_PROVIDER", "stub"),
                    choices=sorted(PROVIDERS))
    ap.add_argument("--host", default="127.0.0.1",
                    help="0.0.0.0 = the whole class connects over the school network")
    ap.add_argument("--port", type=int, default=5173)
    ap.add_argument("--school", default="",
                    help="two-character school code; enforces the code check digit")
    ap.add_argument("--codes", default="", help="file of issued codes, one per line")
    ap.add_argument("--consent-list", default="",
                    help="file of codes with a signed paper consent (guardian AND "
                         "pupil), one per line; other codes are never recorded. "
                         "Without it the consent on screen is the only gate")
    ap.add_argument("--teacher-pin", default=os.environ.get("STUDY_TEACHER_PIN", ""))
    ap.add_argument("--log-answer-text", action="store_true",
                    help="also store the TEXT of answers and drafts (only if the "
                         "consent covers it; by default only their length is stored)")
    ap.add_argument("--researcher-view", action="store_true",
                    help="enable the per-pupil metrics tab; NOT during collection")
    a = ap.parse_args(argv)
    if not a.teacher_pin:
        a.teacher_pin = f"{secrets.randbelow(10 ** 6):06d}"
    return a


def main(argv: list[str] | None = None) -> int:
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

    a = parse_args(sys.argv[1:] if argv is None else argv)
    if not a.salt:
        print("refusing to start: --salt (or STUDY_SALT) is required.\n"
              "The salt is held by the school so that the researcher cannot "
              "reverse a pseudonym back to a pupil.")
        return 2
    if a.school and (len(a.school) != 2 or not a.school.isalnum()):
        print("--school must be the two-character school code, e.g. GY")
        return 2
    try:
        httpd = build_server(a)
    except OSError as e:
        print(f"CHYBA: port {a.port} už používa iné okno (iná hodina alebo test).\n"
              f"Zatvorte to okno (Ctrl+C) a spustite hodinu znova.  [{e}]")
        return 2
    room: Classroom = httpd.room             # type: ignore[attr-defined]
    urls = join_urls(a.host, a.port)
    print("=" * 64)
    print(f" podmienka {a.condition} | {room.lesson.subject}: {room.lesson.topic}")
    print(f" {len(room.main)} úloh | {len(room.live.library)} interaktívnych aktivít | "
          f"poskytovateľ {a.provider}")
    print(f" záznam -> {a.log}")
    print("-" * 64)
    print(" ŽIACI otvoria v prehliadači:")
    for u in urls:
        print(f"     {u}")
    print(f" UČITEĽ: {urls[0]}teacher     PIN: {a.teacher_pin}")
    if a.host in ("127.0.0.1", "localhost"):
        print(" (len tento počítač; pre celú triedu spustite s --host 0.0.0.0)")
    if a.researcher_view:
        print(" POZOR: výskumný režim zapnutý -- počas zberu ho nepoužívajte.")
    if room.paper is None:
        print(" SÚHLASY: zoznam podpísaných súhlasov nie je zadaný -- zaznamenáva sa\n"
              "          len podľa voľby žiaka na obrazovke (--consent-list).")
    else:
        print(f" súhlasy: {len(room.paper)} kódov s podpísaným súhlasom; "
              f"ostatné sa nezaznamenávajú")
    print("=" * 64, flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print(f"\nevents written: {room.log.counts}")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
