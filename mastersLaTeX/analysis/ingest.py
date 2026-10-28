"""ingest.py -- the contract between a Slovak classroom and the analysis.

Why this exists
---------------
Appendix F says what data each session produces. Saying is not enforcing. The
failure mode in school research is specific and expensive: a column is missing,
a code is mistyped, a consent flag never arrives -- and none of it surfaces
until analysis, months later, when the school is unreachable and the pupils have
moved on. At that point a fixable clerical error has become permanent missing
data.

So the schema is machine-readable and the validator runs ON COLLECTION DAY,
against the files from that session, while the teacher is still in the room.
Every message it produces names the file, the row, and what to do about it.

Design rules
------------
1. VALIDATE EARLY, NOT WELL. A cheap check run the same afternoon beats an
   exhaustive check run in March.
2. REFUSE TO GUESS. An unparseable value is an error, never a silent NaN. The
   one exception is the trait covariate, where a missing value is expected and
   imputable -- and that exception is declared in the schema, not decided in
   code.
3. FIELD READINESS IS A DIFFERENT QUESTION FROM VALIDITY. A file can be
   perfectly well-formed and still describe a session that must be discarded:
   consent below the floor, fidelity below the floor, capture coverage too low.
   Those are reported separately and loudly, because they change what happens
   next week rather than what happens in the analysis.

Run:  python ingest.py --check <dir>      validate a session's files
      python ingest.py                    self-test on generated fixtures
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from console import use_utf8

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)

CONDITIONS = ("K", "G", "A")
SESSIONS = ("T0a", "T0b", "P1", "P2", "P3", "T4", "T6")

# Thresholds from Appendix F. They live here, once, so the protocol and the
# validator cannot drift apart.
CONSENT_FLOOR = 0.85        # below this a class is not enrolled
FIDELITY_FLOOR = 0.90       # below this a block goes to sensitivity analysis
COVERAGE_FLOOR = 0.80       # capture-layer agreement with the client's own log


# ===========================================================================
@dataclass
class Column:
    name: str
    kind: str                       # id | int | float | enum | bool | iso8601
    required: bool = True
    allowed: tuple = ()
    lo: float | None = None
    hi: float | None = None
    note: str = ""


@dataclass
class FileSpec:
    filename: str
    produced_by: str
    columns: list[Column]
    key: tuple[str, ...]
    note: str = ""
    optional: bool = False


PSEUDONYM = Column(
    "pseudonym", "id",
    note="16 hex characters: the school code hashed with the school's salt. "
         "A value that looks like a name or a birth number is a protocol "
         "breach, not a formatting problem.")

SCHEMA: list[FileSpec] = [
    FileSpec(
        "roster.csv", "school contact, once",
        [PSEUDONYM,
         Column("klass", "id"),
         Column("sequence", "enum", allowed=("KGA", "KAG", "GKA", "GAK",
                                             "AKG", "AGK")),
         Column("consent_guardian", "bool"),
         Column("consent_pupil", "bool"),
         Column("birth_year", "int", required=False, lo=2000, hi=2020,
                note="year only; a full date would be identifying")],
        key=("pseudonym",),
        note="The only file that links a pupil to a sequence. Contains no name."),
    FileSpec(
        "responses.csv", "test delivery, every session",
        [PSEUDONYM,
         Column("session", "enum", allowed=SESSIONS),
         Column("instrument", "enum",
                allowed=("ICAR", "IBOBOR", "PRECHECK", "IPT", "DRT", "TT",
                         "JRMAI", "BACKGROUND")),
         Column("item_id", "id"),
         Column("response", "id", note="raw response; scored downstream"),
         Column("correct", "int", required=False, allowed=(0, 1),
                note="absent for questionnaires, which have no correct answer"),
         Column("jol", "int", required=False, lo=0, hi=100,
                note="confidence slider; present only where the item carries one"),
         Column("seconds", "float", lo=0, hi=3600),
         Column("timestamp", "iso8601")],
        key=("pseudonym", "session", "instrument", "item_id")),
    FileSpec(
        "fidelity.csv", "researcher, each teaching block",
        [Column("klass", "id"),
         Column("period", "int", lo=1, hi=3),
         Column("cond", "enum", allowed=CONDITIONS),
         Column("steps_planned", "int", lo=1, hi=40),
         Column("steps_delivered", "int", lo=0, hi=40),
         Column("minutes_lesson", "float", lo=0, hi=180),
         Column("incident", "id", required=False,
                note="free text, researcher-written: no pupil data")],
        key=("klass", "period")),
    FileSpec(
        "coverage.csv", "derived, each teaching block",
        [PSEUDONYM,
         Column("period", "int", lo=1, hi=3),
         Column("prompts_client", "int", lo=0, hi=500),
         Column("prompts_captured", "int", lo=0, hi=500)],
        key=("pseudonym", "period"),
        note="Disagreement between the two counts is how off-device use is "
             "detected. It is a measurement, not an accusation."),
    FileSpec(
        "events.jsonl", "exercise client, each AI block",
        [],  # validated structurally rather than by column
        key=(),
        note="JSON Lines, same format the capture layer writes.",
        optional=True),
]


# ===========================================================================
class Report:
    """Errors block analysis; warnings do not. Both name a file and a row."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.notes: list[str] = []

    def error(self, where: str, msg: str) -> None:
        self.errors.append(f"{where}: {msg}")

    def warn(self, where: str, msg: str) -> None:
        self.warnings.append(f"{where}: {msg}")

    def note(self, msg: str) -> None:
        self.notes.append(msg)

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict:
        return {"ok": self.ok, "n_errors": len(self.errors),
                "n_warnings": len(self.warnings),
                "errors": self.errors[:40], "warnings": self.warnings[:40],
                "notes": self.notes}

    def print(self) -> None:
        for n in self.notes:
            print(f"  .    {n}")
        for w in self.warnings:
            print(f"  warn {w}")
        for e in self.errors:
            print(f"  ERR  {e}")
        print(f"\n{'OK' if self.ok else 'NOT USABLE'}: "
              f"{len(self.errors)} errors, {len(self.warnings)} warnings")


def _check_column(df: pd.DataFrame, c: Column, fname: str, rep: Report) -> None:
    if c.name not in df.columns:
        if c.required:
            rep.error(fname, f"missing required column '{c.name}'")
        return
    s = df[c.name]

    if c.required and s.isna().any():
        rows = list(df.index[s.isna()][:5] + 2)      # +2: header plus 1-based
        rep.error(fname, f"'{c.name}' is empty in rows {rows}")

    v = s.dropna()
    if c.kind == "int":
        bad = v[~v.astype(str).str.fullmatch(r"-?\d+")]
        if len(bad):
            rep.error(fname, f"'{c.name}' must be whole numbers; "
                             f"found {list(bad.unique()[:3])}")
            return
        v = v.astype(int)
    elif c.kind == "float":
        v = pd.to_numeric(v, errors="coerce")
        if v.isna().any():
            rep.error(fname, f"'{c.name}' must be numeric")
            return
    elif c.kind == "bool":
        bad = set(v.astype(str).str.lower()) - {"true", "false", "0", "1",
                                                "ano", "nie"}
        if bad:
            rep.error(fname, f"'{c.name}' must be true/false; found {sorted(bad)[:3]}")
    elif c.kind == "enum":
        bad = sorted(set(v.astype(str)) - set(map(str, c.allowed)))
        if bad:
            rep.error(fname, f"'{c.name}' has values outside the allowed set: "
                             f"{bad[:5]} (allowed: {list(c.allowed)})")
    elif c.kind == "iso8601":
        parsed = pd.to_datetime(v, errors="coerce", format="mixed", utc=True)
        if parsed.isna().any():
            rep.error(fname, f"'{c.name}' is not an ISO-8601 timestamp")
    elif c.kind == "id" and c.name == "pseudonym":
        bad = v[~v.astype(str).str.fullmatch(r"[0-9a-f]{16}")]
        if len(bad):
            rep.error(fname,
                      f"'pseudonym' must be 16 hex characters -- found "
                      f"{list(bad.astype(str).unique()[:3])}. If these are "
                      f"names or school codes, the salt was not applied and "
                      f"the file must not leave the school.")

    if c.allowed and c.kind in ("int",):
        bad = sorted(set(v) - set(c.allowed))
        if bad:
            rep.error(fname, f"'{c.name}' allows {list(c.allowed)}; found {bad[:5]}")
    if c.lo is not None and len(v) and pd.to_numeric(v, errors="coerce").min() < c.lo:
        rep.error(fname, f"'{c.name}' below the allowed minimum {c.lo}")
    if c.hi is not None and len(v) and pd.to_numeric(v, errors="coerce").max() > c.hi:
        rep.error(fname, f"'{c.name}' above the allowed maximum {c.hi}")


def validate_directory(path: str | Path) -> Report:
    """Validate one session's collected files. Runnable the same afternoon."""
    d = Path(path)
    rep = Report()
    if not d.is_dir():
        rep.error(str(d), "not a directory")
        return rep

    frames: dict[str, pd.DataFrame] = {}
    for spec in SCHEMA:
        f = d / spec.filename
        if not f.exists():
            if not spec.optional:
                rep.error(spec.filename,
                          f"missing -- produced by: {spec.produced_by}")
            continue
        if spec.filename.endswith(".jsonl"):
            bad = 0
            for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    json.loads(line)
                except json.JSONDecodeError:
                    bad += 1
                    if bad <= 3:
                        rep.error(spec.filename, f"line {i} is not valid JSON")
            if bad:
                rep.note(f"{spec.filename}: {bad} malformed lines")
            continue

        try:
            df = pd.read_csv(f, dtype=str, keep_default_na=True)
        except Exception as e:                        # noqa: BLE001
            rep.error(spec.filename, f"cannot be read as CSV: {e}")
            continue
        frames[spec.filename] = df
        for c in spec.columns:
            _check_column(df, c, spec.filename, rep)

        if spec.key and all(k in df.columns for k in spec.key):
            dup = df.duplicated(subset=list(spec.key), keep=False)
            if dup.any():
                rows = list(df.index[dup][:5] + 2)
                rep.error(spec.filename,
                          f"duplicate rows for key {spec.key} at rows {rows}")

    _cross_file_checks(frames, rep)
    return rep


def _cross_file_checks(frames: dict[str, pd.DataFrame], rep: Report) -> None:
    """The checks that matter most, because no single file can catch them."""
    roster = frames.get("roster.csv")
    resp = frames.get("responses.csv")
    if roster is None or resp is None:
        return

    known = set(roster["pseudonym"]) if "pseudonym" in roster else set()
    seen = set(resp["pseudonym"]) if "pseudonym" in resp else set()

    orphan = sorted(seen - known)
    if orphan:
        rep.error("responses.csv",
                  f"{len(orphan)} pseudonyms are not in the roster "
                  f"({orphan[:3]}). Either the roster is incomplete or a code "
                  f"was mistyped at the keyboard -- both are fixable today and "
                  f"neither is fixable in March.")

    # Data from a pupil without consent is the one error that cannot be
    # corrected afterwards: it should never have been recorded.
    if {"consent_guardian", "consent_pupil"} <= set(roster.columns):
        def truthy(s):
            return s.astype(str).str.lower().isin(("true", "1", "ano"))
        consented = set(roster.loc[truthy(roster["consent_guardian"])
                                   & truthy(roster["consent_pupil"]),
                                   "pseudonym"])
        without = sorted(seen & (known - consented))
        if without:
            rep.error("responses.csv",
                      f"{len(without)} pupils have responses but no complete "
                      f"consent ({without[:3]}). These rows must be deleted, "
                      f"not analysed.")
        if known:
            rate = len(consented) / len(known)
            rep.note(f"consent coverage {rate:.0%} "
                     f"({len(consented)}/{len(known)})")
            if rate < CONSENT_FLOOR:
                rep.warn("roster.csv",
                         f"consent coverage {rate:.0%} is below the "
                         f"{CONSENT_FLOOR:.0%} floor: this class is not "
                         f"enrolled (Appendix F)")

    # A JOL on an item that has no correct answer is a delivery bug: the slider
    # was shown on a questionnaire.
    if {"instrument", "jol"} <= set(resp.columns):
        q = resp[resp["instrument"].isin(("JRMAI", "BACKGROUND"))]
        if q["jol"].notna().any():
            rep.error("responses.csv",
                      "a confidence slider was recorded on a questionnaire "
                      "item; the slider belongs only on scored items")

    fid = frames.get("fidelity.csv")
    if fid is not None and {"steps_planned", "steps_delivered"} <= set(fid.columns):
        p = pd.to_numeric(fid["steps_planned"], errors="coerce")
        dv = pd.to_numeric(fid["steps_delivered"], errors="coerce")
        ratio = (dv / p).replace([np.inf, -np.inf], np.nan)
        for i, r in ratio.items():
            if pd.notna(r) and r > 1.0:
                rep.error("fidelity.csv",
                          f"row {i + 2}: more steps delivered than planned")
            elif pd.notna(r) and r < FIDELITY_FLOOR:
                rep.warn("fidelity.csv",
                         f"row {i + 2}: fidelity {r:.0%} is below the "
                         f"{FIDELITY_FLOOR:.0%} floor; this block goes to the "
                         f"sensitivity analysis")

    cov = frames.get("coverage.csv")
    if cov is not None and {"prompts_client", "prompts_captured"} <= set(cov.columns):
        c1 = pd.to_numeric(cov["prompts_client"], errors="coerce")
        c2 = pd.to_numeric(cov["prompts_captured"], errors="coerce")
        with np.errstate(invalid="ignore", divide="ignore"):
            rate = np.where(c1 > 0, c2 / c1, np.nan)
        usable = rate[~np.isnan(rate)]
        if usable.size:
            share = float((usable >= COVERAGE_FLOOR).mean())
            rep.note(f"capture coverage adequate for {share:.0%} of pupil-blocks")
            if share < 0.9:
                rep.warn("coverage.csv",
                         f"only {share:.0%} of pupil-blocks reach the "
                         f"{COVERAGE_FLOOR:.0%} coverage floor; flag the rest "
                         f"and run the sensitivity analysis without them")


# ===========================================================================
def make_fixture(path: Path, broken: str | None = None) -> None:
    """Write a small, valid collection -- or one broken in a named way.

    The fixtures exist so the validator is tested against the errors it claims
    to catch. A validator that has only ever seen correct data is an assertion.
    """
    path.mkdir(parents=True, exist_ok=True)
    pseudos = [f"{i:016x}" for i in range(1, 13)]
    seqs = ["KGA", "KAG", "GKA", "GAK", "AKG", "AGK"]

    roster = pd.DataFrame({
        "pseudonym": pseudos,
        "klass": ["1A"] * 12,
        "sequence": [seqs[i % 6] for i in range(12)],
        "consent_guardian": ["true"] * 12,
        "consent_pupil": ["true"] * 12,
        "birth_year": [2008] * 12,
    })
    if broken == "consent":
        roster.loc[:3, "consent_guardian"] = "false"
    if broken == "pseudonym":
        roster.loc[0, "pseudonym"] = "Jozef Novak"

    rows = []
    for p in pseudos:
        for k in range(4):
            rows.append(dict(pseudonym=p, session="T0a", instrument="ICAR",
                             item_id=f"icar{k}", response=str(k % 4),
                             correct=k % 2, jol="", seconds=40.0,
                             timestamp="2026-10-07T09:00:00Z"))
    resp = pd.DataFrame(rows)
    if broken == "orphan":
        resp.loc[0, "pseudonym"] = f"{999:016x}"
    if broken == "enum":
        resp.loc[0, "instrument"] = "RAVEN"
    if broken == "duplicate":
        resp = pd.concat([resp, resp.iloc[[0]]], ignore_index=True)
    if broken == "jol_on_questionnaire":
        resp = pd.concat([resp, pd.DataFrame([dict(
            pseudonym=pseudos[0], session="T0b", instrument="JRMAI",
            item_id="m1", response="4", correct="", jol=80, seconds=8.0,
            timestamp="2026-10-07T18:00:00Z")])], ignore_index=True)
    if broken == "missing_column":
        resp = resp.drop(columns=["seconds"])

    fid = pd.DataFrame({"klass": ["1A"], "period": [1], "cond": ["A"],
                        "steps_planned": [12], "steps_delivered": [12],
                        "minutes_lesson": [75.0], "incident": [""]})
    if broken == "fidelity":
        fid.loc[0, "steps_delivered"] = 8
    if broken == "impossible_fidelity":
        fid.loc[0, "steps_delivered"] = 15

    cov = pd.DataFrame({"pseudonym": pseudos, "period": [1] * 12,
                        "prompts_client": [10] * 12,
                        "prompts_captured": [10] * 12})
    if broken == "coverage":
        cov.loc[:5, "prompts_captured"] = 3

    roster.to_csv(path / "roster.csv", index=False)
    resp.to_csv(path / "responses.csv", index=False)
    fid.to_csv(path / "fidelity.csv", index=False)
    cov.to_csv(path / "coverage.csv", index=False)
    (path / "events.jsonl").write_text(
        json.dumps({"kind": "task_shown", "pseudonym": pseudos[0]}) + "\n",
        encoding="utf-8")
    if broken == "jsonl":
        (path / "events.jsonl").write_text("{not json\n", encoding="utf-8")


def self_test() -> dict:
    """Every named breakage must be caught, and clean data must pass."""
    import tempfile
    results = {}
    cases = [None, "consent", "pseudonym", "orphan", "enum", "duplicate",
             "jol_on_questionnaire", "missing_column", "fidelity",
             "impossible_fidelity", "coverage", "jsonl"]
    with tempfile.TemporaryDirectory() as tmp:
        for case in cases:
            d = Path(tmp) / (case or "clean")
            make_fixture(d, case)
            rep = validate_directory(d)
            caught = (not rep.ok) or bool(rep.warnings)
            results[case or "clean"] = {
                "errors": len(rep.errors), "warnings": len(rep.warnings),
                "flagged": caught,
                "first": (rep.errors + rep.warnings)[:1],
            }
    results["clean_passes"] = (results["clean"]["errors"] == 0
                               and results["clean"]["warnings"] == 0)
    results["all_breakages_flagged"] = all(
        v["flagged"] for k, v in results.items()
        if k not in ("clean", "clean_passes", "all_breakages_flagged")
        and isinstance(v, dict))
    return results


def main(argv: list[str]) -> int:
    if len(argv) > 2 and argv[1] == "--check":
        rep = validate_directory(argv[2])
        rep.print()
        return 0 if rep.ok else 1

    res = self_test()
    print(json.dumps(res, indent=2, ensure_ascii=False))
    (OUT / "ingest_selftest.json").write_text(
        json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    ok = res["clean_passes"] and res["all_breakages_flagged"]
    print("\n" + ("schema and validator agree" if ok
                  else "VALIDATOR MISSED A BREAKAGE"))
    return 0 if ok else 1


if __name__ == "__main__":
    use_utf8()
    raise SystemExit(main(sys.argv))
