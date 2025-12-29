from src.database.connector import Neo4jConnector
from src.database.migrations.base import Migration


class CreateTimeChaining(Migration):
    name = "create_time_chaining"
    version = 5

    def up(self, db: Neo4jConnector):
        self._link_inventory_snapshots(db)
        self._link_price_records(db)

    @staticmethod
    def _link_inventory_snapshots(db: Neo4jConnector):
        query = """
        MATCH (c:Company)-[:HAS_STOCK_SNAPSHOT]->(inv:InventorySnapshot)
        WITH c, inv.product_sku as sku, inv
        ORDER BY inv.date ASC
        WITH c, sku, collect(inv) as snapshots
        CALL apoc.nodes.link(snapshots, 'NEXT_DAY')
        RETURN count(*)
        """
        db.run_query(query)
        print("Inventory linked successfully.")

    @staticmethod
    def _link_price_records(db: Neo4jConnector):
        query = """
        MATCH (p:Product)-[:HAS_PRICE_RECORD]->(pr:PriceRecord)
        WITH p, pr
        ORDER BY pr.date ASC
        WITH p, collect(pr) as records
        CALL apoc.nodes.link(records, 'NEXT_DAY')
        RETURN count(*)
        """
        db.run_query(query)
        print("Prices linked successfully.")
