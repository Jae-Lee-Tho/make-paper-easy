"""Paper-style matplotlib theme for make-paper-easy charts.

Import it, call apply(), then plot as usual. It sets fonts, a soft palette that
matches compose_diagram.py, light gridlines, no top/right spines, and gives
helpers for value labels and hatching (so series differ by more than color).

    from plot_style import apply, PALETTE, HATCHES, bar_labels, save
    apply()
    ...
    save(fig, "results.png")   # also writes results.svg

Only plot numbers copied from the paper's tables or text.
"""
import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")

# Strong/soft pairs that match the diagram palette (lavender, sky, peach, mint, rose, butter, sage)
PALETTE = ["#7F74D9", "#4F8FD6", "#E07F55", "#3FAE85", "#D6648C", "#D6A22E", "#77A43C"]
SOFT = ["#E2DCFA", "#D7E8F9", "#F8DDCF", "#D3EFE3", "#F8DCE6", "#F7EAC6", "#E0ECCE"]
HATCHES = ["", "///", "...", "xx", "\\\\", "++", "oo"]
INK, MUTED, GRID = "#2C2C2A", "#6B6A64", "#E4E2DB"


def apply():
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 10.5,
        "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "axes.labelsize": 10.5, "axes.labelcolor": MUTED,
        "axes.edgecolor": "#BDBBB3", "axes.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.8,
        "axes.axisbelow": True,
        "axes.prop_cycle": matplotlib.cycler(color=PALETTE),
        "xtick.color": MUTED, "ytick.color": MUTED, "xtick.major.size": 0, "ytick.major.size": 0,
        "legend.frameon": False, "legend.fontsize": 9.5,
        "hatch.color": "#FFFFFF", "hatch.linewidth": 1.0,
        "figure.dpi": 110, "savefig.dpi": 220, "savefig.bbox": "tight", "savefig.facecolor": "white",
        "text.color": INK,
    })


def bar_labels(ax, bars, fmt="{:.1f}", inside=False, size=8.5):
    """Write each bar's value above it (or inside the top when inside=True)."""
    for b in bars:
        h = b.get_height()
        y = h - 2 if inside else h + 1
        ax.text(b.get_x() + b.get_width() / 2, y, fmt.format(h), ha="center",
                va="top" if inside else "bottom", fontsize=size, color=INK)


def save(fig, path):
    """Save PNG (and an SVG twin) next to each other."""
    fig.savefig(path, metadata={"Software": None})
    if path.lower().endswith(".png"):
        # no date and a fixed id salt, so re-running gives a byte-identical SVG (clean git diffs)
        with plt.rc_context({"svg.hashsalt": "make-paper-easy"}):
            fig.savefig(path[:-4] + ".svg", metadata={"Date": None})
    plt.close(fig)
