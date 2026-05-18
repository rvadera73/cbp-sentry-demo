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

# from services.entity_resolution.routes import router as er_router
# from services.referral.routes import router as referral_router
# from services.graph.routes import router as graph_router

app.include_router(ingest_router, prefix="/api/ingest", tags=["ingest"])
app.include_router(scoring_router, tags=["scoring"])
# app.include_router(er_router, prefix="/api/entity-resolution", tags=["entity-resolution"])
# app.include_router(referral_router, prefix="/api/referral", tags=["referral"])
# app.include_router(graph_router, prefix="/api/graph", tags=["graph"])


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
