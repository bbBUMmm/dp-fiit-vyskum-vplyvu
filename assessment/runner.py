"""runner.py -- the test, as the pupil sits in front of it.

Why the test is delivered by software at all
--------------------------------------------
Three of the measurements this study depends on cannot be made on paper, and two
of them are not optional extras:

  * PER-ITEM CONFIDENCE. The calibration measures -- bias, absolute accuracy,
    Goodman-Kruskal gamma -- need a 0-100 judgement after every item. On paper
    that is 12 extra marks per pupil per test, transcribed by hand for 330
    pupils on five occasions. It would not survive contact with a school.
  * PER-ITEM RESPONSE TIME. Test-taking effort (`effort.py`) is the only direct
    handle on the study's largest confound, and it does not exist without
    timing every item.
  * THE INTEGRITY SIGNALS. Focus loss and pasting (`integrity.py`) are observable
    only here. The fidelity checklist's V12 -- "during the test pupils had no
    access to the assistant" -- is otherwise one observer's assertion about
    twenty screens.

And one that is about not losing data: the code check (`linkage.py`) has to happen
at the keyboard, while the pupil is still in the room.

Design constraints, inherited from the exercise client and for the same reasons
------------------------------------------------------------------------------
Standard library only; it has to run on a locked-down school laptop with no
installation. No network dependency: the test is local. The log is the record --
state is in memory and every answer is appended to JSON Lines as it arrives, so
a crash costs the current item and nothing else. UTF-8 forced on the console
before anything prints, because every stem is Slovak and a narrow console would
otherwise kill the process before the lesson starts.

One thing it deliberately does NOT do: it does not tell the pupil whether an
answer was right. A test that gives feedback is a learning event, and this one
sits between two measurements of learning.

    python runner.py --bank T1_IPT --session P1 --school GY --codes codes.txt
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import linkage
from bank import load_all

HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"


class Sitting:
    """One pupil, one instrument, one occasion. Held in memory; the log is truth."""

    def __init__(self, code: str, bank_id: str, order: list[str]):
        self.code = code
        self.bank_id = bank_id
        self.order = order
        self.answers: dict[str, dict] = {}
        self.shown_at: dict[str, float] = {}
        self.token = secrets.token_urlsafe(12)
        self.started = time.time()
        self.finished = False

    def next_item(self) -> str | None:
        for i in self.order:
            if i not in self.answers:
                return i
        return None


class Store:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.sittings: dict[str, Sitting] = {}

    def append(self, obj: dict) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())      # a school laptop loses power mid-lesson


def make_handler(bank, store: Store, session: str, school: str, allowed: set[str]):

    ITEMS = {i.id: i for i in bank.items}
    ORDER = [i.id for i in bank.items]

    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):            # the server's own log is noise
            pass

        # --- plumbing ---------------------------------------------------
        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, code: int = 200) -> None:
            self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                       "application/json; charset=utf-8")

        def _body(self) -> dict:
            n = int(self.headers.get("Content-Length") or 0)
            if not n:
                return {}
            return json.loads(self.rfile.read(n).decode("utf-8"))

        def _sitting(self) -> Sitting | None:
            tok = self.headers.get("X-Sitting") or ""
            for s in store.sittings.values():
                if s.token == tok:
                    return s
            return None

        # --- routes -----------------------------------------------------
        def do_GET(self):
            if self.path in ("/", "/index.html"):
                p = STATIC / "test.html"
                return self._send(200, p.read_bytes(), "text/html; charset=utf-8")
            if self.path == "/test.js":
                p = STATIC / "test.js"
                return self._send(200, p.read_bytes(),
                                  "application/javascript; charset=utf-8")
            if self.path == "/api/info":
                return self._json(dict(title=bank.title, items=len(ORDER),
                                       session=session, school=school,
                                       jol=any(i.jol for i in bank.items)))
            return self._json({"error": "not found"}, 404)

        def do_POST(self):
            if self.path == "/api/start":
                return self._start()
            if self.path == "/api/item":
                return self._item()
            if self.path == "/api/answer":
                return self._answer()
            return self._json({"error": "not found"}, 404)

        def _start(self):
            raw = (self._body().get("code") or "").strip()
            try:
                code = linkage.verify(raw, school)
            except linkage.CodeError as e:
                # The message is the point: it is read by a fifteen-year-old who
                # has thirty seconds and one envelope.
                return self._json({"error": str(e)}, 400)

            if allowed and code not in allowed:
                return self._json({"error":
                                   "Tento kód nie je na zozname pre túto triedu. "
                                   "Zavolaj vyučujúceho."}, 400)

            prev = store.sittings.get(code)
            if prev and not prev.finished:
                # One code, one sitting. This is the layer that catches the error
                # arithmetic cannot: a pupil entering someone else's VALID code.
                if time.time() - prev.started < 2 * 3600:
                    return self._json({"error":
                                       "Tento kód je už otvorený na inom "
                                       "počítači. Ak si to ty, pokračuj tam; ak "
                                       "nie, skontroluj svoju obálku."}, 409)
            if prev and prev.finished:
                return self._json({"error":
                                   "Tento test už bol s týmto kódom dokončený."},
                                  409)

            s = Sitting(code, bank.bank_id, ORDER)
            store.sittings[code] = s
            store.append(dict(ev="start", code=code, bank=bank.bank_id,
                              session=session, t=time.time()))
            return self._json(dict(token=s.token, total=len(ORDER)))

        def _item(self):
            s = self._sitting()
            if s is None:
                return self._json({"error": "neplatná relácia"}, 401)
            nid = s.next_item()
            if nid is None:
                s.finished = True
                store.append(dict(ev="finish", code=s.code, session=session,
                                  answered=len(s.answers), t=time.time()))
                return self._json(dict(done=True, answered=len(s.answers)))
            it = ITEMS[nid]
            s.shown_at[nid] = time.time()
            return self._json(dict(
                done=False, index=len(s.answers) + 1, total=len(ORDER),
                item=dict(id=it.id, stem=it.stem, format=it.format,
                          options=it.options, jol=it.jol,
                          max_points=it.max_points,
                          rubric_hint=("Odpovedz vlastnými slovami."
                                       if it.is_open else ""))))

        def _answer(self):
            s = self._sitting()
            if s is None:
                return self._json({"error": "neplatná relácia"}, 401)
            b = self._body()
            iid = b.get("item_id")
            if iid not in ITEMS or iid in s.answers:
                return self._json({"error": "neznáma alebo už odpovedaná položka"},
                                  400)
            shown = s.shown_at.get(iid, time.time())
            rec = dict(
                ev="answer", code=s.code, session=session, bank=bank.bank_id,
                item_id=iid, raw=str(b.get("raw", "")),
                seconds=round(max(0.0, time.time() - shown), 2),
                jol=b.get("jol"),
                paste_events=int(b.get("paste_events", 0)),
                blur_seconds=round(float(b.get("blur_seconds", 0.0)), 2),
                revisions=int(b.get("revisions", 0)),
                t=time.time())
            s.answers[iid] = rec
            store.append(rec)         # written before the reply, so a crash after
            return self._json(dict(ok=True))   # the write still has the answer

    return H


def main(argv: list[str]) -> int:
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bank", required=True)
    ap.add_argument("--session", required=True)
    ap.add_argument("--school", required=True, help="two-character school code")
    ap.add_argument("--codes", default="",
                    help="file of issued codes, one per line; "
                         "without it any well-formed code is accepted")
    ap.add_argument("--log", default="")
    ap.add_argument("--port", type=int, default=5174)
    a = ap.parse_args(argv)

    banks = load_all()
    if a.bank not in banks:
        print(f"unknown bank {a.bank!r}. Available: {', '.join(sorted(banks))}")
        return 2
    bank = banks[a.bank]

    allowed: set[str] = set()
    if a.codes:
        for line in Path(a.codes).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                allowed.add(linkage.normalise(line))

    log = Path(a.log or HERE / "out" / f"responses-{a.session}-{a.bank}.jsonl")
    store = Store(log)
    handler = make_handler(bank, store, a.session, a.school.upper(), allowed)

    print(f"{bank.title}")
    print(f"  {bank.n_items} položiek, {bank.max_points} bodov, "
          f"{bank.expected_minutes:.0f} min")
    print(f"  session {a.session}, škola {a.school.upper()}, "
          f"{len(allowed) or 'ľubovoľné'} kódov")
    print(f"  log: {log}")
    print(f"  open http://127.0.0.1:{a.port}/\n")
    ThreadingHTTPServer(("127.0.0.1", a.port), handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
