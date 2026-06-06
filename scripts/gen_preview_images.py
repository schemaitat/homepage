"""Generate featured-image.png for each post using gpt-image-1.

Prompts are derived automatically from post front matter (title, tags,
categories, description). Existing images are skipped unless --force is given.

Usage:
    uv run scripts/gen_preview_images.py [--force] [slug ...]
"""

import argparse
import base64
import re
import sys
import threading
from pathlib import Path

from openai import OpenAI

CONTENT_DIR = Path(__file__).parent.parent / "content" / "posts"
IMAGE_NAME = "featured-image.png"

# Per-slug description overrides. Takes precedence over front matter and abstract extraction.
DESCRIPTIONS: dict[str, str] = {
    "argocd": (
        "Kubernetes cluster lifecycle automation on Linode LKE: a root ArgoCD application "
        "syncing child apps (ArgoCD, Prometheus, Airflow) via the app-of-apps Helm pattern, "
        "bash-driven cluster creation and teardown, kubeconfig provisioning, and volume cleanup."
    ),
    "backprop": (
        "Mathematical derivation of neural network backpropagation: layered feed-forward "
        "composition f_N ∘ … ∘ f_1 with weight matrices W, activation vectors a_i, "
        "MSE cost function, Jacobian chain rule, and partial derivatives ∂C/∂W flowing "
        "backwards through the network."
    ),
    "dev-setup": (
        "A reproducible VS Code devcontainer built from a parameterized bash script: "
        "Docker base image, oh-my-zsh with autosuggestions and syntax-highlighting plugins, "
        "tmux, vim, dotfiles injected via URL, resulting in a fully configured terminal "
        "environment inside a container."
    ),
    "hello-world": (
        "A developer's first blog post: the journey from a three-node Kubernetes cluster "
        "to a lean single CentOS VM serving a static site with nginx, certbot TLS, "
        "hugo, and Jenkins — simplicity winning over complexity."
    ),
    "homepage-setup": (
        "End-to-end static blog pipeline: Linode nanonode with SSH keys, firewall rules, "
        "DNS A-record, nginx serving hugo-generated HTML, certbot auto-renewing TLS certs "
        "via cron, and a Jenkins multibranch pipeline triggered by GitHub webhook on every push."
    ),
    "k8s-basics": (
        "Kubernetes fundamentals on Linode LKE: kubectl setup, cluster creation with "
        "kubeconfig, deploying an nginx app via Deployment and Service YAML manifests, "
        "namespace isolation, ClusterIP and NodePort service types, port-forwarding to localhost."
    ),
    "polars-confusion": (
        "A binary classifier threshold optimization pipeline: a wide Polars DataFrame "
        "expanding horizontally with TP, FP, TN, FN confusion columns generated in parallel "
        "for many thresholds, grouped by partition IDs, culminating in a viridis F1-score "
        "heatmap showing the optimal decision threshold per group."
    ),
    "polars-kde": (
        "A Rust-backed Polars plugin for parallelized Kernel Density Estimation: "
        "Silverman bandwidth, Normal kernel, group-by aggregation over millions of rows, "
        "smooth overlapping probability density curves per group, benchmarked far faster "
        "than scipy, with an embedded interactive Marimo notebook."
    ),
    "quarto-intro": (
        "Scientific publishing pipeline: .qmd source files rendered by Quarto through a "
        "Jupyter Python kernel into Hugo-compatible markdown, with live Mermaid diagram "
        "preview in VS Code, and a Jenkins CI/CD stage running quarto render before hugo "
        "build and nginx deployment."
    ),
}

BASE_STYLE = (
    "Style: abstract tech illustration, dark charcoal background (#1a1b1e), "
    "flat design with vibrant saturated accent colors, rich color contrast, "
    "bold geometric shapes, glowing highlights, no text, no UI chrome, "
    "wide 16:9 format, high quality, consistent visual language across a blog series."
)


def parse_frontmatter(path: Path) -> dict:
    text = path.read_text()
    m = re.search(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    block = m.group(1)

    def scalar(pattern: str) -> str:
        hit = re.search(pattern, block, re.M)
        return hit.group(1).strip("\"' ") if hit else ""

    def list_field(pattern: str) -> list[str]:
        # inline: tags: [a, b]
        hit = re.search(pattern + r":\s*\[(.*?)\]", block, re.M)
        if hit:
            return [t.strip().strip("\"'") for t in hit.group(1).split(",") if t.strip()]
        # block:
        #   - item
        hit = re.search(pattern + r":\s*\n((?:\s+-\s+.+\n?)+)", block, re.M)
        if hit:
            return [re.sub(r"^\s*-\s*", "", l).strip().strip("\"'")
                    for l in hit.group(1).splitlines() if l.strip()]
        return []

    # fall back to the first admonition abstract in the post body
    description = scalar(r'^description:\s*(.+)$')
    if not description:
        abstract = re.search(
            r'\{\{<\s*admonition abstract\s*>\}\}(.*?)\{\{<\s*/admonition\s*>\}\}',
            text, re.DOTALL
        )
        if abstract:
            description = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', abstract.group(1))
            description = re.sub(r'\s+', ' ', description).strip()

    return {
        "title":       scalar(r'^title:\s*(.+)$'),
        "description": description,
        "tags":        list_field("tags"),
        "categories":  list_field("categories"),
    }


def build_prompt(slug: str, fm: dict) -> str:
    title = fm.get("title") or slug.replace("-", " ").title()
    tags = fm.get("tags", [])
    categories = fm.get("categories", [])
    description = DESCRIPTIONS.get(slug) or fm.get("description", "")

    keywords = ", ".join(dict.fromkeys(categories + tags))  # deduplicated, ordered

    parts = [BASE_STYLE]
    parts.append(f'Subject: blog post hero image for "{title}".')
    if description:
        parts.append(description.rstrip(".") + ".")
    if keywords:
        parts.append(f"Themes: {keywords}.")
    return " ".join(parts)


def generate_image(client: OpenAI, prompt: str) -> bytes:
    response = client.images.generate(
        model="gpt-image-2",
        prompt=prompt,
        size="1536x1024",
        quality="medium",
        n=1,
    )
    return base64.b64decode(response.data[0].b64_json)


def resolve_api_key() -> str:
    import os
    key = os.environ.get("OPENAI_API_KEY", "")
    if key:
        return key
    fallback = Path.home() / "projects/food/.env"
    if fallback.exists():
        for line in fallback.read_text().splitlines():
            if line.startswith("OPENAI_API_KEY="):
                return line.split("=", 1)[1].strip()
    raise SystemExit("OPENAI_API_KEY not found")


_print_lock = threading.Lock()


def log(msg: str) -> None:
    with _print_lock:
        print(msg, flush=True)


def process_post(client: OpenAI, post_dir: Path, force: bool) -> None:
    md = next(post_dir.glob("index*.md"), None)
    if not md:
        log(f"skip  {post_dir.name} (no index.md)")
        return

    out = post_dir / IMAGE_NAME
    if out.exists() and not force:
        log(f"skip  {post_dir.name} (image exists, use --force to regenerate)")
        return

    fm = parse_frontmatter(md)
    prompt = build_prompt(post_dir.name, fm)
    log(f"gen   {post_dir.name}: {fm.get('title', post_dir.name)!r}")

    try:
        data = generate_image(client, prompt)
        out.write_bytes(data)
        log(f"done  {post_dir.name}: {len(data) // 1024}KB saved")
    except Exception as e:
        log(f"ERROR {post_dir.name}: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--force", action="store_true",
                        help="regenerate even if image already exists")
    parser.add_argument("--workers", type=int, default=4,
                        help="parallel requests (default: 4)")
    parser.add_argument("slugs", nargs="*",
                        help="post slugs to process (default: all)")
    args = parser.parse_args()

    client = OpenAI(api_key=resolve_api_key())

    post_dirs = sorted(
        d for d in CONTENT_DIR.iterdir()
        if d.is_dir() and (not args.slugs or d.name in args.slugs)
    )

    if args.slugs:
        missing = set(args.slugs) - {d.name for d in post_dirs}
        for s in sorted(missing):
            print(f"warn  {s}: directory not found, skipping", file=sys.stderr)

    threads = [
        threading.Thread(target=process_post, args=(client, d, args.force))
        for d in post_dirs
    ]
    # launch in batches to respect --workers limit
    for i in range(0, len(threads), args.workers):
        batch = threads[i:i + args.workers]
        for t in batch:
            t.start()
        for t in batch:
            t.join()


if __name__ == "__main__":
    main()
