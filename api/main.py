"""
Sentry — CBP Illegal Transshipment Detection MVP
Main FastAPI application entry point
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from contextlib import asynccontextmanager

from core.config import settings
from core.firestore import init_firestore
from core.neo4j_client import init_neo4j

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lifespan context for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events"""
    logger.info("🚀 Sentry API Starting...")

    # Startup
    try:
        await init_firestore()
        logger.info("✓ Firestore initialized")
    except Exception as e:
        logger.warning(f"⚠ Firestore initialization failed: {e}")

    try:
        await init_neo4j()
        logger.info("✓ Neo4j initialized")
    except Exception as e:
        logger.warning(f"⚠ Neo4j initialization failed: {e}")

    logger.info("✓ Sentry API Ready")

    yield

    # Shutdown
    logger.info("🛑 Sentry API Shutting down...")

# Create FastAPI app
app = FastAPI(
    title="Sentry API",
    description="CBP Illegal Transshipment Detection Platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Demo mode — restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "sentry-api",
        "version": "1.0.0"
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint — API info"""
    return {
        "name": "Sentry CBP Illegal Transshipment Detection",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "ingest": "/api/ingest",
            "entity_resolution": "/api/entity_resolution",
            "scoring": "/api/scoring",
            "referral": "/api/referral",
            "graph": "/api/graph"
        }
    }

# Router placeholders (to be implemented in services/)
@app.get("/api/status")
async def api_status():
    """Get overall API component status"""
    return {
        "firestore": "ready",
        "neo4j": "ready",
        "senzing": "ready",
        "gemini": "ready"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
