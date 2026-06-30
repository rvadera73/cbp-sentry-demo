/**
 * Corridor Risk (H1) — THE single corridor-risk number. Calls the live
 * POST /api/cord/corridor/score endpoint with an ENRICHED corridor (built from
 * the selected corridor + its shipments' manifest data) plus the parties
 * assembled from those shipments, and renders the factor-attributed
 * ScoreBreakdownV4 using the shared kit (Panel / SectionHeader / StatusPill /
 * ScoreBar). Degrades to nothing on null.
 *
 * Enrichment is what lights the Commodity / Routing / Pattern / Time factors —
 * passing the bare corridor (id/display_name/risk_level only) starves them to 0.
 * The computed final_score + tier are lifted to the page via onScore so the top
 * Summary card can show the SAME number (single source of truth).
 */
import React, { useEffect, useState } from 'react';
import { Gauge } from 'lucide-react';
import { Panel, SectionHeader, StatusPill, ScoreBar } from '../../components/ui';
import { cordCorridorScore, CordParty } from '../services/cordApi';
import type { ScoreBreakdownV4 } from '../types/v4Contracts';

const riskColor = (s: number) => (s >= 80 ? '#D83933' : s >= 60 ? '#C7791B' : s >= 40 ? '#B8860B' : '#15803D');

interface Props {
  corridor?: any;
  shipments?: any[];
  /** Lift the computed factor-model score to the page (single source of truth). */
  onScore?: (final_score: number, tier: string) => void;
}

/** Collect shipper + consignee names from manifest data, counting how many
 * shipments each distinct name appears on. */
function assembleParties(shipments: any[]): CordParty[] {
  const counts = new Map<string, number>();
  for (const s of shipments) {
    const md = s?.manifest_data || {};
    for (const name of [md.shipper, md.consignee]) {
      const n = (name || '').trim();
      if (!n || n.toLowerCase() === 'unknown') continue;
      counts.set(n, (counts.get(n) || 0) + 1);
    }
  }
  return Array.from(counts.entries()).map(([name, shipment_count]) => ({ name, shipment_count }));
}

/** Static risk_level -> a 0-100 baseline routing/severity score for the model. */
function levelToScore(level?: string): number {
  switch ((level || '').toUpperCase()) {
    case 'CRITICAL': return 85;
    case 'HIGH': return 65;
    case 'MEDIUM': return 45;
    case 'LOW': return 20;
    default: return 45;
  }
}

/** AD/CVD-style duty inference from a commodity / HS code when the corridor +
 * shipments carry no explicit duty rows (e.g. HS 7604 aluminum, 8541 solar). */
function inferDutiesFromHs(hsCodes: string[], commodityText: string): Array<{ duty_type: string; rate?: number }> {
  const txt = (commodityText || '').toLowerCase();
  const has = (prefix: string) => hsCodes.some(h => (h || '').replace(/\./g, '').startsWith(prefix));
  const out: Array<{ duty_type: string; rate?: number }> = [];
  if (has('7604') || has('7610') || has('7616') || txt.includes('aluminum') || txt.includes('aluminium')) {
    out.push({ duty_type: 'AD/CVD' });
  }
  if (has('8541') || txt.includes('solar') || txt.includes('photovoltaic') || txt.includes('pv ')) {
    out.push({ duty_type: 'AD/CVD' });
    out.push({ duty_type: 'UFLPA' });
  }
  if (has('7306') || has('7307') || has('7210') || has('7213') || txt.includes('steel')) {
    out.push({ duty_type: 'AD/CVD' });
  }
  return out;
}

/** Build the enriched corridor the factor model needs. Pulls real duties from
 * the corridor + shipments first; infers from commodity/HS as a fallback. */
function enrichCorridor(corridor: any, shipments: any[]): any {
  // 1) applicable_duties — collect from shipments' cbp_corridor, then the
  //    corridor's own duty rows, dedupe by duty_type; infer from HS if none.
  const dutyMap = new Map<string, { duty_type: string; rate?: number }>();
  const addDuty = (dt: any, rate?: any) => {
    const type = String(dt || '').trim();
    if (!type) return;
    if (!dutyMap.has(type.toUpperCase())) {
      dutyMap.set(type.toUpperCase(), { duty_type: type, rate: rate != null ? Number(rate) : undefined });
    }
  };
  for (const s of shipments) {
    for (const d of (s?.cbp_corridor?.applicable_duties || [])) addDuty(d?.duty_type || d?.type, d?.rate ?? d?.rate_pct);
  }
  for (const d of (corridor?.applicable_duties || corridor?.duties || [])) addDuty(d?.duty_type || d?.type, d?.rate ?? d?.rate_pct);

  let applicable_duties = Array.from(dutyMap.values());
  if (applicable_duties.length === 0) {
    const hsCodes = shipments.map(s => s?.hs_code || s?.product_code || '').filter(Boolean);
    const commodityText = [corridor?.commodity_name, corridor?.risk_profile, ...shipments.map(s => s?.commodity_name || s?.product_description)]
      .filter(Boolean).join(' ');
    applicable_duties = inferDutiesFromHs(hsCodes, commodityText);
  }

  // 2) anomaly_rate — fraction of shipments with a non-empty anomaly list.
  const withAnomaly = shipments.filter(s => Array.isArray(s?.manifest_anomalies) && s.manifest_anomalies.length > 0).length;
  const anomaly_rate = shipments.length ? withAnomaly / shipments.length : 0;

  // 3) incoming_count — arriving-soon pressure; fall back to total shipments.
  const incoming_count = shipments.filter(s => s?.eta_us || s?.dwell_anomaly).length || shipments.length;

  // 4) corridor_risk_score — explicit if present, else mapped from risk_level.
  const corridor_risk_score = corridor?.corridor_risk_score ?? levelToScore(corridor?.risk_level);

  return {
    ...corridor,
    route: corridor?.route || corridor?.display_name,
    commodity_name: corridor?.commodity_name,
    applicable_duties,
    anomaly_rate,
    incoming_count,
    corridor_risk_score,
  };
}

export default function CorridorRiskScoreV4({ corridor, shipments = [], onScore }: Props) {
  const [score, setScore] = useState<ScoreBreakdownV4 | null>(null);

  useEffect(() => {
    let active = true;
    if (!corridor) { setScore(null); return; }
    const enriched = enrichCorridor(corridor, shipments);
    const parties = assembleParties(shipments);
    cordCorridorScore(enriched, parties).then(s => {
      if (!active) return;
      setScore(s);
      if (s) onScore?.(s.final_score, s.tier);
    });
    return () => { active = false; };
    // onScore intentionally excluded — identity may change each render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [corridor, shipments]);

  if (!score) return null;

  const final = Math.round(score.final_score);

  return (
    <Panel className="border-l-4" style={{ borderLeftColor: riskColor(final) }}>
      <SectionHeader
        title="Corridor Risk"
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
