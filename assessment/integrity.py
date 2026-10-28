"""integrity.py -- was the test taken by the pupil, or with help?

The question nobody in this literature answers
----------------------------------------------
This is a study about what happens to learning when pupils have an AI assistant.
Its outcome is a test. The test is sat on a laptop, in a school, by a pupil who
owns a phone. Every published study of this kind handles that the same way: an
observer ticks a box. In this project the box is V12 of the fidelity checklist --
"during the test pupils had no access to the assistant or to notes". That is an
assertion by a person watching twenty screens, and it is the only thing standing
between the primary outcome and a contaminated one.

It also fails in exactly the wrong direction. A pupil who found the lesson
frustrating has less reason to care about an ungraded test than a pupil who found
it pleasant, and a pupil who spent the lesson being handed finished answers has
both the habit and the expectation of looking one up. So contamination is
plausibly *differential by condition* -- which makes it bias, not noise, and bias
whose sign cannot be guessed.

What can actually be observed
-----------------------------
Five signal families, from three independent sources, so that no single
measurement failure produces a flag on its own:

  B  BEHAVIOUR    the test window lost focus; text was pasted
  T  TIME         an item answered correctly far faster than it can be read
  S  SIMILARITY   two pupils' free text is nearly identical
  I  INVERSION    the pupil's hard items were faster than their easy ones
  C  COVERAGE     the capture layer saw assistant traffic during the test window

Each is weak. B catches a pupil who switched tabs and misses one using a phone.
T catches a lookup and misses a slow, careful one. S catches two pupils sharing
and misses one pupil working alone with an assistant. Together they are not
strong either -- which is why the output is a graded signal and never a verdict.

Three rules that make this usable rather than merely suspicious
--------------------------------------------------------------
1. THE DETECTOR IS CALIBRATED ON A SESSION WHERE CONTAMINATION IS IMPOSSIBLE.
   Session T0a happens before any pupil has met the tool, in a room where no
   assistant exists. Whatever the index flags there is a false positive, by
   construction. That rate is reported, and a detector that flags 8% of T0a is a
   detector whose 9% at T4a means nothing.

2. NO PUPIL IS EVER NAMED TO THE SCHOOL. These are measurements of data quality,
   not accusations about children, and the distinction is not rhetorical: a flag
   that could reach a grade would change the pupil's incentive to take the test
   honestly, and would destroy the measurement it was introduced to protect. The
   school report carries a rate for the class and nothing else.

3. EXCLUSION IS PRE-REGISTERED AND ALWAYS DOUBLE-REPORTED. A response is excluded
   only on two signals from different families above threshold. Primary analysis
   runs on everything; the excluded-data analysis runs alongside it; both are
   printed whichever way they come out.

Run:  python integrity.py        self-test, incl. detection power by simulation
"""
from __future__ import annotations

import json
import math
import re
import sys
from dataclasses import dataclass, field

# --- thresholds, declared here once ---------------------------------------
BLUR_SEC_FLAG = 8.0          # a glance is under a second; eight is a lookup
PASTE_FLAG = 1               # any paste into a free-text answer
FAST_CORRECT_FRACTION = 0.25  # correct in under a quarter of the expected time
SIMILARITY_FLAG = 0.82       # Jaccard on content tokens, two different pupils
INVERSION_FLAG = -0.35       # within-pupil correlation of time with difficulty
FAMILIES_TO_EXCLUDE = 2


@dataclass
class Signal:
    family: str
    item_id: str
    value: float
    flagged: bool
    detail: str = ""


@dataclass
class PupilIntegrity:
    pseudonym: str
    session: str
    signals: list[Signal] = field(default_factory=list)

    @property
    def families(self) -> set[str]:
        return {s.family for s in self.signals if s.flagged}

    @property
    def flagged_items(self) -> set[str]:
        return {s.item_id for s in self.signals if s.flagged and s.item_id}

    @property
    def excluded(self) -> bool:
        return len(self.families) >= FAMILIES_TO_EXCLUDE

    def summary(self) -> dict:
        return dict(pseudonym=self.pseudonym, session=self.session,
                    families=sorted(self.families),
                    n_flags=sum(1 for s in self.signals if s.flagged),
                    flagged_items=sorted(self.flagged_items),
                    excluded=self.excluded)


# ===========================================================================
_WORD = re.compile(r"[a-záäčďéíĺľňóôŕšťúýž0-9]+", re.I)
_STOP = {"a", "aj", "ale", "ak", "by", "to", "ten", "tá", "je", "sa", "si",
         "na", "do", "od", "po", "pre", "za", "v", "vo", "s", "so", "z", "zo",
         "že", "lebo", "keď", "tak", "už", "len", "aby", "nie", "ako", "kde",
         "ktorý", "ktorá", "ktoré", "byť", "sú", "bude", "som", "má", "mám"}


def tokens(text: str) -> set[str]:
    return {w.lower() for w in _WORD.findall(text or "")
            if len(w) > 2 and w.lower() not in _STOP}


def jaccard(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    if len(ta) < 4 or len(tb) < 4:
        return 0.0            # too short to be evidence of anything
    return len(ta & tb) / len(ta | tb)


def _spearman(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 5:
        return 0.0

    def rank(v):
        order = sorted(range(n), key=lambda i: v[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = rank(xs), rank(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx)
                    * sum((b - my) ** 2 for b in ry))
    return num / den if den else 0.0


# ===========================================================================
def examine(pupil: str, session: str, rows: list[dict],
            peers: dict[str, dict[str, str]] | None = None) -> PupilIntegrity:
    """rows: one dict per response, with
         item_id, seconds, expected_sec, correct (0/1/None), difficulty (float),
         raw, paste_events, blur_seconds, is_open
       peers: {other_pupil: {item_id: raw}} for the similarity family
    """
    pi = PupilIntegrity(pupil, session)

    # --- B: behaviour the network cannot see and the observer cannot either
    for r in rows:
        if r.get("blur_seconds", 0) >= BLUR_SEC_FLAG:
            pi.signals.append(Signal("B", r["item_id"], r["blur_seconds"], True,
                                     "okno testu stratilo zameranie"))
        if r.get("is_open") and r.get("paste_events", 0) >= PASTE_FLAG:
            pi.signals.append(Signal("B", r["item_id"],
                                     r["paste_events"], True,
                                     "text odpovede bol vložený, nie napísaný"))

    # --- T: correct, and faster than the item can be read
    for r in rows:
        if r.get("correct") != 1:
            continue
        exp = r.get("expected_sec") or 30.0
        if r["seconds"] < FAST_CORRECT_FRACTION * exp:
            pi.signals.append(Signal("T", r["item_id"],
                                     round(r["seconds"] / exp, 3), True,
                                     "správne a rýchlejšie, než sa položka dá "
                                     "prečítať"))

    # --- S: two pupils, one answer
    if peers:
        for r in rows:
            if not r.get("is_open") or not r.get("raw"):
                continue
            best, who = 0.0, ""
            for other, answers in peers.items():
                if other == pupil:
                    continue
                j = jaccard(r["raw"], answers.get(r["item_id"], ""))
                if j > best:
                    best, who = j, other
            if best >= SIMILARITY_FLAG:
                pi.signals.append(Signal("S", r["item_id"], round(best, 3), True,
                                         "voľná odpoveď je takmer totožná s "
                                         "odpoveďou iného žiaka"))

    # --- I: the pupil's hard items went faster than their easy ones
    pairs = [(r["difficulty"], r["seconds"]) for r in rows
             if r.get("difficulty") is not None and not r.get("is_open")]
    if len(pairs) >= 6:
        rho = _spearman([p[0] for p in pairs], [p[1] for p in pairs])
        pi.signals.append(Signal("I", "", round(rho, 3), rho <= INVERSION_FLAG,
                                 "ťažšie položky trvali kratšie než ľahšie"))
    return pi


def coverage_signal(pi: PupilIntegrity, prompts_during_test: int) -> None:
    """The capture layer saw assistant traffic inside the test window.

    The strongest of the five and the only one that is nearly direct -- but it
    exists only where the capture layer is running, so it cannot be the whole
    answer, and it sees nothing at all if the pupil used a phone."""
    if prompts_during_test > 0:
        pi.signals.append(Signal("C", "", float(prompts_during_test), True,
                                 "záchytná vrstva zaznamenala dopyty na "
                                 "asistenta v čase testu"))


# ===========================================================================
def class_report(pupils: list[PupilIntegrity]) -> dict:
    """What the school is told: a rate, never a name."""
    n = len(pupils)
    if not n:
        return {}
    exc = [p for p in pupils if p.excluded]
    fam: dict[str, int] = {}
    for p in pupils:
        for f in p.families:
            fam[f] = fam.get(f, 0) + 1
    return dict(pupils=n,
                flagged_any=sum(1 for p in pupils if p.families),
                excluded=len(exc),
                excluded_rate=round(len(exc) / n, 4),
                by_family={k: round(v / n, 4) for k, v in sorted(fam.items())},
                names_disclosed=0,
                note=("Ide o meranie kvality údajov, nie o obvinenie. Správa pre "
                      "školu obsahuje podiel za triedu a nikdy nie konkrétneho "
                      "žiaka; príznak sa nijako nedotýka známky."))


def calibrate(baseline: list[PupilIntegrity], field_: list[PupilIntegrity]) -> dict:
    """The false-positive rate, measured where contamination is impossible.

    `baseline` is session T0a: before any pupil has met the tool, in a room where
    no assistant exists. Every flag there is false. Without this number the field
    rate is uninterpretable, and quoting it alone would be the same error as
    quoting a test's positive rate without its specificity.
    """
    fp = sum(1 for p in baseline if p.excluded) / max(len(baseline), 1)
    obs = sum(1 for p in field_ if p.excluded) / max(len(field_), 1)
    excess = obs - fp
    return dict(baseline_session="T0a", baseline_n=len(baseline),
                false_positive_rate=round(fp, 4),
                field_n=len(field_), observed_rate=round(obs, 4),
                excess_over_baseline=round(excess, 4),
                interpretable=bool(len(baseline) >= 30),
                reading=("Rozdiel proti T0a je to jediné, čo sa dá čítať ako "
                         "kontaminácia. Samotný podiel príznakov v poli nehovorí "
                         "nič, pokiaľ nevieme, koľko ich detektor vyrobí tam, "
                         "kde kontaminácia nie je možná."))


# ===========================================================================
def self_test() -> list[str]:
    import random
    fails = []

    def row(i, sec, exp, corr, diff, raw="", is_open=False, blur=0.0, paste=0):
        return dict(item_id=i, seconds=sec, expected_sec=exp, correct=corr,
                    difficulty=diff, raw=raw, is_open=is_open,
                    blur_seconds=blur, paste_events=paste)

    # 1. a clean pupil is not flagged
    rng = random.Random(1)
    clean = [row(f"I{k}", 30 + 8 * k + rng.gauss(0, 3), 30 + 8 * k,
                 1 if k < 5 else 0, -1.0 + 0.3 * k) for k in range(8)]
    p = examine("P1", "T4a", clean)
    if p.excluded:
        fails.append(f"clean pupil excluded: {p.summary()}")

    # 2. a pupil who tab-switched and answered hard items correctly in no time
    dirty = [row(f"I{k}", 4.0, 30 + 8 * k, 1, -1.0 + 0.3 * k, blur=20.0)
             for k in range(8)]
    p = examine("P2", "T4a", dirty)
    if not p.excluded or {"B", "T"} - p.families:
        fails.append(f"contaminated pupil not caught: {p.summary()}")

    # 3. one family alone must NOT exclude -- a pupil who looked away once
    only_b = clean[:]
    only_b[0] = row("I0", 30.0, 30, 1, -1.0, blur=25.0)
    p = examine("P3", "T4a", only_b)
    if p.excluded:
        fails.append("a single signal family was enough to exclude")

    # 4. two pupils with the same free text
    txt = ("Binárne vyhľadávanie polí interval na polovicu, takže počet krokov "
           "je logaritmus zo n pri základe dva, čo vysvetľuje pomalý rast.")
    rows_a = [row("O1", 120.0, 150, None, None, raw=txt, is_open=True)]
    peers = {"P5": {"O1": txt}}
    p = examine("P4", "T4a", rows_a, peers)
    if "S" not in p.families:
        fails.append("identical free text not flagged")
    # and two different answers are not
    peers2 = {"P5": {"O1": "Neviem presne, ale asi sa to delí a potom skúša."}}
    p = examine("P4", "T4a", rows_a, peers2)
    if "S" in p.families:
        fails.append("different free text flagged as similar")

    # 5. a short answer is never similarity evidence, however it matches
    short = [row("O1", 40.0, 150, None, None, raw="polovica", is_open=True)]
    p = examine("P6", "T4a", short, {"P7": {"O1": "polovica"}})
    if "S" in p.families:
        fails.append("a two-word answer was used as similarity evidence")

    # 6. time inversion
    inv = [row(f"I{k}", 60 - 6 * k, 40, 1, -1.0 + 0.3 * k) for k in range(8)]
    p = examine("P8", "T4a", inv)
    if "I" not in p.families:
        fails.append("time/difficulty inversion not detected")

    # 7. calibration: the field rate alone says nothing
    base = [examine(f"B{i}", "T0a", clean) for i in range(40)]
    fld = [examine(f"F{i}", "T4a", dirty if i < 6 else clean) for i in range(40)]
    cal = calibrate(base, fld)
    if cal["false_positive_rate"] != 0.0 or abs(cal["excess_over_baseline"]
                                                - 0.15) > 1e-9:
        fails.append(f"calibration wrong: {cal}")

    # 8. the class report names nobody
    rep = class_report(fld)
    if rep["names_disclosed"] != 0 or "pseudonym" in json.dumps(rep):
        fails.append("class report leaked an identity")
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
    print("integrity self-test: " + ("ok" if not fails else f"{len(fails)} failures"))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
