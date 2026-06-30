/**
 * Corridor-level Assessment & Recommendation — shown outside the tabs (below
 * the tab content), so the analyst always sees the conclusion for the selected
 * corridor regardless of which tab is active.
 *
 * Single source of truth: when the factor-model corridor score is available
 * (modelScore/modelTier, lifted from CorridorRiskScoreV4), THAT drives the tier
 * and recommendation. The shipment-average risk is demoted to a clearly labeled
 * secondary stat ("Shipment-average risk (legacy)") so it no longer competes as
 * a second, conflicting "corridor risk" number.
 */
import React from 'react';
import { Gavel } from 'lucide-react';
import { Panel, SectionHeader, StatusPill } from '../../components/ui';

const riskColor = (s: number) => (s >= 80 ? '#D83933' : s >= 60 ? '#C7791B' : s >= 40 ? '#B8860B' : '#15803D');

interface Props {
  corridor?: any;
  shipments?: any[];
  /** Factor-model corridor risk (single source of truth). */
  modelScore?: number | null;
  modelTier?: string | null;
}

export default function CorridorAssessment({ corridor, shipments = [], modelScore = null, modelTier = null }: Props) {
  // Legacy secondary stat: average of shipments' synthetic risk_score.
  const avgRisk = shipments.length
    ? Math.round(shipments.reduce((s, x) => s + (x.risk_score || 0), 0) / shipments.length)
    : Math.round(corridor?.avg_risk_score || 50);

  const hasModel = modelScore != null && Number.isFinite(modelScore);
  // Headline = factor model when present; otherwise fall back to shipment avg.
  const headline = hasModel ? Math.round(modelScore as number) : avgRisk;
  const tier = (hasModel && modelTier)
    ? modelTier.toUpperCase()
    : headline >= 80 ? 'CRITICAL' : headline >= 60 ? 'HIGH' : headline >= 40 ? 'MEDIUM' : 'LOW';

  const flags = [
    shipments.some(s => s.element9_is_mismatch) && 'ISF Element 9 mismatch',
    shipments.some(s => s.manifest_anomalies?.includes('DWELL_ANOMALY')) && 'dwell-time anomaly',
    shipments.some(s => !s.manifest_data?.bill_of_lading) && 'missing documentation',
  ].filter(Boolean) as string[];

  const recommendation =
    tier === 'CRITICAL' || (tier === 'HIGH' && flags.length >= 2) ? 'Refer for examination'
    : tier === 'HIGH' || flags.length >= 1 ? 'Enhanced screening'
    : tier === 'MEDIUM' ? 'Targeted review'
    : 'Routine processing';

  const rationale =
    (hasModel
      ? `Corridor risk ${headline}/100 (${tier}) from the factor model. `
      : `Corridor risk ${headline}/100 (${tier}). `) +
    (flags.length ? `Flagged signals: ${flags.join(', ')}.` : 'No corridor-level anomaly signals flagged.') +
    ` Based on ${shipments.length} shipment(s) in scope.`;

  return (
    <Panel className="border-l-4" style={{ borderLeftColor: riskColor(headline) }}>
      <SectionHeader title="Assessment & Recommendation" icon={<Gavel className="w-4 h-4" />} action={<StatusPill status={tier.toLowerCase()} />} />
      <div className="flex items-center gap-3 mb-1">
        <span className="text-[11px] font-bold uppercase tracking-wide text-[#5C5C5C]">Recommended action</span>
        <span className="text-[13px] font-bold" style={{ color: riskColor(headline) }}>{recommendation}</span>
      </div>
      <p className="text-[12px] text-[#0B1F33] leading-snug">{rationale}</p>
      {hasModel && (
        <p className="text-[10px] text-[#8C8C8C] mt-1">
          Shipment-average risk (legacy): {avgRisk}/100 — secondary signal only, not the corridor risk.
        </p>
      )}
    </Panel>
  );
}
