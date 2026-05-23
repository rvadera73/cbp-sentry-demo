/**
 * API client for Sentry CBP backend — typed methods for all 8 endpoints
 */
import axios, { AxiosInstance, AxiosError } from 'axios'
import type {
  ManifestIngestResponse,
  ERLoadResponse,
  WhyResponse,
  ScoreResponse,
  ReferralPackage,
  GraphPayload,
  H1Response,
  H2Response,
} from '../types/sentry'

// Auto-detect API URL based on deployment environment
const getAPIBaseURL = (): string => {
  if (typeof window === 'undefined') return '/api'

  const hostname = window.location.hostname

  // Local development: localhost:3000 or localhost:3001
  // Nginx proxy at /api routes to http://sentry-api:8000
  if (hostname === 'localhost' || hostname.startsWith('localhost:')) {
    return '/api'
  }

  // Cloud Run: sentry-ui-{HASH}.{REGION}.run.app
  // Extract hash and construct sentry-api URL with same hash
  const cloudRunMatch = hostname.match(/^sentry-ui-(\d+)\.(.+?)\.run\.app$/)
  if (cloudRunMatch) {
    const [, hash, region] = cloudRunMatch
    return `https://sentry-api-${hash}.${region}.run.app/api`
  }

  // Fallback to relative paths (works with nginx proxy)
  return '/api'
}

const API_BASE_URL = getAPIBaseURL()

class SentryAPI {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Request interceptor
    this.client.interceptors.request.use((config) => {
      // TODO: Add auth token if available
      return config
    })

    // Response interceptor for error logging
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        console.error('API Error:', {
          status: error.response?.status,
          data: error.response?.data,
          message: error.message,
        })
        return Promise.reject(error)
      }
    )
  }

  // Health check
  async health() {
    try {
      const response = await this.client.get('/health')
      return response.data
    } catch (error) {
      console.error('Health check failed:', error)
      return null
    }
  }

  /**
   * 1. Ingest Manifest — POST /api/ingest/manifest
   * Uploads Excel file, parses, returns manifest_id + extracted fields
   */
  async ingestManifest(file: File): Promise<ManifestIngestResponse | null> {
    try {
      const formData = new FormData()
      formData.append('file', file)
      const response = await this.client.post<ManifestIngestResponse>(
        '/ingest/manifest',
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      )
      return response.data
    } catch (error) {
      console.error('Error ingesting manifest:', error)
      return null
    }
  }

  /**
   * 2. Resolve Entities — POST /api/er/load
   * Trigger Senzing entity resolution for a shipment
   */
  async resolveEntities(shipmentId: string): Promise<ERLoadResponse | null> {
    try {
      const response = await this.client.post<ERLoadResponse>('/er/load', {
        shipment_id: shipmentId,
      })
      return response.data
    } catch (error) {
      console.error('Error resolving entities:', error)
      return null
    }
  }

  /**
   * 3. Why Connected — GET /api/er/why/{entity_a}/{entity_b}
   * Explain the connection between two entities (Senzing path + evidence)
   */
  async getEntityWhy(entityA: number, entityB: number, shipmentId?: string): Promise<WhyResponse | null> {
    try {
      const url = `/er/why/${entityA}/${entityB}`
      const params = shipmentId ? { shipment_id: shipmentId } : {}
      const response = await this.client.get<WhyResponse>(url, { params })
      return response.data
    } catch (error) {
      console.error('Error fetching entity why:', error)
      return null
    }
  }

  /**
   * 4. Score Shipment — POST /api/score/{shipment_id}
   * Run 4-tier ML scoring pipeline, returns components + XAI assertions
   */
  async scoreShipment(shipmentId: string): Promise<ScoreResponse | null> {
    try {
      const response = await this.client.post<ScoreResponse>(`/score/${shipmentId}`, {
        force_rescore: false,
      })
      return response.data
    } catch (error) {
      console.error('Error scoring shipment:', error)
      return null
    }
  }

  /**
   * 5. Get Referral Package — GET /api/referral/{shipment_id}
   * Retrieve full 14-section referral package (CBP enforcement document)
   */
  async getReferralPackage(shipmentId: string): Promise<ReferralPackage | null> {
    try {
      const response = await this.client.get<ReferralPackage>(`/referral/${shipmentId}`, {
        params: { format: 'json' },
      })
      return response.data
    } catch (error) {
      console.error('Error fetching referral package:', error)
      return null
    }
  }

  /**
   * 6. Get Shipment Graph — GET /api/graph/shipment/{shipment_id}
   * Return Neo4j entity relationship graph (nodes + edges) for visualization
   */
  async getShipmentGraph(shipmentId: string): Promise<GraphPayload | null> {
    try {
      const response = await this.client.get<GraphPayload>(`/graph/shipment/${shipmentId}`)
      return response.data
    } catch (error) {
      console.error('Error fetching shipment graph:', error)
      return null
    }
  }

  /**
   * 7. Horizon H1 — GET /api/horizons/h1
   * Corridor-level risk (tariff + trade pattern anomalies)
   */
  async getHorizonH1(origin: string, destination: string, hts: string): Promise<H1Response | null> {
    try {
      const response = await this.client.get<H1Response>('/horizons/h1', {
        params: { origin, destination, hts },
      })
      return response.data
    } catch (error) {
      console.error('Error fetching Horizon H1:', error)
      return null
    }
  }

  /**
   * 8. Horizon H2 — GET /api/horizons/h2/{shipment_id}
   * Pre-manifest intelligence (ISF contradiction, AIS dwell anomalies)
   */
  async getHorizonH2(shipmentId: string): Promise<H2Response | null> {
    try {
      const response = await this.client.get<H2Response>(`/horizons/h2/${shipmentId}`)
      return response.data
    } catch (error) {
      console.error('Error fetching Horizon H2:', error)
      return null
    }
  }

  /**
   * Get all shipments with pagination — GET /api/shipments
   */
  async getShipments(limit: number = 15, offset: number = 0): Promise<any> {
    try {
      const response = await this.client.get('/shipments', {
        params: { limit, offset },
      })
      return response.data
    } catch (error) {
      console.error('Error fetching shipments:', error)
      return { shipments: [] }
    }
  }

  /**
   * Get single shipment by ID — GET /api/shipments/{id}
   */
  async getShipment(shipmentId: number): Promise<any> {
    try {
      const response = await this.client.get(`/shipments/${shipmentId}`)
      return response.data
    } catch (error) {
      console.error('Error fetching shipment:', error)
      return null
    }
  }

  /**
   * Search shipments with filters — GET /api/shipments/search
   */
  async searchShipments(filters: {
    origin?: string
    destination?: string
    risk_min?: number
    risk_max?: number
    status?: string
    limit?: number
  }): Promise<any> {
    try {
      const response = await this.client.get('/shipments/search', {
        params: filters,
      })
      return response.data
    } catch (error) {
      console.error('Error searching shipments:', error)
      return []
    }
  }

  /**
   * Get shipment map data — GET /api/shipments/map/data
   */
  async getShipmentsMapData(): Promise<any> {
    try {
      const response = await this.client.get('/shipments/map/data')
      return response.data
    } catch (error) {
      console.error('Error fetching map data:', error)
      return { routes: [] }
    }
  }

  /**
   * Get shipment statistics — GET /api/shipments/stats
   */
  async getShipmentsStats(): Promise<any> {
    try {
      const response = await this.client.get('/shipments/stats')
      return response.data
    } catch (error) {
      console.error('Error fetching shipment stats:', error)
      return { total: 0, highRisk: 0, mediumRisk: 0, lowRisk: 0 }
    }
  }

  // ============== COMMAND CENTER / RISK CORRIDORS ==============

  /**
   * Get risk corridors with optional filters — GET /api/risk-corridors
   * Supervisor view: industry-level risk analysis
   */
  async getRiskCorridors(filters?: { industry_filter?: string; time_period?: string }): Promise<any> {
    try {
      const params: any = {}
      if (filters?.industry_filter) params.industry_filter = filters.industry_filter
      if (filters?.time_period) params.time_period = filters.time_period

      const response = await this.client.get('/risk-corridors', { params })
      return response.data
    } catch (error) {
      console.error('Error fetching risk corridors:', error)
      return { corridors: [] }
    }
  }

  /**
   * Get vessels of interest for a specific port — GET /api/ports/{port}/vessels-of-interest
   * Field officer view: vessel tracking at specific ports
   */
  async getVesselsOfInterest(port: string, timeWindow: string = '30d'): Promise<any> {
    try {
      const response = await this.client.get(`/ports/${port}/vessels-of-interest`, {
        params: { time_window: timeWindow },
      })
      return response.data
    } catch (error) {
      console.error('Error fetching vessels of interest:', error)
      return { vessels: [] }
    }
  }

  /**
   * Get timeline of signal events for a risk corridor — GET /api/risk-corridors/{id}/timeline
   * Analyst view: network behavior evolution over time
   */
  async getRiskCorridorTimeline(corridorId: string, startDate?: string, endDate?: string): Promise<any> {
    try {
      const params: any = {}
      if (startDate) params.start_date = startDate
      if (endDate) params.end_date = endDate

      const response = await this.client.get(`/risk-corridors/${corridorId}/timeline`, { params })
      return response.data
    } catch (error) {
      console.error('Error fetching risk corridor timeline:', error)
      return { events: [] }
    }
  }

  /**
   * Generate EAPA referral package — POST /api/referral/generate
   * Generate formal CBP EAPA referral package for investigation
   */
  async generateReferral(corridorId?: string, vesselId?: string, manifestIds?: string[]): Promise<any> {
    try {
      const response = await this.client.post('/referral/generate', {
        corridor_id: corridorId,
        vessel_id: vesselId,
        manifest_ids: manifestIds,
      })
      return response.data
    } catch (error) {
      console.error('Error generating referral:', error)
      return { status: 'error', referral_id: null }
    }
  }

  /**
   * Issue hold for vessel examination — POST /api/vessel/hold
   * Issue hold on vessel for physical examination on arrival
   */
  async issueVesselHold(vesselImo: string, examinationType: string = 'FULL', reason?: string): Promise<any> {
    try {
      const response = await this.client.post('/vessel/hold', {
        vessel_imo: vesselImo,
        examination_type: examinationType,
        reason,
      })
      return response.data
    } catch (error) {
      console.error('Error issuing vessel hold:', error)
      return { status: 'error', hold_id: null }
    }
  }

  /**
   * Log feedback override for model training — POST /api/feedback/override
   * Log human feedback override for model training
   */
  async logFeedbackOverride(feedbackType: string, notes: string, manifestId?: string, shipmentId?: string): Promise<any> {
    try {
      const response = await this.client.post('/feedback/override', {
        feedback_type: feedbackType,
        notes,
        manifest_id: manifestId,
        shipment_id: shipmentId,
      })
      return response.data
    } catch (error) {
      console.error('Error logging feedback:', error)
      return { status: 'error', feedback_id: null }
    }
  }

  /**
   * Generate AI case synopsis — POST /api/gemini/synopsis
   */
  async generateSynopsis(payload: any): Promise<any> {
    try {
      const response = await this.client.post('/gemini/synopsis', payload)
      return response.data
    } catch (error) {
      console.error('Error generating synopsis:', error)
      return { synopsis: 'Unable to generate synopsis' }
    }
  }

  /**
   * Generate draft referral narrative — POST /api/gemini/draft-referral
   */
  async generateDraftReferral(payload: any): Promise<any> {
    try {
      const response = await this.client.post('/gemini/draft-referral', payload)
      return response.data
    } catch (error) {
      console.error('Error generating draft referral:', error)
      return { narrative: 'Unable to generate narrative' }
    }
  }

  // ============== CORD ENTITY RESOLUTION ==============

  /**
   * Search CORD index for entities by name
   * GET /api/cord/search?name={name}&country={country}&limit={limit}
   */
  async cordSearch(name: string, country?: string, limit: number = 10): Promise<any> {
    try {
      const params: any = { name, limit }
      if (country) params.country = country
      const response = await this.client.get('/cord/search', { params })
      return response.data
    } catch (error) {
      console.error('CORD search error:', error)
      return { status: 'error', matches: [] }
    }
  }

  /**
   * Resolve 3-level entity chain for shipper with OFAC detection
   * POST /api/cord/resolve?shipper_name={name}&shipper_country={country}&consignee_name={consignee}&consignee_country={cc}
   */
  async cordResolveChain(shipper_name: string, shipper_country?: string, consignee_name?: string, consignee_country?: string): Promise<any> {
    try {
      const params: any = { shipper_name }
      if (shipper_country) params.shipper_country = shipper_country
      if (consignee_name) params.consignee_name = consignee_name
      if (consignee_country) params.consignee_country = consignee_country

      const response = await this.client.post('/cord/resolve', {}, { params })
      return response.data
    } catch (error) {
      console.error('CORD resolve error:', error)
      return { status: 'error', resolution: null }
    }
  }

  /**
   * Get full entity details from CORD
   * GET /api/cord/entity/{entity_id}
   */
  async cordGetEntity(entity_id: string): Promise<any> {
    try {
      const response = await this.client.get(`/cord/entity/${entity_id}`)
      return response.data
    } catch (error) {
      console.error('CORD get entity error:', error)
      return { status: 'error', entity: null }
    }
  }

  /**
   * Get relationship explanation between two entities
   * GET /api/cord/why/{id_a}/{id_b}
   */
  async cordWhyLinked(entity_id_a: string, entity_id_b: string): Promise<any> {
    try {
      const response = await this.client.get(`/cord/why/${entity_id_a}/${entity_id_b}`)
      return response.data
    } catch (error) {
      console.error('CORD why linked error:', error)
      return { status: 'error', explanation: null }
    }
  }
}

export const api = new SentryAPI()
export { API_BASE_URL }
