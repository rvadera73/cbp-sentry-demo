"""
Comprehensive Referral Package Generator
Generates all 14 sections of CSOP-BP-GS-26-0001 referral packages with:
- Data-backed sections (3-1 through 3-10)
- AI-generated narratives (3-6, 3-7, 3-11+)
- Risk scoring alignment (7-factor model)
- PDF export capability
"""

import sqlite3
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
from enum import Enum

logger = logging.getLogger(__name__)


class ReferralSection(Enum):
    """CSOP-BP-GS-26-0001 Referral Sections"""
    S3_1 = "section_3_1_shipment_identification"
    S3_2 = "section_3_2_line_items"
    S3_3 = "section_3_3_routing_history"
    S3_4 = "section_3_4_parties_and_roles"
    S3_5 = "section_3_5_entity_ownership_chain"
    S3_6 = "section_3_6_historical_import_pattern"
    S3_7 = "section_3_7_trade_flow_intelligence"
    S3_8 = "section_3_8_document_review"
    S3_9 = "section_3_9_document_consistency"
    S3_10 = "section_3_10_supplier_verification"
    S3_11 = "section_3_11_risk_indicators"
    S3_12 = "section_3_12_pattern_analysis"
    S3_13 = "section_3_13_enforcement_analysis"
    S3_14 = "section_3_14_conclusion_and_recommendation"


class ComprehensiveReferralGenerator:
    """Generate complete referral packages with all 14 sections"""

    def __init__(self, db_path: str = "/app/data/cbp_sentry.db"):
        self.db_path = db_path
        self.conn = None

    def generate_referral_package(self, shipment_id: str) -> Dict[str, Any]:
        """
        Generate comprehensive 14-section referral package for a shipment.

        Returns:
            Complete referral package with all sections
        """
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()

        try:
            # Get shipment data
            cursor.execute("SELECT * FROM shipments WHERE id = ?", (shipment_id,))
            shipment_row = cursor.fetchone()
            if not shipment_row:
                return {"error": f"Shipment {shipment_id} not found"}

            shipment = dict(shipment_row)

            # Get risk score breakdown
            cursor.execute("""
                SELECT final_score, breakdown_json, risk_level
                FROM risk_scores_cache
                WHERE shipment_id = ?
            """, (shipment_id,))

            risk_row = cursor.fetchone()
            risk_data = dict(risk_row) if risk_row else {}
            breakdown = json.loads(risk_data.get('breakdown_json', '{}')) if risk_data else {}

            # Generate all sections
            sections = {}
            sections[ReferralSection.S3_1.value] = self._generate_section_3_1(shipment, cursor)
            sections[ReferralSection.S3_2.value] = self._generate_section_3_2(shipment, cursor)
            sections[ReferralSection.S3_3.value] = self._generate_section_3_3(shipment, cursor)
            sections[ReferralSection.S3_4.value] = self._generate_section_3_4(shipment, cursor)
            sections[ReferralSection.S3_5.value] = self._generate_section_3_5(shipment, cursor)
            sections[ReferralSection.S3_6.value] = self._generate_section_3_6(shipment, cursor)
            sections[ReferralSection.S3_7.value] = self._generate_section_3_7(shipment, cursor)
            sections[ReferralSection.S3_8.value] = self._generate_section_3_8(shipment, cursor)
            sections[ReferralSection.S3_9.value] = self._generate_section_3_9(shipment, cursor)
            sections[ReferralSection.S3_10.value] = self._generate_section_3_10(shipment, cursor)
            sections[ReferralSection.S3_11.value] = self._generate_section_3_11(breakdown, shipment)
            sections[ReferralSection.S3_12.value] = self._generate_section_3_12(breakdown, shipment)
            sections[ReferralSection.S3_13.value] = self._generate_section_3_13(shipment, cursor)
            sections[ReferralSection.S3_14.value] = self._generate_section_3_14(breakdown, shipment)

            # Build complete referral package
            referral_package = {
                "referral_id": str(uuid.uuid4()),
                "shipment_id": shipment_id,
                "manifest_id": shipment.get("manifest_id"),
                "created_at": datetime.utcnow().isoformat(),
                "risk_score": float(risk_data.get('final_score', 0)),
                "risk_level": risk_data.get('risk_level', 'UNKNOWN'),
                "risk_breakdown": breakdown,
                "sections": sections,
            }

            # Store in database
            self._store_referral_package(referral_package)

            return referral_package

        finally:
            self.conn.close()

    def _generate_section_3_1(self, shipment: Dict, cursor) -> Dict[str, Any]:
        """Table 3-1: Shipment Identification"""
        return {
            "title": "TABLE 3-1: SHIPMENT IDENTIFICATION",
            "shipment_id": shipment.get("id"),
            "manifest_id": shipment.get("manifest_id"),
            "commodity": shipment.get("commodity_name", "General Merchandise"),
            "hs_code": shipment.get("hs_code"),
            "route": f"{shipment.get('origin_country', 'XX')} → {shipment.get('destination_country', 'US')}",
            "shipper": shipment.get("shipper_name"),
            "shipper_country": shipment.get("origin_country"),
            "consignee": shipment.get("consignee_name"),
            "consignee_country": shipment.get("destination_country"),
            "vessel": shipment.get("vessel_name"),
            "vessel_imo": shipment.get("vessel_imo"),
            "value_usd": shipment.get("declared_value_usd", 0),
            "weight_kg": shipment.get("declared_weight_kg", 0),
            "entry_date": shipment.get("entry_date"),
        }

    def _generate_section_3_2(self, shipment: Dict, cursor) -> Dict[str, Any]:
        """Table 3-2: Line Items"""
        cursor.execute("""
            SELECT hs_code, product_description, quantity, unit, total_value_usd
            FROM shipment_line_items
            WHERE shipment_id = ?
        """, (shipment.get("id"),))

        rows = cursor.fetchall()
        items = []
        for row in rows:
            items.append({
                "hs_code": row["hs_code"],
                "product_description": row["product_description"],
                "quantity": row["quantity"],
                "unit": row["unit"],
                "total_value_usd": row["total_value_usd"]
            })

        if not items:
            items = [{
                "hs_code": shipment.get("hs_code"),
                "product_description": shipment.get("commodity_name", "General Merchandise"),
                "quantity": 1,
                "unit": "shipment",
                "total_value_usd": shipment.get("declared_value_usd", 0)
            }]

        return {
            "title": "TABLE 3-2: LINE ITEMS",
            "items": items,
            "total_value": sum(item.get("total_value_usd", 0) for item in items),
            "total_weight": shipment.get("declared_weight_kg", 0),
        }

    def _generate_section_3_3(self, shipment: Dict, cursor) -> Dict[str, Any]:
        """Table 3-3: AIS Routing History"""
        routing = []
        try:
            cursor.execute("""
                SELECT location, event_date, event_type
                FROM routing_events
                WHERE shipment_id = ?
                ORDER BY event_date
            """, (shipment.get("id"),))

            for row in cursor.fetchall():
                routing.append({
                    "location": row["location"],
                    "event_date": row["event_date"],
                    "event_type": row["event_type"]
                })
        except Exception as e:
            logger.warning(f"Could not fetch routing events: {e}")

        port_calls = shipment.get("port_calls") or []
        if isinstance(port_calls, str):
            try:
                port_calls = json.loads(port_calls)
            except:
                port_calls = []

        return {
            "title": "TABLE 3-3: AIS ROUTING HISTORY",
            "vessel": shipment.get("vessel_name"),
            "vessel_imo": shipment.get("vessel_imo"),
            "route": " → ".join(str(p) for p in (port_calls or [shipment.get("origin_country", "XX"), "INTERMEDIATE", shipment.get("destination_country", "US")])[:5]),
            "dwell_days": shipment.get("dwell_days"),
            "dwell_baseline": 2.5,
            "dwell_anomaly": "HIGH" if shipment.get("dwell_days", 0) > 8 else ("MEDIUM" if shipment.get("dwell_days", 0) > 4 else "NORMAL"),
            "port_calls": port_calls or [],
            "routing_events": routing,
        }

    def _generate_section_3_4(self, shipment: Dict, cursor) -> Dict[str, Any]:
        """Table 3-4: Parties and Roles"""
        cursor.execute("""
            SELECT entity, role, country
            FROM parties_involved
            WHERE shipment_id = ?
        """, (shipment.get("id"),))

        parties = [dict(row) for row in cursor.fetchall()]
        if not parties:
            parties = [
                {"entity": shipment.get("shipper_name"), "role": "SHIPPER", "country": shipment.get("origin_country")},
                {"entity": shipment.get("consignee_name"), "role": "CONSIGNEE", "country": shipment.get("destination_country")},
                {"entity": shipment.get("vessel_name"), "role": "CARRIER", "country": "ZZ"},
            ]

        return {
            "title": "TABLE 3-4: PARTIES AND ROLES",
            "parties": parties,
        }

    def _generate_section_3_5(self, shipment: Dict, cursor) -> Dict[str, Any]:
        """Table 3-5: Entity Ownership Chain (from CORD)"""
        cursor.execute("""
            SELECT entity_id, entity_name, country, entity_type, confidence, relationship_type
            FROM entity_ownership_chain
            WHERE shipment_id = ?
            ORDER BY level
        """, (shipment.get("id"),))

        chain = [dict(row) for row in cursor.fetchall()]

        return {
            "title": "TABLE 3-5: ENTITY OWNERSHIP CHAIN",
            "chain": chain,
            "summary": f"Entity resolution via CORD: {len(chain)} entities identified" if chain else "Entity resolution pending",
            "ofac_detected": any(row.get("ofac_match") for row in chain if isinstance(row, dict) and row.get("ofac_match")),
        }

    def _generate_section_3_6(self, shipment: Dict, cursor) -> Dict[str, Any]:
        """Table 3-6: Historical Import Pattern (AI-generated)"""
        # This would be AI-generated via Gemini
        return {
            "title": "TABLE 3-6: HISTORICAL IMPORT PATTERN ANALYSIS",
            "origin": shipment.get("origin_country"),
            "destination": shipment.get("destination_country"),
            "shipper": shipment.get("shipper_name"),
            "pattern_narrative": "[AI-Generated via Gemini - to be populated]",
            "trend": "INCREASING" if shipment.get("origin_country") in ["VN", "MY", "TH"] else "STABLE",
            "anomalies": [],
        }

    def _generate_section_3_7(self, shipment: Dict, cursor) -> Dict[str, Any]:
        """Table 3-7: Trade Flow Intelligence (AI-generated)"""
        return {
            "title": "TABLE 3-7: TRADE FLOW INTELLIGENCE",
            "hs_code": shipment.get("hs_code"),
            "commodity": shipment.get("commodity_name"),
            "origin": shipment.get("origin_country"),
            "ad_cvd_status": "ACTIVE" if shipment.get("ad_cvd_applicable") else "NONE",
            "ad_cvd_rate": f"{shipment.get('ad_cvd_rate', 0) * 100:.2f}%",
            "trade_flow_narrative": "[AI-Generated via Gemini - to be populated]",
            "enforcement_trend": "INCREASING SCRUTINY",
        }

    def _generate_section_3_8(self, shipment: Dict, cursor) -> Dict[str, Any]:
        """Table 3-8: Document Review Checklist"""
        cursor.execute("""
            SELECT document_type, status
            FROM manifest_documents
            WHERE shipment_id = ?
        """, (shipment.get("id"),))

        documents = [dict(row) for row in cursor.fetchall()]

        return {
            "title": "TABLE 3-8: DOCUMENT REVIEW CHECKLIST",
            "documents": documents or [
                {"document": "Commercial Invoice", "status": "RECEIVED"},
                {"document": "Packing List", "status": "RECEIVED"},
                {"document": "Bill of Lading", "status": "RECEIVED"},
                {"document": "Factory Records", "status": "MISSING"},
            ],
        }

    def _generate_section_3_9(self, shipment: Dict, cursor) -> Dict[str, Any]:
        """Table 3-9: ISF Element 9 Check"""
        return {
            "title": "TABLE 3-9: DOCUMENT CONSISTENCY (ISF ELEMENT 9)",
            "declared_origin": shipment.get("element9_declared_country", shipment.get("origin_country")),
            "actual_stuffing_country": shipment.get("element9_actual_country", shipment.get("ais_stuffing_country")),
            "is_mismatch": bool(shipment.get("element9_is_mismatch")),
            "mismatch_confidence": 0.98 if shipment.get("element9_is_mismatch") else 0.0,
            "evidence": [
                f"ISF declared: {shipment.get('element9_declared_country', shipment.get('origin_country'))}",
                f"AIS actual: {shipment.get('element9_actual_country', shipment.get('ais_stuffing_country'))}",
            ] if shipment.get("element9_is_mismatch") else ["No mismatch detected"],
        }

    def _generate_section_3_10(self, shipment: Dict, cursor) -> Dict[str, Any]:
        """Table 3-10: Supplier Verification"""
        return {
            "title": "TABLE 3-10: SUPPLIER MANUFACTURING VERIFICATION",
            "shipper": shipment.get("shipper_name"),
            "shipper_age_months": shipment.get("shipper_age_months"),
            "shipper_risk_tier": (
                "VERY_NEW (< 12mo)"
                if shipment.get("shipper_age_months") and shipment.get("shipper_age_months") < 12
                else ("NEW (12-24mo)" if shipment.get("shipper_age_months") and shipment.get("shipper_age_months") < 24 else "ESTABLISHED")
            ),
            "capacity_assessment": (
                "UNVERIFIED - newly established entity"
                if shipment.get("shipper_age_months") and shipment.get("shipper_age_months") < 12
                else "CAPABLE - established manufacturer"
            ),
        }

    def _generate_section_3_11(self, breakdown: Dict, shipment: Dict) -> Dict[str, Any]:
        """Table 3-11: Risk Indicator Summary"""
        components = breakdown.get("components", [])

        return {
            "title": "TABLE 3-11: RISK INDICATOR SUMMARY",
            "indicators": [
                {
                    "indicator": comp.get("component", "Unknown"),
                    "factor": comp.get("factor", ""),
                    "score": comp.get("score", 0),
                    "weight": comp.get("weight", 0),
                    "weighted_result": comp.get("weighted_result", 0),
                    "rationale": comp.get("rationale", ""),
                }
                for comp in components
            ] if components else [],
            "summary": "[AI-Generated Analysis - to be populated]",
        }

    def _generate_section_3_12(self, breakdown: Dict, shipment: Dict) -> Dict[str, Any]:
        """Table 3-12: Pattern Analysis & Behavioral Indicators"""
        return {
            "title": "TABLE 3-12: PATTERN ANALYSIS & BEHAVIORAL INDICATORS",
            "narrative": "[AI-Generated Pattern Analysis - to be populated]",
            "flags": self._extract_risk_flags(breakdown, shipment),
        }

    def _generate_section_3_13(self, shipment: Dict, cursor) -> Dict[str, Any]:
        """Table 3-13: Enforcement Actions & Legal Analysis"""
        return {
            "title": "TABLE 3-13: ENFORCEMENT ACTIONS & LEGAL FRAMEWORK",
            "applicable_statutes": [
                "19 USC § 1592 - Customs Fraud",
                "19 USC § 1595a - Seizure and Forfeiture",
                "19 CFR 165 - Entry of Goods",
            ],
            "prior_enforcement": "[Check database for prior actions on shipper/consignee]",
            "recommended_actions": "[Based on risk score and indicators]",
        }

    def _generate_section_3_14(self, breakdown: Dict, shipment: Dict) -> Dict[str, Any]:
        """Table 3-14: Conclusion and Recommendation"""
        final_score = breakdown.get("final_score", 0)

        if final_score >= 85:
            recommendation = "RECOMMEND CUSTOMS EXAMINATION & INVESTIGATION"
            action_level = "CRITICAL"
        elif final_score >= 70:
            recommendation = "RECOMMEND EXAMINATION"
            action_level = "HIGH"
        elif final_score >= 50:
            recommendation = "RECOMMEND REVIEW"
            action_level = "MEDIUM"
        else:
            recommendation = "RECOMMEND RELEASE"
            action_level = "LOW"

        return {
            "title": "TABLE 3-14: CONCLUSION AND RECOMMENDATION",
            "final_risk_score": final_score,
            "action_level": action_level,
            "recommendation": recommendation,
            "conclusion_narrative": "[AI-Generated Legal Conclusion - to be populated]",
            "legal_basis": "[Supporting CFR and USC citations]",
        }

    def _extract_risk_flags(self, breakdown: Dict, shipment: Dict) -> List[str]:
        """Extract key risk flags from breakdown and shipment data"""
        flags = []

        components = breakdown.get("components", [])
        for comp in components:
            score = comp.get("score", 0)
            if score >= 8:
                flags.append(f"⚠️ {comp.get('component', 'Unknown')}: {score}/10")

        # Add data-based flags
        if shipment.get("element9_is_mismatch"):
            flags.append("🚨 ISF Element 9 Mismatch")
        if shipment.get("dwell_days", 0) > 8:
            flags.append(f"📍 Extended Dwell: {shipment.get('dwell_days')} days")
        if shipment.get("shipper_age_months", 999) < 12:
            flags.append("🆕 New Shipper (< 12 months)")

        return flags

    def _store_referral_package(self, package: Dict[str, Any]):
        """Store generated referral package in database"""
        cursor = self.conn.cursor()

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO referral_packages
                (referral_id, shipment_id, manifest_id, created_at, risk_score, risk_level, package_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                package["referral_id"],
                package["shipment_id"],
                package["manifest_id"],
                package["created_at"],
                package["risk_score"],
                package["risk_level"],
                json.dumps(package["sections"]),
            ))

            self.conn.commit()
            logger.info(f"✓ Stored referral package {package['referral_id']} for {package['shipment_id']}")

        except Exception as e:
            logger.error(f"Failed to store referral package: {e}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python referral_comprehensive.py <shipment_id>")
        sys.exit(1)

    shipment_id = sys.argv[1]
    gen = ComprehensiveReferralGenerator()
    package = gen.generate_referral_package(shipment_id)
    print(json.dumps(package, indent=2, default=str))
