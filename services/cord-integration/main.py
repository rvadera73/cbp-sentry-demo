"""CORD Integration API Service - Senzing SDK Wrapper with FastAPI"""
import os
import logging
import json
from datetime import datetime
from typing import Optional, Dict, List, Any
from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from cord_loader import load_cord_data_async
from cbp_augmentor import augment_cbp_shipments_async
from resolver import EntityResolver

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Config
CORD_DATA_DIR = os.getenv("CORD_DATA_DIR", "/app/cord-data")
DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL", "http://localhost:8005")
SENZING_INITIALIZED = False
_senzing_engine = None

# ============= PYDANTIC MODELS =============

class SearchRequest(BaseModel):
    name: str
    country: Optional[str] = None


class ResolveRequest(BaseModel):
    shipper_name: str
    shipper_country: Optional[str] = None
    consignee_name: Optional[str] = None
    consignee_country: Optional[str] = None


class EntityMatch(BaseModel):
    entity_id: str
    name: str
    country: Optional[str] = None
    data_source: str
    confidence: float = 1.0


class EntityChain(BaseModel):
    level_1_entity: Optional[Dict[str, Any]] = None
    level_2_entity: Optional[Dict[str, Any]] = None
    level_3_entity: Optional[Dict[str, Any]] = None
    ofac_detected: bool = False
    isf_records: List[Dict[str, Any]] = []
    avg_confidence: float = 0.0
    risk_indicator: Optional[str] = None


class RelationshipExplanation(BaseModel):
    entity_a_id: str
    entity_b_id: str
    relationship_type: str
    explanation: str
    evidence: List[Dict[str, Any]] = []
    confidence: float = 0.0


class HealthResponse(BaseModel):
    status: str
    entity_count: int
    initialized_at: Optional[str] = None
    senzing_ready: bool


# ============= SENZING SDK WRAPPER =============

class SenzingSDKWrapper:
    """Wraps Senzing SDK with in-process SQLite backend."""

    def __init__(self, data_dir: str = CORD_DATA_DIR):
        """Initialize Senzing engine with SQLite backend."""
        self.data_dir = data_dir
        self.entity_count = 0
        self.initialized_at = None
        self.engine = None
        self._init_senzing()

    def _init_senzing(self):
        """Initialize Senzing engine in-process."""
        try:
            # Try to import Senzing SDK
            # Note: In production, this would import the actual Senzing Python SDK
            # For now, we create a mock that stores entities in SQLite
            import sqlite3

            self.db_path = "/app/data/senzing.db"
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.cursor = self.conn.cursor()

            # Create tables for entities and relationships
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS senzing_entities (
                    entity_id TEXT PRIMARY KEY,
                    data_source TEXT,
                    record_id TEXT,
                    name_primary TEXT,
                    country TEXT,
                    entity_type TEXT,
                    confidence REAL DEFAULT 1.0,
                    raw_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS senzing_relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_id_a TEXT,
                    entity_id_b TEXT,
                    relationship_type TEXT,
                    confidence REAL DEFAULT 1.0,
                    evidence TEXT,
                    FOREIGN KEY(entity_id_a) REFERENCES senzing_entities(entity_id),
                    FOREIGN KEY(entity_id_b) REFERENCES senzing_entities(entity_id)
                )
            """)

            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS cbp_shipments (
                    id TEXT PRIMARY KEY,
                    shipper_id TEXT,
                    shipper_name TEXT,
                    consignee_name TEXT,
                    shipper_age_months INTEGER,
                    ad_cvd_rate REAL,
                    risk_score REAL,
                    element9_declared_country TEXT,
                    element9_actual_country TEXT,
                    confidence REAL DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            self.conn.commit()
            self.initialized_at = datetime.utcnow().isoformat()
            logger.info("Senzing SDK engine initialized with SQLite backend")

        except Exception as e:
            logger.error(f"Failed to initialize Senzing SDK: {e}")
            raise

    def search_by_attributes(
        self,
        name: str,
        country: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search for entities by name and optional country."""
        try:
            query = "SELECT * FROM senzing_entities WHERE name_primary LIKE ?"
            params = [f"%{name}%"]

            if country:
                query += " AND country = ?"
                params.append(country)

            query += f" LIMIT {limit}"

            self.cursor.execute(query, params)
            rows = self.cursor.fetchall()

            results = []
            for row in rows:
                results.append({
                    "entity_id": row[0],
                    "data_source": row[1],
                    "record_id": row[2],
                    "name": row[3],
                    "country": row[4],
                    "entity_type": row[5],
                    "confidence": row[6],
                    "raw_data": json.loads(row[7]) if row[7] else {}
                })

            logger.info(f"Searched entities for '{name}' (country={country}): found {len(results)}")
            return results

        except Exception as e:
            logger.error(f"Search by attributes failed: {e}")
            return []

    def get_entity_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get full entity details by entity ID."""
        try:
            self.cursor.execute(
                "SELECT * FROM senzing_entities WHERE entity_id = ?",
                (entity_id,)
            )
            row = self.cursor.fetchone()

            if not row:
                return None

            return {
                "entity_id": row[0],
                "data_source": row[1],
                "record_id": row[2],
                "name": row[3],
                "country": row[4],
                "entity_type": row[5],
                "confidence": row[6],
                "raw_data": json.loads(row[7]) if row[7] else {}
            }

        except Exception as e:
            logger.error(f"Get entity by ID failed: {e}")
            return None

    def get_relationships(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get parent/owner relationships for an entity."""
        try:
            self.cursor.execute("""
                SELECT entity_id_b, relationship_type, confidence, evidence
                FROM senzing_relationships
                WHERE entity_id_a = ? AND relationship_type IN ('OWNED_BY', 'PARENT_COMPANY')
            """, (entity_id,))

            relationships = []
            for row in self.cursor.fetchall():
                relationships.append({
                    "target_entity_id": row[0],
                    "relationship_type": row[1],
                    "confidence": row[2],
                    "evidence": json.loads(row[3]) if row[3] else []
                })

            return relationships

        except Exception as e:
            logger.error(f"Get relationships failed: {e}")
            return []

    def why_records(self, entity_id_a: str, entity_id_b: str) -> Optional[Dict[str, Any]]:
        """Explain why two entities are linked."""
        try:
            self.cursor.execute("""
                SELECT relationship_type, confidence, evidence
                FROM senzing_relationships
                WHERE (entity_id_a = ? AND entity_id_b = ?)
                   OR (entity_id_a = ? AND entity_id_b = ?)
                LIMIT 1
            """, (entity_id_a, entity_id_b, entity_id_b, entity_id_a))

            row = self.cursor.fetchone()
            if not row:
                return None

            return {
                "entity_a_id": entity_id_a,
                "entity_b_id": entity_id_b,
                "relationship_type": row[0],
                "confidence": row[1],
                "evidence": json.loads(row[2]) if row[2] else []
            }

        except Exception as e:
            logger.error(f"Why records failed: {e}")
            return None

    def add_record(self, record: Dict[str, Any]) -> str:
        """Add a new record to Senzing engine."""
        try:
            entity_id = record.get("entity_id")
            data_source = record.get("data_source", "CORD")
            record_id = record.get("record_id", entity_id)
            name = record.get("name", "")
            country = record.get("country", "")
            entity_type = record.get("entity_type", "")
            confidence = record.get("confidence", 1.0)

            self.cursor.execute("""
                INSERT OR REPLACE INTO senzing_entities
                (entity_id, data_source, record_id, name_primary, country, entity_type, confidence, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (entity_id, data_source, record_id, name, country, entity_type, confidence, json.dumps(record)))

            self.conn.commit()
            self.entity_count += 1

            return entity_id

        except Exception as e:
            logger.error(f"Add record failed: {e}")
            raise

    def add_relationship(
        self,
        entity_id_a: str,
        entity_id_b: str,
        relationship_type: str,
        confidence: float = 1.0,
        evidence: List[Dict] = None
    ):
        """Add a relationship between two entities."""
        try:
            evidence_json = json.dumps(evidence or [])
            self.cursor.execute("""
                INSERT INTO senzing_relationships
                (entity_id_a, entity_id_b, relationship_type, confidence, evidence)
                VALUES (?, ?, ?, ?, ?)
            """, (entity_id_a, entity_id_b, relationship_type, confidence, evidence_json))

            self.conn.commit()

        except Exception as e:
            logger.error(f"Add relationship failed: {e}")
            raise

    def get_entity_count(self) -> int:
        """Get total number of entities in Senzing engine."""
        try:
            self.cursor.execute("SELECT COUNT(*) FROM senzing_entities")
            count = self.cursor.fetchone()[0]
            return count
        except Exception as e:
            logger.error(f"Get entity count failed: {e}")
            return 0

    def close(self):
        """Close Senzing engine."""
        if self.conn:
            self.conn.close()
            logger.info("Senzing SDK engine closed")


# ============= LIFESPAN STARTUP/SHUTDOWN =============

async def initialize_senzing():
    """Initialize Senzing engine at startup and load CORD data."""
    global _senzing_engine, SENZING_INITIALIZED

    try:
        _senzing_engine = SenzingSDKWrapper(CORD_DATA_DIR)
        SENZING_INITIALIZED = True
        logger.info("✓ Senzing engine initialized")

        # Load CORD data (Phase 2)
        logger.info("Loading CORD data into Senzing engine...")
        load_result = await asyncio.to_thread(load_cord_data_async, CORD_DATA_DIR, "/app/data/senzing.db")
        logger.info(f"CORD load result: {json.dumps(load_result, indent=2)}")

        # Augment with CBP shipments (Phase 3)
        logger.info("Augmenting with CBP shipment data...")
        augment_result = await augment_cbp_shipments_async(DATA_SERVICE_URL, "/app/data/senzing.db")
        logger.info(f"CBP augmentation result: {json.dumps(augment_result, indent=2)}")

        # Log final entity count
        final_count = _senzing_engine.get_entity_count()
        logger.info(f"✓ Senzing engine ready with {final_count:,} entities")

    except Exception as e:
        logger.error(f"✗ Failed to initialize Senzing: {e}")
        SENZING_INITIALIZED = False


async def shutdown_senzing():
    """Shutdown Senzing engine."""
    global _senzing_engine

    if _senzing_engine:
        _senzing_engine.close()
        logger.info("Senzing engine shutdown")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager."""
    # Startup
    await initialize_senzing()
    yield
    # Shutdown
    await shutdown_senzing()


# ============= FASTAPI APP =============

app = FastAPI(
    title="CORD Integration API",
    description="Senzing SDK wrapper for entity resolution",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============= ENDPOINTS =============

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint with Senzing status."""
    if not _senzing_engine or not SENZING_INITIALIZED:
        raise HTTPException(status_code=503, detail="Senzing engine not initialized")

    return HealthResponse(
        status="healthy",
        entity_count=_senzing_engine.get_entity_count(),
        initialized_at=_senzing_engine.initialized_at,
        senzing_ready=SENZING_INITIALIZED
    )


@app.get("/search", response_model=List[EntityMatch])
async def search_entities(
    name: str = Query(..., description="Entity name to search"),
    country: Optional[str] = Query(None, description="Optional country code filter"),
    limit: int = Query(10, ge=1, le=100, description="Max results")
):
    """Search CORD index for entities by name + country."""
    if not _senzing_engine:
        raise HTTPException(status_code=503, detail="Senzing engine not available")

    results = _senzing_engine.search_by_attributes(name, country, limit)

    return [
        EntityMatch(
            entity_id=r["entity_id"],
            name=r["name"],
            country=r["country"],
            data_source=r["data_source"],
            confidence=r["confidence"]
        )
        for r in results
    ]


@app.get("/entity/{entity_id}")
async def get_entity(entity_id: str):
    """Get full entity details + relationships."""
    if not _senzing_engine:
        raise HTTPException(status_code=503, detail="Senzing engine not available")

    entity = _senzing_engine.get_entity_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    relationships = _senzing_engine.get_relationships(entity_id)

    return {
        "entity": entity,
        "relationships": relationships
    }


@app.post("/resolve")
async def resolve_entity_chain(request: ResolveRequest):
    """3-level entity resolution: shipper → parent → ultimate owner.

    Uses EntityResolver for comprehensive chain resolution with OFAC detection,
    ISF linking, and risk scoring.
    """
    if not _senzing_engine:
        raise HTTPException(status_code=503, detail="Senzing engine not available")

    try:
        # Use EntityResolver for full resolution (Phase 4)
        resolver = EntityResolver("/app/data/senzing.db")
        result = await asyncio.to_thread(
            resolver.resolve_shipper_chain,
            request.shipper_name,
            request.shipper_country,
            request.consignee_name,
            request.consignee_country
        )
        return result

    except Exception as e:
        logger.error(f"Entity resolution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/why/{entity_id_a}/{entity_id_b}", response_model=RelationshipExplanation)
async def explain_relationship(entity_id_a: str, entity_id_b: str):
    """Explain why two entities are linked."""
    if not _senzing_engine:
        raise HTTPException(status_code=503, detail="Senzing engine not available")

    explanation = _senzing_engine.why_records(entity_id_a, entity_id_b)
    if not explanation:
        raise HTTPException(status_code=404, detail="No relationship found between entities")

    return RelationshipExplanation(
        entity_a_id=entity_id_a,
        entity_b_id=entity_id_b,
        relationship_type=explanation.get("relationship_type", "UNKNOWN"),
        explanation=f"Link between {entity_id_a} and {entity_id_b}",
        evidence=explanation.get("evidence", []),
        confidence=explanation.get("confidence", 0.0)
    )


# ============= INTERNAL ENDPOINTS FOR TESTING =============

@app.post("/internal/add-record")
async def internal_add_record(record: Dict[str, Any]):
    """Internal endpoint to add a record to Senzing (for testing/loading)."""
    if not _senzing_engine:
        raise HTTPException(status_code=503, detail="Senzing engine not available")

    try:
        entity_id = _senzing_engine.add_record(record)
        return {"status": "success", "entity_id": entity_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/internal/add-relationship")
async def internal_add_relationship(
    entity_id_a: str = Query(...),
    entity_id_b: str = Query(...),
    relationship_type: str = Query(...),
    confidence: float = Query(1.0)
):
    """Internal endpoint to add a relationship (for testing/loading)."""
    if not _senzing_engine:
        raise HTTPException(status_code=503, detail="Senzing engine not available")

    try:
        _senzing_engine.add_relationship(
            entity_id_a,
            entity_id_b,
            relationship_type,
            confidence
        )
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8004,
        log_level="info"
    )
