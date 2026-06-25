import React, { useState } from 'react';
import { Search, AlertTriangle, Coins, Shield, TrendingUp, Upload } from 'lucide-react';
import { useV2Cases } from '../hooks/useV2Cases';
import { useV2ThreatFeed } from '../hooks/useV2ThreatFeed';
import { Case, Shipment } from '../types/v2.types';
import UploadPipelineModal from '../../components/cases/UploadPipelineModal';
import EntityRiskDashboard from '../components/EntityRiskDashboard';

interface DashboardStats {
  criticalInvestigations: number;
  highRiskShipments: number;
  watchlistBlocks: number;
}

interface V2DashboardPageProps {
  cases?: Case[];
  shipments?: Shipment[];
  selectCaseForDetail?: (caseObj: Case) => void;
  synopsisMap?: Record<string, string>;
  setActiveTab?: (tab: string) => void;
}

export default function V2DashboardPage({ cases: propCases, shipments: propShipments, selectCaseForDetail, synopsisMap = {}, setActiveTab }: V2DashboardPageProps) {
  // Use passed props if available, otherwise fetch locally
  const { cases: localCases, loading: casesLoading } = useV2Cases();
  const { threatFeed: localThreatFeed, loading: threatLoading } = useV2ThreatFeed();

  const cases = propCases || localCases;
  const threatFeed = localThreatFeed;

  const [searchQuery, setSearchQuery] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [riskFilter, setRiskFilter] = useState('all');
  const [showUploadModal, setShowUploadModal] = useState(false);

  // Calculate stats
  const stats: DashboardStats = {
    criticalInvestigations: cases.filter(c => c.priority === 'Critical').length,
    highRiskShipments: cases.filter(c => c.risk_score >= 80).length,
    watchlistBlocks: cases.filter(c => c.case_status === 'Active').length,
  };

  // Filter cases
  const filteredCases = cases.filter(c => {
    const matchesSearch = c.case_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         c.target_entity.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         c.case_id.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesPriority = priorityFilter === 'all' || c.priority.toLowerCase() === priorityFilter.toLowerCase();
    const matchesRisk = riskFilter === 'all' ||
                       (riskFilter === 'high' && c.risk_score >= 80) ||
                       (riskFilter === 'medium' && c.risk_score >= 50 && c.risk_score < 80) ||
                       (riskFilter === 'low' && c.risk_score < 50);
    return matchesSearch && matchesPriority && matchesRisk;
  });

  return (
    <div className="flex-1 p-5 flex flex-col space-y-5 overflow-y-auto bg-[#F7F9FC]">
      {/* Entity Risk Dashboard (NEW) */}
      <section className="shrink-0">
        <EntityRiskDashboard onViewWatchlist={() => setActiveTab?.('entities')} />
      </section>

      {/* Summary Cards */}
      <section className="grid grid-cols-2 lg:grid-cols-3 gap-3 shrink-0">
        <div className="bg-white border-l-4 border-[#D83933] border-t border-b border-r border-slate-200 p-3 rounded-sm flex flex-col justify-between shadow-sm">
          <span className="text-[9px] text-[#5C5C5C] font-mono uppercase font-bold tracking-wider">Critical Investigations</span>
          <span className="text-2xl font-black font-mono tracking-tight text-[#0B1F33] mt-1">{stats.criticalInvestigations}</span>
          <span className="text-[9px] text-[#D83933] font-bold font-mono">⚠️ PRIORITY ESCALATION</span>
        </div>

        <div className="bg-white border-l-4 border-amber-500 border-t border-b border-r border-slate-200 p-3 rounded-sm flex flex-col justify-between shadow-sm">
          <span className="text-[9px] text-[#5C5C5C] font-mono uppercase font-bold tracking-wider">Anomalous Manifest Volume</span>
          <span className="text-2xl font-black font-mono tracking-tight text-[#0B1F33] mt-1">{stats.highRiskShipments}</span>
          <span className="text-[9px] text-[#5C5C5C] font-mono font-medium">Overloaded containers detected</span>
        </div>

        <div className="bg-white border-l-4 border-[#00BDE3] border-t border-b border-r border-slate-200 p-3 rounded-sm flex flex-col justify-between shadow-sm">
          <span className="text-[9px] text-[#5C5C5C] font-mono uppercase font-bold tracking-wider">UFLPA Watchlist Blocks</span>
          <span className="text-2xl font-black font-mono tracking-tight text-[#0B1F33] mt-1">{stats.watchlistBlocks}</span>
          <span className="text-[9px] text-[#00BDE3] font-bold font-mono">MATCHED VENDOR BLOCKS</span>
        </div>
      </section>

      {/* Search & Filter Bar */}
      <div className="bg-white p-3 rounded-sm border border-[#D0D7DE] flex flex-col sm:flex-row sm:items-center space-y-2.5 sm:space-y-0 sm:space-x-4 shrink-0 shadow-sm">
        <div className="flex-1 relative flex items-center">
          <Search className="h-4 w-4 text-slate-400 absolute left-3" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Audit Search query (e.g., entity name, case ID...)"
            className="w-full bg-[#F7F9FC] border border-[#D0D7DE] rounded-sm pl-9 pr-4 py-1.5 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-[#005EA2] transition-colors"
          />
        </div>

        <div className="flex items-center space-x-3.5 text-xs font-mono font-bold shrink-0">
          <div className="flex items-center space-x-1.5">
            <span className="text-[#5C5C5C] uppercase text-[10px]">Priority:</span>
            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="bg-slate-50 border border-slate-300 rounded px-2 py-1 text-xs text-slate-800 focus:outline-none focus:border-[#005EA2]"
            >
              <option value="all">ALL STAGES</option>
              <option value="critical">CRITICAL</option>
              <option value="high">HIGH</option>
              <option value="medium">MEDIUM</option>
            </select>
          </div>

          <div className="flex items-center space-x-1.5">
            <span className="text-[#5C5C5C] uppercase text-[10px]">Risk Score:</span>
            <select
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value)}
              className="bg-slate-50 border border-slate-300 rounded px-2 py-1 text-xs text-slate-800 focus:outline-none focus:border-[#005EA2]"
            >
              <option value="all">ALL SCORES</option>
              <option value="high">HIGH (≥80)</option>
              <option value="medium">MEDIUM (50-79)</option>
              <option value="low">LOW (&lt;50)</option>
            </select>
          </div>

          <button
            onClick={() => setShowUploadModal(true)}
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-[#0076D6] hover:bg-[#005EA2] text-white rounded text-xs font-bold transition-colors"
            title="Upload manifest"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Upload Manifest</span>
          </button>
        </div>
      </div>

      {/* Main Content: Cases + Threat Feed */}
      <div className="flex-1 flex gap-4 overflow-hidden">
        {/* Cases Table */}
        <div className="flex-1 flex flex-col bg-white border border-[#D0D7DE] rounded-sm overflow-hidden shadow-sm">
          <div className="bg-[#F0F4F8] p-3 border-b border-[#D0D7DE] font-mono text-xs font-bold text-[#112E51] uppercase">
            Active Investigation Queue ({filteredCases.length})
          </div>
          <div className="flex-1 overflow-y-auto">
            <table className="w-full text-left text-xs border-collapse font-sans">
              <thead className="bg-[#F0F4F8] sticky top-0 z-10">
                <tr className="border-b border-[#D0D7DE]">
                  <th className="p-3 font-bold text-[#112E51] w-20">SCORE</th>
                  <th className="p-3 font-bold text-[#112E51]">ID / NAME</th>
                  <th className="p-3 font-bold text-[#112E51]">ENTITY / CATEGORY</th>
                  <th className="p-3 font-bold text-[#112E51]">OPENED</th>
                  <th className="p-3 font-bold text-[#112E51]">SLA</th>
                  <th className="p-3 font-bold text-[#112E51] text-right">ACTIONS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E0E3E8]">
                {casesLoading ? (
                  <tr><td colSpan={6} className="p-4 text-center text-gray-500">Loading cases...</td></tr>
                ) : filteredCases.length === 0 ? (
                  <tr><td colSpan={6} className="p-4 text-center text-gray-500">No cases match filters</td></tr>
                ) : (
                  filteredCases.map((c) => (
                    <tr
                      key={c.case_id}
                      onClick={() => selectCaseForDetail?.(c)}
                      className="hover:bg-[#F7F9FC] transition-all cursor-pointer"
                    >
                      <td className="p-3">
                        <span
                          className={`inline-block px-2.5 py-1 rounded text-center font-bold text-xs text-white ${
                            c.risk_score >= 80 ? 'bg-[#D83933]' : 'bg-amber-600'
                          }`}
                        >
                          {c.risk_score}%
                        </span>
                      </td>
                      <td className="p-3">
                        <div className="flex flex-col">
                          <span className="font-bold text-[#0B1F33]">{c.target_entity.split('/')[0]}</span>
                          <span className="text-[10px] text-[#5C5C5C] font-mono block mt-0.5">{c.case_id}</span>
                        </div>
                      </td>
                      <td className="p-3">{c.product_category}</td>
                      <td className="p-3 font-mono text-[#5C5C5C]">{c.opened_date}</td>
                      <td className={`p-3 font-bold font-mono ${c.sla_timer.includes('Overdue') ? 'text-[#D83933]' : 'text-[#5C5C5C]'}`}>
                        {c.sla_timer}
                      </td>
                      <td className="p-3 text-right">
                        <button
                          onClick={() => selectCaseForDetail?.(c)}
                          className="px-3 py-1.5 bg-[#112E51] hover:bg-[#005EA2] text-white text-[10px] font-bold rounded-sm transition-colors whitespace-nowrap"
                        >
                          WORKSPACE
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Threat Feed */}
        <div className="w-96 flex flex-col bg-white border border-[#D0D7DE] rounded-sm overflow-hidden shadow-sm">
          <div className="bg-[#F7F9FC] p-3 border-b border-[#D0D7DE] font-mono text-xs font-bold text-[#112E51] uppercase">
            Live Threat Feed ({threatFeed.length})
          </div>
          <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
            {threatLoading ? (
              <div className="p-4 text-center text-gray-500 text-xs">Loading threat feed...</div>
            ) : threatFeed.length === 0 ? (
              <div className="p-4 text-center text-gray-500 text-xs">No active threats</div>
            ) : (
              threatFeed.map((event) => (
                <div key={event.id} className="p-3 hover:bg-slate-50 transition-all">
                  <div className="flex items-start space-x-2 mb-1">
                    <span className={`px-1.5 py-0.5 text-[9px] font-mono font-bold rounded whitespace-nowrap ${
                      event.severity === 'Critical' ? 'bg-[#D83933] text-white' :
                      event.severity === 'High' ? 'bg-amber-100 text-amber-900' :
                      'bg-blue-100 text-blue-900'
                    }`}>
                      {event.severity}
                    </span>
                    <span className="text-[10px] text-[#5C5C5C] font-mono">{event.confidence}%</span>
                  </div>
                  <h4 className="text-[10px] font-bold text-[#0B1F33] mb-1">{event.title}</h4>
                  <p className="text-[9px] text-[#5C5C5C] leading-snug mb-2">{event.description}</p>
                  <div className="flex justify-between items-center">
                    <span className="text-[9px] text-gray-400 font-mono">{event.timestamp}</span>
                    {event.related_case_id && (
                      <button
                        onClick={() => {
                          const relatedCase = cases.find(c => c.case_id === event.related_case_id);
                          if (relatedCase && selectCaseForDetail) {
                            selectCaseForDetail(relatedCase);
                          }
                        }}
                        className="text-[9px] text-[#005EA2] font-bold hover:underline cursor-pointer"
                      >
                        {event.related_case_id}
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Upload Manifest Modal */}
      {showUploadModal && (
        <UploadPipelineModal
          onClose={() => setShowUploadModal(false)}
          onComplete={() => {
            setShowUploadModal(false);
            // Refresh cases after upload
            window.location.reload();
          }}
        />
      )}
    </div>
  );
}
