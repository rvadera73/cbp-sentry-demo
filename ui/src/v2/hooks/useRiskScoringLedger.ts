import { useState, useEffect } from 'react';

export interface RiskComponent {
  id: string;
  component_name: string;
  component_category: string;
  component_value: number;
  component_max: number;
  component_weight: number;
  weighted_value: number;
  evidence: string;
  data_source: string;
}

export interface RiskAdjustment {
  id: string;
  adjustment_type: string;
  adjustment_name: string;
  adjustment_amount: number;
  adjustment_multiplier: number;
  confidence_score: number;
  evidence_detail: string;
  data_source: string;
}

export interface RiskLedgerStep {
  id: string;
  ledger_step: number;
  step_name: string;
  step_description: string;
  input_value: number | null;
  operation: string;
  output_value: number;
  data_source: string;
}

export interface WhatIfScenario {
  id: string;
  scenario_name: string;
  scenario_description: string;
  scenario_priority: string;
  what_if_true_description: string;
  what_if_true_evidence_needed: string;
  what_if_true_risk_score: number;
  what_if_false_description: string;
  what_if_false_evidence_needed: string;
  what_if_false_risk_score: number;
  current_risk_score: number;
  impact_if_true: number;
  impact_if_false: number;
  impact_category: string;
  investigation_recommendation: string;
  data_source: string;
}

export interface RiskScoringLedger {
  shipment_id: string;
  shipment_summary: {
    shipper: string;
    consignee: string;
    corridor: string;
    commodity: string;
    risk_score: number;
    risk_classification: string;
    h1_score: number;
    h2_score: number;
    h3_score: number;
  };
  component_scores: Record<string, RiskComponent[]>;
  adjustments: RiskAdjustment[];
  calculation_ledger: RiskLedgerStep[];
  what_if_analysis: WhatIfScenario[];
  data_sources: {
    primary: string[];
    secondary: string[];
    tertiary: string[];
  };
}

export function useRiskScoringLedger(shipmentId: string | null) {
  const [ledger, setLedger] = useState<RiskScoringLedger | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!shipmentId) {
      setLedger(null);
      return;
    }

    const fetchLedger = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`/api/shipments/${shipmentId}/risk-scoring-ledger`);
        if (!response.ok) {
          throw new Error(`Failed to fetch risk scoring ledger: ${response.statusText}`);
        }
        const data = await response.json();
        setLedger(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
        console.error('Error fetching risk scoring ledger:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchLedger();
  }, [shipmentId]);

  return { ledger, loading, error };
}

export function useRiskComponents(shipmentId: string | null) {
  const [components, setComponents] = useState<Record<string, RiskComponent[]> | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!shipmentId) {
      setComponents(null);
      return;
    }

    const fetchComponents = async () => {
      setLoading(true);
      try {
        const response = await fetch(`/api/shipments/${shipmentId}/risk-components`);
        if (response.ok) {
          const data = await response.json();
          setComponents(data.components_by_category);
        }
      } finally {
        setLoading(false);
      }
    };

    fetchComponents();
  }, [shipmentId]);

  return { components, loading };
}

export function useWhatIfAnalysis(shipmentId: string | null) {
  const [scenarios, setScenarios] = useState<WhatIfScenario[] | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!shipmentId) {
      setScenarios(null);
      return;
    }

    const fetchScenarios = async () => {
      setLoading(true);
      try {
        const response = await fetch(`/api/shipments/${shipmentId}/what-if-analysis`);
        if (response.ok) {
          const data = await response.json();
          setScenarios(data.scenarios);
        }
      } finally {
        setLoading(false);
      }
    };

    fetchScenarios();
  }, [shipmentId]);

  return { scenarios, loading };
}
