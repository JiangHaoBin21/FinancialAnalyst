"""Compute financial metrics."""

from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.metric_engine_service import MetricEngineService


def main() -> None:
    """Run the metric computation placeholder."""
    service = MetricEngineService()
    print(service.compute({"ticker": "DEMO"}))


if __name__ == "__main__":
    main()
