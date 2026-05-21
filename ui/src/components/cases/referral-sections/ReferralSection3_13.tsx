import React, { useState } from 'react';
import { Lightbulb } from 'lucide-react';
import { Section3_13_WhatIfScenarios } from '../ReferralPackage.types';
import { SectionWrapper } from './SectionWrapper';

interface ReferralSection3_13Props {
  data: Section3_13_WhatIfScenarios;
  defaultExpanded?: boolean;
}

export function ReferralSection3_13({
  data,
  defaultExpanded = false,
}: ReferralSection3_13Props) {
  const [selectedScenarioId, setSelectedScenarioId] = useState<string | null>(null);

  const selectedScenario = data.scenarios.find((s) => s.scenario_id === selectedScenarioId);
  const scenarioDelta = selectedScenario
    ? selectedScenario.projected_score - data.baseline_score
    : 0;
  const scenarioImpactColor = scenarioDelta < 0 ? '#2e8540' : '#d9381e';

  return (
    <SectionWrapper
      sectionId="section-3-13"
      sectionNumber="3-13"
      title="What-If Scenarios (Interactive)"
      icon={<Lightbulb size={16} />}
      dataQuality="COMPLETE"
      defaultExpanded={defaultExpanded}
    >
      <div
        style={{
          padding: '12px',
          backgroundColor: '#f0f4f8',
          borderRadius: '6px',
          border: '1px solid #d0dce5',
          marginBottom: '16px',
        }}
      >
        <div style={{ fontSize: '12px', color: '#2d3748', lineHeight: '1.5' }}>
          <strong>How to use:</strong> Click any scenario card below to see how addressing that issue would impact the overall risk
          score. Green indicates reduced risk; red indicates increased risk.
        </div>
      </div>

      <div className="referral-section__stats">
        <div className="referral-section__stat">
          <span className="referral-section__stat-label">Baseline Score</span>
          <span className="referral-section__stat-value">{data.baseline_score}/100</span>
        </div>
        {selectedScenario && (
          <>
            <div className="referral-section__stat">
              <span className="referral-section__stat-label">Projected Score</span>
              <span className="referral-section__stat-value" style={{ color: scenarioImpactColor }}>
                {selectedScenario.projected_score}/100
              </span>
            </div>
            <div className="referral-section__stat">
              <span className="referral-section__stat-label">Delta</span>
              <span className="referral-section__stat-value" style={{ color: scenarioImpactColor }}>
                {scenarioDelta > 0 ? '+' : ''}{scenarioDelta}
              </span>
            </div>
          </>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr)), gap: 12px', marginTop: '16px' }}>
        {data.scenarios.map((scenario) => {
          const isSelected = selectedScenarioId === scenario.scenario_id;
          const delta = scenario.projected_score - data.baseline_score;
          const deltaColor = delta < 0 ? '#2e8540' : delta === 0 ? '#5a6c7d' : '#d9381e';
          const deltaBgColor = delta < 0 ? '#e7f4e4' : delta === 0 ? '#f0f4f8' : '#ffe6e6';

          return (
            <div
              key={scenario.scenario_id}
              onClick={() =>
                setSelectedScenarioId(isSelected ? null : scenario.scenario_id)
              }
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  setSelectedScenarioId(isSelected ? null : scenario.scenario_id);
                }
              }}
              role="button"
              tabIndex={0}
              style={{
                padding: '16px',
                border: `2px solid ${
                  isSelected ? '#013060' : deltaColor
                }`,
                borderRadius: '8px',
                backgroundColor: isSelected ? '#f0f8ff' : '#ffffff',
                cursor: 'pointer',
                transition: 'all 0.2s',
                boxShadow: isSelected ? '0 2px 8px rgba(1, 48, 96, 0.2)' : '0 1px 3px rgba(0,0,0,0.1)',
              }}
            >
              <h4
                style={{
                  margin: '0 0 8px 0',
                  fontSize: '13px',
                  fontWeight: 600,
                  color: '#1a202c',
                  lineHeight: '1.3',
                }}
              >
                {scenario.title}
              </h4>
              <p
                style={{
                  margin: '0 0 12px 0',
                  fontSize: '12px',
                  color: '#5a6c7d',
                  lineHeight: '1.4',
                }}
              >
                {scenario.description}
              </p>

              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '8px',
                  backgroundColor: deltaBgColor,
                  borderRadius: '4px',
                }}
              >
                <span style={{ fontSize: '11px', fontWeight: 600, color: deltaColor }}>
                  Projected Score
                </span>
                <span
                  style={{
                    fontSize: '14px',
                    fontWeight: 700,
                    color: deltaColor,
                  }}
                >
                  {scenario.projected_score}/100
                </span>
              </div>

              <div
                style={{
                  marginTop: '8px',
                  fontSize: '11px',
                  fontWeight: 600,
                  color: deltaColor,
                  textAlign: 'center',
                }}
              >
                {delta > 0 ? '+' : ''}{delta} vs baseline
              </div>
            </div>
          );
        })}
      </div>

      {selectedScenario && (
        <div
          style={{
            marginTop: '20px',
            padding: '16px',
            backgroundColor: '#f7fafc',
            border: '1px solid #d0dce5',
            borderRadius: '6px',
          }}
        >
          <h4
            style={{
              margin: '0 0 12px 0',
              fontSize: '14px',
              fontWeight: 600,
              color: '#013060',
            }}
          >
            Scenario Details: {selectedScenario.title}
          </h4>

          {selectedScenario.affected_signals && selectedScenario.affected_signals.length > 0 && (
            <div style={{ marginBottom: '16px' }}>
              <div
                style={{
                  fontSize: '12px',
                  fontWeight: 600,
                  color: '#1a202c',
                  marginBottom: '8px',
                }}
              >
                Affected Risk Signals:
              </div>
              <div
                style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: '6px',
                }}
              >
                {selectedScenario.affected_signals.map((signal, idx) => (
                  <span
                    key={idx}
                    style={{
                      padding: '4px 8px',
                      backgroundColor: '#e7f4e4',
                      color: '#1b4d22',
                      borderRadius: '4px',
                      fontSize: '11px',
                      fontWeight: 600,
                    }}
                  >
                    {signal}
                  </span>
                ))}
              </div>
            </div>
          )}

          {selectedScenario.required_evidence && (
            <div className="referral-section__evidence">
              <span className="referral-section__evidence-label">Documentary Evidence Required</span>
              {selectedScenario.required_evidence}
            </div>
          )}

          {selectedScenario.legal_remedy && (
            <div
              className="referral-section__evidence"
              style={{
                marginTop: '12px',
                borderLeftColor: '#4ac4d3',
                backgroundColor: '#e6f3ff',
              }}
            >
              <span className="referral-section__evidence-label">CBP Legal Remedy / Pathway</span>
              {selectedScenario.legal_remedy}
            </div>
          )}

          {selectedScenario.cbp_procedure_link && (
            <div
              style={{
                marginTop: '12px',
                padding: '12px',
                backgroundColor: '#f0f4f8',
                borderRadius: '4px',
                border: '1px solid #d0dce5',
                fontSize: '12px',
                color: '#2d3748',
              }}
            >
              <strong>Reference:</strong>{' '}
              <a
                href={selectedScenario.cbp_procedure_link}
                target="_blank"
                rel="noopener noreferrer"
                className="referral-section__evidence-link"
              >
                {selectedScenario.cbp_procedure_link}
              </a>
            </div>
          )}
        </div>
      )}
    </SectionWrapper>
  );
}
