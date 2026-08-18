"""只供评测使用的工作流消融变体。"""

from __future__ import annotations

from typing import Any


SUPPORTED_VARIANTS = {"full", "no_reflection"}


class NoOpReflectionAgent:
    """不调用 LLM 的确定性直通审查，用于 Reflection 消融实验。"""

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": "reflection_done",
            "decision": "pass",
            "recommended_next_stage": "finished",
            "summary": "评测消融变体：ReflectionAgent 已禁用，报告未经深度审查。",
            "issues": [],
            "revision_instructions": [],
            "final_report_markdown": None,
            "notes_for_supervisor": ["no_reflection evaluation variant"],
        }


def apply_workflow_variant(workflow_graph: Any, variant: str) -> None:
    if variant not in SUPPORTED_VARIANTS:
        raise ValueError(f"不支持的评测变体: {variant}")
    if variant == "no_reflection":
        workflow_graph.nodes.reflection_agent = NoOpReflectionAgent()

