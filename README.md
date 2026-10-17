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

## Use

Just ask:

> Explain this paper: https://arxiv.org/abs/2610.22372

or attach a PDF and say "summarize this paper for me."

## Repo layout

```
paper-explainer/
├── SKILL.md            # instructions the agent follows
└── scripts/
    └── convert.py      # PDF/URL → Markdown via MarkItDown
```

## Notes

- Scanned (image-only) PDFs yield no text; run OCR first.
- Some sandboxed environments block downloads from arbitrary URLs. For arXiv the skill falls back to the paper's HTML page; otherwise, attach the PDF.

## License

MIT. See [LICENSE](LICENSE).
