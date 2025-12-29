from src.database.connector import Neo4jConnector


def get_db_driver():
    connector = Neo4jConnector()
    try:
        yield connector.driver
    finally:
        pass
