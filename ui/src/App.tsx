import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useRole } from './context/RoleContext'
import { WorkflowProvider } from './context/WorkflowContext'
import { CommandCenterProvider } from './context/CommandCenterContext'
import Header from './components/layout/Header'
import LoginPage from './pages/LoginPage'
import NotFoundPage from './pages/NotFoundPage'
import ScoringCalibrationPage from './pages/ScoringCalibrationPage'

// V2 Imports
import { useState, useCallback } from 'react'
import V2Layout from './v2/layout/V2Layout'
import V2DashboardPage from './v2/pages/V2DashboardPage'
import V2InvestigationsPage from './v2/pages/V2InvestigationsPage'
import V2ShippingIntelligencePage from './v2/pages/V2ShippingIntelligencePage'
import V2EntitiesPage from './v2/pages/V2EntitiesPage'
import V2WatchlistsPage from './v2/pages/V2WatchlistsPage'
import V2AITuningPage from './v2/pages/V2AITuningPage'
import { CBPOfficer, AIFinding, ReferralPackage, Case, Shipment } from './v2/types/v2.types'
import { useV2Cases } from './v2/hooks/useV2Cases'
import { useV2Referrals } from './v2/hooks/useV2Referrals'
import { api } from './services/api'

// Legacy Imports for v1 workflow
import IngestPage from './pages/IngestPage'

// V2 Pages Wrapper Component
function V2AppWrapper() {
  // Core state
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);

  // Fetch cases and shipments
  const { cases, shipments, loading: casesLoading } = useV2Cases();

  // Custom notes per case
  const [customNotes, setCustomNotes] = useState<Record<string, Array<{ text: string; officerName: string; date: string }>>>({});

  // Synopsis caching
  const [synopsisMap, setSynopsisMap] = useState<Record<string, string>>({});
  const [synopsisLoading, setSynopsisLoading] = useState<Record<string, boolean>>({});

  // Referrals state
  const { referrals, createReferral: createReferralHook, loading: referralsLoading } = useV2Referrals(cases);

  // Draft referral state
  const [draftNarrative, setDraftNarrative] = useState<string>('');
  const [draftLoading, setDraftLoading] = useState(false);

  // Generate AI findings from shipment signals with corridor & commodity context
  const generateFindings = useCallback((): AIFinding[] => {
    const findings: AIFinding[] = [];
    const selectedCase = cases.find(c => c.case_id === selectedCaseId);
    if (!selectedCase) return findings;

    const relatedShipments = shipments.filter(s => {
      // Group by shipper + origin + destination
      return s.shipper_name === selectedCase.target_entity?.split(' / ')[0] &&
             s.origin_country === selectedCase.origin_country;
    });

    if (relatedShipments.length === 0) return findings;

    const shipment = relatedShipments[0];

    const ctx = {
      shipper: shipment.shipper_name || 'Unknown',
      consignee: shipment.manifest_data.consignee || 'Unknown',
      declared_origin: shipment.declared_origin,
      suspected_origin: shipment.suspected_origin,
      element9_declared: shipment.element9_declared_country,
      element9_actual: shipment.element9_actual_country,
      commodity_name: shipment.commodity_name,
      hs_code: shipment.hs_code,
      origin: shipment.origin_country,
      destination: shipment.destination_country,
      dwell_days: shipment.dwell_days || 0,
      container_id: shipment.container_id,
      route: shipment.route || [],
      ad_cvd_applicable: shipment.ad_cvd_applicable,
      ad_cvd_rate: shipment.ad_cvd_rate || 0,
      shipper_age_months: shipment.shipper_age_months || 24,
      declared_weight_kg: shipment.manifest_data.weight_kg,
      h1_score: shipment.h1_score || 0,
      h2_score: shipment.h2_score || 0,
      risk_score: selectedCase.risk_score,
    };

    let findingIndex = 0;

    // 1. ISF_MISMATCH
    if (shipment.manifest_anomalies?.includes('ISF_MISMATCH')) {
      findings.push({
        finding_id: `FND-${selectedCaseId}-${findingIndex++}`,
        title: 'Origin Country Mismatch Detected',
        finding_type: 'Origin Concealment',
        severity: 'Critical',
        confidence: 95,
        explanation: `Declared: ${ctx.declared_origin}, Actual: ${ctx.suspected_origin}. Corridor ${ctx.origin}→${ctx.destination} with ${ctx.commodity_name}. Pattern consistent with transshipment evasion.`,
        evidence_links: ['ISF Element 9 check', 'AIS vessel tracking', 'Manifest inconsistency'],
        verification_status: 'Needs Review',
      });
    }

    // 2. ELEMENT9_MISMATCH
    if (shipment.manifest_anomalies?.includes('ELEMENT9_MISMATCH')) {
      findings.push({
        finding_id: `FND-${selectedCaseId}-${findingIndex++}`,
        title: 'Element 9 Declaration Violation',
        finding_type: 'Origin Concealment',
        severity: 'Critical',
        confidence: 98,
        explanation: `ISF Element 9 contradicts AIS data. Shipper ${ctx.shipper} claims ${ctx.element9_declared}, actual ${ctx.element9_actual}. ${ctx.commodity_name} export from ${ctx.origin}. Probable transshipment concealment.`,
        evidence_links: ['ISF pre-arrival filing', 'AIS vessel track', 'Port authority records'],
        verification_status: 'Needs Review',
      });
    }

    // 3. DWELL_ANOMALY
    if (shipment.manifest_anomalies?.includes('DWELL_ANOMALY') && ctx.dwell_days > 8) {
      findings.push({
        finding_id: `FND-${selectedCaseId}-${findingIndex++}`,
        title: 'AIS Vessel Routing Deviation',
        finding_type: 'Routing Deviation',
        severity: 'High',
        confidence: 92,
        explanation: `Vessel dwell ${ctx.dwell_days}d vs baseline 2-3d at transshipment hub. Route via ${ctx.route[1] || 'SG'}. ${ctx.commodity_name} container ${ctx.container_id.substring(0, 12)}... flagged for extended port stay anomaly.`,
        evidence_links: ['AIS dwell analysis', 'Port schedules', 'Vessel itinerary'],
        verification_status: 'Needs Review',
      });
    }

    // 4. UFLPA: China + high risk
    if (ctx.origin === 'CN' && ctx.risk_score >= 80) {
      findings.push({
        finding_id: `FND-${selectedCaseId}-${findingIndex++}`,
        title: 'UFLPA Forced Labor Correlation',
        finding_type: 'Origin Concealment',
        severity: 'Critical',
        confidence: 88,
        explanation: `China-origin shipment detected: ${ctx.shipper} → ${ctx.consignee}. ${ctx.commodity_name} (HS ${ctx.hs_code}) from high-risk manufacturing region. Risk score ${ctx.risk_score}/100 triggers UFLPA Section 307 withhold-release order (19 CFR 330).`,
        evidence_links: ['Country of origin', 'Trade pattern', 'UFLPA registry'],
        verification_status: 'Needs Review',
      });
    }

    // 5. AD/CVD Active + high risk
    if (ctx.ad_cvd_applicable && ctx.risk_score >= 70) {
      findings.push({
        finding_id: `FND-${selectedCaseId}-${findingIndex++}`,
        title: 'Active Tariff Order Duty Evasion',
        finding_type: 'Tariff Evasion',
        severity: 'Critical',
        confidence: 89,
        explanation: `AD/CVD active: ${ctx.commodity_name} (HS ${ctx.hs_code}) at ${(ctx.ad_cvd_rate * 100).toFixed(1)}% duty rate. Route ${ctx.origin}→${ctx.destination} shows pattern consistent with tariff evasion. Risk ${ctx.risk_score}/100 indicates duty avoidance incentive.`,
        evidence_links: ['ITAR database', 'Tariff analysis', 'Trade history'],
        verification_status: 'Needs Review',
      });
    }

    // 6. Shell Company: New shipper + high risk
    if (ctx.shipper_age_months < 12 && ctx.risk_score >= 75) {
      findings.push({
        finding_id: `FND-${selectedCaseId}-${findingIndex++}`,
        title: 'Newly Established Shell Exporter',
        finding_type: 'Shell Conglomerate',
        severity: 'High',
        confidence: 85,
        explanation: `Shipper ${ctx.shipper} established ${ctx.shipper_age_months} months ago. Claimed capacity for ${ctx.declared_weight_kg}kg ${ctx.commodity_name} export unverified. Entity layering pattern and rapid scaling indicate probable shell company structure.`,
        evidence_links: ['Shipper registry', 'Age analysis', 'Capacity assessment'],
        verification_status: 'Needs Review',
      });
    }

    // 7. Multi-factor convergence
    if (ctx.h2_score >= 20 && ctx.h1_score >= 15) {
      findings.push({
        finding_id: `FND-${selectedCaseId}-${findingIndex++}`,
        title: 'Multi-Factor Risk Corridor Concentration',
        finding_type: 'Origin Concealment',
        severity: 'High',
        confidence: 82,
        explanation: `High-risk corridor: ${ctx.origin}→${ctx.destination} combining H1 tariff incentive (${ctx.h1_score} pts) + H2 anomaly signals (${ctx.h2_score} pts). ${ctx.commodity_name} subject to priority enforcement and heightened examination protocols.`,
        evidence_links: ['H1 tariff analysis', 'H2 anomaly signals', 'Corridor history'],
        verification_status: 'Needs Review',
      });
    }

    return findings;
  }, [selectedCaseId, cases, shipments]);

  // Select case for detail view
  const selectCaseForDetail = useCallback(async (caseObj: Case) => {
    setSelectedCaseId(caseObj.case_id);
    setActiveTab('investigations');

    // Fetch synopsis if not already cached
    if (!synopsisMap[caseObj.case_id]) {
      setSynopsisLoading(prev => ({ ...prev, [caseObj.case_id]: true }));
      try {
        const response = await api.generateSynopsis({
          caseName: caseObj.case_name,
          entity: caseObj.target_entity,
          category: caseObj.product_category,
          shipments: shipments.filter(s => s.shipment_id === caseObj.case_id),
          findings: generateFindings(),
        });
        setSynopsisMap(prev => ({ ...prev, [caseObj.case_id]: response.synopsis || 'Unable to generate synopsis' }));
      } catch (err) {
        setSynopsisMap(prev => ({ ...prev, [caseObj.case_id]: 'Error generating synopsis' }));
      } finally {
        setSynopsisLoading(prev => ({ ...prev, [caseObj.case_id]: false }));
      }
    }
  }, [synopsisMap, shipments, generateFindings]);

  // Handle referral draft generation
  const handleDraftReferral = useCallback(async (caseId: string, sections: string[]) => {
    setDraftLoading(true);
    try {
      const caseObj = cases.find(c => c.case_id === caseId);
      if (!caseObj) return;

      const response = await api.generateDraftReferral({
        caseName: caseObj.case_name,
        targetEntity: caseObj.target_entity,
        category: caseObj.product_category,
        shipments: shipments.filter(s => s.shipment_id === caseId),
        findings: generateFindings(),
        sections,
      });

      setDraftNarrative(response.narrative || '');
      await createReferralHook(caseId, sections);
    } catch (err) {
      setDraftNarrative('Error generating referral draft');
    } finally {
      setDraftLoading(false);
    }
  }, [cases, shipments, createReferralHook, generateFindings]);

  // Memoize findings to prevent infinite re-renders
  const findings = generateFindings();

  const pages: Record<string, React.ReactNode> = {
    dashboard: <V2DashboardPage
      cases={cases}
      shipments={shipments}
      selectCaseForDetail={selectCaseForDetail}
      synopsisMap={synopsisMap}
    />,
    investigations: <V2InvestigationsPage
      cases={cases}
      shipments={shipments}
      selectedCaseId={selectedCaseId}
      setSelectedCaseId={setSelectedCaseId}
      synopsisMap={synopsisMap}
      synopsisLoading={synopsisLoading}
      draftNarrative={draftNarrative}
      setDraftNarrative={setDraftNarrative}
      findings={findings}
      referrals={referrals}
    />,
    shipments: <V2ShippingIntelligencePage />,
    entities: <V2EntitiesPage />,
    watchlists: <V2WatchlistsPage />,
    'ai-tuning': <V2AITuningPage />,
  }

  return (
    <V2Layout
      activeTab={activeTab}
      setActiveTab={setActiveTab}
    >
      {pages[activeTab] || pages.dashboard}
    </V2Layout>
  )
}

function AnalystDashboard() {
  return (
    <div style={{ padding: '2rem' }}>
      <Header title="System Metrics" />
      <div style={{ marginTop: '2rem' }}>
        <h2>AI Analyst Dashboard</h2>
        <p>System layers, API status, model performance metrics</p>
        <p style={{ color: '#999', fontSize: '0.9rem' }}>Coming soon</p>
      </div>
    </div>
  )
}

function AdminDashboard() {
  return (
    <div style={{ padding: '2rem' }}>
      <Header title="System Administration" />
      <div style={{ marginTop: '2rem' }}>
        <h2>Admin Dashboard</h2>
        <p>User management, system configuration, audit logs</p>
        <p style={{ color: '#999', fontSize: '0.9rem' }}>Coming soon</p>
      </div>
    </div>
  )
}

interface ProtectedRouteProps {
  element: React.ReactNode;
  allowedRoles?: ('cbp_officer' | 'analyst' | 'admin')[];
}

function ProtectedRoute({ element, allowedRoles }: ProtectedRouteProps) {
  const { role } = useRole();
  const userEmail = localStorage.getItem('user_email');

  if (!userEmail) {
    return <Navigate to="/login" replace />
  }

  if (allowedRoles && !allowedRoles.includes(role)) {
    return <NotFoundPage />
  }

  return element
}

function App() {
  return (
    <WorkflowProvider>
      <CommandCenterProvider>
        <Router>
          <Routes>
            {/* Auth Routes */}
            <Route path="/login" element={<LoginPage />} />

            {/* V2 Dashboard & Main Navigation */}
            <Route
              path="/dashboard"
              element={<ProtectedRoute element={<V2AppWrapper />} allowedRoles={['cbp_officer', 'analyst']} />}
            />
            <Route
              path="/investigations"
              element={<ProtectedRoute element={<V2AppWrapper />} allowedRoles={['cbp_officer', 'analyst']} />}
            />
            <Route
              path="/shipments"
              element={<ProtectedRoute element={<V2AppWrapper />} allowedRoles={['cbp_officer', 'analyst']} />}
            />
            <Route
              path="/entities"
              element={<ProtectedRoute element={<V2AppWrapper />} allowedRoles={['cbp_officer', 'analyst']} />}
            />
            <Route
              path="/referrals"
              element={<ProtectedRoute element={<V2AppWrapper />} allowedRoles={['cbp_officer', 'analyst']} />}
            />
            <Route
              path="/watchlists"
              element={<ProtectedRoute element={<V2AppWrapper />} allowedRoles={['cbp_officer', 'analyst']} />}
            />
            <Route
              path="/ai-tuning"
              element={<ProtectedRoute element={<V2AppWrapper />} allowedRoles={['analyst']} />}
            />

            {/* Scoring Calibration - Analyst only */}
            <Route
              path="/scoring-calibration"
              element={<ProtectedRoute element={<ScoringCalibrationPage />} allowedRoles={['analyst']} />}
            />

            {/* Manifest Ingest - Upload manifests */}
            <Route
              path="/ingest"
              element={<ProtectedRoute element={<IngestPage />} allowedRoles={['cbp_officer', 'analyst']} />}
            />

            {/* Legacy routes - commented out for reference */}
            {/* <Route path="/command-center" element={<ProtectedRoute element={<CommandCenterPage />} allowedRoles={['cbp_officer', 'analyst']} />} /> */}
            {/* <Route path="/cases/:shipmentId" element={<ProtectedRoute element={<CaseViewerPage />} allowedRoles={['cbp_officer', 'analyst']} />} /> */}
            {/* <Route path="/dashboard/analyst" element={<ProtectedRoute element={<AnalystDashboard />} allowedRoles={['analyst']} />} /> */}
            {/* <Route path="/admin" element={<ProtectedRoute element={<AdminDashboard />} allowedRoles={['admin']} />} /> */}

            {/* Root redirect to dashboard or login */}
            <Route path="/" element={<RootRedirect />} />

            {/* 404 */}
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </Router>
      </CommandCenterProvider>
    </WorkflowProvider>
  )
}

function RootRedirect() {
  const userEmail = localStorage.getItem('user_email');
  const userRole = localStorage.getItem('user_role') as 'cbp_officer' | 'analyst' | 'admin' | null;

  if (!userEmail) {
    return <Navigate to="/login" replace />
  }

  // All authenticated users go to V2 dashboard
  return <Navigate to="/dashboard" replace />
}

export default App
