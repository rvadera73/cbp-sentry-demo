"""
Google Vertex AI (Gemini 1.5 Flash) Integration

Uses LLM for:
1. Document extraction (OCR text → structured data from invoices, C/Os, packing lists)
2. Evidence synthesis (narrative generation for referral package sections)
3. Entity name normalization and alias detection
4. Fraud pattern detection in unstructured documents

Lazy-loaded: Only called when risk_score >= 75% or when generating referral package.
"""

import logging
import os
from typing import Optional, Dict, List, Any
import json

logger = logging.getLogger(__name__)

# Attempt to import Gemini SDK
try:
    import google.generativeai as genai

    GEMINI_AVAILABLE = True
except ImportError:
    logger.warning("Gemini SDK not available, using fixture mode")
    GEMINI_AVAILABLE = False


class VertexAIClient:
    """
    Google Gemini API client for document extraction and LLM evidence synthesis.

    Uses Gemini 1.5 Flash for cost-efficient processing of:
    - Commercial invoices (extract supplier, quantities, prices)
    - Certificates of origin (extract declared origin, manufacturer address)
    - Packing lists (extract container details, weights, dimensions)
    - Email correspondence (detect fraud signals, name aliases)
    """

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY", "")
        self.model_name = "gemini-1.5-flash"  # Cost-effective model for demo
        self.available = GEMINI_AVAILABLE and bool(self.api_key)

        if self.available:
            try:
                genai.configure(api_key=self.api_key)
                self.client = genai.GenerativeModel(self.model_name)
                logger.info("Gemini 1.5 Flash API configured")
            except Exception as e:
                logger.warning(f"Gemini API configuration failed: {e}, using fixture mode")
                self.available = False
        else:
            if not GEMINI_AVAILABLE:
                logger.warning("Gemini SDK not available, using fixture mode")
            elif not self.api_key:
                logger.warning("GOOGLE_API_KEY not set, using fixture mode")

    async def extract_from_document(
        self, document_url: str, document_type: str = "invoice"  # invoice, certificate_of_origin, packing_list, email
    ) -> Dict[str, Any]:
        """
        Extract structured data from document using Gemini vision.

        Args:
            document_url: URL or base64-encoded image of document
            document_type: Type of document for context

        Returns:
            {
                "extracted": bool,
                "document_type": str,
                "fields": {
                    "supplier_name": str,
                    "origin_country": str,
                    "manufacturing_date": str,
                    "quantities": Dict,
                    "prices": Dict,
                    "weights": Dict,
                    "alert_signals": List[str]
                },
                "confidence": float,
                "model": str,
                "notes": str
            }
        """
        if not self.available:
            return self._fixture_extract_document(document_type)

        try:
            # In production: call Gemini multimodal endpoint with document image
            # For demo: return fixture data
            logger.info(f"Extracting {document_type} from {document_url[:50]}...")

            # TODO: Implement actual Vertex AI multimodal call
            # response = await self._call_gemini_vision(document_url, document_type)

            return self._fixture_extract_document(document_type)

        except Exception as e:
            logger.error(f"Document extraction failed: {e}")
            return {"extracted": False, "error": str(e), "confidence": 0.0}

    async def generate_evidence_narrative(
        self, shipment_id: str, entities: List[Dict[str, Any]], signals: Dict[str, Any], risk_score: float
    ) -> Dict[str, Any]:
        """
        Generate natural language evidence narratives for referral package sections.

        Uses Gemini to synthesize findings into CBP-style language.

        Args:
            shipment_id: Manifest ID
            entities: Resolved entity chain
            signals: Risk signals (H1/H2/H3 scores, anomalies, OFAC hits)
            risk_score: Overall risk score (0-100)

        Returns:
            {
                "section_3_6_historical_pattern": str,
                "section_3_7_trade_flow": str,
                "section_3_11_risk_indicators": List[Dict],
                "section_3_13_what_if_scenarios": List[Dict],
                "model": str,
                "confidence": float
            }
        """
        if not self.available:
            return self._fixture_generate_evidence_narrative(shipment_id, entities, signals)

        try:
            logger.info(f"Generating evidence narrative for {shipment_id} (risk: {risk_score}/100)")

            # TODO: Implement actual Vertex AI text generation
            # prompt = self._build_evidence_prompt(shipment_id, entities, signals, risk_score)
            # response = await self._call_gemini_text(prompt)

            return self._fixture_generate_evidence_narrative(shipment_id, entities, signals)

        except Exception as e:
            logger.error(f"Evidence narrative generation failed: {e}")
            return {"error": str(e), "confidence": 0.0}

    async def detect_entity_aliases(
        self, primary_name: str, documents: List[str], country: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detect entity name aliases and transliterations from unstructured documents.

        Uses Gemini to:
        - Match transliterated names (e.g., "Greenfield" / "綠田")
        - Detect common aliases (abbreviations, formal vs trade names)
        - Flag name obfuscation patterns

        Args:
            primary_name: Primary entity name (from manifest)
            documents: List of document text samples
            country: Entity country code for transliteration hints

        Returns:
            {
                "aliases": List[str],
                "transliterations": List[Dict],
                "obfuscation_risk": float,
                "confidence": float
            }
        """
        if not self.available:
            return self._fixture_detect_aliases(primary_name, country)

        try:
            logger.info(f"Detecting aliases for '{primary_name}' (country: {country})")

            # TODO: Implement actual Vertex AI analysis
            # prompt = self._build_alias_detection_prompt(primary_name, documents, country)
            # response = await self._call_gemini_text(prompt)

            return self._fixture_detect_aliases(primary_name, country)

        except Exception as e:
            logger.error(f"Alias detection failed: {e}")
            return {"aliases": [], "error": str(e), "confidence": 0.0}

    # Fixture implementations (demo mode)

    @staticmethod
    def _fixture_extract_document(document_type: str) -> Dict[str, Any]:
        """Return fixture document extraction for demo."""
        fixtures = {
            "invoice": {
                "extracted": True,
                "document_type": "invoice",
                "fields": {
                    "supplier_name": "Greenfield Industrial Trading Co., Ltd.",
                    "origin_country": "VN",
                    "manufacturing_date": "2026-02-15",
                    "quantities": {"units": 5000, "unit_type": "kg"},
                    "prices": {"declared_usd": 50000, "market_comparable_usd": 75000},
                    "weights": {"net_kg": 5000, "gross_kg": 5200},
                    "alert_signals": [
                        "Declared price 33% below market comparable",
                        "Supplier incorporated 8 months ago (new entity)",
                    ],
                },
                "confidence": 0.92,
                "model": "Gemini 1.5 Flash (fixture)",
            },
            "certificate_of_origin": {
                "extracted": True,
                "document_type": "certificate_of_origin",
                "fields": {
                    "declared_origin": "VN",
                    "manufacturer_address": "Hanoi, Vietnam",
                    "shipper_address": "Guangzhou, China",
                    "exporter_date": "2026-02-20",
                    "alert_signals": ["ISF Element 9 mismatch: declared VN, actual stuffing China"],
                },
                "confidence": 0.88,
                "model": "Gemini 1.5 Flash (fixture)",
            },
            "packing_list": {
                "extracted": True,
                "document_type": "packing_list",
                "fields": {
                    "container_count": 450,
                    "containers": {"containers_per_20ft": 450},
                    "weights": {"total_net_kg": 5000},
                    "alert_signals": [],
                },
                "confidence": 0.95,
                "model": "Gemini 1.5 Flash (fixture)",
            },
        }
        return fixtures.get(document_type, {"extracted": False, "document_type": document_type, "confidence": 0.0})

    @staticmethod
    def _fixture_generate_evidence_narrative(
        shipment_id: str, entities: List[Dict[str, Any]], signals: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Return fixture evidence narrative for demo."""
        return {
            "section_3_6_historical_pattern": (
                "Import pattern analysis reveals significant shift in origin country from Vietnam to China "
                "over the past 6 months. Prior filings under HTS 7604 show 95% Vietnamese origin; current "
                "filing shows China-based stuffing location with identical pricing and quantities. This shift "
                "coincides with increased AD/CVD enforcement on Vietnamese aluminum (34.78% rate effective Feb 2026)."
            ),
            "section_3_7_trade_flow": (
                "Greenfield Industrial's prior CBP filings total 3 declarations, all routed through Guangzhou, "
                "China as transshipment point. SunPath Energy Distributors (consignee) has 9 prior EAPA-related "
                "declarations with 5 evasion determinations. Shared freight forwarder (Pan-Pacific Logistics) "
                "appears in 87 transshipment cases in SEASIA corridor."
            ),
            "section_3_11_risk_indicators": [
                {
                    "indicator": "ISF Element 9 Mismatch",
                    "risk_level": "HIGH",
                    "evidence": "Declared origin Vietnam; actual port of loading Guangzhou, China",
                    "authority": "19 CFR 149.2(c) — ISF must state accurate origin",
                },
                {
                    "indicator": "Shipper Age + Volume",
                    "risk_level": "HIGH",
                    "evidence": "Shipper incorporated 8 months ago; declaring $50K+ shipments immediately",
                    "authority": "EAPA (19 USC 1517) — sudden large-volume new entities",
                },
                {
                    "indicator": "Dwell Time Anomaly",
                    "risk_level": "MEDIUM",
                    "evidence": "11.2 days in Guangzhou port vs 2.1 day baseline (5.3× normal)",
                    "authority": "AIS tracking, CBP-OP manifest review protocols",
                },
            ],
            "section_3_13_what_if_scenarios": [
                {
                    "scenario": "If origin truly Vietnamese: score would be 12/100 (LOW)",
                    "supporting_facts": "Vietnam Aluminum Corp (established 2009) scores 18/100 with similar volume",
                    "counterfactual_analysis": "Shipper age and corridor alone do not justify HIGH risk",
                }
            ],
            "model": "Gemini 1.5 Flash (fixture)",
            "confidence": 0.87,
        }

    @staticmethod
    def _fixture_detect_aliases(primary_name: str, country: Optional[str]) -> Dict[str, Any]:
        """Return fixture alias detection for demo."""
        if "greenfield" in primary_name.lower() and country == "VN":
            return {
                "primary_name": primary_name,
                "aliases": ["Greenfield Industrial", "Greenfield Vietnam", "GF Industrial Trading"],
                "transliterations": [{"script": "Chinese", "names": ["綠田工業", "绿田工业"], "confidence": 0.78}],
                "obfuscation_risk": 0.45,
                "model": "Gemini 1.5 Flash (fixture)",
                "confidence": 0.84,
            }
        return {
            "primary_name": primary_name,
            "aliases": [],
            "transliterations": [],
            "obfuscation_risk": 0.0,
            "confidence": 0.0,
        }


# Global singleton
_vertex_ai_client = None


async def get_vertex_ai_client() -> VertexAIClient:
    """Get or create Vertex AI client."""
    global _vertex_ai_client
    if _vertex_ai_client is None:
        _vertex_ai_client = VertexAIClient()
    return _vertex_ai_client
