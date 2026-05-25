import React from 'react';
import { Search, ArrowRight } from 'lucide-react';
import { TYPOGRAPHY, DESIGN } from '../styles/typography';

export interface ListItem {
  id: string;
  risk_score?: number;
  name: string;
  entity: string;
  officer?: string;
  commodity: string;
  date: string;
  status: string;
  statusColor?: string;
}

interface InvestigationListTableProps {
  items: ListItem[];
  title: string;
  subtitle?: string;
  searchPlaceholder?: string;
  onRowClick: (itemId: string) => void;
  onAccessWorkspace: (itemId: string) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  priorityFilter: string;
  onPriorityFilterChange: (filter: string) => void;
  riskFilter: string;
  onRiskFilterChange: (filter: string) => void;
  onClearFilters: () => void;
  loading?: boolean;
}

export default function InvestigationListTable({
  items,
  title,
  subtitle,
  searchPlaceholder = 'Filter by name, entity, or ID...',
  onRowClick,
  onAccessWorkspace,
  searchQuery,
  onSearchChange,
  priorityFilter,
  onPriorityFilterChange,
  riskFilter,
  onRiskFilterChange,
  onClearFilters,
  loading = false,
}: InvestigationListTableProps) {
  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className={`${DESIGN.bgWhite} p-4 border ${DESIGN.borderColor} rounded-sm flex justify-between items-center mb-4 shadow-sm`}>
        <div>
          <h2 className={`${TYPOGRAPHY.sectionTitle} uppercase flex items-center space-x-2 mb-0`}>
            <span>{title}</span>
          </h2>
          {subtitle && <p className={`${TYPOGRAPHY.smallText} mt-1`}>{subtitle}</p>}
        </div>
        <button
          onClick={onClearFilters}
          className={`px-3 py-1.5 border ${DESIGN.borderColor} hover:${DESIGN.bgLight} text-xs font-bold rounded-sm ${DESIGN.textDark} cursor-pointer`}
        >
          CLEAR ALL
        </button>
      </div>

      {/* Filter Controls */}
      <div className={`${DESIGN.bgWhite} p-3.5 rounded-sm border ${DESIGN.borderColor} flex flex-col md:flex-row md:items-center gap-4 mb-4 shadow-sm`}>
        <div className="flex-1 relative flex items-center">
          <Search className="h-4 w-4 text-slate-400 absolute left-3" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder={searchPlaceholder}
            className={`w-full ${DESIGN.bgLight} border ${DESIGN.borderColor} rounded-sm pl-9 pr-4 py-1.5 text-xs ${DESIGN.textDark} focus:outline-none focus:border-[#005EA2]`}
          />
        </div>

        <select
          value={priorityFilter}
          onChange={(e) => onPriorityFilterChange(e.target.value)}
          className={`${DESIGN.bgLight} border ${DESIGN.borderColor} rounded px-2.5 py-1.5 text-xs ${DESIGN.textDark} focus:outline-none focus:border-[#005EA2] font-bold`}
        >
          <option value="all">PRIORITY: ALL</option>
          <option value="critical">CRITICAL</option>
          <option value="high">HIGH</option>
          <option value="medium">MEDIUM</option>
        </select>

        <select
          value={riskFilter}
          onChange={(e) => onRiskFilterChange(e.target.value)}
          className={`${DESIGN.bgLight} border ${DESIGN.borderColor} rounded px-2.5 py-1.5 text-xs ${DESIGN.textDark} focus:outline-none focus:border-[#005EA2] font-bold`}
        >
          <option value="all">RISK MATRIX: ALL</option>
          <option value="critical">CRITICAL (≥80)</option>
          <option value="elevated">ELEVATED (50-79)</option>
        </select>
      </div>

      {/* List Table */}
      <div className={`${DESIGN.bgWhite} rounded-sm border ${DESIGN.borderColor} shadow-sm flex-1 overflow-auto`}>
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className={`text-center ${DESIGN.textGray} text-xs`}>Loading...</div>
          </div>
        ) : items.length === 0 ? (
          <div className={`py-12 text-center ${DESIGN.textGray} italic`}>
            No items matched your filters. Try resetting.
          </div>
        ) : (
          <table className="w-full text-left border-collapse">
            <thead className={`sticky top-0 bg-[#F0F4F8] border-b ${DESIGN.borderColor}`}>
              <tr>
                <th className={`${TYPOGRAPHY.tableHeader} p-3 w-20`}>SCORE</th>
                <th className={`${TYPOGRAPHY.tableHeader} p-3`}>ID / NAME</th>
                <th className={`${TYPOGRAPHY.tableHeader} p-3`}>ENTITY / SHIPPER</th>
                <th className={`${TYPOGRAPHY.tableHeader} p-3`}>COMMODITY</th>
                <th className={`${TYPOGRAPHY.tableHeader} p-3`}>DATE</th>
                <th className={`${TYPOGRAPHY.tableHeader} p-3`}>STATUS</th>
                <th className={`${TYPOGRAPHY.tableHeader} p-3 text-right`}>ACTIONS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E0E3E8]">
              {items.map((item) => (
                <tr
                  key={item.id}
                  className="hover:bg-[#F7F9FC] transition-all cursor-pointer"
                  onClick={() => onRowClick(item.id)}
                >
                  <td className={`${TYPOGRAPHY.tableCell} p-3`}>
                    <span
                      className={`inline-block px-2.5 py-1 rounded text-center font-bold text-xs text-white ${
                        (item.risk_score ?? 0) >= 80 ? 'bg-[#D83933]' : 'bg-amber-600'
                      }`}
                    >
                      {item.risk_score}%
                    </span>
                  </td>
                  <td className={`${TYPOGRAPHY.tableCell} p-3`}>
                    <div className="flex flex-col">
                      <span className="font-bold text-[#0B1F33]">{item.name}</span>
                      <span className={`${TYPOGRAPHY.tableMono} block mt-0.5`}>{item.id}</span>
                    </div>
                  </td>
                  <td className={`${TYPOGRAPHY.tableCell} p-3`}>{item.entity}</td>
                  <td className={`${TYPOGRAPHY.tableCell} p-3 text-[11px]`}>{item.commodity}</td>
                  <td className={`${TYPOGRAPHY.tableMono} p-3`}>{item.date}</td>
                  <td className={`${TYPOGRAPHY.tableCell} p-3`}>
                    <span
                      className={`px-2 py-0.5 text-[10px] rounded font-bold ${
                        item.statusColor || 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {item.status}
                    </span>
                  </td>
                  <td className={`${TYPOGRAPHY.tableCell} p-3 text-right`}>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onAccessWorkspace(item.id);
                      }}
                      className="px-3 py-1.5 bg-[#0076D6] hover:bg-[#005EA2] text-white text-[10px] font-bold rounded-sm flex items-center space-x-1 ml-auto transition-colors whitespace-nowrap"
                    >
                      <ArrowRight className="h-3 w-3" />
                      <span>Workspace</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
