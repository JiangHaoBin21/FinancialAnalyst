from langgraph.checkpoint.postgres import PostgresSaver

from app.workflows.graph import build_workflow_graph


DB_URI = "postgresql://admin:admin123@localhost:5432/finance_db?sslmode=disable"


def main():
    thread_id = "financial-analysis-postgres-001"

    with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
        workflow = build_workflow_graph(
            enable_trace=False,
            checkpointer=checkpointer,
        )

        snapshot = workflow.get_checkpoint_state(thread_id)
        history = workflow.get_checkpoint_history(thread_id)

        snapshot_b = workflow.get_checkpoint_state("thread_id_002")
        history_b = workflow.get_checkpoint_history("thread_id_002")

        for i, snapshot in enumerate(history_b):
            print("*" * 20)
            print("index:", i)
            print("stage:", snapshot.values.get("current_stage"))
            print("status:", snapshot.values.get("status"))
            print("next_step:", snapshot.values.get("next_step"))
            print("next nodes:", snapshot.next)
            print("metadata:", snapshot.metadata)
            print("*" * 20)

        for i, snapshot in enumerate(history):
            print("-" * 20)
            print("index:", i)
            print("stage:", snapshot.values.get("current_stage"))
            print("status:", snapshot.values.get("status"))
            print("next_step:", snapshot.values.get("next_step"))
            print("next nodes:", snapshot.next)
            print("metadata:", snapshot.metadata)
            print("-" * 20)

        print("===== READ FROM POSTGRES CHECKPOINT =====")
        print("status:", snapshot.values.get("status"))
        print("current_stage:", snapshot.values.get("current_stage"))
        print("next_step:", snapshot.values.get("next_step"))
        print("next:", snapshot.next)
        print("history_count:", len(history))


if __name__ == "__main__":
    main()