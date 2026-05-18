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


if __name__ == "__main__":
    create_greenfield_manifest()
