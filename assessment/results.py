"""results.py -- from the runner's logs to the files the analysis reads.

The chain existed as modules and was never wired together: the runner wrote
JSON Lines, `scoring.py` scored responses, `effort.py` and `integrity.py`
flagged them, and nothing connected the first to the rest. This is that
connection, run after a session:

    python results.py data/odpovede_*.jsonl --out results/

writes
    scored.csv      every response; closed items scored, open items pending
    coding.csv      the open responses, blinded, for two independent coders
    pupils.csv      per pupil and sitting: score on closed items, open items
                    pending, calibration (bias, gamma, ...), test-taking effort,
                    integrity families flagged
    summary.json    counts, and what is still to be done

and, once both coders have filled coding.csv,

    python results.py data/odpovede_*.jsonl --out results/ --codings coding.csv

also writes responses.csv in the shape `analysis/ingest.py` validates -- and
refuses to while any open item is uncoded, exactly as `scoring.finalise` does.

Standard library only.
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import sys
from pathlib import Path

import calibration
import effort
import integrity
import scoring
from bank import load_all


def load_answers(paths: list[str]) -> tuple[list[dict], dict]:
    answers, stats = [], dict(lines=0, malformed=0, started=0, finished=0,
                              raw_code_records=0)
    for p in paths:
        for line in Path(p).read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            stats["lines"] += 1
            try:
                r = json.loads(line)
            except ValueError:
                stats["malformed"] += 1
                continue
            if "code" in r and "pseudonym" not in r:
                stats["raw_code_records"] += 1      # the pre-fix runner format
                continue
            if r.get("ev") == "start":
                stats["started"] += 1
            elif r.get("ev") == "finish":
                stats["finished"] += 1
            elif r.get("ev") == "answer":
                answers.append(r)
    return answers, stats


def to_responses(answers: list[dict], banks) -> list[scoring.Response]:
    inst_of = {b.bank_id: b.instrument for b in banks.values()}
    out = []
    for r in answers:
        out.append(scoring.Response(
            pseudonym=r["pseudonym"], session=r["session"],
            instrument=r.get("instrument") or inst_of.get(r.get("bank"), ""),
            item_id=r["item_id"], raw=r.get("raw", ""),
            seconds=float(r.get("seconds", 0.0)), jol=r.get("jol"),
            timestamp=r.get("timestamp", ""),
            paste_events=int(r.get("paste_events", 0)),
            blur_seconds=float(r.get("blur_seconds", 0.0)),
            revisions=int(r.get("revisions", 0))))
    return out


def pupil_table(responses: list[scoring.Response], scored: list[scoring.Scored],
                banks) -> list[dict]:
    items = {(b.instrument, i.id): i for b in banks.values() for i in b.items}
    # classical difficulty, from this file: share incorrect among closed answers
    by_item: dict[tuple, list[int]] = {}
    for s in scored:
        if s.correct is not None:
            by_item.setdefault((s.instrument, s.item_id), []).append(s.correct)
    difficulty = {k: 1 - sum(v) / len(v) for k, v in by_item.items() if v}

    groups: dict[tuple, list[tuple[scoring.Response, scoring.Scored]]] = {}
    for r, s in zip(responses, scored):
        groups.setdefault((r.pseudonym, r.session, r.instrument), []).append((r, s))

    # free-text answers of everyone else, for the similarity family
    peers: dict[tuple, dict[str, dict[str, str]]] = {}
    for (p, sess, inst), rows in groups.items():
        for r, s in rows:
            if items[(inst, r.item_id)].is_open:
                peers.setdefault((sess, inst), {}).setdefault(p, {})[r.item_id] = r.raw

    out = []
    for (p, sess, inst), rows in sorted(groups.items()):
        closed = [s for _, s in rows if s.correct is not None]
        cal = calibration.pupil_calibration(
            [(s.jol, s.correct) for _, s in rows if s.jol is not None and s.correct is not None])
        flags = effort.classify([r for r, _ in rows],
                                {r.item_id: items[(inst, r.item_id)].expected_sec for r, _ in rows})
        eff = effort.pupil_summary(flags)
        integ = integrity.examine(p, sess, [dict(
            item_id=r.item_id, seconds=r.seconds,
            expected_sec=items[(inst, r.item_id)].expected_sec,
            correct=s.correct, difficulty=difficulty.get((inst, r.item_id)),
            raw=r.raw, is_open=items[(inst, r.item_id)].is_open,
            paste_events=r.paste_events, blur_seconds=r.blur_seconds) for r, s in rows],
            peers.get((sess, inst)))
        out.append(dict(
            pseudonym=p, session=sess, instrument=inst, n_items=len(rows),
            closed_items=len(closed),
            closed_correct=sum(s.correct for s in closed),
            closed_points=sum(s.points or 0 for s in closed),
            closed_max_points=sum(s.max_points for s in closed),
            open_pending=sum(1 for _, s in rows if s.pending),
            calib_n=cal["n"], calib_bias=cal["bias"],
            calib_absolute_accuracy=cal["absolute_accuracy"], calib_brier=cal["brier"],
            calib_gamma=cal["gamma"], calib_sensitivity=cal["sensitivity"],
            rte_nt10=eff["rte_nt10"], rte_fixed=eff["rte_fixed"],
            rte_bimodal=eff["rte_bimodal"],
            below_effort_floor=eff["below_solution_behaviour_floor"],
            integrity_families="".join(sorted(integ.families)),
            integrity_excluded=integ.excluded))
    return out


def write_csv(rows: list[dict], path: Path) -> None:
    cols: list[str] = []
    for r in rows:
        cols += [k for k in r if k not in cols]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols or ["empty"])
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in cols})


def all_banks() -> dict:
    """The instruments of banks/*.json and the test section's forms (testy/*.txt),
    each form composed with all its items (every condition), keyed by form id."""
    banks = dict(load_all())
    try:
        import testy
        cat = testy.load_catalog()
    except Exception:                 # no testy/ folder: only the JSON banks
        return banks
    for fid in cat:
        banks[fid] = testy.compose(fid, cat, None)
    return banks


def run(paths: list[str], out: Path, codings: str = "") -> dict:
    banks = all_banks()
    answers, stats = load_answers(paths)
    responses = to_responses(answers, banks)
    scored = scoring.score(responses, banks)
    out.mkdir(parents=True, exist_ok=True)

    write_csv([dict(pseudonym=s.pseudonym, session=s.session, instrument=s.instrument,
                    item_id=s.item_id, response=s.raw, correct=s.correct, points=s.points,
                    max_points=s.max_points, chosen=s.chosen, diagnosis=s.diagnosis,
                    jol=s.jol, seconds=s.seconds, level=s.level, skill=s.skill,
                    anchor=s.anchor, pending=s.pending) for s in scored], out / "scored.csv")
    pupils = pupil_table(responses, scored, banks)
    write_csv(pupils, out / "pupils.csv")

    summary = dict(files=len(paths), **stats, responses=len(responses),
                   pupils_sittings=len(pupils),
                   open_pending=sum(1 for s in scored if s.pending))
    if codings:
        summary["coding"] = scoring.import_codings(scored, codings)
    else:
        summary["coding_sheet_rows"] = scoring.export_for_coding(
            scored, out / "coding.csv", banks)
    pending = sum(1 for s in scored if s.pending)
    if pending == 0:
        summary["finalised"] = scoring.finalise(scored, out / "responses.csv")
    else:
        summary["finalised"] = None
        summary["todo"] = (f"{pending} otvorených odpovedí čaká na dvoch hodnotiteľov "
                           f"(coding.csv); responses.csv vznikne až potom.")
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False),
                                      encoding="utf-8")
    return summary


def main(argv: list[str]) -> int:
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--out", default="results")
    ap.add_argument("--codings", default="", help="coding.csv filled by both coders")
    a = ap.parse_args(argv)
    paths = sorted({p for pat in a.logs for p in (glob.glob(pat) or [pat])})
    s = run(paths, Path(a.out), a.codings)
    print(json.dumps(s, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
