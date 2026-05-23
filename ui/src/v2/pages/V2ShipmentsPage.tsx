import React, { useState, useMemo } from 'react';
import { Search, ChevronDown } from 'lucide-react';
import { useV2Cases } from '../hooks/useV2Cases';
import { Shipment } from '../types/v2.types';

interface V2ShipmentsPageProps {
  shipments?: Shipment[];
}

export default function V2ShipmentsPage({ shipments: propShipments }: V2ShipmentsPageProps) {
  const { shipments: localShipments, loading } = useV2Cases();
  const shipments = propShipments || localShipments;

  const [selectedShipmentId, setSelectedShipmentId] = useState<string | null>(null);
  const [holdToggle, setHoldToggle] = useState<Record<string, boolean>>({});
  const [searchQuery, setSearchQuery] = useState('');
  const [riskFilter, setRiskFilter] = useState('all');
  const [corridorFilter, setCorridorFilter] = useState('all');

  const selectedShipment = shipments.find(s => s.shipment_id === selectedShipmentId);

  // Filter and search logic
  const filteredShipments = useMemo(() => {
    return shipments.filter(s => {
      const matchesSearch = s.container_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
                           s.commodity_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
                           s.shipper_name?.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesRisk = riskFilter === 'all' ||
                         (riskFilter === 'critical' && (s.risk_score ?? 0) >= 80) ||
                         (riskFilter === 'elevated' && (s.risk_score ?? 0) >= 50 && (s.risk_score ?? 0) < 80) ||
                         (riskFilter === 'low' && (s.risk_score ?? 0) < 50);
      const corridor = `${s.origin_country}→${s.destination_country}`;
      const matchesCorridor = corridorFilter === 'all' || corridor === corridorFilter;
      return matchesSearch && matchesRisk && matchesCorridor;
    });
  }, [shipments, searchQuery, riskFilter, corridorFilter]);

  // Get unique corridors for filter dropdown
  const corridors = useMemo(() => {
    return Array.from(new Set(shipments.map(s => `${s.origin_country}→${s.destination_country}`)));
  }, [shipments]);

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-[#F7F9FC] p-5">
      {/* Header */}
      <div className="mb-4">
        <h1 className="text-2xl font-bold text-[#0B1F33] mb-4">Shipment Intelligence</h1>

        {/* Search & Filters */}
        <div className="bg-white rounded-sm border border-[#D0D7DE] p-3.5 flex flex-col md:flex-row md:items-center gap-3 shadow-sm">
          {/* Search Box */}
          <div className="flex-1 relative flex items-center">
            <Search className="h-4 w-4 text-slate-400 absolute left-3" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by container ID, commodity, or shipper..."
              className="w-full bg-[#F7F9FC] border border-[#D0D7DE] rounded-sm pl-9 pr-4 py-1.5 text-xs text-slate-800 focus:outline-none focus:border-[#005EA2]"
            />
          </div>

          {/* Risk Filter */}
          <select
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            className="bg-slate-50 border border-slate-300 rounded px-2.5 py-1.5 text-xs text-slate-800 focus:outline-none focus:border-[#005EA2] font-mono"
          >
            <option value="all">RISK: ALL</option>
            <option value="critical">CRITICAL (≥80)</option>
            <option value="elevated">ELEVATED (50-79)</option>
            <option value="low">LOW (&lt;50)</option>
          </select>

          {/* Corridor Filter */}
          <select
            value={corridorFilter}
            onChange={(e) => setCorridorFilter(e.target.value)}
            className="bg-slate-50 border border-[#D0D7DE] rounded px-2.5 py-1.5 text-xs text-[#0B1F33] focus:outline-none focus:border-[#005EA2] font-mono"
          >
            <option value="all">CORRIDOR: ALL</option>
            {corridors.map(c => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        {/* Results Counter */}
        <p className="text-xs text-[#5C5C5C] mt-2">
          Showing {filteredShipments.length} of {shipments.length} shipments
        </p>
      </div>

      {/* Shipment List */}
      <div className="flex-1 overflow-y-auto">
        <div className="space-y-3">
          {loading && <div className="text-gray-500 text-sm">Loading shipments...</div>}
          {filteredShipments.length === 0 && !loading && (
            <div className="text-center text-gray-500 text-sm py-8">
              No shipments match your filters. Try adjusting your search criteria.
            </div>
          )}
          {filteredShipments.map(s => (
            <div
              key={s.shipment_id}
              onClick={() => setSelectedShipmentId(s.shipment_id)}
              className={`p-4 rounded-sm border-2 cursor-pointer transition-all ${
                selectedShipmentId === s.shipment_id
                  ? 'bg-[#F0F4F8] border-[#005EA2] shadow-md'
                  : 'bg-white border-[#D0D7DE] hover:border-[#005EA2]'
              }`}
            >
              {/* Shipment Header */}
              <div className="flex justify-between items-start mb-3">
                <div>
                  <h3 className="font-bold text-[#0B1F33]">{s.container_id}</h3>
                  <p className="text-xs text-[#5C5C5C] font-mono">{s.shipment_id}</p>
                </div>
                <div className="flex items-center space-x-2">
                  <span className={`px-2 py-1 text-xs font-bold rounded whitespace-nowrap ${
                    s.ai_anomaly_score >= 80 ? 'bg-[#D83933] text-white' : 'bg-amber-100 text-amber-900'
                  }`}>
                    {s.ai_anomaly_score}%
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setHoldToggle(prev => ({ ...prev, [s.shipment_id]: !prev[s.shipment_id] }));
                    }}
                    className={`px-2 py-1 text-[9px] font-bold rounded ${
                      holdToggle[s.shipment_id]
                        ? 'bg-[#D83933] text-white'
                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                    }`}
                  >
                    {holdToggle[s.shipment_id] ? 'HOLD' : 'RELEASE'}
                  </button>
                </div>
              </div>

              {/* Meta Grid (4 fields) */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[9px] text-[#5C5C5C] font-bold uppercase">Declared Origin</label>
                  <p className="text-xs text-[#0B1F33] font-semibold">{s.declared_origin}</p>
                </div>
                <div>
                  <label className="text-[9px] text-[#5C5C5C] font-bold uppercase">Suspected Origin</label>
                  <p className="text-xs text-[#D83933] font-semibold">{s.suspected_origin}</p>
                </div>
                <div>
                  <label className="text-[9px] text-[#5C5C5C] font-bold uppercase">Product</label>
                  <p className="text-xs text-[#0B1F33]">{s.product_description.substring(0, 30)}</p>
                </div>
                <div>
                  <label className="text-[9px] text-[#5C5C5C] font-bold uppercase">Value (USD)</label>
                  <p className="text-xs text-[#0B1F33] font-mono">${s.manifest_data.declared_value_usd.toLocaleString()}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Detail Panel */}
      {selectedShipment && (
        <div className="w-96 border-l border-[#D0D7DE] bg-white overflow-y-auto flex flex-col shrink-0">
          {/* Header */}
          <div className="bg-[#F7F9FC] border-b border-[#D0D7DE] p-4 shrink-0">
            <h2 className="text-sm font-bold text-[#0B1F33]">{selectedShipment.container_id}</h2>
            <div className="flex items-center justify-between mt-2">
              <span className="text-[9px] text-[#5C5C5C] font-mono">{selectedShipment.shipment_id}</span>
              <div className={`w-2 h-2 rounded-full ${holdToggle[selectedShipment.shipment_id] ? 'bg-[#D83933]' : 'bg-green-500'}`}></div>
            </div>
          </div>

          {/* Manifest Ledger (6 fields in grid) */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            <section>
              <h3 className="text-xs font-bold text-[#5C5C5C] uppercase mb-3">Manifest Ledger</h3>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-slate-50 p-2 rounded">
                  <label className="text-[8px] text-[#5C5C5C] font-bold uppercase">Shipper</label>
                  <p className="text-xs text-[#0B1F33] font-semibold truncate">{selectedShipment.manifest_data.shipper}</p>
                </div>
                <div className="bg-slate-50 p-2 rounded">
                  <label className="text-[8px] text-[#5C5C5C] font-bold uppercase">Consignee</label>
                  <p className="text-xs text-[#0B1F33] font-semibold truncate">{selectedShipment.manifest_data.consignee}</p>
                </div>
                <div className="bg-slate-50 p-2 rounded">
                  <label className="text-[8px] text-[#5C5C5C] font-bold uppercase">Weight (kg)</label>
                  <p className="text-xs text-[#0B1F33] font-mono">{selectedShipment.manifest_data.weight_kg.toLocaleString()}</p>
                </div>
                <div className="bg-slate-50 p-2 rounded">
                  <label className="text-[8px] text-[#5C5C5C] font-bold uppercase">Carrier</label>
                  <p className="text-xs text-[#0B1F33] truncate">{selectedShipment.manifest_data.carrier}</p>
                </div>
                <div className="bg-slate-50 p-2 rounded">
                  <label className="text-[8px] text-[#5C5C5C] font-bold uppercase">Vessel</label>
                  <p className="text-xs text-[#0B1F33] font-semibold truncate">{selectedShipment.manifest_data.vessel}</p>
                </div>
                <div className="bg-slate-50 p-2 rounded">
                  <label className="text-[8px] text-[#5C5C5C] font-bold uppercase">B/L Number</label>
                  <p className="text-xs text-[#0B1F33] font-mono truncate">{selectedShipment.manifest_data.bill_of_lading}</p>
                </div>
              </div>
            </section>

            {/* Routing Timeline */}
            <section>
              <h3 className="text-xs font-bold text-[#5C5C5C] uppercase mb-3">Routing Timeline</h3>
              <div className="space-y-2">
                {[
                  { port: 'Origin', country: selectedShipment.origin_country, status: '✓' },
                  { port: 'Transshipment', country: selectedShipment.route[selectedShipment.route.length - 2] || 'N/A', status: '⟳' },
                  { port: 'Final Port', country: selectedShipment.destination_country, status: '○' },
                ].map((leg, idx) => (
                  <div key={idx} className="relative pl-6 pb-2">
                    {idx < 2 && <div className="absolute left-2 top-5 w-0.5 h-8 bg-[#D0D7DE]"></div>}
                    <div className="absolute left-0 top-0 w-4 h-4 bg-[#005EA2] rounded-full"></div>
                    <p className="text-xs font-bold text-[#0B1F33]">{leg.port}</p>
                    <p className="text-[9px] text-[#5C5C5C]">{leg.country}</p>
                  </div>
                ))}
              </div>
            </section>

            {/* Anomaly Flags */}
            <section>
              <h3 className="text-xs font-bold text-[#5C5C5C] uppercase mb-3">Anomaly Flags</h3>
              {selectedShipment.manifest_anomalies.length === 0 ? (
                <p className="text-[9px] text-gray-500">No anomalies detected</p>
              ) : (
                <div className="space-y-1">
                  {selectedShipment.manifest_anomalies.map((anomaly, idx) => (
                    <div key={idx} className="flex items-start space-x-2 p-2 bg-red-50 rounded border border-red-200">
                      <span className="text-[10px] font-bold text-[#D83933]">⚠</span>
                      <span className="text-[9px] text-[#D83933]">{anomaly}</span>
                    </div>
                  ))}
                </div>
              )}
            </section>

            {/* Inspection History */}
            <section>
              <h3 className="text-xs font-bold text-[#5C5C5C] uppercase mb-3">Inspection History</h3>
              <p className="text-[9px] text-gray-600">{selectedShipment.inspection_history || 'No inspection records'}</p>
            </section>
          </div>
        </div>
      )}
    </div>
  );
}
