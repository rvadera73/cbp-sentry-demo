"""
Risk Model v4.0 — FROZEN interface contracts (Step 0 / CT-1..CT-5).

These are the interfaces every v4.0 track builds against. They are deliberately
small and stable: each track (T-Data, T-Graph, T-Score, T-MLOps, T-Experience)
depends on THESE shapes, not on another track's implementation — so the tracks
build in parallel against stubs/fixtures and integrate by swapping stubs for the
real producers (integration barriers I-1..I-4).

Design source of truth:
  docs/precise-risk-model/decisions/DECISION_MULTI_LEVEL_FACTOR_SCORING.md
  docs/precise-risk-model/implementation/V4_0_MULTI_LEVEL_SCORING_IMPLEMENTATION_PLAN.md

RULE: contracts only — NO business logic here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

try:  # reuse the existing 7-factor component shape so all levels match (CT-1)
    from risk_models import RiskComponentScore
except Exception:  # pragma: no cover - allow import in isolation/tooling
    @dataclass
    class RiskComponentScore:  # type: ignore
        component: str
        factor: str
        score: float
        weight: float
        weighted_result: float
        rationale: str
        evidence: Optional[List[str]] = None

        def to_dict(self) -> Dict[str, Any]:
            return {
                "component": self.component, "factor": self.factor,
                "score": round(self.score, 1), "weight": round(self.weight, 1),
                "weighted_result": round(self.weighted_result, 1),
                "rationale": self.rationale, "evidence": self.evidence or [],
            }

# Subjects a v4.0 score can describe.
SUBJECT_TYPES = ("shipment", "corridor", "entity")

# The seven shared factors (same recipe at every level).
FACTORS = ("Documentation", "Commodity", "Routing", "Party", "Corridor", "Pattern", "Time")

# Locked rules (decision record §4).
AGGREGATION_RULE = "top_k_blend"      # party-risk factor over actors in a lane
AGGREGATION_K = 5
APPORTIONMENT_RULE = "by_shipment_count"  # cross-corridor actor risk split

EAPA_SOURCE = "CBP-EAPA"
UFLPA_SOURCE = "UFLPA-ENTITY-LIST"
# Sources kept for identity resolution only — excluded from trade scoring (A3).
IDENTITY_ONLY_SOURCES = ("NPI-PROVIDERS", "GLOBALDATA")


# --- CT-5: provenance stamped on every stored score --------------------------
@dataclass
class ScoreProvenance:
    model_version: str
    cord_resolution_version: str
    inputs_hash: str
    computed_at: str  # ISO-8601

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_version": self.model_version,
            "cord_resolution_version": self.cord_resolution_version,
            "inputs_hash": self.inputs_hash,
            "computed_at": self.computed_at,
        }


# --- CT-1: multi-level score breakdown (shipment | corridor | entity) --------
@dataclass
class ScoreBreakdownV4:
    subject_id: str
    subject_type: str  # one of SUBJECT_TYPES
    components: List[RiskComponentScore]
    subtotal: float
    final_score: float = 0.0
    tier: str = ""  # CRITICAL | HIGH | MEDIUM | LOW
    confidence_interval: str = ""
    # Horizon bridges: factor -> ids it points at (party -> entity ids, time -> manifest ids).
    horizon_links: Dict[str, List[str]] = field(default_factory=dict)
    provenance: Optional[ScoreProvenance] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject_id": self.subject_id,
            "subject_type": self.subject_type,
            "components": [c.to_dict() for c in self.components],
            "subtotal": round(self.subtotal, 1),
            "final_score": round(self.final_score, 1),
            "tier": self.tier,
            "confidence_interval": self.confidence_interval,
            "horizon_links": self.horizon_links,
            "provenance": self.provenance.to_dict() if self.provenance else None,
        }


# --- CT-2: entity_edges (resolved-entity graph substrate) --------------------
EDGE_TYPES = (
    "shared_address", "shared_identifier", "ownership",
    "officer", "forwarder", "eapa_anchor", "same_as",
)


@dataclass
class EntityEdge:
    src_entity_id: str
    dst_entity_id: str
    edge_type: str  # one of EDGE_TYPES
    evidence: str   # human-readable "why connected"
    confidence: float  # 0-1
    source: str     # dataset that produced the edge

    def to_dict(self) -> Dict[str, Any]:
        return {
            "src_entity_id": self.src_entity_id, "dst_entity_id": self.dst_entity_id,
            "edge_type": self.edge_type, "evidence": self.evidence,
            "confidence": round(self.confidence, 3), "source": self.source,
        }


ENTITY_EDGES_DDL = """
CREATE SCHEMA IF NOT EXISTS risk_scoring;
CREATE TABLE IF NOT EXISTS risk_scoring.entity_edges (
    id            BIGSERIAL PRIMARY KEY,
    src_entity_id TEXT NOT NULL,
    dst_entity_id TEXT NOT NULL,
    edge_type     TEXT NOT NULL,
    evidence      TEXT,
    confidence    REAL CHECK (confidence >= 0 AND confidence <= 1),
    source        TEXT,
    created_at    TIMESTAMPTZ DEFAULT now(),
    UNIQUE (src_entity_id, dst_entity_id, edge_type)
);
CREATE INDEX IF NOT EXISTS idx_entity_edges_src ON risk_scoring.entity_edges(src_entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_edges_dst ON risk_scoring.entity_edges(dst_entity_id);
""".strip()


# --- CT-3: CORD source records for the two missing flag sources --------------
# Shaped to index/resolve like any other CORD source.
@dataclass
class CordFlagRecord:
    DATA_SOURCE: str       # EAPA_SOURCE | UFLPA_SOURCE
    RECORD_ID: str
    PRIMARY_NAME_ORG: str
    COUNTRY: str = ""
    FLAG: str = ""         # eapa_respondent | uflpa_listed
    DOCKET: str = ""       # EAPA docket / UFLPA listing reference
    COMMODITY: str = ""    # HS code / commodity
    ROUTE: str = ""        # corridor route, e.g. "CN->VN->US"

    def to_record(self) -> Dict[str, Any]:
        return {
            "DATA_SOURCE": self.DATA_SOURCE, "RECORD_ID": self.RECORD_ID,
            "RECORD_TYPE": "ORGANIZATION", "PRIMARY_NAME_ORG": self.PRIMARY_NAME_ORG,
            "COUNTRY": self.COUNTRY, "FLAG": self.FLAG, "DOCKET": self.DOCKET,
            "COMMODITY": self.COMMODITY, "ROUTE": self.ROUTE,
        }


# --- CT-4: graph signals (produced by T-Graph, consumed by T-Score) ----------
@dataclass
class EntityGraphSignals:
    entity_id: str
    corridor_degree: int = 0       # cross-corridor reach, explicit (manifest-visible)
    resolved_degree: int = 0       # extra reach revealed by resolution (resolved - explicit)
    centrality: float = 0.0        # hub score 0-1
    shell_indicator: float = 0.0   # 0-1 shell likelihood (shared addr/id + newness)
    shared_identifier_count: int = 0
    corridors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "corridor_degree": self.corridor_degree,
            "resolved_degree": self.resolved_degree,
            "centrality": round(self.centrality, 3),
            "shell_indicator": round(self.shell_indicator, 3),
            "shared_identifier_count": self.shared_identifier_count,
            "corridors": self.corridors,
        }


# --- CT-4 / CT-5: Protocols the tracks implement (enables stub-then-swap) -----
@runtime_checkable
class GraphSignalProvider(Protocol):
    """T-Graph implements; T-Score consumes. Stub returns zeros until B1/B3 land."""
    def signals_for(self, entity_id: str) -> EntityGraphSignals: ...
    def edges_for(self, entity_id: str) -> List[EntityEdge]: ...


@runtime_checkable
class ScoreStore(Protocol):
    """CT-5 read + propagation surface. invalidate() triggers recompute upstream."""
    def get_score(self, subject_type: str, subject_id: str) -> Optional[ScoreBreakdownV4]: ...
    def put_score(self, score: ScoreBreakdownV4) -> None: ...
    def invalidate(self, subject_type: str, subject_id: str) -> None: ...
