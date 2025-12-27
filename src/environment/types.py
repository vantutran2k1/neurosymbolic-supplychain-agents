from enum import Enum


class CompanyRole(Enum):
    SUPPLIER = "Supplier"
    MANUFACTURER = "Manufacturer"
    DISTRIBUTOR = "Distributor"


class ProductCategory(Enum):
    ELECTRONICS = "Electronics"
    RAW_MATERIAL = "Raw Material"
    MECHANICAL = "Mechanical"
