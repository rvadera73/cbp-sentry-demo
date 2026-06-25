#!/usr/bin/env python3
"""
Enrich shipment records with realistic risk features for scoring.

Assigns ad_cvd_rate, dwell_days, unit_price_per_kg, element9_is_mismatch,
shipper_age_months, and price_variance_percent based on origin_country + hs_code
risk profiles.

Risk tier distribution:
  CRITICAL (~3%):  element9 mismatch + high AD/CVD + new shipper + dwell anomaly
  HIGH    (~12%):  high AD/CVD + some red flags
  MEDIUM  (~25%):  moderate indicators
  LOW     (~60%):  clean / low-tariff

Usage:
  python3 scripts/enrich_shipment_features.py [--dry-run]
"""
import argparse
import os
import random
import sys
from typing import Optional

import psycopg2

# ─────────────────────────────────────────────
# AD/CVD rates by origin_country + hs_family
# Stored as decimal (1.76 = 176%). 0 = no order.
# ─────────────────────────────────────────────
ADCVD_RATES = {
    ("CN", "7604"): 1.77,   # Aluminum extrusions — Commerce Order A-570-967
    ("VN", "7604"): 1.76,   # Aluminum extrusions — A-552-816
    ("CN", "8541"): 2.54,   # Solar panels — A-570-979
    ("MY", "8541"): 2.54,   # Solar panels (via transshipment concern)
    ("CN", "7210"): 1.99,   # Flat-rolled steel — A-570-901
    ("CN", "7225"): 2.65,   # Other flat-rolled steel — A-570-945
    ("KR", "7225"): 0.32,   # Korea steel — lower rate
    ("CN", "7610"): 1.77,   # Aluminum windows/doors
    ("CN", "7611"): 1.77,   # Aluminum reservoirs
    ("VN", "7210"): 0.72,   # Steel VN — moderate
    ("TH", "7210"): 0.25,   # Steel Thailand — lower
    ("IN", "7210"): 0.31,   # Steel India
    ("TW", "7210"): 0.15,   # Steel Taiwan
    ("CN", "6203"): 0.12,   # Men's garments — Section 301
    ("CN", "6204"): 0.12,   # Women's garments — Section 301
    ("VN", "6203"): 0.0,    # VN garments — PNTR, no AD
    ("VN", "6204"): 0.0,
    ("CN", "8471"): 0.25,   # Computers — Section 301 List 3
    ("CN", "8517"): 0.25,   # Phones — Section 301
}

# ─────────────────────────────────────────────
# Unit price benchmarks per HS family ($/kg)
# ─────────────────────────────────────────────
PRICE_BENCHMARKS = {
    "7604": 4.50,    # Aluminum extrusions
    "7210": 0.85,    # Flat-rolled steel
    "7225": 0.90,    # Other flat-rolled steel
    "7610": 5.20,    # Aluminum structures
    "7611": 4.80,    # Aluminum reservoirs
    "8541": 0.45,    # Solar panels
    "8471": 8.00,    # Computers
    "8517": 12.00,   # Phones/telecom
    "6203": 15.00,   # Men's garments
    "6204": 13.00,   # Women's garments
    "3004": 50.00,   # Pharmaceuticals
    "2709": 0.40,    # Petroleum
}

# High-risk origin+hs combinations that can produce CRITICAL/HIGH tiers
HIGH_RISK_PAIRS = {
    ("CN", "7604"), ("VN", "7604"),
    ("CN", "8541"), ("MY", "8541"),
    ("CN", "7210"), ("CN", "7225"),
    ("KH", "7604"), ("KH", "8541"),   # Cambodia — common transshipment
    ("KH", "7210"), ("KH", "7225"),
}

MEDIUM_RISK_ORIGINS = {"CN", "VN", "MY", "KH", "SG", "ID", "TH"}
LOW_RISK_ORIGINS    = {"CA", "JP", "KR", "TW", "IN", "MX", "PH"}


def get_adcvd_rate(origin: str, hs: str) -> float:
    hs4 = (hs or "")[:4]
    key = (origin, hs4)
    if key in ADCVD_RATES:
        return ADCVD_RATES[key]
    # Partial match on HS prefix
    for (o, h), r in ADCVD_RATES.items():
        if o == origin and hs4.startswith(h[:2]):
            return r * 0.5   # conservative estimate for related HS
    return 0.0


def assign_risk_tier(origin: str, hs: str, rng: random.Random) -> str:
    hs4 = (hs or "")[:4]
    is_high_pair = (origin, hs4) in HIGH_RISK_PAIRS
    is_medium_origin = origin in MEDIUM_RISK_ORIGINS

    if is_high_pair:
        return rng.choices(
            ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
            weights=[15, 35, 35, 15], k=1
        )[0]
    elif is_medium_origin:
        return rng.choices(
            ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
            weights=[2, 10, 40, 48], k=1
        )[0]
    else:
        return rng.choices(
            ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
            weights=[0, 3, 20, 77], k=1
        )[0]


def generate_features(origin: str, hs: str, tier: str, rng: random.Random) -> dict:
    hs4 = (hs or "")[:4]
    base_rate = get_adcvd_rate(origin, hs)
    benchmark = PRICE_BENCHMARKS.get(hs4)

    if tier == "CRITICAL":
        ad_cvd_rate   = max(base_rate, rng.uniform(1.20, 2.60))
        dwell_days    = rng.uniform(15, 28)
        shipper_age   = rng.randint(1, 5)
        e9_mismatch   = True
        e9_declared   = origin
        e9_actual     = "CN"  # typical transshipment end origin
        price_factor  = rng.uniform(0.10, 0.25)   # 10–25% of benchmark → severe undervaluation
    elif tier == "HIGH":
        ad_cvd_rate   = max(base_rate, rng.uniform(0.80, 1.80))
        dwell_days    = rng.uniform(9, 18)
        shipper_age   = rng.randint(3, 11)
        e9_mismatch   = rng.random() < 0.25
        e9_declared   = origin if e9_mismatch else None
        e9_actual     = "CN" if e9_mismatch else None
        price_factor  = rng.uniform(0.30, 0.60)
    elif tier == "MEDIUM":
        ad_cvd_rate   = max(base_rate * rng.uniform(0.5, 1.0), 0.0)
        dwell_days    = rng.uniform(4, 10)
        shipper_age   = rng.randint(8, 36)
        e9_mismatch   = False
        e9_declared   = None
        e9_actual     = None
        price_factor  = rng.uniform(0.60, 0.90)
    else:  # LOW
        ad_cvd_rate   = base_rate * rng.uniform(0.0, 0.4)
        dwell_days    = rng.uniform(1, 5)
        shipper_age   = rng.randint(24, 120)
        e9_mismatch   = False
        e9_declared   = None
        e9_actual     = None
        price_factor  = rng.uniform(0.85, 1.20)

    if benchmark and benchmark > 0:
        unit_price    = benchmark * price_factor
        price_var     = ((unit_price - benchmark) / benchmark) * 100
    else:
        unit_price    = None
        price_var     = None

    return {
        "ad_cvd_rate":             round(ad_cvd_rate, 4),
        "ad_cvd_applicable":       ad_cvd_rate > 0,
        "dwell_days":              round(dwell_days, 1),
        "shipper_age_months":      shipper_age,
        "element9_is_mismatch":    e9_mismatch,
        "element9_declared_country": e9_declared or origin,
        "element9_actual_country": e9_actual if e9_mismatch else origin,
        "unit_price_per_kg":       round(unit_price, 4) if unit_price else None,
        "price_variance_percent":  round(price_var, 2) if price_var is not None else None,
    }


def main():
    parser = argparse.ArgumentParser(description="Enrich shipment features for risk scoring")
    parser.add_argument("--dry-run", action="store_true", help="Show counts without writing")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    db_url = os.getenv("DATABASE_URL", "postgresql://sentry:sentry@localhost:5433/sentry")
    rng = random.Random(args.seed)

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, origin_country, hs_code
        FROM cbp_sentry.shipments
        WHERE id NOT LIKE 'DEMO-%'
          AND (ad_cvd_rate IS NULL OR ad_cvd_rate = 0)
        ORDER BY id
    """)
    rows = cur.fetchall()
    print(f"Shipments to enrich: {len(rows)}")

    tier_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    updates = []

    for (ship_id, origin, hs) in rows:
        origin = (origin or "US").strip()
        hs     = (hs or "").strip()
        tier   = assign_risk_tier(origin, hs, rng)
        feats  = generate_features(origin, hs, tier, rng)
        tier_counts[tier] += 1
        updates.append((ship_id, tier, feats))

    print("\nTier distribution:")
    for t, c in tier_counts.items():
        pct = c / len(rows) * 100 if rows else 0
        print(f"  {t:8s}: {c:4d}  ({pct:.1f}%)")

    if args.dry_run:
        print("\nDry-run — no changes written.")
        conn.close()
        return

    updated = 0
    for (ship_id, tier, f) in updates:
        cur.execute("""
            UPDATE cbp_sentry.shipments SET
                ad_cvd_rate               = %s,
                ad_cvd_applicable         = %s,
                dwell_days                = %s,
                shipper_age_months        = %s,
                element9_is_mismatch      = %s,
                element9_declared_country = %s,
                element9_actual_country   = %s,
                unit_price_per_kg         = %s,
                price_variance_percent    = %s,
                updated_at                = NOW()
            WHERE id = %s
        """, (
            f["ad_cvd_rate"],
            f["ad_cvd_applicable"],
            f["dwell_days"],
            f["shipper_age_months"],
            f["element9_is_mismatch"],
            f["element9_declared_country"],
            f["element9_actual_country"],
            f["unit_price_per_kg"],
            f["price_variance_percent"],
            ship_id,
        ))
        updated += 1
        if updated % 200 == 0:
            conn.commit()
            print(f"  ... committed {updated}/{len(rows)}")

    conn.commit()
    print(f"\n✅ Enriched {updated} shipments.")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
