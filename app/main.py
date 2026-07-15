from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.exceptions import internal_error_handler

app = FastAPI(
    title="МагСклад API",
    description="SaaS система управления товарами для розничных магазинов",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(Exception, internal_error_handler)

app.include_router(api_router)


@app.get("/health", tags=["system"])
@app.get("/api/v1/health", tags=["system"])
async def health_check():
    return {"status": "ok", "app": "МагСклад"}
