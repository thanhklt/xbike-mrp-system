from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings
from app.core.database import AsyncSessionLocal
from app.core.exceptions import register_exception_handlers
from app.core.logging import logger, setup_logging
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.bom.router import router as bom_router
from app.modules.finished_goods_issuing.router import router as finished_goods_router
from app.modules.inventory.router import router as inventory_router
from app.modules.lenh_san_xuat.router import router as lenh_san_xuat_router
from app.modules.mat_hang.cache import MatHangCache
from app.modules.mat_hang.router import router as mat_hang_router
from app.modules.mat_hang.synchronizer import create_synchronizer
from app.modules.material_issuing.router import router as material_issuing_router
from app.modules.nha_cung_cap.router import router as nha_cung_cap_router
from app.modules.nhan_vien.router import router as nhan_vien_router
from app.modules.nhan_vien.router import vai_tro_router
from app.modules.production.router import router as production_router
from app.modules.receiving.router import router as receiving_router
from app.modules.reporting.router import router as reporting_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    logger.info(
        "Initializing %s v%s in %s mode...",
        settings.project_name,
        settings.version,
        settings.environment,
    )
    synchronizer = create_synchronizer(
        app.state.mat_hang_cache, settings.database_url, AsyncSessionLocal
    )
    try:
        await synchronizer.start()
        yield
    finally:
        await synchronizer.stop()
    # Shutdown
    logger.info("Shutting down %s...", settings.project_name)


app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    openapi_url=f"{settings.api_v1_str}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.state.mat_hang_cache = MatHangCache()

# Exception handlers
register_exception_handlers(app)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins
    if isinstance(settings.backend_cors_origins, list)
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
        "app": settings.project_name,
        "version": settings.version,
        "environment": settings.environment,
    }


@app.get(f"{settings.api_v1_str}/ping", tags=["Health"])
async def api_ping():
    """API ping status endpoint."""
    return {
        "success": True,
        "message": "xBike MRP API v1 is active",
        "version": settings.version,
    }


# Include Domain Routers
api_v1_prefix = settings.api_v1_str
app.include_router(auth_router, prefix=api_v1_prefix)
app.include_router(nhan_vien_router, prefix=api_v1_prefix)
app.include_router(vai_tro_router, prefix=api_v1_prefix)
app.include_router(nha_cung_cap_router, prefix=api_v1_prefix)
app.include_router(bom_router, prefix=api_v1_prefix)
app.include_router(inventory_router, prefix=api_v1_prefix)
app.include_router(mat_hang_router, prefix=api_v1_prefix)
app.include_router(receiving_router, prefix=api_v1_prefix)
app.include_router(material_issuing_router, prefix=api_v1_prefix)
app.include_router(production_router, prefix=api_v1_prefix)
app.include_router(finished_goods_router, prefix=api_v1_prefix)
app.include_router(reporting_router, prefix=api_v1_prefix)
app.include_router(audit_router, prefix=api_v1_prefix)

app.include_router(lenh_san_xuat_router, prefix=api_v1_prefix)
