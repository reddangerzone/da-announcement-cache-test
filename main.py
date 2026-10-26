from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT.parent))

import api  # type: ignore

from calendar_adapter import parse_torn_calendar
from award_tracker import load_award_tracker, save_award_tracker, update_award_tracker
from chain_adapter import (
    halloween_event_started,
    load_tracker,
    save_tracker,
    update_tracker,
)
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
        for key in (
            "target_at", "generated_at", "chain_estimated_finish",
            "awards_tracking_started_at", "awards_last_updated_at",
        ):
            if data.get(key):
                data[key] = datetime.fromisoformat(data[key])
        data["chain_top_hitters"] = tuple(data.get("chain_top_hitters", ()))
        data["award_top_earners"] = tuple(data.get("award_top_earners", ()))
        return AnnouncementState(events=events, **data)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the DA faction announcement image.")
    parser.add_argument("--output", default="announcement.png")
    parser.add_argument("--state-output", default="state.json")
    parser.add_argument("--halloween-tracker", default="halloween_chain.json")
    parser.add_argument("--award-tracker", default="award_tracker.json")
    parser.add_argument(
        "--enlisted", action=argparse.BooleanOptionalAction, default=None,
        help="Override the faction-news enlistment result for testing",
    )
    parser.add_argument("--war-label", choices=("negotiating", "real", "termed"), default=None)
    parser.add_argument("--notes", default=None)
    args = parser.parse_args()

    config = json.loads((PROJECT_ROOT / "config.json").read_text(encoding="utf-8"))
    now = datetime.now(UTC)
    output = PROJECT_ROOT / args.output
    state_output = PROJECT_ROOT / args.state_output
    tracker_output = PROJECT_ROOT / args.halloween_tracker
    award_tracker_output = PROJECT_ROOT / args.award_tracker
    previous_state = load_previous_state(state_output)

    payload = api.get("faction_ranked_wars", fac_id=config["faction_id"])
    if not payload:
        state = stale_state(previous_state, now, "Ranked-war API data was unavailable")
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

    calendar_payload = api.get("torn_calendar") or {"calendar": {}}
    torn_events, calendar_warnings = parse_torn_calendar(
        calendar_payload, now=now, lookahead_days=config["lookahead_days"]
    )
    for warning in calendar_warnings:
        print(f"Calendar warning: {warning}")

    all_events = (*torn_events, *faction_events)
    state = build_state(
        payload,
        faction_id=config["faction_id"],
        now=now,
        enlisted=enlisted,
        war_label=args.war_label or saved_label,
        notes=saved_notes if args.notes is None else args.notes,
        events=all_events,
        lookahead_days=config["lookahead_days"],
        max_events=config["max_events"],
    )

    tracker = load_tracker(tracker_output, now.year)
    event_started = halloween_event_started(torn_events, now)
    halloween_may_be_active = bool(tracker.get("activated") or event_started)
    chain_payload = None
    contributors_payload = None
    members_payload = None
    if halloween_may_be_active and not tracker.get("complete"):
        chain_payload = api.get("faction_chain") or {"chain": {}}
        contributors_payload = api.get("faction_chain_report") or {}
        members_payload = api.get("faction_members", fac_id=config["faction_id"]) or {}

    tracker, chain = update_tracker(
        tracker,
        now=now,
        event_started=event_started,
        chain_payload=chain_payload,
        contributors_payload=contributors_payload,
        members_payload=members_payload,
    )
    save_tracker(tracker_output, tracker)

    award_data = load_award_tracker(award_tracker_output)
    if halloween_may_be_active:
        if members_payload is None:
            members_payload = api.get("faction_members", fac_id=config["faction_id"]) or {}
        award_data, awards = update_award_tracker(
            award_data,
            now=now,
            members_payload=members_payload,
            fetch_profile=lambda player_id: api.get("user_profile", user_id=player_id),
        )
        save_award_tracker(award_tracker_output, award_data)
        state = replace(
            state,
            awards_today=awards.today,
            awards_event_total=awards.event_total,
            awards_tracking_started_at=awards.tracking_started_at,
            awards_last_updated_at=awards.last_updated_at,
            awards_first_day_partial=awards.first_day_partial,
            award_top_earners=awards.top_earners,
        )

    if chain.active:
        state = replace(
            state,
            headline="AND NOW OUR WATCH BEGINS",
            halloween_active=True,
            chain_current=chain.current,
            chain_target=chain.target,
            chain_rate_per_hour=chain.rate_per_hour,
            chain_estimated_finish=chain.estimated_finish,
            chain_top_hitters=chain.top_hitters,
        )

    render(state, output, config["image_width"], config["image_height"])
    state_output.parent.mkdir(parents=True, exist_ok=True)
    state_output.write_text(json.dumps(state.to_dict(), indent=2) + "\n", encoding="utf-8")
    print(f"Generated {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
