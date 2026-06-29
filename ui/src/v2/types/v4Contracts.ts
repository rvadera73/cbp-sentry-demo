/**
 * Risk Model v4.0 — FROZEN UI-facing contracts (Step 0 / CT-1 + CT-6).
 *
 * T-Experience (H2 UI + referral) builds against these with fixtures until real
 * scores land (integration barrier I-3). Mirrors services/api/v4_contracts.py.
 * Design source of truth:
 *   docs/precise-risk-model/decisions/DECISION_MULTI_LEVEL_FACTOR_SCORING.md
 *
 * Contracts only — no logic.
 */

export type SubjectType = 'shipment' | 'corridor' | 'entity';

export const V4_FACTORS = ['Documentation', 'Commodity', 'Routing', 'Party', 'Corridor', 'Pattern', 'Time'] as const;
export type V4Factor = typeof V4_FACTORS[number];

/** One factor's contribution (mirrors RiskComponentScore). */
export interface ScoreComponentV4 {
  component: string;
  factor: V4Factor | string;
  score: number;          // 0-10
  weight: number;         // 0-100
  weighted_result: number;
  rationale: string;
  evidence?: string[];
}

export interface ScoreProvenanceV4 {
  model_version: string;
  cord_resolution_version: string;
  inputs_hash: string;
  computed_at: string;    // ISO-8601
}

/** CT-1 — one score, any level (shipment | corridor | entity). */
export interface ScoreBreakdownV4 {
  subject_id: string;
  subject_type: SubjectType;
  components: ScoreComponentV4[];
  subtotal: number;
  final_score: number;
  tier: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | string;
  confidence_interval?: string;
  /** Horizon bridges: factor -> ids it points at (party -> entity ids, time -> manifest ids). */
  horizon_links?: Record<string, string[]>;
  provenance?: ScoreProvenanceV4;
}

/* ---- CT-6: referral evidence blocks rendered from the entity score ---- */

/** Referral §3-10 — per-entity risk. */
export interface EntityFactorBlockV4 {
  entity_id: string;
  name: string;
  score: ScoreBreakdownV4;
  ofac: { listed: boolean; program?: string };
  eapa: { listed: boolean; dockets?: string[] };
  uflpa: { listed: boolean };
}

export interface NetworkEvidenceEdgeV4 {
  src: string;
  dst: string;
  type: string;
  evidence: string;
  confidence: number;
}

/** Referral §3-5a — entity network evidence. */
export interface NetworkEvidenceBlockV4 {
  root_entity_id: string;
  edges: NetworkEvidenceEdgeV4[];
  cross_corridor_reach: number;          // explicit degree
  resolved_vs_explicit_delta: number;    // reach added by resolution
}
