"""scoring.py -- turning what a pupil typed into what the analysis reads.

The division of labour, and why it is drawn where it is
-------------------------------------------------------
Closed items are scored by this module, now, with no human in the loop. Open
items are NOT, and the refusal is deliberate: automatic marking of free Slovak
prose about algorithmic reasoning would be unreliable in a way that is worse
than merely noisy. It would be unreliable *differentially* -- a pupil who has
spent a lesson reading fluent assistant prose writes more fluent prose, and any
surface-feature marker would reward that. The study's own hypothesis is that
condition A and condition G differ in how pupils write. A marker sensitive to
how pupils write would therefore manufacture part of the effect it is measuring,
which is exactly the defect the PEQI classifier already had once and had to be
repaired for.

So open items leave here as `pending`, with the rubric attached, and come back
double-coded. What this module does guarantee is that the handover is complete:
every open response is exported for coding, every code is read back, and
`finalise()` refuses to produce an analytic row while any open item is unscored.
A silent zero for an uncoded open item would look like a wrong answer.

Three further things this module does that a marking script normally does not
-----------------------------------------------------------------------------
PARTIAL CREDIT IS KEPT SEPARATE FROM DICHOTOMOUS SCORING. The Rasch model in the
analysis layer is dichotomous. A rubric item worth 0-2 is therefore exported
both as its raw points and as its dichotomisation at the rubric's own midpoint,
and which one the analysis uses is the analysis's decision, declared there. What
is not acceptable is this module quietly picking one.

THE DISTRACTOR IS RECORDED, NOT JUST THE WRONGNESS. `correct = 0` throws away
the only diagnostic information a multiple-choice item produces. The chosen
option and its diagnosis travel with the row, which is what lets the class report
tell a teacher *which* misconception a class holds.

SCORING IS SEPARATE FROM EXCLUSION. An answer given in 1.4 seconds is scored
normally and flagged separately (see `effort.py`). Merging the two would hide a
decision about data exclusion inside a scoring function, where no reviewer would
look for it.

Run:  python scoring.py        self-test on fixtures
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

from bank import Bank, Item, load_all


@dataclass
class Response:
    """One pupil, one item, one occasion. The unit the runner writes."""
    pseudonym: str
    session: str                 # T0a | T0b | P1 | P2 | P3 | T4a | T4b | T6
    instrument: str
    item_id: str
    raw: str                     # exactly what the pupil entered
    seconds: float
    jol: int | None = None       # 0-100 confidence, where the item carries one
    timestamp: str = ""
    # Signals the runner observes and the network cannot (see integrity.py)
    paste_events: int = 0
    blur_seconds: float = 0.0
    revisions: int = 0


@dataclass
class Scored:
    """A scored response. `points is None` means an open item awaiting coding."""
    pseudonym: str
    session: str
    instrument: str
    item_id: str
    raw: str
    seconds: float
    jol: int | None
    points: int | None
    max_points: int
    correct: int | None          # dichotomous, for the Rasch model
    chosen: int | None           # option index, for closed items
    diagnosis: str               # what the chosen distractor says
    level: str
    skill: str
    anchor: str
    pending: bool
    note: str = ""
    # finalise() has always written s.timestamp, and the record never had one:
    # the first finalise() that was not refused for pending items would have
    # crashed. The self-test exercised only the refusal.
    timestamp: str = ""


# ===========================================================================
def _norm_numeric(s: str) -> str:
    """A numeric answer, tolerant of how a pupil writes a number but of nothing
    else. '1 024', '1024', '1024.' are the same; 'asi 1024' is not -- that is a
    different kind of answer and the rubric, not a regex, decides about it."""
    t = s.strip().replace(" ", "").replace(" ", "").replace(",", ".")
    return t.rstrip(".")


def score_one(item: Item, r: Response) -> Scored:
    base = dict(pseudonym=r.pseudonym, session=r.session,
                instrument=r.instrument, item_id=r.item_id, raw=r.raw,
                seconds=r.seconds, jol=r.jol, max_points=item.max_points,
                level=item.level, skill=item.skill, anchor=item.anchor,
                timestamp=r.timestamp)

    test_section = bool(getattr(item, "part_meta", None))
    if item.is_open and test_section and getattr(item, "kind", "") == "psych":
        # a free-text questionnaire answer: kept, never scored
        return Scored(**base, points=None, correct=None, chosen=None,
                      diagnosis="", pending=False, note="questionnaire: no key")
    if item.is_open and test_section and r.raw.strip() == "?":
        # the pupil pressed "Neviem": there is nothing for a coder to read
        return Scored(**base, points=0, correct=0, chosen=None, diagnosis="",
                      pending=False, note="vynechané (neviem)")
    if item.is_open:
        # Left for the coders. Not zero, not guessed, not approximated.
        return Scored(**base, points=None, correct=None, chosen=None,
                      diagnosis="", pending=True,
                      note="open item: awaiting two independent coders")

    if item.format in ("mc4", "mc3", "choice"):
        chosen = None
        t = r.raw.strip()
        if t.isdigit() and 0 <= int(t) < len(item.options):
            chosen = int(t)
        elif t in item.options:
            chosen = item.options.index(t)
        if chosen is None:
            return Scored(**base, points=0, correct=0, chosen=None,
                          diagnosis="", pending=False, note="no answer recorded")
        ok = int(chosen == item.key)
        dx = "" if ok else item.distractor_dx.get(str(chosen), "")
        return Scored(**base, points=ok * item.max_points, correct=ok,
                      chosen=chosen, diagnosis=dx, pending=False)

    if item.format == "multi" and isinstance(item.key, list):
        # Multiple response, number of correct options not disclosed. Scored
        # all or nothing for the dichotomous model; what the pupil got wrong is
        # kept as diagnoses, not thrown away.
        picked = set()
        for part in r.raw.split(","):
            part = part.strip()
            if part.isdigit() and 0 <= int(part) < len(item.options):
                picked.add(int(part))
        key = set(item.key)
        ok = int(picked == key)
        wrong = sorted(picked - key)
        missed = sorted(key - picked)
        dx = "; ".join(item.distractor_dx.get(str(k), "") for k in wrong
                       if item.distractor_dx.get(str(k)))
        note = "" if ok else (f"navyše {[chr(65 + k) for k in wrong]}, "
                              f"chýba {[chr(65 + k) for k in missed]}")
        return Scored(**base, points=ok * item.max_points, correct=ok,
                      chosen=None, diagnosis=dx, pending=False, note=note)

    if item.format == "numeric":
        ok = int(_norm_numeric(r.raw) == _norm_numeric(str(item.key)))
        return Scored(**base, points=ok * item.max_points, correct=ok,
                      chosen=None, diagnosis="", pending=False)

    # --- the test section (testy/*.txt) ---------------------------------
    if item.format == "mr" and isinstance(item.key, list):
        # Closed item; one correct option or several, and the page does not say
        # which. Each of the five options is a true/false judgement: 2 points
        # with none wrong, 1 with one wrong, 0 otherwise. An empty answer or an
        # explicit "Neviem" is 0 -- otherwise leaving a single-answer item blank
        # would earn 1 point for four "correct" non-marks. The dichotomous
        # `correct` (all five right) is what the Rasch model reads.
        t = r.raw.strip()
        if not t or t == "?":
            return Scored(**base, points=0, correct=0, chosen=None, diagnosis="",
                          pending=False, note="vynechané (neviem)")
        picked = {int(p) for p in t.split(",") if p.strip().isdigit()
                  and 0 <= int(p) < len(item.options)}
        key = set(item.key)
        wrong, missed = sorted(picked - key), sorted(key - picked)
        errors = len(wrong) + len(missed)
        points = {0: 2, 1: 1}.get(errors, 0) * item.max_points // 2
        dx = "; ".join(item.distractor_dx.get(str(k), "") for k in wrong
                       if item.distractor_dx.get(str(k)))
        note = "" if not errors else (f"navyše {[chr(97 + k) for k in wrong]}, "
                                      f"chýba {[chr(97 + k) for k in missed]}")
        return Scored(**base, points=points, correct=int(errors == 0),
                      chosen=next(iter(picked)) if len(picked) == 1 else None,
                      diagnosis=dx, pending=False, note=note)

    if item.format == "short" and getattr(item, "fields", None):
        # Semi-open: 2 points all fields right, 1 point with one wrong field
        # (when there are several), 0 otherwise. A field the rule cannot judge
        # -- a unit the key does not use, a word not on the list -- goes to the
        # coders with the whole item, like an open answer. Not guessed.
        import testy                                      # the parser owns the rule
        t = r.raw.strip()
        if not t or t == "?":
            return Scored(**base, points=0, correct=0, chosen=None, diagnosis="",
                          pending=False, note="vynechané (neviem)")
        try:
            vals = json.loads(t)
        except ValueError:
            vals = [t]
        verdicts = [testy.judge_field(f, vals[i] if i < len(vals) else "")
                    for i, f in enumerate(item.fields)]
        if any(v is None for v in verdicts):
            return Scored(**base, points=None, correct=None, chosen=None,
                          diagnosis="", pending=True,
                          note="polootvorená: odpoveď posúdi hodnotiteľ")
        wrong = verdicts.count(False)
        points = (2 if wrong == 0 else 1 if wrong == 1 and len(verdicts) > 1 else 0)
        points = points * item.max_points // 2
        return Scored(**base, points=points, correct=int(wrong == 0), chosen=None,
                      diagnosis="", pending=False,
                      note="" if not wrong else f"chybné políčka: {wrong}")

    # Questionnaire formats carry no correct answer. They are passed through with
    # the response preserved, so a subscale can be computed without this module
    # pretending to judge them.
    return Scored(**base, points=None, correct=None, chosen=None,
                  diagnosis="", pending=False, note="questionnaire: no key")


def score(responses: list[Response], banks: dict[str, Bank] | None = None
          ) -> list[Scored]:
    banks = banks or load_all()
    by_item: dict[tuple[str, str], Item] = {}
    for b in banks.values():
        for it in b.items:
            by_item[(b.instrument, it.id)] = it
    out = []
    for r in responses:
        it = by_item.get((r.instrument, r.item_id))
        if it is None:
            raise KeyError(f"{r.instrument}/{r.item_id} is in no bank. "
                           f"A response to an item that does not exist is a "
                           f"delivery bug, not a data point.")
        out.append(score_one(it, r))
    return out


# ===========================================================================
# The handover for open items. Both directions, because a one-way export is how
# open items end up silently unscored.
# ===========================================================================
def export_for_coding(scored: list[Scored], path: str | Path,
                      banks: dict[str, Bank] | None = None) -> int:
    """Write the open responses, with their rubric, for two coders.

    Pupil order is shuffled by a fixed permutation of the pseudonym hash rather
    than left in collection order, because collection order is condition order:
    a coder who marks all of condition A first will drift, and the drift will
    look like an effect.
    """
    banks = banks or load_all()
    rub = {(b.instrument, it.id): it.rubric
           for b in banks.values() for it in b.items}
    rows = [s for s in scored if s.pending]
    # sha256, not hash(): Python randomises hash() per process, so the "fixed"
    # permutation came out different on every run and the coding sheet could not
    # be regenerated in the order the coders had already worked through
    rows.sort(key=lambda s: (s.item_id, hashlib.sha256(
        f"{s.pseudonym}|blind".encode("utf-8")).hexdigest()))
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["item_id", "max_points", "rubric", "response",
                    "coder_a", "coder_b", "row_key"])
        for s in rows:
            crit = " | ".join(f"{r['points']}: {r['criterion']}"
                              for r in rub[(s.instrument, s.item_id)])
            # row_key carries the identity the coder must not see in a readable
            # form, but which the import must be able to join on
            key = f"{s.pseudonym}|{s.session}|{s.instrument}|{s.item_id}"
            w.writerow([s.item_id, s.max_points, crit, s.raw, "", "", key])
    return len(rows)


def import_codings(scored: list[Scored], path: str | Path,
                   tolerate_single: bool = False) -> dict:
    """Read coder scores back. Reports agreement; refuses to average silently."""
    rows = list(csv.DictReader(Path(path).open(encoding="utf-8")))
    by_key = {f"{s.pseudonym}|{s.session}|{s.instrument}|{s.item_id}": s
              for s in scored}
    filled = disagree = single = 0
    agreements: list[tuple[int, int]] = []
    for r in rows:
        s = by_key.get(r["row_key"])
        if s is None:
            continue
        a, b = r.get("coder_a", ""), r.get("coder_b", "")
        if a == "" and b == "":
            continue
        if a == "" or b == "":
            if not tolerate_single:
                single += 1
                continue
            v = int(a or b)
            s.points, s.pending = v, False
            s.note = "single coder"
            filled += 1
            continue
        ia, ib = int(a), int(b)
        agreements.append((ia, ib))
        if ia != ib:
            disagree += 1
            # NOT averaged. A disagreement is resolved by the coders, because an
            # average of two readings of a rubric is a number neither coder would
            # defend, and the rate of disagreement is itself a reported quantity.
            s.note = f"coders disagree: {ia} vs {ib} -- needs consensus"
            continue
        s.points = ia
        s.correct = int(ia >= (s.max_points + 1) // 2)
        s.pending = False
        filled += 1

    n = len(agreements)
    exact = sum(1 for a, b in agreements if a == b)
    # quadratic-weighted agreement on an ordinal rubric; chance-corrected
    kappa = _quadratic_kappa(agreements) if n >= 10 else None
    return dict(coded=filled, double_coded=n, exact_agreement=
                round(exact / n, 4) if n else None,
                disagreements=disagree, single_coded_skipped=single,
                quadratic_kappa=kappa,
                still_pending=sum(1 for s in scored if s.pending))


def _quadratic_kappa(pairs: list[tuple[int, int]]) -> float:
    if not pairs:
        return 0.0
    cats = sorted({v for p in pairs for v in p})
    idx = {c: i for i, c in enumerate(cats)}
    k = len(cats)
    if k < 2:
        return 1.0
    n = len(pairs)
    obs = [[0] * k for _ in range(k)]
    for a, b in pairs:
        obs[idx[a]][idx[b]] += 1
    ra = [sum(obs[i]) for i in range(k)]
    cb = [sum(obs[i][j] for i in range(k)) for j in range(k)]
    num = den = 0.0
    for i in range(k):
        for j in range(k):
            w = ((i - j) / (k - 1)) ** 2
            num += w * obs[i][j]
            den += w * ra[i] * cb[j] / n
    return round(1 - num / den, 4) if den else 1.0


# ===========================================================================
def finalise(scored: list[Scored], path: str | Path) -> dict:
    """Write responses.csv in the shape `analysis/ingest.py` validates.

    Refuses while any open item is unscored. An analytic file that silently omits
    the open items is a file whose test is shorter than the test the pupils sat,
    and nothing downstream would notice.
    """
    pend = [s for s in scored if s.pending]
    if pend:
        raise RuntimeError(
            f"{len(pend)} open responses are still uncoded "
            f"({', '.join(sorted({p.item_id for p in pend}))[:80]}). "
            f"Code them before the analytic file is written: a missing open item "
            f"is indistinguishable from a wrong answer once the file exists.")

    cols = ["pseudonym", "session", "instrument", "item_id", "response",
            "correct", "jol", "seconds", "timestamp",
            # beyond the ingest contract, and declared as additions
            "points", "max_points", "chosen", "level", "skill", "anchor"]
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for s in scored:
            w.writerow([s.pseudonym, s.session, s.instrument, s.item_id, s.raw,
                        "" if s.correct is None else s.correct,
                        "" if s.jol is None else s.jol,
                        f"{s.seconds:.1f}", s.timestamp,
                        "" if s.points is None else s.points, s.max_points,
                        "" if s.chosen is None else s.chosen,
                        s.level, s.skill, s.anchor])
    scoredable = [s for s in scored if s.correct is not None]
    return dict(rows=len(scored), scored=len(scoredable),
                mean_correct=round(sum(s.correct for s in scoredable)
                                   / max(len(scoredable), 1), 4))


# ===========================================================================
def self_test() -> list[str]:
    fails = []
    banks = load_all()
    ipt = banks["T1_IPT"]

    # a correct and an incorrect closed answer, by index and by text
    r_ok = Response("GYABCDE", "P1", "IPT", "T1-1", "1", 31.0, jol=90)
    r_no = Response("GYABCDE", "P1", "IPT", "T1-6", "zdvojnásobí sa", 22.0, jol=95)
    s = score([r_ok, r_no], banks)
    if s[0].correct != 1 or s[0].points != 1:
        fails.append("correct closed answer not scored 1")
    if s[1].correct != 0:
        fails.append("wrong closed answer not scored 0")
    if "lineárnu intuíciu" not in s[1].diagnosis:
        fails.append(f"distractor diagnosis missing: {s[1].diagnosis!r}")

    # an open item must come back pending, never zero
    r_open = Response("GYABCDE", "P1", "IPT", "T1-12", "polí sa to na polovicu",
                      140.0)
    so = score([r_open], banks)[0]
    if not so.pending or so.points is not None:
        fails.append("open item was scored automatically")

    # finalise must refuse while anything is pending
    try:
        finalise(score([r_ok, r_open], banks), Path("_t.csv"))
        fails.append("finalise accepted a pending open item")
    except RuntimeError:
        pass
    Path("_t.csv").unlink(missing_ok=True)

    # an unknown item is a delivery bug, not a data point
    try:
        score([Response("X", "P1", "IPT", "T1-99", "0", 5.0)], banks)
        fails.append("accepted a response to a non-existent item")
    except KeyError:
        pass

    # the coder round trip, including a disagreement that must NOT be averaged
    tmp = Path("_coding.csv")
    allsc = score([r_ok, r_open], banks)
    n = export_for_coding(allsc, tmp, banks)
    if n != 1:
        fails.append(f"export_for_coding wrote {n} rows, expected 1")
    rows = list(csv.DictReader(tmp.open(encoding="utf-8")))
    rows[0]["coder_a"], rows[0]["coder_b"] = "2", "1"
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    rep = import_codings(allsc, tmp)
    if rep["disagreements"] != 1:
        fails.append(f"disagreement not reported: {rep}")
    if any(s.points == 1.5 for s in allsc):
        fails.append("a disagreement was averaged")
    if rep["still_pending"] != 1:
        fails.append("a disagreed item was treated as resolved")
    tmp.unlink(missing_ok=True)
    return fails


def main() -> int:
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    fails = self_test()
    for f in fails:
        print("  FAIL " + f)
    print("scoring self-test: " + ("ok" if not fails else f"{len(fails)} failures"))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
