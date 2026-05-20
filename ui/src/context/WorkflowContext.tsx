import React, { createContext, useContext, useState, ReactNode } from 'react'
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
 */

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
}

interface WorkflowContextValue {
  state: WorkflowState
  setState: (partial: Partial<WorkflowState>) => void
  reset: () => void
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
}

export const WorkflowContext = createContext<WorkflowContextValue>({
  state: defaultState,
  setState: () => {},
  reset: () => {},
})

export const useWorkflow = () => {
  const context = useContext(WorkflowContext)
  if (!context) {
    throw new Error('useWorkflow must be used within WorkflowProvider')
  }
  return context
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

  return (
    <WorkflowContext.Provider value={{ state, setState, reset }}>
      {children}
    </WorkflowContext.Provider>
  )
}
