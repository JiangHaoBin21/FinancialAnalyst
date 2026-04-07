"""Tools for persistence-related helper payloads."""


def build_review_snapshot(report: dict[str, object]) -> dict[str, object]:
    """Create a snapshot payload for audit or persistence layers."""
    return {"keys": sorted(report.keys()), "snapshot_status": "created"}
