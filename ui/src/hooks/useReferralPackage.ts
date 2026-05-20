import { useState, useEffect } from 'react';
import { ReferralPackage } from '../types/models';
import { API_BASE_URL } from '../services/api';

export function useReferralPackage(shipmentId: string | null) {
  const [referral, setReferral] = useState<ReferralPackage | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!shipmentId) {
      setReferral(null);
      return;
    }

    fetchReferral();
  }, [shipmentId]);

  const fetchReferral = async () => {
    if (!shipmentId) return;

    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/referral/${shipmentId}`);
      if (!response.ok) throw new Error('Failed to fetch referral package');
      const data = await response.json();
      setReferral(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return { referral, loading, error, refetch: fetchReferral };
}
