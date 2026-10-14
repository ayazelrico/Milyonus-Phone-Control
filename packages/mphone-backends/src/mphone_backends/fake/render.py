"""Draw a fake screen so screenshots look like something (and OCR tests have input)."""

import io
from typing import Any

from PIL import Image, ImageDraw, ImageFont

# Pillow's built-in font has no ı/ğ/ş/İ glyphs, which turns Turkish into boxes in screenshots
# and makes them useless as OCR input. Prefer a system font that covers Turkish.
FONT_CANDIDATES = (
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arial.ttf",
)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def render_png(
    w: int,
    h: int,
    elements: list[dict[str, Any]],
    fmt: str = "png",
    quality: int = 85,
    max_side: int | None = None,
) -> tuple[bytes, int, int]:
    image = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(image)
    font = _font(max(18, h // 60))
    for el in elements:
        ew, eh = int(el.get("w", 200)), int(el.get("h", 60))
        left, top = int(el["x"]) - ew // 2, int(el["y"]) - eh // 2
        outline = (
            "#2563eb" if el.get("editable") else ("#9ca3af" if el.get("clickable") or el.get("row") else None)
        )
        if outline:
            draw.rectangle((left, top, left + ew, top + eh), outline=outline, width=2)
        text = str(el.get("text", ""))
        draw.text((left + 12, top + eh // 2), text, fill="black", font=font, anchor="lm")
    if max_side and max(w, h) > max_side:
        ratio = max_side / max(w, h)
        image = image.resize((max(1, round(w * ratio)), max(1, round(h * ratio))))
    buf = io.BytesIO()
    if fmt == "jpeg":
        image.save(buf, format="JPEG", quality=quality)
    else:
        image.save(buf, format="PNG")
    return buf.getvalue(), image.width, image.height
