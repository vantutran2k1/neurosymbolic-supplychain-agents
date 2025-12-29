import logging

from src.agents.workflow import NegotiationAgentGraph
from src.knowledge_graph.db_connector import Neo4jConnector

# Setup
logging.basicConfig(level=logging.ERROR)


def main():
    connector = Neo4jConnector("bolt://localhost:7687", "neo4j", "password")

    agent_brain = NegotiationAgentGraph(connector)

    initial_state = {
        "step": 20,
        "agent_id": "FACT_001",
        "opponent_id": "SUPPLIER_X",
        "product_id": "p_raw_01",
        "is_buying": True,
        "env_context": {
            "balance": 500.0,
            "inventory": {"p_raw_01": 0},
            "capacity": 1000,
            "recipes": [],
        },
        "retry_count": 0,
        "market_context": {},
        "current_proposal": None,
    }

    print("\n>>> STARTING REASONING CHAIN...")
    print(f"Goal: Buy p_raw_01 with limited funds (500.0)")

    final_state = agent_brain.graph.invoke(initial_state)

    print("\n>>> CHAIN FINISHED. RESULT:")
    if final_state["is_compliant"]:
        prop = final_state["current_proposal"]
        cost = prop.quantity * prop.unit_price
        print(f"SUCCESS: Proposed to BUY {prop.quantity} units @ {prop.unit_price:.2f}")
        print(f"Total Cost: {cost:.2f} (Balance: 500.0)")
    else:
        print("FAILED: Could not generate a compliant proposal.")
        print(f"Last Error: {final_state['guardian_feedback']}")


if __name__ == "__main__":
    main()
