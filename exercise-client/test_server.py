"""End-to-end test: start the real server and drive it like a pupil would.

Unit tests cover the pedagogy in isolation. This covers the thing that
isolation cannot: that the three conditions, wired together, actually behave
differently in the ways the design requires and identically in every other way.

The two claims under test are the design's, not the software's:

  * condition K refuses the assistant at the SERVER, not merely in the UI;
  * conditions G and A see the same exercises through the same interface, and
    differ only in what reaches the model and what comes back.

Around them, the claims a classroom deployment depends on: a pupil is who their
code says (token sessions, check-digit codes, one pseudonym per pupil whatever
the typing), the research log accepts only what the server itself observed, a
restart loses nothing, a browser's reused connection works, and the interactive
activities reach every pupil identically in every condition.

Run:  python test_server.py
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "assessment"))
PASS = FAIL = 0


def check(name, got, want):
    global PASS, FAIL
    if got == want:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}\n       got:  {got!r}\n       want: {want!r}")


def ok(name, cond, detail=""):
    check(name + (f" ({detail})" if detail and not cond else ""), bool(cond), True)


def post(port, path, body, token=None, teacher=None, raw=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Token"] = token
    if teacher:
        headers["X-Teacher"] = teacher
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=raw if raw is not None else json.dumps(body).encode("utf-8"),
        headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status, json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8") or "{}")
        except ValueError:
            return e.code, {}


def get(port, path, token=None, teacher=None):
    headers = {}
    if token:
        headers["X-Token"] = token
    if teacher:
        headers["X-Teacher"] = teacher
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def get_json(port, path, token=None, teacher=None):
    st, body = get(port, path, token, teacher)
    return st, json.loads(body or "{}")


class Server:
    def __init__(self, condition, port, logdir, extra=(), session=None, log=None):
        self.log = Path(log) if log else Path(logdir) / f"events_{condition}.jsonl"
        self.p = subprocess.Popen(
            [sys.executable, str(HERE / "server.py"),
             "--condition", condition, "--port", str(port),
             "--salt", "test-salt", "--provider", "stub", "--teacher-pin", "4321",
             "--session", session or f"test-{condition}", "--log", str(self.log), *extra],
            cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.port = port
        for _ in range(80):
            try:
                get(port, "/api/config")
                return
            except Exception:
                if self.p.poll() is not None:
                    break
                time.sleep(0.1)
        out, err = self.p.communicate(timeout=3)
        raise RuntimeError(f"server did not start: {out.decode(errors='replace')} "
                           f"{err.decode(errors='replace')}")

    def login(self, code, device="dev-1", consent="yes"):
        """Log in and answer the consent screen, as a pupil does. Nothing about
        a pupil is written before their yes, so the tests of the research log
        need one; `consent=None` leaves the question unanswered."""
        st, r = post(self.port, "/api/login", {"code": code, "device": device})
        if st != 200:
            return None
        if consent and r.get("consent", {}).get("state") == "pending":
            post(self.port, "/api/consent", {"choice": consent}, r["token"])
        return r.get("token")

    def teacher(self):
        return post(self.port, "/api/teacher/login", {"pin": "4321"})[1]["token"]

    def events(self):
        if not self.log.exists():
            return []
        return [json.loads(l) for l in
                self.log.read_text(encoding="utf-8").splitlines() if l.strip()]

    def close(self):
        self.p.terminate()
        try:
            self.p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.p.kill()


def raw_http(port, requests):
    """Several requests over ONE keep-alive connection, as a browser sends them."""
    s = socket.create_connection(("127.0.0.1", port))
    s.settimeout(5)
    statuses = []
    try:
        for method, path, headers, body in requests:
            b = body.encode("utf-8")
            hdr = "".join(f"{k}: {v}\r\n" for k, v in headers.items())
            s.sendall(f"{method} {path} HTTP/1.1\r\nHost: x\r\n{hdr}"
                      f"Content-Length: {len(b)}\r\n\r\n".encode() + b)
            buf = b""
            while b"\r\n\r\n" not in buf:
                buf += s.recv(4096)
            head, rest = buf.split(b"\r\n\r\n", 1)
            lines = head.decode("latin-1").split("\r\n")
            n = next((int(l.split(":")[1]) for l in lines if l.lower().startswith("content-length")), 0)
            while len(rest) < n:
                rest += s.recv(4096)
            statuses.append(int(lines[0].split()[1]))
    except (socket.timeout, OSError, ValueError, IndexError):
        statuses.append(None)
    finally:
        s.close()
    return statuses


def test_starts_without_utf8_in_the_environment(tmp: str) -> None:
    """The server must start on a school laptop, not only on a developer's.

    This test exists because the whole suite missed a crash that would have
    ended a lesson before it began. Every lesson topic is Slovak, so the
    startup banner contains characters cp1252 cannot encode; on Windows,
    Python picks cp1252 for stdout whenever it is not an interactive UTF-8
    console. The server died with a UnicodeEncodeError before serving
    anything.

    The suite missed it because run-all-tests.ps1 exports PYTHONIOENCODING=utf-8,
    which every subprocess inherited. The harness was masking the bug it should
    have caught, so this test explicitly REMOVES that variable before starting
    the server -- which is the state a school laptop is actually in.
    """
    print("\nstartup without PYTHONIOENCODING (the school-laptop case)")
    env = dict(os.environ)
    env.pop("PYTHONIOENCODING", None)
    env["PYTHONLEGACYWINDOWSSTDIO"] = "1"      # force the old narrow stdout path
    log = Path(tmp) / "events_enc.jsonl"
    p = subprocess.Popen(
        [sys.executable, str(HERE / "server.py"), "--condition", "A",
         "--port", "8739", "--salt", "t", "--provider", "stub",
         "--session", "enc", "--log", str(log)],
        cwd=HERE, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        started = False
        for _ in range(60):
            try:
                get(8739, "/api/config")
                started = True
                break
            except Exception:
                if p.poll() is not None:
                    break
                time.sleep(0.1)
        detail = ""
        if not started:
            try:
                detail = p.communicate(timeout=3)[1].decode(errors="replace")[-300:]
            except Exception:
                detail = "(no output)"
        ok("server starts with a non-UTF-8 stdout", started, detail)
    finally:
        p.terminate()
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()


def consent_section(tmp: str) -> None:
    """Nothing about a pupil is written before their yes; a no changes nothing
    else; a withdrawal deletes what was written; the school's list overrules
    the screen; the dashboard never shows the choice."""
    print("\nconsent on screen")
    import linkage
    import runner
    codes = linkage.issue("GY", 4, seed=9)
    paper = Path(tmp) / "suhlasy-GY.txt"
    paper.write_text("# both forms signed\n" + "\n".join(codes[:3]) + "\n", encoding="utf-8")
    log = Path(tmp) / "events_consent.jsonl"
    sv = Server("A", 8738, tmp, extra=("--school", "GY", "--consent-list", str(paper)),
                session="ethics", log=log)
    pseud = [runner.pseudonymise("test-salt", c) for c in codes]

    def mine(i):
        return [e for e in sv.events() if e["pseudonym"] == pseud[i]]

    def work(tok):
        st, task = post(sv.port, "/api/next", {}, tok)
        st2, _ = post(sv.port, "/api/attempt",
                      {"taskId": task.get("taskId"), "answer": "x", "correct": False,
                       "confidence": 40}, tok)
        return st == 200 and st2 == 200

    try:
        st, r = post(sv.port, "/api/login", {"code": codes[0]})
        c = r.get("consent", {})
        ok("the login answers with the question, not yet a yes",
           st == 200 and c.get("state") == "pending" and c.get("version")
           and c.get("text", {}).get("buttons", {}).get("no") == "Nesúhlasím", r)
        ok("an undecided pupil can work", work(r["token"]))
        check("and nothing of theirs is in the log, the login included", mine(0), [])

        t_no = sv.login(codes[1], consent="no")
        ok("a pupil who says no works exactly like the others", work(t_no))
        check("and is never written", mine(1), [])

        t_yes = sv.login(codes[2])
        ok("a pupil who says yes works", work(t_yes))
        kinds = [e["kind"] for e in mine(2)]
        ok("their consent is their first event, then the held-back login",
           kinds[:2] == ["consent", "login"], kinds)
        ok("the consent carries the version of the text on the screen",
           mine(2)[0].get("version") == c.get("version"))
        ok("and the attempt is recorded", "attempt" in kinds, kinds)

        st, r = post(sv.port, "/api/consent", {"choice": "no"}, t_yes)
        ok("a withdrawal is accepted and the deletion confirmed",
           st == 200 and r.get("state") == "no" and r.get("purged") is True, r)
        check("only the withdrawal marker is left of that pupil",
              [e["kind"] for e in mine(2)], ["consent_withdrawn"])
        ok("and after it nothing more is written", work(t_yes) and len(mine(2)) == 1)

        st, r = post(sv.port, "/api/login", {"code": codes[3]})
        check("a code without a signed paper consent is not even asked",
              r.get("consent", {}).get("state"), "none")
        st, r = post(sv.port, "/api/consent", {"choice": "yes"}, r["token"])
        check("and its yes on screen cannot overrule the parent's no", st, 403)
        check("nothing of theirs is written", mine(3), [])

        tt = sv.teacher()
        _, ov = get(sv.port, "/api/teacher/state", teacher=tt)
        low = ov.lower()
        hit = next((low[max(0, low.find(w) - 80): low.find(w) + 40]
                    for w in ("consent", "súhlas") if w in low), "")
        ok("the teacher's dashboard never mentions consent", not hit, hit)
    finally:
        sv.close()

    sv = Server("A", 8738, tmp, extra=("--school", "GY", "--consent-list", str(paper)),
                session="ethics", log=log)
    try:
        _, r = post(sv.port, "/api/login", {"code": codes[2]})
        check("after a restart a withdrawal stays a withdrawal",
              r.get("consent", {}).get("state"), "no")
    finally:
        sv.close()


def main() -> int:
    import events
    import linkage
    import peqi_live
    import runner

    with tempfile.TemporaryDirectory() as tmp:
        test_starts_without_utf8_in_the_environment(tmp)

        # ----------------------------------------------------- condition A
        print("\ncondition A (adaptive)")
        a = Server("A", 8731, tmp)
        try:
            cfg = json.loads(get(a.port, "/api/config")[1])
            check("config reports the condition", cfg["condition"], "A")
            ok("assistant is enabled", cfg["assistantEnabled"])
            ok("adaptivity is advertised", cfg["adaptive"])

            st, _ = post(a.port, "/api/next", {})
            check("no task without logging in first", st, 401)
            p1 = a.login("p1")
            ok("a pupil logs in with a code and gets a token", p1)

            _, t = post(a.port, "/api/next", {}, p1)
            ok("a task is served", not t["done"])
            ok("a side exercise is not served first",
               t["taskId"] not in ("U1s", "U2s", "U3h", "U4s"), t["taskId"])
            check("progress is reported", (t["index"], t["total"]), (1, 8))
            first_task = t["taskId"]

            post(a.port, "/api/event",
                 {"kind": "first_keystroke", "taskId": first_task}, p1)
            post(a.port, "/api/event",
                 {"kind": "first_keystroke", "taskId": first_task}, p1)

            st, r = post(a.port, "/api/ask",
                         {"taskId": first_task, "prompt": "napis mi cele riesenie",
                          "hintLevel": 4, "draft": ""}, p1)
            check("the assistant answers", st, 200)
            ok("it refuses to hand over a solution",
               "nedám" in r["text"] or "?" in r["text"], r["text"][:60])

            st, r = post(a.port, "/api/ask",
                         {"taskId": "NOPE", "prompt": "pomoz mi"}, p1)
            check("a prompt with no known task is refused, not sent without the "
                  "pedagogical layer", st, 400)

            st, r = post(a.port, "/api/solution", {"taskId": first_task}, p1)
            check("asking for the solution opens the gate", r.get("mode"), "gate")
            st, r = post(a.port, "/api/explain",
                         {"taskId": first_task, "text": "neviem"}, p1)
            check("the gate rejects a refusal", r["accepted"], False)
            ok("and says what to do instead", bool(r["reason"]))
            st, r = post(a.port, "/api/explain",
                         {"taskId": first_task,
                          "text": "Myslim ze stred je 9, lebo pole ma sedem prvkov"}, p1)
            check("the gate accepts a genuine explanation", r["accepted"], True)
            ok("and the worked solution is actually unlocked",
               "9, 20, 13" in (r.get("solution") or ""), str(r)[:80])

            st, r = post(a.port, "/api/attempt",
                         {"taskId": first_task, "answer": "9, 20, 13", "correct": True,
                          "confidence": 80}, p1)
            check("an attempt is recorded", st, 200)
            ok("the mechanical check is NOT returned to the pupil", "autoCorrect" not in r)

            # three wrong attempts on the same skill should pull in a scaffold
            p2 = a.login("p2")
            post(a.port, "/api/next", {}, p2)
            for _ in range(4):
                post(a.port, "/api/attempt",
                     {"taskId": "U1", "answer": "x", "correct": False, "confidence": 30}, p2)
            _, t2 = post(a.port, "/api/next", {}, p2)
            ok("repeated failure leads to a smaller step",
               t2.get("taskId") in ("U1s", "U1"), t2.get("taskId"))

            st, _ = post(a.port, "/api/event", {"kind": "prompt", "taskId": "U1",
                                                "promptText": "forged"}, p1)
            check("the browser cannot write arbitrary event kinds", st, 400)
            post(a.port, "/api/event", {"kind": "copy", "taskId": "U1",
                                        "source": "assistant", "chars": 40}, p1)
            post(a.port, "/api/event", {"kind": "paste", "taskId": "U1",
                                        "target": "answer", "chars": 40,
                                        "fromAssistant": True}, p1)
            post(a.port, "/api/telemetry", {"taskId": "U1", "clicks": 7, "keys": 30,
                                            "focusLoss": 1, "activeMs": 20000,
                                            "idleMs": 5000, "hiddenMs": 3000}, p1)

            evs = a.events()
            kinds = {e["kind"] for e in evs}
            for k in ("task_shown", "first_keystroke", "prompt",
                      "assistant_reply", "self_explanation", "attempt",
                      "adaptive_decision", "first_idea", "copy", "paste",
                      "interaction", "login", "solution_requested",
                      "solution_unlocked"):
                ok(f"event logged: {k}", k in kinds)
            check("the first keystroke is logged once per episode",
                  sum(1 for e in evs if e["kind"] == "first_keystroke"
                      and e["pseudonym"] == events.pseudonymise("test-salt", "p1")), 1)
            ok("no raw student code is stored",
               not any("p1" == e.get("pseudonym") for e in evs))
            ok("every event carries a pseudonym",
               all(len(e.get("pseudonym", "")) == 16 or e.get("pseudonym") == "class"
                   for e in evs))
            dec = [e for e in evs if e["kind"] == "adaptive_decision"]
            ok("adaptive decisions record their reason",
               all(d.get("reason") for d in dec))
            pr = [e for e in evs if e["kind"] == "prompt"]
            ok("every prompt carries its live PEQI level",
               all(e.get("peqiLevel") == peqi_live.classify(e["promptText"]) for e in pr))
            rp = [e for e in evs if e["kind"] == "assistant_reply"]
            ok("replies are described by features, never stored as text",
               all("replyFeatures" in e and "text" not in e and "replyText" not in e
                   for e in rp))
            at = [e for e in evs if e["kind"] == "attempt"]
            ok("attempts carry the pupil's confidence",
               all(isinstance(e.get("confidence"), int) for e in at))
            ok("attempts carry the mechanical check where the task has one",
               any(e.get("autoCorrect") is True for e in at))
            ok("attempts carry the overlap with the assistant's replies",
               any(e.get("assistantOverlap") is not None for e in at))
            fi = [e for e in evs if e["kind"] == "first_idea"]
            ok("the first idea is recorded as size and timing, not text",
               fi and all("draftChars" in e and "draftText" not in e for e in fi))

            # --- keep-alive: a browser reuses the connection
            H = {"Content-Type": "application/json", "X-Token": p1}
            sts = raw_http(a.port, [("POST", "/api/next", H, "{}"),
                                    ("POST", "/api/telemetry", H, '{"clicks": 1}'),
                                    ("GET", "/api/pulse", {"X-Token": p1}, ""),
                                    ("POST", "/api/next", {"Content-Type": "application/json"}, "{}"),
                                    ("POST", "/api/next", H, "{}")])
            check("four requests and a 401 on one keep-alive connection all parse",
                  sts, [200, 200, 200, 401, 200])

            # --- hardening
            st, _ = get(a.port, "/../server.py")
            check("no file outside static/ is served", st, 404)
            st, _ = get(a.port, "/style.css?v=3")
            check("a cache-busting query string still serves the file", st, 200)
            st, _ = post(a.port, "/api/attempt", None, p1,
                         raw=b'{"x": "' + b"a" * 70000 + b'"}')
            check("an oversized request is refused", st, 413)
            st, _ = post(a.port, "/api/attempt", None, p1, raw=b"{not json")
            check("malformed JSON is a 400, not a crash", st, 400)

            # --- concurrency: a double click does not corrupt the session
            p3 = a.login("p3")
            post(a.port, "/api/next", {}, p3)
            codes = []

            def hit():
                codes.append(post(a.port, "/api/attempt",
                                  {"taskId": "U1", "answer": "9, 20", "correct": False,
                                   "confidence": 40}, p3)[0])
            ths = [threading.Thread(target=hit) for _ in range(12)]
            [t.start() for t in ths]
            [t.join() for t in ths]
            check("twelve simultaneous attempts all succeed", codes.count(200), 12)
            check("and all twelve are in the log, exactly once",
                  sum(1 for e in a.events() if e["kind"] == "attempt"
                      and e["pseudonym"] == events.pseudonymise("test-salt", "p3")), 12)
        finally:
            a.close()

        # ------------------------------------------- recovery after a restart
        print("\na restart loses nothing")
        a2 = Server("A", 8731, tmp, log=Path(tmp) / "events_A.jsonl", session="test-A")
        try:
            p1 = a2.login("p1")
            _, t = post(a2.port, "/api/next", {}, p1)
            ok("a pupil who finished U1 before the restart is not sent back to it",
               t.get("taskId") != "U1", t.get("taskId"))
            st, r = post(a2.port, "/api/solution", {"taskId": "U1"}, p1)
            check("an unlocked solution stays unlocked", r.get("mode"), "unlocked")
            login = [e for e in a2.events() if e["kind"] == "login"][-1]
            check("the login says it resumed", login.get("resumed"), True)
        finally:
            a2.close()

        clash = subprocess.run(
            [sys.executable, str(HERE / "server.py"), "--condition", "G", "--port", "8741",
             "--salt", "test-salt", "--session", "test-A",
             "--log", str(Path(tmp) / "events_A.jsonl")],
            cwd=HERE, capture_output=True, timeout=20)
        ok("one session id cannot be restarted in another condition",
           clash.returncode != 0, clash.stdout.decode(errors="replace")[-120:])

        # ----------------------------------------------------- condition G
        print("\ncondition G (generic)")
        g = Server("G", 8732, tmp)
        try:
            cfg = json.loads(get(g.port, "/api/config")[1])
            ok("assistant is enabled", cfg["assistantEnabled"])
            ok("adaptivity is off", not cfg["adaptive"])

            p1 = g.login("p1")
            _, t = post(g.port, "/api/next", {}, p1)
            check("the same first exercise as in A", t["taskId"], first_task)

            st, r = post(g.port, "/api/ask",
                         {"taskId": t["taskId"], "prompt": "napis mi cele riesenie"}, p1)
            check("the assistant answers", st, 200)
            ok("and is NOT constrained to refuse",
               "nedám" not in r["text"], r["text"][:60])

            st, r = post(g.port, "/api/explain",
                         {"taskId": t["taskId"], "text": "neviem"}, p1)
            check("there is no self-explanation gate", r["accepted"], True)
            st, r = post(g.port, "/api/solution", {"taskId": t["taskId"]}, p1)
            check("the solution is discussed at the end of the lesson, as in K",
                  r.get("mode"), "later")

            # a pupil who copies the assistant's reply into the answer
            post(g.port, "/api/ask", {"taskId": t["taskId"], "prompt": "ako funguje binarne vyhladavanie"}, p1)
            time.sleep(1.1)
            post(g.port, "/api/attempt",
                 {"taskId": t["taskId"], "correct": True, "confidence": 90,
                  "answer": "Binárne vyhľadávanie funguje tak, že porovná stredný prvok "
                            "a podľa výsledku zahodí polovicu intervalu."}, p1)

            evs = g.events()
            kinds = {e["kind"] for e in evs}
            ok("no adaptive decisions are taken",
               "adaptive_decision" not in kinds)
            ok("prompts are still logged", "prompt" in kinds)
            att = [e for e in evs if e["kind"] == "attempt"]
            ok("a copied answer shows a high overlap with the replies",
               att and att[-1].get("assistantOverlap", 0) >= 0.6, str(att[-1:]))
            ok("and no mastery estimate is invented without an adaptive layer",
               att and att[-1].get("mastery") is None)
        finally:
            g.close()

        # ----------------------------------------------------- condition K
        print("\ncondition K (control)")
        k = Server("K", 8733, tmp)
        try:
            cfg = json.loads(get(k.port, "/api/config")[1])
            ok("assistant is disabled", not cfg["assistantEnabled"])

            p1 = k.login("p1")
            _, t = post(k.port, "/api/next", {}, p1)
            check("the same first exercise as in A and G", t["taskId"], first_task)

            st, r = post(k.port, "/api/ask",
                         {"taskId": t["taskId"], "prompt": "pomoz mi"}, p1)
            check("the server refuses, not just the UI", st, 403)

            st, _ = post(k.port, "/api/skip", {"taskId": t["taskId"]}, p1)
            check("a stuck pupil can skip honestly", st, 200)
            _, t2 = post(k.port, "/api/next", {}, p1)
            ok("and moves on to the next exercise", t2.get("taskId") != t["taskId"])

            evs = k.events()
            viol = [e for e in evs if e["kind"] == "guard_violation"]
            check("the attempt is recorded as a protocol deviation",
                  len(viol), 1)
            check("with its reason", viol[0]["reason"],
                  "assistant_requested_in_control")
            ok("no prompt was stored, because none was sent to a model",
               not any(e["kind"] == "prompt" for e in evs))
            ok("the skip is recorded", any(e["kind"] == "task_skipped" for e in evs))
        finally:
            k.close()

        # ---------------------------------------- interactive activities
        print("\ninteractive activities: identical in every condition")
        views = {}
        for cond, port in (("K", 8734), ("G", 8735), ("A", 8736)):
            srv = Server(cond, port, tmp, session=f"act-{cond}")
            try:
                st, _ = post(port, "/api/teacher/login", {"pin": "0000"})
                if cond == "K":
                    check("a wrong PIN is refused", st, 403)
                tt = srv.teacher()
                st, _ = get_json(port, "/api/teacher/state")
                if cond == "K":
                    check("the dashboard needs the PIN", st, 401)
                pu = srv.login("p1")
                st, r = post(port, "/api/teacher/activity/start", {"id": "INF-POLL-SORTED"}, teacher=tt)
                st, pulse = get_json(port, "/api/pulse", token=pu)
                st, view = get_json(port, "/api/activity", token=pu)
                views[cond] = view["activity"]
                if cond == "K":
                    check("the pupil's pulse announces the activity",
                          pulse["activity"]["id"], "INF-POLL-SORTED")
                    ok("the correct answer is not sent before the reveal",
                       "key" not in view["activity"] and "explain" not in view["activity"])
                    st, r = post(port, "/api/activity/respond",
                                 {"activityId": "INF-POLL-SORTED", "version": view["version"],
                                  "response": {"choice": 2}}, pu)
                    check("a response without the required confidence is refused", st, 400)
                    st, r = post(port, "/api/activity/respond",
                                 {"activityId": "INF-POLL-SORTED", "version": view["version"],
                                  "response": {"choice": 2, "confidence": 70}}, pu)
                    check("a complete response is accepted and scored", r["mine"]["correct"], True)
                    _, s = get_json(port, "/api/teacher/state", teacher=tt)
                    check("the teacher sees the class count", s["live"]["results"]["counts"], [0, 0, 1, 0])
                    ok("the dashboard carries no prompt text and no pupil measure",
                       "promptText" not in json.dumps(s) and "peqi" not in json.dumps(s))
                    post(port, "/api/teacher/activity/reveal", {}, teacher=tt)
                    _, view2 = get_json(port, "/api/activity", token=pu)
                    ok("after the reveal pupils see the result and the key",
                       view2.get("results", {}).get("key") == 2)
                    st, _ = post(port, "/api/activity/respond",
                                 {"activityId": "INF-POLL-SORTED", "version": view["version"],
                                  "response": {"choice": 1, "confidence": 70}}, pu)
                    check("answers cannot change after the reveal", st, 400)
                    st, r = post(port, "/api/teacher/activity/create",
                                 {"definition": {"type": "poll", "question": "Je to jasné?",
                                                 "options": ["áno", "nie"]}, "start": True}, teacher=tt)
                    ok("the teacher can add an activity during the lesson and start it",
                       st == 200 and r["live"]["id"].startswith("AD-"))
                    st, r = post(port, "/api/teacher/activity/create",
                                 {"definition": {"type": "poll", "question": "?", "options": ["jediná"]}},
                                 teacher=tt)
                    check("a malformed activity is refused at the dashboard", st, 400)
                    st, svg = get(port, "/api/teacher/qr.svg?text=http%3A%2F%2F10.0.0.5%3A5173%2F", teacher=tt)
                    ok("the join QR code is served", st == 200 and svg.startswith("<svg"))
                    st, _ = get(port, "/api/teacher/metrics", teacher=tt)
                    check("research metrics are locked during collection", st, 403)
                    kinds = {e["kind"] for e in srv.events()}
                    for kk in ("activity_started", "activity_view", "activity_response",
                               "activity_revealed", "activity_defined"):
                        ok(f"event logged: {kk}", kk in kinds)
            finally:
                srv.close()
        check("K, G and A pupils receive the identical activity",
              views["K"] == views["G"] == views["A"], True)

        # ------------------------------------- codes and pseudonyms
        print("\ncodes and pseudonyms")
        codes = linkage.issue("GY", 3, seed=5)
        cf = Path(tmp) / "codes.txt"
        cf.write_text("\n".join(codes[:2]), encoding="utf-8")
        sv = Server("A", 8737, tmp, extra=("--school", "GY", "--codes", str(cf)),
                    session="codes", log=Path(tmp) / "events_codes.jsonl")
        try:
            bad = linkage.normalise(codes[0])
            bad = bad[:3] + ("4" if bad[3] != "4" else "7") + bad[4:]
            st, r = post(sv.port, "/api/login", {"code": bad})
            check("a mistyped code is refused at the keyboard", st, 400)
            ok("with a message for the pupil", "prepíš" in r.get("error", "").lower(), r)
            st, r = post(sv.port, "/api/login", {"code": codes[2]})
            check("a valid code that is not on the class list is refused", st, 400)
            t1 = sv.login(codes[0].lower())
            t2 = sv.login(codes[0].replace("-", " "))
            ok("the same code typed two ways logs in both times", t1 and t2)
            pse = {e["pseudonym"] for e in sv.events() if e["kind"] == "login"}
            check("and is ONE pupil, not two", len(pse), 1)
            check("the lesson pseudonym equals the test pseudonym of the same pupil",
                  pse.pop(), runner.pseudonymise("test-salt", codes[0]))
        finally:
            sv.close()
        check("events and linkage agree on the canonical form of a code",
              [events.canonical_code(c) for c in ("gy-k7m4p-q", " GY K7M4P Q ", "GY—K7M4P—Q")],
              [linkage.normalise(c) for c in ("gy-k7m4p-q", " GY K7M4P Q ", "GY—K7M4P—Q")])

        consent_section(tmp)

    print(f"\n{PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
