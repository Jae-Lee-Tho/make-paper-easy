# paper-explainer

An [Agent Skill](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) that turns a research paper into something an undergraduate can actually follow.

Give it a PDF, a PDF link, or a paper webpage (e.g. arXiv), and it:

1. **Converts the paper to Markdown** with [MarkItDown](https://github.com/microsoft/markitdown) and hands you the `.md` file.
2. **Writes an undergrad-friendly summary**: TL;DR, background terms explained, the problem, the method, key findings with the paper's real numbers, and limitations.
3. **Visualizes what helps**: a method/pipeline diagram and charts of the headline results, using only values printed in the paper.

## Install

### Claude Code
Copy the skill folder into your skills directory:

```bash
git clone https://github.com/<your-username>/paper-explainer-skill.git
cp -r paper-explainer-skill/paper-explainer ~/.claude/skills/
pip install 'markitdown[pdf]'
```

### Claude.ai / Claude app
Zip the `paper-explainer/` folder and upload it under **Settings → Capabilities → Skills**.

### Soft, illustrated diagrams (free)

Diagrams are built in hybrid mode. The agent writes every label, number and arrow as real SVG text, so it's always exact. An image model draws only the text-free art pieces, and the two are composited into one PNG and SVG, which the agent reviews before sending.

![Example layout](examples/libero-perm/figure.png)

The art comes from FLUX on Cloudflare Workers AI's free tier, roughly 100–170 images a day:

1. Create a free account at [dash.cloudflare.com](https://dash.cloudflare.com).
2. Go to **AI → Workers AI → Use REST API**. Copy the **Account ID**, then click **Create a Workers AI API Token** and copy the token.
3. Save them on your computer. On macOS with zsh, `read -s` keeps the token out of your shell history:
   ```bash
   echo 'export CF_ACCOUNT_ID="your_account_id"' >> ~/.zshrc
   read -s "tok?Paste token: "; echo "export CF_API_TOKEN=\"$tok\"" >> ~/.zshrc; unset tok
   source ~/.zshrc
   pip install resvg-py pillow
   ```

With no Cloudflare credentials, figures still render as soft pastel cards without art.

To try it on the bundled example:
```bash
python paper-explainer/scripts/flux_art.py examples/libero-perm/spec.json
python paper-explainer/scripts/compose_figure.py examples/libero-perm/spec.json
open examples/libero-perm/figure.png
```

### Optional: publication-style figures with PaperBanana

PaperBanana makes single-image, fully painted diagrams using Gemini or OpenAI image models. It's paid, roughly $0.40 per diagram. For polished, paper-style figures, enable the [PaperBanana](https://github.com/dwzhu-pku/PaperBanana) backend:

```bash
pip install 'paperbanana[pdf]'
export GOOGLE_API_KEY=...        # or OPENAI_API_KEY / OPENROUTER_API_KEY
paperbanana doctor               # confirm it's ready
```

Then ask: "Explain this paper and use PaperBanana for the figures."

A diagram costs roughly $0.40 at default settings, and each figure is capped at $1. Check before running with:

```bash
python paper-explainer/scripts/pb_figure.py diagram method.txt "Overview of the method" fig.png --cost-only
```

## Use

Just ask:

> Explain this paper: https://arxiv.org/abs/2610.22372

or attach a PDF and say "summarize this paper for me."

## Repo layout

```
paper-explainer/
├── SKILL.md            # instructions the agent follows
└── scripts/
    ├── convert.py         # PDF/URL → Markdown via MarkItDown
    ├── compose_figure.py  # spec.json → soft illustrated figure (SVG + PNG)
    ├── flux_art.py        # text-free art pieces via Cloudflare FLUX (free tier)
    ├── gemini_prompt.py   # spec.json → prompt for the free Gemini app
    └── pb_figure.py       # optional paid PaperBanana backend
examples/
└── libero-perm/spec.json  # worked example (LIBERO-PeRM, arXiv 2610.22372)
```

## Credits

- [MarkItDown](https://github.com/microsoft/markitdown) (Microsoft, MIT) for PDF/HTML → Markdown.
- [FLUX.1 schnell](https://developers.cloudflare.com/workers-ai/models/flux-1-schnell/) (Black Forest Labs, via Cloudflare Workers AI) for art pieces; [resvg](https://github.com/linebender/resvg) for SVG rendering.
- [PaperBanana](https://github.com/dwzhu-pku/PaperBanana) (Zhu et al., arXiv:2601.23265, Apache-2.0) for the multi-agent figure method. This skill calls the [`paperbanana`](https://pypi.org/project/paperbanana) package, an unofficial MIT-licensed implementation by llmsresearch. Neither project's code is included here; both are installed separately.

## Notes

- Scanned (image-only) PDFs yield no text; run OCR first.
- Some sandboxed environments block downloads from arbitrary URLs. For arXiv the skill falls back to the paper's HTML page; otherwise, attach the PDF.

## License

MIT. See [LICENSE](LICENSE).
