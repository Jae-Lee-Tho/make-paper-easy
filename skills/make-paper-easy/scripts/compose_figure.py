"""Compose a soft, illustrated paper figure: exact SVG text + optional AI art pieces.

Reads a figure spec (JSON), lays out pastel cards with titles, subtitles and
metric chips (real text, always exact), drops each panel's art image into its
slot, draws arrows, and renders SVG + PNG.

Usage:
    python compose_figure.py spec.json              # -> figure.svg, figure.png next to spec
    python compose_figure.py spec.json --no-art     # soft-SVG mode, no images needed
    python compose_figure.py spec.json --out fig    # -> fig.svg, fig.png

Spec format (all keys except panels optional):
{
  "title": "LIBERO-PeRM data pipeline",
  "caption": "Preferences change how a task is done, not what is done.",
  "layout": "row",                 # "row" or "grid"
  "cols": 2,                       # grid only
  "arrows": true,                  # arrows between consecutive panels
  "art_dir": "art",
  "panels": [
    {"id": "p1", "title": "Input scene", "subtitle": "LIBERO layout + task",
     "art": "<FLUX prompt, used by flux_art.py>",
     "chips": ["312 tasks"], "color": "lavender"}
  ]
}
Colors: lavender, mint, peach, sky, rose, butter, sage, gray.

Requires: pip install resvg-py   (PNG rendering; SVG is written regardless)
"""
import argparse
import base64
import html
import json
import sys
from pathlib import Path

PALETTE = {  # (card fill, card stroke, title ink, chip fill)
    "lavender": ("#F1EEFC", "#CFC8F3", "#3C3489", "#E2DCFA"),
    "mint":     ("#E8F6F0", "#B9E3D2", "#0F5E48", "#D3EFE3"),
    "peach":    ("#FCEFE8", "#F2C9B5", "#7A3518", "#F8DDCF"),
    "sky":      ("#EAF3FC", "#BFD8F2", "#174A7C", "#D7E8F9"),
    "rose":     ("#FCEEF3", "#F0C3D3", "#7A2546", "#F8DCE6"),
    "butter":   ("#FCF5E3", "#EED9A4", "#6B4A08", "#F7EAC6"),
    "sage":     ("#EFF4E6", "#CADDB0", "#35540F", "#E0ECCE"),
    "gray":     ("#F3F2EE", "#D6D4CC", "#3E3D39", "#E6E4DD"),
}
ORDER = ["lavender", "mint", "peach", "sky", "rose", "butter", "sage"]
FONT = "Helvetica, Arial, 'DejaVu Sans', sans-serif"
INK, MUTED, ARROW = "#2C2C2A", "#6B6A64", "#9A988F"

CARD_W, GAP, PAD = 220, 56, 40
ART_H = 150
TITLE_CHARS, SUB_CHARS = 20, 27  # wrap widths that fit CARD_W at 15px bold / 12px


def text_block_h(panel):
    """Height of the text area under the art: title + subtitle + chips + padding."""
    t = len(wrap(panel.get("title", ""), TITLE_CHARS)[:2])
    s = len(wrap(panel.get("subtitle", ""), SUB_CHARS)[:2])
    # first title baseline 14, +18 per extra title line, 4 gap, 16 per subtitle line,
    # then chip row (14 gap + 22 chip + 12 pad) or a small bottom pad
    return 14 + (t - 1) * 18 + 4 + s * 16 + (48 if panel.get("chips") else 14)


def esc(s):
    return html.escape(str(s), quote=True)


def wrap(text, max_chars):
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) <= max_chars:
            cur = f"{cur} {w}".strip()
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def image_href(path: Path):
    if not path.exists():
        return None
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def card(x, y, panel, color, art_href, with_art, text_h):
    fill, stroke, ink, chip = PALETTE[color]
    h = (ART_H + 16 if with_art else 16) + text_h
    cid = f"clip-{esc(panel['id'])}"
    out = [f'<g id="{esc(panel["id"])}">',
           f'<rect x="{x}" y="{y}" width="{CARD_W}" height="{h}" rx="18" fill="{fill}" stroke="{stroke}" stroke-width="1"/>']
    ty = y + 16
    if with_art:
        ax, ay, aw = x + 12, y + 12, CARD_W - 24
        out.append(f'<clipPath id="{cid}"><rect x="{ax}" y="{ay}" width="{aw}" height="{ART_H}" rx="12"/></clipPath>')
        out.append(f'<rect x="{ax}" y="{ay}" width="{aw}" height="{ART_H}" rx="12" fill="#FFFFFF"/>')
        if art_href:
            out.append(f'<image href="{art_href}" x="{ax}" y="{ay}" width="{aw}" height="{ART_H}" '
                       f'preserveAspectRatio="xMidYMid slice" clip-path="url(#{cid})"/>')
        else:  # soft placeholder blobs so the layout still reads as illustrated
            cx, cy = ax + aw / 2, ay + ART_H / 2
            out.append(f'<circle cx="{cx - 30}" cy="{cy + 6}" r="34" fill="{chip}"/>')
            out.append(f'<circle cx="{cx + 26}" cy="{cy - 10}" r="24" fill="{stroke}" opacity="0.6"/>')
            out.append(f'<circle cx="{cx + 40}" cy="{cy + 30}" r="12" fill="{chip}"/>')
        out.append(f'<rect x="{ax}" y="{ay}" width="{aw}" height="{ART_H}" rx="12" fill="none" stroke="{stroke}" stroke-width="1"/>')
        ty = ay + ART_H + 4
    tlines = wrap(panel.get("title", ""), TITLE_CHARS)[:2]
    for i, line in enumerate(tlines):
        out.append(f'<text x="{x + CARD_W / 2}" y="{ty + 14 + i * 18}" text-anchor="middle" '
                   f'font-family="{FONT}" font-size="15" font-weight="bold" fill="{ink}">{esc(line)}</text>')
    sy = ty + 14 + len(tlines) * 18 + 4
    for i, line in enumerate(wrap(panel.get("subtitle", ""), SUB_CHARS)[:2]):
        out.append(f'<text x="{x + CARD_W / 2}" y="{sy + i * 16}" text-anchor="middle" '
                   f'font-family="{FONT}" font-size="12" fill="{MUTED}">{esc(line)}</text>')
    chips = panel.get("chips", [])[:2]
    if chips:
        cy = y + h - 30
        widths = [len(c) * 7 + 20 for c in chips]
        cx = x + (CARD_W - (sum(widths) + 8 * (len(chips) - 1))) / 2
        for c, w in zip(chips, widths):
            out.append(f'<rect x="{cx}" y="{cy}" width="{w}" height="22" rx="11" fill="{chip}" stroke="{stroke}" stroke-width="0.8"/>')
            out.append(f'<text x="{cx + w / 2}" y="{cy + 15}" text-anchor="middle" font-family="{FONT}" '
                       f'font-size="11.5" font-weight="bold" fill="{ink}">{esc(c)}</text>')
            cx += w + 8
    out.append("</g>")
    return "\n".join(out), h


def arrow(x1, y1, x2, y2):
    return (f'<path d="M{x1} {y1} L{x2} {y2}" stroke="{ARROW}" stroke-width="2" fill="none" '
            f'stroke-linecap="round" marker-end="url(#ah)"/>')


def build_svg(spec, base_dir, with_art):
    panels = spec["panels"]
    n = len(panels)
    cols = n if spec.get("layout", "row") == "row" else max(1, int(spec.get("cols", 2)))
    rows = (n + cols - 1) // cols
    text_h = max(text_block_h(p) for p in panels)  # uniform card height, sized to the longest text
    card_h = (ART_H + 16 if with_art else 16) + text_h
    width = PAD * 2 + cols * CARD_W + (cols - 1) * GAP
    top = PAD + (44 if spec.get("title") else 0)
    cap_lines = wrap(spec.get("caption", ""), int((width - 2 * PAD) / 7.2)) if spec.get("caption") else []
    height = top + rows * card_h + (rows - 1) * GAP + PAD + len(cap_lines) * 18 + (8 if cap_lines else 0)
    art_dir = base_dir / spec.get("art_dir", "art")

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<defs><marker id="ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
             f'<path d="M1 1 L9 5 L1 9" fill="none" stroke="{ARROW}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></marker></defs>',
             f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>']
    if spec.get("title"):
        parts.append(f'<text x="{PAD}" y="{PAD + 18}" font-family="{FONT}" font-size="20" font-weight="bold" fill="{INK}">{esc(spec["title"])}</text>')

    pos = []
    for i, panel in enumerate(panels):
        r, c = divmod(i, cols)
        x, y = PAD + c * (CARD_W + GAP), top + r * (card_h + GAP)
        color = panel.get("color") or ORDER[i % len(ORDER)]
        if color not in PALETTE:
            color = "gray"
        href = None
        if with_art and panel.get("art"):
            href = next((h for h in (image_href(art_dir / f"{panel['id']}{ext}") for ext in (".jpg", ".png")) if h), None)
        svg, _ = card(x, y, panel, color, href, with_art, text_h)
        parts.append(svg)
        pos.append((x, y, r))

    if spec.get("arrows", True):
        for i in range(n - 1):
            (x1, y1, r1), (x2, y2, r2) = pos[i], pos[i + 1]
            if r1 == r2:
                my = y1 + card_h / 2
                parts.append(arrow(x1 + CARD_W + 8, my, x2 - 10, my))
            else:  # wrap to next row: drop down from the last card's bottom into the next row's first card
                parts.append(f'<path d="M{x1 + CARD_W / 2} {y1 + card_h + 6} L{x1 + CARD_W / 2} {y1 + card_h + GAP / 2} '
                             f'L{x2 + CARD_W / 2} {y1 + card_h + GAP / 2} L{x2 + CARD_W / 2} {y2 - 10}" stroke="{ARROW}" '
                             f'stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round" marker-end="url(#ah)"/>')

    cy = top + rows * card_h + (rows - 1) * GAP + 30
    for i, line in enumerate(cap_lines):
        parts.append(f'<text x="{PAD}" y="{cy + i * 18}" font-family="{FONT}" font-size="13" font-style="italic" fill="{MUTED}">{esc(line)}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("spec")
    p.add_argument("--out", help="output path without extension (default: figure next to spec)")
    p.add_argument("--no-art", action="store_true", help="soft-SVG mode: no art slots")
    p.add_argument("--scale", type=float, default=2.0, help="PNG zoom (default 2x for crisp text)")
    a = p.parse_args()

    spec_path = Path(a.spec)
    spec = json.loads(spec_path.read_text())
    if not spec.get("panels"):
        print("spec has no panels", file=sys.stderr)
        return 2
    out = Path(a.out) if a.out else spec_path.parent / "figure"
    svg = build_svg(spec, spec_path.parent, with_art=not a.no_art)
    out.with_suffix(".svg").write_text(svg, encoding="utf-8")
    print(f"Wrote {out.with_suffix('.svg')}")
    try:
        import resvg_py
    except ImportError:
        print("resvg-py not installed (pip install resvg-py); SVG only.", file=sys.stderr)
        return 0
    png = resvg_py.svg_to_bytes(svg_string=svg, zoom=a.scale)
    out.with_suffix(".png").write_bytes(bytes(png))
    print(f"Wrote {out.with_suffix('.png')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
