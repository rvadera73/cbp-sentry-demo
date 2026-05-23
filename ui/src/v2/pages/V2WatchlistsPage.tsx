import React, { useState } from 'react';
import { Plus, Trash2, Eye } from 'lucide-react';
import { useV2Entities } from '../hooks/useV2Entities';
import { TradeEntity } from '../types/v2.types';

export default function V2WatchlistsPage() {
  const { entities, loading } = useV2Entities();

  // Form state (fully controlled)
  const [newEntityName, setNewEntityName] = useState('');
  const [newEntityType, setNewEntityType] = useState<'Exporter' | 'Importer' | 'Intermediary' | 'Manufacturer' | 'Broker'>('Exporter');
  const [newEntityCountry, setNewEntityCountry] = useState('CN');
  const [newEntityAddress, setNewEntityAddress] = useState('');

  // Watchlist state
  const [watchlistEntities, setWatchlistEntities] = useState<TradeEntity[]>([]);
  const [submitMessage, setSubmitMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const highRiskEntities = entities.filter(e => e.risk_level === 'Critical' || e.risk_level === 'High');
  const allWatchlistEntities = [...highRiskEntities, ...watchlistEntities];

  const handleAddWatchlist = (e: React.FormEvent) => {
    e.preventDefault();

    // Validation
    if (!newEntityName.trim()) {
      setSubmitMessage({ type: 'error', text: 'Please enter an entity name' });
      return;
    }
    if (!newEntityCountry.trim()) {
      setSubmitMessage({ type: 'error', text: 'Please enter a country' });
      return;
    }

    // Create new entity
    const newEntity: TradeEntity = {
      entity_id: `WL-${Math.random().toString(36).substring(7).toUpperCase()}`,
      entity_type: newEntityType,
      entity_name: newEntityName,
      country: newEntityCountry,
      risk_level: 'High',
      sanctions_status: 'None',
      known_affiliations: [],
      enforcement_history: 'Added to watchlist',
      ownership_indicators: 'Manual watchlist entry',
      registration_status: 'Under Review',
      watchlist_status: 'Flagged',
      address: newEntityAddress,
      tax_id: 'Pending Verification',
      phone: 'Contact pending',
      shared_identifiers: [],
    };

    // Add to local watchlist
    setWatchlistEntities([...watchlistEntities, newEntity]);

    // Reset form
    setNewEntityName('');
    setNewEntityType('Exporter');
    setNewEntityCountry('CN');
    setNewEntityAddress('');

    // Show success message
    setSubmitMessage({
      type: 'success',
      text: `${newEntity.entity_name} added to High Alert Watchlist`,
    });

    // Clear message after 3 seconds
    setTimeout(() => setSubmitMessage(null), 3000);
  };

  const handleRemoveFromWatchlist = (entityId: string) => {
    setWatchlistEntities(watchlistEntities.filter(e => e.entity_id !== entityId));
  };

  if (loading) return <div className="p-6 text-center">Loading watchlists...</div>;

  return (
    <div className="flex-1 flex overflow-hidden bg-[#F7F9FC]">
      {/* Add Watchlist Form */}
      <div className="w-80 border-r border-[#D0D7DE] bg-white p-5 overflow-y-auto flex flex-col shrink-0">
        <h2 className="text-lg font-bold text-[#0B1F33] mb-4">Add to Watchlist</h2>

        {submitMessage && (
          <div className={`mb-4 p-3 rounded text-xs font-bold ${
            submitMessage.type === 'success'
              ? 'bg-green-100 text-green-800'
              : 'bg-red-100 text-red-800'
          }`}>
            {submitMessage.text}
          </div>
        )}

        <form onSubmit={handleAddWatchlist} className="space-y-4 flex-1">
          {/* Entity Name */}
          <div>
            <label className="block text-xs font-bold text-[#5C5C5C] uppercase mb-1.5">Entity Name</label>
            <input
              type="text"
              value={newEntityName}
              onChange={(e) => setNewEntityName(e.target.value)}
              placeholder="Trade entity name..."
              className="w-full px-3 py-2 border border-[#D0D7DE] rounded-sm text-sm focus:outline-none focus:border-[#005EA2] focus:ring-1 focus:ring-[#005EA2]"
              required
            />
          </div>

          {/* Entity Type */}
          <div>
            <label className="block text-xs font-bold text-[#5C5C5C] uppercase mb-1.5">Entity Type</label>
            <select
              value={newEntityType}
              onChange={(e) => setNewEntityType(e.target.value as typeof newEntityType)}
              className="w-full px-3 py-2 border border-[#D0D7DE] rounded-sm text-sm focus:outline-none focus:border-[#005EA2] focus:ring-1 focus:ring-[#005EA2]"
            >
              <option value="Exporter">Exporter</option>
              <option value="Importer">Importer</option>
              <option value="Intermediary">Intermediary</option>
              <option value="Manufacturer">Manufacturer</option>
              <option value="Broker">Broker</option>
            </select>
          </div>

          {/* Country */}
          <div>
            <label className="block text-xs font-bold text-[#5C5C5C] uppercase mb-1.5">Country Code</label>
            <input
              type="text"
              value={newEntityCountry}
              onChange={(e) => setNewEntityCountry(e.target.value.toUpperCase())}
              placeholder="e.g., CN, VN, IN"
              maxLength={2}
              className="w-full px-3 py-2 border border-[#D0D7DE] rounded-sm text-sm focus:outline-none focus:border-[#005EA2] focus:ring-1 focus:ring-[#005EA2]"
              required
            />
          </div>

          {/* Address */}
          <div>
            <label className="block text-xs font-bold text-[#5C5C5C] uppercase mb-1.5">Address</label>
            <textarea
              value={newEntityAddress}
              onChange={(e) => setNewEntityAddress(e.target.value)}
              placeholder="Commercial address..."
              className="w-full px-3 py-2 border border-[#D0D7DE] rounded-sm text-sm focus:outline-none focus:border-[#005EA2] focus:ring-1 focus:ring-[#005EA2]"
              rows={4}
            />
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            className="w-full px-4 py-2 bg-[#005EA2] hover:bg-[#0076D6] active:bg-[#004080] text-white text-sm font-bold rounded-sm cursor-pointer transition-colors mt-auto flex items-center justify-center space-x-2"
          >
            <Plus className="w-4 h-4" />
            <span>Add to Watchlist</span>
          </button>

          <p className="text-[9px] text-gray-500 text-center">
            Entities added here will be flagged as high-alert and monitored
          </p>
        </form>
      </div>

      {/* Watchlist Display */}
      <div className="flex-1 p-5 overflow-y-auto">
        <h2 className="text-2xl font-bold text-[#0B1F33] mb-4">High Alert Exporters Watchlist</h2>
        <p className="text-xs text-[#5C5C5C] mb-4">
          {allWatchlistEntities.length} entities on watchlist
        </p>

        {allWatchlistEntities.length === 0 ? (
          <div className="flex flex-col items-center justify-center bg-white border border-dashed border-[#D0D7DE] rounded p-8 text-center">
            <Eye className="w-8 h-8 text-gray-300 mb-2" />
            <p className="text-gray-500 text-sm">No entities on watchlist yet</p>
            <p className="text-[9px] text-gray-400">Add entities using the form on the left</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {allWatchlistEntities.map(e => {
              const isUserAdded = watchlistEntities.some(we => we.entity_id === e.entity_id);

              return (
                <div
                  key={e.entity_id}
                  className={`border-2 p-4 rounded-sm transition-all ${
                    e.risk_level === 'Critical'
                      ? 'bg-red-50 border-[#D83933]'
                      : 'bg-amber-50 border-amber-300'
                  }`}
                >
                  {/* Header */}
                  <div className="flex justify-between items-start mb-3">
                    <span className={`px-2 py-1 text-[9px] font-bold rounded whitespace-nowrap ${
                      e.risk_level === 'Critical'
                        ? 'bg-[#D83933] text-white'
                        : 'bg-amber-200 text-amber-900'
                    }`}>
                      {e.risk_level === 'Critical' ? '🚨 CRITICAL' : '⚠️ HIGH RISK'}
                    </span>
                    {isUserAdded && (
                      <button
                        onClick={() => handleRemoveFromWatchlist(e.entity_id)}
                        className="text-red-600 hover:text-red-800 transition-colors"
                        title="Remove from watchlist"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>

                  {/* Entity Info */}
                  <h3 className="font-bold text-[#0B1F33] mb-1 line-clamp-2">{e.entity_name}</h3>
                  <p className="text-xs text-[#5C5C5C] mb-2">
                    <span className="font-bold text-[8px]">{e.entity_type}</span> • {e.country}
                  </p>

                  {/* ID & Address */}
                  <div className="text-[9px] text-gray-600 bg-white p-2 rounded mb-2 leading-relaxed">
                    <p className="font-mono">{e.entity_id}</p>
                    {e.address && <p className="text-[8px] mt-1">{e.address.substring(0, 50)}...</p>}
                  </div>

                  {/* Status */}
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[8px] font-bold text-[#5C5C5C]">
                      {e.sanctions_status !== 'None' ? (
                        <span className="text-[#D83933]">⚠️ {e.sanctions_status}</span>
                      ) : (
                        <span className="text-green-600">✓ Clean</span>
                      )}
                    </span>
                  </div>

                  {/* Enforcement History */}
                  {e.enforcement_history && (
                    <div className="text-[8px] text-gray-600 bg-gray-50 p-2 rounded mb-3 leading-snug border-l-2 border-gray-300">
                      {e.enforcement_history.substring(0, 60)}...
                    </div>
                  )}

                  {/* View Profile Link */}
                  <button className="w-full px-2 py-1.5 text-xs text-[#005EA2] font-bold border border-[#005EA2] rounded hover:bg-[#005EA2] hover:text-white transition-colors">
                    View Profile →
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
