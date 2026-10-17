---
name: make-paper-easy
description: Make a research paper easy to understand. Give it a paper link (arXiv, project or publisher page), a PDF link, or an attached PDF, and it returns the paper as Markdown, an undergrad-friendly summary with key points, a PaperBanana-style method diagram and results charts whose every label and number is exact. Use when the user runs /make-paper-easy, or asks to explain, summarize, simplify or visualize a paper.
---

# make-paper-easy

## Usage

```
/make-paper-easy https://arxiv.org/abs/2610.22372
/make-paper-easy /path/to/paper.pdf
/make-paper-easy <link> in Korean          # write the summary in another language
/make-paper-easy <link> no figures         # summary only
```

Anything after the link is a plain-language instruction (language, focus, figure count). With no instructions: English summary, one method diagram, one results chart. Reply in the user's language when they write in one.

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

Go through these in order for each figure:

1. **Chart of numbers?** Always draw it in code from values copied from the paper; never send numbers through an image model. Use the paper-style theme (below).
2. **Method / pipeline / architecture diagram (default): dense mode, `compose_diagram.py`.** PaperBanana-style: tinted modules, many small nodes with icons, math labels, branching and feedback arrows. See "Dense diagrams". FLUX thumbnails are optional.
2b. **Simple 3-5 step overview for a beginner:** card mode, `compose_figure.py` with large FLUX art (see "Hybrid mode").
3. **PaperBanana**, only when the user asks for it and has a key. See the end of this section.
4. **No image model at all and the user wants painted art:** also give them `gemini_prompt.py`'s output to paste into the free Gemini app.

### Dense diagrams (PaperBanana-style)

Write `figures/<name>/spec.json` in the `compose_diagram.py` format (docstring; worked example: `examples/libero-perm-dense/spec.json`, which recreates the paper's Figure 3).

Plan it like the paper's own figure, not like a summary:
- **Modules = groups.** One group per stage or component the paper names (e.g. "Lens module", "Reasoning module"), left to right in data-flow order. Use `"style": "plain"` for an Inputs column and an Outputs group at the ends. Usually 3-5 groups.
- **Nodes = the real parts.** 2-6 nodes per group, placed on the group's `rows` x `cols` grid. Typically 12-20 nodes in total. Each has a 1-4 word `title`, a short `sub` (≤ 24 characters reads best), and an `icon` that fits: vlm, robot, doc, db, plan, gear, chart, check, user, matrix, image, loop, chat, path, metric, layers, scene.
- **Math where the paper has it.** Put the paper's own symbols in `math`: `π_{θ}(a_t | I_t)`, `ℒ_{KL}`, `𝒢`, `d ∈ {0, ¼, ¾, 1}`. Don't invent notation.
- **Edges carry the logic.** List every real data flow. Use `"style": "dashed", "color": "accent"` with a short `label` for feedback or refinement loops. Use `"route": "over"` or `"under"` for long skips that would cross other modules. Merges (several inputs into one node) are fine and look right.
- Add a `legend` when there are two edge styles. Add a one- or two-sentence `caption`.

Render:
```bash
python scripts/compose_diagram.py figures/<name>/spec.json           # icons (+ art thumbnails if present)
python scripts/flux_art.py figures/<name>/spec.json                  # optional: thumbnails for nodes with "art"
```
For thumbnails, give `art` only to the 2-4 nodes that show something concrete (a scene, a robot, a point cloud, an image grid). Keep icons for abstract steps.

Review the PNG (required), checking specifically:
- No arrow passes through a node or crosses a text label. If one does, reorder nodes in the grid, change `row`/`col`, or set `route`.
- Module titles fit their module.
- Every node, symbol and number is from the paper.

Iterate until clean, at most 4 rounds.

### Paper-style charts

```python
import sys; sys.path.insert(0, "<skill dir>/scripts")
from plot_style import apply, PALETTE, SOFT, HATCHES, bar_labels, save
apply()
```
- Combine 2-3 panels in one figure, labelled (a)/(b)/(c), each answering one question. Pick the form that fits: grouped bars with value labels (compare methods), dumbbell or slope chart (before/after, A vs B), line chart (scaling), diverging bars (gains and losses vs a baseline), donut (a taxonomy split).
- Give each panel a one-line takeaway title ("Zero-shot: tasks done, preferences ignored").
- Use hatching or marker shape so series differ by more than color. Put value labels on bars. Use one y-axis per panel.
- `save(fig, "results.png")` also writes an SVG. Worked example: `examples/libero-perm-dense/results_plot.py`.
- Review the PNG: no overlapping tick labels, legends or value labels; every value matches the paper's table.

### Hybrid mode: exact SVG text + FLUX art (card figures)

Needs `pip install resvg-py pillow` and, for the art, a free Cloudflare account with `CF_ACCOUNT_ID` and `CF_API_TOKEN` set (see README). Free tier is roughly 100-170 images a day.

**a. Plan.** Write `figures/<name>/spec.json` (format in `compose_figure.py`'s docstring; worked example in `examples/libero-perm/spec.json`):
- 3-5 panels, one per step or component of the paper's method, in reading order.
- `title`: 2-4 words, the paper's own term for that step. `subtitle`: one short line, at most ~50 characters. `chips`: 0-2 exact facts from the paper (counts, metric names, numbers).
- `art`: a FLUX prompt describing a concrete object or scene for that step. Describe things, never words: "a checkmark badge", not "a sign saying PASS". The shared `style` block is appended automatically; override it in the spec only if the user wants a different look.
- Every label and number must come from the paper.

**b. Draw the art** (runs where the credentials are, usually the user's computer):
```bash
python scripts/flux_art.py figures/<name>/spec.json
```
Exit code 3 means no credentials: say so in one line and continue; step c renders soft cards instead.

**c. Compose and render:**
```bash
python scripts/compose_figure.py figures/<name>/spec.json            # with art
python scripts/compose_figure.py figures/<name>/spec.json --no-art   # soft-SVG only
```
This writes `figure.svg` (editable) and `figure.png` (2x, crisp).

**d. Review: required.** Open `figure.png` and look at it. Check:
- No text overlaps, cut-off text, or text running outside a card.
- Each art piece shows what its step says, and contains no stray letters or garbled text.
- Every label and number matches the paper.
- The pieces look like one set (palette, style).

Fix and re-render: shorten text in the spec for layout problems; for a bad art piece, tweak its prompt and run `flux_art.py spec.json --force <panel id>`. Repeat until clean, at most 3 rounds, then send the PNG and SVG to the user.

### PaperBanana (optional, paid)

Use it when the user asks for it ("use PaperBanana") or has set it up. It needs `pip install 'paperbanana[pdf]'` and one of `GOOGLE_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY` or `ATLASCLOUD_API_KEY`. Run `paperbanana doctor` to check.

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
