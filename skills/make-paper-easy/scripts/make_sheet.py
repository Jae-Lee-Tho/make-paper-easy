"""Build ONE study-sheet PNG: summary text + method diagram + results charts, top to bottom.

Usage:
    python make_sheet.py summary.json                # -> <name>-easy.png next to summary.json
    python make_sheet.py summary.json --out sheet    # -> sheet.png
    python make_sheet.py summary.json --pdf          # also a multi-page PDF with selectable text (Letter)
    python make_sheet.py summary.json --pdf --page a4

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
- **bold** works in text and bullets, and so do x^{2} / d_{k} super/subscripts. CJK text works.
- Figure paths are relative to summary.json.

Requires: pip install resvg-py pillow   (PDF: reportlab, matplotlib)
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
        w = sum(char_w(c, size, b) for c in SCRIPT.sub(r"\2", piece))
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


# Modifier letters that most UI fonts lack; one missing glyph can switch a whole run to a fallback
# font (often bold italic), so turn them into ^{..}/_{..} markup that renders with normal letters.
SUPER = dict(zip("⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁱⁿᵀᵃᵇᶜᵈᵉᶠᵍʰʲᵏˡᵐᵒᵖʳˢᵗᵘᵛʷˣʸᶻ",
                 "0123456789+-=()inTabcdefghjklmoprstuvwxyz"))
SUB = dict(zip("₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₒₓₕₖₗₘₙₚₛₜᵢⱼ", "0123456789+-=()aeoxhklmnpstij"))
SCRIPT = re.compile(r"([_^])\{([^}]*)\}")


def normalize(text):
    """Turn runs of Unicode super/subscript characters (10¹⁸, QKᵀ, x₁) into ^{..}/_{..} markup."""
    out, i = [], 0
    while i < len(text):
        for table, mark in ((SUPER, "^"), (SUB, "_")):
            if text[i] in table:
                j = i
                while j < len(text) and text[j] in table:
                    j += 1
                out.append(mark + "{" + "".join(table[c] for c in text[i:j]) + "}")
                i = j
                break
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def piece_svg(piece, weight, size):
    """Escape a text piece, turning ^{..} and _{..} into super/subscript tspans."""
    out, pos = [], 0
    small = round(size * 0.7, 1)
    for m in SCRIPT.finditer(piece):
        out.append(f'<tspan font-weight="{weight}">{esc(piece[pos:m.start()])}</tspan>')
        shift = "super" if m.group(1) == "^" else "sub"
        out.append(f'<tspan font-weight="{weight}" baseline-shift="{shift}" font-size="{small}">{esc(m.group(2))}</tspan>')
        pos = m.end()
    out.append(f'<tspan font-weight="{weight}">{esc(piece[pos:])}</tspan>')
    return "".join(out)


def line_svg(x, y, line, size, fill, base_bold=False):
    spans = "".join(piece_svg(p, "bold" if (b or base_bold) else "normal", size) for p, b in line)
    return f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}" fill="{fill}" xml:space="preserve">{spans}</text>'


def paragraph(x, y, text, size, width, fill, leading=1.5, bold=False):
    """Returns (svg, height)."""
    out, lh = [], size * leading
    lines = wrap_runs(normalize(str(text)), size, width)
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


# ---------------------------------------------------------------------------
# Paginated PDF (Letter/A4) with real, selectable text. Uses reportlab and the
# DejaVu Sans font that ships with matplotlib, so it renders the same everywhere.
# ---------------------------------------------------------------------------
CJK_RE = re.compile(r"[\u1100-\u11ff\u3000-\u9fff\uac00-\ud7af]")


def _rl_markup(text):
    """Escape for reportlab Paragraph and convert **bold**, ^{sup}, _{sub}."""
    t = normalize(str(text)).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"\^\{([^}]*)\}", r"<super>\1</super>", t)
    t = re.sub(r"_\{([^}]*)\}", r"<sub>\1</sub>", t)
    return t


def _register_fonts():
    import matplotlib
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.fonts import addMapping
    d = Path(matplotlib.__file__).parent / "mpl-data" / "fonts" / "ttf"
    pdfmetrics.registerFont(TTFont("MPE", str(d / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("MPE-Bold", str(d / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("MPE-Italic", str(d / "DejaVuSans-Oblique.ttf")))
    pdfmetrics.registerFont(TTFont("MPE-BoldItalic", str(d / "DejaVuSans-BoldOblique.ttf")))
    addMapping("MPE", 0, 0, "MPE")
    addMapping("MPE", 1, 0, "MPE-Bold")
    addMapping("MPE", 0, 1, "MPE-Italic")
    addMapping("MPE", 1, 1, "MPE-BoldItalic")


def build_pdf(spec, base, out_path, page="letter"):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (Image as RLImage, KeepTogether, Paragraph, SimpleDocTemplate,
                                    Spacer, Table, TableStyle)
    from PIL import Image

    _register_fonts()
    size = A4 if page == "a4" else letter
    margin = 0.6 * inch
    frame_w, frame_h = size[0] - 2 * margin, size[1] - 2 * margin - 0.3 * inch
    C = colors.HexColor
    st = {
        "title": ParagraphStyle("t", fontName="MPE", fontSize=19, leading=23, textColor=C(INK)),
        "meta": ParagraphStyle("m", fontName="MPE", fontSize=8.5, leading=11, textColor=C(MUTED)),
        "tldr_l": ParagraphStyle("tl", fontName="MPE-Bold", fontSize=7.5, leading=10, textColor=C("#F2C94C")),
        "tldr": ParagraphStyle("tt", fontName="MPE", fontSize=10, leading=14.5, textColor=colors.white),
        "body": ParagraphStyle("b", fontName="MPE", fontSize=9, leading=13, textColor=C(INK)),
        "cap": ParagraphStyle("c", fontName="MPE", fontSize=7.8, leading=10.5, textColor=C(MUTED)),
    }

    def block(blk, accent, width, extra=0.0):
        tint, ink, bar = accent
        head = ParagraphStyle("h", fontName="MPE-Bold", fontSize=11.5, leading=15, textColor=C(ink))
        bullet = ParagraphStyle("bl", parent=st["body"], leftIndent=11, bulletIndent=0, bulletColor=C(bar),
                                bulletFontName="MPE-Bold", spaceAfter=3)
        rows = []
        if blk.get("heading"):
            rows.append([Paragraph(_rl_markup(blk["heading"]), head)])
        if blk.get("text"):
            rows.append([Paragraph(_rl_markup(blk["text"]), st["body"])])
        for b in blk.get("bullets", []):
            rows.append([Paragraph(_rl_markup(b), bullet, bulletText="•")])
        t = Table(rows, colWidths=[width], splitByRow=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C(tint)),
            ("LINEBEFORE", (0, 0), (0, -1), 3, C(bar)),
            ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, 0), 9), ("BOTTOMPADDING", (0, -1), (-1, -1), 9 + extra),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        return t

    def figure(blk):
        p = (base / blk["path"]).resolve()
        if not p.exists():
            print(f"figure not found: {p}", file=sys.stderr)
            return None
        iw, ih = Image.open(p).size
        w = frame_w
        h = w * ih / iw
        if h > frame_h * 0.85:  # very tall figure: shrink to fit on one page
            h = frame_h * 0.85
            w = h * iw / ih
        parts = [RLImage(str(p), width=w, height=h)]
        if blk.get("caption"):
            parts += [Spacer(1, 4), Paragraph(_rl_markup(blk["caption"]), st["cap"])]
        return KeepTogether(parts)

    story = [Paragraph(_rl_markup(spec.get("title", "Paper summary")), ParagraphStyle(
        "tb", parent=st["title"], fontName="MPE-Bold"))]
    if spec.get("meta"):
        story += [Spacer(1, 3), Paragraph(_rl_markup(spec["meta"]), st["meta"])]
    story.append(Spacer(1, 10))
    if spec.get("tldr"):
        t = Table([[Paragraph("TL;DR", st["tldr_l"])], [Paragraph(_rl_markup(spec["tldr"]), st["tldr"])]],
                  colWidths=[frame_w])
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), C("#22221F")),
                               ("LEFTPADDING", (0, 0), (-1, -1), 14), ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                               ("TOPPADDING", (0, 0), (-1, 0), 11), ("BOTTOMPADDING", (0, -1), (-1, -1), 12)]))
        story += [t, Spacer(1, 10)]

    blocks, i, k = spec.get("blocks", []), 0, 0
    half_w = (frame_w - 10) / 2
    while i < len(blocks):
        blk = blocks[i]
        if blk.get("type") == "figure":
            f = figure(blk)
            if f:
                story += [f, Spacer(1, 10)]
            i += 1
            continue
        nxt = blocks[i + 1] if i + 1 < len(blocks) else None
        if blk.get("width") == "half" and nxt and nxt.get("type", "text") == "text" and nxt.get("width") == "half":
            a = block(blk, ACCENTS[k % len(ACCENTS)], half_w)
            b = block(nxt, ACCENTS[(k + 1) % len(ACCENTS)], half_w)
            ha, hb = a.wrap(half_w, frame_h)[1], b.wrap(half_w, frame_h)[1]
            if max(ha, hb) < frame_h * 0.9:
                # rebuild the shorter card with extra bottom padding so both cards end together
                a = block(blk, ACCENTS[k % len(ACCENTS)], half_w, max(0, hb - ha))
                b = block(nxt, ACCENTS[(k + 1) % len(ACCENTS)], half_w, max(0, ha - hb))
                pair = Table([[a, "", b]], colWidths=[half_w, 10, half_w])
                pair.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                          ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                          ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
                story += [pair, Spacer(1, 10)]
            else:  # too tall to sit side by side on one page: stack them
                story += [block(blk, ACCENTS[k % len(ACCENTS)], frame_w), Spacer(1, 10),
                          block(nxt, ACCENTS[(k + 1) % len(ACCENTS)], frame_w), Spacer(1, 10)]
            i, k = i + 2, k + 2
        else:
            story += [block(blk, ACCENTS[k % len(ACCENTS)], frame_w), Spacer(1, 10)]
            i, k = i + 1, k + 1

    footer = spec.get("footer", "make-paper-easy")

    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFont("MPE", 7.5)
        canvas.setFillColor(C(MUTED))
        canvas.drawString(margin, 0.42 * inch, normalize(footer)[:150])
        canvas.drawRightString(size[0] - margin, 0.42 * inch, f"{doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(str(out_path), pagesize=size, leftMargin=margin, rightMargin=margin,
                            topMargin=margin, bottomMargin=margin + 0.3 * inch,
                            title=normalize(spec.get("title", "Paper summary")), author="make-paper-easy")
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return doc.page


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("summary")
    p.add_argument("--out", help="output path without extension")
    p.add_argument("--scale", type=float, default=1.5, help="PNG zoom (default 1.5)")
    p.add_argument("--pdf", action="store_true", help="also write a paginated PDF with selectable text")
    p.add_argument("--page", choices=["letter", "a4"], default="letter", help="PDF page size (default letter)")
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
        pdf = out.with_suffix(".pdf")
        all_text = json.dumps(spec, ensure_ascii=False)
        try:
            if CJK_RE.search(all_text):
                raise RuntimeError("CJK text: the bundled PDF font has no CJK glyphs")
            pages = build_pdf(spec, sp.parent, pdf, a.page)
            print(f"Wrote {pdf} ({pages} {a.page} page{'s' if pages != 1 else ''}, selectable text)")
        except Exception as e:  # never lose the PDF: fall back to the sheet image as a single page
            from PIL import Image
            Image.open(png).convert("RGB").save(pdf, resolution=150)
            print(f"Wrote {pdf} (image-only, because: {e})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
