import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useRole } from '../context/RoleContext';
import USWDSLayout from '../components/layout/USWDSLayout';
import FeedbackInterface from '../components/scoring/FeedbackInterface';
import AltanaVerificationPanel from '../components/scoring/AltanaVerificationPanel';
import CollapsibleSection from '../components/common/CollapsibleSection';
import { ChevronDown, ChevronUp, AlertTriangle, TrendingUp, Users, Activity } from 'lucide-react';
import { API_BASE_URL } from '../services/apiUrl';
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
}

interface ThreeLevelScoreData {
  corridor_score: number;
  vessel_score: number;
  manifest_score: number;
  total_score: number;
  risk_level: string;
  requires_altana: boolean;
  weights: {
    w_corridor: number;
    w_vessel: number;
    w_manifest: number;
  };
  components: any;
  xai_factors: string[];
}

export default function ModernCaseInvestigationPage() {
  const { role } = useRole();
  const { shipmentId } = useParams<{ shipmentId?: string }>();
  const [caseData, setCaseData] = useState<Case | null>(null);
  const [threeLevelScore, setThreeLevelScore] = useState<ThreeLevelScoreData | null>(null);
  const [loading, setLoading] = useState(true);
  const [showFeedback, setShowFeedback] = useState(false);
  const [showAltanaPanel, setShowAltanaPanel] = useState(false);

  // Collapsible sections state
  const [expandedSections, setExpandedSections] = useState({
    overview: true,
    scoring: true,
    factors: false,
    timeline: false,
    altana: threeLevelScore?.requires_altana ? true : false,
    actions: true,
  });

  useEffect(() => {
    fetchCase();
  }, [shipmentId]);

  const fetchCase = async () => {
    try {
      let shipment: Case | null = null;

      if (shipmentId) {
        const response = await fetch(`${API_BASE_URL}/shipments`);
        const data = await response.json();
        if (data.shipments) {
          shipment = data.shipments.find((s: Case) => s.id === shipmentId) || null;
          if (shipment) {
            setCaseData(shipment);
          }
        }
      } else {
        const response = await fetch(`${API_BASE_URL}/shipments?limit=1`);
        const data = await response.json();
        if (data.shipments && data.shipments.length > 0) {
          shipment = data.shipments[0];
          setCaseData(shipment);
        }
      }

      if (shipment) {
        try {
          const scoreResponse = await fetch(
            `${API_BASE_URL}/score/three-level/${shipment.id}?` +
            `shipper_name=${encodeURIComponent(shipment.shipper_name)}&` +
            `shipper_country=${shipment.origin_country}&` +
            `consignee_name=${encodeURIComponent(shipment.consignee_name)}&` +
            `consignee_country=${shipment.destination_country}&` +
            `hs_code=${shipment.hs_code}&` +
            `declared_value_usd=${shipment.declared_value_usd}&` +
            `declared_weight_kg=${shipment.declared_weight_kg || 0}&` +
            `vessel_name=${encodeURIComponent(shipment.vessel_name || '')}`,
            { method: 'POST' }
          );

          if (scoreResponse.ok) {
            const scoreData = await scoreResponse.json();
            setThreeLevelScore(scoreData);
          }
        } catch (error) {
          console.error('Failed to fetch three-level score:', error);
        }
      }
    } catch (error) {
      console.error('Failed to fetch case:', error);
    } finally {
      setLoading(false);
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
            <div className="score-display" style={{ borderColor: getRiskColor(threeLevelScore?.total_score || caseData.risk_score) }}>
              <div className="score-number" style={{ color: getRiskColor(threeLevelScore?.total_score || caseData.risk_score) }}>
                {Math.round(threeLevelScore?.total_score || caseData.risk_score)}
              </div>
              <div className="score-label">RISK</div>
              <div className="risk-badge" style={{ backgroundColor: getRiskColor(threeLevelScore?.total_score || caseData.risk_score) }}>
                {getRiskLevel(threeLevelScore?.total_score || caseData.risk_score)}
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

        {/* SCORING SECTION */}
        {threeLevelScore && (
          <CollapsibleSection
            title="📊 Three-Level Risk Scoring"
            expanded={expandedSections.scoring}
            onToggle={() => toggleSection('scoring')}
          >
            <div className="scoring-grid">
              {/* Corridor Score */}
              <div className="score-card">
                <div className="card-header">
                  <span className="card-title">Level 1: Corridor Risk</span>
                  <span className="card-weight">{(threeLevelScore.weights.w_corridor * 100).toFixed(0)}%</span>
                </div>
                <div className="score-value">{Math.round(threeLevelScore.corridor_score)}</div>
                <table className="mini-table">
                  <tbody>
                    <tr>
                      <td>Volume Spike:</td>
                      <td className="number">{Math.round(threeLevelScore.components.corridor?.macro_volume_spike || 0)}</td>
                    </tr>
                    <tr>
                      <td>Regulatory:</td>
                      <td className="number">{Math.round(threeLevelScore.components.corridor?.regulatory_delta || 0)}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              {/* Vessel Score */}
              <div className="score-card">
                <div className="card-header">
                  <span className="card-title">Level 2: Vessel Risk</span>
                  <span className="card-weight">{(threeLevelScore.weights.w_vessel * 100).toFixed(0)}%</span>
                </div>
                <div className="score-value">{Math.round(threeLevelScore.vessel_score)}</div>
                <table className="mini-table">
                  <tbody>
                    <tr>
                      <td>FTZ Loiter:</td>
                      <td className="number">{Math.round(threeLevelScore.components.vessel?.ftz_loitering || 0)}</td>
                    </tr>
                    <tr>
                      <td>AIS Dark:</td>
                      <td className="number">{Math.round(threeLevelScore.components.vessel?.ais_dark_activity || 0)}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              {/* Manifest Score */}
              <div className="score-card">
                <div className="card-header">
                  <span className="card-title">Level 3: Manifest Risk</span>
                  <span className="card-weight">{(threeLevelScore.weights.w_manifest * 100).toFixed(0)}%</span>
                </div>
                <div className="score-value">{Math.round(threeLevelScore.manifest_score)}</div>
                <table className="mini-table">
                  <tbody>
                    <tr>
                      <td>Entity Match:</td>
                      <td className="number">{Math.round(threeLevelScore.components.manifest?.entity_resolution_match || 0)}</td>
                    </tr>
                    <tr>
                      <td>Network:</td>
                      <td className="number">{Math.round(threeLevelScore.components.manifest?.network_anomaly || 0)}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </CollapsibleSection>
        )}

        {/* XAI FACTORS SECTION */}
        {threeLevelScore?.xai_factors && (
          <CollapsibleSection
            title="🎯 Risk Factors"
            expanded={expandedSections.factors}
            onToggle={() => toggleSection('factors')}
          >
            <div className="factors-table">
              <table>
                <tbody>
                  {threeLevelScore.xai_factors.map((factor, idx) => (
                    <tr key={idx}>
                      <td className="factor-icon">•</td>
                      <td>{factor}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CollapsibleSection>
        )}

        {/* ALTANA SECTION */}
        {threeLevelScore?.requires_altana && (
          <CollapsibleSection
            title="⚡ Altana Atlas Verification (Score ≥90%)"
            expanded={expandedSections.altana}
            onToggle={() => toggleSection('altana')}
          >
            {!showAltanaPanel ? (
              <div className="altana-prompt">
                <p>Supply chain deep-dive verification required for this high-risk shipment.</p>
                <button
                  className="btn-primary"
                  onClick={() => setShowAltanaPanel(true)}
                >
                  Run Verification
                </button>
              </div>
            ) : (
              <AltanaVerificationPanel
                shipmentId={caseData.id}
                riskScore={threeLevelScore.total_score}
                onClose={() => setShowAltanaPanel(false)}
              />
            )}
          </CollapsibleSection>
        )}

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
          </div>

          {showFeedback && (
            <div className="feedback-wrapper">
              <FeedbackInterface
                shipmentId={caseData.id}
                originalScore={threeLevelScore?.total_score || caseData.risk_score}
                onSubmit={() => {
                  setShowFeedback(false);
                  fetchCase();
                }}
                onCancel={() => setShowFeedback(false)}
              />
            </div>
          )}
        </CollapsibleSection>

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
