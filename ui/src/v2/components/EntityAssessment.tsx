/** Entity assessment & recommendation — bottom of the workspace, outside the
 * tabs (mirrors CorridorAssessment in Shipment Intelligence). */
import React from 'react';
import { Gavel } from 'lucide-react';
import { Panel, SectionHeader, StatusPill } from '../../components/ui';
import { EntityDetail, entityRisk } from '../services/cordApi';

const riskColor = (s: number) => (s >= 80 ? '#D83933' : s >= 60 ? '#C7791B' : s >= 40 ? '#B8860B' : '#15803D');

export default function EntityAssessment({ detail, scoreBreakdown }: { detail: EntityDetail | null; scoreBreakdown?: any | null }) {
  if (!detail) return null;
  const heur = entityRisk(detail);
  const score = scoreBreakdown ? Math.round(scoreBreakdown.final_score) : heur.score;
  const tier = scoreBreakdown ? String(scoreBreakdown.tier) : heur.tier;
  // Rationale from the real fired components when available, else heuristic signals.
  const signals: string[] = scoreBreakdown
    ? (scoreBreakdown.components || [])
        .filter((c: any) => (c.weighted_result || 0) > 0)
        .sort((a: any, b: any) => (b.weighted_result || 0) - (a.weighted_result || 0))
        .slice(0, 4)
        .map((c: any) => c.rationale || c.component)
    : heur.signals;
  const recommendation =
    tier === 'CRITICAL' ? 'Block & refer for enforcement action'
      : tier === 'HIGH' ? 'Enhanced due diligence before clearance'
        : tier === 'MEDIUM' ? 'Targeted manual review'
          : 'Routine processing — monitor';
  const rationale =
    (signals.length ? signals.join('; ') + '.' : 'No adverse signals resolved from CORD.') +
    ` Resolved risk ${score}/100 (${tier} tier).`;
  return (
    <Panel className="border-l-4" style={{ borderLeftColor: riskColor(score) }}>
      <SectionHeader
        title="Assessment & Recommendation"
        icon={<Gavel className="w-4 h-4" />}
        action={<StatusPill status={tier.toLowerCase()} />}
      />
      <div className="flex items-center gap-3 mb-1.5">
        <span className="text-[11px] font-bold uppercase tracking-wide text-[#5C5C5C]">Recommended action</span>
        <span className="text-[13px] font-bold" style={{ color: riskColor(score) }}>{recommendation}</span>
      </div>
      <p className="text-[12px] text-[#0B1F33] leading-snug">{rationale}</p>
    </Panel>
  );
}
