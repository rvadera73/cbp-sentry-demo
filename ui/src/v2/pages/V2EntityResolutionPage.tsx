import React, { useState, useMemo } from 'react';
import { Search, ChevronRight } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell } from 'recharts';
import { TYPOGRAPHY, DESIGN } from '../styles/typography';

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
  {
    entity_id: 'ENT-GF-VN-001',
    entity_name: 'Greenfield Industrial Trading Co., Ltd.',
    entity_type: 'Shipper',
    risk_score: 65,
    risk_level: 'HIGH',
    last_seen: '2026-05-27',
    flag_reason: 'Prior EAPA determination',
    related_count: 3,
  },
  {
    entity_id: 'ENT-SP-US-001',
    entity_name: 'SunPath Energy Distributors LLC',
    entity_type: 'Consignee',
    risk_score: 52,
    risk_level: 'MEDIUM',
    last_seen: '2026-05-26',
    flag_reason: 'Prior evasion case',
    related_count: 1,
  },
  {
    entity_id: 'ENT-SOL-MY-001',
    entity_name: 'Solaria Manufacturing Sdn. Bhd.',
    entity_type: 'Shipper',
    risk_score: 48,
    risk_level: 'MEDIUM',
    last_seen: '2026-05-25',
    flag_reason: 'New shipper + transshipment pattern',
    related_count: 2,
  },
  {
    entity_id: 'ENT-PAN-PAC-001',
    entity_name: 'Pan-Pacific Logistics, Inc.',
    entity_type: 'Freight Forwarder',
    risk_score: 38,
    risk_level: 'LOW',
    last_seen: '2026-05-27',
    flag_reason: 'Shared with high-risk entities',
    related_count: 5,
  },
  {
    entity_id: 'ENT-OCS-HK-001',
    entity_name: 'Ocean Shipping Inc.',
    entity_type: 'Operator',
    risk_score: 35,
    risk_level: 'LOW',
    last_seen: '2026-05-24',
    flag_reason: 'Vessel operates high-risk corridors',
    related_count: 2,
  },
];

export default function V2EntityResolutionPage({
  selectedEntityId,
  setSelectedEntityId,
  setActiveTab,
}: V2EntityResolutionPageProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [riskFilter, setRiskFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  const filteredEntities = useMemo(() => {
    return FIXTURE_WATCHLIST.filter(entity => {
      const matchesSearch =
        entity.entity_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        entity.entity_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        entity.flag_reason.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesRisk =
        riskFilter === 'all' ||
        (riskFilter === 'critical' && entity.risk_level === 'CRITICAL') ||
        (riskFilter === 'high' && entity.risk_level === 'HIGH') ||
        (riskFilter === 'medium' && entity.risk_level === 'MEDIUM') ||
        (riskFilter === 'low' && entity.risk_level === 'LOW');

      const matchesType = typeFilter === 'all' || entity.entity_type === typeFilter;

      return matchesSearch && matchesRisk && matchesType;
    }).sort((a, b) => b.risk_score - a.risk_score);
  }, [searchQuery, riskFilter, typeFilter]);

  const totalPages = Math.ceil(filteredEntities.length / itemsPerPage);
  const paginatedEntities = filteredEntities.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  const getRiskColor = (level: string): string => {
    switch (level) {
      case 'CRITICAL':
        return '#D83933';
      case 'HIGH':
        return '#FF9500';
      case 'MEDIUM':
        return '#F59E0B';
      case 'LOW':
        return '#22c55e';
      default:
        return '#8B7D6B';
    }
  };

  const riskDistributionChart = useMemo(() => {
    const counts = {
      CRITICAL: filteredEntities.filter(e => e.risk_level === 'CRITICAL').length,
      HIGH: filteredEntities.filter(e => e.risk_level === 'HIGH').length,
      MEDIUM: filteredEntities.filter(e => e.risk_level === 'MEDIUM').length,
      LOW: filteredEntities.filter(e => e.risk_level === 'LOW').length,
    };
    return [
      { name: 'CRIT', value: counts.CRITICAL, fill: '#D83933' },
      { name: 'HIGH', value: counts.HIGH, fill: '#FF9500' },
      { name: 'MED', value: counts.MEDIUM, fill: '#F59E0B' },
      { name: 'LOW', value: counts.LOW, fill: '#22c55e' },
    ];
  }, [filteredEntities]);

  const handleViewEntity = (entityId: string) => {
    setSelectedEntityId?.(entityId);
    setActiveTab?.('entity-workspace');
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-[#F7F9FC]">
      {/* Header */}
      <div className={`${DESIGN.bgWhite} border-b ${DESIGN.borderColor} px-6 py-4 shadow-sm`}>
        <h1 className={TYPOGRAPHY.pageTitle}>ENTITY RESOLUTION</h1>
        <p className={TYPOGRAPHY.pageSubtitle}>Active Watchlist • Pre-Arrival Intelligence • Risk Monitoring</p>
      </div>

      {/* Search & Filter Bar */}
      <div className={`${DESIGN.bgWhite} border-b ${DESIGN.borderColor} px-6 py-3 space-y-2`}>
        {/* Search */}
        <div className="relative flex items-center">
          <Search className="h-4 w-4 text-slate-400 absolute left-3" />
          <input
            type="text"
            placeholder="Search by entity name, ID, or flag reason..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            className={`w-full pl-9 pr-4 py-1.5 border ${DESIGN.borderColor} rounded-sm text-sm ${DESIGN.textDark} focus:outline-none focus:border-[#0076D6]`}
          />
        </div>

        {/* Filters + Risk Distribution */}
        <div className="flex items-center gap-4 text-xs font-bold">
          {/* Filter Dropdowns */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5">
              <span className={DESIGN.textGray}>RISK:</span>
              <select
                value={riskFilter}
                onChange={(e) => {
                  setRiskFilter(e.target.value);
                  setCurrentPage(1);
                }}
                className={`bg-slate-50 border ${DESIGN.borderColor} rounded px-2 py-1 text-xs ${DESIGN.textDark} focus:outline-none`}
              >
                <option value="all">ALL</option>
                <option value="critical">CRIT</option>
                <option value="high">HIGH</option>
                <option value="medium">MED</option>
                <option value="low">LOW</option>
              </select>
            </div>

            <div className="flex items-center gap-1.5">
              <span className={DESIGN.textGray}>TYPE:</span>
              <select
                value={typeFilter}
                onChange={(e) => {
                  setTypeFilter(e.target.value);
                  setCurrentPage(1);
                }}
                className={`bg-slate-50 border ${DESIGN.borderColor} rounded px-2 py-1 text-xs ${DESIGN.textDark} focus:outline-none`}
              >
                <option value="all">ALL</option>
                <option value="Shipper">Ship</option>
                <option value="Consignee">Cons</option>
                <option value="Operator">Op</option>
                <option value="Freight Forwarder">FF</option>
              </select>
            </div>
          </div>

          {/* Risk Distribution Chart */}
          <div className="flex-1 flex items-center" style={{ height: '30px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={riskDistributionChart} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                <Bar dataKey="value" radius={[2, 2, 0, 0]} label={{ position: 'top', fontSize: 9, fill: '#5C5C5C' }}>
                  {riskDistributionChart.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Entity Watchlist Table */}
      <div className="flex-1 overflow-hidden flex flex-col">
        <div className={`${DESIGN.bgWhite} border ${DESIGN.borderColor} rounded-sm m-6 flex flex-col overflow-hidden flex-1`}>
          <div className="bg-[#F0F4F8] p-3 border-b border-[#D0D7DE]">
            <h3 className={TYPOGRAPHY.tableHeader}>ENTITY WATCHLIST ({filteredEntities.length})</h3>
          </div>

          <div className="flex-1 overflow-y-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-[#F0F4F8] sticky top-0 z-10">
                <tr className="border-b border-[#D0D7DE]">
                  <th className={`${TYPOGRAPHY.tableHeader} px-3 py-2 w-16`}>RISK</th>
                  <th className={`${TYPOGRAPHY.tableHeader} px-3 py-2`}>ENTITY NAME</th>
                  <th className={`${TYPOGRAPHY.tableHeader} px-3 py-2 w-20`}>TYPE</th>
                  <th className={`${TYPOGRAPHY.tableHeader} px-3 py-2`}>REASON</th>
                  <th className={`${TYPOGRAPHY.tableHeader} px-3 py-2 w-20`}>SEEN</th>
                  <th className={`${TYPOGRAPHY.tableHeader} px-3 py-2 text-center w-12`}>REL</th>
                  <th className={`${TYPOGRAPHY.tableHeader} px-3 py-2 text-right w-20`}>ACTION</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E0E3E8]">
                {paginatedEntities.map((entity) => (
                  <tr key={entity.entity_id} className="hover:bg-[#F7F9FC] transition-colors">
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-1">
                        <div
                          style={{
                            width: '28px',
                            height: '6px',
                            background: getRiskColor(entity.risk_level),
                            borderRadius: '2px',
                          }}
                        />
                        <span className="text-[8px] font-bold text-[#5C5C5C]">{entity.risk_score}%</span>
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex flex-col">
                        <span className="font-bold text-[#0B1F33] truncate">{entity.entity_name}</span>
                        <span className={`text-[8px] text-[#5C5C5C] mt-0.5`}>{entity.entity_id}</span>
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      <span className="text-[8px] bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded font-bold uppercase">
                        {entity.entity_type.substring(0, 4)}
                      </span>
                    </td>
                    <td className={`px-3 py-2 ${DESIGN.textGray} text-[8px] truncate`}>{entity.flag_reason}</td>
                    <td className={`px-3 py-2 font-mono ${DESIGN.textGray} text-[8px]`}>{entity.last_seen}</td>
                    <td className="px-3 py-2 text-center">
                      <span className="text-[8px] font-bold text-[#0076D6]">{entity.related_count}</span>
                    </td>
                    <td className="px-3 py-2 text-right">
                      <button
                        onClick={() => handleViewEntity(entity.entity_id)}
                        className="flex items-center gap-0.5 px-2 py-1 bg-[#0076D6] hover:bg-[#005EA2] text-white rounded text-[8px] font-bold transition-colors whitespace-nowrap"
                      >
                        <span>WS</span>
                        <ChevronRight className="w-2.5 h-2.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="bg-[#F0F4F8] p-3 border-t border-[#D0D7DE] flex items-center justify-between text-xs">
              <span className={DESIGN.textGray}>
                Page {currentPage} of {totalPages}
              </span>
              <div className="space-x-2">
                <button
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="px-2 py-1 bg-white border border-[#D0D7DE] rounded disabled:opacity-50 hover:bg-slate-50"
                >
                  ← Previous
                </button>
                <button
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="px-2 py-1 bg-white border border-[#D0D7DE] rounded disabled:opacity-50 hover:bg-slate-50"
                >
                  Next →
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
