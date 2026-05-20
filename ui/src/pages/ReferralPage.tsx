import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import type { ReferralPackage } from '../types/sentry'

const ReferralPage: React.FC = () => {
  const { manifestId } = useParams<{ manifestId: string }>()
  const navigate = useNavigate()
  const [referral, setReferral] = useState<ReferralPackage | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['shipment_identification']))

  useEffect(() => {
    loadReferral()
  }, [manifestId])

  const loadReferral = async () => {
    if (!manifestId) {
      setError('No manifest ID provided')
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await api.getReferralPackage(manifestId)
      if (response) {
        setReferral(response)
      } else {
        setError('Failed to load referral package')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev)
      if (next.has(section)) {
        next.delete(section)
      } else {
        next.add(section)
      }
      return next
    })
  }

  if (loading) {
    return (
      <div className="bg-white p-8 rounded-lg shadow text-center">
        <p className="text-sentry-slate">Loading referral package...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
        {error}
      </div>
    )
  }

  if (!referral) {
    return (
      <div className="bg-white p-8 rounded-lg shadow text-center text-gray-600">
        No referral package found.
      </div>
    )
  }

  // List of all 14 CBP referral sections
  const sections = [
    { id: 'shipment_identification', label: 'Shipment Identification' },
    { id: 'line_items', label: 'Line Items' },
    { id: 'routing_history', label: 'Routing History' },
    { id: 'parties', label: 'Parties' },
    { id: 'entity_ownership_chain', label: 'Entity Ownership Chain' },
    { id: 'commodity_analysis', label: 'Commodity Analysis' },
    { id: 'hts_classification', label: 'HTS Classification' },
    { id: 'duty_rates', label: 'Duty Rates & AD/CVD' },
    { id: 'entity_resolution_results', label: 'Entity Resolution Results' },
    { id: 'scoring_breakdown', label: 'Scoring Breakdown' },
    { id: 'xai_assertions', label: 'XAI Assertions' },
    { id: 'recommended_action', label: 'Recommended Action' },
    { id: 'revenue_impact', label: 'Revenue Impact Analysis' },
    { id: 'officer_notes', label: 'Officer Notes' },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-sentry-navy mb-2">Referral Package</h2>
        <p className="text-sentry-slate">
          CBP enforcement-ready 14-section referral document (ID: {referral.package_id})
        </p>
      </div>

      {/* Header Card */}
      <div className="bg-gradient-to-r from-sentry-navy to-sentry-dark-teal text-white p-6 rounded-lg shadow">
        <div className="grid grid-cols-4 gap-4">
          <div>
            <p className="text-sm text-gray-200">Status</p>
            <p className="text-2xl font-bold">{referral.confidence_level}</p>
          </div>
          <div>
            <p className="text-sm text-gray-200">Total Score</p>
            <p className="text-2xl font-bold">{referral.total_score}/100</p>
          </div>
          <div>
            <p className="text-sm text-gray-200">Recommendation</p>
            <p className="text-lg font-bold">{referral.recommended_action}</p>
          </div>
          <div>
            <p className="text-sm text-gray-200">Created</p>
            <p className="text-sm font-mono">
              {new Date(referral.created_at).toLocaleDateString()}
            </p>
          </div>
        </div>
      </div>

      {/* Expandable Sections */}
      <div className="space-y-2">
        {sections.map((section) => (
          <div key={section.id} className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            {/* Section Header */}
            <button
              onClick={() => toggleSection(section.id)}
              className="w-full px-6 py-4 text-left font-semibold text-sentry-navy hover:bg-gray-50 flex items-center justify-between"
            >
              <span>{section.label}</span>
              <span className={`transition-transform ${expandedSections.has(section.id) ? 'rotate-180' : ''}`}>
                ▼
              </span>
            </button>

            {/* Section Content */}
            {expandedSections.has(section.id) && (
              <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
                <div className="space-y-4">
                  {section.id === 'shipment_identification' && referral.sections.shipment_identification && (
                    <div className="space-y-2 text-sm">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <span className="font-semibold text-gray-700">Bill of Lading:</span>
                          <p className="text-gray-600">{referral.sections.shipment_identification.bill_of_lading}</p>
                        </div>
                        <div>
                          <span className="font-semibold text-gray-700">HTS Code:</span>
                          <p className="text-gray-600">{referral.sections.shipment_identification.hts_code}</p>
                        </div>
                        <div>
                          <span className="font-semibold text-gray-700">Shipper:</span>
                          <p className="text-gray-600">
                            {referral.sections.shipment_identification.shipper_name} ({referral.sections.shipment_identification.shipper_country})
                          </p>
                        </div>
                        <div>
                          <span className="font-semibold text-gray-700">Consignee:</span>
                          <p className="text-gray-600">{referral.sections.shipment_identification.consignee_name}</p>
                        </div>
                        <div>
                          <span className="font-semibold text-gray-700">Declared Origin:</span>
                          <p className="text-gray-600">{referral.sections.shipment_identification.declared_country_of_origin}</p>
                        </div>
                        <div>
                          <span className="font-semibold text-gray-700">Declared Value:</span>
                          <p className="text-gray-600">
                            ${referral.sections.shipment_identification.declared_value_usd.toLocaleString()}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  {section.id === 'line_items' && referral.sections.line_items && (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm border-collapse">
                        <thead>
                          <tr className="bg-gray-200">
                            <th className="border border-gray-300 px-3 py-2 text-left font-semibold">SKU</th>
                            <th className="border border-gray-300 px-3 py-2 text-left font-semibold">Description</th>
                            <th className="border border-gray-300 px-3 py-2 text-right font-semibold">Qty (kg)</th>
                            <th className="border border-gray-300 px-3 py-2 text-right font-semibold">Unit Value</th>
                            <th className="border border-gray-300 px-3 py-2 text-right font-semibold">Line Total</th>
                          </tr>
                        </thead>
                        <tbody>
                          {referral.sections.line_items.map((item, idx) => (
                            <tr key={idx}>
                              <td className="border border-gray-300 px-3 py-2">{item.sku}</td>
                              <td className="border border-gray-300 px-3 py-2">{item.description}</td>
                              <td className="border border-gray-300 px-3 py-2 text-right">{item.quantity_kg.toLocaleString()}</td>
                              <td className="border border-gray-300 px-3 py-2 text-right">
                                ${item.unit_value_usd.toFixed(2)}
                              </td>
                              <td className="border border-gray-300 px-3 py-2 text-right">
                                ${item.line_total_usd.toLocaleString()}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {section.id === 'routing_history' && referral.sections.routing_history && (
                    <div className="space-y-2">
                      {referral.sections.routing_history.map((event, idx) => (
                        <div key={idx} className="border-l-4 border-sentry-teal pl-4 py-2">
                          <div className="font-semibold text-gray-900">{event.event}</div>
                          <div className="text-sm text-gray-600">
                            {event.location} • {event.date}
                          </div>
                          {event.notes && <div className="text-sm text-gray-500 mt-1">{event.notes}</div>}
                        </div>
                      ))}
                    </div>
                  )}

                  {section.id === 'entity_ownership_chain' && referral.sections.entity_ownership_chain && (
                    <div className="space-y-3">
                      {referral.sections.entity_ownership_chain.map((entity, idx) => (
                        <div key={idx} className="border border-gray-200 rounded p-3 bg-white">
                          <div className="text-sm">
                            <p className="font-semibold text-gray-900">Tier {entity.tier}: {entity.entity_name}</p>
                            <p className="text-gray-600">Country: {entity.country}</p>
                            {entity.ownership_percentage !== undefined && (
                              <p className="text-gray-600">Ownership: {entity.ownership_percentage}%</p>
                            )}
                            {entity.director_names && entity.director_names.length > 0 && (
                              <p className="text-gray-600">Directors: {entity.director_names.join(', ')}</p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {(section.id === 'commodity_analysis' ||
                    section.id === 'hts_classification' ||
                    section.id === 'duty_rates' ||
                    section.id === 'entity_resolution_results' ||
                    section.id === 'scoring_breakdown' ||
                    section.id === 'xai_assertions' ||
                    section.id === 'recommended_action' ||
                    section.id === 'revenue_impact' ||
                    section.id === 'officer_notes') && (
                    <div className="bg-white border border-gray-200 rounded p-3 text-sm text-gray-600">
                      <pre className="whitespace-pre-wrap font-mono text-xs">
                        {JSON.stringify(referral.sections[section.id as keyof typeof referral.sections] || {}, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Navigation */}
      <div className="flex justify-between pt-4">
        <button
          onClick={() => navigate('/scoring')}
          className="px-6 py-2 text-gray-700 hover:text-gray-900"
        >
          ← Back
        </button>
        <button
          onClick={() => navigate(`/graph`)}
          className="px-6 py-2 rounded font-semibold bg-sentry-teal text-white hover:bg-sentry-dark-teal transition-all"
        >
          View Knowledge Graph →
        </button>
      </div>
    </div>
  )
}

export default ReferralPage
