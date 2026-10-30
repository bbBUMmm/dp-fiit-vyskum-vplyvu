"""bank.py -- the item bank, and the only place an item is written down.

Why this module exists
----------------------
Before it, every measuring instrument in this study existed exactly once: as
LaTeX prose in Appendix A. That is enough to *document* a test and not enough to
*administer* one, so a second copy would have had to appear -- in whatever the
pupils actually sat in front of. Two copies of one specification is the failure
this project has already paid for twice:

    * the PEQI taxonomy, implemented in Python and in Java, drifted silently;
      the repair went into one and not the other, so the thesis would have
      reported numbers from a fixed classifier while pupils were scored by a
      broken one;
    * the UTF-8 console fix went into `server.py` and into no other entry point,
      and resurfaced in the analysis layer three weeks later.

So the item is data. One bank feeds three consumers and none of them may hold
its own copy:

    bank/*.json  ->  runner.py     what the pupil sits in front of
                 ->  scoring.py    what turns a response into a score
                 ->  tex_export.py what Appendix A prints

A test asserts the third against the second: every stem the appendix shows must
be a stem the bank holds. The appendix cannot drift from the instrument because
the appendix is generated from it.

What the bank must declare, and why each field earns its place
--------------------------------------------------------------
`level`           blueprint cell. `validate()` refuses a bank whose level counts
                  do not match the blueprint the thesis prints. The blueprint is
                  a claim about what the test measures; unchecked, it is a table.
`anchor`          the anchor-group id. Six items are shared between the
                  immediate and the delayed form, and they are what put the two
                  on one scale. Equating is the whole basis of the immediate-vs-
                  delayed contrast, so the bank refuses to load if the two forms
                  disagree about which items are shared.
`expected_sec`    the per-item time an attentive pupil needs. Two jobs: the time
                  budget (a Slovak lesson is 45 minutes, and instruments
                  specified in items are delivered in minutes), and the
                  rapid-guessing threshold in `effort.py`, which is defined
                  relative to it.
`distractor_dx`   what choosing each wrong option says about the pupil's
                  reasoning. Not decoration: it is what makes the class report
                  actionable for a teacher, and it is the difference between
                  "11 pupils got item 7 wrong" and "11 pupils think doubling the
                  array doubles the number of steps".
`jol`             whether the item carries a confidence slider. Per item, not
                  per test: a questionnaire has no correct answer and so cannot
                  carry one, and `validate()` enforces exactly that.

Standard library only. This has to run on a locked-down school laptop.

Run:  python bank.py            validate every bank, print the summary
      python bank.py --budget   print the time budget per session
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
BANKS = HERE / "banks"

# The blueprint, from Table 5.3 of the thesis. It lives here, once, so the table
# and the instrument cannot drift apart -- the same reason the ingest thresholds
# live in ingest.py and not in the protocol appendix.
#
# ONE blueprint for both forms, where the thesis had two (16 items immediate, 12
# delayed). The change was forced by the time budget and turned out to be a
# methodological gain rather than a concession: isomorphy of forms is the
# assumption the immediate-to-delayed contrast rests on, and two forms of
# different length, with different level counts and a different mix of open and
# closed items, are not isomorphic in any sense a reader could check. Equal
# length, one blueprint and six genuinely common items is the textbook
# common-item design, and `cross_validate` can then enforce all three.
BLUEPRINT = {"zapamatanie": 2, "porozumenie": 2, "aplikacia": 4,
             "analyza": 3, "hodnotenie": 1}
BLUEPRINT_FOR = ("IPT", "DRT")

# Both forms must also match in FORMAT mix, not only in level counts. An open
# item is a different measurement from a closed one -- it is scored by a human,
# carries rater error, and rewards expression as well as knowledge -- so a form
# with five open items and a form with three are not the same instrument even
# when every blueprint cell agrees.
OPEN_ITEMS_PER_FORM = 3

LEVELS = ("zapamatanie", "porozumenie", "aplikacia", "analyza", "hodnotenie")
FORMATS = ("mc4", "mc3", "numeric", "open", "table", "likert5", "likert7",
           "scale0_10", "scale0_100", "choice", "multi", "text")

# Instruments that are tests (have a key, can carry a confidence slider) as
# opposed to questionnaires (no correct answer, must not carry one).
SCORED = ("PRECHECK", "IPT", "DRT", "TT", "ICAR", "IBOBOR", "CT")
UNSCORED = ("JRMAI", "BACKGROUND", "LOAD", "FOL", "ATTITUDE", "RELIANCE", "AILQ")


class BankError(ValueError):
    """A bank that cannot be trusted. Raised at load, never swallowed."""


@dataclass
class Item:
    id: str
    format: str
    stem: str
    level: str = ""
    options: list[str] = field(default_factory=list)
    key: object = None                  # index for mc*, str/number otherwise
    max_points: int = 1
    anchor: str = ""                    # anchor-group id, "" = not an anchor
    expected_sec: float = 30.0
    jol: bool = False
    rubric: list[dict] = field(default_factory=list)
    distractor_dx: dict = field(default_factory=dict)
    skill: str = ""                     # sub-skill, for the class report
    reverse: bool = False               # reverse-keyed questionnaire item
    note: str = ""
    # Conditions in which the item is administered; empty = all. The post-lesson
    # questionnaire's N items ask about the assistant, which condition K never
    # had. The bank's own note said "runner ich preskočí podľa podmienky" -- and
    # the runner had no notion of a condition, so K pupils were asked to rate
    # an assistant they had not seen.
    conditions: list[str] = field(default_factory=list)

    @property
    def is_open(self) -> bool:
        return self.format in ("open", "table", "text")

    def applies_to(self, condition: str | None) -> bool:
        return not self.conditions or not condition or condition in self.conditions


@dataclass
class Bank:
    bank_id: str
    instrument: str
    title: str
    minutes: float
    items: list[Item]
    topic: str = ""
    jol: bool = False                   # default for the items
    subscales: dict = field(default_factory=dict)
    note: str = ""

    @property
    def n_items(self) -> int:
        return len(self.items)

    @property
    def max_points(self) -> int:
        return sum(i.max_points for i in self.items)

    @property
    def anchors(self) -> list[str]:
        return sorted({i.anchor for i in self.items if i.anchor})

    @property
    def expected_minutes(self) -> float:
        return sum(i.expected_sec for i in self.items) / 60.0

    def by_level(self) -> dict:
        out = {L: 0 for L in LEVELS}
        for i in self.items:
            if i.level:
                out[i.level] += 1
        return out

    def item(self, item_id: str) -> Item:
        for i in self.items:
            if i.id == item_id:
                return i
        raise KeyError(item_id)


# ===========================================================================
def load(path: str | Path) -> Bank:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    items = []
    for d in raw.get("items", []):
        unknown = set(d) - set(Item.__dataclass_fields__)
        if unknown:
            raise BankError(f"{raw.get('bank_id')}/{d.get('id')}: "
                            f"unknown field(s) {sorted(unknown)}")
        items.append(Item(**d))
    b = Bank(bank_id=raw["bank_id"], instrument=raw["instrument"],
             title=raw["title"], minutes=float(raw["minutes"]), items=items,
             topic=raw.get("topic", ""), jol=bool(raw.get("jol", False)),
             subscales=raw.get("subscales", {}), note=raw.get("note", ""))
    for it in b.items:
        if b.jol and b.instrument in SCORED and not it.is_open:
            it.jol = True
    validate(b)
    return b


def load_all() -> dict[str, Bank]:
    out = {}
    for p in sorted(BANKS.glob("*.json")):
        b = load(p)
        if b.bank_id in out:
            raise BankError(f"duplicate bank_id {b.bank_id}")
        out[b.bank_id] = b
    cross_validate(out)
    return out


# ===========================================================================
def validate(b: Bank) -> None:
    """Refuse a bank that cannot be administered or cannot be scored.

    Every check here corresponds to a way a school study loses data that cannot
    be recovered afterwards. None of them is stylistic.
    """
    ids = [i.id for i in b.items]
    if len(set(ids)) != len(ids):
        dup = sorted({x for x in ids if ids.count(x) > 1})
        raise BankError(f"{b.bank_id}: duplicate item ids {dup}")

    for it in b.items:
        where = f"{b.bank_id}/{it.id}"
        if it.format not in FORMATS:
            raise BankError(f"{where}: unknown format {it.format!r}")
        if not it.stem.strip():
            raise BankError(f"{where}: empty stem")

        # --- a scored item must be scorable. An item with no key reaches the
        # analysis as a column of zeros, which looks like a hard item.
        if b.instrument in SCORED:
            if it.format in ("mc4", "mc3", "choice"):
                n = {"mc4": 4, "mc3": 3}.get(it.format, len(it.options))
                if len(it.options) != n:
                    raise BankError(f"{where}: {it.format} needs {n} options, "
                                    f"has {len(it.options)}")
                if not isinstance(it.key, int) or not 0 <= it.key < n:
                    raise BankError(f"{where}: key {it.key!r} is not an option index")
                # a distractor with no diagnosis is a wrong answer we learn
                # nothing from, which wastes the only chance to ask the pupil
                missing = [k for k in range(n)
                           if k != it.key and str(k) not in it.distractor_dx]
                if missing:
                    raise BankError(f"{where}: distractors {missing} have no "
                                    f"diagnosis in distractor_dx")
            elif it.format == "multi":
                # several options may be correct, and the pupil is not told how
                # many (the supervisor's note in masters_opt.txt). Scored all or
                # nothing, so the key must name the full set.
                n = len(it.options)
                if (not isinstance(it.key, list) or not it.key
                        or len(set(it.key)) != len(it.key)
                        or not all(isinstance(k, int) and 0 <= k < n for k in it.key)):
                    raise BankError(f"{where}: multi needs a key listing the "
                                    f"correct option indices")
                missing = [k for k in range(n)
                           if k not in it.key and str(k) not in it.distractor_dx]
                if missing:
                    raise BankError(f"{where}: distractors {missing} have no "
                                    f"diagnosis in distractor_dx")
            elif it.format == "numeric":
                if it.key is None:
                    raise BankError(f"{where}: numeric item with no key")
            elif it.is_open:
                if not it.rubric:
                    raise BankError(f"{where}: open item with no rubric")
                pts = sum(r["points"] for r in it.rubric)
                if pts != it.max_points:
                    raise BankError(f"{where}: rubric sums to {pts}, "
                                    f"max_points is {it.max_points}")
        else:
            if it.jol:
                raise BankError(f"{where}: confidence slider on an item with "
                                f"no correct answer")
            if it.key is not None:
                raise BankError(f"{where}: questionnaire item carries a key")

        # --- an open item cannot carry a confidence slider: the pupil does not
        # yet know what the rubric will award, so the number would not be a
        # judgement of correctness.
        if it.is_open and it.jol:
            raise BankError(f"{where}: confidence slider on an open item")

        if it.expected_sec <= 0:
            raise BankError(f"{where}: expected_sec must be positive")
        if any(c not in ("K", "G", "A") for c in it.conditions):
            raise BankError(f"{where}: conditions must be drawn from K, G, A")
        if it.max_points < 1:
            raise BankError(f"{where}: max_points must be at least 1")

    # --- blueprint conformance. The thesis prints a table claiming the test
    # measures five cognitive levels in fixed proportions. Unchecked, that is a
    # table; checked, it is a property of the instrument.
    if b.instrument in BLUEPRINT_FOR:
        got = b.by_level()
        if got != BLUEPRINT:
            raise BankError(f"{b.bank_id}: blueprint mismatch\n"
                            f"  declared {BLUEPRINT}\n  bank     {got}")
        n_open = sum(1 for i in b.items if i.is_open)
        if n_open != OPEN_ITEMS_PER_FORM:
            raise BankError(f"{b.bank_id}: {n_open} open items, both forms must "
                            f"have {OPEN_ITEMS_PER_FORM}")

    # --- subscale coverage, for questionnaires that declare one
    for name, ids in b.subscales.items():
        missing = [x for x in ids if x not in ids or x not in [i.id for i in b.items]]
        if missing:
            raise BankError(f"{b.bank_id}: subscale {name} names absent items {missing}")

    # --- the time budget. Instruments are specified in items and delivered in
    # minutes; if the two do not reconcile, the plan is fiction.
    if b.expected_minutes > b.minutes * 1.15:
        raise BankError(f"{b.bank_id}: items need {b.expected_minutes:.1f} min, "
                        f"the protocol allows {b.minutes:.0f}")


def cross_validate(banks: dict[str, Bank]) -> None:
    """Checks that only make sense across banks. Equating lives here."""
    # Anchor items must be IDENTICAL in both forms of a topic, not merely
    # present in both. An anchor whose stem differs is not an anchor; it links
    # the forms wrongly and the whole immediate-to-delayed difference inherits
    # the error, silently and in a direction nobody can sign.
    by_topic: dict[str, dict[str, Bank]] = {}
    for b in banks.values():
        if b.instrument in ("IPT", "DRT") and b.topic:
            by_topic.setdefault(b.topic, {})[b.instrument] = b

    for topic, forms in sorted(by_topic.items()):
        if set(forms) != {"IPT", "DRT"}:
            raise BankError(f"topic {topic}: has {sorted(forms)}, needs both forms")
        ipt, drt = forms["IPT"], forms["DRT"]
        if set(ipt.anchors) != set(drt.anchors):
            raise BankError(f"topic {topic}: anchor groups differ\n"
                            f"  IPT {ipt.anchors}\n  DRT {drt.anchors}")
        if len(ipt.anchors) != 6:
            raise BankError(f"topic {topic}: {len(ipt.anchors)} anchors, the "
                            f"plan requires 6")
        for a in ipt.anchors:
            x = [i for i in ipt.items if i.anchor == a]
            y = [i for i in drt.items if i.anchor == a]
            if len(x) != 1 or len(y) != 1:
                raise BankError(f"topic {topic}, anchor {a}: "
                                f"{len(x)} in IPT, {len(y)} in DRT, needs 1 each")
            if x[0].stem.strip() != y[0].stem.strip():
                raise BankError(
                    f"topic {topic}, anchor {a}: stems differ between forms.\n"
                    f"  IPT: {x[0].stem[:90]}\n  DRT: {y[0].stem[:90]}")
            if x[0].format != y[0].format or x[0].max_points != y[0].max_points:
                raise BankError(f"topic {topic}, anchor {a}: format or points differ")
            if x[0].is_open:
                raise BankError(
                    f"topic {topic}, anchor {a}: an open item cannot be an "
                    f"anchor -- the link between the forms would then carry the "
                    f"inter-rater error of the scoring as well")

        # The anchor set must span difficulty. All six at the easy end would link
        # the forms only where nobody differs, and the delayed scale would be
        # pinned by items every pupil answers correctly on both occasions.
        lv = sorted({x.level for x in ipt.items if x.anchor})
        if len(lv) < 3:
            raise BankError(f"topic {topic}: anchors cover only {lv}; the link "
                            f"needs at least three cognitive levels")
        # Equal-length forms, which is what makes "isomorphic" checkable.
        if ipt.n_items != drt.n_items:
            raise BankError(f"topic {topic}: forms have {ipt.n_items} and "
                            f"{drt.n_items} items; equating assumes one blueprint")


# ===========================================================================
def budget(banks: dict[str, Bank]) -> list[dict]:
    rows = []
    for b in sorted(banks.values(), key=lambda z: (z.instrument, z.bank_id)):
        rows.append(dict(bank=b.bank_id, instrument=b.instrument,
                         items=b.n_items, points=b.max_points,
                         protocol_min=b.minutes,
                         items_min=round(b.expected_minutes, 1),
                         slack_min=round(b.minutes - b.expected_minutes, 1),
                         anchors=len(b.anchors)))
    return rows


def main(argv: list[str]) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    try:
        banks = load_all()
    except BankError as e:
        print(f"bank REJECTED:\n{e}")
        return 1
    rows = budget(banks)
    w = max(len(r["bank"]) for r in rows)
    print(f"{'bank':{w}}  instr      items  pts  prot  items  slack  anch")
    for r in rows:
        print(f"{r['bank']:{w}}  {r['instrument']:9}  {r['items']:5}  "
              f"{r['points']:3}  {r['protocol_min']:4.0f}  {r['items_min']:5.1f}  "
              f"{r['slack_min']:5.1f}  {r['anchors']:4}")
    print(f"\n{len(banks)} banks, {sum(b.n_items for b in banks.values())} items, "
          f"all valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
