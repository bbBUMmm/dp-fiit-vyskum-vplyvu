"""End-to-end test: start the real server and drive it like a pupil would.

Unit tests cover the pedagogy in isolation. This covers the thing that
isolation cannot: that the three conditions, wired together, actually behave
differently in the ways the design requires and identically in every other way.

The two claims under test are the design's, not the software's:

  * condition K refuses the assistant at the SERVER, not merely in the UI;
  * conditions G and A see the same exercises through the same interface, and
    differ only in what reaches the model and what comes back.

Run:  python test_server.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
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


def post(port, path, body):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8") or "{}")


def get(port, path):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as r:
        return r.status, r.read().decode("utf-8")


class Server:
    def __init__(self, condition, port, logdir):
        self.log = Path(logdir) / f"events_{condition}.jsonl"
        self.p = subprocess.Popen(
            [sys.executable, str(HERE / "server.py"),
             "--condition", condition, "--port", str(port),
             "--salt", "test-salt", "--provider", "stub",
             "--session", f"test-{condition}", "--log", str(self.log)],
            cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.port = port
        for _ in range(60):
            try:
                get(port, "/api/config")
                return
            except Exception:
                time.sleep(0.1)
        out, err = self.p.communicate(timeout=3)
        raise RuntimeError(f"server did not start: {err.decode(errors='replace')}")

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


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        test_starts_without_utf8_in_the_environment(tmp)

        # ----------------------------------------------------- condition A
        print("condition A (adaptive)")
        a = Server("A", 8731, tmp)
        try:
            _, cfg = 0, json.loads(get(a.port, "/api/config")[1])
            check("config reports the condition", cfg["condition"], "A")
            ok("assistant is enabled", cfg["assistantEnabled"])
            ok("adaptivity is advertised", cfg["adaptive"])

            _, t = post(a.port, "/api/next", {"student": "p1"})
            ok("a task is served", not t["done"])
            ok("a side exercise is not served first",
               t["taskId"] not in ("U1s", "U2s", "U3h", "U4s"), t["taskId"])
            first_task = t["taskId"]

            post(a.port, "/api/event",
                 {"student": "p1", "kind": "first_keystroke", "taskId": first_task})

            st, r = post(a.port, "/api/ask",
                         {"student": "p1", "taskId": first_task,
                          "prompt": "napis mi cele riesenie", "hintLevel": 2})
            check("the assistant answers", st, 200)
            ok("it refuses to hand over a solution",
               "nedám" in r["text"] or "?" in r["text"], r["text"][:60])

            st, r = post(a.port, "/api/explain",
                         {"student": "p1", "taskId": first_task, "text": "neviem"})
            check("the gate rejects a refusal", r["accepted"], False)
            ok("and says what to do instead", bool(r["reason"]))

            st, r = post(a.port, "/api/explain",
                         {"student": "p1", "taskId": first_task,
                          "text": "Myslim ze stred je 9, lebo pole ma sedem prvkov"})
            check("the gate accepts a genuine explanation", r["accepted"], True)

            # three wrong attempts on the same skill should pull in a scaffold
            for _ in range(4):
                post(a.port, "/api/attempt",
                     {"student": "p2", "taskId": "U1", "answer": "x",
                      "correct": False})
            _, t2 = post(a.port, "/api/next", {"student": "p2"})
            ok("repeated failure leads to a smaller step",
               t2.get("taskId") in ("U1s", "U1"), t2.get("taskId"))

            evs = a.events()
            kinds = {e["kind"] for e in evs}
            for k in ("task_shown", "first_keystroke", "prompt",
                      "assistant_reply", "self_explanation", "attempt",
                      "adaptive_decision"):
                ok(f"event logged: {k}", k in kinds)
            ok("no raw student code is stored",
               not any("p1" == e.get("pseudonym") for e in evs))
            ok("every event carries a pseudonym",
               all(len(e.get("pseudonym", "")) == 16 for e in evs))
            dec = [e for e in evs if e["kind"] == "adaptive_decision"]
            ok("adaptive decisions record their reason",
               all(d.get("reason") for d in dec))
        finally:
            a.close()

        # ----------------------------------------------------- condition G
        print("\ncondition G (generic)")
        g = Server("G", 8732, tmp)
        try:
            cfg = json.loads(get(g.port, "/api/config")[1])
            ok("assistant is enabled", cfg["assistantEnabled"])
            ok("adaptivity is off", not cfg["adaptive"])

            _, t = post(g.port, "/api/next", {"student": "p1"})
            check("the same first exercise as in A", t["taskId"], first_task)

            st, r = post(g.port, "/api/ask",
                         {"student": "p1", "taskId": t["taskId"],
                          "prompt": "napis mi cele riesenie"})
            check("the assistant answers", st, 200)
            ok("and is NOT constrained to refuse",
               "nedám" not in r["text"], r["text"][:60])

            st, r = post(g.port, "/api/explain",
                         {"student": "p1", "taskId": t["taskId"], "text": "neviem"})
            check("there is no self-explanation gate", r["accepted"], True)

            kinds = {e["kind"] for e in g.events()}
            ok("no adaptive decisions are taken",
               "adaptive_decision" not in kinds)
            ok("prompts are still logged", "prompt" in kinds)
        finally:
            g.close()

        # ----------------------------------------------------- condition K
        print("\ncondition K (control)")
        k = Server("K", 8733, tmp)
        try:
            cfg = json.loads(get(k.port, "/api/config")[1])
            ok("assistant is disabled", not cfg["assistantEnabled"])

            _, t = post(k.port, "/api/next", {"student": "p1"})
            check("the same first exercise as in A and G", t["taskId"], first_task)

            st, r = post(k.port, "/api/ask",
                         {"student": "p1", "taskId": t["taskId"],
                          "prompt": "pomoz mi"})
            check("the server refuses, not just the UI", st, 403)

            evs = k.events()
            viol = [e for e in evs if e["kind"] == "guard_violation"]
            check("the attempt is recorded as a protocol deviation",
                  len(viol), 1)
            check("with its reason", viol[0]["reason"],
                  "assistant_requested_in_control")
            ok("no prompt was stored, because none was sent to a model",
               not any(e["kind"] == "prompt" for e in evs))
        finally:
            k.close()

    print(f"\n{PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
