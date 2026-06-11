import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SaleStatus
from app.models.location import Location
from app.models.product import Product
from app.models.sale import Sale, SaleItem
from app.models.stock import Stock
from app.schemas.report import (
    DashboardStats,
    LocationReportItem,
    SalesDataPoint,
    SalesReport,
    TopProductItem,
)

_PERIOD_CONFIG: dict[str, tuple[timedelta, str]] = {
    "day":     (timedelta(hours=24), "hour"),
    "week":    (timedelta(days=7),   "day"),
    "month":   (timedelta(days=30),  "day"),
    "quarter": (timedelta(days=90),  "week"),
    "year":    (timedelta(days=365), "month"),
}

_PERIOD_LABEL_FMT: dict[str, str] = {
    "hour":  "%H:00",
    "day":   "%Y-%m-%d",
    "week":  "Week %V, %Y",
    "month": "%Y-%m",
}


def _to_d(value, places: int = 2) -> Decimal:
    raw = Decimal(str(value)) if value is not None else Decimal("0")
    return raw.quantize(Decimal("0." + "0" * places))


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ReportService:

    # ── Dashboard ─────────────────────────────────────────────────────────────

    async def get_dashboard(
        self,
        db: AsyncSession,
        business_id: uuid.UUID,
        location_id: uuid.UUID | None = None,
    ) -> DashboardStats:
        now = _utc_now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = today_start.replace(day=1)

        # ── Product counts ────────────────────────────────────────────────────
        total_products: int = (
            await db.scalar(
                select(func.count(Product.id)).where(
                    Product.business_id == business_id,
                    Product.is_active.is_(True),
                )
            )
        ) or 0

        # Low-stock: total stock across location(s) <= min_stock
        if location_id:
            stock_sq = (
                select(Stock.product_id, Stock.quantity.label("qty"))
                .where(Stock.location_id == location_id)
                .subquery()
            )
        else:
            stock_sq = (
                select(
                    Stock.product_id,
                    func.sum(Stock.quantity).label("qty"),
                )
                .group_by(Stock.product_id)
                .subquery()
            )

        low_stock_count: int = (
            await db.scalar(
                select(func.count(Product.id))
                .select_from(Product)
                .outerjoin(stock_sq, stock_sq.c.product_id == Product.id)
                .where(
                    Product.business_id == business_id,
                    Product.is_active.is_(True),
                    func.coalesce(stock_sq.c.qty, 0) <= Product.min_stock,
                )
            )
        ) or 0

        # ── Sales aggregates (single query with conditional sums) ─────────────
        sale_conditions = [
            Sale.business_id == business_id,
            Sale.status == SaleStatus.completed,
        ]
        if location_id:
            sale_conditions.append(Sale.location_id == location_id)

        profit_expr = Sale.total_amount - Sale.total_cost

        row = (
            await db.execute(
                select(
                    func.coalesce(
                        func.sum(
                            case(
                                (Sale.created_at >= today_start, Sale.total_amount),
                                else_=0,
                            )
                        ),
                        0,
                    ).label("today_rev"),
                    func.coalesce(
                        func.sum(
                            case(
                                (Sale.created_at >= today_start, profit_expr),
                                else_=0,
                            )
                        ),
                        0,
                    ).label("today_prof"),
                    func.coalesce(
                        func.count(
                            case(
                                (Sale.created_at >= today_start, Sale.id),
                            )
                        ),
                        0,
                    ).label("today_cnt"),
                    func.coalesce(
                        func.sum(
                            case(
                                (Sale.created_at >= month_start, Sale.total_amount),
                                else_=0,
                            )
                        ),
                        0,
                    ).label("month_rev"),
                    func.coalesce(
                        func.sum(
                            case(
                                (Sale.created_at >= month_start, profit_expr),
                                else_=0,
                            )
                        ),
                        0,
                    ).label("month_prof"),
                ).where(*sale_conditions)
            )
        ).one()

        return DashboardStats(
            total_products=total_products,
            low_stock_count=low_stock_count,
            today_revenue=_to_d(row.today_rev),
            today_profit=_to_d(row.today_prof),
            today_sales_count=int(row.today_cnt),
            month_revenue=_to_d(row.month_rev),
            month_profit=_to_d(row.month_prof),
        )

    # ── Sales report ──────────────────────────────────────────────────────────

    async def get_sales_report(
        self,
        db: AsyncSession,
        business_id: uuid.UUID,
        period: str = "week",
        location_id: uuid.UUID | None = None,
    ) -> SalesReport:
        delta, trunc_unit = _PERIOD_CONFIG.get(period, _PERIOD_CONFIG["week"])
        label_fmt = _PERIOD_LABEL_FMT[trunc_unit]

        since = _utc_now() - delta
        trunc_expr = func.date_trunc(trunc_unit, Sale.created_at).label("bucket")

        conditions = [
            Sale.business_id == business_id,
            Sale.status == SaleStatus.completed,
            Sale.created_at >= since,
        ]
        if location_id:
            conditions.append(Sale.location_id == location_id)

        rows = (
            await db.execute(
                select(
                    trunc_expr,
                    func.sum(Sale.total_amount).label("rev"),
                    func.sum(Sale.total_amount - Sale.total_cost).label("prof"),
                    func.count(Sale.id).label("cnt"),
                )
                .where(*conditions)
                .group_by(trunc_expr)
                .order_by(trunc_expr)
            )
        ).all()

        data: list[SalesDataPoint] = []
        total_revenue = Decimal("0")
        total_profit = Decimal("0")
        total_count = 0

        for row in rows:
            rev = _to_d(row.rev)
            prof = _to_d(row.prof)
            cnt = int(row.cnt)
            # row.bucket is a datetime returned by date_trunc
            label = row.bucket.strftime(label_fmt)
            data.append(
                SalesDataPoint(
                    period_label=label,
                    revenue=rev,
                    profit=prof,
                    sales_count=cnt,
                )
            )
            total_revenue += rev
            total_profit += prof
            total_count += cnt

        return SalesReport(
            data=data,
            total_revenue=total_revenue,
            total_profit=total_profit,
            total_sales_count=total_count,
        )

    # ── Top products ──────────────────────────────────────────────────────────

    async def get_top_products(
        self,
        db: AsyncSession,
        business_id: uuid.UUID,
        location_id: uuid.UUID | None = None,
        limit: int = 10,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[TopProductItem]:
        conditions = [
            Sale.business_id == business_id,
            Sale.status == SaleStatus.completed,
        ]
        if location_id:
            conditions.append(Sale.location_id == location_id)
        if date_from:
            conditions.append(
                Sale.created_at
                >= datetime(date_from.year, date_from.month, date_from.day, tzinfo=timezone.utc)
            )
        if date_to:
            next_day = date_to + timedelta(days=1)
            conditions.append(
                Sale.created_at
                < datetime(next_day.year, next_day.month, next_day.day, tzinfo=timezone.utc)
            )

        rev_expr = func.sum(SaleItem.quantity * SaleItem.sale_price)

        rows = (
            await db.execute(
                select(
                    SaleItem.product_id,
                    Product.name.label("product_name"),
                    func.sum(SaleItem.quantity).label("total_qty"),
                    rev_expr.label("total_rev"),
                    func.sum(
                        SaleItem.quantity * (SaleItem.sale_price - SaleItem.purchase_price)
                    ).label("total_prof"),
                )
                .join(Sale, SaleItem.sale_id == Sale.id)
                .join(Product, SaleItem.product_id == Product.id)
                .where(*conditions)
                .group_by(SaleItem.product_id, Product.name)
                .order_by(rev_expr.desc())
                .limit(limit)
            )
        ).all()

        return [
            TopProductItem(
                product_id=row.product_id,
                product_name=row.product_name,
                total_quantity_sold=_to_d(row.total_qty, places=3),
                total_revenue=_to_d(row.total_rev),
                total_profit=_to_d(row.total_prof),
            )
            for row in rows
        ]

    # ── Locations report ──────────────────────────────────────────────────────

    async def get_locations_report(
        self,
        db: AsyncSession,
        business_id: uuid.UUID,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[LocationReportItem]:
        conditions = [
            Sale.business_id == business_id,
            Sale.status == SaleStatus.completed,
        ]
        if date_from:
            conditions.append(
                Sale.created_at
                >= datetime(date_from.year, date_from.month, date_from.day, tzinfo=timezone.utc)
            )
        if date_to:
            next_day = date_to + timedelta(days=1)
            conditions.append(
                Sale.created_at
                < datetime(next_day.year, next_day.month, next_day.day, tzinfo=timezone.utc)
            )

        rev_expr = func.sum(Sale.total_amount)

        rows = (
            await db.execute(
                select(
                    Sale.location_id,
                    Location.name.label("location_name"),
                    rev_expr.label("revenue"),
                    func.sum(Sale.total_amount - Sale.total_cost).label("profit"),
                    func.count(Sale.id).label("cnt"),
                )
                .join(Location, Sale.location_id == Location.id)
                .where(*conditions)
                .group_by(Sale.location_id, Location.name)
                .order_by(rev_expr.desc())
            )
        ).all()

        return [
            LocationReportItem(
                location_id=row.location_id,
                location_name=row.location_name,
                revenue=_to_d(row.revenue),
                profit=_to_d(row.profit),
                sales_count=int(row.cnt),
            )
            for row in rows
        ]


report_service = ReportService()
