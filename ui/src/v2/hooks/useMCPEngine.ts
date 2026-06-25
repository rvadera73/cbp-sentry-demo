/**
 * useMCPEngine — hooks for the cbp-risk-engine MLOps MCP service.
 * All requests go through /api/mcp/ → nginx → cbp-risk-engine:8010
 */
import { useState, useEffect, useCallback } from 'react'

const MCP_BASE = '/api/mcp'

// ─── Generic fetcher ─────────────────────────────────────────────────────────

async function mcpFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${MCP_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.text().catch(() => res.statusText)
    throw new Error(`MCP ${path}: ${res.status} ${err}`)
  }
  return res.json() as Promise<T>
}

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ModelVersion {
  version_id: string
  model_name: string
  status: 'production' | 'staging' | 'archived' | 'pending_review'
  created_at: string
  deployed_at?: string
  maturity_level: number
  metrics: {
    auc_roc: number
    precision: number
    recall: number
    f1: number
    accuracy: number
  }
  approval_votes: Array<{
    voter_id: string
    vote: 'approve' | 'reject' | 'pending'
    comment?: string
    voted_at?: string
  }>
  training_data_summary?: string
}

export interface PerformanceSnapshot {
  timestamp: string
  accuracy: number
  auc_roc: number
  precision: number
  recall: number
  latency_p95_ms: number
  predictions_count: number
}

export interface GateStatus {
  gate: string
  label: string
  threshold: number
  current: number
  passed: boolean
  description: string
}

export interface DriftFeature {
  name: string
  drift_score: number
  status: 'elevated' | 'normal'
  drift_type: string
  recommendation?: string
}

export interface TrainingJob {
  job_id: string
  model_type: string
  status: 'completed' | 'in_progress' | 'failed' | 'queued'
  started_at: string
  completed_at?: string
  notes?: string
  metrics?: {
    training_accuracy: number
    test_accuracy: number
    auc_roc: number
  }
  error?: string
}

export interface ShapExplanation {
  shipment_id: string
  final_score: number
  risk_level: string
  shap_values: Array<{
    feature: string
    value: string | number
    contribution: number
    direction: 'up' | 'down'
  }>
  scoring_method: string
  model_version?: string
}

// ─── Model Versions ───────────────────────────────────────────────────────────

export function useModelVersions() {
  const [versions, setVersions] = useState<ModelVersion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await mcpFetch<{ versions: ModelVersion[] }>('/models')
      setVersions(data.versions ?? [])
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  const approveModel = useCallback(
    async (versionId: string, voterId: string, vote: 'approve' | 'reject', comment?: string) => {
      const result = await mcpFetch(`/models/${versionId}/approve`, {
        method: 'POST',
        body: JSON.stringify({ voter_id: voterId, vote, comment }),
      })
      await refresh()
      return result
    },
    [refresh],
  )

  const promoteModel = useCallback(
    async (versionId: string) => {
      const result = await mcpFetch(`/models/${versionId}/promote`, {
        method: 'POST',
        body: JSON.stringify({ requested_by: 'officer' }),
      })
      await refresh()
      return result
    },
    [refresh],
  )

  return { versions, loading, error, refresh, approveModel, promoteModel }
}

// ─── Performance Metrics ─────────────────────────────────────────────────────

export function usePerformanceMetrics() {
  const [performance, setPerformance] = useState<Record<string, unknown> | null>(null)
  const [gates, setGates] = useState<GateStatus[]>([])
  const [history, setHistory] = useState<PerformanceSnapshot[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const [perf, gateData, hist] = await Promise.all([
          mcpFetch<Record<string, unknown>>('/metrics/performance'),
          mcpFetch<{ gates: GateStatus[] }>('/metrics/gates'),
          mcpFetch<{ history: PerformanceSnapshot[] }>('/metrics/history?limit=30'),
        ])
        setPerformance(perf)
        setGates(gateData.gates ?? [])
        setHistory(hist.history ?? [])
      } catch (e) {
        setError((e as Error).message)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  return { performance, gates, history, loading, error }
}

// ─── Data Drift ───────────────────────────────────────────────────────────────

export function useDataDrift() {
  const [drift, setDrift] = useState<DriftFeature[]>([])
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    mcpFetch<{ features: DriftFeature[]; summary: Record<string, unknown> }>('/metrics/drift')
      .then(d => {
        setDrift(d.features ?? [])
        setSummary(d.summary ?? null)
      })
      .catch(e => setError((e as Error).message))
      .finally(() => setLoading(false))
  }, [])

  return { drift, summary, loading, error }
}

// ─── Training History ─────────────────────────────────────────────────────────

export function useTrainingHistory() {
  const [jobs, setJobs] = useState<TrainingJob[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const data = await mcpFetch<{ jobs: TrainingJob[] }>('/jobs')
      setJobs(data.jobs ?? [])
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  const triggerTraining = useCallback(
    async (modelType: 'xgboost' | 'isolation_forest' | 'all' = 'all', notes?: string) => {
      const result = await mcpFetch('/train', {
        method: 'POST',
        body: JSON.stringify({ model_type: modelType, notes }),
      })
      await refresh()
      return result
    },
    [refresh],
  )

  return { jobs, loading, error, refresh, triggerTraining }
}

// ─── SHAP Explanations ────────────────────────────────────────────────────────

export function useShapExplanation(shipmentId: string | null) {
  const [explanation, setExplanation] = useState<ShapExplanation | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const explain = useCallback(async (id: string, shipmentData?: Record<string, unknown>) => {
    setLoading(true)
    setError(null)
    try {
      const result = await mcpFetch<ShapExplanation>(`/features/explain/${id}`, {
        method: 'POST',
        body: JSON.stringify(shipmentData ?? {}),
      })
      setExplanation(result)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (shipmentId) explain(shipmentId)
  }, [shipmentId, explain])

  return { explanation, loading, error, explain }
}

// ─── Dashboard Summary ────────────────────────────────────────────────────────

export function useMCPDashboard() {
  const [activeModel, setActiveModel] = useState<ModelVersion | null>(null)
  const [gates, setGates] = useState<GateStatus[]>([])
  const [recentJob, setRecentJob] = useState<TrainingJob | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const [model, gateData, jobData] = await Promise.all([
          mcpFetch<ModelVersion>('/models/production').catch(() => null),
          mcpFetch<{ gates: GateStatus[] }>('/metrics/gates'),
          mcpFetch<{ jobs: TrainingJob[] }>('/jobs'),
        ])
        setActiveModel(model)
        setGates(gateData.gates ?? [])
        const jobs = jobData.jobs ?? []
        setRecentJob(jobs[0] ?? null)
      } catch (e) {
        setError((e as Error).message)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  return { activeModel, gates, recentJob, loading, error }
}
