# app/workflows/subgraphs/data_nodes.py

"""DataSubgraph 节点实现。"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Optional

from sqlalchemy.exc import MultipleResultsFound

from app.exceptions.data_exception import CompanyNotFoundError
from app.workflows.state import (
    DATA_PART_BALANCE,
    DATA_PART_CASHFLOW,
    DATA_PART_COMPANY_PROFILE,
    DATA_PART_INCOME,
    DATA_PART_INDICATORS,
    DataPartResult,
    PlanStepStatus,
    WorkflowState,
    WorkflowStatus,
    WorkflowStep,
    complete_current_plan_step,
    error_update,
    execution_record,
    fail_current_plan_step,
    is_current_plan_agent,
    update_current_plan_step_status,
)


class DataSubgraphNodes:
    """DataSubgraph 内部节点集合。

    只负责 LangGraph node 层：
    - 读取 WorkflowState
    - 调用 DataAgent / Skill
    - 返回 partial state update

    不负责：
    - 直接实现 TuShare 细节
    - 直接实现 repo 查询细节
    - 直接实现 LLM prompt 细节
    """

    def __init__(
        self,
        *,
        data_agent: Optional[Any] = None,
        company_profile_fetch_skill: Optional[Any] = None,
        data_preparation_skill: Optional[Any] = None,
        completeness_checker_skill: Optional[Any] = None,
    ):
        self.data_agent = data_agent
        self.company_profile_fetch_skill = company_profile_fetch_skill
        self.data_preparation_skill = data_preparation_skill
        self.completeness_checker_skill = completeness_checker_skill

    def data_planner_node(self, state: WorkflowState) -> dict:
        """运行 DataAgent，规划后续需要并行抓取的数据分片。"""
        if self.data_agent is None:
            return self._node_error(
                state=state,
                node_step=WorkflowStep.DATA,
                agent_name="DataAgent",
                message="DataAgent is not configured.",
            )

        if not is_current_plan_agent(state, "DataAgent"):
            return self._node_error(
                state=state,
                node_step=WorkflowStep.DATA,
                agent_name="DataAgent",
                message="Current plan step does not match DataAgent.",
            )

        try:
            update = self.data_agent.run(state)
        except Exception as exc:
            return self._node_error(
                state=state,
                node_step=WorkflowStep.DATA,
                agent_name="DataAgent",
                message=f"DataAgent failed: {type(exc).__name__}: {exc}",
            )

        required_parts = list(update.get("required_data_parts", []))
        message = update.get("assistant_message") or "DataAgent planned data requirements."

        return {
            **update,
            "current_stage": WorkflowStep.DATA,
            "status": WorkflowStatus.DATA_PLANNED,
            "task_plan": update_current_plan_step_status(state, PlanStepStatus.RUNNING),
            "data_part_results": [],
            "data_fetch_errors": [],
            "execution_history": [
                execution_record(
                    step=WorkflowStep.DATA.value,
                    agent="DataAgent",
                    success=True,
                    message=message,
                    metadata={"required_data_parts": required_parts},
                )
            ],
        }

    def prepare_company_context_node(self, state: WorkflowState) -> dict:
        """抓取公司基础画像数据。"""
        if self.company_profile_fetch_skill is None:
            return self._node_error(
                state=state,
                node_step=WorkflowStep.DATA,
                agent_name="DataNode:company context",
                message="CompanyProfileFetchSkill is not configured.",
            )

        print("[DataNode] 解析公司 ts_code 和公司名...")

        company_name = state.get("company_name")
        ts_code = state.get("ts_code")

        try:
            company_profile = self.company_profile_fetch_skill.fetch(company_name, ts_code)
        except MultipleResultsFound as exc:
            return self._node_error(
                state=state,
                node_step=WorkflowStep.DATA,
                agent_name="DataAgent",
                message=f"DataAgent failed: {type(exc).__name__}: {exc}",
            )
        except CompanyNotFoundError as exc:
            return self._node_error(
                state=state,
                node_step=WorkflowStep.DATA,
                agent_name="DataAgent",
                message=f"DataAgent failed: {type(exc).__name__}: {exc}",
            )

        resolved_company_name = company_profile.get("name") or company_profile.get("company_name")

        if not resolved_company_name:
            return self._node_error(
                state=state,
                node_step=WorkflowStep.DATA,
                agent_name="DataAgent",
                message="DataAgent failed: company profile missing company name.",
            )

        company_profile = {**company_profile, "name": resolved_company_name}

        return {
            "ts_code": company_profile["ts_code"],
            "company_name": resolved_company_name,
            "company_profile": company_profile,
            "execution_history": [
                execution_record(
                    step=WorkflowStep.DATA.value,
                    agent="DataNode:company context",
                    success=True,
                    message="公司上下文解析完成",
                    metadata={"ts_code": company_profile["ts_code"]},
                )
            ],
        }

    def fetch_income_statement_node(self, state: WorkflowState) -> dict:
        """抓取利润表数据。"""
        return self._fetch_one_part(
            state=state,
            part_name=DATA_PART_INCOME,
            normal_message="[DataNode] 检索利润表数据表...",
            backfill_message="[DataNode][TuShare回源] 回源拉取利润表数据并落库...",
        )

    def fetch_balance_sheet_node(self, state: WorkflowState) -> dict:
        """抓取资产负债表数据。"""
        return self._fetch_one_part(
            state=state,
            part_name=DATA_PART_BALANCE,
            normal_message="[DataNode] 检索资产负债表数据表...",
            backfill_message="[DataNode][TuShare回源] 回源拉取资产负债表数据并落库...",
        )

    def fetch_cashflow_statement_node(self, state: WorkflowState) -> dict:
        """抓取现金流量表数据。"""
        return self._fetch_one_part(
            state=state,
            part_name=DATA_PART_CASHFLOW,
            normal_message="[DataNode] 检索现金流量表数据表...",
            backfill_message="[DataNode][TuShare回源] 回源拉取现金流量表数据并落库...",
        )

    def fetch_financial_indicator_node(self, state: WorkflowState) -> dict:
        """抓取核心财务指标数据。"""
        return self._fetch_one_part(
            state=state,
            part_name=DATA_PART_INDICATORS,
            normal_message="[DataNode] 检索核心财务指标数据表...",
            backfill_message="[DataNode][TuShare回源] 回源拉取核心财务指标数据并落库...",
        )

    def _fetch_one_part(
        self,
        *,
        state: WorkflowState,
        part_name: str,
        normal_message: str,
        backfill_message: str,
    ) -> dict:
        """抓取单个财务数据分片。"""
        if self.data_preparation_skill is None:
            return self._node_error(
                state=state,
                node_step=WorkflowStep.DATA,
                agent_name=f"DataNode:{part_name}",
                message="DataPreparationSkill is not configured.",
            )

        if state.get("need_backfill"):
            print(backfill_message)
        else:
            print(normal_message)

        try:
            payload = self.data_preparation_skill.prepare(
                time_range=state.get("time_range"),
                required_parts=[part_name],
                company_profile=state.get("company_profile"),
                backfill=self._part_backfill(state, part_name),
            )
        except Exception as exc:
            return self._node_error(
                state=state,
                node_step=WorkflowStep.DATA,
                agent_name=f"DataNode:{part_name}",
                message=f"Fetch {part_name} failed: {type(exc).__name__}: {exc}",
            )

        return self._data_part_update(part_name, payload)

    def data_merge_node(self, state: WorkflowState) -> dict:
        """校验并合并所有并行数据抓取节点的结果。"""
        print("[DataNode] 并行节点数据结果合并...")

        results = state.get("data_part_results", [])

        financial_data = defaultdict(list)
        for result in results:
            financial_data[result.part_name].append(result.payload)

        return {
            "financial_data": dict(financial_data),
            "execution_history": [
                execution_record(
                    step=WorkflowStep.DATA.value,
                    agent="DataNode:merge node",
                    success=True,
                    message="合并并行数据结果",
                    metadata={"part_name": "all"},
                )
            ],
        }

    def completeness_check_node(self, state: WorkflowState) -> dict:
        """执行完整性检查阶段。"""
        if self.completeness_checker_skill is None:
            return self._node_error(
                state=state,
                node_step=WorkflowStep.DATA,
                agent_name="DataNode:completeness check",
                message="CompletenessCheckSkill is not configured.",
            )

        print("[DataNode] 检查合并后数据是否完整...")

        financial_required_parts = [
            part
            for part in state.get("required_data_parts", [])
            if part != DATA_PART_COMPANY_PROFILE
        ]

        try:
            completeness_check_result = self.completeness_checker_skill.skill_check(
                requested_time_range=state.get("time_range"),
                financial_data=state.get("financial_data"),
                required_parts=financial_required_parts,
            )
        except Exception as exc:
            return self._node_error(
                state=state,
                node_step=WorkflowStep.DATA,
                agent_name="DataNode:completeness check",
                message=f"Completeness check failed: {type(exc).__name__}: {exc}",
            )

        return {
            "data_completeness_check_result": completeness_check_result,
            "execution_history": [
                execution_record(
                    step=WorkflowStep.DATA.value,
                    agent="DataNode:completeness check",
                    success=True,
                    message="数据完整性检查",
                )
            ],
        }

    def backfill_planner_node(self, state: WorkflowState) -> dict:
        """执行回源计划步骤。"""
        if self.data_agent is None:
            return self._node_error(
                state=state,
                node_step=WorkflowStep.DATA,
                agent_name="DataAgent",
                message="DataAgent is not configured.",
            )

        completeness_result = state.get("data_completeness_check_result") or {}
        has_missing_data = bool(completeness_result.get("has_missing_data"))

        if has_missing_data:
            print("[DataNode] 数据有缺失，判定是否需要回源...")

            try:
                update = self.data_agent.run(state)
            except Exception as exc:
                return self._node_error(
                    state=state,
                    node_step=WorkflowStep.DATA,
                    agent_name="DataAgent",
                    message=f"Backfill planning failed: {type(exc).__name__}: {exc}",
                )

            if update.get("should_backfill"):
                already_backfill = int(state.get("already_backfill") or 0) + 1
                print(f"[DataNode] 需要回源，当前已回源次数：{already_backfill} 次...")
                print("回源理由：", update.get("reason"))
                return {
                    "already_backfill": already_backfill,
                    "need_backfill": update.get("backfill_targets") or {},
                    "execution_history": [
                        execution_record(
                            step=WorkflowStep.DATA.value,
                            agent="DataNode:backfill plan",
                            success=True,
                            message="回源计划",
                        )
                    ],
                }

            print(update.get("reason"))
            return {
                "need_backfill": {},
                "trans_message": update.get("notes_for_analysis", ""),
                "data_summary": "数据仍不完整，但由 LLM 判定无需回源补充或回源补充已超最大次数。",
                "execution_history": [
                    execution_record(
                        step=WorkflowStep.DATA.value,
                        agent="DataNode:backfill plan",
                        success=True,
                        message="回源计划",
                    )
                ],
            }

        print("[DataNode] 数据完整，无需回源...")

        return {
            "need_backfill": {},
            "trans_message": "数据完整",
            "data_summary": "数据完整。",
            "execution_history": [
                execution_record(
                    step=WorkflowStep.DATA.value,
                    agent="DataNode:backfill plan",
                    success=True,
                    message="回源计划",
                )
            ],
        }

    def data_finalize_node(self, state: WorkflowState) -> dict:
        """执行数据 finalize 计划步骤。"""
        print("[DataNode] 执行数据 finalize 计划步骤...")

        plan_update = complete_current_plan_step(state)

        return {
            **plan_update,
            "current_stage": WorkflowStep.DATA,
            "status": WorkflowStatus.DATA_READY,
            "execution_history": [
                execution_record(
                    step=WorkflowStep.DATA.value,
                    agent="DataNode:finalize",
                    success=True,
                    message="数据处理完成",
                )
            ],
        }

    @staticmethod
    def _data_part_update(part_name: str, payload: Any) -> dict:
        """把单个数据分片结果包装成 LangGraph 可合并的局部更新。"""
        return {
            "data_part_results": [
                DataPartResult(
                    part_name=part_name,
                    payload=payload,
                    success=True,
                    message=f"Fetched {part_name}.",
                )
            ],
            "execution_history": [
                execution_record(
                    step=WorkflowStep.DATA.value,
                    agent=f"DataNode:{part_name}",
                    success=True,
                    message=f"Fetched {part_name}.",
                    metadata={"part_name": part_name},
                )
            ],
        }

    @staticmethod
    def _part_backfill(state: WorkflowState, part_name: str) -> dict[str, list[str]] | None:
        """只把当前数据分片需要回源的 period 传给对应 fetch node。"""
        need_backfill = state.get("need_backfill") or {}
        if part_name not in need_backfill:
            return None
        return {part_name: need_backfill[part_name]}

    @staticmethod
    def _node_error(
        state: WorkflowState,
        node_step: WorkflowStep,
        agent_name: str,
        message: str,
    ) -> dict:
        """构造节点失败时的统一状态更新。"""
        return {
            **error_update(message),
            **fail_current_plan_step(state),
            "execution_history": [
                execution_record(
                    step=node_step.value,
                    agent=agent_name,
                    success=False,
                    message=message,
                )
            ],
        }

    def data_error_node(self, state: WorkflowState) -> dict:
        message = state.get("error_message") or state.get("assistant_message") or "Data stage failed."

        return {
            "current_stage": WorkflowStep.DATA,
            "status": WorkflowStatus.ERROR,
            "next_step": WorkflowStep.ERROR,
            "has_error": True,
            "assistant_message": message,
            "execution_history": [
                execution_record(
                    step=WorkflowStep.DATA.value,
                    agent="DataNode:error",
                    success=False,
                    message=message,
                )
            ],
        }