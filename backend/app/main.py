from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import logger, setup_logging
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.bom.router import router as bom_router
from app.modules.catalog.router import router as catalog_router
from app.modules.finished_goods_issuing.router import router as finished_goods_router
from app.modules.inventory.router import router as inventory_router
from app.modules.mat_hang.router import router as mat_hang_router
from app.modules.material_issuing.router import router as material_issuing_router
from app.modules.production.router import router as production_router
from app.modules.receiving.router import router as receiving_router
from app.modules.reporting.router import router as reporting_router
from app.modules.suppliers.router import router as suppliers_router
from app.modules.users.router import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    logger.info(
        "Initializing %s v%s in %s mode...",
        settings.PROJECT_NAME,
        settings.VERSION,
        settings.ENVIRONMENT,
    )
    yield
    # Shutdown
    logger.info("Shutting down %s...", settings.PROJECT_NAME)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Exception handlers
register_exception_handlers(app)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS
    if isinstance(settings.BACKEND_CORS_ORIGINS, list)
    else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Root Health check endpoints
@app.get("/health", tags=["Health"])
async def health_check():
    """Service health status endpoint."""
    return {
        "status": "ok",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get(f"{settings.API_V1_STR}/ping", tags=["Health"])
async def api_ping():
    """API ping status endpoint."""
    return {
        "success": True,
        "message": "xBike MRP API v1 is active",
        "version": settings.VERSION,
    }


# Include Domain Routers
api_v1_prefix = settings.API_V1_STR
app.include_router(auth_router, prefix=api_v1_prefix)
app.include_router(users_router, prefix=api_v1_prefix)
app.include_router(catalog_router, prefix=api_v1_prefix)
app.include_router(suppliers_router, prefix=api_v1_prefix)
app.include_router(bom_router, prefix=api_v1_prefix)
app.include_router(inventory_router, prefix=api_v1_prefix)
app.include_router(mat_hang_router, prefix=api_v1_prefix)
app.include_router(receiving_router, prefix=api_v1_prefix)
app.include_router(material_issuing_router, prefix=api_v1_prefix)
app.include_router(production_router, prefix=api_v1_prefix)
app.include_router(finished_goods_router, prefix=api_v1_prefix)
app.include_router(reporting_router, prefix=api_v1_prefix)
app.include_router(audit_router, prefix=api_v1_prefix)
