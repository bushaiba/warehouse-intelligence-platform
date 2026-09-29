from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from pydantic import ValidationError
from sqlalchemy import delete, func, select

from warehouse_intelligence.config import Settings
from warehouse_intelligence.database import (
    Base,
    CurrentContainerState,
    DailyMetric,
    DimAssociate,
    DimSku,
    DimStation,
    FactStowActivity,
    FactWarehouseEvent,
    PipelineRun,
    QualityResult,
    build_session_factory,
)
from warehouse_intelligence.logging_utils import log_event
from warehouse_intelligence.models import QualityCheck, WarehouseEvent
from warehouse_intelligence.storage import build_object_store

LOGGER = logging.getLogger(__name__)


def _raw_key(checksum: str) -> str:
    return f"raw/events/{checksum}.ndjson"


def _curated_key(run_id: str) -> str:
    return f"curated/events/{run_id}.parquet"


def _read_and_validate(path: Path) -> tuple[list[WarehouseEvent], int]:
    valid: list[WarehouseEvent] = []
    rejected = 0
    seen: set[str] = set()

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                event = WarehouseEvent.model_validate(json.loads(line))
            except (json.JSONDecodeError, ValidationError):
                rejected += 1
                continue

            if event.event_id in seen:
                continue

            seen.add(event.event_id)
            valid.append(event)

    return valid, rejected


def _write_parquet(events: list[WarehouseEvent], destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame([event.model_dump(mode="json") for event in events])
    frame.to_parquet(destination, index=False)
    return destination


def _quality_checks(events: list[WarehouseEvent], rejected: int) -> list[QualityCheck]:
    unique_ids = len({event.event_id for event in events})
    return [
        QualityCheck(
            name="event_ids_unique",
            passed=unique_ids == len(events),
            observed=unique_ids,
            expected=f"{len(events)} unique event ids",
        ),
        QualityCheck(
            name="valid_quantities",
            passed=all(event.quantity >= 0 for event in events),
            observed=min((event.quantity for event in events), default=0),
            expected="minimum quantity >= 0",
        ),
        QualityCheck(
            name="rejected_row_rate",
            passed=(rejected / max(len(events) + rejected, 1)) <= 0.02,
            observed=round(rejected / max(len(events) + rejected, 1), 4),
            expected="<= 0.02",
        ),
    ]


def _save_quality_results(session, run_id: str, checks: list[QualityCheck]) -> None:
    session.execute(delete(QualityResult).where(QualityResult.run_id == run_id))
    for check in checks:
        session.add(
            QualityResult(
                run_id=run_id,
                check_name=check.name,
                passed=check.passed,
                observed=str(check.observed),
                expected=check.expected,
            )
        )


def _load_event_facts(session, events: list[WarehouseEvent]) -> int:
    loaded = 0
    for event in events:
        if session.get(FactWarehouseEvent, event.event_id):
            continue

        session.add(
            FactWarehouseEvent(
                event_id=event.event_id,
                event_type=event.event_type.value,
                event_time=event.event_time,
                warehouse_id=event.warehouse_id,
                container_id=event.container_id,
                sku=event.sku,
                quantity=event.quantity,
                location=event.location,
                station_id=event.station_id,
                associate_id=event.associate_id,
                source=event.source,
            )
        )
        loaded += 1

    session.flush()
    return loaded


def _load_stow_mart(session, events: list[WarehouseEvent]) -> None:
    sku_keys = {
        row.sku: row.sku_key for row in session.execute(select(DimSku)).scalars().all()
    }
    station_keys = {
        row.station_id: row.station_key
        for row in session.execute(select(DimStation)).scalars().all()
    }
    associate_keys = {
        row.associate_id: row.associate_key
        for row in session.execute(select(DimAssociate)).scalars().all()
    }

    for event in events:
        if (
            event.event_type.value != "stowed"
            or event.station_id is None
            or event.associate_id is None
        ):
            continue

        station_id = event.station_id
        associate_id = event.associate_id

        if event.sku not in sku_keys:
            sku_dim = DimSku(sku=event.sku)
            session.add(sku_dim)
            session.flush()
            sku_keys[event.sku] = sku_dim.sku_key

        if station_id not in station_keys:
            station_dim = DimStation(station_id=station_id)
            session.add(station_dim)
            session.flush()
            station_keys[station_id] = station_dim.station_key

        if associate_id not in associate_keys:
            associate_dim = DimAssociate(associate_id=associate_id)
            session.add(associate_dim)
            session.flush()
            associate_keys[associate_id] = associate_dim.associate_key

        if session.get(FactStowActivity, event.event_id):
            continue

        session.add(
            FactStowActivity(
                event_id=event.event_id,
                event_time=event.event_time,
                sku_key=sku_keys[event.sku],
                station_key=station_keys[station_id],
                associate_key=associate_keys[associate_id],
                units=event.quantity,
            )
        )

    session.flush()


def _rebuild_current_state(session) -> None:
    # Rebuild from fact history so repeated or partial runs cannot silently drift state.
    session.execute(delete(CurrentContainerState))
    latest_rows = session.execute(
        select(FactWarehouseEvent).order_by(
            FactWarehouseEvent.container_id,
            FactWarehouseEvent.event_time.desc(),
            FactWarehouseEvent.event_id.desc(),
        )
    ).scalars()

    latest_by_container: dict[str, FactWarehouseEvent] = {}
    for row in latest_rows:
        latest_by_container.setdefault(row.container_id, row)

    for row in latest_by_container.values():
        session.add(
            CurrentContainerState(
                container_id=row.container_id,
                latest_event_id=row.event_id,
                latest_event_time=row.event_time,
                location=row.location,
                sku=row.sku,
                quantity=row.quantity,
                station_id=row.station_id,
            )
        )


def _rebuild_daily_metrics(session) -> None:
    session.execute(delete(DailyMetric))
    rows = session.execute(select(FactWarehouseEvent)).scalars().all()
    by_day: dict[str, list[FactWarehouseEvent]] = {}

    for row in rows:
        by_day.setdefault(row.event_time.date().isoformat(), []).append(row)

    for day, day_rows in by_day.items():
        exceptions = sum(row.event_type == "exception" for row in day_rows)
        session.add(
            DailyMetric(
                metric_date=day,
                event_count=len(day_rows),
                units=sum(row.quantity for row in day_rows),
                exception_rate=round(exceptions / max(len(day_rows), 1), 4),
                active_containers=len({row.container_id for row in day_rows}),
            )
        )


def run_pipeline(source_file: Path, settings: Settings) -> dict[str, object]:
    """Run one idempotent batch from raw file to curated storage and warehouse tables."""
    run_id = str(uuid.uuid4())
    checksum = hashlib.sha256(source_file.read_bytes()).hexdigest()
    store = build_object_store(settings)

    engine, session_factory = build_session_factory(settings)
    Base.metadata.create_all(engine)

    try:
        with session_factory() as session:
            existing = session.scalar(
                select(PipelineRun)
                .where(
                    PipelineRun.source_checksum == checksum,
                    PipelineRun.status == "success",
                )
                .order_by(PipelineRun.started_at.desc())
            )
            if existing:
                log_event(LOGGER, "pipeline.skipped_duplicate", checksum=checksum)
                return {
                    "run_id": existing.run_id,
                    "status": "skipped_duplicate",
                    "rows_loaded": existing.rows_loaded,
                    "rejected_rows": existing.rejected_rows,
                }

            raw_object = store.put_file(source_file, _raw_key(checksum))
            run = PipelineRun(
                run_id=run_id,
                started_at=datetime.now(UTC),
                status="running",
                source_key=raw_object.key,
                source_checksum=checksum,
            )
            session.add(run)
            session.commit()

            try:
                events, rejected = _read_and_validate(source_file)
                curated_path = Path("runtime") / "curated" / f"{run_id}.parquet"
                _write_parquet(events, curated_path)
                store.put_file(curated_path, _curated_key(run_id))

                checks = _quality_checks(events, rejected)
                _save_quality_results(session, run_id, checks)

                if not all(check.passed for check in checks):
                    run.rows_read = len(events) + rejected
                    run.rows_loaded = 0
                    run.rejected_rows = rejected
                    run.status = "failed"
                    run.finished_at = datetime.now(UTC)
                    session.commit()
                    raise ValueError("Data quality checks failed")

                loaded = _load_event_facts(session, events)
                _load_stow_mart(session, events)
                _rebuild_current_state(session)
                _rebuild_daily_metrics(session)

                run.rows_read = len(events) + rejected
                run.rows_loaded = loaded
                run.rejected_rows = rejected
                run.status = "success"
                run.finished_at = datetime.now(UTC)
                session.commit()

                log_event(LOGGER, "pipeline.completed", run_id=run_id, rows_loaded=loaded)
                return {
                    "run_id": run_id,
                    "status": "success",
                    "rows_loaded": loaded,
                    "rejected_rows": rejected,
                    "curated_key": _curated_key(run_id),
                }
            except Exception:
                session.rollback()
                run = session.get(PipelineRun, run_id)
                if run and run.status != "failed":
                    run.status = "failed"
                    run.finished_at = datetime.now(UTC)
                    session.commit()
                LOGGER.exception("pipeline failed")
                raise
    finally:
        engine.dispose()


def summary_metrics(settings: Settings) -> dict[str, int | float]:
    engine, session_factory = build_session_factory(settings)
    Base.metadata.create_all(engine)
    try:
        with session_factory() as session:
            total_events = session.scalar(
                select(func.count()).select_from(FactWarehouseEvent)
            ) or 0
            containers = session.scalar(
                select(func.count()).select_from(CurrentContainerState)
            ) or 0
            exceptions = session.scalar(
                select(func.count()).select_from(FactWarehouseEvent).where(
                    FactWarehouseEvent.event_type == "exception"
                )
            ) or 0
            return {
                "total_events": int(total_events),
                "active_containers": int(containers),
                "exception_rate": round(exceptions / max(total_events, 1), 4),
            }
    finally:
        engine.dispose()
