"""Workflow node helpers."""

from app.workflows.state import WorkflowState


WORKFLOW_NODES = ["supervisor", "data", "analysis", "report", "reflection"]


def get_workflow_nodes() -> list[str]:
    """Return the nodes participating in the workflow."""
    return WORKFLOW_NODES.copy()


def initialize_state(ticker: str = "") -> WorkflowState:
    """Create a new workflow state object."""
    return WorkflowState(ticker=ticker, steps=get_workflow_nodes())
