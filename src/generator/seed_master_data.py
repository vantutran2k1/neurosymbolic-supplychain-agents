import random

from faker import Faker

from src.database.connector import Neo4jConnector
from src.models.entities import Company, Product

fake = Faker()
db = Neo4jConnector()

CATEGORIES = [
    "Electronics",
    "Raw Materials",
    "Textile",
    "Chemicals",
    "Automotive Parts",
]


def generate_companies(n=20):
    companies = []
    print(f"Generating {n} companies...")
    for _ in range(n):
        role = random.choice(["Supplier", "Manufacturer"])
        comp = Company(
            name=fake.company(),
            role=role,
            location=fake.country(),
            reliability_score=round(random.uniform(0.7, 1.0), 2),
        )
        companies.append(comp)

        query = """
        MERGE (c:Company {id: $id})
        SET c.name = $name, 
            c.role = $role, 
            c.location = $location, 
            c.reliability_score = $score
        """
        db.run_query(
            query,
            {
                "id": comp.id,
                "name": comp.name,
                "role": comp.role,
                "location": comp.location,
                "score": comp.reliability_score,
            },
        )
    return companies


def generate_products(companies, products_per_company=5):
    print("Generating products and relationships...")
    for comp in companies:
        if comp.role == "Supplier":
            for _ in range(products_per_company):
                prod = Product(
                    sku=fake.ean13(),
                    name=f"{random.choice(['High-grade', 'Standard', 'Eco'])} {fake.word().capitalize()}",
                    category=random.choice(CATEGORIES),
                    base_price=round(random.uniform(10, 500), 2),
                    production_cost=0,
                )
                prod.production_cost = round(
                    prod.base_price * random.uniform(0.6, 0.9), 2
                )

                query_prod = """
                MERGE (p:Product {sku: $sku})
                SET p.name = $name, p.category = $category, p.base_price = $price
                """
                db.run_query(
                    query_prod,
                    {
                        "sku": prod.sku,
                        "name": prod.name,
                        "category": prod.category,
                        "price": prod.base_price,
                    },
                )

                query_rel = """
                MATCH (c:Company {id: $cid}), (p:Product {sku: $sku})
                MERGE (c)-[:SUPPLIES]->(p)
                """
                db.run_query(query_rel, {"cid": comp.id, "sku": prod.sku})


if __name__ == "__main__":
    db.run_query("MATCH (n) DETACH DELETE n")

    comps = generate_companies(30)
    generate_products(comps, 10)

    print("Seeding completed successfully!")
    db.close()
