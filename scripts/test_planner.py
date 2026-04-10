from app.llms.openai_client import OpenAIClient
from app.skills.planning.planning_skill import PlanningSkill


def test_planner():
    llm_client = OpenAIClient()
    planner = PlanningSkill(llm_client)

    test_cases = [
        # 1. 正常财务分析
        "帮我分析一下宁德时代近五年的财务表现",

        # # 2. 用 ts_code
        # "分析 000001.SZ 最近三年的财务情况",
        #
        # # 3. 要 summary
        # "帮我简单总结一下比亚迪最近两年的财务表现",
        #
        # # 4. 缺公司
        # "帮我查一下比亚迪最近三年的财务数据",
        #
        # # 5. 模糊任务
        # "这个公司怎么样",
        #
        # # 6. 非财务任务
        # "今天天气怎么样",
    ]

    for i, query in enumerate(test_cases, 1):
        print("\n" + "=" * 50)
        print(f"[Test Case {i}] 用户输入: {query}")

        result = planner.plan_financial_task(query)

        print("\n--- PlanningResult ---")
        print("task_type:", result.task_type)
        print("company_name:", result.company_name)
        print("ts_code:", result.ts_code)
        print("time_range:", result.time_range)
        print("needs_user_input:", result.needs_user_input)
        print("missing_fields:", result.missing_fields)

        print("\n--- task_plan ---")
        for step in result.task_plan:
            print(f"{step.step_id}. {step.agent} -> {step.action}")

        print("\n--- planner_message ---")
        print(result.planner_message)

        print("\n--- raw_response ---")
        # print(result.raw_response[:300], "...")  # 防止太长
        print(result.raw_response)


if __name__ == "__main__":
    test_planner()