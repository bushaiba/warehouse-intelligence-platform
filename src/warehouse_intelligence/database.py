from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from warehouse_intelligence.config import Settings


class Base(DeclarativeBase):
    pass


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    run_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20))
    source_key: Mapped[str] = mapped_column(Text)
    source_checksum: Mapped[str] = mapped_column(String(64), index=True)
    rows_read: Mapped[int] = mapped_column(Integer, default=0)
    rows_loaded: Mapped[int] = mapped_column(Integer, default=0)
    rejected_rows: Mapped[int] = mapped_column(Integer, default=0)


class FactWarehouseEvent(Base):
    __tablename__ = "fact_warehouse_event"
    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(30), index=True)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    warehouse_id: Mapped[str] = mapped_column(String(20), index=True)
    container_id: Mapped[str] = mapped_column(String(30), index=True)
    sku: Mapped[str] = mapped_column(String(40), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    location: Mapped[str] = mapped_column(String(50), index=True)
    station_id: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    associate_id: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(50))


class DimSku(Base):
    __tablename__ = "dim_sku"
    sku_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(String(40), unique=True, index=True)


class DimStation(Base):
    __tablename__ = "dim_station"
    station_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    station_id: Mapped[str] = mapped_column(String(30), unique=True, index=True)


class DimAssociate(Base):
    __tablename__ = "dim_associate"
    associate_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    associate_id: Mapped[str] = mapped_column(String(30), unique=True, index=True)


class FactStowActivity(Base):
    __tablename__ = "fact_stow_activity"
    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    sku_key: Mapped[int] = mapped_column(ForeignKey("dim_sku.sku_key"), index=True)
    station_key: Mapped[int] = mapped_column(ForeignKey("dim_station.station_key"), index=True)
    associate_key: Mapped[int] = mapped_column(
        ForeignKey("dim_associate.associate_key"), index=True
    )
    units: Mapped[int] = mapped_column(Integer)


class CurrentContainerState(Base):
    __tablename__ = "current_container_state"
    container_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    latest_event_id: Mapped[str] = mapped_column(String(36), unique=True)
    latest_event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    location: Mapped[str] = mapped_column(String(50), index=True)
    sku: Mapped[str] = mapped_column(String(40))
    quantity: Mapped[int] = mapped_column(Integer)
    station_id: Mapped[str | None] = mapped_column(String(30), nullable=True)


class QualityResult(Base):
    __tablename__ = "quality_results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(36), index=True)
    check_name: Mapped[str] = mapped_column(String(100))
    passed: Mapped[bool] = mapped_column(Boolean)
    observed: Mapped[str] = mapped_column(Text)
    expected: Mapped[str] = mapped_column(Text)


class DailyMetric(Base):
    __tablename__ = "daily_metrics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    metric_date: Mapped[str] = mapped_column(String(10), index=True)
    event_count: Mapped[int] = mapped_column(Integer)
    units: Mapped[int] = mapped_column(Integer)
    exception_rate: Mapped[float] = mapped_column(Float)
    active_containers: Mapped[int] = mapped_column(Integer)


def build_engine(settings: Settings):
    connect_args = (
        {"check_same_thread": False}
        if settings.database_url.startswith("sqlite")
        else {}
    )
    return create_engine(settings.database_url, future=True, connect_args=connect_args)


def build_session_factory(settings: Settings):
    engine = build_engine(settings)
    return engine, sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
