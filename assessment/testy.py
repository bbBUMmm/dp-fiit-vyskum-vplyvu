"""testy.py -- the topic tests (T1, T3, T4) and the questionnaires (D0-D4), read
from the plain-text files in testy/.

Why the tests are plain text and still the only copy
----------------------------------------------------
The tests are written for people first: the supervisor, the commission, the
teacher who prints the paper backup. So they are plain .txt files, one per test,
readable without any tool. And they are also what the pupil sees on screen: the
runner reads these files directly. There is no second copy to drift:

    testy/*.txt  ->  runner.py --test     the test section of the app
                 ->  scoring.py           points (closed and semi-open items)
                 ->  testy.py --tlac      the pupil's paper sheet, without the key
                 ->  testy.py             the checks below

A file the parser cannot read is refused with the file and line; a test that
breaks a rule of its own specification is refused with the rule.

What is checked, and why each check exists (`python testy.py`)
---------------------------------------------------------------
  * every closed item has five options a-e, a key, and a diagnosis for every
    wrong option -- a distractor without a diagnosis is a wrong answer we learn
    nothing from;
  * hidden multiplicity: in T1/T3 exactly 4 of 10 closed items have more than one
    correct answer (2 or 3), the others exactly one; nothing on the page says
    which (the supervisor's note);
  * the blueprint: cognitive level per position, points per part;
  * T1 and T3 are twins: the same level, skill and multiplicity on every position;
  * T3 and T4 share six anchor items, character for character, on the same
    positions -- they put the two forms on one scale;
  * the self-efficacy items (part P) are identical in T1, T3 and T4 of a topic,
    because they are a repeated measure;
  * semi-open keys parse, rubrics add up, scales parse, the time budget is stated.

Standard library only. Run:
    python testy.py                    check every test, print the overview
    python testy.py --tlac F1-T3       the pupil's sheet (no key) to stdout
    python testy.py --zoznam           list of tests, as the runner offers them
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

from bank import Bank, Item

HERE = Path(__file__).resolve().parent
# repository: ../testy ; school kit: test/testy
ROOTS = (HERE / "testy", HERE.parent / "testy")

LEVELS = ("zapamätanie", "porozumenie", "aplikácia", "analýza", "hodnotenie", "tvorenie")
HIGHER = ("analýza", "hodnotenie", "tvorenie")

# One blueprint for all seven topics. Position -> cognitive level.
BLUEPRINT = {
    "T13": {
        "A": ["zapamätanie", "porozumenie", "porozumenie", "porozumenie", "aplikácia",
              "aplikácia", "aplikácia", "analýza", "analýza", "hodnotenie"],
        "B": ["porozumenie", "aplikácia", "aplikácia", "aplikácia", "analýza", "analýza"],
        "C": ["aplikácia", "analýza", "analýza", "hodnotenie", "hodnotenie", "tvorenie"],
    },
    "T4": {
        "A": ["zapamätanie", "porozumenie", "porozumenie", "porozumenie", "aplikácia",
              "aplikácia", "aplikácia", "analýza", "analýza", "analýza", "hodnotenie",
              "hodnotenie"],
        "B": ["porozumenie", "aplikácia", "aplikácia", "aplikácia", "analýza", "analýza",
              "analýza", "aplikácia"],
        "C": ["aplikácia", "analýza", "analýza", "hodnotenie", "hodnotenie", "tvorenie"],
        "D": ["porozumenie", "analýza", "aplikácia", "analýza", "hodnotenie", "tvorenie"],
    },
}
ANCHOR_POSITIONS = ("A1", "A3", "A4", "A5", "A6", "A9")
MULTI_PER_T13 = 4
POINTS = {"closed": 2, "semi": 2}          # open items: from the rubric

# Expected seconds per item, for the time budget (a pilot replaces these).
SECONDS = {"closed": 75, "semi": 95, "open": 190, "psych": 11, "number": 20, "text": 45}
READING_SEC = 300                          # the T4 text, read once

SUBJECTS = {                               # Slovak forms for the questionnaires
    "fyzika": dict(nom="fyzika", gen="fyziky", loc="fyzike", acc="fyziku"),
    "matematika": dict(nom="matematika", gen="matematiky", loc="matematike", acc="matematiku"),
    "informatika": dict(nom="informatika", gen="informatiky", loc="informatike", acc="informatiku"),
}

PART_KIND = {"P": "psych", "Q": "psych", "Z": "psych", "A": "closed", "B": "semi",
             "C": "open", "D": "text"}

CUT = "ČASŤ PRE HODNOTITEĽA"
LETTERS = "abcdefgh"


class TestError(ValueError):
    """A test file that cannot be trusted. Carries file and line."""


# ===========================================================================
@dataclass
class FormItem(Item):
    part: str = ""
    kind: str = ""                  # closed | semi | open | psych
    fields: list = field(default_factory=list)      # semi-open: label, unit, answer
    scale: dict = field(default_factory=dict)       # psych scale: min, max, step, left, right
    stimulus: dict = field(default_factory=dict)    # part D: title, text
    twin: str = ""
    line: int = 0
    diagnosis_keys: dict = field(default_factory=dict)  # notes on correct options
    examples: list = field(default_factory=list)
    part_meta: dict = field(default_factory=dict)   # set by compose(): title, instructions

    @property
    def n_keys(self) -> int:
        return len(self.key) if isinstance(self.key, list) else 0


@dataclass
class Part:
    id: str
    title: str
    instructions: str
    kind: str
    stimulus: dict = field(default_factory=dict)


@dataclass
class Form:
    id: str
    path: Path
    head: dict
    title_lines: list
    subject: str
    topic: str
    test: str                       # T1 | T3 | T4 | D0 | D1 | D3 | D4
    instructions: str
    conventions: str
    parts: list
    items: list
    skills: dict
    pupil_text: str                 # everything above the cut, as printed
    subscales: dict = field(default_factory=dict)   # questionnaires: name -> item ids

    @property
    def is_test(self) -> bool:
        return self.test in ("T1", "T3", "T4")

    @property
    def topic_title(self) -> str:
        """'F1 · Jednosmerný prúd: …' -> 'Jednosmerný prúd: …' (for {tema})."""
        t = self.head.get("Téma", "")
        return t.split("·", 1)[1].strip() if "·" in t else t

    @property
    def knowledge(self) -> list:
        return [i for i in self.items if i.kind in ("closed", "semi", "open")]

    @property
    def max_points(self) -> int:
        return sum(i.max_points for i in self.knowledge)

    @property
    def expected_minutes(self) -> float:
        s = sum(i.expected_sec for i in self.items)
        return s / 60.0

    def item(self, iid: str) -> FormItem:
        for it in self.items:
            if it.id == iid:
                return it
        raise KeyError(iid)

    @property
    def title(self) -> str:
        return " · ".join(x for x in self.title_lines[:2] if x)


# ===========================================================================
# Numbers and fields of semi-open items
# ===========================================================================
NUM_RE = r"[−-]?\d+(?:[.,]\d+)?(?:\s*/\s*\d+)?"


def to_number(s: str):
    """'0,5' '0.5' '1/2' '−3' '1 024' -> Fraction; None if not a plain number."""
    t = s.strip().replace("\u00a0", " ").replace("−", "-")
    t = re.sub(r"(?<=\d) (?=\d{3}\b)", "", t)          # 1 024 -> 1024
    t = t.replace(",", ".").replace(" ", "")
    if not t:
        return None
    try:
        if "/" in t:
            a, b = t.split("/", 1)
            return Fraction(a) / Fraction(b)
        return Fraction(t)
    except (ValueError, ZeroDivisionError):
        return None


def plain(s: str) -> str:
    """Lower case, no diacritics, single spaces: how text answers are compared."""
    t = unicodedata.normalize("NFKD", s.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^\w%/+.,=<>-]+", " ", t)
    return " ".join(t.split())


def parse_fields(spec: str, where: str) -> list[dict]:
    """'R = 6 Ω; I = 2 A' | '3/8 ± 0,01' | '"prúd" | "elektrický prúd"'."""
    out = []
    for raw in [x.strip() for x in spec.split(";") if x.strip()]:
        label = ""
        m = re.match(r"^(.*?\S)\s+=\s+(.*)$", raw)
        if m and not m.group(1).startswith('"'):
            label, val = m.group(1).strip(), m.group(2).strip()
        else:
            val = raw
        if val.startswith('"'):
            alts = re.findall(r'"([^"]+)"', val)
            if not alts:
                raise TestError(f"{where}: text key without quoted answers: {raw!r}")
            out.append(dict(label=label, kind="text", accept=alts, unit=""))
            continue
        m = re.match(rf"^({NUM_RE})\s*(.*?)\s*(?:±\s*({NUM_RE}))?\s*$", val)
        if not m:
            raise TestError(f"{where}: cannot read the key {raw!r} "
                            f"(number [unit] [± tolerance] or \"text\")")
        num = to_number(m.group(1))
        if num is None:
            raise TestError(f"{where}: not a number: {m.group(1)!r}")
        tol = to_number(m.group(3)) if m.group(3) else None
        out.append(dict(label=label, kind="number", value=str(num), unit=m.group(2).strip(),
                        tol=None if tol is None else str(tol), shown=m.group(1).strip()))
    if not out:
        raise TestError(f"{where}: empty key")
    return out


def judge_field(f: dict, answer: str) -> bool | None:
    """True/False for a clear answer, None when a person must look at it."""
    a = (answer or "").strip().replace("\u00a0", " ")
    if not a or a == "?":
        return False
    a = re.sub(r"(?<=\d) (?=\d{3}\b)", "", a)           # 1 024 -> 1024
    if f["kind"] == "text":
        p = plain(a)
        return True if any(plain(x) == p for x in f["accept"]) else None
    m = re.match(rf"^\s*({NUM_RE})\s*(.*?)\s*$", a.replace("\u00a0", " "))
    if not m:
        return None
    x = to_number(m.group(1))
    if x is None:
        return None
    unit = m.group(2).strip()
    if unit and plain(unit) != plain(f["unit"]) and unit not in ("=",):
        return None                                # "500 mA" -- a person decides
    key = Fraction(f["value"])
    if f.get("tol") is not None:
        tol = Fraction(f["tol"])
    else:
        tol = abs(key) / 1000                      # exact up to rounding noise
    return abs(x - key) <= tol


# ===========================================================================
# Parsing
# ===========================================================================
HEAD_KEYS = ("Forma", "Predmet", "Téma", "Test", "Dvojča", "Kotvy", "Dotazník", "Rozsah")
ITEM_RE = re.compile(r"^([A-Z]\d{1,2})(?:\s+\[([A-Z ,]+)\])?\s{2,}(\S.*)$")
PART_RE = re.compile(r"^ČASŤ ([A-Z])\s+[—–-]\s+(.+?)\s*$")
OPT_RE = re.compile(r"^\s{4,}([a-h])\)\s+(.*)$")
INLINE_OPT_RE = re.compile(r"([a-h])\)\s+(.+?)(?=\s{2,}[a-h]\)\s|\s*$)")
SCALE_RE = re.compile(r"^\s{4,}(?:(?P<left>[^\d\s(][^\d]*?)\s{2,})?(?P<nums>\d+(?:\s{2,}\d+){2,})"
                      r"\s*(?P<pct>%)?(?:\s{2,}(?P<right>\D.*?))?\s*$")
EVAL_RE = re.compile(r"^([A-Z]\d{1,2})\s{2,}(Kľúč|Rubrika)\b\s*:?\s*(.*)$")


def _err(path: Path, n: int, msg: str) -> TestError:
    return TestError(f"{path.name}:{n}: {msg}")


def parse(path: str | Path) -> Form:
    path = Path(path)
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    if "\t" in text:
        ln = text[:text.index("\t")].count("\n") + 1
        raise _err(path, ln, "tabulátor -- používajte medzery")
    lines = text.split("\n")
    cut = next((i for i, x in enumerate(lines) if CUT in x), len(lines))
    pupil = lines[:cut]
    while pupil and set(pupil[-1].strip()) <= {"#"}:
        pupil.pop()
    evaluator = lines[cut + 1:]

    head: dict = {}
    title_lines: list = []
    for i, ln in enumerate(pupil[:40]):
        m = re.match(r"^(\w[\wáäčďéíĺľňóôŕšťúýž ]*?):\s{2,}(.*)$", ln)
        if m and m.group(1) in HEAD_KEYS:
            head[m.group(1)] = m.group(2).strip()
        elif ln.strip() and not set(ln.strip()) <= {"="} and not head and len(title_lines) < 3:
            title_lines.append(ln.strip())
    for k in ("Forma", "Test"):
        if k not in head:
            raise _err(path, 1, f"chýba hlavička „{k}:“")
    form_id = head["Forma"].split()[0]
    test = head["Test"].split()[0]
    subject = head.get("Predmet", "").split()[0].lower() if head.get("Predmet") else ""
    topic = head.get("Téma", "").split()[0] if head.get("Téma") else ""

    # --- free blocks: POKYNY, DOHODY
    def block(name: str) -> str:
        for i, ln in enumerate(pupil):
            if ln.strip().startswith(name):
                out = []
                for x in pupil[i + 1:]:
                    if (PART_RE.match(x) or (x.strip() and x == x.upper() and len(x.strip()) > 6
                                             and not x.strip().startswith(("•", "-")))):
                        break
                    out.append(x.rstrip())
                return "\n".join(out).strip("\n")
        return ""
    instructions = block("POKYNY")
    conventions = block("DOHODY")

    # --- parts and items
    parts: list[Part] = []
    items: list[FormItem] = []
    part: Part | None = None
    it: FormItem | None = None
    stem: list[str] = []
    opts: list[str] = []
    stim_title, stim_lines = "", []
    pending_instr: list[str] = []

    def close_item():
        nonlocal it, stem, opts
        if it is None:
            return
        while stem and not stem[-1].strip():
            stem.pop()
        it.stem = "\n".join(stem).strip("\n")
        it.options = [o.strip() for o in opts]
        items.append(it)
        it, stem, opts = None, [], []

    def close_part_instr():
        if part is not None and not part.instructions:
            part.instructions = "\n".join(x.strip() for x in pending_instr).strip()

    for n, ln in enumerate(pupil, 1):
        if ln.strip().startswith("KONIEC TESTU") or ln.strip().startswith("KONIEC DOTAZNÍKA"):
            close_item()
            break
        pm = PART_RE.match(ln)
        if pm:
            close_item()
            close_part_instr()
            pid = pm.group(1)
            if pid not in PART_KIND:
                raise _err(path, n, f"neznáma časť {pid}")
            part = Part(pid, pm.group(2), "", PART_KIND[pid])
            parts.append(part)
            pending_instr, stim_title, stim_lines = [], "", []
            continue
        if part is None:
            continue
        if set(ln.strip()) <= {"-", "—"} and ln.strip():
            continue
        im = ITEM_RE.match(ln)
        if im:
            close_item()
            close_part_instr()
            if part.kind == "text" and stim_lines and not part.stimulus:
                part.stimulus = dict(title=stim_title, text="\n".join(stim_lines).rstrip())
            iid = im.group(1)
            if not iid.startswith(part.id):
                raise _err(path, n, f"položka {iid} je v časti {part.id}")
            conds = [c.strip() for c in (im.group(2) or "").split(",") if c.strip()]
            it = FormItem(id=iid, format="", stem="", line=n, part=part.id,
                          conditions=conds)
            stem = [im.group(3).rstrip()]
            continue
        if it is None:
            # before the first item of a part: instructions, or the text of part D
            if part.kind == "text" and ln.startswith("TEXT"):
                stim_title = ln.split(":", 1)[1].strip() if ":" in ln else ""
                continue
            if part.kind == "text" and ln.startswith("|"):
                stim_lines.append(ln[2:] if ln.startswith("| ") else ln[1:])
                continue
            pending_instr.append(ln)
            continue
        # inside an item
        if not ln.strip():
            if not opts:
                stem.append("")
            continue
        if re.match(r"^\s*\.{6,}\s*$", ln) or ln.strip().startswith("Istota:"):
            continue
        om = OPT_RE.match(ln)
        if om:
            found = INLINE_OPT_RE.findall(ln.strip())
            expected = LETTERS[len(opts)]
            for letter, txt in found:
                if letter != LETTERS[len(opts)]:
                    raise _err(path, n, f"{it.id}: možnosť {letter}) namiesto {LETTERS[len(opts)]})")
                opts.append(txt)
            if not found or found[0][0] != expected:
                raise _err(path, n, f"{it.id}: nečitateľné možnosti")
            continue
        if opts and re.match(r"^\s{9,}\S", ln):
            opts[-1] += " " + ln.strip()
            continue
        sm = SCALE_RE.match(ln)
        if sm and part.kind == "psych":
            nums = [int(x) for x in sm.group("nums").split()]
            step = nums[1] - nums[0]
            if any(b - a != step for a, b in zip(nums, nums[1:])) or step <= 0:
                raise _err(path, n, f"{it.id}: škála nemá rovnaký krok")
            it.scale = dict(min=nums[0], max=nums[-1], step=step,
                            left=(sm.group("left") or "").strip(),
                            right=(sm.group("right") or "").strip(),
                            pct=bool(sm.group("pct")))
            continue
        am = re.match(r"^\s{4,}Odpoveď:\s*(.*)$", ln)
        if am:
            if part.kind == "psych":
                rng = re.search(r"číslo\s+(\d+)\s*[–-]\s*(\d+)", am.group(1))
                if rng:
                    it.scale = dict(min=int(rng.group(1)), max=int(rng.group(2)), step=1,
                                    number=True, left="", right="")
                else:
                    it.scale = dict(text=True)
            continue
        if opts:
            raise _err(path, n, f"{it.id}: text po možnostiach: {ln.strip()[:50]!r}")
        stem.append(ln[4:] if ln.startswith("    ") else ln.strip())
    close_item()
    close_part_instr()

    form = Form(id=form_id, path=path, head=head, title_lines=title_lines,
                subject=subject, topic=topic, test=test, instructions=instructions,
                conventions=conventions, parts=parts, items=items, skills={},
                pupil_text="\n".join(pupil).rstrip() + "\n")
    _parse_evaluator(form, evaluator, cut + 2)
    _finish(form)
    return form


def _parse_evaluator(form: Form, lines: list[str], offset: int) -> None:
    by_id = {i.id: i for i in form.items}
    cur: FormItem | None = None
    last_dx = None
    in_skills = in_scales = False
    for k, ln in enumerate(lines):
        n = offset + k
        if ln.strip().startswith("ZRUČNOSTI"):
            in_skills = True
            continue
        if ln.strip().startswith("ŠKÁLY"):
            in_scales = True
            continue
        sm = re.match(r"^\s{0,4}(S\d+)\s{2,}(.*)$", ln)
        if in_skills and sm:
            form.skills[sm.group(1)] = sm.group(2).strip()
            continue
        if in_skills and ln.strip() and not sm:
            in_skills = False
        # a questionnaire's subscales: "  nfc6  Q7, Q8, Q9R, Q10R  (comment)";
        # R marks a reverse-scored item
        qm = re.match(r"^\s{1,4}(\S+)\s{2,}((?:[A-Z]\d{1,2}R?\s*,\s*)*[A-Z]\d{1,2}R?)\b(.*)$", ln)
        if in_scales and qm:
            ids = []
            for tok in [t.strip() for t in qm.group(2).split(",")]:
                rev = tok.endswith("R") and tok[:-1] in by_id
                iid = tok[:-1] if rev else tok
                if iid not in by_id:
                    raise _err(form.path, n, f"škála {qm.group(1)} uvádza neznámu položku {tok}")
                by_id[iid].reverse = by_id[iid].reverse or rev
                ids.append(iid)
            form.subscales[qm.group(1)] = ids
            continue
        if in_scales and ln.strip() and not qm:
            in_scales = False
        em = EVAL_RE.match(ln)
        if em:
            iid, what, rest = em.groups()
            if iid not in by_id:
                raise _err(form.path, n, f"kľúč k neexistujúcej položke {iid}")
            cur = by_id[iid]
            last_dx = None
            if what == "Kľúč":
                if cur.options:
                    letters = [x.strip() for x in rest.split(",") if x.strip()]
                    if not letters or any(len(x) != 1 or x not in LETTERS[:len(cur.options)]
                                          for x in letters):
                        raise _err(form.path, n, f"{iid}: kľúč {rest!r} nie sú písmená možností")
                    cur.key = sorted(LETTERS.index(x) for x in letters)
                    cur.kind = "closed"
                else:
                    cur.fields = parse_fields(rest, f"{form.path.name}:{n} {iid}")
                    cur.kind = "semi"
            else:
                cur.kind = "open"
                pm = re.search(r"\((\d+)\s*b\.?\)", rest)
                cur.max_points = int(pm.group(1)) if pm else 3
            continue
        if cur is None:
            continue
        if ln.strip() and not ln.startswith(" "):
            cur = None                     # a free section of the evaluator part
            continue
        s = ln.strip()
        if not s:
            continue
        if "Úroveň:" in s or "Zručnosť:" in s:
            for chunk in s.split("·"):
                if ":" not in chunk:
                    continue
                key, val = [x.strip() for x in chunk.split(":", 1)]
                if key == "Úroveň":
                    cur.level = val
                elif key == "Zručnosť":
                    cur.skill = ",".join(x.strip() for x in val.split(",") if x.strip())
                elif key == "Dvojča":
                    cur.twin = val
                elif key == "Kotva":
                    cur.anchor = "" if val in ("-", "–", "—", "nie") else val
            continue
        dm = re.match(r"^([a-h])\)\s+(.*)$", s)
        if dm and cur.kind == "closed":
            idx = LETTERS.index(dm.group(1))
            if idx in cur.key:
                cur.diagnosis_keys[str(idx)] = dm.group(2)
                last_dx = ("k", str(idx))
            else:
                cur.distractor_dx[str(idx)] = dm.group(2)
                last_dx = ("d", str(idx))
            continue
        km = re.match(r"^K(\d)\s+(?:\((\d)\s*b\.?\)\s+)?(.*)$", s)
        if km and cur.kind == "open":
            cur.rubric.append(dict(criterion=f"K{km.group(1)} {km.group(3)}",
                                   points=int(km.group(2) or 1)))
            last_dx = ("r", len(cur.rubric) - 1)
            continue
        if s.startswith("Uznať aj:") and cur.kind == "semi":
            for extra in parse_fields(s.split(":", 1)[1], f"{form.path.name}:{n} {cur.id}"):
                for f in cur.fields:
                    if f["label"] == extra["label"] and f["kind"] == extra["kind"] == "text":
                        f["accept"] += extra["accept"]
                        break
                else:
                    raise _err(form.path, n, f"{cur.id}: „Uznať aj“ bez zodpovedajúceho poľa")
            continue
        if s.startswith("Ukážka"):
            cur.examples.append(s)
            last_dx = ("e", len(cur.examples) - 1)
            continue
        # continuation of the previous line
        if last_dx:
            kind, ref = last_dx
            if kind == "d":
                cur.distractor_dx[ref] += " " + s
            elif kind == "k":
                cur.diagnosis_keys[ref] += " " + s
            elif kind == "r":
                cur.rubric[ref]["criterion"] += " " + s
            elif kind == "e":
                cur.examples[ref] += " " + s
        else:
            cur.note = (cur.note + " " + s).strip()


def _finish(form: Form) -> None:
    """Formats, points, seconds, part metadata on every item."""
    pmap = {p.id: p for p in form.parts}
    for it in form.items:
        p = pmap[it.part]
        if p.kind == "psych":
            it.kind = "psych"
            if it.options:
                it.format = ("multi" if "viac možností" in " ".join(it.stem.split())
                             else "choice")
            elif it.scale.get("number"):
                it.format = "number"
            elif it.scale.get("text"):
                it.format = "text"
            elif it.scale:
                it.format = "scale"
            else:
                raise TestError(f"{form.path.name}:{it.line}: {it.id}: dotazníková položka "
                                f"bez možností, škály alebo riadku „Odpoveď:“")
            it.expected_sec = SECONDS["number"] if it.format == "number" else (
                SECONDS["text"] if it.format == "text" else SECONDS["psych"])
            continue
        if it.kind == "closed":
            it.format, it.max_points, it.jol = "mr", POINTS["closed"], True
            it.expected_sec = SECONDS["closed"]
        elif it.kind == "semi":
            it.format, it.max_points, it.jol = "short", POINTS["semi"], True
            it.expected_sec = SECONDS["semi"]
            it.key = [f.get("shown") or " / ".join(f.get("accept", [])) for f in it.fields]
            # the coding sheet shows a person the key when a field needs judgement
            it.rubric = [dict(points=POINTS["semi"], criterion="kľúč: " + "; ".join(
                (f["label"] + " = " if f["label"] else "") +
                (f.get("shown", "") + (" " + f["unit"] if f.get("unit") else "")
                 if f["kind"] == "number" else " / ".join(f["accept"]))
                for f in it.fields) + " (2 b. všetko správne, 1 b. jedna chyba)")]
        elif it.kind == "open":
            it.format, it.jol = "open", False
            it.expected_sec = SECONDS["open"]
        else:
            raise TestError(f"{form.path.name}:{it.line}: {it.id}: chýba kľúč alebo rubrika "
                            f"v časti pre hodnotiteľa")
        if p.kind == "text" and p.stimulus:
            it.stimulus = p.stimulus
    first_d = next((i for i in form.items if i.part == "D"), None)
    if first_d is not None:
        first_d.expected_sec += READING_SEC


# ===========================================================================
# Checks
# ===========================================================================
def validate(form: Form) -> list[str]:
    """Errors (a list of strings). Empty = the form follows its specification."""
    E: list[str] = []
    w = form.path.name
    ids = [i.id for i in form.items]
    if len(ids) != len(set(ids)):
        E.append(f"{w}: duplicitné čísla položiek")
    for it in form.items:
        where = f"{w} {it.id}"
        if not it.stem.strip():
            E.append(f"{where}: prázdne zadanie")
        if any(c not in ("K", "G", "A") for c in it.conditions):
            E.append(f"{where}: podmienka musí byť K, G alebo A")
        if it.kind in ("closed", "semi", "open"):
            if it.level not in LEVELS:
                E.append(f"{where}: neznáma úroveň {it.level!r}")
            if not it.skill:
                E.append(f"{where}: chýba zručnosť")
        if it.kind == "closed":
            if form.is_test and len(it.options) != 5:
                E.append(f"{where}: {len(it.options)} možností, má ich byť päť (a–e)")
            missing = [LETTERS[k] for k in range(len(it.options))
                       if k not in it.key and str(k) not in it.distractor_dx]
            if missing:
                E.append(f"{where}: rozptyľovače {missing} nemajú diagnózu")
            if not 1 <= len(it.key) <= 3:
                E.append(f"{where}: {len(it.key)} správnych možností; povolené 1 až 3")
            # case and spacing only: plain() would also drop the brackets and
            # exponents that tell two formulas apart
            if len({" ".join(o.lower().split()) for o in it.options}) != len(it.options):
                E.append(f"{where}: dve rovnaké možnosti")
            for o in it.options:
                if plain(o) in ("vsetky uvedene", "ziadna z uvedenych", "vsetky", "ziadna"):
                    E.append(f"{where}: možnosť „{o}“ porušuje pravidlá tvorby položiek")
            for word in ("viac správnych", "jedna správna", "všetky správne"):
                if word in it.stem:
                    E.append(f"{where}: zadanie prezrádza počet správnych odpovedí ({word})")
        if it.kind == "open":
            pts = sum(r["points"] for r in it.rubric)
            if not it.rubric or pts != it.max_points:
                E.append(f"{where}: rubrika dáva {pts} b., položka má {it.max_points} b.")
        if it.kind == "psych" and it.format == "scale":
            if not (it.scale.get("left") and it.scale.get("right")) and it.scale.get("max", 0) - it.scale.get("min", 0) < 20:
                E.append(f"{where}: škála bez slovného popisu krajných bodov")

    if not form.is_test:
        return E
    # --- blueprint
    bp = BLUEPRINT["T4" if form.test == "T4" else "T13"]
    for pid, levels in bp.items():
        got = [i for i in form.items if i.part == pid]
        if len(got) != len(levels):
            E.append(f"{w}: časť {pid} má {len(got)} položiek, špecifikácia {len(levels)}")
            continue
        for i, (it, lv) in enumerate(zip(got, levels), 1):
            if it.id != f"{pid}{i}":
                E.append(f"{w}: položka {it.id} je na pozícii {pid}{i}")
            if it.level != lv:
                E.append(f"{w} {it.id}: úroveň {it.level}, špecifikácia {lv}")
    for it in form.items:
        if it.part == "A" and it.kind != "closed":
            E.append(f"{w} {it.id}: v časti A má byť uzavretá položka")
        if it.part == "B" and it.kind != "semi":
            E.append(f"{w} {it.id}: v časti B má byť polootvorená položka")
        if it.part == "C" and it.kind != "open":
            E.append(f"{w} {it.id}: v časti C má byť otvorená položka")
    closed = [i for i in form.items if i.kind == "closed" and i.part == "A"]
    multi = [i for i in closed if len(i.key) > 1]
    if form.test in ("T1", "T3") and len(multi) != MULTI_PER_T13:
        E.append(f"{w}: {len(multi)} položiek s viacerými správnymi, má ich byť {MULTI_PER_T13}")
    if form.test == "T4" and not 4 <= len(multi) <= 6:
        E.append(f"{w}: {len(multi)} položiek s viacerými správnymi, má ich byť 4 až 6")
    singles = [i.key[0] for i in closed if len(i.key) == 1]
    if form.test in ("T1", "T3") and len(set(singles)) < 5:
        E.append(f"{w}: kľúče jednoodpoveďových položiek nepokrývajú všetky písmená a–e "
                 f"({''.join(LETTERS[k] for k in singles)})")
    if any(singles.count(k) > 3 for k in set(singles)):
        E.append(f"{w}: jedno písmeno je kľúčom viac ako trikrát")
    if not any(p.id == "P" for p in form.parts):
        E.append(f"{w}: chýba časť P (sebadôvera k téme)")
    if form.test == "T4":
        d = [i for i in form.items if i.part == "D"]
        if d and not d[0].stimulus.get("text"):
            E.append(f"{w}: časť D nemá text")
    return E


def cross_validate(cat: dict[str, Form]) -> list[str]:
    E: list[str] = []
    topics: dict[str, dict[str, Form]] = {}
    for f in cat.values():
        if f.is_test:
            topics.setdefault(f.topic, {})[f.test] = f
    for topic, forms in sorted(topics.items()):
        if set(forms) != {"T1", "T3", "T4"}:
            E.append(f"téma {topic}: má {sorted(forms)}, potrebuje T1, T3 a T4")
            continue
        t1, t3, t4 = forms["T1"], forms["T3"], forms["T4"]
        # twins: the same cell on every position
        for a in t3.knowledge:
            try:
                b = t1.item(a.id)
            except KeyError:
                E.append(f"{topic}: {a.id} nemá dvojča v T1")
                continue
            if (a.level, a.kind, a.n_keys) != (b.level, b.kind, b.n_keys):
                E.append(f"{topic} {a.id}: T1 a T3 nie sú dvojčatá "
                         f"(úroveň/formát/počet správnych: {b.level}/{b.kind}/{b.n_keys} "
                         f"vs {a.level}/{a.kind}/{a.n_keys})")
            if set(a.skill.split(",")) != set(b.skill.split(",")):
                E.append(f"{topic} {a.id}: T1 a T3 merajú iné zručnosti ({b.skill} vs {a.skill})")
            if a.kind == "semi" and len(a.fields) != len(b.fields):
                E.append(f"{topic} {a.id}: dvojčatá majú rôzny počet políčok")
            if a.stem == b.stem:
                E.append(f"{topic} {a.id}: T1 a T3 majú rovnaké zadanie -- dvojča má byť iné")
        # anchors: identical, same position
        for pos in ANCHOR_POSITIONS:
            a, b = t3.item(pos), t4.item(pos)
            if not a.anchor or a.anchor != b.anchor:
                E.append(f"{topic} {pos}: kotva nie je označená v T3 aj T4")
            if (a.stem, a.options, a.key) != (b.stem, b.options, b.key):
                E.append(f"{topic} {pos}: kotva sa v T3 a T4 líši")
            if a.level != b.level or a.skill != b.skill:
                E.append(f"{topic} {pos}: kotva má v T3 a T4 inú úroveň alebo zručnosť")
        others = [i.id for i in t3.items if i.anchor and i.id not in ANCHOR_POSITIONS]
        if others:
            E.append(f"{topic}: kotvy mimo dohodnutých pozícií: {others}")
        lv = {t3.item(p).level for p in ANCHOR_POSITIONS}
        if len(lv) < 3:
            E.append(f"{topic}: kotvy pokrývajú len {sorted(lv)}")
        if sum(1 for p in ANCHOR_POSITIONS if t3.item(p).n_keys > 1) < 2:
            E.append(f"{topic}: medzi kotvami sú menej ako dve položky s viacerými správnymi")
        # T4 non-anchor items must not repeat a T3 item
        t3stems = {plain(i.stem) for i in t3.knowledge}
        for it in t4.knowledge:
            if it.id not in ANCHOR_POSITIONS and plain(it.stem) in t3stems:
                E.append(f"{topic} {it.id}: T4 opakuje položku z T3, ktorá nie je kotvou")
        # self-efficacy items: one repeated measure
        ps = [[(i.id, i.stem, json.dumps(i.scale, sort_keys=True)) for i in f.items if i.part == "P"]
              for f in (t1, t3, t4)]
        if not (ps[0] == ps[1] == ps[2]):
            E.append(f"{topic}: časť P (sebadôvera) nie je v T1, T3 a T4 rovnaká")
        for f in (t1, t3, t4):
            q = f.head.get("Dotazník", "").split()[0] if f.head.get("Dotazník") else ""
            if q and q not in cat:
                E.append(f"{f.path.name}: dotazník {q} neexistuje")
    return E


# ===========================================================================
# Catalogue, composition (what the pupil sits), print version
# ===========================================================================
def root() -> Path:
    for r in ROOTS:
        if r.is_dir() and any(r.glob("*-T1.txt")):
            return r
    raise TestError(f"priečinok s testami sa nenašiel ({', '.join(str(r) for r in ROOTS)})")


def files(where: Path | None = None) -> list[Path]:
    r = where or root()
    return sorted([p for p in r.glob("*.txt")
                   if re.search(r"-T[134]\.txt$", p.name) or p.name.startswith("dotaznik-")])


def load_catalog(where: Path | None = None, check: bool = True) -> dict[str, Form]:
    cat: dict[str, Form] = {}
    for p in files(where):
        f = parse(p)
        if f.id in cat:
            raise TestError(f"{p.name}: forma {f.id} už existuje ({cat[f.id].path.name})")
        cat[f.id] = f
    if check:
        errs = [e for f in cat.values() for e in validate(f)] + cross_validate(cat)
        if errs:
            raise TestError("testy nevyhovujú špecifikácii:\n  " + "\n  ".join(errs))
    return cat


def _subst(s: str, subject: str, topic: str = "") -> str:
    """Fill the questionnaires' placeholders: {predmet} {predmetu} {predmete}
    {predmet_akuz} (the subject, declined) and {tema} (the topic's title)."""
    if topic:
        s = s.replace("{tema}", topic)
    forms = SUBJECTS.get(subject)
    if not forms:
        return s
    return (s.replace("{predmetu}", forms["gen"]).replace("{predmete}", forms["loc"])
            .replace("{predmet_akuz}", forms["acc"]).replace("{predmet}", forms["nom"]))


def _copy(it: FormItem, subject: str, part_meta: dict, topic: str = "") -> FormItem:
    c = FormItem(**{k: getattr(it, k) for k in FormItem.__dataclass_fields__})
    c.stem = _subst(c.stem, subject, topic)
    c.options = [_subst(o, subject, topic) for o in c.options]
    c.scale = dict(c.scale)
    c.part_meta = dict(part_meta)
    return c


def compose(form_id: str, cat: dict[str, Form], condition: str | None = None) -> Bank:
    """The sitting, in order: questionnaire before, self-efficacy, the test,
    questionnaire after. One Bank, so the runner serves it like any other."""
    f = cat[form_id]
    q = cat.get((f.head.get("Dotazník") or "").split()[0]) if f.is_test else None
    seq: list[FormItem] = []
    subscales: dict = {}

    def add(src: Form, part_ids: tuple, label: str):
        pmap = {p.id: p for p in src.parts}
        renamed = {}
        for it in src.items:
            if it.part not in part_ids or not it.applies_to(condition):
                continue
            p = pmap[it.part]
            meta = dict(key=f"{label}:{p.id}", id=p.id,
                        title=_subst(p.title, f.subject, f.topic_title),
                        instructions=_subst(p.instructions, f.subject, f.topic_title),
                        kind=p.kind)
            c = _copy(it, f.subject, meta, f.topic_title)
            if label == "Q":
                c.id = f"{src.id}.{it.id}"           # D1.Q1 -- never clashes with the test
            renamed[it.id] = c.id
            seq.append(c)
        for name, ids in src.subscales.items():
            kept = [renamed[i] for i in ids if i in renamed]
            if kept:
                subscales[f"{src.id}.{name}"] = kept

    if q is not None:
        add(q, ("Q",), "Q")
    add(f, ("P", "A", "B", "C", "D") if f.is_test else ("Q", "Z", "P"), "F")
    if q is not None:
        add(q, ("Z",), "Q")
    b = Bank(bank_id=f.id, instrument=f.id, title=f.title, items=seq, topic=f.topic,
             minutes=round(sum(i.expected_sec for i in seq) / 60.0, 1),
             subscales=subscales, note=f.path.name)
    return b


def pupil_sheet(form: Form, subject: str | None = None, topic: str = "") -> str:
    """The paper version: everything above the cut, nothing of the key.
    A questionnaire is printed for one test: its subject and topic filled in."""
    return _subst(form.pupil_text, subject or form.subject, topic)


def menu_rows(cat: dict[str, Form]) -> list[Form]:
    order = {"fyzika": 0, "matematika": 1, "informatika": 2}
    tests = sorted((f for f in cat.values() if f.is_test),
                   key=lambda f: (order.get(f.subject, 9), f.topic, f.test))
    quests = sorted((f for f in cat.values() if not f.is_test), key=lambda f: f.id)
    return tests + quests


# ===========================================================================
def overview(cat: dict[str, Form]) -> str:
    rows = []
    for f in menu_rows(cat):
        if f.is_test:
            closed = [i for i in f.items if i.kind == "closed"]
            multi = sum(1 for i in closed if len(i.key) > 1)
            keys = "".join(LETTERS[i.key[0]] for i in closed if len(i.key) == 1)
            higher = sum(i.max_points for i in f.knowledge if i.level in HIGHER)
            rows.append(f"{f.id:7} {f.subject:11} {len(f.knowledge):3} pol. {f.max_points:3} b. "
                        f"{f.expected_minutes:5.1f} min  viac správnych {multi:2}  "
                        f"kľúče {keys:12} vyššie úrovne {100 * higher / f.max_points:3.0f} %")
        else:
            rows.append(f"{f.id:7} {'dotazník':11} {len(f.items):3} pol.        "
                        f"{f.expected_minutes:5.1f} min")
    return "\n".join(rows)


def main(argv: list[str]) -> int:
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tlac", default="", help="form id: print the pupil's sheet")
    ap.add_argument("--pre", default="",
                    help="with a questionnaire: the test it accompanies (fills in "
                         "the subject and the topic), e.g. --tlac D1 --pre F1-T1")
    ap.add_argument("--zoznam", action="store_true")
    ap.add_argument("--tlac-vsetko", default="",
                    help="directory: write every pupil sheet (no key) for the paper "
                         "backup -- each test and its questionnaire filled in")
    ap.add_argument("--dir", default="")
    a = ap.parse_args(argv)
    where = Path(a.dir) if a.dir else None
    try:
        cat = load_catalog(where, check=not a.tlac)
    except TestError as e:
        print(f"TESTY ODMIETNUTÉ\n{e}")
        return 1
    if a.tlac_vsetko:
        out = Path(a.tlac_vsetko)
        out.mkdir(parents=True, exist_ok=True)
        n = 0
        for f in menu_rows(cat):
            if f.is_test:
                (out / f"{f.id}.txt").write_text(pupil_sheet(f), encoding="utf-8")
                q = cat.get((f.head.get("Dotazník") or "").split()[0])
                if q is not None:
                    (out / f"{f.id}-dotaznik-{q.id}.txt").write_text(
                        pupil_sheet(q, f.subject, f.topic_title), encoding="utf-8")
                    n += 1
                n += 1
            elif f.id == "D0":
                (out / "D0-vstupny-dotaznik.txt").write_text(pupil_sheet(f), encoding="utf-8")
                n += 1
        print(f"{n} hárkov pre žiakov (bez kľúča) v {out}")
        return 0
    if a.tlac:
        if a.tlac not in cat or (a.pre and a.pre not in cat):
            print(f"neznámy test {a.tlac} {a.pre}; existujú: {', '.join(sorted(cat))}")
            return 2
        t = cat[a.pre] if a.pre else None
        sys.stdout.write(pupil_sheet(cat[a.tlac], t.subject if t else None,
                                     t.topic_title if t else ""))
        return 0
    if a.zoznam:
        for i, f in enumerate(menu_rows(cat), 1):
            print(f"{i:3}  {f.id:7} {f.title}")
        return 0
    print(overview(cat))
    n = sum(len(f.knowledge) for f in cat.values())
    print(f"\n{len(cat)} súborov, {n} vedomostných položiek, všetko v súlade so špecifikáciou")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
