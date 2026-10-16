from __future__ import annotations

import math
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from models import AnnouncementState

BG = "#050914"
CARD = "#0d1728"
CARD_2 = "#111e33"
BORDER = "#315275"
TEXT = "#f4f8ff"
MUTED = "#9fb2ca"
ICE = "#9eeaff"
BLUE = "#40b9ff"
PINK = "#f472aa"
GOLD = "#ffd36a"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def fitted(draw: ImageDraw.ImageDraw, text: str, maximum: int, minimum: int, width: int):
    for size in range(maximum, minimum - 1, -2):
        face = font(size, True)
        bounds = draw.textbbox((0, 0), text, font=face)
        if bounds[2] - bounds[0] <= width:
            return face
    return font(minimum, True)


def glow(canvas: Image.Image, center: tuple[int, int], color: tuple[int, int, int], radius: int) -> None:
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    x, y = center
    draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=(*color, 75))
    canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(radius // 2)))


def card(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], accent: str = ICE) -> None:
    draw.rounded_rectangle(box, 22, fill=CARD, outline=BORDER, width=3)
    draw.line((box[0] + 24, box[1] + 2, box[2] - 24, box[1] + 2), fill=accent, width=3)


def frozen_frame(draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
    draw.rounded_rectangle((7, 7, width-8, height-8), 32, outline="#02050c", width=12)
    draw.rounded_rectangle((13, 13, width-14, height-14), 28, outline="#527da4", width=4)
    draw.rounded_rectangle((20, 20, width-21, height-21), 23, outline="#142c48", width=8)
    draw.line((33, 27, width-33, 27), fill=ICE, width=3)
    draw.line((27, 34, 27, height-34), fill="#4287b7", width=3)
    draw.line((width-27, 34, width-27, height-34), fill=PINK, width=2)
    for x in range(48, width-35, 83):
        length = 10 + (x * 7) % 23
        draw.polygon(((x, 28), (x+13, 28), (x+5, 28+length)), fill="#b9f1ff")


def moon(draw: ImageDraw.ImageDraw) -> None:
    draw.ellipse((48, 45, 126, 123), fill="#dff8ff", outline=ICE, width=4)
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        x1, y1 = 87 + math.cos(rad)*44, 84 + math.sin(rad)*44
        x2, y2 = 87 + math.cos(rad)*55, 84 + math.sin(rad)*55
        draw.line((x1, y1, x2, y2), fill=ICE, width=4)
    draw.arc((65, 69, 83, 87), 195, 345, fill="#2c5677", width=3)
    draw.arc((91, 69, 109, 87), 195, 345, fill="#2c5677", width=3)
    draw.arc((70, 76, 104, 105), 20, 160, fill="#2c5677", width=3)


def pace_text(state: AnnouncementState) -> str:
    if not state.chain_rate_per_hour:
        return "GATHERING PACE DATA…"
    return f"{state.chain_rate_per_hour:,.0f} HITS / HOUR"


def finish_text(state: AnnouncementState) -> str:
    if not state.chain_estimated_finish:
        return "ESTIMATED FINISH: CALCULATING"
    finish = state.chain_estimated_finish.astimezone(UTC)
    return f"ESTIMATED FINISH: {finish:%d %b · %H:%M TCT}"


def render_halloween(state: AnnouncementState, destination: Path, width: int, height: int) -> None:
    if (width, height) != (900, 1200):
        raise ValueError("The Halloween renderer currently requires a 900×1200 canvas")
    now = state.generated_at or datetime.now(UTC)
    canvas = Image.new("RGBA", (width, height), BG)
    glow(canvas, (130, 120), (54, 173, 255), 225)
    glow(canvas, (760, 1030), (113, 48, 145), 260)
    draw = ImageDraw.Draw(canvas)

    # Frozen mountain/watch silhouettes: atmospheric, but kept behind the data.
    draw.polygon(((0, 355), (120, 245), (205, 337), (325, 205), (460, 350),
                  (590, 250), (720, 350), (835, 225), (900, 305), (900, 470), (0, 470)),
                 fill="#0b2037")
    draw.rectangle((755, 187, 805, 350), fill="#091727")
    draw.polygon(((745, 187), (780, 145), (815, 187)), fill="#0a1a2b")
    for y in (220, 264, 308):
        draw.rectangle((770, y, 790, y+14), fill="#53a8cf")

    moon(draw)
    draw.text((150, 57), "DELIGHTFUL ASSHOLES", font=font(22, True), fill=GOLD)
    headline = "AND NOW OUR WATCH BEGINS"
    draw.text((width//2, 148), headline, font=fitted(draw, headline, 49, 30, width-95),
              fill=TEXT, anchor="mm")
    draw.text((width//2, 195), "HALLOWEEN 50K CHAIN", font=font(21, True), fill=ICE, anchor="mm")
    draw.line((48, 226, width-48, 226), fill=ICE, width=3)
    draw.line((48, 231, 475, 231), fill=PINK, width=2)

    hero = (38, 270, width-38, 610)
    card(draw, hero, ICE)
    current = max(0, state.chain_current)
    target = max(1, state.chain_target)
    percent = min(100.0, current / target * 100)
    hits = f"{current:,} / {target:,} HITS"
    draw.text((width//2, 338), hits, font=fitted(draw, hits, 60, 38, width-120), fill=TEXT, anchor="mm")
    track = (90, 405, width-90, 466)
    draw.rounded_rectangle(track, 28, fill="#050b15", outline="#477094", width=3)
    fill_width = int((track[2]-track[0]) * percent / 100)
    if fill_width:
        draw.rounded_rectangle((track[0], track[1], track[0]+max(20, fill_width), track[3]),
                               28, fill=BLUE, outline=ICE, width=2)
    draw.text((width//2, 507), f"{percent:.1f}% COMPLETE", font=font(31, True), fill=ICE, anchor="mm")
    draw.text((width//2, 557), pace_text(state), font=font(21, True), fill=MUTED, anchor="mm")

    # Top hitters.
    left = (38, 645, 548, 1080)
    right = (570, 645, width-38, 1080)
    card(draw, left, GOLD)
    card(draw, right, PINK)
    draw.text((64, 681), "TOP HITTERS", font=font(27, True), fill=GOLD)
    hitters = state.chain_top_hitters[:3]
    if not hitters:
        draw.text((64, 755), "Waiting for contributor data…", font=font(19), fill=MUTED)
    else:
        medals = (GOLD, "#d8e4ef", "#d58a55")
        y = 742
        for rank, hitter in enumerate(hitters, 1):
            draw.rounded_rectangle((62, y, 522, y+82), 16, fill=CARD_2, outline=BORDER, width=2)
            draw.ellipse((80, y+17, 128, y+65), fill="#162943", outline=medals[rank-1], width=3)
            draw.text((104, y+41), str(rank), font=font(20, True), fill=medals[rank-1], anchor="mm")
            name = str(hitter.get("name", "Unknown"))
            draw.text((146, y+41), name, font=fitted(draw, name, 22, 15, 245), fill=TEXT, anchor="lm")
            draw.text((497, y+41), f"{int(hitter.get('hits', 0)):,}", font=font(21, True),
                      fill=ICE, anchor="rm")
            y += 99

    draw.text((596, 681), "THE NIGHT’S WATCH", font=fitted(draw, "THE NIGHT’S WATCH", 24, 18, 240), fill=PINK)
    draw.text((596, 754), "CURRENT PACE", font=font(15, True), fill=MUTED)
    rate = "CALCULATING" if not state.chain_rate_per_hour else f"{state.chain_rate_per_hour:,.0f} / HR"
    draw.text((596, 786), rate, font=fitted(draw, rate, 26, 18, 230), fill=ICE)
    draw.line((596, 835, 810, 835), fill=BORDER, width=2)
    draw.text((596, 870), "ESTIMATED FINISH", font=font(15, True), fill=MUTED)
    if state.chain_estimated_finish:
        finish = state.chain_estimated_finish.astimezone(UTC)
        draw.text((596, 904), finish.strftime("%d %b"), font=font(29, True), fill=TEXT)
        draw.text((596, 947), finish.strftime("%H:%M TCT"), font=font(23, True), fill=ICE)
    else:
        draw.text((596, 910), "GATHERING", font=font(22, True), fill=TEXT)
        draw.text((596, 946), "PACE DATA…", font=font(22, True), fill=ICE)

    draw.rounded_rectangle((38, 1110, 338, 1147), 16, fill="#17263c", outline=BLUE, width=1)
    draw.text((58, 1120), "AUTOMATED FACTION UPDATE", font=font(13, True), fill=ICE)
    draw.text((width-48, 1129), f"Updated {now:%d %b · %H:%M TCT}",
              font=font(14), fill=MUTED, anchor="rm")
    frozen_frame(draw, width, height)
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(destination, format="PNG", optimize=True)
