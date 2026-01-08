from src.orchestrator.nodes import build_research_agent

if __name__ == "__main__":
    # Test Case 1: Full Neuro-Symbolic Agent
    print("\n--- TEST RUN 1: Full Architecture ---")
    app = build_research_agent()

    dummy_state = {
        "negotiation_data": {"step": 0, "current_day": 10, "opponent_id": "Supplier_Boulware_0", "trading_price": 10},
        "private_state": {"num_lines": 10},
        "config": {"use_rag": True, "use_llm": True, "use_smt": True, "agent_id": "Tester"},
        "context_vector": None,
        "verbal_strategy": None,
        "draft_proposal": None,
        "final_offer": None,
        "safety_violations": [],
    }

    result = app.invoke(dummy_state)
    print("Final Output:", result["final_offer"])

    # Test Case 2: Naive Agent (No RAG, No SMT)
    print("\n--- TEST RUN 2: Baseline (Naive) ---")
    dummy_state["config"]["use_rag"] = False
    dummy_state["config"]["use_smt"] = False

    result = app.invoke(dummy_state)
    print("Final Output:", result["final_offer"])
