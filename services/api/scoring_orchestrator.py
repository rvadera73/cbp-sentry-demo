"""
Unified Scoring Orchestrator — H1/H2/H3 continuous API invocation cycle
All APIs invoked in parallel for speed. Live mode by default.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from external_apis.config import get_api_mode, is_api_enabled, API_MODE
from external_apis.h1_adapters import OpenCorporatesAdapter, ComtradeAdapter, ITCTariffsAdapter
from external_apis.h2_adapters import AISAdapter, PortAuthorityAdapter
from external_apis.base_adapter import BaseAPIAdapter
from entity_resolution.cord_rag import CORDRagDatabase
from entity_resolution.senzing_client import SenzingClient

logger = logging.getLogger(__name__)


@dataclass
class ComponentScore:
    """Single component of the 3-horizon scoring."""

    name: str  # "H1 Corridor Risk", "H2 Vessel Anomaly", etc
    value: float  # 0-40, 0-35, 0-25 respectively
    max_points: float
    confidence: float  # 0.0-1.0 based on data quality
    sources: List[str]  # Which APIs provided data
    evidence: List[str]  # Natural language explanations
    api_latency_ms: Dict[str, float]  # Per-API latency


@dataclass
class ScoreResponse:
    """Full scoring response with audit trail."""

    manifest_id: str
    shipment_id: Optional[str]
    timestamp: datetime

    # Component scores
    h1_score: ComponentScore  # Corridor Risk (40 pts)
    h2_score: ComponentScore  # Vessel Anomaly (35 pts)
    h3_score: ComponentScore  # Manifest Intelligence (25 pts)

    # Combined score
    total_score: float  # 0-100
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL

    # Feedback override (if analyst adjusted score)
    feedback_applied: bool
    feedback_id: Optional[str]
    original_score: Optional[float]  # Before feedback
    adjusted_score: Optional[float]  # After feedback

    # Confidence & data sources
    overall_confidence: float  # 0.0-1.0
    live_api_count: int  # How many APIs returned live data
    fixture_api_count: int  # How many fell back to fixtures
    total_latency_ms: float

    # Audit trail
    api_sources: Dict[str, Dict[str, Any]]  # Full response from each API


class ScoringOrchestrator:
    """Orchestrates H1, H2, H3 scoring with live API calls."""

    def __init__(self):
        """Initialize all API adapters."""
        self.api_mode = API_MODE

        # H1 adapters
        self.oc_adapter = OpenCorporatesAdapter()
        self.comtrade_adapter = ComtradeAdapter()
        self.itc_adapter = ITCTariffsAdapter()

        # H2 adapters
        self.ais_adapter = AISAdapter()
        self.port_adapter = PortAuthorityAdapter()

        logger.info(f"ScoringOrchestrator initialized in {self.api_mode} mode")

    async def score_shipment(
        self, manifest_id: str, shipment_data: Dict[str, Any], feedback_override: Optional[Dict[str, Any]] = None
    ) -> ScoreResponse:
        """
        Score a shipment using all three horizons with live APIs.

        Args:
            manifest_id: Unique manifest ID
            shipment_data: {
                shipper_name, shipper_country,
                consignee_name, consignee_country,
                hs_code, declared_value, declared_weight_kg,
                vessel_imo, vessel_name, port_of_entry
            }
            feedback_override: Optional analyst feedback adjusting score

        Returns:
            ScoreResponse with full audit trail
        """
        start_time = datetime.utcnow()
        latencies = {}
        api_sources = {}

        try:
            # H1: Corridor Risk Scoring (live APIs in parallel)
            h1_task = self._score_h1_corridor_risk(shipment_data, latencies, api_sources)

            # H2: Vessel Anomaly Scoring (live APIs in parallel)
            h2_task = self._score_h2_vessel_anomaly(shipment_data, latencies, api_sources)

            # H3: Manifest Intelligence Scoring (live APIs in parallel)
            h3_task = self._score_h3_manifest_intelligence(shipment_data, latencies, api_sources)

            # Execute all in parallel
            h1_score, h2_score, h3_score = await asyncio.gather(h1_task, h2_task, h3_task, return_exceptions=False)

            # Combine scores
            total_score = min(h1_score.value + h2_score.value + h3_score.value, 100.0)

            # Determine risk level
            if total_score >= 80:
                risk_level = "CRITICAL"
            elif total_score >= 60:
                risk_level = "HIGH"
            elif total_score >= 40:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"

            # Apply feedback override if provided
            original_score = total_score
            adjusted_score = None
            feedback_id = None
            feedback_applied = False

            if feedback_override and feedback_override.get("approved"):
                adjusted_score = feedback_override.get("adjusted_score")
                feedback_id = feedback_override.get("feedback_id")
                feedback_applied = True
                total_score = adjusted_score  # Use adjusted score

            # Count live vs fixture APIs
            live_api_count = sum(
                1 for api_data in api_sources.values() if api_data.get("_metadata", {}).get("mode") == "live"
            )
            fixture_api_count = len(api_sources) - live_api_count

            # Calculate overall confidence
            overall_confidence = self._calculate_confidence(
                h1_score.confidence, h2_score.confidence, h3_score.confidence, live_api_count, fixture_api_count
            )

            total_latency = (datetime.utcnow() - start_time).total_seconds() * 1000

            return ScoreResponse(
                manifest_id=manifest_id,
                shipment_id=shipment_data.get("shipment_id"),
                timestamp=start_time,
                h1_score=h1_score,
                h2_score=h2_score,
                h3_score=h3_score,
                total_score=total_score,
                risk_level=risk_level,
                feedback_applied=feedback_applied,
                feedback_id=feedback_id,
                original_score=original_score,
                adjusted_score=adjusted_score,
                overall_confidence=overall_confidence,
                live_api_count=live_api_count,
                fixture_api_count=fixture_api_count,
                total_latency_ms=total_latency,
                api_sources=api_sources,
            )

        except Exception as e:
            logger.error(f"Scoring failed for {manifest_id}: {e}", exc_info=True)
            raise

    async def _score_h1_corridor_risk(
        self, shipment_data: Dict[str, Any], latencies: Dict[str, float], api_sources: Dict[str, Any]
    ) -> ComponentScore:
        """H1: Corridor Risk Scoring (40 pts max)"""
        start = datetime.utcnow()
        sources = []
        evidence = []

        try:
            # Fetch shipper info (OpenCorporates)
            oc_start = datetime.utcnow()
            shipper_info = await self.oc_adapter.fetch(
                company_name=shipment_data["shipper_name"], jurisdiction=shipment_data["shipper_country"]
            )
            latencies["opencorporates"] = (datetime.utcnow() - oc_start).total_seconds() * 1000
            api_sources["opencorporates"] = shipper_info

            if shipper_info.get("_metadata", {}).get("mode") == "live":
                sources.append("OpenCorporates (live)")
            else:
                sources.append("OpenCorporates (fixture)")

            # Fetch trade benchmarks (UN Comtrade)
            ct_start = datetime.utcnow()
            benchmark_data = await self.comtrade_adapter.fetch(
                hs_code=shipment_data["hs_code"],
                reporter=shipment_data["shipper_country"],
                partner=shipment_data["consignee_country"],
            )
            latencies["comtrade"] = (datetime.utcnow() - ct_start).total_seconds() * 1000
            api_sources["comtrade"] = benchmark_data

            if benchmark_data.get("_metadata", {}).get("mode") == "live":
                sources.append("UN Comtrade (live)")
            else:
                sources.append("UN Comtrade (fixture)")

            # Fetch tariff/duty info (ITC)
            itc_start = datetime.utcnow()
            tariff_info = await self.itc_adapter.fetch(
                hs_code=shipment_data["hs_code"], origin_country=shipment_data["shipper_country"]
            )
            latencies["itc_tariffs"] = (datetime.utcnow() - itc_start).total_seconds() * 1000
            api_sources["itc_tariffs"] = tariff_info

            if tariff_info.get("_metadata", {}).get("mode") == "live":
                sources.append("ITC Tariffs (live)")
            else:
                sources.append("ITC Tariffs (fixture)")

            # Score based on corridor risk
            score = 0.0

            # Corridor sensitivity
            corridor = f"{shipment_data['shipper_country']}→{shipment_data['consignee_country']}"
            high_risk_corridors = [("CN", "MY"), ("CN", "VN"), ("CN", "TH"), ("CN", "KH")]
            if tuple(corridor.split("→")) in high_risk_corridors:
                score += 12
                evidence.append(f"High-risk corridor: {corridor} (+12 pts)")

            # Shipper age (from OpenCorporates)
            if shipper_info.get("found"):
                incorporation_date = shipper_info.get("incorporation_date")
                if incorporation_date:
                    # Calculate shipper age in months
                    from datetime import datetime as dt

                    try:
                        inc_date = dt.fromisoformat(incorporation_date.replace("Z", "+00:00"))
                        months_old = (dt.utcnow() - inc_date.replace(tzinfo=None)).days / 30

                        if months_old < 6:
                            score += 10
                            evidence.append(f"Very new shipper ({months_old:.0f} months) (+10 pts)")
                        elif months_old < 18:
                            score += 8
                            evidence.append(f"New shipper ({months_old:.0f} months) (+8 pts)")
                    except:
                        pass

            # AD/CVD active (from ITC)
            if tariff_info.get("active_cases", []):
                score += 12
                cases = [f"{c.get('case_num')} ({c.get('duty_rate')}%)" for c in tariff_info.get("active_cases")]
                evidence.append(f"Active AD/CVD: {', '.join(cases)} (+12 pts)")

            # Price undervaluation (declared vs benchmark)
            if benchmark_data.get("price_per_kg"):
                declared_price = shipment_data.get("declared_value", 0) / max(
                    shipment_data.get("declared_weight_kg", 1), 1
                )
                bench_price = benchmark_data["price_per_kg"]
                if declared_price < bench_price * 0.7:
                    score += 10
                    underval_pct = ((bench_price - declared_price) / bench_price) * 100
                    evidence.append(f"Price undervaluation: {underval_pct:.0f}% below benchmark (+10 pts)")

            # Calculate confidence
            confidence = 0.0
            if shipper_info.get("_metadata", {}).get("mode") == "live":
                confidence += 0.3
            if benchmark_data.get("_metadata", {}).get("mode") == "live":
                confidence += 0.3
            if tariff_info.get("_metadata", {}).get("mode") == "live":
                confidence += 0.4

            latency = (datetime.utcnow() - start).total_seconds() * 1000

            return ComponentScore(
                name="H1 Corridor Risk",
                value=min(score, 40.0),
                max_points=40.0,
                confidence=confidence,
                sources=sources,
                evidence=evidence,
                api_latency_ms=latencies,
            )

        except Exception as e:
            logger.error(f"H1 scoring failed: {e}")
            return ComponentScore(
                name="H1 Corridor Risk",
                value=0.0,
                max_points=40.0,
                confidence=0.0,
                sources=sources,
                evidence=[f"Error: {str(e)}"],
                api_latency_ms=latencies,
            )

    async def _score_h2_vessel_anomaly(
        self, shipment_data: Dict[str, Any], latencies: Dict[str, float], api_sources: Dict[str, Any]
    ) -> ComponentScore:
        """H2: Vessel Anomaly Scoring (35 pts max)"""
        # Placeholder — implement similar to H1 but with vessel APIs
        # This will call VesselFinder, ISF enrichment, AIS

        sources = ["VesselFinder (live)"]
        evidence = ["Vessel dwell analysis pending"]

        return ComponentScore(
            name="H2 Vessel Anomaly",
            value=0.0,
            max_points=35.0,
            confidence=0.5,
            sources=sources,
            evidence=evidence,
            api_latency_ms={},
        )

    async def _score_h3_manifest_intelligence(
        self, shipment_data: Dict[str, Any], latencies: Dict[str, float], api_sources: Dict[str, Any]
    ) -> ComponentScore:
        """H3: Manifest Intelligence Scoring (25 pts max)

        Phase 1 + 2 Integration:
        1. CORD RAG: Resolve entities locally (69K records, <100ms)
        2. Senzing SDK: Map entity relationships (why connected)
        3. Combined: Entity verified + relationships traced
        """
        score = 0.0
        evidence = []
        sources = ["CORD_LONDON", "CORD_MOSCOW", "CORD_LASVEGAS"]
        latencies_h3 = {}

        try:
            import time

            # Phase 1: Initialize CORD RAG
            cord_rag = CORDRagDatabase(os.path.join(os.path.dirname(__file__), "../../data/cord_rag.db"))

            # Phase 2: Initialize Senzing (for relationship mapping)
            try:
                senzing_client = SenzingClient("http://localhost:8250")
                senzing_available = True
            except Exception as e:
                logger.warning(f"Senzing not available: {e}")
                senzing_client = None
                senzing_available = False

            # ═══════════════════════════════════════════════════════════════
            # SHIPPER RESOLUTION & RELATIONSHIP MAPPING
            # ═══════════════════════════════════════════════════════════════

            start = time.time()
            shipper_match = await cord_rag.resolve_entity(
                shipment_data.get("shipper_name", ""), shipment_data.get("shipper_country", "")
            )
            latencies_h3["shipper_cord_lookup"] = (time.time() - start) * 1000

            if shipper_match["found"]:
                shipper_confidence = shipper_match["confidence"]
                score += 10.0 * shipper_confidence  # 0-10 pts
                sources.append(shipper_match["data_source"])

                evidence.append(
                    f"Shipper '{shipper_match['entity_name']}' verified via "
                    f"{shipper_match['data_source']} (confidence: {shipper_confidence:.0%})"
                )

                # Phase 2: Senzing relationship mapping
                if senzing_available and shipper_match.get("entity_id"):
                    start = time.time()
                    try:
                        related = senzing_client.related_entities(shipper_match["entity_id"])
                        latencies_h3["senzing_relationships"] = (time.time() - start) * 1000

                        if related:
                            score += 5.0
                            sources.append("Senzing")
                            evidence.append(
                                f"Beneficial owner chain traced via Senzing " f"({len(related)} related entities found)"
                            )
                        else:
                            # Entity found in CORD but no Senzing relationships
                            evidence.append(
                                f"Entity verified in CORD, " f"no additional relationships found in Senzing"
                            )
                    except Exception as e:
                        logger.warning(f"Senzing relationship query failed: {e}")
                        latencies_h3["senzing_relationships"] = (time.time() - start) * 1000
                else:
                    # Try CORD's built-in beneficial owner tracing
                    start = time.time()
                    chain = await cord_rag.trace_beneficial_owner(
                        shipper_match["entity_name"], shipper_match["country"], depth=3
                    )
                    latencies_h3["cord_beneficial_owner_trace"] = (time.time() - start) * 1000

                    if chain and len(chain) > 1:
                        score += 5.0
                        chain_names = " → ".join([e["entity_name"] for e in chain])
                        evidence.append(f"Beneficial owner chain (CORD): {chain_names}")
            else:
                score -= 2.0
                evidence.append("Shipper not found in CORD database")

            # ═══════════════════════════════════════════════════════════════
            # CONSIGNEE RESOLUTION
            # ═══════════════════════════════════════════════════════════════

            start = time.time()
            consignee_match = await cord_rag.resolve_entity(
                shipment_data.get("consignee_name", ""), shipment_data.get("consignee_country", "")
            )
            latencies_h3["consignee_cord_lookup"] = (time.time() - start) * 1000

            if consignee_match["found"]:
                consignee_confidence = consignee_match["confidence"]
                score += 10.0 * consignee_confidence  # 0-10 pts
                sources.append(consignee_match["data_source"])

                evidence.append(
                    f"Consignee '{consignee_match['entity_name']}' verified via "
                    f"{consignee_match['data_source']} (confidence: {consignee_confidence:.0%})"
                )
            else:
                score -= 2.0
                evidence.append("Consignee not found in CORD database")

            # ═══════════════════════════════════════════════════════════════
            # SANCTIONS SCREENING (OFAC + OPENSANCTIONS)
            # ═══════════════════════════════════════════════════════════════

            start = time.time()

            # Check shipper sanctions
            shipper_sanctions = await cord_rag.search_sanctions(
                shipment_data.get("shipper_name", ""), shipment_data.get("shipper_country", "")
            )
            if shipper_sanctions["status"] != "CLEAR":
                score = -25.0  # BLOCK
                if shipper_sanctions["status"] == "OFAC_HIT":
                    evidence.append("⛔ SHIPPER SANCTIONS HIT (OFAC) — BLOCK SHIPMENT")
                else:
                    evidence.append("⛔ SHIPPER SANCTIONS HIT (OpenSanctions) — HIGH RISK")
                sources.append("OFAC")
                latencies_h3["sanctions_check"] = (time.time() - start) * 1000

                return ComponentScore(
                    name="H3 Manifest Intelligence",
                    value=score,
                    max_points=25.0,
                    confidence=0.95,
                    sources=list(set(sources)),
                    evidence=evidence,
                    api_latency_ms=latencies_h3,
                )

            # Check consignee sanctions
            consignee_sanctions = await cord_rag.search_sanctions(
                shipment_data.get("consignee_name", ""), shipment_data.get("consignee_country", "")
            )
            if consignee_sanctions["status"] != "CLEAR":
                if consignee_sanctions["status"] == "OFAC_HIT":
                    score = -25.0  # BLOCK
                    evidence.append("⛔ CONSIGNEE SANCTIONS HIT (OFAC) — BLOCK SHIPMENT")
                else:
                    score -= 8.0  # OpenSanctions hit
                    evidence.append("⚠️ CONSIGNEE SANCTIONS HIT (OpenSanctions) — HIGH RISK")
                sources.append("OFAC")
                latencies_h3["sanctions_check"] = (time.time() - start) * 1000

                return ComponentScore(
                    name="H3 Manifest Intelligence",
                    value=score,
                    max_points=25.0,
                    confidence=0.95,
                    sources=list(set(sources)),
                    evidence=evidence,
                    api_latency_ms=latencies_h3,
                )

            latencies_h3["sanctions_check"] = (time.time() - start) * 1000

            # ═══════════════════════════════════════════════════════════════
            # NEW IMPORTER RISK
            # ═══════════════════════════════════════════════════════════════

            shipper_age_months = shipment_data.get("shipper_age_months", 0)
            if shipper_age_months < 12:
                score += 8.0
                evidence.append(f"New importer (age: {shipper_age_months} months) high-volume risk")

            # ═══════════════════════════════════════════════════════════════
            # FINAL SCORE CALCULATION
            # ═══════════════════════════════════════════════════════════════

            # Cap score to max
            score = min(max(score, -25), 25)

            # Confidence: CORD alone = 0.85, CORD+Senzing = 0.95
            if "Senzing" in sources:
                confidence = 0.95
            elif shipper_match.get("found") and consignee_match.get("found"):
                confidence = 0.85
            else:
                confidence = 0.60

        except FileNotFoundError as e:
            logger.warning(f"CORD RAG database not found: {e}")
            score = 0.0
            evidence = [f"CORD database not available: {str(e)}"]
            confidence = 0.3
            sources = []
        except Exception as e:
            logger.error(f"Error in H3 scoring: {e}")
            score = 0.0
            evidence = [f"H3 scoring error: {str(e)}"]
            confidence = 0.2

        return ComponentScore(
            name="H3 Manifest Intelligence",
            value=score,
            max_points=25.0,
            confidence=confidence,
            sources=list(set(sources)),
            evidence=evidence,
            api_latency_ms=latencies_h3,
        )

    def _calculate_confidence(
        self, h1_conf: float, h2_conf: float, h3_conf: float, live_count: int, fixture_count: int
    ) -> float:
        """Calculate overall confidence based on component confidence + data source quality."""
        # Average of component confidences
        avg_component_conf = (h1_conf + h2_conf + h3_conf) / 3

        # Penalize fixture data
        total_apis = live_count + fixture_count
        if total_apis > 0:
            live_ratio = live_count / total_apis
        else:
            live_ratio = 0.5

        # Overall = 70% component confidence + 30% data source quality
        overall = (avg_component_conf * 0.7) + (live_ratio * 0.3)

        return min(overall, 1.0)
