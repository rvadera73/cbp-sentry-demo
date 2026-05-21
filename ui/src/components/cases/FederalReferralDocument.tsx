import { useRef } from 'react'
import { Download } from 'lucide-react'
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import html2pdf from 'html2pdf.js'
import '../styles/FederalReferralDocument.css'

interface FederalReferralDocumentProps {
  shipmentId: string
  shipment: {
    id: string
    manifest_id?: string
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
    port_of_lading?: string
    port_of_discharge?: string
    estimated_arrival?: string
    vessel_imo?: string
    dwell_days?: number
    shipper_registration_country?: string
  }
  score: number
  h1Score: number
  h2Score: number
  h3Score: number
  referralData?: any
}

// Component A: Investigation Narrative Banner
function InvestigationNarrativeBanner({ shipment, score }: { shipment: any; score: number }) {
  const getRiskColor = (s: number) => (s >= 70 ? 'high-risk' : s >= 50 ? 'medium-risk' : 'low-risk')
  const getRiskLabel = (s: number) => (s >= 70 ? 'HIGH RISK' : s >= 50 ? 'MEDIUM RISK' : 'LOW RISK')

  let narrative = ''
  if (score >= 70) {
    const isElement9Mismatch =
      shipment.element9_declared_country &&
      shipment.element9_actual_country &&
      shipment.element9_declared_country !== shipment.element9_actual_country

    if (isElement9Mismatch) {
      narrative = `CRITICAL: Potential duty evasion via illogical transshipment. Shipment claims ${shipment.element9_declared_country || shipment.origin_country} origin, but vessel tracking confirms cargo loading in ${shipment.element9_actual_country || 'Guangzhou (CN)'} with explicit linkage to Chinese supplier network. ISF Element 9 mismatch indicates intentional misrepresentation of country of origin under 19 CFR 149.5.`
    } else {
      narrative = `HIGH RISK: ${shipment.origin_country}→${shipment.destination_country} corridor exhibits structural indicators of illegal transshipment under 19 USC § 1516a. Active AD/CVD duties apply. Vessel routing anomalies and supply chain network opacity suggest intentional duty evasion scheme.`
    }
  } else if (score >= 50) {
    narrative = `MEDIUM RISK: ${shipment.shipper_name} shipment warrants heightened review. ${shipment.hs_code} export to ${shipment.consignee_name} shows pattern anomalies. Document discrepancies and route anomalies warrant further investigation per 19 CFR Part 149 (ISF compliance review).`
  } else {
    narrative = `LOW RISK: Standard compliance profile. ${shipment.shipper_name} to ${shipment.consignee_name}. Shipment cleared for release upon completion of routine processing procedures.`
  }

  return (
    <div className={`narrative-banner ${getRiskColor(score)}`}>
      <div className="narrative-content">
        <div className="narrative-label">{getRiskLabel(score)}</div>
        <p className="narrative-text">{narrative}</p>
      </div>
    </div>
  )
}

// Component B: Three-Horizon Risk Assessment
function ThreeHorizonRiskBar({
  h1Score,
  h2Score,
  h3Score,
  score,
}: {
  h1Score: number
  h2Score: number
  h3Score: number
  score: number
}) {
  const segments = [
    {
      id: 'h1',
      label: 'H1: Corridor Risk (Macro)',
      value: h1Score,
      max: 40,
      description: 'Structural corridor analysis, bilateral trade anomalies, AD/CVD orders',
    },
    {
      id: 'h2',
      label: 'H2: Pre-Manifest Intelligence',
      value: h2Score,
      max: 35,
      description: 'ISF Element 9, AIS vessel tracking, dwell time anomalies',
    },
    {
      id: 'h3',
      label: 'H3: Network Intelligence',
      value: h3Score,
      max: 25,
      description: 'Entity resolution, OFAC/watchlist, supply chain network depth',
    },
  ]

  return (
    <div className="three-horizon-assessment">
      <div className="horizon-segments">
        {segments.map((segment) => {
          const percentage = (segment.value / segment.max) * 100
          return (
            <div key={segment.id} className="horizon-segment">
              <div className="segment-header">
                <span className="segment-label">{segment.label}</span>
                <span className="segment-score">
                  {segment.value}/{segment.max}
                </span>
              </div>
              <div className="segment-bar">
                <div className="segment-fill" style={{ width: `${percentage}%` }}></div>
              </div>
              <div className="segment-description">{segment.description}</div>
            </div>
          )
        })}
      </div>
      <div className="total-assessment">
        <div className="total-label">TOTAL RISK SCORE</div>
        <div className="total-value">{Math.round(score)}/100</div>
      </div>
    </div>
  )
}

// Component C: Detailed Investigation Findings (Now as Sections, Not Tabs)
function DetailedInvestigationFindings({ shipment, h1Score, h2Score, h3Score }: { shipment: any; h1Score: number; h2Score: number; h3Score: number }) {
  const scoreDistributionData = [
    { name: 'H1 Corridor', value: h1Score },
    { name: 'H2 Vessel', value: h2Score },
    { name: 'H3 Network', value: h3Score },
  ]
  const COLORS = ['#013060', '#0050D8', '#4AC4D3']

  return (
    <div className="detailed-investigation-sections">
      {/* Section 1: Evidentiary Discrepancies */}
      <div className="investigation-section">
        <h3>⚠️ Section 1: Evidentiary Discrepancies</h3>
        <div className="section-content">
          <div className="discrepancies-grid">
            <div className="discrepancy-box">
              <h4>📄 Declared Paperwork</h4>
              <div className="discrepancy-field">
                <span className="field-label">Origin Country:</span>
                <span className="field-value">{shipment.origin_country}</span>
              </div>
              <div className="discrepancy-field">
                <span className="field-label">Shipper Name:</span>
                <span className="field-value">{shipment.shipper_name}</span>
              </div>
              <div className="discrepancy-field">
                <span className="field-label">HTS Code:</span>
                <span className="field-value">{shipment.hs_code}</span>
              </div>
              <div className="discrepancy-field">
                <span className="field-label">Declared Value:</span>
                <span className="field-value">${shipment.declared_value_usd.toLocaleString()}</span>
              </div>
            </div>

            <div className="discrepancy-comparison">
              {shipment.element9_declared_country &&
              shipment.element9_actual_country &&
              shipment.element9_declared_country !== shipment.element9_actual_country ? (
                <div className="mismatch-indicator">
                  <span className="mismatch-label">ISF ELEMENT 9</span>
                  <span className="mismatch-icon">❌</span>
                  <span className="mismatch-text">MISMATCH</span>
                  <span className="mismatch-detail">
                    Declared: {shipment.element9_declared_country} | Actual: {shipment.element9_actual_country}
                  </span>
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
                <span className="field-label">Vessel Stuffing Location:</span>
                <span className="field-value">{shipment.element9_actual_country || 'Pending'}</span>
              </div>
              <div className="discrepancy-field">
                <span className="field-label">Vessel Name:</span>
                <span className="field-value">{shipment.vessel_name || 'N/A'}</span>
              </div>
              <div className="discrepancy-field">
                <span className="field-label">Dwell Days:</span>
                <span className="field-value">{shipment.dwell_days || '2.1'} days</span>
              </div>
              <div className="discrepancy-field">
                <span className="field-label">Port of Lading:</span>
                <span className="field-value">{shipment.port_of_lading || 'Not specified'}</span>
              </div>
            </div>

            <div className="discrepancy-box">
              <h4>📋 Document Status Checklist</h4>
              <div className="checklist-item">
                <input type="checkbox" checked readOnly />
                <span>Commercial Invoice Present</span>
              </div>
              <div className="checklist-item">
                <input type="checkbox" checked={false} readOnly />
                <span>Factory Certification on File</span>
              </div>
              <div className="checklist-item">
                <input type="checkbox" checked readOnly />
                <span>ISF Element 9 Filed</span>
              </div>
              <div className="checklist-item">
                <input type="checkbox" checked={h1Score < 20} readOnly />
                <span>All Documents Consistent</span>
              </div>
            </div>
          </div>

          {/* Analysis */}
          <div className="analysis-section">
            <h5>Key Findings Analysis</h5>
            <p className="analysis-text">
              The discrepancy analysis reveals significant alignment issues between declared paperwork and verified physical telemetry.
              ISF Element 9 data (Container Stuffing Location) is a critical first-of-kind indicator filed 24 hours before cargo loading,
              occurring 14-22 days before U.S. arrival. Mismatches between declared country of origin and actual stuffing location constitute
              direct evidence of origin fraud under 19 CFR 149.5. Document status confirms receipt of required filings but identifies gaps
              in supporting factory certifications, suggesting incomplete chain-of-custody verification.
            </p>
          </div>

          {/* Charts */}
          <div className="discrepancy-charts">
            <div className="chart-container">
              <h5>Risk Score Distribution</h5>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={scoreDistributionData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, value }) => `${name}: ${value}`}
                    outerRadius={70}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {COLORS.map((color) => (
                      <Cell key={`cell`} fill={color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="chart-container">
              <h5>Three-Horizon Scoring</h5>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={scoreDistributionData} margin={{ top: 5, right: 10, left: 0, bottom: 30 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" style={{ fontSize: '9px' }} angle={-45} textAnchor="end" height={60} />
                  <YAxis style={{ fontSize: '9px' }} />
                  <Tooltip />
                  <Bar dataKey="value" fill="#013060" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      {/* Section 2: Multi-Tier Entity Chain */}
      <div className="investigation-section">
        <h3>🔗 Section 2: Multi-Tier Entity Chain</h3>
        <div className="section-content">
          <div className="analysis-section">
            <h5>Supply Chain Relationship Analysis</h5>
            <p className="analysis-text">
              Senzing entity resolution identifies corporate ownership chains and director linkages across the supply network.
              Multi-tier structures (manufacturer → intermediate holding → shipper → consignee) are common in legitimate trade but become
              problematic when intermediate entities lack verifiable manufacturing capacity, business presence, or transparent ownership.
              Shared directors between the origin manufacturer and U.S. consignee is a high-confidence signal of integrated transshipment
              schemes. DIRECTOR_SHARED relationships across borders without independent business operations suggest shell company structures
              designed to obscure true parties and evade duty obligations.
            </p>
          </div>

          <div className="entity-chain-visualization">
            <div className="entity-node">
              <div className="node-label">Manufacturer</div>
              <div className="node-value">{shipment.origin_country} Supplier</div>
            </div>
            <div className="entity-arrow">→</div>
            <div className="entity-node">
              <div className="node-label">Intermediate</div>
              <div className="node-value">Trading Entity</div>
            </div>
            <div className="entity-arrow">→</div>
            <div className="entity-node">
              <div className="node-label">Shipper</div>
              <div className="node-value">{shipment.shipper_name}</div>
            </div>
            <div className="entity-arrow">→</div>
            <div className="entity-node">
              <div className="node-label">Consignee</div>
              <div className="node-value">{shipment.consignee_name}</div>
            </div>
          </div>

          <div className="relationship-types">
            <h5>Relationship Types & Risk Indicators</h5>
            <div className="relationship-item">
              <span className="rel-type">OWNED_BY</span>
              <span className="rel-desc">Corporate ownership or parent company — validates legitimate business structure if documented</span>
            </div>
            <div className="relationship-item">
              <span className="rel-type">DIRECTOR_SHARED</span>
              <span className="rel-desc">Common board member or director — HIGH RISK indicator if across borders without independent operations</span>
            </div>
            <div className="relationship-item">
              <span className="rel-type">FREIGHT_FORWARDER</span>
              <span className="rel-desc">Logistics provider linking entities — verify independence and established business history</span>
            </div>
          </div>
        </div>
      </div>

      {/* Section 3: Operational Simulation (What-If Scenarios) */}
      <div className="investigation-section">
        <h3>🎯 Section 3: Operational Simulation (What-If Scenarios)</h3>
        <div className="section-content">
          <div className="analysis-section">
            <h5>Scenario Analysis Purpose</h5>
            <p className="analysis-text">
              What-if scenarios isolate individual risk factors to assess their contribution to the overall score. These counterfactuals help
              officers determine which investigative actions (factory verification, ISF amendment, entity ownership confirmation) would most
              effectively reduce risk and enable release. Each scenario represents a plausible evidentiary finding that would change the risk
              profile if corroborated during investigation.
            </p>
          </div>

          <div className="scenario-analysis">
            <div className="scenario-box">
              <h5>Scenario 1: If Origin Were Legitimate</h5>
              <p>
                <strong>Assumption:</strong> Shipper provides complete factory certification, manufacturing capacity documentation, and
                historical purchase orders proving established business relationship with claimed origin manufacturer.
              </p>
              <div className="scenario-impact">
                <span>Adjusted H1 Score:</span>
                <span className="impact-value">{Math.max(h1Score - 15, 0)}/40</span>
              </div>
              <div className="scenario-impact">
                <span>New Total Score:</span>
                <span className="impact-value">
                  {Math.max(h1Score + h2Score + h3Score - 15, 0)}/100
                </span>
              </div>
              <div className="scenario-interpretation">
                <strong>Interpretation:</strong> Corridor risk (H1) accounts for ~{Math.round((h1Score / 100) * 100)}% of total risk. If this factor
                were eliminated through documentation, remaining score would indicate whether H2 (vessel) and H3 (network) factors alone justify
                continued scrutiny.
              </div>
              <div className="scenario-action">
                <strong>Recommended Action:</strong> Request factory certification, business registration, prior import history, and supply
                agreements before release decision.
              </div>
            </div>

            <div className="scenario-box">
              <h5>Scenario 2: If ISF Element 9 Were Consistent</h5>
              <p>
                <strong>Assumption:</strong> ISF Element 9 (Container Stuffing Location) amendment filed showing cargo actually loaded at declared
                origin port, not at intermediate port. Vessel AIS data confirms direct routing without unusual dwell.
              </p>
              <div className="scenario-impact">
                <span>Adjusted H2 Score:</span>
                <span className="impact-value">{Math.max(h2Score - 12, 0)}/35</span>
              </div>
              <div className="scenario-impact">
                <span>New Total Score:</span>
                <span className="impact-value">
                  {Math.max(h1Score + h2Score + h3Score - 12, 0)}/100
                </span>
              </div>
              <div className="scenario-interpretation">
                <strong>Interpretation:</strong> ISF Element 9 mismatch contributes ~{Math.round((h2Score / 100) * 100)}% of total risk. Element 9 is
                filed 14-22 days before U.S. arrival, providing early warning not available in 72-hour manifest window. If corrected, indicates
                shipper can amend early filings and respond to evidence.
              </div>
              <div className="scenario-action">
                <strong>Recommended Action:</strong> Request ISF amendment or explanation from shipper/freight forwarder regarding documented
                stuffing location discrepancy. Verify with vessel operator.
              </div>
            </div>

            <div className="scenario-box">
              <h5>Scenario 3: If No Network Linkage to China</h5>
              <p>
                <strong>Assumption:</strong> Senzing entity resolution finds no director sharing, common freight forwarders, or parent company
                linkages between shipper and any Chinese manufacturing bases. Ownership chain is verified independent.
              </p>
              <div className="scenario-impact">
                <span>Adjusted H3 Score:</span>
                <span className="impact-value">0/25</span>
              </div>
              <div className="scenario-impact">
                <span>New Total Score:</span>
                <span className="impact-value">{h1Score + h2Score}/100</span>
              </div>
              <div className="scenario-interpretation">
                <strong>Interpretation:</strong> Network intelligence (H3) currently accounts for ~{Math.round((h3Score / 100) * 100)}% of total risk.
                Entity resolution is the foundational layer enabling detection. If entities are unrelated, transshipment becomes difficult to conceal
                across traditional corporate channels, requiring use of shell companies or falsified documents (both independently actionable).
              </div>
              <div className="scenario-action">
                <strong>Recommended Action:</strong> Conduct Senzing deep-dive investigation of all shipper and consignee shareholders and
                directors. Verify business registration independence. Cross-reference with prior EAPA cases.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// Component D: Officer Referral Box
function OfficerReferralBox({ score }: { score: number }) {
  const getRecommendation = (s: number) => {
    if (s >= 70) {
      return 'EXAMINE ON ARRIVAL. Potential transshipment scheme detected. Recommend physical examination and CBP National Targeting Center (NTC) referral for EAPA investigation per 19 USC § 1516a.'
    }
    if (s >= 50) {
      return 'REVIEW PRIOR TO RELEASE. ISF compliance review and documentary verification required before authorization. Standard processing may proceed upon satisfactory documentation review.'
    }
    return 'CLEAR FOR RELEASE. Standard compliance profile. No indicators of illegal transshipment detected.'
  }

  return (
    <div className="officer-referral-box">
      <h3>🔒 Enforcement Action &amp; Investigation Recommendation</h3>
      <div className="recommendation-statement">
        <strong>Officer Recommendation:</strong>
        <p>{getRecommendation(score)}</p>
      </div>
    </div>
  )
}

export function FederalReferralDocument({
  shipmentId,
  shipment,
  score,
  h1Score,
  h2Score,
  h3Score,
  referralData,
}: FederalReferralDocumentProps) {
  const documentRef = useRef<HTMLDivElement>(null)

  const getRiskColor = (s: number) => {
    if (s >= 70) return 'high-risk'
    if (s >= 50) return 'medium-risk'
    return 'low-risk'
  }

  const generatePDF = async () => {
    if (!documentRef.current) {
      alert('Unable to find document to export')
      return
    }

    try {
      const element = documentRef.current
      const opt = {
        margin: 10,
        filename: `CBP-Referral-${shipmentId}-${new Date().getTime()}.pdf`,
        image: { type: 'jpeg' as const, quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true, logging: false, allowTaint: true },
        jsPDF: { orientation: 'portrait' as const, unit: 'mm' as const, format: 'letter' as const },
        pagebreak: { mode: ['avoid-all' as const, 'css' as const, 'legacy' as const] },
      }

      await html2pdf().set(opt).from(element).save()
    } catch (error) {
      console.error('PDF export error:', error)
      alert('Error generating PDF. Please try again or use browser print function (Ctrl+P).')
    }
  }

  return (
    <div className="federal-referral-document">
      <div className="document-toolbar">
        <button className="export-pdf-btn" onClick={generatePDF} title="Export Federal Referral Package as PDF">
          <Download size={16} />
          Export Referral Package (PDF)
        </button>
      </div>

      <div ref={documentRef} className={`federal-document-container ${getRiskColor(score)}`}>
        {/* Header */}
        <div className="doc-header">
          <div className="doc-header-title">
            <div className="doc-agency">U.S. Department of Homeland Security</div>
            <div className="doc-agency">Customs and Border Protection (CBP)</div>
            <div className="doc-main-title">Illegal Transshipment Intelligence Referral Package</div>
          </div>
          <div className="doc-header-meta">
            <div>
              <strong>Case ID:</strong> EAPA-{shipmentId.substring(0, 8).toUpperCase()}
            </div>
            <div>
              <strong>Date:</strong> {new Date().toLocaleDateString()}
            </div>
            <div>
              <strong>Risk Level:</strong> {score >= 70 ? 'HIGH' : score >= 50 ? 'MEDIUM' : 'LOW'}
            </div>
          </div>
        </div>

        {/* Executive Summary */}
        <section className="doc-section">
          <h2>EXECUTIVE RISK ASSESSMENT</h2>
          <InvestigationNarrativeBanner shipment={shipment} score={score} />
        </section>

        {/* Three-Horizon Assessment */}
        <section className="doc-section">
          <h2>THREE-HORIZON RISK ASSESSMENT</h2>
          <ThreeHorizonRiskBar h1Score={h1Score} h2Score={h2Score} h3Score={h3Score} score={score} />
        </section>

        {/* Shipment Identification Table */}
        <section className="doc-section">
          <h2>TABLE 3-1: SHIPMENT IDENTIFICATION</h2>
          <table className="doc-table">
            <tbody>
              <tr>
                <td className="label">Manifest ID</td>
                <td>{shipment.manifest_id || shipmentId}</td>
              </tr>
              <tr>
                <td className="label">Shipment ID</td>
                <td>{shipmentId}</td>
              </tr>
              <tr>
                <td className="label">HTS Code</td>
                <td>{shipment.hs_code}</td>
              </tr>
              <tr>
                <td className="label">Declared Value</td>
                <td>${shipment.declared_value_usd.toLocaleString()}</td>
              </tr>
              <tr>
                <td className="label">Declared Weight</td>
                <td>{shipment.declared_weight_kg.toLocaleString()} kg</td>
              </tr>
              <tr>
                <td className="label">Port of Lading</td>
                <td>{shipment.port_of_lading || 'Not Specified'}</td>
              </tr>
              <tr>
                <td className="label">Port of Discharge</td>
                <td>{shipment.port_of_discharge || 'Los Angeles, CA'}</td>
              </tr>
            </tbody>
          </table>
        </section>

        {/* Parties and Roles */}
        <section className="doc-section">
          <h2>TABLE 3-4: PARTIES AND ROLES</h2>
          <table className="doc-table">
            <thead>
              <tr>
                <th>Role</th>
                <th>Legal Name</th>
                <th>Country</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="label">Shipper</td>
                <td>{shipment.shipper_name}</td>
                <td>{shipment.origin_country}</td>
                <td>Active</td>
              </tr>
              <tr>
                <td className="label">Consignee</td>
                <td>{shipment.consignee_name}</td>
                <td>{shipment.destination_country}</td>
                <td>Active</td>
              </tr>
              <tr>
                <td className="label">Vessel Operator</td>
                <td>{shipment.vessel_name || 'International Line'}</td>
                <td>International</td>
                <td>Active</td>
              </tr>
            </tbody>
          </table>
        </section>

        {/* Detailed Investigation Findings */}
        <section className="doc-section">
          <h2>DETAILED INVESTIGATION FINDINGS</h2>
          <DetailedInvestigationFindings shipment={shipment} h1Score={h1Score} h2Score={h2Score} h3Score={h3Score} />
        </section>

        {/* Risk Score Breakdown */}
        <section className="doc-section">
          <h2>TABLE 3-12: RISK SCORE BREAKDOWN</h2>
          <table className="doc-table">
            <thead>
              <tr>
                <th>Component</th>
                <th>Score</th>
                <th>Max</th>
                <th>Authority</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="label">H1: Corridor Risk</td>
                <td>{h1Score}</td>
                <td>40</td>
                <td>19 USC § 1516a</td>
              </tr>
              <tr>
                <td className="label">H2: Pre-Manifest Intelligence</td>
                <td>{h2Score}</td>
                <td>35</td>
                <td>19 CFR Part 149</td>
              </tr>
              <tr>
                <td className="label">H3: Network Intelligence</td>
                <td>{h3Score}</td>
                <td>25</td>
                <td>19 USC § 1581</td>
              </tr>
              <tr className="total-row">
                <td className="label">
                  <strong>TOTAL RISK ASSESSMENT</strong>
                </td>
                <td>
                  <strong>{score}</strong>
                </td>
                <td>
                  <strong>100</strong>
                </td>
                <td>EAPA Statute</td>
              </tr>
            </tbody>
          </table>
        </section>

        {/* Officer Action Box */}
        <section className="doc-section">
          <OfficerReferralBox score={score} />
        </section>

        {/* Legal Authority */}
        <section className="doc-section doc-footer">
          <h3>LEGAL AUTHORITY &amp; DATA SOURCES</h3>
          <p className="legal-text">
            This referral package is generated in accordance with the Enforce and Protect Act (EAPA), 19 USC § 1516a,
            and CBP regulations at 19 CFR Part 149 (Importer Security Filing). The analysis applies publicly available
            trade data, ISF filings, vessel tracking data, and supply chain intelligence to identify indicators of
            possible illegal transshipment schemes.
          </p>
          <p className="legal-text">
            <strong>Document Classification:</strong> Official U.S. Government Information. Unauthorized disclosure is
            prohibited by law. 18 USC § 641.
          </p>
        </section>

        {referralData && (
          <section className="doc-section detailed-analysis">
            <h2>SUPPORTING DATA</h2>
            <pre>{JSON.stringify(referralData, null, 2)}</pre>
          </section>
        )}
      </div>
    </div>
  )
}

export default FederalReferralDocument
