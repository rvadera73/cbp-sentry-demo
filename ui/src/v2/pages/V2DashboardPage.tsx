import React, { useState } from 'react';
import { Search, Upload, ListChecks, Radio } from 'lucide-react';
import { useV2Cases } from '../hooks/useV2Cases';
import { useV2ThreatFeed } from '../hooks/useV2ThreatFeed';
import { Case, Shipment } from '../types/v2.types';
import UploadPipelineModal from '../../components/cases/UploadPipelineModal';
import EntityRiskDashboard from '../components/EntityRiskDashboard';
import { Panel, SectionHeader, StatStrip, DataTable, Column } from '../../components/ui';

interface V2DashboardPageProps {
  cases?: Case[];
  shipments?: Shipment[];
  selectCaseForDetail?: (caseObj: Case) => void;
  synopsisMap?: Record<string, string>;
  setActiveTab?: (tab: string) => void;
}

export default function V2DashboardPage({ cases: propCases, selectCaseForDetail, setActiveTab }: V2DashboardPageProps) {
  const { cases: localCases, loading: casesLoading } = useV2Cases();
  const { threatFeed, loading: threatLoading } = useV2ThreatFeed();
  const cases = propCases || localCases;

  const [searchQuery, setSearchQuery] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [riskFilter, setRiskFilter] = useState('all');
  const [showUploadModal, setShowUploadModal] = useState(false);

  const filteredCases = cases.filter(c => {
    const q = searchQuery.toLowerCase();
    const matchesSearch = c.case_name.toLowerCase().includes(q) || c.target_entity.toLowerCase().includes(q) || c.case_id.toLowerCase().includes(q);
    const matchesPriority = priorityFilter === 'all' || c.priority.toLowerCase() === priorityFilter.toLowerCase();
    const matchesRisk = riskFilter === 'all' ||
      (riskFilter === 'high' && c.risk_score >= 80) ||
      (riskFilter === 'medium' && c.risk_score >= 50 && c.risk_score < 80) ||
      (riskFilter === 'low' && c.risk_score < 50);
    return matchesSearch && matchesPriority && matchesRisk;
  });

  const scoreColor = (s: number) => (s >= 80 ? '#D83933' : s >= 50 ? '#C7791B' : '#15803D');

  const columns: Column[] = [
    {
      key: 'risk_score', label: 'Score', render: c => (
        <div className="flex items-center gap-2">
          <div className="w-10 h-1.5 bg-slate-200 rounded-sm overflow-hidden"><div className="h-full" style={{ width: `${c.risk_score}%`, background: scoreColor(c.risk_score) }} /></div>
          <span className="font-mono font-bold" style={{ color: scoreColor(c.risk_score) }}>{c.risk_score}</span>
        </div>
      ),
    },
    {
      key: 'target_entity', label: 'Case / Entity', render: c => (
        <div><div className="font-semibold text-[#0B1F33]">{c.target_entity.split('/')[0]}</div><div className="text-[10px] font-mono text-[#5C5C5C]">{c.case_id}</div></div>
      ),
    },
    { key: 'product_category', label: 'Category', render: c => <span className="text-[#5C5C5C]">{c.product_category}</span> },
    { key: 'opened_date', label: 'Opened', align: 'right', mono: true },
    { key: 'sla_timer', label: 'SLA', align: 'right', render: c => <span className={`font-mono font-bold ${String(c.sla_timer).includes('Overdue') ? 'text-[#D83933]' : 'text-[#5C5C5C]'}`}>{c.sla_timer}</span> },
    {
      key: 'action', label: '', align: 'right', render: c => (
        <button onClick={() => selectCaseForDetail?.(c)}
          className="px-2.5 py-1 bg-[#005EA2] hover:bg-[#0b4f86] text-white text-[10px] font-bold rounded focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-[#005EA2] whitespace-nowrap">
          Workspace
        </button>
      ),
    },
  ];

  return (
    <div className="flex-1 p-5 flex flex-col space-y-4 overflow-y-auto bg-[#F7F9FC]">
      <section className="shrink-0">
        <EntityRiskDashboard onViewWatchlist={() => setActiveTab?.('entities')} />
      </section>

      {/* KPIs */}
      <StatStrip items={[
        { label: 'Critical Investigations', value: cases.filter(c => c.priority === 'Critical').length, color: '#D83933' },
        { label: 'High-Risk ≥80', value: cases.filter(c => c.risk_score >= 80).length, color: '#C7791B' },
        { label: 'Active Cases', value: cases.filter(c => c.case_status === 'Active').length },
        { label: 'Total Cases', value: cases.length },
      ]} />

      {/* Search + filters */}
      <div className="bg-white p-3 rounded-sm border border-[#D0D7DE] flex flex-col sm:flex-row sm:items-center gap-3 shrink-0">
        <div className="flex-1 relative flex items-center min-w-[220px]">
          <Search className="h-4 w-4 text-slate-400 absolute left-3" />
          <input type="text" value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search by entity name, case ID…"
            className="w-full bg-white border border-[#D0D7DE] rounded-sm pl-9 pr-4 py-1.5 text-[12px] text-[#0B1F33] focus:outline-none focus:ring-2 focus:ring-[#005EA2]" />
        </div>
        <label className="flex items-center gap-1.5 text-[11px] font-semibold text-[#5C5C5C]">PRIORITY
          <select value={priorityFilter} onChange={e => setPriorityFilter(e.target.value)} className="bg-white border border-[#D0D7DE] rounded px-2 py-1 text-[11px] text-[#0B1F33] focus:outline-none focus:ring-2 focus:ring-[#005EA2]">
            <option value="all">All</option><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option>
          </select>
        </label>
        <label className="flex items-center gap-1.5 text-[11px] font-semibold text-[#5C5C5C]">RISK
          <select value={riskFilter} onChange={e => setRiskFilter(e.target.value)} className="bg-white border border-[#D0D7DE] rounded px-2 py-1 text-[11px] text-[#0B1F33] focus:outline-none focus:ring-2 focus:ring-[#005EA2]">
            <option value="all">All</option><option value="high">High ≥80</option><option value="medium">Medium 50-79</option><option value="low">Low &lt;50</option>
          </select>
        </label>
        <button onClick={() => setShowUploadModal(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-[#005EA2] hover:bg-[#0b4f86] text-white rounded text-[11px] font-bold focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-[#005EA2]">
          <Upload className="w-3.5 h-3.5" /> Upload Manifest
        </button>
      </div>

      {/* Cases + threat feed */}
      <div className="flex-1 flex gap-4 overflow-hidden min-h-[320px]">
        <div className="flex-1 min-w-0">
          <Panel className="h-full flex flex-col">
            <SectionHeader title="Active Investigation Queue" subtitle={`${filteredCases.length} case${filteredCases.length === 1 ? '' : 's'}`} icon={<ListChecks className="w-4 h-4" />} />
            <div className="overflow-y-auto">
              {casesLoading
                ? <p className="text-[12px] text-[#5C5C5C] py-6 text-center">Loading cases…</p>
                : <DataTable columns={columns} rows={filteredCases} caption="Active investigation queue" empty="No cases match the current filters." />}
            </div>
          </Panel>
        </div>

        <div className="w-96 shrink-0">
          <Panel className="h-full flex flex-col">
            <SectionHeader title="Live Threat Feed" subtitle={`${threatFeed.length} event${threatFeed.length === 1 ? '' : 's'}`} icon={<Radio className="w-4 h-4" />} />
            <div className="overflow-y-auto divide-y divide-slate-100 -mx-1">
              {threatLoading ? (
                <p className="text-[12px] text-[#5C5C5C] py-6 text-center">Loading threat feed…</p>
              ) : threatFeed.length === 0 ? (
                <p className="text-[12px] text-[#5C5C5C] py-6 text-center">No active threats.</p>
              ) : threatFeed.map(event => (
                <div key={event.id} className="px-1 py-2.5">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`px-1.5 py-0.5 text-[10px] font-bold rounded uppercase ${event.severity === 'Critical' ? 'bg-red-100 text-red-800' : event.severity === 'High' ? 'bg-amber-100 text-amber-900' : 'bg-blue-100 text-blue-900'}`}>{event.severity}</span>
                    <span className="text-[10px] text-[#5C5C5C] font-mono">{event.confidence}%</span>
                  </div>
                  <h4 className="text-[11px] font-bold text-[#0B1F33]">{event.title}</h4>
                  <p className="text-[10px] text-[#5C5C5C] leading-snug mt-0.5 mb-1.5">{event.description}</p>
                  <div className="flex justify-between items-center">
                    <span className="text-[10px] text-slate-400 font-mono">{event.timestamp}</span>
                    {event.related_case_id && (
                      <button onClick={() => { const rc = cases.find(c => c.case_id === event.related_case_id); if (rc && selectCaseForDetail) selectCaseForDetail(rc); }}
                        className="text-[10px] text-[#005EA2] font-bold hover:underline">{event.related_case_id}</button>
                    )}
                  </div>
                </div>
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
