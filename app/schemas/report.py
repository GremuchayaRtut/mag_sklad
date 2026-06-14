import uuid
from datetime import date

from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_products: int
    low_stock_count: int
    today_revenue: float
    today_profit: float
    today_sales_count: int
    month_revenue: float
    month_profit: float


class SalesDataPoint(BaseModel):
    period_label: str
    revenue: float
    profit: float
    sales_count: int


class SalesReport(BaseModel):
    data: list[SalesDataPoint]
    total_revenue: float
    total_profit: float
    total_sales_count: int


class TopProductItem(BaseModel):
    product_id: uuid.UUID
    product_name: str
    total_quantity_sold: float
    total_revenue: float
    total_profit: float


class LocationReportItem(BaseModel):
    location_id: uuid.UUID
    location_name: str
    revenue: float
    profit: float
    sales_count: int
