import { useEffect, useMemo, useState } from 'react';
import { Upload, Radio, AlertTriangle, Route, Users, ChevronRight, Clock } from 'lucide-react';
import { useV2ThreatFeed } from '../hooks/useV2ThreatFeed';
import { useV2Cases } from '../hooks/useV2Cases';
import { useCorridorIntelligence } from '../hooks/useCorridorIntelligence';
import { cordWatchlist, flagRisk, CordMatch } from '../services/cordApi';
import { Case, Shipment } from '../types/v2.types';
import UploadPipelineModal from '../../components/cases/UploadPipelineModal';
import { Panel, SectionHeader, StatStrip } from '../../components/ui';
import ModelBadge from '../components/ModelBadge';

interface V2DashboardPageProps {
  cases?: Case[];
  shipments?: Shipment[];
  selectCaseForDetail?: (caseObj: Case) => void;
  synopsisMap?: Record<string, string>;
  setActiveTab?: (tab: string) => void;
}

const scoreColor = (s: number) => (s >= 80 ? '#D83933' : s >= 50 ? '#C7791B' : '#15803D');
const tierColor = (t: string) => (t === 'CRITICAL' ? '#D83933' : t === 'HIGH' ? '#C7791B' : t === 'MEDIUM' ? '#B8860B' : '#15803D');
const RISK_RANK: Record<string, number> = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };

/** SLA is a free-text timer ("21 Days Remaining" / "3 Days Overdue"). Parse to a
 * sortable urgency: overdue first (most overdue worst), then fewest days left. */
function slaUrgency(sla: string): number {
  const s = String(sla || '');
  const num = parseInt(s.replace(/[^0-9]/g, ''), 10) || 0;
  if (/overdue/i.test(s)) return -1000 - num; // overdue ranks first, more days = worse
  return num; // fewer days remaining = more urgent
}

export default function V2DashboardPage({ cases: propCases, selectCaseForDetail, setActiveTab }: V2DashboardPageProps) {
  const { cases: localCases } = useV2Cases();
  const { threatFeed, loading: threatLoading } = useV2ThreatFeed();
  const { corridors, isLoading: corridorsLoading } = useCorridorIntelligence();
  const cases = propCases || localCases;

  const [showUploadModal, setShowUploadModal] = useState(false);

  // H2 — flagged actors on active shipments (CORD watchlist). Owned by the dashboard.
  const [actors, setActors] = useState<CordMatch[]>([]);
  const [actorsLoading, setActorsLoading] = useState(true);
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const w = await cordWatchlist('active_shipments', 12);
      if (!cancelled) { setActors(w); setActorsLoading(false); }
    })();
    return () => { cancelled = true; };
  }, []);

  // ---- H1: Hot corridors (top high/critical risk lanes) ----
  const hotCorridors = useMemo(() => {
    return [...corridors]
      .filter(c => c.risk_level === 'High' || c.risk_level === 'Critical')
      .sort((a, b) => (RISK_RANK[(a.risk_level || '').toUpperCase()] ?? 9) - (RISK_RANK[(b.risk_level || '').toUpperCase()] ?? 9));
  }, [corridors]);

  // ---- H2: Top flagged actors (ranked by watchlist flag severity) ----
  const topActors = useMemo(() => {
    return actors
      .map(a => ({ ...a, ...flagRisk(a.flag, a.data_source) }))
      .sort((a, b) => b.score - a.score)
      .slice(0, 5);
  }, [actors]);


  // ---- Triage: needs attention now (overdue / highest score), top 5 ----
  const needsAttention = useMemo(() => {
    return [...cases]
      .sort((a, b) => slaUrgency(a.sla_timer) - slaUrgency(b.sla_timer) || b.risk_score - a.risk_score)
      .slice(0, 5);
  }, [cases]);

  const goShipments = () => setActiveTab?.('shipments');
  const goEntities = () => setActiveTab?.('entities');


  // Route a threat-feed click to its horizon.
  const openThreat = (e: typeof threatFeed[number]) => {
    if (e.kind === 'corridor') { goShipments(); return; }
    if (e.kind === 'entity') { goEntities(); return; }
    // manifest → its case if we can match it, else the shipments tab
    const rc = e.related_case_id ? cases.find(c => c.case_id === e.related_case_id) : undefined;
    if (rc && selectCaseForDetail) selectCaseForDetail(rc);
    else goShipments();
  };

  return (
    <div className="flex-1 p-5 flex flex-col space-y-4 overflow-y-auto bg-[#F7F9FC]">
      {/* Page intro */}
      <div className="shrink-0 flex items-start justify-between gap-3">
        <div>
          <h1 className="text-lg font-black text-[#0B1F33] uppercase tracking-wide">Command Center</h1>
          <p className="text-[12px] text-[#5C5C5C] mt-0.5">
            Three-horizon triage — corridors (H1) and actors (H2) above; the flagged-manifest case pipeline (H3) below. Drill into a tab for full detail.
          </p>
        </div>
        <ModelBadge className="shrink-0 mt-0.5" />
      </div>

      {/* KPI synthesis */}
      <StatStrip items={[
        { label: 'Critical Investigations', value: cases.filter(c => c.priority === 'Critical').length, color: '#D83933' },
        { label: 'High-Risk ≥80', value: cases.filter(c => c.risk_score >= 80).length, color: '#C7791B' },
        { label: 'Active Cases', value: cases.filter(c => c.case_status === 'Active').length },
        { label: 'Total Cases', value: cases.length },
      ]} />

      {/* THREE-HORIZON SYNTHESIS */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 shrink-0">
        {/* H1 — Hot Corridors */}
        <Panel className="flex flex-col">
          <SectionHeader
            title="Hot Corridors"
            subtitle="H1 · highest-risk trade lanes"
            icon={<Route className="w-4 h-4" />}
            action={<span className="text-[10px] font-mono text-[#5C5C5C]">{hotCorridors.length} flagged</span>}
          />
          <div className="flex-1">
            {corridorsLoading ? (
              <p className="text-[12px] text-[#5C5C5C] py-6 text-center">Loading corridors…</p>
            ) : hotCorridors.length === 0 ? (
              <p className="text-[12px] text-[#5C5C5C] py-6 text-center">No high-risk corridors right now.</p>
            ) : hotCorridors.slice(0, 5).map(c => (
              <button key={c.id} onClick={goShipments}
                className="w-full text-left flex items-center justify-between gap-2 py-1.5 border-b border-slate-100 last:border-0 hover:bg-slate-50 rounded-sm px-1 focus:outline-none focus:ring-2 focus:ring-[#005EA2]">
                <div className="min-w-0">
                  <div className="text-[11px] font-bold text-[#0B1F33] truncate">{c.display_name || c.id}</div>
                  <div className="text-[10px] text-[#5C5C5C] truncate">{c.risk_profile || `${c.origin_country} → ${c.destination_country}`}</div>
                </div>
                <span className="text-[10px] font-bold uppercase tracking-wide flex-shrink-0" style={{ color: tierColor((c.risk_level || '').toUpperCase()) }}>{c.risk_level}</span>
              </button>
            ))}
          </div>
          <button onClick={goShipments} className="mt-2 text-[11px] font-bold text-[#005EA2] hover:underline self-start flex items-center gap-1">
            View in Shipment Intelligence <ChevronRight className="w-3 h-3" />
          </button>
        </Panel>

        {/* H2 — Top Flagged Actors */}
        <Panel className="flex flex-col">
          <SectionHeader
            title="Top Flagged Actors"
            subtitle="H2 · watchlist hits on active shipments"
            icon={<Users className="w-4 h-4" />}
            action={<span className="text-[10px] font-mono text-[#5C5C5C]">{actors.length} on watchlist</span>}
          />
          <div className="flex-1">
            {actorsLoading ? (
              <p className="text-[12px] text-[#5C5C5C] py-6 text-center">Loading actors…</p>
            ) : topActors.length === 0 ? (
              <p className="text-[12px] text-[#5C5C5C] py-6 text-center">No flagged actors on active shipments.</p>
            ) : topActors.map(a => (
              <button key={a.entity_id} onClick={goEntities}
                className="w-full text-left flex items-center justify-between gap-2 py-1.5 border-b border-slate-100 last:border-0 hover:bg-slate-50 rounded-sm px-1 focus:outline-none focus:ring-2 focus:ring-[#005EA2]">
                <div className="min-w-0">
                  <div className="text-[11px] font-bold text-[#0B1F33] truncate">{a.name}</div>
                  <div className="text-[10px] text-[#5C5C5C] truncate">{[a.country, a.data_source].filter(Boolean).join(' · ')}</div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {a.shipment_count != null && <span className="text-[10px] font-mono text-[#5C5C5C]">{a.shipment_count} shp</span>}
                  <span className="text-[12px] font-black font-mono w-8 text-right" style={{ color: tierColor(a.tier) }}>{a.score}</span>
                </div>
              </button>
            ))}
          </div>
          <button onClick={goEntities} className="mt-2 text-[11px] font-bold text-[#005EA2] hover:underline self-start flex items-center gap-1">
            View in Entity Resolution <ChevronRight className="w-3 h-3" />
          </button>
        </Panel>

      </div>

      {/* Upload action */}
      <div className="flex justify-end shrink-0">
        <button onClick={() => setShowUploadModal(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-[#005EA2] hover:bg-[#0b4f86] text-white rounded text-[11px] font-bold focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-[#005EA2]">
          <Upload className="w-3.5 h-3.5" /> Upload Manifest
        </button>
      </div>

      {/* TRIAGE + THREAT FEED */}
      <div className="flex-1 flex flex-col lg:flex-row gap-4 overflow-hidden min-h-[300px]">
        {/* Needs attention now (triage strip) */}
        <div className="flex-1 min-w-0">
          <Panel className="h-full flex flex-col">
            <SectionHeader
              title="Needs Attention Now"
              subtitle="H3 · flagged manifests in the case pipeline — by SLA breach / highest risk"
              icon={<AlertTriangle className="w-4 h-4" />}
            />
            <div className="overflow-y-auto flex-1">
              {needsAttention.length === 0 ? (
                <p className="text-[12px] text-[#5C5C5C] py-6 text-center">No open cases.</p>
              ) : needsAttention.map(c => {
                const overdue = /overdue/i.test(String(c.sla_timer));
                return (
                  <button key={c.case_id} onClick={() => selectCaseForDetail?.(c)}
                    className="w-full text-left flex items-center justify-between gap-3 py-2 border-b border-slate-100 last:border-0 hover:bg-slate-50 rounded-sm px-1 focus:outline-none focus:ring-2 focus:ring-[#005EA2]">
                    <div className="flex items-center gap-2 min-w-0">
                      <div className="w-9 h-1.5 bg-slate-200 rounded-sm overflow-hidden flex-shrink-0">
                        <div className="h-full" style={{ width: `${c.risk_score}%`, background: scoreColor(c.risk_score) }} />
                      </div>
                      <span className="font-mono font-bold text-[12px] w-7" style={{ color: scoreColor(c.risk_score) }}>{c.risk_score}</span>
                      <div className="min-w-0">
                        <div className="text-[11px] font-semibold text-[#0B1F33] truncate">{c.target_entity.split('/')[0]}</div>
                        <div className="text-[10px] font-mono text-[#5C5C5C] truncate">{c.case_id} · {c.product_category}</div>
                      </div>
                    </div>
                    <span className={`flex items-center gap-1 text-[10px] font-mono font-bold flex-shrink-0 ${overdue ? 'text-[#D83933]' : 'text-[#5C5C5C]'}`}>
                      <Clock className="w-3 h-3" />{c.sla_timer}
                    </span>
                  </button>
                );
              })}
            </div>
            <button onClick={() => setActiveTab?.('investigations')} className="mt-2 text-[11px] font-bold text-[#005EA2] hover:underline self-start flex items-center gap-1">
              View all in Active Investigations <ChevronRight className="w-3 h-3" />
            </button>
          </Panel>
        </div>

        {/* Live Threat Feed */}
        <div className="w-full lg:w-96 shrink-0">
          <Panel className="h-full flex flex-col">
            <SectionHeader
              title="Live Threat Feed"
              subtitle="New & escalating risk events (72h pipeline)"
              icon={<Radio className="w-4 h-4" />}
            />
            <div className="overflow-y-auto flex-1 divide-y divide-slate-100 -mx-1">
              {threatLoading ? (
                <p className="text-[12px] text-[#5C5C5C] py-6 text-center">Loading threat feed…</p>
              ) : threatFeed.length === 0 ? (
                <p className="text-[12px] text-[#5C5C5C] py-8 px-3 text-center leading-snug">
                  No active threats. A threat is a new or escalating high-risk event in the 72-hour pipeline — an arriving manifest hitting a flagged actor or AD/CVD lane, or a newly-flagged entity.
                </p>
              ) : threatFeed.map(event => (
                <button key={event.id} onClick={() => openThreat(event)}
                  className="w-full text-left px-1 py-2.5 hover:bg-slate-50 rounded-sm focus:outline-none focus:ring-2 focus:ring-[#005EA2]">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`px-1.5 py-0.5 text-[10px] font-bold rounded uppercase ${event.severity === 'Critical' ? 'bg-red-100 text-red-800' : event.severity === 'High' ? 'bg-amber-100 text-amber-900' : 'bg-blue-100 text-blue-900'}`}>{event.severity}</span>
                    {event.kind && <span className="px-1.5 py-0.5 text-[9px] font-bold rounded uppercase bg-slate-100 text-slate-600 tracking-wide">{event.kind}</span>}
                    <span className="text-[10px] text-[#5C5C5C] font-mono ml-auto">{event.confidence}%</span>
                  </div>
                  <h4 className="text-[11px] font-bold text-[#0B1F33]">{event.title}</h4>
                  <p className="text-[10px] text-[#5C5C5C] leading-snug mt-0.5 mb-1.5">{event.description}</p>
                  <div className="flex justify-between items-center">
                    <span className="text-[10px] text-slate-400 font-mono">{event.timestamp}</span>
                    <span className="text-[10px] text-[#005EA2] font-bold flex items-center gap-0.5">Investigate <ChevronRight className="w-3 h-3" /></span>
                  </div>
                </button>
              ))}
            </div>
          </Panel>
        </div>
      </div>

      {showUploadModal && (
        <UploadPipelineModal onClose={() => setShowUploadModal(false)} onComplete={() => { setShowUploadModal(false); window.location.reload(); }} />
      )}
    </div>
  );
}
