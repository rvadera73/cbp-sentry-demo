"""
Sentry CBP API — FastAPI application entry point
"""
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from core.db import init_db
from core.senzing_client import init_senzing, is_using_mock
from core.shipments_db import init_shipments_db

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("Starting Sentry CBP API")
    await init_db()
    init_shipments_db()
    await init_senzing()
    if is_using_mock():
        logger.warning("⚠️  Using MOCK Senzing client — entity resolution uses fixture responses")
        logger.warning("    To enable real Senzing: obtain license from https://senzing.com/get-started")
        logger.warning("    and place at ./senzing/senzing.license, then restart with: docker-compose --profile with_senzing up")
    else:
        logger.info("✓ Real Senzing client initialized — entity resolution is live")
    yield
    logger.info("Shutting down Sentry CBP API")


app = FastAPI(
    title="Sentry CBP",
    description="Customs and Border Protection Sentry API",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
origins = settings.cors_origins or ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "debug": settings.debug,
    }


from services.ingest.routes import router as ingest_router
from services.scoring.routes import router as scoring_router
from services.graph.routes import router as graph_router
from services.entity_resolution.routes import router as er_router
from services.referral.routes import router as referral_router
from services.horizons.routes import router as horizons_router
from services.shipments.routes import router as shipments_router
from services.cord_rag.routes import router as cord_router
from services.isf.routes import router as isf_router

app.include_router(ingest_router, prefix="/api/ingest", tags=["ingest"])
app.include_router(scoring_router, prefix="/api/scoring", tags=["scoring"])
app.include_router(graph_router, prefix="/api", tags=["graph"])
app.include_router(er_router, prefix="/api/er", tags=["entity-resolution"])
app.include_router(referral_router, prefix="/api/referral", tags=["referral"])
app.include_router(horizons_router, prefix="/api/horizons", tags=["horizons"])
app.include_router(shipments_router, tags=["shipments"])
app.include_router(cord_router, prefix="/api/cord", tags=["cord-rag"])
app.include_router(isf_router)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.exception("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "debug": str(exc) if settings.debug else None},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )
