import React, { useState, useMemo } from 'react';
import { Search, ChevronRight, Users } from 'lucide-react';
import { Panel, SectionHeader, StatStrip, StatusPill, DataTable, Column } from '../../components/ui';

interface EntityWatchlistItem {
  entity_id: string;
  entity_name: string;
  entity_type: 'Shipper' | 'Consignee' | 'Operator' | 'Freight Forwarder';
  risk_score: number;
  risk_level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  last_seen: string;
  flag_reason: string;
  related_count: number;
}

interface V2EntityResolutionPageProps {
  selectedEntityId?: string | null;
  setSelectedEntityId?: (id: string | null) => void;
  setActiveTab?: (tab: string) => void;
}

const FIXTURE_WATCHLIST: EntityWatchlistItem[] = [
  { entity_id: 'ENT-GF-VN-001', entity_name: 'Greenfield Industrial Trading Co., Ltd.', entity_type: 'Shipper', risk_score: 65, risk_level: 'HIGH', last_seen: '2026-05-27', flag_reason: 'Prior EAPA determination', related_count: 3 },
  { entity_id: 'ENT-SP-US-001', entity_name: 'SunPath Energy Distributors LLC', entity_type: 'Consignee', risk_score: 52, risk_level: 'MEDIUM', last_seen: '2026-05-26', flag_reason: 'Prior evasion case', related_count: 1 },
  { entity_id: 'ENT-SOL-MY-001', entity_name: 'Solaria Manufacturing Sdn. Bhd.', entity_type: 'Shipper', risk_score: 48, risk_level: 'MEDIUM', last_seen: '2026-05-25', flag_reason: 'New shipper + transshipment pattern', related_count: 2 },
  { entity_id: 'ENT-PAN-PAC-001', entity_name: 'Pan-Pacific Logistics, Inc.', entity_type: 'Freight Forwarder', risk_score: 38, risk_level: 'LOW', last_seen: '2026-05-27', flag_reason: 'Shared with high-risk entities', related_count: 5 },
  { entity_id: 'ENT-OCS-HK-001', entity_name: 'Ocean Shipping Inc.', entity_type: 'Operator', risk_score: 35, risk_level: 'LOW', last_seen: '2026-05-24', flag_reason: 'Vessel operates high-risk corridors', related_count: 2 },
];

const riskColor = (level: string) =>
  level === 'CRITICAL' ? '#D83933' : level === 'HIGH' ? '#C7791B' : level === 'MEDIUM' ? '#B8860B' : '#15803D';

export default function V2EntityResolutionPage({ setSelectedEntityId, setActiveTab }: V2EntityResolutionPageProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [riskFilter, setRiskFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  const filtered = useMemo(() => {
    return FIXTURE_WATCHLIST.filter(e => {
      const q = searchQuery.toLowerCase();
      const matchesSearch = e.entity_name.toLowerCase().includes(q) || e.entity_id.toLowerCase().includes(q) || e.flag_reason.toLowerCase().includes(q);
      const matchesRisk = riskFilter === 'all' || e.risk_level.toLowerCase() === riskFilter;
      const matchesType = typeFilter === 'all' || e.entity_type === typeFilter;
      return matchesSearch && matchesRisk && matchesType;
    }).sort((a, b) => b.risk_score - a.risk_score);
  }, [searchQuery, riskFilter, typeFilter]);

  const totalPages = Math.ceil(filtered.length / itemsPerPage);
  const paginated = filtered.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  const counts = useMemo(() => ({
    CRITICAL: filtered.filter(e => e.risk_level === 'CRITICAL').length,
    HIGH: filtered.filter(e => e.risk_level === 'HIGH').length,
    MEDIUM: filtered.filter(e => e.risk_level === 'MEDIUM').length,
    LOW: filtered.filter(e => e.risk_level === 'LOW').length,
  }), [filtered]);

  const open = (id: string) => { setSelectedEntityId?.(id); setActiveTab?.('entity-workspace'); };

  const columns: Column[] = [
    {
      key: 'risk', label: 'Risk', render: e => (
        <div className="flex items-center gap-2">
          <div className="w-12 h-1.5 bg-slate-200 rounded-sm overflow-hidden">
            <div className="h-full" style={{ width: `${e.risk_score}%`, background: riskColor(e.risk_level) }} />
          </div>
          <span className="font-mono font-bold text-[#0B1F33]">{e.risk_score}</span>
          <StatusPill status={e.risk_level} />
        </div>
      ),
    },
    {
      key: 'entity_name', label: 'Entity', render: e => (
        <div><div className="font-semibold text-[#0B1F33]">{e.entity_name}</div><div className="text-[10px] font-mono text-[#5C5C5C]">{e.entity_id}</div></div>
      ),
    },
    { key: 'entity_type', label: 'Type', render: e => <span className="text-[10px] font-bold uppercase text-[#5C5C5C]">{e.entity_type}</span> },
    { key: 'flag_reason', label: 'Flag Reason', render: e => <span className="text-[#5C5C5C]">{e.flag_reason}</span> },
    { key: 'last_seen', label: 'Seen', align: 'right', mono: true },
    { key: 'related_count', label: 'Links', align: 'center', render: e => <span className="font-mono font-bold text-[#005EA2]">{e.related_count}</span> },
    {
      key: 'action', label: '', align: 'right', render: e => (
        <button onClick={() => open(e.entity_id)}
          className="inline-flex items-center gap-1 px-2.5 py-1 bg-[#005EA2] hover:bg-[#0b4f86] text-white rounded text-[10px] font-bold focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-[#005EA2]">
          Workspace <ChevronRight className="w-3 h-3" />
        </button>
      ),
    },
  ];

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-[#F7F9FC]">
      {/* Header */}
      <div className="bg-white border-b border-[#D0D7DE] px-6 py-3">
        <h1 className="text-xl font-bold text-[#0B1F33]">Entity Resolution</h1>
        <p className="text-[12px] text-[#5C5C5C]">Active watchlist · pre-arrival intelligence · risk monitoring</p>
      </div>

      {/* Controls */}
      <div className="px-6 py-3 space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex items-center flex-1 min-w-[240px]">
            <Search className="h-4 w-4 text-slate-400 absolute left-3" />
            <input
              type="text"
              placeholder="Search by entity name, ID, or flag reason…"
              value={searchQuery}
              onChange={e => { setSearchQuery(e.target.value); setCurrentPage(1); }}
              className="w-full pl-9 pr-4 py-1.5 border border-[#D0D7DE] rounded-sm text-[12px] text-[#0B1F33] focus:outline-none focus:ring-2 focus:ring-[#005EA2]"
            />
          </div>
          <label className="flex items-center gap-1.5 text-[11px] font-semibold text-[#5C5C5C]">
            RISK
            <select value={riskFilter} onChange={e => { setRiskFilter(e.target.value); setCurrentPage(1); }}
              className="bg-white border border-[#D0D7DE] rounded px-2 py-1 text-[11px] text-[#0B1F33] focus:outline-none focus:ring-2 focus:ring-[#005EA2]">
              <option value="all">All</option><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option>
            </select>
          </label>
          <label className="flex items-center gap-1.5 text-[11px] font-semibold text-[#5C5C5C]">
            TYPE
            <select value={typeFilter} onChange={e => { setTypeFilter(e.target.value); setCurrentPage(1); }}
              className="bg-white border border-[#D0D7DE] rounded px-2 py-1 text-[11px] text-[#0B1F33] focus:outline-none focus:ring-2 focus:ring-[#005EA2]">
              <option value="all">All</option><option value="Shipper">Shipper</option><option value="Consignee">Consignee</option><option value="Operator">Operator</option><option value="Freight Forwarder">Freight Fwd</option>
            </select>
          </label>
        </div>

        <StatStrip items={[
          { label: 'Total', value: filtered.length },
          { label: 'Critical', value: counts.CRITICAL, color: '#D83933' },
          { label: 'High', value: counts.HIGH, color: '#C7791B' },
          { label: 'Medium', value: counts.MEDIUM, color: '#B8860B' },
          { label: 'Low', value: counts.LOW, color: '#15803D' },
        ]} />
      </div>

      {/* Table */}
      <div className="flex-1 overflow-y-auto px-6 pb-6">
        <Panel>
          <SectionHeader title="Entity Watchlist" subtitle={`${filtered.length} entit${filtered.length === 1 ? 'y' : 'ies'}`} icon={<Users className="w-4 h-4" />} />
          <DataTable columns={columns} rows={paginated} caption="Entity watchlist" empty="No entities match the current filters." />
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-3 text-[11px] text-[#5C5C5C]">
              <span>Page {currentPage} of {totalPages}</span>
              <div className="flex gap-2">
                <button onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage === 1}
                  className="px-2 py-1 bg-white border border-[#D0D7DE] rounded disabled:opacity-50 hover:bg-slate-50">← Prev</button>
                <button onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage === totalPages}
                  className="px-2 py-1 bg-white border border-[#D0D7DE] rounded disabled:opacity-50 hover:bg-slate-50">Next →</button>
              </div>
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}
