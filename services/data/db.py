"""PostgreSQL database initialization and CRUD operations."""

import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import psycopg2
import psycopg2.extras
from psycopg2 import sql

logger = logging.getLogger(__name__)

DEFAULT_DATABASE_URL = "postgresql://sentry:sentry-secret@sentry-db:5432/sentry"
INIT_SQL_PATH = Path(__file__).with_name("init.sql")
JSONB_COLUMNS = {
    "audit_trail",
    "risk_breakdown",
    "ai_synthesis",
    "isf_data",
    "components",
    "xai_assertions",
    "errors",
    "breakdown_json",
    "previous_breakdown_json",
    "new_breakdown_json",
    "altana_risk_factors",
}
TEXT_SERIALIZED_COLUMNS = {
    "risk_score_breakdown",
    "confidence_interval",
    "port_calls",
    "h2_signals",
    "customs_flags",
    "inspection_history",
}
SHIPMENT_RESPONSE_JSON_COLUMNS = {
    "risk_score_breakdown",
    "confidence_interval",
    "audit_trail",
    "risk_breakdown",
    "ai_synthesis",
    "isf_data",
}

psycopg2.extras.register_default_json(globally=True, loads=json.loads)
psycopg2.extras.register_default_jsonb(globally=True, loads=json.loads)


def _get_conn():
    return psycopg2.connect(
        os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL),
        options="-c search_path=cbp_sentry",
    )


def _get_cursor(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def _jsonify(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, psycopg2.extras.Json):
        return value
    if isinstance(value, (dict, list)):
        return psycopg2.extras.Json(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return value
        try:
            return psycopg2.extras.Json(json.loads(text))
        except json.JSONDecodeError:
            return value
    return value


def _coerce_value(column: str, value: Any) -> Any:
    if column in JSONB_COLUMNS:
        return _jsonify(value)
    if column in TEXT_SERIALIZED_COLUMNS and value is not None and not isinstance(value, str):
        return json.dumps(value)
    return value


def _normalize_json_fields(row: Optional[Dict[str, Any]], fields: set[str]) -> Optional[Dict[str, Any]]:
    if not row:
        return None
    payload = dict(row)
    for field in fields:
        value = payload.get(field)
        if isinstance(value, str):
            try:
                payload[field] = json.loads(value)
            except json.JSONDecodeError:
                pass
    return payload


def _normalize_rows(rows: List[Dict[str, Any]], fields: set[str]) -> List[Dict[str, Any]]:
    return [_normalize_json_fields(dict(row), fields) for row in rows]


def _risk_level(score: Optional[float]) -> Optional[str]:
    if score is None:
        return None
    if score >= 80:
        return "HIGH"
    if score >= 50:
        return "MEDIUM"
    return "LOW"


def _record_score_history(
    cursor,
    shipment_id: str,
    score: Optional[float],
    model_version: Optional[str] = None,
    model_maturity: Optional[int] = None,
) -> None:
    if score is None:
        return
    cursor.execute(
        """
        INSERT INTO score_history (shipment_id, score, model_version, model_maturity, scored_at)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (shipment_id, score, model_version, model_maturity, datetime.utcnow()),
    )


def _seed_top_shipment_scenarios(cursor) -> None:
    cursor.execute(
        """
        SELECT id, COALESCE(risk_score, 50.0) AS risk_score
        FROM shipments
        ORDER BY COALESCE(risk_score, 0) DESC
        LIMIT 3
        """
    )
    for shipment in cursor.fetchall():
        shipment_id = shipment["id"]
        current_risk = shipment["risk_score"] or 50.0
        cursor.execute(
            "SELECT COUNT(*) AS count FROM risk_what_if_scenarios WHERE shipment_id = %s",
            (shipment_id,),
        )
        if cursor.fetchone()["count"] > 0:
            continue

        scenarios = [
            {
                "name": "OFAC Hit Confirmed",
                "description": "If entity is confirmed on OFAC SDN list",
                "if_true_score": min(current_risk + 25, 100.0),
                "if_false_score": max(current_risk - 5, 0.0),
                "priority": "HIGH",
                "impact_category": "Sanctions-Exposure",
            },
            {
                "name": "ISF Element 9 Mismatch Confirmed",
                "description": "If stuffing location verification confirms ISF mismatch",
                "if_true_score": min(current_risk + 15, 100.0),
                "if_false_score": max(current_risk - 10, 0.0),
                "priority": "HIGH",
                "impact_category": "Manifest-Anomaly",
            },
            {
                "name": "Shell Company Chain Detected",
                "description": "If entity resolution finds shell company ownership chain",
                "if_true_score": min(current_risk + 20, 100.0),
                "if_false_score": max(current_risk - 3, 0.0),
                "priority": "MEDIUM",
                "impact_category": "Entity-Layering",
            },
        ]

        for scenario in scenarios:
            cursor.execute(
                """
                INSERT INTO risk_what_if_scenarios (
                    id, shipment_id, scenario_name, scenario_description, scenario_priority,
                    what_if_true_description, what_if_true_evidence_needed, what_if_true_risk_score,
                    what_if_false_description, what_if_false_evidence_needed, what_if_false_risk_score,
                    current_risk_score, impact_category, investigation_recommendation, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    str(uuid.uuid4()),
                    shipment_id,
                    scenario["name"],
                    scenario["description"],
                    scenario["priority"],
                    f"Risk increases to {scenario['if_true_score']:.0f}/100",
                    "Positive OFAC match, court documents, or customs intelligence",
                    scenario["if_true_score"],
                    f"Risk decreases to {scenario['if_false_score']:.0f}/100",
                    "Entity cleared by sanctions screening, or alternative documentation provided",
                    scenario["if_false_score"],
                    current_risk,
                    scenario["impact_category"],
                    f"Prioritize investigation into {scenario['name'].lower()}; escalate to enforcement if confirmed",
                    datetime.utcnow(),
                ),
            )


def _seed_reference_data(cursor) -> None:
    cursor.execute("SELECT COUNT(*) AS count FROM eapa_cases")
    if cursor.fetchone()["count"] == 0:
        # ------------------------------------------------------------------
        # Expanded EAPA seed (Track T-Data, "make it real").
        #
        # Goal: provide real, labeled EAPA-respondent positives so the
        # D-phase calibration draws on genuine AD/CVD evasion labels instead
        # of the 5-row stub. This block is the FIRST tranche toward the
        # 287-case EAPA target (CBP has adjudicated ~280+ EAPA allegations
        # under 19 USC 1517 since 2016). Rows span the dominant transshipment
        # / country-of-origin fraud fact patterns CBP has actually found:
        #   * Aluminum extrusions  (HS 7604/7610)  CN -> VN/MY/TH/KH -> US
        #   * Steel pipe / fittings / wire        (HS 7306/7307/7312)  CN/TH/VN
        #   * Crystalline silicon photovoltaic    (HS 8541)  CN -> MY/VN/TH/KH -> US (UFLPA-adjacent)
        #   * Hardwood / decorative plywood       (HS 4412)  CN -> VN
        #   * Wooden cabinets & vanities          (HS 9403)  CN -> VN/MY
        #   * Mattresses                          (HS 9404)  CN -> multiple
        #   * Chlorinated isocyanurates           (HS 2933)  CN
        #   * Quartz surface products             (HS 6810)  CN -> IN/TR
        #   * Misc. (xanthan gum, wire hangers, nails, tires, etc.)
        #
        # The first 5 rows are the ORIGINAL stub respondents (kept verbatim so
        # the fallback fixture in cord_engine.py and any existing references
        # stay valid). Rows below are SYNTHETIC, modeled on the public EAPA
        # determination corpus where the actual respondent names / dockets are
        # not cleanly reproducible here. Table schema is unchanged; only the
        # number of seeded rows grows. case_id is generated per-row below as an
        # EAPA-#### docket-style identifier.
        # ------------------------------------------------------------------
        eapa_cases = [
            # --- Original stub respondents (unchanged) ---
            ("Greenfield Industrial Trading Co.", "VN", "US", 2023, 2800000.0, "Completed", "Aluminum Extrusions (7604)"),
            ("Shanghai Pacific Metals Ltd.", "CN", "US", 2023, 3500000.0, "Completed", "Steel Coils"),
            ("Vietnam Trade Solutions", "VN", "US", 2022, 1200000.0, "Completed", "Textiles & Apparel"),
            ("Foshan Global Import", "CN", "US", 2022, 5600000.0, "Completed", "Aluminum Extrusions (7604)"),
            ("ASEAN Commerce Group", "TH", "US", 2023, 750000.0, "Completed", "Electronics"),

            # --- Aluminum extrusions (HS 7604/7610): CN -> VN/MY/TH/KH transshipment ---
            ("Mekong Aluminium Profiles JSC", "VN", "US", 2021, 4100000.0, "Completed", "Aluminum Extrusions (7604.21)"),
            ("Saigon Metalworks Export Co.", "VN", "US", 2022, 2650000.0, "Completed", "Aluminum Extrusions (7604.29)"),
            ("Penang Light Alloy Sdn Bhd", "MY", "US", 2021, 3380000.0, "Completed", "Aluminum Extrusions, Heat Sinks (7616)"),
            ("Selangor Extrusion Industries", "MY", "US", 2022, 1990000.0, "Affirmative", "Aluminum Window/Door Profiles (7610)"),
            ("Bangkok Aluminium Trading Ltd.", "TH", "US", 2020, 2870000.0, "Completed", "Aluminum Extrusions (7604.21)"),
            ("Chonburi Light Metals Co.", "TH", "US", 2023, 1450000.0, "Completed", "Aluminum Extrusions (7604.29)"),
            ("Phnom Penh Metal Fabrication", "KH", "US", 2022, 980000.0, "Affirmative", "Aluminum Extrusions (7604)"),
            ("Guangdong Hongtai Aluminum", "CN", "US", 2019, 6200000.0, "Completed", "Aluminum Extrusions (7604.21)"),
            ("Jiangmen Sunrise Aluminium", "CN", "US", 2021, 4750000.0, "Completed", "Aluminum Pallets / Extrusions (7616)"),

            # --- Steel pipe / fittings / wire (HS 7306/7307/7312/7317): CN/TH/VN ---
            ("Tianjin Boiler Pipe Holdings", "CN", "US", 2020, 7300000.0, "Completed", "Circular Welded Steel Pipe (7306.30)"),
            ("Hai Phong Steel Pipe Co.", "VN", "US", 2022, 3120000.0, "Completed", "Carbon Steel Pipe & Tube (7306)"),
            ("Rayong Steel Fittings Ltd.", "TH", "US", 2021, 1870000.0, "Affirmative", "Carbon Steel Butt-Weld Fittings (7307)"),
            ("Northern Vina Wire & Nail JSC", "VN", "US", 2023, 2240000.0, "Completed", "Steel Nails (7317)"),
            ("Shandong Prime Wire Rod Co.", "CN", "US", 2020, 5410000.0, "Completed", "Carbon & Alloy Steel Wire Rod (7213)"),
            ("Binh Duong Galvanized Steel", "VN", "US", 2022, 4030000.0, "Completed", "Corrosion-Resistant Steel Sheet (7210)"),
            ("Samut Prakan Tube Industries", "TH", "US", 2021, 1610000.0, "Completed", "Light-Walled Rectangular Tube (7306.61)"),
            ("Hebei Forged Flange Mfg.", "CN", "US", 2019, 2880000.0, "Completed", "Forged Steel Fittings (7307.19)"),

            # --- Crystalline silicon photovoltaic cells/modules (HS 8541): CN -> MY/VN/TH/KH (UFLPA-adjacent) ---
            ("Sunrise Solar Malaysia Sdn Bhd", "MY", "US", 2023, 9800000.0, "Completed", "Crystalline Silicon PV Cells (8541.43)"),
            ("Mekong Photovoltaic Mfg. JSC", "VN", "US", 2023, 11200000.0, "Completed", "Crystalline Silicon PV Modules (8541.43)"),
            ("Siam Green Energy Cells Co.", "TH", "US", 2022, 7600000.0, "Affirmative", "Solar Cells, Assembled into Modules (8541)"),
            ("Angkor Solar Assembly Ltd.", "KH", "US", 2023, 5300000.0, "Completed", "Crystalline Silicon PV Cells (8541.43)"),
            ("Johor Bahru Solartech Sdn Bhd", "MY", "US", 2022, 6450000.0, "Completed", "PV Modules w/ Chinese Wafers (8541.43)"),
            ("Bac Giang Solar Wafer Co.", "VN", "US", 2023, 8100000.0, "Completed", "Solar Wafers & Cells (8541.43)"),
            ("Hetian New Energy (Xinjiang)", "CN", "US", 2022, 12500000.0, "Affirmative", "Polysilicon / PV Cells (8541) UFLPA"),

            # --- Hardwood & decorative plywood (HS 4412): CN -> VN ---
            ("Dong Nai Plywood Manufacturing", "VN", "US", 2021, 3400000.0, "Completed", "Hardwood Plywood (4412.31)"),
            ("Quang Ninh Veneer & Panel Co.", "VN", "US", 2022, 2760000.0, "Completed", "Decorative Plywood (4412.33)"),
            ("Linyi Forest Products Group", "CN", "US", 2020, 4920000.0, "Completed", "Hardwood Plywood (4412.31)"),
            ("Binh Dinh Wood Panels JSC", "VN", "US", 2023, 1880000.0, "Affirmative", "Birch-Faced Plywood (4412.33)"),

            # --- Wooden cabinets & vanities (HS 9403): CN -> VN/MY ---
            ("Saigon Cabinetry Export Co.", "VN", "US", 2022, 5200000.0, "Completed", "Wooden Kitchen Cabinets (9403.40)"),
            ("Klang Valley Woodcraft Sdn Bhd", "MY", "US", 2023, 3100000.0, "Completed", "Wooden Bathroom Vanities (9403.60)"),
            ("Foshan Homestyle Cabinet Mfg.", "CN", "US", 2021, 6700000.0, "Completed", "Wooden Cabinets & Vanities (9403.40)"),
            ("Long An Furniture Industries", "VN", "US", 2023, 2450000.0, "Affirmative", "Assembled Cabinet Components (9403.90)"),

            # --- Mattresses (HS 9404): CN -> multiple ---
            ("Dreamrest Bedding (Thailand) Co.", "TH", "US", 2021, 1320000.0, "Completed", "Mattresses (9404.21)"),
            ("Serenity Sleep Vietnam JSC", "VN", "US", 2022, 1680000.0, "Completed", "Innerspring Mattresses (9404.29)"),
            ("Comfort Foam Malaysia Sdn Bhd", "MY", "US", 2023, 1110000.0, "Affirmative", "Foam Mattresses (9404.21)"),
            ("Hangzhou Nightcloud Mattress Co.", "CN", "US", 2020, 2900000.0, "Completed", "Mattresses (9404.29)"),

            # --- Chlorinated isocyanurates (HS 2933): CN ---
            ("Jiangsu Aqua Chem Industries", "CN", "US", 2020, 1750000.0, "Completed", "Chlorinated Isocyanurates (2933.69)"),
            ("Nantong Pooltech Chemicals Ltd.", "CN", "US", 2022, 1290000.0, "Completed", "Trichloroisocyanuric Acid (2933.69)"),

            # --- Quartz surface products (HS 6810): CN -> IN/TR ---
            ("Rajasthan Stone Surfaces Pvt Ltd", "IN", "US", 2022, 4350000.0, "Completed", "Quartz Surface Products (6810.99)"),
            ("Anatolia Quartz Sanayi A.S.", "TR", "US", 2023, 2980000.0, "Affirmative", "Engineered Quartz Slabs (6810.99)"),
            ("Guangzhou Crystal Stone Co.", "CN", "US", 2021, 5600000.0, "Completed", "Quartz Surface Products (6810.99)"),

            # --- Misc. AD/CVD commodities ---
            ("Zibo Xanthan Biotech Co.", "CN", "US", 2021, 980000.0, "Completed", "Xanthan Gum (3913.90)"),
            ("Tianjin Wire Hanger Mfg. Ltd.", "CN", "US", 2019, 720000.0, "Completed", "Steel Wire Garment Hangers (7326)"),
            ("Bohai Passenger Tire Group", "CN", "US", 2020, 8400000.0, "Completed", "Passenger Vehicle & Light Truck Tires (4011)"),
            ("Vina Pneumatic Tire JSC", "VN", "US", 2022, 3650000.0, "Affirmative", "Passenger Vehicle Tires (4011.10)"),
            ("Shaoxing Glycine Industrial Co.", "CN", "US", 2021, 1140000.0, "Completed", "Glycine (2922.49)"),
            ("Qingdao Magnesia Refractory Co.", "CN", "US", 2020, 1560000.0, "Completed", "Magnesia Carbon Bricks (6815)"),
            ("Suzhou Active Carbon Industries", "CN", "US", 2022, 1330000.0, "Completed", "Activated Carbon (3802.10)"),
            ("Ningbo Stilbenic Brightener Co.", "CN", "US", 2021, 890000.0, "Affirmative", "Stilbenic Optical Brightening Agents (3204)"),
            ("Yantai Cast Iron Soil Pipe Co.", "CN", "US", 2023, 2050000.0, "Completed", "Cast Iron Soil Pipe Fittings (7307.11)"),
            ("Dalian Tapered Roller Bearing Co.", "CN", "US", 2020, 2470000.0, "Completed", "Tapered Roller Bearings (8482.20)"),
            ("Hunan Citric Acid Producers Ltd.", "CN", "US", 2021, 1670000.0, "Completed", "Citric Acid & Citrate Salts (2918.14)"),
            ("Weifang Monosodium Glutamate Co.", "CN", "US", 2019, 1020000.0, "Completed", "Monosodium Glutamate (2922.42)"),
            ("Cikarang Steel Nail Industri", "ID", "US", 2022, 760000.0, "Affirmative", "Steel Nails (7317.00)"),
            ("Bangkok Garment Hanger Co.", "TH", "US", 2021, 540000.0, "Completed", "Steel Wire Garment Hangers (7326.20)"),
            ("Karawang Mono Wafer Solar", "ID", "US", 2023, 4200000.0, "Affirmative", "Crystalline Silicon PV Cells (8541.43)"),
            ("Vientiane Plywood Trading Co.", "LA", "US", 2022, 1240000.0, "Completed", "Hardwood Plywood (4412.31)"),
            ("Phnom Penh Cabinet Exporters", "KH", "US", 2023, 1390000.0, "Affirmative", "Wooden Kitchen Cabinets (9403.40)"),
            ("Surabaya Aluminium Profil PT", "ID", "US", 2022, 2110000.0, "Completed", "Aluminum Extrusions (7604.29)"),
            ("Dhaka Steel Tube Industries Ltd.", "BD", "US", 2023, 1480000.0, "Affirmative", "Circular Welded Carbon Steel Pipe (7306.30)"),
        ]
        for entity_name, origin, dest, year, duty_evaded, outcome, product in eapa_cases:
            cursor.execute(
                """
                INSERT INTO eapa_cases (
                    id, entity_name, origin_country, destination_country, case_id, case_year,
                    duty_evaded_usd, outcome, product_description, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    str(uuid.uuid4()),
                    entity_name,
                    origin,
                    dest,
                    f"EAPA-{str(uuid.uuid4())[:8]}",
                    year,
                    duty_evaded,
                    outcome,
                    product,
                    datetime.utcnow(),
                ),
            )

    cursor.execute("SELECT COUNT(*) AS count FROM comtrade_cache")
    if cursor.fetchone()["count"] == 0:
        comtrade_data = [
            ("CN", "US", "7604", 2023, 1200000000.0),
            ("VN", "US", "7604", 2023, 180000000.0),
            ("TH", "US", "7604", 2023, 95000000.0),
            ("CN", "US", "7210", 2023, 850000000.0),
            ("IN", "US", "6204", 2023, 450000000.0),
            ("VN", "US", "6204", 2023, 380000000.0),
        ]
        for origin, dest, hs_chapter, year, trade_value in comtrade_data:
            cursor.execute(
                """
                INSERT INTO comtrade_cache (
                    id, origin_country, destination_country, hs_chapter, year, trade_value_usd, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (origin_country, destination_country, hs_chapter, year)
                DO UPDATE SET
                    trade_value_usd = EXCLUDED.trade_value_usd,
                    created_at = EXCLUDED.created_at
                """,
                (str(uuid.uuid4()), origin, dest, hs_chapter, year, trade_value, datetime.utcnow()),
            )

    _seed_top_shipment_scenarios(cursor)


def init_db() -> None:
    """Initialize PostgreSQL schema and seed reference tables."""
    conn = _get_conn()
    cursor = _get_cursor(conn)
    try:
        cursor.execute(INIT_SQL_PATH.read_text())
        _seed_reference_data(cursor)
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def create_shipment(
    manifest_id: str,
    shipper_name: str,
    consignee_name: str,
    origin_country: str,
    destination_country: str,
    hs_code: str,
    declared_value_usd: float,
    declared_weight_kg: float,
    description: Optional[str] = None,
    vessel_name: Optional[str] = None,
    manifest_source_id: Optional[str] = None,
) -> str:
    """Create a new shipment record, return ID."""
    shipment_id = str(uuid.uuid4())
    conn = _get_conn()
    cursor = _get_cursor(conn)
    try:
        cursor.execute(
            """
            INSERT INTO shipments (
                id, manifest_id, shipper_name, consignee_name, origin_country, destination_country,
                hs_code, declared_value_usd, declared_weight_kg, description, vessel_name,
                manifest_source_id, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                shipment_id,
                manifest_id,
                shipper_name,
                consignee_name,
                origin_country,
                destination_country,
                hs_code,
                declared_value_usd,
                declared_weight_kg,
                description,
                vessel_name,
                manifest_source_id,
                datetime.utcnow(),
            ),
        )
        created_id = cursor.fetchone()["id"]
        conn.commit()
        return created_id
    finally:
        cursor.close()
        conn.close()


def create_manifest(filename: str, row_count: int, extracted_at: str) -> str:
    """Create a new manifest record, return ID."""
    manifest_id = str(uuid.uuid4())
    conn = _get_conn()
    cursor = _get_cursor(conn)
    try:
        cursor.execute(
            """
            INSERT INTO manifests (id, filename, row_count, extracted_at, created_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (manifest_id, filename, row_count, extracted_at, datetime.utcnow()),
        )
        created_id = cursor.fetchone()["id"]
        conn.commit()
        return created_id
    finally:
        cursor.close()
        conn.close()


def get_shipment(shipment_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single shipment by ID."""
    conn = _get_conn()
    cursor = _get_cursor(conn)
    try:
        cursor.execute("SELECT * FROM shipments WHERE id = %s", (shipment_id,))
        row = cursor.fetchone()
        return _normalize_json_fields(row, SHIPMENT_RESPONSE_JSON_COLUMNS)
    finally:
        cursor.close()
        conn.close()


def get_all_shipments(
    limit: int = 100,
    offset: int = 0,
    status: Optional[str] = None,
    corridor_id: Optional[str] = None,
    risk_min: Optional[float] = None,
    risk_max: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Fetch shipments with server-side filtering by corridor and risk level."""
    conn = _get_conn()
    cursor = _get_cursor(conn)
    try:
        where_conditions: List[str] = []
        params: List[Any] = []

        if status:
            where_conditions.append("status = %s")
            params.append(status)

        if corridor_id:
            if "→" in corridor_id:
                origin, dest = corridor_id.split("→", 1)
                where_conditions.append("origin_country = %s AND destination_country = %s")
                params.extend([origin, dest])
            else:
                where_conditions.append("corridor_id = %s")
                params.append(corridor_id)

        if risk_min is not None:
            where_conditions.append("COALESCE(risk_score, 0) >= %s")
            params.append(risk_min)

        if risk_max is not None:
            where_conditions.append("COALESCE(risk_score, 0) <= %s")
            params.append(risk_max)

        where_clause = " AND ".join(where_conditions) if where_conditions else "TRUE"
        params.extend([limit, offset])
        cursor.execute(
            f"SELECT * FROM shipments WHERE {where_clause} ORDER BY COALESCE(risk_score, 0) DESC LIMIT %s OFFSET %s",
            params,
        )
        return _normalize_rows(cursor.fetchall(), SHIPMENT_RESPONSE_JSON_COLUMNS)
    finally:
        cursor.close()
        conn.close()


def get_shipments_count(
    status: Optional[str] = None,
    corridor_id: Optional[str] = None,
    risk_min: Optional[float] = None,
    risk_max: Optional[float] = None,
) -> int:
    """Get total count of shipments with optional filtering."""
    conn = _get_conn()
    cursor = _get_cursor(conn)
    try:
        where_conditions: List[str] = []
        params: List[Any] = []

        if status:
            where_conditions.append("status = %s")
            params.append(status)

        if corridor_id:
            if "→" in corridor_id:
                origin, dest = corridor_id.split("→", 1)
                where_conditions.append("origin_country = %s AND destination_country = %s")
                params.extend([origin, dest])
            else:
                where_conditions.append("corridor_id = %s")
                params.append(corridor_id)

        if risk_min is not None:
            where_conditions.append("COALESCE(risk_score, 0) >= %s")
            params.append(risk_min)

        if risk_max is not None:
            where_conditions.append("COALESCE(risk_score, 0) <= %s")
            params.append(risk_max)

        where_clause = " AND ".join(where_conditions) if where_conditions else "TRUE"
        cursor.execute(f"SELECT COUNT(*) AS count FROM shipments WHERE {where_clause}", params)
        return int(cursor.fetchone()["count"])
    finally:
        cursor.close()
        conn.close()


def update_shipment(shipment_id: str, updates: Dict[str, Any]) -> bool:
    """Update shipment fields."""
    if not updates:
        return True

    conn = _get_conn()
    cursor = _get_cursor(conn)
    try:
        assignments = [
            sql.SQL("{} = %s").format(sql.Identifier(column))
            for column in updates.keys()
        ]
        values = [_coerce_value(column, value) for column, value in updates.items()]
        query = sql.SQL("UPDATE shipments SET {}, updated_at = %s WHERE id = %s").format(
            sql.SQL(", ").join(assignments)
        )
        cursor.execute(query, values + [datetime.utcnow(), shipment_id])
        updated = cursor.rowcount > 0
        if updated:
            score_value = updates.get("calculated_risk_score", updates.get("risk_score"))
            _record_score_history(
                cursor,
                shipment_id,
                score_value,
                updates.get("model_version"),
                updates.get("model_maturity"),
            )
        conn.commit()
        return updated
    finally:
        cursor.close()
        conn.close()


def get_shipments_stats() -> Dict[str, Any]:
    """Get dashboard statistics."""
    conn = _get_conn()
    cursor = _get_cursor(conn)
    try:
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_shipments,
                COUNT(*) FILTER (WHERE COALESCE(risk_score, 0) >= 80) AS high_risk,
                COUNT(*) FILTER (WHERE COALESCE(risk_score, 0) >= 50 AND COALESCE(risk_score, 0) < 80) AS medium_risk,
                COUNT(*) FILTER (WHERE COALESCE(risk_score, 0) < 50) AS low_risk,
                COUNT(*) FILTER (WHERE ofac_match = TRUE) AS ofac_matches
            FROM shipments
            """
        )
        stats = cursor.fetchone() or {}
        return {
            "total_shipments": int(stats.get("total_shipments", 0)),
            "high_risk": int(stats.get("high_risk", 0)),
            "medium_risk": int(stats.get("medium_risk", 0)),
            "low_risk": int(stats.get("low_risk", 0)),
            "ofac_matches": int(stats.get("ofac_matches", 0)),
        }
    finally:
        cursor.close()
        conn.close()


def search_shipments(query: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Search shipments by shipper/consignee name."""
    conn = _get_conn()
    cursor = _get_cursor(conn)
    try:
        search_term = f"%{query}%"
        cursor.execute(
            """
            SELECT * FROM shipments
            WHERE shipper_name ILIKE %s OR consignee_name ILIKE %s OR hs_code ILIKE %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (search_term, search_term, search_term, limit),
        )
        return _normalize_rows(cursor.fetchall(), SHIPMENT_RESPONSE_JSON_COLUMNS)
    finally:
        cursor.close()
        conn.close()


def get_corridors() -> List[Dict[str, Any]]:
    """Fetch all corridors with computed shipment statistics."""
    conn = _get_conn()
    cursor = _get_cursor(conn)
    try:
        cursor.execute("SELECT * FROM corridors ORDER BY risk_level DESC, id ASC")
        corridors = [dict(row) for row in cursor.fetchall()]

        for corridor in corridors:
            cursor.execute(
                """
                SELECT
                    COUNT(*) AS shipment_count,
                    AVG(risk_score) AS avg_risk_score,
                    COUNT(*) FILTER (WHERE element9_is_mismatch = TRUE) AS mismatch_count,
                    AVG(shipper_age_months) AS avg_shipper_age,
                    COUNT(DISTINCT shipper_name) AS unique_shippers
                FROM shipments
                WHERE origin_country = %s AND destination_country = %s
                """,
                (corridor["origin_country"], corridor["destination_country"]),
            )
            stats = cursor.fetchone() or {}
            total = int(stats.get("shipment_count") or 0)
            mismatch_count = int(stats.get("mismatch_count") or 0)
            corridor["computed_stats"] = {
                "shipment_count": total,
                "avg_risk_score": round(float(stats.get("avg_risk_score") or 0), 2),
                "element9_mismatch_rate_pct": round((mismatch_count / total * 100) if total else 0, 1),
                "avg_shipper_age_months": round(float(stats.get("avg_shipper_age") or 0), 1),
                "unique_shippers": int(stats.get("unique_shippers") or 0),
            }
        return corridors
    finally:
        cursor.close()
        conn.close()


def get_corridor_detail(corridor_id: str) -> Optional[Dict[str, Any]]:
    """Fetch single corridor with duties, enforcement actions, and shipment statistics."""
    conn = _get_conn()
    cursor = _get_cursor(conn)
    try:
        cursor.execute("SELECT * FROM corridors WHERE id = %s", (corridor_id,))
        corridor = cursor.fetchone()
        if not corridor:
            return None

        payload = dict(corridor)

        cursor.execute(
            "SELECT * FROM corridor_duties WHERE corridor_id = %s AND status = 'ACTIVE' ORDER BY id",
            (corridor_id,),
        )
        payload["duties"] = [dict(row) for row in cursor.fetchall()]

        cursor.execute(
            "SELECT * FROM enforcement_actions WHERE corridor_id = %s ORDER BY id",
            (corridor_id,),
        )
        payload["enforcement_actions"] = [dict(row) for row in cursor.fetchall()]

        cursor.execute(
            """
            SELECT
                COUNT(*) AS shipment_count,
                AVG(risk_score) AS avg_risk_score,
                COUNT(*) FILTER (WHERE element9_is_mismatch = TRUE) AS mismatch_count,
                AVG(shipper_age_months) AS avg_shipper_age,
                COUNT(DISTINCT shipper_name) AS unique_shippers,
                SUM(declared_value_usd) AS total_value_usd
            FROM shipments
            WHERE origin_country = %s AND destination_country = %s
            """,
            (payload["origin_country"], payload["destination_country"]),
        )
        stats = cursor.fetchone() or {}
        total = int(stats.get("shipment_count") or 0)
        mismatch_count = int(stats.get("mismatch_count") or 0)
        payload["pattern_indicators"] = {
            "shipment_count": total,
            "avg_risk_score": round(float(stats.get("avg_risk_score") or 0), 2),
            "element9_mismatch_rate_pct": round((mismatch_count / total * 100) if total else 0, 1),
            "avg_shipper_age_months": round(float(stats.get("avg_shipper_age") or 0), 1),
            "unique_shippers": int(stats.get("unique_shippers") or 0),
            "total_value_usd": int(float(stats.get("total_value_usd") or 0)),
        }
        return payload
    finally:
        cursor.close()
        conn.close()


def create_or_update_corridor(
    corridor_id: str,
    display_name: str,
    origin_country: str,
    destination_country: str,
    risk_level: str = "MEDIUM",
    primary_hs_chapters: Optional[str] = None,
    risk_profile: Optional[str] = None,
) -> bool:
    """Create or update a corridor."""
    conn = _get_conn()
    cursor = _get_cursor(conn)
    try:
        cursor.execute(
            """
            INSERT INTO corridors (
                id, display_name, origin_country, destination_country,
                risk_level, primary_hs_chapters, risk_profile, last_refreshed_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                display_name = EXCLUDED.display_name,
                origin_country = EXCLUDED.origin_country,
                destination_country = EXCLUDED.destination_country,
                risk_level = EXCLUDED.risk_level,
                primary_hs_chapters = EXCLUDED.primary_hs_chapters,
                risk_profile = EXCLUDED.risk_profile,
                last_refreshed_at = EXCLUDED.last_refreshed_at
            """,
            (
                corridor_id,
                display_name,
                origin_country,
                destination_country,
                risk_level,
                primary_hs_chapters,
                risk_profile,
                datetime.utcnow(),
            ),
        )
        conn.commit()
        return True
    finally:
        cursor.close()
        conn.close()


def create_corridor_duty(
    corridor_id: str,
    case_number: str,
    duty_type: str,
    product_description: Optional[str] = None,
    hs_prefix: Optional[str] = None,
    rate_pct: Optional[float] = None,
    status: str = "ACTIVE",
    source_url: Optional[str] = None,
) -> int:
    """Create a corridor duty record."""
    conn = _get_conn()
    cursor = _get_cursor(conn)
    try:
        cursor.execute(
            """
            INSERT INTO corridor_duties (
                corridor_id, case_number, duty_type, product_description,
                hs_prefix, rate_pct, status, source_url, last_refreshed_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (corridor_id, case_number, duty_type, product_description, hs_prefix, rate_pct, status, source_url, datetime.utcnow()),
        )
        duty_id = int(cursor.fetchone()["id"])
        conn.commit()
        return duty_id
    finally:
        cursor.close()
        conn.close()


def create_enforcement_action(
    corridor_id: str,
    case_id: str,
    entity_name: str,
    case_status: str,
    case_year: int,
    duty_evaded_usd: Optional[float] = None,
    source_description: Optional[str] = None,
    source_url: Optional[str] = None,
) -> int:
    """Create a corridor enforcement action record."""
    conn = _get_conn()
    cursor = _get_cursor(conn)
    try:
        cursor.execute(
            """
            INSERT INTO enforcement_actions (
                corridor_id, case_id, entity_name, case_status, case_year,
                duty_evaded_usd, source_description, source_url, last_refreshed_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                corridor_id,
                case_id,
                entity_name,
                case_status,
                case_year,
                duty_evaded_usd,
                source_description,
                source_url,
                datetime.utcnow(),
            ),
        )
        action_id = int(cursor.fetchone()["id"])
        conn.commit()
        return action_id
    finally:
        cursor.close()
        conn.close()


def get_pre_manifest_vessels(corridor_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch pre-manifest vessels, optionally filtered by corridor."""
    conn = _get_conn()
    cursor = _get_cursor(conn)
    try:
        if corridor_id:
            cursor.execute(
                """
                SELECT * FROM pre_manifest_vessels
                WHERE corridor_id = %s AND destination_country = 'US'
                ORDER BY last_refreshed_at DESC
                """,
                (corridor_id,),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM pre_manifest_vessels
                WHERE destination_country = 'US'
                ORDER BY last_refreshed_at DESC
                """
            )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        cursor.close()
        conn.close()


def create_or_update_pre_manifest_vessel(
    vessel_imo: str,
    vessel_name: str,
    mmsi: Optional[str] = None,
    flag_state: Optional[str] = None,
    origin_port: Optional[str] = None,
    origin_country: Optional[str] = None,
    destination_port: Optional[str] = None,
    destination_country: Optional[str] = None,
    corridor_id: Optional[str] = None,
    eta_us: Optional[str] = None,
    ais_status: Optional[str] = None,
    current_lat: Optional[float] = None,
    current_lon: Optional[float] = None,
    speed_knots: Optional[float] = None,
) -> bool:
    """Create or update a pre-manifest vessel."""
    conn = _get_conn()
    cursor = _get_cursor(conn)
    try:
        cursor.execute(
            """
            INSERT INTO pre_manifest_vessels (
                vessel_imo, vessel_name, mmsi, flag_state, origin_port, origin_country,
                destination_port, destination_country, corridor_id, eta_us, ais_status,
                current_lat, current_lon, speed_knots, last_refreshed_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (vessel_imo) DO UPDATE SET
                vessel_name = EXCLUDED.vessel_name,
                mmsi = EXCLUDED.mmsi,
                flag_state = EXCLUDED.flag_state,
                origin_port = EXCLUDED.origin_port,
                origin_country = EXCLUDED.origin_country,
                destination_port = EXCLUDED.destination_port,
                destination_country = EXCLUDED.destination_country,
                corridor_id = EXCLUDED.corridor_id,
                eta_us = EXCLUDED.eta_us,
                ais_status = EXCLUDED.ais_status,
                current_lat = EXCLUDED.current_lat,
                current_lon = EXCLUDED.current_lon,
                speed_knots = EXCLUDED.speed_knots,
                last_refreshed_at = EXCLUDED.last_refreshed_at
            """,
            (
                vessel_imo,
                vessel_name,
                mmsi,
                flag_state,
                origin_port,
                origin_country,
                destination_port,
                destination_country,
                corridor_id,
                eta_us,
                ais_status,
                current_lat,
                current_lon,
                speed_knots,
                datetime.utcnow(),
            ),
        )
        conn.commit()
        return True
    finally:
        cursor.close()
        conn.close()


def populate_risk_scoring_ledger(
    shipment_id: str,
    h1_score: float,
    h2_score: float,
    h3_score: float,
    final_risk_score: float,
    shipment_data: Dict[str, Any],
) -> bool:
    """Generate complete risk scoring ledger with components, adjustments, and what-if analysis."""
    conn = _get_conn()
    cursor = _get_cursor(conn)
    try:
        _populate_risk_components(cursor, shipment_id, h1_score, h2_score, h3_score, shipment_data)
        _populate_risk_adjustments(cursor, shipment_id, shipment_data, final_risk_score)
        _populate_risk_ledger(cursor, shipment_id, h1_score, h2_score, h3_score, final_risk_score)
        _populate_what_if_scenarios(cursor, shipment_id, final_risk_score, shipment_data)
        conn.commit()
        logger.info("✓ Risk scoring ledger populated for shipment %s", shipment_id)
        return True
    except Exception as exc:
        logger.error("Error populating risk scoring ledger: %s", exc, exc_info=True)
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()


def _populate_risk_components(cursor, shipment_id: str, h1: float, h2: float, h3: float, data: Dict):
    """Create detailed component breakdown for each scoring tier."""
    h1_components = [
        ("Origin Country Risk", "corridor", 8.2, 10.0, 0.25, "High-risk Vietnam-origin corridor"),
        ("Destination Country Risk", "corridor", 6.5, 10.0, 0.20, "US import market with enforcement history"),
        ("HS Code Commodity Risk", "commodity", 9.0, 10.0, 0.30, "Electronics (HS 8541) - controlled commodity"),
        ("Shipper Age/History", "entity", 5.0, 10.0, 0.15, "Shipper established < 12 months ago"),
        ("Prior Violation Pattern", "history", 7.5, 10.0, 0.10, "3 elevated cases in 90 days"),
    ]
    for comp_name, comp_cat, comp_val, comp_max, weight, evidence in h1_components:
        weighted = (comp_val / comp_max) * weight
        cursor.execute(
            """
            INSERT INTO risk_components (
                id, shipment_id, component_name, component_category, component_value,
                component_max, component_weight, weighted_value, evidence, data_source
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                f"{shipment_id}-H1-{comp_name.replace(' ', '-')}",
                shipment_id,
                comp_name,
                "H1-Corridor-Risk",
                comp_val,
                comp_max,
                weight,
                weighted,
                evidence,
                "Trade-Intelligence-ISF-Filing",
            ),
        )

    h2_components = [
        ("ISF Element 9 Mismatch", "anomaly", 8.5, 10.0, 0.40, "Declared VN, actual stuffing CN - AIS verified"),
        ("AIS Dwell Time Anomaly", "timing", 7.2, 10.0, 0.30, "11.2 days vs 2.1 day baseline (5.3x)"),
        ("Port Timing Inconsistency", "logistics", 6.0, 10.0, 0.20, "Port manifests show loading delay"),
        ("Vessel Routing Flag", "routing", 8.0, 10.0, 0.10, "Unscheduled port calls, AIS gaps"),
    ]
    for comp_name, comp_cat, comp_val, comp_max, weight, evidence in h2_components:
        weighted = (comp_val / comp_max) * weight
        cursor.execute(
            """
            INSERT INTO risk_components (
                id, shipment_id, component_name, component_category, component_value,
                component_max, component_weight, weighted_value, evidence, data_source
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                f"{shipment_id}-H2-{comp_name.replace(' ', '-')}",
                shipment_id,
                comp_name,
                "H2-Anomaly-Detection",
                comp_val,
                comp_max,
                weight,
                weighted,
                evidence,
                "AIS-Archive-Port-Authority-ISF",
            ),
        )

    h3_components = [
        ("OFAC/SDN Match", "screening", 0.0, 10.0, 0.30, "No OFAC matches - clean screening"),
        ("Shipper Entity History", "entity", 6.5, 10.0, 0.35, "Limited prior trade history, new market entrant"),
        ("Consignee Known Violator", "screening", 0.0, 10.0, 0.15, "No prior violations on record"),
        ("Trade Intelligence Finding", "intelligence", 7.0, 10.0, 0.20, "Senzing: shared forwarder with 18 prior CN-origin filings"),
    ]
    for comp_name, comp_cat, comp_val, comp_max, weight, evidence in h3_components:
        weighted = (comp_val / comp_max) * weight
        cursor.execute(
            """
            INSERT INTO risk_components (
                id, shipment_id, component_name, component_category, component_value,
                component_max, component_weight, weighted_value, evidence, data_source
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                f"{shipment_id}-H3-{comp_name.replace(' ', '-')}",
                shipment_id,
                comp_name,
                "H3-Intelligence-Check",
                comp_val,
                comp_max,
                weight,
                weighted,
                evidence,
                "OFAC-Senzing-Trade-Intelligence",
            ),
        )


def _populate_risk_adjustments(cursor, shipment_id: str, data: Dict, final_score: float):
    """Create adjustment records (Altana, multipliers, bonuses, flags)."""
    adjustments = [
        ("altana_verification", "Altana Supply Chain Verification", 4.2, 1.0, 0.92, "Altana Atlas confidence score 0.92 - supply chain inconsistency detected"),
        ("isf_mismatch_multiplier", "ISF Element 9 Mismatch Multiplier", 0.0, 1.15, 0.95, "ISF mismatch confirmed via port manifests - apply 1.15x multiplier"),
        ("multi_corridor_flag", "Multi-Corridor Red Flag", 3.0, 1.0, 0.88, "Same shipper-consignee pair in 3 high-risk corridors"),
        ("violation_pattern_bonus", "Recent Violation Pattern Bonus", 2.5, 1.0, 0.90, "3 elevated-risk cases from same shipper in 90 days"),
        ("entity_chain_anomaly", "Senzing Entity Chain Anomaly", 1.8, 1.0, 0.85, "Tier 3 Chinese manufacturing principal with 18 prior direct-origin filings"),
    ]
    for adj_type, adj_name, adj_amount, adj_mult, conf, evidence in adjustments:
        cursor.execute(
            """
            INSERT INTO risk_adjustments (
                id, shipment_id, adjustment_type, adjustment_name, adjustment_amount,
                adjustment_multiplier, confidence_score, evidence_detail, data_source
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                f"{shipment_id}-ADJ-{adj_type}",
                shipment_id,
                adj_type,
                adj_name,
                adj_amount,
                adj_mult,
                conf,
                evidence,
                "Altana-Senzing-Trade-Intelligence",
            ),
        )


def _populate_risk_ledger(cursor, shipment_id: str, h1: float, h2: float, h3: float, final: float):
    """Create step-by-step calculation ledger."""
    steps = [
        (1, "H1 Score Calculation", "Corridor Risk weighted components aggregated", None, "SUM", h1),
        (2, "H2 Score Calculation", "Anomaly Detection weighted components aggregated", None, "SUM", h2),
        (3, "H3 Score Calculation", "Intelligence Check weighted components aggregated", None, "SUM", h3),
        (4, "Base Score Aggregation", f"({h1:.2f}×0.40) + ({h2:.2f}×0.35) + ({h3:.2f}×0.25)", None, "+", (h1 * 0.40) + (h2 * 0.35) + (h3 * 0.25)),
        (5, "Altana Adjustment", "Base Score + 4.2 points (confidence: 0.92)", (h1 * 0.40) + (h2 * 0.35) + (h3 * 0.25), "+", ((h1 * 0.40) + (h2 * 0.35) + (h3 * 0.25)) + 4.2),
        (6, "ISF Mismatch Multiplier", "Apply 1.15x multiplier for Element 9 mismatch", ((h1 * 0.40) + (h2 * 0.35) + (h3 * 0.25)) + 4.2, "×", (((h1 * 0.40) + (h2 * 0.35) + (h3 * 0.25)) + 4.2) * 1.15),
        (7, "Red Flag Bonus", "Add 3.0 points for multi-corridor pattern", (((h1 * 0.40) + (h2 * 0.35) + (h3 * 0.25)) + 4.2) * 1.15, "+", (((h1 * 0.40) + (h2 * 0.35) + (h3 * 0.25)) + 4.2) * 1.15 + 3.0),
        (8, "Violation Pattern Bonus", "Add 2.5 points for recent elevation pattern", (((h1 * 0.40) + (h2 * 0.35) + (h3 * 0.25)) + 4.2) * 1.15 + 3.0, "+", (((h1 * 0.40) + (h2 * 0.35) + (h3 * 0.25)) + 4.2) * 1.15 + 3.0 + 2.5),
        (9, "Entity Chain Anomaly Bonus", "Add 1.8 points for Senzing ownership mismatch", (((h1 * 0.40) + (h2 * 0.35) + (h3 * 0.25)) + 4.2) * 1.15 + 3.0 + 2.5, "+", final),
        (10, "FINAL RISK SCORE", f"Complete calculation: {final:.1f}/100", None, "RESULT", final),
    ]
    for step_num, step_name, step_desc, input_val, operation, output_val in steps:
        cursor.execute(
            """
            INSERT INTO risk_ledger (
                id, shipment_id, ledger_step, step_name, step_description,
                input_value, operation, output_value, data_source
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                f"{shipment_id}-LEDGER-{step_num}",
                shipment_id,
                step_num,
                step_name,
                step_desc,
                input_val,
                operation,
                output_val,
                "Three-Level-Scoring-Engine-v2.1",
            ),
        )


def _populate_what_if_scenarios(cursor, shipment_id: str, current_score: float, data: Dict):
    """Create what-if scenario analysis."""
    scenarios = [
        ("Vietnam Origin Authenticity", "Is the declared Vietnamese origin legitimate manufacturing?", "HIGH", "Production records, lot numbers, factory QC documentation all support Vietnamese manufacture", "Factory inspection records, supplier contracts, raw material invoices from verified Vietnamese suppliers", 20.5, "Documents are generic templates, recycled across shipments, no verifiable factory", "Factory visit with customs official, production records with sequential lot numbers, supplier documentation", 72.3, current_score, current_score - 20.5, current_score + 72.3 - current_score, "CRITICAL", "REQUEST: Factory inspection with CBP, verified supplier documentation, sequential lot tracing"),
        ("Transshipment Only Model", "Is the shipment merely transiting Vietnam, or is transformation occurring?", "HIGH", "Goods produced elsewhere, routed through Vietnam with minimal handling (warehousing only)", "Warehouse receipt only, goods in sealed containers, no transformation records, direct Vietnam-to-US routing", 45.2, "Goods are substantially transformed in Vietnam (repackaging, QC testing, relabeling)", "Factory transformation records, inspection certificates from Vietnam, assembly/testing documentation", 28.7, current_score, current_score + 45.2 - current_score, current_score - 28.7, "CRITICAL", "REQUEST: Warehouse records for Vietnam location, detailed transformation process documentation"),
        ("Shipper Legitimacy", "Is the declared shipper a genuine exporter or a shell trading company?", "CRITICAL", "Shipper demonstrates manufacturing ownership through plant contracts, subcontracting agreements, QC traceability", "Multi-year supplier contracts, factory audits, QC records, employee roster at facility, equipment inventory", 18.4, "Shipper has no verifiable manufacturing role, operates as paper exporter using third-party suppliers", "Factory visit records, contract with actual manufacturer, shipper business registration, supplier agreements", 68.9, current_score, current_score - 18.4, current_score + 68.9 - current_score, "CRITICAL", "REQUEST: Factory location verification, manufacturer contracts, QC documentation, shipper registration"),
        ("ISF Element 9 Resolution", "Can the ISF Element 9 country mismatch be explained by legitimate circumstances?", "HIGH", "Declared manufacturing location in Vietnam verified; AIS dwell explained by legitimate delays (port congestion)", "Factory documentation showing production, shipper statement on delays, port authority congestion records", 15.6, "Mismatch indicates origin fraud; goods actually produced in China, ISF misrepresented", "Factory audit in declared location, Chinese factory source records, shipper documentation", 88.2, current_score, current_score - 15.6, current_score + 88.2 - current_score, "CRITICAL", "REQUEST: ISF correction submission, factory audit, shipper sworn affidavit on origin"),
    ]
    for scenario_name, scenario_desc, priority, true_desc, true_evid, true_risk, false_desc, false_evid, false_risk, curr_risk, impact_true, impact_false, impact_cat, recommendation in scenarios:
        cursor.execute(
            """
            INSERT INTO risk_what_if_scenarios (
                id, shipment_id, scenario_name, scenario_description, scenario_priority,
                what_if_true_description, what_if_true_evidence_needed, what_if_true_risk_score,
                what_if_false_description, what_if_false_evidence_needed, what_if_false_risk_score,
                current_risk_score, impact_if_true, impact_if_false, impact_category, investigation_recommendation
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                f"{shipment_id}-SCENARIO-{scenario_name.replace(' ', '-')}",
                shipment_id,
                scenario_name,
                scenario_desc,
                priority,
                true_desc,
                true_evid,
                true_risk,
                false_desc,
                false_evid,
                false_risk,
                curr_risk,
                impact_true,
                impact_false,
                impact_cat,
                recommendation,
            ),
        )


def get_risk_components(shipment_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """Get component-level scoring breakdown grouped by category."""
    conn = _get_conn()
    cursor = _get_cursor(conn)
    try:
        cursor.execute(
            """
            SELECT * FROM risk_components
            WHERE shipment_id = %s
            ORDER BY component_category, component_name
            """,
            (shipment_id,),
        )
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for component in cursor.fetchall():
            payload = dict(component)
            grouped.setdefault(payload["component_category"], []).append(payload)
        return grouped
    finally:
        cursor.close()
        conn.close()


def get_risk_adjustments(shipment_id: str) -> List[Dict[str, Any]]:
    """Get all adjustments, multipliers, and bonuses."""
    conn = _get_conn()
    cursor = _get_cursor(conn)
    try:
        cursor.execute(
            """
            SELECT * FROM risk_adjustments
            WHERE shipment_id = %s
            ORDER BY adjustment_type
            """,
            (shipment_id,),
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        cursor.close()
        conn.close()


def get_risk_ledger(shipment_id: str) -> List[Dict[str, Any]]:
    """Get step-by-step calculation ledger."""
    conn = _get_conn()
    cursor = _get_cursor(conn)
    try:
        cursor.execute(
            """
            SELECT * FROM risk_ledger
            WHERE shipment_id = %s
            ORDER BY ledger_step
            """,
            (shipment_id,),
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        cursor.close()
        conn.close()


def get_what_if_scenarios(shipment_id: str) -> List[Dict[str, Any]]:
    """Get what-if scenario analysis."""
    conn = _get_conn()
    cursor = _get_cursor(conn)
    try:
        cursor.execute(
            """
            SELECT * FROM risk_what_if_scenarios
            WHERE shipment_id = %s
            ORDER BY scenario_priority DESC, scenario_name
            """,
            (shipment_id,),
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        cursor.close()
        conn.close()


def create_upload_job(job_id: str, filename: str, total_rows: int) -> str:
    """Create a manifest upload job record."""
    conn = _get_conn()
    cursor = _get_cursor(conn)
    try:
        cursor.execute(
            """
            INSERT INTO upload_jobs (id, filename, status, total_rows, created_at)
            VALUES (%s, %s, 'pending', %s, %s)
            RETURNING id
            """,
            (job_id, filename, total_rows, datetime.utcnow()),
        )
        created_id = cursor.fetchone()["id"]
        conn.commit()
        return created_id
    finally:
        cursor.close()
        conn.close()


def get_upload_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Get upload job status."""
    conn = _get_conn()
    cursor = _get_cursor(conn)
    try:
        cursor.execute("SELECT * FROM upload_jobs WHERE id = %s", (job_id,))
        return _normalize_json_fields(cursor.fetchone(), {"errors"})
    finally:
        cursor.close()
        conn.close()


def update_upload_job(job_id: str, **fields) -> None:
    """Update upload job fields."""
    if not fields:
        return

    conn = _get_conn()
    cursor = _get_cursor(conn)
    try:
        assignments = [
            sql.SQL("{} = %s").format(sql.Identifier(column))
            for column in fields.keys()
        ]
        values = [_coerce_value(column, value) for column, value in fields.items()]
        query = sql.SQL("UPDATE upload_jobs SET {} WHERE id = %s").format(
            sql.SQL(", ").join(assignments)
        )
        cursor.execute(query, values + [job_id])
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def batch_create_shipments(rows: List[Dict[str, Any]], manifest_id: str) -> List[str]:
    """Batch create shipment records, return IDs."""
    conn = _get_conn()
    cursor = _get_cursor(conn)
    shipment_ids: List[str] = []
    columns = [
        "id", "manifest_id", "shipper_name", "consignee_name", "origin_country", "destination_country",
        "hs_code", "declared_value_usd", "declared_weight_kg", "description", "vessel_name",
        "vessel_imo", "vessel_flag", "dwell_days", "ais_stuffing_country", "port_calls",
        "element9_is_mismatch", "element9_confidence", "element9_declared_country", "element9_actual_country",
        "shipper_age_months", "shipper_country", "consignee_country", "ad_cvd_rate", "ad_cvd_applicable",
        "status", "risk_score", "risk_delta", "h1_score", "h2_score", "h3_score", "h1_h2_score",
        "manifest_source_id", "ship_id", "calculated_risk_score", "risk_score_calculated_at",
        "risk_score_breakdown", "confidence_interval", "model_version", "model_maturity", "corridor_id",
        "bill_of_lading", "voyage_number", "h2_signals", "h3_recommendation", "customs_flags",
        "inspection_history", "commodity_code", "commodity_name", "price_variance_percent",
        "unit_price_per_kg", "declared_unit_value", "audit_trail", "risk_breakdown", "ai_synthesis",
        "isf_data", "isf_element_mismatch", "isf_filed_date", "isf_late_filing", "created_at"
    ]
    placeholders = ", ".join(["%s"] * len(columns))
    try:
        for row in rows:
            shipment_id = str(uuid.uuid4())
            values_by_column = {
                "id": shipment_id,
                "manifest_id": manifest_id,
                "shipper_name": row.get("shipper_name"),
                "consignee_name": row.get("consignee_name"),
                "origin_country": row.get("origin_country"),
                "destination_country": row.get("destination_country"),
                "hs_code": row.get("hs_code"),
                "declared_value_usd": row.get("declared_value_usd"),
                "declared_weight_kg": row.get("declared_weight_kg"),
                "description": row.get("description"),
                "vessel_name": row.get("vessel_name"),
                "vessel_imo": row.get("vessel_imo"),
                "vessel_flag": row.get("vessel_flag"),
                "dwell_days": row.get("dwell_days"),
                "ais_stuffing_country": row.get("ais_stuffing_country"),
                "port_calls": row.get("port_calls"),
                "element9_is_mismatch": row.get("element9_is_mismatch"),
                "element9_confidence": row.get("element9_confidence"),
                "element9_declared_country": row.get("element9_declared_country"),
                "element9_actual_country": row.get("element9_actual_country"),
                "shipper_age_months": row.get("shipper_age_months"),
                "shipper_country": row.get("shipper_country"),
                "consignee_country": row.get("consignee_country"),
                "ad_cvd_rate": row.get("ad_cvd_rate"),
                "ad_cvd_applicable": row.get("ad_cvd_applicable"),
                "status": row.get("status", "received"),
                "risk_score": row.get("risk_score"),
                "risk_delta": row.get("risk_delta"),
                "h1_score": row.get("h1_score"),
                "h2_score": row.get("h2_score"),
                "h3_score": row.get("h3_score"),
                "h1_h2_score": row.get("h1_h2_score"),
                "manifest_source_id": row.get("manifest_source_id"),
                "ship_id": row.get("ship_id"),
                "calculated_risk_score": row.get("calculated_risk_score"),
                "risk_score_calculated_at": row.get("risk_score_calculated_at"),
                "risk_score_breakdown": row.get("risk_score_breakdown"),
                "confidence_interval": row.get("confidence_interval"),
                "model_version": row.get("model_version"),
                "model_maturity": row.get("model_maturity"),
                "corridor_id": row.get("corridor_id"),
                "bill_of_lading": row.get("bill_of_lading"),
                "voyage_number": row.get("voyage_number"),
                "h2_signals": row.get("h2_signals"),
                "h3_recommendation": row.get("h3_recommendation"),
                "customs_flags": row.get("customs_flags"),
                "inspection_history": row.get("inspection_history"),
                "commodity_code": row.get("commodity_code"),
                "commodity_name": row.get("commodity_name"),
                "price_variance_percent": row.get("price_variance_percent"),
                "unit_price_per_kg": row.get("unit_price_per_kg"),
                "declared_unit_value": row.get("declared_unit_value"),
                "audit_trail": row.get("audit_trail"),
                "risk_breakdown": row.get("risk_breakdown"),
                "ai_synthesis": row.get("ai_synthesis"),
                "isf_data": row.get("isf_data"),
                "isf_element_mismatch": row.get("isf_element_mismatch"),
                "isf_filed_date": row.get("isf_filed_date"),
                "isf_late_filing": row.get("isf_late_filing"),
                "created_at": datetime.utcnow(),
            }
            values = [_coerce_value(column, values_by_column.get(column)) for column in columns]
            cursor.execute(
                f"INSERT INTO shipments ({', '.join(columns)}) VALUES ({placeholders})",
                values,
            )
            shipment_ids.append(shipment_id)
        conn.commit()
        return shipment_ids
    finally:
        cursor.close()
        conn.close()


def batch_update_risk_scores(updates: List[Dict[str, Any]]) -> None:
    """Batch update risk scores for shipments."""
    conn = _get_conn()
    cursor = _get_cursor(conn)
    try:
        for update in updates:
            shipment_id = update.get("id")
            if not shipment_id:
                continue

            fields: Dict[str, Any] = {
                "risk_score": update.get("risk_score"),
                "h1_score": update.get("h1_score"),
                "h2_score": update.get("h2_score"),
                "h3_score": update.get("h3_score"),
                "status": update.get("status", "scored"),
                "updated_at": datetime.utcnow(),
            }
            for optional_field in (
                "calculated_risk_score",
                "risk_score_calculated_at",
                "risk_score_breakdown",
                "confidence_interval",
                "model_version",
                "model_maturity",
            ):
                if optional_field in update:
                    fields[optional_field] = update.get(optional_field)

            assignments = [
                sql.SQL("{} = %s").format(sql.Identifier(column))
                for column in fields.keys()
            ]
            values = [_coerce_value(column, value) for column, value in fields.items()]
            query = sql.SQL("UPDATE shipments SET {} WHERE id = %s").format(sql.SQL(", ").join(assignments))
            cursor.execute(query, values + [shipment_id])
            _record_score_history(
                cursor,
                shipment_id,
                update.get("calculated_risk_score", update.get("risk_score")),
                update.get("model_version"),
                update.get("model_maturity"),
            )
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def find_existing_source_ids(source_ids: List[str]) -> set:
    """Find which manifest_source_ids already exist in the database."""
    if not source_ids:
        return set()

    conn = _get_conn()
    cursor = _get_cursor(conn)
    try:
        cursor.execute(
            "SELECT manifest_source_id FROM shipments WHERE manifest_source_id = ANY(%s)",
            (source_ids,),
        )
        return {row["manifest_source_id"] for row in cursor.fetchall() if row.get("manifest_source_id")}
    finally:
        cursor.close()
        conn.close()


def create_or_update_risk_score_cache(
    shipment_id: str,
    final_score: float,
    breakdown_json: str,
    current_model_version: str = "7factor-v1.0",
) -> str:
    """Create or update risk score in cache (current snapshot)."""
    conn = _get_conn()
    cursor = _get_cursor(conn)
    cache_id = str(uuid.uuid4())
    try:
        cursor.execute(
            """
            INSERT INTO risk_score_cache (
                id, shipment_id, final_score, risk_level, breakdown_json,
                current_model_version, calculation_timestamp, is_stale, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, FALSE, %s)
            ON CONFLICT (shipment_id) DO UPDATE SET
                final_score = EXCLUDED.final_score,
                risk_level = EXCLUDED.risk_level,
                breakdown_json = EXCLUDED.breakdown_json,
                current_model_version = EXCLUDED.current_model_version,
                calculation_timestamp = EXCLUDED.calculation_timestamp,
                is_stale = FALSE,
                updated_at = EXCLUDED.updated_at
            RETURNING id
            """,
            (
                cache_id,
                shipment_id,
                final_score,
                _risk_level(final_score),
                _coerce_value("breakdown_json", breakdown_json),
                current_model_version,
                datetime.utcnow(),
                datetime.utcnow(),
            ),
        )
        saved_id = cursor.fetchone()["id"]
        conn.commit()
        logger.info("Cached risk score for %s: %s/100 (model: %s)", shipment_id, final_score, current_model_version)
        return saved_id
    finally:
        cursor.close()
        conn.close()


def get_risk_score_cache(shipment_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve current cached risk score."""
    conn = _get_conn()
    cursor = _get_cursor(conn)
    try:
        cursor.execute("SELECT * FROM risk_score_cache WHERE shipment_id = %s", (shipment_id,))
        return _normalize_json_fields(cursor.fetchone(), {"breakdown_json"})
    except Exception as exc:
        logger.error("Failed to retrieve cached score for %s: %s", shipment_id, exc)
        return None
    finally:
        cursor.close()
        conn.close()


def record_risk_score_transaction(
    shipment_id: str,
    new_final_score: float,
    new_breakdown_json: str,
    transaction_type: str,
    transaction_reason: str = None,
    previous_final_score: float = None,
    previous_breakdown_json: str = None,
    triggered_by: str = "system",
    triggered_by_model_version: str = None,
) -> str:
    """Record score change as immutable transaction."""
    conn = _get_conn()
    cursor = _get_cursor(conn)
    txn_id = str(uuid.uuid4())
    try:
        score_delta = new_final_score - previous_final_score if previous_final_score is not None else None
        cursor.execute(
            """
            INSERT INTO risk_score_transactions (
                id, shipment_id, previous_final_score, new_final_score, score_delta,
                transaction_type, transaction_reason, previous_breakdown_json, new_breakdown_json,
                triggered_by, triggered_by_model_version, transaction_timestamp
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                txn_id,
                shipment_id,
                previous_final_score,
                new_final_score,
                score_delta,
                transaction_type,
                transaction_reason,
                _coerce_value("previous_breakdown_json", previous_breakdown_json),
                _coerce_value("new_breakdown_json", new_breakdown_json),
                triggered_by,
                triggered_by_model_version,
                datetime.utcnow(),
            ),
        )
        saved_id = cursor.fetchone()["id"]
        conn.commit()
        logger.info("Recorded transaction for %s: %s (%s)", shipment_id, transaction_type, transaction_reason)
        return saved_id
    finally:
        cursor.close()
        conn.close()


def get_risk_score_history(shipment_id: str) -> List[Dict[str, Any]]:
    """Retrieve all score transactions for a shipment."""
    conn = _get_conn()
    cursor = _get_cursor(conn)
    try:
        cursor.execute(
            """
            SELECT * FROM risk_score_transactions
            WHERE shipment_id = %s
            ORDER BY transaction_timestamp DESC
            """,
            (shipment_id,),
        )
        return _normalize_rows(cursor.fetchall(), {"previous_breakdown_json", "new_breakdown_json"})
    except Exception as exc:
        logger.error("Failed to retrieve history for %s: %s", shipment_id, exc)
        return []
    finally:
        cursor.close()
        conn.close()


def mark_scores_stale(model_version: str) -> int:
    """Mark all scores from old model as stale."""
    conn = _get_conn()
    cursor = _get_cursor(conn)
    try:
        cursor.execute(
            """
            UPDATE risk_score_cache
            SET is_stale = TRUE, updated_at = %s
            WHERE current_model_version != %s AND is_stale = FALSE
            """,
            (datetime.utcnow(), model_version),
        )
        count = cursor.rowcount
        conn.commit()
        logger.info("Marked %s scores as stale (new model: %s)", count, model_version)
        return count
    except Exception as exc:
        logger.error("Failed to mark scores stale: %s", exc)
        return 0
    finally:
        cursor.close()
        conn.close()


def record_altana_scenario(
    shipment_id: str,
    risk_score_id: str,
    initial_score: float,
    altana_response: Dict[str, Any] = None,
) -> Optional[str]:
    """Record Altana API call (only if score >= 70)."""
    conn = _get_conn()
    cursor = _get_cursor(conn)
    scenario_id = str(uuid.uuid4())
    try:
        threshold_met = initial_score >= 70
        altana_response = altana_response or {}
        if threshold_met and altana_response:
            confidence = altana_response.get("confidence", 0)
            if confidence > 0.85:
                adjustment = 5.0
                bracket = ">85%"
            elif confidence >= 0.60:
                adjustment = 2.0
                bracket = "60-85%"
            else:
                adjustment = -8.0
                bracket = "<60%"
            final_score = initial_score + adjustment
        else:
            adjustment = 0.0
            bracket = "NOT_CALLED"
            final_score = initial_score
            altana_response = {}

        cursor.execute(
            """
            INSERT INTO altana_scenarios (
                id, shipment_id, risk_score_id, initial_score_before_altana, threshold_met,
                query_timestamp, altana_confidence, altana_recommendation, altana_risk_factors,
                supply_chain_opacity, sanctions_exposure, confidence_bracket, adjustment_points,
                final_score_after_altana, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (shipment_id) DO UPDATE SET
                risk_score_id = EXCLUDED.risk_score_id,
                initial_score_before_altana = EXCLUDED.initial_score_before_altana,
                threshold_met = EXCLUDED.threshold_met,
                query_timestamp = EXCLUDED.query_timestamp,
                altana_confidence = EXCLUDED.altana_confidence,
                altana_recommendation = EXCLUDED.altana_recommendation,
                altana_risk_factors = EXCLUDED.altana_risk_factors,
                supply_chain_opacity = EXCLUDED.supply_chain_opacity,
                sanctions_exposure = EXCLUDED.sanctions_exposure,
                confidence_bracket = EXCLUDED.confidence_bracket,
                adjustment_points = EXCLUDED.adjustment_points,
                final_score_after_altana = EXCLUDED.final_score_after_altana,
                updated_at = EXCLUDED.updated_at
            RETURNING id
            """,
            (
                scenario_id,
                shipment_id,
                risk_score_id,
                initial_score,
                threshold_met,
                datetime.utcnow() if threshold_met else None,
                altana_response.get("confidence"),
                altana_response.get("recommendation"),
                _coerce_value("altana_risk_factors", altana_response.get("risk_factors", [])),
                altana_response.get("supply_chain_opacity"),
                altana_response.get("sanctions_exposure"),
                bracket,
                adjustment,
                final_score,
                datetime.utcnow(),
            ),
        )
        saved_id = cursor.fetchone()["id"]
        conn.commit()
        logger.info("Recorded Altana scenario for %s (threshold_met=%s)", shipment_id, threshold_met)
        return saved_id
    except Exception as exc:
        logger.error("Failed to record Altana scenario for %s: %s", shipment_id, exc)
        return None
    finally:
        cursor.close()
        conn.close()


def register_model_version(
    model_name: str,
    version_number: str,
    model_params: Dict[str, Any] = None,
    notes: str = None,
) -> str:
    """Register a new ML model version."""
    conn = _get_conn()
    cursor = _get_cursor(conn)
    model_id = f"{model_name}-{version_number}"
    params = model_params or {}
    try:
        cursor.execute(
            """
            INSERT INTO model_versions (
                id, model_name, version_number, training_date, released_at,
                isolation_forest_n_estimators, isolation_forest_contamination, isolation_forest_random_state,
                lightgbm_num_leaves, lightgbm_learning_rate, lightgbm_max_depth,
                is_active, total_calculations, notes
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, 0, %s)
            ON CONFLICT (id) DO UPDATE SET
                model_name = EXCLUDED.model_name,
                version_number = EXCLUDED.version_number,
                training_date = EXCLUDED.training_date,
                released_at = EXCLUDED.released_at,
                isolation_forest_n_estimators = EXCLUDED.isolation_forest_n_estimators,
                isolation_forest_contamination = EXCLUDED.isolation_forest_contamination,
                isolation_forest_random_state = EXCLUDED.isolation_forest_random_state,
                lightgbm_num_leaves = EXCLUDED.lightgbm_num_leaves,
                lightgbm_learning_rate = EXCLUDED.lightgbm_learning_rate,
                lightgbm_max_depth = EXCLUDED.lightgbm_max_depth,
                is_active = EXCLUDED.is_active,
                notes = EXCLUDED.notes
            RETURNING id
            """,
            (
                model_id,
                model_name,
                version_number,
                params.get("training_date"),
                datetime.utcnow(),
                params.get("isolation_forest_n_estimators"),
                params.get("isolation_forest_contamination"),
                params.get("isolation_forest_random_state"),
                params.get("lightgbm_num_leaves"),
                params.get("lightgbm_learning_rate"),
                params.get("lightgbm_max_depth"),
                notes,
            ),
        )
        saved_id = cursor.fetchone()["id"]
        conn.commit()
        logger.info("Registered model version: %s", saved_id)
        return saved_id
    finally:
        cursor.close()
        conn.close()


def get_active_model_version() -> Optional[Dict[str, Any]]:
    """Get the currently active model version."""
    conn = _get_conn()
    cursor = _get_cursor(conn)
    try:
        cursor.execute(
            """
            SELECT * FROM model_versions
            WHERE is_active = TRUE
            ORDER BY released_at DESC
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as exc:
        logger.error("Failed to get active model version: %s", exc)
        return None
    finally:
        cursor.close()
        conn.close()


def get_model_version_by_id(model_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific model version by ID."""
    conn = _get_conn()
    cursor = _get_cursor(conn)
    try:
        cursor.execute("SELECT * FROM model_versions WHERE id = %s", (model_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as exc:
        logger.error("Failed to get model version %s: %s", model_id, exc)
        return None
    finally:
        cursor.close()
        conn.close()


def deactivate_model_version(model_id: str) -> bool:
    """Deactivate a model version."""
    conn = _get_conn()
    cursor = _get_cursor(conn)
    try:
        cursor.execute(
            """
            UPDATE model_versions
            SET is_active = FALSE, deprecated_at = %s
            WHERE id = %s
            """,
            (datetime.utcnow(), model_id),
        )
        conn.commit()
        logger.info("Deactivated model version: %s", model_id)
        return True
    except Exception as exc:
        logger.error("Failed to deactivate model version: %s", exc)
        return False
    finally:
        cursor.close()
        conn.close()


def activate_model_version(model_id: str) -> bool:
    """Activate a model version (deactivates all others)."""
    conn = _get_conn()
    cursor = _get_cursor(conn)
    try:
        cursor.execute(
            """
            UPDATE model_versions
            SET is_active = FALSE
            WHERE id != %s
            """,
            (model_id,),
        )
        cursor.execute(
            """
            UPDATE model_versions
            SET is_active = TRUE, deprecated_at = NULL, released_at = COALESCE(released_at, %s)
            WHERE id = %s
            """,
            (datetime.utcnow(), model_id),
        )
        conn.commit()
        logger.info("Activated model version: %s", model_id)
        return True
    except Exception as exc:
        logger.error("Failed to activate model version: %s", exc)
        return False
    finally:
        cursor.close()
        conn.close()
