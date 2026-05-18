/**
 * API client for Sentry CBP backend
 */
import axios, { AxiosInstance, AxiosError } from 'axios'

const API_BASE_URL = '/api'

class APIClient {
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
      // TODO: Add API key if needed
      return config
    })

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        console.error('API Error:', error.response?.data || error.message)
        return Promise.reject(error)
      }
    )
  }

  // Health check
  async health() {
    return this.client.get('/health')
  }

  // Ingest endpoints (TBD)
  async ingestManifest(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    return this.client.post('/ingest/manifest', formData)
  }

  // Entity resolution endpoints (TBD)
  async resolveEntities() {
    return this.client.post('/entity-resolution/load')
  }

  // Scoring endpoints (TBD)
  async scoreEntity(entityId: number) {
    return this.client.get(`/scoring/score?entity_id=${entityId}`)
  }

  async explainScore(entityId: number) {
    return this.client.get(`/scoring/why?entity_id=${entityId}`)
  }

  // Graph endpoints (TBD)
  async buildGraph() {
    return this.client.post('/graph/build')
  }
}

export const api = new APIClient()
