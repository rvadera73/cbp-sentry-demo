"""Data service — SQLite CRUD abstraction layer"""
from fastapi import FastAPI, HTTPException, Query, Body
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
    create_corridor_duty, create_enforcement_action, get_pre_manifest_vessels, create_or_update_pre_manifest_vessel,
    create_upload_job, get_upload_job, update_upload_job, batch_create_shipments, batch_update_risk_scores, find_existing_source_ids
)
from models import Shipment, ShipmentCreate, ShipmentUpdate, UploadJobCreate, UploadJobUpdate, UploadJobStatus
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
    Load manifest JSON files into database
    Loads BOTH demo cases (30) and full manifest (1191) for complete data
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

    demo_file = Path("/app/seed_data/manifest_demo_cases.json")
    full_file = Path("/app/seed_data/manifest_feb_march_2026_with_isf.json")

    manifest_files = []
    if demo_file.exists():
        manifest_files.append(demo_file)
        print(f"📦 Will load DEMO manifest (30 showcase cases)", flush=True)
        logger.info(f"📦 Will load DEMO manifest (30 showcase cases)")
    if full_file.exists():
        manifest_files.append(full_file)
        print(f"📦 Will load FULL manifest (1191 cases)", flush=True)
        logger.info(f"📦 Will load FULL manifest (1191 cases)")

    if not manifest_files:
        error_msg = (
            f"\n\n❌ CRITICAL: No manifest files found\n"
            f"   Expected files:\n"
            f"      - services/data/seed_data/manifest_demo_cases.json\n"
            f"      - services/data/seed_data/manifest_feb_march_2026_with_isf.json\n\n"
        )
        logger.error(error_msg)
        conn.close()
        raise FileNotFoundError(error_msg)

    total_loaded = 0
    for manifest_file in manifest_files:
        try:
            print(f"Processing file: {manifest_file.name}", flush=True)
            with open(manifest_file) as f:
                manifest_records = json.load(f)
            print(f"✅ Loaded {len(manifest_records)} records from {manifest_file.name}", flush=True)
            logger.info(f"✅ Loaded {len(manifest_records)} records from {manifest_file.name}")

            # Convert and insert records
            for m in manifest_records:
                element_9 = m.get("element_9", {})
                port_calls = m.get("port_calls", [])

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
                    m.get("id", ""),
                    m.get("manifest_id", ""),
                    m.get("shipper_name", ""),
                    m.get("consignee_name", ""),
                    m.get("origin_country", ""),
                    m.get("destination_country", ""),
                    m.get("hs_code", ""),
                    m.get("declared_value_usd", 0),
                    m.get("declared_weight_kg", 0),
                    m.get("vessel_name", ""),
                    m.get("vessel_imo"),
                    m.get("vessel_flag"),
                    m.get("status", "filed"),
                    m.get("risk_score", 50),
                    m.get("shipper_country") or m.get("origin_country", ""),
                    m.get("consignee_country") or m.get("destination_country", ""),
                    m.get("shipper_age_months"),
                    m.get("dwell_days"),
                    m.get("ais_stuffing_country"),
                    json.dumps(port_calls) if port_calls else None,
                    1 if element_9.get("is_mismatch") else 0,
                    element_9.get("confidence"),
                    element_9.get("declared_country"),
                    element_9.get("actual_stuffing_country"),
                    m.get("ad_cvd_rate"),
                    1 if m.get("ad_cvd_applicable") else 0,
                    m.get("h1_score"),
                    m.get("h2_score"),
                    m.get("h3_score")
                ))
            total_loaded += len(manifest_records)

        except Exception as e:
            error_msg = f"\n❌ Failed to load {manifest_file.name}: {e}\n"
            logger.error(error_msg)
            conn.close()
            raise ValueError(error_msg)

    print(f"Committing {total_loaded} total records to database...", flush=True)
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM shipments")
    final_count = cursor.fetchone()[0]
    print(f"✅ Database initialized: {final_count} total shipments loaded", flush=True)
    logger.info(f"✅ Database initialized: {final_count} total shipments loaded from all manifests")
    conn.close()


def seed_pre_manifest_vessels():
    """Load pre-manifest vessel data from seed JSON"""
    import sqlite3

    try:
        seed_file = Path("/app/seed_data/pre_manifest_vessels_seed.json")
        if not seed_file.exists():
            logger.warning(f"⚓ Pre-manifest vessels seed file not found at {seed_file}, skipping vessel seeding")
            return

        with open(seed_file) as f:
            vessels_data = json.load(f)

        conn = sqlite3.connect("/app/data/cbp_sentry.db")
        cursor = conn.cursor()

        # Check if pre-manifest vessels already exist
        cursor.execute("SELECT COUNT(*) FROM pre_manifest_vessels")
        count = cursor.fetchone()[0]
        if count > 0:
            logger.info(f"✅ Pre-manifest vessels already seeded ({count} records), skipping")
            conn.close()
            return

        logger.info(f"⚓ INITIALIZING PRE-MANIFEST VESSELS from seed data")

        total_vessels = 0
        for corridor_data in vessels_data:
            corridor_id = corridor_data["corridor_id"]
            vessels = corridor_data.get("vessels", [])
            logger.info(f"   Loading {len(vessels)} vessels for corridor: {corridor_id}")

            for vessel in vessels:
                cursor.execute("""
                    INSERT OR IGNORE INTO pre_manifest_vessels
                    (vessel_imo, vessel_name, mmsi, flag_state, origin_port, origin_country,
                     destination_port, destination_country, corridor_id, eta_us, ais_status,
                     current_lat, current_lon, speed_knots, last_refreshed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    vessel.get("vessel_imo"),
                    vessel.get("vessel_name"),
                    vessel.get("mmsi"),
                    vessel.get("flag_state"),
                    vessel.get("origin_port"),
                    vessel.get("origin_country"),
                    vessel.get("destination_port"),
                    vessel.get("destination_country"),
                    corridor_id,
                    vessel.get("eta_us"),
                    vessel.get("ais_status"),
                    vessel.get("current_lat"),
                    vessel.get("current_lon"),
                    vessel.get("speed_knots"),
                    datetime.utcnow().isoformat()
                ))
                total_vessels += 1

        conn.commit()
        logger.info(f"✅ Pre-manifest vessels initialized: {total_vessels} vessels across {len(vessels_data)} corridors")
        conn.close()

    except Exception as e:
        logger.error(f"❌ Failed to seed pre-manifest vessels: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    seed_demo_data()
    seed_corridors()
    seed_pre_manifest_vessels()
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
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
    corridor_id: Optional[str] = None,
    risk_min: Optional[float] = None,
    risk_max: Optional[float] = None,
    status: Optional[str] = None
) -> dict:
    """List shipments with server-side filtering by corridor and risk level.

    Query params:
    - limit: Results per page (default 100, max 100)
    - offset: Pagination offset
    - corridor_id: Filter by corridor (e.g. "VN→US")
    - risk_min: Minimum risk score (e.g. 50 for elevated+critical)
    - risk_max: Maximum risk score
    - status: Filter by shipment status
    """
    shipments = get_all_shipments(
        limit=limit,
        offset=offset,
        corridor_id=corridor_id,
        risk_min=risk_min,
        risk_max=risk_max,
        status=status
    )
    # Get accurate count with same filters
    total = get_shipments_count(
        corridor_id=corridor_id,
        risk_min=risk_min,
        risk_max=risk_max,
        status=status
    )
    return {"data": shipments, "count": total}


@app.get("/shipments/meta/count")
async def shipments_count(
    corridor_id: Optional[str] = None,
    risk_min: Optional[float] = None,
    risk_max: Optional[float] = None,
    status: Optional[str] = None
) -> dict:
    """Get total count of manifest shipments with optional filtering"""
    total = get_shipments_count(
        corridor_id=corridor_id,
        risk_min=risk_min,
        risk_max=risk_max,
        status=status
    )
    return {"count": total}


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
async def list_pre_manifest_vessels(corridor_id: Optional[str] = None) -> dict:
    """List pre-manifest vessels, optionally filtered by corridor.

    Query params:
    - corridor_id: Filter by corridor (e.g. "VN→US")
    """
    try:
        vessels = get_pre_manifest_vessels(corridor_id=corridor_id)
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


@app.post("/data/reset-to-demo")
async def reset_to_demo() -> dict:
    """Reset database to demo state by removing user-uploaded shipments and keeping seed data"""
    try:
        db_path = "/app/data/cbp_sentry.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Delete all non-seed shipments (seed data has IDs like SHP-XXXXX or MNF-xxxx format)
        # User uploads will have manifest_source_id set, so we can delete those
        cursor.execute("DELETE FROM shipments WHERE manifest_source_id IS NOT NULL")
        deleted_count = cursor.rowcount

        conn.commit()

        # Get remaining seed shipment count
        cursor.execute("SELECT COUNT(*) FROM shipments WHERE id LIKE 'SHP-%'")
        seed_count = cursor.fetchone()[0]

        conn.close()

        logger.info(f"Database reset: deleted {deleted_count} user rows, {seed_count} seed rows remain")

        return {
            "status": "success",
            "deleted_count": deleted_count,
            "seed_count": seed_count,
            "message": "Database reset to demo state"
        }
    except Exception as e:
        logger.error(f"Reset to demo error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= MANIFEST UPLOAD JOBS =============

@app.post("/upload-jobs", response_model=dict)
async def create_upload_job_endpoint(job: UploadJobCreate) -> dict:
    """Create a new manifest upload job"""
    try:
        from db import create_upload_job as db_create_upload_job
        job_id = db_create_upload_job(job.id, job.filename, job.total_rows)
        return {
            "id": job_id,
            "filename": job.filename,
            "total_rows": job.total_rows,
            "status": "pending"
        }
    except Exception as e:
        logger.error(f"Create upload job failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/upload-jobs/{job_id}", response_model=dict)
async def get_upload_job_endpoint(job_id: str) -> dict:
    """Get upload job status"""
    try:
        from db import get_upload_job as db_get_upload_job
        job = db_get_upload_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Calculate elapsed time
        created_at = job.get('created_at')
        completed_at = job.get('completed_at')
        elapsed_seconds = None
        if created_at and completed_at:
            from datetime import datetime
            created = datetime.fromisoformat(created_at.replace('Z', '+00:00')) if isinstance(created_at, str) else created_at
            completed = datetime.fromisoformat(completed_at.replace('Z', '+00:00')) if isinstance(completed_at, str) else completed_at
            elapsed_seconds = (completed - created).total_seconds()

        return {
            **job,
            "elapsed_seconds": elapsed_seconds,
            "progress_pct": int((job.get('processed_rows', 0) / max(job.get('total_rows', 1), 1)) * 100)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get upload job failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/upload-jobs/{job_id}", response_model=dict)
async def update_upload_job_endpoint(job_id: str, update: UploadJobUpdate) -> dict:
    """Update upload job progress"""
    try:
        from db import update_upload_job as db_update_upload_job, get_upload_job as db_get_upload_job

        # Build update dict with only non-None fields
        fields = {k: v for k, v in update.dict(exclude_unset=True).items() if v is not None}
        if not fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        db_update_upload_job(job_id, **fields)

        # Return updated job
        job = db_get_upload_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update upload job failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/shipments/batch", response_model=dict)
async def batch_create_shipments_endpoint(rows: List[dict]) -> dict:
    """Batch create shipments"""
    try:
        from db import batch_create_shipments

        if not rows:
            return {"ids": []}

        # All rows should have the same manifest_id
        manifest_id = rows[0].get('manifest_id')
        if not manifest_id:
            raise HTTPException(status_code=400, detail="manifest_id required for all rows")

        ids = batch_create_shipments(rows, manifest_id)
        return {"ids": ids}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch create shipments failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/shipments/bulk-risk-update", response_model=dict)
async def bulk_update_risk_scores_endpoint(updates: List[dict]) -> dict:
    """Batch update risk scores for shipments"""
    try:
        from db import batch_update_risk_scores

        if updates:
            batch_update_risk_scores(updates)

        return {"updated_count": len(updates)}
    except Exception as e:
        logger.error(f"Bulk update risk scores failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/shipments/check-duplicates", response_model=dict)
async def check_duplicate_source_ids_endpoint(source_ids: List[str] = Body(...)) -> dict:
    """Check which source IDs already exist"""
    try:
        from db import find_existing_source_ids

        existing = find_existing_source_ids(source_ids)
        return {
            "total_checked": len(source_ids),
            "duplicates": list(existing),
            "duplicate_count": len(existing)
        }
    except Exception as e:
        logger.error(f"Check duplicates failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
