from __future__ import annotations

from pathlib import Path

import pytest

from warehouse_intelligence.config import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'warehouse.db'}",
        object_store_backend="local",
        local_object_store_path=tmp_path / "object-store",
    )
