"""Results charts for Attention Is All You Need. Every value is from Table 2 (newstest2014)."""
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills" / "make-paper-easy" / "scripts"))
from plot_style import apply, PALETTE, INK, MUTED, bar_labels, save  # noqa: E402

apply()
GRAY, HI = "#C9C7BF", PALETTE[2]

# Table 2 rows: (model, BLEU EN-DE, BLEU EN-FR, cost EN-DE FLOPs)
rows = [
    ("ByteNet", 23.75, None, None),
    ("Deep-Att + PosUnk", None, 39.2, None),
    ("GNMT + RL", 24.6, 39.92, 2.3e19),
    ("ConvS2S", 25.16, 40.46, 9.6e18),
    ("MoE", 26.03, 40.56, 2.0e19),
    ("Deep-Att + PosUnk Ens.", None, 40.4, None),
    ("GNMT + RL Ens.", 26.30, 41.16, 1.8e20),
    ("ConvS2S Ens.", 26.36, 41.29, 7.7e19),
    ("Transformer (base)", 27.3, 38.1, 3.3e18),
    ("Transformer (big)", 28.4, 41.8, 2.3e19),
]
fig = plt.figure(figsize=(15.5, 4.8))
gs = fig.add_gridspec(1, 3, width_ratios=[1.3, 1.3, 1.3], wspace=0.62)


def hbar(ax, idx, title, xlim):
    data = [(m, r[idx]) for m, *rest in rows for r in [(None, *rest)] if r[idx] is not None]
    names, vals = zip(*data)
    y = np.arange(len(names))[::-1]
    colors = [HI if "Transformer" in n else GRAY for n in names]
    bars = ax.barh(y, vals, color=colors, height=0.62)
    for b, v in zip(bars, vals):
        ax.text(v + 0.08, b.get_y() + b.get_height() / 2, f"{v:g}", va="center", fontsize=8.5,
                color=INK, fontweight="bold" if b.get_facecolor()[:3] != (0.788, 0.78, 0.749) and v in (28.4, 27.3, 41.8, 38.1) else "normal")
    ax.set_yticks(y, names)
    ax.set_xlim(*xlim)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x")
    ax.set_xlabel("BLEU (higher is better)")
    ax.set_title(title)


# (a) EN-DE BLEU
ax = fig.add_subplot(gs[0])
hbar(ax, 1, "(a) English→German BLEU", (22, 29.5))

# (b) quality vs training cost, EN-DE
ax = fig.add_subplot(gs[1])
pts = [(m, de, c) for m, de, fr, c in rows if de is not None and c is not None]
for m, de, c in pts:
    t = "Transformer" in m
    ax.scatter(c, de, s=90 if t else 60, color=HI if t else "#9A988F", marker="D" if t else "o",
               edgecolor="white", linewidth=1.5, zorder=3)
    # hand-placed offsets (points) so every label sits next to its own dot
    off, ha = {"GNMT + RL": ((8, 0), "left"), "ConvS2S": ((8, 0), "left"), "MoE": ((-8, 0), "right"),
               "GNMT + RL Ens.": ((8, 0), "left"), "ConvS2S Ens.": ((0, 12), "center"),
               "Transformer (base)": ((9, 0), "left"), "Transformer (big)": ((9, 0), "left")}[m]
    ax.annotate(m, (c, de), xytext=off, textcoords="offset points", fontsize=8.5,
                ha=ha, va="center",
                color=INK if t else MUTED, fontweight="bold" if t else "normal")
ax.set_xscale("log")
ax.set_xlim(1.5e18, 2e21)
ax.set_ylim(23.8, 29.2)
ax.grid(axis="x", which="major")
ax.set_xlabel("Training cost, FLOPs (log scale)")
ax.set_ylabel("BLEU EN→DE")
ax.set_title("(b) Higher BLEU for less training")

# (c) EN-FR BLEU
ax = fig.add_subplot(gs[2])
hbar(ax, 2, "(c) English→French BLEU", (37, 42.6))

out = Path(__file__).with_name("results.png")
save(fig, str(out))
print(f"Wrote {out}")
