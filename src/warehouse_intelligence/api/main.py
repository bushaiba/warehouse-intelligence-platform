from __future__ import annotations

from fastapi import FastAPI, HTTPException
from sqlalchemy import select

from warehouse_intelligence.config import get_settings
from warehouse_intelligence.database import (
    Base,
    CurrentContainerState,
    DailyMetric,
    QualityResult,
    build_session_factory,
)
from warehouse_intelligence.pipeline import summary_metrics

app = FastAPI(title="Warehouse Intelligence Platform", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics/summary")
def metrics_summary() -> dict[str, int | float]:
    return summary_metrics(get_settings())


@app.get("/metrics/daily")
def daily_metrics() -> list[dict[str, int | float | str]]:
    settings = get_settings()
    engine, session_factory = build_session_factory(settings)
    Base.metadata.create_all(engine)
    try:
        with session_factory() as session:
            rows = session.execute(
                select(DailyMetric).order_by(DailyMetric.metric_date)
            ).scalars().all()
            return [
                {
                    "date": row.metric_date,
                    "event_count": row.event_count,
                    "units": row.units,
                    "exception_rate": row.exception_rate,
                    "active_containers": row.active_containers,
                }
                for row in rows
            ]
    finally:
        engine.dispose()


@app.get("/containers/{container_id}")
def container_state(container_id: str) -> dict[str, object]:
    settings = get_settings()
    engine, session_factory = build_session_factory(settings)
    Base.metadata.create_all(engine)
    try:
        with session_factory() as session:
            row = session.get(CurrentContainerState, container_id)
            if not row:
                raise HTTPException(status_code=404, detail="Container not found")
            return {
                "container_id": row.container_id,
                "location": row.location,
                "sku": row.sku,
                "quantity": row.quantity,
                "station_id": row.station_id,
                "latest_event_time": row.latest_event_time,
            }
    finally:
        engine.dispose()


@app.get("/quality/latest")
def latest_quality() -> list[dict[str, object]]:
    settings = get_settings()
    engine, session_factory = build_session_factory(settings)
    Base.metadata.create_all(engine)
    try:
        with session_factory() as session:
            latest_run = session.scalar(
                select(QualityResult.run_id).order_by(QualityResult.id.desc()).limit(1)
            )
            if not latest_run:
                return []
            rows = session.execute(
                select(QualityResult)
                .where(QualityResult.run_id == latest_run)
                .order_by(QualityResult.id)
            ).scalars().all()
            return [
                {
                    "run_id": row.run_id,
                    "check": row.check_name,
                    "passed": row.passed,
                    "observed": row.observed,
                    "expected": row.expected,
                }
                for row in rows
            ]
    finally:
        engine.dispose()
