/**
 * Risk Scoring System - TypeScript Type Definitions
 * Complete type safety for 7-factor risk model
 */

export interface RiskComponent {
  factor: string;
  component: string;
  score: number;
  weight: number;
  weighted_result: number;
  rationale: string;
  evidence: string[];
}

export interface CalculationStep {
  step: string;
  description: string;
  value: number;
}

export interface CalculationTable {
  calculation_steps: CalculationStep[];
}

export interface Adjustment {
  type: string;
  reason: string;
  adjustment_points: number;
  baseline?: number;
  multiplier?: number;
}

export interface RiskScoreBreakdown {
  shipment_id: string;
  components: RiskComponent[];
  subtotal: number;
  final_score: number;
  confidence_interval: string;
  calculation_table?: CalculationTable;
  corridor_risk_adjustment?: Adjustment;
  additional_adjustments?: Adjustment[];
}

export interface RiskScoreBreakdownComponentProps {
  data: RiskScoreBreakdown;
  loading?: boolean;
  error?: string;
  onRefresh?: () => void;
}

export interface RiskScoreHeaderProps {
  score: number;
  confidence: string;
  riskLevel: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
}

export interface RiskComponentTableProps {
  components: RiskComponent[];
}
