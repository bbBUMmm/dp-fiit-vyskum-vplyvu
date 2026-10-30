"""consent.py -- what the pupil is told on screen, and what follows from the answer.

The written consent (Appendix E: one form signed by the legal guardian, one by
the pupil) is the legal basis. The screen adds three things paper cannot do:

  * it says, at the start of every lesson and test, what is recorded right now
    -- Appendix E promises pupils "viditeľné upozornenie" at every lesson;
  * the pupil can say no for this sitting, or withdraw during it, without
    asking the teacher -- the power imbalance Appendix E names as a risk;
  * nothing about a pupil is written until they say yes, and a withdrawal
    deletes what this sitting recorded.

With the school's list of codes that have a signed consent (--consent-list), a
code that is not on the list is never recorded, and its pupil is told so: the
screen cannot overrule a parent's no. Without the list the screen is the only
gate, and both servers say so when they start.

Shared by the lesson server and the test runner (copied next to both in the
school kit, like linkage.py), so the two show the same words. Every decision
is logged with the VERSION of the text -- a hash of exactly what was on the
screen -- because Art. 7(1) GDPR asks the controller to be able to show what
the person agreed to.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import linkage

PENDING = "pending"     # not asked yet: nothing is written
YES = "yes"             # recorded from now on
NO = "no"               # said no, or withdrew: nothing is written
NONE = "none"           # no signed paper consent: never recorded, not asked

START = "start"         # what a decision requires the server to do
WITHDRAW = "withdraw"

_COMMON_NOT = [
    "tvoje meno — namiesto neho sa ukladá kód, ktorý k tebe vie priradiť len škola",
]
_GRADE = "Nemá to žiadny vplyv na známku. V paneli učiteľa sa tvoje rozhodnutie nezobrazuje."
_OTHER = ("Ak chceš vymazať aj údaje z iných hodín a testov, povedz to kontaktnej "
          "osobe uvedenej v písomnom súhlase. Nemusíš vysvetľovať prečo.")

_LESSON = {
    "title": "Skôr než začneš",
    "lead": ("Táto hodina je súčasťou výskumu Fakulty informatiky a informačných "
             "technológií STU o tom, ako sa žiaci učia s pomocou umelej "
             "inteligencie. Rozhodni sa, či môžeme zaznamenávať, ako pracuješ."),
    "recordedTitle": "Čo sa zaznamenáva",
    "recorded": [
        "čo napíšeš asistentovi (ak ho na hodine máš)",
        "tvoje pokusy, vysvetlenia a odpovede v interaktívnych úlohách",
        None,                                    # answer text: filled in by text()
        "časy a počty: kedy si čo otvoril/a, koľko si klikal/a a písal/a, "
        "či si kopíroval/a — bez obsahu",
        "nakoľko si si istý/á svojimi odpoveďami",
    ],
    "notRecordedTitle": "Čo sa nezaznamenáva",
    "notRecorded": _COMMON_NOT + [
        "plné znenie odpovedí asistenta",
        "nič mimo tejto stránky a nič po skončení hodiny",
    ],
    "rightsTitle": "Dôležité",
    "rights": [
        _GRADE,
        "Ak nesúhlasíš, pracuješ úplne rovnako ako ostatní — len sa o tebe nič "
        "nezaznamená.",
        "Rozhodnutie môžeš kedykoľvek zmeniť tlačidlom Súhlas hore. Ak súhlas "
        "odvoláš, všetko, čo sa o tebe na tejto hodine zaznamenalo, sa hneď vymaže.",
        _OTHER,
    ],
    "question": "Súhlasíš so záznamom na tejto hodine?",
    "where": "na tejto hodine",
}

_TEST = {
    "title": "Skôr než začneš",
    "lead": ("Tento test je súčasťou výskumu Fakulty informatiky a informačných "
             "technológií STU. Neznámkuje sa. Rozhodni sa, či môžeme zaznamenať "
             "tvoje odpovede."),
    "recordedTitle": "Čo sa zaznamenáva",
    "recorded": [
        "tvoje odpovede a to, nakoľko si si nimi istý/á",
        "koľko času strávíš pri každej položke",
        "či odídeš z okna testu alebo do odpovede vložíš text — nie, čo robíš inde",
    ],
    "notRecordedTitle": "Čo sa nezaznamenáva",
    "notRecorded": _COMMON_NOT + ["nič mimo tejto stránky"],
    "rightsTitle": "Dôležité",
    "rights": [
        _GRADE,
        "Ak nesúhlasíš, píšeš test rovnako ako ostatní — len sa tvoje odpovede "
        "neuložia.",
        "Rozhodnutie môžeš kedykoľvek zmeniť tlačidlom Súhlas hore. Ak súhlas "
        "odvoláš, odpovede z tohto testu sa hneď vymažú.",
        _OTHER,
    ],
    "question": "Súhlasíš so záznamom tohto testu?",
    "where": "v tomto teste",
}

_NO_PAPER = {
    "title": "Dnes sa o tebe nič nezaznamenáva",
    "lead": ("Pre tvoj kód nemáme podpísaný písomný súhlas, preto sa o tebe nič "
             "neukladá. Pracuj úplne normálne — všetko ti funguje rovnako ako "
             "ostatným."),
}

_BUTTONS = {
    "yes": "Súhlasím",
    "no": "Nesúhlasím",
    "continue": "Pokračovať",
}


class ConsentError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def text(scope: str, answer_text: bool = False) -> dict:
    """The words on the screen. `answer_text`: the lesson server stores the TEXT
    of answers (--log-answer-text), and the pupil has to be told."""
    if scope not in ("lesson", "test"):
        raise ValueError(f"unknown consent scope {scope!r}")
    t = json.loads(json.dumps(_LESSON if scope == "lesson" else _TEST))
    if scope == "lesson":
        t["recorded"][2] = ("text tvojich odpovedí v úlohách" if answer_text else
                            "pri odpovediach v úlohách len ich dĺžka, nie text")
    t["noPaper"] = dict(_NO_PAPER)
    t["buttons"] = dict(_BUTTONS)
    return t


def version(t: dict) -> str:
    """12 hex characters that change whenever any word of the text changes."""
    raw = json.dumps(t, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:12]


def view(scope: str, state: str, answer_text: bool = False) -> dict:
    """What the client needs to render the screen for one pupil."""
    t = text(scope, answer_text)
    return {"state": state, "version": version(t), "text": t}


def transition(current: str, choice) -> tuple[str, str | None]:
    """The new state and what the server must do about it.

    START: write the consent record, then everything the pupil does from now on.
    WITHDRAW: stop writing, keep a marker, delete what this sitting recorded.
    """
    if current == NONE:
        raise ConsentError("Pre tento kód nie je podpísaný písomný súhlas, "
                           "preto sa nič nezaznamenáva.", 403)
    if choice not in (YES, NO):
        raise ConsentError("Neplatná voľba súhlasu.")
    if choice == YES:
        return YES, (None if current == YES else START)
    return NO, (WITHDRAW if current == YES else None)


def read_list(path: str | Path) -> set[str]:
    """Codes with a signed paper consent, one per line, canonical form.

    The file holds codes only -- no names -- so like kody-XX.txt it may leave
    the school. Lines starting with # are comments.
    """
    out = set()
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.add(linkage.normalise(line))
    return out
