"""Supervisor agent orchestration."""

from app.workflows.nodes import get_workflow_nodes


class SupervisorAgent:
    """Coordinates the execution order of other agents."""

    def run(self) -> list[str]:
        return get_workflow_nodes()
