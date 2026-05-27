/**
 * Tab 1: Referral Display Panel
 * Shows all 14 sections with expandable cards, risk breakdown, edit capabilities
 */

import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Edit2, AlertCircle, Check } from 'lucide-react';
import { ReferralDisplayData, ReferralDisplayPanelProps, NarrativeSection } from './types/ReferralGeneration.types';
import NarrativeEditModal from './NarrativeEditModal';
import './ReferralDisplayPanel.css';

const NARRATIVE_SECTIONS = ['section_3_6_historical_import_pattern', 'section_3_7_trade_flow_intelligence', 'section_3_11_risk_indicators', 'section_3_14_conclusion_and_recommendation'];

const SECTION_METADATA = {
  section_3_1_shipment_identification: { title: 'SECTION 3-1: Shipment Identification', icon: 'Package' },
  section_3_2_line_items: { title: 'SECTION 3-2: Line Items', icon: 'List' },
  section_3_3_routing_history: { title: 'SECTION 3-3: AIS Routing History', icon: 'Map' },
  section_3_4_parties_and_roles: { title: 'SECTION 3-4: Parties & Roles', icon: 'Users' },
  section_3_5_entity_ownership_chain: { title: 'SECTION 3-5: Entity Ownership Chain', icon: 'Network' },
  section_3_6_historical_import_pattern: { title: 'SECTION 3-6: Historical Import Pattern', icon: 'TrendingUp', editable: true },
  section_3_7_trade_flow_intelligence: { title: 'SECTION 3-7: Trade Flow Intelligence', icon: 'Zap', editable: true },
  section_3_8_document_review: { title: 'SECTION 3-8: Document Review', icon: 'FileText' },
  section_3_9_document_consistency: { title: 'SECTION 3-9: Document Consistency', icon: 'CheckCircle' },
  section_3_10_supplier_verification: { title: 'SECTION 3-10: Supplier Verification', icon: 'Building' },
  section_3_11_risk_indicators: { title: 'SECTION 3-11: Risk Indicators', icon: 'AlertTriangle', editable: true },
  section_3_12_pattern_analysis: { title: 'SECTION 3-12: Pattern Analysis', icon: 'BarChart2' },
  section_3_13_enforcement_analysis: { title: 'SECTION 3-13: Enforcement Analysis', icon: 'Shield' },
  section_3_14_conclusion_and_recommendation: { title: 'SECTION 3-14: Conclusion & Recommendation', icon: 'BookmarkCheck', editable: true }
};

export default function ReferralDisplayPanel({ referralData, onNarrativeEdit, onExportPDF }: ReferralDisplayPanelProps) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['section_3_1_shipment_identification']));
  const [editingSection, setEditingSection] = useState<string | null>(null);

  const toggleSection = (sectionId: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(sectionId)) {
      newExpanded.delete(sectionId);
    } else {
      newExpanded.add(sectionId);
    }
    setExpandedSections(newExpanded);
  };

  const renderRiskBreakdown = () => {
    if (!referralData.risk_breakdown) return null;

    return (
      <div className="risk-breakdown-card">
        <h3>Risk Score Breakdown (7-Factor Model)</h3>
        <div className="score-display">
          <span className="score-value">{referralData.risk_breakdown.final_score}</span>
          <span className="score-label">/ 100</span>
        </div>
        <div className="components-grid">
          {referralData.risk_breakdown.components.map((comp, idx) => (
            <div key={idx} className="component-item">
              <div className="component-header">
                <span className="component-name">{comp.component}</span>
                <span className="component-weight">({comp.weight.toFixed(0)}%)</span>
              </div>
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${(comp.weighted_result / comp.weight) * 100}%` }}
                />
              </div>
              <span className="component-score">{comp.score.toFixed(1)}/{comp.weight.toFixed(1)}</span>
            </div>
          ))}
        </div>
        <div className="evidence-section">
          <h4>Top Contributing Factors:</h4>
          <ul>
            {referralData.risk_breakdown.components
              .sort((a, b) => b.weighted_result - a.weighted_result)
              .slice(0, 3)
              .map((comp, idx) => (
                <li key={idx}>
                  <strong>{comp.component}:</strong> {comp.evidence?.[0] || comp.rationale}
                </li>
              ))}
          </ul>
        </div>
      </div>
    );
  };

  const renderSection = (sectionId: string) => {
    const isExpanded = expandedSections.has(sectionId);
    const sectionData = referralData.sections[sectionId];
    const metadata = SECTION_METADATA[sectionId as keyof typeof SECTION_METADATA];
    const isEditable = NARRATIVE_SECTIONS.includes(sectionId);
    const isEdited = referralData.edited_sections?.[sectionId] !== undefined;

    if (!sectionData) return null;

    return (
      <div key={sectionId} className={`section-card ${isExpanded ? 'expanded' : ''} ${isEdited ? 'edited' : ''}`}>
        <div className="section-header" onClick={() => toggleSection(sectionId)}>
          <div className="section-title-group">
            {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
            <h4 className="section-title">{metadata?.title}</h4>
            {isEdited && <span className="edited-badge">Edited</span>}
          </div>

          {isEditable && (
            <button
              className="edit-button"
              onClick={(e) => {
                e.stopPropagation();
                setEditingSection(sectionId);
              }}
              title="Edit this section"
            >
              <Edit2 size={18} />
            </button>
          )}
        </div>

        {isExpanded && (
          <div className="section-content">
            {typeof sectionData === 'object' ? (
              <div className="data-grid">
                {Object.entries(sectionData).map(([key, value]) => (
                  <div key={key} className="data-row">
                    <span className="data-key">{key.replace(/_/g, ' ')}:</span>
                    <span className="data-value">{formatValue(value)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p>{sectionData}</p>
            )}
          </div>
        )}
      </div>
    );
  };

  const formatValue = (value: any): string => {
    if (value === null || value === undefined) return '—';
    if (typeof value === 'boolean') return value ? 'Yes' : 'No';
    if (Array.isArray(value)) return value.join(', ');
    if (typeof value === 'object') return JSON.stringify(value, null, 2);
    return String(value);
  };

  return (
    <div className="referral-display-panel">
      <div className="referral-display-panel__content">
        {/* Risk Breakdown */}
        <section className="display-section">
          {renderRiskBreakdown()}
        </section>

        {/* Data Sections */}
        <section className="display-section">
          <h3 className="section-group-title">14 Referral Sections</h3>
          <div className="sections-container">
            {Object.keys(SECTION_METADATA).map(sectionId => renderSection(sectionId))}
          </div>
        </section>

        {/* Data Sources */}
        <section className="display-section">
          <div className="data-sources-card">
            <h4>Data Sources & Attribution</h4>
            <ul>
              <li>ISF 10+2 Data: CBP Automated Manifest System (100%)</li>
              <li>AIS Tracking: MarineTraffic & Spire APIs (Real-time)</li>
              <li>Entity Resolution: Senzing CORD Index (Confidence: 92%)</li>
              <li>Price Benchmarking: USITC Trade Data</li>
              <li>Risk Scoring: CBP Sentry 7-Factor Engine (v2.1)</li>
            </ul>
            <p className="timestamp">Last Updated: {new Date(referralData.created_at).toLocaleString()}</p>
          </div>
        </section>
      </div>

      {/* Narrative Edit Modal */}
      {editingSection && (
        <NarrativeEditModal
          section={{
            section_id: editingSection as any,
            title: SECTION_METADATA[editingSection as keyof typeof SECTION_METADATA]?.title || 'Unknown',
            current_narrative: referralData.edited_sections?.[editingSection]?.edited_content || referralData.sections[editingSection]?.pattern_narrative || referralData.sections[editingSection]?.trade_flow_narrative || referralData.sections[editingSection]?.summary || referralData.sections[editingSection]?.conclusion_narrative || '',
            is_edited: referralData.edited_sections?.[editingSection] !== undefined,
            can_regenerate: true
          }}
          referralId={referralData.referral_id}
          onSave={(editedContent) => {
            onNarrativeEdit?.(editingSection, editedContent);
            setEditingSection(null);
          }}
          onRegenerate={async () => ''}
          onClose={() => setEditingSection(null)}
        />
      )}
    </div>
  );
}
