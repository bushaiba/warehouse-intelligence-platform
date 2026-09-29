from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

import boto3

from warehouse_intelligence.config import Settings

T = TypeVar("T")


@dataclass(frozen=True)
class StoredObject:
    key: str
    checksum: str
    size_bytes: int


def with_retry(operation: Callable[[], T], attempts: int = 3, base_delay: float = 0.15) -> T:
    """Small bounded retry helper for transient I/O. No infinite retry loops."""
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except Exception as exc:  # the caller decides which operations are safe to retry
            last_error = exc
            if attempt == attempts:
                break
            time.sleep(base_delay * attempt)
    assert last_error is not None
    raise last_error


class ObjectStore:
    def put_file(self, source: Path, key: str) -> StoredObject:
        raise NotImplementedError

    def get_file(self, key: str, destination: Path) -> Path:
        raise NotImplementedError


class LocalObjectStore(ObjectStore):
    def __init__(self, root: Path):
        self.root = root

    def put_file(self, source: Path, key: str) -> StoredObject:
        target = self.root / key
        target.parent.mkdir(parents=True, exist_ok=True)
        data = source.read_bytes()
        target.write_bytes(data)
        return StoredObject(
            key=key,
            checksum=hashlib.sha256(data).hexdigest(),
            size_bytes=len(data),
        )

    def get_file(self, key: str, destination: Path) -> Path:
        source = self.root / key
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
        return destination


class S3ObjectStore(ObjectStore):
    def __init__(self, settings: Settings):
        if not settings.aws_s3_bucket:
            raise ValueError("AWS_S3_BUCKET must be set for the s3 object-store backend")
        self.bucket = settings.aws_s3_bucket
        self.client = boto3.client(
            "s3",
            region_name=settings.aws_region,
            endpoint_url=settings.aws_s3_endpoint_url,
        )

    def put_file(self, source: Path, key: str) -> StoredObject:
        data = source.read_bytes()
        with_retry(lambda: self.client.put_object(Bucket=self.bucket, Key=key, Body=data))
        return StoredObject(
            key=key,
            checksum=hashlib.sha256(data).hexdigest(),
            size_bytes=len(data),
        )

    def get_file(self, key: str, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with_retry(lambda: self.client.download_file(self.bucket, key, str(destination)))
        return destination


def build_object_store(settings: Settings) -> ObjectStore:
    if settings.object_store_backend.lower() == "s3":
        return S3ObjectStore(settings)
    return LocalObjectStore(settings.local_object_store_path)
