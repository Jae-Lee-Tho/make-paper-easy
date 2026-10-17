"""Reproduce the token-savings table in benchmarks/README.md.

Compares, for real research papers:
  1. Reading the PDF directly: the model gets each page's extracted text PLUS each page as an image
     (how Claude processes PDFs: docs.claude.com/en/docs/build-with-claude/pdf-support).
  2. Plain MarkItDown output.
  3. make-paper-easy's convert.py output (what the skill actually feeds the model).
It also scores faithfulness: how many of the paper's words and decimal numbers survive.

Usage (from the repo root):
    python benchmarks/token_benchmark.py                 # offline estimate
    python benchmarks/token_benchmark.py --exact         # exact counts from Anthropic's token-counting API
                                                         # (needs ANTHROPIC_API_KEY and `pip install anthropic`)
    python benchmarks/token_benchmark.py --pdfs a.pdf b.pdf   # your own papers

Offline mode counts text tokens with Anthropic's open-source legacy tokenizer if it is available
(pip install "anthropic==0.34.2" tokenizers), otherwise with a 4-characters-per-token estimate.
Page-image tokens use the formula in docs.claude.com/en/docs/build-with-claude/vision:
ceil(w/28) * ceil(h/28) after downscaling to the model tier's limits.
"""
import argparse
import base64
import os
import re
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "skills" / "make-paper-easy" / "scripts"))
from convert import CHARS_PER_TOKEN, page_image_tokens, pdf_to_markdown  # noqa: E402

# Public research papers bundled as test fixtures in Apache-2.0 GitHub repos (downloaded, not redistributed).
PAPERS = {
    "2304.02623v1.pdf": "https://raw.githubusercontent.com/allenai/papermage/main/tests/fixtures/2304.02623v1.pdf",
    "N18-3011.pdf": "https://raw.githubusercontent.com/allenai/s2orc-doc2json/main/tests/pdf/N18-3011.pdf",
    "papermage.pdf": "https://raw.githubusercontent.com/allenai/papermage/main/tests/fixtures/papermage.pdf",
    "2020.acl-main.447.pdf": "https://raw.githubusercontent.com/allenai/papermage/main/tests/fixtures/2020.acl-main.447.pdf",
}
MODEL = "claude-sonnet-5-5"


def counter(exact):
    if exact:
        import anthropic
        client = anthropic.Anthropic()

        def count_text(s):
            return client.messages.count_tokens(model=MODEL, messages=[{"role": "user", "content": s}]).input_tokens

        def count_pdf(path):
            data = base64.standard_b64encode(Path(path).read_bytes()).decode()
            msg = [{"role": "user", "content": [{"type": "document", "source": {
                "type": "base64", "media_type": "application/pdf", "data": data}}]}]
            return client.messages.count_tokens(model=MODEL, messages=msg).input_tokens
        return count_text, count_pdf, f"exact, Anthropic token-counting API ({MODEL})"
    try:
        import anthropic
        from tokenizers import Tokenizer
        tok = Tokenizer.from_file(str(Path(anthropic.__file__).parent / "tokenizer.json"))
        return (lambda s: len(tok.encode(s).ids)), None, "estimate, Anthropic legacy tokenizer + vision formula"
    except Exception:
        return (lambda s: round(len(s) / CHARS_PER_TOKEN)), None, "estimate, 4 chars/token + vision formula"


def words(s):
    return set(re.findall(r"[A-Za-z]{4,}", s.lower()))


def numbers(s):
    return set(re.findall(r"\d+\.\d+", s))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exact", action="store_true")
    ap.add_argument("--pdfs", nargs="*")
    a = ap.parse_args()

    cache = HERE / ".cache"
    cache.mkdir(exist_ok=True)
    paths = [Path(p) for p in a.pdfs] if a.pdfs else []
    if not paths:
        for name, url in PAPERS.items():
            p = cache / name
            if not p.exists():
                print(f"downloading {name} ...", file=sys.stderr)
                urllib.request.urlretrieve(url, p)
            paths.append(p)

    count_text, count_pdf, mode = counter(a.exact)
    from markitdown import MarkItDown
    from pypdf import PdfReader
    md = MarkItDown()

    print(f"Token counts ({mode})\n")
    hdr = f"{'paper':24}{'pages':>6}{'PDF direct':>12}{'PDF hi-res':>12}{'MarkItDown':>12}{'convert.py':>12}{'saved':>7}{'saved hi-res':>14}"
    print(hdr)
    tot = dict(p=0, d=0, h=0, m=0, c=0)
    quality = []
    for p in paths:
        reader = PdfReader(str(p))
        n = len(reader.pages)
        ref = "\n".join(pg.extract_text() or "" for pg in reader.pages)  # independent extractor (pypdf)
        ours, _, size = pdf_to_markdown(str(p))
        mk = md.convert(str(p)).text_content
        c_ours, c_mk = count_text(ours), count_text(mk)
        if count_pdf:
            direct = count_pdf(p)
            hires = direct  # the API counts for the chosen model's own resolution tier
        else:
            text_tok = count_text(ref)
            direct = text_tok + n * page_image_tokens(*size, 1568, 1568)
            hires = text_tok + n * page_image_tokens(*size, 2576, 4784)
        for k, v in (("p", n), ("d", direct), ("h", hires), ("m", c_mk), ("c", c_ours)):
            tot[k] += v
        print(f"{p.name[:23]:24}{n:>6}{direct:>12,}{hires:>12,}{c_mk:>12,}{c_ours:>12,}"
              f"{1 - c_ours / direct:>7.0%}{1 - c_ours / hires:>14.0%}")
        rw, rn = words(ref), numbers(ref)
        quality.append((p.name, len(rw & words(mk)) / len(rw), len(rw & words(ours)) / len(rw),
                        len(rn & numbers(mk)) / max(1, len(rn)), len(rn & numbers(ours)) / max(1, len(rn)),
                        sum(ch.isspace() for ch in mk) / len(mk)))
    print(f"{'TOTAL':24}{tot['p']:>6}{tot['d']:>12,}{tot['h']:>12,}{tot['m']:>12,}{tot['c']:>12,}"
          f"{1 - tot['c'] / tot['d']:>7.0%}{1 - tot['c'] / tot['h']:>14.0%}")

    print("\nFaithfulness (share of the paper's words / decimal numbers kept; reference = pypdf text)\n")
    print(f"{'paper':24}{'words: MarkItDown':>19}{'convert.py':>12}{'numbers: MarkItDown':>21}{'convert.py':>12}{'MarkItDown whitespace':>23}")
    for name, wm, wo, nm, no, ws in quality:
        print(f"{name[:23]:24}{wm:>19.1%}{wo:>12.1%}{nm:>21.1%}{no:>12.1%}{ws:>23.0%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
