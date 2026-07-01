"""Excel manifest parsing and normalization"""

import re
import pandas as pd
from io import BytesIO
from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


def parse_excel_manifest(file_content: bytes) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parse Excel manifest file and extract shipment rows.
    Returns: (parsed_rows, errors)
    """
    try:
        # Try reading as Excel first
        df = pd.read_excel(BytesIO(file_content))
    except Exception as e:
        logger.error(f"Failed to parse Excel: {e}")
        return [], [f"Failed to parse file: {str(e)}"]

    errors = []
    rows = []

    # Expected column mappings (case-insensitive, handles both spaces and underscores)
    column_map = {
        "manifest_id": ["manifest_id", "manifest id", "mnf_id", "ref_id"],
        "shipper": ["shipper", "shipper_name", "shipper name", "exporter", "supplier"],
        "consignee": ["consignee", "consignee_name", "consignee name", "importer", "buyer"],
        "origin_country": [
            "origin",
            "origin_country",
            "origin country",
            "country_of_origin",
            "country of origin",
            "export_country",
            "export country",
        ],
        "destination_country": [
            "destination",
            "destination_country",
            "destination country",
            "import_country",
            "import country",
            "consignee_country",
            "consignee country",
        ],
        "hs_code": [
            "hs_code",
            "hs code",
            "hts_code",
            "hts code",
            "commodity_code",
            "commodity code",
            "product_code",
            "product code",
        ],
        "value": [
            "value",
            "declared_value",
            "declared value",
            "value_usd",
            "value usd",
            "fob_value",
            "fob value",
            "declared_value_usd",
            "declared value usd",
        ],
        "weight": [
            "weight",
            "weight_kg",
            "weight kg",
            "net_weight",
            "net weight",
            "declared_weight",
            "declared weight",
            "declared_weight_kg",
            "declared weight kg",
        ],
        "description": ["description", "product_description", "product description", "commodity"],
        "vessel_name": [
            "vessel",
            "vessel_name",
            "vessel name",
            "ship_name",
            "ship name",
            "carrying_vessel",
            "carrying vessel",
        ],
        "vessel_imo": ["vessel_imo", "vessel imo", "imo", "imo_number"],
        "vessel_flag": ["vessel_flag", "vessel flag", "flag_state", "flag state"],
        "dwell_days": ["dwell_days", "dwell days", "dwell_time"],
        "ais_stuffing_country": ["ais_stuffing_country", "ais stuffing country", "ais_country", "stuffing_country"],
        "port_calls": ["port_calls", "port calls", "ports", "port_list"],
        "element9_is_mismatch": ["element9_is_mismatch", "element9 is mismatch", "isf_mismatch", "isf element 9", "isf element 9 mismatch"],
        "element9_declared_country": ["element9_declared_country", "element9 declared country", "isf_declared_country"],
        "element9_actual_country": ["element9_actual_country", "element9 actual country", "isf_actual_country"],
        "shipper_age_months": ["shipper_age_months", "shipper age months", "shipper age", "entity age"],
        "ad_cvd_rate": ["ad_cvd_rate", "ad cvd rate", "duty_rate", "duty rate"],
        "ad_cvd_applicable": ["ad_cvd_applicable", "ad cvd applicable", "duty_applicable", "has_duty"],
        "risk_score": ["risk_score", "risk score", "score"],
    }

    # Normalize column names: lowercase + strip ALL punctuation to single spaces
    # (handles "AD/CVD Rate", "ISF Element 9 Mismatch", underscores, double spaces)
    # so aliases match reliably regardless of header formatting.
    def _norm(s: Any) -> str:
        return re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()

    df_columns_normalized = {_norm(col): col for col in df.columns}
    found_columns = {}

    for target, aliases in column_map.items():
        for alias in aliases:
            if _norm(alias) in df_columns_normalized:
                found_columns[target] = df_columns_normalized[_norm(alias)]
                break

    if "shipper" not in found_columns or "consignee" not in found_columns:
        errors.append("Missing required columns: shipper and consignee")
        return [], errors

    # Parse rows
    for idx, row in df.iterrows():
        try:
            # Helper to safely get and convert values
            def safe_str(val, default=""):
                return str(val).strip() if val and str(val).strip() not in ["", "nan", "None"] else default

            def safe_float(val, default=None):
                try:
                    v = float(val) if val else None
                    return v if v else default
                except:
                    return default

            def safe_int(val, default=None):
                try:
                    v = int(val) if val else None
                    return v if v else default
                except:
                    return default

            parsed_row = {
                "rowNumber": idx + 1,
                "manifest_id": safe_str(row.get(found_columns.get("manifest_id", ""), "")) or None,
                "shipper": safe_str(row.get(found_columns.get("shipper", ""), "Unknown"), "Unknown"),
                "consignee": safe_str(row.get(found_columns.get("consignee", ""), "Unknown"), "Unknown"),
                "origin_country": safe_str(row.get(found_columns.get("origin_country", ""), "XX"), "XX")[:2].upper(),
                "destination_country": safe_str(row.get(found_columns.get("destination_country", ""), "US"), "US")[
                    :2
                ].upper(),
                "hs_code": safe_str(row.get(found_columns.get("hs_code", ""), "9999"), "9999"),
                "declared_value_usd": safe_float(row.get(found_columns.get("value", ""), 0), 0),
                "declared_weight_kg": safe_float(row.get(found_columns.get("weight", ""), 0), 0),
                "description": safe_str(row.get(found_columns.get("description", ""), "")) or None,
                "vessel_name": safe_str(row.get(found_columns.get("vessel_name", ""), "")) or None,
                "vessel_imo": safe_str(row.get(found_columns.get("vessel_imo", ""), "")) or None,
                "vessel_flag": safe_str(row.get(found_columns.get("vessel_flag", ""), "")) or None,
                "dwell_days": safe_float(row.get(found_columns.get("dwell_days", ""), None)),
                "ais_stuffing_country": safe_str(row.get(found_columns.get("ais_stuffing_country", ""), "")) or None,
                "port_calls": safe_str(row.get(found_columns.get("port_calls", ""), "")) or None,
                "element9_is_mismatch": safe_int(row.get(found_columns.get("element9_is_mismatch", ""), 0), 0),
                "element9_declared_country": safe_str(row.get(found_columns.get("element9_declared_country", ""), ""))
                or None,
                "element9_actual_country": safe_str(row.get(found_columns.get("element9_actual_country", ""), ""))
                or None,
                "shipper_age_months": safe_int(row.get(found_columns.get("shipper_age_months", ""), None)),
                "ad_cvd_rate": safe_float(row.get(found_columns.get("ad_cvd_rate", ""), None)),
                "ad_cvd_applicable": safe_int(row.get(found_columns.get("ad_cvd_applicable", ""), 0), 0),
                "risk_score": safe_float(row.get(found_columns.get("risk_score", ""), None)),
            }

            # Derive AD/CVD applicability from a positive duty rate when no explicit column
            if not parsed_row["ad_cvd_applicable"] and (parsed_row.get("ad_cvd_rate") or 0) > 0:
                parsed_row["ad_cvd_applicable"] = 1

            # Basic validation
            if not parsed_row["shipper"]:
                errors.append(f"Row {idx + 1}: Missing shipper name")
                continue

            rows.append(parsed_row)
        except Exception as e:
            errors.append(f"Row {idx + 1}: {str(e)}")
            logger.error(f"Error parsing row {idx + 1}: {e}")

    if not rows:
        errors.append("No valid rows found in manifest")

    return rows, errors
