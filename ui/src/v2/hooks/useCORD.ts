import { useState, useEffect } from 'react';

interface Entity {
  entity_id: string;
  name: string;
  type: string;
  country: string;
  confidence: number;
  data_source: string;
  relationships?: Array<{
    type: string;
    target: string;
    confidence: number;
  }>;
}

interface CORDResponse {
  chain: Entity[];
  ofac?: any;
  error?: string;
}

const CORD_URL = process.env.REACT_APP_CORD_URL || 'http://localhost:8004';

export function useCORD(shipperName?: string, shipperCountry?: string) {
  const [chain, setChain] = useState<Entity[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!shipperName || !shipperCountry) {
      setChain([]);
      return;
    }

    const fetchFromCORD = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`${CORD_URL}/resolve`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            shipper_name: shipperName,
            shipper_country: shipperCountry,
          }),
        });

        if (!response.ok) {
          throw new Error(`CORD returned ${response.status}`);
        }

        const data = await response.json();
        
        if (data.status !== 'success') {
          throw new Error(data.error || 'CORD resolution failed');
        }

        // Transform CORD response to Entity array
        const chainData = data.chain || {};
        const entities: Entity[] = [];

        for (let level = 1; level <= 3; level++) {
          const entityKey = `level_${level}`;
          const entity = chainData[entityKey];
          
          if (!entity) continue;

          const relKey = `level_${level}_relationship`;
          const relationship = chainData[relKey];

          entities.push({
            entity_id: entity.entity_id || `level-${level}`,
            name: entity.name || 'Unknown',
            type: entity.entity_type || entity.type || 'ORGANIZATION',
            country: entity.country || '',
            confidence: parseFloat(entity.confidence) || 0.8,
            data_source: entity.data_source || 'CORD',
            relationships: relationship ? [{
              type: relationship.relationship_type || 'RELATED_TO',
              target: chainData[`level_${level}_id`] || '',
              confidence: parseFloat(relationship.confidence) || 0.8,
            }] : [],
          });
        }

        setChain(entities);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
        setChain([]);
      } finally {
        setLoading(false);
      }
    };

    fetchFromCORD();
  }, [shipperName, shipperCountry]);

  return { chain, loading, error };
}
