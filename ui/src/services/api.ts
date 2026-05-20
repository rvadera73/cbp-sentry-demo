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

// For Cloud Run, use public service URL; for local dev, use localhost
const API_BASE_URL = ((import.meta as any).env?.VITE_API_BASE_URL as string | undefined) ||
  (typeof window !== 'undefined' && window.location.hostname === 'localhost'
    ? 'http://localhost:8000/api'
    : 'https://sentry-api-cbp-sentry.run.app/api')

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
}

export const api = new SentryAPI()
export { API_BASE_URL }
