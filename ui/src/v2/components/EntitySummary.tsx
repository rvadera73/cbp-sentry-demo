/** Entity-level summary — top of the workspace, outside the tabs (mirrors the
 * corridor summary in Shipment Intelligence). Updates with entity selection. */
import React from 'react';
import { StatStrip, StatusPill } from '../../components/ui';
import { EntityDetail, entityRisk } from '../services/cordApi';

const riskColor = (s: number) => (s >= 80 ? '#D83933' : s >= 60 ? '#C7791B' : s >= 40 ? '#B8860B' : '#15803D');

export default function EntitySummary({ detail, loading }: { detail: EntityDetail | null; loading?: boolean }) {
  if (loading || !detail) {
    return <div className="bg-white border-b border-[#D0D7DE] px-6 py-3 text-[12px] text-[#5C5C5C]">Resolving entity from CORD…</div>;
  }
  const e = detail.entity || {};
  const name = e.name || 'Unknown entity';
  const { score, tier } = entityRisk(detail);
  return (
    <div className="bg-white border-b border-[#D0D7DE] px-6 py-3">
      <div className="flex items-center justify-between mb-2 gap-3">
        <div className="min-w-0">
          <h1 className="text-base font-bold text-[#0B1F33] uppercase tracking-wide truncate">{name}</h1>
          <p className="text-[11px] text-[#5C5C5C]">Entity Resolution · {e.data_source || '—'} · {e.entity_type || 'entity'}</p>
        </div>
        <StatusPill status={tier.toLowerCase()} />
      </div>
      <StatStrip items={[
        { label: 'Risk Score', value: score, color: riskColor(score) },
        { label: 'Risk Tier', value: tier, color: riskColor(score) },
        { label: 'Country', value: (e.country || '—').toUpperCase() },
        { label: 'Source', value: e.data_source || '—' },
        { label: 'Match Conf.', value: e.confidence != null ? `${Math.round(e.confidence * 100)}%` : '—' },
      ]} />
    </div>
  );
}
