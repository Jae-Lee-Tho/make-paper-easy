---
name: paper-explainer
description: Turn a research paper (PDF upload, PDF link, or paper webpage like arXiv) into a Markdown file plus an undergrad-friendly summary with key points and visuals of its data.
---

# Paper explainer

Input: one research paper as an attached PDF, a PDF URL, or a paper webpage (arXiv abs/html page, project page, publisher page).

Output, in this order:
1. A clean Markdown file of the full paper, given to the user.
2. A summary written for an undergraduate engineering/CS student.
3. Visuals of the paper's key structure and data, only where they help.

## Step 1 - Get the paper as Markdown

Use [MarkItDown](https://github.com/microsoft/markitdown). Install if missing:

```bash
pip install 'markitdown[pdf]'
```

Run the bundled converter (it accepts a local file or a URL):

```bash
python scripts/convert.py <input_path_or_url> <output.md>
```

By input type:
- **Attached PDF**: copy it into its own empty folder and convert the copy. Never edit the original.
- **PDF URL**: try `convert.py` with the URL directly. If the environment blocks the download, do not retry with other shell tools. For arXiv, switch to the HTML or abs page (below). Otherwise ask the user to attach the PDF.
- **Webpage** (arXiv abs/html, project page): use your web-fetch tool and ask for the full paper text as Markdown, keeping section headings, tables and figure captions. Save it to `<short-title>.md`. For arXiv, prefer `arxiv.org/html/<id>` when it exists; fall back to the abs page.

Name the file after the paper: `<first-author-or-short-title>-<arxiv-id-if-any>.md`.
Clean obvious extraction junk (repeated page headers/footers, broken hyphenation) only if quick; never rewrite the paper's content.
Give the file to the user.

If the paper text is already in the conversation (e.g. an attached .md), skip conversion and reuse it.

## Step 2 - Read before writing

Read the whole Markdown. Note:
- The problem and why it matters.
- The core idea or method, in one sentence.
- The main numbers: headline results tables, ablations, scaling results.
- Stated limitations.
- Prerequisite concepts an undergrad might not know (e.g. LoRA, VLA, SFT, diffusion, Kalman filter).

## Step 3 - Write the summary

Audience: an undergraduate ECE/CS student who knows calculus, linear algebra, basic probability and programming, but not this subfield's jargon. Write in the user's language.

Structure:
1. **TL;DR** - one paragraph: what they did and the single most important finding, in plain words.
2. **Background you need** - 3 to 6 short bullets defining jargon the paper assumes, one sentence each, with an everyday analogy where it helps.
3. **The problem** - what gap the paper fills.
4. **What they did** - the method or contribution, broken into its parts.
5. **Key findings** - bulleted, each with the concrete number from the paper (cite the table/figure).
6. **Limitations** - what the authors say it does not cover, plus any obvious caveat (sim-only, small user study, etc.).
7. **Why it matters** - one or two sentences on how this fits the field.

Rules:
- Every number must come from the paper. Never estimate or invent.
- Explain an acronym the first time it appears.
- Prefer short paragraphs and bullets; no walls of text.
- Keep the whole summary readable in about 5 minutes.

## Step 4 - Visualize where it earns its place

Add visuals between summary sections, with prose around each. Pick only what genuinely helps, usually 2 to 3:
- **Method or pipeline diagram**: the paper's architecture, data pipeline, or taxonomy. Max ~6 boxes.
- **Headline results chart**: a bar or line chart of the main table or scaling result, using exact values from the paper.
- **Concept illustration**: when a prerequisite idea is spatial or mechanical (attention, a control loop, sensor fusion), an illustrative diagram.

Skip a visual when a sentence or small table says it just as well. Only plot values printed in the paper's tables or text, never values guessed from a figure image.

### Choose the figure backend

**Built-in (default, no API key).** Draw figures yourself with whatever the environment offers: inline SVG/chart tools, an HTML artifact, or a matplotlib PNG. Use this unless PaperBanana mode applies.

**PaperBanana (optional, publication-style figures).** Use it when the user asks for it ("use PaperBanana", "make it look like a paper figure") or has set it up. It needs `pip install 'paperbanana[pdf]'` and one of `GOOGLE_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY` or `ATLASCLOUD_API_KEY`. Run `paperbanana doctor` to check.

- Diagram: write the paper's method section to `method.txt`, then:
  ```bash
  python scripts/pb_figure.py diagram method.txt "<one-sentence caption of what the figure shows>" fig_method.png
  ```
- Plot: write the numbers from one results table to `results.csv` (copied exactly from the paper; one row per method/condition), then:
  ```bash
  python scripts/pb_figure.py plot results.csv "<what the chart should compare>" fig_results.png
  ```

Rules for PaperBanana mode:
- It costs money (roughly $0.40 per diagram at default Gemini settings). Each call is capped at $1 by default (`--budget`). Before generating more than two figures, run with `--cost-only` and tell the user the estimate.
- Exit code 3 means it isn't installed or no key is set. Say so in one line and fall back to built-in figures; don't stop the task.
- Diagrams are AI-generated images. Check each one against the paper before sending it, and redo or drop any figure that shows wrong steps, labels or numbers.
- Give the user the image files, and still write the explanation around each figure in the reply.

## Step 5 - Finish

End with one line offering a next step (a quiz on the paper, a deeper dive into one section, or a comparison with a related paper). Don't recap the steps taken.
