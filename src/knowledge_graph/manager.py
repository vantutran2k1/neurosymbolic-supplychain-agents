import logging
from typing import LiteralString

import pandas as pd
from neo4j import GraphDatabase, Query

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KnowledgeGraphManager:
    def __init__(self, uri: str, user: str, password: str) -> None:
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self._driver.close()

    def create_constraints(self) -> None:
        queries: list[LiteralString] = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Company) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE",
            "CREATE INDEX IF NOT EXISTS FOR (c:Company) ON (c.role)",
            "CREATE INDEX IF NOT EXISTS FOR ()-[r:TRANSACTED]-() ON (r.date)",
        ]

        with self._driver.session() as session:
            for q in queries:
                session.run(Query(q))
            logger.info("Constraints and Indexes created.")

    def load_companies(self, csv_path: str) -> None:
        df = pd.read_csv(csv_path)

        query: LiteralString = """
        UNWIND $rows AS row
        MERGE (c:Company {id: row.company_id})
        SET c.name = row.name,
            c.role = row.role,
            c.location = row.location,
            c.capital = toFloat(row.capital),
            c.reliability = toFloat(row.reliability_score)
        """

        with self._driver.session() as session:
            session.run(query, rows=df.to_dict("records"))
        logger.info(f"Loaded {len(df)} companies.")

    def load_products(self, csv_path: str) -> None:
        df = pd.read_csv(csv_path)

        query: LiteralString = """
        UNWIND $rows AS row
        MERGE (p:Product {id: row.product_id})
        SET p.name = row.name,
            p.category = row.category,
            p.base_price = toFloat(row.base_price),
            p.complexity = toFloat(row.complexity_score)
        """

        with self._driver.session() as session:
            session.run(query, rows=df.to_dict("records"))
        logger.info(f"Loaded {len(df)} products.")

    def load_inventory(self, csv_path: str) -> None:
        df = pd.read_csv(csv_path)

        query: LiteralString = """
        UNWIND $rows AS row
        MATCH (c:Company {id: row.company_id})
        MATCH (p:Product {id: row.product_id})
        MERGE (c)-[r:HAS_INVENTORY]->(p)
        SET r.quantity = toInteger(row.quantity),
            r.max_capacity = toInteger(row.max_capacity),
            r.holding_cost = toFloat(row.holding_cost_per_unit),
            r.last_updated = datetime() 
        """

        with self._driver.session() as session:
            session.run(query, rows=df.to_dict("records"))
        logger.info(f"Loaded {len(df)} inventory records.")

    def load_transactions(self, csv_path: str) -> None:
        df = pd.read_csv(csv_path)

        query: LiteralString = """
        UNWIND $rows AS row
        MATCH (seller:Company {id: row.seller_id})
        MATCH (buyer:Company {id: row.buyer_id})
        MATCH (prod:Product {id: row.product_id})

        CREATE (t:Transaction {id: row.transaction_id})
        SET t.date = date(row.date),
            t.quantity = toInteger(row.quantity),
            t.unit_price = toFloat(row.unit_price),
            t.total_value = toFloat(row.total_value),
            t.status = row.status

        CREATE (seller)-[:SOLD]->(t)
        CREATE (t)-[:BOUGHT_BY]->(buyer)
        CREATE (t)-[:INVOLVES]->(prod)
        """

        with self._driver.session() as session:
            session.run(query, rows=df.to_dict("records"))
        logger.info(f"Loaded {len(df)} transactions.")

    def get_context_subgraph(self, company_id: str, lookback_days: int = 30) -> list:
        query: LiteralString = """
        MATCH (c:Company {id: $id})-[r:SOLD|BOUGHT_BY]-(t:Transaction)-[:INVOLVES]->(p:Product)
        WHERE t.date >= date() - duration({days: $days})
        RETURN c, r, t, p
        """

        with self._driver.session() as session:
            result = session.run(query, id=company_id, days=lookback_days)
            return [record.data() for record in result]
