import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../layout/Header';
import CaseSummaryStrip, { SummaryMetrics } from './CaseSummaryStrip';
import AccessibilityToolbar, { ViewMode, RiskFilter, SortBy } from './AccessibilityToolbar';
import CaseListView from './CaseListView';
import CaseSplitPane from './CaseSplitPane';
import CaseMapView from './CaseMapView';
import { CaseCardData } from './CaseCard';
import './CaseManagerLayout.css';

/**
 * CaseManagerLayout: Main enterprise case management container
 *
 * Features:
 * - 3-view toggle: List | Split | Map
 * - Real-time filtering with debounce
 * - Risk-based sorting
 * - Semantic color tokens applied dynamically
 * - WCAG 2.1 AA keyboard navigation
 *
 * Architecture:
 * Block A: Case Summary Strip (metrics header)
 * Block B: Accessibility Toolbar (view toggle + filters)
 * Block C: Dynamic view renderer (list/split/map)
 *
 * Data Flow:
 * - Fetch shipments from /api/shipments
 * - Apply filters (risk, search) in real-time
 * - Sort by risk/date/shipper
 * - Render appropriate view component
 */
export default function CaseManagerLayout() {
  const navigate = useNavigate();

  // State: View mode & filters
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [searchTerm, setSearchTerm] = useState('');
  const [riskFilter, setRiskFilter] = useState<RiskFilter>('all');
  const [sortBy, setSortBy] = useState<SortBy>('risk');

  // State: Case data
  const [allCases, setAllCases] = useState<CaseCardData[]>([]);
  const [filteredCases, setFilteredCases] = useState<CaseCardData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // State: Selected case (for split-pane view)
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);

  // Fetch cases on mount
  useEffect(() => {
    fetchCases();
  }, []);

  // Apply filters/sort whenever dependencies change
  useEffect(() => {
    applyFiltersAndSort();
  }, [allCases, searchTerm, riskFilter, sortBy]);

  /**
   * fetchCases: Load cases from API with fixture fallback
   */
  const fetchCases = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/shipments?limit=100');

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data = await response.json();
      const shipments = data.shipments || [];

      // Map API shipments to CaseCardData
      const cases: CaseCardData[] = shipments.map((s: any) => ({
        id: s.id,
        manifest_id: s.manifest_id,
        shipper_name: s.shipper_name,
        trade_name: s.trade_name,
        entity_type: s.entity_type,
        consignee_name: s.consignee_name,
        route_origin: s.shipper_country || 'Unknown',
        route_destination: s.consignee_country || 'Unknown',
        corridor_name: s.corridor_name,
        commodity_code: s.commodity_code,
        commodity_description: s.commodity_description,
        declared_value: s.declared_value || 0,
        risk_score: s.risk_score || 0,
        filing_date: s.created_at || new Date().toISOString(),
        status: s.status,
      }));

      setAllCases(cases);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch cases:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
      // Load fixture data on error
      setAllCases(getFixtureData());
    } finally {
      setLoading(false);
    }
  };

  /**
   * applyFiltersAndSort: Filter and sort cases based on current state
   */
  const applyFiltersAndSort = () => {
    let filtered = allCases.filter((c) => {
      // Risk filter
      const score = c.risk_score || 0;
      if (riskFilter === 'high' && score < 70) return false;
      if (riskFilter === 'medium' && (score < 40 || score >= 70)) return false;
      if (riskFilter === 'low' && score >= 40) return false;

      // Search filter (case-insensitive)
      const search = searchTerm.toLowerCase();
      return (
        c.shipper_name.toLowerCase().includes(search) ||
        c.consignee_name.toLowerCase().includes(search) ||
        c.manifest_id.toLowerCase().includes(search) ||
        c.commodity_code.toLowerCase().includes(search) ||
        (c.commodity_description && c.commodity_description.toLowerCase().includes(search))
      );
    });

    // Sort
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'risk':
          return (b.risk_score || 0) - (a.risk_score || 0);
        case 'date':
          return new Date(b.filing_date).getTime() - new Date(a.filing_date).getTime();
        case 'shipper':
          return a.shipper_name.localeCompare(b.shipper_name);
        default:
          return 0;
      }
    });

    setFilteredCases(filtered);

    // Clear selected case if it doesn't match filtered results
    if (selectedCaseId && !filtered.some((c) => c.id === selectedCaseId)) {
      setSelectedCaseId(null);
    }
  };

  /**
   * calculateMetrics: Compute summary statistics
   */
  const calculateMetrics = (): SummaryMetrics => {
    const highRisk = allCases.filter((c) => (c.risk_score || 0) >= 70).length;
    const mediumRisk = allCases.filter((c) => (c.risk_score || 0) >= 40 && (c.risk_score || 0) < 70).length;
    const lowRisk = allCases.filter((c) => (c.risk_score || 0) < 40).length;
    const totalValue = allCases.reduce((sum, c) => sum + (c.declared_value || 0), 0);
    const avgRiskScore = allCases.length > 0 ? allCases.reduce((sum, c) => sum + (c.risk_score || 0), 0) / allCases.length : 0;

    return {
      highRiskCount: highRisk,
      mediumRiskCount: mediumRisk,
      lowRiskCount: lowRisk,
      totalCases: allCases.length,
      totalValue,
      avgRiskScore,
    };
  };

  const handleCaseSelect = (caseId: string) => {
    setSelectedCaseId(caseId);
  };

  const handleCaseClick = (caseId: string) => {
    navigate(`/cases/${caseId}`);
  };

  const metrics = calculateMetrics();
  const selectedCase = allCases.find((c) => c.id === selectedCaseId);

  return (
    <div className="case-manager-layout">
      <Header title="Illegal Transshipment Intelligence Dashboard" showNav={true} />

      {/* Block A: Case Summary Strip */}
      <CaseSummaryStrip metrics={metrics} isLoading={loading} />

      {/* Block B: Accessibility Toolbar */}
      <AccessibilityToolbar
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
        riskFilter={riskFilter}
        onRiskFilterChange={setRiskFilter}
        sortBy={sortBy}
        onSortByChange={setSortBy}
        resultCount={filteredCases.length}
        totalCount={allCases.length}
        isLoading={loading}
      />

      {/* Block C: Dynamic View Renderer */}
      <main className="case-manager-content" role="main">
        {error && (
          <div className="error-alert" role="alert" aria-label={`Error: ${error}`}>
            <strong>Error loading cases:</strong> {error}
            <button onClick={fetchCases} className="error-retry-btn">
              Retry
            </button>
          </div>
        )}

        {loading ? (
          <div className="loading-state" role="status" aria-label="Loading cases">
            <div className="loading-spinner"></div>
            <p>Loading cases...</p>
          </div>
        ) : filteredCases.length === 0 ? (
          <div className="empty-state" role="status" aria-label="No cases match your filters">
            <p>No cases match your filters.</p>
            <button onClick={() => { setSearchTerm(''); setRiskFilter('all'); }} className="empty-state-btn">
              Clear Filters
            </button>
          </div>
        ) : (
          <>
            {viewMode === 'list' && (
              <CaseListView
                cases={filteredCases}
                onCaseSelect={handleCaseSelect}
                onCaseClick={handleCaseClick}
              />
            )}

            {viewMode === 'split' && (
              <CaseSplitPane
                cases={filteredCases}
                selectedCaseId={selectedCaseId}
                onCaseSelect={handleCaseSelect}
                onCaseClick={handleCaseClick}
              />
            )}

            {viewMode === 'map' && (
              <CaseMapView
                cases={filteredCases}
                selectedCaseId={selectedCaseId}
                onCaseSelect={handleCaseSelect}
              />
            )}
          </>
        )}
      </main>
    </div>
  );
}

/**
 * getFixtureData: Fixture cases for development/testing
 */
function getFixtureData(): CaseCardData[] {
  return [
    {
      id: '1',
      manifest_id: 'MNF-2024-001',
      shipper_name: 'Global Shipping Co.',
      trade_name: 'GSC International',
      entity_type: 'Corporation',
      consignee_name: 'Port Authority Import',
      route_origin: 'China',
      route_destination: 'USA',
      corridor_name: 'Shanghai-LA-Dallas',
      commodity_code: '8708.30.10',
      commodity_description: 'Motor vehicle parts; stamped metal parts',
      declared_value: 145000,
      risk_score: 85,
      filing_date: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
      status: 'Under Review',
    },
    {
      id: '2',
      manifest_id: 'MNF-2024-002',
      shipper_name: 'Pacific Trade LLC',
      trade_name: 'PT Logistics',
      entity_type: 'LLC',
      consignee_name: 'Distribution Center 5',
      route_origin: 'Vietnam',
      route_destination: 'USA',
      corridor_name: 'Ho Chi Minh-Port of Houston',
      commodity_code: '6204.62.90',
      commodity_description: 'Women\'s trousers; synthetic fibers',
      declared_value: 78500,
      risk_score: 45,
      filing_date: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
      status: 'Cleared',
    },
    {
      id: '3',
      manifest_id: 'MNF-2024-003',
      shipper_name: 'Ocean Bridge Trading',
      consignee_name: 'Tech Components Inc.',
      route_origin: 'South Korea',
      route_destination: 'USA',
      corridor_name: 'Busan-Long Beach-Phoenix',
      commodity_code: '8471.30.00',
      commodity_description: 'Automatic data processing machines; input/output units',
      declared_value: 425000,
      risk_score: 92,
      filing_date: new Date().toISOString(),
      status: 'Flagged',
    },
    {
      id: '4',
      manifest_id: 'MNF-2024-004',
      shipper_name: 'Continental Exports Ltd.',
      trade_name: 'CE Premium',
      entity_type: 'Ltd.',
      consignee_name: 'Retail Buyer Group',
      route_origin: 'India',
      route_destination: 'USA',
      corridor_name: 'Chennai-Long Beach',
      commodity_code: '6109.90.50',
      commodity_description: 'T-shirts; knitted, cotton',
      declared_value: 52000,
      risk_score: 28,
      filing_date: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
      status: 'Cleared',
    },
  ];
}
