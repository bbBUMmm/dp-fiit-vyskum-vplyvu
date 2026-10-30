"""activities.py -- the interactive part of the lesson.

What it is
----------
Chapter 6 of the thesis lists the one part of the tool that was missing: the
interactive part, which "depends on the subject and the lesson". This module is
that part. The teacher launches an activity from the dashboard -- an animation
to step through, a quick check, a prediction, a hands-on simulation, a
put-in-order task, an exit ticket -- and it appears on every pupil's screen at
once. Responses come back to the dashboard aggregated, and every view, response
and interaction goes into the same event log as the rest of the lesson.

Why it does not threaten the design
-----------------------------------
The three conditions may differ only in the help available during independent
work (Appendix D). Activities belong to the parts of the lesson that are shared
by construction -- the exposition and the summary -- and nothing here reads the
condition: the definition a pupil receives, the way it is scored and the way it
is logged are identical in K, G and A. `test_activities.py` asserts exactly that.

What the activities measure
---------------------------
"Zapojenosť do materiálu počas vyučovacej hodiny" -- engagement with the
material during the lesson -- is one of the study's measures, and a response to
an activity is the most direct behavioural evidence of it that a lesson
produces: the pupil saw it, responded or did not, how fast, how accurately, and
how confident they were. `metrics.py` turns those events into participation
and accuracy per pupil.

Activities are data. A subject's activities live in `activities/<pack>.json`;
the teacher can also create one during the lesson (quick poll, prediction, exit
ticket) or paste a JSON definition. Everything passes `validate()` first, so a
malformed definition is refused at the dashboard and never reaches a pupil.
"""
from __future__ import annotations

import copy
import json
import math
import threading
import time
from pathlib import Path

TYPES = ("poll", "predict", "order", "animation", "handson", "reflect")
PHASES = ("uvod", "vyklad", "samostatna", "zhrnutie", "test", "dotaznik")
PHASE_LABELS = {"uvod": "Úvod", "vyklad": "Výklad", "samostatna": "Samostatná práca",
                "zhrnutie": "Zhrnutie", "test": "Test", "dotaznik": "Dotazník"}
WIDGETS = ("binary-search", "search-race", "guess-number", "interest",
           "circuit", "frames")
TYPE_LABELS = {"poll": "Rýchla otázka", "predict": "Predpoveď",
               "order": "Zoraď kroky", "animation": "Animácia",
               "handson": "Praktická úloha", "reflect": "Reflexia"}

MAX_TEXT = 1000          # characters of free text a pupil may submit
MAX_OPTIONS = 8
MAX_ORDER_ITEMS = 12


class ActivityError(ValueError):
    """A definition or a response that cannot be accepted. Carries a message
    fit for the person who caused it: the teacher, or the pupil's client."""


# ===========================================================================
# Definitions
# ===========================================================================
def _req(d: dict, key: str, kind, where: str):
    if key not in d:
        raise ActivityError(f"{where}: chýba pole '{key}'")
    v = d[key]
    if not isinstance(v, kind):
        raise ActivityError(f"{where}: pole '{key}' má nesprávny typ")
    return v


def validate(a: dict) -> dict:
    """Check one activity definition and return a normalised copy.

    Strict on purpose: a definition that reaches thirty screens and then fails
    to render costs the lesson the minutes it was meant to fill.
    """
    if not isinstance(a, dict):
        raise ActivityError("aktivita musí byť objekt")
    a = copy.deepcopy(a)
    aid = _req(a, "id", str, "aktivita").strip()
    where = f"aktivita {aid or '?'}"
    if not aid or len(aid) > 40 or not all(c.isalnum() or c in "-_." for c in aid):
        raise ActivityError(f"{where}: id musí mať 1–40 znakov (písmená, číslice, - _ .)")
    a["id"] = aid
    t = _req(a, "type", str, where)
    if t not in TYPES:
        raise ActivityError(f"{where}: neznámy typ '{t}' (povolené: {', '.join(TYPES)})")
    a["title"] = str(a.get("title") or TYPE_LABELS[t])[:120]
    if a.get("phase") and a["phase"] not in PHASES:
        raise ActivityError(f"{where}: neznáma fáza '{a['phase']}'")
    a["confidence"] = bool(a.get("confidence", False))

    if t in ("poll",):
        _req(a, "question", str, where)
        opts = _req(a, "options", list, where)
        if not 2 <= len(opts) <= MAX_OPTIONS or not all(isinstance(o, str) and o.strip()
                                                       for o in opts):
            raise ActivityError(f"{where}: otázka potrebuje 2–{MAX_OPTIONS} neprázdnych možností")
        if a.get("key") is not None and (not isinstance(a["key"], int)
                                         or not 0 <= a["key"] < len(opts)):
            raise ActivityError(f"{where}: 'key' musí byť index správnej možnosti")
    elif t == "predict":
        _req(a, "question", str, where)
        inp = _req(a, "input", dict, where)
        kind = inp.get("kind")
        if kind == "choice":
            opts = inp.get("options")
            if not isinstance(opts, list) or not 2 <= len(opts) <= MAX_OPTIONS:
                raise ActivityError(f"{where}: predpoveď s výberom potrebuje 2–{MAX_OPTIONS} možností")
            if a.get("answer") is not None and (not isinstance(a["answer"], int)
                                                or not 0 <= a["answer"] < len(opts)):
                raise ActivityError(f"{where}: 'answer' musí byť index možnosti")
        elif kind == "number":
            if a.get("answer") is not None and not isinstance(a["answer"], (int, float)):
                raise ActivityError(f"{where}: 'answer' musí byť číslo")
            tol = inp.get("tolerance", 0)
            if not isinstance(tol, (int, float)) or tol < 0:
                raise ActivityError(f"{where}: 'tolerance' musí byť nezáporné číslo")
        else:
            raise ActivityError(f"{where}: input.kind musí byť 'choice' alebo 'number'")
        if a.get("widget") is not None:
            _check_widget(a, where)
    elif t == "order":
        _req(a, "question", str, where)
        items = _req(a, "items", list, where)
        if not 3 <= len(items) <= MAX_ORDER_ITEMS or not all(
                isinstance(i, str) and i.strip() for i in items):
            raise ActivityError(f"{where}: zoraďovanie potrebuje 3–{MAX_ORDER_ITEMS} položiek")
        if len(set(items)) != len(items):
            raise ActivityError(f"{where}: položky na zoradenie sa nesmú opakovať")
    elif t in ("animation", "handson"):
        _check_widget(a, where)
    elif t == "reflect":
        _req(a, "question", str, where)
    return a


def _check_widget(a: dict, where: str) -> None:
    w = _req(a, "widget", str, where)
    if w not in WIDGETS:
        raise ActivityError(f"{where}: neznámy widget '{w}' (povolené: {', '.join(WIDGETS)})")
    p = a.setdefault("params", {})
    if not isinstance(p, dict):
        raise ActivityError(f"{where}: 'params' musí byť objekt")
    if w == "binary-search":
        arr = p.get("array")
        if not isinstance(arr, list) or not 2 <= len(arr) <= 32 \
                or not all(isinstance(x, (int, float)) for x in arr):
            raise ActivityError(f"{where}: binary-search potrebuje 'array' s 2–32 číslami")
        # an unsorted array in binary mode is allowed only as a declared
        # counter-example ("binary search fails here"), never by accident
        if arr != sorted(arr) and p.get("mode", "binary") == "binary" \
                and not p.get("allowUnsorted"):
            raise ActivityError(f"{where}: binárne vyhľadávanie potrebuje usporiadané pole "
                                f"(pre protipríklad nastavte allowUnsorted)")
        if not isinstance(p.get("target"), (int, float)):
            raise ActivityError(f"{where}: binary-search potrebuje 'target'")
    elif w == "frames":
        fr = p.get("frames")
        if not isinstance(fr, list) or not 1 <= len(fr) <= 40 or not all(
                isinstance(f, dict) and (f.get("text") or f.get("title")) for f in fr):
            raise ActivityError(f"{where}: frames potrebuje 1–40 snímok s 'title' alebo 'text'")
    elif w == "circuit":
        if p.get("mode", "compare") not in ("series", "parallel", "compare"):
            raise ActivityError(f"{where}: circuit.mode je series, parallel alebo compare")
        n = p.get("bulbs", 2)
        if not isinstance(n, int) or not 1 <= n <= 4:
            raise ActivityError(f"{where}: circuit.bulbs musí byť 1–4")
    elif w == "guess-number":
        mx = p.get("max", 100)
        if not isinstance(mx, int) or not 4 <= mx <= 100000:
            raise ActivityError(f"{where}: guess-number.max musí byť 4–100000")


def public_view(a: dict, revealed: bool) -> dict:
    """What a pupil's device receives. The key travels only after the reveal:
    sending it earlier would put the answer one developer-tools click away."""
    v = copy.deepcopy(a)
    v.pop("note", None)                      # the teacher's note never leaves the dashboard
    if not revealed:
        for k in ("key", "answer", "explain"):
            v.pop(k, None)
    if v["type"] == "order":
        # shuffled deterministically per definition, never in the solved order
        items = list(range(len(v["items"])))
        shuffled = _derangement(items, seed=sum(map(ord, v["id"])))
        v["display"] = shuffled
    return v


def _derangement(idx: list[int], seed: int) -> list[int]:
    out = idx[:]
    n = len(out)
    x = seed or 1
    for i in range(n - 1, 0, -1):            # Fisher-Yates with a tiny LCG
        x = (x * 1103515245 + 12345) & 0x7FFFFFFF
        j = x % (i + 1)
        out[i], out[j] = out[j], out[i]
    if out == idx:                           # never hand out the solution
        out = out[1:] + out[:1]
    return out


def load_packs(folder: str | Path) -> dict[str, dict]:
    """Every pack in `folder`, validated. A broken pack is refused with its name."""
    packs: dict[str, dict] = {}
    seen: set[str] = set()
    for p in sorted(Path(folder).glob("*.json")):
        raw = json.loads(p.read_text(encoding="utf-8"))
        name = raw.get("pack") or p.stem
        acts = []
        for a in raw.get("activities", []):
            try:
                v = validate(a)
            except ActivityError as e:
                raise ActivityError(f"{p.name}: {e}") from None
            if v["id"] in seen:
                raise ActivityError(f"{p.name}: id {v['id']} sa opakuje")
            seen.add(v["id"])
            v["pack"] = name
            acts.append(v)
        packs[name] = dict(pack=name, title=raw.get("title", name),
                           subject=raw.get("subject", ""), activities=acts)
    return packs


# ===========================================================================
# Responses
# ===========================================================================
def _num(v, lo=None, hi=None, where="hodnota"):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise ActivityError(f"{where} musí byť číslo")
    if lo is not None and v < lo or hi is not None and v > hi:
        raise ActivityError(f"{where} je mimo rozsahu")
    return v


def check_response(a: dict, r: dict) -> dict:
    """Validate a pupil's response and score it where the activity has a key.

    Returns the normalised response with `correct` (True/False/None) and, for
    ordering, `score` (share of items in the right place). Free text is kept
    as `text` here; whether it is WRITTEN to the log is the server's decision,
    because it depends on what the consent covers.
    """
    if not isinstance(r, dict):
        raise ActivityError("odpoveď musí byť objekt")
    t = a["type"]
    out: dict = {"correct": None}
    if a.get("confidence") or "confidence" in r:
        if r.get("confidence") is not None:
            out["confidence"] = int(_num(r["confidence"], 0, 100, "istota"))
        elif a.get("confidence"):
            raise ActivityError("nastav, nakoľko si si istý/á")
    if t == "poll":
        c = r.get("choice")
        if not isinstance(c, int) or isinstance(c, bool) or not 0 <= c < len(a["options"]):
            raise ActivityError("vyber jednu z možností")
        out["choice"] = c
        if a.get("key") is not None:
            out["correct"] = c == a["key"]
    elif t == "predict":
        kind = a["input"]["kind"]
        if kind == "choice":
            c = r.get("choice")
            if not isinstance(c, int) or isinstance(c, bool) \
                    or not 0 <= c < len(a["input"]["options"]):
                raise ActivityError("vyber svoju predpoveď")
            out["choice"] = c
            if a.get("answer") is not None:
                out["correct"] = c == a["answer"]
        else:
            v = _num(r.get("value"), -1e12, 1e12, "predpoveď")
            out["value"] = v
            if a.get("answer") is not None:
                tol = a["input"].get("tolerance", 0)
                out["correct"] = abs(v - a["answer"]) <= tol + 1e-9
        if r.get("text"):
            out["text"] = str(r["text"])[:MAX_TEXT]
    elif t == "order":
        order = r.get("order")
        n = len(a["items"])
        if not isinstance(order, list) or sorted(order) != list(range(n)):
            raise ActivityError("poradie musí obsahovať každú položku práve raz")
        hits = sum(1 for pos, item in enumerate(order) if pos == item)
        out["order"] = order
        out["score"] = round(hits / n, 4)
        out["correct"] = hits == n
    elif t in ("animation", "handson"):
        res = r.get("result", {})
        if not isinstance(res, dict) or len(json.dumps(res)) > 2000:
            raise ActivityError("neplatný výsledok aktivity")
        out["result"] = res
        if "correct" in res and isinstance(res["correct"], bool):
            out["correct"] = res["correct"]
        if r.get("text"):
            out["text"] = str(r["text"])[:MAX_TEXT]
    elif t == "reflect":
        text = str(r.get("text") or "").strip()
        if not text and out.get("confidence") is None:
            raise ActivityError("napíš aspoň krátku odpoveď")
        out["text"] = text[:MAX_TEXT]
    return out


# ===========================================================================
# Live state
# ===========================================================================
class Live:
    """The activity currently on the pupils' screens, and what came back.

    One activity at a time. That is a teaching decision as much as a technical
    one: two simultaneous activities split the class's attention, and the
    response rate of each would no longer mean what it says.
    """

    def __init__(self, packs: dict[str, dict]):
        self.lock = threading.RLock()
        self.library: dict[str, dict] = {}
        for p in packs.values():
            for a in p["activities"]:
                self.library[a["id"]] = a
        self.packs = packs
        self.current: dict | None = None    # {id, version, started, revealed, closed}
        self.version = 0
        self.responses: dict[str, dict] = {}     # pseudonym -> response
        self.viewers: set[str] = set()
        self.history: list[dict] = []
        self.adhoc = 0

    # --- teacher actions ---------------------------------------------------
    def add(self, definition: dict, adhoc: bool = True) -> dict:
        with self.lock:
            d = dict(definition)
            if adhoc and not d.get("id"):
                self.adhoc += 1
                while f"AD-{self.adhoc}" in self.library:
                    self.adhoc += 1
                d["id"] = f"AD-{self.adhoc}"
            v = validate(d)
            if v["id"] in self.library:
                raise ActivityError(f"aktivita s id {v['id']} už existuje")
            v["pack"] = v.get("pack") or "vlastne"
            self.library[v["id"]] = v
            return v

    def start(self, aid: str) -> dict:
        with self.lock:
            if aid not in self.library:
                raise ActivityError(f"aktivita {aid} neexistuje")
            self._archive()
            self.version += 1
            self.current = dict(id=aid, version=self.version, started=time.time(),
                                revealed=False, closed=False)
            self.responses = {}
            self.viewers = set()
            return dict(self.current)

    def reveal(self) -> dict:
        with self.lock:
            if not self.current:
                raise ActivityError("žiadna aktivita nebeží")
            self.current["revealed"] = True
            return dict(self.current)

    def close(self) -> dict | None:
        with self.lock:
            if not self.current:
                return None
            self.current["closed"] = True
            closed = dict(self.current)
            self._archive()
            self.current = None
            return closed

    def _archive(self) -> None:
        if self.current:
            self.history.append(dict(self.current, n_responses=len(self.responses),
                                     n_viewers=len(self.viewers)))

    # --- pupil side ----------------------------------------------------------
    def pulse(self) -> dict | None:
        with self.lock:
            if not self.current:
                return None
            return dict(id=self.current["id"], version=self.current["version"],
                        revealed=self.current["revealed"])

    def view_for(self, pseudonym: str) -> dict | None:
        with self.lock:
            if not self.current:
                return None
            a = self.library[self.current["id"]]
            first = pseudonym not in self.viewers
            self.viewers.add(pseudonym)
            out = dict(activity=public_view(a, self.current["revealed"]),
                       version=self.current["version"],
                       revealed=self.current["revealed"],
                       mine=self.responses.get(pseudonym),
                       first_view=first)
            if self.current["revealed"]:
                out["results"] = self.results(public=True)
            return out

    def respond(self, pseudonym: str, aid: str, version: int, r: dict) -> dict:
        with self.lock:
            if not self.current or self.current["id"] != aid \
                    or self.current["version"] != version:
                raise ActivityError("táto aktivita už skončila")
            if self.current["revealed"]:
                raise ActivityError("výsledky sú už zverejnené; odpoveď sa nedá zmeniť")
            a = self.library[aid]
            checked = check_response(a, r)
            checked["latency_ms"] = int((time.time() - self.current["started"]) * 1000)
            checked["revision"] = (self.responses.get(pseudonym, {}).get("revision", 0) + 1
                                   if pseudonym in self.responses else 0)
            self.responses[pseudonym] = checked
            return checked

    # --- aggregation ---------------------------------------------------------
    def results(self, public: bool = False) -> dict:
        """Class-level only. There is no per-pupil row here and no way to ask
        for one: the dashboard is a teaching tool, not a register."""
        with self.lock:
            if not self.current:
                return {}
            a = self.library[self.current["id"]]
            return aggregate(a, list(self.responses.values()), len(self.viewers),
                             include_text=not public)


def aggregate(a: dict, responses: list[dict], n_viewers: int,
              include_text: bool = True) -> dict:
    t = a["type"]
    n = len(responses)
    out: dict = dict(type=t, n=n, viewers=n_viewers)
    conf = [r["confidence"] for r in responses if r.get("confidence") is not None]
    if conf:
        out["confidence_mean"] = round(sum(conf) / len(conf), 1)
    keyed = [r["correct"] for r in responses if r.get("correct") is not None]
    if keyed:
        out["correct_share"] = round(sum(1 for c in keyed if c) / len(keyed), 3)
    if t == "poll" or (t == "predict" and a["input"]["kind"] == "choice"):
        opts = a["options"] if t == "poll" else a["input"]["options"]
        counts = [0] * len(opts)
        for r in responses:
            counts[r["choice"]] += 1
        out["options"] = opts
        out["counts"] = counts
    elif t == "predict":
        vals = sorted(r["value"] for r in responses)
        if vals:
            out["median"] = vals[len(vals) // 2] if len(vals) % 2 else \
                (vals[len(vals) // 2 - 1] + vals[len(vals) // 2]) / 2
            out["min"], out["max"] = vals[0], vals[-1]
            out["values"] = vals
    elif t == "order":
        sc = [r["score"] for r in responses]
        if sc:
            out["score_mean"] = round(sum(sc) / len(sc), 3)
        out["items"] = a["items"]
    elif t in ("animation", "handson"):
        out["completed"] = sum(1 for r in responses if r.get("result", {}).get("completed"))
        nums = [r["result"].get("value") for r in responses
                if isinstance(r.get("result", {}).get("value"), (int, float))]
        if nums:
            nums.sort()
            out["value_median"] = nums[len(nums) // 2]
            out["values"] = nums
    if include_text:
        texts = [r["text"] for r in responses if r.get("text")]
        # shuffled so the order of arrival cannot point at a pupil
        texts.sort(key=lambda s: hash(("anon", s)) & 0xffff)
        out["texts"] = texts
    if a.get("key") is not None:
        out["key"] = a["key"]
    if a.get("answer") is not None:
        out["answer"] = a["answer"]
    if a.get("explain"):
        out["explain"] = a["explain"]
    return out
