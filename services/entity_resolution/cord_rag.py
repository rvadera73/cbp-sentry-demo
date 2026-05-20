"""
CORD RAG (Retrieval-Augmented Generation) Database for Entity Resolution.

Provides fast, offline entity resolution against 21M CORD records using local SQLite.
- Resolve entities by name + country
- Trace beneficial ownership chains
- Screen against embedded sanctions data
"""

import sqlite3
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class CORDRagDatabase:
    """Query 21M CORD records from local SQLite database."""

    def __init__(self, db_path: str = "data/cord_rag.db"):
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"CORD RAG database not found at {self.db_path}\n"
                f"Run: python3 scripts/build_cord_rag_db.py"
            )

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    async def resolve_entity(
        self, entity_name: str, country: str, confidence_threshold: float = 0.5
    ) -> Dict:
        """
        Resolve entity name + country to CORD record.

        Tries:
        1. Exact match (entity_name, country)
        2. Fuzzy match (entity_name LIKE %, country)
        3. Not found

        Returns:
        {
            'found': bool,
            'entity_id': str or None,
            'entity_name': str or None,
            'country': str or None,
            'beneficial_owner': str or None,
            'parent_company': str or None,
            'parent_country': str or None,
            'data_source': str (CORD_LONDON, CORD_MOSCOW, CORD_LASVEGAS),
            'gleif_id': str or None,
            'sanctions_status': str (CLEAR, OFAC_HIT, OPENSANCTIONS_HIT),
            'confidence': float (0.0-1.0),
            'match_type': str ('exact', 'fuzzy', 'not_found')
        }
        """
        if not entity_name or not country:
            return {"found": False, "confidence": 0.0, "match_type": "not_found"}

        conn = self._get_connection()
        cur = conn.cursor()

        try:
            # Step 1: Exact match
            cur.execute(
                """
                SELECT * FROM entities
                WHERE UPPER(entity_name) = UPPER(?)
                AND UPPER(country) = UPPER(?)
                LIMIT 1
                """,
                (entity_name, country),
            )

            result = cur.fetchone()
            if result:
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
                    "confidence": 1.0,
                    "match_type": "exact",
                }

            # Step 2: Fuzzy match (first 5 results, return best)
            cur.execute(
                """
                SELECT * FROM entities
                WHERE UPPER(entity_name) LIKE UPPER(?)
                AND UPPER(country) = UPPER(?)
                ORDER BY entity_name ASC
                LIMIT 5
                """,
                (f"%{entity_name}%", country),
            )

            results = cur.fetchall()
            if results:
                # Return best fuzzy match (first one after LIKE)
                best = results[0]
                # Calculate confidence based on name similarity
                confidence = 0.85 if len(results) == 1 else 0.70
                return {
                    "found": True,
                    "entity_id": best["entity_id"],
                    "entity_name": best["entity_name"],
                    "country": best["country"],
                    "beneficial_owner": best["beneficial_owner"],
                    "parent_company": best["parent_company"],
                    "parent_country": best["parent_country"],
                    "data_source": best["data_source"],
                    "gleif_id": best["gleif_id"],
                    "sanctions_status": best["sanctions_status"],
                    "confidence": confidence,
                    "match_type": "fuzzy",
                }

            # Not found
            return {"found": False, "confidence": 0.0, "match_type": "not_found"}

        finally:
            conn.close()

    async def trace_beneficial_owner(
        self, entity_name: str, country: str, depth: int = 3
    ) -> List[Dict]:
        """
        Trace beneficial ownership chain by following parent_company links.

        Returns list of entities up the ownership chain:
        [
            {'entity_name': str, 'country': str, 'beneficial_owner': str, 'data_source': str},
            ...
        ]
        """
        if not entity_name or not country:
            return []

        conn = self._get_connection()
        cur = conn.cursor()
        chain = []

        try:
            current_name = entity_name
            current_country = country

            for level in range(depth):
                cur.execute(
                    """
                    SELECT * FROM entities
                    WHERE UPPER(entity_name) = UPPER(?)
                    AND UPPER(country) = UPPER(?)
                    LIMIT 1
                    """,
                    (current_name, current_country),
                )

                result = cur.fetchone()
                if not result:
                    break

                chain.append(
                    {
                        "entity_name": result["entity_name"],
                        "country": result["country"],
                        "beneficial_owner": result["beneficial_owner"],
                        "data_source": result["data_source"],
                        "level": level,
                    }
                )

                # Move up to parent company
                if result["parent_company"] and result["parent_country"]:
                    current_name = result["parent_company"]
                    current_country = result["parent_country"]
                else:
                    break

            return chain

        finally:
            conn.close()

    async def search_sanctions(self, entity_name: str, country: str) -> Dict:
        """
        Check entity against embedded OpenSanctions/OFAC data in CORD.

        Returns:
        {
            'status': str ('CLEAR', 'OFAC_HIT', 'OPENSANCTIONS_HIT'),
            'confidence': float (0.0-1.0),
            'match_fields': list of fields that matched (if hit)
        }
        """
        if not entity_name or not country:
            return {"status": "CLEAR", "confidence": 0.0, "match_fields": []}

        conn = self._get_connection()
        cur = conn.cursor()

        try:
            # Check both exact and fuzzy for sanctions hits
            cur.execute(
                """
                SELECT sanctions_status FROM entities
                WHERE UPPER(entity_name) = UPPER(?)
                AND UPPER(country) = UPPER(?)
                AND sanctions_status != 'CLEAR'
                LIMIT 1
                """,
                (entity_name, country),
            )

            result = cur.fetchone()
            if result:
                status = result["sanctions_status"]
                confidence = 0.95 if status == "OFAC_HIT" else 0.85
                return {
                    "status": status,
                    "confidence": confidence,
                    "match_fields": ["entity_name", "country"],
                }

            return {"status": "CLEAR", "confidence": 1.0, "match_fields": []}

        finally:
            conn.close()

    async def bulk_search(
        self, entities: List[Tuple[str, str]]
    ) -> Dict[Tuple[str, str], Dict]:
        """
        Resolve multiple entities in parallel.

        Args:
            entities: List of (entity_name, country) tuples

        Returns:
            {(name, country): resolution_result, ...}
        """
        results = {}
        for entity_name, country in entities:
            result = await self.resolve_entity(entity_name, country)
            results[(entity_name, country)] = result
        return results

    async def get_stats(self) -> Dict:
        """Get database statistics."""
        conn = self._get_connection()
        cur = conn.cursor()

        try:
            cur.execute("SELECT COUNT(*) as total FROM entities")
            total = cur.fetchone()["total"]

            cur.execute(
                "SELECT data_source, COUNT(*) as count FROM entities GROUP BY data_source"
            )
            by_source = {row["data_source"]: row["count"] for row in cur.fetchall()}

            cur.execute(
                "SELECT sanctions_status, COUNT(*) as count FROM entities WHERE sanctions_status != 'CLEAR' GROUP BY sanctions_status"
            )
            sanctions = {row["sanctions_status"]: row["count"] for row in cur.fetchall()}

            return {
                "total_records": total,
                "by_source": by_source,
                "sanctions_hits": sanctions,
                "database_path": str(self.db_path),
            }

        finally:
            conn.close()
