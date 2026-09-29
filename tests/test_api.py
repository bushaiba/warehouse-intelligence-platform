from pathlib import Path

from fastapi.testclient import TestClient

from warehouse_intelligence.api.main import app
from warehouse_intelligence.pipeline import run_pipeline
from warehouse_intelligence.synthetic import generate_events, write_ndjson


def _fake_parquet(events, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(b"test-parquet")
    return destination


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_operational_endpoints(tmp_path: Path, settings, monkeypatch):
    monkeypatch.setattr("warehouse_intelligence.pipeline._write_parquet", _fake_parquet)
    monkeypatch.setattr("warehouse_intelligence.api.main.get_settings", lambda: settings)

    events = generate_events(count=80, seed=9)
    source = write_ndjson(events, tmp_path / "api-events.ndjson")
    run_pipeline(source, settings)

    client = TestClient(app)

    summary = client.get("/metrics/summary")
    assert summary.status_code == 200
    assert summary.json()["total_events"] == 80

    daily = client.get("/metrics/daily")
    assert daily.status_code == 200
    assert len(daily.json()) >= 1

    container = client.get(f"/containers/{events[0].container_id}")
    assert container.status_code == 200
    assert container.json()["container_id"] == events[0].container_id

    missing = client.get("/containers/C-DOES-NOT-EXIST")
    assert missing.status_code == 404

    quality = client.get("/quality/latest")
    assert quality.status_code == 200
    assert quality.json()
    assert all(row["passed"] for row in quality.json())
