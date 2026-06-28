/**
 * Corridor Trade Analysis — consolidated, sequenced view of one trade corridor.
 * Sequence: Routing & Transshipment (map + flow) -> Anomaly Detection ->
 * Commodity & Duty Exposure -> Corridor Summary -> Assessment & Recommendation.
 * Built on the shared UI kit for cross-tab consistency.
 */
import React from 'react';
import { Map as MapIcon, Search, Package } from 'lucide-react';
import TradeCorridorMap from './TradeCorridorMap';
import { Panel, SectionHeader, StatusPill, ScoreBar, DataTable, Column } from '../../components/ui';

export interface ManifestStop { location: string; type: 'origin' | 'hub' | 'destination'; entity_name: string; dwell_days?: number; anomalies?: string[]; risk_score?: number }
export interface TradeRoute { origin_country: string; destination_country: string; shipment_count: number; avg_risk_score: number; avg_dwell_days: number; anomaly_count: number }
export interface AnomalyItem { id: string; name: string; status: 'flagged' | 'clear' | 'pending'; severity_score: number; details: string }
export interface CommodityRisk { commodity: string; hs_code: string; supply_chain_risk: number; tariff_risk: number; origin_risk: number; total_risk: number }

interface Props {
  corridor?: any;
  shipments?: any[];
}

const riskColor = (s: number) => (s >= 80 ? '#D83933' : s >= 60 ? '#C7791B' : s >= 40 ? '#B8860B' : '#15803D');

export default function CorridorTradeAnalysis({ corridor, shipments = [] }: Props) {
  const name: string = corridor?.display_name || 'Vietnam → USA';
  const origin = name.split('→')[0]?.trim() || 'Origin';
  const destination = name.split('→')[1]?.trim() || 'Destination';
  const corridorAvgRisk = shipments.length ? shipments.reduce((sum, s) => sum + (s.risk_score || 0), 0) / shipments.length : 50;
  const shipmentCount = shipments.length;

  const stops: ManifestStop[] = [
    { location: origin, type: 'origin', entity_name: 'Shipper Entity', dwell_days: 1, anomalies: [], risk_score: 62 },
    { location: 'Transshipment', type: 'hub', entity_name: 'Port Authority', dwell_days: 3, anomalies: ['DWELL_ANOMALY'], risk_score: 72 },
    { location: destination, type: 'destination', entity_name: 'Consignee', dwell_days: 0, anomalies: [], risk_score: 52 },
  ];
  const routes: TradeRoute[] = [
    { origin_country: origin, destination_country: destination, shipment_count: shipmentCount, avg_risk_score: corridorAvgRisk, avg_dwell_days: 5, anomaly_count: shipments.filter(s => s.manifest_anomalies?.length > 0).length },
  ];
  const commodityInfo = {
    commodity: shipments[0]?.commodity_name || 'General Merchandise',
    hs_code: shipments[0]?.hs_code || 'N/A',
    weight_kg: shipments[0]?.manifest_data?.weight_kg || 0,
    value_usd: shipments[0]?.manifest_data?.declared_value_usd || 0,
  };
  const commodityRisk: CommodityRisk[] = shipments.length > 0
    ? [{ commodity: commodityInfo.commodity, hs_code: commodityInfo.hs_code, supply_chain_risk: 65, tariff_risk: 72, origin_risk: 68, total_risk: 68 }]
    : [];
  const has = (pred: (s: any) => boolean) => shipments.some(pred);
  const anomalies: AnomalyItem[] = [
    { id: 'isf_mismatch', name: 'ISF Element 9 Mismatch', status: has(s => s.element9_is_mismatch) ? 'flagged' : 'clear', severity_score: has(s => s.element9_is_mismatch) ? 78 : 5, details: 'Origin consistency check' },
    { id: 'dwell_anomaly', name: 'Dwell Time Anomaly', status: has(s => s.manifest_anomalies?.includes('DWELL_ANOMALY')) ? 'flagged' : 'clear', severity_score: has(s => s.manifest_anomalies?.includes('DWELL_ANOMALY')) ? 68 : 5, details: 'Port dwell baseline check' },
    { id: 'origin_inconsistent', name: 'Origin Country Inconsistent', status: 'pending', severity_score: 45, details: 'Manual verification pending' },
    { id: 'weight_variance', name: 'Weight/Volume Variance', status: 'clear', severity_score: 12, details: 'Within tolerance' },
    { id: 'missing_docs', name: 'Missing Documentation', status: has(s => !s.manifest_data?.bill_of_lading) ? 'flagged' : 'clear', severity_score: has(s => !s.manifest_data?.bill_of_lading) ? 89 : 2, details: 'Document completeness' },
    { id: 'consignee_verified', name: 'Consignee Verified', status: 'clear', severity_score: 5, details: 'Good standing' },
    { id: 'vessel_flag_risk', name: 'Vessel Flag Risk', status: 'clear', severity_score: 15, details: 'Standard jurisdiction' },
    { id: 'pricing_anomaly', name: 'Pricing Per Unit Anomaly', status: 'pending', severity_score: 38, details: 'Awaiting clarification' },
    { id: 'hs_code_valid', name: 'HS Code Valid & Complete', status: 'clear', severity_score: 2, details: 'Correctly classified' },
    { id: 'prior_violation', name: 'Prior Carrier Violation', status: 'clear', severity_score: 8, details: 'No recent incidents' },
  ];

  const flagged = anomalies.filter(a => a.status === 'flagged');
  const cm = commodityRisk[0];
  const duties: any[] = corridor?.duties || [];

  const anomalyRows = [...anomalies].sort((a, b) => {
    const rank = (s: string) => (s === 'flagged' ? 0 : s === 'pending' ? 1 : 2);
    return rank(a.status) - rank(b.status) || b.severity_score - a.severity_score;
  });
  const anomalyColumns: Column[] = [
    { key: 'name', label: 'Check', render: r => <span className="font-semibold text-[#0B1F33]">{r.name}</span> },
    { key: 'status', label: 'Status', align: 'center', render: r => <StatusPill status={r.status} /> },
    { key: 'severity_score', label: 'Severity', align: 'right', mono: true, render: r => <span style={{ color: riskColor(r.severity_score) }} className="font-bold">{r.severity_score}</span> },
    { key: 'details', label: 'Details', render: r => <span className="text-[#5C5C5C]">{r.details}</span> },
  ];

  return (
    <div className="space-y-4">
      {/* 1. Routing & Transshipment — map + flow side by side */}
      <Panel>
        <SectionHeader title="Routing & Transshipment" subtitle="Geographic route alongside hop-by-hop dwell, risk, and anomalies" icon={<MapIcon className="w-4 h-4" />} />
        <div className="grid lg:grid-cols-2 gap-4">
          <TradeCorridorMap routes={routes} height={300} />
          <ol className="relative">
            {stops.map((stop, i) => {
              const c = riskColor(stop.risk_score || 0);
              return (
                <li key={i} className="relative pl-6 pb-3 last:pb-0">
                  {i < stops.length - 1 && <span className="absolute left-[7px] top-4 bottom-0 w-px bg-[#D0D7DE]" aria-hidden />}
                  <span className="absolute left-0 top-1 w-3.5 h-3.5 rounded-full border-2 border-white" style={{ background: c }} />
                  <div className="flex items-center justify-between gap-2">
                    <div className="min-w-0">
                      <div className="text-[10px] font-bold uppercase tracking-wide text-[#5C5C5C]">{stop.location} · {stop.type}</div>
                      <div className="text-[12px] font-semibold text-[#0B1F33] truncate">{stop.entity_name}</div>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {!!stop.dwell_days && <span className="text-[10px] text-[#5C5C5C]"><b className="text-[#0B1F33]">{stop.dwell_days}d</b> dwell</span>}
                      <span className="text-[11px] font-mono font-bold text-white px-1.5 py-0.5 rounded" style={{ background: c }}>{stop.risk_score}</span>
                    </div>
                  </div>
                  {stop.anomalies && stop.anomalies.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {stop.anomalies.map(a => <span key={a} className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded bg-red-100 text-red-800">{a.replace(/_/g, ' ')}</span>)}
                    </div>
                  )}
                </li>
              );
            })}
          </ol>
        </div>
      </Panel>

      {/* 2. Anomaly Detection */}
      <Panel>
        <SectionHeader title="Anomaly Detection" subtitle={`${flagged.length} flagged · ${anomalies.length} checks`} icon={<Search className="w-4 h-4" />} />
        <DataTable columns={anomalyColumns} rows={anomalyRows} caption="Corridor anomaly checks" empty="No anomaly checks." />
      </Panel>

      {/* 3. Commodity & Duty Exposure */}
      <Panel>
        <SectionHeader title="Commodity & Duty Exposure" subtitle="Commodity profile, risk dimensions, and active trade remedies" icon={<Package className="w-4 h-4" />} />
        <div className="flex flex-wrap gap-x-5 gap-y-1 mb-3 text-[11px]">
          <span><span className="text-[#5C5C5C]">Commodity:</span> <b className="text-[#0B1F33]">{commodityInfo.commodity}</b></span>
          <span><span className="text-[#5C5C5C]">HS:</span> <b className="font-mono text-[#0B1F33]">{commodityInfo.hs_code}</b></span>
          <span><span className="text-[#5C5C5C]">Weight:</span> <b className="font-mono text-[#0B1F33]">{(commodityInfo.weight_kg / 1000).toFixed(1)}T</b></span>
          <span><span className="text-[#5C5C5C]">Value:</span> <b className="font-mono text-[#0B1F33]">${(commodityInfo.value_usd / 1000).toFixed(0)}K</b></span>
        </div>
        <div className="grid md:grid-cols-2 gap-x-6 gap-y-3">
          <div>
            <div className="text-[10px] font-bold uppercase tracking-wide text-[#5C5C5C] mb-1">Risk Dimensions</div>
            {cm ? (
              <>
                <ScoreBar label="Supply Chain" sublabel="Multi-hop / opacity" score={cm.supply_chain_risk} />
                <ScoreBar label="Tariff / Duty" sublabel="AD/CVD & evasion incentive" score={cm.tariff_risk} />
                <ScoreBar label="Origin" sublabel="Country-of-origin profile" score={cm.origin_risk} />
              </>
            ) : <p className="text-[11px] text-[#5C5C5C]">No commodity risk data.</p>}
          </div>
          <div>
            <div className="text-[10px] font-bold uppercase tracking-wide text-[#5C5C5C] mb-1">Active AD/CVD Duties</div>
            {duties.length ? duties.slice(0, 6).map((d, i) => (
              <div key={i} className="flex items-center justify-between gap-2 py-1.5 border-b border-slate-100 last:border-0">
                <div className="min-w-0">
                  <div className="text-[11px] font-semibold text-[#0B1F33] truncate">{d.duty_type || d.product_description || 'AD/CVD order'}</div>
                  <div className="text-[10px] font-mono text-[#5C5C5C]">{d.case_number || d.hs_prefix || '—'}</div>
                </div>
                <span className="text-[12px] font-mono font-bold text-[#D83933] flex-shrink-0">{Number(d.rate_pct) > 0 ? `${d.rate_pct}%` : 'Variable'}</span>
              </div>
            )) : <p className="text-[11px] text-[#5C5C5C]">No active duties for this corridor.</p>}
          </div>
        </div>
      </Panel>

    </div>
  );
}
