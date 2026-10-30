"""tex_export.py -- the appendix, generated from the bank.

The point
---------
Appendix A of the thesis prints the instruments. The runner administers them. If
those are two copies of the same specification, they will diverge -- not as a
risk but as a fact already established twice in this project, once in the PEQI
classifier (Python and Java) and once in the console guard (one entry point out
of eighteen). The second copy always loses, and it loses silently, and here the
losing copy would be the one the thesis is marked on.

So the appendix is output. `python tex_export.py` writes
`mastersLaTeX/appendices/A-instrumenty-generated.tex`, and a check in
`verify_thesis.py` fails the build if the file on disk is not what the bank
produces. The item counts, the blueprint table, the anchor marks and the time
budget are all derived, so none of them can be stale.

What is NOT generated
---------------------
The prose: why ICAR rather than Raven, why the iBobor scoring scheme is not
adopted, why the critical-thinking instrument is home-made. Those are arguments,
they belong to the author, and a generator has no business writing them. The
generated file is included INTO the hand-written appendix at the points where
items are listed, so the two kinds of content stay visibly separate.

Run:  python tex_export.py              write the file
      python tex_export.py --check      exit 1 if the file is stale
"""
from __future__ import annotations

import sys
from pathlib import Path

from bank import (BLUEPRINT, LEVELS, OPEN_ITEMS_PER_FORM, Bank, Item, load_all)
import sessions

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "mastersLaTeX" / "appendices" / "A-instrumenty-generated.tex"
MACROS = HERE.parent / "mastersLaTeX" / "appendices" / "instrument-numbers.tex"

LEVEL_SK = {"zapamatanie": "Zapamätanie", "porozumenie": "Porozumenie",
            "aplikacia": "Aplikácia", "analyza": "Analýza",
            "hodnotenie": "Hodnotenie"}


def esc(s: str) -> str:
    """LaTeX-escape item text. Deliberately small: item stems are plain Slovak."""
    out = []
    for ch in s:
        if ch in "&%$#_{}":
            out.append("\\" + ch)
        elif ch == "~":
            out.append("\\textasciitilde{}")
        elif ch == "^":
            out.append("\\textasciicircum{}")
        elif ch == "\\":
            out.append("\\textbackslash{}")
        else:
            out.append(ch)
    t = "".join(out)
    # Typographic characters that pdflatex's utf8 input encoding does not map.
    # They are legitimate in the bank -- a minus sign is a minus sign and an
    # ellipsis is an ellipsis -- so they are translated here, in the printing
    # step, rather than removed from the data. The build caught U+2212 in
    # exactly one rubric criterion; the rest are pre-empted.
    for ch, tex in (("−", "$-$"),          # MINUS SIGN
                    ("…", "\\dots{}"),     # HORIZONTAL ELLIPSIS
                    ("–", "--"),           # EN DASH
                    ("—", "---"),          # EM DASH
                    (" ", "~"),            # NO-BREAK SPACE
                    ("‑", "-"),            # NON-BREAKING HYPHEN
                    ):
        t = t.replace(ch, tex)
    # a few typographic fixes that belong to the printed form, not to the data
    t = t.replace("O(1)", "$\\mathcal{O}(1)$")
    t = t.replace("O(log n)", "$\\mathcal{O}(\\log n)$")
    t = t.replace("O(n log n)", "$\\mathcal{O}(n\\log n)$")
    t = t.replace("O(n²)", "$\\mathcal{O}(n^2)$")
    t = t.replace("O(n)", "$\\mathcal{O}(n)$")
    t = t.replace("log₂ n", "$\\log_2 n$")
    t = t.replace("√n", "$\\sqrt{n}$")
    t = t.replace("×", "$\\times$")
    return t


def mono(s: str) -> str:
    """Array literals and code fragments set in monospace, found by shape."""
    import re
    s = re.sub(r"\[([0-9]+(?:,\s*[0-9]+)+)\]",
               lambda m: "\\texttt{[" + m.group(1) + "]}", s)
    s = re.sub(r"\b(lavy|pravy|stred)\b", r"\\texttt{\1}", s)
    return s


# ===========================================================================
def render_item(it: Item, n: int) -> str:
    stem = mono(esc(it.stem))
    L = [f"    \\item {stem}"]
    if it.options and it.format in ("mc4", "mc3"):
        opts = []
        for i, o in enumerate(it.options):
            mark = "~$\\checkmark$" if i == it.key else ""
            opts.append(f"({chr(97 + i)})~{esc(o)}{mark}")
        L.append("        \\hfill " + " \\quad ".join(opts))
    elif it.format == "choice":
        L.append("        \\hfill (" + " / ".join(esc(o) for o in it.options) + ")")
    elif it.format == "multi" and isinstance(it.key, list):
        opts = []
        for i, o in enumerate(it.options):
            mark = "~$\\checkmark$" if i in it.key else ""
            opts.append(f"({chr(97 + i)})~{esc(o)}{mark}")
        L.append("        \\hfill (označ všetky správne) " + " \\quad ".join(opts))
    elif it.format == "multi":
        L.append("        \\hfill (viac možností: "
                 + " / ".join(esc(o) for o in it.options) + ")")
    elif it.is_open:
        crit = "; ".join(f"{r['points']}~b.\\ {esc(r['criterion'])}"
                         for r in it.rubric)
        L.append(f"        \\hfill (voľná odpoveď; rubrika 0--{it.max_points}: "
                 f"{crit})")
    elif it.format == "likert5":
        L.append("        \\hfill (1--5)")
    elif it.format == "likert7":
        L.append("        \\hfill (1--7)")
    elif it.format == "scale0_10":
        L.append("        \\hfill (0--10)")
    elif it.format == "numeric":
        L.append(f"        \\hfill ({esc(str(it.key))})")
    return "\n".join(L)


def render_bank(b: Bank, label: str, anchor_marks: bool = False) -> str:
    out = [f"\\subsection{{{esc(b.title)}}}", f"\\label{{{label}}}", ""]
    if b.instrument in BLUEPRINT_INSTRUMENTS():
        out.append(f"Položiek: {b.n_items}, bodov: {b.max_points}, "
                   f"z toho {sum(1 for i in b.items if i.is_open)} s rubrikou. "
                   f"Kotviace položky sú označené $\\ast$ a v oboch formách sú "
                   f"v~totožnom znení.")
        out.append("")
    groups: dict[str, list[Item]] = {}
    for it in b.items:
        groups.setdefault(it.level or "", []).append(it)

    n = 0
    for lvl in list(LEVELS) + [""]:
        items = groups.get(lvl)
        if not items:
            continue
        if lvl:
            out.append(f"\\paragraph{{{LEVEL_SK[lvl]} "
                       f"({len(items)} {_pol(len(items))}).}}")
        out.append("\\begin{enumerate}[nosep, label=\\textbf{%s}]"
                   % "\\arabic*.")
        for it in items:
            n += 1
            body = render_item(it, n)
            if anchor_marks and it.anchor:
                body = body.replace("\\item ", "\\item$\\ast$~", 1)
            out.append(body)
        out.append("\\end{enumerate}")
        out.append("")
    return "\n".join(out)


def BLUEPRINT_INSTRUMENTS():
    from bank import BLUEPRINT_FOR
    return BLUEPRINT_FOR


def _pol(n: int) -> str:
    return "položka" if n == 1 else ("položky" if n < 5 else "položiek")


# ===========================================================================
def render_blueprint() -> str:
    rows = "\n".join(
        f"{LEVEL_SK[k]} & {v} & {v} \\\\" for k, v in BLUEPRINT.items())
    total = sum(BLUEPRINT.values())
    return f"""\\begin{{table}}[H]
\\centering
\\caption{{Špecifikačná tabuľka testu --- jedna pre obe formy}}
\\label{{tab:blueprint-gen}}
\\small
\\begin{{tabular}}{{@{{}}lcc@{{}}}}
\\toprule
\\textbf{{Úroveň}} & \\textbf{{Okamžitá forma}} & \\textbf{{Odložená forma}} \\\\
\\midrule
{rows}
\\midrule
\\textbf{{Spolu}} & \\textbf{{{total}}} & \\textbf{{{total}}} \\\\
\\bottomrule
\\end{{tabular}}
\\end{{table}}

Obe formy majú rovnaký počet položiek, rovnaké rozdelenie po kognitívnych
úrovniach a rovnaký počet položiek s rubrikou ({OPEN_ITEMS_PER_FORM}). To nie je
estetická symetria: izomorfia foriem je predpoklad, na ktorom stojí rozdiel
medzi okamžitým a odloženým výkonom, a dve formy rôznej dĺžky s~rôznym pomerom
formátov nie sú izomorfné v~žiadnom zmysle, ktorý by čitateľ mohol overiť.
"""


def render_budget() -> str:
    res = sessions.budget()
    rows = []
    for s in res["sessions"]:
        blocks = ", ".join(f"{b['label']} ({b['items']})" for b in s["blocks"])
        rows.append(f"{s['code']} & {s['lessons']:.0f} & {s['total_min']:.0f} "
                    f"& {s['budget_min']:.0f} & {esc(blocks)} \\\\")
    body = "\n".join(rows)
    return f"""\\begin{{table}}[H]
\\centering
\\caption{{Časový rozpočet, počítaný z položiek}}
\\label{{tab:budget-gen}}
\\small
\\begin{{tabularx}}{{\\textwidth}}{{@{{}}lcccX@{{}}}}
\\toprule
\\textbf{{Stretnutie}} & \\textbf{{Hodín}} & \\textbf{{Potreba}} &
\\textbf{{Rozpočet}} & \\textbf{{Obsah (počet položiek)}} \\\\
\\midrule
{body}
\\bottomrule
\\end{{tabularx}}
\\end{{table}}
"""


def macros() -> str:
    """Numbers about the instruments, as LaTeX macros, so the prose cannot drift."""
    banks = load_all()
    res = sessions.budget()
    cmp_ = sessions.naive_budget_comparison()
    d = {
        "instrItemsTotal": sum(b.n_items for b in banks.values()),
        "instrBanks": len(banks),
        "instrFormItems": banks["T1_IPT"].n_items,
        "instrFormPoints": banks["T1_IPT"].max_points,
        "instrAnchors": len(banks["T1_IPT"].anchors),
        "instrOpenPerForm": OPEN_ITEMS_PER_FORM,
        "instrCtItems": banks["CT"].n_items,
        "instrMaiItems": banks["JRMAI"].n_items,
        "instrPrecheckItems": banks["T1_PRECHECK"].n_items,
        "instrTtItems": banks["TT"].n_items,
        "instrTtPoints": banks["TT"].max_points,
        "instrMeasureLessons": f"{res['measurement_lessons_excl_teaching']:.0f}",
        "instrBudgetUnderstated": f"{cmp_['total_understated']:.1f}",
        "instrBudgetWorst": cmp_["worst"].replace("_", ""),
        "instrBudgetWorstBy": f"{cmp_['worst_by']:.1f}",
        "instrLessonMin": f"{64:.0f}",
        "instrFatigueCap": f"{sessions.FATIGUE_CAP_MIN:.0f}",
    }
    ts = HERE / "out" / "test-summary.json"
    if ts.exists():
        import json as _json
        s = _json.loads(ts.read_text(encoding="utf-8"))
        d["instrTests"] = str(s["passed"])
        d["instrTestSections"] = str(s["sections"])
    else:
        d["instrTests"] = "??"
        d["instrTestSections"] = "??"
    lines = ["% Generated by assessment/tex_export.py -- do not edit.",
             "% Numbers about the measuring instruments themselves.", ""]
    for k, v in d.items():
        lines.append(f"\\newcommand{{\\{k}}}{{{v}}}")
    return "\n".join(lines) + "\n"


def document() -> str:
    banks = load_all()
    parts = ["% ==========================================================",
             "% GENERATED by assessment/tex_export.py from assessment/banks/*.json",
             "% Do not edit. Edit the bank and re-run. verify_thesis.py checks",
             "% that this file is what the bank currently produces.",
             "% ==========================================================", ""]
    parts.append(render_blueprint())
    parts.append(render_bank(banks["T1_PRECHECK"], "sec:gen-precheck"))
    parts.append(render_bank(banks["T1_IPT"], "sec:gen-ipt", anchor_marks=True))
    parts.append(render_bank(banks["T1_DRT"], "sec:gen-drt", anchor_marks=True))
    parts.append(render_bank(banks["TT"], "sec:gen-tt"))
    parts.append(render_bank(banks["CT"], "sec:gen-ct"))
    parts.append(render_bank(banks["JRMAI"], "sec:gen-mai"))
    parts.append(render_bank(banks["BACKGROUND"], "sec:gen-background"))
    parts.append(render_bank(banks["POST_LESSON"], "sec:gen-post"))
    parts.append(render_budget())
    return "\n".join(parts)


def main(argv: list[str]) -> int:
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    doc, mac = document(), macros()
    if "--check" in argv:
        bad = []
        for path, want in ((OUT, doc), (MACROS, mac)):
            have = path.read_text(encoding="utf-8") if path.exists() else ""
            if have != want:
                bad.append(path.name)
        if bad:
            print("STALE: " + ", ".join(bad)
                  + "\n  run: python assessment/tex_export.py")
            return 1
        print("generated instrument files are current")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(doc, encoding="utf-8")
    MACROS.write_text(mac, encoding="utf-8")
    print(f"wrote {OUT.name} ({len(doc.splitlines())} lines)")
    print(f"wrote {MACROS.name} ({mac.count('newcommand')} macros)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
