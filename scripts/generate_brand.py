"""Generate the NMAxe brand icon and logo assets."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Final

import cairosvg
from PIL import Image, ImageDraw, ImageFont

ROOT: Final = Path(__file__).resolve().parents[1]
OUTPUT_DIR: Final = ROOT / "custom_components" / "nmaxe" / "brand"

SCALE: Final = 4

ICON_SIZE: Final = 256
ICON_PADDING: Final = 10
ICON_RADIUS: Final = 54
ICON_BORDER_WIDTH: Final = 3
ICON_BG: Final = "#0f1724"
ICON_BORDER: Final = "#2a3850"
ICON_ACCENT: Final = "#f59e0b"
ICON_GLYPH_RATIO: Final = 0.61
ICON_GLYPH_OFFSET: Final[tuple[float, float]] = (0.0, 0.0)

LOGO_SIZE: Final = (512, 256)
LOGO_ICON_SIZE: Final = 184
LOGO_ICON_X: Final = 28
LOGO_TEXT_X: Final = 232
LOGO_RIGHT_PADDING: Final = 28
LOGO_TITLE: Final = "NMAxe"
LOGO_SUBTITLE: Final = "Home Assistant"
LOGO_TITLE_SIZE: Final = 64
LOGO_TITLE_MIN_SIZE: Final = 40
LOGO_SUBTITLE_SIZE: Final = 22
LOGO_SUBTITLE_MIN_SIZE: Final = 14
LOGO_TEXT_GAP: Final = 7
LOGO_TITLE_COLOR_LIGHT: Final = "#0f1724"
LOGO_SUBTITLE_COLOR_LIGHT: Final = "#475569"
LOGO_TITLE_COLOR_DARK: Final = "#f2f4f8"
LOGO_SUBTITLE_COLOR_DARK: Final = "#94a3b8"

FONT_BOLD_CANDIDATES: Final = (
    Path("/usr/share/fonts/truetype/lato/Lato-Bold.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
)
FONT_MEDIUM_CANDIDATES: Final = (
    Path("/usr/share/fonts/truetype/lato/Lato-Medium.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
)

PICKAXE_PATH: Final = (
    "M14.79,10.62L3.5,21.9L2.1,20.5L13.38,9.21L14.79,10.62"
    "M19.27,7.73L19.86,7.14L19.07,6.35L19.71,5.71L18.29,4.29"
    "L17.65,4.93L16.86,4.14L16.27,4.73C14.53,3.31 12.57,2.17"
    " 10.47,1.37L9.64,3.16C11.39,4.08 13,5.19 14.5,6.5L14,7"
    "L17,10L17.5,9.5C18.81,11 19.92,12.61 20.84,14.36L22.63,13.53"
    "C21.83,11.43 20.69,9.47 19.27,7.73Z"
)


def _font_path(candidates: tuple[Path, ...]) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    msg = f"No usable font found in {candidates}"
    raise FileNotFoundError(msg)


def _font(size: int, *, bold: bool) -> ImageFont.FreeTypeFont:
    candidates = FONT_BOLD_CANDIDATES if bold else FONT_MEDIUM_CANDIDATES
    return ImageFont.truetype(str(_font_path(candidates)), size)


def _fit_font(
    text: str,
    max_width: int,
    preferred_size: int,
    minimum_size: int,
    *,
    bold: bool,
) -> ImageFont.FreeTypeFont:
    for size in range(preferred_size, minimum_size - 1, -1):
        font = _font(size, bold=bold)
        if font.getlength(text) <= max_width:
            return font
    return _font(minimum_size, bold=bold)


def _pickaxe(size: int) -> Image.Image:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        f'<path fill="{ICON_ACCENT}" d="{PICKAXE_PATH}"/></svg>'
    )
    png = cairosvg.svg2png(
        bytestring=svg.encode(),
        output_width=size,
        output_height=size,
    )
    glyph = Image.open(BytesIO(png)).convert("RGBA")
    alpha_box = glyph.getchannel("A").getbbox()
    return glyph.crop(alpha_box) if alpha_box else glyph


def _render_icon(size: int) -> Image.Image:
    padding = ICON_PADDING * SCALE
    border_width = ICON_BORDER_WIDTH * SCALE
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (padding, padding, size - padding, size - padding),
        radius=ICON_RADIUS * SCALE,
        fill=ICON_BG,
        outline=ICON_BORDER,
        width=border_width,
    )

    glyph = _pickaxe(round(size * ICON_GLYPH_RATIO))
    offset_x = round(ICON_GLYPH_OFFSET[0] * SCALE)
    offset_y = round(ICON_GLYPH_OFFSET[1] * SCALE)
    image.alpha_composite(
        glyph,
        (
            (size - glyph.width) // 2 + offset_x,
            (size - glyph.height) // 2 + offset_y,
        ),
    )
    return image


def _resize(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    return image.convert("RGBa").resize(size, Image.Resampling.LANCZOS).convert("RGBA")


def _draw_icon(size: int) -> Image.Image:
    return _resize(_render_icon(size * SCALE), (size, size))


def _draw_logo(width: int, height: int, *, dark: bool) -> Image.Image:
    scale = SCALE
    canvas = Image.new("RGBA", (width * scale, height * scale), (0, 0, 0, 0))
    icon = _render_icon(LOGO_ICON_SIZE * scale)
    canvas.alpha_composite(
        icon,
        (
            LOGO_ICON_X * scale,
            ((height - LOGO_ICON_SIZE) // 2) * scale,
        ),
    )

    draw = ImageDraw.Draw(canvas)
    available_width = (width - LOGO_TEXT_X - LOGO_RIGHT_PADDING) * scale
    title_font = _fit_font(
        LOGO_TITLE,
        available_width,
        LOGO_TITLE_SIZE * scale,
        LOGO_TITLE_MIN_SIZE * scale,
        bold=True,
    )
    subtitle_font = _fit_font(
        LOGO_SUBTITLE,
        available_width,
        LOGO_SUBTITLE_SIZE * scale,
        LOGO_SUBTITLE_MIN_SIZE * scale,
        bold=False,
    )
    title_color = LOGO_TITLE_COLOR_DARK if dark else LOGO_TITLE_COLOR_LIGHT
    subtitle_color = LOGO_SUBTITLE_COLOR_DARK if dark else LOGO_SUBTITLE_COLOR_LIGHT

    title_box = draw.textbbox((0, 0), LOGO_TITLE, font=title_font)
    subtitle_box = draw.textbbox((0, 0), LOGO_SUBTITLE, font=subtitle_font)
    title_height = title_box[3] - title_box[1]
    subtitle_height = subtitle_box[3] - subtitle_box[1]
    gap = LOGO_TEXT_GAP * scale
    block_height = title_height + gap + subtitle_height
    top = (height * scale - block_height) // 2
    text_x = LOGO_TEXT_X * scale

    draw.text(
        (text_x, top - title_box[1]),
        LOGO_TITLE,
        font=title_font,
        fill=title_color,
    )
    draw.text(
        (text_x, top + title_height + gap - subtitle_box[1]),
        LOGO_SUBTITLE,
        font=subtitle_font,
        fill=subtitle_color,
    )

    return _resize(canvas, (width, height))


def main() -> None:
    """Write all brand assets and print the final layout measurements."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    _draw_icon(ICON_SIZE).save(OUTPUT_DIR / "icon.png", optimize=True)
    _draw_icon(ICON_SIZE * 2).save(OUTPUT_DIR / "icon@2x.png", optimize=True)
    _draw_logo(*LOGO_SIZE, dark=False).save(
        OUTPUT_DIR / "logo.png",
        optimize=True,
    )
    _draw_logo(LOGO_SIZE[0] * 2, LOGO_SIZE[1] * 2, dark=False).save(
        OUTPUT_DIR / "logo@2x.png",
        optimize=True,
    )
    _draw_logo(*LOGO_SIZE, dark=True).save(
        OUTPUT_DIR / "dark_logo.png",
        optimize=True,
    )
    _draw_logo(LOGO_SIZE[0] * 2, LOGO_SIZE[1] * 2, dark=True).save(
        OUTPUT_DIR / "dark_logo@2x.png",
        optimize=True,
    )

    title_font = _fit_font(
        LOGO_TITLE,
        LOGO_SIZE[0] - LOGO_TEXT_X - LOGO_RIGHT_PADDING,
        LOGO_TITLE_SIZE,
        LOGO_TITLE_MIN_SIZE,
        bold=True,
    )
    subtitle_font = _fit_font(
        LOGO_SUBTITLE,
        LOGO_SIZE[0] - LOGO_TEXT_X - LOGO_RIGHT_PADDING,
        LOGO_SUBTITLE_SIZE,
        LOGO_SUBTITLE_MIN_SIZE,
        bold=False,
    )
    print(f"icon: {ICON_SIZE}x{ICON_SIZE}")
    print(f"logo: {LOGO_SIZE[0]}x{LOGO_SIZE[1]}")
    print(
        "title:"
        f" x={LOGO_TEXT_X}"
        f" font={title_font.size}"
        f" width={title_font.getlength(LOGO_TITLE):.1f}"
    )
    print(
        "subtitle:"
        f" x={LOGO_TEXT_X}"
        f" font={subtitle_font.size}"
        f" width={subtitle_font.getlength(LOGO_SUBTITLE):.1f}"
    )


if __name__ == "__main__":
    main()
