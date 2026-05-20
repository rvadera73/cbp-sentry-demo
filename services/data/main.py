"""Data service — SQLite CRUD abstraction layer"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import logging
from contextlib import asynccontextmanager
import json
from pathlib import Path

from db import init_db, create_shipment, get_shipment, get_all_shipments, update_shipment, get_shipments_stats, search_shipments
from models import Shipment, ShipmentCreate, ShipmentUpdate
import sqlite3

logger = logging.getLogger(__name__)


def seed_demo_data():
    """Seed database with manifest data from JSON file"""
    conn = sqlite3.connect("/app/data/cbp_sentry.db")
    cursor = conn.cursor()

    # Check if demo data already exists
    cursor.execute("SELECT COUNT(*) FROM shipments")
    count = cursor.fetchone()[0]
    if count > 0:
        logger.info(f"Data already exists ({count} records), skipping seed")
        conn.close()
        return

    # Try to load from manifest JSON file
    demo_shipments = []
    manifest_file = Path("/app/seed_data/manifest_feb_march_2026_with_isf.json")

    if manifest_file.exists():
        logger.info(f"Loading manifest data from {manifest_file}")
        try:
            with open(manifest_file) as f:
                manifest_records = json.load(f)

            # Convert manifest records to shipment format
            for m in manifest_records:
                demo_shipments.append({
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
                    "status": "filed",
                    "risk_score": m.get("risk_score", 50)
                })

            logger.info(f"Loaded {len(demo_shipments)} records from manifest file")
        except Exception as e:
            logger.error(f"Failed to load manifest file: {e}")
            demo_shipments = []

    # Fallback to hardcoded demo data if manifest file not found
    if not demo_shipments:
        logger.warning("Manifest file not found, using fallback demo data")
        demo_shipments = [
        {
            "id": "shipment-greenfield-001",
            "manifest_id": "manifest-001",
            "shipper_name": "Greenfield Industrial Trading Co.",
            "consignee_name": "SunPath Energy Distributors LLC",
            "origin_country": "VN",
            "destination_country": "US",
            "hs_code": "7604.29",
            "declared_value_usd": 50000,
            "declared_weight_kg": 5000,
            "vessel_name": "MV Pacific Horizon",
            "status": "received",
            "risk_score": 91
        },
        {
            "id": "shipment-solaria-001",
            "manifest_id": "manifest-001",
            "shipper_name": "Solaria Manufacturing Sdn. Bhd.",
            "consignee_name": "SunPath Energy Distributors LLC",
            "origin_country": "MY",
            "destination_country": "US",
            "hs_code": "8541.40",
            "declared_value_usd": 75000,
            "declared_weight_kg": 2000,
            "vessel_name": "MV Solar Express",
            "status": "received",
            "risk_score": 65
        },
        {
            "id": "shipment-vietnam-aluminum-001",
            "manifest_id": "manifest-002",
            "shipper_name": "Vietnam Aluminum Corp",
            "consignee_name": "Newark Metals Inc",
            "origin_country": "VN",
            "destination_country": "US",
            "hs_code": "7610",
            "declared_value_usd": 45000,
            "declared_weight_kg": 4500,
            "vessel_name": "MV Hanoi Star",
            "status": "received",
            "risk_score": 18
        },
        {
            "id": "shipment-bangkok-metals-001",
            "manifest_id": "manifest-002",
            "shipper_name": "Bangkok Metals International",
            "consignee_name": "American Industrial Supply",
            "origin_country": "TH",
            "destination_country": "US",
            "hs_code": "7611",
            "declared_value_usd": 65000,
            "declared_weight_kg": 3500,
            "vessel_name": "MV Bangkok Pride",
            "status": "received",
            "risk_score": 22
        },
        {
            "id": "shipment-techexport-001",
            "manifest_id": "manifest-003",
            "shipper_name": "TechExport Ltd",
            "consignee_name": "GlobalTech Inc",
            "origin_country": "SG",
            "destination_country": "CA",
            "hs_code": "8517.62",
            "declared_value_usd": 30000,
            "declared_weight_kg": 1500,
            "vessel_name": "MV Singapore Link",
            "status": "received",
            "risk_score": 29
        }
    ]

    for shipment in demo_shipments:
        cursor.execute("""
            INSERT INTO shipments (
                id, manifest_id, shipper_name, consignee_name, origin_country,
                destination_country, hs_code, declared_value_usd, declared_weight_kg,
                vessel_name, status, risk_score, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
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
            shipment["status"],
            shipment["risk_score"]
        ))

    conn.commit()
    conn.close()
    logger.info(f"Seeded {len(demo_shipments)} demo shipments")


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
