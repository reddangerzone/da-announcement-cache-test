from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from models import CalendarEvent, WarLabel


VALID_WAR_LABELS = {"negotiating", "real", "termed"}


def _date(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} is required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def load_leadership_data(
    path: Path,
) -> tuple[WarLabel, str, tuple[CalendarEvent, ...], list[str]]:
    """Load and validate the small repository-backed leadership control file."""
    warnings: list[str] = []
    if not path.exists():
        return "negotiating", "", (), [f"Leadership file not found: {path.name}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return "negotiating", "", (), [f"Leadership file could not be read: {error}"]

    label = data.get("war_label", "negotiating")
    if label not in VALID_WAR_LABELS:
        warnings.append(f"Invalid war label {label!r}; using negotiating")
        label = "negotiating"
    notes = str(data.get("notes") or "").strip()[:300]
    events: list[CalendarEvent] = []
    raw_events = data.get("events", [])
    if not isinstance(raw_events, list):
        warnings.append("Leadership events were not a list")
        raw_events = []
    for index, item in enumerate(raw_events):
        try:
            if not isinstance(item, dict):
                raise ValueError("event is not an object")
            title = str(item.get("title") or "").strip()
            if not title:
                raise ValueError("title is required")
            starts_at = _date(item.get("starts_at"), "starts_at")
            ends_at = _date(item["ends_at"], "ends_at") if item.get("ends_at") else None
            if ends_at and ends_at < starts_at:
                raise ValueError("ends_at is before starts_at")
            events.append(CalendarEvent(
                title=title[:80],
                starts_at=starts_at,
                ends_at=ends_at,
                description=str(item.get("description") or "").strip()[:300],
                source="faction",
                kind="faction",
                fixed_start_time=True,
            ))
        except (TypeError, ValueError) as error:
            warnings.append(f"Skipped leadership event {index + 1}: {error}")
    return label, notes, tuple(events), warnings
