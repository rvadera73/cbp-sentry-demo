import { useState, useEffect } from 'react';
import { ScoreResult } from '../types/models';
import { API_BASE_URL } from '../services/api';

export function useScore(shipmentId: string | null) {
  const [score, setScore] = useState<ScoreResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!shipmentId) {
      setScore(null);
      return;
    }

    fetchScore();
  }, [shipmentId]);

  const fetchScore = async () => {
    if (!shipmentId) return;

    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/score/${shipmentId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      if (!response.ok) throw new Error('Failed to fetch score');
      const data = await response.json();
      setScore(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return { score, loading, error, refetch: fetchScore };
}
