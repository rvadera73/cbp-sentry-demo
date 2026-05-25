import { useState, useEffect } from 'react';

export interface RiskScoringBreakdown {
  shipment_id?: string;
  risk_score?: number;
  components: Array<{
    component: string;
    factor: string;
    score: number;
    weight: number;
    weighted_result: number;
    rationale: string;
    evidence?: string[];
  }>;
  subtotal: number;
  corridor_risk_adjustment?: {
    corridor?: string;
    baseline_risk?: number;
    baseline?: number;
    multiplier: number;
    adjustment_points: number;
    reason: string;
  };
  additional_adjustments?: Array<{
    adjustment_type: string;
    points: number;
    reason: string;
  }>;
  final_score: number;
  confidence_interval?: string;
  h1_level?: string;
  h2_signals?: string[];
  h3_recommendation?: string;
}

export function useRiskScoring(shipmentId: string | null) {
  const [scoreData, setScoreData] = useState<RiskScoringBreakdown | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!shipmentId) {
      setScoreData(null);
      return;
    }

    const fetchRiskScoring = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`/api/risk-scoring/comprehensive`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ shipment_id: shipmentId }),
        });

        if (!response.ok) {
          throw new Error(`API error: ${response.statusText}`);
        }

        const apiResponse = await response.json();

        // Extract and flatten the risk_breakdown into the scoreData structure
        const scoreData: RiskScoringBreakdown = {
          shipment_id: apiResponse.shipment_id,
          risk_score: apiResponse.risk_score,
          confidence_interval: apiResponse.confidence_interval,
          components: apiResponse.risk_breakdown?.components || [],
          subtotal: apiResponse.risk_breakdown?.subtotal || 0,
          corridor_risk_adjustment: apiResponse.risk_breakdown?.corridor_risk_adjustment,
          additional_adjustments: apiResponse.risk_breakdown?.additional_adjustments,
          final_score: apiResponse.risk_breakdown?.final_score || apiResponse.risk_score || 0,
          // Compute h1_level, h2_signals, h3_recommendation from components if available
          h1_level: apiResponse.risk_breakdown?.final_score >= 80 ? 'HIGH' : apiResponse.risk_breakdown?.final_score >= 50 ? 'MEDIUM' : 'LOW',
          h3_recommendation: apiResponse.risk_breakdown?.final_score >= 80 ? 'HOLD' : apiResponse.risk_breakdown?.final_score >= 50 ? 'EXAMINE' : 'CLEAR',
        };

        setScoreData(scoreData);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to fetch risk scoring';
        setError(message);
        console.error('Error fetching risk scoring:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchRiskScoring();
  }, [shipmentId]);

  return { scoreData, loading, error };
}
