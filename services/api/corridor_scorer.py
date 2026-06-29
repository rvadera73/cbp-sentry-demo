"""
Corridor (H1) scorer — Track T-Score, tasks C2 + C3.

Scores a CORRIDOR with the same seven-factor recipe as the shipment/entity
scorers, emitting a v4.0 ``ScoreBreakdownV4`` with ``subject_type='corridor'``.

The **Party** factor is the locked **top-k blend** (k=5) over the entity scores
of the actors operating in the lane, **apportioned by shipment count** (locked
rule) — this is the H1<->H2 bridge (decision record §3 row "Party", §4). The
Commodity / Routing / Pattern / Time factors come from corridor metadata.

C3 graph accounting: an actor's contribution to the corridor Party factor is an
edge weight (its share of the corridor's shipments); the corridor score is the
node aggregate. The actor keeps its own global entity score unchanged.

Builds only against the FROZEN contracts in ``v4_contracts.py`` (CT-1) and the
``RiskComponentScore`` shape. Pure NEW module — modifies nothing else.
Decision source: docs/precise-risk-model/decisions/DECISION_MULTI_LEVEL_FACTOR_SCORING.md
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from v4_contracts import ScoreBreakdownV4, AGGREGATION_K

try:  # reuse the frozen 7-factor component shape (CT-1)
    from risk_models import RiskComponentScore
except Exception:  # pragma: no cover
    from v4_contracts import RiskComponentScore


# --- Corridor factor weights (provisional; pinned at D2 calibration) ----------
W_PARTY = 30.0      # prevalent flagged actors in the lane (top-k blend) — H2 bridge
W_COMMODITY = 22.0  # AD/CVD / Section 301 / UFLPA exposure on the lane commodity
W_ROUTING = 20.0    # transshipment / origin-concealment risk of the route
W_PATTERN = 14.0    # lane anomaly density
W_TIME = 14.0       # incoming pressure (72h arrivals) — H3 bridge

TIER_CRITICAL = 80.0
TIER_HIGH = 60.0
TIER_MEDIUM = 40.0

# High-risk transshipment hubs (origin-concealment routes).
_TRANSSHIP_HUBS = {"VN", "MY", "TH", "KH", "ID", "TW", "HK", "LA", "BD"}
_DUTY_SEVERITY = {  # duty type -> 0-10 commodity exposure contribution
    "UFLPA": 10.0, "AD/CVD": 9.0, "ADCVD": 9.0, "AD": 8.5, "CVD": 8.5,
    "SECTION 301": 7.0, "301": 7.0, "SECTION 232": 6.5,
}


def _component(component: str, factor: str, score: float, weight: float,
               rationale: str, evidence: Optional[List[str]] = None) -> RiskComponentScore:
    score = max(0.0, min(10.0, float(score)))
    return RiskComponentScore(
        component=component, factor=factor, score=score, weight=weight,
        weighted_result=score * weight / 10.0, rationale=rationale, evidence=evidence or [],
    )


def _tier(s: float) -> str:
    if s >= TIER_CRITICAL:
        return "CRITICAL"
    if s >= TIER_HIGH:
        return "HIGH"
    if s >= TIER_MEDIUM:
        return "MEDIUM"
    return "LOW"


def top_k_blend(values: List[float], k: int = AGGREGATION_K,
                weights: Optional[List[float]] = None) -> float:
    """LOCKED aggregation rule. Weighted blend of the k highest values — captures
    both 'one very bad actor damns the lane' and 'systemic prevalence' without the
    unbounded inflation of a plain sum. ``weights`` (e.g. shipment counts) apportion
    the blend; when absent, linearly decaying weights (k, k-1, ...) are used."""
    if not values:
        return 0.0
    paired = sorted(zip(values, weights or [1.0] * len(values)), key=lambda p: p[0], reverse=True)[:k]
    vals = [v for v, _ in paired]
    ws = [max(0.0, w) for _, w in paired]
    if sum(ws) <= 0:
        ws = [k - i for i in range(len(vals))]  # decaying fallback
    return sum(v * w for v, w in zip(vals, ws)) / sum(ws)


def _commodity_exposure(corridor: Dict[str, Any]) -> Tuple[float, List[str]]:
    duties = corridor.get("applicable_duties") or []
    best = 0.0
    ev: List[str] = []
    for d in duties:
        dt = str(d.get("duty_type") or d.get("type") or "").upper()
        sev = max((s for key, s in _DUTY_SEVERITY.items() if key in dt), default=4.0)
        best = max(best, sev)
        rate = d.get("rate")
        ev.append(f"{dt or 'duty'}{f' {rate}%' if rate is not None else ''}")
    if not duties and corridor.get("commodity_name"):
        ev.append(f"commodity={corridor.get('commodity_name')}")
    return best, ev


def _routing_risk(corridor: Dict[str, Any]) -> Tuple[float, List[str]]:
    route = str(corridor.get("route") or corridor.get("display_name") or "")
    hops = [h.strip().upper() for h in route.replace("->", " ").replace("→", " ").split() if h.strip()]
    transship = [h for h in hops[1:-1] if h in _TRANSSHIP_HUBS] if len(hops) >= 3 else \
                [h for h in hops if h in _TRANSSHIP_HUBS]
    base = float(corridor.get("corridor_risk_score") or 0) / 10.0  # 0-100 -> 0-10
    score = max(base, 7.5 if transship else base)
    ev = [f"route={route}"] + ([f"transshipment_hub={','.join(transship)}"] if transship else [])
    return min(10.0, score), ev


def score_corridor(
    corridor: Dict[str, Any],
    actor_scores: Optional[List[Tuple[str, float, int]]] = None,
) -> ScoreBreakdownV4:
    """Score a corridor (H1).

    Args:
        corridor: metadata — id / display_name / route, applicable_duties
            [{duty_type, rate}], commodity_name, corridor_risk_score (0-100),
            anomaly_rate (0-1), incoming_count (72h arrivals).
        actor_scores: the resolved actors in the lane as
            ``(name, entity_final_score[0-100], shipment_count)``. Empty -> 0 party.
    """
    actor_scores = actor_scores or []
    cid = str(corridor.get("id") or corridor.get("display_name") or corridor.get("route") or "corridor")
    components: List[RiskComponentScore] = []

    # --- Party factor (H2 bridge): top-k blend over actor entity-scores,
    #     apportioned by shipment count (C3 graph accounting). ---
    party_vals = [esc for (_, esc, _) in actor_scores]
    party_weights = [float(max(1, sc)) for (_, _, sc) in actor_scores]
    party_blend = top_k_blend(party_vals, AGGREGATION_K, party_weights)  # 0-100
    top = sorted(actor_scores, key=lambda x: x[1], reverse=True)[:AGGREGATION_K]
    components.append(_component(
        "Prevalent Flagged Actors", "Party", party_blend / 10.0, W_PARTY,
        f"Top-{AGGREGATION_K} actor-risk blend {party_blend:.0f}/100 over "
        f"{len(actor_scores)} resolved actor(s), apportioned by shipment count.",
        evidence=[f"{n}={esc:.0f}/100 x{sc}shp" for (n, esc, sc) in top] or ["no resolved actors"],
    ))

    # --- Commodity: trade-law exposure on the lane commodity. ---
    comm, comm_ev = _commodity_exposure(corridor)
    components.append(_component(
        "Trade-Law Exposure", "Commodity", comm, W_COMMODITY,
        "Active duty/forced-labor regime on the lane commodity." if comm_ev else "No duty regime on record.",
        comm_ev,
    ))

    # --- Routing: transshipment / origin-concealment risk. ---
    route_score, route_ev = _routing_risk(corridor)
    components.append(_component(
        "Transshipment / Routing Risk", "Routing", route_score, W_ROUTING,
        "Route traverses a known origin-concealment hub." if any("transshipment" in e for e in route_ev)
        else "Corridor baseline routing risk.",
        route_ev,
    ))

    # --- Pattern: lane anomaly density. ---
    anomaly = float(corridor.get("anomaly_rate") or 0.0)
    components.append(_component(
        "Lane Anomaly Density", "Pattern", min(10.0, anomaly * 10.0), W_PATTERN,
        f"Manifest-anomaly rate {anomaly:.0%} across the lane.",
        [f"anomaly_rate={anomaly:.2f}"],
    ))

    # --- Time: incoming pressure (72h arrivals) — H3 bridge. ---
    incoming = int(corridor.get("incoming_count") or 0)
    components.append(_component(
        "Incoming Pressure (72h)", "Time", min(10.0, incoming / 2.0), W_TIME,
        f"{incoming} shipment(s) arriving within 72h on this lane.",
        [f"incoming_count={incoming}"],
    ))

    subtotal = sum(c.weighted_result for c in components)
    final_score = max(0.0, min(100.0, subtotal))
    return ScoreBreakdownV4(
        subject_id=cid,
        subject_type="corridor",
        components=components,
        subtotal=subtotal,
        final_score=final_score,
        tier=_tier(final_score),
        # Horizon bridges: party factor -> the actors (H2); time factor -> the 72h arrivals (H3).
        horizon_links={
            "actors": [n for (n, _, _) in actor_scores],
            "incoming": [],
        },
    )
