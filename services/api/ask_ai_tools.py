"""Ask-AI Agent Tool Functions — Database Query Layer

10 tools for Gemini function calling:
1. search_shipments — Find shipments by query, risk range, limit
2. get_shipment_risk_breakdown — Full H1/H2/H3 detail + audit trail
3. investigate_entity — CORD entity resolution
4. get_ownership_chain — Trace beneficial owners via CORD + internal tables
5. check_sanctions_screening — OFAC + OpenSanctions screening
6. get_corridor_risk — Trade route risk (AD/CVD, enforcement history)
7. get_case_statistics — Aggregate workload metrics
8. get_what_if_scenarios — Risk scenario analysis
9. get_historical_patterns — Shipper/entity history
10. get_referral_summary — Referral packages + officer analysis
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import json

logger = logging.getLogger(__name__)

# DB paths
PRIMARY_DB = "/app/data/cbp_sentry.db"
CORD_DB = "/app/data/cord_rag.db"


def _get_conn(db_path: str) -> sqlite3.Connection:
    """Get SQLite connection with row factory."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to {db_path}: {e}")
        raise


# ============================================================================
# TOOL 1: search_shipments
# ============================================================================

async def search_shipments(
    query: str = "",
    risk_min: float = 0.0,
    risk_max: float = 100.0,
    limit: int = 10
) -> Dict[str, Any]:
    """Search shipments by keyword (shipper/consignee name, vessel, country) and risk range.

    Args:
        query: Keyword search term (shipper, consignee, vessel name, country code)
        risk_min: Minimum risk score (0-100)
        risk_max: Maximum risk score (0-100)
        limit: Max results (1-50, default 10)

    Returns:
        {
            "found": int,
            "shipments": [
                {
                    "id": str,
                    "shipper_name": str,
                    "consignee_name": str,
                    "origin_country": str,
                    "destination_country": str,
                    "commodity": str,
                    "risk_score": float,
                    "status": str,
                    "created_at": str
                }
            ]
        }
    """
    try:
        conn = _get_conn(PRIMARY_DB)
        cur = conn.cursor()

        limit = min(max(limit, 1), 50)

        if query:
            query_lower = f"%{query}%"
            cur.execute(f"""
                SELECT id, shipper_name, consignee_name, origin_country,
                       destination_country, description, risk_score, status, created_at
                FROM shipments
                WHERE (shipper_name LIKE ? OR consignee_name LIKE ? OR vessel_name LIKE ?
                       OR origin_country LIKE ? OR destination_country LIKE ?)
                AND risk_score BETWEEN ? AND ?
                ORDER BY COALESCE(risk_score, 0) DESC
                LIMIT ?
            """, (query_lower, query_lower, query_lower, query_lower, query_lower, risk_min, risk_max, limit))
        else:
            cur.execute(f"""
                SELECT id, shipper_name, consignee_name, origin_country,
                       destination_country, description, risk_score, status, created_at
                FROM shipments
                WHERE risk_score BETWEEN ? AND ?
                ORDER BY COALESCE(risk_score, 0) DESC
                LIMIT ?
            """, (risk_min, risk_max, limit))

        rows = cur.fetchall()
        conn.close()

        return {
            "found": len(rows),
            "shipments": [
                {
                    "id": row["id"],
                    "shipper_name": row["shipper_name"],
                    "consignee_name": row["consignee_name"],
                    "origin_country": row["origin_country"],
                    "destination_country": row["destination_country"],
                    "commodity": row["description"],
                    "risk_score": row["risk_score"],
                    "status": row["status"],
                    "created_at": row["created_at"]
                }
                for row in rows
            ]
        }
    except Exception as e:
        logger.error(f"search_shipments error: {e}")
        return {"found": 0, "shipments": [], "error": str(e)}


# ============================================================================
# TOOL 2: get_shipment_risk_breakdown
# ============================================================================

async def get_shipment_risk_breakdown(shipment_id: str) -> Dict[str, Any]:
    """Get full risk score breakdown: H1/H2/H3 scores, components, and audit trail.

    Args:
        shipment_id: Shipment ID (e.g., "SHP-001")

    Returns:
        {
            "shipment_id": str,
            "final_score": float,
            "risk_level": str,
            "h1_score": float,
            "h2_score": float,
            "h3_score": float,
            "h1_h2_score": float,
            "components": [{name, category, value, weight, evidence}],
            "adjustments": [{name, type, amount, confidence, evidence}],
            "ledger": [{step, description, input, operation, output}],
            "altana_summary": {...},
            "created_at": str
        }
    """
    try:
        conn = _get_conn(PRIMARY_DB)
        cur = conn.cursor()

        # Get shipment + cached score
        cur.execute("""
            SELECT s.id, s.shipper_name, s.risk_score, s.h1_score, s.h2_score, s.h3_score,
                   s.h1_h2_score, s.created_at,
                   rc.final_score, rc.risk_level, rc.breakdown_json, rc.confidence_interval
            FROM shipments s
            LEFT JOIN risk_scores_cache rc ON s.id = rc.shipment_id
            WHERE s.id = ?
        """, (shipment_id,))

        shipment = cur.fetchone()
        if not shipment:
            conn.close()
            return {"error": f"Shipment {shipment_id} not found"}

        # Get components
        cur.execute("""
            SELECT component_name, component_category, component_value, component_weight,
                   weighted_value, evidence
            FROM risk_score_components
            WHERE shipment_id = ?
            ORDER BY component_category, component_weight DESC
        """, (shipment_id,))
        components = [
            {
                "name": row["component_name"],
                "category": row["component_category"],
                "value": row["component_value"],
                "weight": row["component_weight"],
                "weighted_value": row["weighted_value"],
                "evidence": row["evidence"]
            }
            for row in cur.fetchall()
        ]

        # Get adjustments (Altana, multipliers, etc.)
        cur.execute("""
            SELECT adjustment_name, adjustment_type, adjustment_amount, adjustment_multiplier,
                   confidence_score, evidence_detail
            FROM risk_score_adjustments
            WHERE shipment_id = ?
            ORDER BY adjustment_type DESC
        """, (shipment_id,))
        adjustments = [
            {
                "name": row["adjustment_name"],
                "type": row["adjustment_type"],
                "amount": row["adjustment_amount"],
                "multiplier": row["adjustment_multiplier"],
                "confidence": row["confidence_score"],
                "evidence": row["evidence_detail"]
            }
            for row in cur.fetchall()
        ]

        # Get ledger (audit trail)
        cur.execute("""
            SELECT ledger_step, step_name, step_description, input_value, operation, output_value
            FROM risk_score_ledger
            WHERE shipment_id = ?
            ORDER BY ledger_step ASC
        """, (shipment_id,))
        ledger = [
            {
                "step": row["ledger_step"],
                "name": row["step_name"],
                "description": row["step_description"],
                "input": row["input_value"],
                "operation": row["operation"],
                "output": row["output_value"]
            }
            for row in cur.fetchall()
        ]

        # Get Altana adjustment (if any)
        cur.execute("""
            SELECT initial_score_before_altana, final_score_after_altana,
                   altana_confidence, altana_recommendation, altana_risk_factors
            FROM altana_scenarios
            WHERE shipment_id = ?
            LIMIT 1
        """, (shipment_id,))
        altana = cur.fetchone()
        altana_summary = {}
        if altana:
            altana_summary = {
                "initial_score": altana["initial_score_before_altana"],
                "final_score": altana["final_score_after_altana"],
                "confidence": altana["altana_confidence"],
                "recommendation": altana["altana_recommendation"],
                "risk_factors": altana["altana_risk_factors"]
            }

        conn.close()

        return {
            "shipment_id": shipment_id,
            "shipper_name": shipment["shipper_name"],
            "final_score": shipment["final_score"] or shipment["risk_score"],
            "risk_level": shipment["risk_level"] or (
                "CRITICAL" if (shipment["risk_score"] or 0) >= 80 else
                "HIGH" if (shipment["risk_score"] or 0) >= 60 else
                "MEDIUM"
            ),
            "h1_score": shipment["h1_score"],
            "h2_score": shipment["h2_score"],
            "h3_score": shipment["h3_score"],
            "h1_h2_score": shipment["h1_h2_score"],
            "components": components,
            "adjustments": adjustments,
            "ledger": ledger,
            "altana_summary": altana_summary,
            "confidence_interval": shipment["confidence_interval"],
            "created_at": shipment["created_at"]
        }
    except Exception as e:
        logger.error(f"get_shipment_risk_breakdown error: {e}")
        return {"error": str(e)}


# ============================================================================
# TOOL 3: investigate_entity
# ============================================================================

async def investigate_entity(entity_name: str, country: str = "") -> Dict[str, Any]:
    """Query CORD 21M-entity database for entity resolution.

    Args:
        entity_name: Company/person name
        country: ISO country code (optional, improves match)

    Returns:
        {
            "found": bool,
            "entity_id": str,
            "entity_name": str,
            "country": str,
            "beneficial_owner": str,
            "parent_company": str,
            "parent_country": str,
            "data_source": str (CORD_LONDON, CORD_MOSCOW, CORD_LASVEGAS),
            "gleif_id": str,
            "sanctions_status": str (CLEAR, OFAC_HIT, OPENSANCTIONS_HIT),
            "match_type": str (exact, fuzzy, not_found),
            "confidence": float (0.0-1.0)
        }
    """
    try:
        conn = _get_conn(CORD_DB)
        cur = conn.cursor()

        if not Path(CORD_DB).exists():
            conn.close()
            return {
                "found": False,
                "error": f"CORD database not found at {CORD_DB}. Run: python3 scripts/build_cord_rag_db.py"
            }

        # Step 1: Exact match
        if country:
            query = f"%{entity_name}%"
            cur.execute("""
                SELECT * FROM entities
                WHERE UPPER(entity_name) = UPPER(?)
                AND UPPER(country) = UPPER(?)
                LIMIT 1
            """, (entity_name, country))
        else:
            cur.execute("""
                SELECT * FROM entities
                WHERE UPPER(entity_name) = UPPER(?)
                LIMIT 1
            """, (entity_name,))

        result = cur.fetchone()
        match_type = "exact"
        confidence = 0.95 if result else 0.0

        # Step 2: Fuzzy match if exact fails
        if not result:
            query = f"%{entity_name}%"
            if country:
                cur.execute("""
                    SELECT * FROM entities
                    WHERE entity_name LIKE ?
                    AND UPPER(country) = UPPER(?)
                    ORDER BY LENGTH(entity_name) ASC
                    LIMIT 1
                """, (query, country))
            else:
                cur.execute("""
                    SELECT * FROM entities
                    WHERE entity_name LIKE ?
                    ORDER BY LENGTH(entity_name) ASC
                    LIMIT 1
                """, (query,))

            result = cur.fetchone()
            match_type = "fuzzy"
            confidence = 0.65 if result else 0.0

        conn.close()

        if not result:
            return {
                "found": False,
                "entity_name": entity_name,
                "country": country,
                "match_type": "not_found",
                "confidence": 0.0
            }

        return {
            "found": True,
            "entity_id": result["entity_id"],
            "entity_name": result["entity_name"],
            "country": result["country"],
            "beneficial_owner": result["beneficial_owner"],
            "parent_company": result["parent_company"],
            "parent_country": result["parent_country"],
            "data_source": result["data_source"],
            "gleif_id": result["gleif_id"],
            "sanctions_status": result["sanctions_status"],
            "match_type": match_type,
            "confidence": confidence
        }
    except Exception as e:
        logger.error(f"investigate_entity error: {e}")
        return {"found": False, "error": str(e)}


# ============================================================================
# TOOL 4: get_ownership_chain
# ============================================================================

async def get_ownership_chain(entity_name: str, depth: int = 3) -> Dict[str, Any]:
    """Trace beneficial owner chain: entity → parent → parent's parent.

    Args:
        entity_name: Starting entity name
        depth: Max chain depth (1-5)

    Returns:
        {
            "entity_name": str,
            "chain": [
                {
                    "tier": int (1=direct owner, 2=parent, 3=grandparent),
                    "entity_id": str,
                    "entity_name": str,
                    "country": str,
                    "relationship": str (beneficial_owner, parent_company, etc),
                    "confidence": float
                }
            ],
            "shell_company_flags": [str],
            "total_tiers": int
        }
    """
    try:
        chain = []
        depth = min(max(depth, 1), 5)
        shell_flags = []
        visited = set()

        # Start with the initial entity
        entity = await investigate_entity(entity_name)
        if not entity.get("found"):
            return {"entity_name": entity_name, "chain": [], "shell_company_flags": [], "total_tiers": 0}

        conn = _get_conn(CORD_DB)
        cur = conn.cursor()

        current_entity = entity
        tier = 1

        while tier <= depth and current_entity.get("found"):
            chain.append({
                "tier": tier,
                "entity_id": current_entity.get("entity_id"),
                "entity_name": current_entity.get("entity_name"),
                "country": current_entity.get("country"),
                "relationship": "beneficial_owner" if tier == 1 else "parent_company",
                "confidence": current_entity.get("confidence", 0.0)
            })

            # Check for shell company patterns
            parent_name = current_entity.get("parent_company")
            if parent_name and parent_name not in visited:
                visited.add(parent_name)
                # Shell company flags: very new incorporation, no public beneficial owner data
                if current_entity.get("data_source") == "OPEN_OWNERSHIP" and tier > 2:
                    shell_flags.append(f"Tier {tier}: {parent_name} has no public beneficial owner data (potential shell)")

                # Look up parent
                parent_country = current_entity.get("parent_country", "")
                cur.execute("""
                    SELECT * FROM entities
                    WHERE UPPER(entity_name) = UPPER(?)
                    AND UPPER(country) = UPPER(?)
                    LIMIT 1
                """, (parent_name, parent_country))

                parent = cur.fetchone()
                if parent:
                    current_entity = {
                        "found": True,
                        "entity_id": parent["entity_id"],
                        "entity_name": parent["entity_name"],
                        "country": parent["country"],
                        "parent_company": parent["parent_company"],
                        "parent_country": parent["parent_country"],
                        "data_source": parent["data_source"],
                        "confidence": 0.85
                    }
                    tier += 1
                else:
                    current_entity["found"] = False
            else:
                current_entity["found"] = False

        conn.close()

        return {
            "entity_name": entity_name,
            "chain": chain,
            "shell_company_flags": shell_flags,
            "total_tiers": len(chain)
        }
    except Exception as e:
        logger.error(f"get_ownership_chain error: {e}")
        return {"entity_name": entity_name, "chain": [], "error": str(e)}


# ============================================================================
# TOOL 5: check_sanctions_screening
# ============================================================================

async def check_sanctions_screening(entity_name: str, country: str = "") -> Dict[str, Any]:
    """Check entity against OFAC SDN list and OpenSanctions.

    Args:
        entity_name: Entity name
        country: ISO country code

    Returns:
        {
            "entity_name": str,
            "status": str (CLEAR, OFAC_HIT, OPENSANCTIONS_HIT, MULTIPLE_HITS),
            "hits": [
                {
                    "program": str (OFAC, OpenSanctions, UN, EU),
                    "entity_name": str,
                    "entity_type": str,
                    "sanctions_id": str,
                    "reason": str
                }
            ],
            "confidence": float,
            "checked_at": str
        }
    """
    try:
        hits = []

        if not Path(CORD_DB).exists():
            return {
                "entity_name": entity_name,
                "status": "UNKNOWN",
                "hits": [],
                "error": "CORD database not found"
            }

        conn = _get_conn(CORD_DB)
        cur = conn.cursor()

        # Check CORD entities sanctions_status field
        query = f"%{entity_name}%"
        cur.execute("""
            SELECT entity_id, entity_name, sanctions_status, country, data_source
            FROM entities
            WHERE entity_name LIKE ?
            AND sanctions_status IN ('OFAC_HIT', 'OPENSANCTIONS_HIT')
        """, (query,))

        for row in cur.fetchall():
            if country and row["country"].upper() != country.upper():
                continue

            hits.append({
                "program": "OFAC" if row["sanctions_status"] == "OFAC_HIT" else "OpenSanctions",
                "entity_name": row["entity_name"],
                "entity_id": row["entity_id"],
                "country": row["country"],
                "data_source": row["data_source"],
                "confidence": 0.95
            })

        conn.close()

        # Determine overall status
        if not hits:
            status = "CLEAR"
            confidence = 0.90
        elif len(hits) == 1:
            status = hits[0]["program"] + "_HIT"
            confidence = 0.95
        else:
            status = "MULTIPLE_HITS"
            confidence = 0.98

        return {
            "entity_name": entity_name,
            "status": status,
            "hits": hits,
            "confidence": confidence,
            "checked_at": sqlite3.Timestamp(0)
        }
    except Exception as e:
        logger.error(f"check_sanctions_screening error: {e}")
        return {"entity_name": entity_name, "status": "UNKNOWN", "hits": [], "error": str(e)}


# ============================================================================
# TOOL 6: get_corridor_risk
# ============================================================================

async def get_corridor_risk(origin_country: str, destination_country: str) -> Dict[str, Any]:
    """Get trade corridor risk profile: AD/CVD rates, enforcement history.

    Args:
        origin_country: ISO country code (e.g., "CN")
        destination_country: ISO country code (e.g., "US")

    Returns:
        {
            "corridor": str (e.g., "CN→US"),
            "risk_level": str (LOW, MEDIUM, HIGH),
            "ad_cvd_rates": [{hs_code, rate_pct, product_description}],
            "enforcement_actions": [{case_id, year, duty_evaded_usd, outcome}],
            "total_cases": int,
            "total_duties_evaded": float,
            "avg_duty_rate": float
        }
    """
    try:
        conn = _get_conn(PRIMARY_DB)
        cur = conn.cursor()

        # Get corridor
        cur.execute("""
            SELECT id, display_name, risk_level, primary_hs_chapters, risk_profile
            FROM corridors
            WHERE UPPER(origin_country) = UPPER(?)
            AND UPPER(destination_country) = UPPER(?)
            LIMIT 1
        """, (origin_country, destination_country))

        corridor = cur.fetchone()
        if not corridor:
            return {
                "corridor": f"{origin_country}→{destination_country}",
                "error": "Corridor not found"
            }

        # Get AD/CVD rates for this corridor
        cur.execute("""
            SELECT hs_prefix, rate_pct, product_description
            FROM corridor_duties
            WHERE corridor_id = ?
            ORDER BY rate_pct DESC
        """, (corridor["id"],))

        rates = [
            {
                "hs_code": row["hs_prefix"],
                "rate_pct": row["rate_pct"],
                "product": row["product_description"]
            }
            for row in cur.fetchall()
        ]

        # Get enforcement actions
        cur.execute("""
            SELECT case_id, case_year, duty_evaded_usd, case_status
            FROM corridor_enforcement_actions
            WHERE corridor_id = ?
            ORDER BY case_year DESC
        """, (corridor["id"],))

        actions = [
            {
                "case_id": row["case_id"],
                "year": row["case_year"],
                "duty_evaded_usd": row["duty_evaded_usd"],
                "outcome": row["case_status"]
            }
            for row in cur.fetchall()
        ]

        total_duties = sum(a.get("duty_evaded_usd", 0) for a in actions)
        avg_rate = sum(r.get("rate_pct", 0) for r in rates) / len(rates) if rates else 0.0

        conn.close()

        return {
            "corridor": corridor["display_name"],
            "risk_level": corridor["risk_level"],
            "hs_chapters": corridor["primary_hs_chapters"],
            "ad_cvd_rates": rates,
            "enforcement_actions": actions,
            "total_cases": len(actions),
            "total_duties_evaded_usd": total_duties,
            "avg_duty_rate_pct": round(avg_rate, 2)
        }
    except Exception as e:
        logger.error(f"get_corridor_risk error: {e}")
        return {"error": str(e)}


# ============================================================================
# TOOL 7: get_case_statistics
# ============================================================================

async def get_case_statistics() -> Dict[str, Any]:
    """Get aggregate case statistics: active cases, risk distribution, workload.

    Returns:
        {
            "total_shipments": int,
            "active_cases_risk_gte75": int,
            "critical_cases_risk_gte80": int,
            "average_risk_score": float,
            "risk_distribution": {
                "CRITICAL (80+)": int,
                "HIGH (60-79)": int,
                "MEDIUM (40-59)": int,
                "LOW (<40)": int
            },
            "top_corridors": [{"corridor": str, "shipment_count": int, "avg_risk": float}],
            "top_shippers": [{"name": str, "shipment_count": int, "avg_risk": float}]
        }
    """
    try:
        conn = _get_conn(PRIMARY_DB)
        cur = conn.cursor()

        # Basic counts
        cur.execute("SELECT COUNT(*) as cnt FROM shipments")
        total = cur.fetchone()["cnt"]

        cur.execute("SELECT COUNT(*) as cnt FROM shipments WHERE risk_score >= 75")
        active = cur.fetchone()["cnt"]

        cur.execute("SELECT COUNT(*) as cnt FROM shipments WHERE risk_score >= 80")
        critical = cur.fetchone()["cnt"]

        cur.execute("SELECT AVG(COALESCE(risk_score, 0)) as avg_score FROM shipments")
        avg_risk = cur.fetchone()["avg_score"] or 0.0

        # Risk distribution
        cur.execute("""
            SELECT
                SUM(CASE WHEN risk_score >= 80 THEN 1 ELSE 0 END) as critical,
                SUM(CASE WHEN risk_score >= 60 AND risk_score < 80 THEN 1 ELSE 0 END) as high,
                SUM(CASE WHEN risk_score >= 40 AND risk_score < 60 THEN 1 ELSE 0 END) as medium,
                SUM(CASE WHEN risk_score < 40 THEN 1 ELSE 0 END) as low
            FROM shipments
        """)
        dist = cur.fetchone()

        # Top corridors
        cur.execute("""
            SELECT origin_country || '→' || destination_country as corridor,
                   COUNT(*) as shipment_count,
                   AVG(COALESCE(risk_score, 0)) as avg_risk
            FROM shipments
            WHERE origin_country IS NOT NULL AND destination_country IS NOT NULL
            GROUP BY origin_country, destination_country
            ORDER BY shipment_count DESC
            LIMIT 5
        """)
        top_corridors = [
            {
                "corridor": row["corridor"],
                "shipment_count": row["shipment_count"],
                "avg_risk": round(row["avg_risk"], 2)
            }
            for row in cur.fetchall()
        ]

        # Top shippers
        cur.execute("""
            SELECT shipper_name,
                   COUNT(*) as shipment_count,
                   AVG(COALESCE(risk_score, 0)) as avg_risk
            FROM shipments
            WHERE shipper_name IS NOT NULL
            GROUP BY shipper_name
            ORDER BY shipment_count DESC
            LIMIT 5
        """)
        top_shippers = [
            {
                "name": row["shipper_name"],
                "shipment_count": row["shipment_count"],
                "avg_risk": round(row["avg_risk"], 2)
            }
            for row in cur.fetchall()
        ]

        conn.close()

        return {
            "total_shipments": total,
            "active_cases_risk_gte75": active,
            "critical_cases_risk_gte80": critical,
            "average_risk_score": round(avg_risk, 2),
            "risk_distribution": {
                "CRITICAL (80+)": dist["critical"] or 0,
                "HIGH (60-79)": dist["high"] or 0,
                "MEDIUM (40-59)": dist["medium"] or 0,
                "LOW (<40)": dist["low"] or 0
            },
            "top_corridors": top_corridors,
            "top_shippers": top_shippers
        }
    except Exception as e:
        logger.error(f"get_case_statistics error: {e}")
        return {"error": str(e)}


# ============================================================================
# TOOL 8: get_what_if_scenarios
# ============================================================================

async def get_what_if_scenarios(shipment_id: str) -> Dict[str, Any]:
    """Get risk scenario analysis: "What if X becomes true?"

    Args:
        shipment_id: Shipment ID

    Returns:
        {
            "shipment_id": str,
            "current_risk_score": float,
            "scenarios": [
                {
                    "scenario_name": str,
                    "description": str,
                    "if_true_risk_score": float,
                    "if_false_risk_score": float,
                    "risk_delta": float,
                    "investigation_recommendation": str,
                    "priority": str (HIGH, MEDIUM, LOW)
                }
            ]
        }
    """
    try:
        conn = _get_conn(PRIMARY_DB)
        cur = conn.cursor()

        # Get current score
        cur.execute("SELECT risk_score FROM shipments WHERE id = ?", (shipment_id,))
        shipment = cur.fetchone()
        if not shipment:
            return {"error": f"Shipment {shipment_id} not found"}

        current_score = shipment["risk_score"] or 0.0

        # Get scenarios
        cur.execute("""
            SELECT scenario_name, scenario_description, scenario_priority,
                   what_if_true_description, what_if_true_risk_score,
                   what_if_false_description, what_if_false_risk_score,
                   impact_if_true, impact_if_false,
                   investigation_recommendation
            FROM risk_what_if_scenarios
            WHERE shipment_id = ?
            ORDER BY scenario_priority DESC
        """, (shipment_id,))

        scenarios = [
            {
                "scenario_name": row["scenario_name"],
                "description": row["scenario_description"],
                "if_true_risk_score": row["what_if_true_risk_score"],
                "if_false_risk_score": row["what_if_false_risk_score"],
                "risk_delta": (row["what_if_true_risk_score"] or 0) - current_score,
                "if_true_impact": row["impact_if_true"],
                "if_false_impact": row["impact_if_false"],
                "investigation_recommendation": row["investigation_recommendation"],
                "priority": row["scenario_priority"]
            }
            for row in cur.fetchall()
        ]

        conn.close()

        return {
            "shipment_id": shipment_id,
            "current_risk_score": current_score,
            "scenarios": scenarios
        }
    except Exception as e:
        logger.error(f"get_what_if_scenarios error: {e}")
        return {"error": str(e)}


# ============================================================================
# TOOL 9: get_historical_patterns
# ============================================================================

async def get_historical_patterns(entity_name: str) -> Dict[str, Any]:
    """Get historical shipment patterns for an entity (shipper or consignee).

    Args:
        entity_name: Shipper or consignee name

    Returns:
        {
            "entity_name": str,
            "total_shipments": int,
            "avg_risk_score": float,
            "monthly_patterns": [{month, shipment_count, avg_value_usd, avg_weight_kg}],
            "commodity_preferences": [{commodity, count, avg_value}],
            "origin_countries": [{"country": str, "count": int, "avg_risk": float}],
            "destination_countries": [{"country": str, "count": int, "avg_risk": float}],
            "risk_trend": str (improving, worsening, stable)
        }
    """
    try:
        conn = _get_conn(PRIMARY_DB)
        cur = conn.cursor()

        # Total shipments for this entity
        cur.execute("""
            SELECT COUNT(*) as cnt, AVG(COALESCE(risk_score, 0)) as avg_risk
            FROM shipments
            WHERE UPPER(shipper_name) = UPPER(?)
            OR UPPER(consignee_name) = UPPER(?)
        """, (entity_name, entity_name))

        entity_stats = cur.fetchone()
        if not entity_stats or entity_stats["cnt"] == 0:
            return {
                "entity_name": entity_name,
                "total_shipments": 0,
                "message": "No shipments found for this entity"
            }

        total_shipments = entity_stats["cnt"]
        avg_risk = entity_stats["avg_risk"] or 0.0

        # Monthly patterns
        cur.execute("""
            SELECT
                strftime('%Y-%m', created_at) as month,
                COUNT(*) as shipment_count,
                AVG(COALESCE(declared_value_usd, 0)) as avg_value,
                AVG(COALESCE(declared_weight_kg, 0)) as avg_weight
            FROM shipments
            WHERE UPPER(shipper_name) = UPPER(?)
            OR UPPER(consignee_name) = UPPER(?)
            GROUP BY month
            ORDER BY month DESC
            LIMIT 12
        """, (entity_name, entity_name))

        monthly = [
            {
                "month": row["month"],
                "shipment_count": row["shipment_count"],
                "avg_value_usd": round(row["avg_value"] or 0.0, 2),
                "avg_weight_kg": round(row["avg_weight"] or 0.0, 2)
            }
            for row in cur.fetchall()
        ]

        # Commodity preferences
        cur.execute("""
            SELECT description, COUNT(*) as cnt, AVG(COALESCE(declared_value_usd, 0)) as avg_val
            FROM shipments
            WHERE (UPPER(shipper_name) = UPPER(?) OR UPPER(consignee_name) = UPPER(?))
            AND description IS NOT NULL
            GROUP BY description
            ORDER BY cnt DESC
            LIMIT 5
        """, (entity_name, entity_name))

        commodities = [
            {
                "commodity": row["description"],
                "count": row["cnt"],
                "avg_value_usd": round(row["avg_val"] or 0.0, 2)
            }
            for row in cur.fetchall()
        ]

        # Origin countries
        cur.execute("""
            SELECT origin_country, COUNT(*) as cnt, AVG(COALESCE(risk_score, 0)) as avg_risk
            FROM shipments
            WHERE (UPPER(shipper_name) = UPPER(?) OR UPPER(consignee_name) = UPPER(?))
            AND origin_country IS NOT NULL
            GROUP BY origin_country
            ORDER BY cnt DESC
        """, (entity_name, entity_name))

        origins = [
            {
                "country": row["origin_country"],
                "count": row["cnt"],
                "avg_risk": round(row["avg_risk"] or 0.0, 2)
            }
            for row in cur.fetchall()
        ]

        # Destination countries
        cur.execute("""
            SELECT destination_country, COUNT(*) as cnt, AVG(COALESCE(risk_score, 0)) as avg_risk
            FROM shipments
            WHERE (UPPER(shipper_name) = UPPER(?) OR UPPER(consignee_name) = UPPER(?))
            AND destination_country IS NOT NULL
            GROUP BY destination_country
            ORDER BY cnt DESC
        """, (entity_name, entity_name))

        destinations = [
            {
                "country": row["destination_country"],
                "count": row["cnt"],
                "avg_risk": round(row["avg_risk"] or 0.0, 2)
            }
            for row in cur.fetchall()
        ]

        conn.close()

        # Risk trend
        if len(monthly) >= 2:
            recent_avg = monthly[0]["shipment_count"]
            older_avg = sum(m["shipment_count"] for m in monthly[1:]) / len(monthly[1:])
            if recent_avg > older_avg * 1.2:
                risk_trend = "worsening"
            elif recent_avg < older_avg * 0.8:
                risk_trend = "improving"
            else:
                risk_trend = "stable"
        else:
            risk_trend = "insufficient_data"

        return {
            "entity_name": entity_name,
            "total_shipments": total_shipments,
            "avg_risk_score": round(avg_risk, 2),
            "monthly_patterns": monthly,
            "commodity_preferences": commodities,
            "origin_countries": origins,
            "destination_countries": destinations,
            "risk_trend": risk_trend
        }
    except Exception as e:
        logger.error(f"get_historical_patterns error: {e}")
        return {"error": str(e)}


# ============================================================================
# TOOL 10: get_referral_summary
# ============================================================================

async def get_referral_summary(shipment_id: str) -> Dict[str, Any]:
    """Get referral package + officer analysis for a shipment.

    Args:
        shipment_id: Shipment ID

    Returns:
        {
            "shipment_id": str,
            "referral_id": str,
            "created_at": str,
            "package_status": str,
            "risk_score": float,
            "risk_level": str,
            "sections_completed": int,
            "sections_total": int,
            "officer_analysis": {
                "analysis_id": str,
                "officer_name": str,
                "badge_number": str,
                "district": str,
                "submitted_at": str,
                "signed_at": str
            },
            "pdf_ready": bool
        }
    """
    try:
        conn = _get_conn(PRIMARY_DB)
        cur = conn.cursor()

        # Get referral package
        cur.execute("""
            SELECT referral_id, created_at, risk_score, risk_level,
                   package_json, final_package_status, pdf_export_ready
            FROM referral_packages
            WHERE shipment_id = ?
            LIMIT 1
        """, (shipment_id,))

        referral = cur.fetchone()
        if not referral:
            return {
                "shipment_id": shipment_id,
                "referral_id": None,
                "message": "No referral package generated yet"
            }

        # Parse package JSON to count sections
        try:
            package_data = json.loads(referral["package_json"] or "{}")
            sections_completed = len([k for k in package_data.keys() if package_data[k]])
            sections_total = 14  # Standard referral has 14 sections
        except:
            sections_completed = 0
            sections_total = 14

        # Get officer analysis
        cur.execute("""
            SELECT analysis_id, officer_name, badge_number, district, submitted_at, signed_at
            FROM officer_analyses
            WHERE referral_id = ?
            ORDER BY submitted_at DESC
            LIMIT 1
        """, (referral["referral_id"],))

        analysis = cur.fetchone()
        officer_analysis = {}
        if analysis:
            officer_analysis = {
                "analysis_id": analysis["analysis_id"],
                "officer_name": analysis["officer_name"],
                "badge_number": analysis["badge_number"],
                "district": analysis["district"],
                "submitted_at": analysis["submitted_at"],
                "signed_at": analysis["signed_at"]
            }

        conn.close()

        return {
            "shipment_id": shipment_id,
            "referral_id": referral["referral_id"],
            "created_at": referral["created_at"],
            "package_status": referral["final_package_status"],
            "risk_score": referral["risk_score"],
            "risk_level": referral["risk_level"],
            "sections_completed": sections_completed,
            "sections_total": sections_total,
            "officer_analysis": officer_analysis,
            "pdf_ready": bool(referral["pdf_export_ready"])
        }
    except Exception as e:
        logger.error(f"get_referral_summary error: {e}")
        return {"error": str(e)}


# ============================================================================
# GEMINI TOOL DEFINITIONS
# ============================================================================

# These define the schema that Gemini uses to understand what each tool does
GEMINI_TOOL_DEFINITIONS = [
    {
        "name": "search_shipments",
        "description": "Search shipments by keyword (shipper, consignee, vessel, country) and risk range. Use this to find relevant cases to investigate.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Keyword search term (company name, vessel, country code)"},
                "risk_min": {"type": "number", "description": "Minimum risk score (0-100), default 0"},
                "risk_max": {"type": "number", "description": "Maximum risk score (0-100), default 100"},
                "limit": {"type": "integer", "description": "Max results (1-50), default 10"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_shipment_risk_breakdown",
        "description": "Get full risk score breakdown for a shipment: H1/H2/H3 scores, component analysis, adjustments, audit trail, and Altana assessment.",
        "parameters": {
            "type": "object",
            "properties": {
                "shipment_id": {"type": "string", "description": "Shipment ID (e.g., 'SHP-001')"}
            },
            "required": ["shipment_id"]
        }
    },
    {
        "name": "investigate_entity",
        "description": "Query CORD 21M-entity database for entity resolution. Find company info, beneficial owners, parent companies, and sanctions status.",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_name": {"type": "string", "description": "Company or person name"},
                "country": {"type": "string", "description": "ISO country code (optional, improves match)"}
            },
            "required": ["entity_name"]
        }
    },
    {
        "name": "get_ownership_chain",
        "description": "Trace beneficial owner chain for an entity. Shows parent companies and shell company flags.",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_name": {"type": "string", "description": "Starting entity name"},
                "depth": {"type": "integer", "description": "Max chain depth (1-5), default 3"}
            },
            "required": ["entity_name"]
        }
    },
    {
        "name": "check_sanctions_screening",
        "description": "Check if an entity is on OFAC SDN list or OpenSanctions. Flags sanctions hits with details.",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_name": {"type": "string", "description": "Entity name"},
                "country": {"type": "string", "description": "ISO country code (optional)"}
            },
            "required": ["entity_name"]
        }
    },
    {
        "name": "get_corridor_risk",
        "description": "Get trade corridor risk profile: AD/CVD rates, enforcement action history, and risk level for a trade route.",
        "parameters": {
            "type": "object",
            "properties": {
                "origin_country": {"type": "string", "description": "Origin ISO country code (e.g., 'CN')"},
                "destination_country": {"type": "string", "description": "Destination ISO country code (e.g., 'US')"}
            },
            "required": ["origin_country", "destination_country"]
        }
    },
    {
        "name": "get_case_statistics",
        "description": "Get aggregate case statistics: total shipments, active cases, risk distribution, top corridors and shippers.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_what_if_scenarios",
        "description": "Get risk scenario analysis for a shipment. Shows 'what if X becomes true' scenarios and impact on risk score.",
        "parameters": {
            "type": "object",
            "properties": {
                "shipment_id": {"type": "string", "description": "Shipment ID"}
            },
            "required": ["shipment_id"]
        }
    },
    {
        "name": "get_historical_patterns",
        "description": "Get historical shipment patterns for an entity (shipper or consignee). Shows trends, commodities, corridors, and risk patterns.",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_name": {"type": "string", "description": "Shipper or consignee name"}
            },
            "required": ["entity_name"]
        }
    },
    {
        "name": "get_referral_summary",
        "description": "Get referral package status and officer analysis for a shipment. Shows completion status and officer sign-off.",
        "parameters": {
            "type": "object",
            "properties": {
                "shipment_id": {"type": "string", "description": "Shipment ID"}
            },
            "required": ["shipment_id"]
        }
    }
]

# Mapping of tool names to functions for execution
TOOL_REGISTRY = {
    "search_shipments": search_shipments,
    "get_shipment_risk_breakdown": get_shipment_risk_breakdown,
    "investigate_entity": investigate_entity,
    "get_ownership_chain": get_ownership_chain,
    "check_sanctions_screening": check_sanctions_screening,
    "get_corridor_risk": get_corridor_risk,
    "get_case_statistics": get_case_statistics,
    "get_what_if_scenarios": get_what_if_scenarios,
    "get_historical_patterns": get_historical_patterns,
    "get_referral_summary": get_referral_summary
}
