"""run_all.py -- regenerate everything the thesis depends on, in order.

The dependency chain is real and the order matters:

    dgp.py                    (the generating model -- no output of its own)
      -> pipeline.py 18       results_J18.json      (one illustrative study)
      -> pipeline.py 12       results.json          (the under-powered contrast)
      -> power.py             power_*.csv           (design-level power)
      -> validate_plan.py     plan_validation.json  (operating characteristics)
      -> peqi.py              peqi_*.json/csv       (the instrument)
      -> export_macros.py     thesis_numbers.tex    (what the thesis prints)
      -> figures.py           ../assets/images/*    (what the thesis shows)
      -> verify_thesis.py     (checks the whole lot is consistent)

Running any one of these on its own leaves the rest stale, which is exactly how
numbers in a thesis go wrong. So: one command.

    python run_all.py           full regeneration (a few minutes)
    python run_all.py --quick   skips the two long simulations
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from console import use_utf8

HERE = Path(__file__).resolve().parent

QUICK = "--quick" in sys.argv

STEPS: list[tuple[str, list[str], bool]] = [
    ("illustrative study (J=18)", ["pipeline.py", "18"], False),
    ("under-powered contrast (J=12)", ["pipeline.py", "12"], False),
    ("power simulation", ["power.py"], True),
    ("plan operating characteristics", ["validate_plan.py", "1000"], True),
    ("PEQI instrument", ["peqi.py"], False),
    ("mediator measurement error", ["measurement.py"], False),
    ("negative controls", ["falsification.py"], True),
    ("ICAP weight sensitivity", ["icap_weights.py"], False),
    ("equivalence bound", ["sesoi.py"], True),
    ("measurement plan", ["measurement_plan.py"], False),
    ("field data contract", ["ingest.py"], False),
    ("national anchoring", ["national_anchor.py"], True),
    ("pilot decision rules", ["pilot.py"], False),
    ("user categorisation", ["user_profiles.py"], True),
    ("assessment layer", ["assessment_validation.py"], True),
    ("instrument files from the bank",
     ["../../assessment/tex_export.py"], False),
    ("LaTeX macros", ["export_macros.py"], False),
    ("figures", ["figures.py"], False),
    ("consistency check", ["verify_thesis.py"], False),
]


def run(label: str, args: list[str]) -> bool:
    print(f"\n=== {label} " + "=" * max(0, 56 - len(label)))
    t = time.time()
    r = subprocess.run([sys.executable, *args], cwd=HERE,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    ok = r.returncode == 0
    tail = (r.stdout or "").strip().splitlines()[-6:]
    for line in tail:
        print("   " + line)
    if not ok:
        print("   FAILED")
        for line in (r.stderr or "").strip().splitlines()[-12:]:
            print("   ! " + line)
    print(f"   [{time.time() - t:.1f} s]")
    return ok


def main() -> int:
    failed = []
    for label, args, slow in STEPS:
        if QUICK and slow:
            print(f"\n=== {label}: skipped (--quick)")
            continue
        if not run(label, args):
            failed.append(label)
            # the chain is ordered; carrying on after a failure would produce
            # outputs derived from stale inputs, which is worse than stopping
            break

    print("\n" + "=" * 62)
    if failed:
        print("FAILED at:", failed[0])
        print("Nothing downstream was regenerated. Fix and re-run.")
        return 1
    print("all steps completed")
    print("next:  cd .. ; .\\build.ps1")
    return 0


if __name__ == "__main__":
    use_utf8()
    sys.exit(main())
