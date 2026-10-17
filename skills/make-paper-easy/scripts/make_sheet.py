"""Build ONE study-sheet PNG: summary text + method diagram + results charts, top to bottom.

Usage:
    python make_sheet.py summary.json                # -> <name>-easy.png next to summary.json
    python make_sheet.py summary.json --out sheet    # -> sheet.png
    python make_sheet.py summary.json --pdf          # also write a PDF (handy for printing/zooming)

summary.json:
{
  "title": "LIBERO-PeRM: Benchmarking Personalized Robotic Manipulation",
  "meta": "Li et al. · NeurIPS 2026 · arxiv.org/abs/2610.22372",
  "tldr": "One paragraph in plain words.",
  "blocks": [                                   # rendered in this order
    {"type": "text", "heading": "Background you need", "width": "half",
     "bullets": ["**VLA**: a model that sees, reads and outputs robot actions."]},
    {"type": "text", "heading": "The problem", "width": "half", "text": "..."},
    {"type": "figure", "path": "figure.png", "caption": "Figure 1. ..."},
    {"type": "text", "heading": "Key findings", "bullets": ["..."]},
    {"type": "figure", "path": "results.png", "caption": "..."}
  ],
  "footer": "Made with make-paper-easy · every number is from the paper"
}
- "width": "half" blocks pair up side by side; anything else is full width.
- **bold** works in text and bullets. Korean/Chinese/Japanese text works.
- Figure paths are relative to summary.json.

Requires: pip install resvg-py pillow
"""
import argparse
import base64
import html
import json
import re
import sys
import unicodedata
from pathlib import Path

W = 1600                     # sheet width in px (before --scale)
M = 56                       # outer margin
GAP = 24                     # gap between blocks / columns
FONT = "Helvetica, Arial, 'Apple SD Gothic Neo', 'Noto Sans CJK KR', 'Noto Sans KR', 'Malgun Gothic', sans-serif"
INK, MUTED, RULE = "#22221F", "#62615B", "#E3E1D9"
ACCENTS = [  # card tint, heading ink, left bar
    ("#F4F1FD", "#3C3489", "#8E83E0"), ("#ECF4FC", "#174A7C", "#4F8FD6"),
    ("#FDF2EB", "#7A3518", "#E07F55"), ("#EBF7F1", "#0F5E48", "#3FAE85"),
    ("#FDF0F4", "#7A2546", "#D6648C"), ("#FDF7E6", "#6B4A08", "#D6A22E"),
]


def esc(s):
    return html.escape(str(s), quote=False)


def char_w(ch, size, bold):
    """Rough advance width of one character (good enough for wrapping)."""
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return size * 0.93  # Hangul/CJK glyphs render a little narrower than 1em
    if ch == " ":
        return size * 0.28
    if ch in "il.,:;'|!()[]":
        return size * 0.30
    if ch in "mwMW@%":
        return size * 0.86
    if ch.isupper() or ch.isdigit():
        return size * (0.66 if bold else 0.62)
    return size * (0.55 if bold else 0.52)


def runs(text):
    """Split '**bold**' markup into (segment, is_bold) runs."""
    out = []
    for i, part in enumerate(re.split(r"\*\*(.+?)\*\*", str(text))):
        if part:
            out.append((part, i % 2 == 1))
    return out


def wrap_runs(text, size, max_w):
    """Greedy wrap that keeps bold runs; breaks on spaces, or anywhere inside CJK text."""
    tokens = []  # (piece, bold) where piece is a word+space or a single CJK char
    for seg, b in runs(text):
        for m in re.finditer(r"[ᄀ-ᇿ　-鿿가-힯＀-￯]|[^\sᄀ-ᇿ　-鿿가-힯＀-￯]+\s*|\s+", seg):
            tokens.append((m.group(0), b))
    lines, cur, cur_w = [], [], 0.0
    for piece, b in tokens:
        w = sum(char_w(c, size, b) for c in piece)
        if cur and cur_w + w - (char_w(" ", size, b) if piece.endswith(" ") else 0) > max_w:
            lines.append(cur)
            cur, cur_w = [], 0.0
            piece = piece.lstrip()
            w = sum(char_w(c, size, b) for c in piece)
        if piece:
            cur.append((piece, b))
            cur_w += w
    if cur:
        lines.append(cur)
    return lines


def line_svg(x, y, line, size, fill, base_bold=False):
    spans = "".join(f'<tspan font-weight="{"bold" if (b or base_bold) else "normal"}">{esc(p)}</tspan>' for p, b in line)
    return f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}" fill="{fill}" xml:space="preserve">{spans}</text>'


def paragraph(x, y, text, size, width, fill, leading=1.5, bold=False):
    """Returns (svg, height)."""
    out, lh = [], size * leading
    lines = wrap_runs(text, size, width)
    for i, ln in enumerate(lines):
        out.append(line_svg(x, y + size + i * lh, ln, size, fill, bold))
    return "\n".join(out), len(lines) * lh


def text_block(x, y, w, blk, accent, measure_only=False):
    tint, ink, bar = accent
    pad, body = 24, 19
    inner = w - 2 * pad - 6
    parts, cy = [], y + pad
    if blk.get("heading"):
        s, h = paragraph(x + pad + 6, cy - 4, blk["heading"], 23, inner, ink, 1.3, bold=True)
        parts.append(s)
        cy += h + 10
    if blk.get("text"):
        s, h = paragraph(x + pad + 6, cy, blk["text"], body, inner, INK, 1.55)
        parts.append(s)
        cy += h + 6
    for item in blk.get("bullets", []):
        parts.append(f'<circle cx="{x + pad + 14:.1f}" cy="{cy + body * 0.68:.1f}" r="4" fill="{bar}"/>')
        s, h = paragraph(x + pad + 30, cy, item, body, inner - 24, INK, 1.5)
        parts.append(s)
        cy += h + 8
    height = cy - y + pad - 6
    if measure_only:
        return "", height
    card = (f'<rect x="{x}" y="{y}" width="{w}" height="{height:.1f}" rx="18" fill="{tint}"/>'
            f'<rect x="{x}" y="{y + 18}" width="6" height="{max(0, height - 36):.1f}" rx="3" fill="{bar}"/>')
    return card + "\n".join(parts), height


def figure_block(x, y, w, blk, base):
    from PIL import Image
    p = (base / blk["path"]).resolve()
    if not p.exists():
        print(f"figure not found: {p}", file=sys.stderr)
        return "", 0
    iw, ih = Image.open(p).size
    dw = w - 2
    dh = dw * ih / iw
    href = "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{dh + 2:.1f}" rx="14" fill="#FFFFFF" stroke="{RULE}" stroke-width="1.5"/>',
           f'<image href="{href}" x="{x + 1}" y="{y + 1}" width="{dw:.1f}" height="{dh:.1f}" preserveAspectRatio="xMidYMid meet"/>']
    h = dh + 2
    if blk.get("caption"):
        s, ch = paragraph(x + 6, y + h + 8, blk["caption"], 16, w - 12, MUTED, 1.45)
        out.append(s)
        h += ch + 12
    return "\n".join(out), h


def build(spec, base):
    content_w = W - 2 * M
    half_w = (content_w - GAP) / 2
    parts, y = [], M

    s, h = paragraph(M, y, spec.get("title", "Paper summary"), 40, content_w, INK, 1.25, bold=True)
    parts.append(s)
    y += h + 6
    if spec.get("meta"):
        s, h = paragraph(M, y, spec["meta"], 18, content_w, MUTED, 1.4)
        parts.append(s)
        y += h
    y += 22
    if spec.get("tldr"):
        pad = 28
        _, th = paragraph(0, 0, spec["tldr"], 22, content_w - 2 * pad, INK, 1.55)
        box_h = th + 2 * pad + 30
        parts.append(f'<rect x="{M}" y="{y}" width="{content_w}" height="{box_h:.1f}" rx="20" fill="#22221F"/>')
        parts.append(f'<text x="{M + pad}" y="{y + pad + 12}" font-family="{FONT}" font-size="15" font-weight="bold" '
                     f'fill="#F2C94C" letter-spacing="2">TL;DR</text>')
        s, _ = paragraph(M + pad, y + pad + 24, spec["tldr"], 22, content_w - 2 * pad, "#FFFFFF", 1.55)
        parts.append(s)
        y += box_h + GAP

    blocks, i, k = spec.get("blocks", []), 0, 0
    while i < len(blocks):
        blk = blocks[i]
        if blk.get("type") == "figure":
            s, h = figure_block(M, y, content_w, blk, base)
            parts.append(s)
            y += h + GAP
            i += 1
            continue
        nxt = blocks[i + 1] if i + 1 < len(blocks) else None
        if blk.get("width") == "half" and nxt and nxt.get("type", "text") == "text" and nxt.get("width") == "half":
            a1, a2 = ACCENTS[k % len(ACCENTS)], ACCENTS[(k + 1) % len(ACCENTS)]
            _, h1 = text_block(M, y, half_w, blk, a1, True)
            _, h2 = text_block(M, y, half_w, nxt, a2, True)
            hh = max(h1, h2)
            for xx, b, a in ((M, blk, a1), (M + half_w + GAP, nxt, a2)):
                s, _ = text_block(xx, y, half_w, b, a)
                # stretch the shorter card so the row looks even
                s = re.sub(r'(<rect x="[\d.]+" y="[\d.]+" width="[\d.]+" height=")[\d.]+(" rx="18")', rf'\g<1>{hh:.1f}\2', s, count=1)
                s = re.sub(r'(<rect x="[\d.]+" y="[\d.]+" width="6" height=")[\d.]+(")', rf'\g<1>{max(0, hh - 36):.1f}\2', s, count=1)
                parts.append(s)
            y += hh + GAP
            i, k = i + 2, k + 2
        else:
            s, h = text_block(M, y, content_w, blk, ACCENTS[k % len(ACCENTS)])
            parts.append(s)
            y += h + GAP
            i, k = i + 1, k + 1

    if spec.get("footer"):
        parts.append(f'<line x1="{M}" y1="{y + 4}" x2="{W - M}" y2="{y + 4}" stroke="{RULE}" stroke-width="1.5"/>')
        s, h = paragraph(M, y + 14, spec["footer"], 15, content_w, MUTED, 1.4)
        parts.append(s)
        y += h + 20
    height = y + M - GAP
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height:.0f}" viewBox="0 0 {W} {height:.0f}">'
            f'<rect width="{W}" height="{height:.0f}" fill="#FFFFFF"/>' + "\n".join(parts) + "</svg>")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("summary")
    p.add_argument("--out", help="output path without extension")
    p.add_argument("--scale", type=float, default=1.5, help="PNG zoom (default 1.5)")
    p.add_argument("--pdf", action="store_true", help="also write a PDF")
    a = p.parse_args()
    sp = Path(a.summary)
    spec = json.loads(sp.read_text(encoding="utf-8"))
    slug = re.sub(r"[^a-z0-9]+", "-", spec.get("title", "paper").split(":")[0].lower()).strip("-") or "paper"
    out = Path(a.out) if a.out else sp.parent / f"{slug}-easy"
    svg = build(spec, sp.parent)
    try:
        import resvg_py
    except ImportError:
        print("pip install resvg-py", file=sys.stderr)
        return 1
    png = out.with_suffix(".png")
    png.write_bytes(bytes(resvg_py.svg_to_bytes(svg_string=svg, zoom=a.scale)))
    print(f"Wrote {png}")
    if a.pdf:
        from PIL import Image
        Image.open(png).convert("RGB").save(out.with_suffix(".pdf"), resolution=150)
        print(f"Wrote {out.with_suffix('.pdf')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
