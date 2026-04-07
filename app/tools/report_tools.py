"""Tools for report composition."""


def render_report_payload(analysis: dict[str, object]) -> dict[str, object]:
    """Create a minimal report payload."""
    ticker = analysis.get("input", {}).get("ticker", "UNKNOWN") if isinstance(analysis.get("input"), dict) else "UNKNOWN"
    return {"ticker": ticker, "title": f"Financial report for {ticker}", "content": analysis}
