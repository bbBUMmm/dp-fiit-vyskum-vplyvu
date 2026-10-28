"""sessions.py -- what fits into a Slovak lesson, computed from the items.

The defect this module exists to prevent
----------------------------------------
The thesis already had a time budget (`analysis/measurement_plan.py`), and it
already reported that every session fits. It computed each block as

    minutes = n_items * sec_per_item

with one average `sec_per_item` per instrument. That is sound when a test's
items cost roughly the same and badly wrong when they do not -- and here they do
not. The immediate test has ten closed items at about forty seconds and six
rubric items at two and a half minutes; the flat average of 55 s/item splits the
difference and understates the test by five minutes. The transfer test is six
rubric items that Appendix A itself specifies at twenty-five minutes, and the
average put it at six and a half.

The errors do not cancel, because they all point the same way: every instrument
that the average understates is an instrument with open items, and open items
are concentrated in exactly two places -- the delayed test, repeated for three
topics, and the transfer test. Both sit in session T4. T4 carries the primary
outcome of the study.

So the budget is computed from the bank, item by item, and the overrun shows up
as a number that fails a check rather than as an average that passes one.

Two further rules, which the flat average had no way to express
---------------------------------------------------------------
FATIGUE CAP. A measurement session is not merely a sum of minutes. Beyond about
forty-five minutes of continuous testing, adolescent performance declines, and
it declines faster for pupils with lower motivation -- which is a quantity the
conditions plausibly affect. An over-long session therefore does not just add
noise, it adds noise that is correlated with the treatment. The cap is a
validity requirement, not a courtesy.

HANDOVER COST. Every supervised session spends time that is not testing: codes
handed out, instructions read, machines woken. It is charged once per session,
not amortised per item, because that is how it is actually spent.

Run:  python sessions.py            the budget, per session
      python sessions.py --json     machine-readable, for the analysis layer
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from bank import Bank, load_all

# A Slovak lesson is 45 minutes. A double block is 90 plus the break, which the
# school does not give up, so a 90-minute block is 2 x 45 with 75 usable for
# teaching once the handover is paid at both ends.
LESSON_MIN = 45.0

# Continuous testing beyond this depresses performance, and does so unequally.
FATIGUE_CAP_MIN = 45.0

# Handover is charged per session and differs by session, because it is spent on
# different things. T0a hands out code envelopes and explains the study to pupils
# who have never seen it; by P1 the pupils know the drill and only have to log in.
# Averaging these would make the first session look cheap and the later ones
# expensive, which is the mistake this module exists to stop making.
HANDOVER_MIN = {"T0a": 8.0, "T0b": 1.0, "P1..P3": 4.0,
                "T4a": 5.0, "T4b": 5.0, "T6": 5.0}

# A break resets the fatigue clock. It costs minutes and buys measurement that is
# not contaminated by tiredness correlated with motivation -- which the
# conditions plausibly affect, so the contamination would not be mere noise.
BREAK_MIN = 3.0

# The confidence slider, per item that carries one. Measured on the stub client
# rather than guessed: it is one drag of a slider with no reading to do.
JOL_SEC = 6.0


@dataclass
class Block:
    """One instrument inside one session."""
    bank_id: str
    repeats: int = 1          # the delayed test is the same bank x 3 topics
    label: str = ""
    break_after: bool = False

    def one_run_minutes(self, banks: dict[str, Bank]) -> float:
        """One uninterrupted stretch of testing -- what the fatigue cap bounds."""
        b = banks[self.bank_id]
        sec = sum(i.expected_sec + (JOL_SEC if i.jol else 0.0) for i in b.items)
        return sec / 60.0

    def minutes(self, banks: dict[str, Bank]) -> float:
        return self.repeats * self.one_run_minutes(banks)

    def breaks(self) -> int:
        # repeats are separated by breaks too: three topics of the delayed test
        # back to back is one 47-minute sitting, which is the thing to avoid.
        return (self.repeats - 1 if self.break_after or self.repeats > 1 else 0) \
            + (1 if self.break_after else 0)


@dataclass
class Session:
    code: str
    label: str
    supervised: bool
    lessons: float                       # how many 45-min lessons the school gives
    blocks: list[Block] = field(default_factory=list)
    teaching_min: float = 0.0            # the lesson itself, in P1..P3
    # An unsupervised session is not measured in lessons. Homework set through
    # EduPage costs the pupil's own evening, and what bounds it is how much of
    # that evening it is reasonable to ask for -- not the length of a lesson.
    # Modelling it as one lesson gave it a 45-minute budget and 38 minutes of
    # slack, which made an instrument look comfortable because it was being
    # compared against the wrong thing.
    budget_override_min: float | None = None
    note: str = ""

    def budget_min(self) -> float:
        if self.budget_override_min is not None:
            return self.budget_override_min
        return self.lessons * LESSON_MIN

    def handover_min(self) -> float:
        return HANDOVER_MIN.get(self.code, 5.0)

    def break_min(self) -> float:
        return BREAK_MIN * sum(b.breaks() for b in self.blocks)

    def testing_min(self, banks) -> float:
        return sum(b.minutes(banks) for b in self.blocks)

    def longest_run_min(self, banks) -> float:
        """The longest stretch with no break. This is what fatigue responds to,
        not the session total: three 16-minute tests with a stretch between them
        are not a 48-minute test."""
        longest = cur = 0.0
        for b in self.blocks:
            run = b.one_run_minutes(banks)
            if b.repeats > 1:
                cur = max(cur, run)        # repeats are break-separated
                longest, cur = max(longest, cur), 0.0
                continue
            cur += run
            if b.break_after:
                longest, cur = max(longest, cur), 0.0
        return max(longest, cur)

    def total_min(self, banks) -> float:
        return (self.testing_min(banks) + self.teaching_min
                + self.handover_min() + self.break_min())


# ===========================================================================
# The schedule. One topic is written out (T1); T2 and T3 reuse the same banks,
# which is why the delayed test repeats three times rather than appearing three
# times. Keeping it as `repeats` rather than three Block entries is deliberate:
# it makes it impossible to update one topic's timing and forget the others.
# ===========================================================================
def schedule() -> list[Session]:
    return [
        Session("T0a", "vstupná hodina", True, 1.0, [
            Block("ICAR_EXT", 1, "ICAR: matice a rady", break_after=True),
            Block("IBOBOR_EXT", 1, "iBobor: kovariátová sada"),
        ]),
        Session("T0b", "domáca úloha cez EduPage", False, 0.0, [
            Block("JRMAI"),
            Block("BACKGROUND"),
        ], budget_override_min=15.0,
            note="Nie je test a nepotrebuje dozor, takže nesúťaží o hodinu. "
                 "Rozpočet nie je vyučovacia hodina, ale to, koľko z~večera "
                 "žiaka je rozumné žiadať: pätnásť minút."),
        Session("P1..P3", "vyučovací blok (každý z troch)", True, 2.0, [
            Block("T1_IPT", 1, "okamžitý test s JOL"),
            Block("POST_LESSON", 1, "dotazník po bloku"),
        ], teaching_min=64.0,
            note="Predtest k téme sa presunul na konec PREDCHÁDZAJÚCEJ hodiny "
                 "informatiky (4 min, pod dozorom, 2–3 dni vopred). Vedomosti o "
                 "predpokladoch témy sa za dva dni bez výučby nemenia, takže "
                 "kovariát tým nič nestráca — a blok získa štyri minúty, ktoré "
                 "v ňom nie sú. Výklad je 64 min, nie 75: kontrolný list "
                 "vernosti (V1–V3) pôvodne sčítal 35+40+15 = 90 min vyučovania "
                 "vnútri 90-minútového bloku, ktorý má okrem toho obsahovať aj "
                 "test a dotazník."),
        Session("T4a", "odložený test a negatívna kontrola", True, 2.0, [
            Block("T1_DRT", 3, "odložený test, tri témy", break_after=True),
            Block("ICAR_EXT", 1, "ICAR znovu — negatívna kontrola"),
        ], note="Dve hodiny. Tri témy odloženého testu s prestávkami medzi nimi "
                "držia najdlhší nepretržitý úsek na 15 minútach."),
        Session("T4b", "transferový test", True, 1.0, [
            Block("TT", 1, "transferový test"),
        ], note="Oddelený od T4a. Spolu by to bolo 92 minút merania, a transfer "
                "je práve to meranie, pri ktorom únava uškodí najviac: šesť "
                "rubrikových položiek vyžaduje odvodenie, nie vybavenie."),
        Session("T6", "voliteľné semestrálne rameno", True, 1.0, [
            Block("IBOBOR_FULL_EXT", 1, "iBobor: výstupná sada"),
        ]),
    ]


# External instruments: licensed, figural, or held by a third party, so the
# items are not in this repository. Declared with their counts and timings so
# the budget is complete, and marked so nobody mistakes a declaration for an
# instrument we hold.
EXTERNAL = {
    "ICAR_EXT":        dict(items=20, sec_per_item=45,
                            source="ICAR, public domain (Condon & Revelle 2014)"),
    "IBOBOR_EXT":      dict(items=8, sec_per_item=100,
                            source="iBobor, FMFI UK — súhlas nevyžiadaný"),
    "IBOBOR_FULL_EXT": dict(items=15, sec_per_item=100,
                            source="iBobor, FMFI UK — súhlas nevyžiadaný"),
}


class _ExternalBank:
    """Just enough of a Bank to be timed. It cannot be administered or scored."""

    def __init__(self, bank_id: str, spec: dict):
        self.bank_id = bank_id
        self.instrument = bank_id
        self.external = True
        self.source = spec["source"]
        n, sec = spec["items"], spec["sec_per_item"]

        class _I:
            def __init__(self, s): self.expected_sec, self.jol = s, False
        self.items = [_I(sec) for _ in range(n)]


def all_banks() -> dict:
    banks = dict(load_all())
    for k, spec in EXTERNAL.items():
        banks[k] = _ExternalBank(k, spec)
    return banks


# ===========================================================================
def budget(banks=None) -> dict:
    banks = banks or all_banks()
    out: dict = {"sessions": [], "violations": []}
    for s in schedule():
        rows = [dict(label=b.label or banks[b.bank_id].instrument,
                     bank=b.bank_id, repeats=b.repeats,
                     items=len(banks[b.bank_id].items) * b.repeats,
                     minutes=round(b.minutes(banks), 1))
                for b in s.blocks]
        testing = s.testing_min(banks)
        total = s.total_min(banks)
        longest = s.longest_run_min(banks)
        row = dict(code=s.code, label=s.label, supervised=s.supervised,
                   lessons=s.lessons, blocks=rows,
                   teaching_min=s.teaching_min,
                   handover_min=s.handover_min(),
                   break_min=s.break_min(),
                   testing_min=round(testing, 1),
                   longest_run_min=round(longest, 1),
                   total_min=round(total, 1),
                   budget_min=s.budget_min(),
                   slack_min=round(s.budget_min() - total, 1),
                   fits=bool(total <= s.budget_min()),
                   within_fatigue_cap=bool(longest <= FATIGUE_CAP_MIN),
                   note=s.note)
        out["sessions"].append(row)
        if not row["fits"]:
            out["violations"].append(
                f"{s.code}: needs {total:.1f} min, the school gives "
                f"{s.budget_min():.0f}")
        if not row["within_fatigue_cap"]:
            out["violations"].append(
                f"{s.code}: longest unbroken stretch {longest:.1f} min exceeds "
                f"the {FATIGUE_CAP_MIN:.0f}-minute fatigue cap")

    sup = [s for s in out["sessions"] if s["supervised"]]
    out["supervised_sessions"] = len(sup)
    # P1..P3 is three occurrences of one session; the school counts lessons.
    out["measurement_lessons"] = sum(
        s["lessons"] * (3 if s["code"] == "P1..P3" else 1)
        for s in out["sessions"] if s["supervised"] and s["code"] != "T6")
    out["measurement_lessons_excl_teaching"] = sum(
        s["lessons"] for s in out["sessions"]
        if s["supervised"] and s["code"] not in ("T6", "P1..P3"))
    out["all_fit"] = not out["violations"]
    return out


# ===========================================================================
def naive_budget_comparison(banks=None) -> dict:
    """What the flat average said, against what the items say.

    Reported because the size of the gap is the argument for computing the
    budget from the bank, and because a reader is entitled to see that the old
    number was not merely imprecise but wrong in one direction.
    """
    banks = banks or all_banks()
    # the averages that measurement_plan.py used, per instrument
    FLAT = {"T1_IPT": 55 + 6, "T1_DRT": 55 + 6, "TT": 65, "T1_PRECHECK": 50,
            "JRMAI": 12, "BACKGROUND": 15, "POST_LESSON": 12}
    rows = []
    for bid, sec in FLAT.items():
        b = banks[bid]
        flat = len(b.items) * sec / 60.0
        real = sum(i.expected_sec + (JOL_SEC if i.jol else 0) for i in b.items) / 60.0
        rows.append(dict(bank=bid, items=len(b.items),
                         flat_min=round(flat, 1), item_min=round(real, 1),
                         understated_by=round(real - flat, 1),
                         open_items=sum(1 for i in b.items if i.is_open)))
    worst = max(rows, key=lambda r: r["understated_by"])
    return dict(rows=rows,
                total_understated=round(sum(r["understated_by"] for r in rows), 1),
                worst=worst["bank"],
                worst_by=worst["understated_by"],
                all_understatements_same_sign=all(
                    r["understated_by"] >= 0 for r in rows
                    if r["open_items"] > 0))


def main(argv: list[str]) -> int:
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    res = budget()
    if "--json" in argv:
        res["naive_comparison"] = naive_budget_comparison()
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0

    for s in res["sessions"]:
        flag = "ok " if s["fits"] and s["within_fatigue_cap"] else "!! "
        print(f"\n{flag}{s['code']:8} {s['label']}")
        for b in s["blocks"]:
            print(f"      {b['label']:38} {b['items']:3} pol.  {b['minutes']:5.1f} min")
        if s["teaching_min"]:
            print(f"      {'hodina':38} {'':3}       {s['teaching_min']:5.1f} min")
        if s["break_min"]:
            print(f"      {'prestávky':38} {'':3}       {s['break_min']:5.1f} min")
        print(f"      {'odovzdanie a pokyny':38} {'':3}       {s['handover_min']:5.1f} min")
        print(f"      {'-' * 56}")
        print(f"      {'spolu / rozpočet':38} {'':3}       "
              f"{s['total_min']:5.1f} / {s['budget_min']:.0f} min"
              f"   (rezerva {s['slack_min']:+.1f})")
        if not s["within_fatigue_cap"]:
            print(f"      najdlhší nepretržitý úsek {s['longest_run_min']:.1f} min "
                  f"> únavový strop {FATIGUE_CAP_MIN:.0f} min")

    print(f"\nmeracích hodín (bez vyučovacích blokov): "
          f"{res['measurement_lessons_excl_teaching']:.0f}")
    if res["violations"]:
        print("\nPORUŠENIA:")
        for v in res["violations"]:
            print("  - " + v)
        return 1
    print("\nvšetky stretnutia sa zmestia a žiadne neprekračuje únavový strop")

    cmp_ = naive_budget_comparison()
    print(f"\nproti plochému priemeru: podhodnotenie {cmp_['total_understated']:+.1f} "
          f"min celkom, najviac {cmp_['worst']} o {cmp_['worst_by']:+.1f} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
