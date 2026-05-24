"""Data service — SQLite CRUD abstraction layer"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import logging
from contextlib import asynccontextmanager
import json
from pathlib import Path
from datetime import datetime

from db import (
    init_db, create_shipment, get_shipment, get_all_shipments, get_shipments_count, update_shipment,
    get_shipments_stats, search_shipments, get_corridors, get_corridor_detail, create_or_update_corridor,
    create_corridor_duty, create_enforcement_action, get_pre_manifest_vessels, create_or_update_pre_manifest_vessel
)
from models import Shipment, ShipmentCreate, ShipmentUpdate
import sqlite3

logger = logging.getLogger(__name__)


def seed_corridors():
    """Load corridor definitions, duties, and enforcement actions from seed JSON"""
    import sqlite3

    try:
        seed_file = Path("/app/seed_data/corridors_seed.json")
        if not seed_file.exists():
            logger.warning(f"📋 Corridors seed file not found at {seed_file}, skipping corridor seeding")
            return

        with open(seed_file) as f:
            corridors_data = json.load(f)

        conn = sqlite3.connect("/app/data/cbp_sentry.db")
        cursor = conn.cursor()

        # Check if corridors already exist
        cursor.execute("SELECT COUNT(*) FROM corridors")
        count = cursor.fetchone()[0]
        if count > 0:
            logger.info(f"✅ Corridors already seeded ({count} records), skipping")
            conn.close()
            return

        logger.info(f"📦 INITIALIZING CORRIDORS from seed data ({len(corridors_data)} corridors)")

        for corridor_data in corridors_data:
            corridor_id = corridor_data["id"]
            logger.info(f"   Loading corridor: {corridor_id}")

            # Insert corridor
            cursor.execute("""
                INSERT OR IGNORE INTO corridors
                (id, display_name, origin_country, destination_country, risk_level, primary_hs_chapters, risk_profile, last_refreshed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                corridor_id,
                corridor_data.get("display_name"),
                corridor_data.get("origin_country"),
                corridor_data.get("destination_country"),
                corridor_data.get("risk_level", "MEDIUM"),
                corridor_data.get("primary_hs_chapters"),
                corridor_data.get("risk_profile"),
                datetime.utcnow().isoformat()
            ))

            # Insert duties
            for duty in corridor_data.get("duties", []):
                cursor.execute("""
                    INSERT INTO corridor_duties
                    (corridor_id, case_number, duty_type, product_description, hs_prefix, rate_pct, status, source_url, last_refreshed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    corridor_id,
                    duty.get("case_number"),
                    duty.get("duty_type"),
                    duty.get("product_description"),
                    duty.get("hs_prefix"),
                    duty.get("rate_pct"),
                    duty.get("status", "ACTIVE"),
                    duty.get("source_url"),
                    datetime.utcnow().isoformat()
                ))

            # Insert enforcement actions
            for action in corridor_data.get("enforcement_actions", []):
                cursor.execute("""
                    INSERT INTO corridor_enforcement_actions
                    (corridor_id, case_id, entity_name, case_status, case_year, duty_evaded_usd, source_description, source_url, last_refreshed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    corridor_id,
                    action.get("case_id"),
                    action.get("entity_name"),
                    action.get("case_status"),
                    action.get("case_year"),
                    action.get("duty_evaded_usd"),
                    action.get("source_description"),
                    action.get("source_url"),
                    datetime.utcnow().isoformat()
                ))

        conn.commit()
        logger.info(f"✅ Corridors initialized: {len(corridors_data)} corridors with duties and enforcement actions")
        conn.close()

    except Exception as e:
        logger.error(f"❌ Failed to seed corridors: {e}")
        raise


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

    # Determine which manifest to load (priority: demo > full)
    demo_file = Path("/app/seed_data/manifest_demo_cases.json")
    full_file = Path("/app/seed_data/manifest_feb_march_2026_with_isf.json")

    # Priority: 1) Demo cases (30 showcase cases with good risk distribution)
    #           2) Full manifest (1500+ real cases)
    if demo_file.exists():
        manifest_file = demo_file
        logger.info(f"📦 INITIALIZING DATABASE from DEMO manifest (30 showcase cases)")
    else:
        manifest_file = full_file
        logger.info(f"📦 INITIALIZING DATABASE from FULL manifest (1500+ cases)")

    logger.info(f"   File: {manifest_file}")

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
    seed_corridors()
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


@app.get("/corridors", response_model=dict)
async def list_corridors() -> dict:
    """List all corridors with computed shipment statistics"""
    try:
        corridors = get_corridors()
        return {
            "data": corridors,
            "count": len(corridors),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Get corridors failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/corridors/{corridor_id}", response_model=dict)
async def get_corridor_endpoint(corridor_id: str) -> dict:
    """Get single corridor with duties, enforcement actions, and pattern indicators"""
    try:
        corridor = get_corridor_detail(corridor_id)
        if not corridor:
            raise HTTPException(status_code=404, detail="Corridor not found")
        return {
            "data": corridor,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get corridor detail failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/corridors", response_model=dict)
async def create_corridor_endpoint(data: dict) -> dict:
    """Create or update a corridor"""
    try:
        corridor_id = data.get('id')
        if not corridor_id:
            raise ValueError("corridor id required")

        create_or_update_corridor(
            corridor_id=corridor_id,
            display_name=data.get('display_name', ''),
            origin_country=data.get('origin_country', ''),
            destination_country=data.get('destination_country', ''),
            risk_level=data.get('risk_level', 'MEDIUM'),
            primary_hs_chapters=data.get('primary_hs_chapters'),
            risk_profile=data.get('risk_profile')
        )

        # Create duties if provided
        duties = data.get('duties', [])
        for duty in duties:
            create_corridor_duty(
                corridor_id=corridor_id,
                case_number=duty.get('case_number', ''),
                duty_type=duty.get('duty_type', ''),
                product_description=duty.get('product_description'),
                hs_prefix=duty.get('hs_prefix'),
                rate_pct=duty.get('rate_pct'),
                status=duty.get('status', 'ACTIVE'),
                source_url=duty.get('source_url')
            )

        # Create enforcement actions if provided
        actions = data.get('enforcement_actions', [])
        for action in actions:
            create_enforcement_action(
                corridor_id=corridor_id,
                case_id=action.get('case_id', ''),
                entity_name=action.get('entity_name', ''),
                case_status=action.get('case_status', ''),
                case_year=action.get('case_year', 0),
                duty_evaded_usd=action.get('duty_evaded_usd'),
                source_description=action.get('source_description'),
                source_url=action.get('source_url')
            )

        corridor = get_corridor_detail(corridor_id)
        return {
            "data": corridor,
            "message": "Corridor created/updated",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Create corridor failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/pre-manifest/vessels", response_model=dict)
async def list_pre_manifest_vessels() -> dict:
    """List all pre-manifest vessels inbound to US"""
    try:
        vessels = get_pre_manifest_vessels()
        return {
            "data": vessels,
            "count": len(vessels),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Get pre-manifest vessels failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pre-manifest/vessels", response_model=dict)
async def create_pre_manifest_vessel_endpoint(data: dict) -> dict:
    """Create or update a pre-manifest vessel"""
    try:
        vessel_imo = data.get('vessel_imo')
        if not vessel_imo:
            raise ValueError("vessel_imo required")

        create_or_update_pre_manifest_vessel(
            vessel_imo=vessel_imo,
            vessel_name=data.get('vessel_name', ''),
            mmsi=data.get('mmsi'),
            flag_state=data.get('flag_state'),
            origin_port=data.get('origin_port'),
            origin_country=data.get('origin_country'),
            destination_port=data.get('destination_port'),
            destination_country=data.get('destination_country'),
            corridor_id=data.get('corridor_id'),
            eta_us=data.get('eta_us'),
            ais_status=data.get('ais_status'),
            current_lat=data.get('current_lat'),
            current_lon=data.get('current_lon'),
            speed_knots=data.get('speed_knots')
        )

        vessels = get_pre_manifest_vessels()
        return {
            "data": vessels,
            "message": "Vessel created/updated",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Create pre-manifest vessel failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/corridors/refresh/status", response_model=dict)
async def refresh_status() -> dict:
    """Get last refresh timestamps for corridor data"""
    return {
        "corridors_last_refreshed": None,
        "duties_last_refreshed": None,
        "enforcement_actions_last_refreshed": None,
        "pre_manifest_vessels_last_refreshed": None,
        "note": "Refresh is performed by background scheduler every 30 minutes (vessels) and daily (duties)"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
