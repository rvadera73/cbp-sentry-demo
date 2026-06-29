"""
D2 — Risk Model v4.0 entity-score calibration harness (Track T-MLOps).

Builds a LABELED entity set and measures the separation the provisional
``entity_scorer`` weights/floors achieve, then reports the D3 validation gate.

LABELS
------
POSITIVES (should score HIGH, >= 60):
  * the 65 CBP-EAPA respondents  (cord_engine, Postgres ``cbp_sentry.eapa_cases``
    path; embedded fixture only if the DB is unreachable),
  * a sample of OFAC + OPEN-SANCTIONS sanctioned entities (CORD index),
  * the 18 UFLPA Entity List entries (cord_engine UFLPA-ENTITY-LIST source),
  * a sample of ICIJ / NOMINO-RISK offshore/fraud-risk entities (CORD index).
NEGATIVES (should NOT score MEDIUM+, < 40):
  * a sample of benign GLEIF entities (no enforcement flag, no graph signal).

Each subject is scored with ``entity_scorer.score_entity`` (graph ``signals=None``
— the enforcement-flag half scores on its own; the network/shell half is the
documented stub seam to T-Graph, so calibration here pins the enforcement floors
and weights that are live TODAY).

METRICS
-------
  * recall            = % positives with final_score >= HIGH (60)
  * false-positive-rate = % negatives with final_score >= MEDIUM (40)
  * per-flag tier distribution (CRITICAL/HIGH/MEDIUM/LOW per enforcement flag)

D3 GATE
-------
  PASS iff recall >= 0.90 AND false_positive_rate <= 0.10.

This is a PURE NEW module. It only READS entity_scorer / corridor_scorer
CONSTANTS (it does not change their logic). Any floor/weight tuning is applied
by minimally editing the CONSTANTS in entity_scorer.py and re-running this
harness; the rationale for any change is documented in code comments there.

Run inside the sentry-api container:
    docker exec -w /app -e PYTHONPATH=/app sentry-api python /app/calibrate_v4.py
"""
from __future__ import annotations

import json
import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from entity_scorer import (
    score_entity,
    TIER_HIGH,
    TIER_MEDIUM,
    OFAC_SOURCE,
    OPEN_SANCTIONS_SOURCE,
    ICIJ_SOURCE,
    NOMINO_RISK_SOURCE,
)
from v4_contracts import EAPA_SOURCE, UFLPA_SOURCE

# Separation thresholds (mirror entity_scorer tier cuts on the 0-100 scale).
HIGH = TIER_HIGH      # 60.0 — positive is "caught" at/above this
MEDIUM = TIER_MEDIUM  # 40.0 — negative is a false positive at/above this

# How many to sample per CORD-indexed positive/negative source (EAPA + UFLPA
# are taken in full because they are the small gold flag sets).
SAMPLE_PER_SANCTION_SOURCE = 60
SAMPLE_PER_FRAUD_SOURCE = 40
SAMPLE_NEGATIVES = 120

# D3 gate thresholds (decision §6.2 / §6.4 — recall lifted off v3.x 0.528).
GATE_MIN_RECALL = 0.90
GATE_MAX_FP_RATE = 0.10


# --------------------------------------------------------------------------- #
# Label-set construction
# --------------------------------------------------------------------------- #
def _cord_index_path() -> Optional[str]:
    p = os.getenv("CORD_INDEX_PATH", "/app/data/cord_index.db")
    return p if p and os.path.exists(p) else None


def _name_from_raw(raw: Dict[str, Any]) -> str:
    """Best-effort entity name across CORD source schemas (OPEN-SANCTIONS/ICIJ/
    NOMINO carry the name inside NAMES/NAME_LIST, not in the FTS name column)."""
    for key in ("NAMES", "NAME_LIST"):
        arr = raw.get(key)
        if isinstance(arr, list) and arr:
            prim = next((n for n in arr if n.get("NAME_TYPE") == "PRIMARY"), None) or arr[0]
            org = prim.get("NAME_ORG") or prim.get("NAME_FULL")
            if org:
                return str(org)
    for key in ("PRIMARY_NAME_ORG", "LEGAL_NAME_ORG", "NAME", "name", "Title"):
        v = raw.get(key)
        if v:
            return str(v)
    return ""


def _cord_rows(source: str, limit: int) -> List[Dict[str, Any]]:
    """Pull up to ``limit`` records for a CORD source, shaped as the entity dict
    ``score_entity`` consumes (data_source / name / raw_data)."""
    idx = _cord_index_path()
    if not idx:
        return []
    conn = sqlite3.connect(idx)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    out: List[Dict[str, Any]] = []
    try:
        cur.execute(
            "SELECT record_id, data_source, name_primary, country, raw_json "
            "FROM cord_fts WHERE data_source = ? LIMIT ?",
            (source, limit),
        )
        for row in cur.fetchall():
            try:
                raw = json.loads(row["raw_json"])
            except Exception:
                raw = {}
            name = row["name_primary"] or _name_from_raw(raw)
            out.append({
                "entity_id": f"{row['data_source']}:{row['record_id']}",
                "data_source": row["data_source"],
                "name": name or row["record_id"],
                "country": row["country"] or "",
                "raw_data": raw,
            })
    finally:
        conn.close()
    return out


def _eapa_positives() -> List[Dict[str, Any]]:
    """The 65 EAPA respondents via cord_engine (Postgres path). cord_engine
    builds CordFlagRecord-shaped dicts with DATA_SOURCE=CBP-EAPA / FLAG=eapa_respondent."""
    from cord_engine import get_cord_engine
    eng = get_cord_engine()
    out: List[Dict[str, Any]] = []
    for rec in eng.eapa_records():
        out.append({
            "entity_id": f"{rec['DATA_SOURCE']}:{rec['RECORD_ID']}",
            "data_source": rec["DATA_SOURCE"],
            "name": rec["PRIMARY_NAME_ORG"],
            "country": rec.get("COUNTRY", ""),
            "flag": rec.get("FLAG", ""),
            "raw_data": rec,
        })
    return out


def _uflpa_positives() -> List[Dict[str, Any]]:
    """The 18 UFLPA-ENTITY-LIST entries via cord_engine."""
    from cord_engine import get_cord_engine
    eng = get_cord_engine()
    out: List[Dict[str, Any]] = []
    for rec in eng.uflpa_records():
        out.append({
            "entity_id": f"{rec['DATA_SOURCE']}:{rec['RECORD_ID']}",
            "data_source": rec["DATA_SOURCE"],
            "name": rec["PRIMARY_NAME_ORG"],
            "country": rec.get("COUNTRY", ""),
            "flag": rec.get("FLAG", ""),
            "raw_data": rec,
        })
    return out


def build_labeled_set() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Return (positives, negatives), each entity tagged with ``_label_flag``
    naming the enforcement flag it is the gold example of."""
    positives: List[Dict[str, Any]] = []

    for e in _eapa_positives():
        e["_label_flag"] = "EAPA Respondent"
        positives.append(e)
    for e in _uflpa_positives():
        e["_label_flag"] = "UFLPA Entity List"
        positives.append(e)
    for src in (OFAC_SOURCE, OPEN_SANCTIONS_SOURCE):
        for e in _cord_rows(src, SAMPLE_PER_SANCTION_SOURCE):
            e["_label_flag"] = "OFAC / Sanctions Exposure"
            positives.append(e)
    for src in (ICIJ_SOURCE, NOMINO_RISK_SOURCE):
        for e in _cord_rows(src, SAMPLE_PER_FRAUD_SOURCE):
            e["_label_flag"] = "Fraud / Offshore Exposure"
            positives.append(e)

    # NEGATIVES: benign GLEIF legal entities (registry mass, no enforcement flag).
    negatives: List[Dict[str, Any]] = []
    for e in _cord_rows("GLEIF", SAMPLE_NEGATIVES):
        e["_label_flag"] = "benign (GLEIF)"
        negatives.append(e)

    return positives, negatives


# --------------------------------------------------------------------------- #
# Scoring + metrics
# --------------------------------------------------------------------------- #
def _score_all(entities: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], float, str]]:
    scored = []
    for e in entities:
        bd = score_entity(e, signals=None)  # graph stub seam (I-2) — None today
        scored.append((e, bd.final_score, bd.tier))
    return scored


def _tier_of(score: float) -> str:
    if score >= 80.0:
        return "CRITICAL"
    if score >= HIGH:
        return "HIGH"
    if score >= MEDIUM:
        return "MEDIUM"
    return "LOW"


def compute_metrics(
    pos_scored: List[Tuple[Dict[str, Any], float, str]],
    neg_scored: List[Tuple[Dict[str, Any], float, str]],
) -> Dict[str, Any]:
    n_pos = len(pos_scored)
    n_neg = len(neg_scored)
    caught = sum(1 for (_, s, _) in pos_scored if s >= HIGH)
    fp = sum(1 for (_, s, _) in neg_scored if s >= MEDIUM)
    recall = (caught / n_pos) if n_pos else 0.0
    fp_rate = (fp / n_neg) if n_neg else 0.0

    # Per-flag tier distribution.
    per_flag: Dict[str, Dict[str, Any]] = {}
    for (e, s, _t) in pos_scored + neg_scored:
        flag = e.get("_label_flag", "?")
        d = per_flag.setdefault(
            flag, {"count": 0, "CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0,
                   "min": 999.0, "max": -1.0, "sum": 0.0}
        )
        d["count"] += 1
        d[_tier_of(s)] += 1
        d["min"] = min(d["min"], s)
        d["max"] = max(d["max"], s)
        d["sum"] += s
    for d in per_flag.values():
        d["avg"] = round(d["sum"] / d["count"], 1) if d["count"] else 0.0
        d["min"] = round(d["min"], 1)
        d["max"] = round(d["max"], 1)
        del d["sum"]

    return {
        "n_positives": n_pos,
        "n_negatives": n_neg,
        "positives_caught_at_HIGH": caught,
        "negatives_flagged_at_MEDIUM": fp,
        "recall": round(recall, 4),
        "false_positive_rate": round(fp_rate, 4),
        "per_flag_tier_distribution": per_flag,
        "thresholds": {"HIGH": HIGH, "MEDIUM": MEDIUM},
    }


def d3_gate(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """D3 validation gate: PASS iff recall >= 0.90 AND fp_rate <= 0.10."""
    recall = metrics["recall"]
    fp_rate = metrics["false_positive_rate"]
    passed = (recall >= GATE_MIN_RECALL) and (fp_rate <= GATE_MAX_FP_RATE)
    return {
        "gate": "D3-validation",
        "passed": bool(passed),
        "recall": recall,
        "recall_threshold": GATE_MIN_RECALL,
        "recall_ok": recall >= GATE_MIN_RECALL,
        "false_positive_rate": fp_rate,
        "fp_rate_threshold": GATE_MAX_FP_RATE,
        "fp_rate_ok": fp_rate <= GATE_MAX_FP_RATE,
    }


def run_calibration() -> Dict[str, Any]:
    positives, negatives = build_labeled_set()
    pos_scored = _score_all(positives)
    neg_scored = _score_all(negatives)
    metrics = compute_metrics(pos_scored, neg_scored)
    gate = d3_gate(metrics)

    # A few worst-positive / worst-negative examples for the report.
    pos_sorted = sorted(pos_scored, key=lambda x: x[1])
    neg_sorted = sorted(neg_scored, key=lambda x: x[1], reverse=True)
    metrics["worst_positives"] = [
        {"name": e.get("name"), "flag": e.get("_label_flag"), "score": round(s, 1), "tier": t}
        for (e, s, t) in pos_sorted[:5]
    ]
    metrics["worst_negatives"] = [
        {"name": e.get("name"), "flag": e.get("_label_flag"), "score": round(s, 1), "tier": t}
        for (e, s, t) in neg_sorted[:5]
    ]
    return {"metrics": metrics, "d3_gate": gate}


def print_report(result: Dict[str, Any]) -> None:
    m = result["metrics"]
    g = result["d3_gate"]
    line = "=" * 72
    print(line)
    print("  RISK MODEL v4.0 — D2 ENTITY CALIBRATION REPORT")
    print(line)
    print(f"  positives (should be HIGH>={int(HIGH)}):  {m['n_positives']}")
    print(f"  negatives (should be <MEDIUM={int(MEDIUM)}): {m['n_negatives']}")
    print(f"  recall              = {m['recall']:.3f}  "
          f"({m['positives_caught_at_HIGH']}/{m['n_positives']} positives >= HIGH)")
    print(f"  false-positive-rate = {m['false_positive_rate']:.3f}  "
          f"({m['negatives_flagged_at_MEDIUM']}/{m['n_negatives']} negatives >= MEDIUM)")
    print(line)
    print("  PER-FLAG TIER DISTRIBUTION")
    print(f"  {'flag':<28} {'n':>4} {'CRIT':>5} {'HIGH':>5} {'MED':>4} {'LOW':>4} "
          f"{'min':>6} {'avg':>6} {'max':>6}")
    for flag, d in m["per_flag_tier_distribution"].items():
        print(f"  {flag:<28} {d['count']:>4} {d['CRITICAL']:>5} {d['HIGH']:>5} "
              f"{d['MEDIUM']:>4} {d['LOW']:>4} {d['min']:>6} {d['avg']:>6} {d['max']:>6}")
    print(line)
    if m["worst_positives"]:
        print("  WEAKEST POSITIVES (lowest-scoring):")
        for w in m["worst_positives"]:
            print(f"    {w['score']:>6}  {w['tier']:<8} [{w['flag']}] {w['name']}")
    if m["worst_negatives"]:
        print("  STRONGEST NEGATIVES (highest-scoring):")
        for w in m["worst_negatives"]:
            print(f"    {w['score']:>6}  {w['tier']:<8} [{w['flag']}] {w['name']}")
    print(line)
    print("  D3 VALIDATION GATE")
    print(f"    recall   {g['recall']:.3f} >= {g['recall_threshold']:.2f}  -> "
          f"{'OK' if g['recall_ok'] else 'FAIL'}")
    print(f"    fp_rate  {g['false_positive_rate']:.3f} <= {g['fp_rate_threshold']:.2f}  -> "
          f"{'OK' if g['fp_rate_ok'] else 'FAIL'}")
    print(f"    RESULT: {'*** PASS ***' if g['passed'] else '*** FAIL ***'}")
    print(line)


def main() -> Dict[str, Any]:
    result = run_calibration()
    print_report(result)
    return result


if __name__ == "__main__":
    main()
