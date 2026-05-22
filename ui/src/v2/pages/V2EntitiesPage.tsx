import React, { useState } from 'react';
import { useV2Entities } from '../hooks/useV2Entities';

export default function V2EntitiesPage() {
  const { entities, selectedEntity, selectEntity, loading } = useV2Entities();
  const [searchQuery, setSearchQuery] = useState('');

  if (loading) return <div className="p-6 text-center">Loading entities...</div>;

  const filtered = entities.filter(e =>
    e.entity_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex-1 flex overflow-hidden bg-[#F7F9FC]">
      <div className="flex-1 p-5 overflow-y-auto">
        <h1 className="text-2xl font-bold text-[#0B1F33] mb-4">Entity Resolution</h1>
        <input
          type="text"
          placeholder="Search entities..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full mb-4 px-3 py-2 border border-[#D0D7DE] rounded-sm text-sm focus:outline-none focus:border-[#005EA2]"
        />
        <div className="grid grid-cols-2 gap-3">
          {filtered.map(e => (
            <button
              key={e.entity_id}
              onClick={() => selectEntity(e.entity_id)}
              className={`p-4 rounded-sm border-2 text-left transition-all ${
                selectedEntity?.entity_id === e.entity_id
                  ? 'bg-[#F0F4F8] border-[#005EA2]'
                  : 'bg-white border-[#D0D7DE] hover:border-[#005EA2]'
              }`}
            >
              <p className="text-xs font-bold text-[#5C5C5C] uppercase mb-1">{e.entity_type}</p>
              <h3 className="font-bold text-[#0B1F33] text-sm">{e.entity_name}</h3>
              <p className="text-xs text-[#5C5C5C]">{e.country}</p>
              <span className={`inline-block mt-2 px-2 py-0.5 text-[10px] font-bold rounded ${
                e.risk_level === 'Critical' ? 'bg-[#D83933] text-white' :
                e.risk_level === 'High' ? 'bg-amber-100 text-amber-900' :
                'bg-green-100 text-green-900'
              }`}>
                {e.risk_level}
              </span>
            </button>
          ))}
        </div>
      </div>

      {selectedEntity && (
        <div className="w-96 border-l border-[#D0D7DE] bg-white overflow-y-auto p-5">
          <h2 className="text-lg font-bold text-[#0B1F33] mb-4">{selectedEntity.entity_name}</h2>
          <div className="space-y-3 text-sm">
            <div>
              <label className="text-xs font-bold text-[#5C5C5C] uppercase">Risk Level</label>
              <p className="text-[#0B1F33]">{selectedEntity.risk_level}</p>
            </div>
            <div>
              <label className="text-xs font-bold text-[#5C5C5C] uppercase">Country</label>
              <p className="text-[#0B1F33]">{selectedEntity.country}</p>
            </div>
            <div>
              <label className="text-xs font-bold text-[#5C5C5C] uppercase">Sanctions Status</label>
              <p className={selectedEntity.sanctions_status !== 'None' ? 'text-[#D83933] font-bold' : 'text-green-600'}>
                {selectedEntity.sanctions_status}
              </p>
            </div>
            <div>
              <label className="text-xs font-bold text-[#5C5C5C] uppercase">Address</label>
              <p className="text-[#5C5C5C]">{selectedEntity.address}</p>
            </div>
            <div>
              <label className="text-xs font-bold text-[#5C5C5C] uppercase">Enforcement History</label>
              <p className="text-[#5C5C5C] text-xs leading-relaxed">{selectedEntity.enforcement_history}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
