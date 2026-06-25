#!/usr/bin/env python3
"""
CBP Risk Model Feature Engineering - Phase 1 (Final)
72 features organized in 7 risk factors
Optimized for data variance and correlation reduction
"""

import pandas as pd
import numpy as np
import json
import time
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Risk classifications
HIGH_RISK_COUNTRIES = {
    'IR', 'SY', 'KP', 'CU', 'CR', 'VE', 'SO', 'MM',
    'ZW', 'BY', 'XK', 'PK', 'YE', 'LY', 'SS', 'SD'
}

TRANSSHIPMENT_HUBS = {
    'SG', 'MY', 'HK', 'AE', 'PA', 'PH', 'TH', 'VN',
    'ID', 'KH', 'MM', 'LA', 'KZ'
}

CONTROLLED_HS_CODES = {
    '8471.30': 0.9,  '8517.62': 0.8,  '8542.31': 0.95,
    '9005.80': 0.85, '9015.80': 0.8,  '9030.82': 0.85,
    '9030.89': 0.85, '9031.80': 0.8,  '8534.30': 0.9,
    '8534.90': 0.85, '6204.62': 0.3,  '7225.30': 0.2,
    '7210.70': 0.2,  '2709.00': 0.1,  '3004.90': 0.4
}


class FeatureEngineer:
    def __init__(self, data_path: str):
        self.data = pd.read_csv(data_path)
        self.features = {}

    def engineer_features(self) -> pd.DataFrame:
        """Engineer exactly 72 features across 7 factors"""

        self._documentation_risk_features()
        self._routing_risk_features()
        self._commodity_risk_features()
        self._corridor_risk_features()
        self._party_risk_features()
        self._pattern_risk_features()
        self._time_sensitivity_features()

        feature_matrix = pd.DataFrame(self.features)
        return feature_matrix

    def _documentation_risk_features(self):
        """12 DOCUMENTATION_RISK features"""

        # DOCUMENTATION_001: Element 9 mismatch flag
        self.features['DOCUMENTATION_001_element9_mismatch'] = (
            self.data['element9_is_mismatch'].fillna(0).astype(float)
        )

        # DOCUMENTATION_002: Ad/CVD applicable (inverse for risk)
        self.features['DOCUMENTATION_002_adcvd_applicable'] = (
            (self.data['ad_cvd_applicable'] == 0).astype(float)
        )

        # DOCUMENTATION_003: Manifest completeness
        manifest_fields = ['shipper_name', 'consignee_name', 'hs_code', 'vessel_name']
        self.features['DOCUMENTATION_003_manifest_completeness'] = (
            self.data[manifest_fields].notna().sum(axis=1) / len(manifest_fields)
        )

        # DOCUMENTATION_004: Missing critical fields
        critical = ['shipper_country', 'origin_country', 'vessel_imo']
        self.features['DOCUMENTATION_004_missing_fields_pct'] = (
            self.data[critical].isna().sum(axis=1) / len(critical)
        )

        # DOCUMENTATION_005: Value-weight ratio anomaly (normalized)
        vw_ratio = self.data['declared_value_usd'] / (self.data['declared_weight_kg'] + 1)
        vw_med, vw_std = vw_ratio.median(), vw_ratio.std()
        self.features['DOCUMENTATION_005_value_weight_anomaly'] = (
            (np.abs(vw_ratio - vw_med) / (vw_std + 1)).clip(0, 10) / 10
        )

        # DOCUMENTATION_006: HS code control status (continuous)
        control_map = self.data['hs_code'].astype(str).map(CONTROLLED_HS_CODES).fillna(0)
        self.features['DOCUMENTATION_006_hs_code_control_level'] = control_map

        # DOCUMENTATION_007: Shipper-consignee country mismatch
        self.features['DOCUMENTATION_007_shipper_consignee_mismatch'] = (
            (self.data['shipper_country'] != self.data['consignee_country']).astype(float)
        )

        # DOCUMENTATION_008: Origin-shipper country mismatch
        self.features['DOCUMENTATION_008_origin_shipper_mismatch'] = (
            (self.data['origin_country'] != self.data['shipper_country']).astype(float)
        )

        # DOCUMENTATION_009: Country chain length (0-3)
        country_chain = (
            (self.data['origin_country'] != self.data['shipper_country']).astype(int) +
            (self.data['shipper_country'] != self.data['consignee_country']).astype(int) +
            (self.data['consignee_country'] != self.data['destination_country']).astype(int)
        )
        self.features['DOCUMENTATION_009_country_chain_length'] = (country_chain / 3)

        # DOCUMENTATION_010: Filing status risk score
        status_map = {'legitimate': 0.0, 'under_review': 0.5, 'flagged': 0.8, 'alert': 1.0}
        self.features['DOCUMENTATION_010_filing_status_risk'] = (
            self.data['status'].map(status_map).fillna(0.3)
        )

        # DOCUMENTATION_011: Dwell time z-score (normalized)
        dwell_med, dwell_std = self.data['dwell_days'].median(), self.data['dwell_days'].std()
        dwell_zscore = np.abs((self.data['dwell_days'] - dwell_med) / (dwell_std + 1))
        self.features['DOCUMENTATION_011_dwell_time_zscore'] = (dwell_zscore.clip(0, 5) / 5)

        # DOCUMENTATION_012: Manifest field count (continuous 0-1)
        all_fields = ['shipper_name', 'consignee_name', 'hs_code', 'vessel_name',
                     'declared_value_usd', 'declared_weight_kg']
        self.features['DOCUMENTATION_012_field_count_ratio'] = (
            self.data[all_fields].notna().sum(axis=1) / len(all_fields)
        )

    def _routing_risk_features(self):
        """10 ROUTING_RISK features"""

        # ROUTING_001: Transshipment hub as destination
        self.features['ROUTING_001_hub_destination'] = (
            self.data['destination_country'].isin(TRANSSHIPMENT_HUBS).astype(float)
        )

        # ROUTING_002: Origin-destination distance (indicator)
        self.features['ROUTING_002_origin_dest_distance'] = (
            (self.data['origin_country'] != self.data['destination_country']).astype(float)
        )

        # ROUTING_003: Vessel flag risk (pattern matching)
        vessel_patterns = ['Panama', 'Liberia', 'Cambodia', 'Marshall']
        self.features['ROUTING_003_vessel_flag_risk'] = (
            self.data['vessel_name'].fillna('').str.contains(
                '|'.join(vessel_patterns), case=False
            ).astype(float)
        )

        # ROUTING_004: Dwell time quartile (0-1, normalized)
        q25, q75 = self.data['dwell_days'].quantile(0.25), self.data['dwell_days'].quantile(0.75)
        dwell_norm = ((self.data['dwell_days'] - q25) / (q75 - q25 + 1)).clip(0, 1)
        self.features['ROUTING_004_dwell_time_quartile'] = dwell_norm

        # ROUTING_005: Multi-port routing indicator
        self.features['ROUTING_005_multi_port_routing'] = (
            (self.data['shipper_country'] != self.data['origin_country']).astype(float)
        )

        # ROUTING_006: Vessel IMO z-score (condition proxy)
        imo_numeric = pd.to_numeric(self.data['vessel_imo'].astype(str), errors='coerce')
        imo_med, imo_std = imo_numeric.median(), imo_numeric.std()
        imo_zscore = np.abs((imo_numeric - imo_med) / (imo_std + 1))
        self.features['ROUTING_006_vessel_condition_score'] = (imo_zscore.clip(0, 5) / 5).fillna(0)

        # ROUTING_007: Origin country frequency (continuous)
        origin_freq = self.data['origin_country'].value_counts()
        self.features['ROUTING_007_origin_frequency'] = (
            self.data['origin_country'].map(origin_freq) / len(self.data)
        )

        # ROUTING_008: Complex routing indicator (3+ countries)
        country_count = (
            (self.data['origin_country'] != self.data['shipper_country']).astype(int) +
            (self.data['shipper_country'] != self.data['consignee_country']).astype(int) +
            (self.data['consignee_country'] != self.data['destination_country']).astype(int)
        )
        self.features['ROUTING_008_complex_routing'] = ((country_count >= 2).astype(float))

        # ROUTING_009: Transshipment corridor (hub involvement)
        self.features['ROUTING_009_transshipment_corridor'] = (
            (self.data['shipper_country'].isin(TRANSSHIPMENT_HUBS) |
             self.data['origin_country'].isin(TRANSSHIPMENT_HUBS)).astype(float)
        )

        # ROUTING_010: Destination mismatch (consignee != destination)
        self.features['ROUTING_010_destination_mismatch'] = (
            (self.data['consignee_country'] != self.data['destination_country']).astype(float)
        )

    def _commodity_risk_features(self):
        """10 COMMODITY_RISK features"""

        # COMMODITY_001: HS code control level (continuous 0-1)
        control_map = self.data['hs_code'].astype(str).map(CONTROLLED_HS_CODES).fillna(0)
        self.features['COMMODITY_001_hs_control_level'] = control_map

        # COMMODITY_002: High-value flag (above 75th percentile)
        value_q75 = self.data['declared_value_usd'].quantile(0.75)
        self.features['COMMODITY_002_high_value_flag'] = (
            (self.data['declared_value_usd'] > value_q75).astype(float)
        )

        # COMMODITY_003: Electronics/semiconductors indicator
        electronics = ['8471.30', '8517.62', '8542.31', '8534.30']
        self.features['COMMODITY_003_electronics_flag'] = (
            self.data['hs_code'].astype(str).isin(electronics).astype(float)
        )

        # COMMODITY_004: Precious materials indicator
        precious_prefixes = ['7108', '7109', '7110', '7111', '7112']
        precious = self.data['hs_code'].astype(str).str.startswith(tuple(precious_prefixes))
        self.features['COMMODITY_004_precious_materials'] = precious.astype(float).fillna(0)

        # COMMODITY_005: Unit price z-score (normalized)
        unit_price = self.data['declared_value_usd'] / (self.data['declared_weight_kg'] + 1)
        price_med, price_std = unit_price.median(), unit_price.std()
        price_zscore = np.abs((unit_price - price_med) / (price_std + 1))
        self.features['COMMODITY_005_unit_price_anomaly'] = (price_zscore.clip(0, 5) / 5)

        # COMMODITY_006: Weight anomaly (quartile-based)
        q75, q25 = (self.data['declared_weight_kg'].quantile(0.75),
                    self.data['declared_weight_kg'].quantile(0.25))
        weight_anom = ((self.data['declared_weight_kg'] > q75 * 1.5) |
                       (self.data['declared_weight_kg'] < q25 * 0.5)).astype(float)
        self.features['COMMODITY_006_weight_anomaly'] = weight_anom

        # COMMODITY_007: Commodity-origin pairing risk
        is_electronics = self.data['hs_code'].astype(str).isin(electronics)
        tech_origins = ['CN', 'JP', 'KR', 'TW', 'MY', 'SG', 'TH']
        pairing_risk = (is_electronics &
                       ~self.data['origin_country'].isin(tech_origins)).astype(float)
        self.features['COMMODITY_007_commodity_origin_risk'] = pairing_risk

        # COMMODITY_008: Dual-use equipment indicator
        dual_use = ['8471.30', '8517.62', '8542.31', '9005.80', '9030.82']
        self.features['COMMODITY_008_dual_use_equipment'] = (
            self.data['hs_code'].astype(str).isin(dual_use).astype(float)
        )

        # COMMODITY_009: Commodity frequency (normalized)
        hs_freq = self.data['hs_code'].astype(str).value_counts()
        commodity_freq = self.data['hs_code'].astype(str).map(hs_freq) / len(self.data)
        self.features['COMMODITY_009_commodity_frequency'] = commodity_freq

        # COMMODITY_010: Restricted destination match
        restricted = HIGH_RISK_COUNTRIES
        restricted_match = (self.data['destination_country'].isin(restricted) &
                           self.data['hs_code'].astype(str).isin(dual_use)).astype(float)
        self.features['COMMODITY_010_restricted_destination_match'] = restricted_match

    def _corridor_risk_features(self):
        """15 CORRIDOR_RISK features"""

        # CORRIDOR_001: Origin risk (0-1 scale)
        origin_risk = self.data['origin_country'].apply(
            lambda x: 0.95 if x in HIGH_RISK_COUNTRIES else 0.15
        )
        self.features['CORRIDOR_001_origin_risk_score'] = origin_risk

        # CORRIDOR_002: Destination risk (0-1 scale)
        dest_risk = self.data['destination_country'].apply(
            lambda x: 0.95 if x in HIGH_RISK_COUNTRIES else 0.05
        )
        self.features['CORRIDOR_002_destination_risk_score'] = dest_risk

        # CORRIDOR_003: Shipper country risk (0-1 scale)
        shipper_risk = self.data['shipper_country'].apply(
            lambda x: 0.95 if x in HIGH_RISK_COUNTRIES else (
                0.7 if x in TRANSSHIPMENT_HUBS else 0.15
            )
        )
        self.features['CORRIDOR_003_shipper_risk_score'] = shipper_risk

        # CORRIDOR_004: Supply chain complexity (0-1)
        complexity = (
            (self.data['origin_country'] != self.data['shipper_country']).astype(int) +
            (self.data['shipper_country'] != self.data['consignee_country']).astype(int) +
            (self.data['consignee_country'] != self.data['destination_country']).astype(int)
        )
        self.features['CORRIDOR_004_supply_chain_complexity'] = (complexity / 3)

        # CORRIDOR_005: High-risk route indicator
        high_risk_routes = [
            ('CN', 'IR'), ('CN', 'SY'), ('KP', 'CN'), ('VE', 'US'),
            ('IR', 'US'), ('SY', 'US'), ('CU', 'US')
        ]
        is_high_risk = self.data.apply(
            lambda row: (row['origin_country'], row['destination_country']) in high_risk_routes,
            axis=1
        ).astype(float)
        self.features['CORRIDOR_005_high_risk_route'] = is_high_risk

        # CORRIDOR_006: SE Asia hub risk (0-1)
        se_asia = ['SG', 'MY', 'TH', 'VN', 'ID', 'PH']
        se_risk = (
            self.data['shipper_country'].isin(se_asia).astype(int) |
            self.data['origin_country'].isin(se_asia).astype(int)
        ).astype(float)
        self.features['CORRIDOR_006_se_asia_hub_risk'] = se_risk

        # CORRIDOR_007: China origin indicator
        self.features['CORRIDOR_007_china_origin_indicator'] = (
            (self.data['origin_country'] == 'CN').astype(float)
        )

        # CORRIDOR_008: Hong Kong transshipment
        hk = (
            (self.data['origin_country'] == 'HK') |
            (self.data['shipper_country'] == 'HK') |
            (self.data['destination_country'] == 'HK')
        ).astype(float)
        self.features['CORRIDOR_008_hong_kong_route'] = hk

        # CORRIDOR_009: Corridor frequency (normalized)
        corridor = (
            self.data['origin_country'].astype(str) + '-' +
            self.data['destination_country'].astype(str)
        )
        corridor_freq = corridor.value_counts()
        self.features['CORRIDOR_009_corridor_frequency'] = (
            corridor.map(corridor_freq) / len(self.data)
        )

        # CORRIDOR_010: Panama jurisdiction risk
        self.features['CORRIDOR_010_panama_jurisdiction'] = (
            (self.data['shipper_country'] == 'PA').astype(float)
        )

        # CORRIDOR_011: Geographic distance proxy (0-1)
        near = ['US', 'CA', 'MX']
        far = ['CN', 'JP', 'IN', 'VN', 'TH']
        dist = self.data['origin_country'].apply(
            lambda x: 0.1 if x in near else (0.9 if x in far else 0.5)
        )
        self.features['CORRIDOR_011_geographic_distance'] = dist

        # CORRIDOR_012: Sanctioned shipper match
        sanctioned = ['North Korea', 'Iranian', 'Syria', 'Crimea', 'Donetsk']
        sanctioned_s = self.data['shipper_name'].fillna('').str.contains(
            '|'.join(sanctioned), case=False, na=False
        ).astype(float)
        self.features['CORRIDOR_012_sanctioned_shipper'] = sanctioned_s

        # CORRIDOR_013: Sanctioned consignee match
        sanctioned_c = self.data['consignee_name'].fillna('').str.contains(
            '|'.join(sanctioned), case=False, na=False
        ).astype(float)
        self.features['CORRIDOR_013_sanctioned_consignee'] = sanctioned_c

        # CORRIDOR_014: Multi-hop indicator
        multihop = (
            (self.data['origin_country'] != self.data['shipper_country']) &
            (self.data['shipper_country'] != self.data['destination_country'])
        ).astype(float)
        self.features['CORRIDOR_014_multi_hop_routing'] = multihop

        # CORRIDOR_015: Combined corridor risk (0-1)
        self.features['CORRIDOR_015_combined_corridor_risk'] = (
            (origin_risk + dest_risk + shipper_risk) / 3
        )

    def _party_risk_features(self):
        """10 PARTY_RISK features"""

        # PARTY_001: Shipper age risk (newer = higher risk, normalized)
        shipper_age = self.data['shipper_age_months'].fillna(
            self.data['shipper_age_months'].median()
        )
        age_norm = (1 - (shipper_age / (shipper_age.max() + 1))).clip(0, 1)
        self.features['PARTY_001_shipper_age_risk'] = age_norm

        # PARTY_002: New shipper flag (< 12 months)
        self.features['PARTY_002_new_shipper_flag'] = (
            (self.data['shipper_age_months'] < 12).fillna(False).astype(float)
        )

        # PARTY_003: Very new shipper (< 6 months)
        self.features['PARTY_003_very_new_shipper_flag'] = (
            (self.data['shipper_age_months'] < 6).fillna(False).astype(float)
        )

        # PARTY_004: Shipper name opacity (0-1)
        shipper_opacity = self.data['shipper_name'].fillna('').apply(
            lambda x: 1.0 if len(x) < 5 or 'Unknown' in x or 'N/A' in x else 0.0
        )
        self.features['PARTY_004_shipper_name_opacity'] = shipper_opacity

        # PARTY_005: Generic name score (0-1)
        generic_patterns = ['Corp', 'LLC', 'Ltd', 'Inc', 'Trading', 'Export']
        generic = self.data['shipper_name'].fillna('').apply(
            lambda x: sum(1 for p in generic_patterns if p in x) / len(generic_patterns)
        )
        self.features['PARTY_005_generic_name_score'] = generic

        # PARTY_006: Shipper legitimacy score (0-1)
        legit_countries = {'US', 'CA', 'MX', 'JP', 'DE', 'GB', 'AU', 'SG'}
        legitimacy = (self.data['shipper_country'].isin(legit_countries)).astype(float)
        self.features['PARTY_006_shipper_legitimacy_score'] = legitimacy

        # PARTY_007: Shipper-consignee match indicator
        name_match = (self.data['shipper_name'] == self.data['consignee_name']).astype(float)
        self.features['PARTY_007_shipper_consignee_match'] = name_match

        # PARTY_008: Shipper repeat frequency (normalized)
        shipper_freq = self.data['shipper_name'].value_counts()
        repeat_freq = self.data['shipper_name'].map(shipper_freq) / len(self.data)
        self.features['PARTY_008_shipper_repeat_frequency'] = repeat_freq.fillna(0)

        # PARTY_009: Party location mismatch (0-1)
        location_mismatch = (
            (self.data['shipper_country'] != self.data['origin_country']).astype(int) +
            (self.data['consignee_country'] != self.data['destination_country']).astype(int)
        )
        self.features['PARTY_009_location_mismatch_score'] = (location_mismatch / 2)

        # PARTY_010: Combined party risk (0-1)
        party_risk = (shipper_opacity + generic + (1 - legitimacy)) / 3
        self.features['PARTY_010_combined_party_risk'] = party_risk.clip(0, 1)

    def _pattern_risk_features(self):
        """10 PATTERN_RISK features"""

        # PATTERN_001: Value distribution anomaly (0-1)
        val_med = self.data['declared_value_usd'].median()
        val_std = self.data['declared_value_usd'].std()
        val_zscore = np.abs((self.data['declared_value_usd'] - val_med) / (val_std + 1))
        self.features['PATTERN_001_value_anomaly_score'] = (val_zscore.clip(0, 5) / 5)

        # PATTERN_002: Weight anomaly (0-1)
        wt_med = self.data['declared_weight_kg'].median()
        wt_std = self.data['declared_weight_kg'].std()
        wt_zscore = np.abs((self.data['declared_weight_kg'] - wt_med) / (wt_std + 1))
        self.features['PATTERN_002_weight_anomaly_score'] = (wt_zscore.clip(0, 5) / 5)

        # PATTERN_003: Value-weight ratio anomaly (0-1)
        vw_ratio = self.data['declared_value_usd'] / (self.data['declared_weight_kg'] + 1)
        vw_med, vw_std = vw_ratio.median(), vw_ratio.std()
        vw_zscore = np.abs((vw_ratio - vw_med) / (vw_std + 1))
        self.features['PATTERN_003_vw_ratio_anomaly_score'] = (vw_zscore.clip(0, 5) / 5)

        # PATTERN_004: Dwell anomaly (0-1)
        dw_med = self.data['dwell_days'].median()
        dw_std = self.data['dwell_days'].std()
        dw_zscore = np.abs((self.data['dwell_days'] - dw_med) / (dw_std + 1))
        self.features['PATTERN_004_dwell_anomaly_score'] = (dw_zscore.clip(0, 5) / 5)

        # PATTERN_005: Ensemble anomaly (average of 4 above)
        ensemble = np.mean([
            self.features['PATTERN_001_value_anomaly_score'],
            self.features['PATTERN_002_weight_anomaly_score'],
            self.features['PATTERN_003_vw_ratio_anomaly_score'],
            self.features['PATTERN_004_dwell_anomaly_score']
        ], axis=0)
        self.features['PATTERN_005_ensemble_anomaly'] = ensemble

        # PATTERN_006: Rare shipper-destination combo
        shipper_dest = (
            self.data['shipper_country'].astype(str) + '-' +
            self.data['destination_country'].astype(str)
        )
        sd_freq = shipper_dest.value_counts()
        rare_combo = ((sd_freq <= 2).astype(int).to_dict())
        self.features['PATTERN_006_rare_shipper_dest'] = (
            shipper_dest.map(lambda x: rare_combo.get(x, 0)).fillna(0).astype(float)
        )

        # PATTERN_007: Corridor price deviation (0-1)
        corridor = (
            self.data['origin_country'].astype(str) + '->' +
            self.data['destination_country'].astype(str)
        )
        corridor_avg = self.data.groupby(corridor)['declared_value_usd'].transform('mean')
        price_dev = np.abs(self.data['declared_value_usd'] - corridor_avg) / (corridor_avg + 1)
        self.features['PATTERN_007_corridor_price_deviation'] = (price_dev.clip(0, 5) / 5)

        # PATTERN_008: Rare commodity-origin pair
        commodity_origin = (
            self.data['hs_code'].astype(str) + '-' +
            self.data['origin_country'].astype(str)
        )
        co_freq = commodity_origin.value_counts()
        rare_commodity = ((co_freq <= 2).astype(int).to_dict())
        self.features['PATTERN_008_rare_commodity_origin'] = (
            commodity_origin.map(lambda x: rare_commodity.get(x, 0)).fillna(0).astype(float)
        )

        # PATTERN_009: Shipper commodity concentration (0-1)
        shipper_freq = self.data['shipper_name'].value_counts()
        shipper_conc = (self.data['shipper_name'].map(shipper_freq) / len(self.data)).fillna(0)
        self.features['PATTERN_009_shipper_concentration'] = shipper_conc

        # PATTERN_010: Multi-dimensional outlier score (0-1)
        outlier = (
            (val_zscore > 2).astype(int) +
            (wt_zscore > 2).astype(int) +
            (vw_zscore > 2).astype(int) +
            (dw_zscore > 2).astype(int)
        )
        self.features['PATTERN_010_multidim_outlier_score'] = (outlier / 4)

    def _time_sensitivity_features(self):
        """5 TIME_SENSITIVITY features"""

        # TIME_SENSITIVITY_001: Accelerated shipping (< 0.5 days dwell)
        self.features['TIME_SENSITIVITY_001_accelerated_shipping'] = (
            (self.data['dwell_days'] < 0.5).astype(float)
        )

        # TIME_SENSITIVITY_002: High-volume shipper period
        shipper_freq = self.data['shipper_name'].value_counts()
        high_vol = (shipper_freq > shipper_freq.median()).astype(int)
        self.features['TIME_SENSITIVITY_002_high_volume_shipper'] = (
            self.data['shipper_name'].map(high_vol).fillna(0).astype(float)
        )

        # TIME_SENSITIVITY_003: Port congestion indicator
        self.features['TIME_SENSITIVITY_003_port_congestion_proxy'] = (
            (self.data['dwell_days'] > self.data['dwell_days'].quantile(0.75)).astype(float)
        )

        # TIME_SENSITIVITY_004: Urgency indicator (high value + short dwell)
        high_val = self.data['declared_value_usd'] > self.data['declared_value_usd'].quantile(0.75)
        short = self.data['dwell_days'] < self.data['dwell_days'].quantile(0.25)
        self.features['TIME_SENSITIVITY_004_urgency_indicator'] = ((high_val & short).astype(float))

        # TIME_SENSITIVITY_005: Commodity volume surge
        hs_freq = self.data['hs_code'].astype(str).value_counts()
        surge_threshold = hs_freq.quantile(0.85)
        surge = (hs_freq > surge_threshold).astype(int)
        self.features['TIME_SENSITIVITY_005_commodity_surge'] = (
            self.data['hs_code'].astype(str).map(surge).fillna(0).astype(float)
        )

    def validate_features(self, fm: pd.DataFrame) -> dict:
        """Validate feature matrix"""

        issues = []

        if fm.shape[0] != 10287:
            issues.append(f"Expected 10287 rows, got {fm.shape[0]}")

        if fm.shape[1] != 72:
            issues.append(f"Expected 72 columns, got {fm.shape[1]}")

        null_count = fm.isna().sum().sum()
        null_pct = (null_count / (fm.shape[0] * fm.shape[1])) * 100

        constant_features = [col for col in fm.columns if fm[col].nunique() <= 1]

        corr_matrix = fm.corr().abs()
        upper_tri = corr_matrix.where(
            np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
        )
        max_corr = upper_tri.max().max()
        max_corr = 0.0 if np.isnan(max_corr) else max_corr

        if null_pct > 1.0:
            issues.append(f"Null values: {null_pct:.2f}%")

        if constant_features:
            issues.append(f"Constant features: {len(constant_features)}")

        if max_corr > 0.95:
            issues.append(f"High correlation: {max_corr:.4f}")

        return {
            'null_values_pct': null_pct,
            'max_correlation': max_corr,
            'constant_features': constant_features,
            'issues': issues
        }


def main():
    print("=" * 80)
    print("CBP RISK MODEL - FEATURE ENGINEERING (FINAL)")
    print("=" * 80)
    print()

    start_time = time.time()

    print("Loading training data...")
    engineer = FeatureEngineer('/home/rahulvadera/cbp-sentry/data/training_data.csv')
    print(f"  - Loaded {len(engineer.data)} records")
    print()

    print("Engineering 72 features across 7 risk factors...")
    fm = engineer.engineer_features()
    print(f"  - Matrix shape: {fm.shape}")
    print()

    print("Validating feature matrix...")
    validation = engineer.validate_features(fm)
    print(f"  - Null values: {validation['null_values_pct']:.2f}%")
    print(f"  - Max correlation: {validation['max_correlation']:.4f}")
    print(f"  - Constant features: {len(validation['constant_features'])}")

    if validation['issues']:
        print(f"  - Issues:")
        for issue in validation['issues']:
            print(f"    * {issue}")
    print()

    print("Saving outputs...")
    output_path = '/home/rahulvadera/cbp-sentry/data/feature_matrix_72.csv'
    fm.to_csv(output_path, index=False)
    print(f"  - Feature matrix: {output_path}")

    feature_defs = {
        "total_features": fm.shape[1],
        "matrix_shape": list(fm.shape),
        "generation_timestamp": datetime.now().isoformat(),
        "factors": {
            "DOCUMENTATION_RISK": {"weight": 0.25, "count": 12,
                "features": [c for c in fm.columns if c.startswith("DOCUMENTATION")]},
            "ROUTING_RISK": {"weight": 0.15, "count": 10,
                "features": [c for c in fm.columns if c.startswith("ROUTING")]},
            "COMMODITY_RISK": {"weight": 0.15, "count": 10,
                "features": [c for c in fm.columns if c.startswith("COMMODITY")]},
            "CORRIDOR_RISK": {"weight": 0.20, "count": 15,
                "features": [c for c in fm.columns if c.startswith("CORRIDOR")]},
            "PARTY_RISK": {"weight": 0.15, "count": 10,
                "features": [c for c in fm.columns if c.startswith("PARTY")]},
            "PATTERN_RISK": {"weight": 0.10, "count": 10,
                "features": [c for c in fm.columns if c.startswith("PATTERN")]},
            "TIME_SENSITIVITY": {"weight": 0.10, "count": 5,
                "features": [c for c in fm.columns if c.startswith("TIME_SENSITIVITY")]},
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
    print(f"  - Feature definitions: {defs_path}")
    print()

    extraction_time = time.time() - start_time

    print("=" * 80)
    print("FEATURE ENGINEERING COMPLETE")
    print("=" * 80)
    print()

    output_json = {
        "features_count": fm.shape[1],
        "feature_matrix_shape": list(fm.shape),
        "null_values_pct": round(validation['null_values_pct'], 2),
        "max_correlation": round(validation['max_correlation'], 4),
        "feature_extraction_time_seconds": round(extraction_time, 2),
        "feature_matrix_path": output_path,
        "constant_features": validation['constant_features'],
        "issues": validation['issues']
    }

    print(json.dumps(output_json, indent=2))
    return output_json


if __name__ == '__main__':
    main()
