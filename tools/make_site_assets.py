#!/usr/bin/python3
"""Draw the icon, the favicon and the social card of the site (needs Pillow).

Run it with `/usr/bin/python3 tools/make_site_assets.py`. The images go
to docs/assets/ and docs/screenshots/ is read for the picture inside the
social card.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "docs" / "assets"
BOLD = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"
REGULAR = "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"
ACCENT = (50, 108, 229)
DARK = (15, 23, 42)


def gradient(size, top, bottom):
    """A vertical gradient."""
    image = Image.new("RGB", size)
    draw = ImageDraw.Draw(image)
    for y in range(size[1]):
        t = y / max(size[1] - 1, 1)
        draw.line(
            [(0, y), (size[0], y)],
            fill=tuple(
                round(a + (b - a) * t) for a, b in zip(top, bottom, strict=True)
            ),
        )
    return image


def rounded(image, radius):
    """The image with rounded corners."""
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [(0, 0), (image.width - 1, image.height - 1)], radius, fill=255
    )
    out = image.convert("RGBA")
    out.putalpha(mask)
    return out


def icon(size=512):
    """A search glass on a blue rounded square."""
    scale = 4
    big = size * scale
    base = rounded(gradient((big, big), (74, 128, 240), (30, 58, 138)), big // 5)
    draw = ImageDraw.Draw(base)
    cx, cy, radius = big * 0.45, big * 0.45, big * 0.24
    width = round(big * 0.07)
    draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        outline="white",
        width=width,
    )
    start = (cx + radius * 0.72, cy + radius * 0.72)
    end = (big * 0.78, big * 0.78)
    draw.line([start, end], fill="white", width=width)
    draw.ellipse(
        [
            end[0] - width / 2,
            end[1] - width / 2,
            end[0] + width / 2,
            end[1] + width / 2,
        ],
        fill="white",
    )
    return base.resize((size, size), Image.LANCZOS)


def social_card():
    """The 1200x630 card shown when the site is shared."""
    card = gradient((1200, 630), DARK, (30, 41, 80)).convert("RGBA")
    draw = ImageDraw.Draw(card)
    draw.text(
        (70, 60), "Spotlight for Linux", font=ImageFont.truetype(BOLD, 74), fill="white"
    )
    draw.text(
        (72, 160),
        "Open apps, find files and do math from one search box.",
        font=ImageFont.truetype(REGULAR, 34),
        fill=(203, 213, 225),
    )
    shot = Image.open(ROOT / "docs" / "screenshots" / "apps.png").convert("RGBA")
    shot = shot.resize(
        (round(shot.width * 1.5), round(shot.height * 1.5)), Image.LANCZOS
    )
    card.alpha_composite(shot, ((1200 - shot.width) // 2, 275))
    draw.text(
        (72, 560),
        "Super+Space · free and open source · installed with one command",
        font=ImageFont.truetype(REGULAR, 28),
        fill=(148, 163, 184),
    )
    card.alpha_composite(icon(96), (1200 - 96 - 60, 54))
    return card.convert("RGB")


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    big = icon(512)
    big.save(ASSETS / "icon.png")
    big.save(ASSETS / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    social_card().save(ASSETS / "og.png", optimize=True)


if __name__ == "__main__":
    main()
