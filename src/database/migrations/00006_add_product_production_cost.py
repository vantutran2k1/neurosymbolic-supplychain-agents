from src.database.connector import Neo4jConnector
from src.database.migrations.base import Migration


class AddProductProductionCost(Migration):
    name = "add_product_production_cost"
    version = 6

    def up(self, db: Neo4jConnector):
        query = """
        MATCH (p:Product)
        WHERE p.production_cost IS NULL
        SET p.production_cost = p.base_price * 0.8
        RETURN count(p) as updated_products
        """

        db.run_query(query)
