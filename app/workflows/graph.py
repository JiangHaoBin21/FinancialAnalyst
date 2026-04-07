"""Workflow graph definition."""

from app.workflows.nodes import get_workflow_nodes


def build_workflow_graph() -> list[str]:
    """Return the logical execution path for the current workflow."""
    return get_workflow_nodes()
