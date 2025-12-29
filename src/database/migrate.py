import importlib
import pkgutil
import time

from src.database.connector import Neo4jConnector
from src.database.migrations.base import Migration

MIGRATIONS_PACKAGE = "src.database.migrations"


def wait_for_neo4j() -> Neo4jConnector:
    print("Waiting for Neo4j...")
    for _ in range(30):
        try:
            db = Neo4jConnector()
            db.run_query("RETURN 1")
            print("Neo4j ready")
            return db
        except Exception:
            time.sleep(2)
    raise RuntimeError("Neo4j not available")


def ensure_migration_node(db: Neo4jConnector):
    db.run_query(
        """
        CREATE CONSTRAINT migration_version IF NOT EXISTS
        FOR (m:Migration)
        REQUIRE m.version IS UNIQUE
    """
    )


def get_applied_versions(db: Neo4jConnector) -> set[int]:
    result = db.run_query("MATCH (m:Migration) RETURN m.version AS version")
    return {record["version"] for record in result}


def load_migrations() -> list[Migration]:
    migrations: list[Migration] = []

    package = importlib.import_module(MIGRATIONS_PACKAGE)
    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        if module_name == "base":
            continue

        module = importlib.import_module(f"{MIGRATIONS_PACKAGE}.{module_name}")

        for obj in module.__dict__.values():
            if (
                isinstance(obj, type)
                and issubclass(obj, Migration)
                and obj is not Migration
            ):
                migrations.append(obj())

    return sorted(migrations, key=lambda m: m.version)


def apply_migration(db: Neo4jConnector, migration: Migration):
    print(f"Applying migration {migration.version} – {migration.name}")
    migration.up(db)

    db.run_query(
        """
        CREATE (m:Migration {
            version: $version,
            name: $name,
            applied_at: datetime()
        })
    """,
        {
            "version": migration.version,
            "name": migration.name,
        },
    )


def main():
    db = wait_for_neo4j()

    try:
        ensure_migration_node(db)
        applied_versions = get_applied_versions(db)

        migrations = load_migrations()

        for migration in migrations:
            if migration.version in applied_versions:
                print(f"Skipping migration {migration.version}")
                continue

            apply_migration(db, migration)

        print("All migrations applied")

    finally:
        db.close()


if __name__ == "__main__":
    main()
