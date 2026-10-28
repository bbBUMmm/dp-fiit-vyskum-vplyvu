"""scrub.py -- removal of personal data from captured prompt text.

Design notes
------------
Free text written by minors cannot be reliably anonymised, only reduced in risk.
This module therefore does two things and claims nothing more:

  1. Pattern removal for identifiers that have a reliable surface form
     (e-mail, phone, Slovak birth number, IBAN, bearer-style tokens, URLs).
  2. Roster removal: the school supplies the list of names of the pupils in the
     participating classes, and every occurrence of those names -- in any Slovak
     case ending -- is replaced.  This is the part that actually matters, and it
     is why the roster never leaves the school and is passed in at run time.

Everything the module removes is counted, and the counts travel with the record,
so the thesis can report how much was removed rather than asserting that nothing
was missed.  The residual risk (a pupil naming a classmate not on the roster, or
describing themselves identifiably) is stated in the DPIA, not hidden here.

The module is deliberately dependency-free so it can run inside a mitmproxy
addon, inside a test, or as a post-hoc re-scrub of an already captured corpus.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

PLACEHOLDER = {
    "email": "[EMAIL]",
    "phone": "[TELEFON]",
    "birth_number": "[RODNE_CISLO]",
    "iban": "[IBAN]",
    "token": "[TOKEN]",
    "url": "[URL]",
    "name": "[MENO]",
    "long_digits": "[CISLO]",
}

# --- patterns ---------------------------------------------------------------
# Ordered: the more specific patterns run first so that, for example, a birth
# number is not first eaten by the generic long-digit rule.
PATTERNS: list[tuple[str, re.Pattern]] = [
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    # Slovak birth number: 6 digits, slash, 3 or 4 digits
    ("birth_number", re.compile(r"\b\d{6}\s?/\s?\d{3,4}\b")),
    ("iban", re.compile(r"\b[A-Z]{2}\d{2}[ ]?(?:[A-Z0-9]{4}[ ]?){2,7}[A-Z0-9]{1,4}\b")),
    # +421 903 123 456, 0903 123 456, 02/1234 5678 -- prefix plus 8 to 9 further
    # digits with arbitrary separators; the lookarounds stop it from biting into
    # a longer digit run, which the long_digits rule handles instead.
    ("phone", re.compile(r"(?<!\d)(?:\+421|00421|0)[\s/-]?\d(?:[\s/-]?\d){7,8}(?!\d)")),
    ("token", re.compile(r"\b(?:sk-|ey[JI]|Bearer\s+)[A-Za-z0-9._\-]{16,}")),
    ("url", re.compile(r"https?://[^\s<>\"']+")),
    # any remaining run of 9+ digits (student IDs, card numbers, ISIC, ...)
    ("long_digits", re.compile(r"(?<!\d)\d{9,}(?!\d)")),
]

# Slovak case endings that may follow a name stem.  Matching a stem plus an
# optional ending catches "Mykytovi", "Prykhodkovi", "Zuzane" without a
# morphological analyser.  Longer endings must come first so the alternation
# prefers them.
_NAME_SUFFIX = (r"(?:ovcov|ovej|ovci|ovi|ove|ami|och|ou|om|mi|ka|ke|ku|kou|ko"
                r"|a|e|i|y|u|o)?")


def _stem(folded: str) -> str:
    """Drop one trailing vowel so that "zuzana" also matches "zuzane".

    Over-stripping is the safe direction here: a stem that is too short only
    causes over-removal, which is visible in the counts, whereas a stem that is
    too long silently leaves a name in the corpus.  Names of three characters or
    fewer are left intact so that the word boundary still carries the work.
    """
    if len(folded) > 3 and folded[-1] in "aeiouy":
        return folded[:-1]
    return folded


def _fold(text: str) -> str:
    """Lowercase and strip diacritics, for accent-insensitive matching."""
    t = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


@dataclass
class ScrubResult:
    text: str
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def removed(self) -> int:
        return sum(self.counts.values())


class Scrubber:
    """Reusable scrubber.  Build once per capture session with the class roster."""

    def __init__(self, roster: list[str] | None = None, min_name_len: int = 3):
        self.min_name_len = min_name_len
        self._name_re = self._build_roster_regex(roster or [])

    def _build_roster_regex(self, roster: list[str]) -> re.Pattern | None:
        stems: set[str] = set()
        for full in roster:
            for part in re.split(r"[\s,;]+", full.strip()):
                if len(part) >= self.min_name_len:
                    stems.add(re.escape(_stem(_fold(part))))
        if not stems:
            return None
        longest_first = sorted(stems, key=len, reverse=True)
        return re.compile(r"\b(?:" + "|".join(longest_first) + r")" + _NAME_SUFFIX + r"\b")

    def scrub(self, text: str) -> ScrubResult:
        if not text:
            return ScrubResult("", {})
        counts: dict[str, int] = {}
        out = text

        for label, pat in PATTERNS:
            out, n = pat.subn(PLACEHOLDER[label], out)
            if n:
                counts[label] = counts.get(label, 0) + n

        if self._name_re is not None:
            out, n = self._scrub_names(out)
            if n:
                counts["name"] = n

        return ScrubResult(out, counts)

    def _scrub_names(self, text: str) -> tuple[str, int]:
        """Match on the accent-folded text but splice the original string, so
        that the surrounding text keeps its diacritics untouched."""
        folded = _fold(text)
        # folding is length-preserving for Slovak (NFKD combining marks are
        # dropped one-for-one only where they were separate code points), so
        # verify before trusting offsets
        if len(folded) != len(text):
            # fall back to the safe but lossy route
            new, n = self._name_re.subn(PLACEHOLDER["name"], folded)
            return new, n
        spans = [m.span() for m in self._name_re.finditer(folded)]
        if not spans:
            return text, 0
        pieces, last = [], 0
        for a, b in spans:
            pieces.append(text[last:a])
            pieces.append(PLACEHOLDER["name"])
            last = b
        pieces.append(text[last:])
        return "".join(pieces), len(spans)


def scrub(text: str, roster: list[str] | None = None) -> ScrubResult:
    """Convenience wrapper for one-off use."""
    return Scrubber(roster).scrub(text)
