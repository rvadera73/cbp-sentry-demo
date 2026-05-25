import React, { useState, useCallback, useMemo } from 'react';
import { MapPin, Ship, FileText, DollarSign, AlertTriangle, TrendingDown, Calendar, CheckCircle, RefreshCw, ExternalLink } from 'lucide-react';
import { useCorridorShipments } from '../hooks/useCorridorShipments';
import { useCorridorIntelligence, useCorridorDetail } from '../hooks/useCorridorIntelligence';
import { usePreManifestVessels } from '../hooks/usePreManifestVessels';
import { useShippingIntelligence, computeShippingIntelligence } from '../hooks/useShippingIntelligence';
import InvestigationListTable, { ListItem } from '../components/InvestigationListTable';
import { TabNavigation } from '../components/TabNavigation';
import CorridorSummaryCard from '../components/CorridorSummaryCard';
import DataTable, { DataTableColumn } from '../components/DataTable';
import { TYPOGRAPHY, DESIGN } from '../styles/typography';
import { COLORS, PATTERNS } from '../styles/designSystem';

type TabType = 'pre-manifest' | 'active-shipments' | 'compliance';

export default function V2ShippingIntelligencePage() {
  const { corridors, isLoading: corridorsLoading, error: corridorsError, count: corridorsCount } = useCorridorIntelligence();

  // Auto-select first corridor on load
  const [selectedCorridorId, setSelectedCorridorId] = useState<string | null>(null);
  React.useEffect(() => {
    if (!selectedCorridorId && corridors.length > 0) {
      setSelectedCorridorId(corridors[0].id);
    }
  }, [corridors, selectedCorridorId]);

  const [selectedShipmentId, setSelectedShipmentId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('pre-manifest');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [fromPage, setFromPage] = useState<'investigations' | 'shipping-intelligence'>('shipping-intelligence');

  // Search and filter state for Active Shipments tab
  const [shipmentSearchQuery, setShipmentSearchQuery] = useState('');
  const [shipmentPriorityFilter, setShipmentPriorityFilter] = useState('all');
  const [shipmentRiskFilter, setShipmentRiskFilter] = useState('all');

  // Server-side filtered data by corridor
  const { shipments: corridorShipments, loading: shipmentsLoading } = useCorridorShipments(selectedCorridorId || undefined);
  const { vessels, isLoading: vesselsLoading, lastRefreshed } = usePreManifestVessels(selectedCorridorId || undefined);

  const { corridor: selectedCorridor } = useCorridorDetail(selectedCorridorId || '');
  const selectedShipment = corridorShipments.find(s => s.shipment_id === selectedShipmentId);
  const selectedShipmentIntel = selectedShipment ? useShippingIntelligence(selectedShipment) : null;

  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
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
      case 'CRITICAL': return 'bg-[#D83933] text-white';
      case 'HIGH': return 'bg-orange-600 text-white';
      case 'MEDIUM': return 'bg-amber-600 text-white';
      case 'LOW': return 'bg-green-600 text-white';
      default: return 'bg-[#5C5C5C] text-white';
    }
  };

  // Convert shipments to ListItem format for Active Shipments tab
  const shipmentListItems = useMemo((): ListItem[] => {
    return corridorShipments
      .filter(s => s.risk_score! >= 50)
      .map(s => ({
        id: s.shipment_id,
        risk_score: Math.round(s.risk_score || 0),
        name: s.shipper_name || 'Unknown',
        entity: s.manifest_data.consignee || 'Unknown',
        officer: s.vessel_name || 'Unassigned',
        commodity: s.commodity_name || 'General Merchandise',
        date: s.date,
        status: s.risk_score! >= 80 ? 'Critical' : 'Elevated',
        statusColor: s.risk_score! >= 80
          ? 'bg-[#D83933] text-white'
          : 'bg-orange-600 text-white',
      }));
  }, [corridorShipments]);

  // Filter shipments
  const filteredShipments = useMemo(() => {
    return shipmentListItems.filter(item => {
      const matchesSearch =
        item.name.toLowerCase().includes(shipmentSearchQuery.toLowerCase()) ||
        item.id.toLowerCase().includes(shipmentSearchQuery.toLowerCase()) ||
        item.entity.toLowerCase().includes(shipmentSearchQuery.toLowerCase());

      const matchesRisk =
        shipmentRiskFilter === 'all' ||
        (shipmentRiskFilter === 'critical' && item.risk_score! >= 80) ||
        (shipmentRiskFilter === 'elevated' && item.risk_score! >= 50 && item.risk_score! < 80);

      return matchesSearch && matchesRisk;
    });
  }, [shipmentListItems, shipmentSearchQuery, shipmentRiskFilter]);

  // Handle back navigation tracking
  const handleAccessWorkspace = (shipmentId: string) => {
    setSelectedShipmentId(shipmentId);
    setActiveTab('compliance');
    setFromPage('shipping-intelligence');
  };

  const handleBackToShippings = () => {
    setSelectedShipmentId(null);
    setActiveTab('pre-manifest');
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-[#F7F9FC] overflow-hidden">
      {/* Header with Corridor Dropdown */}
      <div className={`${DESIGN.bgWhite} border-b ${DESIGN.borderColor} px-6 py-4 shadow-sm`}>
        <div className="flex items-center justify-between mb-3">
          <div>
            <h1 className={TYPOGRAPHY.pageTitle}>Shipping Intelligence</h1>
            <p className={TYPOGRAPHY.pageSubtitle}>Corridor Intelligence • Pre-Manifest Vessels • Trade Compliance</p>
          </div>
          <div className="flex items-center space-x-4">
            <button
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="flex items-center space-x-1 px-3 py-1.5 bg-blue-50 border border-[#005EA2] rounded text-xs font-mono text-[#005EA2] hover:bg-blue-100 disabled:opacity-50"
            >
              <RefreshCw className={`w-3 h-3 ${isRefreshing ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>
            {lastRefreshed && (
              <div className="text-xs font-mono text-[#5C5C5C]">Last: {formatDate(lastRefreshed)}</div>
            )}
          </div>
        </div>

        {/* Corridor Dropdown */}
        <div className="flex items-center space-x-3">
          <label className={`text-sm font-bold ${DESIGN.textDark}`}>Select Corridor:</label>
          <select
            value={selectedCorridorId || ''}
            onChange={(e) => {
              setSelectedCorridorId(e.target.value);
              setSelectedShipmentId(null);
              setActiveTab('pre-manifest');
            }}
            className={`px-4 py-2 border ${DESIGN.borderColor} rounded-sm ${DESIGN.bgWhite} text-sm font-bold ${DESIGN.textDark} focus:outline-none focus:border-[#005EA2]`}
          >
            {corridorsLoading ? (
              <option>Loading corridors...</option>
            ) : (
              corridors.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.id} ({c.display_name}) — Risk: {c.risk_level}
                </option>
              ))
            )}
          </select>
        </div>
      </div>

      {selectedShipmentId && activeTab === 'compliance' ? (
        // SHIPMENT WORKSPACE VIEW
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Back Button */}
          <div className="bg-[#F7F9FC] border-b border-[#D0D7DE] px-6 py-2 shrink-0">
            <button
              onClick={handleBackToShippings}
              className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 border border-slate-300 text-[#005EA2] hover:text-[#0076D6] text-xs font-bold rounded-sm flex items-center space-x-1 transition-colors"
            >
              <span>←</span>
              <span>BACK TO QUEUE</span>
            </button>
          </div>

          {/* Workspace Detail */}
          <div className="flex-1 overflow-auto p-5">
            {selectedShipment ? (
              <div className="max-w-4xl space-y-4">
                {/* Shipment Header */}
                <div className="bg-white border border-[#D0D7DE] p-4 rounded-sm shadow-sm">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h2 className="text-lg font-bold text-[#0B1F33] mb-1">{selectedShipment.shipper_name}</h2>
                      <p className="text-sm text-[#5C5C5C] font-mono">{selectedShipment.shipment_id}</p>
                    </div>
                    <span className={`px-3 py-1 rounded text-white text-sm font-bold ${
                      selectedShipment.risk_score! >= 80 ? 'bg-[#D83933]' : 'bg-orange-600'
                    }`}>
                      Risk: {Math.round(selectedShipment.risk_score || 0)}
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <div className="text-xs font-bold text-[#5C5C5C]">CORRIDOR</div>
                      <div className="text-sm font-bold text-[#0B1F33] mt-1">{selectedShipment.origin_country}→{selectedShipment.destination_country}</div>
                    </div>
                    <div>
                      <div className="text-xs font-bold text-[#5C5C5C]">COMMODITY</div>
                      <div className="text-sm font-bold text-[#0B1F33] mt-1">{selectedShipment.commodity_name} (HS {selectedShipment.hs_code})</div>
                    </div>
                    <div>
                      <div className="text-xs font-bold text-[#5C5C5C]">DECLARED VALUE</div>
                      <div className="text-sm font-bold text-[#0B1F33] mt-1">${(selectedShipment.manifest_data.declared_value_usd || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}</div>
                    </div>
                  </div>
                </div>

                {/* Risk Signals */}
                {selectedShipment.h2_signals && selectedShipment.h2_signals.length > 0 && (
                  <div className="bg-white border border-[#D0D7DE] p-4 rounded-sm shadow-sm">
                    <h3 className="text-sm font-bold text-[#0B1F33] mb-3">Risk Signals</h3>
                    <div className="flex flex-wrap gap-2">
                      {selectedShipment.h2_signals.map((signal, i) => (
                        <span key={i} className="px-2 py-1 bg-orange-100 text-orange-800 rounded text-xs font-bold">
                          {signal}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Element 9 Alert */}
                {selectedShipment.element9_is_mismatch && (
                  <div className="bg-red-50 border border-red-200 p-4 rounded-sm">
                    <h3 className="text-sm font-bold text-[#D83933] mb-2 flex items-center space-x-2">
                      <AlertTriangle className="w-4 h-4" />
                      <span>Element 9 Mismatch</span>
                    </h3>
                    <div className="text-xs space-y-1 text-[#5C5C5C]">
                      <div><span className="font-bold">Declared:</span> {selectedShipment.element9_declared_country}</div>
                      <div><span className="font-bold">Actual:</span> {selectedShipment.element9_actual_country}</div>
                    </div>
                  </div>
                )}

                {/* Manifest Details */}
                <div className="bg-white border border-[#D0D7DE] p-4 rounded-sm shadow-sm">
                  <h3 className="text-sm font-bold text-[#0B1F33] mb-3">Manifest Details</h3>
                  <div className="grid grid-cols-2 gap-4 text-xs">
                    <div>
                      <div className="text-[#5C5C5C] font-bold">Consignee</div>
                      <div className="text-[#0B1F33] mt-1">{selectedShipment.manifest_data.consignee}</div>
                    </div>
                    <div>
                      <div className="text-[#5C5C5C] font-bold">Vessel</div>
                      <div className="text-[#0B1F33] mt-1">{selectedShipment.vessel_name || 'Unknown'}</div>
                    </div>
                    <div>
                      <div className="text-[#5C5C5C] font-bold">Weight</div>
                      <div className="text-[#0B1F33] mt-1">{selectedShipment.manifest_data.weight_kg.toLocaleString()} kg</div>
                    </div>
                    <div>
                      <div className="text-[#5C5C5C] font-bold">Bill of Lading</div>
                      <div className="text-[#0B1F33] mt-1 font-mono">{selectedShipment.manifest_data.bill_of_lading || 'N/A'}</div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center text-[#5C5C5C] py-12">Shipment not found</div>
            )}
          </div>
        </div>
      ) : (
        // MAIN CONTENT AREA
        <div className="flex-1 flex flex-col overflow-hidden">

        {selectedCorridorId && selectedCorridor && (
          <div className="flex-1 flex flex-col bg-[#F7F9FC] overflow-hidden">
            {/* Corridor Summary Card */}
            <div className={PATTERNS.summaryCard}>
              <CorridorSummaryCard
                id={selectedCorridor.id}
                displayName={selectedCorridor.display_name}
                riskLevel={selectedCorridor.risk_level}
                shipmentCount={corridorShipments.length}
                avgRiskScore={corridorShipments.length > 0
                  ? corridorShipments.reduce((sum, s) => sum + (s.risk_score || 0), 0) / corridorShipments.length
                  : 0}
                element9MismatchPct={corridorShipments.length > 0
                  ? (corridorShipments.filter(s => s.element9_is_mismatch).length / corridorShipments.length) * 100
                  : 0}
                uniqueShippers={new Set(corridorShipments.map(s => s.shipper_name)).size}
                primaryHsChapters={selectedCorridor.primary_hs_chapters}
                riskProfile={selectedCorridor.risk_profile}
              />
            </div>

            {/* Tab Navigation */}
            <TabNavigation
              tabs={[
                { id: 'pre-manifest', label: `Pre-Manifest`, badge: vessels.length.toString() },
                { id: 'active-shipments', label: 'Active Shipments', badge: corridorShipments.length.toString() },
                { id: 'compliance', label: 'Duties & Enforcement' }
              ]}
              activeTab={activeTab as string}
              onTabChange={(tabId: string) => setActiveTab(tabId as TabType)}
              orientation="horizontal"
            />

            {/* Content Pane */}
            <div className={`${PATTERNS.contentPane} space-y-4`}>
              {activeTab === 'pre-manifest' && (
                <DataTable
                  title="INBOUND VESSELS (PRE-MANIFEST)"
                  columns={[
                    { key: 'vessel_name', label: 'VESSEL NAME', width: '20%' },
                    { key: 'vessel_imo', label: 'IMO', width: '12%' },
                    { key: 'flag_state', label: 'FLAG STATE', width: '12%' },
                    { key: 'speed_knots', label: 'SPEED (KT)', width: '10%' },
                    { key: 'eta_us', label: 'ETA US', width: '18%' },
                    {
                      key: 'ais_status',
                      label: 'STATUS',
                      width: '12%',
                      render: (status) => (
                        <span className={`px-2 py-0.5 rounded text-white text-[9px] font-bold ${
                          status === 'UNDERWAY' ? 'bg-[#005EA2]' :
                          status === 'AT_BERTH' ? 'bg-green-600' : 'bg-[#5C5C5C]'
                        }`}>
                          {status || 'UNKNOWN'}
                        </span>
                      )
                    },
                    {
                      key: 'position',
                      label: 'POSITION',
                      width: '16%',
                      render: (_, row) => (
                        <span className="font-mono text-[10px]">
                          {row.current_lat?.toFixed(2)}, {row.current_lon?.toFixed(2)}
                        </span>
                      )
                    }
                  ]}
                  rows={vessels.map(v => ({
                    ...v,
                    eta_us: formatDate(v.eta_us)
                  }))}
                  emptyMessage="No pre-manifest vessels in this corridor"
                  loading={vesselsLoading}
                />
              )}

              {activeTab === 'active-shipments' && (
                <InvestigationListTable
                  items={filteredShipments}
                  title={`ACTIVE SHIPMENTS — ${selectedCorridor?.id || ''}`}
                  subtitle="Manifest-filed shipments with elevated risk indicators"
                  searchPlaceholder="Filter by shipper, consignee, or ID..."
                  onRowClick={(itemId) => setSelectedShipmentId(itemId)}
                  onAccessWorkspace={handleAccessWorkspace}
                  searchQuery={shipmentSearchQuery}
                  onSearchChange={setShipmentSearchQuery}
                  priorityFilter={shipmentPriorityFilter}
                  onPriorityFilterChange={setShipmentPriorityFilter}
                  riskFilter={shipmentRiskFilter}
                  onRiskFilterChange={setShipmentRiskFilter}
                  onClearFilters={() => {
                    setShipmentSearchQuery('');
                    setShipmentPriorityFilter('all');
                    setShipmentRiskFilter('all');
                  }}
                  loading={shipmentsLoading}
                />
              )}

              {activeTab === 'compliance' && (
                <div className="space-y-4">
                  <DataTable
                    title="AD/CVD DUTIES & TRADE REMEDIES"
                    columns={[
                      { key: 'duty_type', label: 'DUTY TYPE', width: '15%' },
                      { key: 'product_description', label: 'PRODUCT DESCRIPTION', width: '30%' },
                      { key: 'hs_prefix', label: 'HS PREFIX', width: '12%' },
                      { key: 'rate_pct', label: 'RATE', width: '10%', render: (rate) => `${rate > 0 ? rate : 'Variable'}${rate > 0 ? '%' : ''}` },
                      { key: 'case_number', label: 'CASE #', width: '15%' },
                      {
                        key: 'source_url',
                        label: 'DETAILS',
                        width: '18%',
                        render: (url) => url ? (
                          <a href={url} target="_blank" rel="noopener noreferrer" className="text-[#005EA2] hover:underline flex items-center space-x-1">
                            <ExternalLink className="w-3 h-3" />
                            <span>View</span>
                          </a>
                        ) : <span className={DESIGN.textGray}>—</span>
                      }
                    ]}
                    rows={selectedCorridor.duties || []}
                    emptyMessage="No active duties for this corridor"
                  />

                  <DataTable
                    title="EAPA ENFORCEMENT ACTIONS"
                    columns={[
                      { key: 'case_id', label: 'CASE ID', width: '15%' },
                      { key: 'entity_name', label: 'ENTITY NAME', width: '20%' },
                      { key: 'case_status', label: 'STATUS', width: '12%', render: (status) => (
                        <span className={`px-2 py-0.5 rounded text-white text-[9px] font-bold ${
                          status === 'AFFIRMATIVE' ? 'bg-[#D83933]' :
                          status === 'PENDING' ? 'bg-orange-600' : 'bg-[#5C5C5C]'
                        }`}>
                          {status}
                        </span>
                      )},
                      { key: 'duty_evaded_usd', label: 'DUTY EVADED', width: '15%', render: (amount) => `$${amount?.toLocaleString() || '—'}` },
                      { key: 'case_year', label: 'YEAR', width: '10%' },
                      { key: 'source_description', label: 'SOURCE', width: '28%' }
                    ]}
                    rows={selectedCorridor.enforcement_actions || []}
                    emptyMessage="No recent enforcement actions for this corridor"
                  />
                </div>
              )}

              {selectedShipment && activeTab === 'compliance' && (
                <section className="bg-white rounded-sm border border-[#D0D7DE] p-4 shadow-sm">
                  <h3 className="text-sm font-bold text-[#0B1F33] mb-3 flex items-center space-x-2">
                    <FileText className="w-4 h-4" />
                    <span>Shipment Compliance: {selectedShipment.shipper_name}</span>
                  </h3>
                  <div className="space-y-3 text-xs">
                    <div className="bg-slate-50 p-2.5 rounded-sm">
                      <div className="font-bold text-[#0B1F33] mb-2">Risk Breakdown</div>
                      <div className="space-y-1 text-[#5C5C5C]">
                        <div className="flex justify-between"><span>H1 (Corridor):</span> <span className="font-bold text-[#0B1F33]">{selectedShipment.h1_score?.toFixed(1) || 0}/40</span></div>
                        <div className="flex justify-between"><span>H2 (Vessel):</span> <span className="font-bold text-[#0B1F33]">{selectedShipment.h2_score?.toFixed(1) || 0}/35</span></div>
                        <div className="flex justify-between"><span>H3 (Intelligence):</span> <span className="font-bold text-[#0B1F33]">{selectedShipment.h3_score?.toFixed(1) || 0}/25</span></div>
                        <div className="flex justify-between border-t border-[#D0D7DE] pt-1 mt-1"><span className="font-bold text-[#0B1F33]">Total Risk:</span> <span className="font-bold text-[#D83933]">{selectedShipment.risk_score?.toFixed(1) || 0}/100</span></div>
                      </div>
                    </div>

                    <div className="bg-slate-50 p-2.5 rounded-sm">
                      <div className="font-bold text-[#0B1F33] mb-1">ISF Filing Status</div>
                      <div className="space-y-1 text-[#5C5C5C]">
                        <div className="flex justify-between">
                          <span>Element 9:</span>
                          <span className={selectedShipment.element9_is_mismatch ? 'text-[#D83933] font-bold' : 'text-green-600 font-bold'}>
                            {selectedShipment.element9_is_mismatch ? 'MISMATCH' : 'MATCH'}
                          </span>
                        </div>
                        {selectedShipment.element9_is_mismatch && (
                          <div className="text-[10px] text-[#D83933]">
                            Declared: {selectedShipment.element9_declared_country} → Actual: {selectedShipment.element9_actual_country}
                          </div>
                        )}
                      </div>
                    </div>

                    {selectedShipmentIntel && (
                      <div className="bg-slate-50 p-2.5 rounded-sm">
                        <div className="font-bold text-[#0B1F33] mb-1">Pricing Analysis</div>
                        <div className="space-y-1 text-[#5C5C5C]">
                          <div className="flex justify-between"><span>Declared Value:</span> <span className="font-bold text-[#0B1F33]">${selectedShipment.manifest_data?.declared_value_usd?.toLocaleString() || 0}</span></div>
                          <div className="flex justify-between"><span>Weight:</span> <span className="font-bold text-[#0B1F33]">{selectedShipment.manifest_data?.weight_kg?.toFixed(0) || 0} kg</span></div>
                          <div className="flex justify-between"><span>Unit Price:</span> <span className="font-bold text-[#0B1F33]">${selectedShipmentIntel?.unit_price_per_kg?.toFixed(2) || 0}/kg</span></div>
                          <div className="flex justify-between"><span>Benchmark:</span> <span className="font-bold text-[#0B1F33]">${selectedShipmentIntel?.benchmark_price_per_kg?.toFixed(2) || 0}/kg</span></div>
                          <div className="flex justify-between">
                            <span>Variance:</span>
                            <span className={`font-bold ${selectedShipmentIntel?.price_variance_percent! > 0 ? 'text-orange-600' : 'text-[#D83933]'}`}>
                              {selectedShipmentIntel?.price_variance_percent?.toFixed(1) || 0}%
                            </span>
                          </div>
                          <div className="flex justify-between border-t border-[#D0D7DE] pt-1 mt-1">
                            <span>Flag:</span>
                            <span className={`font-bold px-2 py-0.5 rounded text-white text-[9px] ${
                              selectedShipmentIntel?.pricing_flag === 'SEVERE' ? 'bg-[#D83933]' :
                              selectedShipmentIntel?.pricing_flag === 'HIGH' ? 'bg-orange-600' :
                              selectedShipmentIntel?.pricing_flag === 'PREMIUM' ? 'bg-[#005EA2]' : 'bg-green-600'
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

        {!selectedCorridorId && (
          <div className="flex-1 flex items-center justify-center bg-[#F7F9FC]">
            <div className="text-center text-[#5C5C5C]">
              <MapPin className="w-12 h-12 mx-auto mb-3 text-[#D0D7DE]" />
              <p className="font-bold text-[#0B1F33] mb-1">Select a corridor to begin</p>
              <p className="text-xs">View pre-manifest vessels, active shipments, and compliance data</p>
            </div>
          </div>
        )}
        </div>
      )}
    </div>
  );
}
