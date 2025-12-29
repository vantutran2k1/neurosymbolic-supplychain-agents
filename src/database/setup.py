import time

from src.database.connector import Neo4jConnector


def wait_for_neo4j():
    print("Waiting for Neo4j to be ready...")
    retries = 30
    while retries > 0:
        try:
            db = Neo4jConnector()
            db.run_query("RETURN 1")
            print("Neo4j is ready!")
            return db
        except Exception as e:
            time.sleep(2)
            retries -= 1
            print(f"Retrying... ({retries} left)")
    raise Exception("Neo4j failed to start.")

def initialize_schema():
    db = Neo4jConnector()
    print("Applying schema constraints and indexes...")
    db.run_schema_script("src/database/schema.cypher")
    print("Schema initialized successfully.")
    db.close()

if __name__ == "__main__":
    wait_for_neo4j()
    initialize_schema()