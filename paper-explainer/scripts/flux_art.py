"""Generate text-free art pieces for a figure spec with Cloudflare Workers AI (FLUX.1 schnell).

Free tier: ~10,000 neurons/day (roughly 100-170 images). Needs a free Cloudflare
account and two environment variables:
    CF_ACCOUNT_ID   Workers AI -> Use REST API -> Get Account ID
    CF_API_TOKEN    Workers AI -> Use REST API -> Create a Workers AI API Token

Usage:
    python flux_art.py spec.json                 # generate missing art only
    python flux_art.py spec.json --force p1 p3   # regenerate these panels
    python flux_art.py spec.json --all           # regenerate everything

Each panel in spec.json with an "art" prompt gets  <art_dir>/<panel id>.jpg.
The spec's "style" block is appended to every prompt so the pieces match.
Exit code 3 = no credentials (caller should fall back to the soft-SVG mode).
"""
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

MODEL = "@cf/black-forest-labs/flux-1-schnell"
NO_BACKEND = 3
DEFAULT_STYLE = (
    "soft flat vector illustration, pastel colors (lavender, mint, peach, cream), "
    "gentle soft shading, rounded shapes, thin dark-gray outlines, clean white background, "
    "centered subject, plenty of empty space around it, academic paper figure style, "
    "no text, no letters, no numbers, no labels, no watermark"
)


def generate(prompt: str, seed: int, steps: int) -> bytes:
    acct, token = os.environ["CF_ACCOUNT_ID"], os.environ["CF_API_TOKEN"]
    url = f"https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/{MODEL}"
    body = json.dumps({"prompt": prompt[:2048], "steps": steps, "seed": seed}).encode()
    req = urllib.request.Request(url, data=body, headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        data = json.loads(e.read() or b"{}")
    if not data.get("success"):
        raise RuntimeError(f"Cloudflare error: {data.get('errors')}")
    return base64.b64decode(data["result"]["image"])


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("spec")
    p.add_argument("--force", nargs="*", default=[], help="panel ids to regenerate")
    p.add_argument("--all", action="store_true", help="regenerate every panel")
    p.add_argument("--steps", type=int, default=6, help="diffusion steps, max 8 (default 6)")
    a = p.parse_args()

    if not (os.environ.get("CF_ACCOUNT_ID") and os.environ.get("CF_API_TOKEN")):
        print("CF_ACCOUNT_ID / CF_API_TOKEN not set; skipping art (soft-SVG mode).", file=sys.stderr)
        return NO_BACKEND

    spec_path = Path(a.spec)
    spec = json.loads(spec_path.read_text())
    style = spec.get("style", DEFAULT_STYLE)
    seed = int(spec.get("seed", 42))
    art_dir = spec_path.parent / spec.get("art_dir", "art")
    art_dir.mkdir(parents=True, exist_ok=True)

    made, failed = 0, 0
    for i, panel in enumerate(spec.get("panels", [])):
        if not panel.get("art"):
            continue
        out = art_dir / f"{panel['id']}.jpg"
        if out.exists() and not a.all and panel["id"] not in a.force:
            print(f"keep   {out.name}")
            continue
        prompt = f"{panel['art']}, {style}"
        try:
            out.write_bytes(generate(prompt, seed + i, min(a.steps, 8)))
            print(f"made   {out.name}")
            made += 1
        except Exception as e:  # keep going so one bad panel doesn't block the figure
            print(f"FAILED {panel['id']}: {e}", file=sys.stderr)
            failed += 1
    print(f"{made} generated, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
