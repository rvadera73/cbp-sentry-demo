import React, { useState } from 'react';
import { Search, AlertTriangle } from 'lucide-react';
import { useV2Entities } from '../hooks/useV2Entities';
import { TradeEntity } from '../types/v2.types';

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
    <div className="flex-1 flex overflow-hidden bg-[#F7F9FC]">
      {/* Entity List */}
      <div className="flex-1 p-5 overflow-y-auto">
        <h1 className="text-2xl font-bold text-[#0B1F33] mb-4">Entity Resolution</h1>

        {/* Search Bar */}
        <div className="mb-4 relative">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search entities by name..."
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 border border-[#D0D7DE] rounded-sm text-sm focus:outline-none focus:border-[#005EA2] focus:ring-1 focus:ring-[#005EA2]"
          />
        </div>

        {/* Entity Cards Grid */}
        <div className="grid grid-cols-2 gap-3">
          {loading ? (
            <div className="col-span-2 text-center text-gray-500 text-sm py-6">
              Searching entities...
            </div>
          ) : entities.length === 0 ? (
            <div className="col-span-2 text-center text-gray-500 text-sm py-6">
              No entities found. Try searching with different keywords.
            </div>
          ) : (
            entities.map(e => (
              <button
                key={e.entity_id}
                onClick={() => selectEntity(e.entity_id)}
                className={`p-4 rounded-sm border-2 text-left transition-all ${
                  selectedEntity?.entity_id === e.entity_id
                    ? 'bg-[#F0F4F8] border-[#005EA2] shadow-md'
                    : 'bg-white border-[#D0D7DE] hover:border-[#005EA2]'
                }`}
              >
                {/* Entity Type Badge */}
                <div className="flex items-start justify-between mb-2">
                  <span className="text-[8px] font-bold bg-slate-200 text-slate-800 px-1.5 py-0.5 rounded uppercase whitespace-nowrap">
                    {e.entity_type}
                  </span>
                  <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded uppercase whitespace-nowrap ${
                    e.risk_level === 'Critical' ? 'bg-[#D83933] text-white' :
                    e.risk_level === 'High' ? 'bg-amber-100 text-amber-900' :
                    'bg-green-100 text-green-900'
                  }`}>
                    {e.risk_level}
                  </span>
                </div>

                {/* Entity Name */}
                <h3 className="font-bold text-[#0B1F33] text-sm mb-1 line-clamp-2">{e.entity_name}</h3>

                {/* Basic Info */}
                <div className="space-y-1 text-[9px]">
                  <p className="text-[#5C5C5C]"><span className="font-bold text-[8px]">Country:</span> {e.country}</p>
                  <p className="text-[#5C5C5C]"><span className="font-bold text-[8px]">Tax ID:</span> {e.tax_id || 'Unverified'}</p>
                  <p className={`font-semibold ${e.watchlist_status === 'Flagged' ? 'text-[#D83933]' : 'text-green-600'}`}>
                    {e.watchlist_status}
                  </p>
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Detail Panel */}
      {selectedEntity && (
        <div className="w-96 border-l border-[#D0D7DE] bg-white overflow-y-auto flex flex-col shrink-0">
          {/* Header */}
          <div className="bg-[#F7F9FC] border-b border-[#D0D7DE] p-4 shrink-0">
            <h2 className="text-sm font-bold text-[#0B1F33] mb-1">{selectedEntity.entity_name}</h2>
            <p className="text-[9px] text-[#5C5C5C] font-mono">{selectedEntity.entity_id}</p>
            <p className="text-[9px] text-[#5C5C5C] mt-1">Tax ID: {selectedEntity.tax_id}</p>
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
                  <p className="text-[9px] text-gray-700">
                    {selectedEntity.sanctions_status === 'Blocked list'
                      ? 'This entity is on the OFAC SDN list. No trade permitted.'
                      : 'This entity is under investigation for sanctions violations.'}
                  </p>
                </div>
              </div>
            )}

            {/* Corporate Registration */}
            <section>
              <h3 className="text-xs font-bold text-[#5C5C5C] uppercase mb-3">Corporate Registration</h3>
              <div className="space-y-2 bg-slate-50 p-3 rounded border border-slate-200">
                <div>
                  <label className="text-[8px] font-bold text-[#5C5C5C]">Entity Type</label>
                  <p className="text-xs text-[#0B1F33]">{selectedEntity.entity_type}</p>
                </div>
                <div>
                  <label className="text-[8px] font-bold text-[#5C5C5C]">Status</label>
                  <p className="text-xs text-[#0B1F33]">{selectedEntity.registration_status}</p>
                </div>
                <div>
                  <label className="text-[8px] font-bold text-[#5C5C5C]">Country</label>
                  <p className="text-xs text-[#0B1F33]">{selectedEntity.country}</p>
                </div>
                <div>
                  <label className="text-[8px] font-bold text-[#5C5C5C]">Address</label>
                  <p className="text-xs text-[#0B1F33]">{selectedEntity.address}</p>
                </div>
              </div>
            </section>

            {/* Architecture Notes */}
            <section>
              <h3 className="text-xs font-bold text-[#5C5C5C] uppercase mb-3">Architecture Notes</h3>

              {/* Affiliations */}
              <div className="mb-3">
                <label className="text-[8px] font-bold text-[#5C5C5C] uppercase block mb-2">Known Affiliations</label>
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
                  <p className="text-[9px] text-gray-500">No known affiliations</p>
                )}
              </div>

              {/* Ownership Indicators */}
              <div>
                <label className="text-[8px] font-bold text-[#5C5C5C] uppercase block mb-2">Ownership Indicators</label>
                <p className="text-[9px] text-gray-700 leading-snug">
                  {selectedEntity.ownership_indicators || 'Data pending from beneficial ownership registry'}
                </p>
              </div>
            </section>

            {/* Enforcement History */}
            <section>
              <h3 className="text-xs font-bold text-[#5C5C5C] uppercase mb-3">Enforcement History</h3>
              <p className="text-[9px] text-gray-700 leading-snug bg-slate-50 p-3 rounded border border-slate-200">
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
            <button className="w-full px-4 py-2 bg-[#005EA2] text-white text-sm font-bold rounded hover:bg-[#0076D6] transition-colors">
              Add to Watchlist
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
