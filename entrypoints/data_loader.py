import logging

from src.knowledge_graph.analytics import DynamicGraphExplorer
from src.knowledge_graph.db_connector import Neo4jConnector
from src.knowledge_graph.importer import GraphImporter

logging.basicConfig(level=logging.INFO)


def main():
    uri = "bolt://localhost:7687"
    user = "neo4j"
    password = "password"

    print(">>> Connecting to Neo4j...")
    connector = Neo4jConnector(uri, user, password)

    try:
        print(">>> Cleaning old data...")
        connector.execute_query("MATCH (n) DETACH DELETE n")

        importer = GraphImporter(connector)

        print(">>> Setting up constraints...")
        importer.setup_constraints()

        print(">>> Importing Static Data (Ontology)...")
        importer.import_static_data("configs/config.yaml")

        print(">>> Importing Dynamic Data (From Week 1 simulation)...")
        importer.import_dynamic_data("data/raw/transactions.csv")

        print(">>> Linking Domain Logic...")
        importer.link_agents_to_processes()

        print("\n>>> Testing Dynamic Analytics:")
        explorer = DynamicGraphExplorer(connector)

        # Test 1:
        prices = explorer.get_market_price_snapshot(step=50, window=10)
        print(f"Market Snapshot at Step 50: {prices}")

        # Test 2:
        trace = explorer.trace_supply_chain("p_comp_01")
        print(f"Supply Chain Trace for p_comp_01: {trace}")

    except Exception as e:
        logging.error(f"Fatal Error: {e}")
    finally:
        connector.close()


if __name__ == "__main__":
    main()
