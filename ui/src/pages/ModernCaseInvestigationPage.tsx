import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useRole } from '../context/RoleContext';
import USWDSLayout from '../components/layout/USWDSLayout';
import FeedbackInterface from '../components/scoring/FeedbackInterface';
import AltanaVerificationPanel from '../components/scoring/AltanaVerificationPanel';
import CollapsibleSection from '../components/common/CollapsibleSection';
import RiskScoreBreakdown from '../components/risk-scoring/RiskScoreBreakdown';
import ReferralPackageGenerationTab from '../components/referral-generation/ReferralPackageGenerationTab';
import { ChevronDown, ChevronUp, AlertTriangle, TrendingUp, Users, Activity } from 'lucide-react';
import { API_BASE_URL } from '../services/apiUrl';
import { RiskScoreBreakdown as RiskScoreBreakdownType } from '../components/risk-scoring/types';
import '../styles/CompactDashboard.css';

interface Case {
  id: string;
  shipper_name: string;
  consignee_name: string;
  origin_country: string;
  destination_country: string;
  hs_code: string;
  declared_value_usd: number;
  declared_weight_kg?: number;
  risk_score: number;
  h1_score?: number;
  h2_score?: number;
  vessel_name?: string;
  status: string;
  created_at?: string;
  // Additional fields for 7-factor risk scoring
  element9_is_mismatch?: boolean;
  element9_declared_country?: string;
  element9_actual_country?: string;
  ad_cvd_rate?: number;
  shipper_age_months?: number;
  dwell_days?: number;
  ais_stuffing_country?: string;
  port_calls?: string | string[];
  vessel_flag?: string;
  vessel_imo?: string;
  prior_violations?: number;
  ofac_status?: string;
  ownership_opacity?: boolean;
  price_variance_percent?: number;
  unit_price_per_kg?: number;
  commodity_code?: string;
  commodity_name?: string;
}


export default function ModernCaseInvestigationPage() {
  const { role } = useRole();
  const { shipmentId } = useParams<{ shipmentId?: string }>();
  const [caseData, setCaseData] = useState<Case | null>(null);
  const [riskBreakdown, setRiskBreakdown] = useState<RiskScoreBreakdownType | null>(null);
  const [riskLoading, setRiskLoading] = useState(false);
  const [riskError, setRiskError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [showFeedback, setShowFeedback] = useState(false);
  const [showAltanaPanel, setShowAltanaPanel] = useState(false);
  const [showReferralPackage, setShowReferralPackage] = useState(false);

  // Collapsible sections state
  const [expandedSections, setExpandedSections] = useState({
    overview: true,
    scoring: true,
    actions: true,
  });

  useEffect(() => {
    fetchCase();
  }, [shipmentId]);

  const fetchCase = async () => {
    try {
      let shipment: Case | null = null;

      if (shipmentId) {
        // Fetch complete shipment data from dedicated endpoint
        const response = await fetch(`${API_BASE_URL}/data/shipments/${shipmentId}`);
        if (response.ok) {
          shipment = await response.json();
          setCaseData(shipment);
        } else {
          console.error('Failed to fetch shipment detail');
        }
      } else {
        // Fallback: fetch from list and get first
        const response = await fetch(`${API_BASE_URL}/shipments?limit=1`);
        const data = await response.json();
        if (data.data && data.data.length > 0) {
          // Get the full shipment details using the ID from list
          const firstId = data.data[0].id;
          const detailResponse = await fetch(`${API_BASE_URL}/data/shipments/${firstId}`);
          if (detailResponse.ok) {
            shipment = await detailResponse.json();
            setCaseData(shipment);
          }
        }
      }

      if (shipment) {
        await fetchRiskBreakdown(shipment.id, shipment);
      }
    } catch (error) {
      console.error('Failed to fetch case:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchRiskBreakdown = async (shipmentId: string, shipment: Case) => {
    try {
      setRiskLoading(true);
      setRiskError(null);

      // Pass all available shipment fields to the 7-factor risk engine
      const shipmentData = {
        id: shipmentId,
        // Basic info
        shipper_name: shipment.shipper_name,
        origin_country: shipment.origin_country,
        consignee_name: shipment.consignee_name,
        destination_country: shipment.destination_country,
        // Commodity
        hs_code: shipment.hs_code,
        commodity_code: shipment.commodity_code,
        commodity_name: shipment.commodity_name,
        declared_value_usd: shipment.declared_value_usd,
        declared_weight_kg: shipment.declared_weight_kg || 0,
        unit_price_per_kg: shipment.unit_price_per_kg || 0,
        price_variance_percent: shipment.price_variance_percent || 0,
        // Vessel & Routing
        vessel_name: shipment.vessel_name || '',
        vessel_imo: shipment.vessel_imo || '',
        vessel_flag: shipment.vessel_flag || '',
        dwell_days: shipment.dwell_days || 0,
        port_calls: shipment.port_calls || [],
        ais_stuffing_country: shipment.ais_stuffing_country || '',
        // Documentation (Element 9 & ISF)
        element9_is_mismatch: shipment.element9_is_mismatch || false,
        element9_declared_country: shipment.element9_declared_country,
        element9_actual_country: shipment.element9_actual_country,
        isf_amendments: 0, // Default if not available
        // Party Profile
        shipper_age_months: shipment.shipper_age_months || 12,
        prior_violations: shipment.prior_violations || 0,
        ofac_status: shipment.ofac_status || 'CLEAR',
        ownership_opacity: shipment.ownership_opacity || false,
        // Trade/Corridor
        ad_cvd_rate: shipment.ad_cvd_rate || 0,
        ad_cvd_applicable: (shipment.ad_cvd_rate || 0) > 0,
        // Metadata
        created_at: shipment.created_at,
      };

      const response = await fetch(`${API_BASE_URL}/score/full-breakdown/${shipmentId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(shipmentData),
      });

      if (response.ok) {
        const breakdown = await response.json();
        setRiskBreakdown(breakdown);
      } else {
        setRiskError('Failed to calculate risk breakdown');
      }
    } catch (error) {
      console.error('Failed to fetch risk breakdown:', error);
      setRiskError('Error calculating risk score');
    } finally {
      setRiskLoading(false);
    }
  };

  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  if (loading || !caseData) {
    return <USWDSLayout title="Case Investigation"><div className="loading">Loading...</div></USWDSLayout>;
  }

  const getRiskColor = (score: number) => {
    if (score >= 90) return '#dc2626';
    if (score >= 70) return '#ea580c';
    if (score >= 50) return '#eab308';
    return '#22c55e';
  };

  const getRiskLevel = (score: number) => {
    if (score >= 90) return 'CRITICAL';
    if (score >= 70) return 'HIGH';
    if (score >= 50) return 'MEDIUM';
    return 'LOW';
  };

  return (
    <USWDSLayout title="Case Investigation">
      <div className="compact-dashboard">
        {/* HEADER ROW */}
        <div className="dashboard-header">
          <div className="header-left">
            <h2>{caseData.id}</h2>
            <p className="header-subtitle">
              {caseData.shipper_name} → {caseData.consignee_name}
            </p>
          </div>
          <div className="header-right">
            <div className="score-display" style={{ borderColor: getRiskColor(riskBreakdown?.final_score || caseData.risk_score) }}>
              <div className="score-number" style={{ color: getRiskColor(riskBreakdown?.final_score || caseData.risk_score) }}>
                {Math.round(riskBreakdown?.final_score || caseData.risk_score)}
              </div>
              <div className="score-label">RISK</div>
              <div className="risk-badge" style={{ backgroundColor: getRiskColor(riskBreakdown?.final_score || caseData.risk_score) }}>
                {getRiskLevel(riskBreakdown?.final_score || caseData.risk_score)}
              </div>
            </div>
          </div>
        </div>

        {/* OVERVIEW SECTION */}
        <CollapsibleSection
          title="📋 Shipment Overview"
          expanded={expandedSections.overview}
          onToggle={() => toggleSection('overview')}
        >
          <div className="section-table">
            <table>
              <tbody>
                <tr>
                  <td className="label">Shipper:</td>
                  <td>{caseData.shipper_name}</td>
                  <td className="label">Consignee:</td>
                  <td>{caseData.consignee_name}</td>
                </tr>
                <tr>
                  <td className="label">Origin:</td>
                  <td>{caseData.origin_country}</td>
                  <td className="label">Destination:</td>
                  <td>{caseData.destination_country}</td>
                </tr>
                <tr>
                  <td className="label">HTS Code:</td>
                  <td className="code">{caseData.hs_code}</td>
                  <td className="label">Value:</td>
                  <td>${caseData.declared_value_usd?.toLocaleString()}</td>
                </tr>
                <tr>
                  <td className="label">Vessel:</td>
                  <td>{caseData.vessel_name || '—'}</td>
                  <td className="label">Status:</td>
                  <td>
                    <span className="status-badge">{caseData.status}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </CollapsibleSection>

        {/* 7-FACTOR RISK SCORING SECTION */}
        <CollapsibleSection
          title="📊 7-Factor Risk Breakdown"
          expanded={expandedSections.scoring}
          onToggle={() => toggleSection('scoring')}
        >
          {riskBreakdown ? (
            <RiskScoreBreakdown
              data={riskBreakdown}
              loading={riskLoading}
              error={riskError || undefined}
              onRefresh={() => caseData && fetchRiskBreakdown(caseData.id, caseData)}
            />
          ) : (
            <RiskScoreBreakdown
              data={riskBreakdown || { shipment_id: caseData.id, components: [], subtotal: 0, final_score: 0, confidence_interval: '—' }}
              loading={riskLoading}
              error={riskError || undefined}
              onRefresh={() => caseData && fetchRiskBreakdown(caseData.id, caseData)}
            />
          )}
        </CollapsibleSection>

        {/* ACTIONS SECTION */}
        <CollapsibleSection
          title="🎯 Recommended Actions"
          expanded={expandedSections.actions}
          onToggle={() => toggleSection('actions')}
        >
          <div className="actions-grid">
            <button className="action-btn action-clear">Clear Shipment</button>
            <button className="action-btn action-examine">Examine on Arrival</button>
            <button className="action-btn action-trled">TRLED Referral</button>
            {(role === 'analyst' || role === 'admin') && (
              <button
                className="action-btn action-feedback"
                onClick={() => setShowFeedback(!showFeedback)}
              >
                Provide Feedback
              </button>
            )}
            <button
              className="action-btn action-trled"
              onClick={() => setShowReferralPackage(!showReferralPackage)}
              style={{ backgroundColor: '#0050d8' }}
            >
              📋 Referral Package
            </button>
          </div>

          {showFeedback && (
            <div className="feedback-wrapper">
              <FeedbackInterface
                shipmentId={caseData.id}
                originalScore={riskBreakdown?.final_score || caseData.risk_score}
                onSubmit={() => {
                  setShowFeedback(false);
                  fetchCase();
                }}
                onCancel={() => setShowFeedback(false)}
              />
            </div>
          )}
        </CollapsibleSection>

        {/* REFERRAL PACKAGE SECTION */}
        {showReferralPackage && (
          <CollapsibleSection
            title="📋 Referral Package Generation"
            expanded={true}
            onToggle={() => setShowReferralPackage(false)}
          >
            <ReferralPackageGenerationTab shipmentId={caseData.id} />
          </CollapsibleSection>
        )}

        {/* NOTES SECTION */}
        <CollapsibleSection
          title="📝 Investigation Notes"
          expanded={false}
          onToggle={() => {}}
        >
          <textarea
            className="notes-textarea"
            placeholder="Add investigation findings, evidence, and next steps..."
            rows={3}
          />
          <div className="notes-actions">
            <button className="btn-primary">Save Notes</button>
            <button className="btn-secondary">Export Referral</button>
          </div>
        </CollapsibleSection>
      </div>
    </USWDSLayout>
  );
}
