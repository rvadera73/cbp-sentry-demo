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

  const mapCordToTradeEntity = (cordEntity: any, riskLevel?: string): TradeEntity | null => {
    try {
      // Defensive checks for missing required fields
      if (!cordEntity || !cordEntity.entity_id || !cordEntity.name) {
        console.warn('Skipping entity with missing required fields:', cordEntity);
        return null;
      }

      // Address extraction with fallbacks
      const address = cordEntity.raw_data?.ADDRESSES?.[0]?.ADDR_FULL ||
                     cordEntity.address ||
                     cordEntity.raw_data?.ADDRESS ||
                     'Unknown';

      // Country code extraction with fallbacks
      const countryCode = (cordEntity.country || cordEntity.raw_data?.COUNTRY || 'UNKNOWN').toUpperCase();

      // Extract real risk level from entity data (OFAC status or RISK_LEVEL attribute)
      let actualRiskLevel: 'Critical' | 'High' | 'Medium' | 'Low' | 'Verified' = 'Low';
      const ofacStatus = cordEntity.raw_data?.OFAC_STATUS || cordEntity.OFAC_STATUS;
      const entityRiskLevel = cordEntity.raw_data?.ATTRIBUTES?.RISK_LEVEL || cordEntity.risk_level;

      if (ofacStatus === 'BLOCKED') {
        actualRiskLevel = 'Critical';
      } else if (ofacStatus === 'WATCH') {
        actualRiskLevel = 'High';
      } else if (ofacStatus === 'CLEAR') {
        actualRiskLevel = 'Verified';
      } else if (entityRiskLevel) {
        // Map RISK_LEVEL from entity attributes
        const upperRisk = String(entityRiskLevel).toUpperCase();
        if (upperRisk === 'CRITICAL') actualRiskLevel = 'Critical';
        else if (upperRisk === 'HIGH') actualRiskLevel = 'High';
        else if (upperRisk === 'MEDIUM') actualRiskLevel = 'Medium';
        else if (upperRisk === 'VERIFIED') actualRiskLevel = 'Verified';
      }

      // Sanctions status mapped from actual risk level
      const sanctionsStatus = actualRiskLevel === 'Critical' ? 'Blocked list' :
                             actualRiskLevel === 'High' ? 'Under Investigation' : 'None';

      // Safe extraction of arrays
      let affiliations: string[] = [];
      if (Array.isArray(cordEntity.raw_data?.RELATIONSHIPS)) {
        affiliations = cordEntity.raw_data.RELATIONSHIPS
          .map((r: any) => r?.REL_ANCHOR_KEY || r?.name || r?.entity_name || '')
          .filter((a: string) => a && a.length > 0);
      }

      // Safe extraction of tax ID
      let taxId = 'Unverified';
      if (Array.isArray(cordEntity.raw_data?.IDENTIFIERS) && cordEntity.raw_data.IDENTIFIERS.length > 0) {
        const idObj = cordEntity.raw_data.IDENTIFIERS[0];
        taxId = idObj?.NATIONAL_ID_NUMBER || idObj?.TAX_ID || idObj?.number || 'Unverified';
      }

      // Safe extraction of shared identifiers
      let sharedIds: string[] = [];
      if (Array.isArray(cordEntity.raw_data?.IDENTIFIERS)) {
        sharedIds = cordEntity.raw_data.IDENTIFIERS
          .map((id: any) => id?.LEI_NUMBER || id?.LEI || '')
          .filter((id: string) => id && id.length > 0);
      }

      return {
        entity_id: String(cordEntity.entity_id),
        entity_type: cordEntity.entity_type === 'organization' ? 'Manufacturer' : 'Intermediary',
        entity_name: String(cordEntity.name || cordEntity.entity_name || 'Unknown'),
        country: countryCode,
        risk_level: actualRiskLevel,
        sanctions_status: sanctionsStatus as 'None' | 'Match Found' | 'Under Investigation' | 'Blocked list',
        known_affiliations: affiliations,
        enforcement_history: cordEntity.enforcement_history || 'No enforcement actions recorded',
        ownership_indicators: cordEntity.ownership_indicators || 'Data pending from beneficial ownership registry',
        registration_status: cordEntity.registration_status || 'Active',
        watchlist_status: cordEntity.watchlist_status || 'Not Flagged',
        address: address,
        tax_id: taxId,
        phone: cordEntity.phone || 'Contact info pending',
        shared_identifiers: sharedIds,
      };
    } catch (err) {
      console.error('Error mapping CORD entity:', cordEntity, err);
      return null;
    }
  };

  const searchEntities = async (query: string) => {
    if (!query || query.length < 2) {
      setEntities([]);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      // Step 1: Search for matching entities
      const response = await fetch(`/api/cord/search?name=${encodeURIComponent(query)}&limit=10`);
      if (!response.ok) throw new Error('Failed to fetch entities');

      const data = await response.json();
      const matches = data.matches || [];

      // Step 2: Fetch full details for each match (includes addresses from raw_data)
      const enrichedMatches = await Promise.all(
        matches.map(async (m: any, idx: number) => {
          try {
            // Fetch full entity details including addresses
            const detailResp = await fetch(`/api/cord/entity/${m.entity_id}`);
            if (detailResp.ok) {
              const detailData = await detailResp.json();
              // Extract entity from nested response structure
              const entity = detailData.entity?.entity || detailData.entity || detailData;
              // Merge basic match with full details
              return { ...m, ...entity };
            }
            // Fallback to basic match if detail fetch fails
            return m;
          } catch (err) {
            console.warn(`Failed to fetch details for entity ${m.entity_id}:`, err);
            return m; // Fall back to basic match
          }
        })
      );

      // Step 3: Map enriched entities to TradeEntity format (risk level extracted from entity data)
      const mappedEntities = enrichedMatches
        .map((m: any) => mapCordToTradeEntity(m))
        .filter((entity: TradeEntity | null): entity is TradeEntity => entity !== null); // Remove null entities

      console.log(`Successfully mapped ${mappedEntities.length} entities from ${matches.length} matches`);
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
      try {
        // Fetch entity chain/relationship graph
        const chainResponse = await fetch(`/api/cord/entity/${entityId}/chain`);
        const chainData = chainResponse.ok ? await chainResponse.json() : null;

        // Fetch entity parties/related entities
        const partiesResponse = await fetch(`/api/cord/entity/${entityId}/parties`);
        const partiesData = partiesResponse.ok ? await partiesResponse.json() : null;

        // Merge entity with chain and parties data
        const enrichedEntity: TradeEntity = {
          ...entity,
          entity_chain: chainData?.chain || chainData?.entity_chain || undefined,
          parties: partiesData?.parties || partiesData?.data || undefined,
        };

        setSelectedEntity(enrichedEntity);
      } catch (err) {
        console.error('Error fetching entity chain:', err);
        // Fallback to just the entity without chain data
        setSelectedEntity(entity);
      }
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
