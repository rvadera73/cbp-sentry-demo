/**
 * Entity Resolution landing — real CORD data. Defaults to the flagged/sanctioned
 * watchlist (OFAC + OpenSanctions, US forced-labor, ICIJ offshore, risk data);
 * the search box queries across all 243K resolved entities.
 */
import React, { useState, useMemo, useEffect, useCallback } from 'react';
import { Search, ChevronRight, Users } from 'lucide-react';
import { Panel, SectionHeader, StatStrip, StatusPill, DataTable, Column, LoadingState } from '../../components/ui';
import { cordWatchlist, cordSearch, flagRisk, CordMatch } from '../services/cordApi';

interface Props {
  selectedEntityId?: string | null;
  setSelectedEntityId?: (id: string | null) => void;
  setActiveTab?: (tab: string) => void;
}

interface Row extends CordMatch { score: number; tier: string }

const riskColor = (t: string) => (t === 'CRITICAL' ? '#D83933' : t === 'HIGH' ? '#C7791B' : t === 'MEDIUM' ? '#B8860B' : '#15803D');
const FLAG_LABEL: Record<string, string> = { sanctioned: 'Sanctioned', forced_labor: 'Forced labor', offshore: 'Offshore leak', high_risk: 'Risk-flagged' };

export default function V2EntityResolutionPage({ setSelectedEntityId, setActiveTab }: Props) {
  const [query, setQuery] = useState('');
  const [flagFilter, setFlagFilter] = useState('all');
  const [page, setPage] = useState(1);
  const [matches, setMatches] = useState<CordMatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState<'watchlist' | 'search'>('watchlist');
  const perPage = 12;

  // Initial flagged watchlist.
  useEffect(() => {
    let cancelled = false;
    (async () => { const w = await cordWatchlist(40); if (!cancelled) { setMatches(w); setLoading(false); } })();
    return () => { cancelled = true; };
  }, []);

  // Debounced search across all entities; empty query falls back to the watchlist.
  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) {
      if (mode === 'search') { setMode('watchlist'); setLoading(true); cordWatchlist(40).then((w) => { setMatches(w); setLoading(false); }); }
      return;
    }
    setLoading(true); setMode('search');
    const t = setTimeout(async () => { const r = await cordSearch(q, 60); setMatches(r); setLoading(false); setPage(1); }, 350);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query]);

  const rows: Row[] = useMemo(() => matches.map((m) => {
    const { score, tier } = flagRisk(m.flag, m.data_source);
    return { ...m, score, tier };
  }), [matches]);

  const filtered = useMemo(() => {
    const r = flagFilter === 'all' ? rows : rows.filter((x) => (x.flag || (x.tier === 'CRITICAL' ? 'sanctioned' : '')) === flagFilter);
    return [...r].sort((a, b) => b.score - a.score);
  }, [rows, flagFilter]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / perPage));
  const paginated = filtered.slice((page - 1) * perPage, page * perPage);

  const counts = useMemo(() => ({
    total: filtered.length,
    critical: filtered.filter((r) => r.tier === 'CRITICAL').length,
    high: filtered.filter((r) => r.tier === 'HIGH').length,
    medium: filtered.filter((r) => r.tier === 'MEDIUM').length,
  }), [filtered]);

  const open = useCallback((id: string) => { setSelectedEntityId?.(id); setActiveTab?.('entity-workspace'); }, [setSelectedEntityId, setActiveTab]);

  const columns: Column[] = [
    {
      key: 'risk', label: 'Risk', render: (e: Row) => (
        <div className="flex items-center gap-2">
          <div className="w-12 h-1.5 bg-slate-200 rounded-sm overflow-hidden">
            <div className="h-full" style={{ width: `${e.score}%`, background: riskColor(e.tier) }} />
          </div>
          <span className="font-mono font-bold text-[#0B1F33]">{e.score}</span>
          <StatusPill status={e.tier} />
        </div>
      ),
    },
    {
      key: 'name', label: 'Entity', render: (e: Row) => (
        <div><div className="font-semibold text-[#0B1F33]">{e.name}</div><div className="text-[10px] font-mono text-[#5C5C5C]">{e.entity_id}</div></div>
      ),
    },
    { key: 'data_source', label: 'Source', render: (e: Row) => <span className="text-[10px] font-bold uppercase text-[#5C5C5C]">{e.data_source || '—'}</span> },
    { key: 'country', label: 'Country', render: (e: Row) => <span className="font-mono text-[#5C5C5C]">{(e.country || '—') || '—'}</span> },
    {
      key: 'flag', label: 'Flag', render: (e: Row) => (
        e.flag ? <span className="text-[#5C5C5C]">{FLAG_LABEL[e.flag] || e.flag}</span> : <span className="text-[#5C5C5C]">{e.program || '—'}</span>
      ),
    },
    {
      key: 'action', label: '', align: 'right', render: (e: Row) => (
        <button onClick={() => open(e.entity_id)}
          className="inline-flex items-center gap-1 px-2.5 py-1 bg-[#005EA2] hover:bg-[#0b4f86] text-white rounded text-[10px] font-bold focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-[#005EA2]">
          Workspace <ChevronRight className="w-3 h-3" />
        </button>
      ),
    },
  ];

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-[#F7F9FC]">
      <div className="bg-white border-b border-[#D0D7DE] px-6 py-3">
        <h1 className="text-xl font-bold text-[#0B1F33]">Entity Resolution</h1>
        <p className="text-[12px] text-[#5C5C5C]">Flagged/sanctioned watchlist · search across 243K resolved CORD entities</p>
      </div>

      <div className="px-6 py-3 space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex items-center flex-1 min-w-[260px]">
            <Search className="h-4 w-4 text-slate-400 absolute left-3" />
            <input
              type="text"
              placeholder="Search all 243K entities by name…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-1.5 border border-[#D0D7DE] rounded-sm text-[12px] text-[#0B1F33] focus:outline-none focus:ring-2 focus:ring-[#005EA2]"
            />
          </div>
          <label className="flex items-center gap-1.5 text-[11px] font-semibold text-[#5C5C5C]">
            FLAG
            <select value={flagFilter} onChange={(e) => { setFlagFilter(e.target.value); setPage(1); }}
              className="bg-white border border-[#D0D7DE] rounded px-2 py-1 text-[11px] text-[#0B1F33] focus:outline-none focus:ring-2 focus:ring-[#005EA2]">
              <option value="all">All</option>
              <option value="sanctioned">Sanctioned</option>
              <option value="forced_labor">Forced labor</option>
              <option value="offshore">Offshore leak</option>
              <option value="high_risk">Risk-flagged</option>
            </select>
          </label>
        </div>

        <StatStrip items={[
          { label: mode === 'search' ? 'Results' : 'Watchlist', value: counts.total },
          { label: 'Critical', value: counts.critical, color: '#D83933' },
          { label: 'High', value: counts.high, color: '#C7791B' },
          { label: 'Medium', value: counts.medium, color: '#B8860B' },
        ]} />
      </div>

      <div className="flex-1 overflow-y-auto px-6 pb-6">
        <Panel>
          <SectionHeader
            title={mode === 'search' ? 'Search Results' : 'Flagged Watchlist'}
            subtitle={`${filtered.length} entit${filtered.length === 1 ? 'y' : 'ies'}`}
            icon={<Users className="w-4 h-4" />}
          />
          {loading ? <LoadingState label={mode === 'search' ? 'Searching CORD…' : 'Loading watchlist…'} /> : (
            <>
              <DataTable columns={columns} rows={paginated} caption="Entity watchlist" empty={mode === 'search' ? 'No entities match your search.' : 'Watchlist unavailable.'} />
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-3 text-[11px] text-[#5C5C5C]">
                  <span>Page {page} of {totalPages}</span>
                  <div className="flex gap-2">
                    <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
                      className="px-2 py-1 bg-white border border-[#D0D7DE] rounded disabled:opacity-50 hover:bg-slate-50">← Prev</button>
                    <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}
                      className="px-2 py-1 bg-white border border-[#D0D7DE] rounded disabled:opacity-50 hover:bg-slate-50">Next →</button>
                  </div>
                </div>
              )}
            </>
          )}
        </Panel>
      </div>
    </div>
  );
}
