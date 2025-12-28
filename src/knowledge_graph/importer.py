import logging

import pandas as pd
import yaml

from src.knowledge_graph.db_connector import Neo4jConnector

logger = logging.getLogger(__name__)


class GraphImporter:
    def __init__(self, connector: Neo4jConnector):
        self.connector = connector

    def setup_constraints(self):
        queries = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (a:Agent) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (proc:Process) REQUIRE proc.id IS UNIQUE",
            "CREATE INDEX IF NOT EXISTS FOR (t:Transaction) ON (t.step)",
            "CREATE INDEX IF NOT EXISTS FOR (m:DailyMetric) ON (m.step)",
        ]
        for q in queries:
            self.connector.execute_query(q)
        logger.info("Graph constraints and indexes configured.")

    def import_static_data(self, config_path: str):
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f)

        logger.info("Importing Products...")
        query_prod = """
        UNWIND $products AS row
        MERGE (p:Product {id: row.id})
        SET p.name = row.name, 
            p.base_price = row.base_price,
            p.is_raw = row.is_raw
        """
        self.connector.execute_query(
            query_prod, parameters={"products": cfg["products"]}
        )

        logger.info("Importing Manufacturing Processes...")
        query_proc_node = """
        UNWIND $processes AS proc
        MERGE (pr:Process {id: proc.id})
        """
        self.connector.execute_query(
            query_proc_node, parameters={"processes": cfg["processes"]}
        )

        for proc in cfg["processes"]:
            for prod_id, qty in proc["inputs"].items():
                q = """
                MATCH (pr:Process {id: $proc_id}), (p:Product {id: $prod_id})
                MERGE (pr)-[r:NEEDS_INPUT]->(p)
                SET r.quantity = $qty
                """
                self.connector.execute_query(
                    q, {"proc_id": proc["id"], "prod_id": prod_id, "qty": qty}
                )

            for prod_id, qty in proc["outputs"].items():
                q = """
                MATCH (pr:Process {id: $proc_id}), (p:Product {id: $prod_id})
                MERGE (pr)-[r:PRODUCES_OUTPUT]->(p)
                SET r.quantity = $qty
                """
                self.connector.execute_query(
                    q, {"proc_id": proc["id"], "prod_id": prod_id, "qty": qty}
                )

    def import_dynamic_data(self, transactions_path: str):
        df = pd.read_csv(transactions_path)

        agents = set(df["buyer"].unique()) | set(df["seller"].unique())
        # agents.discard("Global_Market")

        agent_list = [{"id": a} for a in agents]

        logger.info(f"Importing {len(agent_list)} Agents...")
        query_agent = """
        UNWIND $agents AS row
        MERGE (a:Agent {id: row.id})
        SET a.type = 'Factory'
        """
        self.connector.execute_query(query_agent, {"agents": agent_list})

        logger.info("Importing Transactions...")
        query_trans = """
        UNWIND $rows AS row
        MATCH (buyer:Agent {id: row.buyer})
        MATCH (seller:Agent {id: row.seller})
        MATCH (p:Product {id: row.product})

        CREATE (t:Transaction {uuid: randomUUID()})
        SET t.step = toInteger(row.step),
            t.quantity = toInteger(row.quantity),
            t.unit_price = toFloat(row.unit_price),
            t.total_value = toFloat(row.total_value)

        CREATE (buyer)-[:BOUGHT]->(t)
        CREATE (seller)-[:SOLD]->(t)
        CREATE (t)-[:INVOLVES_PRODUCT]->(p)
        """

        batch_size = 1000
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i : i + batch_size].to_dict("records")
            self.connector.execute_query(query_trans, {"rows": batch})
            logger.info(f"Processed batch {i}-{i+len(batch)}")

    def link_agents_to_processes(self):
        query = """
        MATCH (a:Agent), (p:Process)
        MERGE (a)-[:CAN_EXECUTE]->(p)
        """
        self.connector.execute_query(query)
        logger.info("Linked Agents to Processes.")
