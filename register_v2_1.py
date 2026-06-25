#!/usr/bin/env python3
"""
Register v2.1 (deprecated rule-based model) in the database
"""

import sqlite3
import uuid
from datetime import datetime

DB_PATH = "/home/rahulvadera/cbp-sentry/data/cbp_sentry.db"

def register_v2_1():
    """Insert v2.1 into risk_models table"""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Generate a unique model ID
    model_id = f"model-v2.1-{uuid.uuid4().hex[:8]}"
    v2_1_id = "v2.1"

    # Insert v2.1 as deprecated rule-based model
    cursor.execute("""
        INSERT OR REPLACE INTO risk_models
        (id, model_id, version, name, status, framework, model_type,
         feature_count, weights_sum, created_at, created_by, deprecated_at)
        VALUES
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        model_id,
        v2_1_id,
        "2.1",
        "CBP Risk Model v2.1 (Legacy)",
        "deprecated",
        "rule-based",
        "rule-based classifier",
        72,
        1.1,  # 110% weight sum (legacy overweighting)
        "2026-05-23T00:00:00Z",  # Creation date
        "system",
        datetime.utcnow().isoformat() + "Z"
    ))

    conn.commit()
    conn.close()

    print(f"✅ v2.1 registered in database")
    print(f"   Model ID: {model_id}")
    print(f"   Status: deprecated")
    print(f"   Framework: rule-based")
    print(f"   Weights sum: 1.1 (110%)")

if __name__ == "__main__":
    register_v2_1()
