"""
Horizon 1 & 2 API Routes — Live data with AI scoring
NOTE: Deprecated - these endpoints superseded by /api/score/full-breakdown/{id} (7-factor model)
"""
import logging
from fastapi import APIRouter, Query
from services.external_apis.h1_adapters import OpenCorporatesAdapter, ComtradeAdapter, ITCTariffsAdapter
from services.external_apis.h2_adapters import AISAdapter, PortAuthorityAdapter

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize adapters
oc_adapter = OpenCorporatesAdapter()
comtrade_adapter = ComtradeAdapter()
itc_adapter = ITCTariffsAdapter()
ais_adapter = AISAdapter()
port_adapter = PortAuthorityAdapter()

# NOTE: Old H1/H2 scorers removed (CLEANUP_PHASE_0) - use RiskScoringEngine instead


@router.get("/h1/corridor-risk")
async def get_h1_corridor_risk(
    shipper_name: str = Query(...),
    shipper_country: str = Query(...),
    consignee_name: str = Query(...),
    consignee_country: str = Query(...),
    hs_code: str = Query(...),
    declared_value: float = Query(...),
    declared_weight_kg: float = Query(...),
):
    """
    Horizon 1: Corridor Risk Assessment

    Uses live APIs to:
    1. Look up shipper company (OpenCorporates)
    2. Get trade benchmarks (UN Comtrade)
    3. Fetch tariff/duty rates (ITC)
    4. Score corridor risk with ML model
    """
    try:
        # Fetch shipper info
        shipper_info = await oc_adapter.fetch(company_name=shipper_name, jurisdiction=shipper_country)

        # Fetch trade benchmarks
        benchmark_data = await comtrade_adapter.fetch(
            hs_code=hs_code,
            reporter=shipper_country,
            partner=consignee_country,
        )

        # Fetch tariff/duty info
        tariff_info = await itc_adapter.fetch(
            hs_code=hs_code,
            origin_country=shipper_country,
        )

        # Score with ML model
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
            "shipper_info": {k: v for k, v in shipper_info.items() if k != "_metadata"},
            "tariff_info": {k: v for k, v in tariff_info.items() if k != "_metadata"},
        }

    except Exception as e:
        logger.error(f"H1 scoring error: {e}")
        return {"error": str(e), "status": "failed"}


@router.get("/h2/anomaly-detection")
async def get_h2_anomalies(
    manifest_id: str = Query(...),
    vessel_name: str = Query(...),
    shipper_country: str = Query(...),
    consignee_country: str = Query(...),
):
    """
    Horizon 2: Pre-Intelligence Anomaly Detection

    Uses live APIs to:
    1. Fetch AIS vessel data (tracking, dwell times)
    2. Get port authority records
    3. Infer ISF Element 9 (container stuffing location)
    4. Score anomalies with ML model
    """
    try:
        # Fetch vessel AIS data
        vessel_data = await ais_adapter.fetch(vessel_name=vessel_name)

        # Get dwell anomaly details
        if vessel_data.get("current_port"):
            dwell_details = await ais_adapter.get_dwell_anomaly(
                vessel_name=vessel_name,
                port=vessel_data["current_port"],
                dwell_days=vessel_data.get("port_dwell_days", 0),
            )
            vessel_data.update(dwell_details)

        # Fetch port authority records
        port_data = await port_adapter.fetch(port_code=vessel_data.get("current_port", ""), vessel_name=vessel_name)

        # Infer ISF Element 9 (stuffing location)
        isf_data = await port_adapter.get_isf_stuffing_location(manifest_id=manifest_id, container_number="")

        # Score anomalies
        h2_score = await h2_scorer.score(
            vessel_data=vessel_data,
            isf_data=isf_data,
            port_calls=[port_data],
        )

        return {
            "manifest_id": manifest_id,
            "vessel": vessel_name,
            "score": h2_score,
            "data_sources": {
                "ais": vessel_data.get("_metadata", {}),
                "port": port_data.get("_metadata", {}),
                "isf": isf_data.get("_metadata", {}),
            },
            "vessel_data": {k: v for k, v in vessel_data.items() if k != "_metadata"},
            "anomalies_detected": h2_score.get("anomalies", []),
        }

    except Exception as e:
        logger.error(f"H2 scoring error: {e}")
        return {"error": str(e), "status": "failed"}


@router.get("/h1-h2/integrated")
async def get_h1_h2_integrated(
    manifest_id: str = Query(...),
    shipper_name: str = Query(...),
    shipper_country: str = Query(...),
    consignee_name: str = Query(...),
    consignee_country: str = Query(...),
    hs_code: str = Query(...),
    declared_value: float = Query(...),
    declared_weight_kg: float = Query(...),
    vessel_name: str = Query(None),
):
    """
    Combined H1 & H2 scoring (Horizon 1 + Horizon 2)

    Returns integrated risk assessment using both corridors and anomalies
    """
    try:
        # Get H1 corridor risk
        h1_response = await get_h1_corridor_risk(
            shipper_name=shipper_name,
            shipper_country=shipper_country,
            consignee_name=consignee_name,
            consignee_country=consignee_country,
            hs_code=hs_code,
            declared_value=declared_value,
            declared_weight_kg=declared_weight_kg,
        )

        # Get H2 anomalies (if vessel provided)
        h2_response = None
        if vessel_name:
            h2_response = await get_h2_anomalies(
                manifest_id=manifest_id,
                vessel_name=vessel_name,
                shipper_country=shipper_country,
                consignee_country=consignee_country,
            )

        # Combine scores
        h1_score = h1_response.get("score", {}).get("score", 0)
        h2_score = h2_response.get("score", {}).get("score", 0) if h2_response else 0

        combined_h1_h2_score = h1_score + h2_score  # Max 75/100 (40+35)

        return {
            "manifest_id": manifest_id,
            "h1_corridor_risk": h1_response.get("score"),
            "h2_anomalies": h2_response.get("score") if h2_response else None,
            "h1_h2_combined_score": combined_h1_h2_score,
            "h1_h2_max_score": 75,
            "assessment": "HIGH RISK" if combined_h1_h2_score > 50 else "MEDIUM RISK" if combined_h1_h2_score > 25 else "LOW RISK",
        }

    except Exception as e:
        logger.error(f"H1+H2 integrated error: {e}")
        return {"error": str(e), "status": "failed"}
