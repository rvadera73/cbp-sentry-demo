#!/usr/bin/env python3
"""
Batch rescore all shipments using the updated risk scoring engine.
Populates calculated_risk_score, model_version, model_maturity, scored_at for every shipment.
Run after engine changes or reference data updates.
"""

import sys
import time
import requests

SENTRY_API = "http://localhost:8000"
BATCH_SIZE = 50

def get_all_shipment_ids():
    ids = []
    offset = 0
    page_size = 500
    while True:
        r = requests.get(f"{SENTRY_API}/api/shipments", params={"limit": page_size, "offset": offset}, timeout=30)
        r.raise_for_status()
        data = r.json()
        items = data.get("data") or []
        if not items:
            break
        ids.extend(s["id"] for s in items if isinstance(s, dict) and "id" in s)
        offset += page_size
        if len(items) < page_size:
            break
    return ids

def rescore(shipment_id: str) -> dict:
    r = requests.post(
        f"{SENTRY_API}/api/risk-scoring/comprehensive",
        json={"shipment_id": shipment_id},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()

def main():
    print("Fetching shipment IDs...", flush=True)
    ids = get_all_shipment_ids()
    total = len(ids)
    print(f"Found {total} shipments to rescore", flush=True)

    ok = fail = 0
    scores = []

    for i, sid in enumerate(ids, 1):
        try:
            result = rescore(sid)
            score = result.get("calculated_risk_score") or result.get("risk_score") or 0
            scores.append(score)
            ok += 1
            if i % BATCH_SIZE == 0 or i == total:
                avg = sum(scores[-BATCH_SIZE:]) / len(scores[-BATCH_SIZE:])
                print(f"  [{i}/{total}] ok={ok} fail={fail} last_avg_score={avg:.1f}", flush=True)
        except Exception as e:
            fail += 1
            print(f"  FAIL {sid}: {e}", flush=True)
            time.sleep(0.2)

    print(f"\nDone. {ok} rescored, {fail} failed", flush=True)
    if scores:
        print(f"Score distribution: min={min(scores):.1f} avg={sum(scores)/len(scores):.1f} max={max(scores):.1f}", flush=True)

if __name__ == "__main__":
    main()
