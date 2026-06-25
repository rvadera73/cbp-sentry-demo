#!/usr/bin/env python3
"""
CBP Risk Model Feature Engineering - Phase 1
72 features organized in 7 risk factors
"""

import pandas as pd
import numpy as np
import json
import time
from datetime import datetime
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Country risk classifications
HIGH_RISK_COUNTRIES = {
    'IR', 'SY', 'KP', 'CU', 'CR', 'VE', 'SO', 'MM',
    'ZW', 'BY', 'XK', 'PK', 'YE', 'LY', 'SS', 'SD'
}

TRANSSHIPMENT_HUBS = {
    'SG', 'MY', 'HK', 'AE', 'PA', 'PH', 'TH', 'VN',
    'ID', 'KH', 'MM', 'LA', 'KZ'
}

TRANSHIPMENT_FLAG_STATES = {
    'PA', 'LR', 'KH', 'KI', 'MH', 'MZ', 'VU', 'BS', 'CY'
}

CONTROLLED_HS_CODES = {
    '8471.30': 0.9,  # Computer processors
    '8517.62': 0.8,  # Telephone switching
    '8542.31': 0.95, # Semiconductors
    '9005.80': 0.85, # Optical instruments
    '9015.80': 0.8,  # Surveying instruments
    '9030.82': 0.85, # Electronic test instruments
    '9030.89': 0.85, # Electronic instruments
    '9031.80': 0.8,  # Test apparatus
    '8534.30': 0.9,  # Printed circuit boards
    '8534.90': 0.85, # PCB materials
}

# US ports
US_PORTS = {
    'LA', 'NY', 'HT', 'SF', 'SE', 'NO', 'SA', 'PO',
    'SN', 'TB', 'FT', 'DL', 'GV', 'MO', 'BL', 'MG'
}

# Sanctioned entities (simplified sample)
SANCTIONED_ENTITIES = {
    'North Korea', 'Iranian', 'Syria', 'Crimea', 'Donetsk',
    'Luhansk', 'Cuba', 'Venezuela'
}


class FeatureEngineer:
    def __init__(self, data_path: str):
        self.data = pd.read_csv(data_path)
        self.features = {}
        self.start_time = time.time()

    def engineer_features(self) -> pd.DataFrame:
        """Engineer all 72 features"""

        # DOCUMENTATION_RISK (12 features)
        self._documentation_risk_features()

        # ROUTING_RISK (10 features)
        self._routing_risk_features()

        # COMMODITY_RISK (10 features)
        self._commodity_risk_features()

        # CORRIDOR_RISK (15 features)
        self._corridor_risk_features()

        # PARTY_RISK (10 features)
        self._party_risk_features()

        # PATTERN_RISK (10 features)
        self._pattern_risk_features()

        # TIME_SENSITIVITY (10 features)
        self._time_sensitivity_features()

        # Combine all features
        feature_matrix = pd.DataFrame(self.features)
        return feature_matrix

    def _documentation_risk_features(self):
        """12 DOCUMENTATION_RISK features"""

        # DOCUMENTATION_001: Element 9 mismatch (0-1)
        self.features['DOCUMENTATION_001_element9_mismatch'] = (
            self.data['element9_is_mismatch'].fillna(0).astype(int)
        )

        # DOCUMENTATION_002: Ad/CVD applicable flag (0-1)
        self.features['DOCUMENTATION_002_adcvd_applicable'] = (
            (self.data['ad_cvd_applicable'] == 0).astype(int)
        )

        # DOCUMENTATION_003: ISF completeness proxy (based on fields present)
        # Count non-null fields as proxy for ISF completeness
        required_fields = ['shipper_name', 'consignee_name', 'hs_code', 'vessel_name']
        self.features['DOCUMENTATION_003_isf_completeness'] = (
            self.data[required_fields].notna().sum(axis=1) / len(required_fields)
        )

        # DOCUMENTATION_004: Missing critical fields count
        critical_fields = ['shipper_country', 'origin_country', 'vessel_imo', 'manifest_id']
        missing_count = self.data[critical_fields].isna().sum(axis=1)
        self.features['DOCUMENTATION_004_missing_fields'] = (
            missing_count / len(critical_fields)
        )

        # DOCUMENTATION_005: Value-to-weight ratio anomaly
        vw_ratio = self.data['declared_value_usd'] / (self.data['declared_weight_kg'] + 1)
        vw_median = vw_ratio.median()
        vw_std = vw_ratio.std()
        self.features['DOCUMENTATION_005_value_weight_anomaly'] = (
            np.abs(vw_ratio - vw_median) / (vw_std + 1)
        ).clip(0, 5) / 5

        # DOCUMENTATION_006: HS code validity proxy (known codes)
        self.features['DOCUMENTATION_006_hs_code_validity'] = (
            self.data['hs_code'].isin(CONTROLLED_HS_CODES.keys()).astype(int)
        )

        # DOCUMENTATION_007: Shipper-consignee country mismatch
        self.features['DOCUMENTATION_007_shipper_consignee_mismatch'] = (
            (self.data['shipper_country'] != self.data['consignee_country']).astype(int)
        )

        # DOCUMENTATION_008: Origin-declared origin mismatch
        self.features['DOCUMENTATION_008_origin_declared_mismatch'] = (
            (self.data['origin_country'] != self.data['shipper_country']).astype(int)
        )

        # DOCUMENTATION_009: Destination consistency check
        self.features['DOCUMENTATION_009_destination_consistency'] = (
            (self.data['destination_country'] == 'US').astype(int)
        )

        # DOCUMENTATION_010: Filing status risk
        status_risk = self.data['status'].map({
            'legitimate': 0.0,
            'under_review': 0.5,
            'flagged': 0.8,
            'alert': 1.0
        }).fillna(0.3)
        self.features['DOCUMENTATION_010_filing_status_risk'] = status_risk

        # DOCUMENTATION_011: Dwell time anomaly
        dwell_median = self.data['dwell_days'].median()
        dwell_std = self.data['dwell_days'].std()
        self.features['DOCUMENTATION_011_dwell_anomaly'] = (
            np.abs(self.data['dwell_days'] - dwell_median) / (dwell_std + 1)
        ).clip(0, 5) / 5

        # DOCUMENTATION_012: Manifest completeness score
        manifest_cols = ['shipper_name', 'consignee_name', 'hs_code', 'declared_value_usd',
                        'declared_weight_kg', 'vessel_name', 'vessel_imo']
        self.features['DOCUMENTATION_012_manifest_completeness'] = (
            self.data[manifest_cols].notna().sum(axis=1) / len(manifest_cols)
        )

    def _routing_risk_features(self):
        """10 ROUTING_RISK features"""

        # ROUTING_001: Destination is FTZ or transshipment hub
        self.features['ROUTING_001_ftz_destination'] = (
            self.data['destination_country'].isin(TRANSSHIPMENT_HUBS).astype(int)
        )

        # ROUTING_002: Port selection risk (origin_country != destination_country)
        # Indicator that cargo is transshipped through multiple ports
        self.features['ROUTING_002_non_us_port_risk'] = (
            (self.data['origin_country'] != self.data['destination_country']).astype(int)
        )

        # ROUTING_003: Vessel flag risk
        vessel_flag_risk = 0.0
        if 'vessel_name' in self.data.columns:
            # Use vessel_name as proxy - common flag state names
            vessel_names = self.data['vessel_name'].fillna('')
            vessel_flag_risk = vessel_names.str.contains(
                'Panama|Liberia|Cambodia|Marshall', case=False, na=False
            ).astype(float)
        self.features['ROUTING_003_vessel_flag_risk'] = vessel_flag_risk

        # ROUTING_004: AIS dwell anomaly
        dwell_q25 = self.data['dwell_days'].quantile(0.25)
        dwell_q75 = self.data['dwell_days'].quantile(0.75)
        dwell_iqr = dwell_q75 - dwell_q25
        self.features['ROUTING_004_ais_dwell_anomaly'] = (
            ((self.data['dwell_days'] > dwell_q75 + 1.5 * dwell_iqr) |
             (self.data['dwell_days'] < dwell_q25 - 1.5 * dwell_iqr)).astype(int)
        )

        # ROUTING_005: Multi-port routing complexity
        self.features['ROUTING_005_multiport_routing'] = (
            self.data['shipper_country'] != self.data['origin_country']
        ).astype(int)

        # ROUTING_006: Vessel age/condition proxy (using IMO as proxy)
        imo_risk = 0.0
        if 'vessel_imo' in self.data.columns:
            # Vessels with very low or very high IMO numbers are flagged
            valid_imos = pd.to_numeric(
                self.data['vessel_imo'].astype(str), errors='coerce'
            )
            imo_median = valid_imos.median()
            imo_std = valid_imos.std()
            imo_risk = (np.abs(valid_imos - imo_median) / (imo_std + 1)).clip(0, 5) / 5
        self.features['ROUTING_006_vessel_age_risk'] = imo_risk.fillna(0)

        # ROUTING_007: Port density/frequency
        port_freq = self.data['origin_country'].value_counts()
        self.features['ROUTING_007_origin_frequency'] = (
            self.data['origin_country'].map(port_freq) / len(self.data)
        )

        # ROUTING_008: Cross-border transit chain
        self.features['ROUTING_008_cross_border_chain'] = (
            ((self.data['origin_country'] != self.data['shipper_country']) &
             (self.data['shipper_country'] != self.data['consignee_country'])).astype(int)
        )

        # ROUTING_009: Direct vs. indirect routing
        self.features['ROUTING_009_indirect_routing'] = (
            ((self.data['origin_country'] != self.data['destination_country']) &
             (self.data['shipper_country'] != self.data['destination_country'])).astype(int)
        )

        # ROUTING_010: Transshipment likelihood
        self.features['ROUTING_010_transshipment_likelihood'] = (
            (self.data['shipper_country'].isin(TRANSSHIPMENT_HUBS) |
             self.data['origin_country'].isin(TRANSSHIPMENT_HUBS)).astype(float)
        )

    def _commodity_risk_features(self):
        """10 COMMODITY_RISK features"""

        # COMMODITY_001: HS code control status
        control_rates = self.data['hs_code'].map(CONTROLLED_HS_CODES).fillna(0)
        self.features['COMMODITY_001_hs_control_status'] = control_rates

        # COMMODITY_002: High-value commodity flag
        value_q75 = self.data['declared_value_usd'].quantile(0.75)
        self.features['COMMODITY_002_high_value_flag'] = (
            (self.data['declared_value_usd'] > value_q75).astype(int)
        )

        # COMMODITY_003: Dual-use equipment proxy
        dual_use_codes = ['8471.30', '8517.62', '8542.31', '9005.80', '9030.82']
        self.features['COMMODITY_003_dual_use_equipment'] = (
            self.data['hs_code'].isin(dual_use_codes).astype(int)
        )

        # COMMODITY_004: Semiconductor/electronics risk
        electronics_codes = ['8471.30', '8517.62', '8542.31', '8534.30', '8534.90']
        self.features['COMMODITY_004_electronics_risk'] = (
            self.data['hs_code'].isin(electronics_codes).astype(int)
        )

        # COMMODITY_005: Precious metals flag
        precious_codes = ['7108', '7109', '7110', '7111', '7112']
        precious = self.data['hs_code'].astype(str).str.startswith(tuple(precious_codes))
        self.features['COMMODITY_005_precious_metals'] = precious.astype(int).fillna(0)

        # COMMODITY_006: Weight-based anomaly
        weight_q75 = self.data['declared_weight_kg'].quantile(0.75)
        weight_q25 = self.data['declared_weight_kg'].quantile(0.25)
        self.features['COMMODITY_006_weight_anomaly'] = (
            (self.data['declared_weight_kg'] > weight_q75 * 2) |
            (self.data['declared_weight_kg'] < weight_q25 * 0.5)
        ).astype(int)

        # COMMODITY_007: Unit price anomaly
        unit_price = self.data['declared_value_usd'] / (self.data['declared_weight_kg'] + 1)
        price_median = unit_price.median()
        price_std = unit_price.std()
        self.features['COMMODITY_007_unit_price_anomaly'] = (
            np.abs(unit_price - price_median) / (price_std + 1)
        ).clip(0, 5) / 5

        # COMMODITY_008: Commodity-origin mismatch
        # E.g., electronics from non-manufacturing origins
        self.features['COMMODITY_008_commodity_origin_mismatch'] = 0
        electronics_match = (
            self.data['hs_code'].isin(electronics_codes) &
            ~self.data['origin_country'].isin(['CN', 'JP', 'KR', 'TW', 'MY', 'SG', 'TH'])
        ).astype(int).fillna(0)
        self.features['COMMODITY_008_commodity_origin_mismatch'] = electronics_match

        # COMMODITY_009: Restricted destination commodity
        restricted_dest = (
            (self.data['destination_country'].isin(HIGH_RISK_COUNTRIES)) &
            (self.data['hs_code'].isin(dual_use_codes))
        ).astype(int)
        self.features['COMMODITY_009_restricted_destination'] = restricted_dest

        # COMMODITY_010: Commodity concentration risk
        hs_freq = self.data['hs_code'].value_counts()
        commodity_concentration = 1 - (
            self.data['hs_code'].map(hs_freq) / len(self.data)
        )
        self.features['COMMODITY_010_commodity_concentration'] = commodity_concentration

    def _corridor_risk_features(self):
        """15 CORRIDOR_RISK features"""

        # CORRIDOR_001: Origin country risk score
        origin_risk = self.data['origin_country'].map(
            lambda x: 0.95 if x in HIGH_RISK_COUNTRIES else 0.2
        )
        self.features['CORRIDOR_001_origin_risk'] = origin_risk

        # CORRIDOR_002: Destination country risk score
        dest_risk = self.data['destination_country'].map(
            lambda x: 0.95 if x in HIGH_RISK_COUNTRIES else 0.1
        )
        self.features['CORRIDOR_002_destination_risk'] = dest_risk

        # CORRIDOR_003: Shipper country risk
        shipper_risk = self.data['shipper_country'].map(
            lambda x: 0.95 if x in HIGH_RISK_COUNTRIES else (
                0.7 if x in TRANSSHIPMENT_HUBS else 0.2
            )
        )
        self.features['CORRIDOR_003_shipper_country_risk'] = shipper_risk

        # CORRIDOR_004: Consignee country risk
        consignee_risk = self.data['consignee_country'].map(
            lambda x: 0.95 if x in HIGH_RISK_COUNTRIES else 0.1
        )
        self.features['CORRIDOR_004_consignee_country_risk'] = consignee_risk

        # CORRIDOR_005: Sanctioned entity match (name-based)
        sanctioned_shipper = self.data['shipper_name'].fillna('').str.contains(
            '|'.join(SANCTIONED_ENTITIES), case=False, na=False
        ).astype(int)
        self.features['CORRIDOR_005_sanctioned_shipper'] = sanctioned_shipper

        # CORRIDOR_006: Sanctioned entity match (consignee)
        sanctioned_consignee = self.data['consignee_name'].fillna('').str.contains(
            '|'.join(SANCTIONED_ENTITIES), case=False, na=False
        ).astype(int)
        self.features['CORRIDOR_006_sanctioned_consignee'] = sanctioned_consignee

        # CORRIDOR_007: Route through high-risk corridor
        high_risk_routes = [
            ('CN', 'IR'), ('CN', 'SY'), ('KP', 'CN'), ('VE', 'US'),
            ('IR', 'US'), ('SY', 'US'), ('CU', 'US')
        ]
        is_high_risk_route = self.data.apply(
            lambda row: (row['origin_country'], row['destination_country']) in high_risk_routes,
            axis=1
        ).astype(int)
        self.features['CORRIDOR_007_high_risk_route'] = is_high_risk_route

        # CORRIDOR_008: Transshipment corridor
        transship_corridor = (
            self.data['origin_country'].isin(TRANSSHIPMENT_HUBS) |
            self.data['shipper_country'].isin(TRANSSHIPMENT_HUBS)
        ).astype(int)
        self.features['CORRIDOR_008_transshipment_corridor'] = transship_corridor

        # CORRIDOR_009: Multi-country supply chain
        countries_involved = (
            (self.data['origin_country'] != self.data['shipper_country']).astype(int) +
            (self.data['shipper_country'] != self.data['consignee_country']).astype(int) +
            (self.data['consignee_country'] != self.data['destination_country']).astype(int)
        )
        self.features['CORRIDOR_009_supply_chain_complexity'] = (countries_involved / 3)

        # CORRIDOR_010: China-origin risk multiplier
        china_origin = (self.data['origin_country'] == 'CN').astype(int)
        self.features['CORRIDOR_010_china_origin'] = china_origin

        # CORRIDOR_011: Southeast Asia hub risk
        se_asia_hub = self.data['shipper_country'].isin(
            ['SG', 'MY', 'TH', 'VN', 'ID', 'PH']
        ).astype(int)
        self.features['CORRIDOR_011_se_asia_hub'] = se_asia_hub

        # CORRIDOR_012: Hong Kong transshipment risk
        hk_transship = (
            (self.data['origin_country'] == 'HK') |
            (self.data['shipper_country'] == 'HK') |
            (self.data['destination_country'] == 'HK')
        ).astype(int)
        self.features['CORRIDOR_012_hk_transshipment'] = hk_transship

        # CORRIDOR_013: Panama corridor risk (flag + jurisdiction)
        panama_risk = (
            self.data['shipper_country'] == 'PA'
        ).astype(int)
        self.features['CORRIDOR_013_panama_corridor'] = panama_risk

        # CORRIDOR_014: Origin-destination geographic distance proxy
        # Simple proxy: same region = 0, different region = 1
        regions = {
            'CN': 'Asia', 'JP': 'Asia', 'KR': 'Asia', 'SG': 'Asia', 'MY': 'Asia',
            'TH': 'Asia', 'VN': 'Asia', 'ID': 'Asia', 'PH': 'Asia', 'IN': 'Asia',
            'US': 'NA', 'CA': 'NA', 'MX': 'NA',
            'DE': 'EU', 'GB': 'EU', 'FR': 'EU', 'NL': 'EU',
            'IR': 'ME', 'SY': 'ME', 'AE': 'ME',
        }
        origin_region = self.data['origin_country'].map(regions).fillna('Other')
        dest_region = self.data['destination_country'].map(regions).fillna('Other')
        self.features['CORRIDOR_014_long_distance_route'] = (
            (origin_region != dest_region).astype(int)
        )

        # CORRIDOR_015: Corridor frequency anomaly
        corridor_pairs = (
            self.data['origin_country'].astype(str) + '->' + self.data['destination_country'].astype(str)
        )
        corridor_freq = corridor_pairs.value_counts()
        self.features['CORRIDOR_015_corridor_frequency'] = (
            corridor_pairs.map(corridor_freq) / len(self.data)
        )

    def _party_risk_features(self):
        """10 PARTY_RISK features"""

        # PARTY_001: Shipper age (months)
        shipper_age = self.data['shipper_age_months'].fillna(
            self.data['shipper_age_months'].median()
        )
        shipper_age_norm = 1 - (shipper_age / (shipper_age.max() + 1))
        self.features['PARTY_001_shipper_age_risk'] = shipper_age_norm.clip(0, 1)

        # PARTY_002: New shipper flag (< 12 months)
        self.features['PARTY_002_new_shipper'] = (
            self.data['shipper_age_months'] < 12
        ).astype(int).fillna(0)

        # PARTY_003: Very young shipper flag (< 6 months)
        self.features['PARTY_003_very_new_shipper'] = (
            self.data['shipper_age_months'] < 6
        ).astype(int).fillna(0)

        # PARTY_004: Shipper name opacity (character analysis)
        shipper_opacity = self.data['shipper_name'].fillna('').apply(
            lambda x: 1.0 if len(x) < 5 or 'Unknown' in x or 'N/A' in x else 0.0
        )
        self.features['PARTY_004_shipper_opacity'] = shipper_opacity

        # PARTY_005: Generic shipper name risk
        generic_names = ['Corp', 'LLC', 'Ltd', 'Inc', 'Trading', 'Export', 'Import']
        generic_shipper = self.data['shipper_name'].fillna('').apply(
            lambda x: sum(1 for g in generic_names if g in x) / len(generic_names)
        )
        self.features['PARTY_005_generic_shipper_name'] = generic_shipper

        # PARTY_006: Consignee age (importer age proxy)
        # Using average shipper age as proxy for consignee stability
        consignee_age_avg = self.data['shipper_age_months'].median()
        consignee_age_norm = 1 - (consignee_age_avg / 200)
        self.features['PARTY_006_consignee_age_risk'] = consignee_age_norm.clip(0, 1)

        # PARTY_007: Party name mismatch count
        shipper_consignee_match = (
            self.data['shipper_name'] == self.data['consignee_name']
        ).astype(int)
        self.features['PARTY_007_shipper_consignee_match'] = shipper_consignee_match

        # PARTY_008: Party country legitimacy
        legitimate_party_countries = {'US', 'CA', 'MX', 'JP', 'SG', 'DE', 'GB', 'AU'}
        party_legit = (
            self.data['shipper_country'].isin(legitimate_party_countries) &
            self.data['consignee_country'].isin(legitimate_party_countries)
        ).astype(int).fillna(0)
        self.features['PARTY_008_party_country_legitimacy'] = 1 - party_legit

        # PARTY_009: Shipper frequency (repeated shipper)
        shipper_freq = self.data['shipper_name'].value_counts()
        shipper_repeat = self.data['shipper_name'].map(shipper_freq) / len(self.data)
        self.features['PARTY_009_shipper_repeat_frequency'] = shipper_repeat

        # PARTY_010: Party obscurity score
        party_obscurity = (
            shipper_opacity +
            generic_shipper +
            (1 - (shipper_repeat.fillna(0)))
        ) / 3
        self.features['PARTY_010_party_obscurity'] = party_obscurity.clip(0, 1)

    def _pattern_risk_features(self):
        """10 PATTERN_RISK features"""

        # PATTERN_001: Value distribution anomaly (isolation forest proxy)
        value_median = self.data['declared_value_usd'].median()
        value_std = self.data['declared_value_usd'].std()
        value_zscore = np.abs(
            (self.data['declared_value_usd'] - value_median) / (value_std + 1)
        )
        self.features['PATTERN_001_value_anomaly'] = (
            (value_zscore > 3).astype(int)
        )

        # PATTERN_002: Weight distribution anomaly
        weight_median = self.data['declared_weight_kg'].median()
        weight_std = self.data['declared_weight_kg'].std()
        weight_zscore = np.abs(
            (self.data['declared_weight_kg'] - weight_median) / (weight_std + 1)
        )
        self.features['PATTERN_002_weight_anomaly'] = (
            (weight_zscore > 3).astype(int)
        )

        # PATTERN_003: Value-weight ratio anomaly
        vw_ratio = self.data['declared_value_usd'] / (self.data['declared_weight_kg'] + 1)
        vw_median = vw_ratio.median()
        vw_std = vw_ratio.std()
        vw_zscore = np.abs((vw_ratio - vw_median) / (vw_std + 1))
        self.features['PATTERN_003_vw_ratio_anomaly'] = (
            (vw_zscore > 3).astype(int)
        )

        # PATTERN_004: Dwell time anomaly
        dwell_median = self.data['dwell_days'].median()
        dwell_std = self.data['dwell_days'].std()
        dwell_zscore = np.abs(
            (self.data['dwell_days'] - dwell_median) / (dwell_std + 1)
        )
        self.features['PATTERN_004_dwell_time_anomaly'] = (
            (dwell_zscore > 3).astype(int)
        )

        # PATTERN_005: Multivariate anomaly score (combined zscore)
        features_for_anomaly = [
            value_zscore, weight_zscore, vw_zscore, dwell_zscore
        ]
        combined_zscore = np.mean(features_for_anomaly, axis=0)
        self.features['PATTERN_005_multivariate_anomaly'] = (
            (combined_zscore > 2.5).astype(float)
        )

        # PATTERN_006: Frequency anomaly (infrequent combinations)
        shipper_dest = (
            self.data['shipper_country'].astype(str) + '-' + self.data['destination_country'].astype(str)
        )
        freq = shipper_dest.value_counts()
        rare_combo = (shipper_dest.map(freq) == 1).astype(int)
        self.features['PATTERN_006_rare_shipper_dest_combo'] = rare_combo.fillna(0)

        # PATTERN_007: Pricing deviation from corridor average
        corridors = (
            self.data['origin_country'].astype(str) + '->' + self.data['destination_country'].astype(str)
        )
        corridor_avg_price = (
            self.data.groupby(corridors)['declared_value_usd'].transform('mean')
        )
        price_deviation = np.abs(
            self.data['declared_value_usd'] - corridor_avg_price
        ) / (corridor_avg_price + 1)
        self.features['PATTERN_007_price_deviation'] = (
            price_deviation.clip(0, 5) / 5
        )

        # PATTERN_008: Commodity-origin mismatch frequency
        commodity_origin = (
            self.data['hs_code'].astype(str) + '-' + self.data['origin_country'].astype(str)
        )
        combo_freq = commodity_origin.value_counts()
        rare_commodity = (commodity_origin.map(combo_freq) <= 2).astype(int)
        self.features['PATTERN_008_rare_commodity_origin'] = rare_commodity.fillna(0)

        # PATTERN_009: Shipper-commodity concentration
        shipper_commodity = (
            self.data['shipper_name'].astype(str) + '-' + self.data['hs_code'].astype(str)
        )
        shipper_comm_freq = shipper_commodity.value_counts()
        shipper_concentration = (
            shipper_commodity.map(shipper_comm_freq) / len(self.data)
        )
        self.features['PATTERN_009_shipper_commodity_concentration'] = (
            shipper_concentration.fillna(0)
        )

        # PATTERN_010: Ensemble anomaly score
        anomaly_features = [
            self.features['PATTERN_001_value_anomaly'],
            self.features['PATTERN_002_weight_anomaly'],
            self.features['PATTERN_003_vw_ratio_anomaly'],
            self.features['PATTERN_004_dwell_time_anomaly'],
        ]
        ensemble_score = np.mean(anomaly_features, axis=0)
        self.features['PATTERN_010_ensemble_anomaly'] = ensemble_score

    def _time_sensitivity_features(self):
        """10 TIME_SENSITIVITY features"""

        # TIME_SENSITIVITY_001: Tariff announcement proximity (simulated)
        # Simulate tariff events (quarterly)
        # Assume major tariff event every 90 days
        self.features['TIME_SENSITIVITY_001_tariff_proximity'] = 0.3

        # TIME_SENSITIVITY_002: Seasonal commodity risk
        # Electronics peak: Q4, Steel: Q2-Q3
        electronics_codes = ['8471.30', '8517.62', '8542.31', '8534.30']
        is_electronics = self.data['hs_code'].isin(electronics_codes).astype(int)
        self.features['TIME_SENSITIVITY_002_seasonal_commodity'] = is_electronics * 0.5

        # TIME_SENSITIVITY_003: Pre-tariff timing flag
        # Simulated: assume increased activity patterns pre-tariff
        self.features['TIME_SENSITIVITY_003_pre_tariff_rush'] = (
            (self.data['dwell_days'] < 0.5).astype(int)
        )

        # TIME_SENSITIVITY_004: High-volume period flag
        # Shipper frequency increases during pre-tariff periods
        shipper_freq = self.data['shipper_name'].value_counts()
        high_volume = (shipper_freq > shipper_freq.median() * 2).astype(int)
        shipper_volume = self.data['shipper_name'].map(high_volume).fillna(0)
        self.features['TIME_SENSITIVITY_004_high_volume_period'] = shipper_volume

        # TIME_SENSITIVITY_005: Acceleration indicator
        # Multiple shipments from same shipper in short window
        self.features['TIME_SENSITIVITY_005_shipping_acceleration'] = (
            shipper_volume * 0.5
        )

        # TIME_SENSITIVITY_006: Market event proximity (port congestion proxy)
        # High dwell = potential congestion or deliberate delay
        self.features['TIME_SENSITIVITY_006_port_congestion_proxy'] = (
            (self.data['dwell_days'] > self.data['dwell_days'].quantile(0.75))
            .astype(int)
        )

        # TIME_SENSITIVITY_007: Seasonal anomaly
        # Out-of-season shipments (e.g., fresh goods in off-season)
        self.features['TIME_SENSITIVITY_007_seasonal_anomaly'] = 0.2

        # TIME_SENSITIVITY_008: Urgency indicator (short dwell + high value)
        high_value = (
            self.data['declared_value_usd'] >
            self.data['declared_value_usd'].quantile(0.75)
        )
        short_dwell = (
            self.data['dwell_days'] < self.data['dwell_days'].quantile(0.25)
        )
        self.features['TIME_SENSITIVITY_008_urgency_indicator'] = (
            (high_value & short_dwell).astype(int)
        )

        # TIME_SENSITIVITY_009: Volume surge detection
        commodity_volume = (
            self.data.groupby('hs_code').size() / len(self.data)
        )
        commodity_volume_map = self.data['hs_code'].map(commodity_volume)
        volume_surge = (commodity_volume_map > commodity_volume_map.quantile(0.9)).astype(int)
        self.features['TIME_SENSITIVITY_009_volume_surge'] = volume_surge.fillna(0)

        # TIME_SENSITIVITY_010: Timing coordination risk
        # Multiple parties acting in coordination (same commodity, short timespan)
        commodity_shipper = (
            self.data['hs_code'].astype(str) + '-' + self.data['shipper_country'].astype(str)
        )
        combo_count = commodity_shipper.value_counts()
        coordination_risk = (
            (combo_count > combo_count.quantile(0.75)).astype(int)
        )
        self.features['TIME_SENSITIVITY_010_timing_coordination'] = (
            commodity_shipper.map(coordination_risk).fillna(0).astype(int)
        )

    def validate_features(self, feature_matrix: pd.DataFrame) -> dict:
        """Validate feature matrix quality"""

        issues = []

        # Check shape
        if feature_matrix.shape[0] != 10287:
            issues.append(f"Expected 10287 rows, got {feature_matrix.shape[0]}")

        if feature_matrix.shape[1] != 72:
            issues.append(f"Expected 72 columns, got {feature_matrix.shape[1]}")

        # Check for null values
        null_count = feature_matrix.isna().sum().sum()
        null_pct = (null_count / (feature_matrix.shape[0] * feature_matrix.shape[1])) * 100

        if null_pct > 1.0:
            issues.append(f"Null values: {null_pct:.2f}% (threshold: 1%)")

        # Check for constant features
        constant_features = []
        for col in feature_matrix.columns:
            if feature_matrix[col].nunique() == 1:
                constant_features.append(col)

        if constant_features:
            issues.append(f"Constant features found: {len(constant_features)}")

        # Check correlation matrix
        corr_matrix = feature_matrix.corr().abs()
        # Get upper triangle to avoid duplicates
        upper_triangle = corr_matrix.where(
            np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
        )
        max_corr = upper_triangle.max().max()

        if max_corr > 0.95:
            issues.append(f"High correlation detected: {max_corr:.4f} (threshold: 0.95)")

        return {
            'null_values_pct': null_pct,
            'max_correlation': max_corr,
            'constant_features': constant_features,
            'issues': issues
        }


def main():
    print("=" * 80)
    print("CBP RISK MODEL - FEATURE ENGINEERING (PHASE 1)")
    print("=" * 80)
    print()

    start_time = time.time()

    # Load data
    print("Loading training data...")
    data_path = '/home/rahulvadera/cbp-sentry/data/training_data.csv'
    engineer = FeatureEngineer(data_path)
    print(f"  - Loaded {len(engineer.data)} records")
    print()

    # Engineer features
    print("Engineering 72 features across 7 risk factors...")
    feature_matrix = engineer.engineer_features()
    print(f"  - Generated {feature_matrix.shape[1]} features")
    print(f"  - Matrix shape: {feature_matrix.shape}")
    print()

    # Validate
    print("Validating feature matrix...")
    validation = engineer.validate_features(feature_matrix)
    print(f"  - Null values: {validation['null_values_pct']:.2f}%")
    print(f"  - Max correlation: {validation['max_correlation']:.4f}")
    print(f"  - Constant features: {len(validation['constant_features'])}")

    if validation['issues']:
        print(f"  - Issues found: {len(validation['issues'])}")
        for issue in validation['issues']:
            print(f"    * {issue}")
    print()

    # Save feature matrix
    print("Saving feature matrix...")
    output_path = '/home/rahulvadera/cbp-sentry/data/feature_matrix_72.csv'
    feature_matrix.to_csv(output_path, index=False)
    print(f"  - Saved to: {output_path}")
    print()

    # Save feature definitions
    print("Saving feature definitions...")
    feature_defs = {
        "total_features": 72,
        "matrix_shape": list(feature_matrix.shape),
        "generation_timestamp": datetime.now().isoformat(),
        "factors": {
            "DOCUMENTATION_RISK": {
                "weight": 0.25,
                "count": 12,
                "features": [col for col in feature_matrix.columns if col.startswith("DOCUMENTATION")]
            },
            "ROUTING_RISK": {
                "weight": 0.15,
                "count": 10,
                "features": [col for col in feature_matrix.columns if col.startswith("ROUTING")]
            },
            "COMMODITY_RISK": {
                "weight": 0.15,
                "count": 10,
                "features": [col for col in feature_matrix.columns if col.startswith("COMMODITY")]
            },
            "CORRIDOR_RISK": {
                "weight": 0.20,
                "count": 15,
                "features": [col for col in feature_matrix.columns if col.startswith("CORRIDOR")]
            },
            "PARTY_RISK": {
                "weight": 0.15,
                "count": 10,
                "features": [col for col in feature_matrix.columns if col.startswith("PARTY")]
            },
            "PATTERN_RISK": {
                "weight": 0.10,
                "count": 10,
                "features": [col for col in feature_matrix.columns if col.startswith("PATTERN")]
            },
            "TIME_SENSITIVITY": {
                "weight": 0.10,
                "count": 10,
                "features": [col for col in feature_matrix.columns if col.startswith("TIME_SENSITIVITY")]
            }
        },
        "validation": {
            "null_values_pct": validation['null_values_pct'],
            "max_correlation": validation['max_correlation'],
            "constant_features": validation['constant_features'],
            "issues": validation['issues']
        }
    }

    defs_path = '/home/rahulvadera/cbp-sentry/data/feature_definitions_72.json'
    with open(defs_path, 'w') as f:
        json.dump(feature_defs, f, indent=2)
    print(f"  - Saved to: {defs_path}")
    print()

    # Summary
    extraction_time = time.time() - start_time
    print("=" * 80)
    print("FEATURE ENGINEERING COMPLETE")
    print("=" * 80)
    print()
    print("SUMMARY:")
    print(f"  - Features engineered: {feature_matrix.shape[1]}")
    print(f"  - Feature matrix shape: {feature_matrix.shape}")
    print(f"  - Null values: {validation['null_values_pct']:.2f}%")
    print(f"  - Max correlation: {validation['max_correlation']:.4f}")
    print(f"  - Extraction time: {extraction_time:.2f} seconds")
    print()

    # Output JSON
    output_json = {
        "features_count": feature_matrix.shape[1],
        "feature_matrix_shape": list(feature_matrix.shape),
        "null_values_pct": round(validation['null_values_pct'], 2),
        "max_correlation": round(validation['max_correlation'], 4),
        "feature_extraction_time_seconds": round(extraction_time, 2),
        "feature_matrix_path": output_path,
        "constant_features": validation['constant_features'],
        "issues": validation['issues']
    }

    print("OUTPUT JSON:")
    print(json.dumps(output_json, indent=2))

    return output_json


if __name__ == '__main__':
    main()
