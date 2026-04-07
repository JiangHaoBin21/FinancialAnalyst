"""Application entrypoint for the FinancialAnalyst project."""

from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.routes import register_routes
from app.workflows.graph import build_workflow_graph


def create_app() -> dict[str, object]:
    """Return a minimal app descriptor for the current project layout."""
    return {
        "name": "FinancialAnalyst",
        "status": "initialized",
        "routes": register_routes(),
        "workflow": build_workflow_graph(),
    }


if __name__ == "__main__":
    application = create_app()
    print(
        f"{application['name']} is {application['status']} "
        f"with {len(application['routes'])} routes."
    )
