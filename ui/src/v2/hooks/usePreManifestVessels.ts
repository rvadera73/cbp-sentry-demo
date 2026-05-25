import { useState, useEffect, useCallback } from 'react';

export interface PreManifestVessel {
  vessel_imo: string;
  vessel_name: string;
  mmsi: string;
  flag_state: string;
  origin_port: string;
  origin_country: string;
  destination_port: string;
  destination_country: string;
  corridor_id: string;
  eta_us: string;
  ais_status: string;
  current_lat: number;
  current_lon: number;
  speed_knots: number;
  last_refreshed_at: string;
}

export interface PreManifestVesselsData {
  vessels: PreManifestVessel[];
  count: number;
  timestamp: string;
  isLoading: boolean;
  error: string | null;
  lastRefreshed: string | null;
  isRefreshing: boolean;
}

/**
 * Fetches pre-manifest vessels currently inbound to US ports
 * Shows vessel data available before the shipment manifest is filed
 * Last refresh timestamp indicates when data was pulled from external APIs
 *
 * @param corridorId Optional corridor filter (e.g. "VN→US")
 * @param autoRefresh Enable auto-refresh every 30 minutes
 */
export function usePreManifestVessels(corridorId?: string, autoRefresh = false): PreManifestVesselsData {
  const [vessels, setVessels] = useState<PreManifestVessel[]>([]);
  const [isLoading, setIsLoading] = useState(!!corridorId || autoRefresh);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<string | null>(null);

  const fetchVessels = useCallback(async () => {
    try {
      setIsLoading(true);
      const params = new URLSearchParams();
      if (corridorId) {
        params.append('corridor_id', corridorId);
      }

      const url = params.toString()
        ? `/api/pre-manifest/vessels?${params}`
        : '/api/pre-manifest/vessels';

      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Failed to fetch pre-manifest vessels: ${response.statusText}`);
      }
      const data = await response.json();
      setVessels(data.data || []);
      setLastRefreshed(data.timestamp);
      setError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
      console.error('Error fetching pre-manifest vessels:', err);
    } finally {
      setIsLoading(false);
    }
  }, [corridorId]);

  const refreshVessels = useCallback(async () => {
    try {
      setIsRefreshing(true);
      const params = new URLSearchParams();
      if (corridorId) {
        params.append('corridor_id', corridorId);
      }

      const url = params.toString()
        ? `/api/pre-manifest/vessels?${params}`
        : '/api/pre-manifest/vessels';

      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Failed to refresh vessels: ${response.statusText}`);
      }
      const data = await response.json();
      setVessels(data.data || []);
      setLastRefreshed(data.timestamp);
      setError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
      console.error('Error refreshing pre-manifest vessels:', err);
    } finally {
      setIsRefreshing(false);
    }
  }, [corridorId]);

  useEffect(() => {
    fetchVessels();

    // Auto-refresh every 30 minutes if enabled
    if (autoRefresh) {
      const interval = setInterval(fetchVessels, 30 * 60 * 1000);
      return () => clearInterval(interval);
    }
  }, [corridorId, autoRefresh, fetchVessels]);

  return {
    vessels,
    count: vessels.length,
    timestamp: new Date().toISOString(),
    isLoading,
    error,
    lastRefreshed,
    isRefreshing,
    // Note: refreshVessels is a manual trigger function, not returned here
    // User calls refreshVessels directly via button click
  };
}

/**
 * Extended version that includes refresh trigger function
 */
export function usePreManifestVesselsWithRefresh(autoRefresh = false) {
  const data = usePreManifestVessels(undefined, autoRefresh);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const manualRefresh = async () => {
    try {
      setIsRefreshing(true);
      const response = await fetch('/api/pre-manifest/vessels');
      if (!response.ok) {
        throw new Error(`Failed to refresh vessels: ${response.statusText}`);
      }
      const newData = await response.json();
      // Trigger re-fetch by calling the hook again
      return newData;
    } catch (err) {
      console.error('Error refreshing vessels:', err);
      throw err;
    } finally {
      setIsRefreshing(false);
    }
  };

  return {
    ...data,
    isRefreshing,
    manualRefresh,
  };
}
