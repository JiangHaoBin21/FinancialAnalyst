from app.workflows.graph import WorkflowGraph
from app.workflows.nodes import WorkflowNodes
from app.agents.supervisor_agent import SupervisorAgent
from app.agents.data_agent import DataAgent
from app.agents.analysis_agent import AnalysisAgent
from app.agents.report_agent import ReportAgent
from app.agents.reflection_agent import ReflectionAgent
from app.skills.planning.planning_skill import PlanningSkill
from app.llms.openai_client import OpenAIClient


def main():
    llm_client = OpenAIClient()
    planning_skill = PlanningSkill(llm_client=llm_client)
    supervisor_agent = SupervisorAgent(planning_skill=planning_skill)

    nodes = WorkflowNodes(
        supervisor_agent=supervisor_agent,
        data_agent=DataAgent(),
        analysis_agent=AnalysisAgent(),
        report_agent=ReportAgent(),
        reflection_agent=ReflectionAgent(),
    )

    graph = WorkflowGraph(
        nodes=nodes,
        max_iterations=20,
        enable_trace=True,
    )

    state = graph.run("请分析财务表现")

    print("\n===== FINAL STATUS =====")
    print(state.status)

    print("\n===== ASSISTANT MESSAGE =====")
    print(state.assistant_message)

    print("\n===== FINAL REPORT =====")
    print(state.final_report)

    print("\n===== EXECUTION HISTORY =====")
    for record in state.execution_history:
        print(record)


if __name__ == "__main__":
    main()