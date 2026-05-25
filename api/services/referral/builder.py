"""
⚠️ DEPRECATED: Referral package builder service.

This module builds packages from FIXTURE DATA only.

For production use, implement Option 3:
- Call CORD microservice at http://sentry-cord-integration:8004
- Fetch entity resolution directly via CORDClient (api/services/referral/cord_client.py)
- Use EntityGraphService to transform data (api/services/referral/entity_graph_service.py)

Will be replaced in v2.0 (target: Q3 2026).
See ENTITY_GRAPH_OPTION3_STRATEGY.md for migration details.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ReferralPackageBuilder:
    """
    ⚠️ DEPRECATED: Builds referral packages from FIXTURE DATA.

    This builder uses static fixture data and is being replaced by Option 3:
    - CORDClient: Direct calls to CORD microservice
    - EntityGraphService: Transform CORD responses to Entity[] format

    Current limitations:
    - ❌ No real entity resolution (uses hardcoded demo data)
    - ❌ Missing entity_type, entity_id, relationships[]
    - ❌ No ISF enrichment integration
    - ❌ No OFAC status per entity

    Combines (FIXTURE ONLY):
    - Static manifest data (hardcoded)
    - Hardcoded entity resolution (demo data)
    - Mock ML scoring (fixed values)
    - Static document analysis (templates)

    Scheduled removal: v2.0 (Q3 2026)
    Migration: Use CORDClient + EntityGraphService instead
    """

    def build_package(
        self,
        manifest_id: str,
        manifest_data: Dict[str, Any],
        entities: Dict[str, Any],
        score_breakdown: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Build a complete referral package from constituent parts.

        Args:
            manifest_id: Manifest identifier
            manifest_data: Raw manifest data
            entities: Entity resolution results
            score_breakdown: ML scoring breakdown

        Returns:
            Complete referral package dict with all 14 tables
        """

        # Generate package ID
        package_id = self._generate_package_id()
        shipment_id = f"SHP-{manifest_id.split('-')[-1]}" if "-" in manifest_id else manifest_id

        # Extract score and confidence
        score = score_breakdown.get("total", 0)
        confidence_tier = score_breakdown.get("confidence_tier", "MEDIUM")

        # Determine recommended action based on score
        recommended_action = self._determine_action(score)

        # Build all 14 sections
        sections = {
            "shipment_id": self._build_shipment_id(manifest_data),
            "line_items": self._build_line_items(manifest_data),
            "routing_history": self._build_routing_history(manifest_data),
            "parties": self._build_parties(entities),
            "ownership_chain": self._build_ownership_chain(entities),
            "import_pattern": self._build_import_pattern(manifest_data),
            "trade_flow": self._build_trade_flow(manifest_data),
            "document_review": self._build_document_review(manifest_data),
            "document_consistency": self._build_document_consistency(manifest_data),
            "manufacturing_verification": self._build_manufacturing_verification(entities),
            "risk_indicators": self._build_risk_indicators(manifest_data, entities, score_breakdown),
            "score_breakdown": score_breakdown,
            "what_if_scenarios": self._build_what_if_scenarios(score),
            "data_sources": self._build_data_sources(),
        }

        return {
            "package_id": package_id,
            "shipment_id": shipment_id,
            "confidence_level": confidence_tier,
            "score": score,
            "recommended_action": recommended_action,
            "sections": sections,
        }

    def _generate_package_id(self) -> str:
        """Generate unique package ID"""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"SENTRY-{timestamp}"

    def _determine_action(self, score: int) -> str:
        """
        Determine recommended action based on score.

        Score ranges:
        - >= 80: EXAMINE_ON_ARRIVAL
        - 60-79: HOLD_FOR_INVESTIGATION
        - 40-59: AUDIT
        - < 40: CLEAR
        """
        if score >= 80:
            return "EXAMINE_ON_ARRIVAL"
        elif score >= 60:
            return "HOLD_FOR_INVESTIGATION"
        elif score >= 40:
            return "AUDIT"
        else:
            return "CLEAR"

    def _build_shipment_id(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """Build Table 3-1: Shipment Identification"""
        return {
            "bill_id": manifest.get("bill_id", "UNKNOWN"),
            "manifest_id": manifest.get("manifest_id", "UNKNOWN"),
            "shipper": manifest.get("shipper", ""),
            "shipper_country": manifest.get("shipper_country", ""),
            "consignee": manifest.get("consignee", ""),
            "consignee_country": manifest.get("consignee_country", ""),
            "hts_code": manifest.get("hts_code", ""),
            "hts_description": manifest.get("description", ""),
            "declared_value_usd": manifest.get("declared_value_usd", 0),
            "total_weight_kg": manifest.get("weight_kg", 0),
            "weight_mt": manifest.get("weight_mt", 0),
            "vessel_name": manifest.get("vessel_name", ""),
            "port_of_lading": manifest.get("port_of_lading", ""),
            "port_of_discharge": manifest.get("port_of_discharge", ""),
            "eta": manifest.get("eta", datetime.utcnow().isoformat() + "Z"),
        }

    def _build_line_items(self, manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build Table 3-2: Line Items"""
        # For now, single line item for entire shipment
        hts_code = manifest.get("hts_code", "")
        weight_kg = manifest.get("weight_kg", 0)
        weight_mt = weight_kg / 1000 if weight_kg > 0 else 0
        declared_value = manifest.get("declared_value_usd", 0)
        duty_rate = manifest.get("hts_duty_rate_pct", 0) / 100
        estimated_duty = declared_value * duty_rate

        return [
            {
                "sku": f"SKU-{hts_code[:4]}",
                "description": manifest.get("description", ""),
                "quantity_kg": weight_kg,
                "hts_code": hts_code,
                "weight_mt": weight_mt,
                "declared_value_usd": declared_value,
                "duty_rate": duty_rate,
                "estimated_duty_usd": round(estimated_duty, 2),
            }
        ]

    def _build_routing_history(self, manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build Table 3-3: Routing History"""
        routing = []

        # Stuffing location (AIS anomaly check)
        if manifest.get("port_of_lading"):
            routing.append({
                "location": "Nansha Terminal, Guangzhou",  # From fixture
                "country": manifest.get("isf_stuffing_country", "CN"),
                "date": "2026-04-12",
                "event": "Stuffed",
                "ais_anomaly": manifest.get("ais_anomaly_ratio", 1) > 2,
                "dwell_days": manifest.get("ais_dwell_days"),
                "baseline_days": manifest.get("ais_dwell_baseline"),
                "anomaly_ratio": manifest.get("ais_anomaly_ratio"),
            })

        return routing

    def _build_parties(self, entities: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build Table 3-4: Parties"""
        parties = []

        if "shipper_vn" in entities:
            shipper = entities["shipper_vn"]
            parties.append({
                "role": "Shipper",
                "name": shipper.get("entity_name", ""),
                "country": shipper.get("country", ""),
                "senzing_id": shipper.get("senzing_entity_id", 0),
                "risk_score": shipper.get("risk_score", 0),
                "confidence": shipper.get("match_confidence", 0),
            })

        if "consignee_us" in entities:
            consignee = entities["consignee_us"]
            parties.append({
                "role": "Consignee",
                "name": consignee.get("entity_name", ""),
                "country": consignee.get("country", ""),
                "senzing_id": consignee.get("senzing_entity_id", 0),
                "risk_score": consignee.get("risk_score", 0),
                "confidence": consignee.get("match_confidence", 0),
            })

        if "parent_cn" in entities:
            manufacturer = entities["parent_cn"]
            parties.append({
                "role": "True Manufacturer",
                "name": manufacturer.get("entity_name", ""),
                "country": manufacturer.get("country", ""),
                "senzing_id": manufacturer.get("senzing_entity_id", 0),
                "risk_score": manufacturer.get("risk_score", 0),
                "confidence": manufacturer.get("match_confidence", 0),
            })

        return parties

    def _build_ownership_chain(self, entities: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build Table 3-5: Entity Ownership Chain"""
        # Build VN -> HK -> CN linkage
        chain = []

        levels = [
            ("shipper_vn", 1, "Root shipper"),
            ("parent_hk", 2, "SPV holding company" if "parent_hk" in entities else None),
            ("parent_cn", 3, "Primary manufacturer"),
        ]

        level = 1
        for entity_key, _, relationship in levels:
            if entity_key in entities:
                entity = entities[entity_key]
                chain.append({
                    "level": level,
                    "entity": entity.get("entity_name", ""),
                    "jurisdiction": entity.get("country", ""),
                    "relationship": relationship,
                    "confidence": entity.get("match_confidence", 0),
                })
                level += 1

        return chain

    def _build_import_pattern(self, manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build Table 3-6: Import Pattern (6-month history)"""
        # Mock 6-month history showing origin shift
        return [
            {
                "month": "2025-11",
                "shipments": 1,
                "weight_kg": 18500,
                "declared_origin": "MY",
                "unit_value": 2.15,
            },
            {
                "month": "2025-12",
                "shipments": 2,
                "weight_kg": 41200,
                "declared_origin": "TH",
                "unit_value": 2.22,
            },
            {
                "month": "2026-01",
                "shipments": 2,
                "weight_kg": 39800,
                "declared_origin": "VN",
                "unit_value": 2.35,
            },
            {
                "month": "2026-02",
                "shipments": 3,
                "weight_kg": 62900,
                "declared_origin": "VN",
                "unit_value": 2.41,
            },
            {
                "month": "2026-03",
                "shipments": 4,
                "weight_kg": 88100,
                "declared_origin": "VN",
                "unit_value": 2.37,
            },
            {
                "month": "2026-04",
                "shipments": 1,
                "weight_kg": manifest.get("weight_kg", 26200),
                "declared_origin": manifest.get("country_of_origin", "VN"),
                "unit_value": manifest.get("price_declared_per_unit", 2.48),
            },
        ]

    def _build_trade_flow(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """Build Table 3-7: Trade Flow Context"""
        duty_rate = manifest.get("hts_duty_rate_pct", 0)

        return {
            "hts_code": manifest.get("hts_code", ""),
            "ad_cvd_status": manifest.get("ad_cvd_status", "UNKNOWN"),
            "china_rate": duty_rate / 100,
            "vietnam_rate": 0.425,  # Typical Vietnam duty rate
            "duty_evasion_incentive": "HIGH" if duty_rate > 100 else "MEDIUM",
            "trade_corridor_risk": "HIGH",
        }

    def _build_document_review(self, manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build Table 3-8: Document Review"""
        return [
            {
                "type": "Bill of Lading",
                "filed_date": "2026-04-14",
                "shipper_declared": manifest.get("shipper", ""),
            },
            {
                "type": "Commercial Invoice",
                "filed_date": "2026-04-14",
                "origin_declared": manifest.get("country_of_origin", ""),
            },
            {
                "type": "ISF Filing",
                "filed_date": "2026-05-23",
                "element_9": manifest.get("isf_stuffing_country", ""),
                "status": "MISMATCH" if manifest.get("isf_stuffing_country") != manifest.get("declared_coo") else "OK",
            },
        ]

    def _build_document_consistency(self, manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build Table 3-9: Document Consistency Issues"""
        issues = []

        # ISF/COO mismatch
        if manifest.get("isf_stuffing_country") != manifest.get("declared_coo"):
            issues.append({
                "issue": "ISF Element 9 vs manifests",
                "type": "CRITICAL",
                "evidence": f"ISF filed: {manifest.get('isf_stuffing_country')} | Manifests declare: {manifest.get('declared_coo')}",
            })

        # Price anomaly
        declared_price = manifest.get("price_declared_per_unit", 0)
        market_price = manifest.get("market_price_per_unit", 0)
        if declared_price > 0 and market_price > 0 and declared_price < market_price * 0.95:
            issues.append({
                "issue": "Price below market",
                "type": "HIGH",
                "evidence": f"Declared ${declared_price:.2f} vs market ${market_price:.2f}",
            })

        # Shipper age (new entity)
        if manifest.get("shipper_incorporation_date"):
            from datetime import datetime
            incorporation_date = datetime.fromisoformat(manifest.get("shipper_incorporation_date"))
            age_months = (datetime.utcnow() - incorporation_date).days / 30
            if age_months < 24:
                issues.append({
                    "issue": "Shipper very new",
                    "type": "HIGH",
                    "evidence": f"Incorporated {incorporation_date.year}, only {int(age_months)} months old",
                })

        return issues

    def _build_manufacturing_verification(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Build Table 3-10: Manufacturing Verification"""
        mfg = entities.get("parent_cn", {})

        return {
            "true_manufacturer": mfg.get("entity_name", ""),
            "factory_location": "Foshan, Guangdong, China",
            "facility_confirmed": False,
            "production_records": "Not provided",
            "certificates": "Not provided",
            "prior_filings": mfg.get("attributes", {}).get("prior_filings", 0),
        }

    def _build_risk_indicators(
        self,
        manifest: Dict[str, Any],
        entities: Dict[str, Any],
        score_breakdown: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Build Table 3-11: Risk Indicators"""
        indicators = []

        # Extract indicators from score breakdown components
        for component in score_breakdown.get("components", []):
            if component.get("tier") >= 3:  # Only high-tier components
                indicator_name = self._component_to_indicator(component.get("name", ""))
                if indicator_name:
                    indicators.append({
                        "indicator": indicator_name,
                        "severity": "CRITICAL" if component.get("score") > 20 else "HIGH",
                        "evidence": component.get("description", ""),
                        "confidence": 0.85 + (component.get("score") / component.get("max", 1) * 0.14),
                    })

        return indicators

    def _component_to_indicator(self, component_name: str) -> Optional[str]:
        """Convert score component to risk indicator name"""
        mapping = {
            "origin_doc_gap": "ISF/COO mismatch",
            "commodity_sensitivity": "AD/CVD incentive",
            "routing_consistency": "AIS dwell anomaly",
            "party_profile_risk": "Entity linkage to China parent",
            "historical_pattern": "Origin shift pattern",
            "time_sensitivity": "Time-critical window",
        }
        return mapping.get(component_name)

    def _build_what_if_scenarios(self, score: int) -> List[Dict[str, Any]]:
        """Build Table 3-13: What-If Scenarios"""
        return [
            {
                "scenario": "Legitimate Vietnamese aluminum",
                "assumption": "Shipper owns factory in Vietnam",
                "expected_score": 22,
                "key_differences": "No China linkage, factory records provided",
            },
            {
                "scenario": "Legitimate transshipment",
                "assumption": "ISF Element 9 China filed correctly",
                "expected_score": 35,
                "key_differences": "COO still Vietnam, no shipper-parent linkage",
            },
            {
                "scenario": "Chinese goods, Vietnam label only",
                "assumption": "Only shipper changed, no value-add",
                "expected_score": 98,
                "key_differences": "All red flags present, strongest fraud signal",
            },
        ]

    def _build_data_sources(self) -> List[Dict[str, Any]]:
        """Build Table 3-14: Data Sources"""
        return [
            {
                "name": "CBP Manifest Filing",
                "confidence": 0.95,
                "data_element": "Shipper, consignee, HTS, value",
            },
            {
                "name": "ISF Data Element 9",
                "confidence": 0.99,
                "data_element": "Container stuffing location",
            },
            {
                "name": "AIS vessel tracking",
                "confidence": 0.92,
                "data_element": "Port dwell times, routing",
            },
            {
                "name": "Senzing entity resolution",
                "confidence": 0.98,
                "data_element": "Entity linkage, relationships",
            },
            {
                "name": "AD/CVD Proceedings",
                "confidence": 0.99,
                "data_element": "Tariff rates, duty incentives",
            },
            {
                "name": "Corporate Registry (Vietnam)",
                "confidence": 0.94,
                "data_element": "Shipper registration, director",
            },
            {
                "name": "Corporate Registry (Hong Kong)",
                "confidence": 0.91,
                "data_element": "Holding company structure",
            },
            {
                "name": "Corporate Registry (China SAMR)",
                "confidence": 0.98,
                "data_element": "Manufacturer details, filings",
            },
            {
                "name": "Trade History (Panjiva)",
                "confidence": 0.87,
                "data_element": "Prior shipment patterns",
            },
        ]
