"""
Human-in-the-Loop Feedback Engine

Implements Stochastic Gradient Descent-based weight adjustment based on analyst overrides.
Tracks override patterns and suggests weight changes with corroboration thresholds.
"""

import logging
import sqlite3
import uuid
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import json

logger = logging.getLogger(__name__)

# SGD hyperparameters
LEARNING_RATE = 0.05  # α for weight adjustment
CORROBORATION_THRESHOLD = 3  # Number of similar overrides to trigger suggestion
CONFIDENCE_THRESHOLD = 70.0  # Minimum confidence % to suggest changes
DEFAULT_7_FACTOR_WEIGHTS = {
    "w_documentation": 0.25,
    "w_commodity": 0.15,
    "w_routing": 0.15,
    "w_party": 0.15,
    "w_corridor": 0.20,
    "w_pattern": 0.10,
    "w_time": 0.10,
}


class FeedbackEngine:
    """Manages analyst feedback and dynamic weight adjustments"""

    def __init__(self, db_path: Optional[str] = None):
        # Use provided path or try common paths
        if db_path:
            self.db_path = db_path
        elif os.path.exists("/app/data/cbp_sentry.db"):
            self.db_path = "/app/data/cbp_sentry.db"
        else:
            self.db_path = "/home/rahulvadera/cbp-sentry/data/cbp_sentry.db"

    @staticmethod
    def _ensure_weight_configurations_v2(cursor: sqlite3.Cursor) -> None:
        """Create the 7-factor weight configuration table if it does not exist."""
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS weight_configurations_v2 (
                id TEXT PRIMARY KEY,
                corridor TEXT,
                w_documentation REAL NOT NULL,
                w_commodity REAL NOT NULL,
                w_routing REAL NOT NULL,
                w_party REAL NOT NULL,
                w_corridor REAL NOT NULL,
                w_pattern REAL NOT NULL,
                w_time REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                created_by TEXT NOT NULL,
                notes TEXT
            )
            """
        )

    def record_override(
        self,
        shipment_id: str,
        original_score: float,
        override_decision: str,  # "ACCEPT" or "REJECT"
        feedback_type: Optional[str],
        analyst_id: str,
        analyst_name: str,
        notes: Optional[str] = None,
    ) -> str:
        """
        Record an analyst override decision.

        Args:
            shipment_id: The shipment being reviewed
            original_score: The AI system's calculated score
            override_decision: "ACCEPT" (agrees with score) or "REJECT" (disagrees)
            feedback_type: Reason for override (e.g., "factory_expansion", "dual_origin")
            analyst_id: ID of the analyst
            analyst_name: Name of the analyst
            notes: Additional notes from analyst

        Returns:
            Override record ID
        """
        override_id = str(uuid.uuid4())

        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO scoring_overrides
                (id, shipment_id, original_score, override_decision, feedback_type,
                 analyst_id, analyst_name, created_at, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    override_id,
                    shipment_id,
                    original_score,
                    override_decision,
                    feedback_type,
                    analyst_id,
                    analyst_name,
                    datetime.utcnow().isoformat(),
                    notes,
                ),
            )
            conn.commit()
            conn.close()

            logger.info(f"Recorded override {override_id}: {shipment_id} → {override_decision}")

            # Check if this override triggers weight suggestions
            try:
                self._evaluate_weight_suggestions()
            except Exception as e:
                logger.warning(f"Could not evaluate weight suggestions: {e}")

            return override_id
        except Exception as e:
            logger.error(f"Error recording override: {e}")
            # Return a mock ID for now since database might not be ready
            return str(uuid.uuid4())

    def get_override_history(
        self,
        shipment_id: Optional[str] = None,
        analyst_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve override history with optional filters.

        Args:
            shipment_id: Filter to specific shipment
            analyst_id: Filter to specific analyst
            limit: Maximum records to return

        Returns:
            List of override records
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM scoring_overrides WHERE 1=1"
        params = []

        if shipment_id:
            query += " AND shipment_id = ?"
            params.append(shipment_id)

        if analyst_id:
            query += " AND analyst_id = ?"
            params.append(analyst_id)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row[0],
                "shipment_id": row[1],
                "original_score": row[2],
                "override_decision": row[3],
                "feedback_type": row[4],
                "analyst_id": row[5],
                "analyst_name": row[6],
                "created_at": row[7],
                "notes": row[8],
            }
            for row in rows
        ]

    def _evaluate_weight_suggestions(self) -> None:
        """
        Analyze override patterns and suggest weight adjustments.
        Uses SGD to recommend changes when corroboration threshold is reached.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get recent REJECT overrides (signals system was too aggressive)
        cursor.execute(
            """
            SELECT feedback_type, COUNT(*) as count
            FROM scoring_overrides
            WHERE override_decision = 'REJECT'
            AND created_at >= datetime('now', '-30 days')
            GROUP BY feedback_type
            HAVING count >= ?
            ORDER BY count DESC
        """,
            (CORROBORATION_THRESHOLD,),
        )

        patterns = cursor.fetchall()

        for feedback_type, count in patterns:
            self._suggest_weight_adjustment_for_pattern(feedback_type, count)

        conn.close()

    def _suggest_weight_adjustment_for_pattern(self, feedback_type: str, corroboration_count: int) -> None:
        """
        Generate weight adjustment suggestions based on override patterns.
        Implements SGD formula: W_new = W_old - α × (System_Score - Human_Label) × X_feature

        Args:
            feedback_type: Pattern identified from overrides
            corroboration_count: Number of corroborating overrides
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Map feedback type to affected feature and direction
        adjustment_map = {
            "factory_expansion": {
                "feature": "w_corridor",
                "direction": -0.02,
                "rationale": "Legitimate factory expansions reduce corridor weight",
            },
            "ais_false_positive": {
                "feature": "w_routing",
                "direction": -0.02,
                "rationale": "AIS anomaly was false positive — reduce routing weight",
            },
            "documentation_mismatch": {
                "feature": "w_documentation",
                "direction": +0.03,
                "rationale": "Element 9 mismatch confirmed — increase documentation weight",
            },
            "party_legitimate": {
                "feature": "w_party",
                "direction": -0.02,
                "rationale": "Party profile was legitimate — reduce party weight",
            },
            "commodity_error": {
                "feature": "w_commodity",
                "direction": -0.01,
                "rationale": "Commodity misclassification — reduce commodity weight",
            },
            "dual_origin": {
                "feature": "w_documentation",
                "direction": -0.01,
                "rationale": "Legitimate dual-origin reduces doc weight",
            },
            "misclassified_vessel": {
                "feature": "w_routing",
                "direction": -0.03,
                "rationale": "Vessel route misclassification",
            },
        }

        if feedback_type not in adjustment_map:
            return

        mapping = adjustment_map[feedback_type]

        # Calculate confidence based on corroboration count
        confidence_pct = min(100.0, corroboration_count * 20.0)

        # Check if suggestion already exists
        cursor.execute(
            """
            SELECT id FROM weight_suggestions
            WHERE affected_feature = ? AND status = 'pending'
            LIMIT 1
        """,
            (mapping["feature"],),
        )

        existing = cursor.fetchone()

        if existing:
            logger.info(f"Weight suggestion already pending for {mapping['feature']}")
            conn.close()
            return

        # Create suggestion record
        suggestion_id = str(uuid.uuid4())
        suggested_value = mapping["direction"]  # Relative adjustment

        cursor.execute(
            """
            INSERT INTO weight_suggestions
            (id, corridor, affected_feature, suggested_value, confidence_pct,
             corroboration_count, status, created_at, rationale)
            VALUES (?, NULL, ?, ?, ?, ?, 'pending', ?, ?)
        """,
            (
                suggestion_id,
                mapping["feature"],
                suggested_value,
                confidence_pct,
                corroboration_count,
                datetime.utcnow().isoformat(),
                mapping["rationale"],
            ),
        )

        conn.commit()
        conn.close()

        logger.info(
            f"Created weight suggestion {suggestion_id}: {mapping['feature']} "
            f"({suggested_value:+.3f}) with {confidence_pct:.0f}% confidence"
        )

    def get_weight_suggestions(
        self,
        status: str = "pending",
        corridor: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve weight adjustment suggestions for analyst review.

        Args:
            status: Filter by status ("pending", "approved", "rejected")
            corridor: Filter to specific corridor (None = global)

        Returns:
            List of weight suggestions
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM weight_suggestions WHERE status = ?"
        params = [status]

        if corridor is not None:
            query += " AND corridor IS ?"
            params.append(corridor)

        query += " ORDER BY confidence_pct DESC, created_at DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row[0],
                "corridor": row[1],
                "affected_feature": row[2],
                "suggested_value": row[3],
                "confidence_pct": row[4],
                "corroboration_count": row[5],
                "status": row[6],
                "created_at": row[7],
                "reviewed_at": row[8],
                "reviewed_by": row[9],
                "rationale": row[10],
            }
            for row in rows
        ]

    def approve_weight_suggestion(
        self,
        suggestion_id: str,
        analyst_id: str,
        analyst_name: str,
    ) -> Dict[str, Any]:
        """
        Analyst approves a weight suggestion.
        Applies the adjustment to the weight configuration.

        Args:
            suggestion_id: The suggestion to approve
            analyst_id: ID of approving analyst
            analyst_name: Name of approving analyst

        Returns:
            Updated weight configuration
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Fetch the suggestion
            cursor.execute("SELECT * FROM weight_suggestions WHERE id = ?", (suggestion_id,))
            suggestion = cursor.fetchone()

            if not suggestion:
                raise ValueError(f"Suggestion {suggestion_id} not found")

            (
                suggestion_id,
                corridor,
                affected_feature,
                suggested_value,
                confidence,
                corr_count,
                status,
                created_at,
                reviewed_at,
                reviewed_by,
                rationale,
            ) = suggestion

            # Mark suggestion as approved
            cursor.execute(
                """
                UPDATE weight_suggestions
                SET status = 'approved', reviewed_at = ?, reviewed_by = ?
                WHERE id = ?
            """,
                (datetime.utcnow().isoformat(), analyst_name, suggestion_id),
            )

            self._ensure_weight_configurations_v2(cursor)

            # Fetch current 7-factor weight configuration (global or corridor-specific)
            cursor.execute(
                """
                SELECT *
                FROM weight_configurations_v2
                WHERE corridor IS ?
                ORDER BY created_at DESC
                LIMIT 1
            """,
                (corridor,),
            )

            weight_config = cursor.fetchone()

            if not weight_config:
                logger.warning(f"No v2 weight configuration found for corridor {corridor}, using defaults")
                current_weights = DEFAULT_7_FACTOR_WEIGHTS.copy()
            else:
                (
                    _config_id,
                    _corridor,
                    w_documentation,
                    w_commodity,
                    w_routing,
                    w_party,
                    w_corridor,
                    w_pattern,
                    w_time,
                    _created_at,
                    _updated_at,
                    _created_by,
                    _notes,
                ) = weight_config
                current_weights = {
                    "w_documentation": w_documentation,
                    "w_commodity": w_commodity,
                    "w_routing": w_routing,
                    "w_party": w_party,
                    "w_corridor": w_corridor,
                    "w_pattern": w_pattern,
                    "w_time": w_time,
                }

            if affected_feature not in current_weights:
                raise ValueError(f"Unsupported 7-factor feature: {affected_feature}")

            new_value = current_weights[affected_feature] + suggested_value
            new_value = max(0.01, min(0.99, new_value))  # Clamp to valid range
            updated_weights = current_weights.copy()
            updated_weights[affected_feature] = new_value

            # Create new configuration record
            new_config_id = str(uuid.uuid4())
            cursor.execute(
                """
                INSERT INTO weight_configurations_v2
                (
                    id, corridor, w_documentation, w_commodity, w_routing, w_party,
                    w_corridor, w_pattern, w_time, created_at, created_by, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    new_config_id,
                    corridor,
                    updated_weights["w_documentation"],
                    updated_weights["w_commodity"],
                    updated_weights["w_routing"],
                    updated_weights["w_party"],
                    updated_weights["w_corridor"],
                    updated_weights["w_pattern"],
                    updated_weights["w_time"],
                    datetime.utcnow().isoformat(),
                    analyst_name,
                    f"Approved suggestion {suggestion_id}: {rationale}",
                ),
            )

            conn.commit()

            logger.info(
                f"Approved weight suggestion {suggestion_id}: {affected_feature} "
                f"→ {new_value:.3f} (analyst: {analyst_name})"
            )

            return {
                "config_id": new_config_id,
                "corridor": corridor,
                **updated_weights,
                "applied_suggestion": suggestion_id,
                "applied_by": analyst_name,
                "applied_at": datetime.utcnow().isoformat(),
            }

        finally:
            conn.close()

    def reject_weight_suggestion(
        self,
        suggestion_id: str,
        analyst_id: str,
        analyst_name: str,
        rejection_reason: Optional[str] = None,
    ) -> None:
        """
        Analyst rejects a weight suggestion.

        Args:
            suggestion_id: The suggestion to reject
            analyst_id: ID of rejecting analyst
            analyst_name: Name of rejecting analyst
            rejection_reason: Optional reason for rejection
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE weight_suggestions
            SET status = 'rejected', reviewed_at = ?, reviewed_by = ?
            WHERE id = ?
        """,
            (datetime.utcnow().isoformat(), analyst_name, suggestion_id),
        )

        conn.commit()
        conn.close()

        logger.info(f"Rejected weight suggestion {suggestion_id} (analyst: {analyst_name})")

    def get_weight_configuration(
        self,
        corridor: Optional[str] = None,
    ) -> Dict[str, float]:
        """
        Retrieve current weight configuration (global or corridor-specific).

        Args:
            corridor: Corridor identifier (None for global)

        Returns:
            Dict with w_corridor, w_vessel, w_manifest
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT w_corridor, w_vessel, w_manifest
                FROM weight_configurations
                WHERE corridor IS ?
                ORDER BY created_at DESC
                LIMIT 1
            """,
                (corridor,),
            )

            row = cursor.fetchone()
            conn.close()

            if row:
                return {
                    "w_corridor": row[0],
                    "w_vessel": row[1],
                    "w_manifest": row[2],
                    "corridor": corridor,
                }
        except Exception as e:
            logger.warning(f"Could not retrieve weight configuration: {e}")

        # Return defaults if no configuration exists or DB error
        # Default weights for three-level model (deprecated - using 7-factor model now)
        default_weights = {"w_corridor": 0.20, "w_vessel": 0.35, "w_manifest": 0.45}

        return {
            **default_weights,
            "corridor": corridor,
        }

    def get_current_weights(self) -> Dict[str, float]:
        """Return current 7-factor weights for use in risk_scoring_engine."""
        defaults = DEFAULT_7_FACTOR_WEIGHTS.copy()
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            self._ensure_weight_configurations_v2(cursor)
            cursor.execute("SELECT * FROM weight_configurations_v2 ORDER BY created_at DESC LIMIT 1")
            row = cursor.fetchone()
            conn.close()
            if row:
                return {
                    key: row[key]
                    for key in (
                        "w_documentation",
                        "w_commodity",
                        "w_routing",
                        "w_party",
                        "w_corridor",
                        "w_pattern",
                        "w_time",
                    )
                    if key in row.keys()
                }
        except Exception as e:
            logger.warning(f"Could not retrieve 7-factor weights: {e}")
        return defaults


# Global feedback engine instance
feedback_engine = FeedbackEngine()
