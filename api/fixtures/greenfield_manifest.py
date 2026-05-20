"""
Generate Greenfield manifest Excel file for testing.

This creates the test data used in test_ingest.py:
- 12 total rows (9 legitimate, 3 decoy)
- Shipper: "Greenfield Industrial Trading Co., Ltd." (Vietnam)
- Consignee: "SunPath Energy Distributors LLC" (USA)
- HTS code: 7604.10.1000 (aluminum extrusions)
- Quantities: 26,200 kg total
- Value: $64,896 total
"""
import openpyxl
from openpyxl.worksheet.worksheet import Worksheet
from pathlib import Path


def create_greenfield_manifest(output_path: str = None, password: str = "CBPDemo2026") -> str:
    """
    Create Greenfield manifest Excel file.

    Args:
        output_path: Output file path (defaults to api/fixtures/greenfield_manifest.xlsx)
        password: Password to protect sheet

    Returns:
        Path to created file
    """

    if not output_path:
        output_path = str(Path(__file__).parent / "greenfield_manifest.xlsx")

    # Create workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Manifest"

    # Headers
    headers = ["Shipper", "Consignee", "HTS Code", "Quantity (kg)", "Value (USD)", "Description"]
    ws.append(headers)

    # 9 legitimate rows (Greenfield to SunPath, Vietnam origin)
    legitimate_rows = [
        ["Greenfield Industrial Trading Co., Ltd.", "SunPath Energy Distributors LLC", "7604.10.1000", 3000, 7200, "Aluminum extrusions"],
        ["Greenfield Industrial Trading Co., Ltd.", "SunPath Energy Distributors LLC", "7604.10.1000", 2800, 6720, "Aluminum extrusions"],
        ["Greenfield Industrial Trading Co., Ltd.", "SunPath Energy Distributors LLC", "7604.10.1000", 2600, 6240, "Aluminum extrusions"],
        ["Greenfield Industrial Trading Co., Ltd.", "SunPath Energy Distributors LLC", "7604.10.1000", 3200, 7680, "Aluminum extrusions"],
        ["Greenfield Industrial Trading Co., Ltd.", "SunPath Energy Distributors LLC", "7604.10.1000", 2900, 6960, "Aluminum extrusions"],
        ["Greenfield Industrial Trading Co., Ltd.", "SunPath Energy Distributors LLC", "7604.10.1000", 2700, 6480, "Aluminum extrusions"],
        ["Greenfield Industrial Trading Co., Ltd.", "SunPath Energy Distributors LLC", "7604.10.1000", 3100, 7440, "Aluminum extrusions"],
        ["Greenfield Industrial Trading Co., Ltd.", "SunPath Energy Distributors LLC", "7604.10.1000", 2900, 6960, "Aluminum extrusions"],
        ["Greenfield Industrial Trading Co., Ltd.", "SunPath Energy Distributors LLC", "7604.10.1000", 3000, 7200, "Aluminum extrusions"],
    ]

    # 3 decoy rows (legitimate but different origin for testing pattern detection)
    decoy_rows = [
        ["Industrial Metals Trading (Malaysia)", "SunPath Energy Distributors LLC", "7604.10.1000", 1200, 2880, "Aluminum extrusions (Malaysia)"],
        ["Bangkok Aluminum Co., Ltd.", "SunPath Energy Distributors LLC", "7604.10.1000", 1000, 2400, "Aluminum extrusions (Thailand)"],
        ["Greenfield Industrial Trading Co., Ltd.", "Pacific Metals Import LLC", "7604.10.1000", 1500, 3600, "Aluminum extrusions (alternate buyer)"],
    ]

    # Add all rows
    for row in legitimate_rows + decoy_rows:
        ws.append(row)

    # Save with password protection
    wb.save(output_path)

    # Re-open and protect sheet
    wb = openpyxl.load_workbook(output_path)
    ws = wb.active
    ws.protection.sheet = True
    ws.protection.password = password
    wb.save(output_path)

    print(f"Created {output_path}")
    return output_path


def get_greenfield_manifest() -> dict:
    """
    Get Greenfield manifest data as a dictionary for scoring.

    Returns:
        Dictionary with manifest metadata and entries
    """
    return {
        "manifest_id": "greenfield_demo",
        "shipper": "Greenfield Industrial Trading Co., Ltd.",
        "shipper_country": "VN",
        "consignee": "SunPath Energy Distributors LLC",
        "consignee_country": "US",
        "isf_stuffing_country": "CN",
        "vessel_name": "MV Pacific Horizon",
        "port_of_loading": "Guangzhou",
        "port_of_discharge": "Los Angeles",
        "hts_code": "7604.10.1000",
        "hts_description": "Aluminum extrusions",
        "total_quantity_kg": 26200.0,
        "total_declared_value_usd": 62880.0,
        "total_weight_mt": 26.2,
        "eta": "2026-06-15",
        "declared_origin": "VN",
        "ais_dwell_days": 11.2,
        "baseline_dwell_days": 2.1,
        "unit_value_usd_per_kg": 2.4,
        "market_floor_usd_per_kg": 3.4,
        "price_ratio": 0.706,
        "shipper_age_months": 14,
        "prior_filings": 0,
        "ad_cvd_rate": 374.15,
        "ad_cvd_active": True
    }


def get_greenfield_entities() -> dict:
    """
    Get Greenfield entity resolution results as a dictionary for scoring.

    Returns:
        Dictionary with resolved entities and relationships
    """
    return {
        "shipper_vn": {
            "id": "ENT-VN-001",
            "name": "Greenfield Industrial Trading Co., Ltd.",
            "country": "VN",
            "jurisdiction": "VN",
            "type": "TRADING_COMPANY",
            "senzing_record_id": "rec_vn_001",
            "senzing_confidence": 0.95,
            "risk_score": 45,
            "age_months": 14,
            "metadata": {
                "director": "Tran Van Minh",
                "registered_agent": "Greenfield Trading Group"
            }
        },
        "parent_cn": {
            "id": "ENT-CN-001",
            "name": "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
            "country": "CN",
            "jurisdiction": "CN",
            "type": "MANUFACTURER",
            "senzing_record_id": "rec_cn_001",
            "senzing_confidence": 0.98,
            "risk_score": 68,
            "age_months": 120,
            "metadata": {
                "director": "Tran Van Minh",
                "shared_directors": ["Tran Van Minh"],
                "prior_ad_cvd_filings": 9
            }
        },
        "holding_hk": {
            "id": "ENT-HK-001",
            "name": "Greenfield Global Metals Holdings Ltd.",
            "country": "HK",
            "jurisdiction": "HK",
            "type": "HOLDING_COMPANY",
            "senzing_record_id": "rec_hk_001",
            "senzing_confidence": 0.92,
            "risk_score": 52,
            "age_months": 84,
            "metadata": {
                "registered_agent": "Apex Corporate Services Ltd."
            }
        },
        "consignee_us": {
            "id": "ENT-US-001",
            "name": "SunPath Energy Distributors LLC",
            "country": "US",
            "jurisdiction": "US",
            "type": "IMPORTER",
            "senzing_record_id": "rec_us_001",
            "senzing_confidence": 0.87,
            "risk_score": 22,
            "age_months": 48,
            "metadata": {
                "location": "Newark, NJ"
            }
        },
        "vessel": {
            "id": "ENT-VESSEL-001",
            "name": "MV Pacific Horizon",
            "country": "SG",
            "jurisdiction": "SG",
            "type": "VESSEL",
            "senzing_record_id": "rec_vessel_001",
            "senzing_confidence": 0.99,
            "imo": "9432110",
            "metadata": {}
        },
        "ff_cn": {
            "id": "ENT-FF-001",
            "name": "Global Cargo Logistics (Guangzhou) Co., Ltd.",
            "country": "CN",
            "jurisdiction": "CN",
            "type": "FREIGHT_FORWARDER",
            "senzing_record_id": "rec_ff_001",
            "senzing_confidence": 0.88,
            "risk_score": 35,
            "metadata": {}
        }
    }


if __name__ == "__main__":
    create_greenfield_manifest()
