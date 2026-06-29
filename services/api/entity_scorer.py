"""
Entity (H2) scorer — Track T-Score, task C1.

Scores a resolved ACTOR (entity) with the same seven-factor recipe the shipment
scorer uses, emitting a v4.0 ``ScoreBreakdownV4`` with ``subject_type='entity'``.

Scope of this task (C1):
  * The **enforcement-flag** half of the entity Party factor is implemented FULLY
    from entity data: OFAC/sanctions, EAPA respondent, UFLPA listing, fraud/offshore.
  * The **network/shell + cross-corridor reach** half is read from
    ``EntityGraphSignals`` (CT-4) WHEN PROVIDED. When ``signals is None`` a zero
    stub is emitted — this is the documented stub-then-swap seam to Track T-Graph
    (integration barrier I-2). Swap the stub by passing a real
    ``GraphSignalProvider.signals_for(entity_id)`` result; no scorer code changes.

Builds only against the FROZEN contracts in ``v4_contracts.py`` (CT-1, CT-4) and
the ``RiskComponentScore`` shape in ``risk_models.py``. Pure NEW module: it does
not modify any existing file. Decision source:
``docs/precise-risk-model/decisions/DECISION_MULTI_LEVEL_FACTOR_SCORING.md`` §3-4.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from v4_contracts import (
    ScoreBreakdownV4,
    EntityGraphSignals,
    FACTORS,
    EAPA_SOURCE,
    UFLPA_SOURCE,
    IDENTITY_ONLY_SOURCES,
)

try:  # reuse the frozen 7-factor component shape (CT-1)
    from risk_models import RiskComponentScore
except Exception:  # pragma: no cover - fall back to the contract's own copy
    from v4_contracts import RiskComponentScore


# --- Source / flag vocabulary (mirrors cord_engine record schema) -------------
OFAC_SOURCE = "OFAC"
OPEN_SANCTIONS_SOURCE = "OPEN-SANCTIONS"
ICIJ_SOURCE = "ICIJ"
NOMINO_RISK_SOURCE = "NOMINO-RISK"

SANCTIONS_SOURCES = (OFAC_SOURCE, OPEN_SANCTIONS_SOURCE)
FRAUD_OFFSHORE_SOURCES = (ICIJ_SOURCE, NOMINO_RISK_SOURCE)

EAPA_FLAG = "eapa_respondent"
UFLPA_FLAG = "uflpa_listed"

# --- Enforcement-flag component weights (Party factor; tuned/pinned later) -----
# Weights are on the 0-100 percent scale used by RiskComponentScore. The
# enforcement flags dominate the Party factor (decision §3, row "Party → H2").
W_OFAC = 22.0
W_EAPA = 22.0   # EAPA is the anchor flag of the entire entity model (§7)
W_UFLPA = 18.0
W_FRAUD = 12.0
# Network/shell + reach weights (filled from graph signals, stub-zero otherwise).
W_SHELL = 12.0
W_CENTRALITY = 8.0
W_REACH = 6.0

# Tier thresholds on the 0-100 final score.
TIER_CRITICAL = 80.0
TIER_HIGH = 60.0
TIER_MEDIUM = 40.0


def _component(
    component: str,
    factor: str,
    score: float,
    weight: float,
    rationale: str,
    evidence: Optional[List[str]] = None,
) -> RiskComponentScore:
    """Build a RiskComponentScore with weighted_result = score * weight / 10."""
    score = max(0.0, min(10.0, float(score)))
    return RiskComponentScore(
        component=component,
        factor=factor,
        score=score,
        weight=weight,
        weighted_result=score * weight / 10.0,
        rationale=rationale,
        evidence=evidence or [],
    )


def _raw(entity: Dict[str, Any]) -> Dict[str, Any]:
    raw = entity.get("raw_data") or entity.get("raw_record") or {}
    return raw if isinstance(raw, dict) else {}


def _data_source(entity: Dict[str, Any]) -> str:
    return str(entity.get("data_source") or _raw(entity).get("DATA_SOURCE") or "").strip()


def _flag(entity: Dict[str, Any]) -> str:
    raw = _raw(entity)
    return str(entity.get("flag") or raw.get("FLAG") or "").strip().lower()


def _subject_id(entity: Dict[str, Any]) -> str:
    return str(
        entity.get("entity_id")
        or entity.get("id")
        or _raw(entity).get("RECORD_ID")
        or entity.get("name")
        or "unknown-entity"
    )


# --- Enforcement-flag components (FULLY implemented from entity data) ----------
def _enforcement_components(entity: Dict[str, Any]) -> List[RiskComponentScore]:
    """The enforcement-flag half of the entity Party factor.

    Each flag is a Party RiskComponentScore. Only flags that fire are emitted so
    a benign entity carries no enforcement weight (and stays LOW)."""
    src = _data_source(entity)
    raw = _raw(entity)
    flag = _flag(entity)
    name = entity.get("name") or _subject_id(entity)
    out: List[RiskComponentScore] = []

    # OFAC / sanctions ---------------------------------------------------------
    sdn_program = raw.get("SDN_PROGRAM")
    if src in SANCTIONS_SOURCES or sdn_program:
        prog = f" (program {sdn_program})" if sdn_program else ""
        out.append(_component(
            component="OFAC / Sanctions Exposure",
            factor="Party",
            score=9.5,
            weight=W_OFAC,
            rationale=f"Entity '{name}' appears on a sanctions source ({src or 'OFAC'}){prog}.",
            evidence=[e for e in (
                f"data_source={src}" if src else None,
                f"SDN_PROGRAM={sdn_program}" if sdn_program else None,
            ) if e],
        ))

    # EAPA respondent ----------------------------------------------------------
    if src == EAPA_SOURCE or flag == EAPA_FLAG:
        out.append(_component(
            component="EAPA Respondent",
            factor="Party",
            score=9.0,
            weight=W_EAPA,
            rationale=f"Entity '{name}' is a CBP-EAPA respondent (anchor enforcement flag).",
            evidence=[e for e in (
                f"data_source={src}" if src == EAPA_SOURCE else None,
                f"FLAG={EAPA_FLAG}" if flag == EAPA_FLAG else None,
                f"DOCKET={raw.get('DOCKET')}" if raw.get("DOCKET") else None,
            ) if e],
        ))

    # UFLPA Entity List --------------------------------------------------------
    if src == UFLPA_SOURCE or flag == UFLPA_FLAG:
        out.append(_component(
            component="UFLPA Entity List",
            factor="Party",
            score=8.5,
            weight=W_UFLPA,
            rationale=f"Entity '{name}' is on the DHS UFLPA Entity List (forced-labor presumption).",
            evidence=[e for e in (
                f"data_source={src}" if src == UFLPA_SOURCE else None,
                f"FLAG={UFLPA_FLAG}" if flag == UFLPA_FLAG else None,
            ) if e],
        ))

    # Fraud / offshore ---------------------------------------------------------
    if src in FRAUD_OFFSHORE_SOURCES:
        riskcode = raw.get("riskcode") or raw.get("RISKCODE")
        out.append(_component(
            component="Fraud / Offshore Exposure",
            factor="Party",
            score=7.0,
            weight=W_FRAUD,
            rationale=f"Entity '{name}' appears in offshore/fraud-risk data ({src}).",
            evidence=[e for e in (
                f"data_source={src}",
                f"riskcode={riskcode}" if riskcode else None,
            ) if e],
        ))

    return out


# --- Network / shell + reach components (graph signals; stub seam to T-Graph) --
def _graph_components(
    entity: Dict[str, Any], signals: Optional[EntityGraphSignals]
) -> List[RiskComponentScore]:
    """Network/shell + cross-corridor reach half of the entity score.

    >>> STUB-THEN-SWAP SEAM (integration barrier I-2 to Track T-Graph) <<<
    When ``signals is None`` we emit ZERO-scored placeholder components so the
    breakdown shape is stable and the enforcement-flag half scores on its own.
    T-Graph swaps the stub by supplying a real ``EntityGraphSignals`` (produced
    by ``GraphSignalProvider.signals_for(entity_id)``, CT-4) — no change here.
    """
    name = entity.get("name") or _subject_id(entity)

    if signals is None:
        # --- STUB: graph signals not yet wired. Zero contribution. ---
        stub_note = "STUB: awaiting T-Graph GraphSignalProvider.signals_for() (I-2)."
        return [
            _component("Network / Shell Indicator", "Party", 0.0, W_SHELL,
                       f"{stub_note} No shell signal for '{name}'.",
                       evidence=["graph_signals=None"]),
            _component("Network Centrality (hub)", "Party", 0.0, W_CENTRALITY,
                       f"{stub_note} No centrality signal for '{name}'.",
                       evidence=["graph_signals=None"]),
            _component("Cross-Corridor Reach", "Pattern", 0.0, W_REACH,
                       f"{stub_note} No corridor-reach signal for '{name}'.",
                       evidence=["graph_signals=None"]),
        ]

    # --- REAL: scale 0-1 graph signals onto the 0-10 component scale. ---
    shell = max(0.0, min(1.0, signals.shell_indicator))
    centrality = max(0.0, min(1.0, signals.centrality))
    reach_degree = signals.corridor_degree + signals.resolved_degree
    # >=5 distinct corridors saturates the reach component.
    reach = min(1.0, reach_degree / 5.0)

    return [
        _component(
            "Network / Shell Indicator", "Party", shell * 10.0, W_SHELL,
            f"Shell likelihood {shell:.2f} for '{name}' "
            f"(shared address/identifier + newness).",
            evidence=[
                f"shell_indicator={shell:.3f}",
                f"shared_identifier_count={signals.shared_identifier_count}",
            ],
        ),
        _component(
            "Network Centrality (hub)", "Party", centrality * 10.0, W_CENTRALITY,
            f"Graph hub score {centrality:.2f} for '{name}'.",
            evidence=[f"centrality={centrality:.3f}"],
        ),
        _component(
            "Cross-Corridor Reach", "Pattern", reach * 10.0, W_REACH,
            f"Spans {reach_degree} corridor(s) "
            f"({signals.corridor_degree} explicit + {signals.resolved_degree} resolved).",
            evidence=[
                f"corridor_degree={signals.corridor_degree}",
                f"resolved_degree={signals.resolved_degree}",
                f"corridors={signals.corridors}",
            ],
        ),
    ]


def _tier(final_score: float) -> str:
    if final_score >= TIER_CRITICAL:
        return "CRITICAL"
    if final_score >= TIER_HIGH:
        return "HIGH"
    if final_score >= TIER_MEDIUM:
        return "MEDIUM"
    return "LOW"


def _is_identity_only(entity: Dict[str, Any]) -> bool:
    """A3: an entity whose ONLY signal is an identity-resolution source
    (NPI-PROVIDERS / GLOBALDATA) must not be scored as risky."""
    src = _data_source(entity)
    return src in IDENTITY_ONLY_SOURCES


def score_entity(
    entity: Dict[str, Any],
    signals: Optional[EntityGraphSignals] = None,
) -> ScoreBreakdownV4:
    """Score a resolved entity (H2 actor) → ScoreBreakdownV4(subject_type='entity').

    Args:
        entity: a CORD-style entity record (``data_source``, ``name``,
            ``raw_data`` carrying ``SDN_PROGRAM``/``FLAG``/etc.).
        signals: optional ``EntityGraphSignals`` from T-Graph. ``None`` → stub.
    """
    subject_id = _subject_id(entity)

    # A3 — identity-only sources never score as risky. Emit a single LOW marker
    # component and short-circuit (no enforcement / graph contribution).
    if _is_identity_only(entity):
        src = _data_source(entity)
        marker = _component(
            component="Identity-Resolution Only (A3)",
            factor="Party",
            score=0.0,
            weight=0.0,
            rationale=(
                f"Source {src} is identity-resolution mass only "
                f"(IDENTITY_ONLY_SOURCES); excluded from trade scoring per A3."
            ),
            evidence=[f"data_source={src}"],
        )
        return ScoreBreakdownV4(
            subject_id=subject_id,
            subject_type="entity",
            components=[marker],
            subtotal=0.0,
            final_score=0.0,
            tier="LOW",
            horizon_links={"incoming": []},
        )

    components: List[RiskComponentScore] = []
    components.extend(_enforcement_components(entity))
    components.extend(_graph_components(entity, signals))

    subtotal = sum(c.weighted_result for c in components)
    # weighted_result is already on the 0-100 contribution scale
    # (score[0-10] * weight%[0-100] / 10). Clamp to a 0-100 final score.
    final_score = max(0.0, min(100.0, subtotal))
    tier = _tier(final_score)

    return ScoreBreakdownV4(
        subject_id=subject_id,
        subject_type="entity",
        components=components,
        subtotal=subtotal,
        final_score=final_score,
        tier=tier,
        # H3 bridge placeholder: the manifest/incoming link (time factor → 72h
        # arrivals) is filled by the H3 manifest bridge in a later task.
        horizon_links={"incoming": []},
    )
