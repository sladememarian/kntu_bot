"""
Pixel Art Rendering Engine for Telegram Bot.
Provides reusable functions for drawing charming 8-bit/16-bit retro pixel art using Pillow.
"""

import io
import hashlib
import math
import random
from PIL import Image, ImageDraw, ImageFont

# ── Catppuccin Mocha Palette ──────────────────────────────────────────────
BG = (24, 24, 37)
SURFACE = (30, 30, 46)
OVERLAY = (49, 50, 68)
TEXT_COLOR = (205, 214, 244)
RED = (243, 139, 168)
GREEN = (166, 227, 161)
BLUE = (137, 180, 250)
YELLOW = (249, 226, 175)
PINK = (245, 194, 231)
PURPLE = (203, 166, 247)
TEAL = (148, 226, 213)
ORANGE = (250, 179, 135)
GOLD = (249, 226, 175)
WHITE = (205, 214, 244)
DARK = (17, 17, 27)
SHADOW = (24, 24, 37)

_FONT_PATHS = [
    "C:/Windows/Fonts/consola.ttf",
    "C:/Windows/Fonts/cour.ttf",
    "C:/Windows/Fonts/lucon.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
]

_font_cache: dict[tuple, ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}


def _get_font(size: int = 12) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if size in _font_cache:
        return _font_cache[size]
    for path in _FONT_PATHS:
        try:
            font = ImageFont.truetype(path, size)
            _font_cache[size] = font
            return font
        except (OSError, IOError):
            continue
    font = ImageFont.load_default()
    _font_cache[size] = font
    return font


def _name_hash(name: str) -> int:
    return int(hashlib.md5(name.encode("utf-8")).hexdigest(), 16)


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def _blend(c1: tuple, c2: tuple, t: float) -> tuple:
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def _darker(c: tuple, factor: float = 0.6) -> tuple:
    return tuple(_clamp(int(v * factor), 0, 255) for v in c)


def _lighter(c: tuple, factor: float = 1.4) -> tuple:
    return tuple(_clamp(int(v * factor), 0, 255) for v in c)


# ── Core Drawing Functions ────────────────────────────────────────────────


def pixel_text(draw: ImageDraw.ImageDraw, x: int, y: int, text: str,
               color: tuple = TEXT_COLOR, scale: int = 2) -> None:
    """Draw pixel-style text with a blocky shadow."""
    font = _get_font(10 * scale)
    # Shadow
    draw.text((x + scale, y + scale), text, font=font, fill=_darker(color, 0.3))
    draw.text((x, y), text, font=font, fill=color)


def pixel_box(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int,
              fill: tuple, border: tuple, border_w: int = 2) -> None:
    """Draw a pixel-art styled box with dithered borders."""
    # Fill
    draw.rectangle([x, y, x + w, y + h], fill=fill)
    # Dithered border
    for i in range(border_w):
        draw.rectangle([x + i, y + i, x + w - i, y + h - i], outline=border)
    # Dither dots on the border region
    for bx in range(x, x + w + 1, 4):
        for by in range(y, y + h + 1, 4):
            if (bx + by) % 8 < 4:
                if (bx <= x + border_w or bx >= x + w - border_w or
                        by <= y + border_w or by >= y + h - border_w):
                    draw.point((bx, by), fill=_lighter(border))
    # Highlight top-left edge
    draw.line([x + border_w, y + border_w, x + w - border_w, y + border_w],
              fill=_lighter(fill, 1.3))
    draw.line([x + border_w, y + border_w, x + border_w, y + h - border_w],
              fill=_lighter(fill, 1.2))
    # Shadow bottom-right edge
    draw.line([x + border_w, y + h - border_w, x + w - border_w, y + h - border_w],
              fill=_darker(fill, 0.7))
    draw.line([x + w - border_w, y + border_w, x + w - border_w, y + h - border_w],
              fill=_darker(fill, 0.7))


def pixel_avatar(draw: ImageDraw.ImageDraw, x: int, y: int, size: int,
                 name: str, color: tuple) -> None:
    """Draw a pixel-art character avatar – a cute face with deterministic features."""
    h = _name_hash(name)
    s = size // 8  # pixel unit

    # Head
    draw.rectangle([x + s, y, x + size - s, y + size], fill=color)
    draw.rectangle([x, y + s, x + size, y + size - s], fill=color)

    # Eyes
    eye_style = h % 4
    el_x, er_x = x + 2 * s, x + 5 * s
    ey = y + 3 * s
    eye_c = DARK
    if eye_style == 0:  # dot eyes
        draw.rectangle([el_x, ey, el_x + s, ey + s], fill=eye_c)
        draw.rectangle([er_x, ey, er_x + s, ey + s], fill=eye_c)
    elif eye_style == 1:  # wide eyes
        draw.rectangle([el_x, ey, el_x + s, ey + s * 2], fill=eye_c)
        draw.rectangle([er_x, ey, er_x + s, ey + s * 2], fill=eye_c)
        draw.point((el_x, ey), fill=WHITE)
        draw.point((er_x, ey), fill=WHITE)
    elif eye_style == 2:  # line eyes
        draw.line([el_x, ey + s // 2, el_x + s, ey + s // 2], fill=eye_c, width=max(1, s // 2))
        draw.line([er_x, ey + s // 2, er_x + s, ey + s // 2], fill=eye_c, width=max(1, s // 2))
    else:  # x eyes
        draw.line([el_x, ey, el_x + s, ey + s], fill=eye_c, width=1)
        draw.line([el_x + s, ey, el_x, ey + s], fill=eye_c, width=1)
        draw.line([er_x, ey, er_x + s, ey + s], fill=eye_c, width=1)
        draw.line([er_x + s, ey, er_x, ey + s], fill=eye_c, width=1)

    # Mouth
    mouth_style = (h >> 4) % 4
    my = y + 5 * s
    mx = x + 3 * s
    if mouth_style == 0:  # smile
        draw.line([mx, my, mx + s * 2, my], fill=eye_c, width=max(1, s // 2))
        draw.point((mx, my - 1), fill=eye_c)
        draw.point((mx + s * 2, my - 1), fill=eye_c)
    elif mouth_style == 1:  # open mouth
        draw.rectangle([mx, my, mx + s * 2, my + s], fill=eye_c)
        draw.rectangle([mx + s // 2, my, mx + s * 2 - s // 2, my + s // 2], fill=RED)
    elif mouth_style == 2:  # flat
        draw.line([mx, my, mx + s * 2, my], fill=eye_c, width=max(1, s // 2))
    else:  # cat mouth
        draw.line([mx + s, my, mx, my + s // 2], fill=eye_c, width=1)
        draw.line([mx + s, my, mx + s * 2, my + s // 2], fill=eye_c, width=1)

    # Cheek blush
    if (h >> 8) % 2:
        blush = _blend(color, PINK, 0.5)
        draw.rectangle([x + s, y + 4 * s, x + 2 * s, y + 5 * s], fill=blush)
        draw.rectangle([x + 6 * s, y + 4 * s, x + 7 * s, y + 5 * s], fill=blush)

    # Hair / accessory
    hair_style = (h >> 12) % 3
    hair_c = _darker(color, 0.5)
    if hair_style == 0:
        draw.rectangle([x + s, y - s, x + size - s, y + s // 2], fill=hair_c)
    elif hair_style == 1:
        draw.rectangle([x, y - s, x + size, y], fill=hair_c)
        draw.rectangle([x + s, y - 2 * s, x + size - s, y - s + 1], fill=hair_c)
    else:
        for i in range(0, size, s * 2):
            draw.rectangle([x + i, y - s, x + i + s, y], fill=hair_c)


def pixel_coins(draw: ImageDraw.ImageDraw, x: int, y: int, amount: int) -> None:
    """Draw pixel gold coins with the amount shown beside them."""
    # Stack of coins
    for i in range(min(3, max(1, amount // 100 + 1))):
        cx = x + i * 3
        cy = y - i * 4
        # Coin body
        draw.rectangle([cx + 2, cy, cx + 10, cy + 12], fill=GOLD)
        draw.rectangle([cx, cy + 2, cx + 12, cy + 10], fill=GOLD)
        # Coin shine
        draw.rectangle([cx + 2, cy + 2, cx + 4, cy + 4], fill=_lighter(GOLD))
        # Coin shadow
        draw.rectangle([cx + 8, cy + 8, cx + 10, cy + 10], fill=_darker(GOLD, 0.7))
        # $ sign
        draw.line([cx + 6, cy + 3, cx + 6, cy + 9], fill=_darker(GOLD, 0.5), width=1)
        draw.line([cx + 4, cy + 4, cx + 8, cy + 4], fill=_darker(GOLD, 0.5), width=1)
        draw.line([cx + 4, cy + 8, cx + 8, cy + 8], fill=_darker(GOLD, 0.5), width=1)

    # Amount text
    pixel_text(draw, x + 20, y - 2, str(amount), GOLD, scale=1)


def pixel_heart(draw: ImageDraw.ImageDraw, x: int, y: int, size: int,
                color: tuple = RED) -> None:
    """Draw a pixel heart shape."""
    s = max(1, size // 8)
    # Heart pattern (8x7 grid)
    pattern = [
        "  ##  ##  ",
        " ######## ",
        "##########",
        "##########",
        " ######## ",
        "  ######  ",
        "   ####   ",
        "    ##    ",
    ]
    for row, line in enumerate(pattern):
        for col, ch in enumerate(line):
            if ch == '#':
                px = x + col * s
                py = y + row * s
                draw.rectangle([px, py, px + s - 1, py + s - 1], fill=color)
    # Shine
    draw.rectangle([x + 2 * s, y + s, x + 3 * s - 1, y + 2 * s - 1],
                    fill=_lighter(color))


def pixel_star(draw: ImageDraw.ImageDraw, x: int, y: int, size: int,
               color: tuple = YELLOW) -> None:
    """Draw a pixel star shape."""
    s = max(1, size // 8)
    pattern = [
        "    ##    ",
        "   ####   ",
        "##########",
        " ######## ",
        "  ######  ",
        " ## ## ## ",
        "##  ##  ##",
        "#   ##   #",
    ]
    for row, line in enumerate(pattern):
        for col, ch in enumerate(line):
            if ch == '#':
                px = x + col * s
                py = y + row * s
                draw.rectangle([px, py, px + s - 1, py + s - 1], fill=color)
    # Center glow
    cx, cy = x + 4 * s, y + 3 * s
    draw.rectangle([cx, cy, cx + s, cy + s], fill=_lighter(color))


def _draw_building_base(draw: ImageDraw.ImageDraw, x: int, y: int,
                        wall: tuple, roof: tuple, door: tuple) -> None:
    """Shared building structure: roof, walls, door."""
    # Shadow
    draw.rectangle([x + 4, y + 4, x + 83, y + 83], fill=DARK)
    # Walls
    draw.rectangle([x + 5, y + 20, x + 75, y + 78], fill=wall)
    # Roof
    points = [(x + 0, y + 22), (x + 40, y + 2), (x + 80, y + 22)]
    draw.polygon(points, fill=roof)
    draw.line([(x + 0, y + 22), (x + 40, y + 2), (x + 80, y + 22)],
              fill=_darker(roof, 0.6), width=2)
    # Door
    draw.rectangle([x + 30, y + 55, x + 50, y + 78], fill=door)
    draw.rectangle([x + 31, y + 56, x + 49, y + 77], fill=_lighter(door, 1.2))
    # Door knob
    draw.rectangle([x + 46, y + 66, x + 48, y + 68], fill=GOLD)
    # Foundation
    draw.rectangle([x + 3, y + 76, x + 77, y + 80], fill=_darker(wall, 0.5))


def _building_bank(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    _draw_building_base(draw, x, y, wall=OVERLAY, roof=BLUE, door=(60, 60, 80))
    # Columns
    for cx in (x + 12, x + 24, x + 56, x + 68):
        draw.rectangle([cx, y + 24, cx + 4, y + 76], fill=WHITE)
        draw.rectangle([cx - 1, y + 24, cx + 5, y + 27], fill=WHITE)
        draw.rectangle([cx - 1, y + 73, cx + 5, y + 76], fill=WHITE)
    # Triangular pediment
    draw.polygon([(x + 8, y + 22), (x + 40, y + 8), (x + 72, y + 22)],
                 fill=_lighter(BLUE, 1.1))
    draw.line([(x + 8, y + 22), (x + 40, y + 8), (x + 72, y + 22)],
              fill=_darker(BLUE, 0.5), width=2)
    # $ symbol on pediment
    font = _get_font(14)
    draw.text((x + 35, y + 10), "$", font=font, fill=GOLD)
    # Window decorations
    for wx in (x + 14, x + 58):
        draw.rectangle([wx, y + 34, wx + 8, y + 44], fill=SURFACE)
        draw.rectangle([wx, y + 34, wx + 8, y + 35], fill=_lighter(OVERLAY))


def _building_casino(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    _draw_building_base(draw, x, y, wall=PURPLE, roof=PINK, door=OVERLAY)
    # Flashy lights along roofline
    colors = [RED, YELLOW, GREEN, BLUE, PINK, ORANGE]
    for i, lx in enumerate(range(x + 6, x + 76, 8)):
        c = colors[i % len(colors)]
        draw.rectangle([lx, y + 20, lx + 4, y + 24], fill=c)
        draw.rectangle([lx + 1, y + 21, lx + 3, y + 23], fill=_lighter(c))
    # "777" or dice
    font = _get_font(10)
    draw.text((x + 18, y + 28), "777", font=font, fill=GOLD)
    # Dice on side
    draw.rectangle([x + 14, y + 42, x + 26, y + 54], fill=WHITE)
    draw.rectangle([x + 15, y + 43, x + 25, y + 53], fill=(240, 240, 240))
    for dp in [(x + 17, y + 45), (x + 22, y + 48), (x + 17, y + 51),
               (x + 22, y + 45), (x + 22, y + 51)]:
        draw.rectangle([dp[0], dp[1], dp[0] + 1, dp[1] + 1], fill=DARK)
    # Card symbol
    draw.rectangle([x + 56, y + 42, x + 66, y + 54], fill=WHITE)
    font_sm = _get_font(10)
    draw.text((x + 58, y + 42), "A", font=font_sm, fill=RED)
    # Neon border
    draw.rectangle([x + 5, y + 20, x + 75, y + 22], fill=YELLOW)


def _building_bar(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    _draw_building_base(draw, x, y, wall=(80, 50, 30), roof=(60, 35, 20),
                        door=(50, 30, 15))
    # Sign board
    draw.rectangle([x + 15, y + 26, x + 65, y + 40], fill=OVERLAY)
    draw.rectangle([x + 16, y + 27, x + 64, y + 39], fill=SURFACE)
    font = _get_font(10)
    draw.text((x + 22, y + 28), "BAR", font=font, fill=ORANGE)
    # Beer mug
    mug_x, mug_y = x + 56, y + 44
    draw.rectangle([mug_x, mug_y, mug_x + 12, mug_y + 14], fill=YELLOW)
    draw.rectangle([mug_x + 1, mug_y + 1, mug_x + 11, mug_y + 13],
                    fill=_lighter(YELLOW))
    # Beer color
    draw.rectangle([mug_x + 2, mug_y + 3, mug_x + 10, mug_y + 12],
                    fill=ORANGE)
    # Foam
    draw.rectangle([mug_x + 1, mug_y + 1, mug_x + 11, mug_y + 4], fill=WHITE)
    # Handle
    draw.rectangle([mug_x + 12, mug_y + 3, mug_x + 15, mug_y + 10],
                    fill=YELLOW)
    draw.rectangle([mug_x + 12, mug_y + 5, mug_x + 14, mug_y + 8],
                    fill=(80, 50, 30))
    # Window with warm glow
    draw.rectangle([x + 12, y + 44, x + 26, y + 54], fill=(100, 70, 30))
    draw.rectangle([x + 13, y + 45, x + 25, y + 53], fill=ORANGE)


def _building_shop(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    _draw_building_base(draw, x, y, wall=(200, 180, 160), roof=GREEN,
                        door=(120, 90, 60))
    # Awning (striped)
    for i in range(0, 70, 10):
        c = RED if (i // 10) % 2 == 0 else WHITE
        draw.rectangle([x + 5 + i, y + 20, x + 14 + i, y + 30], fill=c)
    # Scalloped bottom edge of awning
    for sx in range(x + 5, x + 76, 5):
        draw.polygon([(sx, y + 30), (sx + 2, y + 34), (sx + 5, y + 30)],
                     fill=RED if ((sx - x) // 5) % 2 == 0 else WHITE)
    # Display window
    draw.rectangle([x + 10, y + 36, x + 28, y + 54], fill=TEAL)
    draw.rectangle([x + 11, y + 37, x + 27, y + 53], fill=_lighter(TEAL))
    draw.rectangle([x + 52, y + 36, x + 70, y + 54], fill=TEAL)
    draw.rectangle([x + 53, y + 37, x + 69, y + 53], fill=_lighter(TEAL))
    # Items in windows
    draw.rectangle([x + 15, y + 44, x + 22, y + 52], fill=YELLOW)
    draw.rectangle([x + 57, y + 44, x + 64, y + 52], fill=PINK)
    # "SHOP" sign
    font = _get_font(8)
    draw.text((x + 28, y + 8), "SHOP", font=font, fill=WHITE)


def _building_jail(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    # Stone walls (no standard base, custom)
    draw.rectangle([x + 4, y + 4, x + 83, y + 83], fill=DARK)
    draw.rectangle([x + 2, y + 10, x + 78, y + 78], fill=(80, 80, 90))
    # Stone texture
    for sy in range(y + 10, y + 78, 8):
        offset = 4 if ((sy - y) // 8) % 2 else 0
        for sx in range(x + 2 + offset, x + 78, 16):
            draw.rectangle([sx, sy, sx + 14, sy + 6], outline=(60, 60, 70))
    # Flat roof
    draw.rectangle([x, y + 8, x + 80, y + 14], fill=(60, 60, 70))
    draw.rectangle([x + 2, y + 10, x + 78, y + 13], fill=(70, 70, 80))
    # Barred windows
    for wx in (x + 10, x + 34, x + 58):
        draw.rectangle([wx, y + 24, wx + 16, y + 44], fill=DARK)
        for bx in range(wx + 2, wx + 16, 4):
            draw.line([bx, y + 24, bx, y + 44], fill=(140, 140, 150), width=2)
        draw.line([wx, y + 34, wx + 16, y + 34], fill=(140, 140, 150), width=1)
    # Heavy door
    draw.rectangle([x + 28, y + 52, x + 52, y + 78], fill=(50, 50, 55))
    draw.rectangle([x + 30, y + 54, x + 50, y + 76], fill=(60, 60, 65))
    # Door rivets
    for rx, ry in [(x + 33, y + 58), (x + 47, y + 58),
                   (x + 33, y + 72), (x + 47, y + 72)]:
        draw.rectangle([rx, ry, rx + 2, ry + 2], fill=(120, 120, 130))
    # Lock
    draw.rectangle([x + 38, y + 64, x + 42, y + 68], fill=GOLD)
    # Foundation
    draw.rectangle([x, y + 76, x + 80, y + 80], fill=(50, 50, 55))


def _building_police(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    _draw_building_base(draw, x, y, wall=BLUE, roof=_darker(BLUE, 0.7),
                        door=OVERLAY)
    # Badge / star on front
    star_x, star_y = x + 33, y + 28
    # Simple 5-pointed pixel star badge
    draw.rectangle([star_x + 2, star_y, star_x + 10, star_y + 2], fill=GOLD)
    draw.rectangle([star_x, star_y + 2, star_x + 12, star_y + 8], fill=GOLD)
    draw.rectangle([star_x + 2, star_y + 8, star_x + 10, star_y + 12], fill=GOLD)
    draw.rectangle([star_x + 4, star_y + 12, star_x + 8, star_y + 14], fill=GOLD)
    # Inner detail
    draw.rectangle([star_x + 4, star_y + 4, star_x + 8, star_y + 8],
                    fill=_darker(GOLD, 0.7))
    # Blue light on roof
    draw.rectangle([x + 35, y + 4, x + 45, y + 10], fill=(40, 40, 80))
    draw.rectangle([x + 36, y + 5, x + 39, y + 9], fill=RED)
    draw.rectangle([x + 41, y + 5, x + 44, y + 9], fill=BLUE)
    # Windows
    for wx in (x + 12, x + 60):
        draw.rectangle([wx, y + 38, wx + 12, y + 50], fill=SURFACE)
        draw.line([wx + 6, y + 38, wx + 6, y + 50], fill=_darker(BLUE, 0.6))
        draw.line([wx, y + 44, wx + 12, y + 44], fill=_darker(BLUE, 0.6))
    # "POLICE" label
    font = _get_font(7)
    draw.text((x + 16, y + 22), "POLICE", font=font, fill=WHITE)


def _building_restaurant(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    _draw_building_base(draw, x, y, wall=(180, 80, 70), roof=RED,
                        door=(100, 40, 30))
    # Warm windows
    for wx in (x + 10, x + 56):
        draw.rectangle([wx, y + 34, wx + 16, y + 50], fill=YELLOW)
        draw.rectangle([wx + 1, y + 35, wx + 15, y + 49],
                        fill=_lighter(YELLOW))
        draw.line([wx + 8, y + 34, wx + 8, y + 50],
                  fill=_darker(YELLOW, 0.8))
    # Fork and knife sign
    sign_x = x + 28
    sign_y = y + 6
    draw.rectangle([sign_x, sign_y, sign_x + 24, sign_y + 14], fill=WHITE)
    draw.rectangle([sign_x + 1, sign_y + 1, sign_x + 23, sign_y + 13],
                    fill=(240, 230, 220))
    # Fork (left)
    fx = sign_x + 5
    draw.line([fx, sign_y + 2, fx, sign_y + 12], fill=OVERLAY, width=1)
    draw.line([fx - 2, sign_y + 2, fx - 2, sign_y + 5], fill=OVERLAY, width=1)
    draw.line([fx + 2, sign_y + 2, fx + 2, sign_y + 5], fill=OVERLAY, width=1)
    draw.line([fx - 2, sign_y + 5, fx + 2, sign_y + 5], fill=OVERLAY, width=1)
    # Knife (right)
    kx = sign_x + 18
    draw.line([kx, sign_y + 2, kx, sign_y + 12], fill=OVERLAY, width=2)
    draw.polygon([(kx - 1, sign_y + 2), (kx + 2, sign_y + 2), (kx, sign_y + 5)],
                 fill=OVERLAY)
    # Chimney with smoke
    draw.rectangle([x + 60, y + 2, x + 68, y + 18], fill=_darker(RED, 0.6))
    for si, sy in enumerate(range(y - 2, y - 10, -3)):
        draw.rectangle([x + 62 + si * 2, sy, x + 66 + si * 2, sy + 2],
                        fill=(120, 120, 140))


def _building_park(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    # Ground
    draw.rectangle([x, y + 60, x + 80, y + 80], fill=(40, 80, 40))
    # Grass tufts
    for gx in range(x + 2, x + 78, 6):
        draw.rectangle([gx, y + 58, gx + 3, y + 62], fill=GREEN)
        draw.rectangle([gx + 1, y + 56, gx + 2, y + 60], fill=_lighter(GREEN))

    # Tree 1 (left)
    # Trunk
    draw.rectangle([x + 14, y + 34, x + 20, y + 60], fill=(100, 70, 40))
    draw.rectangle([x + 15, y + 34, x + 19, y + 60], fill=(120, 85, 50))
    # Canopy (layered circles via rectangles)
    for ly, lw in [(y + 8, 10), (y + 14, 14), (y + 22, 16), (y + 30, 12)]:
        cx = x + 17 - lw // 2
        draw.rectangle([cx, ly, cx + lw, ly + 8], fill=GREEN)
        draw.rectangle([cx + 1, ly + 1, cx + lw - 1, ly + 3],
                        fill=_lighter(GREEN, 1.2))

    # Tree 2 (right)
    draw.rectangle([x + 58, y + 30, x + 64, y + 60], fill=(100, 70, 40))
    draw.rectangle([x + 59, y + 30, x + 63, y + 60], fill=(120, 85, 50))
    for ly, lw in [(y + 4, 8), (y + 10, 12), (y + 18, 14), (y + 26, 10)]:
        cx = x + 61 - lw // 2
        draw.rectangle([cx, ly, cx + lw, ly + 8], fill=TEAL)
        draw.rectangle([cx + 1, ly + 1, cx + lw - 1, ly + 3],
                        fill=_lighter(TEAL, 1.2))

    # Bench
    bench_x = x + 28
    bench_y = y + 52
    # Seat
    draw.rectangle([bench_x, bench_y, bench_x + 24, bench_y + 4],
                    fill=(140, 100, 60))
    draw.rectangle([bench_x + 1, bench_y + 1, bench_x + 23, bench_y + 2],
                    fill=(160, 120, 70))
    # Back
    draw.rectangle([bench_x, bench_y - 6, bench_x + 24, bench_y],
                    fill=(140, 100, 60))
    draw.rectangle([bench_x + 1, bench_y - 5, bench_x + 23, bench_y - 1],
                    fill=(160, 120, 70))
    # Legs
    draw.rectangle([bench_x + 2, bench_y + 4, bench_x + 4, bench_y + 12],
                    fill=(90, 90, 95))
    draw.rectangle([bench_x + 20, bench_y + 4, bench_x + 22, bench_y + 12],
                    fill=(90, 90, 95))

    # Path
    for px in range(x + 30, x + 52, 4):
        c = (150, 140, 120) if ((px - x) // 4) % 2 else (130, 120, 100)
        draw.rectangle([px, y + 64, px + 3, y + 80], fill=c)

    # Flowers
    flower_colors = [RED, PINK, YELLOW, PURPLE]
    for i, fx in enumerate(range(x + 4, x + 76, 18)):
        draw.rectangle([fx, y + 54, fx + 2, y + 58], fill=GREEN)
        draw.rectangle([fx - 1, y + 50, fx + 3, y + 54],
                        fill=flower_colors[i % len(flower_colors)])
        draw.point((fx + 1, y + 52), fill=YELLOW)


_BUILDING_RENDERERS = {
    "bank": _building_bank,
    "casino": _building_casino,
    "bar": _building_bar,
    "shop": _building_shop,
    "jail": _building_jail,
    "police_station": _building_police,
    "restaurant": _building_restaurant,
    "park": _building_park,
}


def pixel_building(img: Image.Image, x: int, y: int, building_type: str) -> None:
    """Draw a pixel art building onto the image. 80x80 pixels."""
    draw = ImageDraw.Draw(img)
    renderer = _BUILDING_RENDERERS.get(building_type)
    if renderer:
        renderer(draw, x, y)


def pixel_item(img: Image.Image, x: int, y: int, item_type: str) -> None:
    """Draw a small 16x16 pixel art item icon."""
    draw = ImageDraw.Draw(img)
    s = 2  # pixel scale

    if item_type == "food":
        # Apple
        draw.rectangle([x + 3 * s, y + 2 * s, x + 5 * s, y + 6 * s], fill=RED)
        draw.rectangle([x + 2 * s, y + 3 * s, x + 6 * s, y + 5 * s], fill=RED)
        draw.rectangle([x + 4 * s, y + s, x + 5 * s, y + 2 * s], fill=GREEN)
        draw.rectangle([x + 3 * s, y + 2 * s, x + 4 * s, y + 3 * s],
                        fill=_lighter(RED))

    elif item_type == "pet":
        # Cat face
        draw.rectangle([x + 2 * s, y + 2 * s, x + 6 * s, y + 6 * s], fill=ORANGE)
        draw.rectangle([x + s, y + 2 * s, x + 7 * s, y + 5 * s], fill=ORANGE)
        # Ears
        draw.rectangle([x + s, y + s, x + 2 * s, y + 3 * s], fill=ORANGE)
        draw.rectangle([x + 6 * s, y + s, x + 7 * s, y + 3 * s], fill=ORANGE)
        # Eyes
        draw.rectangle([x + 2 * s, y + 3 * s, x + 3 * s, y + 4 * s], fill=DARK)
        draw.rectangle([x + 5 * s, y + 3 * s, x + 6 * s, y + 4 * s], fill=DARK)
        # Nose
        draw.point((x + 4 * s, y + 4 * s), fill=PINK)

    elif item_type == "sword":
        draw.rectangle([x + 3 * s, y + s, x + 4 * s, y + 5 * s], fill=(180, 180, 200))
        draw.rectangle([x + 3 * s, y + s, x + 4 * s, y + 2 * s],
                        fill=_lighter((180, 180, 200)))
        draw.rectangle([x + 2 * s, y + 5 * s, x + 5 * s, y + 6 * s], fill=GOLD)
        draw.rectangle([x + 3 * s, y + 6 * s, x + 4 * s, y + 7 * s],
                        fill=(100, 70, 40))

    elif item_type == "shield":
        draw.rectangle([x + 2 * s, y + s, x + 6 * s, y + 5 * s], fill=BLUE)
        draw.rectangle([x + s, y + 2 * s, x + 7 * s, y + 4 * s], fill=BLUE)
        draw.rectangle([x + 3 * s, y + 5 * s, x + 5 * s, y + 6 * s], fill=BLUE)
        draw.rectangle([x + 4 * s, y + 6 * s, x + 5 * s, y + 7 * s], fill=BLUE)
        # Cross emblem
        draw.rectangle([x + 3 * s, y + 2 * s, x + 5 * s, y + 3 * s], fill=GOLD)
        draw.rectangle([x + 4 * s, y + s, x + 5 * s, y + 4 * s], fill=GOLD)

    elif item_type == "potion":
        # Bottle
        draw.rectangle([x + 3 * s, y + s, x + 5 * s, y + 2 * s],
                        fill=(180, 180, 200))
        draw.rectangle([x + 2 * s, y + 2 * s, x + 6 * s, y + 6 * s], fill=PURPLE)
        draw.rectangle([x + s, y + 3 * s, x + 7 * s, y + 5 * s], fill=PURPLE)
        draw.rectangle([x + 3 * s, y + 6 * s, x + 5 * s, y + 7 * s], fill=PURPLE)
        # Shine
        draw.rectangle([x + 2 * s, y + 3 * s, x + 3 * s, y + 4 * s],
                        fill=_lighter(PURPLE))
        # Cork
        draw.rectangle([x + 3 * s, y + s, x + 5 * s, y + 2 * s],
                        fill=(140, 100, 60))

    elif item_type == "key":
        draw.rectangle([x + 2 * s, y + 2 * s, x + 4 * s, y + 4 * s], fill=GOLD)
        draw.rectangle([x + 3 * s, y + 3 * s, x + 4 * s, y + 4 * s],
                        fill=_darker(GOLD, 0.6))
        draw.rectangle([x + 4 * s, y + 3 * s, x + 7 * s, y + 4 * s], fill=GOLD)
        draw.rectangle([x + 6 * s, y + 4 * s, x + 7 * s, y + 5 * s], fill=GOLD)
        draw.rectangle([x + 5 * s, y + 4 * s, x + 6 * s, y + 5 * s], fill=GOLD)

    elif item_type == "ring":
        draw.rectangle([x + 2 * s, y + 2 * s, x + 6 * s, y + 6 * s], fill=GOLD)
        draw.rectangle([x + 3 * s, y + 3 * s, x + 5 * s, y + 5 * s], fill=BG)
        # Gem
        draw.rectangle([x + 3 * s, y + s, x + 5 * s, y + 3 * s], fill=RED)
        draw.rectangle([x + 4 * s, y + s, x + 5 * s, y + 2 * s],
                        fill=_lighter(RED))

    elif item_type == "coin":
        draw.rectangle([x + 2 * s, y + 2 * s, x + 6 * s, y + 6 * s], fill=GOLD)
        draw.rectangle([x + s, y + 3 * s, x + 7 * s, y + 5 * s], fill=GOLD)
        draw.rectangle([x + 3 * s, y + s, x + 5 * s, y + 7 * s], fill=GOLD)
        # Inner
        draw.rectangle([x + 3 * s, y + 3 * s, x + 5 * s, y + 5 * s],
                        fill=_darker(GOLD, 0.8))
        draw.rectangle([x + 4 * s, y + 3 * s, x + 5 * s, y + 5 * s],
                        fill=_lighter(GOLD))


def pixel_scene(title: str, width: int = 600, height: int = 400) -> Image.Image:
    """Create a new pixel-art scene with dark background, stars, and title bar."""
    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)

    # Star field
    rng = random.Random(hash(title) & 0xFFFFFFFF)
    for _ in range(width * height // 600):
        sx = rng.randint(0, width - 1)
        sy = rng.randint(0, height - 1)
        brightness = rng.randint(100, 255)
        c = (brightness, brightness, brightness)
        size = rng.choice([1, 1, 1, 2])
        if size == 1:
            draw.point((sx, sy), fill=c)
        else:
            draw.rectangle([sx, sy, sx + 1, sy + 1], fill=c)

    # Title bar
    pixel_box(draw, 4, 4, width - 8, 32, fill=SURFACE, border=OVERLAY, border_w=2)
    font = _get_font(18)
    bbox = draw.textbbox((0, 0), title, font=font)
    tw = bbox[2] - bbox[0]
    tx = (width - tw) // 2
    draw.text((tx + 1, 9), title, font=font, fill=DARK)
    draw.text((tx, 8), title, font=font, fill=TEXT_COLOR)

    # Decorative corner pixels
    for cx, cy in [(6, 6), (width - 10, 6), (6, 30), (width - 10, 30)]:
        draw.rectangle([cx, cy, cx + 3, cy + 3], fill=PURPLE)

    return img


def pixel_gradient_bg(img: Image.Image, color1: tuple, color2: tuple) -> None:
    """Apply a pixel dithered gradient background."""
    draw = ImageDraw.Draw(img)
    w, h = img.size
    for y in range(h):
        t = y / max(1, h - 1)
        base = _blend(color1, color2, t)
        for x in range(0, w, 2):
            # Dither: offset color slightly based on checkerboard
            if (x + y) % 4 < 2:
                c = base
            else:
                c = _blend(base, color2, min(1.0, t + 0.05))
            draw.rectangle([x, y, x + 1, y], fill=c)


def pixel_banner(img: Image.Image, text: str, y: int,
                 color: tuple = PURPLE) -> None:
    """Draw a centered pixel art banner/ribbon."""
    draw = ImageDraw.Draw(img)
    w = img.size[0]
    font = _get_font(14)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    bw = tw + 40
    bh = th + 16
    bx = (w - bw) // 2

    # Banner body
    draw.rectangle([bx, y, bx + bw, y + bh], fill=color)
    draw.rectangle([bx + 1, y + 1, bx + bw - 1, y + bh - 1], fill=color)
    # Highlight
    draw.line([bx + 2, y + 2, bx + bw - 2, y + 2], fill=_lighter(color))
    # Shadow
    draw.line([bx + 2, y + bh - 2, bx + bw - 2, y + bh - 2],
              fill=_darker(color, 0.7))

    # Ribbon tails (left)
    draw.polygon([(bx - 8, y), (bx, y), (bx, y + bh), (bx - 8, y + bh),
                  (bx - 2, y + bh // 2)], fill=_darker(color, 0.8))
    # Ribbon tails (right)
    draw.polygon([(bx + bw + 8, y), (bx + bw, y), (bx + bw, y + bh),
                  (bx + bw + 8, y + bh), (bx + bw + 2, y + bh // 2)],
                 fill=_darker(color, 0.8))

    # Text
    tx = (w - tw) // 2
    ty = y + (bh - th) // 2
    draw.text((tx + 1, ty + 1), text, font=font, fill=DARK)
    draw.text((tx, ty), text, font=font, fill=WHITE)


def pixel_progress_bar(draw: ImageDraw.ImageDraw, x: int, y: int,
                       width: int, height: int, progress: float,
                       color: tuple = GREEN) -> None:
    """Draw a pixel-style progress bar. progress is 0.0 to 1.0."""
    progress = max(0.0, min(1.0, progress))
    # Background
    draw.rectangle([x, y, x + width, y + height], fill=OVERLAY)
    # Border
    draw.rectangle([x, y, x + width, y + height], outline=_lighter(OVERLAY))
    # Fill
    fill_w = int((width - 4) * progress)
    if fill_w > 0:
        draw.rectangle([x + 2, y + 2, x + 2 + fill_w, y + height - 2], fill=color)
        # Pixel highlight on fill
        draw.line([x + 2, y + 2, x + 2 + fill_w, y + 2],
                  fill=_lighter(color))
        # Segmented look
        for sx in range(x + 6, x + 2 + fill_w, 4):
            draw.line([sx, y + 2, sx, y + height - 2],
                      fill=_darker(color, 0.85))


def pixel_explosion(draw: ImageDraw.ImageDraw, cx: int, cy: int,
                    radius: int) -> None:
    """Draw a pixel burst/explosion effect."""
    rng = random.Random((cx * 7919 + cy * 6271) & 0xFFFFFFFF)
    colors = [RED, ORANGE, YELLOW, WHITE]
    # Concentric rings with scatter
    for r in range(radius, 0, -3):
        color = colors[min(len(colors) - 1, (radius - r) * len(colors) // radius)]
        for angle_deg in range(0, 360, 15):
            angle = math.radians(angle_deg)
            jitter = rng.randint(-2, 2)
            px = int(cx + (r + jitter) * math.cos(angle))
            py = int(cy + (r + jitter) * math.sin(angle))
            size = rng.choice([1, 2, 3])
            draw.rectangle([px, py, px + size, py + size], fill=color)
    # Center flash
    draw.rectangle([cx - 3, cy - 3, cx + 3, cy + 3], fill=WHITE)
    draw.rectangle([cx - 1, cy - 1, cx + 1, cy + 1], fill=YELLOW)
    # Spark lines
    for angle_deg in range(0, 360, 45):
        angle = math.radians(angle_deg + rng.randint(-10, 10))
        length = rng.randint(radius // 2, radius + 4)
        ex = int(cx + length * math.cos(angle))
        ey = int(cy + length * math.sin(angle))
        draw.line([cx, cy, ex, ey], fill=YELLOW, width=1)


def pixel_skull(draw: ImageDraw.ImageDraw, x: int, y: int,
                size: int) -> None:
    """Draw a pixel skull icon."""
    s = max(1, size // 8)
    # Cranium
    draw.rectangle([x + 2 * s, y, x + 6 * s, y + s], fill=WHITE)
    draw.rectangle([x + s, y + s, x + 7 * s, y + 5 * s], fill=WHITE)
    draw.rectangle([x + 2 * s, y + 5 * s, x + 6 * s, y + 6 * s], fill=WHITE)
    # Eye sockets
    draw.rectangle([x + 2 * s, y + 2 * s, x + 3 * s, y + 4 * s], fill=DARK)
    draw.rectangle([x + 5 * s, y + 2 * s, x + 6 * s, y + 4 * s], fill=DARK)
    # Nose
    draw.rectangle([x + 4 * s, y + 4 * s, x + 5 * s, y + 5 * s],
                    fill=_darker(WHITE, 0.7))
    # Teeth
    draw.rectangle([x + 2 * s, y + 5 * s, x + 6 * s, y + 7 * s], fill=WHITE)
    for tx in range(x + 2 * s, x + 6 * s, s):
        draw.line([tx, y + 5 * s, tx, y + 7 * s], fill=_darker(WHITE, 0.6))
    draw.line([x + 2 * s, y + 6 * s, x + 6 * s, y + 6 * s],
              fill=_darker(WHITE, 0.6))
    # Jaw outline
    draw.rectangle([x + s, y + 5 * s, x + 2 * s, y + 6 * s],
                    fill=_darker(WHITE, 0.8))
    draw.rectangle([x + 6 * s, y + 5 * s, x + 7 * s, y + 6 * s],
                    fill=_darker(WHITE, 0.8))


def pixel_badge(draw: ImageDraw.ImageDraw, x: int, y: int, text: str,
                color: tuple = PURPLE) -> None:
    """Draw a small pixel badge/label."""
    font = _get_font(10)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pw, ph = 6, 4  # padding
    bw = tw + pw * 2
    bh = th + ph * 2

    # Badge background
    draw.rectangle([x, y, x + bw, y + bh], fill=color)
    # Pixel corners (notch)
    draw.point((x, y), fill=BG)
    draw.point((x + bw, y), fill=BG)
    draw.point((x, y + bh), fill=BG)
    draw.point((x + bw, y + bh), fill=BG)
    # Highlight
    draw.line([x + 1, y + 1, x + bw - 1, y + 1], fill=_lighter(color))
    # Text
    draw.text((x + pw, y + ph), text, font=font, fill=WHITE)


# ── Export Helper ─────────────────────────────────────────────────────────


def render_to_buffer(img: Image.Image) -> io.BytesIO:
    """Convert a PIL Image to a BytesIO PNG buffer, ready for sending."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
