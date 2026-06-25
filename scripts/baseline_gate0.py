#!/usr/bin/env python3
"""
Gate 0 Interim Baseline Script
================================
Registers the Gate 0 rule engine model in the MLOps registry, batch-rescores
all shipments, snapshots the dataset, and records Gate 0 performance metrics.

Run from project root:
  python3 scripts/baseline_gate0.py [--dry-run]

This creates:
  1. risk_models row: gate0-rule-engine-v1.0
  2. dataset_baselines row: gate0-enriched-1396
  3. calculated_risk_score + model_version write-back to 1396 shipments
  4. performance_gate_results row: Gate 0 metrics
  5. risk_score_ledger entries for each scored shipment
"""

import sys
import os
import sqlite3
import json
import hashlib
import argparse
import logging
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "services" / "api"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("baseline_gate0")

DB_PATH = PROJECT_ROOT / "data" / "cbp_sentry.db"
WEIGHTS_DIR = PROJECT_ROOT / "services" / "api" / "models"

MODEL_VERSION = "gate0-rule-engine-v1.0"
DATASET_VERSION = "gate0-enriched-1396"
REFERRAL_THRESHOLD = 65
CRITICAL_THRESHOLD = 80


def get_conn():
    return sqlite3.connect(DB_PATH)


# ── Step 0: Ensure tables exist ───────────────────────────────────────────────

def ensure_tables(conn):
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS dataset_baselines (
            id TEXT PRIMARY KEY,
            version TEXT NOT NULL,
            model_version TEXT,
            gate TEXT,
            row_count INTEGER,
            feature_hash TEXT,
            feature_stats TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        )
    """)

    # Ensure risk_score_ledger has needed columns
    c.execute("""
        CREATE TABLE IF NOT EXISTS risk_score_ledger (
            id TEXT PRIMARY KEY,
            shipment_id TEXT NOT NULL,
            model_version TEXT NOT NULL,
            calculated_score REAL NOT NULL,
            scoring_method TEXT,
            confidence_interval TEXT,
            model_maturity INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Ensure performance_gate_results has needed columns
    c.execute("""
        CREATE TABLE IF NOT EXISTS performance_gate_results (
            id TEXT PRIMARY KEY,
            gate TEXT NOT NULL,
            model_version TEXT NOT NULL,
            threshold REAL,
            total_scored INTEGER,
            flagged_count INTEGER,
            critical_count INTEGER,
            high_count INTEGER,
            ppv_estimate REAL,
            recall_estimate REAL,
            fpr_estimate REAL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    logger.info("Tables verified/created")


# ── Step 1: Register model versions ──────────────────────────────────────────

def register_models(conn, dry_run=False):
    c = conn.cursor()

    # Check existing
    c.execute("SELECT id, status FROM risk_models")
    existing = {r[0]: r[1] for r in c.fetchall()}
    logger.info(f"Existing models: {existing}")

    # Register v2.1 legacy (if not already present with correct metadata)
    v21_weights = json.loads((WEIGHTS_DIR / "v21_legacy_weights.json").read_text())
    v21_row = {
        "id": "model-v2.1-legacy",
        "model_id": "v2.1",
        "version": "2.1",
        "name": "CBP Risk Model v2.1 (Legacy Rule-Based)",
        "status": "deprecated",
        "framework": "rule-based-deterministic",
        "model_type": "rule-based classifier",
        "feature_count": 3,
        "weights_sum": 1.10,
        "artifact_path": f"models/v21_legacy_weights.json",
        "metadata": json.dumps(v21_weights),
        "created_at": "2026-05-23T00:00:00Z",
        "deprecated_at": "2026-06-13T19:17:14Z",
        "updated_at": datetime.now().isoformat(),
    }

    # Register Gate 0 model
    gate0_weights = json.loads((WEIGHTS_DIR / "gate0_rule_engine_weights_v1.0.json").read_text())
    gate0_row = {
        "id": MODEL_VERSION,
        "model_id": "gate0-v1.0",
        "version": "gate0-1.0",
        "name": "CBP Sentry Gate 0 Rule Engine v1.0",
        "status": "production",
        "framework": "rule-engine-xgboost-delta",
        "model_type": "weighted rule classifier",
        "feature_count": 18,
        "weights_sum": 1.0,
        "artifact_path": f"models/gate0_rule_engine_weights_v1.0.json",
        "metadata": json.dumps(gate0_weights),
        "created_at": datetime.now().isoformat(),
        "deployed_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    if not dry_run:
        for row in [v21_row, gate0_row]:
            if row["id"] not in existing:
                c.execute("""
                    INSERT OR REPLACE INTO risk_models
                    (id, model_id, version, name, status, framework, model_type,
                     feature_count, weights_sum, artifact_path, metadata,
                     created_at, deployed_at, updated_at)
                    VALUES (:id, :model_id, :version, :name, :status, :framework,
                            :model_type, :feature_count, :weights_sum, :artifact_path,
                            :metadata, :created_at,
                            :deployed_at, :updated_at)
                """, {**row, "deprecated_at": row.get("deprecated_at")})
                logger.info(f"  Registered: {row['id']}")
            else:
                c.execute("""
                    UPDATE risk_models SET status=?, artifact_path=?, metadata=?,
                    deployed_at=COALESCE(deployed_at,?), updated_at=?
                    WHERE id=?
                """, (row["status"], row["artifact_path"], row["metadata"],
                      row.get("deployed_at"), row["updated_at"], row["id"]))
                logger.info(f"  Updated: {row['id']}")
        conn.commit()
    else:
        logger.info(f"  [DRY RUN] Would register: {[r['id'] for r in [v21_row, gate0_row]]}")


# ── Step 2: Dataset snapshot ──────────────────────────────────────────────────

def snapshot_dataset(conn, dry_run=False):
    c = conn.cursor()

    # Fetch feature columns for hashing
    c.execute("""
        SELECT id, risk_score, h1_score, h2_score, h3_score,
               ad_cvd_rate, dwell_days, element9_is_mismatch,
               shipper_age_months, origin_country, hs_code
        FROM shipments ORDER BY id
    """)
    rows = c.fetchall()
    row_count = len(rows)

    # SHA-256 hash of serialized feature data
    feature_str = json.dumps(rows, default=str)
    feature_hash = hashlib.sha256(feature_str.encode()).hexdigest()

    # Basic feature stats
    risk_scores = [r[1] for r in rows if r[1] is not None]
    dwell_days  = [r[5] for r in rows if r[5] is not None]
    stats = {
        "risk_score": {
            "count": len(risk_scores),
            "mean": round(sum(risk_scores)/len(risk_scores), 2) if risk_scores else 0,
            "min": round(min(risk_scores), 2) if risk_scores else 0,
            "max": round(max(risk_scores), 2) if risk_scores else 0,
            "pct65_plus": sum(1 for s in risk_scores if s >= 65),
            "pct80_plus": sum(1 for s in risk_scores if s >= 80),
        },
        "dwell_days": {
            "count": len(dwell_days),
            "mean": round(sum(dwell_days)/len(dwell_days), 2) if dwell_days else 0,
        },
        "total_shipments": row_count,
        "snapshotted_at": datetime.now().isoformat(),
    }

    logger.info(f"Dataset: {row_count} rows, hash={feature_hash[:16]}...")
    logger.info(f"  Risk score distribution: {stats['risk_score']}")

    if not dry_run:
        c.execute("""
            INSERT OR REPLACE INTO dataset_baselines
            (id, version, model_version, gate, row_count, feature_hash, feature_stats, notes)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            DATASET_VERSION,
            DATASET_VERSION,
            MODEL_VERSION,
            "gate0",
            row_count,
            feature_hash,
            json.dumps(stats),
            "Gate 0 interim baseline — 1396 enriched shipments with AD/CVD, dwell, ISF mismatch, shipper age features",
        ))
        conn.commit()
        logger.info(f"  Snapshot saved: {DATASET_VERSION}")
    else:
        logger.info(f"  [DRY RUN] Would save dataset snapshot")

    return stats


# ── Step 3: Batch rescore + write-back ───────────────────────────────────────

def batch_rescore(conn, dry_run=False):
    """
    Call the scoring engine for each shipment and write back:
      calculated_risk_score, model_version, risk_score_calculated_at, confidence_interval
    Also inserts a row in risk_score_ledger per shipment.
    """
    from risk_scoring_engine import RiskScoringEngine

    c = conn.cursor()
    c.execute("""
        SELECT id, manifest_id, shipper_name, consignee_name,
               origin_country, destination_country, hs_code,
               declared_value_usd, declared_weight_kg,
               vessel_name, vessel_imo, vessel_flag,
               dwell_days, ais_stuffing_country, port_calls,
               element9_is_mismatch, element9_confidence,
               element9_declared_country, element9_actual_country,
               shipper_age_months, shipper_country,
               ad_cvd_rate, ad_cvd_applicable,
               h1_score, h2_score, h3_score, risk_score
        FROM shipments
    """)
    cols = [d[0] for d in c.description]
    shipments = [dict(zip(cols, r)) for r in c.fetchall()]
    logger.info(f"Rescoring {len(shipments)} shipments...")

    engine = RiskScoringEngine()
    scored = []
    errors = 0

    for i, s in enumerate(shipments):
        try:
            # Add model_maturity field for the engine
            s["model_maturity"] = 15
            breakdown = engine.score_shipment(s)
            final_score = breakdown.final_score
            ci = breakdown.confidence_interval
            scored.append({
                "id": s["id"],
                "score": round(final_score, 2),
                "ci": ci,
                "method": breakdown.scoring_method,
            })
        except Exception as e:
            logger.warning(f"  Score failed for {s['id']}: {e}")
            errors += 1
            # Fallback: keep existing risk_score
            scored.append({
                "id": s["id"],
                "score": s.get("risk_score") or 0,
                "ci": "±17",
                "method": "rule_engine_fallback",
            })

        if (i + 1) % 100 == 0:
            logger.info(f"  Progress: {i+1}/{len(shipments)} scored ({errors} errors)")

    logger.info(f"Scoring complete: {len(scored)} scores, {errors} errors")

    if not dry_run:
        now = datetime.now().isoformat()
        for s in scored:
            c.execute("""
                UPDATE shipments
                SET calculated_risk_score=?,
                    model_version=?,
                    model_maturity=15,
                    risk_score_calculated_at=?,
                    confidence_interval=?
                WHERE id=?
            """, (s["score"], MODEL_VERSION, now, s["ci"], s["id"]))

            import uuid
            c.execute("""
                INSERT OR IGNORE INTO risk_score_ledger
                (id, shipment_id, model_version, calculated_score, scoring_method,
                 confidence_interval, model_maturity, created_at)
                VALUES (?,?,?,?,?,?,?,?)
            """, (str(uuid.uuid4()), s["id"], MODEL_VERSION,
                  s["score"], s["method"], s["ci"], 15, now))

        conn.commit()
        logger.info(f"  Write-back complete: {len(scored)} rows updated")
    else:
        sample = scored[:3]
        logger.info(f"  [DRY RUN] Sample scores: {sample}")

    return scored


# ── Step 4: Performance gate record ──────────────────────────────────────────

def record_performance(conn, scored, dry_run=False):
    import uuid
    total = len(scored)
    flagged = sum(1 for s in scored if s["score"] >= REFERRAL_THRESHOLD)
    critical = sum(1 for s in scored if s["score"] >= CRITICAL_THRESHOLD)
    high = sum(1 for s in scored if REFERRAL_THRESHOLD <= s["score"] < CRITICAL_THRESHOLD)

    # At 15% maturity on synthetic data: PPV/recall are estimates
    # True positives not known — these are synthetic baseline estimates
    ppv_estimate = 0.70   # 70% estimated PPV based on rule logic correctness
    recall_estimate = 0.65
    fpr_estimate = 0.30

    notes = (
        f"Gate 0 interim baseline on synthetic enriched dataset. "
        f"{critical} CRITICAL (≥{CRITICAL_THRESHOLD}), {high} HIGH (≥{REFERRAL_THRESHOLD}). "
        f"PPV/recall are model-design estimates — not validated against real EAPA outcomes. "
        f"Gate 1 exit requires validated PPV ≥0.70 on ≥200 real officer feedback records."
    )

    logger.info(f"Performance: {total} total, {flagged} flagged, {critical} critical, {high} high")
    logger.info(f"  Estimates: PPV={ppv_estimate}, Recall={recall_estimate}, FPR={fpr_estimate}")

    if not dry_run:
        conn.cursor().execute("""
            INSERT OR REPLACE INTO performance_gate_results
            (id, gate, model_version, threshold, total_scored, flagged_count,
             critical_count, high_count, ppv_estimate, recall_estimate, fpr_estimate,
             notes, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            str(uuid.uuid4()), "gate0", MODEL_VERSION, REFERRAL_THRESHOLD,
            total, flagged, critical, high,
            ppv_estimate, recall_estimate, fpr_estimate,
            notes, datetime.now().isoformat()
        ))
        conn.commit()
        logger.info("  Performance record saved")
    else:
        logger.info("  [DRY RUN] Would save performance record")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Gate 0 MLOps Baseline")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without writing to DB")
    args = parser.parse_args()

    logger.info(f"=== Gate 0 Baseline {'(DRY RUN) ' if args.dry_run else ''}===")
    conn = get_conn()

    logger.info("Step 0: Ensuring tables...")
    ensure_tables(conn)

    logger.info("Step 1: Registering model versions...")
    register_models(conn, args.dry_run)

    logger.info("Step 2: Snapshotting dataset...")
    stats = snapshot_dataset(conn, args.dry_run)

    logger.info("Step 3: Batch rescoring (may take 30-60s)...")
    scored = batch_rescore(conn, args.dry_run)

    logger.info("Step 4: Recording Gate 0 performance...")
    record_performance(conn, scored, args.dry_run)

    conn.close()

    logger.info("=== Baseline complete ===")
    logger.info(f"Model:   {MODEL_VERSION}")
    logger.info(f"Dataset: {DATASET_VERSION} ({stats['total_shipments']} rows)")
    logger.info(f"Scores:  {stats['risk_score']['pct65_plus']} ≥65, {stats['risk_score']['pct80_plus']} ≥80")
    if not args.dry_run:
        logger.info("Next: git tag v0.15-gate0-interim-baseline && git push --tags")


if __name__ == "__main__":
    main()
