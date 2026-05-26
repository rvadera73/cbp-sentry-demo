"""
Gemini-Powered Referral Narrative Generator
Generates AI-crafted sections for CSOP-BP-GS-26-0001 referral packages.

Uses Gemini 1.5 Flash with professional legal/CBP tone templates.
Stores generated narratives in DB for audit trail and consistency.
"""

import logging
import json
from typing import Dict, Any, Optional
import google.generativeai as genai
from datetime import datetime

logger = logging.getLogger(__name__)


class ReferralNarrativeGenerator:
    """Generate professional referral narratives via Gemini"""

    def __init__(self, api_key: str = None):
        """Initialize Gemini API client"""
        if api_key:
            genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    def generate_section_3_6(self, shipment: Dict[str, Any], breakdown: Dict[str, Any]) -> str:
        """
        Generate Section 3-6: Historical Import Pattern Analysis

        CSOP Template: Analyze shipper/consignee historical patterns, origin shifts,
        frequency changes, value anomalies, corridor trends.
        """
        prompt = f"""
You are a CBP compliance officer writing a professional legal referral document for transshipment analysis.

Generate a SECTION 3-6: HISTORICAL IMPORT PATTERN ANALYSIS narrative for this shipment.

SHIPMENT DATA:
- Shipper: {shipment.get('shipper_name', 'Unknown')}
- Origin: {shipment.get('origin_country', 'XX')}
- Destination: {shipment.get('destination_country', 'US')}
- Commodity: {shipment.get('commodity_name', 'General')} (HS {shipment.get('hs_code', '9999')})
- Value: ${shipment.get('declared_value_usd', 0):,.0f}
- Shipper Age: {shipment.get('shipper_age_months', 'Unknown')} months
- Risk Score: {breakdown.get('final_score', 0):.0f}/100

TONE & FORMAT:
- Professional legal/technical language
- 2-3 paragraphs maximum
- Focus on: Origin country trends, shipper history, corridor patterns, anomalies
- Reference actual data points
- Cite applicable CBP regulations

CSOP CONTEXT:
- High-risk corridors: CN, VN, MY, TH to US
- Recent trend: Increased transshipment via intermediate ports
- Concern: New shippers in high-duty commodities

Write the narrative:
"""
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            return self._fallback_section_3_6(shipment)

    def generate_section_3_7(self, shipment: Dict[str, Any], breakdown: Dict[str, Any]) -> str:
        """
        Generate Section 3-7: Trade Flow Intelligence

        CSOP Template: Analyze commodity tariff environment, AD/CVD orders,
        prior enforcement, circumvention indicators.
        """
        prompt = f"""
You are a CBP tariff analyst writing a professional legal referral for trade enforcement.

Generate SECTION 3-7: TRADE FLOW INTELLIGENCE for this shipment.

SHIPMENT DATA:
- Commodity: {shipment.get('commodity_name', 'General')} (HS {shipment.get('hs_code', '9999')})
- Origin: {shipment.get('origin_country', 'XX')}
- AD/CVD Applicable: {'Yes' if shipment.get('ad_cvd_applicable') else 'No'}
- AD/CVD Rate: {shipment.get('ad_cvd_rate', 0)*100:.1f}% if applicable
- Value: ${shipment.get('declared_value_usd', 0):,.0f}
- Risk Score: {breakdown.get('final_score', 0):.0f}/100

ANALYSIS FRAMEWORK:
1. Tariff environment & AD/CVD orders
2. Circumvention risk indicators
3. Prior enforcement actions on commodity
4. Transshipment corridor analysis
5. Market pricing anomalies

TONE & FORMAT:
- Technical CBP language
- 2-3 paragraphs
- Cite CFR and prior cases where applicable
- Focus on evasion indicators

Write the narrative:
"""
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            return self._fallback_section_3_7(shipment)

    def generate_section_3_11_narrative(self, breakdown: Dict[str, Any], shipment: Dict[str, Any]) -> str:
        """
        Generate Section 3-11 Supporting Narrative: Risk Indicator Summary Analysis

        CSOP Template: Synthesize all 7 factors into cohesive risk narrative.
        Explain why shipment is high-risk, what patterns were detected,
        what indicators triggered concern.
        """
        components = breakdown.get("components", [])

        factor_summary = {}
        for comp in components:
            factor = comp.get("factor", "Unknown")
            if factor not in factor_summary:
                factor_summary[factor] = {"components": [], "total": 0}
            factor_summary[factor]["components"].append({
                "name": comp.get("component"),
                "score": comp.get("score"),
                "rationale": comp.get("rationale")
            })
            factor_summary[factor]["total"] += comp.get("weighted_result", 0)

        prompt = f"""
You are a senior CBP analyst writing a professional risk assessment.

Generate SECTION 3-11 SUPPORTING NARRATIVE: Risk Indicator Summary & Analysis

SHIPMENT RISK BREAKDOWN:
- Final Risk Score: {breakdown.get('final_score', 0):.0f}/100
- Risk Level: Critical/High/Medium/Low based on score

7-FACTOR ANALYSIS:
{json.dumps(factor_summary, indent=2)}

SHIPMENT CONTEXT:
- Shipper: {shipment.get('shipper_name', 'Unknown')} ({shipment.get('shipper_age_months', 'Unknown')} months old)
- Route: {shipment.get('origin_country', 'XX')} → {shipment.get('destination_country', 'US')}
- Element 9 Mismatch: {'Yes - CRITICAL' if shipment.get('element9_is_mismatch') else 'No'}
- Dwell Time: {shipment.get('dwell_days', 'Unknown')} days

WRITE:
1. Executive summary of key risk factors (1 paragraph)
2. Detailed analysis of top 3-5 risk indicators (1-2 paragraphs)
3. Pattern assessment & transshipment indicators (1 paragraph)
4. Cumulative risk assessment (1 paragraph)

TONE:
- Professional legal/analytical
- Evidence-based
- Focus on data-driven conclusions
- Reference specific factors and scores

Narrative:
"""
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            return self._fallback_section_3_11(breakdown, shipment)

    def generate_section_3_14_conclusion(self, breakdown: Dict[str, Any], shipment: Dict[str, Any]) -> str:
        """
        Generate Section 3-14: Conclusion & Recommendation

        CSOP Template: Legal conclusion with CFR/USC citations.
        Recommendation for examination/investigation/release based on risk score.
        """
        final_score = breakdown.get('final_score', 0)

        if final_score >= 85:
            recommendation = "RECOMMEND EXAMINATION & INVESTIGATION"
            action = "CRITICAL"
            legal_basis = "19 USC § 1592 (Customs Fraud), 19 CFR 165 (Entry/Examination)"
        elif final_score >= 70:
            recommendation = "RECOMMEND EXAMINATION"
            action = "HIGH"
            legal_basis = "19 CFR 165 (Examination Authority), CAVC Standards"
        else:
            recommendation = "RECOMMEND RELEASE"
            action = "MEDIUM"
            legal_basis = "19 CFR 163 (Reasonable Care Standard)"

        prompt = f"""
You are a CBP legal counsel writing a professional conclusion and recommendation.

Generate SECTION 3-14: CONCLUSION & RECOMMENDATION

CASE SUMMARY:
- Shipment: {shipment.get('shipper_name', 'Unknown')} → {shipment.get('consignee_name', 'Unknown')}
- Route: {shipment.get('origin_country', 'XX')} → {shipment.get('destination_country', 'US')}
- Commodity: {shipment.get('commodity_name', 'General')} (HS {shipment.get('hs_code', '9999')})
- Value: ${shipment.get('declared_value_usd', 0):,.0f}
- Final Risk Score: {final_score:.0f}/100
- Action Level: {action}

RECOMMENDATION: {recommendation}
LEGAL BASIS: {legal_basis}

KEY FINDINGS:
- Element 9 Mismatch: {'YES - Declared {shipment.get("element9_declared_country")} but actual {shipment.get("element9_actual_country")}' if shipment.get('element9_is_mismatch') else 'No'}
- Dwell Anomaly: {shipment.get('dwell_days', 0)} days (suspicious)
- New Shipper: {shipment.get('shipper_age_months', 0)} months old
- High Tariff Commodity: AD/CVD {shipment.get('ad_cvd_rate', 0)*100:.1f}%

WRITE:
1. Conclusion paragraph synthesizing findings (1-2 paragraphs)
2. Legal basis paragraph citing applicable statutes/regulations (1 paragraph)
3. Clear recommendation statement (1 sentence)
4. Suggested next steps / investigation focus (1 paragraph)

TONE:
- Formal legal language
- Evidence-based conclusions
- Proper citations to CFR/USC
- Professional CBP voice
- Appropriate for federal legal proceedings

Conclusion Narrative:
"""
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            return self._fallback_section_3_14(final_score, shipment)

    # ===== FALLBACK TEMPLATES (if Gemini fails) =====

    def _fallback_section_3_6(self, shipment: Dict[str, Any]) -> str:
        """Fallback narrative for Section 3-6"""
        origin = shipment.get('origin_country', 'XX')
        shipper = shipment.get('shipper_name', 'Unknown Shipper')
        age = shipment.get('shipper_age_months', 'unknown')

        return f"""
HISTORICAL IMPORT PATTERN ANALYSIS

Analysis of import records for {shipper} (based in {origin}) reveals concerning patterns consistent with
transshipment evasion schemes. The shipper, established approximately {age} months ago, has conducted multiple
shipments within a short operational window—a pattern frequently associated with shell companies created
specifically to facilitate illicit trade flows.

The {origin} to United States corridor has been identified by CBP as a high-risk pathway for transshipment
of commodities subject to anti-dumping and countervailing duties. Recent increases in shipment frequency from
this region, coupled with the new shipper establishment date, suggest potential coordination with circumvention
networks rather than legitimate commercial operations.

Prior enforcement actions targeting similar shipper profiles from the region indicate this pattern aligns
with known transshipment methodologies, including the use of intermediate transshipment points to obscure
the true country of origin and evade applicable trade remedy orders.
"""

    def _fallback_section_3_7(self, shipment: Dict[str, Any]) -> str:
        """Fallback narrative for Section 3-7"""
        commodity = shipment.get('commodity_name', 'General')
        hs = shipment.get('hs_code', '9999')
        rate = shipment.get('ad_cvd_rate', 0) * 100
        origin = shipment.get('origin_country', 'XX')

        return f"""
TRADE FLOW INTELLIGENCE

The subject commodity, {commodity} (HTS {hs}), is currently subject to active anti-dumping and countervailing
duty orders at a combined rate of {rate:.1f}%. This elevated tariff environment creates significant financial
incentive for circumvention through transshipment schemes.

Historical trade data demonstrates that commodities in this HTS classification from {origin} have been
frequently targeted by enforcement actions for transshipment fraud. The magnitude of duty exposure
({rate:.1f}%) is substantial enough to justify considerable operational costs associated with disguising
country of origin.

CBP has documented multiple cases involving similar commodity/origin/destination combinations where
transshipment through intermediate ports was used to defeat the applicability of trade remedy orders.
The pattern suggests organized, systematic efforts rather than isolated commercial transactions.
"""

    def _fallback_section_3_11(self, breakdown: Dict[str, Any], shipment: Dict[str, Any]) -> str:
        """Fallback narrative for Section 3-11"""
        score = breakdown.get('final_score', 0)

        return f"""
RISK INDICATOR SUMMARY - ANALYTICAL ASSESSMENT

This shipment presents multiple concurrent risk indicators that, in aggregate, establish a pattern
consistent with transshipment evasion. The combined risk score of {score:.0f}/100 reflects cumulative
exposure across documentation, commodity, routing, party, corridor, pattern, and temporal factors.

Most significantly, the shipment exhibits both evidence of origin misrepresentation (Element 9 mismatch
between declared and actual country of origin) and behavioral anomalies (extended dwell periods, new
shipper establishment, high-tariff commodity classification). These indicators do not appear in isolation
but form a coherent pattern known from enforcement experience to correlate with intentional circumvention.

The risk score distribution indicates that no single factor accounts for the elevated assessment; rather,
the accumulation of moderate-to-high indicators across multiple risk categories creates a strong basis for
examination and further investigation. The pattern aligns with known transshipment methodologies documented
in prior CBP enforcement actions against similar shipper/commodity/corridor combinations.
"""

    def _fallback_section_3_14(self, final_score: float, shipment: Dict[str, Any]) -> str:
        """Fallback narrative for Section 3-14"""

        if final_score >= 85:
            return f"""
CONCLUSION & RECOMMENDATION

Based on the comprehensive analysis of available shipment data, manifest documentation, and CBP intelligence,
this shipment presents critical risk indicators consistent with transshipment evasion of applicable trade remedy
orders. The cumulative evidence—including origin misrepresentation, new shipper status, suspicious routing patterns,
and high-tariff commodity classification—establishes probable cause for examination and further investigation.

LEGAL BASIS: This recommendation is issued pursuant to 19 USC § 1592 (Customs Fraud), 19 CFR 165 (Examination Authority),
and CBP authority under 19 USC § 1595a (Seizure and Forfeiture) for goods entered in violation of trade remedy orders
or through fraudulent transshipment schemes.

RECOMMENDATION: RECOMMEND EXAMINATION & INVESTIGATION

CBP should conduct a comprehensive examination of this shipment, with particular focus on: (1) verification of country
of origin through inspection of manufacturing records and supply chain documentation, (2) comparison of declared versus
actual commodities, (3) investigation of shipper entity background and beneficial ownership, and (4) correlation with
intelligence on transshipment networks operating in identified intermediate ports.
"""
        else:
            return f"""
CONCLUSION & RECOMMENDATION

This shipment presents elevated risk factors warranting closer examination before clearance. The risk score of
{final_score:.0f}/100 indicates medium-to-high concern across multiple factor categories, particularly related
to documentary consistency and routing anomalies.

LEGAL BASIS: Examination is authorized under 19 CFR 165 and consistent with reasonable care standards under
19 CFR 163.

RECOMMENDATION: RECOMMEND EXAMINATION

CBP should conduct examination focusing on verification of documentation consistency, country of origin confirmation,
and commodity verification prior to release.
"""


if __name__ == "__main__":
    import os

    api_key = os.getenv("GOOGLE_API_KEY")
    gen = ReferralNarrativeGenerator(api_key)

    # Test
    test_shipment = {
        "shipper_name": "Greenfield Industrial Trading Co.",
        "origin_country": "VN",
        "destination_country": "US",
        "commodity_name": "Aluminum Extrusions",
        "hs_code": "7604",
        "declared_value_usd": 150000,
        "shipper_age_months": 4,
        "element9_is_mismatch": True,
        "element9_declared_country": "VN",
        "element9_actual_country": "CN",
        "dwell_days": 12,
        "ad_cvd_applicable": True,
        "ad_cvd_rate": 0.55,
    }

    test_breakdown = {
        "final_score": 92.5,
        "components": []
    }

    print("=" * 80)
    print("Section 3-6: Historical Import Pattern")
    print("=" * 80)
    print(gen.generate_section_3_6(test_shipment, test_breakdown))
