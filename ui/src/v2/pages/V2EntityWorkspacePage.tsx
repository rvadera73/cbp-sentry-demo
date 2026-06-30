/**
 * Entity workspace — orchestrates the selected entity: resolves it from CORD,
 * shows the summary on top (outside tabs), the intelligence panel (tabs), a
 * Related & Similar sidebar, and the Assessment & Recommendation at the bottom
 * (outside tabs) — mirroring the Shipment Intelligence layout.
 */
import React, { useState, useEffect } from 'react';
import { ArrowLeft, FileText } from 'lucide-react';
import V2EntityResolutionPanel from '../components/V2EntityResolutionPanel';
import EntitySummary from '../components/EntitySummary';
import ModelBadge from '../components/ModelBadge';
import { cordEntityDetail, cordEntityScore, cordSearch, EntityDetail, CordMatch } from '../services/cordApi';

interface Props {
  selectedEntityId?: string | null;
  setSelectedEntityId?: (id: string | null) => void;
  setActiveTab?: (tab: string) => void;
}

export default function V2EntityWorkspacePage({ selectedEntityId, setSelectedEntityId, setActiveTab }: Props) {
  const [detail, setDetail] = useState<EntityDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [similar, setSimilar] = useState<CordMatch[]>([]);
  const [scoreBreakdown, setScoreBreakdown] = useState<any | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!selectedEntityId) { setDetail(null); setSimilar([]); setScoreBreakdown(null); setLoading(false); return; }
      setLoading(true);
      setScoreBreakdown(null);
      const d = await cordEntityDetail(selectedEntityId);
      if (cancelled) return;
      setDetail(d);
      setLoading(false);
      // Real v4.0 factor-attributed score (non-blocking).
      cordEntityScore(d.entity).then((s) => { if (!cancelled) setScoreBreakdown(s); });
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

  // EAPA is an enforcement action against ENTITIES (actors) — surface a
  // prominent, entity-targeted referral action from the workspace.
  const entityName = detail?.entity?.name || 'this entity';
  const buildEapaReferral = () => {
    if (setActiveTab) setActiveTab('investigations');
    else console.log('[EAPA Referral] Build referral for entity:', selectedEntityId, entityName);
  };

  const parties = detail?.parties || [];
  const prettyRel = (t?: string) => (t || 'related').replace(/_/g, ' ').toLowerCase();
  const usingResolved = parties.length > 0;
  const related = usingResolved
    ? parties.map((p: any) => ({ id: p.entity_id || p.id, name: p.name || p.entity_name || p.entity_id, sub: prettyRel(p.relationship_type || p.relationship || p.type), score: Math.round((p.confidence ?? 0.5) * 100), real: true }))
    : similar.map((m) => ({ id: m.entity_id, name: m.name, sub: `${m.data_source || 'match'}${m.country ? ' · ' + m.country : ''}`, score: null as number | null, real: false }));

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-[#F7F9FC]">
      {/* Back bar */}
      <div className="bg-white border-b border-[#D0D7DE] px-6 py-2 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <button onClick={handleBack} className="flex items-center gap-2 text-[12px] font-bold text-[#005EA2] hover:underline focus:outline-none focus:ring-2 focus:ring-[#005EA2] rounded px-1">
            <ArrowLeft className="w-4 h-4" /> Back to Watchlist
          </button>
          <span className="text-[11px] font-semibold uppercase tracking-wide text-[#005EA2] truncate">
            Entity Resolution · H2 (actor intelligence)
          </span>
          <ModelBadge className="shrink-0" />
        </div>
        <button
          onClick={buildEapaReferral}
          title={`Build an EAPA referral for ${entityName}`}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#D83933] hover:bg-[#b32b27] text-white rounded text-[11px] font-bold shrink-0 focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-[#D83933]">
          <FileText className="w-3.5 h-3.5" /> Build EAPA Referral
        </button>
      </div>

      {/* Entity summary — outside the tabs, changes with selection */}
      <EntitySummary detail={detail} loading={loading} scoreBreakdown={scoreBreakdown} />

      {/* Single content pane — the 3-tab panel (full width), mirroring the
          Shipment Intelligence single-pane layout. Related entities live in the
          Network tab; the assessment is folded into the Risk Profile tab. */}
      <div className="flex-1 overflow-hidden p-4">
        <div className="h-full bg-white rounded-sm border border-[#D0D7DE] overflow-hidden flex flex-col">
          {loading && <div className="flex-1 flex items-center justify-center text-[12px] text-[#5C5C5C]">Resolving entity…</div>}
          {!loading && detail && (
            <V2EntityResolutionPanel
              detail={detail}
              onOpenEntity={openEntity}
              scoreBreakdown={scoreBreakdown}
              related={related}
              usingResolved={usingResolved}
            />
          )}
          {!loading && !detail && <div className="flex-1 flex items-center justify-center text-[12px] text-[#5C5C5C]">Select an entity from the watchlist.</div>}
        </div>
      </div>
    </div>
  );
}
