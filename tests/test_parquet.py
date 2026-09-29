from pathlib import Path

import pytest

from warehouse_intelligence.pipeline import _write_parquet
from warehouse_intelligence.synthetic import generate_events

pytest.importorskip("pyarrow")


def test_curated_layer_is_real_parquet(tmp_path: Path):
    destination = _write_parquet(generate_events(count=10, seed=4), tmp_path / "events.parquet")
    assert destination.exists()
    assert destination.read_bytes()[:4] == b"PAR1"
