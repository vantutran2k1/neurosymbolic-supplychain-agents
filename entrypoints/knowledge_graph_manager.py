from src.knowledge_graph.manager import KnowledgeGraphManager

if __name__ == "__main__":
    kg = KnowledgeGraphManager("bolt://localhost:7687", "neo4j", "password123")

    try:
        kg.create_constraints()
        kg.load_products("data/raw/products.csv")
        kg.load_companies("data/raw/companies.csv")
        kg.load_inventory("data/raw/inventory.csv")
        kg.load_transactions("data/raw/transactions.csv")
        print("Knowledge Graph initialized successfully.")

        print("Testing Subgraph Retrieval...")
        subgraph = kg.get_context_subgraph("SUP_000", 90)
        print(f"Found {len(subgraph)} recent interaction paths.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        kg.close()
