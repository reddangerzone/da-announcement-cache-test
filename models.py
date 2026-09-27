from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal


WarLabel = Literal["negotiating", "real", "termed"]


@dataclass(frozen=True)
class CalendarEvent:
    title: str
    starts_at: datetime
    ends_at: datetime | None = None
    description: str = ""
    source: Literal["torn", "faction"] = "faction"
    kind: Literal["event", "competition", "faction"] = "faction"
    fixed_start_time: bool = True

    def to_dict(self) -> dict[str, Any]:
        record = asdict(self)
        record["starts_at"] = self.starts_at.isoformat()
        record["ends_at"] = self.ends_at.isoformat() if self.ends_at else None
        return record


@dataclass(frozen=True)
class AnnouncementState:
    mode: Literal[
        "active_war",
        "matched",
        "awaiting_matchmaking",
        "not_enlisted",
        "stale",
    ]
    headline: str
    target_at: datetime | None = None
    opponent_name: str | None = None
    opponent_id: int | None = None
    war_id: int | None = None
    war_label: WarLabel | None = None
    notes: str = ""
    events: tuple[CalendarEvent, ...] = field(default_factory=tuple)
    generated_at: datetime | None = None
    stale_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        record = asdict(self)
        for key in ("target_at", "generated_at"):
            value = record[key]
            record[key] = value.isoformat() if value else None
        record["events"] = [event.to_dict() for event in self.events]
        return record
