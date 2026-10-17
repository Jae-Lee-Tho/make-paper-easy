"""Smoke tests: every script runs on the bundled examples and produces sane output.

Run from the repo root:  python -m pytest -q
No network or API keys needed. Outputs go to a temp dir, never into examples/.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "make-paper-easy"
SCRIPTS = SKILL / "scripts"
EXAMPLES = ROOT / "examples"
PY = sys.executable
NO_KEYS = {k: v for k, v in os.environ.items()
           if k not in ("CF_ACCOUNT_ID", "CF_API_TOKEN", "GOOGLE_API_KEY", "OPENAI_API_KEY",
                        "OPENROUTER_API_KEY", "ATLASCLOUD_API_KEY")}


def run(*args, cwd=None):
    return subprocess.run([PY, *map(str, args)], cwd=cwd, env=NO_KEYS, capture_output=True, text=True)


def copy_example(name, tmp_path):
    dst = tmp_path / name
    shutil.copytree(EXAMPLES / name, dst)
    return dst


# ---------- skill metadata ----------
def test_skill_frontmatter():
    text = (SKILL / "SKILL.md").read_text()
    m = re.match(r"---\nname: (.+)\ndescription: (.+)\n---\n", text)
    assert m, "SKILL.md must start with name/description frontmatter"
    assert m.group(1) == SKILL.name == "make-paper-easy"
    assert len(m.group(2)) <= 1024


def test_all_json_parses():
    for p in EXAMPLES.rglob("*.json"):
        json.loads(p.read_text(encoding="utf-8"))


def test_summary_figures_exist():
    for p in EXAMPLES.rglob("summary.json"):
        for b in json.loads(p.read_text())["blocks"]:
            if b.get("type") == "figure":
                assert (p.parent / b["path"]).exists(), f"{p}: missing {b['path']}"


# ---------- convert.py ----------
def test_convert_local_html(tmp_path):
    src = tmp_path / "paper.html"
    src.write_text("<h1>A Test Paper</h1><p>We report 42.0 BLEU.</p>")
    r = run(SCRIPTS / "convert.py", src, tmp_path / "paper.md")
    assert r.returncode == 0, r.stderr
    md = (tmp_path / "paper.md").read_text()
    assert "A Test Paper" in md and "42.0 BLEU" in md


def make_two_column_pdf(path):
    """A 2-page, two-column paper-like PDF: the layout that breaks naive extractors."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph
    w, h = letter
    gap, m = 18, 54
    col = (w - 2 * m - gap) / 2
    doc = BaseDocTemplate(str(path), pagesize=letter)
    doc.addPageTemplates([PageTemplate(frames=[Frame(m, m, col, h - 2 * m), Frame(m + col + gap, m, col, h - 2 * m)])])
    body = getSampleStyleSheet()["BodyText"]
    story = []
    for i in range(1, 41):
        story.append(Paragraph(f"Paragraph {i}: the encoder reaches {20 + i}.5 BLEU on newstest2014 while the "
                               f"decoder uses multi-head attention with eight heads. " * 2, body))
    doc.build(story)


def test_convert_two_column_pdf(tmp_path):
    pdf = tmp_path / "paper.pdf"
    make_two_column_pdf(pdf)
    r = run(SCRIPTS / "convert.py", pdf, tmp_path / "paper.md")
    assert r.returncode == 0, r.stderr
    md = (tmp_path / "paper.md").read_text()
    assert "fewer)" in r.stdout and "high-resolution" in r.stdout          # token report printed
    assert "<!-- page 2 -->" in md
    assert "| --- |" not in md and "  " not in md                         # no fake tables / padding
    for i in range(1, 41):                                                # every number survives
        assert f"{20 + i}.5 BLEU" in md
    order = [md.index(f"Paragraph {i}:") for i in range(1, 41)]
    assert order == sorted(order), "two-column reading order broken"
    assert "multi-head attention with eight heads" in md                  # words not glued together


def test_convert_bad_url_exits_4(tmp_path):
    r = run(SCRIPTS / "convert.py", "http://127.0.0.1:9/paper.pdf", tmp_path / "x.md")
    assert r.returncode == 4 and "Traceback" not in r.stderr


# ---------- compose_diagram.py ----------
@pytest.mark.parametrize("example", ["transformer", "libero-perm-dense"])
def test_dense_diagram_renders_cleanly(example, tmp_path):
    d = copy_example(example, tmp_path)
    r = run(SCRIPTS / "compose_diagram.py", d / "spec.json", "--out", d / "out")
    assert r.returncode == 0, f"warnings or errors:\n{r.stderr}"
    assert (d / "out.png").stat().st_size > 50_000
    assert "<svg" in (d / "out.svg").read_text()[:200]


def test_dense_diagram_flags_text_overflow(tmp_path):
    spec = {"groups": [{"id": "g", "title": "G", "rows": 1, "nodes": [
        {"id": "n", "title": "Short", "sub": "this subtitle is far far far too long to fit inside one small node box"}]}]}
    p = tmp_path / "spec.json"
    p.write_text(json.dumps(spec))
    r = run(SCRIPTS / "compose_diagram.py", p)
    assert r.returncode == 3 and "WARNING" in r.stderr and '"n"' in r.stderr


# ---------- compose_figure.py (card mode) ----------
@pytest.mark.parametrize("flag", [[], ["--no-art"]])
def test_card_figure(flag, tmp_path):
    d = copy_example("libero-perm", tmp_path)
    r = run(SCRIPTS / "compose_figure.py", d / "spec.json", "--out", d / "out", *flag)
    assert r.returncode == 0, r.stderr
    assert (d / "out.png").exists()


# ---------- make_sheet.py ----------
@pytest.mark.parametrize("example", ["transformer", "libero-perm-dense"])
def test_sheet_png_and_pdf(example, tmp_path):
    from pypdf import PdfReader
    d = copy_example(example, tmp_path)
    r = run(SCRIPTS / "make_sheet.py", d / "summary.json", "--out", d / "sheet", "--pdf")
    assert r.returncode == 0, r.stderr
    assert "selectable text" in r.stdout, r.stdout
    assert (d / "sheet.png").stat().st_size > 200_000
    reader = PdfReader(d / "sheet.pdf")
    assert len(reader.pages) >= 2
    text = " ".join(pg.extract_text() for pg in reader.pages)
    spec = json.loads((d / "summary.json").read_text())
    for num in re.findall(r"\d+\.\d+", spec["tldr"]):  # every number in the TL;DR is in the PDF text
        assert num in text, f"{num} missing from PDF text"


def test_sheet_a4(tmp_path):
    from pypdf import PdfReader
    d = copy_example("transformer", tmp_path)
    r = run(SCRIPTS / "make_sheet.py", d / "summary.json", "--out", d / "a4", "--pdf", "--page", "a4")
    assert r.returncode == 0, r.stderr
    w, h = (float(v) for v in PdfReader(d / "a4.pdf").pages[0].mediabox[2:])
    assert abs(w - 595.3) < 1 and abs(h - 841.9) < 1


def test_sheet_cjk_falls_back_to_image_pdf(tmp_path):
    d = copy_example("transformer", tmp_path)
    spec = json.loads((d / "summary.json").read_text())
    spec["tldr"] = "한국어 요약 테스트입니다."
    (d / "summary.json").write_text(json.dumps(spec, ensure_ascii=False))
    r = run(SCRIPTS / "make_sheet.py", d / "summary.json", "--out", d / "ko", "--pdf")
    assert r.returncode == 0 and (d / "ko.pdf").exists() and "image-only" in r.stdout


def test_normalize_super_and_subscripts():
    sys.path.insert(0, str(SCRIPTS))
    from make_sheet import normalize
    assert normalize("3.3·10¹⁸") == "3.3·10^{18}"
    assert normalize("QKᵀ") == "QK^{T}"
    assert normalize("x₁ + x₂") == "x_{1} + x_{2}"
    assert normalize("plain") == "plain"


# ---------- charts ----------
def test_results_plot_example(tmp_path):
    # the example script writes next to itself; run a copy inside a mirrored tree
    root = tmp_path / "repo"
    shutil.copytree(SKILL, root / "skills" / "make-paper-easy")
    shutil.copytree(EXAMPLES / "transformer", root / "examples" / "transformer")
    r = run(root / "examples" / "transformer" / "results_plot.py")
    assert r.returncode == 0, r.stderr
    assert (root / "examples" / "transformer" / "results.svg").exists()


# ---------- optional backends degrade gracefully ----------
def test_flux_without_credentials_exits_3(tmp_path):
    d = copy_example("libero-perm", tmp_path)
    r = run(SCRIPTS / "flux_art.py", d / "spec.json")
    assert r.returncode == 3


def test_paperbanana_without_key_exits_3(tmp_path):
    (tmp_path / "m.txt").write_text("method")
    r = run(SCRIPTS / "pb_figure.py", "diagram", tmp_path / "m.txt", "caption", tmp_path / "f.png")
    assert r.returncode == 3


def test_gemini_prompt(tmp_path):
    r = run(SCRIPTS / "gemini_prompt.py", EXAMPLES / "libero-perm" / "spec.json")
    assert r.returncode == 0 and "Spell every label exactly" in r.stdout
