/**
 * v4.0 Corridor Risk (H1) — calls the live POST /api/cord/corridor/score endpoint
 * with the selected corridor + parties assembled from its shipments' manifest
 * data, and renders the factor-attributed ScoreBreakdownV4 using the shared kit
 * (Panel / SectionHeader / StatusPill / ScoreBar). Degrades to nothing on null.
 */
import React, { useEffect, useState } from 'react';
import { Gauge } from 'lucide-react';
import { Panel, SectionHeader, StatusPill, ScoreBar } from '../../components/ui';
import { cordCorridorScore, CordParty } from '../services/cordApi';
import type { ScoreBreakdownV4 } from '../types/v4Contracts';

const riskColor = (s: number) => (s >= 80 ? '#D83933' : s >= 60 ? '#C7791B' : s >= 40 ? '#B8860B' : '#15803D');

interface Props { corridor?: any; shipments?: any[] }

/** Collect shipper + consignee names from manifest data, counting how many
 * shipments each distinct name appears on. */
function assembleParties(shipments: any[]): CordParty[] {
  const counts = new Map<string, number>();
  for (const s of shipments) {
    const md = s?.manifest_data || {};
    for (const name of [md.shipper, md.consignee]) {
      const n = (name || '').trim();
      if (!n) continue;
      counts.set(n, (counts.get(n) || 0) + 1);
    }
  }
  return Array.from(counts.entries()).map(([name, shipment_count]) => ({ name, shipment_count }));
}

export default function CorridorRiskScoreV4({ corridor, shipments = [] }: Props) {
  const [score, setScore] = useState<ScoreBreakdownV4 | null>(null);

  useEffect(() => {
    let active = true;
    if (!corridor) { setScore(null); return; }
    const parties = assembleParties(shipments);
    cordCorridorScore(corridor, parties).then(s => { if (active) setScore(s); });
    return () => { active = false; };
  }, [corridor, shipments]);

  if (!score) return null;

  const final = Math.round(score.final_score);

  return (
    <Panel className="border-l-4" style={{ borderLeftColor: riskColor(final) }}>
      <SectionHeader
        title="v4.0 Corridor Risk"
        icon={<Gauge className="w-4 h-4" />}
        action={<StatusPill status={score.tier} />}
      />
      <div className="flex items-baseline gap-2 mb-3">
        <span className="text-[28px] font-black font-mono leading-none" style={{ color: riskColor(final) }}>{final}</span>
        <span className="text-[11px] text-[#5C5C5C]">/100 final score</span>
      </div>
      <div>
        {score.components.map((c, i) => (
          <ScoreBar
            key={i}
            label={c.component}
            sublabel={`${c.factor} · weight ${c.weight}%`}
            score={Math.round(c.score * 10)}
          />
        ))}
      </div>
    </Panel>
  );
}
