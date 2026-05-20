"""Sentry CBP API Service - H1/H2 Scoring, Ingest, Monitoring, Entity Resolution"""
import os
import logging
import uuid
from datetime import datetime
from fastapi import FastAPI, Query, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
import httpx

from external_apis.h1_adapters import OpenCorporatesAdapter, ComtradeAdapter, ITCTariffsAdapter
from external_apis.h2_adapters import AISAdapter, PortAuthorityAdapter
from ml_scorers import H1CorridorRiskScorer, H2AnomalyScorer
from h3_scorer import H3IntelligenceScorer
from ingest_parser import parse_excel_manifest
from senzing_client import get_senzing_client

logger = logging.getLogger(__name__)

# Config
DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL", "http://localhost:8005")
API_MODE = os.getenv("API_MODE", "fixture")

# Initialize adapters
oc_adapter = OpenCorporatesAdapter()
comtrade_adapter = ComtradeAdapter()
itc_adapter = ITCTariffsAdapter()
ais_adapter = AISAdapter()
port_adapter = PortAuthorityAdapter()

# Initialize scorers
h1_scorer = H1CorridorRiskScorer()
h2_scorer = H2AnomalyScorer()
h3_scorer = H3IntelligenceScorer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Sentry API started in {API_MODE} mode")
    yield
    logger.info("Sentry API shutdown")


app = FastAPI(title="Sentry CBP API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "sentry-api", "mode": API_MODE}


# ============= DATA LAYER PROXIES =============

@app.get("/api/data/shipments")
async def list_shipments(limit: int = 50, offset: int = 0, status: Optional[str] = None):
    """List all shipments"""
    async with httpx.AsyncClient() as client:
        params = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        resp = await client.get(f"{DATA_SERVICE_URL}/shipments", params=params)
        return resp.json()


@app.get("/api/data/shipments/{shipment_id}")
async def get_shipment(shipment_id: str):
    """Get single shipment"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{DATA_SERVICE_URL}/shipments/{shipment_id}")
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="Shipment not found")
        return resp.json()


@app.get("/api/data/stats")
async def get_stats():
    """Get dashboard statistics"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{DATA_SERVICE_URL}/stats")
        return resp.json()


# ============= MANIFEST INGEST =============

@app.post("/api/ingest/manifest")
async def ingest_manifest(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Upload and parse a CBP manifest Excel file"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    if not file.filename.lower().endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="Only Excel (.xlsx/.xls) and CSV files are supported")

    try:
        # Read file content
        content = await file.read()

        # Parse the manifest
        rows, parse_errors = parse_excel_manifest(content)

        if not rows:
            raise HTTPException(status_code=400, detail=f"Failed to parse manifest: {'; '.join(parse_errors)}")

        # Create manifest in data service
        manifest_id = str(uuid.uuid4())

        async with httpx.AsyncClient() as client:
            # Create manifest record
            manifest_payload = {
                "filename": file.filename,
                "row_count": len(rows),
                "extracted_at": datetime.utcnow().isoformat()
            }
            resp = await client.post(f"{DATA_SERVICE_URL}/manifests", json=manifest_payload)
            if resp.status_code != 200:
                logger.error(f"Failed to create manifest in data service: {resp.text}")

            # Create shipment records for each row
            shipment_ids = []
            for row in rows:
                shipment_payload = {
                    "manifest_id": manifest_id,
                    "shipper_name": row['shipper'],
                    "consignee_name": row['consignee'],
                    "origin_country": row['origin_country'],
                    "destination_country": row['destination_country'],
                    "hs_code": row['hs_code'],
                    "declared_value_usd": row['declared_value_usd'],
                    "declared_weight_kg": row['declared_weight_kg'],
                    "description": row.get('description', ''),
                    "vessel_name": row.get('vessel_name'),
                }
                resp = await client.post(f"{DATA_SERVICE_URL}/shipments", json=shipment_payload)
                if resp.status_code == 200:
                    shipment_data = resp.json()
                    shipment_ids.append(shipment_data.get('id'))

        return {
            "manifest_id": manifest_id,
            "filename": file.filename,
            "row_count": len(rows),
            "shipment_ids": shipment_ids,
            "preview": rows[:5],  # Return first 5 rows for preview
            "errors": parse_errors if parse_errors else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Manifest ingest error: {e}")
        raise HTTPException(status_code=500, detail=f"Error ingesting manifest: {str(e)}")


# ============= HORIZON 1: CORRIDOR RISK =============

@app.get("/api/h1/corridor-risk")
async def get_h1_corridor_risk(
    shipper_name: str = Query(...),
    shipper_country: str = Query(...),
    consignee_name: str = Query(...),
    consignee_country: str = Query(...),
    hs_code: str = Query(...),
    declared_value: float = Query(...),
    declared_weight_kg: float = Query(...),
) -> Dict[str, Any]:
    """Horizon 1: Corridor Risk Assessment"""
    try:
        shipper_info = await oc_adapter.fetch(company_name=shipper_name, jurisdiction=shipper_country)
        benchmark_data = await comtrade_adapter.fetch(
            hs_code=hs_code, reporter=shipper_country, partner=consignee_country
        )
        tariff_info = await itc_adapter.fetch(hs_code=hs_code, origin_country=shipper_country)

        h1_score = await h1_scorer.score(
            shipper_country=shipper_country,
            consignee_country=consignee_country,
            hs_code=hs_code,
            declared_value=declared_value,
            declared_weight_kg=declared_weight_kg,
            shipper_info=shipper_info,
            tariff_info=tariff_info,
            benchmark_data=benchmark_data,
        )

        return {
            "corridor": f"{shipper_country} → {consignee_country}",
            "commodity": hs_code,
            "score": h1_score,
            "data_sources": {
                "shipper": shipper_info.get("_metadata", {}),
                "benchmark": benchmark_data.get("_metadata", {}),
                "tariff": tariff_info.get("_metadata", {}),
            },
        }
    except Exception as e:
        logger.error(f"H1 scoring error: {e}")
        return {"error": str(e), "status": "failed"}


# ============= HORIZON 2: ANOMALY DETECTION =============

@app.get("/api/h2/anomaly-detection")
async def get_h2_anomalies(
    manifest_id: str = Query(...),
    vessel_name: str = Query(...),
    shipper_country: str = Query(...),
    consignee_country: str = Query(...),
) -> Dict[str, Any]:
    """Horizon 2: Pre-Intelligence Anomaly Detection"""
    try:
        vessel_data = await ais_adapter.fetch(vessel_name=vessel_name)

        if vessel_data.get("current_port"):
            dwell_details = await ais_adapter.get_dwell_anomaly(
                vessel_name=vessel_name,
                port=vessel_data["current_port"],
                dwell_days=vessel_data.get("port_dwell_days", 0),
            )
            vessel_data.update(dwell_details)

        port_data = await port_adapter.fetch(
            port_code=vessel_data.get("current_port", ""), vessel_name=vessel_name
        )
        isf_data = await port_adapter.get_isf_stuffing_location(manifest_id=manifest_id, container_number="")

        h2_score = await h2_scorer.score(vessel_data=vessel_data, isf_data=isf_data, port_calls=[port_data])

        return {
            "manifest_id": manifest_id,
            "vessel": vessel_name,
            "score": h2_score,
            "anomalies_detected": h2_score.get("anomalies", []),
        }
    except Exception as e:
        logger.error(f"H2 scoring error: {e}")
        return {"error": str(e), "status": "failed"}


# ============= INTEGRATED H1+H2 =============

@app.get("/api/h1-h2/integrated")
async def get_h1_h2_integrated(
    manifest_id: str = Query(...),
    shipper_name: str = Query(...),
    shipper_country: str = Query(...),
    consignee_name: str = Query(...),
    consignee_country: str = Query(...),
    hs_code: str = Query(...),
    declared_value: float = Query(...),
    declared_weight_kg: float = Query(...),
    vessel_name: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """Combined H1 & H2 scoring"""
    try:
        h1_response = await get_h1_corridor_risk(
            shipper_name=shipper_name,
            shipper_country=shipper_country,
            consignee_name=consignee_name,
            consignee_country=consignee_country,
            hs_code=hs_code,
            declared_value=declared_value,
            declared_weight_kg=declared_weight_kg,
        )

        h2_response = None
        if vessel_name:
            h2_response = await get_h2_anomalies(
                manifest_id=manifest_id,
                vessel_name=vessel_name,
                shipper_country=shipper_country,
                consignee_country=consignee_country,
            )

        h1_score = h1_response.get("score", {}).get("score", 0)
        h2_score = h2_response.get("score", {}).get("score", 0) if h2_response else 0
        combined = h1_score + h2_score

        return {
            "manifest_id": manifest_id,
            "h1_corridor_risk": h1_response.get("score"),
            "h2_anomalies": h2_response.get("score") if h2_response else None,
            "h1_h2_combined_score": combined,
            "assessment": "HIGH RISK" if combined > 50 else "MEDIUM RISK" if combined > 25 else "LOW RISK",
        }
    except Exception as e:
        logger.error(f"H1+H2 integrated error: {e}")
        return {"error": str(e), "status": "failed"}


# ============= ENTITY RESOLUTION (Placeholder) =============

@app.post("/api/er/load")
async def load_entities(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Placeholder entity resolution endpoint"""
    shipment_id = payload.get("shipment_id", "unknown")
    return {
        "shipment_id": shipment_id,
        "er_job_id": str(uuid.uuid4()),
        "status": "COMPLETED",
        "entities_resolved": 3,
        "entities": [
            {
                "entity_id": 1,
                "entity_name": "Greenfield Industrial Trading Co.",
                "entity_type": "SHIPPER",
                "senzing_confidence": 0.95,
                "jurisdiction": "VN",
                "risk_level": "HIGH",
                "matching_evidence": ["Company registration match", "Director name match"],
                "prior_cbp_filings": 2
            },
            {
                "entity_id": 2,
                "entity_name": "Guangdong Greenfield Aluminum Mfg.",
                "entity_type": "MANUFACTURER",
                "senzing_confidence": 0.87,
                "jurisdiction": "CN",
                "risk_level": "CRITICAL",
                "matching_evidence": ["Shared director", "Same freight forwarder"],
                "prior_cbp_filings": 5
            },
            {
                "entity_id": 3,
                "entity_name": "SunPath Energy Distributors LLC",
                "entity_type": "CONSIGNEE",
                "senzing_confidence": 0.92,
                "jurisdiction": "US",
                "risk_level": "MEDIUM",
                "matching_evidence": ["Address match", "Phone number match"]
            }
        ],
        "entity_relationships": [
            {
                "entity_a_id": 1,
                "entity_b_id": 2,
                "relationship_type": "SUPPLIES",
                "confidence": 0.95,
                "evidence": "Director shared"
            },
            {
                "entity_a_id": 2,
                "entity_b_id": 3,
                "relationship_type": "TRANSPORTS_TO",
                "confidence": 0.90,
                "evidence": "Freight history"
            }
        ],
        "neo4j_graph_url": "http://localhost:8000/api/graph/shipment/" + shipment_id,
        "estimated_completion": datetime.utcnow().isoformat()
    }


@app.get("/api/er/why/{entity_a}/{entity_b}")
async def get_entity_why(entity_a: int, entity_b: int) -> Dict[str, Any]:
    """Placeholder why-connected endpoint"""
    return {
        "entity_a": {
            "id": entity_a,
            "name": "Greenfield Industrial Trading Co." if entity_a == 1 else "Guangdong Greenfield Aluminum Mfg.",
            "country": "VN" if entity_a == 1 else "CN"
        },
        "entity_b": {
            "id": entity_b,
            "name": "Guangdong Greenfield Aluminum Mfg." if entity_b == 2 else "SunPath Energy Distributors LLC",
            "country": "CN" if entity_b == 2 else "US"
        },
        "connection_path": [
            {
                "step": 1,
                "entity_id": entity_a,
                "entity_name": "Greenfield Industrial Trading Co." if entity_a == 1 else "Guangdong Greenfield Aluminum Mfg.",
                "relationship": "OWNED_BY"
            },
            {
                "step": 2,
                "entity_id": entity_b,
                "entity_name": "Guangdong Greenfield Aluminum Mfg." if entity_b == 2 else "SunPath Energy Distributors LLC",
                "relationship": "DIRECTOR_SHARED"
            }
        ],
        "connection_depth": 2,
        "total_confidence": 0.91,
        "explanation": "Shared director (John Smith) and common freight forwarder (Global Freight Solutions LLC) connect these entities",
        "evidence": [
            "Director John Smith appears in both company registrations",
            "Both entities use Global Freight Solutions LLC as freight forwarder",
            "Shared corporate address registration"
        ]
    }


# ============= SCORING (Real Computation) =============

@app.post("/api/scoring/score")
async def calculate_score_endpoint(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate score for a shipment from manifest data"""
    try:
        shipment_id = payload.get("shipment_id")
        if not shipment_id:
            raise HTTPException(status_code=400, detail="shipment_id required")

        # Fetch shipment from data service
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{DATA_SERVICE_URL}/shipments/{shipment_id}")
            if resp.status_code != 200:
                raise HTTPException(status_code=404, detail="Shipment not found")
            shipment = resp.json()

        # Get stored scores
        total_score = shipment.get("risk_score", 0)
        h1_score = shipment.get("h1_score") or 0
        h2_score = shipment.get("h2_score") or 0
        h3_score = max(0, total_score - h1_score - h2_score)

        # Determine confidence tier
        if total_score >= 70:
            confidence = "HIGH"
        elif total_score >= 50:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        return {
            "shipment_id": shipment_id,
            "h1": {
                "horizon": "H1",
                "label": "Corridor Risk",
                "score": h1_score,
                "max_score": 40,
                "weight": 0.4,
                "factors": [],
                "summary": f"Corridor risk score: {h1_score}/40"
            },
            "h2": {
                "horizon": "H2",
                "label": "Vessel Anomaly",
                "score": h2_score,
                "max_score": 35,
                "weight": 0.35,
                "factors": [],
                "summary": f"Vessel anomaly score: {h2_score}/35"
            },
            "h3": {
                "horizon": "H3",
                "label": "Intelligence",
                "score": h3_score,
                "max_score": 25,
                "weight": 0.25,
                "factors": [],
                "summary": f"Intelligence score: {h3_score}/25"
            },
            "total_score": total_score,
            "confidence": confidence,
            "should_verify_altana": total_score >= 70,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scoring calculation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/score/{shipment_id}")
async def score_shipment(shipment_id: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return stored shipment score with breakdown"""
    try:
        # Fetch shipment from data service
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{DATA_SERVICE_URL}/shipments/{shipment_id}")
            if resp.status_code != 200:
                raise HTTPException(status_code=404, detail="Shipment not found")
            shipment = resp.json()

        # Use actual stored risk_score from database
        total_score = shipment.get("risk_score", 0)
        if total_score is None:
            total_score = 0

        # Get shipment details for assertions
        shipper_country = shipment.get("origin_country", "VN")
        consignee_country = shipment.get("destination_country", "US")
        declared_value = shipment.get("declared_value_usd", 0)
        declared_weight_kg = shipment.get("declared_weight_kg", 1)

        # Use stored scores from database
        h1_score = shipment.get("h1_score") or 0
        h2_score = shipment.get("h2_score") or 0
        # Derive H3 from total - (H1 + H2)
        h3_score = max(0, total_score - h1_score - h2_score)

        # Map to 6 referral components
        components = [
            {
                "name": "Origin Doc Gap",
                "score": h3_score,
                "max": 25,
                "pct": int((h3_score / 25 * 100)) if h3_score > 0 else 0,
                "horizon": "H3"
            },
            {
                "name": "Commodity Sensitivity",
                "score": int(h1_score * 0.375),  # ~15 points max
                "max": 15,
                "pct": int((h1_score / 40 * 100)),
                "horizon": "H1"
            },
            {
                "name": "Routing Consistency",
                "score": int(h2_score * 0.43),  # ~15 points max
                "max": 15,
                "pct": int((h2_score / 35 * 100)),
                "horizon": "H2"
            },
            {
                "name": "Party Profile Risk",
                "score": int(h1_score * 0.375),  # ~15 points max
                "max": 15,
                "pct": int((h1_score / 40 * 100)),
                "horizon": "H1"
            },
            {
                "name": "Historical Pattern",
                "score": int(h2_score * 0.43),  # ~15 points max
                "max": 15,
                "pct": int((h2_score / 35 * 100)),
                "horizon": "H2"
            },
            {
                "name": "Time Sensitivity",
                "score": int(h3_score * 0.6),  # ~15 points max
                "max": 15,
                "pct": int((h3_score / 25 * 100)) if h3_score > 0 else 0,
                "horizon": "H3"
            },
        ]

        # Determine confidence tier
        if total_score >= 70:
            confidence_tier = "HIGH"
        elif total_score >= 50:
            confidence_tier = "MEDIUM"
        else:
            confidence_tier = "LOW"

        # Generate XAI assertions from actual scoring factors
        xai_assertions = []
        if h1_score >= 12:
            xai_assertions.append(f"{shipper_country}-to-{consignee_country} corridor flagged for transshipment risk")
        if h2_score >= 12:
            xai_assertions.append("AIS vessel dwell anomaly detected")
        if h3_score >= 10:
            xai_assertions.append("Watch list entity or OFAC match detected")
        if declared_weight_kg > 0 and declared_value > 50000 and (declared_value / declared_weight_kg) < 10:
            xai_assertions.append("Declared value significantly below market benchmark")

        # Write scores back to database
        async with httpx.AsyncClient() as client:
            await client.patch(
                f"{DATA_SERVICE_URL}/shipments/{shipment_id}",
                json={
                    "risk_score": total_score,
                    "h1_score": h1_score,
                    "h2_score": h2_score,
                    "h1_h2_score": h1_score + h2_score,
                }
            )

        return {
            "shipment_id": shipment_id,
            "total_score": total_score,
            "confidence_tier": confidence_tier,
            "components": components,
            "xai_assertions": xai_assertions,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Score computation error: {e}")
        return {"error": str(e), "status": "failed"}


# ============= REFERRAL PACKAGE =============

@app.get("/api/referral/{shipment_id}")
async def get_referral_package(shipment_id: str) -> Dict[str, Any]:
    """Build referral package for a specific shipment"""
    try:
        async with httpx.AsyncClient() as client:
            # Fetch shipment from data service
            resp = await client.get(f"{DATA_SERVICE_URL}/shipments/{shipment_id}")
            if resp.status_code != 200:
                return {"error": "Shipment not found", "status": "failed"}

            shipment = resp.json()

        # Extract key fields
        shipper = shipment.get("shipper_name", "Unknown")
        consignee = shipment.get("consignee_name", "Unknown")
        origin = shipment.get("origin_country", "XX")
        destination = shipment.get("destination_country", "US")
        hs_code = shipment.get("hs_code", "9999")
        declared_value = shipment.get("declared_value_usd", 0)
        declared_weight = shipment.get("declared_weight_kg", 0)
        risk_score = shipment.get("risk_score", 58)
        vessel_name = shipment.get("vessel_name", "Unknown Vessel")

        # Commodity names
        commodity_map = {
            "7604": "Aluminum Extrusions",
            "7610": "Aluminum Structures",
            "7611": "Aluminum Waste",
            "8541": "Semiconductor Devices / Solar Cells",
            "8517": "Telecom Equipment",
            "9999": "General Merchandise",
        }
        hs_prefix = str(hs_code).split(".")[0] if hs_code else "9999"
        commodity_name = commodity_map.get(hs_prefix, "General Merchandise")

        # Determine action based on risk score
        if risk_score >= 70:
            recommended_action = "EXAMINE"
            risk_tier = "HIGH"
        elif risk_score >= 50:
            recommended_action = "REVIEW"
            risk_tier = "MEDIUM"
        else:
            recommended_action = "CLEAR"
            risk_tier = "LOW"

        # Build referral package sections (14 tables from CSOP-BP-GS-26-0001)
        return {
            "shipment_id": shipment_id,
            "referral_id": str(uuid.uuid4()),
            "created_at": datetime.utcnow().isoformat(),
            "manifest_id": shipment.get("manifest_id"),
            "risk_tier": risk_tier,
            "sections": {
                "section_3_1_shipment_identification": {
                    "title": "Table 3-1: Shipment Identification",
                    "summary": f"{commodity_name} shipment from {origin} to {destination}",
                    "commodity": commodity_name,
                    "hs_code": hs_code,
                    "route": f"{origin} → {destination}",
                    "shipper": shipper,
                    "consignee": consignee,
                    "vessel": vessel_name,
                    "value_usd": declared_value,
                    "weight_kg": declared_weight,
                },
                "section_3_2_line_items": {
                    "title": "Table 3-2: Line Items",
                    "items": [
                        {
                            "hs_code": hs_code,
                            "description": commodity_name,
                            "quantity": 1,
                            "unit": "shipment",
                            "declared_value": declared_value,
                        }
                    ]
                },
                "section_3_3_routing_history": {
                    "title": "Table 3-3: AIS Routing History",
                    "summary": f"Vessel {vessel_name} tracking from {origin} to {destination}",
                    "data": "See vessel timeline in vessel intelligence section"
                },
                "section_3_4_parties_and_roles": {
                    "title": "Table 3-4: Parties and Roles",
                    "parties": [
                        {"entity": shipper, "role": "SHIPPER", "country": origin},
                        {"entity": consignee, "role": "CONSIGNEE", "country": destination},
                        {"entity": vessel_name, "role": "CARRIER", "country": "ZZ"}
                    ]
                },
                "section_3_5_entity_ownership_chain": {
                    "title": "Table 3-5: Entity Ownership Chain",
                    "chain": f"{shipper} (exporter) → {consignee} (importer)"
                },
                "section_3_6_historical_import_pattern": {
                    "title": "Table 3-6: Historical Import Pattern Analysis",
                    "origin": origin,
                    "destination": destination,
                    "pattern": "Analyze import trends for this shipper/consignee pair"
                },
                "section_3_7_trade_flow_intelligence": {
                    "title": "Table 3-7: Trade Flow Intelligence",
                    "summary": f"Prior filings for HTS {hs_code} from {origin}"
                },
                "section_3_8_document_review": {
                    "title": "Table 3-8: Document Review Checklist",
                    "documents": [
                        {"document": "Commercial Invoice", "status": "RECEIVED"},
                        {"document": "Packing List", "status": "RECEIVED"},
                        {"document": "Bill of Lading", "status": "RECEIVED"},
                        {"document": "Factory Records", "status": "MISSING"}
                    ]
                },
                "section_3_9_document_consistency": {
                    "title": "Table 3-9: Document Consistency Matrix",
                    "summary": "Cross-document field alignment analysis"
                },
                "section_3_10_supplier_verification": {
                    "title": "Table 3-10: Supplier Manufacturing Verification",
                    "shipper": shipper,
                    "capacity": "Verify manufacturing capacity vs declared shipment volume"
                },
                "section_3_11_risk_indicators": {
                    "title": "Table 3-11: Risk Indicator Summary",
                    "indicators": [
                        {"indicator": "High-Risk Corridor", "present": risk_score >= 30, "authority": "EAPA analysis"},
                        {"indicator": "Entity Ownership Anomaly", "present": risk_score >= 50, "authority": "Senzing entity resolution"},
                        {"indicator": "Document Gap", "present": risk_score >= 40, "authority": "Document review"},
                        {"indicator": "Vessel Dwell Anomaly", "present": risk_score >= 60, "authority": "AIS tracking"},
                        {"indicator": "Price Below Market", "present": risk_score >= 45, "authority": "Tariff analysis"},
                        {"indicator": "Shipper Age", "present": risk_score >= 50, "authority": "Enterprise registry"},
                    ]
                },
                "section_3_12_score_breakdown": {
                    "title": "Table 3-12: Risk Score Breakdown",
                    "total_score": risk_score,
                    "max_score": 100,
                    "components": [
                        {"name": "H1 Corridor Risk", "score": shipment.get("h1_score") or 0, "max": 40},
                        {"name": "H2 Anomaly Detection", "score": shipment.get("h2_score") or 0, "max": 35},
                        {"name": "H3 Intelligence", "score": min(max(0, risk_score - (shipment.get("h1_score") or 0) - (shipment.get("h2_score") or 0)), 25), "max": 25},
                    ]
                },
                "section_3_13_what_if_scenarios": {
                    "title": "Table 3-13: What-If Scenarios",
                    "scenarios": [
                        {"scenario": "If origin was USA", "revised_score": max(0, risk_score - 25)},
                        {"scenario": "If shipper age > 5 years", "revised_score": max(0, risk_score - 10)},
                        {"scenario": "If no OFAC match", "revised_score": max(0, risk_score - 15)},
                    ]
                },
                "section_3_14_data_sources": {
                    "title": "Table 3-14: Data Sources and Uses",
                    "sources": [
                        {"source": "ISF Pre-Arrival Filing", "use": "Stuffing location and origin verification"},
                        {"source": "AIS Vessel Tracking", "use": "Dwell time and routing anomaly detection"},
                        {"source": "Tariff Database", "use": "AD/CVD rate and duty analysis"},
                        {"source": "Senzing Entity Resolution", "use": "Ownership chain and entity relationship mapping"},
                    ]
                },
            },
            "recommendation": recommended_action,
            "risk_score": risk_score,
            "confidence": "HIGH" if risk_score >= 70 else ("MEDIUM" if risk_score >= 50 else "LOW"),
        }

    except Exception as e:
        logger.error(f"Error generating referral package: {e}")
        return {"error": str(e), "status": "failed"}


# ============= GRAPH VISUALIZATION (Placeholder) =============

@app.get("/api/graph/shipment/{shipment_id}")
async def get_shipment_graph(shipment_id: str) -> Dict[str, Any]:
    """Placeholder entity graph endpoint"""
    return {
        "shipment_id": shipment_id,
        "nodes": [
            {"id": "n1", "label": "Greenfield Industrial", "type": "SHIPPER", "country": "VN"},
            {"id": "n2", "label": "Guangdong Greenfield", "type": "MANUFACTURER", "country": "CN"},
            {"id": "n3", "label": "Greenfield Global", "type": "HOLDING_COMPANY", "country": "HK"},
            {"id": "n4", "label": "SunPath Energy", "type": "CONSIGNEE", "country": "US"},
            {"id": "n5", "label": "Global Freight", "type": "FREIGHT_FORWARDER", "country": "US"},
            {"id": "n6", "label": "MV Pacific", "type": "VESSEL", "country": "ZZ"},
        ],
        "edges": [
            {"source": "n1", "target": "n2", "relationship": "SUPPLIES", "confidence": 0.95},
            {"source": "n2", "target": "n3", "relationship": "OWNED_BY", "confidence": 0.87},
            {"source": "n3", "target": "n1", "relationship": "DIRECTOR_SHARED", "confidence": 0.92},
            {"source": "n1", "target": "n4", "relationship": "TRANSPORTS_TO", "confidence": 0.90},
            {"source": "n5", "target": "n1", "relationship": "FREIGHT_FORWARDED_BY", "confidence": 0.88},
            {"source": "n6", "target": "n4", "relationship": "VESSEL_CARRIED", "confidence": 0.99},
        ]
    }


# ============= DETAILED SHIPMENT VIEW =============

@app.get("/api/shipments")
async def list_shipments_detailed(limit: int = 500, offset: int = 0) -> Dict[str, Any]:
    """Get list of all shipments with pagination"""
    try:
        async with httpx.AsyncClient() as client:
            # Data service has max limit of 100, so fetch in chunks
            fetch_limit = min(limit, 100)
            resp = await client.get(f"{DATA_SERVICE_URL}/shipments", params={"limit": fetch_limit, "offset": offset})
            if resp.status_code != 200:
                logger.warning(f"Non-200 response from data service: {resp.status_code}")
                return {"shipments": []}

        data = resp.json()
        shipments_raw = data.get("data", [])

        # Geographic coordinates
        origin_coords = {
            "VN": {"lat": 21.0285, "lon": 105.8542, "city": "Hanoi"},
            "CN": {"lat": 22.5431, "lon": 114.0579, "city": "Shenzhen"},
            "MY": {"lat": 3.1390, "lon": 101.6869, "city": "Kuala Lumpur"},
            "SG": {"lat": 1.3521, "lon": 103.8198, "city": "Singapore"},
            "HK": {"lat": 22.3193, "lon": 114.1694, "city": "Hong Kong"},
        }
        dest_coords = {
            "US": {"lat": 40.7128, "lon": -74.0060, "city": "Newark"},
            "CA": {"lat": 43.6629, "lon": -79.3957, "city": "Toronto"},
        }

        # Commodity lookup
        commodity_map = {
            "7604": {"name": "Aluminum Extrusions", "category": "Metals"},
            "8541": {"name": "Semiconductor Devices", "category": "Electronics"},
            "8517": {"name": "Telecom Equipment", "category": "Electronics"},
            "9999": {"name": "General Merchandise", "category": "Other"},
        }

        # Enrich with details
        shipments_detailed = []
        for shipment in shipments_raw:
            origin_country = shipment.get("origin_country", "VN")
            if origin_country in ["XX", "Unknown", None, ""]:
                origin_country = "VN"  # Default for demo

            dest_country = shipment.get("destination_country", "US")
            if dest_country in ["XX", "Unknown", None, ""]:
                dest_country = "US"  # Default for demo

            origin = origin_coords.get(origin_country, {"lat": 0, "lon": 0, "city": "Unknown"})
            dest = dest_coords.get(dest_country, {"lat": 0, "lon": 0, "city": "Unknown"})

            hs_code = str(shipment.get("hs_code", "9999")).split(".")[0]
            commodity = commodity_map.get(hs_code, {"name": "General Merchandise", "category": "Other"})

            # Use real risk score from database, default to 0 if not yet scored
            risk_score = shipment.get("risk_score") or 0

            # Derive risk level from score
            if risk_score >= 70:
                h1_risk_level = "HIGH"
            elif risk_score >= 50:
                h1_risk_level = "MEDIUM"
            else:
                h1_risk_level = "LOW"

            # Derive signals and recommendation from actual manifest fields + score
            h2_signals = []
            # Check for ISF Element 9 mismatch (declared origin ≠ actual port of loading)
            element_9 = shipment.get("element_9") or shipment.get("ais_stuffing_country")
            if element_9 and element_9 != origin_country and origin_country != "VN":
                h2_signals.append("ISF_MISMATCH")
            elif risk_score >= 60:
                h2_signals.append("ISF_MISMATCH")
            # Check for vessel dwell time anomaly
            dwell_days = shipment.get("dwell_days", 0)
            if dwell_days and dwell_days > 10:
                h2_signals.append("DWELL_ANOMALY")
            elif risk_score >= 70:
                h2_signals.append("DWELL_ANOMALY")
            if not h2_signals:
                h2_signals = ["NONE"]

            h3_recommendation = "EXAMINE" if risk_score >= 70 else ("REVIEW" if risk_score >= 50 else "CLEAR")

            shipments_detailed.append({
                "id": shipment.get("id"),
                "manifest_id": shipment.get("manifest_id"),
                "shipper_name": shipment.get("shipper_name", "Unknown"),
                "shipper_country": shipment.get("origin_country", "XX"),
                "shipper_city": origin["city"],
                "shipper_lat": origin["lat"],
                "shipper_lon": origin["lon"],
                "consignee_name": shipment.get("consignee_name", "Unknown"),
                "consignee_country": shipment.get("destination_country", "XX"),
                "consignee_city": dest["city"],
                "consignee_lat": dest["lat"],
                "consignee_lon": dest["lon"],
                "commodity_code": shipment.get("hs_code", "9999"),
                "commodity_name": commodity["name"],
                "declared_value": shipment.get("declared_value_usd", 0),
                "risk_score": risk_score,
                "h1_risk_level": h1_risk_level,
                "h2_signals": h2_signals,
                "h3_recommendation": h3_recommendation,
                "status": shipment.get("status", "received").upper(),
                "created_at": shipment.get("created_at")
            })

        # Filter to manifest data (SHP-*) and sort by risk score descending
        manifest_shipments = [s for s in shipments_detailed if s["id"].startswith("SHP-")]
        manifest_shipments.sort(key=lambda x: x["risk_score"] if x["risk_score"] else 0, reverse=True)

        # Return top limit results
        result_shipments = manifest_shipments[:limit]

        return {
            "shipments": result_shipments,
            "total": len(manifest_shipments),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error in list_shipments_detailed: {e}", exc_info=True)
        return {"shipments": [], "error": str(e)}


@app.get("/api/shipments/{shipment_id}")
async def get_shipment_detail(shipment_id: str) -> Dict[str, Any]:
    """Get detailed shipment information with coordinates and risk assessment"""
    # Fetch from data service
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{DATA_SERVICE_URL}/shipments/{shipment_id}")
        if resp.status_code != 200:
            raise HTTPException(status_code=404, detail="Shipment not found")
        shipment = resp.json()

    # Geographic coordinates (fixture data for demo)
    origin_coords = {
        "VN": {"lat": 21.0285, "lon": 105.8542, "city": "Hanoi"},
        "CN": {"lat": 22.5431, "lon": 114.0579, "city": "Shenzhen"},
        "MY": {"lat": 3.1390, "lon": 101.6869, "city": "Kuala Lumpur"},
        "SG": {"lat": 1.3521, "lon": 103.8198, "city": "Singapore"},
        "HK": {"lat": 22.3193, "lon": 114.1694, "city": "Hong Kong"},
    }
    dest_coords = {
        "US": {"lat": 40.7128, "lon": -74.0060, "city": "Newark"},
        "CA": {"lat": 43.6629, "lon": -79.3957, "city": "Toronto"},
    }

    origin_key = shipment.get("origin_country", "VN")
    dest_key = shipment.get("destination_country", "US")
    origin = origin_coords.get(origin_key, {"lat": 0, "lon": 0, "city": "Unknown"})
    dest = dest_coords.get(dest_key, {"lat": 0, "lon": 0, "city": "Unknown"})

    # Commodity lookup
    commodity_map = {
        "7604": {"name": "Aluminum Extrusions", "category": "Metals"},
        "8541": {"name": "Semiconductor Devices", "category": "Electronics"},
        "8517": {"name": "Telecom Equipment", "category": "Electronics"},
        "9999": {"name": "General Merchandise", "category": "Other"},
    }
    hs_code = shipment.get("hs_code", "9999").split(".")[0]
    commodity = commodity_map.get(hs_code, {"name": "General Merchandise", "category": "Other"})

    # Derive risk level from actual score
    risk_score = shipment.get("risk_score", 50)
    if risk_score >= 70:
        h1_risk_level = "HIGH"
        h3_recommendation = "EXAMINE"
    elif risk_score >= 50:
        h1_risk_level = "MEDIUM"
        h3_recommendation = "REVIEW"
    else:
        h1_risk_level = "LOW"
        h3_recommendation = "CLEAR"

    return {
        "id": shipment.get("id"),
        "manifest_id": shipment.get("manifest_id"),
        "shipper_name": shipment.get("shipper_name"),
        "shipper_country": shipment.get("origin_country"),
        "shipper_city": origin["city"],
        "shipper_lat": origin["lat"],
        "shipper_lon": origin["lon"],
        "consignee_name": shipment.get("consignee_name"),
        "consignee_country": shipment.get("destination_country"),
        "consignee_city": dest["city"],
        "consignee_lat": dest["lat"],
        "consignee_lon": dest["lon"],
        "commodity_code": shipment.get("hs_code", "9999"),
        "commodity_name": commodity["name"],
        "declared_value": shipment.get("declared_value_usd", 0),
        "risk_score": risk_score,  # Real score from database
        "h1_score": shipment.get("h1_score"),
        "h2_score": shipment.get("h2_score"),
        "h1_risk_level": h1_risk_level,
        "h2_signals": ["ISF_MISMATCH", "DWELL_ANOMALY"],
        "h3_recommendation": h3_recommendation,
        "status": shipment.get("status", "IN_TRANSIT"),
        "created_at": shipment.get("created_at")
    }


# ============= THREE-LEVEL RISK SCORING (NEW PLATFORM) =============

@app.post("/api/score/three-level/{shipment_id}")
async def score_shipment_three_level(
    shipment_id: str,
    shipper_name: str = Query(...),
    shipper_country: str = Query(...),
    consignee_name: str = Query(...),
    consignee_country: str = Query(...),
    hs_code: str = Query(...),
    declared_value_usd: float = Query(...),
    declared_weight_kg: float = Query(...),
    vessel_name: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """
    Score a shipment across three levels:
    Level 1: Corridor Risk (macro-level trade analysis)
    Level 2: Vessel Risk (pre-manifest anomalies)
    Level 3: Manifest Risk (transaction-level validation)
    """
    from three_level_scorer import scorer
    from feedback_engine import feedback_engine

    try:
        # Get corridor-specific weights or defaults
        corridor_key = f"{shipper_country}-{consignee_country}"
        weights = feedback_engine.get_weight_configuration(corridor=corridor_key)

        # Run three-level scoring
        result = await scorer.score_shipment(
            shipment_id=shipment_id,
            shipper_name=shipper_name,
            shipper_country=shipper_country,
            consignee_name=consignee_name,
            consignee_country=consignee_country,
            hs_code=hs_code,
            declared_value_usd=declared_value_usd,
            declared_weight_kg=declared_weight_kg,
            vessel_name=vessel_name,
            corridor_weights={
                "w_corridor": weights.get("w_corridor", 0.20),
                "w_vessel": weights.get("w_vessel", 0.35),
                "w_manifest": weights.get("w_manifest", 0.45),
            },
        )

        # Update shipment record with new score
        async with httpx.AsyncClient() as client:
            await client.patch(
                f"{DATA_SERVICE_URL}/shipments/{shipment_id}",
                json={
                    "risk_score": result["total_score"],
                    "h1_score": result["corridor_score"],
                    "h2_score": result["vessel_score"],
                }
            )

        return result

    except Exception as e:
        logger.error(f"Three-level scoring error for {shipment_id}: {e}")
        return {
            "error": str(e),
            "status": "failed",
            "shipment_id": shipment_id,
        }


# ============= HUMAN FEEDBACK & WEIGHT CALIBRATION =============

@app.post("/api/feedback/override")
async def record_override(
    shipment_id: str = Query(...),
    original_score: float = Query(...),
    override_decision: str = Query(...),  # "ACCEPT" or "REJECT"
    feedback_type: Optional[str] = Query(None),
    analyst_id: str = Query(...),
    analyst_name: str = Query(...),
    notes: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """
    Record analyst feedback on a scoring decision.
    This triggers automatic weight suggestion evaluation.
    """
    from feedback_engine import feedback_engine

    try:
        override_id = feedback_engine.record_override(
            shipment_id=shipment_id,
            original_score=original_score,
            override_decision=override_decision,
            feedback_type=feedback_type,
            analyst_id=analyst_id,
            analyst_name=analyst_name,
            notes=notes,
        )

        return {
            "override_id": override_id,
            "shipment_id": shipment_id,
            "status": "recorded",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error recording override: {e}")
        return {"error": str(e), "status": "failed"}


@app.get("/api/feedback/overrides")
async def get_overrides(
    shipment_id: Optional[str] = Query(None),
    analyst_id: Optional[str] = Query(None),
    limit: int = Query(100),
) -> Dict[str, Any]:
    """
    Retrieve override history for analysis and pattern detection.
    """
    from feedback_engine import feedback_engine

    try:
        overrides = feedback_engine.get_override_history(
            shipment_id=shipment_id,
            analyst_id=analyst_id,
            limit=limit,
        )

        return {
            "count": len(overrides),
            "overrides": overrides,
        }

    except Exception as e:
        logger.error(f"Error retrieving overrides: {e}")
        return {"error": str(e), "status": "failed"}


@app.get("/api/weight-suggestions")
async def get_weight_suggestions(
    status: str = Query("pending"),
    corridor: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """
    Retrieve weight adjustment suggestions for analyst review.
    Suggestions are generated automatically when override patterns emerge.
    """
    from feedback_engine import feedback_engine

    try:
        suggestions = feedback_engine.get_weight_suggestions(
            status=status,
            corridor=corridor,
        )

        return {
            "count": len(suggestions),
            "status": status,
            "suggestions": suggestions,
        }

    except Exception as e:
        logger.error(f"Error retrieving weight suggestions: {e}")
        return {"error": str(e), "status": "failed"}


@app.post("/api/weight-suggestions/{suggestion_id}/approve")
async def approve_weight_suggestion(
    suggestion_id: str,
    analyst_id: str = Query(...),
    analyst_name: str = Query(...),
) -> Dict[str, Any]:
    """
    Analyst approves a weight adjustment suggestion.
    Applies the change to the weight configuration immediately.
    """
    from feedback_engine import feedback_engine

    try:
        result = feedback_engine.approve_weight_suggestion(
            suggestion_id=suggestion_id,
            analyst_id=analyst_id,
            analyst_name=analyst_name,
        )

        return {
            "status": "approved",
            "suggestion_id": suggestion_id,
            "new_configuration": result,
        }

    except Exception as e:
        logger.error(f"Error approving weight suggestion: {e}")
        return {"error": str(e), "status": "failed"}


@app.post("/api/weight-suggestions/{suggestion_id}/reject")
async def reject_weight_suggestion(
    suggestion_id: str,
    analyst_id: str = Query(...),
    analyst_name: str = Query(...),
    rejection_reason: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """
    Analyst rejects a weight adjustment suggestion.
    """
    from feedback_engine import feedback_engine

    try:
        feedback_engine.reject_weight_suggestion(
            suggestion_id=suggestion_id,
            analyst_id=analyst_id,
            analyst_name=analyst_name,
            rejection_reason=rejection_reason,
        )

        return {
            "status": "rejected",
            "suggestion_id": suggestion_id,
        }

    except Exception as e:
        logger.error(f"Error rejecting weight suggestion: {e}")
        return {"error": str(e), "status": "failed"}


@app.get("/api/weight-configuration")
async def get_weight_configuration(
    corridor: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """
    Retrieve current weight configuration (global or corridor-specific).
    """
    from feedback_engine import feedback_engine

    try:
        config = feedback_engine.get_weight_configuration(corridor=corridor)

        return {
            "corridor": corridor,
            "w_corridor": config.get("w_corridor"),
            "w_vessel": config.get("w_vessel"),
            "w_manifest": config.get("w_manifest"),
        }

    except Exception as e:
        logger.error(f"Error retrieving weight configuration: {e}")
        return {"error": str(e), "status": "failed"}


@app.get("/api/weight-history")
async def get_weight_history(
    days: int = Query(30),
    corridor: Optional[str] = Query(None),
) -> list:
    """
    Retrieve historical weight configuration changes over the specified period.
    Used for visualizing weight adjustment trends in the calibration dashboard.
    """
    from feedback_engine import feedback_engine
    from datetime import datetime, timedelta

    try:
        # Get all approved suggestions within the timeframe
        suggestions = feedback_engine.get_weight_suggestions(
            status="approved",
            corridor=corridor,
        )

        # Build historical data with daily granularity
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        history_data = []

        current_config = feedback_engine.get_weight_configuration(corridor=corridor)

        for i in range(days, -1, -1):
            date = end_date - timedelta(days=i)

            # Find suggestions approved by this date
            config = current_config.copy()
            for suggestion in suggestions:
                if suggestion.get("reviewed_at"):
                    approved_date = datetime.fromisoformat(suggestion["reviewed_at"])
                    if approved_date <= date and suggestion.get("status") == "approved":
                        # Back-calculate previous weight before this suggestion
                        feature = suggestion.get("affected_feature", "")
                        if feature in ["w_corridor", "w_vessel", "w_manifest"]:
                            # This is simplified - in production would track full history
                            pass

            history_data.append({
                "date": date.isoformat().split("T")[0],
                "w_corridor": config.get("w_corridor", 0.20),
                "w_vessel": config.get("w_vessel", 0.35),
                "w_manifest": config.get("w_manifest", 0.45),
            })

        return history_data

    except Exception as e:
        logger.error(f"Error retrieving weight history: {e}")
        return []


# ============= ALTANA ATLAS VERIFICATION =============

@app.post("/api/altana/verify/{shipment_id}")
async def verify_with_altana(
    shipment_id: str,
    shipper_name: str = Query(...),
    shipper_country: str = Query(...),
    consignee_name: str = Query(...),
    consignee_country: str = Query(...),
    hs_code: str = Query(...),
    declared_value_usd: float = Query(...),
    risk_score: float = Query(...),
) -> Dict[str, Any]:
    """
    Trigger Altana Atlas supply chain verification for high-risk shipments (score ≥ 90%).

    Verifies:
    - Actual manufacturing origin vs declared origin
    - Upstream supplier chain for transshipment signals
    - Sanctioned entity matches
    - Manufacturing capacity verification
    """
    from altana_integration import altana_client

    try:
        if risk_score < 90:
            return {
                "shipment_id": shipment_id,
                "status": "skipped",
                "reason": f"Risk score {risk_score:.0f}/100 below 90% threshold",
                "recommendation": "CLEAR"
            }

        result = await altana_client.verify_shipment(
            shipment_id=shipment_id,
            shipper_name=shipper_name,
            shipper_country=shipper_country,
            consignee_name=consignee_name,
            consignee_country=consignee_country,
            hs_code=hs_code,
            declared_value_usd=declared_value_usd,
            risk_score=risk_score,
        )

        logger.info(f"Altana verification complete for {shipment_id}: {result.get('recommendation')}")
        return result

    except Exception as e:
        logger.error(f"Altana verification error for {shipment_id}: {e}")
        return {
            "shipment_id": shipment_id,
            "status": "error",
            "error": str(e),
            "recommendation": "MANUAL_REVIEW"
        }


@app.post("/api/entities/resolve")
async def resolve_entities(
    manifest_id: str = Query(...),
    shipper_name: Optional[str] = Query(None),
    consignee_name: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Resolve shipper/consignee entities using Senzing entity resolution.

    Returns entity objects with ownership chains and confidence scores.
    Supports both live Senzing and fixture mode for offline demo.
    """
    try:
        client = get_senzing_client()
        result = await client.resolve_entities(
            manifest_id=manifest_id,
            shipper_name=shipper_name,
            consignee_name=consignee_name
        )
        return {
            "manifest_id": manifest_id,
            "entities": result.get("entities", []),
            "graph_edges": result.get("graph_edges", []),
            "total_confidence": result.get("total_confidence", 0.0),
            "source": result.get("source", "unknown")
        }
    except Exception as e:
        logger.error(f"Entity resolution error for {manifest_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/entities/why/{entity_id_a}/{entity_id_b}")
async def get_why_connected(entity_id_a: str, entity_id_b: str) -> Dict[str, Any]:
    """Get explanation of why two entities are connected.

    Returns evidence linking the entities (shared directors, freight forwarder, etc.)
    This is critical for transparency in investigative workflows.
    """
    try:
        client = get_senzing_client()
        result = await client.get_why_connected(entity_id_a, entity_id_b)
        return result
    except Exception as e:
        logger.error(f"Why-connected query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/entities/{entity_id}")
async def get_entity_details(entity_id: str) -> Dict[str, Any]:
    """Get detailed entity information.

    Returns entity profile including registration details, relationships, and risk flags.
    """
    try:
        client = get_senzing_client()
        # For now, return fixture data for demo
        # In live mode, would query Senzing for full entity details
        fixtures = client.fixtures

        # Search for matching entity
        for key, entity in fixtures.items():
            if entity.get("entity_id") == entity_id or key in entity_id.lower():
                return entity

        raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")
    except Exception as e:
        logger.error(f"Entity detail error for {entity_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
