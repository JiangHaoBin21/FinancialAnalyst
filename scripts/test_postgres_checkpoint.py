from langgraph.checkpoint.postgres import PostgresSaver

from app.workflows.graph import build_workflow_graph


DB_URI = "postgresql://admin:admin123@localhost:5432/finance_db?sslmode=disable"


def main():
    thread_id = "financial-analysis-postgres-001"

    with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
        # 第一次必须执行，用于创建/迁移 checkpoint 表
        checkpointer.setup()

        workflow = build_workflow_graph(
            enable_trace=True,
            checkpointer=checkpointer,
        )

        result = workflow.run(
            "帮我分析一下宁德时代2023年的财务表现",
            thread_id=thread_id,
        )
        result2 = workflow.run(
            "分析贵州茅台2023年财务表现",
            thread_id="thread_id_002",
        )

        print("===== FINAL STATE =====")
        print("task_plan1:", result.get("task_plan"))
        print("task_plan2:", result2.get("task_plan"))
        print("status:", result.get("status"))
        print("current_stage:", result.get("current_stage"))
        print("next_step:", result.get("next_step"))
        print("has_error:", result.get("has_error"))
        print("error_message:", result.get("error_message"))

        snapshot = workflow.get_checkpoint_state(thread_id)
        history = workflow.get_checkpoint_history(thread_id)

        print("===== CHECKPOINT =====")
        print("snapshot.status:", snapshot.values.get("status"))
        print("snapshot.current_stage:", snapshot.values.get("current_stage"))
        print("snapshot.next_step:", snapshot.values.get("next_step"))
        print("snapshot.next:", snapshot.next)
        print("history_count:", len(history))


if __name__ == "__main__":
    main()