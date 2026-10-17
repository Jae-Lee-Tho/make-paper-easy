# Token benchmark

**Question:** how many tokens does make-paper-easy save by converting a paper to clean text instead of letting the agent read the PDF directly?

**Answer, on 4 real papers (40 pages): 60% fewer tokens on standard models and 82% fewer on high-resolution models.** It also keeps more of the paper's text intact than plain MarkItDown.

## Results

| Paper | Pages | PDF read directly | PDF, high-res model | Plain MarkItDown | **make-paper-easy** | Saved | Saved, high-res |
|---|---:|---:|---:|---:|---:|---:|---:|
| [Beyond Summarization](https://arxiv.org/abs/2304.02623) (CHI '23 workshop) | 4 | 12,509 | 25,557 | 6,615 | **6,120** | 51% | 76% |
| [Literature Graph in Semantic Scholar](https://aclanthology.org/N18-3011/) (NAACL '18) | 8 | 21,230 | 46,870 | 17,461 | **8,046** | 62% | 83% |
| [PaperMage](https://aclanthology.org/2023.emnlp-demo.45/) (EMNLP '23 demo) | 13 | 35,473 | 77,138 | 26,504 | **14,044** | 60% | 82% |
| [S2ORC](https://aclanthology.org/2020.acl-main.447/) (ACL '20) | 15 | 39,219 | 87,294 | 30,778 | **14,645** | 63% | 83% |
| **Total** | **40** | **108,431** | **236,859** | **81,358** | **42,855** | **60%** | **82%** |

On average a page costs about **2,700 tokens** read directly (about **5,900** on high-resolution models), versus about **1,070 tokens** with make-paper-easy.

### Faithfulness: fewer tokens, nothing lost

Each output is scored by the share of the paper's words (4+ letters) and decimal numbers that survive. The reference is an independent extractor (pypdf).

| Paper | Words kept: MarkItDown | Words kept: **make-paper-easy** | Numbers kept: MarkItDown | Numbers kept: **make-paper-easy** | MarkItDown output that is whitespace |
|---|---:|---:|---:|---:|---:|
| Beyond Summarization | 99.8% | **99.8%** | 94.4% | **100%** | 15% |
| Literature Graph | 59.4% | **97.9%** | 100% | **100%** | 36% |
| PaperMage | 60.2% | **99.7%** | 100% | **100%** | 31% |
| S2ORC | 73.5% | **97.8%** | 100% | **100%** | 39% |

MarkItDown's newest PDF converter detects borderless tables. On two-column papers it mistakes ordinary paragraphs for tables, so it glues words together inside padded `| --- |` cells. That's why its word scores are low and so much of its output is whitespace. make-paper-easy uses PDFium (via `pypdfium2`, which MarkItDown already installs) for PDFs, then cleans the text up: ligatures, hyphenated line breaks, wrapped lines. MarkItDown is still used for HTML, DOCX and other formats.

## How it was measured

- **PDF read directly** = the page's extracted text tokens + one page-image per page. Claude [processes PDFs](https://docs.claude.com/en/docs/build-with-claude/pdf-support) as "a combination of text and images", where every page becomes an image. Image tokens use the [vision formula](https://docs.claude.com/en/docs/build-with-claude/vision) `ceil(w/28) × ceil(h/28)`, assuming each page reaches the model tier's maximum size: 1,568 tokens per page on standard models, and up to 4,784 on high-resolution models (Claude 4.7 and later).
- **Text tokens** were counted with Anthropic's open-source legacy tokenizer. Without it, the script falls back to 4 characters per token, which gives 59% / 81%, within one point.
- **Exact numbers for your model:** run with `--exact` and an `ANTHROPIC_API_KEY`. The script then sends the PDF and the text to Anthropic's [token-counting API](https://docs.claude.com/en/docs/build-with-claude/token-counting), which is free, and reports the real counts.

```bash
pip install -r requirements.txt pypdf
python benchmarks/token_benchmark.py            # reproduces the tables above
python benchmarks/token_benchmark.py --exact    # exact counts (needs ANTHROPIC_API_KEY, pip install anthropic)
python benchmarks/token_benchmark.py --pdfs my_paper.pdf
```

The four PDFs are public papers that ship as test fixtures in Apache-2.0 repositories ([allenai/papermage](https://github.com/allenai/papermage), [allenai/s2orc-doc2json](https://github.com/allenai/s2orc-doc2json)). The script downloads them; they aren't redistributed here.

## Trade-off

Text only means the model doesn't *see* the paper's figures. make-paper-easy doesn't need them: it builds its own diagram and charts from the paper's text and tables, and every number in them is checked against that text. Equations come through as plain text, for example `softmax(QK^T/sqrt(d_k))`. That's enough for an undergrad-level explanation, but not for reproducing a typeset derivation.
