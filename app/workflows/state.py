"""Workflow state definitions."""

from dataclasses import dataclass, field


@dataclass(slots=True)
class WorkflowState:
    """Shared state passed across workflow nodes."""

    ticker: str = ""
    steps: list[str] = field(default_factory=list)
    payload: dict[str, object] = field(default_factory=dict)
