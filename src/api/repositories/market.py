from datetime import datetime, timedelta
from typing import Any, LiteralString

from neo4j import Driver
from neo4j.time import DateTime as Neo4jDateTime


class MarketRepository:
    def __init__(self, driver: Driver):
        self.driver = driver

    def get_product_price_history(
        self, sku: str, days: int = 30
    ) -> list[dict[str, Any]]:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        query: LiteralString = """
        MATCH (p:Product {sku: $sku})-[:HAS_PRICE_RECORD]->(pr:PriceRecord)
        WHERE pr.date >= datetime($start_date) AND pr.date <= datetime($end_date)
        RETURN pr.date as date, pr.amount as price, pr.demand_signal as demand
        ORDER BY pr.date ASC
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                {
                    "sku": sku,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
            )
            return [self._normalize_record(record.data()) for record in result]

    def get_market_snapshot(self, date: datetime) -> list[dict[str, Any]]:
        query: LiteralString = """
        MATCH (p:Product)-[:HAS_PRICE_RECORD]->(pr:PriceRecord)
        WHERE date(pr.date) = date($target_date)
        RETURN p.name as product, p.sku as sku, pr.amount as price
        LIMIT 100
        """
        with self.driver.session() as session:
            result = session.run(query, {"target_date": date.isoformat()})
            return [record.data() for record in result]

    @staticmethod
    def _normalize_record(record: dict[str, Any]) -> dict[str, Any]:
        value = record.get("date")

        if isinstance(value, Neo4jDateTime):
            record["date"] = value.to_native()

        return record
