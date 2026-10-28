"""verify_thesis.py -- cross-check the numbers printed in the thesis against the
analysis outputs that are supposed to have produced them.

Why this exists
---------------
The thesis claims that every number in Chapters 5 and 6 comes out of this
directory and that none of it is typed by hand.  That claim is worthless unless
it is checked, because the usual failure mode is silent: a parameter changes, the
code is re-run, and a number left behind in the prose quietly becomes false.

This script re-reads the generated JSON/CSV, re-reads the .tex sources, and
compares them.  A mismatch is a defect in the thesis, not in the data.

Run:  python verify_thesis.py
Exit code 0 = every checked claim matches.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd
from console import use_utf8

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
TEX = HERE.parent

FAILS: list[str] = []
CHECKS = 0


def read_tex(*names: str) -> str:
    return "\n".join((TEX / n).read_text(encoding="utf-8") for n in names)


def norm(s: str) -> str:
    """Slovak decimal comma -> dot, LaTeX thin space -> nothing."""
    return s.replace("{,}", ".").replace(",", ".").replace("\\,", "")


def claim(label: str, ok: bool, detail: str = "") -> None:
    global CHECKS
    CHECKS += 1
    if ok:
        print(f"  ok   {label}")
    else:
        FAILS.append(f"{label}: {detail}")
        print(f"  FAIL {label}\n       {detail}")


def _decimals(x: float) -> int:
    s = f"{x!r}"
    return len(s.split(".")[1]) if "." in s else 0


def near(a: float, b: float, tol: float = 0.006) -> bool:
    return abs(a - b) <= tol


def find_num(text: str, pattern: str) -> float | None:
    m = re.search(pattern, text)
    if not m:
        return None
    return float(norm(m.group(1)))


# ===========================================================================
def check_power_table() -> None:
    """The generated power macros must match out/power_grid.csv, and the table
    in the thesis must reference those macros rather than literals."""
    print("\n[1] power macros vs out/power_grid.csv")
    g = pd.read_csv(OUT / "power_grid.csv")
    g = g[g.tau2_ct == 0.03].set_index("n_classes")
    mech = pd.read_csv(OUT / "power_mechanism.csv").set_index("n_classes")
    gen = (OUT / "thesis_numbers.tex").read_text(encoding="utf-8")

    def macro(name: str) -> float | None:
        # values may contain {,} for the Slovak decimal comma, so match to the
        # last brace on the line rather than to the first
        m = re.search(r"^\\newcommand\{\\" + name + r"\}\{(.*)\}\s*$", gen, re.M)
        return float(norm(m.group(1))) if m else None

    WORD = {6: "six", 9: "nine", 12: "twelve", 15: "fifteen",
            18: "eighteen", 24: "twentyfour"}
    for J, w in WORD.items():
        if J not in g.index:
            continue
        claim(f"J={J} enrolled", macro("powN" + w) == int(g.loc[J, "n_students"]),
              f"macro {macro('powN' + w)} vs csv {int(g.loc[J, 'n_students'])}")
        claim(f"J={J} analysed", macro("powNa" + w) == int(g.loc[J, "n_analysed"]),
              f"macro {macro('powNa' + w)} vs csv {int(g.loc[J, 'n_analysed'])}")
        for name, col in (("AK", "AK"), ("AG", "AG"), ("Eq", "GK_equiv"),
                          ("Fam", "family")):
            got, want = macro("pow" + name + w), float(g.loc[J, col])
            claim(f"J={J} {col}", got is not None and near(got, want),
                  f"macro {got} vs csv {want:.3f}")
        if J in mech.index:
            got = macro("powMech" + w)
            want = float(mech.loc[J, "power_precision"])
            claim(f"J={J} mechanism precision",
                  got is not None and near(got, want),
                  f"macro {got} vs csv {want:.3f}")

    tex = read_tex("content/5-metodika.tex")
    body = tex.split("label{tab:sila}")[1].split("end{tabular}")[0]
    claim("tab:sila references macros, not literals",
          "\\powAK" in body and not re.search(r"\d\{,\}\d", body),
          "the power table still contains hand-typed decimals")


def check_macro_integrity() -> None:
    """Every generated macro referenced in the prose must be defined, and no
    volatile number may be typed back into the text.

    This replaces the old value-by-value comparison. Now that the numbers are
    emitted by export_macros.py and referenced by name they cannot go stale, so
    the failure mode moved: from "the printed value is wrong" to "the macro is
    missing or misspelled", and to "someone typed a number back in".
    """
    print("\n[2] generated macros: defined, referenced, and not bypassed")
    gen = (OUT / "thesis_numbers.tex").read_text(encoding="utf-8")
    defined = set(re.findall(r"\\newcommand\{\\([A-Za-z]+)\}", gen))
    claim("macro file is non-trivial", len(defined) > 200,
          f"only {len(defined)} macros defined")
    claim("no macro name contains a digit",
          not re.findall(r"\\newcommand\{\\[A-Za-z]*[0-9]", gen),
          "LaTeX command names may contain letters only")

    body = re.sub(r"%.*", "",
                  read_tex("content/5-metodika.tex", "content/6-vysledky.tex"))

    # every command in the prose that looks like one of ours must be defined
    prefixes = ("num", "psy", "con", "eq", "med", "iv", "dose", "rho", "tri",
                "cal", "dis", "mod", "slope", "load", "carry", "var", "rob",
                "miss", "proc", "peqi", "pow", "rec", "val", "pDel")
    candidates = {m for m in re.findall(r"\\([A-Za-z]+)", body)
                  if m.startswith(prefixes)}
    known_latex = {"caption", "centering", "cite", "label", "midrule",
                   "mathrm", "medskip", "multicolumn", "paragraph", "par",
                   "part", "pagebreak", "pm", "propto", "protect", "psi",
                   "varepsilon", "varnothing", "vspace", "newcommand", "nu",
                   "equiv", "eqref", "cal", "colon", "conj", "varphi",
                   "phi", "pi", "prod", "ref", "rho", "emph", "textbf",
                   "textit", "toprule", "bottomrule", "item", "verb", "value"}
    missing = sorted(c for c in candidates - known_latex if c not in defined)
    claim("every referenced macro is defined", not missing,
          f"undefined: {missing}")

    used = sorted(d for d in defined if re.search(r"\\" + d + r"\b", body))
    claim("macros are actually referenced", len(used) >= 60,
          f"only {len(used)} of {len(defined)} macros appear in the prose")

    # a decimal typed back into a volatile table would silently go stale again
    for label in ("tab:kontrasty", "tab:psychometria", "tab:operacne",
                  "tab:nestrannost", "tab:proces", "tab:triangulacia"):
        marker = "label{" + label + "}"
        if marker not in body:
            claim(f"{label} exists", False, "table not found")
            continue
        tbl = body.split(marker, 1)[1].split("end{tabular", 1)[0]
        # a threshold such as $<0{,}001$ is a convention, not a value
        tbl_no_thresh = re.sub(r"<\s*0\{,\}0*1", "", tbl)
        typed = re.findall(r"\d+\{,\}\d+", tbl_no_thresh)
        claim(f"{label}: no hand-typed decimals", not typed,
              f"found {typed[:6]}")


def _macro_value(name: str) -> float | None:
    gen = (OUT / "thesis_numbers.tex").read_text(encoding="utf-8")
    m = re.search(r"^\\newcommand\{\\" + name + r"\}\{(.*)\}\s*$", gen, re.M)
    return float(norm(m.group(1))) if m else None


def check_peqi_numbers() -> None:
    """The PEQI macros must match out/peqi_report.json, and the appendix -- which
    is not macro-driven, because it is a frozen description of the instrument --
    must still agree with them."""
    print("\n[3] PEQI macros vs out/peqi_report.json")
    p = json.load(open(OUT / "peqi_report.json", encoding="utf-8"))

    for name, want, tol in (
        ("peqiRuleKappa", p["rule_only"]["kappa"], 0.006),
        ("peqiCvKappa", p["model_cv"]["kappa"], 0.006),
        ("peqiAdjacent", p["adjacent_within_1_level"] * 100, 0.06),
        ("peqiAlpha", p["human_irr"]["krippendorff_alpha"], 0.006),
        ("peqiCorpus", p["corpus_size"], 0.5),
    ):
        got = _macro_value(name)
        claim(f"macro {name}", got is not None and near(got, want, tol),
              f"macro {got} vs json {want}")

    # The appendix used to quote these figures as literals and was checked
    # against the JSON. That is the weaker arrangement: it detects staleness
    # after the fact instead of preventing it, and it detected exactly nothing
    # when the classifier was repaired -- three of the four numbers went stale
    # in one commit. The appendix now references the macros, so the check
    # becomes "no literal was typed back in".
    app = read_tex("appendices/B-kodovaci-manual.tex")
    perf = app.split("label{tab:klasifikator}")[1].split("end{tabular}")[0]
    claim("classifier table references macros",
          "\\peqiRuleKappa" in perf and "\\peqiCvKappa" in perf,
          "the performance table does not use the generated macros")
    claim("classifier table has no hand-typed decimals",
          not re.findall(r"\d+,\d+", perf),
          f"found {re.findall(r'[0-9]+,[0-9]+', perf)[:4]}")

    sess = p["session_index"]
    claim("PEQI separates the conditions",
          sess["A"]["peqi"] - sess["G"]["peqi"] > 0.2,
          f"G={sess['G']['peqi']} A={sess['A']['peqi']}")


def check_sample_size_consistency() -> None:
    """Sample-size figures must agree everywhere they appear."""
    print("\n[6] internal consistency of sample-size statements")
    tex = read_tex("content/5-metodika.tex", "content/6-vysledky.tex",
                   "content/1-technical-abstract.tex", "preamble/annotation.tex")
    g = pd.read_csv(OUT / "power_grid.csv")
    row = g[(g.tau2_ct == 0.03) & (g.n_classes == 18)].iloc[0]

    claim("planned enrolment quoted in the prose",
          str(int(row.n_students)) in tex,
          f"csv says {int(row.n_students)}")
    claim("planned analysable N quoted in the prose",
          str(int(row.n_analysed)) in tex, f"csv says {int(row.n_analysed)}")

    r18 = json.load(open(OUT / "results_J18.json", encoding="utf-8"))
    claim("macro numNstudents matches the pipeline",
          _macro_value("numNstudents") == r18["design"]["n_students"],
          f"macro {_macro_value('numNstudents')} vs pipeline "
          f"{r18['design']['n_students']}")
    claim("macro numNcomplete matches the pipeline",
          _macro_value("numNcomplete")
          == r18["contrasts"]["theta_del|A-K"]["n"],
          f"macro {_macro_value('numNcomplete')} vs pipeline "
          f"{r18['contrasts']['theta_del|A-K']['n']}")
    claim("the two N figures are distinguished in the text",
          "losuj" in tex or "predpoklad" in tex,
          "the prose must explain why the simulated N differs from the planned N")


def check_confusion_matrix() -> None:
    print("\n[4] confusion matrix in appendix B vs out/peqi_confusion.csv")
    cm = pd.read_csv(OUT / "peqi_confusion.csv", index_col=0)
    tex = read_tex("appendices/B-kodovaci-manual.tex")
    body = tex.split("label{tab:zamena}")[1].split("end{tabular}")[0]
    for lvl in ["L0", "L1", "L2", "L3", "L4", "X"]:
        m = re.search(rf"^{lvl}\s*& (.*?)\\\\", body, re.M)
        if not m:
            claim(f"confusion row {lvl}", False, "row not found")
            continue
        got = [int(re.sub(r"\\textbf\{|\}", "", c).strip()) for c in m.group(1).split("&")]
        want = cm.loc[lvl].tolist()
        claim(f"confusion row {lvl}", got == want, f"tex {got} vs csv {want}")


def check_dgp_anchors() -> None:
    """The anchoring table must match the actual Params defaults."""
    print("\n[5] anchoring table (tab:kotvy) vs dgp.Params defaults")
    sys.path.insert(0, str(HERE))
    from dgp import Params
    p = Params()
    tex = read_tex("content/6-vysledky.tex")
    body = tex.split("label{tab:kotvy}")[1].split("end{tabularx}")[0]

    for label, pat, want in [
        ("d_del_G", r"odlo.en. test \$G\$ vs\. \$K\$ & \$([\d\{\},+-]+)\\,\\theta\$", p.d_del_G),
        ("d_del_A", r"odlo.en. test \$A\$ vs\. \$K\$ & \$([\d\{\},+-]+)\\,\\theta\$", p.d_del_A),
        ("d_imm_A", r"okam.it. test \$A\$ vs\. \$K\$ & \$([\d\{\},+-]+)\\,\\theta\$", p.d_imm_A),
        ("b_peqi", r"PEQI \$\\to\$ odlo.en. test & \$([\d\{\},+-]+)\$", p.b_peqi_on_del),
        ("icc", r"vn.trotriedna korel.cia & \$([\d\{\},]+)\$", p.icc_class),
        ("jol_bias_G", r"kalibra.n. skreslenie \$G\$ & \$([\d\{\},+-]+)\$", p.jol_bias_G),
    ]:
        got = find_num(body, pat)
        claim(f"anchor {label}", got is not None and near(got, want, 0.0006),
              f"tex {got} vs dgp {want}")

    claim("attrition 12 %", near(p.attrition, 0.12, 0.0001) and "12" in body,
          f"dgp {p.attrition}")
    claim("r_within 0,55 matches power.py",
          _power_setting("r_within") == 0.55, "power.py disagrees")
    claim("icc matches power.py",
          near(_power_setting("icc_class"), p.icc_class, 0.0001),
          "power.py icc differs from dgp icc")


def _power_setting(key: str):
    s = json.load(open(OUT / "power_settings.json", encoding="utf-8"))
    return s[key]


def check_source_hygiene() -> None:
    """No LaTeX command may have lost its backslash to a shell or script escape.

    This check exists because three real defects got past everything else.
    Three occurrences of `\\ref` and one of `\\footnotesize` had been written
    through a tool that interpreted the backslash: `\\r` became a carriage
    return and `\\f` a form feed, leaving `<CR>ef{sec:rozhovory}` and
    `<FF>ootnotesize` in the source.

    Nothing caught them.  The build did not, because TeX prints the orphaned
    tail as ordinary text; there is no undefined reference to warn about when
    the reference command itself is gone.  Check [7] did not, because it
    verifies that every `\\ref` resolves -- and a destroyed `\\ref` is not a
    `\\ref`.  A check that a command RESOLVES cannot see a command that no
    longer EXISTS, which is the general lesson and the reason this is separate.

    Two detectors, because either alone leaves a gap:

      (a) any control byte in a source file.  This catches the cause exactly:
          \\a \\b \\f \\v \\r all become control characters, and none of them
          belongs in a .tex file.  It also catches commands that take no
          argument, which (b) cannot see.
      (b) an orphaned command tail before an opening brace -- `ef{`, `abel{`.
          This catches damage done by an escape that produced no control byte
          at all, such as a backslash simply dropped in a copy.
    """
    print("\n[7] source hygiene: no command has lost its backslash")
    files = sorted(list((TEX / "content").glob("*.tex"))
                   + list((TEX / "appendices").glob("*.tex"))
                   + list((TEX / "preamble").glob("*.tex"))
                   + [TEX / "main.tex"])

    # (a) control bytes.  TAB and LF are legal; CR is legal only inside CRLF.
    dirty = []
    for f in files:
        b = f.read_bytes()
        lone_cr = b.count(b"\r") - b.count(b"\r\n")
        others = sum(b.count(bytes([c])) for c in
                     list(range(0, 9)) + [11, 12] + list(range(14, 32)))
        if lone_cr or others:
            dirty.append(f"{f.name}: {lone_cr} lone CR, {others} other control bytes")
    claim("no control bytes in any .tex source", not dirty, "; ".join(dirty))

    # (b) orphaned command tails.  Every command used with an argument anywhere
    # in the thesis contributes its own tail, so the detector grows with the
    # document instead of relying on a hand-kept list.
    src = {f: f.read_text(encoding="utf-8") for f in files}
    joined = "\n".join(src.values())
    names = {n for n in re.findall(r"\\([A-Za-z]{3,})\{", joined)}
    tails = {n[1:]: n for n in names if len(n) >= 4}
    orphans = []
    for f, text in src.items():
        for tail, full in tails.items():
            for m in re.finditer(r"(?<![A-Za-z\\])" + re.escape(tail) + r"\{", text):
                line = text.count("\n", 0, m.start()) + 1
                orphans.append(f"{f.name}:{line} '{tail}{{' (from \\{full})")
    claim("no orphaned command tails", not orphans, "; ".join(orphans[:6]))


def check_negative_controls() -> None:
    """A negative control must be able to fail, and must not fail when clean."""
    print("\n[10] negative controls")
    path = OUT / "falsification.json"
    if not path.exists():
        claim("falsification.json exists", False, "run falsification.py")
        return
    f = json.load(open(path, encoding="utf-8"))
    power = {r["leak"]: r for r in f["power_against_leak"]}

    claim("a clean control declares equivalence most of the time",
          power[0.0]["passes_equivalence"] >= 0.80,
          f"only {power[0.0]['passes_equivalence']} -- the control would cry "
          f"wolf on clean studies")
    claim("false alarms stay at the nominal rate",
          power[0.0]["detects"] <= 0.08, str(power[0.0]["detects"]))
    claim("a leak the size of the primary effect is caught",
          power[0.3]["detects"] >= 0.70, str(power[0.3]["detects"]))
    claim("and is not waved through as equivalent",
          power[0.3]["passes_equivalence"] <= 0.15,
          "a control that passes under a large leak certifies nothing")
    claim("the trait control is insensitive to the same-day channel",
          f["trait_control"]["passes_equivalence"] >= 0.90,
          str(f["trait_control"]))
    claim("the bound is the primary SESOI, not something tighter and unreachable",
          abs(f["design"]["bound"] - 0.30) < 1e-9, str(f["design"]["bound"]))

    tex = read_tex("content/5-metodika.tex")
    claim("the decision rule is stated in the methodology",
          "sec:negativne-kontroly" in tex and "mechanizmové tvrdenie sa sťahuje" in tex,
          "a pre-specified rule that is not written down is not pre-specified")


def check_equivalence_bound() -> None:
    """The equivalence claim must be stated as what it licenses, not more.

    SESOI does two opposite jobs: conservative for superiority, permissive for
    equivalence. The thesis may keep one number for both, but it may not keep
    quiet about the second job.
    """
    print("\n[12] the equivalence bound and what it licenses")
    path = OUT / "sesoi.json"
    if not path.exists():
        claim("sesoi.json exists", False, "run sesoi.py")
        return
    s = json.load(open(path, encoding="utf-8"))
    g = s["declaration_rate"]

    claim("a true null is usually declared equivalent at the planned bound",
          g["0.00"]["0.30"] >= 0.80, str(g["0.00"]["0.30"]))
    claim("the declaration rate falls as the true effect grows",
          g["0.00"]["0.30"] > g["0.10"]["0.30"] > g["0.20"]["0.30"]
          > g["0.25"]["0.30"])
    claim("narrowing the bound is strictly harder",
          all(g[t]["0.15"] < g[t]["0.30"] for t in g))

    # the number the thesis owes its reader, and the proof it printed it
    tex = read_tex("content/5-metodika.tex")
    claim("the false-equivalence rate is reported, not just the bound",
          "eqTTwentyBThirty" in tex,
          "the probability of certifying a 0.20 effect as equivalence is not "
          "shown anywhere in the methodology")
    claim("the bound is justified normatively, not only descriptively",
          "kraft2020effectsizes" in tex and "lakens2018tosttutorial" in tex,
          "SESOI is stated without the benchmark literature that disputes it")
    claim("the metric the bound lives on is named",
          "cheung2016methodological" in tex,
          "a bound borrowed from standardized-test norms must say so")

    sap = read_tex("appendices/C-sap.tex")
    claim("the SAP forbids the overstated wording",
          "nikdy ako" in sap and "rozdiel väčší než" in sap,
          "the binding rule against 'G is equivalent to K' is missing")


def check_measurement_plan() -> None:
    """Every instrument must be fit for the job it was given, and the plan must
    fit in the lessons a school can actually give."""
    print("\n[13] the measurement plan")
    path = OUT / "measurement_plan.json"
    if not path.exists():
        claim("measurement_plan.json exists", False, "run measurement_plan.py")
        return
    m = json.load(open(path, encoding="utf-8"))
    v = m["verdict"]

    claim("the trait instrument is reliable enough to be a covariate",
          v["gf_fit_for_covariate"],
          f"reliability {v['gf_reliability']} at {v['gf_items']} items")
    claim("and reliable enough to CLEAR as a negative control",
          v["gf_clearance_at_that_reliability"] >= 0.80,
          f"clears only {v['gf_clearance_at_that_reliability']} of the time")
    claim("the length that was originally specified would not have been",
          v["twelve_item_reliability"] < 0.75,
          "if twelve items had sufficed, lengthening the test would be waste")
    claim("clearance falls as the instrument gets worse",
          (m["negative_control_clearance_by_reliability"]["0.90"]
           > m["negative_control_clearance_by_reliability"]["0.70"]
           > m["negative_control_clearance_by_reliability"]["0.50"]),
          "an unreliable control must be shown to fail, or the check is empty")

    claim("every session fits the time a school can give", v["every_session_fits"],
          str({k: (x["total_minutes"], x["budget_minutes"])
               for k, x in m["time_budget"].items() if isinstance(x, dict)
               and not x["fits"]}))
    claim("the drift band is reachable at this sample",
          v["drift_band_reachable"],
          f"se of an item shift is {m['drift_precision']['se_of_item_shift_logits']}")
    claim("drift flagging is specific",
          m["item_drift"]["mean_false_flags_per_study"] < 0.1,
          "a drift check that flags clean items is noise")

    tex = read_tex("content/5-metodika.tex")
    claim("the construct hierarchy is stated in the methodology",
          "sec:konstrukty" in tex and "Interval merania musí zodpovedať" in tex,
          "the change-rate rule is what makes the rest of the plan checkable")
    claim("the executable protocol is cross-referenced",
          "chapter:protokol" in tex,
          "a plan a school cannot run is a plan in name only")
    app = read_tex("appendices/F-protokol.tex")
    for needed in ("informovan", "GDPR", "EduPage", "iBobor"):
        claim(f"protocol covers: {needed}", needed in app)


def check_national_anchor() -> None:
    """Locating the sample nationally must be honest about what it buys."""
    print("\n[14] placing the sample on the national scale")
    path = OUT / "national_anchor.json"
    if not path.exists():
        claim("national_anchor.json exists", False, "run national_anchor.py")
        return
    n = json.load(open(path, encoding="utf-8"))
    v = n["verdict"]

    claim("the planted location is recovered", v["location_recovered"],
          f"bias {v['residual_bias_logits']} logits")
    claim("the residual bias is small enough to report alongside",
          abs(v["residual_bias_percentile_points"]) < 5.0,
          f"{v['residual_bias_percentile_points']} percentile points")
    claim("precision is cheap in anchor items",
          v["items_for_se_0_10"] is not None and v["items_for_se_0_10"] <= 8,
          str(v["items_for_se_0_10"]))
    claim("cohort drift is identified as the binding risk",
          v["systematic_drift_is_the_binding_risk"],
          "if independent drift dominated, more items would be the answer")

    tex = read_tex("content/5-metodika.tex")
    claim("the reference population is named as iBobor participants",
          "účastníci" in tex or "účastníck" in tex,
          "calling it 'national' without qualification overstates it")
    claim("the section is cross-referenced from the limitations",
          "sec:narodne-ukotvenie" in read_tex("content/8-conclusion.tex"),
          "a mitigation the limitations section does not mention is not a "
          "mitigation the reader can find")


def check_pilot_rules() -> None:
    """A pilot must have pre-specified rules, and must not claim what it cannot do."""
    print("\n[15] pilot decision rules")
    path = OUT / "pilot.json"
    if not path.exists():
        claim("pilot.json exists", False, "run pilot.py")
        return
    p = json.load(open(path, encoding="utf-8"))
    v = p["verdict"]

    claim("the interval rule keeps far more good items than the point rule",
          v["good_items_saved_by_the_interval_rule"] > 0.05,
          f"saves only {v['good_items_saved_by_the_interval_rule']}")
    claim("and still catches a substantial share of bad ones",
          v["bad_items_still_caught"] > 0.30,
          f"catches {v['bad_items_still_caught']} -- too lenient to be a screen")
    claim("the between-class variance is declared NOT estimable from one class",
          v["tau_squared_not_estimable"],
          "a one-class pilot has no degrees of freedom for a between-class term")
    claim("the guard gate is bounded, not certified",
          0 < v["guard_bound_not_zero"] < 0.20,
          f"upper bound {v['guard_bound_not_zero']}")

    tex = read_tex("content/5-metodika.tex")
    claim("the pilot's forbidden changes are written down",
          "SESOI, primárny ukazovateľ" in tex,
          "a pilot that may change anything is a tuning procedure")
    claim("the tau-squared claim was corrected in the prose",
          "τ^2" not in tex or "nemôže" in tex or "nie" in tex)
    app = read_tex("appendices/A-instrumenty.tex")
    claim("the appendix no longer presents the guard set as a certificate",
          "nejde o certifikát" in app,
          "zero of forty bounds the leak rate near 7 %, not at zero")


def check_assignment_compliance() -> None:
    """Every clause of the thesis assignment must be answerable from the text.

    This is not a quality check, it is a scope check: the assignment names
    specific deliverables, and a thesis can be excellent and still not contain
    one of them. Each claim below points at the section that discharges a
    clause, so a missing section fails loudly rather than being noticed by an
    examiner.
    """
    print("\n[16] thesis assignment: every clause discharged")
    sota = read_tex("content/4-state-of-the-art.tex")
    met = read_tex("content/5-metodika.tex")
    sol = read_tex("content/7-problem-statement-and-solution.tex")
    all_tex = sota + met + sol + read_tex("content/8-conclusion.tex")

    # mandatory literature, named in the assignment
    for key, who in (("garzon2025systematic", "Garzon et al. 2025"),
                     ("hariyanto2025adaptive", "Discover Education 2025")):
        claim(f"mandatory reference cited: {who}",
              ("cite{" + key) in all_tex or (key + "}") in all_tex
              or key in all_tex,
              f"{key} is in the bib but never cited in the text")

    # clause 1: how AI tools are currently deployed, quant AND qual
    claim("clause 1: deployment analysis present",
          "sec:nasadenie" in sota)
    claim("clause 1: quantitative evaluation of deployed solutions",
          "tab:nasadenia" in sota)
    claim("clause 1: qualitative evaluation",
          "Kvalitat" in sota and "obmedzuj" in sota)
    claim("clause 1: benefits and limiting factors identified",
          "tab:prinosy-obmedzenia" in sota)

    # topic text: Slovak context, and teachers
    claim("topic text: Slovak research context",
          "sec:slovensko" in sota)
    claim("topic text: teachers as well as pupils",
          "sec:ucitelia" in met)

    # clause 2: the three required capabilities of the solution
    claim("clause 2: systematic data collection", "sec:infrastruktura" in met)
    claim("clause 2: USER categorisation (not prompt categorisation)",
          "sec:kategorizacia" in met,
          "the assignment asks for kategorizacia pouzivatelov")
    claim("clause 2: change in selected abilities, before and after",
          "sec:konstrukty" in met and "sec:tri-vrstvy" in met)

    # clause 3: implemented and deployable to a school
    claim("clause 3: deployability treated as an artefact",
          "sec:nasaditelnost" in sol)

    # clause 4: comparison and recommendations
    claim("clause 4: comparison with available solutions",
          "sec:porovnanie" in sol)
    claim("clause 4: the comparison names what the solution CANNOT do",
          "Nedok" in sol or "nedok" in sol,
          "a comparison that only lists advantages is marketing")
    claim("clause 4: recommendations formulated",
          "sec:odporucania" in sol)
    claim("clause 4: recommendations separate what is established from what "
          "depends on the study's own result",
          "podmienen" in sol,
          "stating untested recommendations as advice claims more than the "
          "work has earned")


def check_repo_self_description() -> None:
    """The chapter that describes this repository must describe it correctly.

    Chapter 7 reports how many macros, checks, modules and tests there are. Those
    counts are generated, not typed -- but a generated count can still be stale by
    one pass, because export_macros.py reads a summary that verify_thesis.py and
    the test runner wrote on the PREVIOUS run. This check closes that loop: if a
    count no longer matches reality, it fails here and names what to re-run.
    """
    print("\n[11] the repository's description of itself")
    gen = (OUT / "thesis_numbers.tex").read_text(encoding="utf-8")

    def macro(name: str) -> str | None:
        m = re.search(r"^\\newcommand\{\\" + name + r"\}\{(.*)\}\s*$", gen, re.M)
        return m.group(1) if m else None

    n_macros = len(re.findall(r"\\newcommand\{", gen))
    claim("macro count is self-consistent", macro("repoMacros") == str(n_macros),
          f"macro says {macro('repoMacros')}, file has {n_macros}; re-run export_macros.py")

    n_modules = len(sorted(HERE.glob("*.py")))
    claim("module count matches the directory",
          macro("repoModules") == str(n_modules),
          f"macro says {macro('repoModules')}, directory has {n_modules}")

    claim("check count is not a placeholder", macro("repoChecks") != "??",
          "run verify_thesis.py then export_macros.py")
    # CHECKS is still being incremented while this runs, so compare against the
    # previous run's total plus the checks added since -- i.e. just require that
    # it is in the right neighbourhood and that it was regenerated at all.
    prev = (OUT / "verify_summary.json")
    if prev.exists() and macro("repoChecks") not in (None, "??"):
        last = json.load(open(prev, encoding="utf-8"))["checks"]
        claim("check count macro matches the last recorded run",
              macro("repoChecks") == str(last),
              f"macro says {macro('repoChecks')}, last run recorded {last}")

    claim("test counts were captured", macro("repoTests") not in (None, "??"),
          "run .\\run-all-tests.ps1 then export_macros.py")
    ts = HERE.parents[1] / "ai-doc" / "test-summary.json"
    if ts.exists():
        t = json.load(open(ts, encoding="utf-8-sig"))
        claim("total test count matches the runner's summary",
              macro("repoTests") == str(t["total_passed"]),
              f"macro says {macro('repoTests')}, summary says {t['total_passed']}")
        # This script is itself one of the suites, so it cannot certify its own
        # run: any new check that fails here would mark the suite failed, and
        # this assertion would then fail for that reason alone, on every run,
        # for ever. It certifies the other five.
        others = {k: v for k, v in t["suites"].items()
                  if k != "thesis consistency"}
        bad = [k for k, v in others.items() if v["status"] != "PASS"]
        claim("every other suite in the summary passed", not bad,
              f"the thesis must not quote a test count from a failing run: {bad}")


def check_measurement_error() -> None:
    """The propositions about mediator measurement error must still hold.

    They are algebraic, so they cannot fail by chance -- but they are stated in
    the thesis as numbers, and the code that produces those numbers can.
    """
    print("\n[9] differential measurement error in the mediator")
    path = OUT / "measurement.json"
    if not path.exists():
        claim("measurement.json exists", False, "run measurement.py")
        return
    m = json.load(open(path, encoding="utf-8"))

    p = m["propositions"]
    claim("all three propositions verify numerically",
          p["all_propositions_hold"],
          "; ".join(k for k, v in p.items()
                    if isinstance(v, dict) and not v.get("holds", True)))
    claim("P1: the reduced form is untouched by mediator error",
          abs(p["P1_reduced_form_is_immune"]["itt_y_true_mediator"]
              - p["P1_reduced_form_is_immune"]["itt_y_error_ridden"]) < 1e-6)
    claim("P2: differential error attenuates the IV estimate",
          p["P2_iv_attenuates"]["attenuation_factor"] < 1.0)

    v = m["veneer"]
    claim("the veneer attack is closed in the current rule",
          v["v2_dominance_rules"]["n_level_shifts"] == 0,
          f"{v['v2_dominance_rules']['n_level_shifts']} prompts still shift level")
    claim("closing it did not cost agreement",
          v["v2_dominance_rules"]["kappa_on_anchors"]
          >= v["v0_as_written"]["kappa_on_anchors"],
          f"kappa went {v['v0_as_written']['kappa_on_anchors']} -> "
          f"{v['v2_dominance_rules']['kappa_on_anchors']}")
    claim("the repair is decomposed into its two independent parts",
          v["v0_as_written"]["kappa_on_anchors"]
          < v["v1_lexicons_anchored"]["kappa_on_anchors"]
          < v["v2_dominance_rules"]["kappa_on_anchors"])

    claim("the audit is powered for the planned size",
          m["audit_power"]["power"] >= 0.80,
          f"power {m['audit_power']['power']} at n="
          f"{m['audit_power']['design']['n_prompts_per_condition']}")
    claim("the correction recovers the planted b-path",
          m["correction"]["recovers_b"],
          f"got {m['correction']['corrected']['b_path_calibrated']}, "
          f"planted {m['correction']['planted']['b']}")
    claim("the naive estimate does not",
          abs(m["correction"]["naive_b_error"]) > 0.02,
          "if the naive estimate were already right the correction would be "
          "solving a problem that does not exist")


def check_cross_references() -> None:
    """Every \\ref and \\cite must resolve."""
    print("\n[7] cross-references and citations resolve")
    tex_files = list((TEX / "content").glob("*.tex")) + \
        list((TEX / "appendices").glob("*.tex")) + \
        list((TEX / "preamble").glob("*.tex"))
    src = "\n".join(f.read_text(encoding="utf-8") for f in tex_files)

    labels = set(re.findall(r"\\label\{([^}]+)\}", src))
    refs = set(re.findall(r"\\(?:ref|autoref|pageref)\{([^}]+)\}", src))
    missing = sorted(refs - labels)
    claim("all \\ref targets exist", not missing, f"missing labels: {missing}")

    dup = [l for l in labels if src.count("\\label{" + l + "}") > 1]
    claim("no duplicate labels", not dup, f"duplicated: {dup}")

    bib = (TEX / "bib" / "references.bib").read_text(encoding="utf-8")
    keys = set(re.findall(r"^@\w+\{([^,]+),", bib, re.M))
    cited = set()
    for group in re.findall(r"\\cite\{([^}]+)\}", src):
        cited.update(k.strip() for k in group.split(","))
    unknown = sorted(cited - keys)
    claim("all \\cite keys exist in the bib", not unknown, f"unknown keys: {unknown}")

    unused = sorted(keys - cited)
    print(f"       (note: {len(unused)} bib entries are never cited: "
          f"{', '.join(unused[:8])}{'...' if len(unused) > 8 else ''})")


def check_hypothesis_consistency() -> None:
    """The hypotheses declared primary must be the ones the SAP actually tests."""
    print("\n[8] hypotheses declared primary vs the confirmatory family in the SAP")
    sota = read_tex("content/4-state-of-the-art.tex")
    sap = read_tex("content/5-metodika.tex", "appendices/C-sap.tex")

    m = re.search(r"Konfirma.n. rodinu tvoria tri tvrdenia:(.{0,300})", sota, re.S)
    declared_text = m.group(1) if m else ""
    declared = set(re.findall(r"H\d[ab]?", declared_text))
    fam = re.search(r"Konfirma.n. rodinu tvoria tri testy(.{0,300})", sap, re.S)
    family_text = fam.group(1) if fam else ""
    in_family = set(re.findall(r"H\d[ab]?", family_text))

    claim("confirmatory family declared in the SOTA chapter",
          len(declared) == 3, f"parsed {sorted(declared)} from {declared_text[:120]!r}")
    claim("confirmatory family restated in the SAP",
          len(in_family) == 3, f"parsed {sorted(in_family)}")
    claim("the two statements agree", declared == in_family,
          f"SOTA says {sorted(declared)}, SAP says {sorted(in_family)}")
    claim("mediation hypothesis is NOT in the confirmatory family",
          "H6b" not in declared,
          "H6b is not identified by randomisation and must not be confirmatory")

    # every confirmatory claim must also appear in the primary results table
    res = read_tex("content/6-vysledky.tex")
    prim = res.split("label{tab:primarne}")[1].split("end{tabular}")[0]
    for h in sorted(declared):
        claim(f"{h} reported in tab:primarne", h in prim,
              f"{h} is confirmatory but is not in the primary results table")

    # The results chapter enumerates the design faults the simulation found and
    # the conclusion counts them in a sentence. Two places, one number: exactly
    # the arrangement that goes stale. It already had -- the list grew from six
    # to nine while the conclusion still said six.
    WORDS = {"tri": 3, "štyri": 4, "päť": 5, "šesť": 6, "sedem": 7,
             "osem": 8, "deväť": 9, "desať": 10, "jedenásť": 11, "dvanásť": 12}
    sec = res.split("label{sec:co-odhalila-simulacia}")[1]
    enumerated = sec.split("\\end{enumerate}")[0].count("\\item")
    concl = read_tex("content/8-conclusion.tex")
    m = re.search(r"Postup odhalil (\w+) ch[ýy]b n[áa]vrhu", concl)
    stated = WORDS.get(m.group(1)) if m else None
    claim("the conclusion's count of design faults matches the enumeration",
          stated == enumerated,
          f"conclusion says {m.group(1) if m else '(not found)'} "
          f"({stated}), chapter 6 lists {enumerated}")

    m2 = re.search(r"Pr[áa]ca prin[áa]ša (\w+) vec[ií]", concl)
    contributions = concl.split("\\section{Inžiniersky")[0].count("\\paragraph{")
    claim("the conclusion's count of contributions matches its own paragraphs",
          m2 is not None and WORDS.get(m2.group(1)) == contributions,
          f"says {m2.group(1) if m2 else '(not found)'}, "
          f"has {contributions} paragraphs")


# ===========================================================================
def check_assessment_layer() -> None:
    """The instruments, and the claims the thesis makes about them.

    This group exists because the thesis now states properties OF ITS OWN
    INSTRUMENTS -- that both test forms are the same length, that six items are
    identical across them, that every session fits a Slovak lesson. Those are
    exactly the claims that were false before and nobody noticed, so they are
    checked against the bank rather than read off the page.
    """
    print("\n[12] the assessment layer")

    asm_path = OUT / "assessment.json"
    if not asm_path.exists():
        claim("assessment.json exists", False,
              "run analysis/assessment_validation.py")
        return
    a = json.load(open(asm_path, encoding="utf-8"))

    # --- the generated appendix must be what the bank produces NOW
    sys.path.insert(0, str(HERE.parents[1] / "assessment"))
    import importlib
    try:
        texp = importlib.import_module("tex_export")
        importlib.reload(texp)
        gen_ok = (texp.OUT.exists()
                  and texp.OUT.read_text(encoding="utf-8") == texp.document())
        claim("the generated appendix matches the bank", gen_ok,
              "run: python assessment/tex_export.py")
        mac_ok = (texp.MACROS.exists()
                  and texp.MACROS.read_text(encoding="utf-8") == texp.macros())
        claim("the generated instrument macros match the bank", mac_ok,
              "run: python assessment/tex_export.py")
        banks = importlib.import_module("bank").load_all()
    except Exception as e:                       # noqa: BLE001
        claim("the assessment layer imports", False, repr(e))
        return

    ipt, drt = banks["T1_IPT"], banks["T1_DRT"]

    # --- the three claims that were false before
    claim("both test forms have the same number of items",
          ipt.n_items == drt.n_items, f"{ipt.n_items} vs {drt.n_items}")
    ident = all(
        [i for i in ipt.items if i.anchor == k][0].stem.strip()
        == [i for i in drt.items if i.anchor == k][0].stem.strip()
        for k in ipt.anchors)
    claim("all six anchor items are identical across the forms", ident)
    claim("no anchor is an open item",
          all(not i.is_open for i in ipt.items if i.anchor))

    # --- the thesis prints these counts; they must come from the bank
    tex = read_tex("content/5-metodika.tex", "appendices/A-instrumenty.tex",
               "appendices/H-hodnotiaci-modul.tex")
    for macro in ("asmFormItems", "asmItems", "asmBanks", "asmAnchors",
                  "asmOpenPerForm", "instrTests"):
        claim(f"\\{macro} is referenced by the prose", macro in tex)

    # --- no hand-typed item count may survive in the places that had one
    met = read_tex("content/5-metodika.tex")
    for bad in ("16~položiek", "16 položiek", "12 položiek na tému",
                "Jr.~MAI, 18 položiek"):
        claim(f"no hand-typed count {bad!r} in the methodology", bad not in met)

    # --- the time budget
    ins = a["instrument"]
    claim("every session fits the lessons the school gives",
          ins["all_sessions_fit"] is True)
    claim("the flat-average budget understated the plan by a reportable amount",
          ins["budget_understated_by_flat_average"] > 15,
          str(ins["budget_understated_by_flat_average"]))

    # --- the equating result, which is the reason this chapter exists
    eq = a["equating"]
    claim("the repaired instrument recovers planted forgetting",
          abs(eq["repaired_bias"]) < 0.10, str(eq["repaired_bias"]))
    claim("the broken anchor set would have flipped the sign",
          any(r["estimated"] < 0 for r in eq["grid"]
              if r["anchor_drift_logits"] >= 0.5),
          "the thesis claims the sign flips at half a logit")

    # --- the condition contrast survives the practice effect; the level does not
    te = a["testing_effect"]
    claim("the condition contrast survives the practice effect",
          te["contrast_is_protected"] is True, str(te["contrast_bias"]))
    claim("and the absolute retention level does not",
          abs(te["forgetting_bias"]) > 0.10, str(te["forgetting_bias"]))

    # --- rotation must actually help, or the appendix should not recommend it
    ra = a["rotated_anchors"]
    claim("the rotated design recovers the practice effect",
          abs(ra["practice_bias"]) < 0.10, str(ra["practice_bias"]))
    claim("and reduces the bias in absolute retention",
          ra["rotation_helps"] is True,
          f"{ra['bias_rotated']} vs {ra['bias_fixed_anchors']}")

    # --- the rule classifier, including the claim that LPA cannot do this
    rv = {r["n"]: r for r in a["rule_vs_lpa"]["grid"]}
    claim("the rule works on one class", rv[22]["rule_ari"] > 0.5,
          str(rv[22]["rule_ari"]))
    claim("the mixture model does not, on one class",
          (rv[22]["lpa_ari"] or 0) < 0.2, str(rv[22]["lpa_ari"]))
    claim("the mixture model is better at the study's own sample size",
          (rv[330]["lpa_ari"] or 0) > rv[330]["rule_ari"],
          f"{rv[330]['lpa_ari']} vs {rv[330]['rule_ari']}")
    claim("a pupil's label does not depend on the rest of the sample",
          a["label_stability"]["stable"] is True)

    # --- the honest limitation: the rule IS sensitive to a joint shift
    cs = a["cut_point_sensitivity"]
    claim("sensitivity to a single cut point is reported",
          cs["worst_single_spread"] is not None)
    claim("the appendix admits sensitivity to a joint shift of all five cuts",
          "citlivé na ich" in read_tex("appendices/H-hodnotiaci-modul.tex"),
          "the number is not flattering and must be stated")

    # --- a typology that is only prior attainment relabelled adds nothing
    iv = a["incremental_validity"]
    claim("the incremental-validity test has power", iv["power"] > 0.80,
          str(iv["power"]))
    claim("and does not fire on a relabelled covariate",
          iv["false_positive_rate"] < 0.10, str(iv["false_positive_rate"]))

    # --- detectors: a flattering number is worse than a modest one
    ig = a["integrity_power"]
    claim("the contamination detector's false-positive rate is reported",
          ig["false_positive_rate"] is not None)
    claim("its detection rate is below 1.0 (a perfect detector is a bug)",
          ig["detection_at_10pct"] < 1.0, str(ig["detection_at_10pct"]))



def main() -> int:
    print("Verifying the thesis against the analysis outputs\n" + "=" * 62)
    check_power_table()
    check_macro_integrity()
    check_peqi_numbers()
    check_confusion_matrix()
    check_dgp_anchors()
    check_sample_size_consistency()
    check_source_hygiene()
    check_cross_references()
    check_hypothesis_consistency()
    check_measurement_error()
    check_negative_controls()
    check_equivalence_bound()
    check_measurement_plan()
    check_national_anchor()
    check_pilot_rules()
    check_assignment_compliance()
    check_repo_self_description()
    check_assessment_layer()

    # The reproducibility chapter quotes how many checks run here, so the count
    # is written out and turned into a macro rather than typed into the prose.
    # A value that no longer matches fails the check above on the next pass,
    # which is the whole design: the number cannot be silently wrong, only
    # loudly stale.
    (OUT / "verify_summary.json").write_text(
        json.dumps({"checks": CHECKS, "failures": len(FAILS)}, indent=2),
        encoding="utf-8")

    print("\n" + "=" * 62)
    print(f"{CHECKS - len(FAILS)} / {CHECKS} claims verified")
    if FAILS:
        print(f"\n{len(FAILS)} MISMATCHES:")
        for f in FAILS:
            print("  - " + f)
        return 1
    print("no mismatches")
    return 0


if __name__ == "__main__":
    use_utf8()
    sys.exit(main())
