"""Data service — SQLite CRUD abstraction layer"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import logging
from contextlib import asynccontextmanager
import json
from pathlib import Path

from db import init_db, create_shipment, get_shipment, get_all_shipments, get_shipments_count, update_shipment, get_shipments_stats, search_shipments
from models import Shipment, ShipmentCreate, ShipmentUpdate
import sqlite3

logger = logging.getLogger(__name__)


def seed_demo_data():
    """
    SINGLE SOURCE OF TRUTH: Load manifest JSON into database

    The manifest JSON is the authoritative data source.
    All shipment IDs come from manifest (SHP-000001, etc.)
    Database is populated ONCE from manifest JSON on first startup.

    Priority:
    1. If manifest_demo_cases.json exists (CBP demo/fixture mode) → load it
    2. Else if manifest_feb_march_2026_with_isf.json exists → load the full manifest
    3. Else error
    """
    conn = sqlite3.connect("/app/data/cbp_sentry.db")
    cursor = conn.cursor()

    # Check if data already exists
    cursor.execute("SELECT COUNT(*) FROM shipments")
    count = cursor.fetchone()[0]
    if count > 0:
        logger.info(f"✅ Database already seeded ({count} records), skipping")
        conn.close()
        return

    # Load FULL manifest (1500+ cases) as primary data source
    full_file = Path("/app/seed_data/manifest_feb_march_2026_with_isf.json")
    # Load DEMO cases to enrich/override with showcase examples
    demo_file = Path("/app/seed_data/manifest_demo_cases.json")

    manifest_file = full_file

    logger.info(f"📦 INITIALIZING DATABASE from manifest JSON")
    logger.info(f"   Looking for: {manifest_file}")

    if not manifest_file.exists():
        error_msg = (
            f"\n\n❌ CRITICAL: Manifest file not found at {manifest_file}\n"
            f"   This file MUST exist to populate the database.\n"
            f"   All shipments in the system come from this manifest.\n\n"
            f"   Fix:\n"
            f"   1. Ensure one of these files exists:\n"
            f"      - services/data/seed_data/manifest_demo_cases.json (CBP demo)\n"
            f"      - services/data/seed_data/manifest_feb_march_2026_with_isf.json (full)\n"
            f"   2. Run: docker-compose down -v && docker-compose up\n"
            f"   3. OR: bash scripts/unified-setup.sh local\n\n"
        )
        logger.error(error_msg)
        conn.close()
        raise FileNotFoundError(error_msg)

    # Load and parse manifest
    try:
        with open(manifest_file) as f:
            manifest_records = json.load(f)
        logger.info(f"✅ Loaded {len(manifest_records)} records from manifest")
    except Exception as e:
        error_msg = f"\n❌ Failed to parse manifest JSON: {e}\n"
        logger.error(error_msg)
        conn.close()
        raise ValueError(error_msg)

    # Convert manifest to shipment records (preserve all IDs from manifest)
    shipments = []
    for m in manifest_records:
        # Parse element_9 sub-object if present
        element_9 = m.get("element_9", {})
        port_calls = m.get("port_calls", [])

        shipments.append({
            "id": m.get("id", ""),
            "manifest_id": m.get("manifest_id", ""),
            "shipper_name": m.get("shipper_name", ""),
            "consignee_name": m.get("consignee_name", ""),
            "origin_country": m.get("origin_country", ""),
            "destination_country": m.get("destination_country", ""),
            "hs_code": m.get("hs_code", ""),
            "declared_value_usd": m.get("declared_value_usd", 0),
            "declared_weight_kg": m.get("declared_weight_kg", 0),
            "vessel_name": m.get("vessel_name", ""),
            "vessel_imo": m.get("vessel_imo"),
            "vessel_flag": m.get("vessel_flag"),
            "status": m.get("status", "filed"),
            "risk_score": m.get("risk_score", 50),
            "shipper_country": m.get("shipper_country") or m.get("origin_country", ""),
            "consignee_country": m.get("consignee_country") or m.get("destination_country", ""),
            "shipper_age_months": m.get("shipper_age_months"),
            "dwell_days": m.get("dwell_days"),
            "ais_stuffing_country": m.get("ais_stuffing_country"),
            "port_calls": json.dumps(port_calls) if port_calls else None,
            "element9_is_mismatch": 1 if element_9.get("is_mismatch") else 0,
            "element9_confidence": element_9.get("confidence"),
            "element9_declared_country": element_9.get("declared_country"),
            "element9_actual_country": element_9.get("actual_stuffing_country"),
            "ad_cvd_rate": m.get("ad_cvd_rate"),
            "ad_cvd_applicable": 1 if m.get("ad_cvd_applicable") else 0,
            "h1_score": m.get("h1_score"),
            "h2_score": m.get("h2_score"),
            "h3_score": m.get("h3_score"),
        })

    # Insert into database
    for shipment in shipments:
        cursor.execute("""
            INSERT OR IGNORE INTO shipments (
                id, manifest_id, shipper_name, consignee_name, origin_country,
                destination_country, hs_code, declared_value_usd, declared_weight_kg,
                vessel_name, vessel_imo, vessel_flag, status, risk_score,
                shipper_country, consignee_country, shipper_age_months,
                dwell_days, ais_stuffing_country, port_calls,
                element9_is_mismatch, element9_confidence, element9_declared_country, element9_actual_country,
                ad_cvd_rate, ad_cvd_applicable, h1_score, h2_score, h3_score, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            shipment["id"],
            shipment["manifest_id"],
            shipment["shipper_name"],
            shipment["consignee_name"],
            shipment["origin_country"],
            shipment["destination_country"],
            shipment["hs_code"],
            shipment["declared_value_usd"],
            shipment["declared_weight_kg"],
            shipment["vessel_name"],
            shipment["vessel_imo"],
            shipment["vessel_flag"],
            shipment["status"],
            shipment["risk_score"],
            shipment["shipper_country"],
            shipment["consignee_country"],
            shipment["shipper_age_months"],
            shipment["dwell_days"],
            shipment["ais_stuffing_country"],
            shipment["port_calls"],
            shipment["element9_is_mismatch"],
            shipment["element9_confidence"],
            shipment["element9_declared_country"],
            shipment["element9_actual_country"],
            shipment["ad_cvd_rate"],
            shipment["ad_cvd_applicable"],
            shipment["h1_score"],
            shipment["h2_score"],
            shipment["h3_score"]
        ))

    conn.commit()
    logger.info(f"✅ Database initialized: {len(shipments)} shipments with SHP-* IDs")
    logger.info(f"   All shipments come from manifest JSON - single source of truth")
    conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    seed_demo_data()
    logger.info("Data service initialized")
    yield
    # Shutdown
    logger.info("Data service shutdown")


app = FastAPI(title="Sentry Data Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "sentry-data"}


@app.post("/shipments", response_model=Shipment)
async def create_shipment_endpoint(shipment: ShipmentCreate) -> dict:
    """Create a new shipment"""
    try:
        shipment_id = create_shipment(
            manifest_id=shipment.manifest_id,
            shipper_name=shipment.shipper_name,
            consignee_name=shipment.consignee_name,
            origin_country=shipment.origin_country,
            destination_country=shipment.destination_country,
            hs_code=shipment.hs_code,
            declared_value_usd=shipment.declared_value_usd,
            declared_weight_kg=shipment.declared_weight_kg,
            description=shipment.description,
            vessel_name=shipment.vessel_name
        )
        return get_shipment(shipment_id)
    except Exception as e:
        logger.error(f"Create shipment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/shipments/{shipment_id}", response_model=Shipment)
async def get_shipment_endpoint(shipment_id: str) -> dict:
    """Get single shipment by ID"""
    data = get_shipment(shipment_id)
    if not data:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return data


@app.get("/shipments", response_model=dict)
async def list_shipments(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None
) -> dict:
    """List all shipments with pagination"""
    shipments = get_all_shipments(limit=limit, offset=offset, status=status)
    return {"data": shipments, "count": len(shipments)}


@app.get("/shipments/meta/count")
async def shipments_count(status: Optional[str] = None) -> dict:
    """Get total count of manifest shipments"""
    total = get_shipments_count(status=status)
    return {"total": total}


@app.patch("/shipments/{shipment_id}", response_model=Shipment)
async def update_shipment_endpoint(shipment_id: str, updates: ShipmentUpdate) -> dict:
    """Update shipment fields"""
    try:
        update_dict = updates.model_dump(exclude_unset=True)
        if not update_dict:
            return get_shipment(shipment_id)

        update_shipment(shipment_id, update_dict)
        return get_shipment(shipment_id)
    except Exception as e:
        logger.error(f"Update shipment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/shipments/search")
async def search_shipments_endpoint(q: str = Query(..., min_length=1)) -> dict:
    """Search shipments"""
    results = search_shipments(q)
    return {"data": results, "count": len(results)}


@app.get("/stats")
async def get_stats() -> dict:
    """Get dashboard statistics"""
    return get_shipments_stats()


@app.post("/manifests", response_model=dict)
async def create_manifest_endpoint(data: dict) -> dict:
    """Create a new manifest record"""
    try:
        from db import create_manifest
        manifest_id = create_manifest(
            filename=data.get('filename', 'unknown'),
            row_count=data.get('row_count', 0),
            extracted_at=data.get('extracted_at')
        )
        return {"id": manifest_id, "filename": data.get('filename')}
    except Exception as e:
        logger.error(f"Create manifest failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
