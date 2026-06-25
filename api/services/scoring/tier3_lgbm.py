"""
Tier 3 Scorer: LightGBM Supervised Classification
Input: Manifest data (HTS, shipper_age, price, country_of_origin, etc.)
Output: Commodity Sensitivity + Historical Pattern Anomaly (0-30 pts, split 15/15)

Logic:
- Commodity Sensitivity: HTS duty rate, AD/CVD status (0-15)
- Historical Pattern: Origin shifts, timing, shipper age (0-15)
"""

import importlib.util
import sys
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

try:
    from services.api.risk_models import COUNTRY_ENCODING
except ImportError:
    risk_models_path = Path(__file__).resolve().parents[3] / "services" / "api" / "risk_models.py"
    spec = importlib.util.spec_from_file_location("cbp_sentry_risk_models", risk_models_path)
    risk_models = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = risk_models
    spec.loader.exec_module(risk_models)
    COUNTRY_ENCODING = risk_models.COUNTRY_ENCODING


class Tier3Scorer:
    """Score based on commodity characteristics and historical patterns"""

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize Tier 3 scorer.

        Args:
            model_path: Path to pre-trained lgbm_classifier.txt (optional for testing)
        """
        self.model_path = model_path
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load pre-trained LightGBM model"""
        if self.model_path:
            try:
                import lightgbm as lgb
                self.model = lgb.Booster(model_file=self.model_path)
            except Exception:
                # Model not available, use synthetic scoring for testing
                self.model = None
        else:
            self.model = None

    def score_commodity_sensitivity(self, manifest: Dict[str, Any]) -> float:
        """
        Score commodity sensitivity to duty evasion (0-15).

        Factors:
        - HTS duty rate (higher = more incentive to evade)
        - AD/CVD status (ACTIVE = high risk)
        - Commodity type (aluminum = high risk)

        Args:
            manifest: Dict with HTS, duty rate, AD/CVD status

        Returns:
            float: Score 0-15
        """
        hts_code = manifest.get("hts_code", "")
        duty_rate = manifest.get("hts_duty_rate_pct", 0)
        ad_cvd_status = manifest.get("ad_cvd_status", "INACTIVE")

        # Base score from duty rate
        # 0-15% duty = 0-2 points
        # 15-50% duty = 2-6 points
        # 50-100% duty = 6-10 points
        # 100%+ duty = 10-14 points (capped lower)
        if duty_rate < 15:
            commodity_score = 2
        elif duty_rate < 50:
            commodity_score = 6
        elif duty_rate < 100:
            commodity_score = 10
        else:
            # Greenfield: 374% duty → max 13 points before other factors
            commodity_score = min(10 + (duty_rate / 150), 13)

        # Boost for AD/CVD active
        if ad_cvd_status == "ACTIVE":
            commodity_score += 1

        # Boost for aluminum (HTS 7604) or other high-risk commodities
        if hts_code.startswith("7604"):
            commodity_score = min(commodity_score + 0.5, 14)

        return round(commodity_score, 1)

    def score_historical_pattern(self, manifest: Dict[str, Any], evidence: Optional[List[str]] = None) -> float:
        """
        Score historical pattern anomalies (0-15).

        Factors:
        - Origin shifts over 6 months (VN→TH→VN = high risk)
        - Shipper age (newer = higher suspicion)
        - Price variance from market (below market = underinvoicing)
        - Known evasion corridors (VN→US aluminum = CRITICAL_STRUCTURAL_RISK)

        Args:
            manifest: Dict with prior_origins_6m, shipper age, price variance

        Returns:
            float: Score 0-15
        """
        prior_origins = manifest.get("prior_origins_6m", [])
        shipper_incorporation_date = manifest.get("shipper_incorporation_date", "")
        price_variance = manifest.get("price_variance_pct", 0)
        hts_code = manifest.get("hts_code", "")
        country_of_origin = manifest.get("country_of_origin", "")

        pattern_score = 0.0
        evidence = evidence if evidence is not None else []

        # Origin shift detection
        # Single origin (same 6m) = 0 points
        # 2-3 different origins = 10 points (transshipment pathway)
        # 3+ origins with multiple shifts = 12 points
        if prior_origins and len(prior_origins) > 1:
            unique_origins = len(set(prior_origins))
            if unique_origins >= 3:
                # 3 or more unique origins = high transshipment signal
                pattern_score += 12
                evidence.append(f"{unique_origins} prior origins over 6 months: +12")
            elif unique_origins >= 2:
                # 2 unique origins = moderate transshipment signal
                pattern_score += 10
                evidence.append(f"{unique_origins} prior origins over 6 months: +10")

        # Shipper age penalty (newer = suspicious)
        if shipper_incorporation_date:
            try:
                incorp_date = datetime.fromisoformat(shipper_incorporation_date.replace('Z', '+00:00'))
                now = datetime.now(incorp_date.tzinfo) if incorp_date.tzinfo else datetime.utcnow()
                age_months = (now - incorp_date).days / 30
                if age_months < 6:
                    pattern_score += 3
                    evidence.append(f"Very new shipper ({age_months:.0f} months): +3")
                elif age_months < 12:
                    pattern_score += 2
                    evidence.append(f"New shipper ({age_months:.0f} months): +2")
            except Exception:
                pass

        # Price variance penalty
        if price_variance < -15:  # Greenfield: -18.7%
            penalty = min(3.0, abs(price_variance) / 15)
            pattern_score += penalty
            evidence.append(f"Price {price_variance:.1f}% below market: +{penalty:.1f}")

        # Known evasion corridor
        if hts_code.startswith("7604") and country_of_origin.upper() == "VN":
            # Aluminum from Vietnam is CRITICAL_STRUCTURAL_RISK
            pattern_score += 2
            evidence.append("VN aluminum evasion corridor (7604): +2")

        return round(min(pattern_score, 15), 1)

    def score(self, manifest: Dict[str, Any]) -> tuple:
        """
        Calculate Commodity Sensitivity + Historical Pattern (0-30 pts total).

        Uses trained LightGBM model if available, otherwise falls back
        to deterministic scoring for testing.

        Returns:
            tuple: (commodity_score, historical_score) where each is 0-15
        """
        # If real model is loaded, use it for pattern detection
        if self.model is not None:
            try:
                # Prepare feature vector matching training:
                # [hts_6digit, country_origin_encoded, shipper_age_months, ad_duty_rate,
                #  er_confidence, ais_anomaly_score, isf_stuffing_country, price_market_ratio]

                hts_code = manifest.get("hts_code", "")
                hts_6digit = int(hts_code[:6].replace(".", "")) if hts_code else 0

                country_of_origin = manifest.get("country_of_origin", "")
                country_encoded = COUNTRY_ENCODING.get(country_of_origin.upper(), 0)

                shipper_date = manifest.get("shipper_incorporation_date", "")
                try:
                    incorp_date = datetime.fromisoformat(shipper_date.replace('Z', '+00:00'))
                    now = datetime.now(incorp_date.tzinfo) if incorp_date.tzinfo else datetime.utcnow()
                    shipper_age_months = (now - incorp_date).days / 30
                except Exception:
                    shipper_age_months = 24

                ad_duty_rate = manifest.get("hts_duty_rate_pct", 0)
                er_confidence = manifest.get("er_shipper_confidence", 0.85)
                ais_anomaly_score = manifest.get("ais_anomaly_score", 0.0)
                isf_stuffing = 0 if manifest.get("isf_stuffing_country") == country_of_origin else 1
                price_declared = manifest.get("price_declared_per_unit", 1.0)
                market_price = manifest.get("market_price_per_unit", 1.0)
                price_market_ratio = price_declared / market_price if market_price > 0 else 1.0

                import numpy as np
                features = np.array([[
                    hts_6digit,
                    country_encoded,
                    shipper_age_months,
                    ad_duty_rate,
                    er_confidence,
                    ais_anomaly_score,
                    isf_stuffing,
                    price_market_ratio
                ]])

                # Get prediction probability
                pred_proba = self.model.predict(features)[0]

                # pred_proba is the probability of transshipment (0-1)
                # Use it to score both commodity and pattern dimensions
                # Commodity driven by duty rate, pattern driven by LightGBM transshipment score

                # Commodity: use duty rate + AD/CVD status
                commodity_score = self.score_commodity_sensitivity(manifest)

                # Pattern: use LightGBM prediction + origin shift
                historical_base = self.score_historical_pattern(manifest)
                # Blend with LightGBM score (increase pattern score if model detects transshipment)
                pattern_lgbm_boost = pred_proba * 10  # 0-10 point boost
                pattern_score = min(15, historical_base + pattern_lgbm_boost)

                return round(commodity_score, 1), round(pattern_score, 1)
            except Exception:
                # Fall back to deterministic scoring if model inference fails
                pass

        # Fallback: deterministic scoring (for testing without trained model)
        commodity_score = self.score_commodity_sensitivity(manifest)
        historical_score = self.score_historical_pattern(manifest)
        return commodity_score, historical_score
