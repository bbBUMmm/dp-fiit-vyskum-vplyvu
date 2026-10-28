"""linkage.py -- recognising the same pupil on five occasions, without knowing who.

The problem, stated precisely
-----------------------------
The primary outcome of this study is a CHANGE: what a pupil scored at week 6
minus what the same pupil scored at week 0. Computing it requires joining five
occasions for one person. Protecting the pupil requires that the researcher
never be able to name that person. The protocol solves the second half well --
the school's contact person hands out code envelopes at T0a and is the only
person who can map a code to a pupil -- and leaves the first half to the pupil's
fingers.

That is the gap. Across 330 pupils and five occasions a code is typed about
1 650 times, by fifteen-year-olds, on school keyboards, under time pressure.
A mistyped code does not produce an error. It produces two:

    * one pupil silently loses that occasion -- and with it their change score,
      which is the quantity the study exists to measure;
    * a pupil who does not exist silently gains a row.

Both are invisible. Missing data you can see is a nuisance; missing data that
looks like data is a defect, and it is worse here than usual because the
analysis plan treats dropout as MAR and imputes it. Imputing a value for a
phantom pupil, and dropping a real pupil's occasion as absent, biases a result
in a direction nobody can sign.

The repair
----------
Three layers, each catching what the previous one cannot.

1. A CHECK CHARACTER (ISO 7064 MOD 37,36). Detects every single-character
   substitution, and -- for the codes this module issues -- every transposition
   of adjacent or near-adjacent characters. Those are the large majority of
   typing errors, and they are rejected at the keyboard, while the pupil is still
   in the room and can retype.

   The transposition half of that sentence is not a property of the standard. The
   standard is usually summarised as detecting all adjacent transpositions and it
   does not: measured exhaustively, about one in two thousand survives
   (GY-YEDET-R becomes GY-YDEET-R and both verify). Since the code space is nine
   and a half million and a school needs thirty codes, `issue()` simply refuses
   any candidate that has such a weakness, and `self_test` re-derives the
   property exhaustively on the codes actually issued. See `is_robust`.

2. A CONFUSABLE-FREE ALPHABET. Letters and digits that look alike are never
   issued: O/0, I/1/L, S/5, Z/2, B/8. A character outside the issued alphabet is
   therefore not a code at all, and the runner can say *which* mistake was made
   ("codes contain no letter O -- did you mean zero?") instead of refusing
   blankly. This converts a class of error into an instruction.

3. ONE CODE, ONE SITTING. A code already open on another machine in the same
   session is refused. This is the only layer that catches the error a check
   character provably cannot: a pupil typing someone else's *valid* code, by
   accident or otherwise. The check digit is arithmetic and cannot tell two
   legitimate codes apart.

What is deliberately NOT done
-----------------------------
No self-generated identification code (initials, mother's birth month, and so
on). Those are the usual answer when no roster exists, and they are both weaker
and worse: recall at a three-week interval is imperfect, so occasions are lost
anyway, and the components are quasi-identifiers, so the "anonymous" code is
re-identifiable by anyone holding a class list. A school-held roster is strictly
better on both counts, and this study has one.

Run:  python linkage.py             issue a class's codes and self-test
      python linkage.py --audit     the error-detection properties, measured
"""
from __future__ import annotations

import json
import random
import sys

# ISO 7064 MOD 37,36 works over 36 symbols. Verification accepts all of them;
# ISSUING uses only the safe subset, so any excluded character in an entered code
# is a typo with a known cause rather than an unknown one.
ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
CONFUSABLE = "O0I1LS5Z2B8"
SAFE = "".join(c for c in ALPHABET if c not in CONFUSABLE)   # 25 symbols

# What a confusable character was most likely meant to be. Used for the message,
# never to silently correct: a silent correction would turn a detected error into
# an undetected one, which is the whole thing this module is against.
MEANT = {"O": "0", "0": "O", "I": "1", "1": "I", "L": "1", "S": "5",
         "5": "S", "Z": "2", "2": "Z", "B": "8", "8": "B"}

BODY_LEN = 5          # random characters, 25**5 = 9 765 625 per school


class CodeError(ValueError):
    """An entered code that is not a code. Carries a message for the pupil."""


# ===========================================================================
def _check_char(body: str) -> str:
    """ISO 7064 MOD 37,36 check character for an alphanumeric body."""
    M, M1 = 36, 37
    p = M
    for ch in body:
        v = ALPHABET.index(ch)
        s = (p + v) % M
        s = M if s == 0 else s
        p = (2 * s) % M1
    final = (M1 - p) % M
    return ALPHABET[final % M]


def format_code(school: str, body: str) -> str:
    """Human-facing form: GY-K7M4P-Q. The dashes are for reading, not for data."""
    return f"{school}-{body}-{_check_char(school + body)}"


def _passes(raw: str) -> bool:
    return _check_char(raw[:-1]) == raw[-1]


def is_robust(code: str) -> bool:
    """True if NO adjacent or jump transposition of this code survives the check.

    ISO 7064 MOD 37,36 is usually described as detecting every single-character
    error and every adjacent transposition. The first half is exact; the second
    is not. Measured exhaustively over 400 issued codes, one adjacent
    transposition in roughly two thousand passes the check:

        GY-YEDET-R  ->  GY-YDEET-R        both verify

    The cause is the wrap-around in the hybrid recurrence (`s = 36 if s == 0`),
    which makes the effective multiplier repeat for one pair of positions.

    The honest options were to report 99.95% or to make it 100%. It is 100%,
    because the code space is nine and a half million and a school needs about
    thirty: at issuing time every adjacent and every jump transposition of the
    candidate is tried, and the candidate is discarded if any of them verifies.
    The property then holds by construction for every code actually in an
    envelope, and `self_test` re-derives it exhaustively rather than trusting the
    standard's summary of itself.

    Discarding costs nothing -- about one candidate in six -- and buys a
    statement that needs no asterisk.
    """
    raw = normalise(code)
    n = len(raw)
    for i in range(2, n - 2):                      # adjacent, body only
        if raw[i] == raw[i + 1]:
            continue
        if _passes(raw[:i] + raw[i + 1] + raw[i] + raw[i + 2:]):
            return False
    for i in range(2, n - 3):                      # jump: swap i and i+2
        if raw[i] == raw[i + 2]:
            continue
        sw = list(raw)
        sw[i], sw[i + 2] = sw[i + 2], sw[i]
        if _passes("".join(sw)):
            return False
    return True


def normalise(entered: str) -> str:
    """Strip what a pupil may add: spaces, dashes, lower case."""
    return "".join(entered.split()).replace("-", "").replace("—", "").upper()


def verify(entered: str, school: str | None = None) -> str:
    """Return the canonical code, or raise CodeError with a message for the pupil.

    The order of the checks is the message quality order: say the most specific
    true thing. "You typed a letter O and codes have none" is actionable;
    "invalid code" is not.
    """
    raw = normalise(entered)
    if not raw:
        raise CodeError("Kód je prázdny. Prepíš ho z obálky presne tak, ako je.")

    bad = [c for c in raw if c not in ALPHABET]
    if bad:
        raise CodeError(f"Kód obsahuje znak, ktorý v kódoch nie je: "
                        f"{', '.join(sorted(set(bad)))}. Sú v ňom len veľké "
                        f"písmená a číslice.")

    want = 2 + BODY_LEN + 1
    if len(raw) != want:
        raise CodeError(f"Kód má {want} znakov (dva písmená školy, "
                        f"{BODY_LEN} znakov a kontrolný znak). "
                        f"Ty si zadal {len(raw)}.")

    body = raw[:-1]
    if _check_char(body) != raw[-1]:
        # Name the likely cause if a confusable character is present, because
        # that is the mistake the alphabet was designed to make explicable.
        susp = [c for c in body[2:] if c in CONFUSABLE]
        hint = ""
        if susp:
            pairs = ", ".join(f"{c} -> {MEANT[c]}" for c in sorted(set(susp)))
            hint = (f" V kóde je znak, ktorý sa nikdy nepoužíva, a ľahko sa "
                    f"zamieňa: {pairs}. Skontroluj ho.")
        raise CodeError("Kód nesedí — niekde je preklep. Prepíš ho ešte raz, "
                        "znak po znaku." + hint)

    if school is not None and raw[:2] != school.upper():
        raise CodeError(f"Tento kód nie je z tejto školy ({school.upper()}). "
                        f"Skontroluj, či máš svoju obálku.")
    return raw


# ===========================================================================
def issue(school: str, n: int, seed: int | None = None) -> list[str]:
    """Issue n distinct codes for one school.

    Uniqueness is guaranteed by construction rather than left to probability.
    With 330 pupils drawn at random from 25**5 the chance of at least one
    collision is about 0.6% -- small, and there is no reason to accept it when
    the issuing step is centralised and can simply check.
    """
    school = school.upper()
    if len(school) != 2 or any(c not in SAFE for c in school):
        raise ValueError(f"school code {school!r} must be 2 safe characters")
    rng = random.Random(seed)
    seen: set[str] = set()
    out = []
    while len(out) < n:
        body = "".join(rng.choice(SAFE) for _ in range(BODY_LEN))
        if body in seen:
            continue
        # The check character is typed by the pupil like every other character,
        # so it has to come from the safe alphabet as well. ISO 7064 computes it,
        # it is not chosen -- so the body is redrawn until the computed character
        # is safe. About 31% of draws are rejected; the arithmetic is untouched,
        # only the issued subset is smaller.
        if _check_char(school + body) not in SAFE:
            continue
        code = format_code(school, body)
        # and the local-error property holds for THIS code, not on average
        if not is_robust(code):
            continue
        seen.add(body)
        out.append(code)
    return out


def acceptance_rate(school: str = "GY", draws: int = 4000, seed: int = 5) -> dict:
    """How much of the code space survives both issuing filters. Reported so the
    cost of the guarantee is visible rather than assumed negligible."""
    rng = random.Random(seed)
    safe_check = robust = 0
    for _ in range(draws):
        body = "".join(rng.choice(SAFE) for _ in range(BODY_LEN))
        if _check_char(school + body) not in SAFE:
            continue
        safe_check += 1
        if is_robust(format_code(school, body)):
            robust += 1
    return dict(draws=draws,
                check_char_safe=round(safe_check / draws, 4),
                also_transposition_robust=round(robust / draws, 4),
                usable_codes_per_school=int(len(SAFE) ** BODY_LEN * robust / draws))


# ===========================================================================
def audit(n_codes: int = 330, trials: int = 20000, seed: int = 7) -> dict:
    """Measure what the scheme actually detects, rather than citing the standard.

    The quantity that matters for the study is not "does the check character
    work" but: of the mistyped codes that slip through, how many land on a code
    issued to ANOTHER PUPIL -- because only those produce the silent two-error
    case. A mistyped code that is merely invalid is a pupil retyping, which costs
    seconds.
    """
    rng = random.Random(seed)
    codes = issue("GY", n_codes, seed=seed)
    issued = {normalise(c) for c in codes}

    def mutate(raw: str, kind: str) -> str:
        s = list(raw)
        # never touch the two school characters: a pupil reads them off the room
        lo, hi = 2, len(s) - 1          # body only; the check char is copied
        if kind == "sub":
            i = rng.randrange(lo, hi)
            alt = [c for c in SAFE if c != s[i]]
            s[i] = rng.choice(alt)
        elif kind == "trans":
            i = rng.randrange(lo, hi - 1)
            if s[i] == s[i + 1]:
                return "".join(s)        # a transposition of equal characters
            s[i], s[i + 1] = s[i + 1], s[i]
        elif kind == "sub2":
            idx = rng.sample(range(lo, hi), 2)
            for i in idx:
                alt = [c for c in SAFE if c != s[i]]
                s[i] = rng.choice(alt)
        elif kind == "jump":                 # two apart: K7M4P -> K4M7P
            i = rng.randrange(lo, hi - 2)
            if s[i] == s[i + 2]:
                return "".join(s)
            s[i], s[i + 2] = s[i + 2], s[i]
        return "".join(s)

    res = {}
    for kind in ("sub", "trans", "sub2", "jump"):
        caught = effective = collisions = 0
        for _ in range(trials):
            raw = normalise(rng.choice(codes))
            bad = mutate(raw, kind)
            if bad == raw:
                continue
            effective += 1
            try:
                verify(bad, "GY")
                if bad in issued:
                    collisions += 1          # the silent two-error case
            except CodeError:
                caught += 1
        res[kind] = dict(
            trials=effective,
            detected=round(caught / max(effective, 1), 4),
            undetected=effective - caught,
            hit_another_pupil=collisions)

    # What the whole study expects, from a per-character typing error rate.
    # 1650 entries = 330 pupils x 5 occasions; a code body is 6 characters typed.
    per_char = 0.01                 # 1% per character is pessimistic for 6 chars
    entries, chars = n_codes * 5, BODY_LEN + 1
    p_any_error = 1 - (1 - per_char) ** chars
    p_single = chars * per_char * (1 - per_char) ** (chars - 1)
    p_multi = p_any_error - p_single
    undetected_rate = 1 - res["sub2"]["detected"]
    expected_phantoms = entries * p_multi * undetected_rate
    # and the chance such a survivor is another pupil's code
    p_issued = n_codes / (len(SAFE) ** BODY_LEN)

    res["study_level"] = dict(
        entries=entries,
        per_char_error_rate=per_char,
        p_entry_has_any_error=round(p_any_error, 4),
        p_entry_has_single_error=round(p_single, 4),
        single_errors_all_detected=res["sub"]["detected"] == 1.0
                                   and res["trans"]["detected"] == 1.0,
        expected_undetected_entries=round(expected_phantoms, 2),
        p_a_survivor_is_another_pupils_code=round(p_issued, 9),
        expected_merged_pupils=round(expected_phantoms * p_issued, 9),
        reading=("Jednoznakové preklepy a prehodenia susedných znakov sa "
                 "zachytia všetky, takže ich žiak prepíše ešte v triede. "
                 "Nezachytia sa len viacznakové chyby, a aj z tých musí "
                 "výsledok padnúť presne na kód iného žiaka, aby vznikol ten "
                 "tichý dvojnásobný prípad — očakávaný počet za celú štúdiu je "
                 "rádovo stotisíckrát menší než jeden žiak. Bez kontrolného "
                 "znaku by naopak každá jednoznaková chyba, teda väčšina "
                 "všetkých, prešla bez stopy."))
    res["without_check_character"] = dict(
        expected_undetected_entries=round(entries * p_any_error, 2),
        reading=("Pre porovnanie: bez kontrolného znaku prejde nepozorovane "
                 "každá chyba, teda očakávane desiatky záznamov."))
    return res


# ===========================================================================
def self_test() -> list[str]:
    fails = []
    codes = issue("GY", 50, seed=1)
    for c in codes:
        if verify(c, "GY") != normalise(c):
            fails.append(f"round trip failed for {c}")
    # the issued alphabet really excludes confusables
    for c in codes:
        if any(ch in CONFUSABLE for ch in normalise(c)[2:]):
            fails.append(f"issued code contains a confusable: {c}")
    # the transposition property, re-derived exhaustively on the issued codes
    for c in codes:
        if not is_robust(c):
            fails.append(f"issued code is not transposition-robust: {c}")
    # messages, not blank refusals
    for bad, expect in [("", "prázdny"), ("GY-K7M4O-Q", ""), ("GY-K7M4", "znakov")]:
        try:
            verify(bad, "GY")
            fails.append(f"accepted {bad!r}")
        except CodeError as e:
            if expect and expect not in str(e):
                fails.append(f"message for {bad!r} lacks {expect!r}: {e}")
    return fails


def main(argv: list[str]) -> int:
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    fails = self_test()
    if fails:
        print("SELF-TEST FAILED")
        for f in fails:
            print("  - " + f)
        return 1

    if "--audit" in argv:
        print(json.dumps(audit(), indent=2, ensure_ascii=False))
        return 0

    print(f"alphabet: {SAFE}  ({len(SAFE)} symbols, confusables excluded)")
    print(f"code space per school: {len(SAFE) ** BODY_LEN:,}\n")
    print("ukážka kódov pre školu GY:")
    for c in issue("GY", 8, seed=42):
        print("   " + c)
    a = audit(trials=4000)
    print(f"\nsingle-character substitution detected: {a['sub']['detected']:.1%}")
    print(f"adjacent transposition detected:        {a['trans']['detected']:.1%}")
    print(f"two-character error detected:           {a['sub2']['detected']:.1%}")
    print(f"expected silently merged pupils in the whole study: "
          f"{a['study_level']['expected_merged_pupils']:.2e}")
    print("self-test ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
