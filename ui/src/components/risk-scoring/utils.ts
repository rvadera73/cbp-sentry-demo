/**
 * Risk Scoring Utilities
 * Pure functions for risk calculation, formatting, and data transformation
 */

import { RiskComponent, RiskScoreBreakdown } from './types';

/**
 * Determine risk level based on score
 */
export function getRiskLevel(score: number): 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' {
  if (score >= 90) return 'CRITICAL';
  if (score >= 70) return 'HIGH';
  if (score >= 50) return 'MEDIUM';
  return 'LOW';
}

/**
 * Get color for risk level
 */
export function getRiskColor(score: number): string {
  if (score >= 90) return '#dc2626';    // Red
  if (score >= 70) return '#ea580c';    // Orange
  if (score >= 50) return '#eab308';    // Yellow
  return '#22c55e';                      // Green
}

/**
 * Group components by factor, maintaining order
 */
export function groupComponentsByFactor(
  components: RiskComponent[]
): Record<string, RiskComponent[]> {
  const grouped: Record<string, RiskComponent[]> = {};

  components.forEach((comp) => {
    if (!grouped[comp.factor]) {
      grouped[comp.factor] = [];
    }
    grouped[comp.factor].push(comp);
  });

  return grouped;
}

/**
 * Calculate subtotal for a specific factor
 */
export function calculateFactorSubtotal(
  components: RiskComponent[],
  factor: string
): number {
  return components
    .filter((c) => c.factor === factor)
    .reduce((sum, c) => sum + c.weighted_result, 0);
}

/**
 * Validate risk breakdown structure
 */
export function isValidRiskBreakdown(data: any): data is RiskScoreBreakdown {
  if (!data || typeof data !== 'object') return false;

  return (
    typeof data.shipment_id === 'string' &&
    Array.isArray(data.components) &&
    typeof data.final_score === 'number' &&
    typeof data.confidence_interval === 'string'
  );
}

/**
 * Generate mock risk breakdown for testing
 */
export function generateMockRiskBreakdown(shipmentId?: string): RiskScoreBreakdown {
  const id = shipmentId || `SHP-${Date.now()}`;

  const components: RiskComponent[] = [
    // Documentation Risk (3 components)
    {
      factor: 'Documentation',
      component: 'Element 9 Mismatch',
      score: 6.5,
      weight: 25,
      weighted_result: 1.625,
      rationale: 'Declared origin does not match actual shipment origin',
      evidence: ['ISF Filing: 2026-05-20', 'Element 9 Mismatch Detected']
    },
    {
      factor: 'Documentation',
      component: 'ISF Amendment Count',
      score: 3.2,
      weight: 25,
      weighted_result: 0.8,
      rationale: 'Normal amendment activity',
      evidence: ['Amendment Count: 2', 'Within threshold']
    },
    {
      factor: 'Documentation',
      component: 'Manifest Completeness',
      score: 2.1,
      weight: 25,
      weighted_result: 0.525,
      rationale: 'All required fields present',
      evidence: ['Completeness: 100%']
    },
    // Commodity Risk (3 components)
    {
      factor: 'Commodity',
      component: 'Tariff Rate Risk',
      score: 4.8,
      weight: 15,
      weighted_result: 0.72,
      rationale: 'Commodity has moderate tariff exposure',
      evidence: ['Tariff Rate: 16%', 'HTS: 6204.62.8015']
    },
    {
      factor: 'Commodity',
      component: 'Export Control Risk',
      score: 1.0,
      weight: 15,
      weighted_result: 0.15,
      rationale: 'Commodity not export controlled',
      evidence: ['Not on EAR/ITAR lists']
    },
    {
      factor: 'Commodity',
      component: 'UFLPA Risk',
      score: 6.5,
      weight: 15,
      weighted_result: 0.975,
      rationale: 'Apparel has UFLPA exposure risk',
      evidence: ['UFLPA High Risk: Yes', 'Origin: Vietnam']
    },
    // Routing Risk (3 components)
    {
      factor: 'Routing',
      component: 'AIS Dwell Anomaly',
      score: 5.2,
      weight: 15,
      weighted_result: 0.78,
      rationale: 'Extended dwell time in port',
      evidence: ['Dwell Days: 8.5', 'Baseline: 3 days']
    },
    {
      factor: 'Routing',
      component: 'Port Selection Risk',
      score: 3.1,
      weight: 15,
      weighted_result: 0.465,
      rationale: 'Standard port selection',
      evidence: ['Port: Los Angeles', 'Risk Level: Medium']
    },
    {
      factor: 'Routing',
      component: 'Vessel Flag Risk',
      score: 2.0,
      weight: 15,
      weighted_result: 0.3,
      rationale: 'Vessel in low-risk flag state',
      evidence: ['Vessel Flag: Panama', 'Risk: Low']
    },
    // Party Risk (3 components)
    {
      factor: 'Party',
      component: 'Shipper Age',
      score: 6.0,
      weight: 15,
      weighted_result: 0.9,
      rationale: 'Shipper relatively new to trade',
      evidence: ['Shipper Age: 12 months', 'Threshold: 24 months']
    },
    {
      factor: 'Party',
      component: 'OFAC Match',
      score: 0.0,
      weight: 15,
      weighted_result: 0.0,
      rationale: 'No OFAC match detected',
      evidence: ['OFAC Match: No']
    },
    {
      factor: 'Party',
      component: 'Customs Violations',
      score: 2.5,
      weight: 15,
      weighted_result: 0.375,
      rationale: 'One minor violation in 24 months',
      evidence: ['Violation Count: 1', 'Type: Documentation']
    },
    // Corridor Risk (3 components)
    {
      factor: 'Corridor',
      component: 'Corridor Baseline',
      score: 5.8,
      weight: 20,
      weighted_result: 1.16,
      rationale: 'Vietnam-US corridor has elevated risk',
      evidence: ['Corridor: VN→US', 'Baseline Risk: Medium']
    },
    {
      factor: 'Corridor',
      component: 'Tariff Evasion Incentive',
      score: 3.2,
      weight: 20,
      weighted_result: 0.64,
      rationale: 'Declared value within range',
      evidence: ['Declared Value: $45,000', 'Unit Value: Normal']
    },
    {
      factor: 'Corridor',
      component: 'Trade Agreement Impact',
      score: 1.5,
      weight: 20,
      weighted_result: 0.3,
      rationale: 'CPTPP benefit available',
      evidence: ['Agreement: CPTPP', 'Preferential Rate: 0%']
    },
    // Pattern Risk (3 components)
    {
      factor: 'Pattern',
      component: 'Pricing Anomaly',
      score: 4.1,
      weight: 10,
      weighted_result: 0.41,
      rationale: 'Pricing within normal distribution',
      evidence: ['Unit Value vs Baseline: -2%', 'Within 1 std dev']
    },
    {
      factor: 'Pattern',
      component: 'Transshipment Detection',
      score: 6.8,
      weight: 10,
      weighted_result: 0.68,
      rationale: 'ML model indicates transshipment risk',
      evidence: ['LightGBM Probability: 68%', 'Port dwell analysis']
    },
    {
      factor: 'Pattern',
      component: 'Network Analysis',
      score: 3.5,
      weight: 10,
      weighted_result: 0.35,
      rationale: 'Shipper network shows patterns',
      evidence: ['Network Risk: Moderate', 'Related Entities: 3']
    },
    // Time Sensitivity (3 components)
    {
      factor: 'Time',
      component: 'Pre-Tariff Timing',
      score: 1.0,
      weight: 10,
      weighted_result: 0.1,
      rationale: 'No imminent tariff changes',
      evidence: ['Tariff Effective: No change', 'Days to Change: N/A']
    },
    {
      factor: 'Time',
      component: 'Seasonal Anomaly',
      score: 2.3,
      weight: 10,
      weighted_result: 0.23,
      rationale: 'Within seasonal baseline',
      evidence: ['Volume vs Baseline: +15%', 'Within normal range']
    },
    {
      factor: 'Time',
      component: 'Quota Timing Risk',
      score: 1.5,
      weight: 10,
      weighted_result: 0.15,
      rationale: 'No quota fill pressure',
      evidence: ['Quota Fill Level: 45%', 'Risk: Low']
    }
  ];

  const subtotal = components.reduce((sum, c) => sum + c.weighted_result, 0);
  const finalScore = Math.min(100, subtotal * 2);

  return {
    shipment_id: id,
    components,
    subtotal: Number(subtotal.toFixed(1)),
    final_score: Number(finalScore.toFixed(1)),
    confidence_interval: '±2.5',
    calculation_table: {
      calculation_steps: [
        { step: '1', description: 'Documentation Risk (25%)', value: 2.95 },
        { step: '2', description: 'Commodity Risk (15%)', value: 1.82 },
        { step: '3', description: 'Routing Risk (15%)', value: 1.55 },
        { step: '4', description: 'Party Risk (15%)', value: 1.275 },
        { step: '5', description: 'Corridor Risk (20%)', value: 2.1 },
        { step: '6', description: 'Pattern Risk (10%)', value: 1.44 },
        { step: '7', description: 'Time Risk (10%)', value: 0.48 }
      ]
    },
    corridor_risk_adjustment: {
      type: 'Corridor Risk Multiplier',
      reason: 'Vietnam-US corridor elevated risk (1.2x multiplier applied)',
      baseline: subtotal,
      multiplier: 1.2,
      adjustment_points: Number((subtotal * 0.2).toFixed(2))
    },
    additional_adjustments: []
  };
}

/**
 * Export breakdown as JSON string
 */
export function exportBreakdownAsJSON(breakdown: RiskScoreBreakdown): string {
  return JSON.stringify(breakdown, null, 2);
}

/**
 * Export breakdown as CSV string
 */
export function exportBreakdownAsCSV(breakdown: RiskScoreBreakdown): string {
  const rows: string[] = [];

  rows.push('Shipment ID,Component,Factor,Score,Weight %,Weighted Result');

  breakdown.components.forEach((comp) => {
    rows.push(
      `"${breakdown.shipment_id}","${comp.component}","${comp.factor}",${comp.score},${comp.weight},${comp.weighted_result}`
    );
  });

  rows.push('');
  rows.push(`Final Score,${breakdown.final_score}`);
  rows.push(`Confidence Interval,${breakdown.confidence_interval}`);

  return rows.join('\n');
}

/**
 * Format score to 1 decimal place
 */
export function formatScore(score: number, decimals: number = 1): string {
  return score.toFixed(decimals);
}
