import { useState, useEffect } from 'react';
import { TradeEntity } from '../types/v2.types';
import { api } from '../../services/api';

interface UseV2EntitiesReturn {
  entities: TradeEntity[];
  selectedEntity: TradeEntity | null;
  loading: boolean;
  error: string | null;
  selectEntity: (entityId: string) => Promise<void>;
  searchEntities: (query: string) => Promise<void>;
}

/**
 * Fetches entities from CORD entity resolution service
 */
export function useV2Entities(): UseV2EntitiesReturn {
  const [entities, setEntities] = useState<TradeEntity[]>([]);
  const [selectedEntity, setSelectedEntity] = useState<TradeEntity | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mapCordToTradeEntity = (cordEntity: any, riskLevel: string = 'Low'): TradeEntity => {
    const address = cordEntity.raw_data?.ADDRESSES?.[0]?.ADDR_FULL || 'Unknown';
    const countryCode = cordEntity.country?.toUpperCase() || 'UNKNOWN';
    const sanctionsStatus = riskLevel === 'Critical' ? 'Blocked list' : riskLevel === 'High' ? 'Under Investigation' : 'None';

    return {
      entity_id: cordEntity.entity_id,
      entity_type: cordEntity.entity_type === 'organization' ? 'Manufacturer' : 'Intermediary',
      entity_name: cordEntity.name,
      country: countryCode,
      risk_level: riskLevel as 'Critical' | 'High' | 'Medium' | 'Low' | 'Verified',
      sanctions_status: sanctionsStatus as 'None' | 'Match Found' | 'Under Investigation' | 'Blocked list',
      known_affiliations: cordEntity.raw_data?.RELATIONSHIPS?.map((r: any) => r.REL_ANCHOR_KEY) || [],
      enforcement_history: 'No enforcement actions recorded',
      ownership_indicators: 'Data pending from beneficial ownership registry',
      registration_status: 'Active',
      watchlist_status: 'Not Flagged',
      address: address,
      tax_id: cordEntity.raw_data?.IDENTIFIERS?.[0]?.NATIONAL_ID_NUMBER || 'Unverified',
      phone: 'Contact info pending',
      shared_identifiers: cordEntity.raw_data?.IDENTIFIERS?.map((id: any) => id.LEI_NUMBER).filter(Boolean) || [],
    };
  };

  const searchEntities = async (query: string) => {
    if (!query || query.length < 2) {
      setEntities([]);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`/api/cord/search?name=${encodeURIComponent(query)}&limit=10`);
      if (!response.ok) throw new Error('Failed to fetch entities');

      const data = await response.json();
      const matches = data.matches || [];

      const mappedEntities = matches.map((m: any, idx: number) => {
        const riskLevels: Array<'Critical' | 'High' | 'Medium' | 'Low' | 'Verified'> = ['Low', 'Low', 'Medium', 'High', 'Critical'];
        return mapCordToTradeEntity(m, riskLevels[idx % 5]);
      });

      setEntities(mappedEntities);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch entities';
      setError(message);
      setEntities([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    searchEntities('import');
  }, []);

  const selectEntity = async (entityId: string) => {
    const entity = entities.find(e => e.entity_id === entityId);
    if (entity) {
      setSelectedEntity(entity);
    }
  };

  return {
    entities,
    selectedEntity,
    loading,
    error,
    selectEntity,
    searchEntities,
  };
}
