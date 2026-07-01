"""data_pipelines.py — Data Pipelines admin registry + run ledger.

Backs the "Data Pipelines" admin tab. Provides:
  - a source registry  (risk_scoring.data_sources)
  - a run ledger        (risk_scoring.ingestion_runs)

Reuses the exact direct-psycopg2 pattern from main.py's Gate-1 feedback loop
(_gate1_conn / _ensure_gate1_table): same DATABASE_URL, risk_scoring schema,
CREATE ... IF NOT EXISTS, defensive callers wrap usage in try/except.

Endpoints live in main.py; this module owns the DDL, idempotent seed, CSV row
counts, and the status/contract shaping so main.py stays thin.
"""
from __future__ import annotations

import csv
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Same DB URL contract as main.py's Gate-1 feedback loop.
_PIPELINES_DB_URL = os.getenv(
    "DATABASE_URL", "postgresql://sentry:sentry-secret@sentry-db:5432/sentry"
)

# reference/ CSVs live next to this module (mirrors reference_loader._REF_DIR).
_REF_DIR = Path(__file__).parent / "reference"


def _pipelines_conn():
    """Open a direct psycopg2 connection to the risk_scoring schema.

    Mirrors main._gate1_conn(); defensive callers wrap usage in try.
    """
    import psycopg2

    conn = psycopg2.connect(_PIPELINES_DB_URL)
    return conn


def _ensure_pipeline_tables(cur) -> None:
    """CREATE IF NOT EXISTS the data_sources + ingestion_runs tables."""
    cur.execute("CREATE SCHEMA IF NOT EXISTS risk_scoring")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS risk_scoring.data_sources (
            id TEXT PRIMARY KEY,
            name TEXT,
            dataset_type TEXT,
            mode TEXT,
            schedule TEXT,
            endpoint_or_path TEXT,
            detail TEXT,
            gap_note TEXT,
            enabled BOOLEAN DEFAULT TRUE,
            updated_at TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS risk_scoring.ingestion_runs (
            run_id TEXT PRIMARY KEY,
            source_id TEXT,
            started_at TIMESTAMP,
            ended_at TIMESTAMP,
            status TEXT,
            rows_in INTEGER,
            rows_out INTEGER,
            message TEXT
        )
        """
    )


# ── Seed: the REAL current data sources (exact ids/values per spec) ───────────
# (id, name, dataset_type, mode, schedule, endpoint_or_path, detail, gap_note)
_SEED_SOURCES: List[tuple] = [
    (
        "manifest-filedrop",
        "Manifest (file-drop)",
        "manifest",
        "file",
        "on upload",
        "POST /api/ingest/manifest",
        "Uploaded CBP manifest spreadsheets (Excel/CSV). Parsed, deduped, scored.",
        "No public per-shipment CBP feed; sample/file-sourced.",
    ),
    (
        "vessel-vesselfinder",
        "Vessel / AIS (VesselFinder)",
        "vessel",
        "online",
        "on-demand",
        "api.vesselfinder.com",
        "Live AIS vessel tracking; dwell + port calls.",
        "On-demand only (no scheduled enrich yet).",
    ),
    (
        "isf-derived",
        "ISF Element 9 (derived)",
        "isf",
        "derived",
        "per shipment",
        "internal",
        "Element 9 declared-vs-actual stuffing derived from AIS + manifest.",
        "No public ISF feed exists — derived.",
    ),
    (
        "entity-cord",
        "Entity screening (CORD)",
        "entity",
        "file",
        "static",
        "cord-data/*.jsonl",
        "244K entities: GLEIF, OFAC, OpenSanctions, ICIJ, OpenOwnership.",
        "SE-Asia (VN/CN) coverage sparse; refresh not scheduled.",
    ),
    (
        "adcvd-fedreg",
        "AD/CVD orders (Federal Register)",
        "reference",
        "online",
        "weekly",
        "federalregister.gov/api/v1 + CBP AD/CVD data",
        "Active AD/CVD duty orders by HS+country.",
        "Fetcher coded (scripts/fetch_adcvd.py) but not scheduled.",
    ),
    (
        "comtrade",
        "Corridor trade norms (UN Comtrade)",
        "reference",
        "online",
        "quarterly",
        "comtrade.un.org/api",
        "VN->US $/kg + volume baselines for pricing anomaly.",
        "Fetcher not built yet; 7-row seed CSV.",
    ),
    (
        "eapa-cbp",
        "EAPA respondents (CBP)",
        "entity",
        "online",
        "monthly",
        "cbp.gov EAPA notices (scrape)",
        "Confirmed EAPA enforcement respondents.",
        "System data is synthetic; real list is scrape-only.",
    ),
]


def seed_sources(cur) -> None:
    """Idempotent upsert of the real current sources into data_sources.

    ON CONFLICT refreshes descriptive columns (name/detail/gap_note/...) but
    intentionally preserves operator-owned state (enabled, schedule) so a PATCH
    is not clobbered on the next boot/seed.
    """
    now = datetime.utcnow()
    for row in _SEED_SOURCES:
        cur.execute(
            """
            INSERT INTO risk_scoring.data_sources (
                id, name, dataset_type, mode, schedule,
                endpoint_or_path, detail, gap_note, enabled, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE, %s)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                dataset_type = EXCLUDED.dataset_type,
                mode = EXCLUDED.mode,
                endpoint_or_path = EXCLUDED.endpoint_or_path,
                detail = EXCLUDED.detail,
                gap_note = EXCLUDED.gap_note,
                updated_at = EXCLUDED.updated_at
            """,
            (*row, now),
        )


# ── CSV row counts (data files, excluding header) ─────────────────────────────

def _csv_row_count(path: Path) -> Optional[int]:
    """Count data rows (excluding header) in a CSV, or None if it doesn't exist."""
    if not path.exists():
        return None
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = sum(1 for _ in reader)
        return max(rows - 1, 0)  # drop header
    except OSError as exc:
        logger.warning(f"Could not read pipeline CSV {path}: {exc}")
        return None


def _adcvd_row_count() -> Optional[int]:
    """Total AD/CVD data rows across reference/adcvd/*.csv (Federal Register output)."""
    adcvd_dir = _REF_DIR / "adcvd"
    if not adcvd_dir.exists():
        return None
    total = 0
    found = False
    for path in sorted(adcvd_dir.glob("*.csv")):
        n = _csv_row_count(path)
        if n is not None:
            total += n
            found = True
    return total if found else None


def _comtrade_row_count() -> Optional[int]:
    """Corridor trade-norm rows from reference/corridors_vn_us.csv."""
    return _csv_row_count(_REF_DIR / "corridors_vn_us.csv")


def _eapa_row_count() -> Optional[int]:
    """EAPA respondent rows from reference/eapa_real.csv (created by another agent)."""
    return _csv_row_count(_REF_DIR / "eapa_real.csv")


# ── Run ledger helpers ────────────────────────────────────────────────────────

def latest_run_map(cur) -> Dict[str, Dict[str, Any]]:
    """Return {source_id: latest ingestion_run row} using the most recent
    started_at per source. Used to fill last_run_at / rows_last_run / status."""
    cur.execute(
        """
        SELECT DISTINCT ON (source_id)
            source_id, run_id, started_at, ended_at, status, rows_in, rows_out, message
        FROM risk_scoring.ingestion_runs
        ORDER BY source_id, started_at DESC
        """
    )
    out: Dict[str, Dict[str, Any]] = {}
    for r in cur.fetchall():
        out[r[0]] = {
            "run_id": r[1],
            "started_at": r[2].isoformat() if r[2] else None,
            "ended_at": r[3].isoformat() if r[3] else None,
            "status": r[4],
            "rows_in": r[5],
            "rows_out": r[6],
            "message": r[7],
        }
    return out


def insert_run(
    cur,
    source_id: str,
    started_at: datetime,
    ended_at: datetime,
    status: str,
    rows_in: Optional[int],
    rows_out: Optional[int],
    message: str,
) -> str:
    """Insert an ingestion_runs row and return the generated run_id."""
    run_id = str(uuid.uuid4())
    cur.execute(
        """
        INSERT INTO risk_scoring.ingestion_runs (
            run_id, source_id, started_at, ended_at, status, rows_in, rows_out, message
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (run_id, source_id, started_at, ended_at, status, rows_in, rows_out, message),
    )
    return run_id


def list_runs(cur, source_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Most-recent-first ingestion_runs for a source (limit 20 by default)."""
    cur.execute(
        """
        SELECT run_id, started_at, ended_at, status, rows_in, rows_out, message
        FROM risk_scoring.ingestion_runs
        WHERE source_id = %s
        ORDER BY started_at DESC
        LIMIT %s
        """,
        (source_id, limit),
    )
    runs = []
    for r in cur.fetchall():
        runs.append(
            {
                "run_id": r[0],
                "started_at": r[1].isoformat() if r[1] else None,
                "ended_at": r[2].isoformat() if r[2] else None,
                "status": r[3],
                "rows_in": r[4],
                "rows_out": r[5],
                "message": r[6],
            }
        )
    return runs


def fetch_sources(cur) -> List[Dict[str, Any]]:
    """Return all data_sources rows (registry order preserved via seed order)."""
    cur.execute(
        """
        SELECT id, name, dataset_type, mode, schedule,
               endpoint_or_path, detail, gap_note, enabled, updated_at
        FROM risk_scoring.data_sources
        """
    )
    rows = []
    for r in cur.fetchall():
        rows.append(
            {
                "id": r[0],
                "name": r[1],
                "dataset_type": r[2],
                "mode": r[3],
                "schedule": r[4],
                "endpoint_or_path": r[5],
                "detail": r[6],
                "gap_note": r[7],
                "enabled": bool(r[8]) if r[8] is not None else True,
                "updated_at": r[9].isoformat() if r[9] else None,
            }
        )
    # Preserve the curated seed order for a stable UI.
    order = {s[0]: i for i, s in enumerate(_SEED_SOURCES)}
    rows.sort(key=lambda x: order.get(x["id"], len(order)))
    return rows


# Default per-source status for sources whose health isn't computed live.
# vessel/isf/entity are wired into the running system -> healthy.
_DEFAULT_STATUS = {
    "vessel-vesselfinder": "healthy",
    "isf-derived": "healthy",
    "entity-cord": "healthy",
}


def compute_total_rows_and_status(
    source_id: str,
    shipment_count: Optional[int],
) -> tuple[Optional[int], str]:
    """Compute (total_rows, status) for a source using cheap live signals.

    shipment_count is passed in from main.py (data service /shipments count) so
    this module stays sync/DB-only and does no HTTP.
    """
    if source_id == "manifest-filedrop":
        total = shipment_count
        status = "healthy" if (total or 0) > 0 else "not_configured"
        return total, status

    if source_id == "adcvd-fedreg":
        total = _adcvd_row_count()
        return (total, "healthy") if total is not None else (None, "not_configured")

    if source_id == "comtrade":
        total = _comtrade_row_count()
        return (total, "healthy") if total is not None else (None, "not_configured")

    if source_id == "eapa-cbp":
        total = _eapa_row_count()
        if total is None:
            return 0, "not_configured"
        return total, "healthy"

    # vessel / isf / entity — wired subsystems, sensible healthy default.
    return None, _DEFAULT_STATUS.get(source_id, "healthy")
