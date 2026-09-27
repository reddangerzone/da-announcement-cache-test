from __future__ import annotations

import math
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from models import AnnouncementState


ROOT = Path(__file__).resolve().parent
SUNSHINE_ASSET = ROOT / "assets" / "DASunshine.png"

BG = "#070b13"
CARD = "#111827"
CARD_2 = "#141d2d"
BORDER = "#293850"
TEXT = "#f7f3e8"
MUTED = "#9aabc3"
TEAL = "#22d3c5"
PINK = "#f472aa"
PURPLE = "#9b87f5"
YELLOW = "#ffd54a"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    names = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for name in names:
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def countdown(target: datetime | None, now: datetime) -> str:
    if not target:
        return "TBA"
    seconds = max(0, int((target.astimezone(UTC) - now.astimezone(UTC)).total_seconds()))
    days, seconds = divmod(seconds, 86_400)
    hours, seconds = divmod(seconds, 3_600)
    minutes, _ = divmod(seconds, 60)
    return f"{days}d {hours:02}h {minutes:02}m" if days else f"{hours:02}h {minutes:02}m"


def primary_status(state: AnnouncementState, now: datetime) -> str:
    if state.mode == "active_war":
        return "LIVE NOW"
    if state.mode == "not_enlisted":
        return "STANDING BY"
    if state.mode == "stale" and not state.target_at:
        return "CHECK DISCORD"
    return countdown(state.target_at, now)


def wrap(draw: ImageDraw.ImageDraw, text: str, face: ImageFont.ImageFont, width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        bounds = draw.textbbox((0, 0), candidate, font=face)
        if bounds[2] - bounds[0] <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def fitted_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    maximum: int,
    minimum: int,
    width: int,
    *,
    bold: bool = True,
) -> ImageFont.ImageFont:
    for size in range(maximum, minimum - 1, -2):
        face = font(size, bold)
        bounds = draw.textbbox((0, 0), text, font=face)
        if bounds[2] - bounds[0] <= width:
            return face
    return font(minimum, bold)


def wrapped_to_limit(
    draw: ImageDraw.ImageDraw,
    text: str,
    width: int,
    *,
    maximum_size: int,
    minimum_size: int,
    maximum_lines: int,
) -> tuple[ImageFont.ImageFont, list[str]]:
    for size in range(maximum_size, minimum_size - 1, -2):
        face = font(size)
        lines = wrap(draw, text, face, width)
        if len(lines) <= maximum_lines:
            return face, lines

    face = font(minimum_size)
    lines = wrap(draw, text, face, width)
    visible = lines[:maximum_lines]
    if len(lines) > maximum_lines and visible:
        suffix = "… See Discord."
        last = visible[-1]
        while last and draw.textbbox((0, 0), last + suffix, font=face)[2] > width:
            last = last.rsplit(" ", 1)[0] if " " in last else last[:-1]
        visible[-1] = last.rstrip(" .,;") + suffix
    return face, visible


def glow(
    canvas: Image.Image,
    center: tuple[int, int],
    color: tuple[int, int, int],
    radius: int,
    opacity: int = 82,
) -> None:
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    x, y = center
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(*color, opacity))
    canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(max(1, radius // 2))))


def place_sunshine(canvas: Image.Image, box: tuple[int, int, int, int]) -> None:
    if not SUNSHINE_ASSET.exists():
        return
    sunshine = Image.open(SUNSHINE_ASSET).convert("RGBA")
    alpha_box = sunshine.getchannel("A").getbbox()
    if alpha_box:
        sunshine = sunshine.crop(alpha_box)
    sunshine.thumbnail((box[2] - box[0], box[3] - box[1]), Image.Resampling.LANCZOS)
    x = box[0] + ((box[2] - box[0]) - sunshine.width) // 2
    y = box[1] + ((box[3] - box[1]) - sunshine.height) // 2
    canvas.alpha_composite(sunshine, (x, y))


def gradient_text(
    canvas: Image.Image,
    position: tuple[int, int],
    text: str,
    face: ImageFont.ImageFont,
    start: tuple[int, int, int],
    end: tuple[int, int, int],
    *,
    anchor: str | None = None,
) -> None:
    mask = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(mask).text(position, text, font=face, fill=255, anchor=anchor)
    strip = Image.new("RGB", (2, 1))
    strip.putpixel((0, 0), start)
    strip.putpixel((1, 0), end)
    gradient = strip.resize(canvas.size, Image.Resampling.BILINEAR).convert("RGBA")
    canvas.alpha_composite(Image.composite(gradient, Image.new("RGBA", canvas.size), mask))


def rounded_card(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], accent: str) -> None:
    draw.rounded_rectangle(box, 24, fill=CARD, outline=BORDER, width=2)
    x1, y1, x2, _ = box
    draw.line((x1 + 24, y1 + 1, x2 - 24, y1 + 1), fill=accent, width=3)


def beveled_frame(canvas: Image.Image) -> None:
    width, height = canvas.size
    frame = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame)
    draw.rounded_rectangle((5, 5, width - 6, height - 6), 34, outline="#02040a", width=12)
    draw.rounded_rectangle((11, 11, width - 12, height - 12), 30, outline="#4a5a72", width=4)
    draw.rounded_rectangle((16, 16, width - 17, height - 17), 26, outline="#182437", width=8)
    draw.rounded_rectangle((22, 22, width - 23, height - 23), 22, outline="#050810", width=4)
    draw.line((35, 13, width - 42, 13), fill="#8190a7", width=2)
    draw.line((13, 36, 13, height - 44), fill="#6d7c91", width=2)
    draw.line((42, height - 14, width - 34, height - 14), fill="#000106", width=5)
    draw.line((width - 14, 42, width - 14, height - 35), fill="#000106", width=5)
    draw.line((31, 27, width // 2, 27), fill=PINK, width=3)
    draw.line((width // 2, 27, width - 31, 27), fill=PURPLE, width=3)
    draw.line((width - 27, 31, width - 27, height - 31), fill=TEAL, width=3)
    draw.line((31, height - 27, width - 31, height - 27), fill="#166a70", width=3)
    draw.line((27, 31, 27, height - 31), fill="#8f3b69", width=3)
    for x, y, color in (
        (31, 31, PINK),
        (width - 32, 31, PURPLE),
        (31, height - 32, "#8f3b69"),
        (width - 32, height - 32, TEAL),
    ):
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill="#050810", outline=color, width=2)
    canvas.alpha_composite(frame)


def status_accent(state: AnnouncementState) -> str:
    if state.mode == "active_war":
        return PINK
    if state.mode == "stale":
        return YELLOW
    return {"real": TEAL, "termed": YELLOW, "negotiating": PURPLE}.get(
        state.war_label or "", TEAL
    )


def status_label(state: AnnouncementState) -> str:
    if state.mode == "active_war":
        return (state.war_label or "war").upper()
    if state.mode == "awaiting_matchmaking":
        return "ENLISTED"
    if state.mode == "not_enlisted":
        return "NOT ENLISTED"
    if state.mode == "stale":
        return "STATUS UNAVAILABLE"
    return (state.war_label or "negotiating").upper()


def event_stamp(event) -> str:
    start = event.starts_at.astimezone(UTC)
    end = event.ends_at.astimezone(UTC) if event.ends_at else None
    if event.fixed_start_time:
        return start.strftime("%d %b · %H:%M TCT")
    if end and end.date() != start.date():
        return f"{start:%d %b}–{end:%d %b}"
    return start.strftime("%d %b")


def render(state: AnnouncementState, destination: Path, width: int = 900, height: int = 1200) -> None:
    if (width, height) != (900, 1200):
        raise ValueError("The announcement renderer currently requires a 900×1200 canvas")

    now = state.generated_at or datetime.now(UTC)
    canvas = Image.new("RGBA", (width, height), BG)
    glow(canvas, (155, 90), (244, 114, 170), 210)
    glow(canvas, (760, 430), (34, 211, 197), 250)
    glow(canvas, (130, 1050), (58, 95, 145), 240)
    draw = ImageDraw.Draw(canvas)

    # A subtle sunrise remains in the background as a second, restrained brand cue.
    draw.ellipse((525, 895, 1035, 1405), fill="#0d2530", outline="#174755", width=4)
    for angle in range(198, 343, 18):
        radians = math.radians(angle)
        draw.line(
            (
                780 + math.cos(radians) * 285,
                1150 + math.sin(radians) * 285,
                780 + math.cos(radians) * 370,
                1150 + math.sin(radians) * 370,
            ),
            fill="#123442",
            width=12,
        )

    place_sunshine(canvas, (42, 37, 100, 95))
    draw = ImageDraw.Draw(canvas)
    draw.text((116, 49), "DELIGHTFUL ASSHOLES", font=font(22, True), fill=PINK)
    headline_face = fitted_font(draw, state.headline, 50, 30, width - 96)
    draw.text((48, 102), state.headline, font=headline_face, fill=TEXT)
    draw.line((48, 170, width - 48, 170), fill=TEAL, width=3)
    draw.line((48, 174, 520, 174), fill=PINK, width=3)

    hero = (38, 211, width - 38, 520)
    accent = status_accent(state)
    rounded_card(draw, hero, accent)
    if state.opponent_name:
        draw.text((width // 2, 251), "VS", font=font(22, True), fill=MUTED, anchor="mm")
        opponent_face = fitted_font(draw, state.opponent_name, 44, 26, width - 145)
        opponent_lines = wrap(draw, state.opponent_name, opponent_face, width - 145)
        if len(opponent_lines) > 2:
            opponent_face, opponent_lines = wrapped_to_limit(
                draw,
                state.opponent_name,
                width - 145,
                maximum_size=34,
                minimum_size=22,
                maximum_lines=2,
            )
        line_height = opponent_face.size + 4
        opponent_y = 312 - (len(opponent_lines) - 1) * line_height // 2
        for line in opponent_lines:
            draw.text((width // 2, opponent_y), line, font=opponent_face, fill=TEXT, anchor="mm")
            opponent_y += line_height
        status_y = 383
    else:
        descriptor = {
            "awaiting_matchmaking": "MATCHING WINDOW",
            "not_enlisted": "FACTION STATUS",
            "stale": "LATEST UPDATE",
        }.get(state.mode, "FACTION STATUS")
        draw.text((width // 2, 282), descriptor, font=font(22, True), fill=MUTED, anchor="mm")
        status_y = 365

    status_text = primary_status(state, now)
    status_face = fitted_font(draw, status_text, 78, 48, width - 170)
    gradient_text(
        canvas,
        (width // 2, status_y),
        status_text,
        status_face,
        (244, 114, 170),
        (34, 211, 197),
        anchor="mm",
    )
    draw = ImageDraw.Draw(canvas)
    label = status_label(state)
    label_face = fitted_font(draw, label, 18, 14, 170)
    label_bounds = draw.textbbox((0, 0), label, font=label_face)
    pill_width = max(130, label_bounds[2] - label_bounds[0] + 42)
    pill_box = (
        width // 2 - pill_width // 2,
        468,
        width // 2 + pill_width // 2,
        505,
    )
    draw.rounded_rectangle(pill_box, 19, fill="#102b31", outline=accent, width=2)
    draw.text((width // 2, 487), label, font=label_face, fill=accent, anchor="mm")

    y = 552
    if state.notes:
        note_face, note_lines = wrapped_to_limit(
            draw,
            state.notes,
            width - 130,
            maximum_size=22,
            minimum_size=16,
            maximum_lines=5,
        )
        line_height = note_face.size + 8
        note_height = 71 + line_height * len(note_lines)
        rounded_card(draw, (38, y, width - 38, y + note_height), PINK)
        draw.text((64, y + 27), "A NOTE FROM LEADERSHIP", font=font(19, True), fill=PINK)
        text_y = y + 72
        for line in note_lines:
            draw.text((64, text_y), line, font=note_face, fill=TEXT)
            text_y += line_height
        y += note_height + 34

    draw.text((48, y), "UPCOMING", font=font(23, True), fill=YELLOW)
    draw.line((196, y + 15, width - 48, y + 15), fill=TEAL, width=4)
    y += 44
    event_bottom = height - (120 if state.mode == "stale" else 82)
    if not state.events:
        draw.rounded_rectangle((38, y, width - 38, y + 76), 18, fill=CARD_2, outline=BORDER, width=2)
        draw.text((65, y + 23), "No upcoming events yet.", font=font(22), fill=MUTED)
    else:
        for event in state.events:
            if y + 88 > event_bottom:
                break
            color = TEAL if event.source == "torn" else PINK
            draw.rounded_rectangle((38, y, width - 38, y + 88), 18, fill=CARD_2, outline=BORDER, width=2)
            draw.rounded_rectangle((38, y, 46, y + 88), 4, fill=color)
            title_face = fitted_font(draw, event.title, 23, 16, width - 155)
            draw.text((66, y + 14), event.title, font=title_face, fill=TEXT)
            draw.text((66, y + 53), event_stamp(event), font=font(17), fill=color)
            source = "TORN" if event.source == "torn" else "FACTION"
            draw.text((width - 64, y + 55), source, font=font(12, True), fill=MUTED, anchor="rs")
            y += 102

    if state.mode == "stale":
        draw.rounded_rectangle((38, height - 112, width - 38, height - 70), 16, fill="#5b2738", outline=YELLOW, width=2)
        draw.text(
            (width // 2, height - 91),
            "DATA MAY BE STALE · LAST GOOD STATUS SHOWN",
            font=font(16, True),
            fill=TEXT,
            anchor="mm",
        )

    draw.rounded_rectangle((30, height - 52, 278, height - 20), 14, fill="#38233d", outline=PINK, width=1)
    draw.text((45, height - 43), "AUTOMATED FACTION UPDATE", font=font(12, True), fill=PINK)
    draw.text(
        (width - 48, height - 35),
        f"Updated {now:%d %b %Y · %H:%M TCT}",
        font=font(14),
        fill=MUTED,
        anchor="rm",
    )

    beveled_frame(canvas)
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(destination, format="PNG", optimize=True)
