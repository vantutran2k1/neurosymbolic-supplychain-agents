from typing import Any, LiteralString

from neo4j import Driver
from neo4j.exceptions import Neo4jError


class SupplierRepository:
    def __init__(self, driver: Driver):
        self.driver = driver

    def get_all_suppliers(self) -> list[dict[str, Any]]:
        query: LiteralString = """
        MATCH (c:Company)
        WHERE c.role = 'Supplier'
        RETURN
            c.id AS id,
            c.name AS name,
            c.role AS role,
            c.reliability_score AS reliability
        LIMIT 50
        """

        try:
            with self.driver.session() as session:
                result = session.run(query)
                return [record.data() for record in result]
        except Neo4jError as exc:
            raise RuntimeError("Failed to fetch suppliers") from exc
