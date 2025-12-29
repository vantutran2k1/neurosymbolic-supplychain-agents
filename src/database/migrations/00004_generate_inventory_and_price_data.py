from datetime import datetime
from typing import Any

from src.database.connector import Neo4jConnector
from src.database.migrations.base import Migration
from src.generator.math_engine import MarketSimulator


class GenerateInventoryAndPriceData(Migration):
    name = "generate_inventory_and_price_data"
    version = 4

    def up(self, db: Neo4jConnector):
        sim = MarketSimulator(start_date=datetime(2025, 1, 1), days=365)

        print("Fetching products...")
        query = """
                MATCH (c:Company)-[:SUPPLIES]->(p:Product)
                RETURN c.id as comp_id, p.sku as sku, p.base_price as base_price
                """
        products = db.run_query(query)

        batch_data = []
        batch_size = 100

        for i, prod in enumerate(products):
            dates = sim.get_date_series()
            demands = sim.generate_demand_curve(base_demand=50)
            inventories, prices = sim.simulate_inventory_price(
                demands, initial_stock=1000, base_price=prod["base_price"]
            )

            for t in range(len(dates)):
                data_point = {
                    "sku": prod["sku"],
                    "comp_id": prod["comp_id"],
                    "date": dates[t].isoformat(),
                    "inventory": inventories[t],
                    "price": prices[t],
                    "demand": int(demands[t]),
                    "day_index": t,
                }
                batch_data.append(data_point)

            if (i + 1) % batch_size == 0 or (i + 1) == len(products):
                print(f"Flushing batch {i+1}/{len(products)}...")
                self._flush(db, batch_data)
                batch_data = []

    @staticmethod
    def _flush(db: Neo4jConnector, data: list[dict[str, Any]]):
        query = """
            UNWIND $batch AS row
            MATCH (p:Product {sku: row.sku})
            MATCH (c:Company {id: row.comp_id})

            CREATE (inv:InventorySnapshot {
                id: randomUUID(),
                date: datetime(row.date),
                quantity: row.inventory,
                product_sku: row.sku,
                company_id: row.comp_id
            })
            CREATE (c)-[:HAS_STOCK_SNAPSHOT]->(inv)

            CREATE (pr:PriceRecord {
                id: randomUUID(),
                date: datetime(row.date),
                amount: row.price,
                currency: 'USD',
                demand_signal: row.demand
            })
            CREATE (p)-[:HAS_PRICE_RECORD]->(pr)
            """

        db.run_query(query, {"batch": data})
