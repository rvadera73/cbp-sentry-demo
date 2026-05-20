/**
 * Scoring Engine API Client
 * Calls three-level risk assessment backend
 */

interface ShipmentDataInput {
  shipment_id: string
  shipper_name: string
  consignee_name: string
  origin_country: string
  destination_country: string
  origin_port?: string
  destination_port?: string
  hs_code: string
  declared_value_usd: number
  declared_weight_kg: number
  vessel_name?: string
  dwell_days?: number
  declared_origin?: string
  ais_stuffing_country?: string
  port_calls?: string[]
  shipper_age_months?: number
  importer_age_months?: number
  importer_ytd_volume?: number
  senzing_confidence?: number
  entity_type?: string
  ofac_match?: boolean
  watchlist_match?: boolean
}

interface ScoringFactor {
  name: string
  contribution: number
  signal: string
  evidence: string[]
  status: 'high' | 'medium' | 'low' | 'neutral'
}

interface HorizonScoreData {
  horizon: 'H1' | 'H2' | 'H3'
  label: string
  score: number
  max_score: number
  weight: number
  factors: ScoringFactor[]
  summary: string
}

interface ScoringResponse {
  shipment_id: string
  h1: HorizonScoreData
  h2: HorizonScoreData
  h3: HorizonScoreData
  total_score: number
  confidence: 'HIGH' | 'MEDIUM' | 'LOW'
  should_verify_altana: boolean
  timestamp: string
}

interface FeedbackInput {
  shipment_id: string
  system_score: number
  human_label: number
  feedback_type: 'factory_expansion' | 'dual_origin' | 'misclassified_vessel'
  notes?: string
}

interface FeedbackResponse {
  shipment_id: string
  accepted: boolean
  weight_adjustment: Record<string, number>
  new_weights: Record<string, number>
  message: string
}

const API_BASE = '/api/scoring'

export const scoringApi = {
  /**
   * Calculate comprehensive risk score for a shipment
   */
  async calculateScore(shipment: ShipmentDataInput): Promise<ScoringResponse> {
    try {
      const response = await fetch(`${API_BASE}/score`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(shipment),
      })

      if (!response.ok) {
        throw new Error(`Scoring failed: ${response.statusText}`)
      }

      return await response.json()
    } catch (error) {
      console.error('Scoring API error:', error)
      throw error
    }
  },

  /**
   * Retrieve pre-calculated score for a shipment
   */
  async getScore(shipmentId: string): Promise<ScoringResponse> {
    try {
      const response = await fetch(`${API_BASE}/score/${shipmentId}`)

      if (!response.ok) {
        throw new Error(`Failed to fetch score: ${response.statusText}`)
      }

      return await response.json()
    } catch (error) {
      console.error('Score retrieval error:', error)
      throw error
    }
  },

  /**
   * Process human analyst feedback and update weights
   */
  async submitFeedback(feedback: FeedbackInput): Promise<FeedbackResponse> {
    try {
      const response = await fetch(`${API_BASE}/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(feedback),
      })

      if (!response.ok) {
        throw new Error(`Feedback submission failed: ${response.statusText}`)
      }

      return await response.json()
    } catch (error) {
      console.error('Feedback API error:', error)
      throw error
    }
  },

  /**
   * Get current dynamic weights and adjustment history
   */
  async getWeights() {
    try {
      const response = await fetch(`${API_BASE}/weights`)

      if (!response.ok) {
        throw new Error(`Failed to fetch weights: ${response.statusText}`)
      }

      return await response.json()
    } catch (error) {
      console.error('Weights retrieval error:', error)
      throw error
    }
  },

  /**
   * Trigger Altana verification for high-risk shipments
   */
  async verifyWithAltana(shipmentId: string) {
    try {
      const response = await fetch(`${API_BASE}/altana/verify/${shipmentId}`, {
        method: 'POST',
      })

      if (!response.ok) {
        throw new Error(`Altana verification failed: ${response.statusText}`)
      }

      return await response.json()
    } catch (error) {
      console.error('Altana verification error:', error)
      throw error
    }
  },

  /**
   * Health check for scoring service
   */
  async healthCheck() {
    try {
      const response = await fetch(`${API_BASE}/health`)

      if (!response.ok) {
        throw new Error('Service health check failed')
      }

      return await response.json()
    } catch (error) {
      console.error('Health check error:', error)
      throw error
    }
  },
}

export type {
  ShipmentDataInput,
  ScoringResponse,
  ScoringFactor,
  HorizonScoreData,
  FeedbackInput,
  FeedbackResponse,
}
