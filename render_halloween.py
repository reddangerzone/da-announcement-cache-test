from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from models import AnnouncementState


ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "assets" / "nights-watch-template.jpg"
FROZEN_SUNSHINE = ROOT / "assets" / "DASunshine-frozen.png"
HEADER = ROOT / "assets" / "nights-watch-header.png"

WHITE = "#f6fbff"
ICE = "#8feaff"
PALE_ICE = "#d9f7ff"
MUTED = "#a8c1d7"
PINK = "#ed7fb7"
GOLD = "#ffd45f"
ORANGE = "#ff9654"
VIOLET = "#b99cff"
INK = "#050a13"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    )
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def gothic(size: int) -> ImageFont.FreeTypeFont:
    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSerifCondensed-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    ):
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return font(size, True)


def fitted(draw: ImageDraw.ImageDraw, text: str, maximum: int, minimum: int,
           width: int, *, serif: bool = False) -> ImageFont.FreeTypeFont:
    for size in range(maximum, minimum - 1, -1):
        face = gothic(size) if serif else font(size, True)
        box = draw.textbbox((0, 0), text, font=face)
        if box[2] - box[0] <= width:
            return face
    return gothic(minimum) if serif else font(minimum, True)


def shadow_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str,
                face: ImageFont.FreeTypeFont, fill: str, *, anchor: str = "la",
                shadow: int = 3) -> None:
    x, y = xy
    draw.text((x + shadow, y + shadow), text, font=face, fill=INK, anchor=anchor,
              stroke_width=2, stroke_fill=INK)
    draw.text((x, y), text, font=face, fill=fill, anchor=anchor,
              stroke_width=1, stroke_fill="#153349")


def centered_segments(draw: ImageDraw.ImageDraw, y: int,
                      segments: tuple[tuple[str, str], ...],
                      face: ImageFont.FreeTypeFont) -> None:
    """Draw differently colored text fragments as one centered line."""
    widths = [draw.textlength(text, font=face) for text, _ in segments]
    x = 450 - sum(widths) / 2
    for (text, color), width in zip(segments, widths):
        draw.text((x + 3, y + 3), text, font=face, fill=INK,
                  stroke_width=2, stroke_fill=INK)
        draw.text((x, y), text, font=face, fill=color,
                  stroke_width=1, stroke_fill="#153349")
        x += width


def place_asset(canvas: Image.Image, path: Path,
                box: tuple[int, int, int, int]) -> None:
    if not path.exists():
        return
    asset = Image.open(path).convert("RGBA")
    alpha_box = asset.getchannel("A").getbbox()
    if alpha_box:
        asset = asset.crop(alpha_box)
    asset.thumbnail((box[2] - box[0], box[3] - box[1]), Image.Resampling.LANCZOS)
    x = box[0] + ((box[2] - box[0]) - asset.width) // 2
    y = box[1] + ((box[3] - box[1]) - asset.height) // 2
    canvas.alpha_composite(asset, (x, y))


def bevel_row(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, 10, fill=(6, 17, 32, 230), outline="#4a7797", width=2)
    draw.line((x1 + 12, y1 + 3, x2 - 12, y1 + 3), fill="#a7eaff", width=2)
    draw.line((x1 + 12, y2 - 3, x2 - 12, y2 - 3), fill="#07101e", width=2)


def rate_text(state: AnnouncementState) -> str:
    if not state.chain_rate_per_hour:
        return "CALCULATING"
    return f"{state.chain_rate_per_hour:,.0f} HITS / HR"


def render_halloween(state: AnnouncementState, destination: Path,
                     width: int, height: int) -> None:
    if (width, height) != (900, 1200):
        raise ValueError("The Halloween renderer requires a 900×1200 canvas")
    if not TEMPLATE.exists():
        raise FileNotFoundError(f"Missing Halloween template: {TEMPLATE}")

    canvas = ImageOps.fit(
        Image.open(TEMPLATE).convert("RGBA"),
        (width, height),
        Image.Resampling.LANCZOS,
    )
    draw = ImageDraw.Draw(canvas)
    now = state.generated_at or datetime.now(UTC)

    # The headline is fixed artwork; only the chain information below is dynamic.
    if HEADER.exists():
        canvas.alpha_composite(Image.open(HEADER).convert("RGBA"), (0, 0))
    else:
        place_asset(canvas, FROZEN_SUNSHINE, (31, 27, 181, 183))
        draw = ImageDraw.Draw(canvas)
        shadow_text(draw, (190, 82), "AND NOW OUR WATCH BEGINS", gothic(40), WHITE)
    draw = ImageDraw.Draw(canvas)

    current = max(0, state.chain_current)
    target = max(1, state.chain_target)
    percent = min(100.0, current / target * 100)

    shadow_text(draw, (450, 350), "2026 NIGHT’S WATCH 50K", gothic(31), GOLD,
                anchor="mm")
    hit_text = f"{current:,} / {target:,}"
    hit_face = fitted(draw, hit_text, 72, 45, 730)
    centered_segments(
        draw,
        408,
        ((f"{current:,}", ICE), (" / ", WHITE), (f"{target:,}", PINK)),
        hit_face,
    )
    draw.text((450, 491), "CHAIN HITS", font=font(19, True), fill=MUTED, anchor="mm")

    # The template provides the dimensional frozen track; this is the live fill.
    track = (92, 579, 808, 642)
    inner = (track[0] + 10, track[1] + 11, track[2] - 10, track[3] - 11)
    fill_width = int((inner[2] - inner[0]) * percent / 100)
    if fill_width > 0:
        fill_right = min(inner[2], inner[0] + max(20, fill_width))
        draw.rounded_rectangle(
            (inner[0], inner[1], fill_right, inner[3]),
            19,
            fill="#39d5d0",
            outline="#c6f8ff",
            width=2,
        )
        draw.line((inner[0] + 12, inner[1] + 4, fill_right - 9, inner[1] + 4),
                  fill="#e1fbff", width=2)
    shadow_text(draw, (450, 686), f"{percent:.1f}% COMPLETE", font(27, True), ICE,
                anchor="mm", shadow=2)

    # Lower left: the exact recognition block from the original model.
    draw.text((79, 760), "TOP HITTERS", font=gothic(27), fill=GOLD)
    hitters = state.chain_top_hitters[:3]
    if hitters:
        medals = (GOLD, "#dce9f3", "#d8945f")
        y = 810
        for rank, hitter in enumerate(hitters, 1):
            bevel_row(draw, (74, y, 438, y + 61))
            draw.ellipse((88, y + 10, 129, y + 51), fill="#13263d",
                         outline=medals[rank - 1], width=3)
            draw.text((108, y + 31), str(rank), font=font(18, True),
                      fill=medals[rank - 1], anchor="mm")
            name = str(hitter.get("name", "Unknown"))
            draw.text((143, y + 30), name,
                      font=fitted(draw, name, 19, 13, 180), fill=WHITE, anchor="lm")
            draw.text((422, y + 30), f"{int(hitter.get('hits', 0)):,}",
                      font=font(18, True), fill=ICE, anchor="rm")
            y += 76
    else:
        draw.text((79, 824), "Waiting for contributor data…", font=font(17), fill=MUTED)

    # The original Upcoming card becomes the only functional change: live forecast.
    draw.text((493, 760), "CHAIN FORECAST", font=gothic(25), fill=PINK)
    draw.text((493, 818), "CURRENT PACE", font=font(13, True), fill=MUTED)
    draw.text((493, 849), rate_text(state),
              font=fitted(draw, rate_text(state), 25, 17, 320), fill=ICE)
    draw.line((493, 887, 813, 887), fill="#466c88", width=2)
    draw.text((493, 907), "ESTIMATED FINISH", font=font(13, True), fill=MUTED)
    if state.chain_estimated_finish:
        finish = state.chain_estimated_finish.astimezone(UTC)
        draw.text((493, 936), finish.strftime("%d %b · %H:%M TCT"),
                  font=fitted(draw, finish.strftime("%d %b · %H:%M TCT"), 23, 16, 320),
                  fill=WHITE)
    else:
        draw.text((493, 936), "GATHERING PACE DATA…", font=font(18, True), fill=WHITE)
    draw.text((493, 985), "LAST UPDATE", font=font(13, True), fill=MUTED)
    draw.text((493, 1011), now.strftime("%d %b · %H:%M TCT"),
              font=font(18, True), fill=ICE)

    footer = (
        "AUTOMATED FACTION ANNOUNCEMENT  |||  "
        f"LAST UPDATED {now:%d %b · %H:%M TCT}"
    )
    draw.text((450, 1100), footer,
              font=fitted(draw, footer, 16, 12, 710), fill=PALE_ICE,
              anchor="mm", stroke_width=1, stroke_fill=INK)
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(destination, format="PNG", optimize=True)
