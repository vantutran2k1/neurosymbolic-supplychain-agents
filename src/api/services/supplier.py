from src.api.exceptions.exceptions import NotFoundError
from src.api.repositories.supplier import SupplierRepository


class SupplierService:
    def __init__(self, repo: SupplierRepository):
        self.repo = repo

    def list_suppliers(self):
        suppliers = self.repo.get_all_suppliers()

        if not suppliers:
            raise NotFoundError("No suppliers found")

        return suppliers
