"""
Referral Package Analysis Service
Transforms raw referral data into professional analytical presentations using Gemini LLM
"""

import json
import logging
from typing import Dict, Any, Optional
import google.generativeai as genai
import os

logger = logging.getLogger(__name__)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)


class ReferralAnalysisService:
    """Analyzes referral packages and generates professional narratives using Gemini"""

    def __init__(self):
        self.model = None
        self._model_initialized = False
        self._api_key = GOOGLE_API_KEY

    def _get_model(self):
        """Lazily initialize the model on first use"""
        if self._model_initialized:
            return self.model

        self._model_initialized = True

        if not self._api_key:
            return None

        # Use latest available models for text generation
        model_names = ["gemini-3.5-flash", "gemini-2.5-flash", "gemini-2.0-flash"]

        for model_name in model_names:
            try:
                logger.info(f"Attempting to initialize {model_name}...")
                self.model = genai.GenerativeModel(model_name)
                logger.info(f"Successfully initialized {model_name}")
                return self.model
            except Exception as e:
                logger.warning(f"Could not load {model_name}: {e}")

        logger.error("Could not load any Gemini model")
        return None

    async def analyze_section(
        self,
        section_id: str,
        section_data: Dict[str, Any],
        shipment_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze a single referral section and generate professional narrative

        Args:
            section_id: Section identifier (e.g., "section_3_1_shipment_identification")
            section_data: Raw data for the section
            shipment_context: Full shipment context (for analysis)

        Returns:
            Enhanced section data with analysis, risk factors, and narrative
        """

        model = self._get_model()
        if not model:
            logger.warning("Gemini not configured, returning raw data")
            return self._format_raw_section(section_id, section_data)

        try:
            prompt = self._build_section_prompt(section_id, section_data, shipment_context)
            response = model.generate_content(prompt)

            # Extract response text
            response_text = response.text if hasattr(response, 'text') else str(response)

            # Strip markdown code fences if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]  # Remove ```json
            if response_text.startswith("```"):
                response_text = response_text[3:]  # Remove ```
            if response_text.endswith("```"):
                response_text = response_text[:-3]  # Remove trailing ```

            response_text = response_text.strip()
            logger.debug(f"[{section_id}] Cleaned response: {response_text[:100]}")

            analysis = json.loads(response_text)

            return {
                "section_id": section_id,
                "raw_data": section_data,
                "analysis": analysis,
                "narrative": analysis.get("narrative", ""),
                "risk_factors": analysis.get("risk_factors", []),
                "confidence_score": analysis.get("confidence_score", 0.5)
            }
        except json.JSONDecodeError as e:
            logger.error(f"Gemini JSON parsing failed for {section_id}: {e}. Response: {response_text[:500] if 'response_text' in locals() else 'N/A'}")
            return self._format_raw_section(section_id, section_data)
        except Exception as e:
            logger.error(f"Gemini analysis failed for {section_id}: {e}")
            return self._format_raw_section(section_id, section_data)

    def _build_section_prompt(
        self,
        section_id: str,
        section_data: Dict[str, Any],
        shipment_context: Dict[str, Any]
    ) -> str:
        """Build a Gemini prompt for analyzing a specific section"""

        section_prompts = {
            "section_3_1_shipment_identification": self._prompt_shipment_id,
            "section_3_2_line_items": self._prompt_line_items,
            "section_3_3_routing_history": self._prompt_routing,
            "section_3_4_parties_and_roles": self._prompt_parties,
            "section_3_5_entity_ownership_chain": self._prompt_entity_chain,
            "section_3_6_historical_import_pattern": self._prompt_import_history,
            "section_3_7_trade_flow_intelligence": self._prompt_trade_flow,
            "section_3_8_document_review": self._prompt_doc_review,
            "section_3_9_document_consistency": self._prompt_doc_consistency,
            "section_3_10_supplier_verification": self._prompt_supplier_verify,
            "section_3_11_risk_indicators": self._prompt_risk_indicators,
            "section_3_12_risk_score": self._prompt_risk_score,
            "section_3_13_what_if_analysis": self._prompt_what_if,
            "section_3_14_data_sources": self._prompt_data_sources,
        }

        prompt_fn = section_prompts.get(section_id)
        if not prompt_fn:
            return self._default_prompt(section_id, section_data, shipment_context)

        return prompt_fn(section_data, shipment_context)

    def _prompt_shipment_id(self, data: Dict, context: Dict) -> str:
        return f"""Analyze this shipment identification data for transshipment risk.

Data:
{json.dumps(data, indent=2)}

Shipment Context:
- Declared Origin: {context.get('origin_country')}
- HTS Code: {context.get('hs_code')}
- Risk Score: {context.get('risk_score')}

Provide a JSON response with:
{{
    "narrative": "Professional 2-3 sentence analysis of the shipment ID and any origin concerns",
    "risk_factors": [
        {{"factor": "Origin claim plausibility", "level": "HIGH/MEDIUM/LOW", "evidence": "Why?"}}
    ],
    "confidence_score": 0.0 to 1.0
}}"""

    def _prompt_line_items(self, data: Dict, context: Dict) -> str:
        return f"""Analyze these line items for pricing and commodity anomalies.

Data:
{json.dumps(data, indent=2)}

Context:
- Commodity: {context.get('commodity_name')}
- HTS Code: {context.get('hs_code')}
- Origin: {context.get('origin_country')}

Assess:
1. Are unit prices consistent across items?
2. Do prices match expected market values for this commodity?
3. Are prices consistent with declared origin manufacturing?

Return JSON:
{{
    "narrative": "Analysis of pricing and commodity consistency",
    "risk_factors": [...],
    "confidence_score": 0.0 to 1.0
}}"""

    def _prompt_routing(self, data: Dict, context: Dict) -> str:
        return f"""Analyze this routing history for transshipment indicators.

Data:
{json.dumps(data, indent=2)}

Look for:
1. Port dwell time anomalies
2. Unusual routing patterns
3. Inconsistencies with commodity baselines

Return JSON:
{{
    "narrative": "Analysis of routing consistency and anomalies",
    "risk_factors": [...],
    "confidence_score": 0.0 to 1.0
}}"""

    def _prompt_parties(self, data: Dict, context: Dict) -> str:
        return f"""Analyze the parties involved in this shipment for transshipment risk.

Data:
{json.dumps(data, indent=2)}

Assess:
1. Are party roles consistent with declared origin?
2. Do freight forwarder and broker connections suggest shell structures?
3. Any indicators of coordinated transshipment networks?

Return JSON:
{{
    "narrative": "Analysis of party roles and transshipment risk",
    "risk_factors": [...],
    "confidence_score": 0.0 to 1.0
}}"""

    def _prompt_entity_chain(self, data: Dict, context: Dict) -> str:
        return f"""Analyze entity ownership and relationships.

Data:
{json.dumps(data, indent=2)}

Shipper: {context.get('shipper_name')}
Declared Origin: {context.get('origin_country')}

Assess:
1. Does shipper entity profile match origin country?
2. Any evidence of beneficial owner in restricted jurisdictions?
3. Recent entity registration (potential shell structure)?

Return JSON:
{{
    "narrative": "Entity resolution analysis and ownership concerns",
    "risk_factors": [...],
    "confidence_score": 0.0 to 1.0
}}"""

    def _prompt_import_history(self, data: Dict, context: Dict) -> str:
        return f"""Analyze historical import patterns for origin-shifting.

Data:
{json.dumps(data, indent=2)}

HTS Code: {context.get('hs_code')}
Commodity: {context.get('commodity_name')}

Assess:
1. Has declared origin changed recently?
2. Is timing correlated with antidumping/countervailing duty orders?
3. Does pattern suggest systematic origin avoidance?

Return JSON:
{{
    "narrative": "Historical pattern analysis and origin-shifting risk",
    "risk_factors": [...],
    "confidence_score": 0.0 to 1.0
}}"""

    def _prompt_trade_flow(self, data: Dict, context: Dict) -> str:
        return f"""Analyze trade flow intelligence for anomalies.

Data:
{json.dumps(data, indent=2)}

Assess:
1. Is shipper-consignee relationship established and consistent?
2. Do commodity flows match supply chain norms?
3. Any indicators of pass-through manufacturing?

Return JSON:
{{
    "narrative": "Trade flow analysis and supply chain coherence",
    "risk_factors": [...],
    "confidence_score": 0.0 to 1.0
}}"""

    def _prompt_doc_review(self, data: Dict, context: Dict) -> str:
        return f"""Assess documentation completeness for origin verification.

Context: {context.get('shipper_name')} claims {context.get('origin_country')} origin
Commodity: {context.get('commodity_name')}

For this commodity and origin claim, what documents are REQUIRED for verification?
What documents are typically MISSING in transshipment cases?

Return JSON:
{{
    "narrative": "Documentation requirements and gaps analysis",
    "risk_factors": [...],
    "confidence_score": 0.0 to 1.0
}}"""

    def _prompt_doc_consistency(self, data: Dict, context: Dict) -> str:
        return f"""Assess document consistency for origin claims.

Data:
{json.dumps(data, indent=2)}

What data elements should appear consistently across commercial documents?
What inconsistencies would indicate origin fraud?

Return JSON:
{{
    "narrative": "Document consistency assessment",
    "risk_factors": [...],
    "confidence_score": 0.0 to 1.0
}}"""

    def _prompt_supplier_verify(self, data: Dict, context: Dict) -> str:
        return f"""Assess supplier manufacturing verification for {context.get('origin_country')} origin claim.

Commodity: {context.get('commodity_name')}
Shipper: {context.get('shipper_name')}

For this commodity:
1. What manufacturing facilities are required in claimed origin country?
2. What verification evidence is typically needed?
3. What gaps would indicate non-manufacturing (transshipment)?

Return JSON:
{{
    "narrative": "Supplier verification assessment and manufacturing plausibility",
    "risk_factors": [...],
    "confidence_score": 0.0 to 1.0
}}"""

    def _prompt_risk_indicators(self, data: Dict, context: Dict) -> str:
        return f"""Synthesize risk indicators from all previous analyses.

Risk Score: {context.get('risk_score')}
Risk Tier: {context.get('risk_tier')}

Data:
{json.dumps(data, indent=2)}

Summarize:
1. Top 3 risk factors
2. Evidence supporting each
3. Overall risk narrative

Return JSON:
{{
    "narrative": "Executive summary of risk factors and enforcement concerns",
    "risk_factors": [...],
    "confidence_score": 0.0 to 1.0
}}"""

    def _prompt_risk_score(self, data: Dict, context: Dict) -> str:
        return f"""Explain the risk scoring methodology and results.

Risk Components:
{json.dumps(data, indent=2)}

Risk Score: {context.get('risk_score')}

Explain:
1. What each factor measures
2. Why the weights matter
3. What the final score means for enforcement action

Return JSON:
{{
    "narrative": "Risk scoring methodology explanation and implications",
    "risk_factors": [...],
    "confidence_score": 0.0 to 1.0
}}"""

    def _prompt_what_if(self, data: Dict, context: Dict) -> str:
        return f"""Generate scenario analysis for this shipment.

Shipment: {context.get('shipment_id')}
Declared Origin: {context.get('origin_country')}
Risk Score: {context.get('risk_score')}

For this shipment, consider 3 scenarios:
1. "What if origin is legitimate?" - What evidence would support this?
2. "What if goods only transited origin country?" - How would risk change?
3. "What if pricing is legitimate?" - What would justify the declared values?

Return JSON:
{{
    "scenarios": [
        {{"name": "Scenario name", "probability": "HIGH/MEDIUM/LOW", "impact_on_risk": "+5 points / -10 points / No change"}}
    ],
    "narrative": "Scenario analysis and likelihood assessment",
    "confidence_score": 0.0 to 1.0
}}"""

    def _prompt_data_sources(self, data: Dict, context: Dict) -> str:
        return f"""Document data sources and methodology used in analysis.

Data:
{json.dumps(data, indent=2)}

Return JSON:
{{
    "narrative": "Summary of data sources, collection methodology, and analytical approach",
    "data_sources": [
        {{"source": "Source name", "use": "How it was used in analysis", "reliability": "HIGH/MEDIUM/LOW"}}
    ],
    "confidence_score": 0.0 to 1.0
}}"""

    def _default_prompt(self, section_id: str, data: Dict, context: Dict) -> str:
        """Default prompt for unknown sections"""
        return f"""Analyze this section of a trade referral package for illegal transshipment risk.

Section: {section_id}
Data: {json.dumps(data, indent=2)}

Context:
- Shipment: {context.get('shipment_id')}
- Declared Origin: {context.get('origin_country')}
- Risk Score: {context.get('risk_score')}

Provide professional analysis in JSON:
{{
    "narrative": "2-3 sentence analysis of this section",
    "risk_factors": [
        {{"factor": "Name", "level": "HIGH/MEDIUM/LOW", "evidence": "Supporting evidence"}}
    ],
    "confidence_score": 0.0 to 1.0
}}"""

    def _format_raw_section(self, section_id: str, data: Dict) -> Dict[str, Any]:
        """Format section with no Gemini analysis"""
        return {
            "section_id": section_id,
            "raw_data": data,
            "analysis": {
                "narrative": "Analysis unavailable",
                "risk_factors": [],
                "confidence_score": 0.0
            }
        }

    async def analyze_full_referral(self, referral_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze complete referral package and generate professional presentation

        Args:
            referral_data: Complete referral data from API

        Returns:
            Enhanced referral with analysis for all sections
        """

        shipment_context = {
            "shipment_id": referral_data.get("shipment_id"),
            "origin_country": referral_data.get("origin_country", "UNKNOWN"),
            "risk_score": referral_data.get("risk_score"),
            "risk_tier": referral_data.get("risk_tier"),
            "hs_code": referral_data.get("hs_code"),
            "commodity_name": referral_data.get("commodity_name"),
            "shipper_name": referral_data.get("shipper_name"),
        }

        analyzed_sections = {}
        sections = referral_data.get("sections", {})

        logger.info(f"Analyzing {len(sections)} sections for referral {referral_data.get('referral_id')}")

        for section_id, section_data in sections.items():
            try:
                analyzed = await self.analyze_section(section_id, section_data, shipment_context)
                analyzed_sections[section_id] = analyzed
            except Exception as e:
                logger.error(f"Failed to analyze {section_id}: {e}")
                analyzed_sections[section_id] = self._format_raw_section(section_id, section_data)

        # Calculate overall confidence score
        scores = [s.get("confidence_score", 0) for s in analyzed_sections.values()]
        overall_confidence = sum(scores) / len(scores) if scores else 0.5

        return {
            "referral_id": referral_data.get("referral_id"),
            "shipment_id": referral_data.get("shipment_id"),
            "risk_score": referral_data.get("risk_score"),
            "risk_tier": referral_data.get("risk_tier"),
            "overall_confidence": overall_confidence,
            "created_at": referral_data.get("created_at"),
            "analyzed_sections": analyzed_sections,
            "metadata": referral_data.get("metadata", {})
        }
