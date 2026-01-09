import json
from pathlib import Path
from typing import Any

from src.knowledge_graph.neo4j_client import Neo4jClient, neo4j_client
from src.utils.logger import logger


class KnowledgeGraphIngestor:
    def __init__(self, client: Neo4jClient = neo4j_client):
        self._client = client

    def load_log(self, json_file_path: Path):
        with open(json_file_path, "r") as f:
            events = json.load(f)

        if not isinstance(events, list):
            raise ValueError("Log file must contain a list of events")

        self._init_schema()

        print(f"Loading {len(events)} events into Neo4j...")

        sessions = [e for e in events if e["event"] == "SESSION_START"]
        offers = [e for e in events if e["event"] == "OFFER"]
        deals = [e for e in events if e["event"] == "DEAL"]
        failures = [e for e in events if e["event"] == "FAILED"]

        self._client.execute_write(lambda tx: self._create_sessions(tx, sessions))
        self._client.execute_write(lambda tx: self._create_offers(tx, offers))
        self._client.execute_write(lambda tx: self._create_outcomes(tx, deals, failures))
        self._client.execute_write(lambda tx: self._link_trajectories(tx))

        logger.info("Ingestion complete")

    def _init_schema(self):
        def _constraints(tx):
            tx.run("CREATE CONSTRAINT agent_id_unique IF NOT EXISTS FOR (a:Agent) REQUIRE a.id IS UNIQUE")
            tx.run("CREATE CONSTRAINT session_id_unique IF NOT EXISTS FOR (s:Session) REQUIRE s.id IS UNIQUE")
            tx.run("CREATE INDEX session_day_idx IF NOT EXISTS FOR (s:Session) ON (s.day)")
            tx.run("CREATE INDEX offer_step_idx IF NOT EXISTS FOR (o:Offer) ON (o.step)")

        self._client.execute_write(_constraints)

    @staticmethod
    def _sanitize(event: dict[str, Any]) -> dict[str, Any]:
        safe = event.copy()
        for key in ["market_price", "buyer_bal", "price"]:
            if key in safe and isinstance(safe[key], str):
                try:
                    safe[key] = float(safe[key])
                except ValueError:
                    safe[key] = 0.0
        return safe

    @staticmethod
    def _create_sessions(tx, events: list[dict[str, Any]]):
        query = """
        UNWIND $events AS e
        MERGE (d:Day {value: e.day})
        MERGE (s:Agent {id: e.seller})
        MERGE (b:Agent {id: e.buyer})

        CREATE (sess:Session {
            id: e.sid, 
            market_price: e.market_price
        })

        MERGE (sess)-[:OCCURRED_ON]->(d)
        MERGE (s)-[:PARTICIPATED_IN {role: 'seller'}]->(sess)
        MERGE (b)-[:PARTICIPATED_IN {role: 'buyer'}]->(sess)
        """
        if events:
            tx.run(query, events=events)
            logger.info(f"-> Inserted {len(events)} Sessions")

    @staticmethod
    def _create_offers(tx, events: list[dict[str, Any]]):
        query = """
        UNWIND $events AS e
        MATCH (sess:Session {id: e.sid})
        MATCH (actor:Agent {id: e.proposer})

        CREATE (o:Offer {
            step: e.step,
            price: e.price,
            quantity: e.qty
        })

        MERGE (actor)-[:MADE_OFFER]->(o)
        MERGE (o)-[:BELONGS_TO]->(sess)
        """
        if events:
            tx.run(query, events=events)
            logger.info(f"-> Inserted {len(events)} Offers")

    @staticmethod
    def _create_outcomes(tx, deals: list[dict[str, Any]], failures: list[dict[str, Any]]):
        if deals:
            query_deal = """
            UNWIND $events AS e
            MATCH (sess:Session {id: e.sid})
            SET sess.status = 'SUCCESS', 
                sess.final_price = e.price

            CREATE (c:Contract {price: e.price, qty: e.qty})
            MERGE (sess)-[:RESULTED_IN]->(c)
            """
            tx.run(query_deal, events=deals)

        if failures:
            query_fail = """
            UNWIND $events AS e
            MATCH (sess:Session {id: e.sid})
            SET sess.status = 'FAILED', 
                sess.fail_reason = e.reason,
                sess.ended_at_step = coalesce(e.step, 20)
            """
            tx.run(query_fail, events=failures)

        logger.info(f"-> Processed {len(deals)} Deals and {len(failures)} Failures")

    @staticmethod
    def _link_trajectories(tx):
        logger.info("-> Linking trajectories...")

        query = """
        MATCH (s:Session)<-[:BELONGS_TO]-(o:Offer)
        WITH s, o ORDER BY o.step ASC
        WITH s, collect(o) as offers
        FOREACH (i in range(0, size(offers)-2) |
            FOREACH (o1 in [offers[i]] |
                FOREACH (o2 in [offers[i+1]] |
                    MERGE (o1)-[:NEXT_OFFER]->(o2)
                )
            )
        )
        """
        tx.run(query)


if __name__ == "__main__":
    neo4j_client.clear_database()

    loader = KnowledgeGraphIngestor(neo4j_client)
    loader.load_log(Path("data/market_log.json"))
