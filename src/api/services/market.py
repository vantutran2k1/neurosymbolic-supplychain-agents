from typing import List

from src.api.exceptions.exceptions import NotFoundError
from src.api.repositories.market import MarketRepository


class MarketService:
    def __init__(self, repo: MarketRepository):
        self.repo = repo

    def get_price_history(self, sku: str, days: int) -> List[dict]:
        data = self.repo.get_product_price_history(sku, days)

        if not data:
            raise NotFoundError("Product history not found")

        return data
