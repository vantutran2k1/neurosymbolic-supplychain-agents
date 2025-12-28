import logging
import os
import random

import yaml

from src.domain.entities import Product, FactoryProfile, ManufacturingProcess
from src.generator.factory import SupplyChainWorld
from src.generator.market import Market

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def load_config(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def main():
    cfg = load_config("configs/config.yaml")
    os.makedirs(cfg["simulation"]["output_dir"], exist_ok=True)

    products = []
    for p_conf in cfg["products"]:
        products.append(
            Product(
                id=p_conf["id"],
                name=p_conf["name"],
                base_price=p_conf["base_price"],
                is_raw_material=p_conf.get("is_raw", False),
            )
        )

    processes = []
    for proc_conf in cfg["processes"]:
        processes.append(
            ManufacturingProcess(
                process_id=proc_conf["id"],
                inputs=proc_conf["inputs"],
                outputs=proc_conf["outputs"],
            )
        )

    logging.info("Simulating Market Prices...")
    market_sim = Market(products, n_steps=cfg["simulation"]["n_steps"])
    market_sim.generate_price_trends()
    market_df = market_sim.to_dataframe()

    market_csv_path = os.path.join(cfg["simulation"]["output_dir"], "market_prices.csv")
    market_df.to_csv(market_csv_path)
    logging.info(f"Market prices saved to {market_csv_path}")

    logging.info("Simulating Supply Chain Interactions...")

    factories = []
    for i in range(cfg["simulation"]["n_factories"]):
        start_inventory = {}
        for p in products:
            if p.is_raw_material:
                start_inventory[p.id] = random.randint(50, 100)

        f_profile = FactoryProfile(
            agent_id=f"FACT_{i:03d}",
            factory_name=f"Factory_{i}",
            location="0,0",
            initial_balance=10000.0,
            current_balance=10000.0,
            inventory_capacity=500,
            production_lines=2,
            processes=processes,
            current_inventory=start_inventory,
        )
        factories.append(f_profile)

    world = SupplyChainWorld(factories, market_df)
    world.run_simulation(steps=cfg["simulation"]["n_steps"])

    trans_path = os.path.join(cfg["simulation"]["output_dir"], "transactions.csv")
    world.ledger.save_csv(trans_path)
    logging.info(f"Transactions saved to {trans_path}")


if __name__ == "__main__":
    main()
