"""Excel manifest parsing and normalization"""
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

    # Expected column mappings (case-insensitive)
    column_map = {
        'shipper': ['shipper', 'shipper_name', 'exporter', 'supplier'],
        'consignee': ['consignee', 'consignee_name', 'importer', 'buyer'],
        'origin_country': ['origin', 'origin_country', 'country_of_origin', 'export_country'],
        'destination_country': ['destination', 'destination_country', 'import_country', 'consignee_country'],
        'hs_code': ['hs_code', 'hts_code', 'commodity_code', 'product_code'],
        'value': ['value', 'declared_value', 'value_usd', 'fob_value'],
        'weight': ['weight', 'weight_kg', 'net_weight', 'declared_weight'],
        'description': ['description', 'product_description', 'commodity'],
        'vessel_name': ['vessel', 'vessel_name', 'ship_name', 'carrying_vessel'],
    }

    # Find actual columns in the dataframe
    df_columns_lower = {col.lower(): col for col in df.columns}
    found_columns = {}

    for target, aliases in column_map.items():
        for alias in aliases:
            if alias.lower() in df_columns_lower:
                found_columns[target] = df_columns_lower[alias.lower()]
                break

    if 'shipper' not in found_columns or 'consignee' not in found_columns:
        errors.append("Missing required columns: shipper and consignee")
        return [], errors

    # Parse rows
    for idx, row in df.iterrows():
        try:
            parsed_row = {
                'rowNumber': idx + 1,
                'shipper': str(row.get(found_columns.get('shipper', ''), 'Unknown')).strip(),
                'consignee': str(row.get(found_columns.get('consignee', ''), 'Unknown')).strip(),
                'origin_country': str(row.get(found_columns.get('origin_country', ''), 'XX')).strip()[:2].upper(),
                'destination_country': str(row.get(found_columns.get('destination_country', ''), 'US')).strip()[:2].upper(),
                'hs_code': str(row.get(found_columns.get('hs_code', ''), '')).strip() or '9999',
                'declared_value_usd': float(row.get(found_columns.get('value', ''), 0) or 0),
                'declared_weight_kg': float(row.get(found_columns.get('weight', ''), 0) or 0),
                'description': str(row.get(found_columns.get('description', ''), '')).strip(),
                'vessel_name': str(row.get(found_columns.get('vessel_name', ''), '')).strip() or None,
            }

            # Basic validation
            if not parsed_row['shipper']:
                errors.append(f"Row {idx + 1}: Missing shipper name")
                continue

            rows.append(parsed_row)
        except Exception as e:
            errors.append(f"Row {idx + 1}: {str(e)}")
            logger.error(f"Error parsing row {idx + 1}: {e}")

    if not rows:
        errors.append("No valid rows found in manifest")

    return rows, errors
