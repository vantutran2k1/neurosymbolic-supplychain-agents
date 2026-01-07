from neo4j import GraphDatabase
import os


class KnowledgeGraphManager:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="password123"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def reset_db(self):
        """Wipes the database for a fresh simulation run."""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            # Create constraints for performance
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (d:Day) REQUIRE d.index IS UNIQUE")

    def initialize_static_entities(self, products: dict, agents: list):
        """Creates the immutable nodes: Agents and Products."""
        with self.driver.session() as session:
            # Create Products
            for pid, p in products.items():
                session.run(
                    "MERGE (:Product {id: $pid, name: $name, catalog_price: $cp})",
                    pid=pid, name=p.name, cp=p.catalog_price
                )
            # Create Agents
            for aid in agents:
                session.run("MERGE (:Agent {id: $aid})", aid=aid)

    def ingest_daily_snapshot(self, snapshot: dict):
        """
        Takes the output from SCMLEnv.step() and writes it to the graph.
        This constructs the 'Dynamic' part of the graph.
        """
        day_idx = snapshot['day']

        with self.driver.session() as session:
            # 1. Create Time Anchor (Day Node)
            session.run("""
                        MERGE (d:Day {index: $day})
                        WITH d
                        MATCH (prev:Day {index: $prev_day})
                        MERGE (prev)-[:NEXT]->(d)
                        """, day=day_idx, prev_day=day_idx - 1)

            # 2. Record Market Prices (Product -> MarketState -> Day)
            for pid, price in snapshot['market_prices'].items():
                session.run("""
                            MATCH (p:Product {id: $pid})
                            MATCH (d:Day {index: $day})
                            CREATE (m:MarketState {price: $price})
                            CREATE (p)-[:HAS_PRICE]->(m)
                            CREATE (m)-[:AT_TIME]->(d)
                            """, pid=pid, day=day_idx, price=price)

            # 3. Record Agent States (Agent -> AgentState -> Day)
            for aid, data in snapshot['agents'].items():
                session.run("""
                            MATCH (a:Agent {id: $aid})
                            MATCH (d:Day {index: $day})
                            CREATE (s:AgentState {balance: $bal, inventory: $inv})
                            CREATE (a)-[:HAS_STATUS]->(s)
                            CREATE (s)-[:AT_TIME]->(d)
                            """, aid=aid, day=day_idx, bal=data['bal'], inv=data['inv'])

            # 4. Record Contracts (Transactions)
            # Note: In SCML, contracts are signed on 'signed_day' but delivery is 'delivery_day'
            for contract in snapshot['contracts']:
                session.run("""
                            MATCH (buyer:Agent {id: $bid}), (seller:Agent {id: $sid})
                            MATCH (p:Product {id: $pid})
                            MATCH (d:Day {index: $day})
                            CREATE (c:Contract {
                              id: $cid, quantity: $q, unit_price: $price, delivery_day: $dd
                            })
                            CREATE (seller)-[:SOLD]->(c)-[:BOUGHT_BY]->(buyer)
                            CREATE (c)-[:FOR_PRODUCT]->(p)
                            CREATE (c)-[:SIGNED_ON]->(d)
                            """,
                            bid=contract.buyer_id, sid=contract.seller_id,
                            pid=contract.product_id, day=day_idx,
                            cid=contract.contract_id, q=contract.quantity,
                            price=contract.unit_price, dd=contract.delivery_day)

    def retrieve_context_subgraph(self, agent_id: str, product_id: int, current_day: int, window: int = 3):
        """
        Retrieves the relevant subgraph for decision making.
        Returns a JSON structure representing the local graph neighborhood.
        """
        query = """
        MATCH (d:Day)
        WHERE d.index >= $start_day AND d.index <= $current_day

        // 1. Get Market Trend for the target product
        MATCH (p:Product {id: $pid})-[:HAS_PRICE]->(m:MarketState)-[:AT_TIME]->(d)

        // 2. Get My Financial State history
        MATCH (me:Agent {id: $aid})-[:HAS_STATUS]->(s:AgentState)-[:AT_TIME]->(d)

        // Return structured results ordered by time (Recent first)
        RETURN d.index as day, m.price as market_price, s.balance as my_balance, s.inventory as my_stock
        ORDER BY d.index DESC
        """

        with self.driver.session() as session:
            result = session.run(query, aid=agent_id, pid=product_id,
                                 current_day=current_day, start_day=current_day - window)
            return [record.data() for record in result]