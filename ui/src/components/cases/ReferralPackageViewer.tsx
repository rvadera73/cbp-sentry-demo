import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import '../styles/ReferralPackageViewer.css'

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
  }
  score: number
  h1Score: number
  h2Score: number
  h3Score: number
}

export default function ReferralPackageViewer({
  shipmentId,
  shipment,
  score,
  h1Score,
  h2Score,
  h3Score,
}: ReferralPackageViewerProps) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['3-1']))

  const toggleSection = (sectionId: string) => {
    const newExpanded = new Set(expandedSections)
    if (newExpanded.has(sectionId)) {
      newExpanded.delete(sectionId)
    } else {
      newExpanded.add(sectionId)
    }
    setExpandedSections(newExpanded)
  }

  const sections = [
    {
      number: '3-1',
      title: 'Shipment Identification',
      description: 'Basic shipment and manifest data',
      details: {
        manifest_id: shipmentId,
        shipper: shipment.shipper_name,
        consignee: shipment.consignee_name,
        hs_code: shipment.hs_code,
        value_usd: shipment.declared_value_usd,
        weight_kg: shipment.declared_weight_kg,
        route: `${shipment.origin_country} → ${shipment.destination_country}`,
        vessel: shipment.vessel_name || 'N/A',
      },
    },
    {
      number: '3-2',
      title: 'Line Items & Product Details',
      description: 'Commodity classification and specifications',
      details: {
        hs_code: shipment.hs_code,
        unit_price_declared: '$10.50 per kg',
        total_weight: `${shipment.declared_weight_kg} kg`,
        total_value: `$${shipment.declared_value_usd.toLocaleString()}`,
      },
    },
    {
      number: '3-3',
      title: 'Routing History & Vessel Data',
      description: 'AIS vessel tracking and port calls',
      details: {
        vessel_name: shipment.vessel_name || 'N/A',
        dwell_time: '11.2 days',
        port_calls: ['Guangzhou (CN)', 'Haiphong (VN)', 'Los Angeles (US)'],
      },
    },
    {
      number: '3-4',
      title: 'Parties & Roles',
      description: 'Shipper, manufacturer, consignee, freight forwarder',
      details: {
        shipper: shipment.shipper_name,
        consignee: shipment.consignee_name,
        origin_country: shipment.origin_country,
        destination_country: shipment.destination_country,
      },
    },
    {
      number: '3-5',
      title: 'Entity Ownership Chain',
      description: 'Beneficial ownership and corporate structure',
      details: {
        tier_1: 'Guangdong Greenfield Aluminum (CN)',
        tier_2: 'Greenfield Global Holdings (HK)',
        tier_3: 'Greenfield Industrial Trading (VN)',
        tier_4: 'SunPath Energy Distributors (US)',
      },
    },
    {
      number: '3-6',
      title: 'Historical Import Pattern Analysis',
      description: 'Prior shipment history and trend analysis',
      details: {
        prior_entries: 3,
        volume_trend: 'Increased 240% YoY',
        origin_shift: 'From Germany to China',
      },
    },
    {
      number: '3-7',
      title: 'Trade Flow Intelligence',
      description: 'Customs filings and historical intelligence',
      details: {
        prior_cbp_filings: 12,
        prior_holds: 'None',
        prior_examinations: 1,
      },
    },
    {
      number: '3-8',
      title: 'Document Review',
      description: 'Completeness and availability of supporting documents',
      details: {
        commercial_invoice: '✓ Present',
        packing_list: '✓ Present',
        factory_records: '✗ Missing',
      },
    },
    {
      number: '3-9',
      title: 'Document Consistency Analysis',
      description: 'Cross-document field alignment',
      details: {
        invoice_vs_bl: 'Match ✓',
        weight_consistency: 'Match ✓',
        origin_consistency: 'Mismatch ✗',
      },
    },
    {
      number: '3-10',
      title: 'Supplier Manufacturing Verification',
      description: 'Factory capacity and production verification',
      details: {
        supplier: 'Guangdong Greenfield Aluminum',
        claimed_capacity: '500 MT/month',
        this_shipment: `${(shipment.declared_weight_kg / 1000).toFixed(1)} MT`,
      },
    },
    {
      number: '3-11',
      title: 'Risk Indicator Summary',
      description: 'Named indicators with legal authority',
      details: {
        under_invoice: '15 pts',
        transshipment_risk: '10 pts',
        isf_mismatch: '10 pts',
        circumvention_pattern: '8 pts',
      },
    },
    {
      number: '3-12',
      title: 'Score Breakdown',
      description: 'Component scores and horizon allocation',
      details: {
        h1_corridor: `${h1Score}/40`,
        h2_vessel: `${h2Score}/35`,
        h3_intelligence: `${h3Score}/25`,
        total: `${Math.round(score)}/100`,
      },
    },
    {
      number: '3-13',
      title: 'What-If Scenarios',
      description: 'Score impact if key facts were different',
      details: {
        'if_shipper_established': `${Math.max(score - 8, 0)}/100`,
        'if_factory_records': `${Math.max(score - 10, 0)}/100`,
        'if_normal_pricing': `${Math.max(score - 15, 0)}/100`,
      },
    },
    {
      number: '3-14',
      title: 'Data Sources & Update History',
      description: 'Information sources and audit trail',
      details: {
        'sources': 'CBP, OpenCorporates, Senzing, CORD, AIS',
        'last_updated': new Date().toISOString().split('T')[0],
        'analyst': 'AI Risk Scoring System v1.0',
      },
    },
  ]

  return (
    <div className="referral-package">
      <div className="referral-header">
        <h2>CBP EAPA Referral Package — 14 Sections</h2>
        <p style={{ color: '#666', marginTop: '8px', fontSize: '14px' }}>
          Shipment {shipmentId} | Risk Score: {Math.round(score)}/100 | {score >= 70 ? '🔴 HIGH' : score >= 40 ? '🟡 MEDIUM' : '🟢 LOW'}
        </p>
      </div>

      <div className="referral-sections">
        {sections.map((section) => (
          <div key={section.number} className="section-accordion">
            <button
              className="section-header"
              onClick={() => toggleSection(section.number)}
            >
              <div className="section-title">
                <span className="section-number">{section.number}</span>
                <div>
                  <h3>{section.title}</h3>
                  <p>{section.description}</p>
                </div>
              </div>
              <ChevronDown
                size={20}
                style={{
                  transform: expandedSections.has(section.number) ? 'rotate(180deg)' : 'rotate(0deg)',
                  transition: 'transform 0.2s',
                }}
              />
            </button>

            {expandedSections.has(section.number) && (
              <div className="section-content">
                <table className="details-table">
                  <tbody>
                    {Object.entries(section.details).map(([key, value]) => (
                      <tr key={key}>
                        <td className="detail-key">{key.replace(/_/g, ' ').toUpperCase()}</td>
                        <td className="detail-value">{String(value)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="referral-footer">
        <button className="btn-export" onClick={() => window.print()}>
          📄 Export as PDF
        </button>
        <button className="btn-share" onClick={() => console.log('Share referral package')}>
          🔗 Share
        </button>
      </div>
    </div>
  )
}
