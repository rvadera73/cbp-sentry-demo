"""
Transshipment Risk Scoring Models - ML-Based Framework
Comprehensive multi-factor weighted model for CBP trade enforcement
"""

from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum

# ============================================================================
# RISK MODEL FACTORS & WEIGHTS
# ============================================================================


@dataclass
class RiskFactor:
    """Individual risk factor configuration"""

    name: str
    description: str
    weight: float  # 0-1 scale (will be normalized to 100%)
    scale: int = 10  # Score scale (typically 0-10)
    thresholds: Dict[str, float] = None  # "LOW", "MEDIUM", "HIGH", "CRITICAL"


class RiskModelConfig:
    """Main Risk Scoring Model Configuration"""

    # ========== FACTOR 1: DOCUMENTATION RISK (25%) ==========
    DOCUMENTATION_RISK = {
        "name": "Origin Documentation Gap",
        "weight": 0.25,
        "description": "ISF filing completeness, Element 9 verification, manifest accuracy",
        "sub_factors": {
            "element_9_mismatch": {
                "name": "Element 9 Origin Mismatch",
                "weight": 0.50,
                "severity_multiplier": 2.5,  # Critical factor
                "description": "Declared origin vs actual origin discrepancy",
            },
            "isf_amendments": {
                "name": "ISF Amendments/Corrections",
                "weight": 0.30,
                "base_score": 2,  # 2 pts per amendment
                "description": "Number of filed amendments post-transmission",
            },
            "manifest_completeness": {
                "name": "Manifest Field Completeness",
                "weight": 0.20,
                "description": "Missing or vague descriptions, inconsistent formatting",
            },
        },
    }

    # ========== FACTOR 2: COMMODITY SENSITIVITY (15%) ==========
    COMMODITY_RISK = {
        "name": "Commodity Sensitivity",
        "weight": 0.15,
        "description": "Product classification, tariff exposure, export control risk",
        "sensitivity_matrix": {
            "semiconductors": {"base_risk": 8.5, "export_control": True, "commodity_code": ["8541", "8542"]},
            "aluminum_extrusions": {
                "base_risk": 7.0,
                "export_control": False,
                "commodity_code": ["7604", "7610"],
                "ad_cvd_rate": 150,
            },
            "solar_equipment": {
                "base_risk": 7.5,
                "export_control": False,
                "commodity_code": ["8501", "8517"],
                "uflpa_risk": True,
            },
            "machinery": {"base_risk": 6.0, "export_control": True, "commodity_code": ["8401-8484"]},
            "chemicals": {"base_risk": 6.5, "export_control": False, "commodity_code": ["2800-2930"]},
            "textiles": {"base_risk": 5.5, "export_control": False, "commodity_code": ["6100-6299"]},
        },
        "sub_factors": {
            "tariff_rate": {
                "name": "Applicable Tariff Rate",
                "weight": 0.50,
                "formula": "min(rate_percent / 500 * 10, 10)",  # Normalize to 0-10
                "description": "Section 301, AD/CVD, USMCA rates - higher rate = stronger evasion incentive",
            },
            "export_control": {
                "name": "Export Control Classification",
                "weight": 0.30,
                "base_score": 9,  # High risk if controlled
                "description": "EAR, ITAR, CCL classification",
            },
            "uflpa_exposure": {
                "name": "UFLPA/Forced Labor Risk",
                "weight": 0.20,
                "risk_countries": ["CN", "MY", "VN"],  # Xinjiang, Malaysia, Vietnam concerns
                "base_score": 8,
                "description": "Goods subject to forced labor presumption",
            },
        },
    }

    # ========== FACTOR 3: ROUTING & LOGISTICS RISK (15%) ==========
    ROUTING_RISK = {
        "name": "Routing Consistency",
        "weight": 0.15,
        "description": "AIS tracking, dwell anomalies, port selection patterns, vessel flags",
        "sub_factors": {
            "ais_dwell_anomaly": {
                "name": "AIS Dwell Time Anomaly",
                "weight": 0.40,
                "baseline_multiplier": 5.0,  # >5x baseline = anomaly
                "points_per_anomaly": 1.0,  # +1 point per baseline multiple
                "description": "Vessel idle time inconsistent with typical transshipment route",
            },
            "port_selection": {
                "name": "Transshipment Hub Selection",
                "weight": 0.30,
                "known_hubs": ["SG", "HK", "LA", "PA"],  # Singapore, Hong Kong, LA, Panama
                "base_score": 6,
                "description": "Use of known transshipment centers vs direct routing",
            },
            "vessel_flag_risk": {
                "name": "Vessel Flag of Convenience",
                "weight": 0.20,
                "high_risk_flags": ["PA", "KH", "MH", "MM"],  # Panama, Cambodia, Marshall Is, Myanmar
                "base_score": 7,
                "description": "Vessel registered to high-risk flag state",
            },
            "routing_consistency": {
                "name": "Route Fidelity vs Manifest",
                "weight": 0.10,
                "description": "AIS track matches declared port calls",
            },
        },
    }

    # ========== FACTOR 4: PARTY PROFILE RISK (15%) ==========
    PARTY_RISK = {
        "name": "Party Profile Risk",
        "weight": 0.15,
        "description": "Shipper/importer establishment, compliance history, beneficial ownership",
        "sub_factors": {
            "shipper_age": {
                "name": "Shipper Age & Establishment",
                "weight": 0.35,
                "thresholds": {
                    "new": {"months": (0, 12), "score": 9},
                    "emerging": {"months": (12, 36), "score": 6.5},
                    "established": {"months": (36, 10000), "score": 3},
                },
                "description": "Company age: <1yr=HIGH, 1-3yr=MED, >3yr=LOW risk",
            },
            "prior_violations": {
                "name": "Compliance History",
                "weight": 0.30,
                "formula": "violations_count * 2.5",  # Points per violation
                "max_score": 10,
                "description": "Prior CBP violations, detentions, or penalties",
            },
            "ofac_sanctions": {
                "name": "OFAC/Sanctions Exposure",
                "weight": 0.20,
                "blocked_list": 9.5,
                "watch_list": 7.0,
                "description": "Entity on OFAC SDN, Entity List, or Watch List",
            },
            "beneficial_ownership": {
                "name": "Corporate Structure Opacity",
                "weight": 0.15,
                "hidden_ownership_score": 8,
                "shell_company_score": 9,
                "description": "Difficulty verifying true beneficial owner",
            },
        },
    }

    # ========== FACTOR 5: COUNTRY-OF-ORIGIN CORRIDOR RISK (20%) ==========
    CORRIDOR_RISK = {
        "name": "Country-of-Origin Risk & Corridor",
        "weight": 0.20,
        "description": "Baseline risk by country pair, tariff evasion incentive, export control restrictions",
        "corridors": {
            "CN→US": {
                "name": "China to United States",
                "baseline_risk": 8.5,
                "risk_profile": "ORIGIN_CONCEALMENT",
                "tariff_rate": 25,  # Section 301
                "export_control": True,  # EAR/ITAR
                "uflpa_exposure": False,
                "primary_concern": "Origin concealment, IP theft, forced labor (Xinjiang)",
                "multiplier": 1.3,
            },
            "VN→US": {
                "name": "Vietnam to United States",
                "baseline_risk": 7.0,
                "risk_profile": "TARIFF_EVASION",
                "tariff_rate": 150,  # AD/CVD on aluminum
                "export_control": False,
                "uflpa_exposure": True,
                "primary_concern": "Aluminum tariff evasion, origin misrepresentation",
                "multiplier": 1.15,
            },
            "MY→US": {
                "name": "Malaysia to United States",
                "baseline_risk": 6.5,
                "risk_profile": "FORCED_LABOR",
                "tariff_rate": 40,  # Anti-dumping solar
                "export_control": False,
                "uflpa_exposure": True,
                "primary_concern": "Forced labor (semiconductors, solar), UFLPA enforcement",
                "multiplier": 1.10,
            },
            "CA→US": {
                "name": "Canada to United States",
                "baseline_risk": 4.5,
                "risk_profile": "EXPORT_CONTROL",
                "tariff_rate": 0,  # USMCA - no tariffs
                "export_control": True,
                "uflpa_exposure": False,
                "primary_concern": "Semiconductor export controls, hidden Chinese ownership",
                "multiplier": 0.95,
            },
            "SG→US": {
                "name": "Singapore to United States",
                "baseline_risk": 5.0,
                "risk_profile": "TRANSSHIPMENT_HUB",
                "tariff_rate": 0,
                "export_control": False,
                "uflpa_exposure": False,
                "primary_concern": "Known transshipment center for origin concealment",
                "multiplier": 1.08,
            },
        },
        "tariff_evasion_incentive": {
            "formula": "min(tariff_rate / 25 * 5, 5)",  # Max +5 pts
            "description": "Higher tariff differential = stronger incentive to evade",
        },
    }

    # ========== FACTOR 6: PATTERN ANOMALY RISK (10%) ==========
    PATTERN_RISK = {
        "name": "Historical Pattern Anomaly",
        "weight": 0.10,
        "description": "Price vs benchmark, weight anomalies, frequency changes, new patterns",
        "sub_factors": {
            "pricing_anomaly": {
                "name": "Unit Price vs Benchmark",
                "weight": 0.50,
                "thresholds": {
                    "severe_underpricing": {"variance": (-100, -50), "score": 9},  # >50% below
                    "high_underpricing": {"variance": (-50, -20), "score": 6.5},  # 20-50% below
                    "normal": {"variance": (-20, 20), "score": 2},  # ±20%
                    "overpricing": {"variance": (20, 100), "score": 4},  # >20% above
                },
                "description": "Declared value significantly below industry benchmark",
            },
            "weight_anomaly": {
                "name": "Weight vs Typical Shipments",
                "weight": 0.25,
                "description": "Unusually light/heavy for commodity and container type",
            },
            "trade_frequency": {
                "name": "New/Changed Trade Patterns",
                "weight": 0.25,
                "new_shipper_score": 6,
                "frequency_change_score": 5,
                "description": "First shipment from shipper or sudden volume increase",
            },
        },
    }

    # ========== TIME SENSITIVITY (10%) ==========
    TIME_SENSITIVITY = {
        "name": "Time Sensitivity",
        "weight": 0.10,
        "description": "Urgency indicators, seasonal patterns, seasonal tariff changes",
        "sub_factors": {
            "pre_tariff_timing": {
                "name": "Timing Before Tariff/Rule Change",
                "weight": 0.50,
                "days_before_cutoff": (0, 30),  # Shipments within 30 days of rule change
                "base_score": 7,
                "description": "Timing coincides with upcoming tariff increase or enforcement action",
            },
            "seasonal_anomaly": {
                "name": "Seasonal Pattern Deviation",
                "weight": 0.50,
                "description": "Shipping outside typical season for commodity",
            },
        },
    }

    @classmethod
    def get_all_factors(cls) -> Dict[str, Dict]:
        """Return all configured factors with normalized weights"""
        return {
            "documentation": cls.DOCUMENTATION_RISK,
            "commodity": cls.COMMODITY_RISK,
            "routing": cls.ROUTING_RISK,
            "party": cls.PARTY_RISK,
            "corridor": cls.CORRIDOR_RISK,
            "pattern": cls.PATTERN_RISK,
            "time": cls.TIME_SENSITIVITY,
        }

    @classmethod
    def get_factor_weights(cls) -> Dict[str, float]:
        """Get normalized factor weights (sum to 100%)"""
        factors = cls.get_all_factors()
        weights = {name: factor["weight"] for name, factor in factors.items()}
        total = sum(weights.values())
        return {name: (weight / total * 100) for name, weight in weights.items()}


# ============================================================================
# RISK SCORING BREAKDOWN STRUCTURE
# ============================================================================


@dataclass
class RiskComponentScore:
    """Individual component score with details"""

    component: str  # e.g., "Element 9 Mismatch"
    factor: str  # e.g., "Documentation"
    score: float  # 0-10
    weight: float  # Percentage (0-100)
    weighted_result: float  # score * weight / 10
    rationale: str  # Why this score
    evidence: List[str] = None  # Supporting evidence

    def to_dict(self) -> Dict:
        return {
            "component": self.component,
            "factor": self.factor,
            "score": round(self.score, 1),
            "weight": round(self.weight, 1),
            "weighted_result": round(self.weighted_result, 1),
            "rationale": self.rationale,
            "evidence": self.evidence or [],
        }


@dataclass
class RiskScoreBreakdown:
    """Complete risk score breakdown for referral package"""

    shipment_id: str
    components: List[RiskComponentScore]  # Individual factors
    subtotal: float  # Sum of weighted components (pre-adjustment)

    # Country-of-Origin Risk Model adjustment
    corridor_risk_adjustment: Dict[str, Any] = None  # Baseline, multiplier, adjustment points
    additional_adjustments: List[Dict[str, Any]] = None  # Other adjustments (AIS dwell, etc)

    final_score: float = 0.0  # Final composite score (0-100)
    confidence_interval: str = ""  # e.g., "85.0±2.5"
    calculation_table: Dict[str, Any] = None  # Detailed calculation breakdown for transparency

    def to_dict(self) -> Dict:
        return {
            "shipment_id": self.shipment_id,
            "components": [c.to_dict() for c in self.components],
            "subtotal": round(self.subtotal, 1),
            "corridor_risk_adjustment": self.corridor_risk_adjustment,
            "additional_adjustments": self.additional_adjustments,
            "final_score": round(self.final_score, 1),
            "confidence_interval": self.confidence_interval,
            "calculation_table": self.calculation_table,
        }
