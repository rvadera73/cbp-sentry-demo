/**
 * Workflow Signal Map — Shows risk score accumulation through investigation steps
 *
 * Displays:
 * - Current step in workflow (1-6)
 * - Score building at each step with delta
 * - Signal inputs at each step
 * - Real-time progression indicator
 */

import { CheckCircle, Circle, AlertCircle } from 'lucide-react';
import '../styles/WorkflowSignalMap.css';

interface WorkflowStep {
  step: number;
  name: string;
  description: string;
  scoreContribution: number;
  currentScore: number;
  signals: string[];
  status: 'completed' | 'active' | 'pending';
  icon: React.ReactNode;
}

interface WorkflowSignalMapProps {
  currentStep: number;
  totalScore: number;
  h1Score: number;
  h2Score: number;
  h3Score: number;
  entityChainCount: number;
  riskFlagCount: number;
  workflowComplete: boolean;
}

export default function WorkflowSignalMap({
  currentStep,
  totalScore,
  h1Score,
  h2Score,
  h3Score,
  entityChainCount,
  riskFlagCount,
  workflowComplete,
}: WorkflowSignalMapProps) {
  const baseSteps: WorkflowStep[] = [
    {
      step: 1,
      name: 'Manifest Ingestion',
      description: 'Parse & normalize CBP Excel data',
      scoreContribution: 0,
      currentScore: 0,
      signals: ['Shipper', 'Consignee', 'HTS Code', 'Weight', 'Value'],
      status: currentStep > 1 ? 'completed' : currentStep === 1 ? 'active' : 'pending',
      icon: <CheckCircle size={20} className="icon-completed" />,
    },
    {
      step: 2,
      name: 'H1: Corridor Risk',
      description: 'AD/CVD rates, origin risk, shipper profile',
      scoreContribution: h1Score,
      currentScore: h1Score,
      signals: [
        `AD/CVD: ${h1Score > 10 ? '✗ Active' : '✓ None'}`,
        `Origin Risk: ${h1Score > 8 ? '⚠ HIGH' : '✓ Normal'}`,
        `Shipper Age: ${h1Score > 8 ? '⚠ New' : '✓ Established'}`,
        `Pricing: ${h1Score > 10 ? '⚠ Below market' : '✓ Fair'}`,
      ],
      status: currentStep > 2 ? 'completed' : currentStep === 2 ? 'active' : 'pending',
      icon: <CheckCircle size={20} className="icon-completed" />,
    },
    {
      step: 3,
      name: 'H2: Vessel Anomaly',
      description: 'AIS dwell, ISF mismatch, routing gaps',
      scoreContribution: h2Score,
      currentScore: h1Score + h2Score,
      signals: [
        `AIS Dwell: ${h2Score > 12 ? '⚠ 5x baseline' : '✓ Normal'}`,
        `ISF Element 9: ${h2Score > 12 ? '✗ Mismatch' : '✓ Match'}`,
        `AIS Gaps: ${h2Score > 4 ? '⚠ Multiple' : '✓ None'}`,
        `Routing: ${h2Score > 3 ? '⚠ Anomalies' : '✓ Normal'}`,
      ],
      status: currentStep > 3 ? 'completed' : currentStep === 3 ? 'active' : 'pending',
      icon: <CheckCircle size={20} className="icon-completed" />,
    },
    {
      step: 4,
      name: 'H3: Manifest Intelligence',
      description: 'OFAC matches, watch lists, entity patterns',
      scoreContribution: h3Score,
      currentScore: h1Score + h2Score + h3Score,
      signals: [
        `OFAC: ${riskFlagCount > 0 ? '✗ Hits' : '✓ Clear'}`,
        `Watch List: ${riskFlagCount > 1 ? '⚠ Flagged' : '✓ Clear'}`,
        `Entity Chain: ${entityChainCount > 2 ? '⚠ Multi-hop' : '✓ Direct'}`,
        `Patterns: ${riskFlagCount > 0 ? '✗ Suspicious' : '✓ Normal'}`,
      ],
      status: currentStep > 4 ? 'completed' : currentStep === 4 ? 'active' : 'pending',
      icon: <CheckCircle size={20} className="icon-completed" />,
    },
    {
      step: 5,
      name: 'Senzing Resolution',
      description: 'Entity chain tracing, beneficial owners, relationships',
      scoreContribution: 0,
      currentScore: totalScore,
      signals: [
        `Entities: ${entityChainCount} linked`,
        `Confidence: ${entityChainCount > 0 ? '85%+' : 'N/A'}`,
        `Why-Explanations: ${entityChainCount > 0 ? '✓ Available' : '✗ None'}`,
        `Chain Depth: ${entityChainCount > 2 ? '⚠ Deep (transshipment)' : '✓ Direct'}`,
      ],
      status: currentStep > 5 ? 'completed' : currentStep === 5 ? 'active' : 'pending',
      icon: <CheckCircle size={20} className="icon-completed" />,
    },
  ];

  // Add Altana verification step if score >= 70
  const allSteps: WorkflowStep[] = totalScore >= 70 ? [
    ...baseSteps,
    {
      step: 6,
      name: 'Altana Atlas Verification',
      description: 'Cross-check with Altana sanctions & verification database',
      scoreContribution: 0,
      currentScore: totalScore,
      signals: [
        `Atlas Status: ${totalScore >= 90 ? '✓ Full scan' : '✓ Quick check'}`,
        `Result: ${totalScore >= 90 ? '🔴 Referral warranted' : '⚠️ Review recommendation'}`,
        `Data Sources: ${totalScore >= 90 ? 'Sanctions, PEP, Shipper intel' : 'Public data'}`,
        `Confidence: ${totalScore >= 90 ? '95%+' : 'Standard'}`,
      ],
      status: currentStep > 6 ? 'completed' : currentStep === 6 ? 'active' : 'pending',
      icon: <CheckCircle size={20} className="icon-completed" />,
    },
    {
      step: 7,
      name: 'Risk Decision',
      description: 'Gateway filter & recommended action',
      scoreContribution: 0,
      currentScore: totalScore,
      signals: [
        `Score: ${totalScore}/100`,
        `Level: ${totalScore >= 70 ? '🔴 HIGH' : totalScore >= 40 ? '🟡 MEDIUM' : '🟢 LOW'}`,
        `Action: ${totalScore >= 90 ? '📋 Referral' : totalScore >= 70 ? '🔍 Examine' : '✓ Clear'}`,
        `Altana Verified: ${totalScore >= 90 ? '✓ Yes' : '✗ No'}`,
      ],
      status: workflowComplete ? 'completed' : currentStep === 7 ? 'active' : 'pending',
      icon: <CheckCircle size={20} className="icon-completed" />,
    },
  ] : [
    ...baseSteps,
    {
      step: 6,
      name: 'Risk Decision',
      description: 'Gateway filter & recommended action',
      scoreContribution: 0,
      currentScore: totalScore,
      signals: [
        `Score: ${totalScore}/100`,
        `Level: ${totalScore >= 70 ? '🔴 HIGH' : totalScore >= 40 ? '🟡 MEDIUM' : '🟢 LOW'}`,
        `Action: ${totalScore >= 90 ? '📋 Referral' : totalScore >= 70 ? '🔍 Examine' : '✓ Clear'}`,
        `Altana: ${totalScore >= 90 ? '✓ Triggered' : '✗ N/A'}`,
      ],
      status: workflowComplete ? 'completed' : currentStep === 6 ? 'active' : 'pending',
      icon: <CheckCircle size={20} className="icon-completed" />,
    },
  ];

  const steps = allSteps;

  return (
    <div className="workflow-signal-map">
      {/* Summary Bar */}
      <div className="workflow-summary">
        <div className="summary-stat">
          <span className="label">Current Step</span>
          <span className="value">{currentStep} of 6</span>
        </div>
        <div className="summary-stat">
          <span className="label">Score</span>
          <span className={`value score-${totalScore >= 70 ? 'high' : totalScore >= 40 ? 'medium' : 'low'}`}>
            {totalScore}/100
          </span>
        </div>
        <div className="summary-stat">
          <span className="label">H1 + H2 + H3</span>
          <span className="value">{h1Score} + {h2Score} + {h3Score}</span>
        </div>
        <div className="summary-stat">
          <span className="label">Risk Flags</span>
          <span className={`value ${riskFlagCount > 0 ? 'flag-detected' : 'flag-clear'}`}>
            {riskFlagCount} detected
          </span>
        </div>
        <div className="summary-stat">
          <span className="label">Entity Chain</span>
          <span className="value">{entityChainCount} entities</span>
        </div>
      </div>

      {/* Workflow Steps */}
      <div className="workflow-steps">
        {steps.map((step, index) => (
          <div key={step.step} className="step-container">
            {/* Step Header */}
            <div className={`step-header ${step.status}`}>
              <div className="step-icon">
                {step.status === 'completed' ? (
                  <CheckCircle size={24} className="icon-check" />
                ) : step.status === 'active' ? (
                  <AlertCircle size={24} className="icon-active" />
                ) : (
                  <Circle size={24} className="icon-pending" />
                )}
              </div>
              <div className="step-info">
                <h3>Step {step.step}: {step.name}</h3>
                <p>{step.description}</p>
              </div>
              {step.scoreContribution > 0 && (
                <div className={`step-score ${step.status}`}>
                  <span className="contribution">+{step.scoreContribution}</span>
                  <span className="cumulative">= {step.currentScore}</span>
                </div>
              )}
            </div>

            {/* Signals */}
            <div className="step-signals">
              {step.signals.map((signal, idx) => (
                <div key={idx} className="signal-badge">
                  {signal}
                </div>
              ))}
            </div>

            {/* Connector */}
            {index < steps.length - 1 && (
              <div className={`step-connector ${step.status === 'completed' ? 'completed' : ''}`}>
                ↓
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Risk Level Indicator */}
      <div className="risk-decision-banner">
        <div className={`risk-badge risk-${totalScore >= 70 ? 'high' : totalScore >= 40 ? 'medium' : 'low'}`}>
          {totalScore >= 70
            ? '🔴 HIGH RISK'
            : totalScore >= 40
            ? '🟡 MEDIUM RISK'
            : '🟢 LOW RISK'}
        </div>
        <div className="risk-action">
          <strong>Recommended Action:</strong>
          {totalScore >= 90
            ? ' 📋 TRLED Referral + Altana Verification'
            : totalScore >= 70
            ? ' 🔍 Examine on Arrival'
            : totalScore >= 40
            ? ' ⚠️ Standard Review'
            : ' ✓ Clear to Release'}
        </div>
        {totalScore >= 90 && (
          <div className="altana-trigger">
            ✓ Altana API verification triggered
          </div>
        )}
      </div>
    </div>
  );
}
