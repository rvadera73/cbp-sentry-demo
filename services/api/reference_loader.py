"""
reference_loader.py — loads VN reference data CSVs into memory at startup.

Used by risk_scoring_engine.py to fix zero-scoring factors:
  - Commodity: real AD/CVD duty rates by HS code
  - Corridor: real Comtrade weight/value norms by HS code
  - Party: real incorporation dates for VN exporters
"""
from __future__ import annotations

import csv
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_REF_DIR = Path(__file__).parent / "reference"


def _load_csv(filename: str) -> list[dict]:
    path = _REF_DIR / filename
    if not path.exists():
        logger.warning(f"Reference file not found: {path}")
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@lru_cache(maxsize=1)
def _adcvd_table() -> Dict[str, dict]:
    """HS code prefix → {duty_rate_pct, order_number, order_type}"""
    rows = _load_csv("adcvd_vn.csv")
    table: Dict[str, dict] = {}
    for row in rows:
        hs = str(row.get("hs_code", "")).replace(".", "")[:6]
        if hs:
            try:
                rate = float(row.get("duty_rate_pct") or 0)
            except ValueError:
                rate = 0.0
            if hs not in table or rate > table[hs]["duty_rate_pct"]:
                table[hs] = {
                    "duty_rate_pct": rate,
                    "order_number": row.get("order_number", ""),
                    "order_type": row.get("order_type", "AD"),
                    "hs_description": row.get("hs_description", ""),
                }
    logger.info(f"Loaded {len(table)} AD/CVD HS entries from reference")
    return table


@lru_cache(maxsize=1)
def _corridor_table() -> Dict[str, dict]:
    """HS code → {avg_usd_per_kg (most recent year), total_kg, total_usd}"""
    rows = _load_csv("corridors_vn_us.csv")
    table: Dict[str, dict] = {}
    for row in rows:
        hs = str(row.get("hs_code", "")).replace(".", "")[:4]
        try:
            year = int(row.get("year", 0))
            avg = float(row.get("avg_usd_per_kg") or 0)
            kg = float(row.get("net_weight_kg") or 0)
            usd = float(row.get("trade_value_usd") or 0)
        except ValueError:
            continue
        if hs not in table or year > table[hs]["year"]:
            table[hs] = {"year": year, "avg_usd_per_kg": avg, "total_kg": kg, "total_usd": usd}
    logger.info(f"Loaded {len(table)} corridor HS entries from reference")
    return table


@lru_cache(maxsize=1)
def _entities_table() -> Dict[str, dict]:
    """Normalised company name → {age_months, incorporation_date, status}"""
    rows = _load_csv("entities_vn.csv")
    table: Dict[str, dict] = {}
    for row in rows:
        name = str(row.get("company_name", "")).lower().strip()
        if name:
            try:
                age = int(row.get("age_months") or 0)
            except ValueError:
                age = 0
            table[name] = {
                "age_months": age,
                "incorporation_date": row.get("incorporation_date", ""),
                "company_number": row.get("company_number", ""),
                "status": row.get("status", ""),
            }
    logger.info(f"Loaded {len(table)} VN entities from reference")
    return table


# ─── Public API ───────────────────────────────────────────────────────────────

def get_adcvd_rate(hs_code: str) -> Optional[float]:
    """Return the highest applicable AD/CVD duty rate for an HS code, or None."""
    hs = str(hs_code).replace(".", "")
    table = _adcvd_table()
    for prefix_len in (6, 4):
        key = hs[:prefix_len]
        if key in table:
            return table[key]["duty_rate_pct"]
    return None


def get_corridor_norms(hs_code: str) -> Optional[dict]:
    """Return Comtrade trade norms for a VN→US HS code, or None."""
    hs = str(hs_code).replace(".", "")[:4]
    return _corridor_table().get(hs)


def get_entity_age(company_name: str) -> Optional[int]:
    """Return known age_months for a VN company name, or None if not found."""
    if not company_name:
        return None
    key = company_name.lower().strip()
    table = _entities_table()
    if key in table:
        return table[key]["age_months"]
    # Partial match — check if any entity name is contained in the query
    for entity_name, data in table.items():
        if entity_name and (entity_name in key or key in entity_name):
            return data["age_months"]
    return None


def get_adcvd_order(hs_code: str) -> Optional[dict]:
    """Return full AD/CVD order info for an HS code."""
    hs = str(hs_code).replace(".", "")
    table = _adcvd_table()
    for prefix_len in (6, 4):
        key = hs[:prefix_len]
        if key in table:
            return table[key]
    return None


@lru_cache(maxsize=1)
def _adcvd_orders_by_country() -> Dict[tuple, dict]:
    """(origin_country, hs_prefix) → active AD/CVD order, from the live Federal
    Register pipeline output (reference/adcvd/<region>_<version>.csv written by
    scripts/fetch_adcvd.py)."""
    table: Dict[tuple, dict] = {}
    adcvd_dir = _REF_DIR / "adcvd"
    if not adcvd_dir.exists():
        return table
    for path in sorted(adcvd_dir.glob("*.csv")):
        try:
            with open(path, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    country = (row.get("origin_country") or "").strip().upper()
                    hs = str(row.get("hs_prefix") or "").replace(".", "").strip()
                    if not country or not hs:
                        continue
                    table[(country, hs)] = {
                        "order_type": (row.get("order_type") or "AD").strip(),
                        "case_number": row.get("case_number", ""),
                        "commodity": row.get("commodity", ""),
                        "source_doc": row.get("source_doc", ""),
                        "source_url": row.get("source_url", ""),
                        "publication_date": row.get("publication_date", ""),
                    }
        except OSError as exc:
            logger.warning(f"Could not read AD/CVD order file {path}: {exc}")
    logger.info(f"Loaded {len(table)} (country, HS) AD/CVD active orders from Federal Register pipeline")
    return table


def get_adcvd_order_by_country(origin_country: str, hs_code: str) -> Optional[dict]:
    """Return an active AD/CVD order for a (origin_country, HS) pair from the
    Federal Register pipeline, matching on HS prefix (longest first)."""
    if not origin_country:
        return None
    country = str(origin_country).strip().upper()
    hs = str(hs_code or "").replace(".", "")
    table = _adcvd_orders_by_country()
    for prefix_len in (6, 4, 2):
        key = (country, hs[:prefix_len])
        if key in table:
            return table[key]
    return None
