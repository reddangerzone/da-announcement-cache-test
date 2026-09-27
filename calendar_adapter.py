from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from models import CalendarEvent


def parse_torn_calendar(
    payload: dict[str, Any],
    *,
    now: datetime,
    lookahead_days: int = 21,
) -> tuple[list[CalendarEvent], list[str]]:
    """Normalize valid upcoming Torn events and report malformed records."""
    now = now.astimezone(UTC)
    cutoff = now + timedelta(days=lookahead_days)
    calendar = payload.get("calendar") or {}
    parsed: list[CalendarEvent] = []
    warnings: list[str] = []

    for collection, kind in (("competitions", "competition"), ("events", "event")):
        records = calendar.get(collection) or []
        if not isinstance(records, list):
            warnings.append(f"calendar.{collection} was not a list")
            continue

        for record in records:
            title = str(record.get("title") or "Untitled Torn event")
            try:
                start = datetime.fromtimestamp(int(record["start"]), UTC)
                end = datetime.fromtimestamp(int(record["end"]), UTC)
            except (KeyError, TypeError, ValueError, OSError):
                warnings.append(f"{title}: invalid start/end timestamp")
                continue

            if end < start:
                warnings.append(f"{title}: end precedes start; skipped")
                continue
            if end < now or start > cutoff:
                continue

            parsed.append(CalendarEvent(
                title=title,
                description=str(record.get("description") or ""),
                starts_at=start,
                ends_at=end,
                source="torn",
                kind=kind,
                fixed_start_time=bool(record.get("fixed_start_time")),
            ))

    parsed.sort(key=lambda event: event.starts_at)
    return parsed, warnings

