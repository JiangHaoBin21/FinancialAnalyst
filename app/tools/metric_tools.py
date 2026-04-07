"""Tools for metric computation."""


def calculate_placeholder_metrics(payload: dict[str, object]) -> dict[str, object]:
    """Return basic metrics for scaffolding purposes."""
    ticker = str(payload.get("ticker", "UNKNOWN"))
    return {"ticker": ticker, "score": 0.0, "status": "not_computed"}
