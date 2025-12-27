import random
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

from src.environment.types import CompanyRole, ProductCategory

SEED = 42
np.random.seed(SEED)
random.seed(SEED)


@dataclass
class Product:
    product_id: str
    name: str
    category: ProductCategory
    base_price: float
    complexity_score: float


@dataclass
class Company:
    company_id: str
    name: str
    role: CompanyRole
    location: str
    capital: float
    reliability_score: float


@dataclass
class InventoryItem:
    company_id: str
    product_id: str
    quantity: int
    max_capacity: int
    holding_cost_per_unit: float


class SupplyChainGenerator:
    def __init__(
        self,
        n_suppliers: int = 5,
        n_manufacturers: int = 3,
        n_distributors: int = 3,
        n_products: int = 10,
    ) -> None:
        self._n_suppliers: int = n_suppliers
        self._n_manufacturers: int = n_manufacturers
        self._n_distributors: int = n_distributors
        self._n_products: int = n_products

        self.products: list[Product] = []
        self.companies: list[Company] = []
        self.inventory: list[InventoryItem] = []

        self.locations: list[str] = [
            "Hanoi",
            "HoChiMinh",
            "DaNang",
            "HaiPhong",
            "CanTho",
        ]

    def generate_products(self) -> pd.DataFrame:
        for i in range(self._n_products):
            cat = np.random.choice(list(ProductCategory))
            base_price = np.round(np.random.uniform(10, 500), 2)

            product = Product(
                product_id=f"PROD_{i:03d}",
                name=f"Product_{cat}_{i}",
                category=cat,
                base_price=base_price,
                complexity_score=np.round(np.random.beta(2, 5), 2),
            )
            self.products.append(product)

        return pd.DataFrame([asdict(p) for p in self.products])

    def generate_companies(self) -> pd.DataFrame:
        roles: dict[CompanyRole, int] = {
            CompanyRole.SUPPLIER: self._n_suppliers,
            CompanyRole.MANUFACTURER: self._n_manufacturers,
            CompanyRole.DISTRIBUTOR: self._n_distributors,
        }

        for role, count in roles.items():
            for i in range(count):
                capital = np.random.uniform(50000, 1000000)
                reliability = np.random.normal(0.9, 0.05)
                reliability = np.clip(reliability, 0.5, 1.0)

                company = Company(
                    company_id=f"{role.value[:3].upper()}_{i:03d}",
                    name=f"{role}_Company_{i}",
                    role=role,
                    location=np.random.choice(self.locations),
                    capital=np.round(capital, 2),
                    reliability_score=np.round(reliability, 2),
                )
                self.companies.append(company)

        return pd.DataFrame([asdict(c) for c in self.companies])

    def generate_initial_inventory(self) -> pd.DataFrame:
        if not self.companies or not self.products:
            raise ValueError("Must generate companies and products first.")

        for company in self.companies:
            num_items = np.random.randint(2, self._n_products // 2 + 1)
            selected_products = np.random.choice(
                self.products, num_items, replace=False
            )

            for prod in selected_products:
                qty = 0
                max_cap = 1000

                if (
                    company.role == CompanyRole.SUPPLIER
                    and prod.category == ProductCategory.RAW_MATERIAL
                ):
                    qty = np.random.randint(500, 900)
                elif (
                    company.role == CompanyRole.MANUFACTURER
                    and prod.category != ProductCategory.RAW_MATERIAL
                ):
                    qty = np.random.randint(0, 100)

                item = InventoryItem(
                    company_id=company.company_id,
                    product_id=prod.product_id,
                    quantity=qty,
                    max_capacity=max_cap,
                    holding_cost_per_unit=float(np.round(prod.base_price * 0.05, 2)),
                )
                self.inventory.append(item)

        return pd.DataFrame([asdict(i) for i in self.inventory])

    def generate_historical_transactions(self, n_transactions=100) -> pd.DataFrame:
        transactions: list[dict[str, Any]] = []
        start_date = datetime.now() - timedelta(days=365)

        suppliers = [c for c in self.companies if c.role == CompanyRole.SUPPLIER]
        manufacturers = [
            c for c in self.companies if c.role == CompanyRole.MANUFACTURER
        ]

        for _ in range(n_transactions):
            date = start_date + timedelta(days=np.random.randint(0, 365))
            supplier = np.random.choice(suppliers)
            manufacturer = np.random.choice(manufacturers)
            product = np.random.choice(self.products)

            success_prob = (
                supplier.reliability_score + manufacturer.reliability_score
            ) / 2
            status = "COMPLETED" if np.random.random() < success_prob else "FAILED"

            quantity = np.random.randint(10, 200)
            unit_price = product.base_price * np.random.uniform(0.9, 1.2)

            transactions.append(
                {
                    "transaction_id": str(uuid.uuid4()),
                    "seller_id": supplier.company_id,
                    "buyer_id": manufacturer.company_id,
                    "product_id": product.product_id,
                    "date": date.strftime("%Y-%m-%d"),
                    "quantity": quantity,
                    "unit_price": np.round(unit_price, 2),
                    "total_value": np.round(quantity * unit_price, 2),
                    "status": status,
                }
            )

        return pd.DataFrame(transactions)
