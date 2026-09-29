from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), format="%(message)s")


def log_event(logger: logging.Logger, event: str, **details: Any) -> None:
    payload = {
        "ts": datetime.now(UTC).isoformat(),
        "event": event,
        **details,
    }
    logger.info(json.dumps(payload, default=str, sort_keys=True))
