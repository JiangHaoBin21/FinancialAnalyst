"""ReflectionAgent: minimal review implementation."""

from __future__ import annotations

from app.workflows.state import WorkflowState


class ReflectionAgent:
    """Reviews the report and passes by default."""

    def run(self, state: WorkflowState) -> dict:
        print("[ReflectionAgent] 正在执行...")

        return {
            "reflection_result": {
                "passed": True,
                "issues": [],
                "suggestions": [],
            },
            "needs_revision": False,
            "replan_required": False,
            "assistant_message": "ReflectionAgent 审查通过。",
        }
