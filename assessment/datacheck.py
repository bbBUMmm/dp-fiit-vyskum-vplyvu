"""datacheck.py -- the same-afternoon check of a school kit's data folder.

The kit promised a check on collection day ("kontrola\\SKONTROLUJ.cmd ... the
most important step of the whole procedure") and shipped `analysis/ingest.py`
for it. That could never run in the kit: it imports numpy and pandas, which a
locked-down school laptop does not have, and a `console` module the kit did not
copy -- and it validates roster.csv, responses.csv, fidelity.csv and
coverage.csv, none of which the kit produces. The step that was meant to catch
errors while the class is still reachable failed on every machine, every time.

This checker reads what the kit actually writes:

    events_<hodina>.jsonl        the lesson (exercise client)
    odpovede_<stretnutie>_<test>.jsonl   the tests (runner)
    kody-XX.txt                  issued codes (no names)

Standard library only. It names the file and the line, and it separates
    CHYBA        must be fixed before the data leave the school
    UPOZORNENIE  the data are usable, but someone should know

It also holds the consent promise (consent.py): every record of a pupil must
come after their yes on screen, and a pupil who withdrew must leave nothing but
the withdrawal marker. The servers delete at once; if the file was locked at
that moment, `--vymaz` finishes the job.

    python datacheck.py ..\\data
    python datacheck.py --vymaz ..\\data
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

HEX16 = re.compile(r"^[0-9a-f]{16}$")
RAW_CODE = re.compile(r"\b[A-Z0-9]{2}-[A-Z0-9]{5}-[A-Z0-9]\b")
LESSON_KINDS = {
    "task_shown", "first_keystroke", "attempt", "prompt", "assistant_reply",
    "guard_violation", "self_explanation", "solution_unlocked", "adaptive_decision",
    "task_completed", "provider_error", "login", "logout", "task_skipped", "first_idea",
    "copy", "paste", "interaction", "solution_requested", "phase", "activity_defined",
    "activity_started", "activity_revealed", "activity_closed", "activity_view",
    "activity_response", "activity_engagement", "server_start",
    "consent", "consent_withdrawn"}
TEST_EVENTS = {"start", "resume", "answer", "finish", "consent", "withdraw"}
WITHDRAWN = {"consent_withdrawn", "withdraw"}      # the lesson's and the test's marker


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.notes: list[str] = []

    def error(self, where: str, msg: str) -> None:
        self.errors.append(f"{where}: {msg}")

    def warn(self, where: str, msg: str) -> None:
        self.warnings.append(f"{where}: {msg}")

    @property
    def ok(self) -> bool:
        return not self.errors

    def print(self) -> None:
        for n in self.notes:
            print(f"  .            {n}")
        for w in self.warnings:
            print(f"  UPOZORNENIE  {w}")
        for e in self.errors:
            print(f"  CHYBA        {e}")
        print()
        print(("V PORIADKU" if self.ok else "TREBA OPRAVIŤ") +
              f" — chyby: {len(self.errors)}, upozornenia: {len(self.warnings)}")


def _iso(s) -> bool:
    try:
        datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def _lines(path: Path, rep: Report):
    for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if not line.strip():
            continue
        if RAW_CODE.search(line):
            rep.error(f"{path.name}:{i}", "obsahuje čosi, čo vyzerá ako kód žiaka. "
                                          "Do záznamu patrí len pseudonym — súbor "
                                          "nesmie opustiť školu, kým sa to nevyrieši.")
        try:
            yield i, json.loads(line)
        except ValueError:
            yield i, None


def _tag(r: dict) -> str:
    what = r.get("kind") or r.get("ev")
    return "consent" if what == "consent" else "withdrawn" if what in WITHDRAWN else "data"


def _consent_audit(path: Path, rows: list[tuple[int, tuple, str]], rep: Report) -> None:
    """Every record of a pupil comes after their yes; after a withdrawal nothing
    recorded before it remains. `rows`: (line, pupil key, tag) in file order."""
    by_key: dict[tuple, list] = defaultdict(list)
    for i, key, tag in rows:
        by_key[key].append((i, tag))
    unconsented = leftover = withdrew = 0
    for evs in by_key.values():
        last_w = max((i for i, t in evs if t == "withdrawn"), default=None)
        if last_w is not None:
            withdrew += 1
            if any(t != "withdrawn" and i < last_w for i, t in evs):
                leftover += 1
        yes = [i for i, t in evs if t == "consent"]
        if any(t == "data" and not any(c < i for c in yes) for i, t in evs):
            unconsented += 1
    if unconsented:
        rep.error(path.name, f"{unconsented} žiak(ov) má záznamy bez súhlasu na obrazovke "
                             f"— zrejme stará verzia nástroja; tieto dáta školu neopúšťajú")
    if leftover:
        rep.error(path.name, f"{leftover} žiak(ov) odvolal(o) súhlas, ale ich záznamy nie sú "
                             f"vymazané — spustite: python datacheck.py --vymaz <priečinok>")
    if withdrew:
        rep.notes.append(f"{path.name}: odvolané súhlasy: {withdrew}")


def purge_withdrawn(path: Path) -> int:
    """Delete what a pupil who withdrew consent left behind: every record of
    theirs before their last withdrawal marker, except the markers."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    recs = []
    for line in lines:
        try:
            r = json.loads(line)
        except ValueError:
            r = None
        recs.append(r if isinstance(r, dict) else None)

    def key(r):
        return r.get("pseudonym"), r.get("session"), r.get("bank")

    last = {key(r): i for i, r in enumerate(recs) if r and _tag(r) == "withdrawn"}
    keep, removed = [], 0
    for i, (line, r) in enumerate(zip(lines, recs)):
        if r and key(r) in last and i < last[key(r)] and _tag(r) != "withdrawn":
            removed += 1
            continue
        keep.append(line)
    if removed:
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text("".join(x + "\n" for x in keep), encoding="utf-8")
        os.replace(tmp, path)
    return removed


def check_lesson(path: Path, rep: Report) -> dict:
    bad = 0
    rows: list[tuple[int, tuple, str]] = []
    pupils: set[str] = set()
    kinds: Counter = Counter()
    conds_by_session: dict[str, set] = defaultdict(set)
    for i, r in _lines(path, rep):
        where = f"{path.name}:{i}"
        if r is None:
            bad += 1
            if bad <= 3:
                rep.error(where, "riadok nie je platný JSON")
            continue
        for f in ("timestamp", "kind", "session", "pseudonym", "condition"):
            if f not in r:
                rep.error(where, f"chýba pole '{f}'")
        if r.get("timestamp") and not _iso(r["timestamp"]):
            rep.error(where, "čas nie je vo formáte ISO 8601")
        p = r.get("pseudonym", "")
        if p != "class" and not HEX16.match(str(p)):
            rep.error(where, f"pseudonym '{str(p)[:20]}' nie je 16 hexadecimálnych znakov "
                             f"— soľ sa zrejme nepoužila")
        elif p != "class":
            pupils.add(p)
            rows.append((i, (p, r.get("session")), _tag(r)))
        if r.get("condition") not in ("K", "G", "A"):
            rep.error(where, f"neznáma podmienka {r.get('condition')!r}")
        if r.get("kind") not in LESSON_KINDS:
            rep.warn(where, f"neznámy druh udalosti {r.get('kind')!r}")
        kinds[r.get("kind")] += 1
        conds_by_session[r.get("session")].add(r.get("condition"))
    if bad > 3:
        rep.error(path.name, f"spolu {bad} neplatných riadkov")
    _consent_audit(path, rows, rep)
    for sess, conds in conds_by_session.items():
        if len(conds) > 1:
            rep.error(path.name, f"hodina {sess} má záznamy vo viacerých podmienkach "
                                 f"{sorted(c for c in conds if c)} — jedna hodina = jedna podmienka")
    cond = next(iter(next(iter(conds_by_session.values()), {None})), None)
    if kinds["prompt"] and kinds["provider_error"] / kinds["prompt"] > 0.10:
        rep.warn(path.name, f"{kinds['provider_error']} z {kinds['prompt']} otázok asistentovi "
                            f"zlyhalo — zapíšte do protokolu vernosti (výpadok asistenta)")
    if cond == "K" and kinds["guard_violation"]:
        rep.warn(path.name, f"v podmienke K sa {kinds['guard_violation']}× niekto pokúsil "
                            f"použiť asistenta (odchýlka od protokolu, nie chyba dát)")
    if cond in ("G", "A") and pupils and not kinds["prompt"]:
        rep.warn(path.name, "podmienka s asistentom, ale žiadna otázka asistentovi — "
                            "fungoval asistent?")
    rep.notes.append(f"{path.name}: podmienka {cond}; žiaci: {len(pupils)}; "
                     f"vyriešené úlohy: {kinds['task_completed']}; otázky asistentovi: "
                     f"{kinds['prompt']}; odpovede v aktivitách: {kinds['activity_response']}")
    return dict(pupils=pupils, condition=cond)


def check_test(path: Path, rep: Report) -> dict:
    seen: Counter = Counter()
    started: set[tuple] = set()
    finished: set[tuple] = set()
    pupils: set[str] = set()
    rows: list[tuple[int, tuple, str]] = []
    for i, r in _lines(path, rep):
        where = f"{path.name}:{i}"
        if r is None:
            rep.error(where, "riadok nie je platný JSON")
            continue
        if "code" in r:
            rep.error(where, "záznam obsahuje kód žiaka namiesto pseudonymu "
                             "(starý formát testu) — spustite test aktuálnou verziou")
            continue
        ev = r.get("ev")
        if ev not in TEST_EVENTS:
            rep.error(where, f"neznámy záznam {ev!r}")
            continue
        p = r.get("pseudonym", "")
        if not HEX16.match(str(p)):
            rep.error(where, "pseudonym nie je 16 hexadecimálnych znakov")
            continue
        pupils.add(p)
        key = (p, r.get("session"), r.get("bank"))
        rows.append((i, key, _tag(r)))
        if ev == "start":
            started.add(key)
        elif ev == "finish":
            finished.add(key)
        elif ev == "answer":
            seen[key + (r.get("item_id"),)] += 1
            if not isinstance(r.get("seconds"), (int, float)) or r["seconds"] < 0:
                rep.error(where, "čas odpovede chýba alebo je záporný")
            j = r.get("jol")
            if j is not None and not (isinstance(j, int) and 0 <= j <= 100):
                rep.error(where, f"istota {j!r} je mimo 0–100")
            if not r.get("timestamp") or not _iso(r["timestamp"]):
                rep.error(where, "chýba čas záznamu (timestamp)")
    for k, n in seen.items():
        if n > 1:
            rep.error(path.name, f"položka {k[3]} je u jedného žiaka zapísaná {n}× (duplicita)")
    _consent_audit(path, rows, rep)
    unfinished = started - finished
    if unfinished:
        rep.warn(path.name, f"nedokončené testy: {len(unfinished)} — ak žiaci ešte sedia "
                            f"v triede, nech zadajú kód znova a pokračujú")
    rep.notes.append(f"{path.name}: žiaci: {len(pupils)}; dokončené testy: {len(finished)}")
    return dict(pupils=pupils)


def check_directory(path: str | Path) -> Report:
    d = Path(path)
    rep = Report()
    if not d.is_dir():
        rep.error(str(d), "priečinok neexistuje")
        return rep
    lessons = sorted(d.glob("events_*.jsonl"))
    tests = sorted(d.glob("odpovede_*.jsonl"))
    codes = sorted(d.glob("kody-*.txt"))
    for z in d.glob("ZOZNAM-kody-*"):
        rep.warn(z.name, "tento súbor spája kód s menom: ZOSTÁVA V ŠKOLE, neodovzdávajte ho")
    if not lessons and not tests:
        rep.error(str(d), "nenašiel som žiadny záznam hodiny (events_*.jsonl) ani testu "
                          "(odpovede_*.jsonl)")
    for f in lessons:
        check_lesson(f, rep)
    for f in tests:
        check_test(f, rep)
    for f in codes:
        n = sum(1 for x in f.read_text(encoding="utf-8").splitlines() if x.strip())
        rep.notes.append(f"{f.name}: vydané kódy: {n}")
    return rep


def self_test() -> list[str]:
    import tempfile
    fails = []
    good_l = {"timestamp": "2026-10-07T09:00:00+00:00", "kind": "login", "session": "S",
              "pseudonym": "0123456789abcdef", "condition": "A", "period": 1}
    good_t = {"timestamp": "2026-10-07T10:00:00+00:00", "ev": "answer", "pseudonym": "0123456789abcdef",
              "session": "P1", "bank": "T1_IPT", "item_id": "T1-1", "seconds": 12.0, "jol": 60}
    yes_l = json.dumps(dict(good_l, kind="consent"))
    yes_t = json.dumps({k: v for k, v in dict(good_t, ev="consent").items()
                        if k in ("timestamp", "ev", "pseudonym", "session", "bank")})
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        lesson, test = d / "events_S.jsonl", d / "odpovede_P1_T1_IPT.jsonl"
        lesson.write_text(yes_l + "\n" + json.dumps(good_l) + "\n", encoding="utf-8")
        test.write_text(yes_t + "\n" + json.dumps(good_t) + "\n", encoding="utf-8")
        if not check_directory(d).ok:
            fails.append("clean data rejected")
        for name, line in [
            ("raw code", json.dumps(dict(good_t, code="GY-K7M4P-Q"))),
            ("bad pseudonym", json.dumps(dict(good_t, pseudonym="Jozef Novak"))),
            ("bad jol", json.dumps(dict(good_t, jol=150))),
            ("duplicate", json.dumps(good_t) + "\n" + json.dumps(good_t)),
            ("not json", "{oops"),
        ]:
            test.write_text(yes_t + "\n" + line + "\n", encoding="utf-8")
            if check_directory(d).ok:
                fails.append(f"{name} not caught")
        test.write_text(json.dumps(good_t) + "\n", encoding="utf-8")
        if check_directory(d).ok:
            fails.append("an answer without consent not caught")
        withdraw = json.dumps({k: v for k, v in json.loads(yes_t).items()} | {"ev": "withdraw"})
        test.write_text(yes_t + "\n" + json.dumps(good_t) + "\n" + withdraw + "\n", encoding="utf-8")
        if check_directory(d).ok:
            fails.append("a withdrawal with the data still there not caught")
        if purge_withdrawn(test) != 2 or not check_directory(d).ok:
            fails.append("--vymaz did not leave only the withdrawal marker")
        test.write_text(yes_t + "\n" + json.dumps(good_t) + "\n", encoding="utf-8")
        lesson.write_text(json.dumps(good_l) + "\n", encoding="utf-8")
        if check_directory(d).ok:
            fails.append("a lesson event without consent not caught")
        lesson.write_text(
            yes_l + "\n" + json.dumps(good_l) + "\n" + json.dumps(dict(good_l, condition="G")) + "\n",
            encoding="utf-8")
        if check_directory(d).ok:
            fails.append("two conditions in one lesson not caught")
    return fails


def main(argv: list[str]) -> int:
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    if len(argv) >= 2 and argv[0] == "--vymaz":
        d = Path(argv[1])
        for f in sorted(d.glob("events_*.jsonl")) + sorted(d.glob("odpovede_*.jsonl")):
            n = purge_withdrawn(f)
            if n:
                print(f"  {f.name}: vymazaných {n} záznamov žiakov, ktorí odvolali súhlas")
        argv = [argv[1]]
    if len(argv) >= 1 and argv[0] != "--self-test":
        rep = check_directory(argv[0])
        rep.print()
        return 0 if rep.ok else 1
    fails = self_test()
    for f in fails:
        print("  FAIL " + f)
    print("datacheck self-test: " + ("ok" if not fails else f"{len(fails)} failures"))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
