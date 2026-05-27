import React, { useState } from 'react';
import { Search, AlertTriangle, ChevronRight, Network } from 'lucide-react';
import { useV2Entities } from '../hooks/useV2Entities';
import { TradeEntity } from '../types/v2.types';
import { TYPOGRAPHY, DESIGN } from '../styles/typography';
import { EntityRelationshipGraph } from '../components/EntityRelationshipGraph';

export default function V2EntitiesPage() {
  const { entities, selectedEntity, selectEntity, searchEntities, loading } = useV2Entities();
  const [searchQuery, setSearchQuery] = useState('');
  const [viewingGraph, setViewingGraph] = useState(false);

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    if (query.length >= 2) {
      searchEntities(query);
    }
  };

  const getRiskPriority = (riskLevel: string): number => {
    const priorityMap: { [key: string]: number } = {
      'Critical': 0,
      'High': 1,
      'Medium': 2,
      'Low': 3,
      'Verified': 4,
    };
    return priorityMap[riskLevel] ?? 5;
  };

  const sortedEntities = [...entities].sort((a, b) => {
    return getRiskPriority(a.risk_level) - getRiskPriority(b.risk_level);
  });

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className={`${DESIGN.bgWhite} border-b ${DESIGN.borderColor} px-6 py-4 shadow-sm`}>
        <h1 className={TYPOGRAPHY.pageTitle}>Entity Resolution</h1>
        <p className={TYPOGRAPHY.pageSubtitle}>Identify and track trade entities across networks</p>
      </div>

      {/* List View */}
      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Search Bar */}
          <div className={`${DESIGN.bgWhite} border-b ${DESIGN.borderColor} px-6 py-4`}>
            <div className="relative flex items-center">
              <Search className="h-4 w-4 text-slate-400 absolute left-3" />
              <input
                type="text"
                placeholder="Search by entity name, tax ID, country..."
                value={searchQuery}
                onChange={(e) => handleSearch(e.target.value)}
                className={`w-full pl-9 pr-4 py-2 border ${DESIGN.borderColor} rounded-sm text-sm ${DESIGN.textDark} focus:outline-none focus:border-[#005EA2]`}
              />
            </div>
          </div>

          {/* Entity Table */}
          <div className="flex-1 overflow-auto">
            <div className={`${DESIGN.bgWhite} border ${DESIGN.borderColor} rounded-sm shadow-sm h-full`}>
              {loading ? (
                <div className="flex items-center justify-center h-full">
                  <div className={`text-center ${DESIGN.textGray} text-xs`}>Searching entities...</div>
                </div>
              ) : sortedEntities.length === 0 ? (
                <div className="flex items-center justify-center h-full">
                  <div className={`text-center ${DESIGN.textGray} text-xs italic`}>No entities found. Try searching with different keywords.</div>
                </div>
              ) : (
                <table className="w-full text-left border-collapse">
                  <thead className={`sticky top-0 bg-[#F0F4F8] border-b ${DESIGN.borderColor}`}>
                    <tr>
                      <th className={`${TYPOGRAPHY.tableHeader} p-3`}>ENTITY NAME / ID</th>
                      <th className={`${TYPOGRAPHY.tableHeader} p-3 w-20`}>TYPE</th>
                      <th className={`${TYPOGRAPHY.tableHeader} p-3 w-20`}>COUNTRY</th>
                      <th className={`${TYPOGRAPHY.tableHeader} p-3 w-24`}>TAX ID</th>
                      <th className={`${TYPOGRAPHY.tableHeader} p-3 w-24`}>STATUS</th>
                      <th className={`${TYPOGRAPHY.tableHeader} p-3 text-right`}>ACTIONS</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E0E3E8]">
                    {sortedEntities.map((e) => (
                      <tr
                        key={e.entity_id}
                        className="hover:bg-[#F7F9FC] transition-colors cursor-pointer"
                        onClick={() => {
                          selectEntity(e.entity_id).catch(err => console.error('Error selecting entity:', err));
                        }}
                      >
                        <td className={`${TYPOGRAPHY.tableCell} p-3`}>
                          <div className="flex flex-col">
                            <span className="font-bold">{e.entity_name}</span>
                            <span className={`${TYPOGRAPHY.tableMono} mt-0.5`}>{e.entity_id}</span>
                          </div>
                        </td>
                        <td className={`${TYPOGRAPHY.tableCell} p-3`}>
                          <span className="text-[9px] bg-slate-100 text-slate-700 px-2 py-1 rounded">
                            {e.entity_type}
                          </span>
                        </td>
                        <td className={`${TYPOGRAPHY.tableCell} p-3`}>{e.country}</td>
                        <td className={`${TYPOGRAPHY.tableMono} p-3`}>{e.tax_id || '—'}</td>
                        <td className={`${TYPOGRAPHY.tableCell} p-3`}>
                          <span className={`text-[10px] font-bold ${
                            e.watchlist_status === 'Flagged' ? 'text-[#D83933]' : 'text-green-600'
                          }`}>
                            {e.watchlist_status}
                          </span>
                        </td>
                        <td className={`${TYPOGRAPHY.tableCell} p-3 text-right`}>
                          <button
                            onClick={(ev) => {
                              ev.stopPropagation();
                              selectEntity(e.entity_id);
                              setViewingGraph(false);
                            }}
                            className="px-3 py-1.5 bg-[#112E51] hover:bg-[#005EA2] text-white text-[10px] font-bold rounded-sm transition-colors whitespace-nowrap ml-auto"
                          >
                            WORKSPACE
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>

        {/* Detail Panel */}
        {selectedEntity && (
          <div className={`flex-1 border-l ${DESIGN.borderColor} ${DESIGN.bgWhite} overflow-y-auto flex flex-col`}>
          {/* Back Button */}
          <div className="bg-[#F7F9FC] border-b border-[#D0D7DE] px-6 py-2 shrink-0">
            <button
              onClick={() => selectEntity('')}
              className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 border border-slate-300 text-[#005EA2] hover:text-[#0076D6] text-xs font-bold rounded-sm flex items-center space-x-1 transition-colors"
            >
              <span>←</span>
              <span>BACK TO QUEUE</span>
            </button>
          </div>

          {/* Entity Details - Compact Format */}
          <div className="p-6 space-y-4 overflow-y-auto flex-1">
            {/* Row 1: Entity Identity */}
            <div className={`${DESIGN.bgWhite} border ${DESIGN.borderColor} rounded-sm p-4`}>
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <p className="text-xs font-bold text-[#0B1F33] uppercase">{selectedEntity.entity_name}</p>
                  <p className="text-[9px] text-slate-600 mt-1">ID: {selectedEntity.entity_id}</p>
                </div>
                <span className={`px-2.5 py-1 rounded font-extrabold text-xs text-white ${
                  selectedEntity.watchlist_status === 'Flagged' ? 'bg-[#D83933]' : 'bg-green-600'
                }`}>
                  {selectedEntity.watchlist_status}
                </span>
              </div>
            </div>

            {/* Row 2: Entity Details Grid */}
            <div className={`${DESIGN.bgWhite} border ${DESIGN.borderColor} rounded-sm p-4`}>
              <div className="grid grid-cols-4 gap-3 text-[9px]">
                <div>
                  <p className="text-slate-600 font-bold uppercase">Type</p>
                  <p className="text-[#0B1F33] font-medium mt-0.5">{selectedEntity.entity_type}</p>
                </div>
                <div>
                  <p className="text-slate-600 font-bold uppercase">Country</p>
                  <p className="text-[#0B1F33] font-medium mt-0.5">{selectedEntity.country}</p>
                </div>
                <div>
                  <p className="text-slate-600 font-bold uppercase">Tax ID</p>
                  <p className="text-[#0B1F33] font-medium mt-0.5">{selectedEntity.tax_id || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-slate-600 font-bold uppercase">Source</p>
                  <p className="text-[#0B1F33] font-medium mt-0.5">CORD</p>
                </div>
              </div>
            </div>

            {/* Entity Relationship Network Graph */}
            <div className={`${DESIGN.bgWhite} border ${DESIGN.borderColor} rounded-sm p-4`}>
              <EntityRelationshipGraph
                chain={selectedEntity.entity_chain}
                parties={selectedEntity.parties}
              />
            </div>

            {/* OFAC & Enforcement History */}
            {(selectedEntity.risk_level === 'Critical' || selectedEntity.watchlist_status === 'Flagged') && (
              <div className={`${DESIGN.bgWhite} border border-[#D83933] rounded-sm p-4`}>
                <h3 className="text-xs font-bold text-[#D83933] uppercase mb-3">⚠️ RISK ASSESSMENT</h3>
                <div className="space-y-2 text-[9px]">
                  {selectedEntity.risk_level === 'Critical' && (
                    <div className="p-2 bg-red-50 border border-red-200 rounded">
                      <p className="font-bold text-red-700">🚩 OFAC SDN MATCH - CRITICAL</p>
                      <p className="text-red-600 mt-0.5">Entity is on OFAC Specially Designated Nationals List</p>
                    </div>
                  )}
                  {selectedEntity.risk_level === 'High' && (
                    <div className="p-2 bg-orange-50 border border-orange-200 rounded">
                      <p className="font-bold text-orange-700">⚠️ SANCTIONS WATCH LIST - HIGH RISK</p>
                      <p className="text-orange-600 mt-0.5">Entity is under sanctions monitoring</p>
                    </div>
                  )}
                </div>
              </div>
            )}
            {/* Party Associations */}

            {/* Party Table */}
            {selectedEntity.parties && selectedEntity.parties.length > 0 && (
              <section>
                <h3 className={`text-xs font-bold text-[#5C5C5C] uppercase mb-3 tracking-wider`}>Supply Chain Parties</h3>
                <div className={`overflow-x-auto border ${DESIGN.borderColor} rounded`}>
                  <table className="w-full text-left text-[9px]">
                    <thead className="bg-[#F0F4F8] border-b border-[#D0D7DE]">
                      <tr>
                        <th className="p-2 font-bold text-[#0B1F33]">ROLE</th>
                        <th className="p-2 font-bold text-[#0B1F33]">ENTITY</th>
                        <th className="p-2 font-bold text-[#0B1F33]">COUNTRY</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#E0E3E8]">
                      {selectedEntity.parties.slice(0, 5).map((party, idx) => (
                        <tr key={idx} className="hover:bg-[#F7F9FC]">
                          <td className="p-2 font-bold text-[#0B1F33]">{party.role}</td>
                          <td className="p-2 text-[#0B1F33]">{party.entity}</td>
                          <td className="p-2 font-mono text-[#5C5C5C]">{party.country}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}
          </div>
          </div>
        )}
      </div>
    </div>
  );
}
