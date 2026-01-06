from typing import Dict, Any

from neo4j import GraphDatabase

from src.settings.settings import settings


class KnowledgeGraphManager:
    """
    The 'Hippocampus' of the agent.
    Handles writing time-aware experiences to Neo4j and retrieving context.
    """

    def __init__(self):
        try:
            self.driver = GraphDatabase.driver(
                settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            self.driver.verify_connectivity()
            self.clear_database()
            # self._init_schema()
        except Exception as e:
            print(f"Failed to connect to Neo4j: {e}")

    def close(self):
        if self.driver:
            self.driver.close()

    def clear_database(self):
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

    def log_state(self, step: int, market_prices: Dict[int, float], competitor_cash: Dict[str, float]):
        """Writes the daily snapshot to Neo4j (The 'Dynamic' part)."""
        if not self.driver: return

        # === FIX: Convert Integer keys to Strings ===
        # Neo4j driver throws error if map keys are integers
        safe_prices = {str(k): v for k, v in market_prices.items()}

        query = """
        MERGE (d:Day {step: $step})
        WITH d
        UNWIND keys($prices) as pid
        MERGE (p:Product {id: toInteger(pid)})
        MERGE (p)-[:TRADED_AT {price: $prices[pid]}]->(d)

        WITH d
        UNWIND keys($comp_cash) as agent_name
        MERGE (a:Agent {name: agent_name})
        MERGE (a)-[:HAS_BALANCE {amount: $comp_cash[agent_name]}]->(d)
        """
        try:
            with self.driver.session() as session:
                # Pass 'safe_prices' instead of raw 'market_prices'
                session.run(query, step=step, prices=safe_prices, comp_cash=competitor_cash)
        except Exception as e:
            print(f"Graph Write Error: {e}")

    def retrieve_context(self, product_id: int, current_step: int) -> Dict[str, Any]:
        """
        Implements DySK-Attn:
        Retrieves a 'Sparse' Subgraph relevant to the current decision.
        """
        if not self.driver:
            return {"avg_price": 10.0, "market_trend": "unknown", "competitor_cash": 0.0}

        # Query: Get avg price of TARGET product over LAST 5 steps only (Sparse Time Window)
        query = """
        MATCH (p:Product {id: $pid})-[r:TRADED_AT]->(d:Day)
        WHERE d.step >= $start_step AND d.step < $current_step
        WITH avg(r.price) as avg_price, collect(r.price) as history

        MATCH (a:Agent)-[bal:HAS_BALANCE]->(d2:Day)
        WHERE d2.step = $current_step - 1
        WITH avg_price, history, avg(bal.amount) as avg_cash

        RETURN avg_price, avg_cash, history
        """

        try:
            with self.driver.session() as session:
                result = session.run(query, pid=product_id, current_step=current_step, start_step=max(0, current_step-5))
                record = result.single()

                if record:
                    # Simple logic to determine trend from history
                    hist = record['history']
                    trend = "stable"
                    if hist and len(hist) > 1:
                        trend = "up" if hist[0] < hist[-1] else "down"

                    return {
                        "avg_price": record['avg_price'] or 10.0,
                        "competitor_cash": record['avg_cash'] or 0.0,
                        "market_trend": trend
                    }
        except Exception as e:
            print(f"Graph Read Error: {e}")

        return {"avg_price": 10.0, "market_trend": "unknown", "competitor_cash": 0.0}