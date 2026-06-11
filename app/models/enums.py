import enum


class Currency(str, enum.Enum):
    TJS = "TJS"
    RUB = "RUB"
    UZS = "UZS"
    USD = "USD"


class Language(str, enum.Enum):
    ru = "ru"
    tj = "tj"


class Plan(str, enum.Enum):
    trial = "trial"
    active = "active"
    suspended = "suspended"


class UserRole(str, enum.Enum):
    owner = "owner"
    manager = "manager"
    cashier = "cashier"
    storekeeper = "storekeeper"


class Unit(str, enum.Enum):
    pcs = "pcs"
    kg = "kg"
    l = "l"
    m = "m"
    pack = "pack"


class SupplyStatus(str, enum.Enum):
    draft = "draft"
    confirmed = "confirmed"


class SaleStatus(str, enum.Enum):
    completed = "completed"
    cancelled = "cancelled"


class StocktakeStatus(str, enum.Enum):
    in_progress = "in_progress"
    completed = "completed"
