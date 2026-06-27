/**
 * Risk Model API Service
 * Handles all MLOps lifecycle actions and data fetching
 */

export interface ApprovalAction {
  approval_id: string
  voter_name: string
  vote: 'approve' | 'reject'
  comment?: string
}

export interface ModelPromoteAction {
  model_id: string
  from_stage: string
  to_stage: string
}

export interface ModelRollbackAction {
  model_id: string
  to_version: string
}

export class RiskModelApi {
  private baseUrl = '/api/risk-models'

  /**
   * Fetch dashboard data (active model, metrics, alerts)
   */
  async getDashboard() {
    const res = await fetch(`${this.baseUrl}/dashboard`)
    if (!res.ok) throw new Error('Failed to fetch dashboard')
    return res.json()
  }

  /**
   * Fetch all model versions
   */
  async getVersions() {
    const res = await fetch(`${this.baseUrl}/versions`)
    if (!res.ok) throw new Error('Failed to fetch versions')
    return res.json()
  }

  /**
   * Get current gate status
   */
  async getCurrentGate() {
    const res = await fetch(`${this.baseUrl}/performance/current-gate`)
    if (!res.ok) throw new Error('Failed to fetch gate status')
    return res.json()
  }

  /**
   * Get model metrics
   */
  async getModelMetrics(modelId: string) {
    const res = await fetch(`${this.baseUrl}/${modelId}/metrics`)
    if (!res.ok) throw new Error(`Failed to fetch metrics for ${modelId}`)
    return res.json()
  }

  /**
   * Get all pending approvals
   */
  async getPendingApprovals() {
    const res = await fetch(`${this.baseUrl}/approvals`)
    if (!res.ok) throw new Error('Failed to fetch approvals')
    return res.json()
  }

  /**
   * Submit an approval vote
   */
  async submitApprovalVote(approvalId: string, action: ApprovalAction) {
    const res = await fetch(`${this.baseUrl}/approvals/${approvalId}/vote`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(action),
    })
    if (!res.ok) throw new Error('Failed to submit approval vote')
    return res.json()
  }

  /**
   * Promote model from staging to production
   */
  async promoteModel(modelId: string, action: ModelPromoteAction) {
    const res = await fetch(`${this.baseUrl}/${modelId}/promote`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(action),
    })
    if (!res.ok) throw new Error('Failed to promote model')
    return res.json()
  }

  /**
   * Rollback to a previous model version
   */
  async rollbackModel(modelId: string, action: ModelRollbackAction) {
    const res = await fetch(`${this.baseUrl}/${modelId}/rollback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(action),
    })
    if (!res.ok) throw new Error('Failed to rollback model')
    return res.json()
  }

  /**
   * Deploy model to shadow mode for testing
   */
  async shadowDeploy(modelId: string) {
    const res = await fetch(`${this.baseUrl}/${modelId}/shadow-deploy`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })
    if (!res.ok) throw new Error('Failed to shadow deploy')
    return res.json()
  }

  /**
   * Deprecate a model version
   */
  async deprecateModel(modelId: string) {
    const res = await fetch(`${this.baseUrl}/${modelId}/deprecate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })
    if (!res.ok) throw new Error('Failed to deprecate model')
    return res.json()
  }

  /**
   * Get data drift detection results
   */
  async getDriftDetection() {
    const res = await fetch(`${this.baseUrl}/drift`)
    if (!res.ok) throw new Error('Failed to fetch drift detection')
    return res.json()
  }

  /**
   * Get training job history
   */
  async getTrainingJobs() {
    const res = await fetch(`${this.baseUrl}/training-jobs`)
    if (!res.ok) throw new Error('Failed to fetch training jobs')
    return res.json()
  }

  /**
   * Get retraining configuration
   */
  async getRetrainingConfig() {
    const res = await fetch(`${this.baseUrl}/retraining-config`)
    if (!res.ok) throw new Error('Failed to fetch retraining config')
    return res.json()
  }
}

// Export singleton instance
export const riskModelApi = new RiskModelApi()
