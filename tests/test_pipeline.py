from pathlib import Path

from sqlalchemy import func, select

from warehouse_intelligence.database import (
    Base,
    CurrentContainerState,
    FactStowActivity,
    FactWarehouseEvent,
    PipelineRun,
    QualityResult,
    build_session_factory,
)
from warehouse_intelligence.pipeline import run_pipeline, summary_metrics
from warehouse_intelligence.synthetic import generate_events, write_ndjson


def _fake_parquet(events, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(b"test-parquet")
    return destination


def test_pipeline_loads_and_reconciles(tmp_path: Path, settings, monkeypatch):
    monkeypatch.setattr("warehouse_intelligence.pipeline._write_parquet", _fake_parquet)
    source = write_ndjson(generate_events(count=250, seed=12), tmp_path / "events.ndjson")
    result = run_pipeline(source, settings)

    assert result["status"] == "success"
    assert result["rows_loaded"] == 250

    engine, session_factory = build_session_factory(settings)
    Base.metadata.create_all(engine)
    with session_factory() as session:
        fact_count = session.scalar(select(func.count()).select_from(FactWarehouseEvent))
        state_count = session.scalar(select(func.count()).select_from(CurrentContainerState))
        stow_fact_count = session.scalar(
            select(func.count()).select_from(FactWarehouseEvent).where(
                FactWarehouseEvent.event_type == "stowed"
            )
        )
        stow_mart_count = session.scalar(select(func.count()).select_from(FactStowActivity))
        assert fact_count == 250
        assert state_count > 0
        assert stow_mart_count == stow_fact_count

    engine.dispose()

    metrics = summary_metrics(settings)
    assert metrics["total_events"] == 250
    assert 0 <= metrics["exception_rate"] <= 1


def test_duplicate_source_is_idempotent(tmp_path: Path, settings, monkeypatch):
    monkeypatch.setattr("warehouse_intelligence.pipeline._write_parquet", _fake_parquet)
    source = write_ndjson(generate_events(count=50, seed=3), tmp_path / "events.ndjson")
    first = run_pipeline(source, settings)
    second = run_pipeline(source, settings)

    assert first["status"] == "success"
    assert second["status"] == "skipped_duplicate"
    assert first["run_id"] == second["run_id"]

    engine, session_factory = build_session_factory(settings)
    with session_factory() as session:
        successful_runs = session.scalar(
            select(func.count()).select_from(PipelineRun).where(PipelineRun.status == "success")
        )
        assert successful_runs == 1
    engine.dispose()



def test_failed_quality_run_is_recorded(tmp_path: Path, settings, monkeypatch):
    import pytest

    monkeypatch.setattr("warehouse_intelligence.pipeline._write_parquet", _fake_parquet)
    source = write_ndjson(generate_events(count=50, seed=5), tmp_path / "events-bad.ndjson")
    with source.open("a", encoding="utf-8") as handle:
        handle.write("not-json\n")
        handle.write("still-not-json\n")

    with pytest.raises(ValueError, match="Data quality checks failed"):
        run_pipeline(source, settings)

    engine, session_factory = build_session_factory(settings)
    with session_factory() as session:
        failed_runs = session.scalar(
            select(func.count()).select_from(PipelineRun).where(PipelineRun.status == "failed")
        )
        failed_run = session.scalar(
            select(PipelineRun).where(PipelineRun.status == "failed")
        )
        quality_count = session.scalar(
            select(func.count()).select_from(QualityResult).where(
                QualityResult.run_id == failed_run.run_id
            )
        )
        assert failed_runs == 1
        assert quality_count == 3
    engine.dispose()
