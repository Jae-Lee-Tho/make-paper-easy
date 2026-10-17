"""Optional PaperBanana backend for make-paper-easy.

Generates a publication-style figure with the `paperbanana` package
(https://pypi.org/project/paperbanana, an unofficial MIT implementation of
PaperBanana, arXiv:2601.23265). Requires an API key; without one it exits
with code 3 so the agent can fall back to drawing figures itself.

Usage:
    # Methodology / pipeline diagram from a text file (e.g. the paper's method section)
    python pb_figure.py diagram <method.txt> "<caption>" <out.png> [--budget 1.0]

    # Statistical plot from a CSV/JSON of numbers copied from the paper's tables
    python pb_figure.py plot <data.csv> "<intent>" <out.png> [--budget 1.0]

    # Estimate cost only, no API calls (works without a key)
    python pb_figure.py diagram <method.txt> "<caption>" <out.png> --cost-only
"""
import argparse
import os
import shutil
import subprocess
import sys

KEY_VARS = ["GOOGLE_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY", "ATLASCLOUD_API_KEY"]
NO_BACKEND = 3


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("kind", choices=["diagram", "plot"])
    p.add_argument("source", help="method text/PDF (diagram) or CSV/JSON data (plot)")
    p.add_argument("caption", help="figure caption (diagram) or plot intent (plot)")
    p.add_argument("output", help="output image path, e.g. fig.png")
    p.add_argument("--budget", type=float, default=1.0, help="USD cap per figure (default 1.0)")
    p.add_argument("--aspect-ratio", default="16:9")
    p.add_argument("--cost-only", action="store_true", help="estimate cost, no API calls")
    p.add_argument("--vector", action="store_true", help="plots only: also export SVG/PDF")
    a = p.parse_args()

    if shutil.which("paperbanana") is None:
        print("paperbanana not installed: pip install 'paperbanana[pdf]'", file=sys.stderr)
        return NO_BACKEND
    if not a.cost_only and not any(os.environ.get(k) for k in KEY_VARS):
        print("No PaperBanana API key set (" + ", ".join(KEY_VARS) + "). "
              "Falling back to built-in figures.", file=sys.stderr)
        return NO_BACKEND
    if not os.path.exists(a.source):
        print(f"Input not found: {a.source}", file=sys.stderr)
        return 2

    if a.kind == "diagram":
        cmd = ["paperbanana", "generate", "-i", a.source, "-c", a.caption,
               "-o", a.output, "-ar", a.aspect_ratio]
    else:
        cmd = ["paperbanana", "plot", "-d", a.source, "--intent", a.caption,
               "-o", a.output, "-ar", a.aspect_ratio]
        if a.vector:
            cmd.append("--vector")
    cmd += ["--cost-only"] if a.cost_only else ["--budget", str(a.budget)]

    print("Running:", " ".join(cmd), file=sys.stderr)
    rc = subprocess.run(cmd).returncode
    if rc == 0 and not a.cost_only:
        print(f"Wrote {a.output}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
