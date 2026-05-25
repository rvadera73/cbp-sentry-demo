import { useState, useEffect } from 'react';
import { API_BASE_URL } from '../../services/apiUrl';

interface CorridorStats {
  shipment_count: number;
  avg_risk_score: number;
  element9_mismatch_rate_pct: number;
  avg_shipper_age_months: number;
  unique_shippers: number;
}

interface Duty {
  id: number;
  corridor_id: string;
  case_number: string;
  duty_type: string;
  product_description: string;
  hs_prefix: string;
  rate_pct: number;
  status: string;
  source_url: string;
  last_refreshed_at: string;
}

interface EnforcementAction {
  id: number;
  corridor_id: string;
  case_id: string;
  entity_name: string;
  case_status: string;
  case_year: number;
  duty_evaded_usd: number;
  source_description: string;
  source_url: string;
  last_refreshed_at: string;
}

interface CorridorDetail {
  id: string;
  display_name: string;
  origin_country: string;
  destination_country: string;
  risk_level: string;
  primary_hs_chapters: string;
  risk_profile: string;
  computed_stats?: CorridorStats;
  duties?: Duty[];
  enforcement_actions?: EnforcementAction[];
  pattern_indicators?: CorridorStats;
}

export interface CorridorIntelligence {
  corridors: CorridorDetail[];
  count: number;
  timestamp: string;
  isLoading: boolean;
  error: string | null;
}

/**
 * Fetches corridor definitions, duties, and enforcement actions from the API
 * Returns computed statistics from the shipments table
 */
export function useCorridorIntelligence(): CorridorIntelligence {
  const [corridors, setCorridors] = useState<CorridorDetail[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchCorridors = async () => {
      try {
        setIsLoading(true);
        const response = await fetch(`${API_BASE_URL}/corridors`);
        if (!response.ok) {
          throw new Error(`Failed to fetch corridors: ${response.statusText}`);
        }
        const data = await response.json();
        setCorridors(data.data || []);
        setError(null);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error';
        setError(message);
        console.error('Error fetching corridors:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchCorridors();
  }, []);

  return {
    corridors,
    count: corridors.length,
    timestamp: new Date().toISOString(),
    isLoading,
    error,
  };
}

/**
 * Fetches a single corridor's detail including duties and enforcement actions
 */
export function useCorridorDetail(corridorId: string) {
  const [corridor, setCorridor] = useState<CorridorDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!corridorId) {
      setCorridor(null);
      return;
    }

    const fetchCorridorDetail = async () => {
      try {
        setIsLoading(true);
        const response = await fetch(`/api/corridors/${corridorId}`);
        if (!response.ok) {
          throw new Error(`Failed to fetch corridor: ${response.statusText}`);
        }
        const data = await response.json();
        setCorridor(data.data || null);
        setError(null);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error';
        setError(message);
        console.error('Error fetching corridor detail:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchCorridorDetail();
  }, [corridorId]);

  return {
    corridor,
    isLoading,
    error,
  };
}
