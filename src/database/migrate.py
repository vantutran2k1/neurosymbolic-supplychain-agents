import sys
import time
from pathlib import Path

from src.database.connector import Neo4jConnector

RETRY_DELAY = 2
MAX_RETRIES = 30


def wait_for_neo4j() -> Neo4jConnector:
    print("Waiting for Neo4j to be ready...")
    retries = MAX_RETRIES

    while retries > 0:
        try:
            db = Neo4jConnector()
            db.run_query("RETURN 1")
            print("Neo4j is ready")
            return db
        except Exception as e:
            retries -= 1
            print(f"Neo4j not ready, retrying... ({retries} left)")
            time.sleep(RETRY_DELAY)

    raise RuntimeError("Neo4j failed to start after multiple retries.")


def run_migration(cypher_file: Path):
    if not cypher_file.exists():
        raise FileNotFoundError(f"Migration file not found: {cypher_file}")

    if cypher_file.suffix != ".cypher":
        raise ValueError("Migration file must have a .cypher extension")

    print(f"Running migration: {cypher_file.name}")

    with cypher_file.open("r", encoding="utf-8") as f:
        raw_script = f.read()

    statements = [stmt.strip() for stmt in raw_script.split(";") if stmt.strip()]

    if not statements:
        print("Migration file is empty. Skipping.")
        return

    db = Neo4jConnector()
    try:
        for i, statement in enumerate(statements, start=1):
            print(f"Executing statement {i}/{len(statements)}")
            db.run_query(statement)
        print("Migration applied successfully.")
    finally:
        db.close()


def main():
    if len(sys.argv) != 2:
        print("Usage: python -m src.database.migrate <migration_file.cypher>")
        sys.exit(1)

    migration_path = Path(sys.argv[1]).resolve()

    wait_for_neo4j()
    run_migration(migration_path)


if __name__ == "__main__":
    main()
