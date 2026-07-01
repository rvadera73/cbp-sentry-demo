import { useState, useEffect, useCallback } from 'react';
import { API_BASE_URL } from '../../services/apiUrl';

/**
 * Data pipeline sources feeding the risk model. Mirrors `GET /pipelines`.
 * Each source is a dataset feed (manifest/isf/vessel/entity/reference) with a
 * mode (online/file/derived) and a health status.
 */
export type PipelineDatasetType = 'manifest' | 'isf' | 'vessel' | 'entity' | 'reference';
export type PipelineMode = 'online' | 'file' | 'derived';
export type PipelineStatus = 'healthy' | 'stale' | 'error' | 'not_configured' | 'seed';

export interface PipelineSource {
  id: string;
  name: string;
  dataset_type: PipelineDatasetType;
  mode: PipelineMode;
  status: PipelineStatus;
  last_run_at: string | null;
  rows_last_run: number | null;
  total_rows: number | null;
  schedule: string | null;
  endpoint_or_path: string | null;
  detail: string | null;
  gap_note: string | null;
  enabled: boolean;
}

/** A single ingestion run for a source. Mirrors `GET /pipelines/{id}/runs`. */
export interface PipelineRun {
  run_id: string;
  started_at: string | null;
  ended_at: string | null;
  status: string;
  rows_in: number | null;
  rows_out: number | null;
  message: string | null;
}

/** Response from `POST /pipelines/{id}/run`. */
export interface PipelineRunResult {
  status: string;
  id: string;
  run_id: string;
  rows_ingested: number;
  message: string;
}

/**
 * Fetches the data pipeline sources. Resilient by design: on any failure it
 * resolves to an empty list and sets `error`, and never throws — so the tab
 * always renders an honest empty/error state instead of crashing.
 */
export function useDataPipelines() {
  const [sources, setSources] = useState<PipelineSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSources = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/pipelines`, {
        headers: { 'Content-Type': 'application/json' },
      });
      if (!response.ok) throw new Error(`API error: ${response.status} ${response.statusText}`);
      const data = (await response.json()) as { sources?: PipelineSource[] };
      setSources(Array.isArray(data.sources) ? data.sources : []);
    } catch (err) {
      console.warn('[useDataPipelines] failed to load pipelines:', err);
      setSources([]);
      setError(err instanceof Error ? err.message : 'Failed to load pipelines');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSources();
  }, [fetchSources]);

  /**
   * Triggers a manual run for a source, then refetches the source list so the
   * table reflects the new status/rows. Returns the run result (or null on
   * failure) — never throws.
   */
  const runPipeline = useCallback(
    async (id: string): Promise<PipelineRunResult | null> => {
      try {
        const response = await fetch(`${API_BASE_URL}/pipelines/${id}/run`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        });
        if (!response.ok) throw new Error(`API error: ${response.status} ${response.statusText}`);
        const result = (await response.json()) as PipelineRunResult;
        await fetchSources();
        return result;
      } catch (err) {
        console.warn(`[useDataPipelines] failed to run pipeline ${id}:`, err);
        return null;
      }
    },
    [fetchSources],
  );

  /** Fetches recent run history for a source. Returns [] on failure — never throws. */
  const getRuns = useCallback(async (id: string): Promise<PipelineRun[]> => {
    try {
      const response = await fetch(`${API_BASE_URL}/pipelines/${id}/runs`, {
        headers: { 'Content-Type': 'application/json' },
      });
      if (!response.ok) throw new Error(`API error: ${response.status} ${response.statusText}`);
      const data = (await response.json()) as { runs?: PipelineRun[] };
      return Array.isArray(data.runs) ? data.runs : [];
    } catch (err) {
      console.warn(`[useDataPipelines] failed to load runs for ${id}:`, err);
      return [];
    }
  }, []);

  return { sources, loading, error, refetch: fetchSources, runPipeline, getRuns };
}
