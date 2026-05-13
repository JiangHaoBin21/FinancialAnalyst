from langgraph.checkpoint.memory import InMemorySaver

from app.workflows.graph import build_workflow_graph


def main():
    checkpointer = InMemorySaver()

    workflow = build_workflow_graph(
        enable_trace=True,
        checkpointer=checkpointer,
    )

    thread_id = "test-financial-analysis-001"

    result = workflow.run(
        "帮我分析一下宁德时代近三年的财务表现",
        thread_id=thread_id,
    )

    print("status:", result.get("status"))
    print("current_stage:", result.get("current_stage"))
    print("next_step:", result.get("next_step"))
    print("has_error:", result.get("has_error"))
    print("error_message:", result.get("error_message"))

    state_snapshot = workflow.get_checkpoint_state(thread_id)
    history = workflow.get_checkpoint_history(thread_id)

    print("current checkpoint status:", state_snapshot.values.get("status"))
    print("history count:", len(history))
    print("*" * 50)
    print("history:", history)
    print("*" * 50)

if __name__ == "__main__":
    main()