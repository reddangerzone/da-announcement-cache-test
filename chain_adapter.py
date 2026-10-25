from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

TARGET_HITS = 50_000
PACE_WINDOW = timedelta(hours=3)


@dataclass(frozen=True)
class ChainSnapshot:
    active: bool = False
    current: int = 0
    target: int = TARGET_HITS
    rate_per_hour: float | None = None
    estimated_finish: datetime | None = None
    top_hitters: tuple[dict[str, Any], ...] = ()


def current_chain(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    chain = payload.get("chain")
    return chain if isinstance(chain, dict) else {}


def chain_number(chain: dict[str, Any], key: str, default: int = 0) -> int:
    try:
        return max(0, int(chain.get(key, default) or default))
    except (TypeError, ValueError):
        return default


def parse_top_hitters(payload: dict[str, Any] | None, limit: int = 3) -> tuple[dict[str, Any], ...]:
    if not isinstance(payload, dict):
        return ()

    # The live chain report is the authoritative source for per-member hits.
    # Torn v2 returns: chainreport -> attackers -> attacks -> total.
    report = payload.get("chainreport")
    raw: Any = report.get("attackers", []) if isinstance(report, dict) else None

    # Retain support for the older contributors payload shapes.
    if raw is None:
        raw = payload.get("contributors") or []
        if isinstance(raw, dict):
            grouped_rows = [
                item
                for value in raw.values()
                if isinstance(value, list)
                for item in value
            ]
            if grouped_rows:
                raw = grouped_rows

    if isinstance(raw, dict):
        raw = [
            dict(value, id=value.get("id") or key) if isinstance(value, dict)
            else {"id": key, "value": value}
            for key, value in raw.items()
        ]
    if not isinstance(raw, list):
        return ()

    parsed: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        player = item.get("player") if isinstance(item.get("player"), dict) else {}
        user = item.get("user") if isinstance(item.get("user"), dict) else {}
        attacks = item.get("attacks") if isinstance(item.get("attacks"), dict) else {}
        name = (
            item.get("username") or item.get("name") or item.get("player_name")
            or player.get("name") or player.get("username")
            or user.get("name") or user.get("username") or "Unknown"
        )
        value = attacks.get("total")
        if value is None:
            value = next(
                (item.get(key) for key in ("contributed", "value", "amount", "chainhits", "chain_hits", "hits")
                 if item.get(key) is not None),
                0,
            )
        try:
            hits = max(0, int(value))
        except (TypeError, ValueError):
            continue
        player_id = (
            item.get("id") or item.get("player_id") or item.get("user_id")
            or player.get("id") or user.get("id")
        )
        parsed.append({"id": player_id, "name": str(name), "hits": hits})
    return tuple(sorted(parsed, key=lambda row: (-row["hits"], row["name"].lower()))[:limit])

def halloween_event_started(events: Iterable[Any], now: datetime) -> bool:
    now = now.astimezone(UTC)
    return any(
        "trick or treat" in event.title.casefold() and event.starts_at.astimezone(UTC) <= now
        for event in events
    )


def load_tracker(path: Path, year: int) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        data = {}
    if data.get("year") != year:
        return {"year": year, "activated": False, "complete": False, "chain_id": None,
                "samples": [], "top_hitters": []}
    data.setdefault("activated", False)
    data.setdefault("complete", False)
    data.setdefault("chain_id", None)
    data.setdefault("samples", [])
    data.setdefault("top_hitters", [])
    return data


def save_tracker(path: Path, tracker: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(tracker, indent=2) + "\n", encoding="utf-8")


def update_tracker(
    tracker: dict[str, Any], *, now: datetime, event_started: bool,
    chain_payload: dict[str, Any] | None, contributors_payload: dict[str, Any] | None,
    target: int = TARGET_HITS,
) -> tuple[dict[str, Any], ChainSnapshot]:
    now = now.astimezone(UTC)
    tracker["activated"] = bool(tracker.get("activated") or event_started)
    chain = current_chain(chain_payload)
    current = chain_number(chain, "current")
    chain_id = chain.get("id")

    if tracker.get("activated") and not tracker.get("complete"):
        if chain_id and tracker.get("chain_id") not in (None, chain_id):
            tracker["samples"] = []
        if chain_id:
            tracker["chain_id"] = chain_id
        if current >= target:
            tracker["complete"] = True

    active = bool(tracker.get("activated") and not tracker.get("complete"))
    if not active:
        return tracker, ChainSnapshot()

    cutoff = now - PACE_WINDOW
    samples = []
    for sample in tracker.get("samples", []):
        try:
            stamp = datetime.fromisoformat(sample["at"]).astimezone(UTC)
            hits = int(sample["hits"])
        except (KeyError, TypeError, ValueError):
            continue
        if stamp >= cutoff and hits <= current:
            samples.append({"at": stamp.isoformat(), "hits": hits})
    samples.append({"at": now.isoformat(), "hits": current})
    tracker["samples"] = samples

    top_hitters = parse_top_hitters(contributors_payload)
    if top_hitters:
        tracker["top_hitters"] = list(top_hitters)
    else:
        top_hitters = tuple(tracker.get("top_hitters", []))

    rate = None
    estimate = None
    if len(samples) >= 2:
        first = samples[0]
        first_at = datetime.fromisoformat(first["at"])
        elapsed_hours = (now - first_at).total_seconds() / 3600
        gained = current - int(first["hits"])
        if elapsed_hours >= 0.20 and gained > 0:
            rate = gained / elapsed_hours
            estimate = now + timedelta(hours=max(0, target - current) / rate)

    return tracker, ChainSnapshot(
        active=True, current=current, target=target, rate_per_hour=rate,
        estimated_finish=estimate, top_hitters=top_hitters,
    )
