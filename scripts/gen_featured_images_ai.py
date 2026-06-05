"""Generate featured-image.png for each post using OpenAI gpt-image-1."""

import base64
import re
import time
from pathlib import Path

from openai import OpenAI

CONTENT_DIR = Path(__file__).parent.parent / "content" / "posts"

PROMPTS: dict[str, str] = {
    "argocd":          "Abstract tech illustration: glowing blue Kubernetes hexagon clusters connected by ArgoCD deployment pipelines, dark background, minimal flat style",
    "backprop":        "Abstract neural network backpropagation visualization, glowing gradient flow through layered nodes, dark background, mathematical elegance",
    "dev-setup":       "Clean developer workstation illustration, terminal windows with code, zsh prompt, Docker containers, minimal dark aesthetic",
    "hello-world":     "Abstract digital hello world moment, code on dark screen, soft glow, minimalist tech art",
    "homepage-setup":  "Server rack with nginx web server, deployment pipeline arrows, dark background, clean infrastructure diagram style",
    "k8s-basics":      "Kubernetes architecture diagram, pods and nodes floating in space, dark background, soft blue and purple tones",
    "polars-confusion": "Abstract data confusion matrix heatmap visualization, colorful grid on dark background, data science aesthetic",
    "polars-kde":      "Kernel density estimation curve, smooth colorful probability distribution on dark background, mathematical beauty",
    "quarto-intro":    "Scientific publishing workflow, Jupyter notebook transforming into a polished document, dark background, clean minimal style",
}


def parse_title(path: Path) -> str:
    text = path.read_text()
    m = re.search(r'^title:\s*["\']?(.*?)["\']?\s*$', text, re.M)
    return m.group(1).strip('"\'') if m else path.parent.name


def generate_image(client: OpenAI, prompt: str) -> bytes:
    response = client.images.generate(
        model="gpt-image-1",
        prompt=f"{prompt}. Wide 16:9 format, high quality, no text.",
        size="1536x1024",
        quality="medium",
        n=1,
    )
    b64 = response.data[0].b64_json
    return base64.b64decode(b64)


def main() -> None:
    import os
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        env = Path.home() / "projects/food/.env"
        for line in env.read_text().splitlines():
            if line.startswith("OPENAI_API_KEY="):
                api_key = line.split("=", 1)[1].strip()
                break
    if not api_key:
        raise SystemExit("OPENAI_API_KEY not found")

    client = OpenAI(api_key=api_key)

    for post_dir in sorted(CONTENT_DIR.iterdir()):
        if not post_dir.is_dir():
            continue
        md = next(post_dir.glob("index*.md"), None)
        if not md:
            continue
        out = post_dir / "featured-image.png"
        slug = post_dir.name
        prompt = PROMPTS.get(slug)
        if not prompt:
            print(f"skip  {slug} (no prompt defined)")
            continue
        title = parse_title(md)
        print(f"gen   {slug}: {title!r} ... ", end="", flush=True)
        try:
            data = generate_image(client, prompt)
            out.write_bytes(data)
            print(f"saved ({len(data)//1024}KB)")
        except Exception as e:
            print(f"ERROR: {e}")
        time.sleep(1)


if __name__ == "__main__":
    main()
