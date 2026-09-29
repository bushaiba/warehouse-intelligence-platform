from __future__ import annotations

import json
import random
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from warehouse_intelligence.models import EventType, WarehouseEvent

LOCATIONS = ["RECEIVE-01", "BUFFER-01", "BUFFER-02", "LEVEL-1", "LEVEL-2", "LEVEL-3"]
STATIONS = [f"ST-{number:03d}" for number in range(1, 25)]
SKUS = [f"SKU-{number:05d}" for number in range(1, 101)]
ASSOCIATES = [f"A-{number:04d}" for number in range(1, 41)]


def generate_events(count: int = 1000, seed: int = 42) -> list[WarehouseEvent]:
    """Generate repeatable warehouse events without using real company data."""
    rng = random.Random(seed)
    start = datetime(2026, 1, 15, 7, 0, tzinfo=UTC)
    containers = [f"C-{number:06d}" for number in range(1, max(20, count // 8) + 1)]

    events: list[WarehouseEvent] = []
    for index in range(count):
        event_type = rng.choices(
            list(EventType),
            weights=[15, 30, 50, 5],
            k=1,
        )[0]
        events.append(
            WarehouseEvent(
                event_id=str(uuid.UUID(int=rng.getrandbits(128))),
                event_type=event_type,
                event_time=start + timedelta(seconds=index * rng.randint(8, 45)),
                warehouse_id="WH-DEMO",
                container_id=rng.choice(containers),
                sku=rng.choice(SKUS),
                quantity=rng.randint(1, 30),
                location=rng.choice(LOCATIONS),
                station_id=rng.choice(STATIONS) if event_type == EventType.STOWED else None,
                associate_id=(
                    rng.choice(ASSOCIATES)
                    if event_type in {EventType.STOWED, EventType.MOVED}
                    else None
                ),
            )
        )
    return events


def write_ndjson(events: list[WarehouseEvent], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event.model_dump(mode="json"), sort_keys=True) + "\n")
    return path
