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
installation. No network dependency: the test is local -- or served to the class
from one machine with --host 0.0.0.0. The log is the record -- every answer is
appended to JSON Lines and synced as it arrives, and on a restart the sittings
are rebuilt from the log, so a crash costs nothing and the pupil continues at
the item they were on. UTF-8 forced on the console before anything prints.

The log carries the PSEUDONYM -- the code hashed with the school's salt, exactly
as the lesson log does -- and never the code itself. The first version wrote the
raw code, which (a) left the lesson log and the test log of one pupil joinable
only by someone holding the salt, i.e. never by the researcher, and (b) failed
the analysis contract, which requires 16 hex characters in `pseudonym`.

One thing it deliberately does NOT do: it does not tell the pupil whether an
answer was right. A test that gives feedback is a learning event, and this one
sits between two measurements of learning.

Consent (`consent.py`, the lesson's `static/consent.js`): after the code the
pupil is asked on screen, and nothing of the sitting is written until they say
yes. A pupil who says no takes the same test; the sitting lives in memory only.
A withdrawal deletes the sitting's records at once and leaves a marker. With
--consent-list, codes without a signed paper consent are never recorded.

The test section (--test). The topic tests T1, T3, T4 and their questionnaires
are read from the plain-text files in testy/ (`testy.py`), the same files the
supervisor and the commission read and the teacher prints for the paper backup.
One sitting = questionnaire before -> self-efficacy -> the test -> questionnaire
after. Nothing here talks to a model or adapts to the pupil: every pupil gets the
same items in the same order. The runner imports neither providers.py nor
pedagogy.py, and the assistant cannot be reached from this page.

    python runner.py --bank T1_IPT --session P1 --school GY --codes kody-GY.txt --salt <salt>
    python runner.py --bank POST_LESSON --condition K ...   (skips the assistant items)
    python runner.py --test F1-T3 --condition G --session 2A-F1-T3 --school GY --salt <salt>
    python runner.py --test vyber ...          (menu of all tests in the console)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import consent
import linkage
from bank import load_all

HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"
# The consent screen is one file for the lesson and the test; it lives with the
# lesson app -- in the repository and in the school kit.
CONSENT_JS = next((p for p in (STATIC / "consent.js",
                               HERE.parent / "exercise-client" / "static" / "consent.js",
                               HERE.parent / "client" / "static" / "consent.js")
                   if p.is_file()), None)
MAX_BODY = 64 * 1024
TAKEOVER_AFTER_S = 120      # an abandoned sitting may be resumed on another machine
LOCK_HOURS = 2


def pseudonymise(salt: str, code: str) -> str:
    """sha256(salt | canonical code), 16 hex -- identical to the lesson log."""
    return hashlib.sha256((salt + "|" + linkage.normalise(code)).encode("utf-8")).hexdigest()[:16]


class Sitting:
    """One pupil, one instrument, one occasion. Held in memory; the log is truth."""

    def __init__(self, pseudonym: str, bank_id: str, order: list[str]):
        self.pseudonym = pseudonym
        self.bank_id = bank_id
        self.order = order
        self.answers: dict[str, dict] = {}
        self.shown_at: dict[str, float] = {}
        self.token = secrets.token_urlsafe(18)
        self.started = time.time()
        self.last_seen = time.time()
        self.finished = False
        self.consent = consent.PENDING
        self.start_rec: dict | None = None    # written when the pupil says yes
        self.lock = threading.RLock()

    def next_item(self) -> str | None:
        for i in self.order:
            if i not in self.answers:
                return i
        return None


class Store:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.sittings: dict[str, Sitting] = {}      # pseudonym -> sitting
        self.lock = threading.RLock()

    def append(self, obj: dict) -> None:
        obj = {"timestamp": datetime.now(timezone.utc).isoformat(), **obj}
        with self.lock:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
                f.flush()
                os.fsync(f.fileno())      # a school laptop loses power mid-lesson

    def purge(self, pseudonym: str, session: str, bank_id: str) -> bool:
        """Delete one pupil's records of this sitting, except the withdrawal
        marker -- the pupil withdrew consent. Temporary file swapped in under the
        store's lock; False if the swap fails (the data check deletes the rest)."""
        with self.lock:
            if not self.path.exists():
                return True
            kept = []
            for line in self.path.read_text(encoding="utf-8", errors="replace").splitlines():
                try:
                    r = json.loads(line)
                except ValueError:
                    kept.append(line)
                    continue
                if (r.get("pseudonym") == pseudonym and r.get("session") == session
                        and r.get("bank") == bank_id and r.get("ev") != "withdraw"):
                    continue
                kept.append(line)
            tmp = self.path.with_name(self.path.name + ".tmp")
            try:
                with tmp.open("w", encoding="utf-8") as f:
                    f.write("".join(x + "\n" for x in kept))
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp, self.path)
            except OSError:
                try:
                    tmp.unlink()
                except OSError:
                    pass
                return False
            return True

    def replay(self, session: str, bank_id: str, order: list[str]) -> int:
        """Rebuild the sittings of this session and bank from the log."""
        if not self.path.exists():
            return 0
        n = 0
        said: dict[str, str] = {}      # consent seen before the sitting's start record
        for line in self.path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("session") != session or r.get("bank") != bank_id:
                continue
            p = r.get("pseudonym")
            if not p:
                continue
            s = self.sittings.get(p)
            if r.get("ev") in ("consent", "withdraw"):
                said[p] = consent.YES if r["ev"] == "consent" else consent.NO
                if s is not None:
                    s.consent = said[p]
            elif r.get("ev") in ("start", "resume") and s is None:
                s = Sitting(p, bank_id, [i for i in r.get("order", order) if i in order] or order)
                s.started = float(r.get("t", time.time()))
                s.last_seen = 0.0                      # resumable at once after a restart
                # a sitting already in the log was recorded with a yes; logs from
                # before the consent screen have no consent record at all
                s.consent = said.get(p, consent.YES)
                s.start_rec = {k: v for k, v in r.items() if k != "timestamp"}
                self.sittings[p] = s
            elif r.get("ev") == "answer" and s is not None:
                s.answers[r["item_id"]] = r
            elif r.get("ev") == "finish" and s is not None:
                s.finished = True
            n += 1
        return n


def _public(it) -> dict:
    """What the browser may know about an item of the test section. Never the key:
    a semi-open field travels with its label and unit, not with its answer."""
    if not getattr(it, "part_meta", None):
        return {}
    return dict(
        kind=it.kind, part=it.part_meta, skip=True,
        scale=it.scale or None,
        fields=[dict(label=f.get("label", ""), unit=f.get("unit", ""), kind=f.get("kind"))
                for f in it.fields] or None,
        stimulus=it.stimulus or None)


def _check_answer(it, raw: str) -> str | None:
    """A message for the pupil if the answer cannot be stored as given (test
    section only); None when it is fine. "?" is an explicit "I don't know"."""
    if raw.strip() == "?":
        return None
    fmt = it.format
    if fmt in ("mr", "choice", "multi"):
        try:
            picked = [int(x) for x in raw.split(",") if x.strip()]
        except ValueError:
            return "Neplatná voľba."
        if not picked or any(not 0 <= p < len(it.options) for p in picked):
            return "Neplatná voľba."
        if fmt == "choice" and len(picked) != 1:
            return "Vyber jednu možnosť."
    elif fmt in ("scale", "number"):
        try:
            v = int(raw.strip())
        except ValueError:
            return "Zadaj celé číslo."
        lo, hi, step = it.scale.get("min", 0), it.scale.get("max", 0), it.scale.get("step", 1)
        if not lo <= v <= hi or (v - lo) % step:
            return f"Zadaj číslo od {lo} do {hi}."
    elif fmt == "short":
        try:
            vals = json.loads(raw)
        except ValueError:
            return "Odpoveď sa nepodarilo prečítať."
        if (not isinstance(vals, list) or len(vals) != len(it.fields)
                or not all(isinstance(v, str) for v in vals)):
            return "Odpoveď sa nepodarilo prečítať."
        if not any(v.strip() for v in vals):
            return "Vyplň aspoň jedno políčko, alebo zvoľ „Neviem“."
    return None


def make_handler(bank, store: Store, session: str, school: str, allowed: set[str],
                 salt: str, condition: str | None, host: str, port: int,
                 paper: set[str] | None = None, form_info: dict | None = None):
    """`paper`: pseudonyms whose signed consent the school listed; None = no list.
    `form_info`: set in the test section (--test): what the page shows about the
    test -- subject, topic, conventions."""

    ITEMS = {i.id: i for i in bank.items}
    ORDER = [i.id for i in bank.items if i.applies_to(condition)]
    VERSION = consent.view("test", consent.PENDING)["version"]

    def record(s: Sitting, obj: dict) -> None:
        """The consent gate: a sitting is written only after the pupil's yes."""
        if s.consent == consent.YES:
            store.append(obj)

    def view(s: Sitting) -> dict:
        return consent.view("test", s.consent)

    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        timeout = 30

        def log_message(self, *a):            # the server's own log is noise
            pass

        # --- plumbing ---------------------------------------------------
        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Content-Security-Policy",
                             "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
                             "script-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, code: int = 200) -> None:
            self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                       "application/json; charset=utf-8")

        def _read_raw(self) -> None:
            # Consumed BEFORE dispatch. With keep-alive, an endpoint that
            # ignored its "{}" body (/api/item did) left two bytes in the socket
            # and the browser's NEXT request -- the pupil's answer -- was parsed
            # as "{}POST /api/answer" and refused with a 501.
            self._raw, self._bad = b"", None
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                self.close_connection, self._bad = True, "neplatná dĺžka požiadavky"
                return
            if n > MAX_BODY:
                self.close_connection, self._bad = True, "požiadavka je príliš veľká"
                return
            if n:
                self._raw = self.rfile.read(n)

        def _body(self) -> dict:
            if self._bad:
                raise ValueError(self._bad)
            if not self._raw:
                return {}
            data = json.loads(self._raw.decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("očakáva sa objekt JSON")
            return data

        def _sitting(self) -> Sitting | None:
            tok = self.headers.get("X-Sitting") or ""
            with store.lock:
                for s in store.sittings.values():
                    if tok and secrets.compare_digest(s.token, tok):
                        s.last_seen = time.time()
                        return s
            return None

        # --- routes -----------------------------------------------------
        def do_GET(self):
            path = urlsplit(self.path).path
            try:
                if path in ("/", "/index.html"):
                    return self._send(200, (STATIC / "test.html").read_bytes(),
                                      "text/html; charset=utf-8")
                if path == "/test.js":
                    return self._send(200, (STATIC / "test.js").read_bytes(),
                                      "application/javascript; charset=utf-8")
                if path == "/consent.js" and CONSENT_JS:
                    return self._send(200, CONSENT_JS.read_bytes(),
                                      "application/javascript; charset=utf-8")
                if path == "/api/info":
                    info = dict(
                        title=bank.title, items=len(ORDER), session=session,
                        school=school, condition=condition,
                        jol=any(ITEMS[i].jol for i in ORDER),
                        minutes=bank.minutes,
                        codeFormat=f"{school}-XXXXX-X")
                    if form_info:
                        # the condition is not shown: the page looks the same
                        # in K, G and A
                        info.update(section="testy", form=form_info, condition=None)
                    return self._json(info)
                return self._json({"error": "not found"}, 404)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_POST(self):
            self._read_raw()
            path = urlsplit(self.path).path
            route = {"/api/start": self._start, "/api/item": self._item,
                     "/api/answer": self._answer, "/api/ping": self._ping,
                     "/api/consent": self._consent}.get(path)
            if route is None:
                return self._json({"error": "not found"}, 404)
            try:
                route()
            except ValueError as e:                  # bad JSON, bad numbers
                self._json({"error": f"neplatná požiadavka: {e}"}, 400)
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception as e:                   # never a silent dead socket
                traceback.print_exc()
                self._json({"error": type(e).__name__}, 500)

        def _start(self):
            raw = str(self._body().get("code") or "").strip()
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

            p = pseudonymise(salt, code)
            with store.lock:
                prev = store.sittings.get(p)
                if prev and prev.finished:
                    return self._json({"error":
                                       "Tento test už bol s týmto kódom dokončený."}, 409)
                if prev and not prev.finished:
                    idle = time.time() - prev.last_seen
                    if idle < TAKEOVER_AFTER_S and time.time() - prev.started < LOCK_HOURS * 3600:
                        # One code, one sitting. This is the layer that catches the
                        # error arithmetic cannot: a pupil entering someone else's
                        # VALID code -- while that pupil is still working.
                        return self._json({"error":
                                           "Tento kód je už otvorený na inom "
                                           "počítači. Ak si to ty, pokračuj tam; ak "
                                           "nie, skontroluj svoju obálku."}, 409)
                    # an abandoned sitting (crashed laptop, restarted server):
                    # continue it here, with every answer already given kept
                    prev.token = secrets.token_urlsafe(18)
                    prev.last_seen = time.time()
                    record(prev, dict(ev="resume", pseudonym=p, bank=bank.bank_id,
                                      session=session, answered=len(prev.answers),
                                      order=prev.order, t=time.time()))
                    return self._json(dict(token=prev.token, total=len(prev.order),
                                           answered=len(prev.answers), resumed=True,
                                           consent=view(prev)))
                s = Sitting(p, bank.bank_id, ORDER)
                if paper is not None and p not in paper:
                    s.consent = consent.NONE
                # held until the pupil says yes (`_consent`); nothing yet on disk
                s.start_rec = dict(ev="start", pseudonym=p, bank=bank.bank_id,
                                   instrument=bank.instrument, session=session,
                                   condition=condition, order=ORDER, t=time.time())
                store.sittings[p] = s
            return self._json(dict(token=s.token, total=len(ORDER), answered=0,
                                   resumed=False, consent=view(s)))

        def _consent(self):
            """Read (no `choice`) or change the pupil's consent for this sitting.

            yes -> the consent record, the held-back start, and every answer
                   given so far; from then on everything is written.
            no  -> nothing is written. After a yes it is a withdrawal: the marker
                   is written and the sitting's other records are deleted at once.
            """
            s = self._sitting()
            if s is None:
                return self._json({"error": "neplatná relácia"}, 401)
            choice = self._body().get("choice")
            purged = None
            with s.lock:
                if choice is not None:
                    try:
                        new, action = consent.transition(s.consent, choice)
                    except consent.ConsentError as e:
                        return self._json({"error": str(e)}, e.status)
                    s.consent = new
                    base = dict(pseudonym=s.pseudonym, session=session, bank=bank.bank_id,
                                version=VERSION, t=time.time())
                    if action == consent.START:
                        record(s, dict(ev="consent", paper_list=paper is not None, **base))
                        record(s, s.start_rec or dict(ev="start", pseudonym=s.pseudonym,
                                                      bank=bank.bank_id, session=session,
                                                      order=s.order, t=time.time()))
                        for iid in s.order:
                            if iid in s.answers:
                                record(s, s.answers[iid])
                        if s.finished:
                            record(s, dict(ev="finish", pseudonym=s.pseudonym,
                                           session=session, bank=bank.bank_id,
                                           answered=len(s.answers), t=time.time()))
                    elif action == consent.WITHDRAW:
                        store.append(dict(ev="withdraw", **base))
                        purged = store.purge(s.pseudonym, session, bank.bank_id)
                out = view(s)
            if purged is not None:
                out["purged"] = purged
            return self._json(out)

        def _ping(self):
            s = self._sitting()
            return self._json({"ok": s is not None}, 200 if s else 401)

        def _item(self):
            s = self._sitting()
            if s is None:
                return self._json({"error": "neplatná relácia"}, 401)
            if s.consent == consent.PENDING:
                return self._json({"error": "Najprv sa rozhodni, či súhlasíš so záznamom."}, 403)
            with s.lock:
                nid = s.next_item()
                if nid is None:
                    if not s.finished:
                        s.finished = True
                        record(s, dict(ev="finish", pseudonym=s.pseudonym,
                                       session=session, bank=bank.bank_id,
                                       answered=len(s.answers), t=time.time()))
                    return self._json(dict(done=True, answered=len(s.answers)))
                it = ITEMS[nid]
                s.shown_at.setdefault(nid, time.time())
                return self._json(dict(
                    done=False, index=len(s.answers) + 1, total=len(s.order),
                    item=dict(id=it.id, stem=it.stem, format=it.format,
                              options=it.options, jol=it.jol,
                              max_points=it.max_points,
                              rubric_hint=("Odpovedz vlastnými slovami."
                                           if it.is_open else ""),
                              **_public(it))))

        def _answer(self):
            s = self._sitting()
            if s is None:
                return self._json({"error": "neplatná relácia"}, 401)
            if s.consent == consent.PENDING:
                return self._json({"error": "Najprv sa rozhodni, či súhlasíš so záznamom."}, 403)
            b = self._body()
            iid = b.get("item_id")
            with s.lock:
                # only the item that is on the screen may be answered: anything
                # else is a stale tab or a forged request, and both would put a
                # response time of zero into the effort analysis
                if iid != s.next_item():
                    return self._json({"error": "táto položka nie je na rade"}, 400)
                it = ITEMS[iid]
                raw = str(b.get("raw", ""))[:8000]
                if not raw.strip():
                    return self._json({"error": "prázdna odpoveď"}, 400)
                # the test section: "?" is an explicit "I don't know" (scored 0,
                # never a guess), and every answer is checked against its format
                skip = form_info is not None and raw.strip() == "?"
                if form_info is not None:
                    msg = _check_answer(it, raw)
                    if msg:
                        return self._json({"error": msg}, 400)
                jol = b.get("jol")
                if jol is not None:
                    jol = int(jol)
                    if not 0 <= jol <= 100:
                        raise ValueError("istota musí byť 0 až 100")
                if it.jol and jol is None and not skip:
                    return self._json({"error": "Nastav, nakoľko si si istý/á."}, 400)
                if not it.jol or skip:
                    jol = None                         # never on a questionnaire
                shown = s.shown_at.get(iid, time.time())
                rec = dict(
                    ev="answer", pseudonym=s.pseudonym, session=session,
                    bank=bank.bank_id, instrument=bank.instrument,
                    condition=condition, item_id=iid, raw=raw,
                    seconds=round(max(0.0, time.time() - shown), 2),
                    jol=jol,
                    paste_events=max(0, int(b.get("paste_events", 0))),
                    blur_seconds=round(max(0.0, float(b.get("blur_seconds", 0.0))), 2),
                    revisions=max(0, int(b.get("revisions", 0))),
                    t=time.time())
                record(s, rec)        # written before the reply, so a crash after
                s.answers[iid] = rec  # the write still has the answer
            return self._json(dict(ok=True))

    return H


def _choose_test(cat: dict) -> str:
    """The console menu of the test section: subject, topic, form."""
    import testy
    rows = testy.menu_rows(cat)
    print("\nSEKCIA TESTY -- ktorý test alebo dotazník spustiť?")
    last = None
    for i, f in enumerate(rows, 1):
        group = f.subject if f.is_test else "dotazníky (samostatne)"
        if group != last:
            print(f"\n  {group.upper()}")
            last = group
        what = {"T1": "vstupný test (pred hodinou)", "T3": "test hneď po hodine",
                "T4": "odložený test (po 3 týždňoch)"}.get(f.test, f.title_lines[0].title())
        print(f"   {i:2}  {f.id:6} {f.topic_title if f.is_test else ''}  -- {what}")
    while True:
        try:
            pick = input("\nČíslo: ").strip()
        except EOFError:
            return ""
        if pick.isdigit() and 1 <= int(pick) <= len(rows):
            return rows[int(pick) - 1].id
        print("neplatná voľba")


def _ask_condition() -> str | None:
    """Ask for the lesson's condition when a questionnaire depends on it."""
    try:
        c = input("Podmienka hodiny, po ktorej sa test píše (K, G alebo A): ").strip().upper()
    except EOFError:
        return None
    return c if c in ("K", "G", "A") else None


class Server(ThreadingHTTPServer):
    # http.server asks for SO_REUSEADDR, and on Windows that lets a second runner
    # bind a port an older runner still holds. The new window starts, the browser
    # keeps reaching the old one, and a pupil who finished T1 is told in T3 that
    # the test is already finished. One port, one runner: the bind must fail.
    allow_reuse_address = os.name != "nt"


def main(argv: list[str]) -> int:
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bank", default="", help="an instrument from banks/*.json")
    ap.add_argument("--test", default="",
                    help="the test section: a form from testy/ (e.g. F1-T3, D0), or "
                         "'vyber' for a menu in the console")
    ap.add_argument("--session", required=True)
    ap.add_argument("--school", required=True, help="two-character school code")
    ap.add_argument("--salt", default=os.environ.get("STUDY_SALT", ""),
                    help="the school's pseudonym salt, the same as for the lesson")
    ap.add_argument("--condition", choices=["K", "G", "A"], default=None,
                    help="the class's condition; skips items that do not apply "
                         "(the assistant items of the post-lesson questionnaire in K)")
    ap.add_argument("--codes", default="",
                    help="file of issued codes, one per line; "
                         "without it any well-formed code is accepted")
    ap.add_argument("--consent-list", default="",
                    help="file of codes with a signed paper consent (guardian AND "
                         "pupil); other codes are never recorded. Without it the "
                         "consent on screen is the only gate")
    ap.add_argument("--log", default="")
    ap.add_argument("--log-dir", default="",
                    help="directory for the log; the file is named "
                         "odpovede_<session>_<test>.jsonl")
    ap.add_argument("--host", default="127.0.0.1",
                    help="0.0.0.0 = the whole class connects over the school network")
    ap.add_argument("--port", type=int, default=5174)
    a = ap.parse_args(argv)

    if not a.salt:
        print("refusing to start: --salt (or STUDY_SALT) is required -- the same "
              "salt the school uses for the lesson, so the two logs join.")
        return 2

    if bool(a.bank) == bool(a.test):
        print("zadaj práve jedno: --test (sekcia testov, testy/*.txt) alebo --bank "
              "(nástroj z banks/*.json)")
        return 2
    form_info = None
    if a.test:
        import testy                       # only the test section needs it
        try:
            cat = testy.load_catalog()
        except testy.TestError as e:
            print(f"testy sa nedajú načítať:\n{e}")
            return 2
        fid = _choose_test(cat) if a.test.lower() in ("vyber", "?", "menu") else a.test
        if fid not in cat:
            print(f"neznámy test {fid!r}. Existujú: {', '.join(sorted(cat))}")
            return 2
        form = cat[fid]
        if not a.condition and any(i.conditions for i in testy.compose(fid, cat).items):
            a.condition = _ask_condition()
            if not a.condition:
                print(f"{fid} má otázky, ktoré závisia od podmienky hodiny; zadaj "
                      f"--condition K|G|A")
                return 2
        bank = testy.compose(fid, cat, a.condition)
        form_info = dict(id=form.id, test=form.test, subject=form.subject,
                         topic=form.topic, topicTitle=form.topic_title,
                         titleLines=form.title_lines, conventions=form.conventions,
                         instructions=form.instructions, points=form.max_points,
                         minutes=bank.minutes)
    else:
        banks = load_all()
        if a.bank not in banks:
            print(f"unknown bank {a.bank!r}. Available: {', '.join(sorted(banks))}")
            return 2
        bank = banks[a.bank]
        if any(i.conditions for i in bank.items) and not a.condition:
            print(f"{a.bank} has items that depend on the condition; pass --condition K|G|A")
            return 2

    if CONSENT_JS is None:
        print("refusing to start: the consent screen (consent.js) is missing -- it "
              "belongs next to the lesson app, exercise-client/static or client/static.")
        return 2

    allowed: set[str] = set()
    if a.codes:
        for line in Path(a.codes).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                allowed.add(linkage.normalise(line))
    paper = ({pseudonymise(a.salt, c) for c in consent.read_list(a.consent_list)}
             if a.consent_list else None)

    if a.log:
        log = Path(a.log)
    elif a.log_dir:
        log = Path(a.log_dir) / f"odpovede_{a.session}_{bank.bank_id}.jsonl"
    else:
        log = HERE / "out" / f"responses-{a.session}-{bank.bank_id}.jsonl"
    store = Store(log)
    order = [i.id for i in bank.items if i.applies_to(a.condition)]
    replayed = store.replay(a.session, bank.bank_id, order)
    if paper is not None:              # a consent the school has since withdrawn
        for p, s in store.sittings.items():
            if p not in paper:
                s.consent = consent.NONE
    handler = make_handler(bank, store, a.session, a.school.upper(), allowed,
                           a.salt, a.condition, a.host, a.port, paper, form_info)
    try:
        httpd = Server((a.host, a.port), handler)
    except OSError as e:
        print(f"CHYBA: port {a.port} už používa iné okno (iný test alebo hodina).\n"
              f"Zatvorte to okno (Ctrl+C) a spustite tento test znova.  [{e}]")
        return 2
    httpd.daemon_threads = True

    if form_info:
        print("SEKCIA TESTY -- bez asistenta a bez prispôsobovania, pre všetkých rovnako")
    print(f"{bank.title}")
    points = form_info["points"] if form_info else bank.max_points
    print(f"  {len(order)} položiek, {points} bodov, "
          f"{bank.expected_minutes:.0f} min"
          + (f", podmienka {a.condition}" if a.condition else ""))
    print(f"  session {a.session}, škola {a.school.upper()}, "
          f"{len(allowed) or 'ľubovoľné'} kódov")
    if replayed:
        print(f"  obnovené zo záznamu: {len(store.sittings)} rozpracovaných testov")
    if paper is None:
        print("  SÚHLASY: zoznam podpísaných súhlasov nie je zadaný -- zaznamenáva sa\n"
              "           len podľa voľby žiaka na obrazovke (--consent-list).")
    else:
        print(f"  súhlasy: {len(paper)} kódov s podpísaným súhlasom; ostatné sa nezaznamenávajú")
    print(f"  log: {log}")
    host_shown = "127.0.0.1" if a.host in ("0.0.0.0", "") else a.host
    print(f"  open http://{host_shown}:{a.port}/"
          + ("   (celá trieda: adresa tohto počítača v sieti)" if a.host in ("0.0.0.0", "") else ""))
    print(flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
