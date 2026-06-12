from app.schemas.business import BusinessResponse, BusinessUpdate, EmployeeResponse, EmployeeUpdate
from app.schemas.location import LocationCreate, LocationResponse, LocationUpdate
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.schemas.product import CategoryCreate, CategoryRead, ProductCreate, ProductRead, ProductUpdate
from app.schemas.stock import StockAdjust, StockRead
from app.schemas.supply import SupplyCreate, SupplyResponse, SupplyListResponse
from app.schemas.sale import SaleCreate, SaleResponse, SaleListResponse, SalesSummary
from app.schemas.stocktake import StocktakeResponse, StocktakeListResponse, UpdateStocktakeItemRequest
from app.schemas.report import DashboardStats, SalesReport, TopProductItem, LocationReportItem

__all__ = [
    # business
    "BusinessResponse", "BusinessUpdate", "EmployeeResponse", "EmployeeUpdate",
    # location
    "LocationCreate", "LocationResponse", "LocationUpdate",
    # user
    "UserCreate", "UserRead", "UserUpdate",
    # product
    "CategoryCreate", "CategoryRead",
    "ProductCreate", "ProductRead", "ProductUpdate",
    # stock
    "StockAdjust", "StockRead",
    # supply
    "SupplyCreate", "SupplyResponse", "SupplyListResponse",
    # sale
    "SaleCreate", "SaleResponse", "SaleListResponse", "SalesSummary",
    # stocktake
    "StocktakeResponse", "StocktakeListResponse", "UpdateStocktakeItemRequest",
    # report
    "DashboardStats", "SalesReport", "TopProductItem", "LocationReportItem",
]
