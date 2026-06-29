"""
D1 — Risk Model v4.0 model registry (Track T-MLOps).

Registers the v4.0 scoring bundle as ONE versioned artifact (decision §6.1:
"single bundled version" — corridor + entity + shipment scores are aggregations
of the *same* factor model, so they register together and always agree).

The registered bundle pins, as a coherent unit:
  * model_version            : "v4.0"
  * factor_weights           : the live entity + corridor factor/flag weights
                               (read from entity_scorer / corridor_scorer CONSTANTS),
  * severity_floors          : entity_scorer.SEVERITY_FLOOR (enforcement-flag tier floors),
  * aggregation              : top_k_blend, k=5            (locked rule, §4.1),
  * apportionment            : by_shipment_count           (locked rule, §4.2),
  * cord_resolution_version  : the CORD/Senzing resolution snapshot version
                               (lineage dependency, §6.1 — re-resolving changes
                               scores even at fixed weights; env-driven placeholder),
  * feature_pipeline_version : the feature-pipeline version (env-driven placeholder),
  * calibration_metrics      : the D2 metrics + D3 gate from calibrate_v4,
  * registered_at            : caller-supplied ISO-8601 timestamp.

PERSISTENCE
-----------
  1. Always: a JSON artifact under ``services/api/data/v4_model_registry.json``
     (list of registered versions; newest registration wins "active").
  2. Best-effort: upsert a row into Postgres ``risk_scoring.model_versions``
     when reachable (the table is inspected first; if absent, JSON only). The
     full bundle is stored in that table's ``metadata`` JSONB column.

PUBLIC API
----------
  * register_version(metrics, registered_at=None, ...) -> dict (the bundle)
  * get_active_version() -> dict | None

Pure NEW module — reads scorer CONSTANTS only; modifies no existing file.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Read (never mutate) the live scorer constants so the registered bundle always
# reflects exactly what scored the calibration set.
import entity_scorer as _es
import corridor_scorer as _cs
from v4_contracts import AGGREGATION_RULE, AGGREGATION_K, APPORTIONMENT_RULE

MODEL_VERSION = "v4.0"
MODEL_ID = "cbp-sentry-risk-v4.0"
MODEL_NAME = "CBP Sentry Risk Model v4.0 (Multi-Level Factor Scoring)"

# Where the JSON artifact lives (alongside this module's data dir, with a
# container/env override for the running sentry-api at /app/data).
_DEFAULT_REGISTRY_JSON = str(Path(__file__).with_name("data") / "v4_model_registry.json")


def _registry_json_path() -> str:
    return os.getenv("V4_MODEL_REGISTRY_PATH", _DEFAULT_REGISTRY_JSON)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# Bundle assembly (read the LIVE scorer constants)
# --------------------------------------------------------------------------- #
def _factor_weights() -> Dict[str, Any]:
    """Snapshot the live entity + corridor factor/flag weights."""
    return {
        "entity": {
            "W_OFAC": _es.W_OFAC,
            "W_EAPA": _es.W_EAPA,
            "W_UFLPA": _es.W_UFLPA,
            "W_FRAUD": _es.W_FRAUD,
            "W_SHELL": _es.W_SHELL,
            "W_CENTRALITY": _es.W_CENTRALITY,
            "W_REACH": _es.W_REACH,
        },
        "corridor": {
            "W_PARTY": _cs.W_PARTY,
            "W_COMMODITY": _cs.W_COMMODITY,
            "W_ROUTING": _cs.W_ROUTING,
            "W_PATTERN": _cs.W_PATTERN,
            "W_TIME": _cs.W_TIME,
        },
    }


def _tier_thresholds() -> Dict[str, float]:
    return {
        "CRITICAL": _es.TIER_CRITICAL,
        "HIGH": _es.TIER_HIGH,
        "MEDIUM": _es.TIER_MEDIUM,
    }


def build_bundle(
    calibration_metrics: Dict[str, Any],
    registered_at: Optional[str] = None,
    cord_resolution_version: Optional[str] = None,
    feature_pipeline_version: Optional[str] = None,
) -> Dict[str, Any]:
    """Assemble the registry bundle from the live scorer constants + supplied
    calibration metrics. ``registered_at`` is caller-supplied (param); resolution
    / feature-pipeline versions fall back to env placeholders (§6.1 lineage)."""
    return {
        "model_id": MODEL_ID,
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "factor_weights": _factor_weights(),
        "severity_floors": dict(_es.SEVERITY_FLOOR),
        "tier_thresholds": _tier_thresholds(),
        "aggregation": {"rule": AGGREGATION_RULE, "k": AGGREGATION_K},
        "apportionment": {"rule": APPORTIONMENT_RULE},
        "cord_resolution_version": (
            cord_resolution_version
            or os.getenv("CORD_RESOLUTION_VERSION", "cord-resolution-2026.06.29")
        ),
        "feature_pipeline_version": (
            feature_pipeline_version
            or os.getenv("FEATURE_PIPELINE_VERSION", "feature-pipeline-v4.0.0")
        ),
        "calibration_metrics": calibration_metrics,
        "registered_at": registered_at or _now_iso(),
    }


# --------------------------------------------------------------------------- #
# JSON persistence
# --------------------------------------------------------------------------- #
def _read_json_registry() -> List[Dict[str, Any]]:
    path = _registry_json_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):  # tolerate a single-object legacy file
            return [data]
        return list(data) if isinstance(data, list) else []
    except Exception:
        return []


def _write_json_registry(versions: List[Dict[str, Any]]) -> str:
    path = _registry_json_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(versions, f, indent=2, sort_keys=False)
    os.replace(tmp, path)
    return path


# --------------------------------------------------------------------------- #
# Postgres persistence (best-effort upsert)
# --------------------------------------------------------------------------- #
def _pg_dsn() -> str:
    return os.environ.get(
        "DATABASE_URL", "postgresql://sentry:sentry-secret@sentry-db:5432/sentry"
    )


def _table_exists(cur, schema: str, table: str) -> bool:
    cur.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema=%s AND table_name=%s",
        (schema, table),
    )
    return cur.fetchone() is not None


def _upsert_postgres(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Upsert the bundle into ``risk_scoring.model_versions`` if reachable.

    The bundle's calibration metrics + locked params are stored in the JSONB
    ``metadata`` column; ``is_active`` is set true for v4.0 (older rows untouched).
    Returns a small status dict (never raises — JSON is the source of truth)."""
    try:
        import psycopg2
        from psycopg2.extras import Json
    except Exception as exc:  # psycopg2 absent
        return {"persisted": False, "reason": f"psycopg2 unavailable: {exc}"}

    try:
        conn = psycopg2.connect(_pg_dsn(), connect_timeout=5)
    except Exception as exc:
        return {"persisted": False, "reason": f"db unreachable: {exc}"}

    try:
        cur = conn.cursor()
        if not _table_exists(cur, "risk_scoring", "model_versions"):
            conn.close()
            return {"persisted": False, "reason": "risk_scoring.model_versions not present"}

        status = (
            "production"
            if bundle.get("calibration_metrics", {})
                     .get("d3_gate", {})
                     .get("passed")
            else "candidate"
        )
        # UNIQUE(model_id) → upsert. metadata carries the full v4.0 bundle.
        cur.execute(
            """
            INSERT INTO risk_scoring.model_versions
                (model_id, model_name, version, status, framework, model_type,
                 created_at, metadata, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, now(), %s, TRUE)
            ON CONFLICT (model_id) DO UPDATE SET
                model_name = EXCLUDED.model_name,
                version    = EXCLUDED.version,
                status     = EXCLUDED.status,
                framework  = EXCLUDED.framework,
                model_type = EXCLUDED.model_type,
                metadata   = EXCLUDED.metadata,
                is_active  = TRUE
            RETURNING model_version_id
            """,
            (
                bundle["model_id"],
                bundle["model_name"],
                bundle["model_version"],
                status,
                "rule-engine+xgboost-ensemble",
                "multi-level-factor-scoring",
                Json(bundle),
            ),
        )
        row = cur.fetchone()
        conn.commit()
        conn.close()
        return {
            "persisted": True,
            "table": "risk_scoring.model_versions",
            "model_version_id": row[0] if row else None,
            "status": status,
        }
    except Exception as exc:
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return {"persisted": False, "reason": f"upsert error: {exc}"}


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def register_version(
    metrics: Dict[str, Any],
    registered_at: Optional[str] = None,
    cord_resolution_version: Optional[str] = None,
    feature_pipeline_version: Optional[str] = None,
) -> Dict[str, Any]:
    """Register (or re-register) the v4.0 bundle with the supplied calibration
    metrics. Persists to JSON always, and to Postgres best-effort. Returns the
    bundle with an added ``_persistence`` status block."""
    bundle = build_bundle(
        calibration_metrics=metrics,
        registered_at=registered_at,
        cord_resolution_version=cord_resolution_version,
        feature_pipeline_version=feature_pipeline_version,
    )

    # JSON: replace any prior row for this model_id; newest goes last (active).
    versions = [v for v in _read_json_registry() if v.get("model_id") != bundle["model_id"]]
    versions.append(bundle)
    json_path = _write_json_registry(versions)

    pg_status = _upsert_postgres(bundle)

    out = dict(bundle)
    out["_persistence"] = {"json_path": json_path, "postgres": pg_status}
    return out


def get_active_version() -> Optional[Dict[str, Any]]:
    """Return the active v4.0 bundle. Prefers the JSON artifact (the always-on
    source of truth); the newest entry for MODEL_ID is the active one."""
    versions = [v for v in _read_json_registry() if v.get("model_id") == MODEL_ID]
    if versions:
        return versions[-1]
    # Fall back to Postgres if the JSON artifact is missing.
    try:
        import psycopg2
        conn = psycopg2.connect(_pg_dsn(), connect_timeout=5)
        cur = conn.cursor()
        cur.execute(
            "SELECT metadata FROM risk_scoring.model_versions "
            "WHERE model_id=%s AND is_active=TRUE ORDER BY created_at DESC LIMIT 1",
            (MODEL_ID,),
        )
        row = cur.fetchone()
        conn.close()
        if row and row[0]:
            return row[0] if isinstance(row[0], dict) else json.loads(row[0])
    except Exception:
        pass
    return None


def main() -> Dict[str, Any]:
    """CLI entry: run the D2 calibration, register the resulting bundle, print
    the registry artifact shape + persistence status."""
    from calibrate_v4 import run_calibration

    result = run_calibration()
    metrics = {"d2_metrics": result["metrics"], "d3_gate": result["d3_gate"]}
    bundle = register_version(metrics, registered_at=_now_iso())

    print("=" * 72)
    print("  RISK MODEL v4.0 — D1 REGISTRY ARTIFACT")
    print("=" * 72)
    # Print the bundle minus the (large) calibration metrics body for readability.
    shape = {k: v for k, v in bundle.items() if k != "calibration_metrics"}
    shape["calibration_metrics"] = {
        "d3_gate_passed": metrics["d3_gate"]["passed"],
        "recall": metrics["d2_metrics"]["recall"],
        "false_positive_rate": metrics["d2_metrics"]["false_positive_rate"],
    }
    print(json.dumps(shape, indent=2))
    print("=" * 72)
    print("  ACTIVE VERSION (round-trip via get_active_version):",
          (get_active_version() or {}).get("model_version"))
    print("=" * 72)
    return bundle


if __name__ == "__main__":
    main()
