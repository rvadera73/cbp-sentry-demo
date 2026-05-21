import React, { createContext, useContext, useState, ReactNode, useCallback } from 'react'
import type {
  ManifestIngestResponse,
  Entity,
  ScoreResponse,
  ReferralPackage,
} from '../types/sentry'

/**
 * WorkflowContext — shared state across pages
 * Enables data flow: Ingest → ER → Scoring → Referral → Graph
 * Updates trigger H2/H3 dashboard panels when data becomes available
 *
 * Workflow Progression:
 * 1. Manifest upload → step='ingest', status='in-progress'
 * 2. Entity resolution complete → step='entity-resolution', status='complete'
 * 3. H1/H2/H3 scoring → step='scoring', scores accumulate
 * 4. Referral ready → step='referral', status='complete'
 */

export type WorkflowStep = 'ingest' | 'entity-resolution' | 'scoring' | 'referral'
export type WorkflowStatus = 'pending' | 'in-progress' | 'complete' | 'error'
export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'

export interface WorkflowState {
  // Ingest
  manifestId: string | null
  manifestData: ManifestIngestResponse | null
  manifestRows: any[]

  // Entity Resolution
  entities: Entity[] | null
  entitiesResolved: boolean

  // Scoring
  score: ScoreResponse | null
  scoringComplete: boolean

  // Referral
  referralPackage: ReferralPackage | null
  referralId: string | null

  // Loading states
  ingestLoading: boolean
  entitiesLoading: boolean
  scoringLoading: boolean
  referralLoading: boolean

  // Error states
  errors: { [key: string]: string | null }

  // Workflow progression (NEW)
  currentStep: WorkflowStep
  stepStatus: { [key in WorkflowStep]: WorkflowStatus }

  // Score accumulation (NEW)
  h1_score: number | null
  h2_score: number | null
  h3_score: number | null
  total_score: number | null
  risk_level: RiskLevel | null

  // Workflow error tracking
  workflowError: string | null
}

interface WorkflowContextValue {
  state: WorkflowState
  setState: (partial: Partial<WorkflowState>) => void
  reset: () => void

  // Workflow progression helpers (NEW)
  advanceStep: (step: WorkflowStep, status: WorkflowStatus) => void
  updateScore: (h1?: number, h2?: number, h3?: number) => void
  setWorkflowError: (error: string | null) => void
  getRiskLevel: (score: number) => RiskLevel
}

const defaultState: WorkflowState = {
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
  currentStep: 'ingest',
  stepStatus: {
    ingest: 'pending',
    'entity-resolution': 'pending',
    scoring: 'pending',
    referral: 'pending',
  },
  h1_score: null,
  h2_score: null,
  h3_score: null,
  total_score: null,
  risk_level: null,
  workflowError: null,
}

export const WorkflowContext = createContext<WorkflowContextValue>({
  state: defaultState,
  setState: () => {},
  reset: () => {},
  advanceStep: () => {},
  updateScore: () => {},
  setWorkflowError: () => {},
  getRiskLevel: () => 'LOW',
})

export const useWorkflow = () => {
  const context = useContext(WorkflowContext)
  if (!context) {
    throw new Error('useWorkflow must be used within WorkflowProvider')
  }
  return context
}

/**
 * Specialized hooks for workflow management
 */
export const useWorkflowState = () => {
  const { state } = useWorkflow()
  return state
}

export const useUpdateScore = () => {
  const { updateScore } = useWorkflow()
  return updateScore
}

export const useAdvanceStep = () => {
  const { advanceStep } = useWorkflow()
  return advanceStep
}

interface WorkflowProviderProps {
  children: ReactNode
}

export const WorkflowProvider: React.FC<WorkflowProviderProps> = ({ children }) => {
  const [state, setStateInternal] = useState<WorkflowState>(defaultState)

  const setState = (partial: Partial<WorkflowState>) => {
    setStateInternal((prev) => ({
      ...prev,
      ...partial,
    }))
  }

  const reset = () => {
    setStateInternal(defaultState)
  }

  /**
   * Determine risk level from total score
   * <30: LOW, 30-70: MEDIUM, >70: HIGH, >90: CRITICAL
   */
  const getRiskLevel = useCallback((score: number): RiskLevel => {
    if (score > 90) return 'CRITICAL'
    if (score > 70) return 'HIGH'
    if (score >= 30) return 'MEDIUM'
    return 'LOW'
  }, [])

  /**
   * Advance workflow to next step and update status
   */
  const advanceStep = useCallback((step: WorkflowStep, status: WorkflowStatus) => {
    setStateInternal((prev) => ({
      ...prev,
      currentStep: step,
      stepStatus: {
        ...prev.stepStatus,
        [step]: status,
      },
      workflowError: status === 'error' ? prev.workflowError : null,
    }))
  }, [])

  /**
   * Update individual scores and recalculate total
   * Scores are capped at their individual max (40 each max typical)
   * Total is capped at 100
   */
  const updateScore = useCallback((h1?: number, h2?: number, h3?: number) => {
    setStateInternal((prev) => {
      const newH1 = h1 !== undefined ? Math.max(0, Math.min(h1, 40)) : prev.h1_score
      const newH2 = h2 !== undefined ? Math.max(0, Math.min(h2, 40)) : prev.h2_score
      const newH3 = h3 !== undefined ? Math.max(0, Math.min(h3, 40)) : prev.h3_score

      // Calculate total only if all scores are present
      let newTotal: number | null = null
      if (newH1 !== null && newH2 !== null && newH3 !== null) {
        newTotal = Math.min(100, Math.round(newH1 + newH2 + newH3))
      }

      return {
        ...prev,
        h1_score: newH1,
        h2_score: newH2,
        h3_score: newH3,
        total_score: newTotal,
        risk_level: newTotal !== null ? getRiskLevel(newTotal) : null,
      }
    })
  }, [getRiskLevel])

  /**
   * Set workflow error and mark current step as error
   */
  const setWorkflowError = useCallback((error: string | null) => {
    setStateInternal((prev) => ({
      ...prev,
      workflowError: error,
      stepStatus: error
        ? {
            ...prev.stepStatus,
            [prev.currentStep]: 'error',
          }
        : prev.stepStatus,
    }))
  }, [])

  const value: WorkflowContextValue = {
    state,
    setState,
    reset,
    advanceStep,
    updateScore,
    setWorkflowError,
    getRiskLevel,
  }

  return (
    <WorkflowContext.Provider value={value}>
      {children}
    </WorkflowContext.Provider>
  )
}
