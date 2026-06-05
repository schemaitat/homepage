"""Generate featured-image.png for each post that doesn't have one."""

import re
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CONTENT_DIR = Path(__file__).parent.parent / "content" / "posts"
IMG_W, IMG_H = 1200, 630
FONT_TITLE = "/System/Library/Fonts/HelveticaNeue.ttc"
FONT_TAG   = "/System/Library/Fonts/HelveticaNeue.ttc"

# Palette: dark charcoal bg, off-white title, accent per category
CATEGORY_COLORS: dict[str, tuple[int, int, int]] = {
    "mathematics":  (45,  96, 179),
    "data science": (32, 156, 120),
    "data-science": (32, 156, 120),
    "kubernetes":   (65, 132, 196),
    "dev-ops":      (65, 132, 196),
    "tutorial":     (140, 80, 200),
    "python":       (54, 140,  90),
    "default":      (80,  80, 100),
}

BG_DARK   = (26, 27, 30)
BG_LIGHT  = (36, 38, 43)
TEXT_MAIN = (240, 240, 245)
TEXT_SUB  = (160, 165, 180)


def accent_for(tags: list[str], categories: list[str]) -> tuple[int, int, int]:
    for key in categories + tags:
        k = key.lower().replace(" ", "-")
        if k in CATEGORY_COLORS:
            return CATEGORY_COLORS[k]
    return CATEGORY_COLORS["default"]


def parse_frontmatter(path: Path) -> dict:
    text = path.read_text()
    m = re.search(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    fm: dict = {}
    block = m.group(1)
    fm["title"] = re.search(r'^title:\s*["\']?(.*?)["\']?\s*$', block, re.M)
    fm["title"] = fm["title"].group(1).strip('"\'') if fm["title"] else ""
    tags_m = re.search(r'^tags:\s*\[(.*?)\]', block, re.M)
    fm["tags"] = [t.strip().strip('"\'') for t in tags_m.group(1).split(",")] if tags_m else []
    cat_m = re.search(r'^categories:\s*\[(.*?)\]', block, re.M)
    fm["categories"] = [c.strip().strip('"\'') for c in cat_m.group(1).split(",")] if cat_m else []
    return fm


def draw_image(title: str, tags: list[str], accent: tuple[int, int, int]) -> Image.Image:
    img = Image.new("RGB", (IMG_W, IMG_H), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Gradient side stripe
    stripe_w = 8
    for y in range(IMG_H):
        t = y / IMG_H
        r = int(accent[0] * (1 - t * 0.4))
        g = int(accent[1] * (1 - t * 0.4))
        b = int(accent[2] * (1 - t * 0.4))
        draw.rectangle([(0, y), (stripe_w, y)], fill=(r, g, b))

    # Subtle bottom gradient band
    for y in range(IMG_H - 120, IMG_H):
        alpha = (y - (IMG_H - 120)) / 120
        c = int(BG_LIGHT[0] * alpha + BG_DARK[0] * (1 - alpha))
        draw.rectangle([(stripe_w, y), (IMG_W, y)], fill=(c, c, c + 5))

    # Accent dot
    draw.ellipse([(40, IMG_H // 2 - 60), (48, IMG_H // 2 - 52)], fill=accent)

    # Title
    try:
        font_title = ImageFont.truetype(FONT_TITLE, 62, index=1)  # bold index
    except Exception:
        font_title = ImageFont.truetype(FONT_TITLE, 62)
    wrapped = textwrap.wrap(title, width=28)
    y = 200
    for line in wrapped[:3]:
        draw.text((60, y), line, font=font_title, fill=TEXT_MAIN)
        y += 80

    # Tags
    try:
        font_tag = ImageFont.truetype(FONT_TAG, 24)
    except Exception:
        font_tag = ImageFont.load_default()
    x = 60
    ty = IMG_H - 80
    for tag in tags[:5]:
        bbox = draw.textbbox((0, 0), tag, font=font_tag)
        tw = bbox[2] - bbox[0] + 24
        th = bbox[3] - bbox[1] + 12
        draw.rounded_rectangle([(x, ty), (x + tw, ty + th)], radius=4,
                                fill=(*accent, 60), outline=(*accent,))
        draw.text((x + 12, ty + 6), tag, font=font_tag, fill=TEXT_MAIN)
        x += tw + 10
        if x > IMG_W - 100:
            break

    # Site watermark
    try:
        font_wm = ImageFont.truetype(FONT_TAG, 22)
    except Exception:
        font_wm = ImageFont.load_default()
    draw.text((IMG_W - 240, IMG_H - 42), "schemaitat.de", font=font_wm, fill=TEXT_SUB)

    return img


def main() -> None:
    for post_dir in sorted(CONTENT_DIR.iterdir()):
        if not post_dir.is_dir():
            continue
        md = next(post_dir.glob("index*.md"), None)
        if not md:
            continue
        out = post_dir / "featured-image.png"
        if out.exists():
            print(f"skip  {post_dir.name} (already has featured-image.png)")
            continue
        fm = parse_frontmatter(md)
        title = fm.get("title", post_dir.name)
        tags = fm.get("tags", [])
        categories = fm.get("categories", [])
        accent = accent_for(tags, categories)
        img = draw_image(title, tags + categories, accent)
        img.save(out, "PNG", optimize=True)
        print(f"wrote {out.relative_to(CONTENT_DIR.parent.parent)}")


if __name__ == "__main__":
    main()
