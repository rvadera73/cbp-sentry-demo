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
import V2EntityResolutionPanel from '../components/V2EntityResolutionPanel';
import CorridorTradeAnalysis from '../components/CorridorTradeAnalysis';
import CorridorAssessment from '../components/CorridorAssessment';
import { TYPOGRAPHY, DESIGN } from '../styles/typography';
import { COLORS, PATTERNS } from '../styles/designSystem';
import { API_BASE_URL } from '../../services/apiUrl';
import { Case, Shipment } from '../types/v2.types';

type TabType = 'pre-manifest' | 'active-shipments' | 'trade-analysis' | 'compliance' | 'entity-resolution';

interface V2ShippingIntelligencePageProps {
  selectedCaseId?: string | null;
  setSelectedCaseId?: (id: string | null) => void;
  setActiveTab?: (tab: string) => void;
  shipments?: Shipment[];
  cases?: Case[];
}

export default function V2ShippingIntelligencePage({
  selectedCaseId: propSelectedCaseId,
  setSelectedCaseId: propSetSelectedCaseId,
  setActiveTab: propSetActiveTab,
  shipments: propShipments = [],
  cases: propCases = [],
}: V2ShippingIntelligencePageProps = {}) {
  const { corridors, isLoading: corridorsLoading, error: corridorsError, count: corridorsCount } = useCorridorIntelligence();

  // Auto-select first corridor on load
  const [selectedCorridorId, setSelectedCorridorId] = useState<string | null>(null);
  React.useEffect(() => {
    if (!selectedCorridorId && corridors.length > 0) {
      setSelectedCorridorId(corridors[0].id);
    }
  }, [corridors, selectedCorridorId]);

  const [activeTab, setActiveTab] = useState<TabType>('trade-analysis');
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Search and filter state for Active Shipments tab
  const [shipmentSearchQuery, setShipmentSearchQuery] = useState('');
  const [shipmentPriorityFilter, setShipmentPriorityFilter] = useState('all');
  const [shipmentRiskFilter, setShipmentRiskFilter] = useState('all');

  // Server-side filtered data by corridor
  const { shipments: corridorShipments, loading: shipmentsLoading } = useCorridorShipments(selectedCorridorId || undefined);
  const { vessels, isLoading: vesselsLoading, lastRefreshed } = usePreManifestVessels(selectedCorridorId || undefined);

  const { corridor: selectedCorridor } = useCorridorDetail(selectedCorridorId || '');

  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      await Promise.all([
        fetch(`${API_BASE_URL}/corridors`),
        fetch(`${API_BASE_URL}/pre-manifest/vessels`)
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

  // Navigate to Investigation Workspace with shipment ID
  const handleAccessWorkspace = useCallback((shipmentId: string) => {
    if (propSetSelectedCaseId && propSetActiveTab && propCases.length > 0) {
      // Find case that matches this shipment
      const shipment = corridorShipments.find(s => s.shipment_id === shipmentId);
      if (shipment) {
        const matchingCase = propCases.find(c =>
          c.origin_country === shipment.origin_country &&
          c.destination_country === shipment.destination_country &&
          c.target_entity.includes(shipment.shipper_name || '')
        );
        if (matchingCase) {
          propSetSelectedCaseId(matchingCase.case_id);
          propSetActiveTab('investigations');
        }
      }
    }
  }, [propSetSelectedCaseId, propSetActiveTab, propCases, corridorShipments]);

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

      </div>

      {/* MAIN CONTENT AREA - TAB NAVIGATION */}
      <div className="flex-1 flex flex-col overflow-hidden">

        {selectedCorridorId && selectedCorridor && (
          <div className="flex-1 flex flex-col bg-[#F7F9FC] overflow-hidden">
            {/* Corridor Summary Card */}
            <CorridorSummaryCard
              id={selectedCorridor.id}
              displayName={selectedCorridor.display_name}
              riskLevel={selectedCorridor.risk_level}
              shipmentCount={corridorShipments.length}
              avgRiskScore={corridorShipments.length > 0
                ? corridorShipments.reduce((sum: number, s: any) => sum + (s.risk_score || 0), 0) / corridorShipments.length
                : 0}
              element9MismatchPct={corridorShipments.length > 0
                ? (corridorShipments.filter((s: any) => s.element9_is_mismatch).length / corridorShipments.length) * 100
                : 0}
              uniqueShippers={new Set(corridorShipments.map((s: any) => s.shipper_name)).size}
              primaryHsChapters={selectedCorridor.primary_hs_chapters}
              riskProfile={selectedCorridor.risk_profile}
              corridors={corridors}
              onCorridorChange={(corridorId: string) => {
                setSelectedCorridorId(corridorId);
                setActiveTab('trade-analysis');
              }}
            />

            {/* Tab Navigation */}
            <TabNavigation
              tabs={[
                { id: 'trade-analysis', label: 'Trade Analysis', badge: '✨' },
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
                      render: (status: any) => (
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
                      render: (_: any, row: any) => (
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
                  onRowClick={() => {}}
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

              {activeTab === 'trade-analysis' && (
                <div className="space-y-4 overflow-y-auto flex-1">
                  <CorridorTradeAnalysis corridor={selectedCorridor} shipments={corridorShipments} />
                </div>
              )}

              {activeTab === 'compliance' && (
                <div className="space-y-4">
                  <DataTable
                    title="AD/CVD DUTIES & TRADE REMEDIES"
                    columns={[
                      { key: 'duty_type', label: 'DUTY TYPE', width: '15%' },
                      { key: 'product_description', label: 'PRODUCT DESCRIPTION', width: '30%' },
                      { key: 'hs_prefix', label: 'HS PREFIX', width: '12%' },
                      { key: 'rate_pct', label: 'RATE', width: '10%', render: (rate: any) => `${rate > 0 ? rate : 'Variable'}${rate > 0 ? '%' : ''}` },
                      { key: 'case_number', label: 'CASE #', width: '15%' },
                      {
                        key: 'source_url',
                        label: 'DETAILS',
                        width: '18%',
                        render: (url: any) => url ? (
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
                      { key: 'case_status', label: 'STATUS', width: '12%', render: (status: any) => (
                        <span className={`px-2 py-0.5 rounded text-white text-[9px] font-bold ${
                          status === 'AFFIRMATIVE' ? 'bg-[#D83933]' :
                          status === 'PENDING' ? 'bg-orange-600' : 'bg-[#5C5C5C]'
                        }`}>
                          {status}
                        </span>
                      )},
                      { key: 'duty_evaded_usd', label: 'DUTY EVADED', width: '15%', render: (amount: any) => `$${amount?.toLocaleString() || '—'}` },
                      { key: 'case_year', label: 'YEAR', width: '10%' },
                      { key: 'source_description', label: 'SOURCE', width: '28%' }
                    ]}
                    rows={selectedCorridor.enforcement_actions || []}
                    emptyMessage="No recent enforcement actions for this corridor"
                  />
                </div>
              )}

            </div>

            {/* Corridor-level assessment — shown outside the tabs, like the top summary */}
            <div className="shrink-0 px-4 pt-2 pb-4 bg-[#F7F9FC] border-t border-[#D0D7DE]">
              <CorridorAssessment corridor={selectedCorridor} shipments={corridorShipments} />
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
    </div>
  );
}
