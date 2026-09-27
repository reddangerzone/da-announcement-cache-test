from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any


PROFILE_RE = re.compile(r"XID=(\d+)[^>]*>([^<]+)</a>", re.IGNORECASE)


@dataclass(frozen=True)
class EnlistmentStatus:
    enlisted: bool
    cutoff: datetime
    action: str | None = None
    action_at: datetime | None = None
    actor_id: int | None = None
    actor_name: str | None = None


def previous_matching_cutoff(
    now: datetime, weekday: int = 1, hour: int = 5
) -> datetime:
    """Return the latest Tuesday 05:00 UTC/TCT at or before ``now``."""
    now = now.astimezone(UTC)
    days_since_weekday = (now.weekday() - weekday) % 7
    cutoff = (now - timedelta(days=days_since_weekday)).replace(
        hour=hour, minute=0, second=0, microsecond=0
    )
    if cutoff > now:
        cutoff -= timedelta(days=7)
    return cutoff


def parse_ranked_war_news(
    payload: dict[str, Any], *, now: datetime
) -> tuple[EnlistmentStatus, list[str]]:
    """Infer this matchmaking cycle's enlistment state from ranked-war news.

    Only enlist/unenlist actions at or after the latest Tuesday 05:00 TCT
    cutoff participate. The newest qualifying action wins.
    """
    cutoff = previous_matching_cutoff(now)
    warnings: list[str] = []
    actions: list[tuple[int, str, str]] = []

    news = payload.get("news", [])
    if not isinstance(news, list):
        return EnlistmentStatus(False, cutoff), ["Faction news did not contain a news list"]

    for index, item in enumerate(news):
        if not isinstance(item, dict):
            warnings.append(f"Skipped faction news item {index}: not an object")
            continue
        text = str(item.get("text") or "")
        if "unenlisted the faction" in text:
            action = "unenlisted"
        elif "enlisted the faction" in text:
            action = "enlisted"
        else:
            continue
        try:
            timestamp = int(item["timestamp"])
        except (KeyError, TypeError, ValueError):
            warnings.append(f"Skipped faction news item {index}: invalid timestamp")
            continue
        if datetime.fromtimestamp(timestamp, UTC) >= cutoff:
            actions.append((timestamp, action, text))

    if not actions:
        return EnlistmentStatus(False, cutoff), warnings

    timestamp, action, text = max(actions, key=lambda row: row[0])
    actor = PROFILE_RE.search(text)
    return EnlistmentStatus(
        enlisted=action == "enlisted",
        cutoff=cutoff,
        action=action,
        action_at=datetime.fromtimestamp(timestamp, UTC),
        actor_id=int(actor.group(1)) if actor else None,
        actor_name=actor.group(2).strip() if actor else None,
    ), warnings
