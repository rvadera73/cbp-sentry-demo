import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Header from '../components/layout/Header'
import ScoreBreakdown from '../components/scoring/ScoreBreakdown'
import WorkflowSignalMap from '../components/cases/WorkflowSignalMap'
import EntityChainViewer from '../components/cases/EntityChainViewer'
import ReferralPackageViewer from '../components/cases/ReferralPackageViewer'
import { AlertCircle, ChevronLeft } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { scoringApi, type ScoringResponse } from '../services/scoringApi'
import { cordApi, type SearchFirstInvestigateResponse, type EntityChain, type RiskFlag } from '../services/cordApi'
import '../styles/CaseViewerPage.css'

interface Shipment {
  id: string;
  shipper_name: string;
  consignee_name: string;
  origin_country: string;
  destination_country: string;
  hs_code: string;
  declared_value_usd: number;
  declared_weight_kg: number;
  vessel_name?: string;
  risk_score: number;
  status: string;
}

export default function CaseViewerPage() {
  const { shipmentId } = useParams<{ shipmentId: string }>();
  const navigate = useNavigate();
  const [shipment, setShipment] = useState<Shipment | null>(null);
  const [scoringData, setScoringData] = useState<ScoringResponse | null>(null);
  const [cordData, setCordData] = useState<SearchFirstInvestigateResponse | null>(null);
  const [entityChains, setEntityChains] = useState<EntityChain[]>([]);
  const [riskFlags, setRiskFlags] = useState<RiskFlag[]>([]);
  const [loading, setLoading] = useState(true);
  const [scoringLoading, setScoringLoading] = useState(false);
  const [cordLoading, setCordLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('workflow');
  const [notes, setNotes] = useState('');
  const [action, setAction] = useState<string>('');

  useEffect(() => {
    if (shipmentId) {
      fetchShipment(shipmentId);
    }
  }, [shipmentId]);

  const fetchShipment = async (id: string) => {
    try {
      // Fetch shipment data through API gateway
      const apiBaseUrl = ((import.meta as any).env?.VITE_API_BASE_URL as string | undefined) ||
        (typeof window !== 'undefined' && window.location.hostname === 'localhost'
          ? 'http://localhost:8000/api'
          : 'https://sentry-api-cbp-sentry.run.app/api');
      const response = await fetch(`${apiBaseUrl}/data/shipments/${id}`);
      if (!response.ok) throw new Error('Failed to fetch shipment');
      const data = await response.json();
      setShipment(data);

      // Fetch scoring data
      setScoringLoading(true);
      const shipmentInput = {
        shipment_id: id,
        shipper_name: data.shipper_name,
        consignee_name: data.consignee_name,
        origin_country: data.origin_country,
        destination_country: data.destination_country,
        origin_port: data.origin_port || '',
        destination_port: data.destination_port || '',
        hs_code: data.hs_code,
        declared_value_usd: data.declared_value_usd,
        declared_weight_kg: data.declared_weight_kg,
        vessel_name: data.vessel_name || '',
        dwell_days: data.dwell_days || 2.1,
        declared_origin: data.declared_origin || data.origin_country,
        ais_stuffing_country: data.ais_stuffing_country || data.origin_country,
        port_calls: data.port_calls || [],
        shipper_age_months: data.shipper_age_months || 24,
        importer_age_months: data.importer_age_months || 24,
        importer_ytd_volume: data.importer_ytd_volume || 0,
        senzing_confidence: data.senzing_confidence || 0.85,
        entity_type: data.entity_type || 'company',
        ofac_match: data.ofac_match || false,
        watchlist_match: data.watchlist_match || false,
      };

      const scoringResponse = await scoringApi.calculateScore(shipmentInput);
      setScoringData(scoringResponse);

      // Fetch entity chains via search-first CORD integration
      setCordLoading(true);
      try {
        const cordResponse = await cordApi.investigateShipment({
          manifest_id: id,
          shipper_name: data.shipper_name,
          shipper_country: data.origin_country,
          consignee_name: data.consignee_name,
          consignee_country: data.destination_country,
          declared_origin: data.declared_origin || data.origin_country,
          base_score: data.risk_score || 30,
        });
        setCordData(cordResponse);
        setEntityChains(cordResponse.investigation?.entity_chains || []);
        setRiskFlags(cordResponse.investigation?.risk_flags || []);
      } catch (cordError) {
        console.warn('CORD investigation failed:', cordError);
        // Don't fail the whole page if CORD fails
      } finally {
        setCordLoading(false);
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error occurred';
      console.error('Fetch error:', errorMsg);
      setError(errorMsg);
    } finally {
      setLoading(false);
      setScoringLoading(false);
    }
  };

  if (loading) {
    return (
      <div>
        <Header />
        <div className="case-viewer-loading">Loading case...</div>
      </div>
    );
  }

  if (!shipment) {
    return (
      <div>
        <Header />
        <div className="case-viewer-error">
          <AlertCircle size={32} />
          <h2>Case Not Found</h2>
          <button onClick={() => navigate('/dashboard')} className="btn-primary">
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  const getRiskColor = (score: number) => {
    if (score >= 70) return '#dc2626';
    if (score >= 40) return '#f97316';
    return '#16a34a';
  };

  const getRiskLabel = (score: number) => {
    if (score >= 70) return 'HIGH';
    if (score >= 40) return 'MEDIUM';
    return 'LOW';
  };

  // Use calculated score, not DB value
  const currentScore = scoringData?.total_score ?? shipment?.risk_score ?? 0;

  // Get viable officer actions based on score
  const getViableActions = (score: number) => {
    const actions = [];
    if (score >= 90) {
      actions.push({ id: 'refer', label: '📋 TRLED Referral', color: '#dc2626' });
      actions.push({ id: 'examine', label: '🔍 Examine on Arrival', color: '#f97316' });
    } else if (score >= 70) {
      actions.push({ id: 'examine', label: '🔍 Examine on Arrival', color: '#f97316' });
      actions.push({ id: 'cf28', label: '📝 CF-28 Exam', color: '#eab308' });
    } else if (score >= 40) {
      actions.push({ id: 'cf28', label: '📝 CF-28 Exam', color: '#eab308' });
      actions.push({ id: 'clear', label: '✓ Clear', color: '#16a34a' });
    } else {
      actions.push({ id: 'clear', label: '✓ Clear', color: '#16a34a' });
    }
    return actions;
  };

  const viableActions = getViableActions(currentScore);

  return (
    <div className="case-viewer-page">
      <Header />

      <div className="case-viewer-container">
        {/* Back Button & Case Header */}
        <div className="case-header">
          <button onClick={() => navigate('/dashboard')} className="btn-back">
            <ChevronLeft size={20} />
            Back to Cases
          </button>
          <div className="case-header-info">
            <h1>
              {shipment.shipper_name} → {shipment.consignee_name}
            </h1>
            <div className="case-meta">
              <span className="meta-item">
                <strong>HTS Code:</strong> {shipment.hs_code}
              </span>
              <span className="meta-item">
                <strong>Route:</strong> {shipment.origin_country} → {shipment.destination_country}
              </span>
              <span className="meta-item">
                <strong>Value:</strong> ${shipment.declared_value_usd.toLocaleString()}
              </span>
              <span className="meta-item">
                <strong>Vessel:</strong> {shipment.vessel_name || 'N/A'}
              </span>
            </div>
          </div>
        </div>

        {/* Workflow Signal Header - Sticky at Top */}
        <div className="workflow-header-sticky">
          <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
            <h3 style={{ margin: '0 0 16px 0', fontSize: '14px', fontWeight: '600', color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Investigation Workflow Status
            </h3>
            {/* Compact Workflow Status */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '12px', marginBottom: '16px' }}>
              {[
                { step: 'Manifest', status: 'completed', signal: '✓' },
                { step: 'H1 Corridor', status: 'completed', signal: `${scoringData?.h1.score || 0} pts` },
                { step: 'H2 Vessel', status: 'completed', signal: `${scoringData?.h2.score || 0} pts` },
                { step: 'H3 Intelligence', status: 'completed', signal: `${scoringData?.h3.score || 0} pts` },
                { step: 'Senzing', status: cordLoading ? 'active' : 'completed', signal: `${entityChains.reduce((sum, chain) => sum + (chain.entities?.length || 0), 0)} entities` },
                { step: currentScore >= 70 ? 'Altana' : 'Decision', status: currentScore >= 70 && cordLoading ? 'active' : 'completed', signal: currentScore >= 70 ? 'Verifying' : '✓' },
              ].map((item, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '12px',
                    borderRadius: '6px',
                    background: item.status === 'completed' ? '#f0fdf4' : item.status === 'active' ? '#eff6ff' : '#fafafa',
                    border: `1px solid ${item.status === 'completed' ? '#16a34a' : item.status === 'active' ? '#3b82f6' : '#d1d5db'}`,
                    textAlign: 'center',
                  }}
                >
                  <div style={{ fontSize: '12px', fontWeight: '600', color: item.status === 'completed' ? '#16a34a' : item.status === 'active' ? '#3b82f6' : '#6b7280' }}>
                    {item.step}
                  </div>
                  <div style={{ fontSize: '13px', fontWeight: '700', color: '#1f2937', marginTop: '4px' }}>
                    {item.signal}
                  </div>
                </div>
              ))}
            </div>
            {/* Signal Health Indicators */}
            <div style={{ display: 'flex', gap: '16px', padding: '12px', background: '#fafafa', borderRadius: '6px', fontSize: '13px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ display: 'inline-block', width: '10px', height: '10px', borderRadius: '50%', background: '#16a34a' }}></span>
                <span>Good (Green)</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ display: 'inline-block', width: '10px', height: '10px', borderRadius: '50%', background: '#eab308' }}></span>
                <span>Fine (Yellow)</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ display: 'inline-block', width: '10px', height: '10px', borderRadius: '50%', background: '#dc2626' }}></span>
                <span>Bad (Red)</span>
              </div>
              <div style={{ marginLeft: 'auto', fontWeight: '600', color: currentScore >= 70 ? '#dc2626' : currentScore >= 40 ? '#f97316' : '#16a34a' }}>
                {Math.round(currentScore)}/100 {currentScore >= 70 ? '🔴 HIGH' : currentScore >= 40 ? '🟡 MEDIUM' : '🟢 LOW'}
              </div>
            </div>
          </div>
        </div>

        <div className="case-content">
          {/* Risk Gauge & Action Buttons */}
          <div className="case-sidebar">
            <div className="risk-gauge-container">
              <svg className="risk-gauge" viewBox="0 0 200 200">
                <circle cx="100" cy="100" r="90" fill="none" stroke="#e5e5e5" strokeWidth="20" />
                <circle
                  cx="100"
                  cy="100"
                  r="90"
                  fill="none"
                  stroke={getRiskColor(currentScore)}
                  strokeWidth="20"
                  strokeDasharray={`${((currentScore / 100) * 565.48)}, 565.48`}
                  transform="rotate(-90 100 100)"
                />
                <text x="100" y="85" textAnchor="middle" fontSize="36" fontWeight="700" fill="#1e293b">
                  {Math.round(currentScore)}
                </text>
                <text x="100" y="110" textAnchor="middle" fontSize="14" fill="#666">
                  {getRiskLabel(currentScore)}
                </text>
              </svg>
            </div>

            <div className="action-buttons">
              <h3>Officer Action</h3>
              <p style={{ fontSize: '12px', color: '#666', marginBottom: '12px' }}>
                Score {Math.round(currentScore)}/100 — Showing viable options
              </p>
              {viableActions.map(btn => (
                <button
                  key={btn.id}
                  className={`action-btn ${action === btn.id ? 'active' : ''}`}
                  style={action === btn.id ? { backgroundColor: btn.color, color: 'white' } : { borderColor: btn.color, color: btn.color }}
                  onClick={() => setAction(btn.id)}
                >
                  {btn.label}
                </button>
              ))}
            </div>
          </div>

          {/* Tabs */}
          <div className="case-tabs-container">
            <div className="tabs-header">
              <button
                className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
                onClick={() => setActiveTab('overview')}
              >
                📋 Overview
              </button>
              <button
                className={`tab-btn ${activeTab === 'score-breakdown' ? 'active' : ''}`}
                onClick={() => setActiveTab('score-breakdown')}
              >
                📊 Score Breakdown
              </button>
              <button
                className={`tab-btn ${activeTab === 'workflow' ? 'active' : ''}`}
                onClick={() => setActiveTab('workflow')}
              >
                🔄 Workflow & Signals
              </button>
              <button
                className={`tab-btn ${activeTab === 'entity-chain' ? 'active' : ''}`}
                onClick={() => setActiveTab('entity-chain')}
              >
                🔗 Entity Chain
              </button>
              <button
                className={`tab-btn ${activeTab === 'referral' ? 'active' : ''}`}
                onClick={() => setActiveTab('referral')}
              >
                📦 Referral Package
              </button>
            </div>

            <div className="tab-content">
              {activeTab === 'overview' && (
                <div className="tab-panel">
                  <div style={{ marginBottom: '24px', padding: '16px', background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: '8px' }}>
                    <h3 style={{ margin: '0 0 12px 0', fontSize: '15px', fontWeight: '600', color: '#1e40af' }}>
                      🤖 AI Investigation Summary
                    </h3>
                    <p style={{ margin: 0, fontSize: '14px', color: '#1f2937', lineHeight: '1.6' }}>
                      {shipment.shipper_name} is a {scoringData?.h1.score ? `${scoringData.h1.score > 20 ? 'high-risk' : 'moderate-risk'}` : ''} shipper in the {shipment.origin_country}→{shipment.destination_country} corridor.
                      Analysis shows {riskFlags.length > 0 ? `${riskFlags.length} risk flag(s) detected` : 'no major flags'}.
                      The shipment has {entityChains.length > 0 ? `a ${entityChains.reduce((sum, c) => sum + (c.entities?.length || 0), 0)}-entity ownership chain` : 'direct ownership'}.
                      Recommended action: <strong>{currentScore >= 90 ? 'TRLED Referral' : currentScore >= 70 ? 'Examine on Arrival' : currentScore >= 40 ? 'CF-28 Exam' : 'Clear to Release'}</strong>
                    </p>
                  </div>
                  <h3 style={{ marginBottom: '12px', fontSize: '16px', fontWeight: '600', color: '#1f2937' }}>Shipment Details</h3>
                  <table className="overview-table">
                    <tbody>
                      <tr>
                        <td><strong>Shipper</strong></td>
                        <td>{shipment.shipper_name}</td>
                      </tr>
                      <tr>
                        <td><strong>Consignee</strong></td>
                        <td>{shipment.consignee_name}</td>
                      </tr>
                      <tr>
                        <td><strong>HTS Code</strong></td>
                        <td><code>{shipment.hs_code}</code></td>
                      </tr>
                      <tr>
                        <td><strong>Origin</strong></td>
                        <td>{shipment.origin_country}</td>
                      </tr>
                      <tr>
                        <td><strong>Destination</strong></td>
                        <td>{shipment.destination_country}</td>
                      </tr>
                      <tr>
                        <td><strong>Declared Value</strong></td>
                        <td>${shipment.declared_value_usd.toLocaleString()}</td>
                      </tr>
                      <tr>
                        <td><strong>Weight</strong></td>
                        <td>{shipment.declared_weight_kg.toLocaleString()} kg</td>
                      </tr>
                      <tr>
                        <td><strong>Vessel</strong></td>
                        <td>{shipment.vessel_name || 'N/A'}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              )}
              {activeTab === 'score-breakdown' && (
                <div className="tab-panel">
                  {scoringLoading ? (
                    <div style={{ padding: '2rem', textAlign: 'center', color: '#666' }}>
                      <p>Loading risk assessment...</p>
                    </div>
                  ) : error ? (
                    <div style={{ padding: '2rem', color: '#d32f2f', backgroundColor: '#ffebee', borderRadius: '4px' }}>
                      <p><strong>Error:</strong> {error}</p>
                    </div>
                  ) : scoringData ? (
                    <ScoreBreakdown
                      totalScore={scoringData.total_score}
                      confidence={scoringData.confidence}
                      h1={{
                        horizon: scoringData.h1.horizon,
                        label: scoringData.h1.label,
                        score: scoringData.h1.score,
                        maxScore: scoringData.h1.max_score,
                        weight: scoringData.h1.weight,
                        summary: scoringData.h1.summary,
                        factors: scoringData.h1.factors,
                      }}
                      h2={{
                        horizon: scoringData.h2.horizon,
                        label: scoringData.h2.label,
                        score: scoringData.h2.score,
                        maxScore: scoringData.h2.max_score,
                        weight: scoringData.h2.weight,
                        summary: scoringData.h2.summary,
                        factors: scoringData.h2.factors,
                      }}
                      h3={{
                        horizon: scoringData.h3.horizon,
                        label: scoringData.h3.label,
                        score: scoringData.h3.score,
                        maxScore: scoringData.h3.max_score,
                        weight: scoringData.h3.weight,
                        summary: scoringData.h3.summary,
                        factors: scoringData.h3.factors,
                      }}
                    />
                  ) : null}
                </div>
              )}
              {activeTab === 'workflow' && (
                <div className="tab-panel">
                  <WorkflowSignalMap
                    currentStep={cordLoading ? 5 : 6}
                    totalScore={scoringData?.total_score || 0}
                    h1Score={scoringData?.h1.score || 0}
                    h2Score={scoringData?.h2.score || 0}
                    h3Score={scoringData?.h3.score || 0}
                    entityChainCount={entityChains.reduce((sum, chain) => sum + (chain.entities?.length || 0), 0)}
                    riskFlagCount={riskFlags.length}
                    workflowComplete={!cordLoading && !scoringLoading}
                  />

                  {/* Score Trend Chart */}
                  <div style={{ marginTop: '32px' }}>
                    <h3 style={{ marginBottom: '16px', color: '#1f2937', fontSize: '18px', fontWeight: '600' }}>
                      Score Accumulation Through Workflow
                    </h3>
                    <ResponsiveContainer width="100%" height={300}>
                      <LineChart
                        data={[
                          { step: 1, score: 0, h1: 0, h2: 0, h3: 0, label: 'Manifest' },
                          { step: 2, score: scoringData?.h1.score || 0, h1: scoringData?.h1.score || 0, h2: 0, h3: 0, label: 'H1' },
                          { step: 3, score: (scoringData?.h1.score || 0) + (scoringData?.h2.score || 0), h1: scoringData?.h1.score || 0, h2: scoringData?.h2.score || 0, h3: 0, label: 'H2' },
                          { step: 4, score: (scoringData?.h1.score || 0) + (scoringData?.h2.score || 0) + (scoringData?.h3.score || 0), h1: scoringData?.h1.score || 0, h2: scoringData?.h2.score || 0, h3: scoringData?.h3.score || 0, label: 'H3' },
                          { step: 5, score: scoringData?.total_score || 0, h1: scoringData?.h1.score || 0, h2: scoringData?.h2.score || 0, h3: scoringData?.h3.score || 0, label: 'Senzing' },
                          { step: 6, score: scoringData?.total_score || 0, h1: scoringData?.h1.score || 0, h2: scoringData?.h2.score || 0, h3: scoringData?.h3.score || 0, label: 'Decision' },
                        ]}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis
                          dataKey="label"
                          stroke="#6b7280"
                          style={{ fontSize: '12px' }}
                        />
                        <YAxis
                          stroke="#6b7280"
                          domain={[0, 100]}
                          style={{ fontSize: '12px' }}
                          label={{ value: 'Risk Score', angle: -90, position: 'insideLeft' }}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#ffffff',
                            border: '1px solid #e5e7eb',
                            borderRadius: '6px',
                            padding: '8px'
                          }}
                          formatter={(value: number) => Math.round(value)}
                        />
                        <Legend />
                        <Line
                          type="monotone"
                          dataKey="score"
                          stroke="#ff7300"
                          strokeWidth={3}
                          name="Total Score"
                          dot={{ fill: '#ff7300', r: 4 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}
              {activeTab === 'entity-chain' && (
                <div className="tab-panel">
                  <EntityChainViewer
                    entityChains={entityChains}
                    riskFlags={riskFlags}
                    confidence={cordData?.scoring.confidence || 0}
                    loading={cordLoading}
                    errorReason={cordData?.error_reason}
                    debugInfo={cordData?.debug}
                  />
                </div>
              )}
              {activeTab === 'referral' && (
                <div className="tab-panel">
                  <ReferralPackageViewer
                    shipmentId={shipmentId || ''}
                    shipment={shipment}
                    score={currentScore}
                    h1Score={scoringData?.h1.score || 0}
                    h2Score={scoringData?.h2.score || 0}
                    h3Score={scoringData?.h3.score || 0}
                  />
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Investigation Notes */}
        <div className="investigation-notes">
          <h3>Investigation Notes</h3>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Document your investigation findings and analysis..."
            rows={6}
          />
          <div className="notes-actions">
            <button className="btn-save" onClick={() => console.log('Save notes:', notes)}>
              Save Notes
            </button>
            {action && (
              <button className="btn-submit" onClick={() => console.log('Submit action:', action, notes)}>
                Submit & Close Case
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
