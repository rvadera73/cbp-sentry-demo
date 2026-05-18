/**
 * Sentry CBP TypeScript type definitions
 */

export interface ManifestMetadata {
  manifestId: string
  timestamp: string
  source: string
  recordCount: number
}

export interface ManifestIngestResponse {
  success: boolean
  manifestId: string
  recordCount: number
  status: 'pending' | 'processing' | 'complete' | 'error'
  message?: string
}

export interface ERRecord {
  recordId: number
  recordNumber: number
  rawData: Record<string, unknown>
}

export interface EntityResolutionResult {
  recordId: number
  entityType: string
  confidence: number
  resolvedData: Record<string, unknown>
}

export interface ERLoadResponse {
  success: boolean
  recordsProcessed: number
  entitiesResolved: number
  errors: string[]
}

export interface RiskScore {
  entityId: number
  riskScore: number
  threatScore: number
  riskLevel: 'low' | 'medium' | 'high' | 'critical'
  factors: string[]
}

export interface WhyResponse {
  success: boolean
  entityId: number
  riskScore: number
  riskLevel: string
  explanation: string
  factors: string[]
  recommendations: string[]
}

export interface ScoreResponse {
  success: boolean
  entityId: number
  riskScore: number
  threatScore: number
  riskLevel: 'low' | 'medium' | 'high' | 'critical'
  processed: number
  errors: string[]
}

export interface ReferralPackage {
  referralId: string
  entityId: number
  riskScore: number
  riskLevel: string
  recommendedAction: string
  packageData: Record<string, unknown>
  createdAt: string
}

export interface GraphNode {
  id: string
  label: string
  type: 'person' | 'organization' | 'location' | 'event'
  properties: Record<string, unknown>
}

export interface GraphEdge {
  source: string
  target: string
  type: string
  weight: number
}

export interface GraphPayload {
  nodes: GraphNode[]
  edges: GraphEdge[]
  metadata: Record<string, unknown>
}

export interface APIResponse<T> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

export interface HealthCheck {
  status: 'healthy' | 'unhealthy'
  environment: string
  debug: boolean
}
