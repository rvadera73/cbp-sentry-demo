import { useState, useEffect } from 'react';
import { API_BASE_URL } from '../../services/apiUrl';

/**
 * Production model provenance — describes which production model produced the
 * scores shown across the scoring tabs. Mirrors `GET /api/model/production`.
 */
export interface ProductionModel {
  version: string;
  model_id?: string | null;
  gate?: number | null;
  status: string;
  calibration?: {
    calibration_multiplier?: number;
    referral_threshold?: number;
    critical_threshold?: number;
  } | null;
  maturity_pct?: number | null;
  confidence_interval_pts?: number | null;
}

/**
 * Defensive default so the badge always renders something sane even when the
 * risk engine is unreachable (matches the backend's `v1.1` fallback).
 */
export const DEFAULT_PRODUCTION_MODEL: ProductionModel = {
  version: 'v1.1',
  status: 'production',
  gate: 1,
  maturity_pct: null,
  confidence_interval_pts: null,
};

/**
 * Fetches the active production model once. Never throws — on any failure it
 * resolves to `DEFAULT_PRODUCTION_MODEL` so the UI never breaks.
 */
export function useProductionModel() {
  const [model, setModel] = useState<ProductionModel>(DEFAULT_PRODUCTION_MODEL);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/model/production`, {
          headers: { 'Content-Type': 'application/json' },
        });
        if (!response.ok) throw new Error(`API error: ${response.statusText}`);
        const data = (await response.json()) as Partial<ProductionModel>;
        if (cancelled) return;
        // Merge over defaults so missing optional fields stay sane.
        setModel({ ...DEFAULT_PRODUCTION_MODEL, ...data });
      } catch (err) {
        if (cancelled) return;
        console.warn('[useProductionModel] falling back to default model:', err);
        setModel(DEFAULT_PRODUCTION_MODEL);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  return { model, loading };
}
