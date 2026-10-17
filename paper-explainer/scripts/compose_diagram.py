"""Dense, PaperBanana-style methodology diagrams: modules, small nodes, icons, math, routed arrows.

All text is real SVG text (always exact). Each node can show a built-in vector
icon or a small AI art thumbnail (from flux_art.py). Renders SVG + PNG.

Usage:
    python compose_diagram.py spec.json [--out figure] [--no-art] [--scale 2]

Spec:
{
  "title": "...", "caption": "...",
  "node_w": 150, "node_h": 118,               # optional sizing
  "groups": [                                  # drawn left to right
    {"id": "g1", "title": "Reasoning module", "color": "peach",
     "cols": 2, "rows": 3,                    # internal grid
     "style": "zone" | "dashed" | "plain",     # plain = no box (for inputs/outputs)
     "nodes": [
       {"id": "n1", "row": 0, "col": 0,
        "title": "Planner", "sub": "VLM, task + pref",
        "math": "π_{θ}(a_t | I_t, ℓ)",          # optional serif italic line
        "icon": "vlm",                         # built-in icon, or
        "art": "<FLUX prompt>"}                # small thumbnail (overrides icon when present)
     ]}
  ],
  "edges": [
    {"from": "n1", "to": "n2", "label": "plan", "style": "solid" | "dashed",
     "color": "gray" | "accent", "route": "auto" | "over" | "under"}
  ],
  "legend": [{"label": "data flow", "style": "solid"}, {"label": "feedback", "style": "dashed", "color": "accent"}]
}
Math: "L_{KL}", "x^{2}", "π_{θ}" become sub/superscripts. Unicode math letters (ℒ 𝒢 𝐇) work.
Icons: doc, scene, robot, vlm, plan, gear, chart, check, db, user, matrix, image, loop, chat, path, metric, layers.
Colors: lavender, mint, peach, sky, rose, butter, sage, gray.

Requires: pip install resvg-py
"""
import argparse
import base64
import html
import json
import re
import sys
from pathlib import Path

PALETTE = {  # zone fill, zone stroke, ink, soft (icon fill / chip), mid (icon accent)
    "lavender": ("#F3F0FD", "#C9C1F1", "#3C3489", "#E2DCFA", "#8E83E0"),
    "mint":     ("#EBF7F1", "#B3E0CD", "#0F5E48", "#D3EFE3", "#3FAE85"),
    "peach":    ("#FDF1EA", "#F0C4AE", "#7A3518", "#F8DDCF", "#E07F55"),
    "sky":      ("#ECF4FC", "#BAD5F1", "#174A7C", "#D7E8F9", "#4F8FD6"),
    "rose":     ("#FDF0F4", "#EDBFD0", "#7A2546", "#F8DCE6", "#D6648C"),
    "butter":   ("#FDF7E6", "#ECD69B", "#6B4A08", "#F7EAC6", "#D6A22E"),
    "sage":     ("#F1F6E9", "#C6DBA9", "#35540F", "#E0ECCE", "#77A43C"),
    "gray":     ("#F5F4F0", "#D4D2CA", "#3E3D39", "#E6E4DD", "#9A988F"),
}
ORDER = ["lavender", "sky", "peach", "mint", "rose", "butter", "sage"]
SANS = "Helvetica, Arial, 'DejaVu Sans', sans-serif"
SERIF = "'Times New Roman', 'DejaVu Serif', serif"
INK, MUTED = "#2C2C2A", "#6B6A64"
EDGE = {"gray": "#8E8C84", "accent": "#D9643A"}

GPAD, NGAP, HEADER, GGAP, PAD = 14, 14, 34, 58, 36


# ---------- text helpers ----------
def esc(s):
    return html.escape(str(s), quote=False)


def rich(text, size):
    """Escape text and turn _{..}/^{..} (or _x/^x) into sub/superscript tspans."""
    out, small = [], round(size * 0.68, 1)
    for tok in re.split(r"([_^](?:\{[^}]*\}|.))", str(text)):
        if len(tok) >= 2 and tok[0] in "_^":
            body = tok[2:-1] if tok[1] == "{" else tok[1:]
            shift = "sub" if tok[0] == "_" else "super"
            out.append(f'<tspan baseline-shift="{shift}" font-size="{small}">{esc(body)}</tspan>')
        else:
            out.append(esc(tok))
    return "".join(out)


def plain_len(text):
    return len(re.sub(r"[_^]\{([^}]*)\}", r"\1", str(text)))


def wrap(text, max_chars):
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        if plain_len(cur) + plain_len(w) + (1 if cur else 0) <= max_chars:
            cur = f"{cur} {w}".strip()
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def text_el(x, y, s, size, fill, weight="normal", anchor="middle", family=SANS, italic=False):
    st = ' font-style="italic"' if italic else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-family="{family}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}"{st}>{rich(s, size)}</text>')


# ---------- icons: drawn in a 36x36 box at (x, y) ----------
def icon(name, x, y, c):
    _, stroke, ink, soft, mid = c
    s = f'stroke="{ink}" stroke-width="1.4" stroke-linejoin="round" stroke-linecap="round"'
    g = [f'<g transform="translate({x:.1f},{y:.1f})">']
    if name == "doc":
        g += [f'<path d="M8 3 H23 L29 9 V33 H8 Z" fill="#FFFFFF" {s}/>', f'<path d="M23 3 V9 H29" fill="{soft}" {s}/>']
        g += [f'<line x1="12" y1="{yy}" x2="25" y2="{yy}" {s}/>' for yy in (15, 20, 25)]
    elif name == "scene":
        g += [f'<ellipse cx="18" cy="24" rx="15" ry="7" fill="{soft}" {s}/>',
              f'<rect x="9" y="12" width="8" height="10" rx="2" fill="#FFFFFF" {s}/>',
              f'<path d="M17 15 q4 0 4 3 q0 3 -4 3" fill="none" {s}/>',
              f'<rect x="21" y="16" width="8" height="6" rx="1.5" fill="{mid}" {s}/>']
    elif name == "robot":
        g += [f'<rect x="4" y="28" width="12" height="5" rx="1.5" fill="{soft}" {s}/>',
              f'<path d="M10 28 L12 16 L24 10" fill="none" stroke="{ink}" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/>',
              f'<circle cx="12" cy="16" r="2.6" fill="{mid}" {s}/>',
              f'<path d="M24 10 L30 6 M24 10 L31 13" fill="none" {s}/>']
    elif name == "vlm":
        g += [f'<rect x="4" y="6" width="28" height="24" rx="7" fill="{soft}" {s}/>',
              f'<path d="M9 18 Q18 9 27 18 Q18 27 9 18 Z" fill="#FFFFFF" {s}/>',
              f'<circle cx="18" cy="18" r="3.4" fill="{mid}" {s}/>']
    elif name == "plan":
        for i, yy in enumerate((9, 18, 27)):
            g += [f'<rect x="5" y="{yy - 3}" width="6" height="6" rx="1.5" fill="{mid if i < 2 else "#FFFFFF"}" {s}/>',
                  f'<line x1="15" y1="{yy}" x2="31" y2="{yy}" {s}/>']
    elif name == "gear":
        teeth = "".join(f'<rect x="16" y="2" width="4" height="7" rx="1" fill="{mid}" transform="rotate({a} 18 18)"/>'
                        for a in range(0, 360, 45))
        g += [teeth, f'<circle cx="18" cy="18" r="10" fill="{soft}" {s}/>', f'<circle cx="18" cy="18" r="4" fill="#FFFFFF" {s}/>']
    elif name == "chart":
        g += [f'<line x1="5" y1="31" x2="31" y2="31" {s}/>']
        for bx, h in ((8, 10), (15, 18), (22, 13)):
            g.append(f'<rect x="{bx}" y="{31 - h}" width="6" height="{h}" rx="1" fill="{mid if h == 18 else soft}" {s}/>')
        g.append(f'<path d="M7 14 L17 8 L27 12" fill="none" stroke="{EDGE["accent"]}" stroke-width="1.6" stroke-linecap="round"/>')
    elif name == "check":
        g += [f'<circle cx="18" cy="18" r="13" fill="{soft}" {s}/>',
              f'<path d="M11 18 L16 23 L25 13" fill="none" stroke="{ink}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>']
    elif name == "db":
        g += [f'<path d="M7 9 V27 Q18 33 29 27 V9" fill="{soft}" {s}/>', f'<ellipse cx="18" cy="9" rx="11" ry="4.5" fill="#FFFFFF" {s}/>',
              f'<path d="M7 18 Q18 24 29 18" fill="none" {s}/>']
    elif name == "user":
        g += [f'<circle cx="18" cy="12" r="6" fill="{soft}" {s}/>', f'<path d="M6 32 Q6 21 18 21 Q30 21 30 32 Z" fill="{mid}" {s}/>']
    elif name == "matrix":
        fills = ["#FFFFFF", soft, mid, soft, mid, "#FFFFFF", mid, "#FFFFFF", soft]
        for i, f in enumerate(fills):
            g.append(f'<rect x="{5 + (i % 3) * 9}" y="{5 + (i // 3) * 9}" width="8" height="8" rx="1.5" fill="{f}" {s}/>')
    elif name == "image":
        g += [f'<rect x="4" y="7" width="28" height="22" rx="3" fill="#FFFFFF" {s}/>',
              f'<path d="M6 27 L14 18 L20 23 L24 19 L30 27 Z" fill="{soft}" {s}/>', f'<circle cx="25" cy="13" r="2.6" fill="{mid}"/>']
    elif name == "loop":
        g += [f'<path d="M28 18 A10 10 0 1 1 22 9" fill="none" stroke="{ink}" stroke-width="2" stroke-linecap="round"/>',
              f'<path d="M20 4 L24 9 L18 12" fill="none" stroke="{ink}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>']
    elif name == "chat":
        g += [f'<path d="M5 8 Q5 5 8 5 H28 Q31 5 31 8 V22 Q31 25 28 25 H14 L8 31 V25 Q5 25 5 22 Z" fill="{soft}" {s}/>']
        g += [f'<line x1="10" y1="{yy}" x2="{26 if yy == 12 else 21}" y2="{yy}" {s}/>' for yy in (12, 18)]
    elif name == "path":
        g += [f'<path d="M5 29 C10 8 24 30 31 7" fill="none" stroke="{mid}" stroke-width="2" stroke-dasharray="2.5 3" stroke-linecap="round"/>',
              f'<circle cx="5" cy="29" r="3" fill="#FFFFFF" {s}/>', f'<circle cx="31" cy="7" r="3" fill="{mid}" {s}/>']
    elif name == "metric":
        g += [f'<path d="M5 27 A13 13 0 0 1 31 27" fill="none" stroke="{soft}" stroke-width="5" stroke-linecap="round"/>',
              f'<path d="M5 27 A13 13 0 0 1 26 17" fill="none" stroke="{mid}" stroke-width="5" stroke-linecap="round"/>',
              f'<line x1="18" y1="27" x2="25" y2="18" {s}/>', f'<circle cx="18" cy="27" r="2.4" fill="{ink}"/>']
    elif name == "layers":
        for i, yy in enumerate((22, 16, 10)):
            g.append(f'<path d="M4 {yy} L18 {yy - 6} L32 {yy} L18 {yy + 6} Z" fill="{[soft, mid, "#FFFFFF"][i]}" {s}/>')
    else:
        g.append(f'<circle cx="18" cy="18" r="10" fill="{soft}" {s}/>')
    g.append("</g>")
    return "".join(g)


def image_href(path: Path):
    if not path.exists():
        return None
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


# ---------- layout ----------
def layout(spec):
    nw, nh = spec.get("node_w", 150), spec.get("node_h", 118)
    groups = spec["groups"]
    top = PAD + (40 if spec.get("title") else 0)
    max_rows = max(g.get("rows", 1) for g in groups)
    inner_h = max_rows * nh + (max_rows - 1) * NGAP
    gh = HEADER + GPAD * 2 + inner_h
    x = PAD
    for gi, g in enumerate(groups):
        cols, rows = g.get("cols", 1), g.get("rows", 1)
        g["_color"] = g.get("color") if g.get("color") in PALETTE else ORDER[gi % len(ORDER)]
        g["_w"] = cols * nw + (cols - 1) * NGAP + GPAD * 2
        g["_x"], g["_y"], g["_h"] = x, top, gh
        grid_h = rows * nh + (rows - 1) * NGAP
        y0 = top + HEADER + GPAD + (inner_h - grid_h) / 2  # center short columns vertically
        for n in g["nodes"]:
            n["_x"] = x + GPAD + n.get("col", 0) * (nw + NGAP)
            n["_y"] = y0 + n.get("row", 0) * (nh + NGAP)
            n["_w"], n["_h"], n["_g"] = nw, nh, g
        x += g["_w"] + GGAP
    width = x - GGAP + PAD
    return top, gh, width


def draw_group(g):
    fill, stroke, ink, soft, _ = PALETTE[g["_color"]]
    x, y, w, h = g["_x"], g["_y"], g["_w"], g["_h"]
    style = g.get("style", "zone")
    out = []
    if style == "zone":
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>')
        out.append(f'<path d="M{x} {y + 16} Q{x} {y} {x + 16} {y} H{x + w - 16} Q{x + w} {y} {x + w} {y + 16} V{y + HEADER} H{x} Z" fill="{soft}"/>')
    elif style == "dashed":
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="{fill}" stroke="{stroke}" stroke-width="1.4" stroke-dasharray="6 5"/>')
    return "\n".join(out)


def draw_group_title(g):
    if not g.get("title"):
        return ""
    fill, stroke, ink, soft, _ = PALETTE[g["_color"]]
    style = g.get("style", "zone")
    bg = soft if style == "zone" else (fill if style == "dashed" else "#FFFFFF")
    color = ink if style != "plain" else INK
    cx, avail = g["_x"] + g["_w"] / 2, g["_w"] - 16
    per_char = 0.58  # bold sans width per char, as a fraction of font size
    size, lines = 13.5, [g["title"]]
    if plain_len(g["title"]) * per_char * size > avail:  # too wide: shrink, then wrap to 2 lines
        size = max(11.5, avail / (plain_len(g["title"]) * per_char))
        if plain_len(g["title"]) * per_char * size > avail:
            size, lines = 11.5, wrap(g["title"], int(avail / (per_char * 11.5)))[:2]
    tw = min(avail + 8, max(plain_len(l) for l in lines) * per_char * size + 14)
    if len(lines) == 1:
        return (f'<rect x="{cx - tw / 2:.1f}" y="{g["_y"] + 6}" width="{tw:.1f}" height="22" rx="6" fill="{bg}"/>'
                + text_el(cx, g["_y"] + 17 + size * 0.36, lines[0], round(size, 1), color, "bold"))
    return (f'<rect x="{cx - tw / 2:.1f}" y="{g["_y"] + 3}" width="{tw:.1f}" height="30" rx="6" fill="{bg}"/>'
            + text_el(cx, g["_y"] + 15, lines[0], size, color, "bold")
            + text_el(cx, g["_y"] + 29, lines[1], size, color, "bold"))


def draw_node(n, art_dir, with_art):
    c = PALETTE[n["_g"]["_color"]]
    _, stroke, ink, soft, _ = c
    x, y, w, h = n["_x"], n["_y"], n["_w"], n["_h"]
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="#FFFFFF" stroke="{stroke}" stroke-width="1.1"/>']
    vis_h = 50
    href = None
    if with_art and n.get("art"):
        href = next((h_ for h_ in (image_href(art_dir / f"{n['id']}{e}") for e in (".jpg", ".png")) if h_), None)
    if href:
        cid = f"c-{n['id']}"
        ax, ay, aw = x + 8, y + 8, w - 16
        out.append(f'<clipPath id="{cid}"><rect x="{ax}" y="{ay}" width="{aw}" height="{vis_h}" rx="7"/></clipPath>')
        out.append(f'<image href="{href}" x="{ax}" y="{ay}" width="{aw}" height="{vis_h}" preserveAspectRatio="xMidYMid slice" clip-path="url(#{cid})"/>')
        out.append(f'<rect x="{ax}" y="{ay}" width="{aw}" height="{vis_h}" rx="7" fill="none" stroke="{stroke}" stroke-width="0.8"/>')
    else:
        out.append(f'<rect x="{x + w / 2 - 26}" y="{y + 8}" width="52" height="{vis_h - 4}" rx="10" fill="{c[0]}"/>')
        out.append(icon(n.get("icon", "layers"), x + w / 2 - 18, y + 13, c))
    ty = y + vis_h + 24
    tl = wrap(n.get("title", ""), 18)[:2]
    for i, line in enumerate(tl):
        out.append(text_el(x + w / 2, ty + i * 15, line, 12.5, ink, "bold"))
    yy = ty + len(tl) * 15
    if n.get("math"):
        out.append(text_el(x + w / 2, yy + 2, n["math"], 13, INK, family=SERIF, italic=True))
        yy += 16
    room = 1 if (len(tl) == 2 or n.get("math")) else 2
    for i, line in enumerate(wrap(n.get("sub", ""), 24)[:room]):
        out.append(text_el(x + w / 2, yy + i * 13.5, line, 10.5, MUTED))
    return "\n".join(out)


def anchor(n, side):
    x, y, w, h = n["_x"], n["_y"], n["_w"], n["_h"]
    return {"right": (x + w, y + h / 2), "left": (x, y + h / 2),
            "top": (x + w / 2, y), "bottom": (x + w / 2, y + h)}[side]


def route(a, b, e, top, gh):
    """Orthogonal path between nodes a and b. Returns (path d, label point)."""
    mode = e.get("route", "auto")
    if mode in ("over", "under") or b["_x"] + 1 < a["_x"]:
        if mode == "auto":
            mode = "under"
        sa, sb = ("top", "top") if mode == "over" else ("bottom", "bottom")
        (x1, y1), (x2, y2) = anchor(a, sa), anchor(b, sb)
        ly = top - 14 if mode == "over" else top + gh + 18
        return f"M{x1} {y1} V{ly} H{x2} V{y2 + (6 if mode == 'under' else -6)}", ((x1 + x2) / 2, ly)
    if abs(b["_x"] - a["_x"]) < 1:  # same column
        if b["_y"] > a["_y"]:
            (x1, y1), (x2, y2) = anchor(a, "bottom"), anchor(b, "top")
            return f"M{x1} {y1} V{y2 - 6}", (x1 + 4, (y1 + y2) / 2)
        if e.get("style") != "dashed":
            (x1, y1), (x2, y2) = anchor(a, "top"), anchor(b, "bottom")
            return f"M{x1} {y1} V{y2 + 6}", (x1 + 4, (y1 + y2) / 2)
        # dashed feedback loop: leave from the upper right, run up the right side, so it never shares
        # a start point or a line with the forward edges
        (x1, y1), (x2, y2) = anchor(a, "right"), anchor(b, "right")
        y1 -= a["_h"] / 4
        y2 += b["_h"] / 6
        side = x1 + GPAD - 4
        return f"M{x1} {y1} H{side} V{y2} H{x2 + 6}", (side, (y1 + y2) / 2)
    (x1, y1), (x2, y2) = anchor(a, "right"), anchor(b, "left")
    if abs(y1 - y2) < 1:
        return f"M{x1} {y1} H{x2 - 6}", ((x1 + x2) / 2, y1)
    same_group = a["_g"] is b["_g"]
    mx = (x1 + x2) / 2 if same_group else x2 - GGAP / 2 + 6
    if not same_group and x1 > mx - 8:
        mx = (x1 + x2) / 2
    return f"M{x1} {y1} H{mx} V{y2} H{x2 - 6}", ((x1 + mx) / 2, y1)


def draw_edge(e, nodes, top, gh):
    a, b = nodes.get(e["from"]), nodes.get(e["to"])
    if not a or not b:
        print(f"edge {e.get('from')} -> {e.get('to')}: unknown node", file=sys.stderr)
        return "", ""
    color = e.get("color", "gray")
    col = EDGE.get(color, EDGE["gray"])
    dash = ' stroke-dasharray="6 4"' if e.get("style") == "dashed" else ""
    d, (lx, ly) = route(a, b, e, top, gh)
    path = (f'<path d="{d}" fill="none" stroke="{col}" stroke-width="1.6"{dash} stroke-linecap="round" '
            f'stroke-linejoin="round" marker-end="url(#ah-{color if color in EDGE else "gray"})"/>')
    label = ""
    if e.get("label"):
        lw = plain_len(e["label"]) * 6.2 + 12
        label = (f'<rect x="{lx - lw / 2:.1f}" y="{ly - 9:.1f}" width="{lw:.1f}" height="17" rx="8.5" fill="#FFFFFF" '
                 f'stroke="{col}" stroke-width="0.7"/>' + text_el(lx, ly + 3.8, e["label"], 10.5, col, "bold"))
    return path, label


def build_svg(spec, base_dir, with_art):
    top, gh, width = layout(spec)
    nodes = {n["id"]: n for g in spec["groups"] for n in g["nodes"]}
    edges = spec.get("edges", [])
    needs_under = any(e.get("route") == "under" or
                      (e.get("route", "auto") == "auto" and e["to"] in nodes and e["from"] in nodes
                       and nodes[e["to"]].get("_x", 0) + 1 < nodes[e["from"]].get("_x", 0)) for e in edges)
    bottom = top + gh + (36 if needs_under else 0)
    legend = spec.get("legend", [])
    cap = wrap(spec["caption"], int((width - 2 * PAD) / 6.6)) if spec.get("caption") else []
    height = bottom + (30 if legend else 10) + len(cap) * 18 + PAD
    art_dir = base_dir / spec.get("art_dir", "art")

    defs = "".join(
        f'<marker id="ah-{k}" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
        f'<path d="M1 1 L9 5 L1 9 Z" fill="{v}"/></marker>' for k, v in EDGE.items())
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height:.0f}" viewBox="0 0 {width} {height:.0f}">',
           f"<defs>{defs}</defs>", f'<rect width="{width}" height="{height:.0f}" fill="#FFFFFF"/>']
    if spec.get("title"):
        out.append(text_el(PAD, PAD + 18, spec["title"], 20, INK, "bold", anchor="start"))
    out += [draw_group(g) for g in spec["groups"]]
    paths, labels = zip(*[draw_edge(e, nodes, top, gh) for e in edges]) if edges else ((), ())
    out += list(paths)  # edges under nodes
    out += [draw_node(n, art_dir, with_art) for n in nodes.values()]
    out += [draw_group_title(g) for g in spec["groups"]]
    out += list(labels)  # labels on top of everything

    y = bottom + 18
    if legend:
        x = PAD
        for item in legend:
            col = EDGE.get(item.get("color", "gray"), EDGE["gray"])
            dash = ' stroke-dasharray="6 4"' if item.get("style") == "dashed" else ""
            out.append(f'<line x1="{x}" y1="{y}" x2="{x + 30}" y2="{y}" stroke="{col}" stroke-width="1.8"{dash}/>')
            out.append(text_el(x + 38, y + 4, item["label"], 11.5, MUTED, anchor="start"))
            x += 38 + plain_len(item["label"]) * 6.6 + 28
        y += 28
    for i, line in enumerate(cap):
        out.append(text_el(PAD, y + i * 18, line, 12.5, MUTED, anchor="start", italic=True))
    out.append("</svg>")
    return "\n".join(out)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("spec")
    p.add_argument("--out", help="output path without extension (default: figure next to spec)")
    p.add_argument("--no-art", action="store_true", help="use icons only, ignore art thumbnails")
    p.add_argument("--scale", type=float, default=2.0)
    a = p.parse_args()
    spec_path = Path(a.spec)
    spec = json.loads(spec_path.read_text())
    if not spec.get("groups"):
        print("spec has no groups (for simple card figures use compose_figure.py)", file=sys.stderr)
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
    out.with_suffix(".png").write_bytes(bytes(resvg_py.svg_to_bytes(svg_string=svg, zoom=a.scale)))
    print(f"Wrote {out.with_suffix('.png')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
