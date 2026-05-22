import React, { useState } from 'react';
import { useV2Entities } from '../hooks/useV2Entities';

export default function V2WatchlistsPage() {
  const { entities, loading } = useV2Entities();
  const [newEntityName, setNewEntityName] = useState('');
  const [newEntityCountry, setNewEntityCountry] = useState('Vietnam');

  const highRiskEntities = entities.filter(e => e.risk_level === 'Critical' || e.risk_level === 'High');

  const handleAddWatchlist = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newEntityName.trim()) return;
    // Add to watchlist (would call API in production)
    setNewEntityName('');
  };

  if (loading) return <div className="p-6 text-center">Loading watchlists...</div>;

  return (
    <div className="flex-1 flex overflow-hidden bg-[#F7F9FC]">
      {/* Add Watchlist Form */}
      <div className="w-80 border-r border-[#D0D7DE] bg-white p-5 overflow-y-auto flex flex-col">
        <h2 className="text-lg font-bold text-[#0B1F33] mb-4">Add to Watchlist</h2>
        <form onSubmit={handleAddWatchlist} className="space-y-4 flex-1">
          <div>
            <label className="block text-xs font-bold text-[#5C5C5C] uppercase mb-1">Entity Name</label>
            <input
              type="text"
              value={newEntityName}
              onChange={(e) => setNewEntityName(e.target.value)}
              placeholder="Trade entity name..."
              className="w-full px-3 py-2 border border-[#D0D7DE] rounded-sm text-sm focus:outline-none focus:border-[#005EA2]"
            />
          </div>
          <div>
            <label className="block text-xs font-bold text-[#5C5C5C] uppercase mb-1">Entity Type</label>
            <select className="w-full px-3 py-2 border border-[#D0D7DE] rounded-sm text-sm focus:outline-none focus:border-[#005EA2]">
              <option>Exporter</option>
              <option>Importer</option>
              <option>Intermediary</option>
              <option>Manufacturer</option>
              <option>Broker</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-bold text-[#5C5C5C] uppercase mb-1">Country</label>
            <input
              type="text"
              value={newEntityCountry}
              onChange={(e) => setNewEntityCountry(e.target.value)}
              className="w-full px-3 py-2 border border-[#D0D7DE] rounded-sm text-sm focus:outline-none focus:border-[#005EA2]"
            />
          </div>
          <div>
            <label className="block text-xs font-bold text-[#5C5C5C] uppercase mb-1">Address</label>
            <textarea
              placeholder="Commercial address..."
              className="w-full px-3 py-2 border border-[#D0D7DE] rounded-sm text-sm focus:outline-none focus:border-[#005EA2]"
              rows={3}
            />
          </div>
          <button
            type="submit"
            className="w-full px-4 py-2 bg-[#005EA2] hover:bg-[#0076D6] text-white text-sm font-bold rounded-sm cursor-pointer mt-auto"
          >
            Add to High Alert Watchlist
          </button>
        </form>
      </div>

      {/* Watchlist Display */}
      <div className="flex-1 p-5 overflow-y-auto">
        <h2 className="text-2xl font-bold text-[#0B1F33] mb-4">High Alert Exporters Watchlist</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {highRiskEntities.length === 0 ? (
            <p className="text-gray-500">No high-risk entities on watchlist</p>
          ) : (
            highRiskEntities.map(e => (
              <div key={e.entity_id} className="bg-white border-2 border-[#D0D7DE] p-4 rounded-sm">
                <div className="flex justify-between items-start mb-2">
                  <span className={`px-2 py-1 text-[10px] font-bold rounded ${
                    e.risk_level === 'Critical' ? 'bg-[#D83933] text-white' : 'bg-amber-100 text-amber-900'
                  }`}>
                    {e.risk_level === 'Critical' ? '🚨 CRITICAL EVADER' : 'HIGH RISK'}
                  </span>
                  <span className="text-xs font-mono text-[#5C5C5C]">{e.entity_id}</span>
                </div>
                <h3 className="font-bold text-[#0B1F33] mb-1">{e.entity_name}</h3>
                <p className="text-xs text-[#5C5C5C] mb-2">{e.country} • {e.entity_type}</p>
                <div className="text-[9px] text-gray-600 bg-gray-50 p-2 rounded mb-2 leading-relaxed">
                  {e.enforcement_history}
                </div>
                <button className="text-xs text-[#005EA2] font-bold hover:underline cursor-pointer">
                  View Profile →
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
