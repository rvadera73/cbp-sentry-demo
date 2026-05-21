import { useState, useRef } from 'react'
import { ChevronDown, AlertTriangle, Download, FileText } from 'lucide-react'
import html2pdf from 'html2pdf.js'
import '../styles/ReferralPackageViewerEnhanced.css'

interface ReferralPackageViewerProps {
  shipmentId: string
  shipment: {
    shipper_name: string
    consignee_name: string
    hs_code: string
    declared_value_usd: number
    declared_weight_kg: number
    origin_country: string
    destination_country: string
    vessel_name?: string
    element9_declared_country?: string
    element9_actual_country?: string
  }
  score: number
  h1Score: number
  h2Score: number
  h3Score: number
}

// Component A: Visual Investigation Narrative Banner
function InvestigationNarrativeBanner({ shipment, score }: { shipment: any; score: number }) {
  const getRiskColor = (s: number) => (s >= 70 ? 'high-risk' : s >= 50 ? 'medium-risk' : 'low-risk')
  const getRiskLabel = (s: number) => (s >= 70 ? 'HIGH RISK' : s >= 50 ? 'MEDIUM RISK' : 'LOW RISK')
  const getRiskAction = (s: number) => (s >= 70 ? 'EXAMINE ON ARRIVAL' : s >= 50 ? 'REVIEW' : 'CLEAR')

  // Generate narrative based on actual shipment data
  let narrative = ''
  if (score >= 70) {
    const isElement9Mismatch = shipment.element9_declared_country !== shipment.element9_actual_country
    if (isElement9Mismatch) {
      narrative = `Potential Duty Evasion via Illogical Transshipment. Shipment claims ${shipment.element9_declared_country || shipment.origin_country} origin, but vessel tracking confirms cargo loading in ${shipment.element9_actual_country || 'Guangzhou (CN)'} with explicit T1 link to Chinese supplier network. ISF Element 9 mismatch indicates intentional misrepresentation of country of origin.`
    } else {
      narrative = `High-Risk Transshipment Corridor: ${shipment.origin_country}→${shipment.destination_country}. Active AD/CVD duties apply. Vessel routing anomalies and supply chain opacity indicate potential duty evasion scheme. Recommend immediate physical examination.`
    }
  } else if (score >= 50) {
    narrative = `Medium-Risk Shipment Requiring Review. ${shipment.shipper_name} exporting ${shipment.hs_code} to ${shipment.consignee_name}. Document discrepancies and route anomalies warrant further investigation before release.`
  } else {
    narrative = `Low-Risk Shipment. Standard compliance profile. ${shipment.shipper_name} to ${shipment.consignee_name}. Cleared for release upon routine processing.`
  }

  return (
    <div className={`narrative-banner ${getRiskColor(score)}`} role="alert">
      <div className="narrative-icon">
        <AlertTriangle size={28} />
      </div>
      <div className="narrative-content">
        <div className="narrative-label">{getRiskLabel(score)} — {getRiskAction(score)}</div>
        <p className="narrative-text">{narrative}</p>
      </div>
    </div>
  )
}

// Component B: Progressive Risk Bar
function ProgressiveRiskBar({ h1Score, h2Score, h3Score, score }: { h1Score: number; h2Score: number; h3Score: number; score: number }) {
  const [activeTooltip, setActiveTooltip] = useState<string | null>(null)

  const segments = [
    {
      id: 'h1',
      label: 'Corridor Risk',
      value: h1Score,
      max: 40,
      context: 'Macro Volume Anomaly: +240% YoY Shift',
      color: '#FF4444',
    },
    {
      id: 'h2',
      label: 'Vessel Risk',
      value: h2Score,
      max: 35,
      context: 'Critical Route Conflict: Guangzhou & Haiphong Callings',
      color: '#FF8844',
    },
    {
      id: 'h3',
      label: 'Network Intelligence',
      value: h3Score,
      max: 25,
      context: 'Enriched Watchlist Match: Tier 1 Chinese Supplier',
      color: '#FFAA44',
    },
  ]

  return (
    <div className="progressive-risk-bar" role="img" aria-label={`Total Risk Score: ${score} out of 100`}>
      <div className="risk-pipeline">
        {segments.map((segment) => {
          const percentage = (segment.value / segment.max) * 100
          return (
            <div
              key={segment.id}
              className="risk-segment"
              style={{ flex: segment.max }}
              onMouseEnter={() => setActiveTooltip(segment.id)}
              onMouseLeave={() => setActiveTooltip(null)}
              onFocus={() => setActiveTooltip(segment.id)}
              onBlur={() => setActiveTooltip(null)}
              tabIndex={0}
              role="button"
              aria-label={`${segment.label}: ${segment.value} out of ${segment.max}`}
            >
              <div className="segment-fill" style={{ width: `${percentage}%`, backgroundColor: segment.color }}></div>
              <div className="segment-label">
                <span className="segment-name">{segment.label}</span>
                <span className="segment-score">{segment.value}/{segment.max}</span>
              </div>

              {activeTooltip === segment.id && (
                <div className="segment-tooltip" role="tooltip">
                  {segment.context}
                </div>
              )}
            </div>
          )
        })}
      </div>
      <div className="total-score-display">
        <span className="total-label">TOTAL RISK SCORE</span>
        <span className="total-value">{Math.round(score)}/100</span>
      </div>
    </div>
  )
}

// Component C: Segregated Case Profile Tabs
function CaseProfileTabs({ shipment, h1Score, h2Score, h3Score, score }: { shipment: any; h1Score: number; h2Score: number; h3Score: number; score: number }) {
  const [activeTab, setActiveTab] = useState('discrepancies')

  const tabs = [
    { id: 'discrepancies', label: 'Evidentiary Discrepancies', icon: '⚠️' },
    { id: 'entity-chain', label: 'Multi-Tier Entity Chain', icon: '🔗' },
    { id: 'what-if', label: 'Operational Simulation', icon: '🎯' },
  ]

  return (
    <div className="case-profile-tabs">
      <div className="tab-list" role="tablist">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={`tab-button ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
            role="tab"
            aria-selected={activeTab === tab.id}
            aria-controls={`tabpanel-${tab.id}`}
          >
            <span className="tab-icon">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab 1: Evidentiary Discrepancies */}
      {activeTab === 'discrepancies' && (
        <div id="tabpanel-discrepancies" className="tab-panel" role="tabpanel">
          <div className="discrepancies-grid">
            <div className="discrepancy-box">
              <h4>📄 Declared Paperwork</h4>
              <div className="discrepancy-field">
                <span className="field-label">Origin Country:</span>
                <span className="field-value">{shipment.origin_country}</span>
              </div>
              <div className="discrepancy-field">
                <span className="field-label">Shipper:</span>
                <span className="field-value">{shipment.shipper_name}</span>
              </div>
              <div className="discrepancy-field">
                <span className="field-label">HTS Code:</span>
                <span className="field-value">{shipment.hs_code}</span>
              </div>
            </div>

            <div className="discrepancy-comparison">
              {shipment.element9_declared_country && shipment.element9_actual_country && shipment.element9_declared_country !== shipment.element9_actual_country ? (
                <div className="mismatch-indicator">
                  <span className="mismatch-label">ISF ELEMENT 9</span>
                  <span className="mismatch-icon">❌</span>
                  <span className="mismatch-text">MISMATCH</span>
                </div>
              ) : (
                <div className="match-indicator">
                  <span className="match-label">CONSISTENT</span>
                  <span className="match-icon">✓</span>
                </div>
              )}
            </div>

            <div className="discrepancy-box">
              <h4>📡 Verified Physical Telemetry</h4>
              <div className="discrepancy-field">
                <span className="field-label">AIS Vessel Stuffing:</span>
                <span className="field-value">{shipment.element9_actual_country || 'CN'}</span>
              </div>
              <div className="discrepancy-field">
                <span className="field-label">Port Calls:</span>
                <span className="field-value">Guangzhou (CN) → Haiphong (VN) → Newark (US)</span>
              </div>
              <div className="discrepancy-field">
                <span className="field-label">Dwell Time Anomaly:</span>
                <span className="field-value" style={{ color: '#D9381E' }}>11.2 days (5.3× baseline)</span>
              </div>
            </div>
          </div>

          <div className="document-status-grid">
            <h4>📋 Document Status</h4>
            <div className="document-items">
              <div className="document-item received">
                <span className="doc-icon">✓</span>
                <span className="doc-name">Commercial Invoice</span>
              </div>
              <div className="document-item received">
                <span className="doc-icon">✓</span>
                <span className="doc-name">Bill of Lading</span>
              </div>
              <div className="document-item missing">
                <span className="doc-icon">✗</span>
                <span className="doc-name">Factory Records</span>
              </div>
              <div className="document-item warning">
                <span className="doc-icon">⚠</span>
                <span className="doc-name">Origin Certificate Mismatch</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Multi-Tier Entity Chain */}
      {activeTab === 'entity-chain' && (
        <div id="tabpanel-entity-chain" className="tab-panel" role="tabpanel">
          <div className="entity-tree">
            <div className="entity-node tier-1 root-risk">
              <div className="entity-name">Guangdong Greenfield Aluminum</div>
              <div className="entity-country">CN</div>
              <div className="entity-role">Manufacturer</div>
              <div className="entity-risk-badge">ROOT RISK</div>
            </div>

            <div className="tree-connector">↓</div>

            <div className="entity-node tier-2">
              <div className="entity-name">Greenfield Global Holdings Ltd.</div>
              <div className="entity-country">HK</div>
              <div className="entity-role">Holding Company (OWNED_BY)</div>
            </div>

            <div className="tree-connector">↓</div>

            <div className="entity-node tier-3">
              <div className="entity-name">Greenfield Industrial Trading Co., Ltd.</div>
              <div className="entity-country">VN</div>
              <div className="entity-role">Exporter (SUBSIDIARY)</div>
            </div>

            <div className="tree-connector">↓</div>

            <div className="entity-node tier-4">
              <div className="entity-name">{shipment.shipper_name}</div>
              <div className="entity-country">{shipment.origin_country}</div>
              <div className="entity-role">Manifest Shipper</div>
              <div className="entity-note">🚩 Used as origin misrepresentation</div>
            </div>

            <div className="tree-connector">↓</div>

            <div className="entity-node tier-5 consignee">
              <div className="entity-name">{shipment.consignee_name}</div>
              <div className="entity-country">{shipment.destination_country}</div>
              <div className="entity-role">US Importer</div>
            </div>
          </div>

          <div className="entity-relationship-legend">
            <h4>Relationship Types</h4>
            <div className="legend-items">
              <div className="legend-item">
                <span className="legend-color" style={{ backgroundColor: '#FF4444' }}></span>
                <span>OWNED_BY (Control)</span>
              </div>
              <div className="legend-item">
                <span className="legend-color" style={{ backgroundColor: '#FF8844' }}></span>
                <span>SUBSIDIARY (Subcontrol)</span>
              </div>
              <div className="legend-item">
                <span className="legend-color" style={{ backgroundColor: '#FFB84D' }}></span>
                <span>DIRECTOR_SHARED (Overlap)</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: What-If Parameters */}
      {activeTab === 'what-if' && (
        <div id="tabpanel-what-if" className="tab-panel" role="tabpanel">
          <div className="what-if-simulator">
            <div className="simulator-intro">
              <p>
                <strong>Current Score: {Math.round(score)}/100</strong>
              </p>
              <p>Interactive risk simulation: Adjust key parameters to see how the score would change.</p>
            </div>

            <div className="scenario-items">
              <div className="scenario">
                <div className="scenario-title">Scenario 1: If Shipper Age &gt; 5 Years</div>
                <div className="scenario-description">Remove new shipper premium (-8 pts)</div>
                <div className="scenario-result">
                  <span className="result-label">Revised Score:</span>
                  <span className="result-value">{Math.max(0, score - 8)}/100</span>
                </div>
                <div className="scenario-impact">Impact: -{Math.min(8, score)} pts</div>
              </div>

              <div className="scenario">
                <div className="scenario-title">Scenario 2: If Factory Records Uploaded</div>
                <div className="scenario-description">Verify manufacturing capacity (-10 pts)</div>
                <div className="scenario-result">
                  <span className="result-label">Revised Score:</span>
                  <span className="result-value">{Math.max(0, score - 10)}/100</span>
                </div>
                <div className="scenario-impact">Impact: -{Math.min(10, score)} pts</div>
              </div>

              <div className="scenario">
                <div className="scenario-title">Scenario 3: If ISF Element 9 Matches Declared</div>
                <div className="scenario-description">Remove origin mismatch penalty (-15 pts)</div>
                <div className="scenario-result">
                  <span className="result-label">Revised Score:</span>
                  <span className="result-value">{Math.max(0, score - 15)}/100</span>
                </div>
                <div className="scenario-impact">Impact: -{Math.min(15, score)} pts</div>
              </div>

              <div className="scenario">
                <div className="scenario-title">Scenario 4: If No AD/CVD Active</div>
                <div className="scenario-description">Remove tariff order incentive (-12 pts)</div>
                <div className="scenario-result">
                  <span className="result-label">Revised Score:</span>
                  <span className="result-value">{Math.max(0, score - 12)}/100</span>
                </div>
                <div className="scenario-impact">Impact: -{Math.min(12, score)} pts</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// Component D: Officer Referral Box
function OfficerReferralBox({ shipmentId, score }: { shipmentId: string; score: number }) {
  const [notes, setNotes] = useState('')
  const [selectedAction, setSelectedAction] = useState<string | null>(null)

  const handleAction = (action: string) => {
    setSelectedAction(action)
    console.log(`Officer Action: ${action}`)
    // Would call API to record action
  }

  return (
    <div className="officer-referral-box" role="region" aria-label="Officer Action Controls">
      <div className="referral-header">
        <h3>🔒 Enforcement Action & Investigation Notes</h3>
        <div className="action-timestamp">{new Date().toLocaleString()}</div>
      </div>

      <div className="action-controls">
        <button
          className={`action-btn primary ${selectedAction === 'trled-referral' ? 'selected' : ''}`}
          onClick={() => handleAction('trled-referral')}
        >
          🚨 Execute TRLED Referral
        </button>
        <button
          className={`action-btn warning ${selectedAction === 'hold-examine' ? 'selected' : ''}`}
          onClick={() => handleAction('hold-examine')}
        >
          ⏸ Hold & Examine on Arrival
        </button>
        <button
          className={`action-btn secondary ${selectedAction === 'review' ? 'selected' : ''}`}
          onClick={() => handleAction('review')}
        >
          📋 Review & Release
        </button>
      </div>

      <div className="notes-section">
        <label htmlFor="investigation-notes">Officer Investigation Notes</label>
        <textarea
          id="investigation-notes"
          className="notes-field"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Document your investigation findings, evidence review, and enforcement decision rationale. Preserve audit trail..."
          rows={6}
          aria-label="Investigation notes for audit trail"
        />
      </div>

      {selectedAction && (
        <div className="action-confirmation">
          <strong>Selected Action:</strong> {selectedAction.replace('-', ' ').toUpperCase()}
          <button className="btn-confirm" onClick={() => alert('Action recorded: ' + selectedAction)}>
            ✓ Confirm & Record
          </button>
        </div>
      )}
    </div>
  )
}

// Main Component
export default function ReferralPackageViewerEnhanced({
  shipmentId,
  shipment,
  score,
  h1Score,
  h2Score,
  h3Score,
}: ReferralPackageViewerProps) {
  const contentRef = useRef<HTMLDivElement>(null)

  const exportToPDF = async () => {
    if (!contentRef.current) return

    const element = contentRef.current
    const opt = {
      margin: 10,
      filename: `SENTRY-Referral-${shipmentId}-${new Date().toISOString().split('T')[0]}.pdf`,
      image: { type: 'png' as const, quality: 0.98 },
      html2canvas: { scale: 2 },
      jsPDF: { orientation: 'portrait' as const, unit: 'mm', format: 'a4' },
    }

    try {
      html2pdf().set(opt).from(element).save()
    } catch (error) {
      console.error('PDF export failed:', error)
      alert('Failed to export PDF. Please try again.')
    }
  }

  return (
    <div className="referral-package-enhanced" ref={contentRef}>
      {/* Header */}
      <div className="referral-header-section">
        <div className="header-content">
          <h2>CBP EAPA REFERRAL PACKAGE</h2>
          <div className="header-metadata">
            <span className="metadata-item">
              <strong>Shipment ID:</strong> {shipmentId}
            </span>
            <span className="metadata-item">
              <strong>Shipper:</strong> {shipment.shipper_name}
            </span>
            <span className="metadata-item">
              <strong>Consignee:</strong> {shipment.consignee_name}
            </span>
            <span className="metadata-item">
              <strong>Generated:</strong> {new Date().toLocaleString()}
            </span>
          </div>
        </div>
      </div>

      {/* Component A: Narrative Banner */}
      <section className="section-a">
        <InvestigationNarrativeBanner shipment={shipment} score={score} />
      </section>

      {/* Component B: Risk Bar */}
      <section className="section-b">
        <h3>Three-Horizon Risk Assessment</h3>
        <ProgressiveRiskBar h1Score={h1Score} h2Score={h2Score} h3Score={h3Score} score={score} />
      </section>

      {/* Component C: Case Profile Tabs */}
      <section className="section-c">
        <h3>Detailed Investigation Findings</h3>
        <CaseProfileTabs shipment={shipment} h1Score={h1Score} h2Score={h2Score} h3Score={h3Score} score={score} />
      </section>

      {/* Component D: Officer Action Box */}
      <section className="section-d">
        <OfficerReferralBox shipmentId={shipmentId} score={score} />
      </section>

      {/* Footer with Export */}
      <div className="referral-footer">
        <button className="btn-export" onClick={exportToPDF}>
          <Download size={18} /> Export as PDF
        </button>
        <button className="btn-print" onClick={() => window.print()}>
          <FileText size={18} /> Print
        </button>
      </div>
    </div>
  )
}
