"""Convert a paper (local PDF/HTML file or URL) to Markdown with MarkItDown.

Usage:
    python convert.py <input_path_or_url> <output.md>
"""
import sys

from markitdown import MarkItDown


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    src, out = sys.argv[1], sys.argv[2]
    result = MarkItDown().convert(src)
    text = result.text_content or ""
    if not text.strip():
        print(f"No text extracted from {src} (scanned PDF? try OCR).", file=sys.stderr)
        return 1
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Wrote {out} ({len(text):,} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
