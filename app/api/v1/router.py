from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.business import router as business_router
from app.api.v1.endpoints.locations import router as locations_router
from app.api.v1.endpoints.products import router as products_router
from app.api.v1.endpoints.reports import router as reports_router
from app.api.v1.endpoints.sales import router as sales_router
from app.api.v1.endpoints.stocktake import router as stocktake_router
from app.api.v1.endpoints.supplies import router as supplies_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(products_router, prefix="/products", tags=["products"])
api_router.include_router(supplies_router, prefix="/supplies", tags=["supplies"])
api_router.include_router(sales_router, prefix="/sales", tags=["sales"])
api_router.include_router(stocktake_router, prefix="/stocktake", tags=["stocktake"])
api_router.include_router(reports_router, prefix="/reports", tags=["reports"])
api_router.include_router(locations_router, prefix="/locations", tags=["locations"])
api_router.include_router(business_router, prefix="/business", tags=["business"])
