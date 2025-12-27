import os

from src.environment.generator import SupplyChainGenerator

if __name__ == "__main__":
    gen = SupplyChainGenerator()
    df_prods = gen.generate_products()
    df_comps = gen.generate_companies()
    df_inv = gen.generate_initial_inventory()
    df_trans = gen.generate_historical_transactions()

    print("Products generated:", len(df_prods))
    print("Companies generated:", len(df_comps))
    print("Transactions generated:", len(df_trans))

    os.makedirs("data/raw", exist_ok=True)
    df_prods.to_csv("data/raw/products.csv", index=False)
    df_comps.to_csv("data/raw/companies.csv", index=False)
    df_inv.to_csv("data/raw/inventory.csv", index=False)
    df_trans.to_csv("data/raw/transactions.csv", index=False)
