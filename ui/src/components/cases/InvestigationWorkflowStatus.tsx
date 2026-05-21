/**
 * Investigation Workflow Status — Unified visualization
 *
 * Consolidates three separate visualizations into one:
 * 1. Workflow progression (4 steps: Manifest → Entity Resolution → Risk Scoring → Referral)
 * 2. Score accumulation (H1 + H2 + H3 → total)
 * 3. Overall risk classification (HIGH/MEDIUM/LOW)
 *
 * Displays as:
 * - Horizontal timeline at top of case viewer
 * - Left: 4-step progression with visual indicators
 * - Right: Score summary box with component breakdown
 */

import React from 'react'
import { CheckCircle, AlertCircle, Clock, Zap } from 'lucide-react'
import { WorkflowState, WorkflowStep } from '../../context/WorkflowContext'
import './InvestigationWorkflowStatus.css'

interface InvestigationWorkflowStatusProps {
  /** Workflow state from context */
  workflowState: WorkflowState
  /** Callback when step completes */
  onStepComplete?: (step: WorkflowStep) => void
  /** Callback to retry on error */
  onRetry?: () => void
}

// Legacy props support for backward compatibility
interface InvestigationWorkflowStatusLegacyProps {
  /** Current step: 1 = Manifest, 2 = Entity Resolution, 3 = Risk Scoring, 4 = Referral */
  currentStep: number
  /** H1 (Corridor Risk) score and max */
  h1Score: number
  h1MaxScore?: number
  /** H2 (Vessel Intelligence) score and max */
  h2Score: number
  h2MaxScore?: number
  /** H3 (Entity/Watch List) score and max */
  h3Score: number
  h3MaxScore?: number
  /** Total combined score */
  totalScore: number
  /** Total possible score */
  maxScore?: number
  /** Whether workflow is complete */
  isComplete?: boolean
  /** Whether currently processing (show loading state) */
  isProcessing?: boolean
}

/**
 * Get risk level and color styling from score
 */
const getRiskLevel = (score: number | null) => {
  if (!score) return { label: 'CALCULATING', color: '#6b7280', bg: '#f3f4f6' }
  if (score > 90) return { label: 'CRITICAL', color: '#dc2626', bg: '#fee2e2' }
  if (score > 70) return { label: 'HIGH', color: '#ea580c', bg: '#fed7aa' }
  if (score >= 30) return { label: 'MEDIUM', color: '#eab308', bg: '#fef08a' }
  return { label: 'LOW', color: '#22c55e', bg: '#dcfce7' }
}

/**
 * Get icon for workflow step status
 */
const getStepIcon = (status: string) => {
  if (status === 'complete') {
    return <CheckCircle size={24} className="step-icon step-icon--complete" />
  }
  if (status === 'error') {
    return <AlertCircle size={24} className="step-icon step-icon--error" />
  }
  if (status === 'in-progress') {
    return <Zap size={24} className="step-icon step-icon--progress" />
  }
  return <Clock size={24} className="step-icon step-icon--pending" />
}

/**
 * Main component: Supports both context-based and legacy props
 */
function InvestigationWorkflowStatusImpl({
  workflowState,
  onStepComplete,
  onRetry,
}: InvestigationWorkflowStatusProps) {
  const stepsConfig: Array<{ key: WorkflowStep; name: string; label: string }> = [
    { key: 'ingest', name: 'Manifest', label: 'Upload' },
    { key: 'entity-resolution', name: 'Entity', label: 'Resolution' },
    { key: 'scoring', name: 'Risk', label: 'Scoring' },
    { key: 'referral', name: 'Referral', label: 'Ready' },
  ]

  const riskInfo = getRiskLevel(workflowState.total_score)

  return (
    <section
      className="investigation-workflow-status"
      aria-label="Investigation workflow progress"
      role="status"
      aria-live="polite"
    >
      <h2 className="workflow-title">Investigation Workflow</h2>

      {/* Error Display */}
      {workflowState.workflowError && (
        <div className="workflow-error" role="alert">
          <AlertCircle size={16} />
          <span>{workflowState.workflowError}</span>
          {onRetry && (
            <button className="error-retry-btn" onClick={onRetry}>
              Retry
            </button>
          )}
        </div>
      )}

      {/* Timeline Steps */}
      <div className="workflow-timeline">
        {stepsConfig.map((step, idx) => (
          <React.Fragment key={step.key}>
            <div
              className={`workflow-step workflow-step--${step.key === workflowState.currentStep ? 'active' : 'inactive'} workflow-step--${workflowState.stepStatus[step.key]}`}
              role="listitem"
              aria-label={`${step.name}: ${workflowState.stepStatus[step.key]}`}
            >
              <div className="step-icon-wrapper">
                {getStepIcon(workflowState.stepStatus[step.key])}
              </div>
              <div className="step-content">
                <div className="step-label">{step.name}</div>
                <div className="step-status">{step.label}</div>
              </div>
            </div>

            {idx < stepsConfig.length - 1 && (
              <div
                className={`workflow-connector workflow-connector--${workflowState.stepStatus[step.key] === 'complete' ? 'complete' : 'pending'}`}
                aria-hidden="true"
              >
                →
              </div>
            )}
          </React.Fragment>
        ))}
      </div>

      {/* Score Summary Box */}
      <div className={`score-summary score-summary--${riskInfo.label.toLowerCase()}`} style={{ borderColor: riskInfo.color }}>
        <div className="score-header">
          <div className="score-value" style={{ color: riskInfo.color }}>
            {workflowState.total_score !== null ? (
              <>
                {Math.round(workflowState.total_score)}
                <span className="score-max">/100</span>
              </>
            ) : (
              'Calculating...'
            )}
          </div>
          <div className="score-level" style={{ backgroundColor: riskInfo.bg, color: riskInfo.color }}>
            {riskInfo.label}
          </div>
        </div>

        {/* Component Breakdown */}
        <div className="score-components">
          <div className="component-row">
            <span className="component-label">H1 Corridor Risk</span>
            <span className="component-value">
              {workflowState.h1_score !== null ? Math.round(workflowState.h1_score) : '—'}
              <span className="max">/40</span>
            </span>
          </div>
          <div className="component-row">
            <span className="component-label">H2 Vessel Risk</span>
            <span className="component-value">
              {workflowState.h2_score !== null ? Math.round(workflowState.h2_score) : '—'}
              <span className="max">/40</span>
            </span>
          </div>
          <div className="component-row">
            <span className="component-label">H3 Network Intelligence</span>
            <span className="component-value">
              {workflowState.h3_score !== null ? Math.round(workflowState.h3_score) : '—'}
              <span className="max">/40</span>
            </span>
          </div>
        </div>

        {/* Progress Indicator */}
        {workflowState.total_score !== null && (
          <div className="progress-bar-wrapper">
            <div
              className="progress-bar-fill"
              style={{
                width: `${Math.min(100, workflowState.total_score)}%`,
                backgroundColor: riskInfo.color,
              }}
              role="progressbar"
              aria-valuenow={Math.round(workflowState.total_score)}
              aria-valuemin={0}
              aria-valuemax={100}
            />
          </div>
        )}

        {/* Status Indicator */}
        {workflowState.stepStatus.referral === 'complete' && (
          <div className="workflow-status-indicator complete">
            <span className="status-dot"></span>
            Workflow Complete
          </div>
        )}
        {workflowState.stepStatus.scoring === 'in-progress' && (
          <div className="workflow-status-indicator processing">
            <span className="status-dot"></span>
            Scoring in progress...
          </div>
        )}
      </div>
    </section>
  )
}

/**
 * Export component with default handler and backward-compatible wrapper
 */
export default function InvestigationWorkflowStatus(props: any) {
  // Support legacy props for backward compatibility
  if ('currentStep' in props && !('workflowState' in props)) {
    // Convert legacy props to modern format
    const workflowState: WorkflowState = {
      manifestId: null,
      manifestData: null,
      manifestRows: [],
      entities: null,
      entitiesResolved: false,
      score: null,
      scoringComplete: false,
      referralPackage: null,
      referralId: null,
      ingestLoading: false,
      entitiesLoading: false,
      scoringLoading: false,
      referralLoading: false,
      errors: {},
      currentStep: props.currentStep === 1 ? 'ingest' : props.currentStep === 2 ? 'entity-resolution' : props.currentStep === 3 ? 'scoring' : 'referral',
      stepStatus: {
        ingest: props.currentStep > 1 ? 'complete' : props.currentStep === 1 ? 'in-progress' : 'pending',
        'entity-resolution': props.currentStep > 2 ? 'complete' : props.currentStep === 2 ? 'in-progress' : 'pending',
        scoring: props.currentStep > 3 ? 'complete' : props.currentStep === 3 ? 'in-progress' : 'pending',
        referral: props.currentStep > 4 ? 'complete' : props.currentStep === 4 ? 'in-progress' : 'pending',
      },
      h1_score: props.h1Score || null,
      h2_score: props.h2Score || null,
      h3_score: props.h3Score || null,
      total_score: props.totalScore || null,
      risk_level: null,
      workflowError: null,
    }
    return <InvestigationWorkflowStatusImpl workflowState={workflowState} />
  }

  // Modern usage with context
  return <InvestigationWorkflowStatusImpl {...props} />
}

