from __future__ import annotations

import argparse
import json
from pathlib import Path

from warehouse_intelligence.config import Settings, get_settings
from warehouse_intelligence.logging_utils import configure_logging
from warehouse_intelligence.pipeline import run_pipeline, summary_metrics
from warehouse_intelligence.synthetic import generate_events, write_ndjson


def demo(settings: Settings, count: int, seed: int) -> dict[str, object]:
    source = Path("runtime/input/demo-events.ndjson")
    write_ndjson(generate_events(count=count, seed=seed), source)
    result = run_pipeline(source, settings)
    result["summary"] = summary_metrics(settings)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Warehouse Intelligence Platform")
    sub = parser.add_subparsers(dest="command", required=True)

    demo_parser = sub.add_parser("demo", help="Generate synthetic events and run the pipeline")
    demo_parser.add_argument("--count", type=int, default=1000)
    demo_parser.add_argument("--seed", type=int, default=42)

    run_parser = sub.add_parser("run", help="Run the pipeline against an NDJSON file")
    run_parser.add_argument("source", type=Path)

    args = parser.parse_args()
    settings = get_settings()
    configure_logging(settings.log_level)

    if args.command == "demo":
        result = demo(settings, args.count, args.seed)
    else:
        result = run_pipeline(args.source, settings)

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
