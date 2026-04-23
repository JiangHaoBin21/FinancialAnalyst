from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.llms.openai_client import OpenAIClient
from app.skills.planning.planning_skill import PlanningSkill


def main() -> None:
    llm_client = OpenAIClient()
    planner = PlanningSkill(llm_client)

    test_cases = [
        "\u7ed9\u6211\u5b81\u5fb7\u65f6\u4ee3\u8fd1\u4e94\u5e74\u7684\u6536\u5165\u6570\u636e",
    ]

    for index, query in enumerate(test_cases, 1):
        print("\n" + "=" * 50)
        print(f"[Test Case {index}] user_query: {query}")

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
        print(result.raw_response)


if __name__ == "__main__":
    main()
