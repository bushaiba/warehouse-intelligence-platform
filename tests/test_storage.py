from pathlib import Path

from warehouse_intelligence.storage import LocalObjectStore, with_retry


def test_local_object_store_round_trip(tmp_path: Path):
    source = tmp_path / "source.txt"
    source.write_text("warehouse-data", encoding="utf-8")
    store = LocalObjectStore(tmp_path / "objects")
    saved = store.put_file(source, "raw/source.txt")
    destination = tmp_path / "downloaded.txt"
    store.get_file(saved.key, destination)

    assert destination.read_text(encoding="utf-8") == "warehouse-data"
    assert len(saved.checksum) == 64



def test_retry_recovers_from_transient_failure():
    attempts = {"count": 0}

    def flaky_operation():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise OSError("temporary")
        return "ok"

    assert with_retry(flaky_operation, attempts=3, base_delay=0) == "ok"
    assert attempts["count"] == 3


def test_retry_stops_after_limit():
    import pytest

    def broken_operation():
        raise OSError("still broken")

    with pytest.raises(OSError, match="still broken"):
        with_retry(broken_operation, attempts=2, base_delay=0)
