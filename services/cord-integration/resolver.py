"""3-Level Entity Resolution + Risk Scoring."""
import logging
import sqlite3
from typing import Dict, List, Optional, Any
import json

logger = logging.getLogger(__name__)


class EntityResolver:
    """Resolve 3-level entity chains with OFAC detection and risk scoring."""

    def __init__(self, db_path: str = "/app/data/senzing.db"):
        """Initialize resolver.

        Args:
            db_path: Path to Senzing SQLite database
        """
        self.db_path = db_path

    def resolve_shipper_chain(
        self,
        shipper_name: str,
        shipper_country: Optional[str] = None,
        consignee_name: Optional[str] = None,
        consignee_country: Optional[str] = None
    ) -> Dict[str, Any]:
        """Resolve 3-level entity chain for shipper with OFAC and ISF linking.

        Level 1: Shipper entity (searchByAttributes)
        Level 2: Parent company (getRelationships with OWNED_BY)
        Level 3: Ultimate owner (getRelationships from Level 2)

        Also links matching CBP-ISF records.

        Args:
            shipper_name: Name of shipper to resolve
            shipper_country: Optional shipper country code
            consignee_name: Optional consignee name
            consignee_country: Optional consignee country code

        Returns:
            Dict with 3-level chain, OFAC status, ISF records, and risk score
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # ===== LEVEL 1: SEARCH FOR SHIPPER =====
            level_1_results = self._search_entities(cursor, shipper_name, shipper_country, limit=5)
            if not level_1_results:
                conn.close()
                return self._error_response(f"Shipper '{shipper_name}' not found")

            # Pick highest confidence match
            level_1_entity = max(level_1_results, key=lambda x: x.get("confidence", 0.0))
            level_1_id = level_1_entity["entity_id"]

            logger.info(f"Level 1 (Shipper): {level_1_entity.get('name')} ({level_1_id})")

            # ===== LEVEL 2: PARENT COMPANY =====
            level_2_entity = None
            level_2_id = None
            level_2_relationship = None

            relationships_l2 = self._get_parent_relationships(cursor, level_1_id)
            if relationships_l2:
                # Pick first parent relationship
                level_2_rel = relationships_l2[0]
                level_2_id = level_2_rel["target_entity_id"]
                level_2_entity = self._get_entity(cursor, level_2_id)
                level_2_relationship = level_2_rel
                logger.info(f"Level 2 (Parent): {level_2_entity.get('name')} ({level_2_id})")

            # ===== LEVEL 3: ULTIMATE OWNER =====
            level_3_entity = None
            level_3_id = None
            level_3_relationship = None

            if level_2_id:
                relationships_l3 = self._get_parent_relationships(cursor, level_2_id)
                if relationships_l3:
                    level_3_rel = relationships_l3[0]
                    level_3_id = level_3_rel["target_entity_id"]
                    level_3_entity = self._get_entity(cursor, level_3_id)
                    level_3_relationship = level_3_rel
                    logger.info(f"Level 3 (Owner): {level_3_entity.get('name')} ({level_3_id})")

            # ===== OFAC DETECTION =====
            ofac_detected = False
            ofac_entity = None
            for entity in [level_1_entity, level_2_entity, level_3_entity]:
                if entity and entity.get("data_source") == "OFAC":
                    ofac_detected = True
                    ofac_entity = entity
                    logger.warning(f"OFAC entity detected: {entity.get('name')}")
                    break

            # ===== ISF LINKING =====
            isf_records = self._find_isf_records(cursor, level_1_id)
            logger.info(f"Linked {len(isf_records)} ISF records")

            # ===== CONFIDENCE SCORING =====
            confidences = [level_1_entity.get("confidence", 1.0)]
            if level_2_entity:
                confidences.append(level_2_entity.get("confidence", 1.0))
            if level_3_entity:
                confidences.append(level_3_entity.get("confidence", 1.0))

            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            # ===== RISK SCORING =====
            risk_score = self._calculate_risk_score(
                level_1_entity,
                level_2_entity,
                level_3_entity,
                ofac_detected,
                avg_confidence
            )

            # ===== RISK INDICATOR =====
            risk_indicator = self._determine_risk_indicator(
                level_1_entity,
                ofac_detected,
                risk_score
            )

            conn.close()

            return {
                "status": "success",
                "chain": {
                    "level_1": self._entity_to_dict(level_1_entity),
                    "level_1_id": level_1_id,
                    "level_2": self._entity_to_dict(level_2_entity) if level_2_entity else None,
                    "level_2_id": level_2_id,
                    "level_2_relationship": level_2_relationship,
                    "level_3": self._entity_to_dict(level_3_entity) if level_3_entity else None,
                    "level_3_id": level_3_id,
                    "level_3_relationship": level_3_relationship
                },
                "ofac": {
                    "detected": ofac_detected,
                    "entity": self._entity_to_dict(ofac_entity) if ofac_entity else None
                },
                "isf_records": isf_records,
                "scoring": {
                    "confidence": avg_confidence,
                    "risk_score": risk_score,
                    "risk_level": self._risk_level_from_score(risk_score),
                    "risk_indicator": risk_indicator
                }
            }

        except Exception as e:
            logger.error(f"Resolve shipper chain failed: {e}")
            return self._error_response(str(e))

    def _search_entities(
        self,
        cursor: sqlite3.Cursor,
        name: str,
        country: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for entities by name + country."""
        try:
            query = "SELECT * FROM senzing_entities WHERE name_primary LIKE ?"
            params = [f"%{name}%"]

            if country:
                query += " AND country = ?"
                params.append(country)

            query += f" ORDER BY confidence DESC LIMIT {limit}"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            results = []
            for row in rows:
                results.append({
                    "entity_id": row[0],
                    "data_source": row[1],
                    "record_id": row[2],
                    "name": row[3],
                    "country": row[4],
                    "entity_type": row[5],
                    "confidence": row[6],
                    "raw_data": json.loads(row[7]) if row[7] else {}
                })

            return results

        except Exception as e:
            logger.error(f"Search entities failed: {e}")
            return []

    def _get_parent_relationships(
        self,
        cursor: sqlite3.Cursor,
        entity_id: str
    ) -> List[Dict[str, Any]]:
        """Get parent company relationships for an entity."""
        try:
            cursor.execute("""
                SELECT entity_id_b, relationship_type, confidence, evidence
                FROM senzing_relationships
                WHERE entity_id_a = ? AND relationship_type IN ('OWNED_BY', 'PARENT_COMPANY')
                ORDER BY confidence DESC
                LIMIT 5
            """, (entity_id,))

            relationships = []
            for row in cursor.fetchall():
                relationships.append({
                    "target_entity_id": row[0],
                    "relationship_type": row[1],
                    "confidence": row[2],
                    "evidence": json.loads(row[3]) if row[3] else []
                })

            return relationships

        except Exception as e:
            logger.error(f"Get parent relationships failed: {e}")
            return []

    def _get_entity(self, cursor: sqlite3.Cursor, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get entity details by ID."""
        try:
            cursor.execute(
                "SELECT * FROM senzing_entities WHERE entity_id = ?",
                (entity_id,)
            )
            row = cursor.fetchone()

            if not row:
                return None

            return {
                "entity_id": row[0],
                "data_source": row[1],
                "record_id": row[2],
                "name": row[3],
                "country": row[4],
                "entity_type": row[5],
                "confidence": row[6],
                "raw_data": json.loads(row[7]) if row[7] else {}
            }

        except Exception as e:
            logger.error(f"Get entity failed: {e}")
            return None

    def _find_isf_records(self, cursor: sqlite3.Cursor, entity_id: str) -> List[Dict[str, Any]]:
        """Find CBP-ISF records linked to shipper."""
        try:
            cursor.execute("""
                SELECT e.* FROM senzing_entities e
                INNER JOIN senzing_relationships r ON r.entity_id_b = e.entity_id
                WHERE r.entity_id_a = ? AND e.data_source = 'CBP-ISF'
            """, (entity_id,))

            isf_records = []
            for row in cursor.fetchall():
                isf_records.append({
                    "entity_id": row[0],
                    "data_source": row[1],
                    "record_id": row[2],
                    "name": row[3],
                    "country": row[4],
                    "attributes": json.loads(row[7]) if row[7] else {}
                })

            return isf_records

        except Exception as e:
            logger.error(f"Find ISF records failed: {e}")
            return []

    def _calculate_risk_score(
        self,
        level_1: Dict[str, Any],
        level_2: Optional[Dict[str, Any]],
        level_3: Optional[Dict[str, Any]],
        ofac_detected: bool,
        confidence: float
    ) -> float:
        """Calculate overall risk score (0-100)."""
        base_score = 50.0  # Neutral baseline

        # OFAC detection = critical risk
        if ofac_detected:
            return 95.0

        # Origin country risk
        level_1_country = level_1.get("country", "")
        if level_1_country in ["CN", "IR", "SY", "KP"]:
            base_score += 30.0
        elif level_1_country in ["RU", "BY"]:
            base_score += 25.0
        elif level_1_country in ["VN", "TH", "MY"]:
            base_score += 15.0

        # Low confidence increases risk
        if confidence < 0.7:
            base_score += 20.0
        elif confidence < 0.85:
            base_score += 10.0

        # Complex ownership chain (Level 2 + Level 3) = elevated risk
        if level_2 and level_3:
            base_score += 5.0

        # Normalize to 0-100
        return min(100.0, max(0.0, base_score))

    def _determine_risk_indicator(
        self,
        level_1_entity: Dict[str, Any],
        ofac_detected: bool,
        risk_score: float
    ) -> str:
        """Determine human-readable risk indicator."""
        if ofac_detected:
            return "OFAC_SANCTIONS_LIST"

        country = level_1_entity.get("country", "")

        if risk_score >= 80.0:
            if country == "CN":
                return "CHINA_ORIGIN_CRITICAL_RISK"
            else:
                return "HIGH_RISK_JURISDICTION"
        elif risk_score >= 60.0:
            if country == "CN":
                return "CHINA_ORIGIN_HIGH_RISK"
            else:
                return "ELEVATED_RISK"
        elif risk_score >= 40.0:
            if country in ["VN", "TH", "MY"]:
                return "TRANSSHIPMENT_CORRIDOR_MEDIUM_RISK"
            else:
                return "MEDIUM_RISK"
        else:
            return "LOW_RISK"

    def _risk_level_from_score(self, score: float) -> str:
        """Convert numeric score to risk level."""
        if score >= 80.0:
            return "CRITICAL"
        elif score >= 60.0:
            return "HIGH"
        elif score >= 40.0:
            return "MEDIUM"
        else:
            return "LOW"

    def _entity_to_dict(self, entity: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Convert entity to output dict."""
        if not entity:
            return None

        return {
            "entity_id": entity.get("entity_id"),
            "name": entity.get("name"),
            "country": entity.get("country"),
            "data_source": entity.get("data_source"),
            "confidence": entity.get("confidence"),
            "entity_type": entity.get("entity_type")
        }

    # ===================================================================== #
    # Related-parties / chain serving (reads derived senzing_relationships)  #
    # ===================================================================== #
    @staticmethod
    def _name_from_raw(raw_json: Optional[str]) -> str:
        """Best-effort primary name from a raw CORD record (index name_primary
        is blank for OFAC/OPEN-SANCTIONS/labor sources)."""
        if not raw_json:
            return ""
        try:
            raw = json.loads(raw_json)
        except (json.JSONDecodeError, TypeError):
            return ""
        for key in ("NAMES", "NAME_LIST"):
            arr = raw.get(key)
            if isinstance(arr, list) and arr:
                prim = next((n for n in arr
                             if isinstance(n, dict) and n.get("NAME_TYPE") == "PRIMARY"),
                            arr[0])
                if isinstance(prim, dict):
                    org = prim.get("NAME_ORG") or prim.get("NAME_FULL")
                    if org:
                        return str(org)
                    full = " ".join(str(prim.get(k, "")) for k in
                                    ("PRIMARY_NAME_FIRST", "PRIMARY_NAME_MIDDLE",
                                     "PRIMARY_NAME_LAST")).strip()
                    if full:
                        return full
        for key in ("PRIMARY_NAME_ORG", "LEGAL_NAME_ORG", "NAME", "name", "Title"):
            if raw.get(key):
                return str(raw[key])
        return ""

    def get_related_parties(self, entity_id: str, limit: int = 50
                            ) -> List[Dict[str, Any]]:
        """All related parties for an entity from senzing_relationships.

        Returns every relationship incident to ``entity_id`` (any type), joined
        with the related entity's name/country/source so the workspace can show
        a real resolved network. Excludes the internal derived marker.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT r.entity_id_a AS a, r.entity_id_b AS b,
                       r.relationship_type AS rtype, r.confidence AS conf,
                       r.evidence AS evidence,
                       e.name_primary AS name, e.country AS country,
                       e.data_source AS data_source, e.entity_type AS entity_type,
                       e.raw_data AS raw_data
                FROM senzing_relationships r
                LEFT JOIN senzing_entities e ON e.entity_id = r.entity_id_b
                WHERE r.entity_id_a = ?
                  AND r.relationship_type != '__DERIVED_MARKER__'
                ORDER BY r.confidence DESC
                LIMIT ?
            """, (entity_id, limit))
            parties: List[Dict[str, Any]] = []
            for row in cursor.fetchall():
                try:
                    ev = json.loads(row["evidence"]) if row["evidence"] else []
                except (json.JSONDecodeError, TypeError):
                    ev = []
                name = row["name"]
                if not name or not name.strip():
                    name = self._name_from_raw(row["raw_data"]) or row["b"]
                parties.append({
                    "entity_id": row["b"],
                    "name": name,
                    "country": row["country"] or "",
                    "data_source": row["data_source"] or "",
                    "entity_type": row["entity_type"] or "",
                    "relationship_type": row["rtype"],
                    "confidence": row["conf"],
                    "evidence": ev,
                })
            conn.close()
            return parties
        except Exception as e:
            logger.error(f"get_related_parties failed: {e}")
            return []

    def get_ownership_chain(self, entity_id: str, max_depth: int = 4
                            ) -> List[Dict[str, Any]]:
        """Walk OWNED_BY / PARENT_COMPANY pointers up to ``max_depth`` levels."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            chain: List[Dict[str, Any]] = []
            current = entity_id
            seen = {entity_id}
            for level in range(1, max_depth + 1):
                rels = self._get_parent_relationships(cursor, current)
                if not rels:
                    break
                rel = rels[0]
                target = rel["target_entity_id"]
                if target in seen:
                    break
                seen.add(target)
                ent = self._get_entity(cursor, target) or {}
                ename = ent.get("name")
                if not ename or not str(ename).strip():
                    ename = self._name_from_raw(
                        json.dumps(ent.get("raw_data")) if ent.get("raw_data") else None
                    ) or target
                chain.append({
                    "level": level,
                    "entity_id": target,
                    "name": ename,
                    "country": ent.get("country") or "",
                    "data_source": ent.get("data_source") or "",
                    "relationship_type": rel["relationship_type"],
                    "confidence": rel["confidence"],
                    "evidence": rel["evidence"],
                })
                current = target
            conn.close()
            return chain
        except Exception as e:
            logger.error(f"get_ownership_chain failed: {e}")
            return []

    def _error_response(self, error_msg: str) -> Dict[str, Any]:
        """Return error response."""
        return {
            "status": "error",
            "error": error_msg,
            "chain": None,
            "ofac": {"detected": False, "entity": None},
            "isf_records": [],
            "scoring": {
                "confidence": 0.0,
                "risk_score": 0.0,
                "risk_level": "UNKNOWN",
                "risk_indicator": "RESOLUTION_FAILED"
            }
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    resolver = EntityResolver()
    result = resolver.resolve_shipper_chain(
        "Greenfield Industrial Trading Co., Ltd.",
        "VN"
    )
    print(json.dumps(result, indent=2))
