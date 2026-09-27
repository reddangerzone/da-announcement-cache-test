from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT.parent))

import api  # type: ignore  # Uses the existing project API wrapper.

from calendar_adapter import parse_torn_calendar
from leadership_adapter import load_leadership_data
from models import AnnouncementState, CalendarEvent
from news_adapter import parse_ranked_war_news
from render_image import render
from state_engine import build_state, stale_state


def load_previous_state(path: Path) -> AnnouncementState | None:
    """Load the last generated state so API failures can preserve useful data."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        events = tuple(
            CalendarEvent(
                title=item["title"],
                starts_at=datetime.fromisoformat(item["starts_at"]),
                ends_at=datetime.fromisoformat(item["ends_at"]) if item.get("ends_at") else None,
                description=item.get("description", ""),
                source=item.get("source", "faction"),
                kind=item.get("kind", "faction"),
                fixed_start_time=bool(item.get("fixed_start_time", True)),
            )
            for item in data.pop("events", [])
        )
        for key in ("target_at", "generated_at"):
            if data.get(key):
                data[key] = datetime.fromisoformat(data[key])
        return AnnouncementState(events=events, **data)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the DA faction announcement image.")
    parser.add_argument("--output", default="announcement.png")
    parser.add_argument("--state-output", default="state.json")
    parser.add_argument(
        "--enlisted",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Override the faction-news enlistment result for testing",
    )
    parser.add_argument("--war-label", choices=("negotiating", "real", "termed"), default=None)
    parser.add_argument("--notes", default=None)
    args = parser.parse_args()

    config = json.loads((PROJECT_ROOT / "config.json").read_text(encoding="utf-8"))
    now = datetime.now(UTC)
    output = PROJECT_ROOT / args.output
    state_output = PROJECT_ROOT / args.state_output
    payload = api.get("faction_ranked_wars", fac_id=config["faction_id"])
    if not payload:
        state = stale_state(
            load_previous_state(state_output), now, "Ranked-war API data was unavailable"
        )
        render(state, output, config["image_width"], config["image_height"])
        state_output.parent.mkdir(parents=True, exist_ok=True)
        state_output.write_text(json.dumps(state.to_dict(), indent=2) + "\n", encoding="utf-8")
        print("Ranked-war API unavailable; rendered a stale-data warning")
        return 0
    saved_label, saved_notes, faction_events, leadership_warnings = load_leadership_data(
        PROJECT_ROOT / "leadership.json"
    )
    for warning in leadership_warnings:
        print(f"Leadership warning: {warning}")
    news_payload = api.get("faction_news", cat="rankedWar") or {"news": []}
    enlistment, news_warnings = parse_ranked_war_news(news_payload, now=now)
    for warning in news_warnings:
        print(f"Faction-news warning: {warning}")
    enlisted = enlistment.enlisted if args.enlisted is None else args.enlisted
    if enlistment.action_at:
        actor = f" by {enlistment.actor_name}" if enlistment.actor_name else ""
        print(
            f"Latest matchmaking action: {enlistment.action}{actor} at "
            f"{enlistment.action_at.isoformat()}"
        )
    else:
        print(
            "No enlistment action found since "
            f"{enlistment.cutoff.isoformat()}; treating faction as not enlisted"
        )
    calendar_payload = api.get("torn_calendar") or {"calendar": {}}
    torn_events, calendar_warnings = parse_torn_calendar(
        calendar_payload, now=now, lookahead_days=config["lookahead_days"]
    )
    for warning in calendar_warnings:
        print(f"Calendar warning: {warning}")
    state = build_state(
        payload,
        faction_id=config["faction_id"],
        now=now,
        enlisted=enlisted,
        war_label=args.war_label or saved_label,
        notes=saved_notes if args.notes is None else args.notes,
        events=(*torn_events, *faction_events),
        lookahead_days=config["lookahead_days"],
        max_events=config["max_events"],
    )

    render(state, output, config["image_width"], config["image_height"])
    state_output.parent.mkdir(parents=True, exist_ok=True)
    state_output.write_text(json.dumps(state.to_dict(), indent=2) + "\n", encoding="utf-8")
    print(f"Generated {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
