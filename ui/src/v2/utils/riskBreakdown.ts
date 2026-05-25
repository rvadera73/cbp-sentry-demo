export interface RiskBreakdown {
  h1_score: number;
  h2_score: number;
  h3_score: number;
  calculation_table?: any[];
  confidence_interval?: number;
}

export function computeRiskBreakdown(shipment: any): RiskBreakdown {
  const h1_score = shipment.h1_score || 0;
  const h2_score = shipment.h2_score || 0;
  const h3_score = shipment.h3_score || Math.max(0, (shipment.risk_score || 0) - h1_score - h2_score);

  return {
    h1_score,
    h2_score,
    h3_score,
    confidence_interval: 95,
  };
}
