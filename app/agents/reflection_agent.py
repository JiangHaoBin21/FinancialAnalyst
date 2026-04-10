"""ReflectionAgent: 最小可运行 stub 版本。"""

from __future__ import annotations

from app.workflows.state import WorkflowState


class ReflectionAgent:
    """
    最小版 ReflectionAgent：
    - 默认直接通过
    - 不触发回退、不重规划
    """

    def run(self, state: WorkflowState) -> WorkflowState:
        print("[ReflectionAgent] running...")

        state.reflection_result = {
            "passed": True,
            "issues": [],
            "suggestions": [],
        }

        state.needs_revision = False
        state.replan_required = False
        state.assistant_message = "ReflectionAgent 审查通过。"
        return state