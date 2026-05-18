"""Vertex AI Gemini LLM client for XAI and narrative generation"""

import logging
from typing import Optional
import google.generativeai as genai
from core.config import settings

logger = logging.getLogger(__name__)

class GeminiClient:
    """Client for Vertex AI Gemini LLM"""

    def __init__(self, project_id: str = settings.gemini_project, model: str = settings.gemini_model):
        self.project_id = project_id
        self.model = model
        # Configure the API key from environment
        try:
            genai.configure(api_key=settings.api_key)  # Set via GOOGLE_API_KEY or settings
        except Exception as e:
            logger.warning(f"Gemini API key not configured: {e}")

    async def generate_xai_assertion(self, context: dict) -> str:
        """Generate a plain-English XAI assertion for a risk factor"""
        prompt = f"""
You are a CBP trade compliance expert. Generate a brief, evidence-based assertion
explaining a specific risk factor in a transshipment detection case.

Context:
- Component: {context.get('component', 'unknown')}
- Evidence: {context.get('evidence', '')}
- Confidence: {context.get('confidence', 0)}
- Sources: {context.get('sources', [])}

Generate a 2-3 sentence assertion in plain English. Be specific. Reference actual data points.
No jargon. Format: "{{assertion text}}"
"""
        try:
            response = await self._call_gemini(prompt)
            return response.strip().strip('"')
        except Exception as e:
            logger.error(f"Failed to generate XAI assertion: {e}")
            return "Unable to generate assertion"

    async def generate_referral_narrative(self, package_data: dict) -> str:
        """Generate the narrative sections of a referral package"""
        prompt = f"""
You are drafting a CBP enforcement referral package. Generate a executive summary
of the illegal transshipment evidence for this shipment.

Shipment:
- Shipper: {package_data.get('shipper', 'Unknown')}
- Declared COO: {package_data.get('country_of_origin', 'Unknown')}
- HTS: {package_data.get('hts_code', 'Unknown')}
- Confidence Score: {package_data.get('score', 0)}/100

Key Evidence:
{package_data.get('key_evidence', '')}

Write 3-4 sentences for the executive summary. Use facts, not speculation.
"""
        try:
            response = await self._call_gemini(prompt)
            return response.strip()
        except Exception as e:
            logger.error(f"Failed to generate referral narrative: {e}")
            return "Unable to generate narrative"

    async def explain_score(self, score_context: dict) -> str:
        """Conversational explanation of why a shipment scored a certain value"""
        prompt = f"""
A CBP officer is asking: "Why did this shipment score {score_context.get('total_score', 0)}/100?"

Provide a conversational explanation of the key factors contributing to the score.

Score Breakdown:
{score_context.get('components', '')}

Key Evidence:
{score_context.get('evidence', '')}

Use plain language. Cite specific data points. Keep it 3-4 sentences.
"""
        try:
            response = await self._call_gemini(prompt)
            return response.strip()
        except Exception as e:
            logger.error(f"Failed to explain score: {e}")
            return "Unable to explain score"

    async def _call_gemini(self, prompt: str) -> str:
        """Make a call to Gemini API"""
        try:
            model = genai.GenerativeModel(self.model)
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            raise

# Global client instance
_gemini_client: Optional[GeminiClient] = None

async def init_gemini() -> GeminiClient:
    """Initialize Gemini client"""
    global _gemini_client
    _gemini_client = GeminiClient()
    logger.info(f"Gemini client initialized (model: {_gemini_client.model})")
    return _gemini_client

def get_gemini_client() -> GeminiClient:
    """Get the Gemini client instance"""
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client
