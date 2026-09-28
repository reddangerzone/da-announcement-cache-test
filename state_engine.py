from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Iterable

from models import AnnouncementState, CalendarEvent, WarLabel


DEFAULT_WAR_NOTES: dict[WarLabel, str] = {
    "negotiating": "Terms are still being negotiated. Watch Discord for the final war plan.",
    "real": "Remember to stack before the war and turn off revives.",
    "termed": "Onliners only. Check your newsie for score.",
}


def utc_timestamp(value: Any) -> datetime | None:
    if value in (None, "", 0, "0"):
        return None
    return datetime.fromtimestamp(int(value), UTC)


def latest_unfinished_war(payload: dict[str, Any]) -> dict[str, Any] | None:
    wars = payload.get("rankedwars", [])
    candidates = [war for war in wars if not int(war.get("end") or 0)]
    return max(candidates, key=lambda war: int(war.get("start") or 0), default=None)


def opponent_for(war: dict[str, Any], faction_id: int) -> dict[str, Any] | None:
    return next(
        (faction for faction in war.get("factions", []) if int(faction["id"]) != faction_id),
        None,
    )


def next_matching_time(now: datetime, weekday: int = 1, hour: int = 12) -> datetime:
    """Return the next weekday/hour in UTC (TCT), never a past timestamp."""
    now = now.astimezone(UTC)
    days = (weekday - now.weekday()) % 7
    candidate = (now + timedelta(days=days)).replace(
        hour=hour, minute=0, second=0, microsecond=0
    )
    if candidate <= now:
        candidate += timedelta(days=7)
    return candidate


def normalize_events(
    events: Iterable[CalendarEvent], now: datetime, lookahead_days: int, maximum: int
) -> tuple[CalendarEvent, ...]:
    now = now.astimezone(UTC)
    cutoff = now + timedelta(days=lookahead_days)
    upcoming = [
        event
        for event in events
        if (event.ends_at or event.starts_at) >= now and event.starts_at <= cutoff
    ]
    return tuple(sorted(upcoming, key=lambda event: event.starts_at)[:maximum])


def build_state(
    ranked_wars: dict[str, Any],
    *,
    faction_id: int,
    now: datetime,
    enlisted: bool,
    war_label: WarLabel = "negotiating",
    notes: str = "",
    events: Iterable[CalendarEvent] = (),
    lookahead_days: int = 21,
    max_events: int = 6,
) -> AnnouncementState:
    now = now.astimezone(UTC)
    war = latest_unfinished_war(ranked_wars)
    normalized = normalize_events(events, now, lookahead_days, max_events)

    if war:
        opponent = opponent_for(war, faction_id)
        start = utc_timestamp(war.get("start"))
        active = bool(start and start <= now)
        display_notes = notes.strip() or DEFAULT_WAR_NOTES[war_label]
        return AnnouncementState(
            mode="active_war" if active else "matched",
            headline="WAR IS LIVE" if active else "NEXT RANKED WAR",
            target_at=start,
            opponent_name=(opponent or {}).get("name"),
            opponent_id=(opponent or {}).get("id"),
            war_id=int(war["id"]),
            war_label=war_label,
            notes=display_notes,
            events=normalized,
            generated_at=now,
        )

    if enlisted:
        return AnnouncementState(
            mode="awaiting_matchmaking",
            headline="NEXT MATCHMAKING",
            target_at=next_matching_time(now),
            notes=notes,
            events=normalized,
            generated_at=now,
        )

    return AnnouncementState(
        mode="not_enlisted",
        headline="NEXT ENLISTMENT",
        notes=notes or "We are not currently enlisted for a ranked war.",
        events=normalized,
        generated_at=now,
    )


def stale_state(previous: AnnouncementState | None, now: datetime, reason: str) -> AnnouncementState:
    if previous:
        data = previous.to_dict()
        data["mode"] = "stale"
        data["generated_at"] = now.astimezone(UTC)
        data["stale_reason"] = reason
        data["events"] = previous.events
        for key in ("target_at", "generated_at"):
            if isinstance(data[key], str):
                data[key] = datetime.fromisoformat(data[key])
        return AnnouncementState(**data)
    return AnnouncementState(
        mode="stale",
        headline="STATUS TEMPORARILY UNAVAILABLE",
        generated_at=now.astimezone(UTC),
        stale_reason=reason,
    )
