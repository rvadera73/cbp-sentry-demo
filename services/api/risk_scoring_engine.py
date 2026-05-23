"""
ML-Based Risk Scoring Engine
Calculates comprehensive transshipment risk scores with detailed breakdowns
"""
import math
from typing import Dict, List, Any, Tuple
from risk_models import RiskModelConfig, RiskComponentScore, RiskScoreBreakdown


class RiskScoringEngine:
    """
    Transshipment Risk Scoring Engine
    Implements multi-factor weighted model with configurable factors
    """

    def __init__(self):
        self.config = RiskModelConfig()
        self.factor_weights = self.config.get_factor_weights()

    def score_shipment(self, shipment: Dict[str, Any]) -> RiskScoreBreakdown:
        """
        Calculate comprehensive risk score for a shipment

        Args:
            shipment: Shipment data with all fields

        Returns:
            RiskScoreBreakdown with detailed component scores
        """
        components: List[RiskComponentScore] = []

        # 1. DOCUMENTATION RISK
        doc_components = self._score_documentation_risk(shipment)
        components.extend(doc_components)

        # 2. COMMODITY RISK
        commodity_components = self._score_commodity_risk(shipment)
        components.extend(commodity_components)

        # 3. ROUTING RISK
        routing_components = self._score_routing_risk(shipment)
        components.extend(routing_components)

        # 4. PARTY RISK
        party_components = self._score_party_risk(shipment)
        components.extend(party_components)

        # 5. CORRIDOR RISK (baseline)
        corridor_components = self._score_corridor_risk(shipment)
        components.extend(corridor_components)

        # 6. PATTERN ANOMALY RISK
        pattern_components = self._score_pattern_risk(shipment)
        components.extend(pattern_components)

        # 7. TIME SENSITIVITY
        time_components = self._score_time_sensitivity(shipment)
        components.extend(time_components)

        # Calculate subtotal (sum of weighted components)
        subtotal = sum(c.weighted_result for c in components)

        # Calculate adjustments
        corridor_adjustment = self._calculate_corridor_adjustment(shipment, components)
        additional_adjustments = self._calculate_additional_adjustments(shipment)

        # Final score calculation
        final_score = subtotal
        if corridor_adjustment:
            final_score += corridor_adjustment['adjustment_points']
        for adj in (additional_adjustments or []):
            final_score += adj['adjustment_points']

        # Cap at 100
        final_score = min(final_score, 100.0)

        # Calculate confidence interval (±uncertainty)
        confidence = self._calculate_confidence_interval(components)

        breakdown = RiskScoreBreakdown(
            shipment_id=shipment.get('id', 'UNKNOWN'),
            components=components,
            subtotal=subtotal,
            corridor_risk_adjustment=corridor_adjustment,
            additional_adjustments=additional_adjustments,
            final_score=final_score,
            confidence_interval=confidence
        )

        return breakdown

    # ========== FACTOR SCORING METHODS ==========

    def _score_documentation_risk(self, shipment: Dict) -> List[RiskComponentScore]:
        """Score documentation risk factors"""
        components = []
        config = self.config.DOCUMENTATION_RISK
        factor_weight = self.factor_weights['documentation']

        # Element 9 Mismatch (50% of documentation risk)
        element9_mismatch = shipment.get('element9_is_mismatch', False)
        element9_score = 9.5 if element9_mismatch else 2.0
        components.append(RiskComponentScore(
            component='Element 9 Origin Mismatch',
            factor='Documentation',
            score=element9_score,
            weight=factor_weight * 0.50,
            weighted_result=(element9_score * factor_weight * 0.50) / 10,
            rationale='Declared origin differs from actual origin - critical fraud indicator',
            evidence=['element9_declared: ' + str(shipment.get('element9_declared_country')),
                     'element9_actual: ' + str(shipment.get('element9_actual_country'))]
        ))

        # ISF Amendments (30% of documentation risk)
        isf_amendments = shipment.get('isf_amendments', 0)
        isf_score = min(2.0 + (isf_amendments * 2.5), 10.0)
        components.append(RiskComponentScore(
            component='ISF Amendments/Corrections',
            factor='Documentation',
            score=isf_score,
            weight=factor_weight * 0.30,
            weighted_result=(isf_score * factor_weight * 0.30) / 10,
            rationale=f'{isf_amendments} amendments filed post-transmission',
            evidence=[f'Amendments: {isf_amendments}', 'Indicates correction of initial errors or concealment']
        ))

        # Manifest Completeness (20% of documentation risk)
        manifest_score = self._assess_manifest_completeness(shipment)
        components.append(RiskComponentScore(
            component='Manifest Field Completeness',
            factor='Documentation',
            score=manifest_score,
            weight=factor_weight * 0.20,
            weighted_result=(manifest_score * factor_weight * 0.20) / 10,
            rationale='Manifest descriptions and formatting consistency',
            evidence=['Completeness check: ' + str(manifest_score)]
        ))

        return components

    def _score_commodity_risk(self, shipment: Dict) -> List[RiskComponentScore]:
        """Score commodity sensitivity factors"""
        components = []
        config = self.config.COMMODITY_RISK
        factor_weight = self.factor_weights['commodity']

        commodity_code = shipment.get('commodity_code', '9999')[:4]
        commodity_name = shipment.get('commodity_name', 'General')

        # Find sensitivity level
        sensitivity = config['sensitivity_matrix'].get(
            commodity_name.lower(),
            {'base_risk': 5.0, 'export_control': False, 'ad_cvd_rate': 0}
        )

        # Tariff Rate Risk (50% of commodity risk)
        tariff_rate = sensitivity.get('ad_cvd_rate', 0)
        tariff_score = min(tariff_rate / 500 * 10, 10.0)
        components.append(RiskComponentScore(
            component='Tariff Rate / AD-CVD Exposure',
            factor='Commodity',
            score=tariff_score,
            weight=factor_weight * 0.50,
            weighted_result=(tariff_score * factor_weight * 0.50) / 10,
            rationale=f'HS {commodity_code}: {tariff_rate}% tariff rate = {tariff_rate}% evasion incentive',
            evidence=[f'Commodity: {commodity_name}', f'HS Code: {commodity_code}', f'AD/CVD Rate: {tariff_rate}%']
        ))

        # Export Control (30% of commodity risk)
        export_control_score = 9.0 if sensitivity.get('export_control', False) else 2.0
        components.append(RiskComponentScore(
            component='Export Control Classification',
            factor='Commodity',
            score=export_control_score,
            weight=factor_weight * 0.30,
            weighted_result=(export_control_score * factor_weight * 0.30) / 10,
            rationale='Commodity subject to EAR/ITAR export controls' if sensitivity.get('export_control') else 'No export control classification',
            evidence=['Export Controlled' if sensitivity.get('export_control') else 'Not Controlled']
        ))

        # UFLPA Risk (20% of commodity risk)
        uflpa_score = 8.0 if sensitivity.get('uflpa_exposure', False) else 3.0
        components.append(RiskComponentScore(
            component='UFLPA Forced Labor Risk',
            factor='Commodity',
            score=uflpa_score,
            weight=factor_weight * 0.20,
            weighted_result=(uflpa_score * factor_weight * 0.20) / 10,
            rationale='Goods subject to forced labor presumption or enforcement risk',
            evidence=['UFLPA Exposure' if sensitivity.get('uflpa_exposure') else 'No UFLPA Exposure']
        ))

        return components

    def _score_routing_risk(self, shipment: Dict) -> List[RiskComponentScore]:
        """Score routing and logistics risk factors"""
        components = []
        config = self.config.ROUTING_RISK
        factor_weight = self.factor_weights['routing']

        # AIS Dwell Anomaly (40% of routing risk)
        dwell_anomaly = 'DWELL_ANOMALY' in (shipment.get('h2_signals', []) or [])
        dwell_score = 8.5 if dwell_anomaly else 3.0
        components.append(RiskComponentScore(
            component='AIS Dwell Time Anomaly',
            factor='Routing',
            score=dwell_score,
            weight=factor_weight * 0.40,
            weighted_result=(dwell_score * factor_weight * 0.40) / 10,
            rationale='Vessel idle time >5x baseline = potential transshipment/concealment',
            evidence=['DWELL_ANOMALY detected' if dwell_anomaly else 'Normal dwell time']
        ))

        # Port Selection (30% of routing risk)
        port_calls = shipment.get('port_calls', []) or []
        hub_risk = any(hub in str(port_calls) for hub in ['SG', 'HK', 'LA', 'PA'])
        port_score = 6.5 if hub_risk else 3.0
        components.append(RiskComponentScore(
            component='Transshipment Hub Selection',
            factor='Routing',
            score=port_score,
            weight=factor_weight * 0.30,
            weighted_result=(port_score * factor_weight * 0.30) / 10,
            rationale='Route includes known transshipment centers (Singapore, Hong Kong, LA, Panama)',
            evidence=['Port Calls: ' + str(port_calls)]
        ))

        # Vessel Flag Risk (20% of routing risk)
        vessel_imo = shipment.get('vessel_imo', '')
        # Flag derived from IMO (simplified - in production would query IMO registry)
        flag_score = 6.0  # Default medium risk
        components.append(RiskComponentScore(
            component='Vessel Flag of Convenience',
            factor='Routing',
            score=flag_score,
            weight=factor_weight * 0.20,
            weighted_result=(flag_score * factor_weight * 0.20) / 10,
            rationale='Vessel flag state risk classification',
            evidence=['Vessel: ' + str(shipment.get('vessel_name', 'Unknown'))]
        ))

        # Routing Consistency (10% of routing risk) - covered by above
        return components

    def _score_party_risk(self, shipment: Dict) -> List[RiskComponentScore]:
        """Score party (shipper/importer) risk factors"""
        components = []
        config = self.config.PARTY_RISK
        factor_weight = self.factor_weights['party']

        # Shipper Age (35% of party risk)
        shipper_age_months = shipment.get('shipper_age_months', 0)
        if shipper_age_months < 12:
            age_score = 9.0
            age_category = 'NEW'
        elif shipper_age_months < 36:
            age_score = 6.5
            age_category = 'EMERGING'
        else:
            age_score = 3.0
            age_category = 'ESTABLISHED'

        components.append(RiskComponentScore(
            component='Shipper Age & Establishment',
            factor='Party',
            score=age_score,
            weight=factor_weight * 0.35,
            weighted_result=(age_score * factor_weight * 0.35) / 10,
            rationale=f'Shipper age: {shipper_age_months} months ({age_category})',
            evidence=[f'Age: {shipper_age_months} months']
        ))

        # Prior Violations (30% of party risk)
        prior_violations = shipment.get('prior_violations', 0)
        violation_score = min(prior_violations * 2.5, 10.0)
        components.append(RiskComponentScore(
            component='Compliance History',
            factor='Party',
            score=violation_score,
            weight=factor_weight * 0.30,
            weighted_result=(violation_score * factor_weight * 0.30) / 10,
            rationale=f'{prior_violations} prior CBP violations or detentions',
            evidence=[f'Violations: {prior_violations}']
        ))

        # OFAC/Sanctions (20% of party risk)
        ofac_status = shipment.get('ofac_status', 'CLEAR')
        if ofac_status == 'BLOCKED':
            ofac_score = 9.5
        elif ofac_status == 'WATCH':
            ofac_score = 7.0
        else:
            ofac_score = 1.5
        components.append(RiskComponentScore(
            component='OFAC/Sanctions Exposure',
            factor='Party',
            score=ofac_score,
            weight=factor_weight * 0.20,
            weighted_result=(ofac_score * factor_weight * 0.20) / 10,
            rationale=f'OFAC Status: {ofac_status}',
            evidence=[f'Status: {ofac_status}']
        ))

        # Beneficial Ownership (15% of party risk)
        ownership_opacity = shipment.get('ownership_opacity', False)
        ownership_score = 8.0 if ownership_opacity else 2.0
        components.append(RiskComponentScore(
            component='Corporate Structure Opacity',
            factor='Party',
            score=ownership_score,
            weight=factor_weight * 0.15,
            weighted_result=(ownership_score * factor_weight * 0.15) / 10,
            rationale='Difficulty verifying beneficial owner',
            evidence=['Hidden ownership' if ownership_opacity else 'Clear ownership']
        ))

        return components

    def _score_corridor_risk(self, shipment: Dict) -> List[RiskComponentScore]:
        """Score corridor and origin risk factors"""
        components = []
        config = self.config.CORRIDOR_RISK
        factor_weight = self.factor_weights['corridor']

        origin = shipment.get('origin_country', 'XX')[:2].upper()
        dest = shipment.get('destination_country', 'XX')[:2].upper()
        corridor_key = f'{origin}→{dest}'

        corridor_data = config['corridors'].get(corridor_key, {
            'baseline_risk': 5.0,
            'tariff_rate': 0,
            'export_control': False,
            'multiplier': 1.0
        })

        baseline_score = corridor_data['baseline_risk']
        tariff_points = min(corridor_data['tariff_rate'] / 25 * 5, 5.0)

        components.append(RiskComponentScore(
            component='Country-of-Origin Risk',
            factor='Corridor',
            score=baseline_score,
            weight=factor_weight * 0.60,
            weighted_result=(baseline_score * factor_weight * 0.60) / 10,
            rationale=f'Corridor {corridor_key}: {corridor_data.get("primary_concern", "Unknown")}',
            evidence=[
                f'Route: {corridor_key}',
                f'Risk Profile: {corridor_data.get("risk_profile", "Unknown")}',
                f'Tariff Rate: {corridor_data["tariff_rate"]}%'
            ]
        ))

        components.append(RiskComponentScore(
            component='Tariff Evasion Incentive',
            factor='Corridor',
            score=tariff_points,
            weight=factor_weight * 0.40,
            weighted_result=(tariff_points * factor_weight * 0.40) / 10,
            rationale=f'Tariff differential = {tariff_points:.1f} incentive points',
            evidence=[f'Tariff Rate: {corridor_data["tariff_rate"]}%']
        ))

        return components

    def _score_pattern_risk(self, shipment: Dict) -> List[RiskComponentScore]:
        """Score historical pattern anomalies"""
        components = []
        config = self.config.PATTERN_RISK
        factor_weight = self.factor_weights['pattern']

        # Pricing Anomaly (50% of pattern risk)
        price_variance = shipment.get('price_variance_percent', 0)
        if price_variance < -50:
            pricing_score = 9.0
            pricing_cat = 'SEVERE'
        elif price_variance < -20:
            pricing_score = 6.5
            pricing_cat = 'HIGH'
        elif price_variance > 20:
            pricing_score = 4.0
            pricing_cat = 'PREMIUM'
        else:
            pricing_score = 2.0
            pricing_cat = 'NORMAL'

        components.append(RiskComponentScore(
            component='Unit Price vs Benchmark',
            factor='Pattern',
            score=pricing_score,
            weight=factor_weight * 0.50,
            weighted_result=(pricing_score * factor_weight * 0.50) / 10,
            rationale=f'Price variance: {price_variance:.1f}% ({pricing_cat})',
            evidence=[f'Variance: {price_variance:.1f}%', f'Unit Price: ${shipment.get("unit_price_per_kg", 0):.2f}/kg']
        ))

        # Trade Pattern Changes (50% of pattern risk)
        new_shipper = shipment.get('new_shipper', False)
        pattern_score = 6.0 if new_shipper else 3.0
        components.append(RiskComponentScore(
            component='New/Changed Trade Patterns',
            factor='Pattern',
            score=pattern_score,
            weight=factor_weight * 0.50,
            weighted_result=(pattern_score * factor_weight * 0.50) / 10,
            rationale='New shipper or unusual frequency changes',
            evidence=['New Shipper' if new_shipper else 'Established Pattern']
        ))

        return components

    def _score_time_sensitivity(self, shipment: Dict) -> List[RiskComponentScore]:
        """Score time sensitivity factors"""
        components = []
        config = self.config.TIME_SENSITIVITY
        factor_weight = self.factor_weights['time']

        # Simplified time sensitivity (would integrate with actual tariff calendars in production)
        time_score = 3.0  # Default low risk
        components.append(RiskComponentScore(
            component='Time Sensitivity Indicators',
            factor='Time',
            score=time_score,
            weight=factor_weight,
            weighted_result=(time_score * factor_weight) / 10,
            rationale='Timing relative to tariff changes and enforcement actions',
            evidence=['Filing Date: ' + str(shipment.get('created_at', 'Unknown'))]
        ))

        return components

    # ========== HELPER METHODS ==========

    def _assess_manifest_completeness(self, shipment: Dict) -> float:
        """Assess manifest field completeness (0-10 scale)"""
        required_fields = [
            'shipper_name', 'consignee_name', 'commodity_name',
            'commodity_code', 'declared_weight_kg', 'declared_value'
        ]
        completeness = sum(1 for field in required_fields if shipment.get(field)) / len(required_fields)
        # Score: 10 = complete, 2 = incomplete
        return 2.0 + (completeness * 8.0)

    def _calculate_corridor_adjustment(self, shipment: Dict, components: List[RiskComponentScore]) -> Dict:
        """Calculate Country-of-Origin Risk adjustment"""
        origin = shipment.get('origin_country', 'XX')[:2].upper()
        dest = shipment.get('destination_country', 'XX')[:2].upper()
        corridor_key = f'{origin}→{dest}'

        corridor_data = self.config.CORRIDOR_RISK['corridors'].get(corridor_key)
        if not corridor_data:
            return None

        baseline = corridor_data['baseline_risk']
        multiplier = corridor_data.get('multiplier', 1.0)

        # Find corridor risk component
        corridor_component = next((c for c in components if c.component == 'Country-of-Origin Risk'), None)
        if not corridor_component:
            return None

        adjustment_points = corridor_component.score * (multiplier - 1.0)

        return {
            'corridor': corridor_key,
            'baseline_risk': baseline,
            'multiplier': multiplier,
            'adjustment_points': adjustment_points,
            'reason': f'Country pair risk adjustment for {corridor_key}'
        }

    def _calculate_additional_adjustments(self, shipment: Dict) -> List[Dict]:
        """Calculate additional adjustments (AIS dwell, etc)"""
        adjustments = []

        # AIS dwell anomaly adjustment
        if 'DWELL_ANOMALY' in (shipment.get('h2_signals', []) or []):
            dwell_points = min(shipment.get('dwell_anomaly_multiplier', 3) * 4, 16)
            adjustments.append({
                'type': 'AIS Dwell Time Corroboration',
                'adjustment_points': dwell_points,
                'reason': f'AIS idle time {shipment.get("dwell_anomaly_multiplier", 3):.1f}x baseline'
            })

        return adjustments if adjustments else None

    def _calculate_confidence_interval(self, components: List[RiskComponentScore]) -> str:
        """Calculate confidence interval for score"""
        # Simplified: ±2.5 for high confidence, ±5 for lower
        uncertainty = 2.5 if len(components) >= 15 else 5.0
        return f"±{uncertainty:.1f}"
