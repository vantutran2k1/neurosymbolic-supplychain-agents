from datetime import datetime, timedelta
from typing import Any

from src.database.connector import Neo4jConnector
from src.rag.encoder import TextEncoder
from src.rag.vector_store import VectorStore


class HybridRetriever:
    def __init__(self):
        self.neo4j = Neo4jConnector()
        self.vector_store = VectorStore()
        self.encoder = TextEncoder()

    def search(self, user_query: str, top_k: int = 3) -> str:
        query_vector = self.encoder.encode([user_query])[0]
        semantic_hits = self.vector_store.search(query_vector, limit=top_k)

        if not semantic_hits:
            return "No relevant market data found."

        consolidated_context = []

        for hit in semantic_hits.points:
            sku = hit.payload.get("sku")
            score = hit.score

            if score < 0.4:
                continue

            dynamic_data = self._get_dynamic_context(sku)

            if len(dynamic_data) > 0:
                context_str = self._format_data_to_text(dynamic_data)
                consolidated_context.append(context_str)

        if not consolidated_context:
            return "Found products matching description, but no recent market data available."

        final_context = "\n---\n".join(consolidated_context)
        return final_context

    def _get_dynamic_context(self, sku: str, days: int = 7) -> dict[str, Any]:
        query = """
        MATCH (p:Product {sku: $sku})
        OPTIONAL MATCH (c:Company)-[:SUPPLIES]->(p)
        OPTIONAL MATCH (p)-[:HAS_PRICE_RECORD]->(pr:PriceRecord)
        WHERE pr.date >= datetime($start_date)
        WITH p, c, pr ORDER BY pr.date ASC

        RETURN 
            p.name as name,
            c.name as supplier,
            c.reliability_score as reliability,
            collect({date: toString(pr.date), price: pr.amount, demand: pr.demand_signal}) as history
        """

        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        results = self.neo4j.run_query(query, {"sku": sku, "start_date": start_date})

        if not results:
            return {}

        return results[0]

    @staticmethod
    def _format_data_to_text(data: dict) -> str:
        history = data["history"]
        if not history:
            latest_price = "Unknown"
            trend = "No data"
        else:
            latest = history[-1]
            latest_price = f"${latest['price']}"

            # TODO: implement a more dynamic approach
            first_price = history[0]["price"]
            last_price = history[-1]["price"]
            if last_price > first_price * 1.05:
                trend = "Increasing strongly"
            elif last_price < first_price * 0.95:
                trend = "Decreasing"
            else:
                trend = "Stable"

        return (
            f"PRODUCT REPORT: {data['name']}\n"
            f"- Supplier: {data['supplier']} (Reliability: {data['reliability']})\n"
            f"- Current Market Status: Price is {latest_price}. Trend (7 days): {trend}.\n"
            f"- Detailed History: {history[-5:] if history else 'Empty'}..."
        )
