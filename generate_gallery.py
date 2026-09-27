from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from models import AnnouncementState, CalendarEvent
from render_image import render


NOW = datetime(2026, 9, 27, 0, 0, tzinfo=UTC)
OUTPUT = Path(__file__).resolve().parent / "output" / "state-gallery"


def torn(title: str, days: float, duration: float = 1, fixed: bool = False) -> CalendarEvent:
    start = NOW + timedelta(days=days)
    return CalendarEvent(
        title=title,
        starts_at=start,
        ends_at=start + timedelta(days=duration),
        description="Torn-wide event",
        source="torn",
        kind="event",
        fixed_start_time=fixed,
    )


def faction(title: str, days: float) -> CalendarEvent:
    return CalendarEvent(
        title=title,
        starts_at=NOW + timedelta(days=days),
        description="Faction event",
        source="faction",
        kind="faction",
        fixed_start_time=True,
    )


COMMON_EVENTS = (
    torn("Tourism Day", 0.2),
    faction("Faction Movie Night and Questionably Competitive Trivia", 3.25),
    torn("CaffeineCon 2026", 8),
)


STATES = {
    "01-matched-negotiating": AnnouncementState(
        mode="matched",
        headline="NEXT RANKED WAR",
        target_at=NOW + timedelta(days=2, hours=5),
        opponent_name="Phoenix Ascent",
        opponent_id=48640,
        war_id=49314,
        war_label="negotiating",
        notes="Terms are still being discussed. Watch Discord for the final war plan.",
        events=COMMON_EVENTS,
        generated_at=NOW,
    ),
    "02-real-war": AnnouncementState(
        mode="matched",
        headline="NEXT RANKED WAR",
        target_at=NOW + timedelta(hours=18, minutes=35),
        opponent_name="The Extremely Long and Unnecessarily Dramatic Faction Name",
        war_label="real",
        notes="Remember to stack before the war and turn off revives.",
        events=COMMON_EVENTS,
        generated_at=NOW,
    ),
    "03-termed-war": AnnouncementState(
        mode="matched",
        headline="NEXT RANKED WAR",
        target_at=NOW + timedelta(days=4, hours=1),
        opponent_name="Reasonable Adults Allegedly",
        war_label="termed",
        notes="Onliners only. Check your newsie for score.",
        events=COMMON_EVENTS,
        generated_at=NOW,
    ),
    "04-war-live": AnnouncementState(
        mode="active_war",
        headline="WAR IS LIVE",
        target_at=NOW - timedelta(hours=2),
        opponent_name="Phoenix Ascent",
        war_label="real",
        notes="Get in Discord, check the target list, and call assists before wandering into danger.",
        events=COMMON_EVENTS,
        generated_at=NOW,
    ),
    "05-awaiting-matchmaking": AnnouncementState(
        mode="awaiting_matchmaking",
        headline="NEXT MATCHMAKING",
        target_at=NOW + timedelta(days=2, hours=5),
        notes="We are enlisted. Matching occurs Tuesday at 05:00 TCT.",
        events=COMMON_EVENTS,
        generated_at=NOW,
    ),
    "06-not-enlisted": AnnouncementState(
        mode="not_enlisted",
        headline="NEXT ENLISTMENT",
        notes="Enjoy Tourism Day! Leadership will post the next enlistment plan in Discord.",
        events=COMMON_EVENTS,
        generated_at=NOW,
    ),
    "07-stale-data": AnnouncementState(
        mode="stale",
        headline="STATUS TEMPORARILY UNAVAILABLE",
        target_at=None,
        notes="Torn did not return fresh faction data. The last successful event schedule is still shown below.",
        events=COMMON_EVENTS,
        generated_at=NOW,
        stale_reason="Ranked-war API data was unavailable",
    ),
    "08-long-note-stress-test": AnnouncementState(
        mode="matched",
        headline="NEXT RANKED WAR",
        target_at=NOW + timedelta(days=1, hours=3),
        opponent_name="The Extremely Long and Unnecessarily Dramatic Faction Name",
        war_label="real",
        notes=(
            "This is an intentionally overlong leadership note used to test the layout. "
            "Stack before the war, turn off revives, check Discord for target assignments, "
            "review the chain plan, confirm your availability, and remember that detailed "
            "instructions always live in the newsie and Discord."
        ),
        events=COMMON_EVENTS,
        generated_at=NOW,
    ),
}


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, state in STATES.items():
        render(state, OUTPUT / f"{name}.png", 900, 1200)
    print(f"Rendered {len(STATES)} states to {OUTPUT}")


if __name__ == "__main__":
    main()
