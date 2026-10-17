"""Turn a figure spec into one prompt to paste into the free Gemini app.

For users with no image-model access: the Gemini app (gemini.google.com) can
generate a few illustrated images a day for free. This writes a single,
detailed prompt describing the whole figure, including the exact labels.

Usage:
    python gemini_prompt.py spec.json > gemini_prompt.txt
"""
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    spec = json.loads(Path(sys.argv[1]).read_text())
    panels = spec["panels"]
    lines = [
        "Create a clean academic paper figure in a soft, illustrated style: pastel colors "
        "(lavender, mint, peach, cream), rounded cards, gentle shading, thin dark-gray outlines, "
        "white background, generous spacing. Use a clear sans-serif font. "
        f"Arrange {len(panels)} panels {'left to right' if spec.get('layout', 'row') == 'row' else 'in a grid'}"
        f"{', connected by arrows in order' if spec.get('arrows', True) else ''}.",
    ]
    if spec.get("title"):
        lines.append(f'Figure title at the top: "{spec["title"]}".')
    for i, p in enumerate(panels, 1):
        desc = p.get("art", "a simple illustration").split(", no text")[0]
        s = f'Panel {i}: an illustration of {desc}. Label it exactly "{p.get("title", "")}"'
        if p.get("subtitle"):
            s += f' with the smaller line "{p["subtitle"]}"'
        if p.get("chips"):
            s += " and small badges reading " + ", ".join(f'"{c}"' for c in p["chips"])
        lines.append(s + ".")
    lines.append("Spell every label exactly as written above. Add no other text.")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
