import { useState, useEffect } from 'react';
import { GraphData } from '../types/models';
import { API_BASE_URL } from '../services/api';

export function useEntityGraph(shipmentId: string | null) {
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!shipmentId) {
      setGraph(null);
      return;
    }

    fetchGraph();
  }, [shipmentId]);

  const fetchGraph = async () => {
    if (!shipmentId) return;

    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/graph/shipment/${shipmentId}`);
      if (!response.ok) throw new Error('Failed to fetch entity graph');
      const data = await response.json();
      setGraph(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return { graph, loading, error, refetch: fetchGraph };
}
