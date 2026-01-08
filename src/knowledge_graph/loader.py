import json
from pathlib import Path
from typing import Any

from src.knowledge_graph.neo4j_client import Neo4jClient, neo4j_client


class KnowledgeGraphLoader:
    def __init__(self, client: Neo4jClient):
        self._client = client

    def load_log(self, json_file_path: Path):
        with open(json_file_path, "r") as f:
            events = json.load(f)

        if not isinstance(events, list):
            raise ValueError("Log file must contain a list of events")

        print(f"Loading {len(events)} events into Neo4j...")

        self._ensure_constraints()

        for event in events:
            self._process_event(event)

    def _process_event(self, event: dict[str, Any]) -> None:
        event_type = event["event_type"]
        if event_type == "NEGOTIATION_START":
            self._client.execute_write(lambda tx: self._create_session(tx, event))
        elif event_type == "OFFER_MADE":
            self._client.execute_write(lambda tx: self._create_offer(tx, event))
        elif event_type == "CONTRACT_SIGNED":
            self._client.execute_write(lambda tx: self._create_contract(tx, event, True))
        else:
            raise ValueError(f"Unsupported event_type: {event_type}")

    def _ensure_constraints(self):
        def _constraints(tx):
            tx.run("CREATE CONSTRAINT IF NOT EXISTS " "FOR (a:Agent) REQUIRE a.id IS UNIQUE")
            tx.run("CREATE CONSTRAINT IF NOT EXISTS " "FOR (s:Session) REQUIRE s.id IS UNIQUE")
            tx.run("CREATE INDEX IF NOT EXISTS FOR (s:Session) ON (s.day)")
            tx.run("CREATE INDEX IF NOT EXISTS FOR (o:Offer) ON (o.step)")

        self._client.execute_write(_constraints)

    @staticmethod
    def _create_session(tx, data: dict[str, Any]):
        query = """
                MERGE (d:Day {value: $day})

                MERGE (seller:Agent {id: $seller_id})
                ON CREATE SET seller.strategy = $seller_strat

                MERGE (buyer:Agent {id: $buyer_id})
                ON CREATE SET buyer.strategy = $buyer_strat

                CREATE (s:Session {id: $sess_id})

                MERGE (s)-[:OCCURRED_ON]->(d)
                MERGE (seller)-[:PARTICIPATED_IN {role: 'seller'}]->(s)
                MERGE (buyer)-[:PARTICIPATED_IN {role: 'buyer'}]->(s)
                """
        tx.run(
            query,
            day=data["day"],
            sess_id=data["session_id"],
            seller_id=data["seller"],
            seller_strat=data.get("seller_strategy", "unknown"),
            buyer_id=data["buyer"],
            buyer_strat=data.get("buyer_strategy", "unknown"),
        )

    @staticmethod
    def _create_offer(tx, data: dict[str, Any]):
        query = """
                MATCH (s:Session {id: $sess_id})
                MATCH (actor:Agent {id: $proposer_id})

                CREATE (o:Offer {
                    step: $step,
                    price: $price,
                    quantity: $qty
                })

                MERGE (actor)-[:MADE_OFFER]->(o)
                MERGE (o)-[:BELONGS_TO]->(s)

                // Dynamic Linking: Find the offer immediately preceding this one (step - 1)
                WITH o, s, $step as current_step
                MATCH (prev:Offer)-[:BELONGS_TO]->(s)
                WHERE prev.step = current_step - 1
                MERGE (prev)-[:NEXT_OFFER]->(o)
                """
        tx.run(
            query,
            sess_id=data["session_id"],
            proposer_id=data["proposer"],
            step=data["step"],
            price=data["price"],
            qty=data["quantity"],
        )

    @staticmethod
    def _create_contract(tx, data: dict[str, Any], success: bool):
        if success:
            query = """
                    MATCH (s:Session {id: $sess_id})
                    SET s.status = 'SUCCESS', s.final_price = $price

                    CREATE (c:Contract {price: $price, quantity: $qty})
                    MERGE (s)-[:RESULTED_IN]->(c)
                    """
            tx.run(query, sess_id=data["session_id"], price=data["final_price"], qty=data["final_quantity"])
        else:
            query = """
                    MATCH (s:Session {id: $sess_id})
                    SET s.status = 'FAILED', 
                        s.failure_reason = $reason, 
                        s.ended_at_step = $step
                    """
            tx.run(query, sess_id=data["session_id"], reason=data["reason"], step=data.get("last_step", 20))


if __name__ == "__main__":
    # 1. Run the loader
    neo4j_client.clear_database()

    loader = KnowledgeGraphLoader(neo4j_client)
    loader.load_log(Path("../market/research_data.json"))
