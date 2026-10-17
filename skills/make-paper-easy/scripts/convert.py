"""Convert a paper (PDF, HTML, DOCX, URL, ...) to compact Markdown, and report the token savings.

Why: when an agent opens a PDF directly, every page is sent to the model as an IMAGE plus its
extracted text. Clean text alone carries the same words and numbers for far fewer tokens
(about 60% fewer on standard-resolution models, about 80% fewer on high-resolution ones;
see benchmarks/README.md).

- PDFs: PDFium text extraction (pypdfium2) + cleanup. It keeps two-column reading order and word
  spacing, and avoids MarkItDown's table detector, which misfires on two-column papers and
  pads the output with `| --- |` cells.
- Everything else (HTML, DOCX, PPTX, URLs): MarkItDown + whitespace cleanup.

Usage:
    python convert.py paper.pdf paper.md
    python convert.py https://arxiv.org/abs/1706.03762 paper.md   # arXiv abs/html links fetch the PDF
    python convert.py https://example.com/page.html page.md       # web pages go through MarkItDown

Exit codes: 0 ok, 1 no text (scanned PDF), 2 bad usage, 4 download failed.
"""
import math
import re
import sys
from pathlib import Path

CHARS_PER_TOKEN = 4.0  # measured on cleaned paper text with Anthropic's tokenizer (benchmarks/README.md)
LIGATURES = {"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl",
             "­": "", "‐": "-", " ": " "}


def clean_block(t: str) -> str:
    """Normalize ligatures/whitespace, re-join hyphenated line breaks, unwrap paragraph lines."""
    for k, v in LIGATURES.items():
        t = t.replace(k, v)
    t = re.sub(r"\(cid:\d+\)", "", t)
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"(\w)-\n(\w)", r"\1\2", t)
    paras = [p.strip() for p in re.split(r"\n\s*\n", t)]
    return "\n\n".join(re.sub(r"\s*\n\s*", " ", p) for p in paras if p)


def pdf_to_markdown(path: str):
    """Returns (markdown, page_count, (width_pt, height_pt) of page 1)."""
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(path)
    pages = []
    for i in range(len(doc)):
        text = doc[i].get_textpage().get_text_bounded()
        pages.append(f"<!-- page {i + 1} -->\n" + clean_block(text))
    size = doc[0].get_size() if len(doc) else (612, 792)
    return "\n\n".join(pages) + "\n", len(doc), size


def fetch_if_pdf(url: str):
    """Download a PDF URL to a temp file so it goes through the PDFium path.
    arXiv abs/html links are rewritten to the PDF. Returns (path_or_url, tempfile_or_None)."""
    import tempfile
    import urllib.request
    m = re.match(r"https?://(?:www\.|export\.)?arxiv\.org/(?:abs|html|pdf)/([^?#]+?)(?:\.pdf)?/?(?:[?#].*)?$", url)
    if m:
        url = f"https://arxiv.org/pdf/{m.group(1)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "make-paper-easy/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
    except Exception as e:
        print(f"Could not download {url}: {e}", file=sys.stderr)
        return None, None
    if not data.startswith(b"%PDF"):
        return url, None  # an HTML page etc.: MarkItDown handles it
    f = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    f.write(data)
    f.close()
    return f.name, f.name


def tidy_markdown(md: str) -> str:
    """Light cleanup for MarkItDown output: trailing spaces, padded table cells, extra blank lines."""
    md = re.sub(r"[ \t]+\n", "\n", md)
    md = re.sub(r"\|( {2,})", "| ", md)
    md = re.sub(r"( {2,})\|", " |", md)
    md = re.sub(r"\|( ?-{4,} ?)(?=\|)", "| --- ", md)
    return re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"


def page_image_tokens(w_pt: float, h_pt: float, max_edge: int, max_tokens: int) -> int:
    """Claude vision cost of one page image: ceil(w/28) * ceil(h/28) after downscaling to the
    model tier's limits (docs: build-with-claude/vision). Assumes the page is rendered at least that large."""
    s = max_edge / max(w_pt, h_pt)
    w, h = w_pt * s, h_pt * s
    while math.ceil(w / 28) * math.ceil(h / 28) > max_tokens:
        w, h = w * 0.995, h * 0.995
    return math.ceil(w / 28) * math.ceil(h / 28)


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--quiet"]
    quiet = "--quiet" in sys.argv
    if len(args) != 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    src, out = args
    tmp = None
    if src.startswith(("http://", "https://")):
        src, tmp = fetch_if_pdf(src)
        if src is None:
            print("Download blocked or failed. Use your web-fetch tool on the paper's HTML page, "
                  "or ask the user to attach the PDF.", file=sys.stderr)
            return 4
    is_pdf = src.lower().endswith(".pdf") and not src.startswith(("http://", "https://"))

    pages = size = None
    if is_pdf:
        try:
            text, pages, size = pdf_to_markdown(src)
            if len(text.strip()) < 200 * max(1, pages):  # (nearly) no text layer: scanned PDF
                print(f"{src}: very little text found; it may be a scanned PDF (run OCR first).", file=sys.stderr)
        except ImportError:
            is_pdf = False  # pypdfium2 missing: fall back to MarkItDown below
    if not is_pdf:
        from markitdown import MarkItDown
        text = tidy_markdown(MarkItDown().convert(src).text_content or "")
        if src.lower().endswith(".pdf"):
            try:
                import pypdfium2 as pdfium
                d = pdfium.PdfDocument(src)
                pages, size = len(d), d[0].get_size()
            except Exception:
                pass

    if tmp:
        Path(tmp).unlink(missing_ok=True)
    if not text.strip():
        print(f"No text extracted from {src} (scanned PDF? try OCR).", file=sys.stderr)
        return 1
    Path(out).write_text(text, encoding="utf-8")
    md_tokens = round(len(text) / CHARS_PER_TOKEN)
    print(f"Wrote {out} ({len(text):,} chars, ~{md_tokens:,} tokens)")

    if pages and size and not quiet:
        std = md_tokens + pages * page_image_tokens(*size, 1568, 1568)
        hi = md_tokens + pages * page_image_tokens(*size, 2576, 4784)
        print(f"Token estimate vs. reading the PDF directly ({pages} pages, each sent as text + a page image):")
        print(f"  standard-resolution models: ~{std:,} -> ~{md_tokens:,} tokens ({1 - md_tokens / std:.0%} fewer)")
        print(f"  high-resolution models:     ~{hi:,} -> ~{md_tokens:,} tokens ({1 - md_tokens / hi:.0%} fewer)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
