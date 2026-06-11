import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_products: int
    low_stock_count: int
    today_revenue: Decimal
    today_profit: Decimal
    today_sales_count: int
    month_revenue: Decimal
    month_profit: Decimal


class SalesDataPoint(BaseModel):
    period_label: str
    revenue: Decimal
    profit: Decimal
    sales_count: int


class SalesReport(BaseModel):
    data: list[SalesDataPoint]
    total_revenue: Decimal
    total_profit: Decimal
    total_sales_count: int


class TopProductItem(BaseModel):
    product_id: uuid.UUID
    product_name: str
    total_quantity_sold: Decimal
    total_revenue: Decimal
    total_profit: Decimal


class LocationReportItem(BaseModel):
    location_id: uuid.UUID
    location_name: str
    revenue: Decimal
    profit: Decimal
    sales_count: int
