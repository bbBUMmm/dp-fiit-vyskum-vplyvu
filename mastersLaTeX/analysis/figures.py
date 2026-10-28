"""figures.py -- every figure in the thesis, generated from the analysis outputs.

Print-safe house style: serif type to match newpx, a single ink-on-paper palette
that survives greyscale photocopying, no chartjunk, no gridline clutter, and
each panel carrying exactly one claim.

Usage:  python figures.py     -> ../assets/images/fig_*.png  (and .pdf)
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, Rectangle
from console import use_utf8

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
IMG = HERE.parent / "assets" / "images"
IMG.mkdir(parents=True, exist_ok=True)

# --- house style -------------------------------------------------------------
INK = "#1a1a1a"
GREY = "#8a8a8a"
LIGHT = "#d8d8d8"
COND_COLOR = {"K": "#b0b0b0", "G": "#4c4c4c", "A": "#111111"}
COND_HATCH = {"K": "", "G": "///", "A": ""}
COND_LABEL = {"K": "K – klasická", "G": "G – generický AI", "A": "A – adaptívny AI"}

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["DejaVu Serif", "Times New Roman", "Georgia"],
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "axes.edgecolor": INK,
    "axes.linewidth": 0.7,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.color": INK, "ytick.color": INK, "text.color": INK,
    "xtick.major.width": 0.7, "ytick.major.width": 0.7,
    "legend.frameon": False,
    "figure.dpi": 200,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
})


def save(fig, name: str):
    for ext in ("png", "pdf"):
        fig.savefig(IMG / f"{name}.{ext}")
    plt.close(fig)
    print("wrote", IMG / f"{name}.png")


# ============================================================ 1. design diagram
def fig_design():
    seqs = [("K", "G", "A"), ("K", "A", "G"), ("G", "K", "A"),
            ("G", "A", "K"), ("A", "K", "G"), ("A", "G", "K")]
    fig, (ax0, ax1) = plt.subplots(2, 1, figsize=(6.6, 5.0),
                                   gridspec_kw={"height_ratios": [1.25, 1]})

    # --- upper: the Latin square -------------------------------------------
    ax0.set_xlim(-0.2, 3.9); ax0.set_ylim(-0.6, 6.5); ax0.axis("off")
    ax0.text(-0.15, 6.15, "Sekvencia\n(trieda)", ha="left", va="center", fontsize=8,
             style="italic", color=GREY)
    for j, lab in enumerate(["Perióda 1\nT1 vyhľadávanie",
                             "Perióda 2\nT2 triedenie",
                             "Perióda 3\nT3 rekurzia"]):
        ax0.text(1 + j, 6.15, lab, ha="center", va="center", fontsize=8,
                 style="italic", color=GREY)
    for i, seq in enumerate(seqs):
        y = 5 - i
        ax0.text(0.05, y, f"S{i + 1}", ha="left", va="center", fontsize=8.5)
        for j, c in enumerate(seq):
            ax0.add_patch(Rectangle((0.62 + j, y - 0.34), 0.76, 0.68,
                                    facecolor=COND_COLOR[c], edgecolor=INK, lw=0.6))
            ax0.text(1 + j, y, c, ha="center", va="center", fontsize=11,
                     fontweight="bold", color="white" if c != "K" else INK)
    ax0.set_title("3 × 3 latinský štvorec, 6 sekvencií (vyvážený pre prenos 1. rádu)",
                  loc="left", pad=6)
    handles = [Rectangle((0, 0), 1, 1, facecolor=COND_COLOR[c], edgecolor=INK, lw=0.6)
               for c in "KGA"]
    ax0.legend(handles, [COND_LABEL[c] for c in "KGA"], loc="center left",
               bbox_to_anchor=(0.995, 0.5), fontsize=8)

    # --- lower: the timeline ------------------------------------------------
    ax1.set_xlim(-0.4, 7.2); ax1.set_ylim(-1.25, 1.35); ax1.axis("off")
    ax1.plot([-0.1, 6.9], [0, 0], color=INK, lw=1.0, zorder=1)
    stops = [
        (0.0, "T0\ntýždeň 0", "Vstupná batéria\n45 min", "up"),
        (1.3, "P1\ntýždeň 1", "Lekcia T1 + IPT1\n90 + 20 min", "down"),
        (2.6, "P2\ntýždeň 2", "Lekcia T2 + IPT2", "up"),
        (3.9, "P3\ntýždeň 3", "Lekcia T3 + IPT3", "down"),
        (5.6, "T4\ntýždeň 6", "Oneskorený test DRT\n+ transfer TT", "up"),
        (6.9, "T5\ntýždeň 7", "Rozhovory\n(n ≈ 18)", "down"),
    ]
    for x, lab, sub, side in stops:
        ax1.plot([x], [0], marker="o", ms=6, color=INK, zorder=3)
        dy = 0.36 if side == "up" else -0.36
        ax1.text(x, dy, lab, ha="center", va="bottom" if side == "up" else "top",
                 fontsize=8, fontweight="bold")
        ax1.text(x, dy + (0.46 if side == "up" else -0.46), sub, ha="center",
                 va="bottom" if side == "up" else "top", fontsize=7.2, color=GREY)
    ax1.annotate("", xy=(5.55, -0.05), xytext=(3.95, -0.05),
                 arrowprops=dict(arrowstyle="<->", lw=0.8, color=GREY))
    ax1.text(4.75, -0.16, "3 týždne bez opakovania", ha="center", va="top",
             fontsize=7.2, style="italic", color=GREY)
    ax1.set_title("Časový plán zberu údajov", loc="left", pad=2)
    save(fig, "fig_design")


# ================================================================== 2. power
def fig_power():
    g = pd.read_csv(OUT / "power_grid.csv")
    sens = pd.read_csv(OUT / "power_sensitivity.csv")
    eqv = pd.read_csv(OUT / "power_equivalence.csv")

    fig, axes = plt.subplots(1, 3, figsize=(7.0, 2.5))

    ax = axes[0]
    styles = {0.0: ("-", INK), 0.015: ("--", "#3d3d3d"), 0.03: ("-.", GREY), 0.06: (":", "#b5b5b5")}
    for tau, sub in g.groupby("tau2_ct"):
        ls, col = styles[tau]
        ax.plot(sub.n_classes, sub.AK, ls, color=col, marker="o", ms=3, lw=1.2,
                label=rf"$\tau^2_{{ct}}$ = {tau:g}")
    ax.axhline(0.8, color=INK, lw=0.6, ls=(0, (1, 2)))
    ax.set_xlabel("počet tried $J$"); ax.set_ylabel("sila testu")
    ax.set_title("(a) A vs. K, $d$ = 0,30", loc="left")
    ax.set_ylim(0, 1.03); ax.legend(fontsize=6.6, loc="lower right")

    ax = axes[1]
    for tau, sub in g.groupby("tau2_ct"):
        ls, col = styles[tau]
        ax.plot(sub.n_classes, sub.GK_equiv, ls, color=col, marker="s", ms=3, lw=1.2)
    ax.axhline(0.8, color=INK, lw=0.6, ls=(0, (1, 2)))
    ax.set_xlabel("počet tried $J$")
    ax.set_title("(b) ekvivalencia G ≡ K\n(TOST, SESOI = 0,30)", loc="left")
    ax.set_ylim(0, 1.03)

    ax = axes[2]
    ax.plot(sens.d, sens.power_AK, "-", color=INK, marker="o", ms=3, lw=1.2)
    ax.axhline(0.8, color=GREY, lw=0.6, ls=(0, (1, 2)))
    ax.axvline(0.30, color=GREY, lw=0.6, ls=(0, (1, 2)))
    ax.set_xlabel("skutočný účinok $d$"); ax.set_title("(c) citlivosť pri $J$ = 12", loc="left")
    ax.set_ylim(0, 1.03)
    fig.tight_layout()
    save(fig, "fig_power")

    # separate: equivalence operating characteristic
    fig, ax = plt.subplots(figsize=(3.4, 2.4))
    ax.plot(eqv.true_delta_GK, eqv.power_equiv, "-o", color=INK, ms=3, lw=1.2,
            label="vyhlásiť ekvivalenciu")
    ax.plot(eqv.true_delta_GK, eqv.power_super, "--s", color=GREY, ms=3, lw=1.2,
            label="vyhlásiť rozdiel")
    ax.axvspan(-0.30, 0.30, color=LIGHT, alpha=0.45, zorder=0)
    ax.set_xlabel("skutočný rozdiel G − K ($d$)"); ax.set_ylabel("pravdepodobnosť")
    ax.set_title("Operačná charakteristika TOST ($J$ = 12)", loc="left")
    ax.legend(fontsize=7)
    save(fig, "fig_equivalence")


# ========================================================= 3. expected results
def fig_expected(tag: str = "_J18"):
    res = json.load(open(OUT / f"results{tag}.json", encoding="utf-8"))
    d = pd.read_csv(OUT / f"simulated_long{tag}.csv")

    outcomes = [("practice_acc", "výkon\npočas hodiny"),
                ("theta_imm", "okamžitý\ntest"),
                ("theta_del", "oneskorený\ntest (3 t.)"),
                ("theta_tt", "transfer"),
                ("fol", "pocit\nnaučenia")]
    fig, ax = plt.subplots(figsize=(6.6, 2.9))
    width = 0.26
    xs = np.arange(len(outcomes))
    for i, c in enumerate("KGA"):
        means, errs = [], []
        for col, _ in outcomes:
            sub = d[d.cond == c][col].dropna()
            ref = d[col].dropna()
            z = (sub.mean() - ref.mean()) / ref.std()
            means.append(z)
            errs.append(sub.std() / np.sqrt(len(sub)) / ref.std() * 1.96)
        ax.bar(xs + (i - 1) * width, means, width, yerr=errs, capsize=2,
               color=COND_COLOR[c], edgecolor=INK, lw=0.6, label=COND_LABEL[c],
               error_kw=dict(lw=0.7, ecolor=INK))
    ax.axhline(0, color=INK, lw=0.7)
    ax.set_xticks(xs); ax.set_xticklabels([l for _, l in outcomes], fontsize=8)
    ax.set_ylabel("štandardizovaný priemer (SD)")
    ax.set_title("Očakávaný obrazec: prospech v hodine a v pocite,\n"
                 "nie však v odloženom vybavení", loc="left")
    ax.legend(fontsize=7.5, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.22))
    # highlight the dissociation
    ax.annotate("disociácia", xy=(2.0, -0.05), xytext=(2.05, 0.62), fontsize=7.6,
                style="italic", color=INK,
                arrowprops=dict(arrowstyle="->", lw=0.7, color=INK,
                                connectionstyle="arc3,rad=-0.25"))
    save(fig, "fig_expected")


# ============================================================= 4. calibration
def fig_calibration(tag: str = "_J18"):
    d = pd.read_csv(OUT / f"simulated_long{tag}.csv")
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.7))

    ax = axes[0]
    ax.plot([0, 1], [0, 1], color=GREY, lw=0.8, ls=(0, (2, 2)))
    for c in "KGA":
        sub = d[d.cond == c]
        ax.scatter(sub.acc_imm, sub.jol_imm, s=5, alpha=0.30,
                   color=COND_COLOR[c], edgecolors="none")
        ax.scatter([sub.acc_imm.mean()], [sub.jol_imm.mean()], s=60, marker="D",
                   color=COND_COLOR[c], edgecolors=INK, lw=0.8, zorder=5,
                   label=COND_LABEL[c])
    ax.set_xlabel("skutočná úspešnosť"); ax.set_ylabel("sebadôvera (JOL)")
    ax.set_title("(a) kalibrácia", loc="left")
    ax.text(0.06, 0.93, "nadhodnotenie", fontsize=7, color=GREY, style="italic")
    ax.text(0.52, 0.10, "podhodnotenie", fontsize=7, color=GREY, style="italic")
    ax.legend(fontsize=6.8, loc="lower right")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)

    ax = axes[1]
    parts = [d[d.cond == c]["calib_bias"].dropna().to_numpy() for c in "KGA"]
    vp = ax.violinplot(parts, showmeans=True, showextrema=False, widths=0.8)
    for body, c in zip(vp["bodies"], "KGA"):
        body.set_facecolor(COND_COLOR[c]); body.set_edgecolor(INK)
        body.set_alpha(0.85); body.set_linewidth(0.6)
    vp["cmeans"].set_color(INK); vp["cmeans"].set_linewidth(1.0)
    ax.axhline(0, color=INK, lw=0.7)
    ax.set_xticks([1, 2, 3]); ax.set_xticklabels(["K", "G", "A"])
    ax.set_ylabel("skreslenie (JOL − správnosť)")
    ax.set_title("(b) nadhodnotenie porozumenia", loc="left")
    fig.tight_layout()
    save(fig, "fig_calibration")


# ============================================================ 5. PEQI / ICAP
def fig_peqi():
    sess = pd.read_csv(OUT / "peqi_sessions.csv")
    rep = json.load(open(OUT / "peqi_report.json", encoding="utf-8"))

    fig = plt.figure(figsize=(6.8, 5.2))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.15, 1.0], hspace=0.55, wspace=0.34)

    # (a) the ladder
    ax = fig.add_subplot(gs[0, :])
    ax.set_xlim(0, 10.5); ax.set_ylim(-0.05, 3.5); ax.axis("off")
    rungs = [("L0", "SOLVE", "pasívne", "„napíš mi\nkód“", 0.00),
             ("L1", "VERIFY", "aktívne", "„je to\nsprávne?“", 0.25),
             ("L2", "EXPLAIN", "aktívne", "„prečo je to\nO(log n)?“", 0.50),
             ("L3", "ELABORATE", "konštruktívne", "„kedy je lineárne\nlepšie?“", 0.75),
             ("L4", "SELF-EXPL.", "interaktívne", "„myslím X, kde\nrobím chybu?“", 1.00)]
    bw, gap = 1.86, 0.30
    for i, (code, name, icap, ex, w) in enumerate(rungs):
        x = 0.12 + i * (bw + gap)
        cx = x + bw / 2
        shade = 0.84 - 0.17 * i
        ax.add_patch(Rectangle((x, 1.62), bw, 0.80, facecolor=str(max(shade, 0.06)),
                               edgecolor=INK, lw=0.7))
        fg = "white" if i >= 2 else INK
        ax.text(cx, 2.22, code, ha="center", va="center", fontsize=9.5,
                fontweight="bold", color=fg)
        ax.text(cx, 1.86, name, ha="center", va="center", fontsize=7.2, color=fg)
        ax.text(cx, 3.26, icap, ha="center", va="center", fontsize=7.2,
                style="italic", color=GREY)
        ax.text(cx, 2.72, f"w = {w:.2f}", ha="center", va="center", fontsize=7, color=GREY)
        ax.text(cx, 1.42, ex, ha="center", va="top", fontsize=6.5, color=INK)
    ax.annotate("", xy=(10.35, 0.42), xytext=(0.12, 0.42),
                arrowprops=dict(arrowstyle="->", lw=0.9, color=INK))
    ax.text(5.25, 0.22, "rastúce kognitívne zapojenie (ICAP; Chi a Wylie, 2014)",
            ha="center", va="top", fontsize=7.2, style="italic", color=GREY)
    ax.set_title("(a) Taxonómia promptov a váhy indexu PEQI", loc="left", pad=1)

    # (b) distribution of PEQI
    ax = fig.add_subplot(gs[1, 0])
    for c in ("G", "A"):
        sub = sess[sess.cond == c]["peqi"].dropna()
        ax.hist(sub, bins=24, alpha=0.75, color=COND_COLOR[c], edgecolor=INK,
                lw=0.4, label=COND_LABEL[c])
    ax.set_xlabel("PEQI"); ax.set_ylabel("počet relácií")
    ax.set_title("(b) rozdelenie PEQI", loc="left")
    ax.legend(fontsize=6.8)

    # (c) mediation path diagram
    ax = fig.add_subplot(gs[1, 1])
    ax.set_xlim(-0.3, 10.3); ax.set_ylim(-0.6, 7.4); ax.axis("off")
    boxes = [(0.0, 2.2, 2.9, 1.5, "podmienka\nA vs. G"),
             (3.55, 5.5, 2.9, 1.3, "PEQI"),
             (7.1, 2.2, 2.9, 1.5, "oneskorené\nvybavenie")]
    for x, y, w, h, lab in boxes:
        ax.add_patch(Rectangle((x, y), w, h, facecolor="white", edgecolor=INK, lw=0.8))
        ax.text(x + w / 2, y + h / 2, lab, ha="center", va="center", fontsize=7.4)
    ident = json.load(open(OUT / "results_J18.json",
                       encoding="utf-8"))["identification_H6"]
    med = ident["1_mediation_lsem"]
    ax.add_patch(FancyArrowPatch((2.0, 3.75), (3.9, 5.45), arrowstyle="->",
                                 mutation_scale=9, lw=0.9, color=INK))
    ax.add_patch(FancyArrowPatch((6.1, 5.45), (8.0, 3.75), arrowstyle="->",
                                 mutation_scale=9, lw=0.9, color=INK))
    ax.add_patch(FancyArrowPatch((2.95, 2.95), (7.05, 2.95), arrowstyle="->",
                                 mutation_scale=9, lw=0.9, color=GREY, linestyle="--"))
    ax.text(2.25, 4.95, f"a = {med['a_path']['est']:.2f}***", fontsize=7, ha="center")
    ax.text(7.85, 4.95, f"b = {med['b_path']['est']:.2f}**", fontsize=7, ha="center")
    ax.text(5.0, 3.15, f"c′ = {med['direct']:.2f} n.s.", fontsize=7,
            ha="center", va="bottom", color=GREY)
    ax.text(5.0, 1.55, f"nepriamy účinok = {med['indirect']:.2f}\n"
                       f"95 % MC CI [{med['indirect_ci95'][0]:.2f}; "
            f"{med['indirect_ci95'][1]:.2f}]",
            fontsize=6.9, ha="center", va="top", style="italic")
    ax.set_title("(c) mediačný model (H6)", loc="left")
    save(fig, "fig_peqi")


# ============================================================ 6. moderation H7
def fig_moderation(tag: str = "_J18"):
    d = pd.read_csv(OUT / f"simulated_long{tag}.csv").dropna(subset=["theta_del"])
    fig, ax = plt.subplots(figsize=(3.6, 2.7))
    xs = np.linspace(-2, 2, 50)
    ref = d["theta_del"]
    for c in "KGA":
        sub = d[d.cond == c]
        b1, b0 = np.polyfit(sub.theta_pre, sub.theta_del, 1)
        ax.plot(xs, ((b0 + b1 * xs) - ref.mean()) / ref.std(), lw=1.5,
                color=COND_COLOR[c], label=COND_LABEL[c],
                ls={"K": (0, (4, 2)), "G": "-", "A": "-"}[c])
    ax.axhline(0, color=GREY, lw=0.6)
    ax.set_xlabel("vstupné vedomosti $\\theta_{pre}$ (SD)")
    ax.set_ylabel("oneskorené vybavenie (SD)")
    ax.set_title("H7: generický AI poškodzuje\nnajmä slabších žiakov", loc="left")
    ax.legend(fontsize=6.8, loc="upper left")
    save(fig, "fig_moderation")


# ================================================== 7. identification / DAG
def fig_dag():
    """What randomisation identifies, and what it does not."""
    fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.9),
                             gridspec_kw={"width_ratios": [1.15, 1]})

    def node(ax, x, y, w, h, text, dashed=False, fill="white", fs=7.4):
        ax.add_patch(Rectangle((x, y), w, h, facecolor=fill, edgecolor=INK,
                               lw=0.9, linestyle=(0, (3, 2)) if dashed else "solid",
                               zorder=3))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
                fontsize=fs, zorder=4, linespacing=1.3)

    def edge(ax, p1, p2, label="", dashed=False, rad=0.0, lab_pos=0.5,
             dy=1.4, col=INK):
        ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=9,
                                     lw=0.9, color=col, zorder=2,
                                     linestyle="--" if dashed else "-",
                                     connectionstyle=f"arc3,rad={rad}"))
        if label:
            x = p1[0] + (p2[0] - p1[0]) * lab_pos
            y = p1[1] + (p2[1] - p1[1]) * lab_pos + dy
            ax.text(x, y, label, ha="center", va="bottom", fontsize=7, color=col)

    # --- (a) the causal graph ------------------------------------------
    ax = axes[0]
    ax.set_xlim(-2, 104); ax.set_ylim(-18, 58); ax.axis("off")
    node(ax, 1, 18, 23, 13, "podmienka\n$A$ vs. $G$", fill=LIGHT)
    node(ax, 40, 42, 22, 12, "PEQI\n$M$")
    node(ax, 78, 18, 24, 13, "odložené\nvybavenie $Y$")
    node(ax, 40, -2, 22, 11, "$U$\nnepozorované", dashed=True)

    edge(ax, (24, 26), (40, 46), rad=0.10)
    ax.text(24, 41, "$a$\nrandomizované", ha="left", va="center", fontsize=6.8)
    edge(ax, (62, 46), (80, 28), rad=0.10)
    ax.text(73, 42, "$b$\npredpoklad", ha="left", va="center", fontsize=6.8)
    edge(ax, (24, 23), (78, 23), "$c'$", lab_pos=0.42, dy=1.4)
    edge(ax, (48, 9), (48, 42), dashed=True, col=GREY)
    edge(ax, (62, 9), (86, 18), dashed=True, col=GREY)
    ax.text(51, -15, "randomizácia identifikuje $a$ a celkový účinok $c' + ab$,\n"
            "nie však $b$ samotné — to vyžaduje predpoklad o $U$",
            ha="center", va="bottom", fontsize=6.9, style="italic", color=GREY)
    ax.set_title("(a) Čo randomizácia identifikuje", loc="left", pad=2)

    # --- (b) sensitivity curve -----------------------------------------
    ax = axes[1]
    res = json.load(open(OUT / "results_J18.json", encoding="utf-8"))
    sens = res["identification_H6"]["4_sensitivity"]
    rho = np.array([c["rho"] for c in sens["curve"]])
    ind = np.array([c["indirect"] for c in sens["curve"]])
    ax.plot(rho, ind, "-", color=INK, lw=1.4)
    ax.axhline(0, color=INK, lw=0.7)
    ax.axvline(0, color=GREY, lw=0.6, ls=(0, (1, 2)))
    r = sens["rho_star"]
    ax.plot([r], [0], marker="o", ms=5, color=INK, zorder=5)
    ax.annotate(rf"$\rho^\ast$ = {r:.2f}".replace(".", ","),
                xy=(r, 0), xytext=(r + 0.10, max(ind) * 0.45), fontsize=7.4,
                arrowprops=dict(arrowstyle="->", lw=0.7, color=INK))
    ax.axvspan(-0.05, 0.05, color=LIGHT, alpha=0.5, zorder=0)
    ax.text(-0.58, min(ind) * 0.72, "pásmo hodnoverného\nzvyškového zmätenia",
            ha="left", va="center", fontsize=6.6, style="italic", color=GREY)
    ax.set_xlabel(r"$\rho$ = korelácia nepozorovaných zložiek $M$ a $Y$")
    ax.set_ylabel("nepriamy účinok")
    ax.set_title("(b) Citlivosť na zmätenie", loc="left", pad=2)
    fig.tight_layout()
    save(fig, "fig_dag")


# ==================================================== 8. mechanism precision
def fig_mechanism():
    m = pd.read_csv(OUT / "power_mechanism.csv")
    fig, ax = plt.subplots(figsize=(3.6, 2.6))
    ax.plot(m.n_classes, m.power_iv, "-o", color=INK, ms=3.5, lw=1.3,
            label="účinok odlíšiteľný od nuly")
    ax.plot(m.n_classes, m.power_precision, "--s", color=GREY, ms=3.5, lw=1.3,
            label="interval užší než 0,20")
    ax.axhline(0.8, color=INK, lw=0.6, ls=(0, (1, 2)))
    ax.axvline(18, color=GREY, lw=0.6, ls=(0, (1, 2)))
    ax.set_xlabel("počet tried $J$"); ax.set_ylabel("pravdepodobnosť")
    ax.set_ylim(0, 1.04)
    ax.set_title("Mechanizmus: významnosť je ľahká,\npresnosť nie", loc="left")
    ax.legend(fontsize=6.6, loc="lower right")
    save(fig, "fig_mechanism")


# ============================================================ 9. architecture
def fig_architecture():
    fig, ax = plt.subplots(figsize=(6.8, 3.9))
    ax.set_xlim(0, 100); ax.set_ylim(0, 60); ax.axis("off")

    def box(x, y, w, h, title, sub="", fill="white", ls="solid"):
        ax.add_patch(Rectangle((x, y), w, h, facecolor=fill, edgecolor=INK,
                               lw=0.9, linestyle=ls, zorder=2))
        ax.text(x + w / 2, y + h * (0.70 if sub else 0.50), title, ha="center",
                va="center", fontsize=8, fontweight="bold", zorder=3)
        if sub:
            ax.text(x + w / 2, y + h * 0.30, sub, ha="center", va="center",
                    fontsize=6.3, color=GREY, zorder=3, linespacing=1.4)

    def arrow(x1, y1, x2, y2, dashed=False):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                     mutation_scale=10, lw=0.9, color=INK,
                                     linestyle="--" if dashed else "-", zorder=4))

    ax.add_patch(Rectangle((1, 15), 65, 43, facecolor="#f4f4f4", edgecolor=GREY,
                           lw=0.7, linestyle=(0, (4, 3)), zorder=0))
    ax.text(2.6, 55.6, "školský notebook", fontsize=6.8, style="italic", color=GREY)

    box(3, 38, 26, 17, "Prehliadač", "cvičné rozhranie\n(panel asistenta: G, A)")
    box(38, 38, 26, 17, "mitmproxy", "terminácia TLS,\nzoznam povolených adries")
    box(72, 38, 26, 17, "Aplikačná vrstva  ·  Java",
        "odstránenie PII, pseudonymizácia,\nklasifikácia promptov, PEQI")
    box(38, 18, 26, 13, "JSON Lines", "trvalý, auditovateľný,\nspätne prehrateľný", fill=LIGHT)
    box(72, 18, 26, 13, "Analytický dataset", "žiak × perióda,\nbez voľného textu", fill=LIGHT)
    box(3, 1, 26, 11, "Poskytovateľ modelu", "ten istý model pre G aj A", ls=(0, (3, 2)))
    box(72, 1, 26, 11, "Udalosti rozhrania",
        "zobrazenie úlohy, pokus,\nodomknutie riešenia", ls=(0, (3, 2)))

    arrow(29, 48, 38, 48)
    ax.text(33.5, 49.4, "HTTPS", ha="center", va="bottom", fontsize=6.4,
            color=GREY, style="italic")
    arrow(51, 38, 51, 31.5)
    ax.text(52.2, 35.6, "zhodné\npožiadavky", ha="left", va="center", fontsize=6.4,
            color=GREY, style="italic")
    arrow(64, 25, 72, 40)
    ax.text(66.4, 26.8, "sleduje koniec súboru", ha="left", va="center",
            fontsize=6.4, color=GREY, style="italic", rotation=30)
    arrow(85, 38, 85, 31.5)
    arrow(16, 38, 16, 12.5, dashed=True)
    ax.text(17.3, 25, "cez proxy k modelu", ha="left", va="center", fontsize=6.4,
            color=GREY, style="italic", rotation=90)
    arrow(85, 12, 85, 18, dashed=True)
    ax.set_title("Architektúra nástroja po revízii", loc="left", pad=4)
    save(fig, "fig_architecture")


FIGURES = (fig_design, fig_power, fig_expected, fig_calibration, fig_peqi,
           fig_moderation, fig_dag, fig_mechanism, fig_architecture)

if __name__ == "__main__":
    use_utf8()
    for fn in FIGURES:
        fn()
    print(f"{len(FIGURES)} figure sets written to {IMG}")
