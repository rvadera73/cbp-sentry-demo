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
  refetch: () => Promise<void>;
}

/**
 * Entity Resolution via CORD
 * Fetches entities and resolves their full 3-4 level supply chain relationships
 */
export function useV2Entities(): UseV2EntitiesReturn {
  const [entities, setEntities] = useState<TradeEntity[]>([]);
  const [selectedEntity, setSelectedEntity] = useState<TradeEntity | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Sample entities with ACTUAL relationship data in resolve backend
  // These are test fixtures with 3-4 level entity chains
  const SAMPLE_ENTITIES = [
    { name: 'Greenfield Industrial Trading Co., Ltd.', country: 'VN' },
    { name: 'Greenfield Global Metals Holdings Ltd.', country: 'HK' },
    { name: 'Guangdong Greenfield Aluminum Mfg. Co., Ltd.', country: 'CN' },
    { name: 'SunPath Energy Distributors LLC', country: 'US' },
    { name: 'Solaria Manufacturing Sdn. Bhd.', country: 'MY' },
    { name: 'Guangdong Solaria New Energy Technology Co.', country: 'CN' },
  ];

  const mapCordToTradeEntity = (name: string, country: string, cordEntity: any): TradeEntity => {
    const ofacStatus = cordEntity?.ofac_status || cordEntity?.raw_data?.OFAC_STATUS;
    let riskLevel: 'Critical' | 'High' | 'Medium' | 'Low' | 'Verified' = 'Low';
    let watchlistStatus = 'Not Flagged';

    if (ofacStatus === 'BLOCKED') {
      riskLevel = 'Critical';
      watchlistStatus = 'Flagged';
    } else if (ofacStatus === 'WATCH') {
      riskLevel = 'High';
      watchlistStatus = 'Flagged';
    } else if (ofacStatus === 'CLEAR') {
      riskLevel = 'Verified';
    }

    const entityId = `${name}|${country}`.toLowerCase().replace(/\s+/g, '-');

    return {
      entity_id: entityId,
      entity_type: 'Manufacturer',
      entity_name: name,
      country: country.toUpperCase(),
      risk_level: riskLevel,
      sanctions_status: watchlistStatus === 'Flagged' ? 'Under Investigation' : 'None',
      known_affiliations: [],
      enforcement_history: 'No enforcement actions recorded',
      ownership_indicators: 'Data pending from beneficial ownership registry',
      registration_status: 'Active',
      watchlist_status: watchlistStatus,
      address: cordEntity?.address || 'Address pending',
      tax_id: cordEntity?.tax_id || 'Unverified',
      phone: cordEntity?.phone || 'Contact pending',
      shared_identifiers: [],
    };
  };

  const resolveEntityChainFromCORD = async (name: string, country: string): Promise<any> => {
    try {
      console.log(`[Entity Resolution] Resolving chain for ${name} (${country})`);

      // Call CORD resolve endpoint to get full 3-4 level chain
      const response = await fetch(`/api/cord/resolve?shipper_name=${encodeURIComponent(name)}&shipper_country=${encodeURIComponent(country)}`);

      if (!response.ok) {
        console.warn(`[Entity Resolution] Resolve failed with status ${response.status}`);
        return null;
      }

      const data = await response.json();
      console.log(`[Entity Resolution] Resolve response for ${name}:`, data);

      // Extract chain from response - API returns { resolution: { chain: {...} } }
      const apiResponse = data.resolution || {};
      const resolution = apiResponse.chain || apiResponse || {};

      console.log(`[Entity Resolution] Extracted resolution:`, resolution);

      // Build entity_chain array from CORD resolution levels
      const chain = [];

      // Level 1: Shipper (direct entity)
      if (resolution.level_1) {
        chain.push({
          entity_id: resolution.level_1.entity_id || name,
          name: resolution.level_1.name || name,
          country: country,
          entity_type: resolution.level_1.entity_type || 'SHIPPER',
          role: 'Shipper/Direct Entity',
          confidence: resolution.level_1.confidence || 0.9,
          relationships: [],
          data_source: 'CORD',
        });
      }

      // Level 2: Related party
      if (resolution.level_2) {
        chain.push({
          entity_id: resolution.level_2.entity_id || '',
          name: resolution.level_2.name || 'Related Entity',
          country: resolution.level_2.country || '',
          entity_type: resolution.level_2.entity_type || 'INTERMEDIARY',
          role: resolution.level_2_relationship?.relationship_type || 'Related Party',
          confidence: resolution.level_2.confidence || 0.8,
          relationships: resolution.level_2_relationship ? [
            {
              type: 'OWNERSHIP_LINK',
              details: `${resolution.level_2.name} is parent/owner of ${resolution.level_1.name}`,
              confidence: resolution.level_2_relationship.confidence || 0.8,
            },
            {
              type: 'SHARED_INFRASTRUCTURE',
              details: 'Operates under common corporate structure',
              confidence: 0.85,
            },
          ] : [],
          data_source: 'CORD',
        });
      }

      // Level 3: Deeper connection
      if (resolution.level_3) {
        chain.push({
          entity_id: resolution.level_3.entity_id || '',
          name: resolution.level_3.name || 'Upstream Entity',
          country: resolution.level_3.country || '',
          entity_type: resolution.level_3.entity_type || 'MANUFACTURER',
          role: resolution.level_3_relationship?.relationship_type || 'Upstream Supplier',
          confidence: resolution.level_3.confidence || 0.7,
          relationships: resolution.level_3_relationship ? [
            {
              type: 'PARENT_MANUFACTURER',
              details: `Ultimate manufacturer/beneficial owner of entire chain`,
              confidence: resolution.level_3_relationship.confidence || 0.9,
            },
            {
              type: 'FACILITY_CONTROL',
              details: 'Controls primary manufacturing facility',
              confidence: 0.88,
            },
          ] : [],
          data_source: 'CORD',
        });
      }

      return chain.length > 0 ? chain : null;
    } catch (err) {
      console.warn(`[Entity Resolution] Failed to resolve ${name}:`, err);
      return null;
    }
  };

  const loadCORDEntities = async () => {
    try {
      setLoading(true);
      setError(null);
      console.log('[Entity Resolution] Loading CORD entities...');

      const resolvedEntities: TradeEntity[] = [];

      // Resolve each sample entity with CORD to get full 3-4 level chain
      for (const sample of SAMPLE_ENTITIES) {
        try {
          // First get the entity details via search
          const searchResp = await fetch(`/api/cord/search?name=${encodeURIComponent(sample.name)}&country=${encodeURIComponent(sample.country)}&limit=1`);
          if (!searchResp.ok) continue;

          const searchData = await searchResp.json();
          const match = searchData.matches?.[0];
          if (!match) continue;

          // Map to TradeEntity
          const tradeEntity = mapCordToTradeEntity(sample.name, sample.country, match);

          // Resolve the full supply chain relationship
          const chain = await resolveEntityChainFromCORD(sample.name, sample.country);
          if (chain) {
            tradeEntity.entity_chain = chain;
          }

          resolvedEntities.push(tradeEntity);
          console.log(`[Entity Resolution] Resolved entity: ${sample.name}`);
        } catch (err) {
          console.warn(`[Entity Resolution] Error processing ${sample.name}:`, err);
        }
      }

      // Sort by risk level
      resolvedEntities.sort((a, b) => {
        const riskOrder = { 'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3, 'Verified': 4 };
        return (riskOrder[a.risk_level] || 5) - (riskOrder[b.risk_level] || 5);
      });

      console.log(`[Entity Resolution] Loaded ${resolvedEntities.length} entities with CORD chains`);
      setEntities(resolvedEntities);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load CORD entities';
      console.error('[Entity Resolution] Error:', message);
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const searchEntities = async (query: string) => {
    if (!query || query.length < 2) {
      await loadCORDEntities();
      return;
    }

    try {
      setLoading(true);
      setError(null);
      console.log(`[Entity Resolution] Searching for "${query}" in CORD...`);

      const response = await fetch(`/api/cord/search?name=${encodeURIComponent(query)}&limit=20`);
      if (!response.ok) throw new Error('Search failed');

      const data = await response.json();
      const matches = data.matches || [];

      const resolvedEntities: TradeEntity[] = [];

      // Process search results
      for (const match of matches) {
        try {
          const entity = mapCordToTradeEntity(match.name || query, match.country || 'XX', match);

          // Try to resolve chain for search results too
          const chain = await resolveEntityChainFromCORD(
            match.name || query,
            match.country || 'XX'
          );
          if (chain) {
            entity.entity_chain = chain;
          }

          resolvedEntities.push(entity);
        } catch (err) {
          console.warn(`[Entity Resolution] Error processing search result:`, err);
        }
      }

      console.log(`[Entity Resolution] Found ${resolvedEntities.length} entities for "${query}"`);
      setEntities(resolvedEntities);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Search failed';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const selectEntity = async (entityId: string) => {
    if (!entityId) {
      setSelectedEntity(null);
      return;
    }

    const entity = entities.find(e => e.entity_id === entityId);
    if (!entity) {
      console.warn(`[Entity Resolution] Entity ${entityId} not found`);
      setSelectedEntity(null);
      return;
    }

    try {
      console.log(`[Entity Resolution] Selected entity:`, entity);

      // If entity doesn't have chain data, try to fetch it
      if (!entity.entity_chain) {
        const nameCountry = entityId.split('|');
        if (nameCountry.length === 2) {
          const chain = await resolveEntityChainFromCORD(nameCountry[0], nameCountry[1]);
          if (chain) {
            entity.entity_chain = chain;
          }
        }
      }

      setSelectedEntity({ ...entity });
    } catch (err) {
      console.error('[Entity Resolution] Error selecting entity:', err);
      setSelectedEntity(entity);
    }
  };

  useEffect(() => {
    loadCORDEntities();
  }, []);

  return {
    entities,
    selectedEntity,
    loading,
    error,
    selectEntity,
    searchEntities,
    refetch: loadCORDEntities,
  };
}
