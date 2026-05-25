/**
 * Custom hooks for entity graph visualization and data management.
 */

import { useState, useCallback, useEffect } from 'react';
import { EntityGraph, EntityNodeData, Warning } from './types';
import { cordApi } from '../../services/cordApi';

/**
 * Hook to fetch and manage entity graph data.
 */
export function useEntityGraph(shipmentId: string | null) {
  const [graph, setGraph] = useState<EntityGraph | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchGraph = useCallback(async () => {
    if (!shipmentId) return;

    setLoading(true);
    setError(null);

    try {
      const data = await cordApi.getEntityGraph(shipmentId);
      setGraph(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch entity graph';
      setError(message);
      setGraph(null);
    } finally {
      setLoading(false);
    }
  }, [shipmentId]);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  return { graph, loading, error, refetch: fetchGraph };
}

/**
 * Hook to extract warnings from entity graph.
 */
export function useGraphWarnings(graph: EntityGraph | null) {
  const [warnings, setWarnings] = useState<Map<string, Warning[]>>(new Map());

  useEffect(() => {
    if (!graph) {
      setWarnings(new Map());
      return;
    }

    const warningMap = new Map<string, Warning[]>();

    graph.chain.forEach((entity) => {
      if (entity.warnings && entity.warnings.length > 0) {
        warningMap.set(entity.entity_id, entity.warnings);
      }
    });

    setWarnings(warningMap);
  }, [graph]);

  return warnings;
}

/**
 * Hook to track highlighted entity in graph.
 */
export function useEntityHighlight() {
  const [highlightedId, setHighlightedId] = useState<string | null>(null);

  const setHighlight = useCallback((entityId: string | null) => {
    setHighlightedId(entityId);
  }, []);

  return { highlightedId, setHighlight };
}

/**
 * Hook to manage entity graph filtering and search.
 */
export function useEntitySearch(graph: EntityGraph | null) {
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredChain, setFilteredChain] = useState<EntityNodeData[]>([]);

  useEffect(() => {
    if (!graph) {
      setFilteredChain([]);
      return;
    }

    if (!searchQuery.trim()) {
      setFilteredChain(graph.chain);
      return;
    }

    const query = searchQuery.toLowerCase();
    const filtered = graph.chain.filter(
      (entity) =>
        entity.name.toLowerCase().includes(query) ||
        entity.entity_id.toLowerCase().includes(query) ||
        entity.country.toLowerCase().includes(query)
    );

    setFilteredChain(filtered);
  }, [graph, searchQuery]);

  return { searchQuery, setSearchQuery, filteredChain };
}

/**
 * Hook to calculate entity risk styling based on confidence and risk_score.
 */
export function useEntityRiskStyling(entity: EntityNodeData) {
  const getRiskColor = useCallback(() => {
    const riskScore = entity.risk_score ?? 0;

    if (riskScore >= 80) return '#d32f2f'; // RED
    if (riskScore >= 60) return '#f57c00'; // ORANGE
    if (riskScore >= 40) return '#fbc02d'; // YELLOW
    return '#388e3c'; // GREEN
  }, [entity.risk_score]);

  const getConfidenceOpacity = useCallback(() => {
    return Math.max(0.5, Math.min(1, entity.confidence));
  }, [entity.confidence]);

  return { getRiskColor, getConfidenceOpacity };
}
