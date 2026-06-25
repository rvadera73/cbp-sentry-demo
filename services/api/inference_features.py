"""
Single-shipment feature extractor for XGBoost inference.

Computes the same 36 clean features used during training from a raw shipment
dict, using precomputed reference statistics for any dataset-dependent transforms.
"""

import json
import math
import os
from pathlib import Path
from typing import Dict, List

import numpy as np

_STATS = None
_REF_STATS_PATH = Path(os.environ.get("MODEL_DIR", "/home/rahulvadera/cbp-sentry/models")) / "inference_ref_stats.json"


def _load_stats():
    global _STATS
    if _STATS is None:
        if _REF_STATS_PATH.exists():
            with open(_REF_STATS_PATH) as f:
                _STATS = json.load(f)
        else:
            _STATS = {}
    return _STATS


HIGH_RISK_COUNTRIES = {"CN", "IR", "KP", "SY", "CU", "VE", "RU", "BY", "MM"}
TRANSSHIPMENT_HUBS  = {"SG", "MY", "HK", "AE", "PA", "KH", "TH"}
HIGH_RISK_ROUTES    = {("CN","IR"), ("CN","SY"), ("KP","CN"), ("VE","US"),
                       ("IR","US"), ("SY","US"), ("CU","US")}
CONTROLLED_HS = {
    "8471.30": 0.8, "8517.62": 0.9, "8542.31": 0.95, "8534.30": 0.7,
    "9005.80": 0.85, "9030.82": 0.8, "7308.90": 0.6, "7610.10": 0.65,
}
DUAL_USE_HS    = {"8471.30", "8517.62", "8542.31", "9005.80", "9030.82"}
ELECTRONICS_HS = {"8471.30", "8517.62", "8542.31", "8534.30"}
PRECIOUS_PREFIXES = ("7108", "7109", "7110", "7111", "7112")
TECH_ORIGINS   = {"CN", "JP", "KR", "TW", "MY", "SG", "TH"}
NEAR_ORIGINS   = {"US", "CA", "MX"}
FAR_ORIGINS    = {"CN", "JP", "IN", "VN", "TH"}
VESSEL_RISK_PATTERNS = ("panama", "liberia", "cambodia", "marshall")
GENERIC_NAME_PATTERNS = ("Corp", "LLC", "Ltd", "Inc", "Trading", "Export")
SANCTIONED_TERMS = ("North Korea", "Iranian", "Syria", "Crimea", "Donetsk")
STATUS_RISK = {"legitimate": 0.0, "under_review": 0.5, "flagged": 0.8, "alert": 1.0}


def _f(shipment: Dict, key: str, default=None):
    """Safe field access."""
    v = shipment.get(key)
    return default if (v is None or v == "" or (isinstance(v, float) and math.isnan(v))) else v


def extract_clean_features(shipment: Dict, feature_names: List[str]) -> np.ndarray:
    """
    Map a raw shipment dict to a numpy feature vector aligned to feature_names.

    Args:
        shipment: Raw shipment dict (same fields as training_data.csv)
        feature_names: Ordered list of feature names from score_calibration.json

    Returns:
        1-D float64 numpy array of length len(feature_names)
    """
    stats = _load_stats()
    all_feats = _compute_all_features(shipment, stats)
    return np.array([all_feats.get(name, 0.0) for name in feature_names], dtype=np.float64)


def _compute_all_features(shipment: Dict, stats: Dict) -> Dict[str, float]:
    feats: Dict[str, float] = {}

    # ── Raw fields ──────────────────────────────────────────────────────────
    origin  = str(_f(shipment, "origin_country", "") or "").upper()
    dest    = str(_f(shipment, "destination_country", "") or "").upper()
    shipper_c = str(_f(shipment, "shipper_country", "") or "").upper()
    consignee_c = str(_f(shipment, "consignee_country", "") or "").upper()
    shipper_n = str(_f(shipment, "shipper_name", "") or "")
    consignee_n = str(_f(shipment, "consignee_name", "") or "")
    hs = str(_f(shipment, "hs_code", "") or "")
    vessel = str(_f(shipment, "vessel_name", "") or "")
    vessel_imo = str(_f(shipment, "vessel_imo", "") or "")
    val = float(_f(shipment, "declared_value_usd", 0) or 0)
    wt  = float(_f(shipment, "declared_weight_kg", 1) or 1)
    dwell = float(_f(shipment, "dwell_days", 0) or 0)
    shipper_age = float(_f(shipment, "shipper_age_months", 24) or 24)
    status = str(_f(shipment, "status", "under_review") or "under_review")

    # ── DOCUMENTATION features ──────────────────────────────────────────────
    feats["DOCUMENTATION_001_element9_mismatch"] = float(bool(_f(shipment, "element9_is_mismatch", False)))

    manifest_present = sum([
        1 if shipper_n else 0, 1 if consignee_n else 0,
        1 if hs else 0, 1 if vessel else 0,
    ])
    feats["DOCUMENTATION_003_manifest_completeness"] = manifest_present / 4.0

    critical_missing = sum([1 if not shipper_c else 0, 1 if not origin else 0, 1 if not vessel_imo else 0])
    feats["DOCUMENTATION_004_missing_fields_pct"] = critical_missing / 3.0

    feats["DOCUMENTATION_005_value_weight_anomaly"] = 0.0  # needs population stats — zero for now

    feats["DOCUMENTATION_006_hs_code_control_level"] = float(CONTROLLED_HS.get(hs, 0.0))

    feats["DOCUMENTATION_007_shipper_consignee_mismatch"] = float(shipper_c != consignee_c)

    feats["DOCUMENTATION_008_origin_shipper_mismatch"]  = float(origin != shipper_c)

    cc_len = (int(origin != shipper_c) + int(shipper_c != consignee_c) + int(consignee_c != dest))
    feats["DOCUMENTATION_009_country_chain_length"] = cc_len / 3.0

    feats["DOCUMENTATION_010_filing_status_risk"] = STATUS_RISK.get(status.lower(), 0.3)

    feats["DOCUMENTATION_011_dwell_time_zscore"] = 0.0  # needs population stats

    all_fields_present = sum([
        1 if shipper_n else 0, 1 if consignee_n else 0, 1 if hs else 0,
        1 if vessel else 0, 1 if val else 0, 1 if wt else 0,
    ])
    feats["DOCUMENTATION_012_field_count_ratio"] = all_fields_present / 6.0

    # ── ROUTING features ────────────────────────────────────────────────────
    feats["ROUTING_001_hub_destination"] = float(dest in TRANSSHIPMENT_HUBS)

    feats["ROUTING_002_origin_dest_distance"] = float(origin != dest)

    feats["ROUTING_003_vessel_flag_risk"] = float(
        any(p in vessel.lower() for p in VESSEL_RISK_PATTERNS)
    )

    feats["ROUTING_004_dwell_time_quartile"] = 0.5  # neutral; proper value needs Q25/Q75

    feats["ROUTING_005_multi_port_routing"] = float(shipper_c != origin)

    try:
        imo_num = float(vessel_imo) if vessel_imo.isdigit() else float("nan")
    except Exception:
        imo_num = float("nan")
    imo_med = stats.get("imo_med", 9000000.0)
    imo_std = stats.get("imo_std", 1000000.0)
    if not math.isnan(imo_num):
        imo_z = min(abs((imo_num - imo_med) / (imo_std + 1)) / 5.0, 1.0)
    else:
        imo_z = 0.0
    feats["ROUTING_006_vessel_condition_score"] = imo_z

    origin_freq = stats.get("origin_freq", {})
    feats["ROUTING_007_origin_frequency"] = float(origin_freq.get(origin, 0.0))

    complex_routing = int(origin != shipper_c) + int(shipper_c != consignee_c) + int(consignee_c != dest)
    feats["ROUTING_008_complex_routing"] = float(complex_routing >= 2)

    feats["ROUTING_009_transshipment_corridor"] = float(
        shipper_c in TRANSSHIPMENT_HUBS or origin in TRANSSHIPMENT_HUBS
    )

    feats["ROUTING_010_destination_mismatch"] = float(consignee_c != dest)

    # ── COMMODITY features ──────────────────────────────────────────────────
    feats["COMMODITY_001_hs_control_level"] = float(CONTROLLED_HS.get(hs, 0.0))

    value_q75 = stats.get("value_q75", 352742.0)
    feats["COMMODITY_002_high_value_flag"] = float(val > value_q75)

    feats["COMMODITY_003_electronics_flag"] = float(hs in ELECTRONICS_HS)

    feats["COMMODITY_004_precious_materials"] = float(hs.startswith(PRECIOUS_PREFIXES))

    feats["COMMODITY_005_unit_price_anomaly"] = 0.0  # needs population stats

    weight_q25 = stats.get("weight_q25", 25111.0)
    weight_q75 = stats.get("weight_q75", 72886.0)
    feats["COMMODITY_006_weight_anomaly"] = float(wt > weight_q75 * 1.5 or wt < weight_q25 * 0.5)

    feats["COMMODITY_007_commodity_origin_risk"] = float(hs in ELECTRONICS_HS and origin not in TECH_ORIGINS)

    feats["COMMODITY_008_dual_use_equipment"] = float(hs in DUAL_USE_HS)

    feats["COMMODITY_009_commodity_frequency"] = 0.0  # needs freq table

    feats["COMMODITY_010_restricted_destination_match"] = float(
        dest in HIGH_RISK_COUNTRIES and hs in DUAL_USE_HS
    )

    # ── CORRIDOR features ───────────────────────────────────────────────────
    feats["CORRIDOR_001_origin_risk_score"]      = 0.95 if origin in HIGH_RISK_COUNTRIES else 0.15
    feats["CORRIDOR_002_destination_risk_score"] = 0.95 if dest in HIGH_RISK_COUNTRIES else 0.05
    feats["CORRIDOR_003_shipper_risk_score"]     = (
        0.95 if shipper_c in HIGH_RISK_COUNTRIES else (0.7 if shipper_c in TRANSSHIPMENT_HUBS else 0.15)
    )

    complexity = int(origin != shipper_c) + int(shipper_c != consignee_c) + int(consignee_c != dest)
    feats["CORRIDOR_004_supply_chain_complexity"] = complexity / 3.0

    feats["CORRIDOR_005_high_risk_route"] = float((origin, dest) in HIGH_RISK_ROUTES)

    feats["CORRIDOR_006_se_asia_hub_risk"] = float(
        shipper_c in {"SG","MY","TH","VN","ID","PH"} or origin in {"SG","MY","TH","VN","ID","PH"}
    )

    feats["CORRIDOR_007_china_origin_indicator"] = float(origin == "CN")

    feats["CORRIDOR_008_hong_kong_route"] = float("HK" in {origin, shipper_c, dest})

    corridor_key = f"{origin}-{dest}"
    corridor_freq = stats.get("corridor_freq", {})
    feats["CORRIDOR_009_corridor_frequency"] = float(corridor_freq.get(corridor_key, 0.0))

    feats["CORRIDOR_010_panama_jurisdiction"] = float(shipper_c == "PA")

    feats["CORRIDOR_011_geographic_distance"] = (
        0.1 if origin in NEAR_ORIGINS else (0.9 if origin in FAR_ORIGINS else 0.5)
    )

    feats["CORRIDOR_012_sanctioned_shipper"] = float(
        any(t.lower() in shipper_n.lower() for t in SANCTIONED_TERMS)
    )
    feats["CORRIDOR_013_sanctioned_consignee"] = float(
        any(t.lower() in consignee_n.lower() for t in SANCTIONED_TERMS)
    )

    feats["CORRIDOR_014_multi_hop_routing"] = float(
        origin != shipper_c and shipper_c != dest
    )

    feats["CORRIDOR_015_combined_corridor_risk"] = (
        feats["CORRIDOR_001_origin_risk_score"]
        + feats["CORRIDOR_002_destination_risk_score"]
        + feats["CORRIDOR_003_shipper_risk_score"]
    ) / 3.0

    # ── PARTY features ──────────────────────────────────────────────────────
    age_max = stats.get("shipper_age_max", 120.0)
    feats["PARTY_001_shipper_age_risk"] = max(0.0, min(1.0, 1.0 - shipper_age / (age_max + 1.0)))

    feats["PARTY_002_new_shipper_flag"]      = float(shipper_age < 12)
    feats["PARTY_003_very_new_shipper_flag"] = float(shipper_age < 6)

    feats["PARTY_004_shipper_name_opacity"] = float(
        len(shipper_n) < 5 or "Unknown" in shipper_n or "N/A" in shipper_n
    )

    generic_score = sum(1 for p in GENERIC_NAME_PATTERNS if p in shipper_n) / len(GENERIC_NAME_PATTERNS)
    feats["PARTY_005_generic_name_score"] = float(generic_score)

    legit_countries = {"US","CA","MX","JP","DE","GB","AU","SG"}
    feats["PARTY_006_shipper_legitimacy_score"] = float(shipper_c in legit_countries)

    feats["PARTY_007_shipper_consignee_match"] = float(shipper_n == consignee_n)

    feats["PARTY_008_shipper_repeat_frequency"] = 0.0  # needs frequency table

    location_mismatch = int(shipper_c != origin) + int(consignee_c != dest)
    feats["PARTY_009_location_mismatch_score"] = location_mismatch / 2.0

    opacity = feats["PARTY_004_shipper_name_opacity"]
    generic = feats["PARTY_005_generic_name_score"]
    legit   = feats["PARTY_006_shipper_legitimacy_score"]
    feats["PARTY_010_combined_party_risk"] = min(1.0, (opacity + generic + (1.0 - legit)) / 3.0)

    return feats
