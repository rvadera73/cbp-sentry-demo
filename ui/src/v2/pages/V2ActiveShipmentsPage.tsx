import React, { useState, useMemo } from 'react';
import { AlertTriangle, MapPin, DollarSign, TrendingDown, Calendar, Search, ChevronRight, ArrowLeft } from 'lucide-react';
import { useCorridorShipments } from '../hooks/useCorridorShipments';
import { Shipment } from '../types/v2.types';
import { computeShippingIntelligence } from '../hooks/useShippingIntelligence';

interface UseActiveShipmentsReturn {
  shipments: Shipment[];
  loading: boolean;
  error: string | null;
  total: number;
}

function useActiveShipments(): UseActiveShipmentsReturn {
  const [shipments, setShipments] = useState<Shipment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);

  React.useEffect(() => {
    const fetchShipments = async () => {
      try {
        setLoading(true);
        const params = new URLSearchParams({
          risk_min: '50',
          limit: '100',
          offset: '0'
        });

        const response = await fetch(`/api/shipments?${params}`);
        if (!response.ok) {
          throw new Error(`Failed to fetch shipments: ${response.statusText}`);
        }

        const data = await response.json();
        const mappedShipments = (data.data || []).map((apiData: any): Shipment => {
          const originCountry = apiData.shipper_country || 'XX';
          const destCountry = apiData.consignee_country || 'US';

          return {
            shipment_id: apiData.id || apiData.shipment_id || '',
            origin_country: originCountry,
            destination_country: destCountry,
            declared_origin: apiData.element9_declared_country || originCountry,
            suspected_origin: apiData.element9_actual_country || originCountry,
            product_code: apiData.commodity_code || apiData.hs_code || '9999',
            product_description: apiData.commodity_name || 'General Merchandise',
            route: [originCountry, destCountry],
            container_id: apiData.id || '',
            manifest_data: {
              shipper: apiData.shipper_name || 'Unknown',
              consignee: apiData.consignee_name || 'Unknown',
              weight_kg: apiData.declared_weight_kg || 0,
              declared_value_usd: apiData.declared_value || 0,
              carrier: apiData.vessel_name || 'Unknown',
              vessel: apiData.vessel_name || 'Unknown',
              voyage_number: apiData.voyage_number || '',
              bill_of_lading: apiData.bill_of_lading || '',
            },
            manifest_anomalies: apiData.h2_signals || [],
            ai_anomaly_score: apiData.risk_score || 0,
            customs_flags: [],
            inspection_history: 'No recent inspections',
            date: apiData.created_at || new Date().toISOString(),

            hs_code: apiData.commodity_code || apiData.hs_code,
            commodity_name: apiData.commodity_name,
            h1_score: apiData.h1_score || 0,
            h2_score: apiData.h2_score || 0,
            h3_score: apiData.h3_score || 0,
            h2_signals: apiData.h2_signals || [],
            h3_recommendation: apiData.h3_recommendation || 'EXAMINE',
            element9_is_mismatch: apiData.element9_is_mismatch === 1 || apiData.element9_is_mismatch === true,
            element9_declared_country: apiData.element9_declared_country,
            element9_actual_country: apiData.element9_actual_country,
            shipper_name: apiData.shipper_name,
            shipper_country: apiData.shipper_country,
            risk_score: apiData.risk_score || 0,
          };
        });
        setShipments(mappedShipments);
        setTotal(data.count || 0);
        setError(null);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error';
        setError(message);
        console.error('Error fetching active shipments:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchShipments();
  }, []);

  return { shipments, loading, error, total };
}

export default function V2ActiveShipmentsPage() {
  const { shipments, loading, error, total } = useActiveShipments();
  const [selectedShipmentId, setSelectedShipmentId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [riskFilter, setRiskFilter] = useState('all');

  const selectedShipment = selectedShipmentId
    ? shipments.find(s => s.shipment_id === selectedShipmentId)
    : null;

  const filteredShipments = useMemo(() => {
    return shipments.filter(s => {
      const matchesSearch =
        s.shipper_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.manifest_data.consignee?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.shipment_id?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.hs_code?.includes(searchQuery);

      const matchesRisk =
        riskFilter === 'all' ||
        (riskFilter === 'critical' && s.risk_score! >= 80) ||
        (riskFilter === 'elevated' && s.risk_score! >= 50 && s.risk_score! < 80);

      return matchesSearch && matchesRisk;
    });
  }, [shipments, searchQuery, riskFilter]);

  const getRiskColor = (score: number) => {
    if (score >= 80) return 'bg-[#D83933]';
    if (score >= 60) return 'bg-orange-600';
    return 'bg-green-600';
  };

  const getRiskLabel = (score: number) => {
    if (score >= 80) return 'Critical';
    if (score >= 60) return 'High';
    return 'Medium';
  };

  const stats = useMemo(() => {
    const critical = shipments.filter(s => s.risk_score! >= 80).length;
    const elevated = shipments.filter(s => s.risk_score! >= 50 && s.risk_score! < 80).length;
    return { critical, elevated, total: shipments.length };
  }, [shipments]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-[#005EA2]"></div>
          <p className="mt-4 text-[#5C5C5C]">Loading active shipments...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full overflow-hidden">
      {/* List Panel */}
      <div className={`${selectedShipment ? 'w-96' : 'w-full'} flex flex-col bg-white border-r border-[#D0D7DE] overflow-hidden`}>
        {/* Header */}
        <div className="bg-[#F7F9FC] border-b border-[#D0D7DE] p-4">
          <h2 className="text-lg font-bold text-[#0B1F33] mb-4 flex items-center space-x-2">
            <AlertTriangle className="w-5 h-5 text-orange-600" />
            <span>Active Shipments</span>
          </h2>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-2 mb-4">
            <div className="bg-white p-2 rounded-sm border border-[#D0D7DE]">
              <div className="text-[10px] text-[#5C5C5C]">Total</div>
              <div className="text-lg font-bold text-[#0B1F33]">{stats.total}</div>
            </div>
            <div className="bg-white p-2 rounded-sm border border-red-200">
              <div className="text-[10px] text-[#D83933]">Critical</div>
              <div className="text-lg font-bold text-[#D83933]">{stats.critical}</div>
            </div>
            <div className="bg-white p-2 rounded-sm border border-orange-200">
              <div className="text-[10px] text-orange-700">Elevated</div>
              <div className="text-lg font-bold text-orange-600">{stats.elevated}</div>
            </div>
          </div>

          {/* Search */}
          <div className="mb-3">
            <div className="flex items-center bg-white border border-[#D0D7DE] rounded-sm px-3 py-2">
              <Search className="w-4 h-4 text-[#5C5C5C]" />
              <input
                type="text"
                placeholder="Search shipper, consignee..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="flex-1 ml-2 text-xs outline-none"
              />
            </div>
          </div>

          {/* Risk Filter */}
          <div className="flex gap-2">
            <button
              onClick={() => setRiskFilter('all')}
              className={`px-3 py-1.5 rounded-sm text-[10px] font-bold transition-colors ${
                riskFilter === 'all'
                  ? 'bg-[#005EA2] text-white'
                  : 'bg-white border border-[#D0D7DE] text-[#0B1F33] hover:bg-[#F7F9FC]'
              }`}
            >
              All
            </button>
            <button
              onClick={() => setRiskFilter('critical')}
              className={`px-3 py-1.5 rounded-sm text-[10px] font-bold transition-colors ${
                riskFilter === 'critical'
                  ? 'bg-[#D83933] text-white'
                  : 'bg-white border border-[#D0D7DE] text-[#0B1F33] hover:bg-[#F7F9FC]'
              }`}
            >
              Critical (≥80)
            </button>
            <button
              onClick={() => setRiskFilter('elevated')}
              className={`px-3 py-1.5 rounded-sm text-[10px] font-bold transition-colors ${
                riskFilter === 'elevated'
                  ? 'bg-orange-600 text-white'
                  : 'bg-white border border-[#D0D7DE] text-[#0B1F33] hover:bg-[#F7F9FC]'
              }`}
            >
              Elevated (50-79)
            </button>
          </div>
        </div>

        {/* Shipments List */}
        <div className="flex-1 overflow-y-auto">
          {filteredShipments.length === 0 ? (
            <div className="p-4 text-center text-[#5C5C5C] text-xs">
              {shipments.length === 0 ? 'No active shipments' : 'No results matching your filters'}
            </div>
          ) : (
            <div className="space-y-2 p-3">
              {filteredShipments.map((shipment) => (
                <button
                  key={shipment.shipment_id}
                  onClick={() => setSelectedShipmentId(shipment.shipment_id)}
                  className={`w-full text-left p-3 rounded-sm border transition-all ${
                    selectedShipmentId === shipment.shipment_id
                      ? 'bg-blue-50 border-[#005EA2] shadow-sm'
                      : 'border-[#D0D7DE] hover:bg-[#F7F9FC] hover:border-[#005EA2]'
                  }`}
                >
                  <div className="flex items-start justify-between mb-1">
                    <div className="flex-1">
                      <div className="text-xs font-bold text-[#0B1F33] truncate">{shipment.shipper_name}</div>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-white text-[9px] font-bold ml-2 flex-shrink-0 ${getRiskColor(shipment.risk_score!)}`}>
                      {Math.round(shipment.risk_score!)}
                    </span>
                  </div>
                  <div className="text-[10px] text-[#5C5C5C] mb-1">
                    {shipment.origin_country} → {shipment.destination_country}
                  </div>
                  <div className="text-[9px] text-[#5C5C5C] font-mono">
                    {shipment.hs_code} | ${(shipment.manifest_data.declared_value_usd || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}
                  </div>
                  {shipment.element9_is_mismatch && (
                    <div className="text-[9px] text-[#D83933] mt-1 font-bold">
                      ⚠️ Element 9: {shipment.element9_declared_country} → {shipment.element9_actual_country}
                    </div>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Detail Panel */}
      {selectedShipment && (
        <div className="flex-1 flex flex-col bg-[#F7F9FC] overflow-hidden">
          <div className="bg-white border-b border-[#D0D7DE] p-4 flex items-center justify-between">
            <button
              onClick={() => setSelectedShipmentId(null)}
              className="flex items-center space-x-2 text-[#005EA2] hover:text-[#003366] text-sm font-bold"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to List</span>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* Shipment Overview */}
            <section className="bg-white rounded-sm border border-[#D0D7DE] p-4 shadow-sm">
              <h3 className="text-sm font-bold text-[#0B1F33] mb-3">Shipment Overview</h3>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <div className="text-[#5C5C5C] font-bold mb-1">Shipment ID</div>
                  <div className="font-mono text-[#0B1F33]">{selectedShipment.shipment_id}</div>
                </div>
                <div>
                  <div className="text-[#5C5C5C] font-bold mb-1">Risk Score</div>
                  <div className={`font-bold ${selectedShipment.risk_score! >= 80 ? 'text-[#D83933]' : 'text-orange-600'}`}>
                    {Math.round(selectedShipment.risk_score!)} / 100 ({getRiskLabel(selectedShipment.risk_score!)})
                  </div>
                </div>
                <div>
                  <div className="text-[#5C5C5C] font-bold mb-1">Shipper</div>
                  <div className="text-[#0B1F33]">{selectedShipment.shipper_name}</div>
                </div>
                <div>
                  <div className="text-[#5C5C5C] font-bold mb-1">Consignee</div>
                  <div className="text-[#0B1F33]">{selectedShipment.manifest_data.consignee}</div>
                </div>
                <div>
                  <div className="text-[#5C5C5C] font-bold mb-1">Route</div>
                  <div className="text-[#0B1F33]">{selectedShipment.origin_country} → {selectedShipment.destination_country}</div>
                </div>
                <div>
                  <div className="text-[#5C5C5C] font-bold mb-1">Declared Value</div>
                  <div className="text-[#0B1F33]">${(selectedShipment.manifest_data.declared_value_usd || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}</div>
                </div>
              </div>
            </section>

            {/* Commodity & Trade Details */}
            <section className="bg-white rounded-sm border border-[#D0D7DE] p-4 shadow-sm">
              <h3 className="text-sm font-bold text-[#0B1F33] mb-3">Commodity & Trade Details</h3>
              <div className="space-y-3 text-xs">
                <div className="flex justify-between">
                  <span className="text-[#5C5C5C]">HS Code:</span>
                  <span className="font-bold text-[#0B1F33] font-mono">{selectedShipment.hs_code}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#5C5C5C]">Commodity:</span>
                  <span className="font-bold text-[#0B1F33]">{selectedShipment.commodity_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#5C5C5C]">Weight:</span>
                  <span className="font-bold text-[#0B1F33]">{selectedShipment.manifest_data.weight_kg.toLocaleString()} kg</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#5C5C5C]">Vessel:</span>
                  <span className="font-bold text-[#0B1F33]">{selectedShipment.vessel_name || 'Unknown'}</span>
                </div>
              </div>
            </section>

            {/* Risk Signals */}
            {selectedShipment.h2_signals && selectedShipment.h2_signals.length > 0 && (
              <section className="bg-white rounded-sm border border-[#D0D7DE] p-4 shadow-sm">
                <h3 className="text-sm font-bold text-[#0B1F33] mb-3">Risk Signals</h3>
                <div className="flex flex-wrap gap-2">
                  {selectedShipment.h2_signals.map((signal, i) => (
                    <span key={i} className="px-2 py-1 bg-orange-100 text-orange-800 rounded text-[9px] font-bold">
                      {signal}
                    </span>
                  ))}
                </div>
              </section>
            )}

            {/* Element 9 Mismatch */}
            {selectedShipment.element9_is_mismatch && (
              <section className="bg-red-50 rounded-sm border border-red-200 p-4">
                <h3 className="text-sm font-bold text-[#D83933] mb-2 flex items-center space-x-2">
                  <AlertTriangle className="w-4 h-4" />
                  <span>Element 9 Mismatch Detected</span>
                </h3>
                <div className="text-xs space-y-1 text-[#5C5C5C]">
                  <div><span className="font-bold text-[#0B1F33]">Declared:</span> {selectedShipment.element9_declared_country}</div>
                  <div><span className="font-bold text-[#0B1F33]">Actual:</span> {selectedShipment.element9_actual_country}</div>
                </div>
              </section>
            )}

            {/* Action Buttons */}
            <div className="flex gap-2 pt-2">
              <button
                onClick={() => {
                  try {
                    window.location.href = `/investigations?shipmentId=${selectedShipment.shipment_id}`;
                  } catch (e) {
                    console.error('Failed to navigate to investigations:', e);
                    alert('Unable to open investigation workspace');
                  }
                }}
                className="flex-1 px-4 py-2 bg-[#005EA2] hover:bg-[#0076D6] text-white text-xs font-bold rounded-sm transition-colors"
              >
                Access Investigation Workspace
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
