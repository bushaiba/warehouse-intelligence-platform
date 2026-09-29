from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class EventType(StrEnum):
    RECEIVED = "received"
    MOVED = "moved"
    STOWED = "stowed"
    EXCEPTION = "exception"


class WarehouseEvent(BaseModel):
    event_id: str = Field(min_length=8)
    event_type: EventType
    event_time: datetime
    warehouse_id: str = Field(pattern=r"^[A-Z0-9_-]{2,20}$")
    container_id: str = Field(min_length=4)
    sku: str = Field(min_length=4)
    quantity: int = Field(ge=0, le=10000)
    location: str = Field(min_length=2)
    station_id: str | None = None
    associate_id: str | None = None
    source: str = "synthetic-generator"

    @field_validator("event_id", "container_id", "sku", "location")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class QualityCheck(BaseModel):
    name: str
    passed: bool
    observed: int | float | str
    expected: str
