"""Render FanRank's deterministic 1200x630 social preview.

Usage:
    python tools/render_social_card.py

The asset deliberately uses local system fonts and Pillow only. This keeps the
brand text exact and makes the published PNG reproducible without a browser.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "social-card.png"
WIDTH, HEIGHT = 1200, 630
FONT_BLACK = Path(r"C:\Windows\Fonts\ariblk.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\arialbd.ttf")
FONT_REGULAR = Path(r"C:\Windows\Fonts\arial.ttf")


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    if not path.exists():
        raise FileNotFoundError(f"Required font is missing: {path}")
    return ImageFont.truetype(str(path), size)


def mix(start: tuple[int, int, int], end: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return tuple(round(a + (b - a) * amount) for a, b in zip(start, end))


def horizontal_gradient(size: tuple[int, int], stops: list[tuple[float, tuple[int, int, int]]]) -> Image.Image:
    image = Image.new("RGBA", size)
    draw = ImageDraw.Draw(image)
    width, height = size
    for x in range(width):
        point = x / max(width - 1, 1)
        left, right = stops[0], stops[-1]
        for candidate in zip(stops, stops[1:]):
            if candidate[0][0] <= point <= candidate[1][0]:
                left, right = candidate
                break
        span = max(right[0] - left[0], 1e-9)
        color = mix(left[1], right[1], (point - left[0]) / span)
        draw.line((x, 0, x, height), fill=color + (255,))
    return image


def gradient_text(
    canvas: Image.Image,
    position: tuple[int, int],
    text: str,
    face: ImageFont.FreeTypeFont,
    stops: list[tuple[float, tuple[int, int, int]]],
    glow: tuple[int, int, int] | None = None,
) -> None:
    mask = Image.new("L", canvas.size)
    ImageDraw.Draw(mask).text(position, text, font=face, fill=255, stroke_width=1)
    if glow:
        alpha = mask.filter(ImageFilter.GaussianBlur(12)).point(lambda value: value * 0.58)
        layer = Image.new("RGBA", canvas.size, glow + (0,))
        layer.putalpha(alpha)
        canvas.alpha_composite(layer)
    gradient = horizontal_gradient(canvas.size, stops)
    canvas.paste(gradient, (0, 0), mask)


def draw_heart(canvas: Image.Image) -> None:
    heart = Image.new("RGBA", (260, 250))
    points: list[tuple[float, float]] = []
    for step in range(241):
        angle = 2 * math.pi * step / 240
        x = 16 * math.sin(angle) ** 3
        y = 13 * math.cos(angle) - 5 * math.cos(2 * angle) - 2 * math.cos(3 * angle) - math.cos(4 * angle)
        points.append((130 + x * 6.8, 118 - y * 6.8))
    ImageDraw.Draw(heart).polygon(points, fill=(255, 23, 79, 255), outline=(255, 155, 172, 255), width=4)
    highlight = ImageDraw.Draw(heart)
    highlight.arc((65, 44, 150, 116), 205, 300, fill=(255, 255, 255, 205), width=9)
    glow_alpha = heart.getchannel("A").filter(ImageFilter.GaussianBlur(17)).point(lambda value: value * 0.72)
    glow = Image.new("RGBA", heart.size, (255, 23, 79, 0))
    glow.putalpha(glow_alpha)
    glow = glow.rotate(8, resample=Image.Resampling.BICUBIC, expand=True)
    heart = heart.rotate(8, resample=Image.Resampling.BICUBIC, expand=True)
    canvas.alpha_composite(glow, (68, 139))
    canvas.alpha_composite(heart, (68, 139))


def draw_trophy(draw: ImageDraw.ImageDraw) -> None:
    gold = (255, 209, 41, 255)
    light = (255, 244, 168, 255)
    dark = (232, 147, 0, 255)
    draw.rounded_rectangle((1023, 195, 1094, 267), radius=14, fill=gold, outline=light, width=4)
    draw.arc((996, 205, 1048, 270), 78, 282, fill=light, width=10)
    draw.arc((1069, 205, 1121, 270), 258, 102, fill=light, width=10)
    draw.rounded_rectangle((1052, 268, 1065, 309), radius=6, fill=dark)
    draw.rounded_rectangle((1028, 304, 1089, 319), radius=7, fill=gold, outline=light, width=3)


def render() -> None:
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), (10, 11, 18, 255))
    background = horizontal_gradient(
        canvas.size,
        [(0, (9, 10, 17)), (0.54, (17, 20, 38)), (1, (23, 15, 36))],
    )
    canvas.alpha_composite(background)

    glows = Image.new("RGBA", canvas.size)
    glow_draw = ImageDraw.Draw(glows)
    glow_draw.ellipse((-230, -260, 700, 610), fill=(255, 209, 41, 42))
    glow_draw.ellipse((650, -180, 1450, 620), fill=(99, 179, 255, 48))
    glows = glows.filter(ImageFilter.GaussianBlur(86))
    canvas.alpha_composite(glows)

    draw = ImageDraw.Draw(canvas)
    for x in range(0, WIDTH, 34):
        draw.line((x, 0, x, HEIGHT), fill=(255, 255, 255, 9))
    for y in range(0, HEIGHT, 34):
        draw.line((0, y, WIDTH, y), fill=(255, 255, 255, 9))
    draw.rounded_rectangle((28, 28, 1172, 602), radius=32, outline=(255, 255, 255, 23), width=2)

    draw.rounded_rectangle((79, 74, 407, 120), radius=23, fill=(255, 255, 255, 18), outline=(255, 255, 255, 31))
    draw.ellipse((98, 91, 110, 103), fill=(85, 229, 154, 255))
    draw.text((123, 87), "IDEAS QUE MERECEN SUBIR", font=font(FONT_BOLD, 18), fill=(220, 230, 250, 255))

    draw_heart(canvas)
    fan_font = font(FONT_BLACK, 150)
    rank_font = font(FONT_BLACK, 139)
    gradient_text(
        canvas,
        (180, 185),
        "FAN",
        fan_font,
        [(0, (255, 248, 181)), (0.5, (255, 209, 41)), (1, (255, 173, 18))],
    )

    # The podium lives behind R-A-N, making the ranking meaning readable even
    # without explanatory copy.
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((532, 338, 620, 385), radius=11, fill=(203, 211, 227, 255))
    draw.rounded_rectangle((656, 302, 744, 385), radius=11, fill=(255, 209, 41, 255))
    draw.rounded_rectangle((780, 352, 868, 385), radius=10, fill=(223, 159, 105, 255))
    number_font = font(FONT_BOLD, 23)
    draw.text((566, 348), "2", font=number_font, fill=(16, 19, 29, 255))
    draw.text((690, 312), "1", font=number_font, fill=(33, 25, 0, 255))
    draw.text((814, 356), "3", font=font(FONT_BOLD, 20), fill=(31, 18, 11, 255))

    rank_stops = [(0, (183, 226, 255)), (0.48, (99, 179, 255)), (1, (211, 140, 255))]
    for position, letter in [((506, 190), "R"), ((630, 154), "A"), ((754, 204), "N"), ((884, 192), "K")]:
        gradient_text(canvas, position, letter, rank_font, rank_stops, glow=(99, 179, 255))

    draw = ImageDraw.Draw(canvas)
    draw_trophy(draw)
    draw.text((80, 432), "Las mejores ideas, ordenadas.", font=font(FONT_BOLD, 46), fill=(245, 247, 251, 255))
    draw.text(
        (82, 489),
        "Sugiere en segundos. Los fans votan. La IA encuentra lo más útil.",
        font=font(FONT_REGULAR, 25),
        fill=(170, 178, 198, 255),
    )
    draw.rounded_rectangle((80, 544, 404, 598), radius=27, fill=(255, 209, 41, 255))
    cta = "SUGIERE  ·  VOTA  ·  MEJORA"
    cta_font = font(FONT_BOLD, 18)
    cta_box = draw.textbbox((0, 0), cta, font=cta_font)
    draw.text((242 - (cta_box[2] - cta_box[0]) / 2, 562), cta, font=cta_font, fill=(33, 25, 0, 255))
    draw.text((1035, 558), "fanrank", font=font(FONT_BOLD, 19), fill=(148, 163, 189, 255))

    canvas.convert("RGB").save(OUTPUT, format="PNG", optimize=True)
    with Image.open(OUTPUT) as rendered:
        print(f"SOCIAL_CARD={rendered.width}x{rendered.height} bytes={OUTPUT.stat().st_size}")


if __name__ == "__main__":
    render()
