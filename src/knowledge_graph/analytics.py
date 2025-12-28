from src.knowledge_graph.db_connector import Neo4jConnector


class DynamicGraphExplorer:
    def __init__(self, connector: Neo4jConnector):
        self.connector = connector

    def get_market_price_snapshot(self, step: int, window: int = 5) -> list[dict]:
        query = """
        MATCH (t:Transaction)-[:INVOLVES_PRODUCT]->(p:Product)
        WHERE t.step >= $start_step AND t.step <= $end_step
        RETURN p.id as product, 
               avg(t.unit_price) as avg_price, 
               sum(t.quantity) as volume,
               stDev(t.unit_price) as volatility
        """
        return self.connector.execute_query(
            query, {"start_step": step - window, "end_step": step}
        )

    def get_competitor_behavior(self, agent_id: str, step: int) -> dict:
        query = """
        MATCH (a:Agent {id: $agent_id})
        OPTIONAL MATCH (a)-[:SOLD]->(t:Transaction)-[:INVOLVES_PRODUCT]->(p_out:Product)
        WHERE t.step < $step
        WITH a, p_out, count(t) as sales_count

        OPTIONAL MATCH (a)-[:BOUGHT]->(t2:Transaction)-[:INVOLVES_PRODUCT]->(p_in:Product)
        WHERE t2.step < $step
        WITH a, collect(DISTINCT p_out.id) as sells, collect(DISTINCT p_in.id) as buys
        RETURN sells, buys
        """
        result = self.connector.execute_query(
            query, {"agent_id": agent_id, "step": step}
        )
        return result[0] if result else {}

    def trace_supply_chain(self, product_id: str):
        query = """
        MATCH (p:Product {id: $pid})<-[:PRODUCES_OUTPUT]-(proc:Process)-[:NEEDS_INPUT]->(input:Product)
        RETURN proc.id as process, collect(input.id) as required_inputs
        """
        return self.connector.execute_query(query, {"pid": product_id})
