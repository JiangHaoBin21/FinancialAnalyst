"""SupervisorAgent: plans the high-level agent workflow."""

from __future__ import annotations

from app.domain.models import PlanningResult, PlanningStep as SkillPlanningStep
from app.skills.supervisor.planning_skill import PlanningSkill
from app.skills.supervisor.review_skill import SupervisorReviewSkill
from app.workflows.state import (
    OutputMode,
    PlanStep,
    TaskType,
    WorkflowState,
    WorkflowStatus,
    WorkflowStep,
    next_workflow_step,
    plan_step,
    time_range_to_state,
)


class SupervisorAgent:
    """Top-level planner.

    The supervisor decides which agents should run. It does not decide the
    internal data parts; that belongs to DataAgent.
    """

    def __init__(self, planning_skill: PlanningSkill, review_skill: SupervisorReviewSkill):
        self.planning_skill = planning_skill
        self.review_skill = review_skill

    def run(self, state: WorkflowState) -> dict:
        if not state.get("task_plan"):
            user_query = state.get("user_query")
            if not user_query or not str(user_query).strip():
                return self._empty_query_update()

            try:
                planning_result = self.planning_skill.plan_financial_task(user_query=user_query)
            except Exception as exc:
                return self._planning_exception_update(exc)

            update = self._planning_result_update(planning_result)

            if planning_result.needs_user_input:
                update.update(
                    self._waiting_for_user_input_update(
                        assistant_message=self._build_clarification_message(planning_result),
                    )
                )
                return update

            update.update(self._ready_for_execution_update(planning_result, update["task_plan"]))
            return update

        else:
            update = self.review_skill.review(
                user_query=state["user_query"],
                analysis_focus=state["analysis_focus"],
                last_completed_stage=state["last_completed_stage"],
                stage_outputs=state["stage_outputs"],
                next_step=state["next_step"]
            )
            current_index = -1
            agent_step_map = {
                "DataAgent": WorkflowStep.DATA.value,
                "AnalysisAgent": WorkflowStep.ANALYSIS.value,
                "ReportAgent": WorkflowStep.REPORT.value,
                "ReflectionAgent": WorkflowStep.REFLECTION.value,
            }
            if not update.get("review_passed"):
                for index, item in enumerate(state["task_plan"]):
                    # if agent_step_map.get(item["agent"]) == update["next_step"]:
                    if item["agent"] == update["next_step"]:
                        current_index = index
                        break
                update["current_step_index"] = current_index
            update.pop("review_passed")
            return update


    def _planning_result_update(self, planning_result: PlanningResult) -> dict:
        task_plan = [self._to_state_plan_step(step) for step in planning_result.task_plan]
        return {
            "task_type": self._to_task_type(planning_result.task_type),
            "company_name": planning_result.company_name,
            "ts_code": planning_result.ts_code,
            "time_range": time_range_to_state(planning_result.time_range),
            "analysis_focus": planning_result.analysis_focus,
            "output_mode": self._to_output_mode(planning_result.output_mode),
            "planner_message": planning_result.planner_message,
            "needs_user_input": planning_result.needs_user_input,
            "missing_fields": list(planning_result.missing_fields or []),
            "raw_planner_response": planning_result.raw_response,
            "task_plan": task_plan,
            "current_step_index": 0,
            "completed_step_ids": [],
            "current_stage": WorkflowStep.SUPERVISOR.value,
            "next_step": None,
            "has_error": False,
            "error_message": None,
            "is_finished": False,
        }

    @staticmethod
    def _waiting_for_user_input_update(assistant_message: str) -> dict:
        return {
            "status": WorkflowStatus.NEEDS_USER_INPUT.value,
            "current_stage": WorkflowStep.AWAIT_USER_INPUT.value,
            "next_step": WorkflowStep.AWAIT_USER_INPUT.value,
            "assistant_message": assistant_message,
            "is_finished": False,
            "has_error": False,
            "error_message": None,
        }

    def _ready_for_execution_update(
        self,
        planning_result: PlanningResult,
        task_plan: list[PlanStep],
    ) -> dict:
        next_step = next_workflow_step(task_plan, 0)
        assistant_message = self._build_ready_message(planning_result)
        update = {
            "status": WorkflowStatus.READY_FOR_EXECUTION.value,
            "current_stage": WorkflowStep.SUPERVISOR.value,
            "next_step": next_step,
            "assistant_message": assistant_message,
            "is_finished": False,
            "has_error": False,
            "error_message": None,
        }

        if next_step == WorkflowStep.ERROR.value:
            update.update(
                {
                    "has_error": True,
                    "status": WorkflowStatus.ERROR.value,
                    "error_message": "Planner task_plan cannot be mapped to workflow steps.",
                    "assistant_message": "Planner task_plan cannot be mapped to workflow steps.",
                }
            )

        return update

    @staticmethod
    def _empty_query_update() -> dict:
        return {
            "status": WorkflowStatus.NEEDS_USER_INPUT.value,
            "current_stage": WorkflowStep.AWAIT_USER_INPUT.value,
            "next_step": WorkflowStep.AWAIT_USER_INPUT.value,
            "needs_user_input": True,
            "missing_fields": ["task_description"],
            "assistant_message": (
                "Please tell me which company to analyze and what you want to know."
            ),
            "is_finished": False,
            "has_error": False,
            "error_message": None,
        }

    @staticmethod
    def _planning_exception_update(exc: Exception) -> dict:
        return {
            "status": WorkflowStatus.ERROR.value,
            "current_stage": WorkflowStep.SUPERVISOR.value,
            "next_step": WorkflowStep.ERROR.value,
            "needs_user_input": False,
            "assistant_message": "Planning failed; the workflow cannot continue.",
            "error_message": f"{type(exc).__name__}: {exc}",
            "has_error": True,
            "is_finished": False,
        }

    @staticmethod
    def _build_clarification_message(planning_result: PlanningResult) -> str:
        missing = set(planning_result.missing_fields or [])
        if "company_name_or_ts_code" in missing:
            return "Please provide the company name or stock code, such as 300750.SZ."

        prompts: list[str] = []
        if "company_name" in missing:
            prompts.append("company name")
        if "ts_code" in missing:
            prompts.append("stock code")
        if "time_range" in missing:
            prompts.append("time range")
        if "analysis_focus" in missing:
            prompts.append("analysis focus")
        if "task_description" in missing:
            prompts.append("task description")

        if prompts:
            return "Please provide: " + ", ".join(prompts) + "."

        return "Please provide more information so I can plan the analysis."

    def _build_ready_message(self, planning_result: PlanningResult) -> str:
        company = planning_result.company_name or planning_result.ts_code or "target company"
        time_range_text = self._format_time_range(planning_result.time_range)
        focus = planning_result.analysis_focus or "overall financial performance"

        if planning_result.output_mode == "summary":
            return f"Planning complete. I will summarize {company} for {time_range_text}: {focus}."

        return f"Planning complete. I will analyze {company} for {time_range_text}: {focus}."

    @staticmethod
    def _format_time_range(time_range) -> str:
        if not time_range:
            return "the default period"
        return (
            f"{time_range.start_year}.{time_range.start_month:02d} - "
            f"{time_range.end_year}.{time_range.end_month:02d}"
        )

    @staticmethod
    def _to_task_type(value: str) -> str:
        if value == "financial_analysis":
            return TaskType.FINANCIAL_ANALYSIS.value
        return TaskType.UNKNOWN.value

    @staticmethod
    def _to_output_mode(value: str) -> str:
        if value == "summary":
            return OutputMode.SUMMARY.value
        return OutputMode.REPORT.value

    @staticmethod
    def _to_state_plan_step(step: SkillPlanningStep) -> PlanStep:
        return plan_step(
            step_id=step.step_id,
            agent=step.agent,
            action=step.action,
            description=step.description,
        )
