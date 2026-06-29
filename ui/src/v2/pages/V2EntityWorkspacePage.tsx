/**
 * Entity workspace — orchestrates the selected entity: resolves it from CORD,
 * shows the summary on top (outside tabs), the intelligence panel (tabs), a
 * Related & Similar sidebar, and the Assessment & Recommendation at the bottom
 * (outside tabs) — mirroring the Shipment Intelligence layout.
 */
import React, { useState, useEffect } from 'react';
import { ArrowLeft } from 'lucide-react';
import V2EntityResolutionPanel from '../components/V2EntityResolutionPanel';
import EntitySummary from '../components/EntitySummary';
import EntityAssessment from '../components/EntityAssessment';
import { cordEntityDetail, cordSearch, EntityDetail, CordMatch } from '../services/cordApi';

interface Props {
  selectedEntityId?: string | null;
  setSelectedEntityId?: (id: string | null) => void;
  setActiveTab?: (tab: string) => void;
}

const riskDot = (s: number) => (s >= 80 ? 'bg-[#D83933]' : s >= 60 ? 'bg-orange-600' : s >= 40 ? 'bg-amber-600' : 'bg-green-600');

export default function V2EntityWorkspacePage({ selectedEntityId, setSelectedEntityId, setActiveTab }: Props) {
  const [detail, setDetail] = useState<EntityDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [similar, setSimilar] = useState<CordMatch[]>([]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!selectedEntityId) { setDetail(null); setSimilar([]); setLoading(false); return; }
      setLoading(true);
      const d = await cordEntityDetail(selectedEntityId);
      if (cancelled) return;
      setDetail(d);
      setLoading(false);
      // Related & Similar fallback: when CORD resolves no parties, surface
      // name-network matches so the "view related" flow is always usable.
      if (!d.parties?.length) {
        const token = (d.entity?.name || '').split(/[\s,.]+/).find((w: string) => w.length >= 4) || '';
        if (token) {
          const matches = await cordSearch(token, 8);
          if (!cancelled) setSimilar(matches.filter((m) => m.entity_id !== selectedEntityId).slice(0, 6));
        } else if (!cancelled) setSimilar([]);
      } else if (!cancelled) setSimilar([]);
    })();
    return () => { cancelled = true; };
  }, [selectedEntityId]);

  const openEntity = (id: string) => id && setSelectedEntityId?.(id);
  const handleBack = () => { setSelectedEntityId?.(null); setActiveTab?.('entities'); };

  const parties = detail?.parties || [];
  const related = parties.length
    ? parties.map((p: any) => ({ id: p.entity_id || p.id, name: p.name || p.entity_name || p.entity_id, sub: p.relationship || p.type || 'related', score: Math.round((p.confidence ?? 0.5) * 100), real: true }))
    : similar.map((m) => ({ id: m.entity_id, name: m.name, sub: `${m.data_source || 'match'}${m.country ? ' · ' + m.country : ''}`, score: null as number | null, real: false }));

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-[#F7F9FC]">
      {/* Back bar */}
      <div className="bg-white border-b border-[#D0D7DE] px-6 py-2">
        <button onClick={handleBack} className="flex items-center gap-2 text-[12px] font-bold text-[#005EA2] hover:underline focus:outline-none focus:ring-2 focus:ring-[#005EA2] rounded px-1">
          <ArrowLeft className="w-4 h-4" /> Back to Watchlist
        </button>
      </div>

      {/* Entity summary — outside the tabs, changes with selection */}
      <EntitySummary detail={detail} loading={loading} />

      {/* Panel + Related sidebar */}
      <div className="flex-1 flex overflow-hidden gap-4 p-4">
        <div className="flex-1 bg-white rounded-sm border border-[#D0D7DE] overflow-hidden flex flex-col">
          {loading && <div className="flex-1 flex items-center justify-center text-[12px] text-[#5C5C5C]">Resolving entity…</div>}
          {!loading && detail && <V2EntityResolutionPanel detail={detail} onOpenEntity={openEntity} />}
          {!loading && !detail && <div className="flex-1 flex items-center justify-center text-[12px] text-[#5C5C5C]">Select an entity from the watchlist.</div>}
        </div>

        <div className="w-72 bg-white rounded-sm border border-[#D0D7DE] flex flex-col overflow-hidden">
          <div className="bg-[#F0F4F8] px-3 py-2.5 border-b border-[#D0D7DE]">
            <h3 className="text-[11px] font-bold uppercase tracking-wide text-[#0B1F33]">
              {parties.length ? 'Related Entities' : 'Related & Similar'} ({related.length})
            </h3>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
            {related.length ? related.map((r, i) => (
              <button key={i} onClick={() => openEntity(r.id)}
                className="w-full text-left p-2 bg-slate-50 hover:bg-[#E3F2FD] border border-slate-200 hover:border-[#005EA2] rounded transition-colors focus:outline-none focus:ring-2 focus:ring-[#005EA2]">
                <div className="flex items-start justify-between gap-1.5">
                  <span className="text-[11px] font-bold text-[#0B1F33] line-clamp-2">{r.name}</span>
                  {r.score != null && <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded text-white shrink-0 ${riskDot(r.score)}`}>{r.score}</span>}
                </div>
                <div className="flex items-center justify-between mt-0.5">
                  <span className="text-[10px] text-[#5C5C5C] truncate">{r.sub}</span>
                  <span className="text-[10px] text-[#005EA2] font-bold shrink-0">→ Open</span>
                </div>
              </button>
            )) : (
              <p className="text-[11px] text-[#5C5C5C] text-center py-8">No related or similar entities resolved.</p>
            )}
          </div>
        </div>
      </div>

      {/* Assessment & recommendation — outside the tabs, at the bottom */}
      <div className="shrink-0 px-4 pb-4 pt-1 border-t border-[#D0D7DE] bg-[#F7F9FC]">
        <EntityAssessment detail={detail} />
      </div>
    </div>
  );
}
