import logging

from neo4j import GraphDatabase


class Neo4jConnector:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.verify_connection()

    def close(self):
        self.driver.close()

    def verify_connection(self):
        try:
            self.driver.verify_connectivity()
            logging.info("Successfully connected to Neo4j.")
        except Exception as e:
            logging.error(f"Failed to connect to Neo4j: {e}")
            raise

    def execute_query(self, query, parameters=None, db=None):
        try:
            with self.driver.session(database=db) as session:
                result = session.run(query, parameters)
                return [record.data() for record in result]
        except Exception as e:
            logging.error(f"Query failed: {query}\nError: {e}")
            raise
