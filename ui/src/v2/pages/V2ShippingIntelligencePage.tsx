import React, { useState, useCallback } from 'react';
import { MapPin, Ship, FileText, DollarSign, AlertTriangle, TrendingDown, Calendar, CheckCircle, RefreshCw, ExternalLink } from 'lucide-react';
import { useV2Cases } from '../hooks/useV2Cases';
import { useCorridorIntelligence, useCorridorDetail } from '../hooks/useCorridorIntelligence';
import { usePreManifestVessels } from '../hooks/usePreManifestVessels';
import { useShippingIntelligence, computeShippingIntelligence } from '../hooks/useShippingIntelligence';

type TabType = 'pre-manifest' | 'active-shipments' | 'compliance';

export default function V2ShippingIntelligencePage() {
  const { shipments } = useV2Cases();
  const { corridors, isLoading: corridorsLoading, error: corridorsError, count: corridorsCount } = useCorridorIntelligence();
  const { vessels, isLoading: vesselsLoading, lastRefreshed } = usePreManifestVessels();

  const [selectedCorridorId, setSelectedCorridorId] = useState<string | null>(null);
  const [selectedShipmentId, setSelectedShipmentId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('pre-manifest');
  const [isRefreshing, setIsRefreshing] = useState(false);

  const { corridor: selectedCorridor } = useCorridorDetail(selectedCorridorId || '');
  const selectedShipment = shipments.find(s => s.shipment_id === selectedShipmentId);
  const selectedShipmentIntel = selectedShipment ? useShippingIntelligence(selectedShipment) : null;

  // Get shipments for selected corridor
  const corridorShipments = selectedCorridorId
    ? shipments.filter(s => {
        const origin = s.origin_country?.slice(0, 2).toUpperCase() || '';
        const dest = s.destination_country?.slice(0, 2).toUpperCase() || '';
        return selectedCorridorId.includes(origin) && selectedCorridorId.includes(dest);
      })
    : shipments;

  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      // Trigger a re-fetch of corridors and vessels
      await Promise.all([
        fetch('/api/corridors'),
        fetch('/api/pre-manifest/vessels')
      ]);
    } catch (err) {
      console.error('Refresh failed:', err);
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  const formatDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return 'Never';
    const date = new Date(dateStr);
    return date.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const getRiskLevelColor = (level: string) => {
    switch (level) {
      case 'CRITICAL': return 'bg-red-900 text-white';
      case 'HIGH': return 'bg-red-600 text-white';
      case 'MEDIUM': return 'bg-amber-600 text-white';
      case 'LOW': return 'bg-emerald-600 text-white';
      default: return 'bg-slate-600 text-white';
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-[#F7F9FC] overflow-hidden">
      {/* Header */}
      <div className="h-16 bg-white border-b border-[#D0D7DE] px-6 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-[#112E51]">Shipping Intelligence</h1>
          <p className="text-xs text-slate-500 font-mono">Compliance-Focused • DB-Driven Corridors • Pre-Manifest Vessels • Pattern Indicators</p>
        </div>
        <div className="flex items-center space-x-4">
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="flex items-center space-x-1 px-3 py-1.5 bg-blue-50 border border-blue-300 rounded text-xs font-mono text-blue-700 hover:bg-blue-100 disabled:opacity-50"
          >
            <RefreshCw className={`w-3 h-3 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <div className="text-xs font-mono text-slate-600">
            {lastRefreshed && <div>Last: {formatDate(lastRefreshed)}</div>}
          </div>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel: Corridor List */}
        <div className="w-80 border-r border-[#D0D7DE] flex flex-col bg-white overflow-hidden">
          {/* Corridor Stats */}
          <div className="p-3 border-b border-[#D0D7DE] bg-[#F7F9FC]">
            <div className="text-xs font-bold text-slate-600 uppercase mb-2">
              {corridorsLoading ? 'Loading Corridors...' : `${corridorsCount} Active Corridors`}
            </div>
            {corridorsError && (
              <div className="text-red-600 text-[10px] bg-red-50 p-2 rounded mb-2">
                Error: {corridorsError}
              </div>
            )}
          </div>

          {/* Corridor List */}
          <div className="flex-1 overflow-y-auto">
            {corridors.map((corridor) => {
              const stats = corridor.computed_stats;
              const isSelected = selectedCorridorId === corridor.id;

              return (
                <button
                  key={corridor.id}
                  onClick={() => {
                    setSelectedCorridorId(corridor.id);
                    setSelectedShipmentId(null);
                    setActiveTab('pre-manifest');
                  }}
                  className={`w-full text-left p-3 border-b border-[#E5E7EB] hover:bg-blue-50 transition-colors ${
                    isSelected ? 'bg-[#E8F4FD] border-l-4 border-l-[#005EA2]' : ''
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="text-xs font-bold text-[#112E51]">{corridor.id}</div>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${getRiskLevelColor(corridor.risk_level)}`}>
                      {corridor.risk_level}
                    </span>
                  </div>
                  <div className="text-[10px] text-slate-600 font-mono mb-1">
                    {corridor.display_name}
                  </div>
                  <div className="text-[10px] text-slate-500 space-y-0.5">
                    <div className="flex justify-between">
                      <span>Shipments:</span>
                      <span className="font-bold">{stats?.shipment_count || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Avg Risk:</span>
                      <span className="font-bold">{stats?.avg_risk_score?.toFixed(0) || 0}/100</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Element 9 Mismatch:</span>
                      <span className="font-bold text-red-600">{stats?.element9_mismatch_rate_pct?.toFixed(1) || 0}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Active Shippers:</span>
                      <span className="font-bold">{stats?.unique_shippers || 0}</span>
                    </div>
                  </div>

                  {/* Duty Badges */}
                  {corridor.primary_hs_chapters && (
                    <div className="mt-2 flex gap-1 flex-wrap">
                      {JSON.parse(corridor.primary_hs_chapters || '[]').map((hs: string, i: number) => (
                        <span key={i} className="px-1.5 py-0.5 bg-orange-100 text-orange-800 rounded text-[9px] font-bold">
                          {hs}*
                        </span>
                      ))}
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Right Panel: Corridor Detail or Shipment Detail */}
        {selectedCorridorId && selectedCorridor && (
          <div className="flex-1 flex flex-col bg-[#F7F9FC] overflow-hidden">
            {/* Tabs */}
            <div className="h-10 bg-white border-b border-[#D0D7DE] flex items-center px-4 space-x-4">
              <button
                onClick={() => setActiveTab('pre-manifest')}
                className={`text-xs font-bold px-2 py-1 border-b-2 ${
                  activeTab === 'pre-manifest'
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-slate-600 hover:text-slate-900'
                }`}
              >
                Pre-Manifest ({vessels.filter(v => selectedCorridorId.includes(v.origin_country)).length})
              </button>
              <button
                onClick={() => setActiveTab('active-shipments')}
                className={`text-xs font-bold px-2 py-1 border-b-2 ${
                  activeTab === 'active-shipments'
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-slate-600 hover:text-slate-900'
                }`}
              >
                Active Shipments ({corridorShipments.length})
              </button>
              <button
                onClick={() => setActiveTab('compliance')}
                className={`text-xs font-bold px-2 py-1 border-b-2 ${
                  activeTab === 'compliance'
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-slate-600 hover:text-slate-900'
                }`}
              >
                Duties & Enforcement
              </button>
            </div>

            {/* Tab Content */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {/* Pre-Manifest Tab */}
              {activeTab === 'pre-manifest' && (
                <div className="space-y-4">
                  <section className="bg-white rounded border border-[#D0D7DE] p-4">
                    <h3 className="text-sm font-bold text-[#112E51] mb-3 flex items-center space-x-2">
                      <Ship className="w-4 h-4" />
                      <span>Inbound Vessels (Pre-Manifest)</span>
                    </h3>
                    {vessels.length === 0 ? (
                      <div className="text-slate-500 text-xs italic">No pre-manifest vessels in this corridor</div>
                    ) : (
                      <div className="space-y-2">
                        {vessels.filter(v => selectedCorridorId.includes(v.origin_country)).map((vessel) => (
                          <div key={vessel.vessel_imo} className="bg-slate-50 p-3 rounded border border-slate-200 text-xs">
                            <div className="flex justify-between mb-1">
                              <div className="font-bold text-[#112E51]">{vessel.vessel_name}</div>
                              <span className={`px-1.5 py-0.5 rounded text-white text-[9px] font-bold ${
                                vessel.ais_status === 'UNDERWAY' ? 'bg-blue-600' :
                                vessel.ais_status === 'AT_BERTH' ? 'bg-emerald-600' : 'bg-slate-600'
                              }`}>
                                {vessel.ais_status}
                              </span>
                            </div>
                            <div className="text-slate-600 font-mono mb-1">IMO: {vessel.vessel_imo}</div>
                            <div className="grid grid-cols-2 gap-2 text-slate-600">
                              <div>Flag: <span className="font-bold">{vessel.flag_state}</span></div>
                              <div>Speed: <span className="font-bold">{vessel.speed_knots} kt</span></div>
                              <div>ETA: <span className="font-bold">{formatDate(vessel.eta_us)}</span></div>
                              <div>Pos: <span className="font-mono text-[10px]">{vessel.current_lat?.toFixed(2)}, {vessel.current_lon?.toFixed(2)}</span></div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </section>

                  {/* Corridor Risk Profile */}
                  <section className="bg-white rounded border border-[#D0D7DE] p-4">
                    <h3 className="text-sm font-bold text-[#112E51] mb-2">Corridor Risk Profile</h3>
                    <div className="text-xs space-y-1 text-slate-600">
                      <div><span className="font-bold">Profile:</span> {selectedCorridor.risk_profile}</div>
                      <div><span className="font-bold">HS Chapters:</span> {JSON.parse(selectedCorridor.primary_hs_chapters || '[]').join(', ')}</div>
                    </div>
                  </section>
                </div>
              )}

              {/* Active Shipments Tab */}
              {activeTab === 'active-shipments' && (
                <div className="space-y-3">
                  {corridorShipments.length === 0 ? (
                    <div className="text-slate-500 text-xs italic bg-white p-4 rounded">No active shipments in this corridor</div>
                  ) : (
                    corridorShipments.map((shipment) => {
                      const intel = computeShippingIntelligence(shipment);
                      return (
                        <button
                          key={shipment.shipment_id}
                          onClick={() => {
                            setSelectedShipmentId(shipment.shipment_id);
                            setActiveTab('compliance');
                          }}
                          className="w-full text-left bg-white rounded border border-[#D0D7DE] p-3 hover:border-blue-400 hover:bg-blue-50 transition-colors"
                        >
                          <div className="flex justify-between mb-1">
                            <div className="text-xs font-bold text-[#112E51]">{shipment.shipper_name}</div>
                            <span className={`px-2 py-0.5 rounded text-white text-[9px] font-bold ${
                              shipment.risk_score! >= 80 ? 'bg-red-600' :
                              shipment.risk_score! >= 60 ? 'bg-amber-600' : 'bg-emerald-600'
                            }`}>
                              Risk: {Math.round(shipment.risk_score || 0)}
                            </span>
                          </div>
                          <div className="text-[10px] text-slate-600 font-mono mb-1">
                            {shipment.hs_code} | ${(shipment.manifest_data?.declared_value_usd || 0).toLocaleString()}
                          </div>
                          {intel?.pricing_flag !== 'NORMAL' && (
                            <div className="text-[10px] text-orange-700 font-bold">
                              ⚠️ Pricing: {intel?.pricing_flag} ({intel?.price_variance_percent?.toFixed(1)}%)
                            </div>
                          )}
                          {shipment.element9_is_mismatch && (
                            <div className="text-[10px] text-red-700 font-bold">
                              ⚠️ Element 9: {shipment.element9_declared_country} → {shipment.element9_actual_country}
                            </div>
                          )}
                        </button>
                      );
                    })
                  )}
                </div>
              )}

              {/* Duties & Enforcement Tab */}
              {activeTab === 'compliance' && (
                <div className="space-y-4">
                  {/* AD/CVD Duties */}
                  <section className="bg-white rounded border border-[#D0D7DE] p-4">
                    <h3 className="text-sm font-bold text-[#112E51] mb-3 flex items-center space-x-2">
                      <DollarSign className="w-4 h-4" />
                      <span>AD/CVD Duties & Trade Remedies</span>
                    </h3>
                    {(selectedCorridor.duties || []).length === 0 ? (
                      <div className="text-slate-500 text-xs italic">No active duties</div>
                    ) : (
                      <div className="space-y-2">
                        {selectedCorridor.duties?.map((duty) => (
                          <div key={duty.id} className="bg-amber-50 border border-amber-200 p-2.5 rounded text-xs">
                            <div className="flex justify-between items-start mb-1">
                              <div className="font-bold text-amber-900">{duty.duty_type}</div>
                              <div className="font-bold text-amber-700">{duty.rate_pct > 0 ? `${duty.rate_pct}%` : 'Variable'}</div>
                            </div>
                            <div className="text-amber-800 mb-1">{duty.product_description}</div>
                            <div className="text-[10px] text-amber-700">
                              Case: {duty.case_number} | HS: {duty.hs_prefix}
                            </div>
                            {duty.source_url && (
                              <a href={duty.source_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline text-[10px] flex items-center space-x-1 mt-1">
                                <ExternalLink className="w-3 h-3" />
                                <span>View Details</span>
                              </a>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </section>

                  {/* EAPA Enforcement Actions */}
                  <section className="bg-white rounded border border-[#D0D7DE] p-4">
                    <h3 className="text-sm font-bold text-[#112E51] mb-3 flex items-center space-x-2">
                      <AlertTriangle className="w-4 h-4" />
                      <span>EAPA Enforcement Actions</span>
                    </h3>
                    {(selectedCorridor.enforcement_actions || []).length === 0 ? (
                      <div className="text-slate-500 text-xs italic">No recent enforcement actions</div>
                    ) : (
                      <div className="space-y-2">
                        {selectedCorridor.enforcement_actions?.map((action) => (
                          <div key={action.id} className="bg-red-50 border border-red-200 p-2.5 rounded text-xs">
                            <div className="flex justify-between items-start mb-1">
                              <div className="font-bold text-red-900">{action.case_id}</div>
                              <span className={`px-1.5 py-0.5 rounded text-white text-[9px] font-bold ${
                                action.case_status === 'AFFIRMATIVE' ? 'bg-red-600' :
                                action.case_status === 'PENDING' ? 'bg-amber-600' : 'bg-slate-600'
                              }`}>
                                {action.case_status}
                              </span>
                            </div>
                            <div className="text-red-800 font-mono mb-1">{action.entity_name}</div>
                            {action.duty_evaded_usd && (
                              <div className="text-red-700 font-bold mb-1">
                                Duty Evaded: ${action.duty_evaded_usd.toLocaleString()}
                              </div>
                            )}
                            <div className="text-[10px] text-red-600">
                              Year: {action.case_year} | {action.source_description}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </section>
                </div>
              )}

              {/* Selected Shipment Compliance Breakdown */}
              {selectedShipment && activeTab === 'compliance' && (
                <section className="bg-white rounded border border-[#D0D7DE] p-4">
                  <h3 className="text-sm font-bold text-[#112E51] mb-3 flex items-center space-x-2">
                    <FileText className="w-4 h-4" />
                    <span>Shipment Compliance: {selectedShipment.shipper_name}</span>
                  </h3>
                  <div className="space-y-3 text-xs">
                    {/* Risk Scores */}
                    <div className="bg-slate-50 p-2.5 rounded">
                      <div className="font-bold text-slate-900 mb-2">Risk Breakdown</div>
                      <div className="space-y-1 text-slate-700">
                        <div className="flex justify-between"><span>H1 (Corridor):</span> <span className="font-bold">{selectedShipment.h1_score?.toFixed(1) || 0}/40</span></div>
                        <div className="flex justify-between"><span>H2 (Vessel):</span> <span className="font-bold">{selectedShipment.h2_score?.toFixed(1) || 0}/35</span></div>
                        <div className="flex justify-between"><span>H3 (Intelligence):</span> <span className="font-bold">{selectedShipment.h3_score?.toFixed(1) || 0}/25</span></div>
                        <div className="flex justify-between border-t border-slate-200 pt-1 mt-1"><span className="font-bold">Total Risk:</span> <span className="font-bold text-red-600">{selectedShipment.risk_score?.toFixed(1) || 0}/100</span></div>
                      </div>
                    </div>

                    {/* ISF Status */}
                    <div className="bg-slate-50 p-2.5 rounded">
                      <div className="font-bold text-slate-900 mb-1">ISF Filing Status</div>
                      <div className="space-y-1 text-slate-700">
                        <div className="flex justify-between">
                          <span>Element 9:</span>
                          <span className={selectedShipment.element9_is_mismatch ? 'text-red-600 font-bold' : 'text-emerald-600 font-bold'}>
                            {selectedShipment.element9_is_mismatch ? 'MISMATCH' : 'MATCH'}
                          </span>
                        </div>
                        {selectedShipment.element9_is_mismatch && (
                          <div className="text-[10px] text-red-600">
                            Declared: {selectedShipment.element9_declared_country} → Actual: {selectedShipment.element9_actual_country}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Pricing Analysis */}
                    {selectedShipmentIntel && (
                      <div className="bg-slate-50 p-2.5 rounded">
                        <div className="font-bold text-slate-900 mb-1">Pricing Analysis</div>
                        <div className="space-y-1 text-slate-700">
                          <div className="flex justify-between"><span>Declared Value:</span> <span className="font-bold">${selectedShipment.manifest_data?.declared_value_usd?.toLocaleString() || 0}</span></div>
                          <div className="flex justify-between"><span>Weight:</span> <span className="font-bold">{selectedShipment.manifest_data?.weight_kg?.toFixed(0) || 0} kg</span></div>
                          <div className="flex justify-between"><span>Unit Price:</span> <span className="font-bold">${selectedShipmentIntel?.unit_price_per_kg?.toFixed(2) || 0}/kg</span></div>
                          <div className="flex justify-between"><span>Benchmark:</span> <span className="font-bold">${selectedShipmentIntel?.benchmark_price_per_kg?.toFixed(2) || 0}/kg</span></div>
                          <div className="flex justify-between">
                            <span>Variance:</span>
                            <span className={`font-bold ${selectedShipmentIntel?.price_variance_percent! > 0 ? 'text-amber-600' : 'text-red-600'}`}>
                              {selectedShipmentIntel?.price_variance_percent?.toFixed(1) || 0}%
                            </span>
                          </div>
                          <div className="flex justify-between border-t border-slate-200 pt-1 mt-1">
                            <span>Flag:</span>
                            <span className={`font-bold px-2 py-0.5 rounded text-white text-[9px] ${
                              selectedShipmentIntel?.pricing_flag === 'SEVERE' ? 'bg-red-600' :
                              selectedShipmentIntel?.pricing_flag === 'HIGH' ? 'bg-orange-600' :
                              selectedShipmentIntel?.pricing_flag === 'PREMIUM' ? 'bg-blue-600' : 'bg-emerald-600'
                            }`}>
                              {selectedShipmentIntel?.pricing_flag || 'NORMAL'}
                            </span>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </section>
              )}
            </div>
          </div>
        )}

        {/* Empty State */}
        {!selectedCorridorId && (
          <div className="flex-1 flex items-center justify-center bg-[#F7F9FC]">
            <div className="text-center text-slate-600">
              <MapPin className="w-12 h-12 mx-auto mb-3 text-slate-400" />
              <p className="font-bold mb-1">Select a corridor to begin</p>
              <p className="text-xs">View pre-manifest vessels, active shipments, and compliance data</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
