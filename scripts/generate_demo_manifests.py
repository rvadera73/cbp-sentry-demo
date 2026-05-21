#!/usr/bin/env python3
"""
Generate realistic manifest datasets for demo purposes.
Creates Excel files for April, May, and June 2026 with:
- Realistic shipment data based on common trade routes
- ISF Element 9 data (declared vs actual country)
- Risk corridor indicators
- Variable risk scores based on patterns
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

# Risk corridors with AD/CVD data
RISK_CORRIDORS = {
    '7604': {  # Aluminum
        'name': 'Aluminum Extrusions',
        'origins': ['CN', 'VN', 'MY', 'TH', 'KH'],
        'ad_cvd_rate': 3.7415,
        'baseline_dwell': 2.1,
        'anomaly_dwell': 7.2,
    },
    '8541': {  # Solar cells
        'name': 'Solar Modules',
        'origins': ['CN', 'VN', 'MY', 'TH', 'KH'],
        'ad_cvd_rate': 1.0,
        'baseline_dwell': 1.5,
        'anomaly_dwell': 5.8,
    },
    '7210': {  # Flat-rolled steel
        'name': 'Flat-Rolled Steel',
        'origins': ['CN', 'IN', 'VN', 'KR'],
        'ad_cvd_rate': 0.35,
        'baseline_dwell': 2.8,
        'anomaly_dwell': 6.5,
    },
    '6204': {  # Apparel
        'name': 'T-shirts & Apparel',
        'origins': ['BD', 'VN', 'IN', 'KH', 'ID'],
        'ad_cvd_rate': 0.0,
        'baseline_dwell': 1.0,
        'anomaly_dwell': 3.2,
    },
}

SHIPPERS = [
    'Greenfield Industrial Trading Co.',
    'Solaria Manufacturing Sdn. Bhd.',
    'Vietnam Aluminum Corp',
    'Bangkok Metals International',
    'Da Nang Industrial',
    'Chiang Mai Trading Ltd.',
    'Phnom Penh Manufacturing',
    'Selangor Manufacturing',
    'Mekong Industrial Trading Ltd.',
    'Beijing Electronics Ltd.',
]

CONSIGNEES = [
    'SunPath Energy Distributors LLC',
    'Newark Metals Inc.',
    'Gulf Coast Industrial',
    'Atlantic Trading Partners',
    'American Industrial Supply Corp',
    'Global Imports USA',
    'Southeast Trading Corp',
    'Great Lakes Import Co',
    'California Solar Solutions',
    'Midwest Industrial Supply',
]

VESSELS = [
    ('MV Pacific Horizon', '9710399', 'PA'),
    ('MV Seamless Journey', '9710398', 'PA'),
    ('MV Ocean Master', '9710397', 'SG'),
    ('MV International Flow', '9710396', 'LR'),
    ('MV Asia Bridge', '9710395', 'PH'),
]

def generate_manifests(year, month, month_name, num_records=300):
    """Generate manifest records for a specific month."""

    records = []

    # Generate shipping dates throughout the month
    month_start = datetime(year, month, 1)
    month_end = datetime(year, month, 28) if month == 2 else datetime(year, month, 30) if month in [4,6,9,11] else datetime(year, month, 31)

    for i in range(num_records):
        # Random shipping date in the month
        shipping_date = month_start + timedelta(days=random.randint(0, (month_end - month_start).days))
        eta = shipping_date + timedelta(days=random.randint(8, 35))

        # Select corridor
        hs_code = random.choice(list(RISK_CORRIDORS.keys()))
        corridor = RISK_CORRIDORS[hs_code]

        # Risk pattern: 20% high-risk, 30% medium-risk, 50% low-risk
        risk_pattern = random.choices(['high', 'medium', 'low'], weights=[0.2, 0.3, 0.5])[0]

        # Determine shipper, consignee, vessel
        shipper_idx = i % len(SHIPPERS)
        consignee_idx = (i + 1) % len(CONSIGNEES)
        vessel_idx = i % len(VESSELS)

        shipper_name = SHIPPERS[shipper_idx]
        consignee_name = CONSIGNEES[consignee_idx]
        vessel_name, vessel_imo, vessel_flag = VESSELS[vessel_idx]

        # High-risk: transshipment indicators
        if risk_pattern == 'high':
            shipper_country = random.choice(['VN', 'MY', 'TH', 'KH'])
            stuffing_country = 'CN'  # ISF mismatch
            dwell_days = corridor['anomaly_dwell'] + random.uniform(-1, 2)
            value_usd = random.uniform(30000, 80000)
            weight_kg = random.uniform(15000, 50000)
        # Medium-risk: some indicators
        elif risk_pattern == 'medium':
            shipper_country = random.choice(corridor['origins'])
            stuffing_country = shipper_country if random.random() < 0.5 else 'CN'
            dwell_days = corridor['baseline_dwell'] + random.uniform(0.5, 3)
            value_usd = random.uniform(25000, 75000)
            weight_kg = random.uniform(10000, 40000)
        # Low-risk: legitimate
        else:
            shipper_country = random.choice(corridor['origins'][:3])  # Prefer major origins
            stuffing_country = shipper_country
            dwell_days = corridor['baseline_dwell'] + random.uniform(-0.5, 1)
            value_usd = random.uniform(15000, 60000)
            weight_kg = random.uniform(5000, 30000)

        # Shipper age: high-risk = new (< 2yr), low-risk = established (> 3yr)
        if risk_pattern == 'high':
            shipper_age_months = random.randint(1, 18)
        elif risk_pattern == 'medium':
            shipper_age_months = random.randint(6, 36)
        else:
            shipper_age_months = random.randint(12, 120)

        # ISF Element 9 mismatch
        element9_mismatch = 1 if shipper_country != stuffing_country else 0

        # Calculate base risk score
        base_score = 25
        if risk_pattern == 'high':
            base_score += 45
        elif risk_pattern == 'medium':
            base_score += 20

        # Add factors
        if element9_mismatch:
            base_score += 15
        if shipper_age_months < 12:
            base_score += 10
        if dwell_days > corridor['anomaly_dwell'] - 1:
            base_score += 8
        if corridor['ad_cvd_rate'] > 0.5:
            base_score += 5

        # Random adjustment
        risk_score = min(100, base_score + random.randint(-5, 5))

        record = {
            'Manifest ID': f'MNF-{year}-{month:02d}-{i+1:05d}',
            'Shipper Name': shipper_name,
            'Consignee Name': consignee_name,
            'Shipper Country': shipper_country,
            'Consignee Country': 'US',
            'Origin Country': shipper_country,
            'Destination Country': 'US',
            'HS Code': hs_code,
            'Commodity': corridor['name'],
            'Declared Value USD': f'{value_usd:.2f}',
            'Declared Weight KG': f'{weight_kg:.1f}',
            'Vessel Name': vessel_name,
            'Vessel IMO': vessel_imo,
            'Vessel Flag': vessel_flag,
            'Shipping Date': shipping_date.strftime('%Y-%m-%d'),
            'ETA': eta.strftime('%Y-%m-%d'),
            'Port Calls': f'{shipper_country},SG,US',
            'Dwell Days': f'{dwell_days:.1f}',
            'AIS Stuffing Country': stuffing_country,
            'ISF Element 9 Mismatch': element9_mismatch,
            'ISF Declared Country': shipper_country,
            'ISF Actual Country': stuffing_country,
            'Shipper Age Months': shipper_age_months,
            'AD/CVD Rate': f'{corridor["ad_cvd_rate"]:.4f}',
            'Risk Score': f'{risk_score:.1f}',
            'Status': 'FILED',
        }
        records.append(record)

    return pd.DataFrame(records)

def main():
    """Generate manifest files for April, May, June."""

    output_dir = 'demo_manifests'
    os.makedirs(output_dir, exist_ok=True)

    months = [
        (4, 'April', 250),
        (5, 'May', 300),
        (6, 'June', 280),
    ]

    for month_num, month_name, num_records in months:
        print(f'Generating {month_name} 2026 manifests ({num_records} records)...')

        df = generate_manifests(2026, month_num, month_name, num_records)

        filename = f'{output_dir}/manifests_{month_name.lower()}_2026.xlsx'
        df.to_excel(filename, index=False, sheet_name='Manifests')

        print(f'  ✓ Saved: {filename}')
        print(f'  - High-risk (80+): {len(df[df["Risk Score"].astype(float) >= 80])}')
        print(f'  - Medium-risk (60-79): {len(df[(df["Risk Score"].astype(float) >= 60) & (df["Risk Score"].astype(float) < 80)])}')
        print(f'  - Low-risk (<60): {len(df[df["Risk Score"].astype(float) < 60])}')
        print()

    print(f'✓ All manifest files generated in {output_dir}/')
    print(f'  - You can now upload these files via the Command Center UI')
    print(f'  - Each file contains realistic shipment data with ISF Element 9, dwell patterns, and risk indicators')

if __name__ == '__main__':
    main()
