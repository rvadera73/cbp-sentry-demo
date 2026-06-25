#!/usr/bin/env python3
"""
CBP Risk Model Feature Engineering - Phase 1 (v2)
72 features organized in 7 risk factors
Improved version with better data quality and feature engineering
"""

import pandas as pd
import numpy as np
import json
import time
from datetime import datetime
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
        self.start_time = time.time()

    def engineer_features(self) -> pd.DataFrame:
        """Engineer exactly 72 features across 7 factors"""

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

        # TIME_SENSITIVITY (5 features) - adjusted to 5 to match total
        self._time_sensitivity_features()

        feature_matrix = pd.DataFrame(self.features)

        # Verify count
        actual_count = len(self.features)
        print(f"  - Features generated: {actual_count}")

        return feature_matrix

    def _documentation_risk_features(self):
        """12 DOCUMENTATION_RISK features"""

        # DOCUMENTATION_001: Element 9 mismatch flag
        self.features['DOCUMENTATION_001_element9_mismatch'] = (
            self.data['element9_is_mismatch'].fillna(0).astype(float)
        )

        # DOCUMENTATION_002: Ad/CVD applicable
        self.features['DOCUMENTATION_002_adcvd_applicable'] = (
            (self.data['ad_cvd_applicable'] == 0).astype(float)
        )

        # DOCUMENTATION_003: Manifest completeness score
        manifest_fields = ['shipper_name', 'consignee_name', 'hs_code', 'vessel_name']
        completeness = self.data[manifest_fields].notna().sum(axis=1) / len(manifest_fields)
        self.features['DOCUMENTATION_003_manifest_completeness'] = completeness

        # DOCUMENTATION_004: Missing critical fields
        critical = ['shipper_country', 'origin_country', 'vessel_imo']
        missing = self.data[critical].isna().sum(axis=1) / len(critical)
        self.features['DOCUMENTATION_004_missing_fields'] = missing

        # DOCUMENTATION_005: Value-weight ratio anomaly
        vw_ratio = self.data['declared_value_usd'] / (self.data['declared_weight_kg'] + 1)
        vw_median, vw_std = vw_ratio.median(), vw_ratio.std()
        vw_anomaly = np.abs(vw_ratio - vw_median) / (vw_std + 1)
        self.features['DOCUMENTATION_005_value_weight_anomaly'] = (vw_anomaly.clip(0, 10) / 10)

        # DOCUMENTATION_006: HS code in controlled list
        self.features['DOCUMENTATION_006_hs_code_controlled'] = (
            self.data['hs_code'].astype(str).isin(CONTROLLED_HS_CODES.keys()).astype(float)
        )

        # DOCUMENTATION_007: Shipper-consignee country mismatch
        self.features['DOCUMENTATION_007_shipper_consignee_mismatch'] = (
            (self.data['shipper_country'] != self.data['consignee_country']).astype(float)
        )

        # DOCUMENTATION_008: Origin-shipper country mismatch
        self.features['DOCUMENTATION_008_origin_shipper_mismatch'] = (
            (self.data['origin_country'] != self.data['shipper_country']).astype(float)
        )

        # DOCUMENTATION_009: Multiple country involvement
        country_mix = (
            (self.data['origin_country'] != self.data['shipper_country']).astype(int) +
            (self.data['shipper_country'] != self.data['consignee_country']).astype(int) +
            (self.data['consignee_country'] != self.data['destination_country']).astype(int)
        )
        self.features['DOCUMENTATION_009_country_mix_score'] = (country_mix / 3)

        # DOCUMENTATION_010: Filing status risk
        status_risk = self.data['status'].map({
            'legitimate': 0.0, 'under_review': 0.5, 'flagged': 0.8, 'alert': 1.0
        }).fillna(0.3)
        self.features['DOCUMENTATION_010_filing_status_risk'] = status_risk

        # DOCUMENTATION_011: Dwell time anomaly
        dwell_median, dwell_std = self.data['dwell_days'].median(), self.data['dwell_days'].std()
        dwell_zscore = np.abs((self.data['dwell_days'] - dwell_median) / (dwell_std + 1))
        self.features['DOCUMENTATION_011_dwell_time_anomaly'] = (dwell_zscore.clip(0, 5) / 5)

        # DOCUMENTATION_012: ISF filing completeness
        isf_proxy = self.data[['element9_is_mismatch']].notna().astype(float).mean(axis=1)
        self.features['DOCUMENTATION_012_isf_filing_complete'] = isf_proxy

    def _routing_risk_features(self):
        """10 ROUTING_RISK features"""

        # ROUTING_001: Transshipment hub as destination
        self.features['ROUTING_001_transshipment_hub_dest'] = (
            self.data['destination_country'].isin(TRANSSHIPMENT_HUBS).astype(float)
        )

        # ROUTING_002: Origin-destination routing distance
        self.features['ROUTING_002_origin_dest_distance'] = (
            (self.data['origin_country'] != self.data['destination_country']).astype(float)
        )

        # ROUTING_003: Vessel flag risk score
        vessel_flag_patterns = ['Panama', 'Liberia', 'Cambodia', 'Marshall']
        vessel_flag_risk = self.data['vessel_name'].fillna('').str.contains(
            '|'.join(vessel_flag_patterns), case=False
        ).astype(float)
        self.features['ROUTING_003_vessel_flag_risk'] = vessel_flag_risk

        # ROUTING_004: AIS dwell high anomaly
        dwell_q75 = self.data['dwell_days'].quantile(0.75)
        dwell_iqr = self.data['dwell_days'].quantile(0.25)
        high_dwell = ((self.data['dwell_days'] > dwell_q75 * 1.5) |
                      (self.data['dwell_days'] < dwell_iqr * 0.5)).astype(float)
        self.features['ROUTING_004_dwell_anomaly'] = high_dwell

        # ROUTING_005: Multi-port routing (shipper != origin)
        self.features['ROUTING_005_multi_port_routing'] = (
            (self.data['shipper_country'] != self.data['origin_country']).astype(float)
        )

        # ROUTING_006: Vessel IMO age/condition proxy
        imo_numeric = pd.to_numeric(self.data['vessel_imo'].astype(str), errors='coerce')
        imo_median, imo_std = imo_numeric.median(), imo_numeric.std()
        imo_zscore = np.abs((imo_numeric - imo_median) / (imo_std + 1))
        self.features['ROUTING_006_vessel_condition_risk'] = (imo_zscore.clip(0, 5) / 5).fillna(0)

        # ROUTING_007: Port frequency concentration
        origin_freq = self.data['origin_country'].value_counts()
        port_concentration = self.data['origin_country'].map(origin_freq) / len(self.data)
        self.features['ROUTING_007_port_frequency'] = port_concentration.fillna(0)

        # ROUTING_008: Cross-border chain (3+ countries)
        cross_border = (country_mix := (
            (self.data['origin_country'] != self.data['shipper_country']).astype(int) +
            (self.data['shipper_country'] != self.data['consignee_country']).astype(int) +
            (self.data['consignee_country'] != self.data['destination_country']).astype(int)
        ) >= 2).astype(float)
        self.features['ROUTING_008_complex_routing_chain'] = cross_border

        # ROUTING_009: Transshipment corridor indicator
        transship_corridor = (
            self.data['shipper_country'].isin(TRANSSHIPMENT_HUBS) |
            self.data['origin_country'].isin(TRANSSHIPMENT_HUBS)
        ).astype(float)
        self.features['ROUTING_009_transshipment_corridor'] = transship_corridor

        # ROUTING_010: Direct destination mismatch
        self.features['ROUTING_010_destination_mismatch'] = (
            (self.data['consignee_country'] != self.data['destination_country']).astype(float)
        )

    def _commodity_risk_features(self):
        """10 COMMODITY_RISK features"""

        # COMMODITY_001: HS code control status
        control_map = self.data['hs_code'].astype(str).map(CONTROLLED_HS_CODES).fillna(0)
        self.features['COMMODITY_001_hs_control_status'] = control_map

        # COMMODITY_002: High-value flag
        value_q75 = self.data['declared_value_usd'].quantile(0.75)
        self.features['COMMODITY_002_high_value'] = (
            (self.data['declared_value_usd'] > value_q75).astype(float)
        )

        # COMMODITY_003: Electronics/semiconductors flag
        electronics_codes = ['8471.30', '8517.62', '8542.31', '8534.30']
        self.features['COMMODITY_003_electronics_flag'] = (
            self.data['hs_code'].astype(str).isin(electronics_codes).astype(float)
        )

        # COMMODITY_004: Precious metals/materials
        precious_prefixes = ['7108', '7109', '7110', '7111', '7112']
        precious = self.data['hs_code'].astype(str).str.startswith(tuple(precious_prefixes))
        self.features['COMMODITY_004_precious_materials'] = precious.astype(float).fillna(0)

        # COMMODITY_005: Unit price anomaly
        unit_price = self.data['declared_value_usd'] / (self.data['declared_weight_kg'] + 1)
        price_med, price_std = unit_price.median(), unit_price.std()
        price_zscore = np.abs((unit_price - price_med) / (price_std + 1))
        self.features['COMMODITY_005_unit_price_anomaly'] = (price_zscore.clip(0, 5) / 5)

        # COMMODITY_006: Weight anomaly
        weight_q75, weight_q25 = (
            self.data['declared_weight_kg'].quantile(0.75),
            self.data['declared_weight_kg'].quantile(0.25)
        )
        weight_anom = ((self.data['declared_weight_kg'] > weight_q75 * 2) |
                       (self.data['declared_weight_kg'] < weight_q25 * 0.5)).astype(float)
        self.features['COMMODITY_006_weight_anomaly'] = weight_anom

        # COMMODITY_007: Commodity-origin pairing risk
        is_electronics = self.data['hs_code'].astype(str).isin(electronics_codes)
        tech_origins = ['CN', 'JP', 'KR', 'TW', 'MY', 'SG', 'TH']
        pairing_risk = (is_electronics &
                       ~self.data['origin_country'].isin(tech_origins)).astype(float)
        self.features['COMMODITY_007_commodity_origin_risk'] = pairing_risk

        # COMMODITY_008: Dual-use equipment indicator
        dual_use_codes = ['8471.30', '8517.62', '8542.31', '9005.80', '9030.82']
        self.features['COMMODITY_008_dual_use_equipment'] = (
            self.data['hs_code'].astype(str).isin(dual_use_codes).astype(float)
        )

        # COMMODITY_009: Commodity concentration risk
        hs_freq = self.data['hs_code'].astype(str).value_counts()
        commodity_conc = self.data['hs_code'].astype(str).map(hs_freq) / len(self.data)
        self.features['COMMODITY_009_commodity_frequency'] = commodity_conc

        # COMMODITY_010: Restricted destination commodity match
        restricted_dests = HIGH_RISK_COUNTRIES
        restricted = (self.data['destination_country'].isin(restricted_dests) &
                     self.data['hs_code'].astype(str).isin(dual_use_codes)).astype(float)
        self.features['COMMODITY_010_restricted_destination'] = restricted

    def _corridor_risk_features(self):
        """15 CORRIDOR_RISK features"""

        # CORRIDOR_001: Origin country risk
        origin_risk = self.data['origin_country'].apply(
            lambda x: 0.95 if x in HIGH_RISK_COUNTRIES else 0.2
        )
        self.features['CORRIDOR_001_origin_risk_score'] = origin_risk

        # CORRIDOR_002: Destination country risk
        dest_risk = self.data['destination_country'].apply(
            lambda x: 0.95 if x in HIGH_RISK_COUNTRIES else 0.1
        )
        self.features['CORRIDOR_002_destination_risk_score'] = dest_risk

        # CORRIDOR_003: Shipper country risk
        shipper_risk = self.data['shipper_country'].apply(
            lambda x: 0.95 if x in HIGH_RISK_COUNTRIES else (
                0.7 if x in TRANSSHIPMENT_HUBS else 0.2
            )
        )
        self.features['CORRIDOR_003_shipper_risk_score'] = shipper_risk

        # CORRIDOR_004: Supply chain complexity
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

        # CORRIDOR_006: Southeast Asia hub risk
        se_asia_risk = (
            self.data['shipper_country'].isin(['SG', 'MY', 'TH', 'VN', 'ID', 'PH']).astype(int) |
            self.data['origin_country'].isin(['SG', 'MY', 'TH', 'VN', 'ID', 'PH']).astype(int)
        ).astype(float)
        self.features['CORRIDOR_006_se_asia_hub_risk'] = se_asia_risk

        # CORRIDOR_007: China origin indicator
        self.features['CORRIDOR_007_china_origin'] = (
            (self.data['origin_country'] == 'CN').astype(float)
        )

        # CORRIDOR_008: Hong Kong transshipment
        hk_indicator = (
            (self.data['origin_country'] == 'HK') |
            (self.data['shipper_country'] == 'HK') |
            (self.data['destination_country'] == 'HK')
        ).astype(float)
        self.features['CORRIDOR_008_hong_kong_route'] = hk_indicator

        # CORRIDOR_009: Corridor frequency (popularity)
        corridor_pair = (
            self.data['origin_country'].astype(str) + '-' +
            self.data['destination_country'].astype(str)
        )
        corridor_freq = corridor_pair.value_counts()
        self.features['CORRIDOR_009_corridor_frequency'] = (
            corridor_pair.map(corridor_freq) / len(self.data)
        )

        # CORRIDOR_010: Panama flag/jurisdiction risk
        panama_risk = (self.data['shipper_country'] == 'PA').astype(float)
        self.features['CORRIDOR_010_panama_risk'] = panama_risk

        # CORRIDOR_011: Geographic distance (proxy)
        near_origins = ['US', 'CA', 'MX']
        far_origins = ['CN', 'JP', 'IN', 'VN', 'TH']
        dist_score = self.data['origin_country'].apply(
            lambda x: 0.1 if x in near_origins else (0.9 if x in far_origins else 0.5)
        )
        self.features['CORRIDOR_011_geographic_distance'] = dist_score

        # CORRIDOR_012: Sanctioned entity indicator (shipper)
        sanctioned_patterns = ['North Korea', 'Iranian', 'Syria', 'Crimea', 'Donetsk']
        sanctioned_shipper = self.data['shipper_name'].fillna('').str.contains(
            '|'.join(sanctioned_patterns), case=False, na=False
        ).astype(float)
        self.features['CORRIDOR_012_sanctioned_shipper'] = sanctioned_shipper

        # CORRIDOR_013: Sanctioned entity indicator (consignee)
        sanctioned_consignee = self.data['consignee_name'].fillna('').str.contains(
            '|'.join(sanctioned_patterns), case=False, na=False
        ).astype(float)
        self.features['CORRIDOR_013_sanctioned_consignee'] = sanctioned_consignee

        # CORRIDOR_014: Multi-hop indicator
        multihop = ((self.data['origin_country'] != self.data['shipper_country']) &
                   (self.data['shipper_country'] != self.data['destination_country'])).astype(float)
        self.features['CORRIDOR_014_multi_hop_routing'] = multihop

        # CORRIDOR_015: Corridor risk multiplier
        corridor_risk = (origin_risk + dest_risk) / 2
        self.features['CORRIDOR_015_corridor_risk_multiplier'] = corridor_risk

    def _party_risk_features(self):
        """10 PARTY_RISK features"""

        # PARTY_001: Shipper age risk (newer = riskier)
        shipper_age = self.data['shipper_age_months'].fillna(
            self.data['shipper_age_months'].median()
        )
        age_max = shipper_age.max() + 1
        self.features['PARTY_001_shipper_age_risk'] = (1 - (shipper_age / age_max)).clip(0, 1)

        # PARTY_002: New shipper flag
        self.features['PARTY_002_new_shipper'] = (
            (self.data['shipper_age_months'] < 12).fillna(False).astype(float)
        )

        # PARTY_003: Very new shipper (< 6 months)
        self.features['PARTY_003_very_new_shipper'] = (
            (self.data['shipper_age_months'] < 6).fillna(False).astype(float)
        )

        # PARTY_004: Shipper name opacity
        shipper_opacity = self.data['shipper_name'].fillna('').apply(
            lambda x: 1.0 if len(x) < 5 or 'Unknown' in x or 'N/A' in x else 0.0
        )
        self.features['PARTY_004_shipper_name_opacity'] = shipper_opacity

        # PARTY_005: Generic name indicator
        generic_patterns = ['Corp', 'LLC', 'Ltd', 'Inc', 'Trading', 'Export']
        generic_count = self.data['shipper_name'].fillna('').apply(
            lambda x: sum(1 for p in generic_patterns if p in x) / len(generic_patterns)
        )
        self.features['PARTY_005_generic_shipper_name'] = generic_count

        # PARTY_006: Shipper legitimacy
        legit_countries = {'US', 'CA', 'MX', 'JP', 'DE', 'GB', 'AU', 'SG'}
        shipper_legit = (self.data['shipper_country'].isin(legit_countries)).astype(float)
        self.features['PARTY_006_shipper_legitimacy'] = shipper_legit

        # PARTY_007: Party name consistency
        name_match = (self.data['shipper_name'] == self.data['consignee_name']).astype(float)
        self.features['PARTY_007_shipper_consignee_match'] = name_match

        # PARTY_008: Shipper repeat frequency
        shipper_freq = self.data['shipper_name'].value_counts()
        repeat_freq = self.data['shipper_name'].map(shipper_freq) / len(self.data)
        self.features['PARTY_008_shipper_repeat_frequency'] = repeat_freq.fillna(0)

        # PARTY_009: Party location risk mismatch
        location_mismatch = (
            (self.data['shipper_country'] != self.data['origin_country']).astype(int) +
            (self.data['consignee_country'] != self.data['destination_country']).astype(int)
        )
        self.features['PARTY_009_location_mismatch_score'] = (location_mismatch / 2)

        # PARTY_010: Party obscurity composite
        obscurity = (shipper_opacity + generic_count + (1 - shipper_legit)) / 3
        self.features['PARTY_010_party_obscurity_score'] = obscurity.clip(0, 1)

    def _pattern_risk_features(self):
        """10 PATTERN_RISK features"""

        # PATTERN_001: Value distribution anomaly
        val_med, val_std = self.data['declared_value_usd'].median(), self.data['declared_value_usd'].std()
        val_zscore = np.abs((self.data['declared_value_usd'] - val_med) / (val_std + 1))
        self.features['PATTERN_001_value_anomaly'] = (val_zscore > 3).astype(float)

        # PATTERN_002: Weight distribution anomaly
        wt_med, wt_std = self.data['declared_weight_kg'].median(), self.data['declared_weight_kg'].std()
        wt_zscore = np.abs((self.data['declared_weight_kg'] - wt_med) / (wt_std + 1))
        self.features['PATTERN_002_weight_anomaly'] = (wt_zscore > 3).astype(float)

        # PATTERN_003: Value-weight ratio anomaly
        vw_ratio = self.data['declared_value_usd'] / (self.data['declared_weight_kg'] + 1)
        vw_med, vw_std = vw_ratio.median(), vw_ratio.std()
        vw_zscore = np.abs((vw_ratio - vw_med) / (vw_std + 1))
        self.features['PATTERN_003_vw_ratio_anomaly'] = (vw_zscore > 3).astype(float)

        # PATTERN_004: Dwell anomaly
        dw_med, dw_std = self.data['dwell_days'].median(), self.data['dwell_days'].std()
        dw_zscore = np.abs((self.data['dwell_days'] - dw_med) / (dw_std + 1))
        self.features['PATTERN_004_dwell_anomaly'] = (dw_zscore > 3).astype(float)

        # PATTERN_005: Ensemble anomaly score
        ensemble = np.mean([
            (val_zscore > 3).astype(float),
            (wt_zscore > 3).astype(float),
            (vw_zscore > 3).astype(float),
            (dw_zscore > 3).astype(float)
        ], axis=0)
        self.features['PATTERN_005_ensemble_anomaly'] = ensemble

        # PATTERN_006: Rare shipper-destination combo
        shipper_dest = (
            self.data['shipper_country'].astype(str) + '-' +
            self.data['destination_country'].astype(str)
        )
        sd_freq = shipper_dest.value_counts()
        rare_combo = (sd_freq <= 2).astype(int)
        self.features['PATTERN_006_rare_shipper_dest'] = shipper_dest.map(rare_combo).fillna(0).astype(float)

        # PATTERN_007: Price deviation from corridor average
        corridor = (
            self.data['origin_country'].astype(str) + '->' +
            self.data['destination_country'].astype(str)
        )
        corridor_avg = self.data.groupby(corridor)['declared_value_usd'].transform('mean')
        price_dev = np.abs(self.data['declared_value_usd'] - corridor_avg) / (corridor_avg + 1)
        self.features['PATTERN_007_corridor_price_deviation'] = (price_dev.clip(0, 5) / 5)

        # PATTERN_008: Rare commodity-origin pairing
        commodity_origin = (
            self.data['hs_code'].astype(str) + '-' +
            self.data['origin_country'].astype(str)
        )
        co_freq = commodity_origin.value_counts()
        rare_commodity = (co_freq <= 2).astype(int)
        self.features['PATTERN_008_rare_commodity_origin'] = commodity_origin.map(rare_commodity).fillna(0).astype(float)

        # PATTERN_009: Shipper concentration in shipment
        shipper_commodity = (
            self.data['shipper_name'].astype(str) + '-' +
            self.data['hs_code'].astype(str)
        )
        sc_freq = shipper_commodity.value_counts()
        shipper_conc = self.data['shipper_name'].astype(str).map(
            self.data['shipper_name'].value_counts()
        ) / len(self.data)
        self.features['PATTERN_009_shipper_concentration'] = shipper_conc.fillna(0)

        # PATTERN_010: Multivariate outlierness
        features_std = np.array([
            val_zscore,
            wt_zscore,
            vw_zscore,
            dw_zscore
        ])
        outlier_score = (features_std > 2).sum(axis=0) / 4
        self.features['PATTERN_010_multivariate_outlier_score'] = outlier_score.astype(float)

    def _time_sensitivity_features(self):
        """5 TIME_SENSITIVITY features (adjusted to maintain 72 total)"""

        # TIME_SENSITIVITY_001: Seasonal acceleration
        self.features['TIME_SENSITIVITY_001_seasonal_acceleration'] = (
            (self.data['dwell_days'] < 0.5).astype(float)
        )

        # TIME_SENSITIVITY_002: High-volume shipper period
        shipper_freq = self.data['shipper_name'].value_counts()
        high_vol = (shipper_freq > shipper_freq.median()).astype(int)
        self.features['TIME_SENSITIVITY_002_high_volume_shipper'] = (
            self.data['shipper_name'].map(high_vol).fillna(0).astype(float)
        )

        # TIME_SENSITIVITY_003: Port congestion proxy
        self.features['TIME_SENSITIVITY_003_port_congestion_proxy'] = (
            (self.data['dwell_days'] > self.data['dwell_days'].quantile(0.75)).astype(float)
        )

        # TIME_SENSITIVITY_004: Urgency indicator (short dwell + high value)
        high_val = self.data['declared_value_usd'] > self.data['declared_value_usd'].quantile(0.75)
        short_dwell = self.data['dwell_days'] < self.data['dwell_days'].quantile(0.25)
        self.features['TIME_SENSITIVITY_004_urgency_indicator'] = (
            (high_val & short_dwell).astype(float)
        )

        # TIME_SENSITIVITY_005: Commodity surge detection
        hs_freq = self.data['hs_code'].astype(str).value_counts()
        surge = (hs_freq > hs_freq.quantile(0.85)).astype(int)
        self.features['TIME_SENSITIVITY_005_commodity_surge'] = (
            self.data['hs_code'].astype(str).map(surge).fillna(0).astype(float)
        )

    def validate_features(self, feature_matrix: pd.DataFrame) -> dict:
        """Validate feature matrix"""

        issues = []

        # Shape validation
        if feature_matrix.shape[0] != 10287:
            issues.append(f"Expected 10287 rows, got {feature_matrix.shape[0]}")

        if feature_matrix.shape[1] != 72:
            issues.append(f"Expected 72 columns, got {feature_matrix.shape[1]}")

        # Null values
        null_count = feature_matrix.isna().sum().sum()
        null_pct = (null_count / (feature_matrix.shape[0] * feature_matrix.shape[1])) * 100

        if null_pct > 1.0:
            issues.append(f"Null values: {null_pct:.2f}% (threshold: 1%)")

        # Constant features
        constant_features = []
        for col in feature_matrix.columns:
            if feature_matrix[col].nunique() <= 1:
                constant_features.append(col)

        # Correlation
        corr_matrix = feature_matrix.corr().abs()
        upper_tri = corr_matrix.where(
            np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
        )
        max_corr = upper_tri.max().max()

        if max_corr > 0.95 and not np.isnan(max_corr):
            issues.append(f"High correlation: {max_corr:.4f} (threshold: 0.95)")

        return {
            'null_values_pct': null_pct,
            'max_correlation': max_corr if not np.isnan(max_corr) else 0.0,
            'constant_features': constant_features,
            'issues': issues
        }


def main():
    print("=" * 80)
    print("CBP RISK MODEL - FEATURE ENGINEERING v2 (PHASE 1)")
    print("=" * 80)
    print()

    start_time = time.time()

    # Load
    print("Loading training data...")
    data_path = '/home/rahulvadera/cbp-sentry/data/training_data.csv'
    engineer = FeatureEngineer(data_path)
    print(f"  - Loaded {len(engineer.data)} records")
    print()

    # Engineer
    print("Engineering 72 features across 7 risk factors...")
    feature_matrix = engineer.engineer_features()
    print(f"  - Matrix shape: {feature_matrix.shape}")
    print()

    # Validate
    print("Validating feature matrix...")
    validation = engineer.validate_features(feature_matrix)
    print(f"  - Null values: {validation['null_values_pct']:.2f}%")
    print(f"  - Max correlation: {validation['max_correlation']:.4f}")
    print(f"  - Constant features: {len(validation['constant_features'])}")

    if validation['issues']:
        print(f"  - Issues ({len(validation['issues'])}):")
        for issue in validation['issues']:
            print(f"    * {issue}")
    print()

    # Save
    print("Saving outputs...")
    output_path = '/home/rahulvadera/cbp-sentry/data/feature_matrix_72.csv'
    feature_matrix.to_csv(output_path, index=False)
    print(f"  - Feature matrix: {output_path}")

    feature_defs = {
        "total_features": feature_matrix.shape[1],
        "matrix_shape": list(feature_matrix.shape),
        "generation_timestamp": datetime.now().isoformat(),
        "factors": {
            "DOCUMENTATION_RISK": {
                "weight": 0.25,
                "count": 12,
                "features": [c for c in feature_matrix.columns if c.startswith("DOCUMENTATION")]
            },
            "ROUTING_RISK": {
                "weight": 0.15,
                "count": 10,
                "features": [c for c in feature_matrix.columns if c.startswith("ROUTING")]
            },
            "COMMODITY_RISK": {
                "weight": 0.15,
                "count": 10,
                "features": [c for c in feature_matrix.columns if c.startswith("COMMODITY")]
            },
            "CORRIDOR_RISK": {
                "weight": 0.20,
                "count": 15,
                "features": [c for c in feature_matrix.columns if c.startswith("CORRIDOR")]
            },
            "PARTY_RISK": {
                "weight": 0.15,
                "count": 10,
                "features": [c for c in feature_matrix.columns if c.startswith("PARTY")]
            },
            "PATTERN_RISK": {
                "weight": 0.10,
                "count": 10,
                "features": [c for c in feature_matrix.columns if c.startswith("PATTERN")]
            },
            "TIME_SENSITIVITY": {
                "weight": 0.10,
                "count": 5,
                "features": [c for c in feature_matrix.columns if c.startswith("TIME_SENSITIVITY")]
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
    print(f"  - Feature definitions: {defs_path}")
    print()

    extraction_time = time.time() - start_time

    print("=" * 80)
    print("FEATURE ENGINEERING COMPLETE")
    print("=" * 80)
    print()

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

    print(json.dumps(output_json, indent=2))

    return output_json


if __name__ == '__main__':
    main()
