from typing import LiteralString

from src.database.connector import Neo4jConnector
from src.database.migrations.base import Migration


class InitSchema00001(Migration):
    name = "init_schema"
    version = 1

    def up(self, db: Neo4jConnector):
        stms: list[LiteralString] = [
            "CREATE CONSTRAINT company_id IF NOT EXISTS FOR (c:Company) REQUIRE c.id IS UNIQUE;",
            "CREATE CONSTRAINT product_sku IF NOT EXISTS FOR (p:Product) REQUIRE p.sku IS UNIQUE;",
            "CREATE CONSTRAINT category_name IF NOT EXISTS FOR (cat:Category) REQUIRE cat.name IS UNIQUE;",
            "CREATE TEXT INDEX company_name_index IF NOT EXISTS FOR (c:Company) ON (c.name);",
            "CREATE TEXT INDEX product_name_index IF NOT EXISTS FOR (p:Product) ON (p.name);",
            "CREATE INDEX inventory_date IF NOT EXISTS FOR (i:InventorySnapshot) ON (i.date);",
            "CREATE INDEX price_date IF NOT EXISTS FOR (pr:PriceRecord) ON (pr.date);",
            "CREATE INDEX inventory_product_date IF NOT EXISTS FOR (i:InventorySnapshot) ON (i.product_sku, i.date);",
        ]

        for stm in stms:
            db.run_query(stm)
