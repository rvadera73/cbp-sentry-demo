"""
Comprehensive Referral Package Generator v2 - Robust Schema Handling

Generates all 14 sections of CSOP-BP-GS-26-0001 referral packages with graceful
fallbacks for missing tables or columns. Integrates with CORD for entity resolution.
"""

import sqlite3
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import httpx
import os

logger = logging.getLogger(__name__)


class ComprehensiveReferralGenerator:
    """Generate complete referral packages with robust schema handling"""

    def __init__(self, db_path: str = "/app/data/cbp_sentry.db", cord_url: str = None):
        self.db_path = db_path
        self.cord_url = cord_url or os.getenv("CORD_SERVICE_URL", "http://sentry-cord-integration:8004")

    # ------------------------------------------------------------------
    # Track T-Experience (F1/F4/F6) — referral entity-resolution evidence
    # ------------------------------------------------------------------
    def _enrich_entity_flags(self, name: str, country: str = None) -> Dict[str, Any]:
        """Build an entity_scorer-ready dict for a party, enriched with the live
        CORD enforcement flags (EAPA respondent / UFLPA listing). Never raises.

        The returned dict mirrors the CORD entity record shape entity_scorer
        keys on: ``data_source`` + ``flag`` drive the EAPA/UFLPA components, and
        ``raw_data.DOCKET`` carries the EAPA docket if reachable.
        """
        name = (name or "").strip()
        entity: Dict[str, Any] = {
            "name": name,
            "entity_id": name or "unknown-entity",
            "country": (country or "").strip(),
            "data_source": "",
            "flag": "",
            "raw_data": {},
        }
        if not name or name.lower() == "unknown":
            return entity

        eapa_docket = None
        try:
            from cord_engine import get_cord_engine

            engine = get_cord_engine()
            if engine.is_eapa_respondent(name):
                # EAPA is the anchor enforcement flag (F4). data_source==CBP-EAPA
                # is what entity_scorer keys on for the EAPA component.
                entity["data_source"] = "CBP-EAPA"
                entity["flag"] = "eapa_respondent"
                eapa_docket = self._eapa_docket_for(engine, name)
                if eapa_docket:
                    entity["raw_data"]["DOCKET"] = eapa_docket
            elif engine.is_uflpa_listed(name):
                entity["data_source"] = "UFLPA-ENTITY-LIST"
                entity["flag"] = "uflpa_listed"
        except Exception as e:
            logger.warning(f"Entity flag enrichment unavailable for '{name}': {e}")

        # Surface OFAC via the SDN index too (sets SDN_PROGRAM so the scorer's
        # OFAC component fires even when EAPA/UFLPA also flag the entity).
        ofac = self._ofac_status_for(name)
        if ofac.get("ofac_listed"):
            entity["raw_data"]["SDN_PROGRAM"] = ofac.get("ofac_program") or "OFAC-SDN"
        entity["_ofac"] = ofac
        entity["_eapa_docket"] = eapa_docket
        return entity

    @staticmethod
    def _eapa_docket_for(engine, name: str) -> Optional[str]:
        """Best-effort EAPA docket lookup from the CORD CBP-EAPA records."""
        try:
            target = name.strip().lower()
            for rec in engine.eapa_records():
                if (rec.get("PRIMARY_NAME_ORG") or "").strip().lower() == target:
                    return rec.get("DOCKET") or rec.get("RECORD_ID") or None
        except Exception:
            return None
        return None

    def _entity_factor_block(self, name: str, role: str, country: str = None) -> Optional[Dict[str, Any]]:
        """F1: per-entity v4.0 factor-attributed risk for one party.

        Scores the party via entity_scorer.score_entity (after EAPA/UFLPA/OFAC
        enrichment) and returns an EntityFactorBlockV4-aligned dict:
        {entity_id, name, role, score: ScoreBreakdownV4.to_dict(), ofac, eapa,
        uflpa, top_components}. Returns None if the party name is missing.
        Fully defensive — any failure degrades to None rather than blocking.
        """
        name = (name or "").strip()
        if not name or name.lower() == "unknown":
            return None
        try:
            from entity_scorer import score_entity

            entity = self._enrich_entity_flags(name, country)
            breakdown = score_entity(entity)
            score_dict = breakdown.to_dict()

            # Top weighted components (drives the ScoreBars in the UI).
            top = sorted(
                score_dict.get("components", []),
                key=lambda c: c.get("weighted_result", 0),
                reverse=True,
            )[:5]

            ofac = entity.get("_ofac") or {"ofac_listed": False, "ofac_program": None}
            eapa_listed = entity.get("flag") == "eapa_respondent"
            uflpa_listed = entity.get("flag") == "uflpa_listed"
            docket = entity.get("_eapa_docket")

            return {
                "entity_id": score_dict.get("subject_id", name),
                "name": name,
                "role": role,
                "score": score_dict,
                "final_score": score_dict.get("final_score", 0.0),
                "tier": score_dict.get("tier", "LOW"),
                "top_components": top,
                "ofac": {
                    "listed": bool(ofac.get("ofac_listed")),
                    "program": ofac.get("ofac_program"),
                },
                "eapa": {
                    "listed": eapa_listed,
                    "dockets": [docket] if (eapa_listed and docket) else [],
                },
                "uflpa": {"listed": uflpa_listed},
            }
        except Exception as e:
            logger.warning(f"Per-entity factor block failed for '{name}': {e}")
            return None

    def _network_evidence_block(self, name: str, country: str = None) -> Dict[str, Any]:
        """F6: NetworkEvidenceBlockV4 for the primary party from entity_edges.

        Resolves the party to an entity id and pulls incident edges. Work is
        capped (small build limit) and fully guarded so the referral never
        blocks if the CORD graph index is unavailable. Empty edges if none.
        """
        name = (name or "").strip()
        root_id = name or "unknown-entity"
        block: Dict[str, Any] = {
            "root_entity_id": root_id,
            "edges": [],
            "cross_corridor_reach": 0,
            "resolved_vs_explicit_delta": 0,
        }
        if not name or name.lower() == "unknown":
            return block

        try:
            import entity_edges

            # Cap the lazy build so a cold referral never scans the full index.
            try:
                entity_edges.build_edges(limit=400)
            except Exception as e:
                logger.warning(f"entity_edges build capped/failed for '{name}': {e}")

            # Resolve a candidate entity id via the CORD watchlist/search so the
            # "{DATA_SOURCE}:{RECORD_ID}" id convention edges_for expects is used.
            entity_id = self._resolve_entity_id(name, country) or root_id
            block["root_entity_id"] = entity_id

            edges = []
            try:
                edges = entity_edges.edges_for(entity_id) or []
            except Exception as e:
                logger.warning(f"edges_for unavailable for '{entity_id}': {e}")

            block["edges"] = [
                {
                    "src": e.src_entity_id,
                    "dst": e.dst_entity_id,
                    "type": e.edge_type,
                    "evidence": e.evidence,
                    "confidence": round(float(e.confidence), 3),
                }
                for e in edges
            ]

            # Cross-corridor reach from graph signals (explicit + resolved delta).
            try:
                provider = entity_edges.get_provider(limit=400)
                signals = provider.signals_for(entity_id)
                block["cross_corridor_reach"] = int(signals.corridor_degree)
                block["resolved_vs_explicit_delta"] = int(signals.resolved_degree)
            except Exception as e:
                logger.warning(f"graph signals unavailable for '{entity_id}': {e}")
        except Exception as e:
            logger.warning(f"Network evidence block failed for '{name}': {e}")

        return block

    def _resolve_entity_id(self, name: str, country: str = None) -> Optional[str]:
        """Resolve a party name to a CORD entity id ("{DATA_SOURCE}:{RECORD_ID}")
        so it matches the entity_edges id convention. Defensive; returns None."""
        try:
            from cord_engine import get_cord_engine

            matches = get_cord_engine().search(name, country=country, limit=1)
            if matches:
                m = matches[0]
                return f"{m.get('data_source')}:{m.get('record_id')}"
        except Exception as e:
            logger.warning(f"Entity id resolution unavailable for '{name}': {e}")
        return None

    def _ofac_status_for(self, name: str) -> Dict[str, Any]:
        """Defensively resolve OFAC/sanctions status for a party name.

        Uses the local CORD OFAC SDN index (cord_engine.get_ofac_status). Never
        raises — returns a clear status if CORD/OFAC lookup is unavailable.

        Returns: {"ofac_listed": bool, "ofac_program": str|None}
        """
        clear = {"ofac_listed": False, "ofac_program": None}
        if not name or not str(name).strip() or str(name).strip().lower() == "unknown":
            return clear
        try:
            from cord_engine import get_cord_engine

            match = get_cord_engine().get_ofac_status(str(name).strip())
            if match and match.get("matched"):
                return {
                    "ofac_listed": True,
                    "ofac_program": match.get("program")
                    or (match.get("raw") or {}).get("SDN_PROGRAM"),
                }
        except Exception as e:
            logger.warning(f"OFAC lookup unavailable for '{name}': {e}")
        return clear

    def generate_referral_package(self, shipment_id: str) -> Dict[str, Any]:
        """
        Generate comprehensive 14-section referral package for a shipment.

        Returns:
            Complete referral package with all sections
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Get shipment data
            cursor.execute("SELECT * FROM shipments WHERE id = ?", (shipment_id,))
            shipment_row = cursor.fetchone()
            if not shipment_row:
                return {"error": f"Shipment {shipment_id} not found"}

            shipment = dict(shipment_row)

            # Generate all sections with graceful fallbacks
            sections = {}
            sections["section_3_1_shipment_identification"] = self._section_3_1(shipment)
            sections["section_3_2_line_items"] = self._section_3_2(shipment, cursor)
            sections["section_3_3_routing_history"] = self._section_3_3(shipment, cursor)
            sections["section_3_4_parties_and_roles"] = self._section_3_4(shipment, cursor)
            sections["section_3_5_entity_ownership_chain"] = self._section_3_5(shipment, cursor)
            sections["section_3_6_historical_import_pattern"] = self._section_3_6(shipment)
            sections["section_3_7_trade_flow_intelligence"] = self._section_3_7(shipment)
            sections["section_3_8_document_review"] = self._section_3_8(shipment, cursor)
            sections["section_3_9_document_consistency"] = self._section_3_9(shipment)
            sections["section_3_10_supplier_verification"] = self._section_3_10(shipment, cursor)
            sections["section_3_11_risk_indicators"] = self._section_3_11(shipment)
            sections["section_3_12_pattern_analysis"] = self._section_3_12(shipment)
            sections["section_3_13_enforcement_analysis"] = self._section_3_13(shipment)
            sections["section_3_14_conclusion_and_recommendation"] = self._section_3_14(shipment)

            # Build referral package
            package = {
                "referral_id": str(uuid.uuid4()),
                "shipment_id": shipment_id,
                "manifest_id": shipment.get("manifest_id"),
                "created_at": datetime.utcnow().isoformat(),
                "risk_score": float(shipment.get("risk_score", 0)),
                "risk_level": self._get_risk_level(shipment.get("risk_score", 0)),
                "sections": sections,
            }

            return package

        except Exception as e:
            logger.error(f"Referral generation failed: {e}", exc_info=True)
            return {"error": str(e)}
        finally:
            conn.close()

    def _section_3_1(self, shipment: Dict) -> Dict[str, Any]:
        """Section 3-1: Shipment Identification"""
        return {
            "title": "SECTION 3-1: SHIPMENT IDENTIFICATION",
            "shipment_id": shipment.get("id"),
            "manifest_id": shipment.get("manifest_id"),
            "shipper": shipment.get("shipper_name", "Unknown"),
            "shipper_country": shipment.get("shipper_country") or shipment.get("origin_country"),
            "consignee": shipment.get("consignee_name", "Unknown"),
            "consignee_country": shipment.get("consignee_country") or shipment.get("destination_country"),
            "origin": shipment.get("origin_country"),
            "destination": shipment.get("destination_country"),
            "hs_code": shipment.get("hs_code"),
            "declared_value_usd": float(shipment.get("declared_value_usd", 0)),
            "weight_kg": float(shipment.get("declared_weight_kg", 0)),
            "entry_date": shipment.get("created_at"),
        }

    def _section_3_2(self, shipment: Dict, cursor) -> Dict[str, Any]:
        """Section 3-2: Line Items"""
        items = []
        try:
            cursor.execute(
                "SELECT hs_code, product_description, quantity, unit, total_value_usd FROM shipment_line_items WHERE shipment_id = ?",
                (shipment.get("id"),)
            )
            for row in cursor.fetchall():
                items.append({
                    "hs_code": row["hs_code"],
                    "description": row["product_description"],
                    "quantity": row["quantity"],
                    "unit": row["unit"],
                    "value_usd": row["total_value_usd"]
                })
        except Exception as e:
            logger.warning(f"Could not fetch line items: {e}")

        if not items:
            items = [{
                "hs_code": shipment.get("hs_code"),
                "description": shipment.get("commodity_name", "Unspecified Commodity"),
                "quantity": 1,
                "unit": "shipment",
                "value_usd": shipment.get("declared_value_usd", 0)
            }]

        return {
            "title": "SECTION 3-2: LINE ITEMS",
            "items": items,
            "total_value": sum(item.get("value_usd", 0) for item in items),
            "total_weight_kg": float(shipment.get("declared_weight_kg", 0)),
        }

    def _section_3_3(self, shipment: Dict, cursor) -> Dict[str, Any]:
        """Section 3-3: AIS Routing History"""
        routing = []
        try:
            cursor.execute(
                "SELECT location, event_date, event_type FROM routing_events WHERE shipment_id = ? ORDER BY event_date",
                (shipment.get("id"),)
            )
            for row in cursor.fetchall():
                routing.append({
                    "location": row["location"],
                    "date": row["event_date"],
                    "event": row["event_type"]
                })
        except Exception as e:
            logger.warning(f"Could not fetch routing events: {e}")

        return {
            "title": "SECTION 3-3: AIS ROUTING HISTORY",
            "routing_events": routing,
            "dwell_days": shipment.get("dwell_days", "Unknown"),
        }

    def _section_3_4(self, shipment: Dict, cursor) -> Dict[str, Any]:
        """Section 3-4: Parties and Roles"""
        parties = []
        try:
            cursor.execute(
                "SELECT party_name, party_role, party_country FROM parties_involved WHERE shipment_id = ?",
                (shipment.get("id"),)
            )
            for row in cursor.fetchall():
                parties.append({
                    "name": row["party_name"],
                    "role": row["party_role"],
                    "country": row["party_country"]
                })
        except Exception as e:
            logger.warning(f"Could not fetch parties: {e}")

        if not parties:
            parties = [
                {"name": shipment.get("shipper_name", "Unknown"), "role": "Shipper", "country": shipment.get("origin_country")},
                {"name": shipment.get("consignee_name", "Unknown"), "role": "Consignee", "country": shipment.get("destination_country")},
            ]

        # F0: surface OFAC/sanctions status per party (defensive — never crashes)
        for party in parties:
            party.update(self._ofac_status_for(party.get("name")))

        return {
            "title": "SECTION 3-4: PARTIES AND ROLES",
            "parties": parties,
        }

    def _section_3_5(self, shipment: Dict, cursor) -> Dict[str, Any]:
        """Section 3-5: Entity Ownership Chain - resolved from CORD"""
        chain = []

        # Try CORD first for live entity resolution
        try:
            chain = self._resolve_entities_from_cord(shipment)
            if chain:
                logger.info(f"Resolved {len(chain)} entities from CORD for {shipment.get('id')}")
        except Exception as e:
            logger.warning(f"CORD entity resolution failed: {e}", exc_info=True)

        # Fallback to database if CORD fails
        if not chain:
            try:
                cursor.execute(
                    "SELECT entity_id, entity_name, entity_type, country FROM entity_ownership_chain WHERE shipment_id = ? ORDER BY level",
                    (shipment.get("id"),)
                )
                for row in cursor.fetchall():
                    chain.append({
                        "entity_id": str(row["entity_id"]),
                        "name": row["entity_name"],
                        "type": row["entity_type"],
                        "country": row["country"]
                    })
            except Exception as e:
                logger.warning(f"Could not fetch entity chain from DB: {e}")

        return {
            "title": "SECTION 3-5: ENTITY OWNERSHIP CHAIN",
            "chain": chain,
        }

    def _resolve_entities_from_cord(self, shipment: Dict) -> List[Dict[str, Any]]:
        """Resolve entity ownership chain from CORD service"""
        shipper_name = shipment.get("shipper_name", "").strip()
        shipper_country = shipment.get("shipper_country") or shipment.get("origin_country")

        if not shipper_name:
            return []

        logger.info(f"Resolving entity chain from CORD for {shipper_name} ({shipper_country})")
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    f"{self.cord_url}/resolve",
                    json={
                        "shipper_name": shipper_name,
                        "shipper_country": shipper_country,
                        "destination": shipment.get("destination_country")
                    }
                )

                if response.status_code != 200:
                    logger.warning(f"CORD returned {response.status_code} for {shipper_name}")
                    return []

                cord_result = response.json()
                if cord_result.get("status") != "success":
                    logger.warning(f"CORD resolution failed for {shipper_name}")
                    return []

                chain_data = cord_result.get("chain", {})
                chain = []

                # Extract entities from CORD's level-based response
                for level in range(1, 4):
                    entity_key = f"level_{level}"
                    if entity_key not in chain_data or chain_data[entity_key] is None:
                        continue

                    entity = chain_data[entity_key]
                    rel_key = f"level_{level}_relationship"
                    relationship = chain_data.get(rel_key)

                    chain.append({
                        "entity_id": str(entity.get("entity_id", f"level-{level}")),
                        "name": entity.get("name", "Unknown"),
                        "type": entity.get("entity_type", "ORGANIZATION").upper(),
                        "country": entity.get("country", ""),
                        "confidence": float(entity.get("confidence", 0.85)),
                        "data_source": entity.get("data_source", "CORD"),
                        "relationships": [
                            {
                                "type": relationship.get("relationship_type", "RELATED_TO"),
                                "target": chain_data.get(f"level_{level}_id", ""),
                                "confidence": relationship.get("confidence", 0.8)
                            }
                        ] if relationship else []
                    })

                return chain

        except Exception as e:
            logger.error(f"CORD entity resolution error: {e}")
            return []

    def _section_3_6(self, shipment: Dict) -> Dict[str, Any]:
        """Section 3-6: Historical Import Pattern - AI placeholder"""
        return {
            "title": "SECTION 3-6: HISTORICAL IMPORT PATTERN",
            "pattern_narrative": "[AI-generated narrative will be added by Gemini service]",
            "shipper_age_months": shipment.get("shipper_age_months"),
            "origin_country": shipment.get("origin_country"),
        }

    def _section_3_7(self, shipment: Dict) -> Dict[str, Any]:
        """Section 3-7: Trade Flow Intelligence - AI placeholder.

        F4: EAPA anchor linkage — if a party (shipper / consignee) is a confirmed
        CBP-EAPA respondent, surface it here (with docket if reachable). EAPA is
        the anchor enforcement flag of the entity model, so the trade-flow section
        carries the explicit respondent linkage. Defensive — never blocks.
        """
        eapa_anchors: List[Dict[str, Any]] = []
        try:
            from cord_engine import get_cord_engine

            engine = get_cord_engine()
            for name, role in (
                (shipment.get("shipper_name"), "Shipper"),
                (shipment.get("consignee_name"), "Consignee"),
            ):
                pname = (name or "").strip()
                if not pname or pname.lower() == "unknown":
                    continue
                if engine.is_eapa_respondent(pname):
                    eapa_anchors.append({
                        "name": pname,
                        "role": role,
                        "is_eapa_respondent": True,
                        "docket": self._eapa_docket_for(engine, pname),
                    })
        except Exception as e:
            logger.warning(f"EAPA anchor linkage unavailable: {e}")

        return {
            "title": "SECTION 3-7: TRADE FLOW INTELLIGENCE",
            "trade_flow_narrative": "[AI-generated narrative will be added by Gemini service]",
            "hs_code": shipment.get("hs_code"),
            "ad_cvd_rate": shipment.get("ad_cvd_rate", 0),
            # F4 — EAPA respondent anchor linkage for parties on this shipment.
            "eapa_anchors": eapa_anchors,
        }

    def _section_3_8(self, shipment: Dict, cursor) -> Dict[str, Any]:
        """Section 3-8: Document Review"""
        documents = []
        try:
            cursor.execute(
                "SELECT doc_type, doc_status FROM documents WHERE shipment_id = ?",
                (shipment.get("id"),)
            )
            for row in cursor.fetchall():
                documents.append({
                    "type": row["doc_type"],
                    "status": row["doc_status"]
                })
        except Exception as e:
            logger.warning(f"Could not fetch documents: {e}")

        return {
            "title": "SECTION 3-8: DOCUMENT REVIEW",
            "documents": documents or [{"type": "ISF/Manifest", "status": "Filed"}],
        }

    def _section_3_9(self, shipment: Dict) -> Dict[str, Any]:
        """Section 3-9: Document Consistency (ISF Element 9)"""
        return {
            "title": "SECTION 3-9: DOCUMENT CONSISTENCY (ELEMENT 9)",
            "element9_mismatch": bool(shipment.get("element9_is_mismatch")),
            "declared_country": shipment.get("element9_declared_country"),
            "actual_country": shipment.get("element9_actual_country"),
            "confidence": shipment.get("element9_confidence", 0),
        }

    def _section_3_10(self, shipment: Dict, cursor) -> Dict[str, Any]:
        """Section 3-10: Supplier Manufacturing Verification"""
        suppliers = []
        try:
            cursor.execute(
                "SELECT supplier_name, mfg_location FROM suppliers WHERE shipment_id = ?",
                (shipment.get("id"),)
            )
            for row in cursor.fetchall():
                suppliers.append({
                    "name": row["supplier_name"],
                    "location": row["mfg_location"]
                })
        except Exception as e:
            logger.warning(f"Could not fetch suppliers: {e}")

        # F0: surface OFAC/sanctions status per supplier (defensive — never crashes)
        for supplier in suppliers:
            supplier.update(self._ofac_status_for(supplier.get("name")))

        # F0: OFAC status for the shipper (manufacturer/verification subject)
        shipper_name = shipment.get("shipper_name")
        shipper_ofac = self._ofac_status_for(shipper_name)

        # F1: per-entity v4.0 factor-attributed risk for shipper / consignee /
        # manufacturer (suppliers). Each party is scored through entity_scorer
        # after EAPA/UFLPA/OFAC enrichment; shape aligns to EntityFactorBlockV4.
        shipper_country = shipment.get("shipper_country") or shipment.get("origin_country")
        consignee_country = shipment.get("consignee_country") or shipment.get("destination_country")
        entity_risk: List[Dict[str, Any]] = []
        for name, role, country in (
            (shipper_name, "Shipper", shipper_country),
            (shipment.get("consignee_name"), "Consignee", consignee_country),
        ):
            block = self._entity_factor_block(name, role, country)
            if block:
                entity_risk.append(block)
        for supplier in suppliers:
            block = self._entity_factor_block(
                supplier.get("name"), "Manufacturer", supplier.get("location")
            )
            if block:
                entity_risk.append(block)

        # F6: network-evidence block for the primary party (the shipper).
        network_evidence = self._network_evidence_block(shipper_name, shipper_country)

        return {
            "title": "SECTION 3-10: SUPPLIER MANUFACTURING VERIFICATION",
            "suppliers": suppliers,
            "shipper_ofac_listed": shipper_ofac["ofac_listed"],
            "shipper_ofac_program": shipper_ofac["ofac_program"],
            # F1 — per-entity v4.0 factor-attributed risk (EntityFactorBlockV4[]).
            "entity_risk": entity_risk,
            # F6 — primary-party network evidence (NetworkEvidenceBlockV4).
            "network_evidence": network_evidence,
        }

    def _critical_indicators(self, shipment: Dict) -> List[str]:
        """Triggered critical risk indicators — mirrors the rule engine's
        risk_scoring_engine.RiskScoringEngine._check_critical_indicators so the
        referral package surfaces the same compound-risk signals that drove the
        score. Kept dependency-light (no ML model load) for PDF generation.
        """
        indicators: List[str] = []

        if shipment.get("element9_is_mismatch") or shipment.get("isf_element_mismatch"):
            declared = shipment.get("element9_declared_country", "?")
            actual = shipment.get("element9_actual_country", "?")
            indicators.append(f"ISF Element 9 origin mismatch ({declared} declared → {actual} actual)")

        ad_cvd = float(shipment.get("ad_cvd_rate") or 0)
        if ad_cvd >= 1.0:
            indicators.append(f"High AD/CVD tariff exposure ({ad_cvd * 100:.0f}%)")

        dwell = float(shipment.get("dwell_days") or 0)
        if dwell >= 10:
            indicators.append(f"Excessive dwell time ({dwell:.0f} days — transshipment window)")

        age = int(shipment.get("shipper_age_months") or 99)
        if age < 6:
            indicators.append(f"Newly established shipper ({age} months — evasion risk)")

        price_var = float(shipment.get("price_variance_percent") or 0)
        if price_var <= -40:
            indicators.append(f"Severely undervalued pricing ({price_var:.0f}% below benchmark)")
        elif price_var <= -20:
            indicators.append(f"Undervalued pricing ({price_var:.0f}% below benchmark)")

        return indicators

    def _section_3_11(self, shipment: Dict) -> Dict[str, Any]:
        """Section 3-11: Risk Indicator Summary (from rule-engine indicators)"""
        indicators = self._critical_indicators(shipment)
        if indicators:
            summary = (
                f"{len(indicators)} critical risk indicator(s) triggered: "
                + "; ".join(indicators) + "."
            )
        else:
            summary = "No critical compound-risk indicators triggered for this shipment."
        return {
            "title": "SECTION 3-11: RISK INDICATOR SUMMARY",
            "summary": summary,
            "critical_indicators": indicators,
            "indicator_count": len(indicators),
            "risk_score": shipment.get("risk_score", 0),
        }

    def _section_3_12(self, shipment: Dict) -> Dict[str, Any]:
        """Section 3-12: Pattern Analysis & Behavioral Indicators"""
        ad_cvd_rate = shipment.get('ad_cvd_rate') or 0
        return {
            "title": "SECTION 3-12: PATTERN ANALYSIS & BEHAVIORAL INDICATORS",
            "critical_indicators": self._critical_indicators(shipment),
            "patterns": [
                f"Shipper age: {shipment.get('shipper_age_months')} months",
                f"Dwell time: {shipment.get('dwell_days')} days",
                f"Element 9 mismatch: {bool(shipment.get('element9_is_mismatch'))}",
                f"AD/CVD exposure: {float(ad_cvd_rate) * 100:.1f}%"
            ]
        }

    def _section_3_13(self, shipment: Dict) -> Dict[str, Any]:
        """Section 3-13: Enforcement Actions & Legal"""
        return {
            "title": "SECTION 3-13: ENFORCEMENT ACTIONS & LEGAL REFERENCES",
            "origin_country": shipment.get("origin_country"),
            "enforcement_references": "See prior enforcement on similar corridors"
        }

    def _section_3_14(self, shipment: Dict) -> Dict[str, Any]:
        """Section 3-14: Conclusion & Recommendation - AI placeholder"""
        risk_score = shipment.get("risk_score", 0)
        if risk_score >= 85:
            recommendation = "RECOMMEND EXAMINATION & INVESTIGATION (19 USC § 1592, 19 CFR 165)"
        elif risk_score >= 70:
            recommendation = "RECOMMEND EXAMINATION (19 CFR 165)"
        else:
            recommendation = "RECOMMEND RELEASE (19 CFR 163)"

        return {
            "title": "SECTION 3-14: CONCLUSION & RECOMMENDATION",
            "conclusion": "[AI-generated conclusion will be added by Gemini service]",
            "recommendation": recommendation,
            "risk_score": risk_score,
        }

    def _get_risk_level(self, risk_score: float) -> str:
        """Map risk score to risk level"""
        if risk_score >= 85:
            return "CRITICAL"
        elif risk_score >= 70:
            return "HIGH"
        elif risk_score >= 50:
            return "MEDIUM"
        else:
            return "LOW"
