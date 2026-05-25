import React, { useState } from 'react';
import { Search, AlertTriangle, ChevronRight } from 'lucide-react';
import { useV2Entities } from '../hooks/useV2Entities';
import { TradeEntity } from '../types/v2.types';
import { TYPOGRAPHY, DESIGN } from '../styles/typography';

export default function V2EntitiesPage() {
  const { entities, selectedEntity, selectEntity, searchEntities, loading } = useV2Entities();
  const [searchQuery, setSearchQuery] = useState('');

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    if (query.length >= 2) {
      searchEntities(query);
    }
  };

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
              ) : entities.length === 0 ? (
                <div className="flex items-center justify-center h-full">
                  <div className={`text-center ${DESIGN.textGray} text-xs italic`}>No entities found. Try searching with different keywords.</div>
                </div>
              ) : (
                <table className="w-full text-left border-collapse">
                  <thead className={`sticky top-0 bg-[#F0F4F8] border-b ${DESIGN.borderColor}`}>
                    <tr>
                      <th className={`${TYPOGRAPHY.tableHeader} p-3 w-24`}>RISK</th>
                      <th className={`${TYPOGRAPHY.tableHeader} p-3`}>ENTITY NAME</th>
                      <th className={`${TYPOGRAPHY.tableHeader} p-3 w-20`}>TYPE</th>
                      <th className={`${TYPOGRAPHY.tableHeader} p-3 w-20`}>COUNTRY</th>
                      <th className={`${TYPOGRAPHY.tableHeader} p-3 w-28`}>TAX ID</th>
                      <th className={`${TYPOGRAPHY.tableHeader} p-3 w-24`}>WATCHLIST</th>
                      <th className={`${TYPOGRAPHY.tableHeader} p-3 text-right w-16`}>DETAILS</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E0E3E8]">
                    {entities.map((e) => (
                      <tr
                        key={e.entity_id}
                        className="hover:bg-[#F7F9FC] transition-colors cursor-pointer"
                        onClick={() => selectEntity(e.entity_id)}
                      >
                        <td className={`${TYPOGRAPHY.tableCell} p-3`}>
                          <span className={`inline-block px-2.5 py-1 rounded text-center font-bold text-xs text-white ${
                            e.risk_level === 'Critical' ? 'bg-[#D83933]' :
                            e.risk_level === 'High' ? 'bg-orange-600' :
                            'bg-green-600'
                          }`}>
                            {e.risk_level}
                          </span>
                        </td>
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
                            }}
                            className="px-2 py-1 bg-[#0076D6] hover:bg-[#005EA2] text-white text-[10px] font-bold rounded-sm flex items-center space-x-1 ml-auto transition-colors"
                          >
                            <ChevronRight className="h-3 w-3" />
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
          <div className={`w-96 border-l ${DESIGN.borderColor} ${DESIGN.bgWhite} overflow-y-auto flex flex-col shrink-0`}>
          {/* Header */}
          <div className={`bg-[#F7F9FC] border-b ${DESIGN.borderColor} p-4 shrink-0`}>
            <h2 className={`${TYPOGRAPHY.sectionTitle} mb-1`}>{selectedEntity.entity_name}</h2>
            <p className={`${TYPOGRAPHY.tableMono}`}>{selectedEntity.entity_id}</p>
            <p className={`${TYPOGRAPHY.smallText} mt-2`}>Tax ID: {selectedEntity.tax_id || 'Unverified'}</p>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* Sanctions Banner */}
            {selectedEntity.sanctions_status !== 'None' && (
              <div className={`p-3 rounded border-l-4 flex items-start space-x-2 ${
                selectedEntity.sanctions_status === 'Blocked list'
                  ? 'bg-red-50 border-l-[#D83933]'
                  : 'bg-amber-50 border-l-amber-500'
              }`}>
                <AlertTriangle className={`w-4 h-4 shrink-0 mt-0.5 ${
                  selectedEntity.sanctions_status === 'Blocked list'
                    ? 'text-[#D83933]'
                    : 'text-amber-600'
                }`} />
                <div>
                  <p className={`text-xs font-bold ${
                    selectedEntity.sanctions_status === 'Blocked list'
                      ? 'text-[#D83933]'
                      : 'text-amber-900'
                  }`}>
                    {selectedEntity.sanctions_status === 'Blocked list' ? 'BLOCKED ENTITY' : 'SANCTIONS ALERT'}
                  </p>
                  <p className={`${TYPOGRAPHY.smallText}`}>
                    {selectedEntity.sanctions_status === 'Blocked list'
                      ? 'This entity is on the OFAC SDN list. No trade permitted.'
                      : 'This entity is under investigation for sanctions violations.'}
                  </p>
                </div>
              </div>
            )}

            {/* Corporate Registration */}
            <section>
              <h3 className={`${TYPOGRAPHY.label} uppercase mb-3`}>Corporate Registration</h3>
              <div className={`space-y-2 ${DESIGN.bgLight} p-3 rounded border ${DESIGN.borderColor}`}>
                <div>
                  <label className={TYPOGRAPHY.label}>Entity Type</label>
                  <p className={`${TYPOGRAPHY.tableCell} mt-1`}>{selectedEntity.entity_type}</p>
                </div>
                <div>
                  <label className={TYPOGRAPHY.label}>Status</label>
                  <p className={`${TYPOGRAPHY.tableCell} mt-1`}>{selectedEntity.registration_status}</p>
                </div>
                <div>
                  <label className={TYPOGRAPHY.label}>Country</label>
                  <p className={`${TYPOGRAPHY.tableCell} mt-1`}>{selectedEntity.country}</p>
                </div>
                <div>
                  <label className={TYPOGRAPHY.label}>Address</label>
                  <p className={`${TYPOGRAPHY.tableCell} mt-1`}>{selectedEntity.address}</p>
                </div>
              </div>
            </section>

            {/* Network Indicators */}
            <section>
              <h3 className={`${TYPOGRAPHY.label} uppercase mb-3`}>Network Indicators</h3>

              {/* Affiliations */}
              <div className="mb-3">
                <label className={`${TYPOGRAPHY.label} block mb-2`}>Known Affiliations</label>
                {selectedEntity.known_affiliations && selectedEntity.known_affiliations.length > 0 ? (
                  <div className="flex flex-wrap gap-1">
                    {selectedEntity.known_affiliations.slice(0, 5).map((aff, idx) => (
                      <span key={idx} className="text-[8px] bg-blue-100 text-blue-900 px-2 py-1 rounded">
                        {aff}
                      </span>
                    ))}
                    {selectedEntity.known_affiliations.length > 5 && (
                      <span className="text-[8px] bg-slate-100 text-slate-700 px-2 py-1 rounded">
                        +{selectedEntity.known_affiliations.length - 5} more
                      </span>
                    )}
                  </div>
                ) : (
                  <p className={`${TYPOGRAPHY.smallText}`}>No known affiliations</p>
                )}
              </div>

              {/* Ownership Indicators */}
              <div>
                <label className={`${TYPOGRAPHY.label} block mb-2`}>Ownership Indicators</label>
                <p className={`${TYPOGRAPHY.smallText} leading-snug`}>
                  {selectedEntity.ownership_indicators || 'Data pending from beneficial ownership registry'}
                </p>
              </div>
            </section>

            {/* Enforcement History */}
            <section>
              <h3 className={`${TYPOGRAPHY.label} uppercase mb-3`}>Enforcement History</h3>
              <p className={`${TYPOGRAPHY.smallText} leading-snug ${DESIGN.bgLight} p-3 rounded border ${DESIGN.borderColor}`}>
                {selectedEntity.enforcement_history || 'No enforcement actions recorded'}
              </p>
            </section>

            {/* Watchlist Status */}
            <div className={`p-3 rounded text-sm font-bold text-center ${
              selectedEntity.watchlist_status === 'Flagged'
                ? 'bg-red-100 text-[#D83933]'
                : 'bg-green-100 text-green-700'
            }`}>
              {selectedEntity.watchlist_status}
            </div>

            {/* Add to Watchlist Button */}
            <button className={`w-full px-4 py-2 bg-[#005EA2] text-white text-sm font-bold rounded hover:bg-[#0076D6] transition-colors`}>
              Add to Watchlist
            </button>
          </div>
          </div>
        )}
      </div>
    </div>
  );
}
