"""Workflow graph definition."""


def build_workflow_graph() -> list[str]:
    """Return the logical execution path for the current workflow."""
    return ["data_retrieval", "analysis", "report", "reflection"]
