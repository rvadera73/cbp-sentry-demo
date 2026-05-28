"""Ask-AI Agent — Gemini-powered RAG intelligence analyst for CBP Sentry

Provides streaming responses with function calling, session memory, and source attribution.
"""

import google.generativeai as genai
import json
import uuid
import logging
from typing import AsyncGenerator, Dict, Any, Optional, List
from datetime import datetime
try:
    from .ask_ai_tools import TOOL_REGISTRY, GEMINI_TOOL_DEFINITIONS
except ImportError:
    from ask_ai_tools import TOOL_REGISTRY, GEMINI_TOOL_DEFINITIONS

logger = logging.getLogger(__name__)


class AskAIAgent:
    """Gemini-powered intelligence analyst with function calling and streaming."""

    SYSTEM_PROMPT = """You are Sentry, an AI intelligence analyst embedded in the CBP illegal transshipment detection platform.

You have access to tools to query:
- Live shipment data (manifests, vessel tracking, risk scores)
- CORD entity database (21M+ corporate registry records)
- OFAC and OpenSanctions screening
- Risk score components and audit trails
- Historical patterns and trends
- Trade corridor intelligence (AD/CVD rates, enforcement history)
- Referral packages and officer analysis

You are advising CBP trade enforcement officers who need fast, accurate intelligence to make rapid decisions.

**Persona:** Senior trade enforcement analyst with deep knowledge of transshipment patterns, sanctions evasion, and supply chain manipulation.

**Response Style:**
- Be specific: cite shipper names, risk scores, data sources, and confidence levels
- Flag OFAC hits and shell company chains PROMINENTLY — these are critical findings
- Provide context: explain why a score is 87/100, not just what the score is
- Suggest next steps: "This entity warrants entity chain investigation" or "The ISF mismatch and OFAC hit together suggest..."
- Always mention your sources: which tools you used and what data you found

**Key Rules:**
1. Always use tools to query data — never make up statistics or risk scores
2. When you find a potential sanctions evasion or shell company chain, flag it prominently
3. If you lack information to answer a question (tool returns error or no data), say so clearly
4. Provide confidence levels for your findings
5. Cross-reference data sources: if OFAC says HIGH_RISK and the entity chain shows shell companies, emphasize the convergence

Answer conversationally but with precision. A CBP officer is reading your response to make operational decisions."""

    def __init__(self, api_key: str = None):
        """Initialize AskAIAgent with Gemini configuration.

        Args:
            api_key: Google API key (uses env var GOOGLE_API_KEY if not provided)
        """
        if api_key:
            genai.configure(api_key=api_key)

        # Initialize model
        # Note: system instruction and tools are passed at generation time
        self.model = genai.GenerativeModel(model_name="gemini-2.5-flash")

        # Session memory: session_id → list of chat messages
        self.sessions: Dict[str, List[Dict[str, str]]] = {}
        self.MAX_HISTORY = 20  # Keep last 20 messages per session

    def create_session(self) -> str:
        """Create a new chat session.

        Returns:
            session_id (UUID)
        """
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = []
        return session_id

    def _add_message(self, session_id: str, role: str, content: str) -> None:
        """Add message to session history."""
        if session_id not in self.sessions:
            self.sessions[session_id] = []

        self.sessions[session_id].append({"role": role, "content": content})

        # Keep only last N messages
        if len(self.sessions[session_id]) > self.MAX_HISTORY:
            self.sessions[session_id] = self.sessions[session_id][-self.MAX_HISTORY:]

    def _build_context_prefix(self, context: Dict[str, Any]) -> str:
        """Build system context from page + selected case.

        Args:
            context: {page, shipment_id, entity, ...}

        Returns:
            Prefix string to prepend to user message
        """
        parts = []

        if context.get("page"):
            parts.append(f"[Page: {context['page']}]")

        if context.get("shipment_id"):
            parts.append(f"[Current Shipment: {context['shipment_id']}]")

        if context.get("entity"):
            parts.append(f"[Current Entity: {context['entity']}]")

        if parts:
            return " ".join(parts) + "\n"
        return ""

    async def stream_response(
        self,
        session_id: str,
        user_message: str,
        context: Dict[str, Any] = None
    ) -> AsyncGenerator[str, None]:
        """Stream a response with function calling and source attribution.

        Yields JSON-formatted SSE events:
        - {"type": "text", "content": "token text"}
        - {"type": "source", "tool": "investigate_entity", "summary": "...", "hit": true}
        - {"type": "done"}

        Args:
            session_id: Chat session ID
            user_message: User question/command
            context: Optional context {page, shipment_id, entity, ...}
        """
        if session_id not in self.sessions:
            self.sessions[session_id] = []

        context = context or {}

        # Build full message with context
        context_prefix = self._build_context_prefix(context)
        full_message = context_prefix + user_message if context_prefix else user_message

        # Add user message to history
        self._add_message(session_id, "user", full_message)

        # Prepend system prompt to first message in history
        history = []

        # Build message content with system prompt at the start
        messages_to_send = self.sessions[session_id][:-1]  # Exclude the message we just added

        if not messages_to_send:
            # First message - include system prompt
            history.append({
                "role": "user",
                "parts": [{"text": f"{self.SYSTEM_PROMPT}\n\n{full_message}"}]
            })
        else:
            # Build history without system prompt on subsequent messages
            for msg in messages_to_send:
                # Map session role format to Gemini role format
                gemini_role = "model" if msg["role"] == "assistant" else "user"
                history.append({
                    "role": gemini_role,
                    "parts": [{"text": msg["content"]}]
                })

            # Add the new user message
            history.append({
                "role": "user",
                "parts": [{"text": full_message}]
            })

        try:
            # Start streaming (genai 0.3.0 doesn't support tools parameter, will use content-based)
            response = await self.model.generate_content_async(
                history,
                stream=True
            )

            accumulated_text = ""
            full_response = ""
            tool_calls_made = []

            async for chunk in response:
                if not chunk.candidates:
                    continue

                for part in chunk.candidates[0].content.parts:
                    # Handle text parts (genai 0.3.0 only supports text)
                    if hasattr(part, "text") and part.text:
                        text = part.text
                        full_response += text

                        # Yield text as SSE event
                        yield f'data: {json.dumps({"type": "text", "content": text})}\n\n'

            # Add assistant response to history
            self._add_message(session_id, "assistant", full_response)

            # Yield completion event
            yield f'data: {json.dumps({"type": "done"})}\n\n'

        except Exception as e:
            logger.error(f"Stream error in session {session_id}: {e}")
            yield f'data: {json.dumps({"type": "error", "content": str(e)})}\n\n'

    def _summarize_tool_result(self, tool_name: str, result: Dict[str, Any]) -> str:
        """Generate a user-friendly summary of tool execution result.

        Args:
            tool_name: Name of the tool
            result: Result dictionary from tool

        Returns:
            Summary string
        """
        try:
            if result.get("error"):
                return f"{tool_name}: {result['error'][:100]}"

            if tool_name == "search_shipments":
                found = result.get("found", 0)
                return f"Found {found} shipments matching query"

            elif tool_name == "get_shipment_risk_breakdown":
                score = result.get("final_score", "?")
                level = result.get("risk_level", "?")
                return f"Risk Score: {score}/100 ({level})"

            elif tool_name == "investigate_entity":
                found = result.get("found", False)
                entity = result.get("entity_name", "?")
                country = result.get("country", "")
                match_type = result.get("match_type", "")
                status = result.get("sanctions_status", "")
                if found:
                    if status and "HIT" in status:
                        return f"Entity found: {entity} ({country}) — ⚠️ SANCTIONS HIT ({status})"
                    return f"Entity found: {entity} ({country}) [{match_type}]"
                return f"Entity not found: {entity}"

            elif tool_name == "get_ownership_chain":
                tiers = result.get("total_tiers", 0)
                flags = result.get("shell_company_flags", [])
                if flags:
                    return f"Ownership chain ({tiers} tiers) — ⚠️ {len(flags)} shell company flags"
                return f"Ownership chain: {tiers} tiers traced"

            elif tool_name == "check_sanctions_screening":
                status = result.get("status", "UNKNOWN")
                hits = len(result.get("hits", []))
                if "HIT" in status:
                    return f"Sanctions screening: ⚠️ {status} ({hits} hits)"
                return f"Sanctions screening: {status}"

            elif tool_name == "get_corridor_risk":
                corridor = result.get("corridor", "?")
                level = result.get("risk_level", "?")
                cases = result.get("total_cases", 0)
                return f"Corridor {corridor}: {level} risk ({cases} enforcement cases)"

            elif tool_name == "get_case_statistics":
                total = result.get("total_shipments", 0)
                active = result.get("active_cases_risk_gte75", 0)
                return f"Caseload: {total} total, {active} active (risk ≥75)"

            elif tool_name == "get_what_if_scenarios":
                scenarios = len(result.get("scenarios", []))
                return f"What-if scenarios: {scenarios} scenarios analyzed"

            elif tool_name == "get_historical_patterns":
                total = result.get("total_shipments", 0)
                avg_risk = result.get("avg_risk_score", 0)
                trend = result.get("risk_trend", "?")
                return f"Historical patterns: {total} shipments, avg risk {avg_risk}/100, {trend}"

            elif tool_name == "get_referral_summary":
                status = result.get("package_status", "?")
                complete = result.get("sections_completed", 0)
                total = result.get("sections_total", 0)
                return f"Referral package: {status} ({complete}/{total} sections)"

            return f"{tool_name}: executed"
        except Exception as e:
            return f"{tool_name}: {str(e)[:50]}"

    def clear_session(self, session_id: str) -> None:
        """Clear session history."""
        if session_id in self.sessions:
            del self.sessions[session_id]

    def get_session_history(self, session_id: str) -> List[Dict[str, str]]:
        """Get chat history for a session."""
        return self.sessions.get(session_id, [])
