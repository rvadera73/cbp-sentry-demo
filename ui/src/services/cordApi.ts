/**
 * CORD RAG API Client
 *
 * Interfaces with the search-first CORD integration backend:
 * - POST /api/cord/investigate-shipment - Search-first CORD investigation
 * - POST /api/cord/investigate - Entity-based investigation
 * - GET /api/cord/status - CORD data status
 * - POST /api/cord/download - Download CORD dataset
 */

const API_BASE_URL = ((import.meta as any).env?.VITE_API_BASE_URL as string | undefined) || 'http://localhost:8000/api';

// Request/Response Models

export interface SearchFirstInvestigateRequest {
  manifest_id: string;
  shipper_name: string;
  shipper_country: string;
  consignee_name: string;
  consignee_country: string;
  declared_origin?: string;
  manufacturer_inferred?: string;
  base_score?: number;
}

export interface EntityNode {
  id?: string;
  name: string;
  country: string;
  confidence?: number;
  role?: 'shipper' | 'consignee' | 'manufacturer' | 'holding_company' | 'freight_forwarder';
  jurisdiction?: string;
  sources?: string[];
}

export interface RelationshipEdge {
  type: string; // 'OWNED_BY', 'DIRECTOR_SHARED', 'SHIPS_VIA', etc.
  confidence?: number;
  evidence?: string[];
}

export interface EntityChain {
  primary?: EntityNode;
  query?: { name: string; country: string };
  entities: EntityNode[];
  relationships: RelationshipEdge[];
}

export interface RiskFlag {
  type: string; // 'OFAC_MATCH', 'AD_CVD_CASE', 'SANCTIONS', 'TRANSSHIPMENT', 'OFAC_ADJACENT'
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  entity?: string;
  detail: string;
  source?: string;
}

export interface ScoringBreakdown {
  base_score: number;
  risk_points: number;
  chain_points: number;
  total_score: number;
  level: 'LOW' | 'MEDIUM' | 'HIGH';
  confidence: number;
}

export interface EvalSafety {
  sdk_enabled: boolean;
  entities_loaded: number;
  eval_limit: number;
  percent_used: number;
  status: 'safe' | 'warning' | 'critical';
}

export interface SearchFirstInvestigateResponse {
  manifest_id: string;
  status: 'success' | 'error' | 'partial';
  error_reason?: string; // Why entity chains weren't found
  investigation: {
    manifest_entities: EntityNode[];
    cord_search_results: number;
    cord_records_found: number;
    cord_subset_loaded: number;
    entity_chains: EntityChain[];
    risk_flags: RiskFlag[];
  };
  scoring: ScoringBreakdown;
  sources: string[];
  eval_safety: EvalSafety;
  timestamp: string;
  debug?: {
    search_queries_attempted?: string[];
    no_matches_found_for?: string[];
    low_confidence_matches?: Array<{ entity: string; confidence: number }>;
  };
}

export interface CORDStatusResponse {
  status: string;
  london_loaded: boolean;
  moscow_loaded: boolean;
  records_total: number;
  last_updated?: string;
}

export interface InvestigateRequest {
  entity_name: string;
  country?: string;
  depth?: number;
}

export interface InvestigateResponse {
  status: string;
  primary_entity?: Record<string, any>;
  entity_chain: EntityChain[];
  beneficial_owners: Array<{ name: string; source?: string }>;
  risk_flags: RiskFlag[];
  explanation: string;
  confidence: number;
  sources: string[];
}

// CORD API Client

class CORDApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Investigate shipment manifest using search-first CORD approach.
   *
   * Flow:
   * 1. Extract entities from manifest
   * 2. Search FULL CORD via REST (unlimited)
   * 3. Extract relevant subset (~20 entities)
   * 4. Load to Senzing SDK (<100K eval limit)
   * 5. Resolve entity chains
   * 6. Flag risks
   * 7. Calculate score
   *
   * @param request - Manifest data for investigation
   * @returns Investigation result with entity chains, risks, and score
   */
  async investigateShipment(
    request: SearchFirstInvestigateRequest
  ): Promise<SearchFirstInvestigateResponse> {
    const response = await fetch(
      `${this.baseUrl}/cord/investigate-shipment`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      }
    );

    if (!response.ok) {
      throw new Error(
        `CORD investigation failed: ${response.status} ${response.statusText}`
      );
    }

    return response.json();
  }

  /**
   * Investigate entity using CORD RAG.
   *
   * Searches CORD for the entity and traces relationships.
   *
   * @param request - Entity name and optional country
   * @returns Investigation result with entity chain and risks
   */
  async investigateEntity(
    request: InvestigateRequest
  ): Promise<InvestigateResponse> {
    const response = await fetch(`${this.baseUrl}/cord/investigate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(
        `Entity investigation failed: ${response.status} ${response.statusText}`
      );
    }

    return response.json();
  }

  /**
   * Check if two entities are connected in CORD.
   *
   * @param entityA - First entity name
   * @param entityB - Second entity name
   * @param maxHops - Maximum hops to trace (default: 3)
   * @returns Connection status and path details
   */
  async isConnected(
    entityA: string,
    entityB: string,
    maxHops: number = 3
  ): Promise<{
    connected: boolean;
    details: {
      path?: EntityNode[];
      hops?: number;
      connection_type?: string;
      evidence?: string[];
    };
  }> {
    const response = await fetch(`${this.baseUrl}/cord/is-connected`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        entity_a: entityA,
        entity_b: entityB,
        max_hops: maxHops,
      }),
    });

    if (!response.ok) {
      throw new Error(
        `Connection check failed: ${response.status} ${response.statusText}`
      );
    }

    return response.json();
  }

  /**
   * Get CORD data status.
   *
   * @returns Status of loaded CORD collections
   */
  async getStatus(): Promise<CORDStatusResponse> {
    const response = await fetch(`${this.baseUrl}/cord/status`);

    if (!response.ok) {
      throw new Error(
        `Status check failed: ${response.status} ${response.statusText}`
      );
    }

    return response.json();
  }

  /**
   * Download CORD dataset.
   *
   * @param location - CORD location: london, moscow, las_vegas
   * @param autoLoad - Automatically load into Senzing after download
   * @returns Download status and file info
   */
  async downloadCORD(
    location: string = 'london',
    autoLoad: boolean = false
  ): Promise<{
    status: string;
    location: string;
    file: string;
    auto_load: boolean;
    load?: {
      location: string;
      loaded: number;
      errors: number;
    };
  }> {
    const params = new URLSearchParams({
      location,
      auto_load: autoLoad.toString(),
    });

    const response = await fetch(
      `${this.baseUrl}/cord/download?${params}`,
      {
        method: 'POST',
      }
    );

    if (!response.ok) {
      throw new Error(
        `Download failed: ${response.status} ${response.statusText}`
      );
    }

    return response.json();
  }

  /**
   * List available CORD collections.
   *
   * @returns Available CORD locations
   */
  async listAvailableCORDs(): Promise<{
    locations: Array<{
      name: string;
      records: number;
      description: string;
    }>;
  }> {
    const response = await fetch(
      `${this.baseUrl}/cord/available-locations`
    );

    if (!response.ok) {
      throw new Error(
        `List failed: ${response.status} ${response.statusText}`
      );
    }

    return response.json();
  }
}

// Export singleton instance
export const cordApi = new CORDApiClient();

// Export class for testing
export default CORDApiClient;
