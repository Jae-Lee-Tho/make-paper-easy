"""Example results figure for LIBERO-PeRM (values copied from the paper's Tables 2-3 and Sec. 3.1).

Run from the repo root:  python examples/libero-perm-dense/results_plot.py
"""
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills" / "make-paper-easy" / "scripts"))
from plot_style import apply, PALETTE, SOFT, HATCHES, INK, MUTED, bar_labels, save  # noqa: E402

apply()
fig = plt.figure(figsize=(13, 4.2))
gs = fig.add_gridspec(1, 3, width_ratios=[2.2, 1.6, 1.0], wspace=0.32)

# (a) Table 2: zero-shot, All-Pref SR vs SA
models = ["OpenVLA-OFT", "π0-fast", "π0.5", "GR00T-N1.6", "SmolVLA", "UniVLA"]
sr = [40.00, 51.25, 66.67, 51.67, 4.17, 45.83]
sa = [4.53, 30.37, 37.92, 27.45, 2.03, 21.52]
ax = fig.add_subplot(gs[0])
x, w = np.arange(len(models)), 0.38
b1 = ax.bar(x - w / 2, sr, w, color=PALETTE[1], label="Task success (SR)")
b2 = ax.bar(x + w / 2, sa, w, color=PALETTE[2], hatch=HATCHES[1], label="Preference satisfied (SA)")
bar_labels(ax, b1, "{:.0f}")
bar_labels(ax, b2, "{:.0f}")
ax.set_xticks(x, models, rotation=22, ha="right", rotation_mode="anchor")
ax.set_ylim(0, 80)
ax.set_ylabel("%")
ax.set_title("(a) Zero-shot: tasks done, preferences ignored")
ax.legend(loc="upper right")

# (b) Table 3: fine-tuned pi0.5 SA by preference type (dumbbell: LoRA vs Mix-LoRA)
cats = ["Motion", "Skill", "User profile", "ComprePref"]
lora = [85.37, 76.67, 85.22, 42.64]
mix = [66.06, 89.29, 91.33, 70.07]
ax = fig.add_subplot(gs[1])
y = np.arange(len(cats))[::-1]
for yi, a_, b_ in zip(y, lora, mix):
    ax.plot([a_, b_], [yi, yi], color="#C9C7BF", lw=3, solid_capstyle="round", zorder=1)
ax.scatter(lora, y, s=70, color=PALETTE[1], zorder=2, label="LoRA (pref only)", edgecolor="white", linewidth=1.5)
ax.scatter(mix, y, s=70, color=PALETTE[3], marker="D", zorder=2, label="Mix-LoRA", edgecolor="white", linewidth=1.5)
for yi, a_, b_ in zip(y, lora, mix):
    ax.text(max(a_, b_) + 3, yi, f"{b_ - a_:+.0f}", ha="left", va="center", fontsize=9, fontweight="bold",
            color=PALETTE[3] if b_ >= a_ else PALETTE[2])
ax.set_yticks(y, cats)
ax.set_xlim(35, 104)
ax.set_ylim(-0.6, len(cats) - 0.4)
ax.grid(axis="x")
ax.grid(axis="y", visible=False)
ax.set_xlabel("Preference satisfaction, SA %")
ax.set_title("(b) Fine-tuned π0.5: mixing data trades off")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, fontsize=8.5)

# (c) Sec. 3.1: the 37 single-preference instances by type
ax = fig.add_subplot(gs[2])
counts, labels = [8, 14, 15], ["Motion", "Skill", "User profile"]
wedges, _ = ax.pie(counts, colors=[PALETTE[0], PALETTE[1], PALETTE[2]], startangle=90, counterclock=False,
                   wedgeprops=dict(width=0.38, edgecolor="white", linewidth=2))
for wdg, c, lab, col in zip(wedges, counts, labels, [PALETTE[0], PALETTE[1], PALETTE[2]]):
    wdg.set_edgecolor("white")
    ang = np.deg2rad((wdg.theta1 + wdg.theta2) / 2)
    ax.text(0.80 * np.cos(ang), 0.80 * np.sin(ang), str(c), ha="center", va="center", fontsize=10.5, fontweight="bold", color="white")
ax.text(0, 0.05, "37", ha="center", va="center", fontsize=20, fontweight="bold", color=INK)
ax.text(0, -0.2, "preferences", ha="center", va="center", fontsize=9, color=MUTED)
ax.legend(wedges, labels, loc="upper center", bbox_to_anchor=(0.5, 0.02), ncol=3, fontsize=8.5, handlelength=1)
ax.set_title("(c) Preference taxonomy")

out = Path(__file__).with_name("results.png")
save(fig, str(out))
print(f"Wrote {out}")
