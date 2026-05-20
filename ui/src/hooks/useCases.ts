import { useState, useEffect } from 'react';
import { Case, CaseFilter } from '../types/models';
import { API_BASE_URL } from '../services/api';

export function useCases() {
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCases();
  }, []);

  const fetchCases = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/shipments`);
      if (!response.ok) throw new Error('Failed to fetch cases');
      const data = await response.json();
      setCases(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const filterCases = (filters: CaseFilter): Case[] => {
    let filtered = [...cases];

    if (filters.riskLevel && filters.riskLevel !== 'all') {
      filtered = filtered.filter((c) => {
        const tier = c.risk_score >= 70 ? 'HIGH' : c.risk_score >= 50 ? 'MEDIUM' : 'LOW';
        return tier === filters.riskLevel;
      });
    }

    if (filters.searchTerm) {
      const term = filters.searchTerm.toLowerCase();
      filtered = filtered.filter(
        (c) =>
          c.shipper_name.toLowerCase().includes(term) ||
          c.consignee_name.toLowerCase().includes(term) ||
          c.commodity_code.includes(term)
      );
    }

    if (filters.sortBy) {
      filtered.sort((a, b) => {
        let aVal: any = a[filters.sortBy as keyof Case];
        let bVal: any = b[filters.sortBy as keyof Case];

        if (aVal < bVal) return filters.sortOrder === 'desc' ? 1 : -1;
        if (aVal > bVal) return filters.sortOrder === 'desc' ? -1 : 1;
        return 0;
      });
    }

    return filtered;
  };

  return { cases, loading, error, fetchCases, filterCases };
}
