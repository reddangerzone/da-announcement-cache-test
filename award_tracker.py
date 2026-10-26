from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable


DEFAULT_BATCH_SIZE = 25
KEEP_DAYS = 14


@dataclass(frozen=True)
class AwardSnapshot:
    today: int = 0
    event_total: int = 0
    tracking_started_at: datetime | None = None
    last_updated_at: datetime | None = None
    first_day_partial: bool = True
    top_earners: tuple[dict[str, Any], ...] = ()


def _iso(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value)).astimezone(UTC)
    except (TypeError, ValueError):
        return None


def _member_rows(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    raw = payload.get("members") or []
    if isinstance(raw, dict):
        raw = [
            dict(value, id=value.get("id") or key) if isinstance(value, dict)
            else {"id": key, "name": value}
            for key, value in raw.items()
        ]
    if not isinstance(raw, list):
        return []

    rows: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            player_id = int(item.get("id") or item.get("player_id") or item.get("user_id"))
        except (TypeError, ValueError):
            continue
        rows.append({
            "id": player_id,
            "name": str(item.get("name") or item.get("username") or f"Player {player_id}"),
        })
    return sorted(rows, key=lambda row: row["id"])


def load_award_tracker(path: Path) -> dict[str, Any]:
    try:
        tracker = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        tracker = {}
    if not isinstance(tracker, dict) or tracker.get("version") != 1:
        tracker = {}
    tracker.setdefault("version", 1)
    tracker.setdefault("started_at", None)
    tracker.setdefault("last_updated_at", None)
    tracker.setdefault("cursor", 0)
    tracker.setdefault("members", {})
    tracker.setdefault("days", {})
    return tracker


def save_award_tracker(path: Path, tracker: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(tracker, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _profile_awards(payload: dict[str, Any] | None) -> int | None:
    if not isinstance(payload, dict):
        return None
    profile = payload.get("profile")
    if not isinstance(profile, dict):
        return None
    try:
        return max(0, int(profile.get("awards")))
    except (TypeError, ValueError):
        return None


def _summary(tracker: dict[str, Any], now: datetime) -> AwardSnapshot:
    day_key = now.astimezone(UTC).date().isoformat()
    today = tracker.get("days", {}).get(day_key, {})
    member_gains = today.get("members", {}) if isinstance(today, dict) else {}
    members = tracker.get("members", {})
    top = []
    for player_id, raw_gain in member_gains.items():
        try:
            gain = int(raw_gain)
        except (TypeError, ValueError):
            continue
        member = members.get(str(player_id), {})
        top.append({
            "id": int(player_id),
            "name": member.get("name") or f"Player {player_id}",
            "awards": gain,
        })
    top.sort(key=lambda row: (-row["awards"], row["name"].casefold()))

    started = _iso(tracker.get("started_at"))
    return AwardSnapshot(
        today=int(today.get("total", 0) or 0) if isinstance(today, dict) else 0,
        event_total=sum(
            int(record.get("total", 0) or 0)
            for record in tracker.get("days", {}).values()
            if isinstance(record, dict)
        ),
        tracking_started_at=started,
        last_updated_at=_iso(tracker.get("last_updated_at")),
        first_day_partial=bool(started and started.date() == now.astimezone(UTC).date()),
        top_earners=tuple(top[:3]),
    )


def update_award_tracker(
    tracker: dict[str, Any], *, now: datetime,
    members_payload: dict[str, Any] | None,
    fetch_profile: Callable[[int], dict[str, Any] | None],
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> tuple[dict[str, Any], AwardSnapshot]:
    now = now.astimezone(UTC)
    rows = _member_rows(members_payload)
    if not rows:
        return tracker, _summary(tracker, now)

    if not tracker.get("started_at"):
        tracker["started_at"] = now.isoformat()
        # Establish the whole roster as quickly as possible on the first run.
        selected = rows
        tracker["cursor"] = 0
    else:
        cursor = int(tracker.get("cursor", 0) or 0) % len(rows)
        count = min(max(1, batch_size), len(rows))
        selected = [rows[(cursor + offset) % len(rows)] for offset in range(count)]
        tracker["cursor"] = (cursor + count) % len(rows)

    day_key = now.date().isoformat()
    day = tracker["days"].setdefault(day_key, {"total": 0, "members": {}})
    known_members = tracker["members"]
    successful = 0

    for row in selected:
        awards = _profile_awards(fetch_profile(row["id"]))
        if awards is None:
            continue
        successful += 1
        key = str(row["id"])
        previous = known_members.get(key)
        if isinstance(previous, dict) and previous.get("awards") is not None:
            try:
                delta = awards - int(previous["awards"])
            except (TypeError, ValueError):
                delta = 0
            if delta > 0:
                day["total"] = int(day.get("total", 0) or 0) + delta
                day_members = day.setdefault("members", {})
                day_members[key] = int(day_members.get(key, 0) or 0) + delta
        known_members[key] = {
            "name": row["name"],
            "awards": awards,
            "checked_at": now.isoformat(),
        }

    if successful:
        tracker["last_updated_at"] = now.isoformat()

    cutoff = now.date() - timedelta(days=KEEP_DAYS)
    tracker["days"] = {
        key: value for key, value in tracker["days"].items()
        if datetime.fromisoformat(key).date() >= cutoff
    }
    current_ids = {str(row["id"]) for row in rows}
    tracker["members"] = {
        key: value for key, value in known_members.items() if key in current_ids
    }
    return tracker, _summary(tracker, now)
