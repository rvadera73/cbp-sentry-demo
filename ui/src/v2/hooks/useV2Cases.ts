import { useState, useEffect } from 'react';
import { Case, Shipment } from '../types/v2.types';
import { api } from '../../services/api';
import { API_BASE_URL } from '../../services/apiUrl';

interface UseV2CasesReturn {
  cases: Case[];
  shipments: Shipment[];
  caseShipments: Record<string, Shipment[]>;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

// HS code to commodity name mapping
const COMMODITY_MAP: Record<string, string> = {
  '7604': 'Aluminum Extrusions',
  '7610': 'Aluminum Structures',
  '7611': 'Aluminum Waste & Scrap',
  '8541': 'Semiconductor Devices & Solar Cells',
  '8517': 'Telecom Equipment',
  '2933': 'Pharmaceutical Compounds',
  '2942': 'Organic Chemicals',
  '7308': 'Steel Structures',
  '9999': 'General Merchandise',
};

function getCommodityName(hsCode: string): string {
  if (!hsCode) return 'General Merchandise';
  const prefix = hsCode.split('.')[0];
  return COMMODITY_MAP[prefix] || 'General Merchandise';
}

/**
 * Fetches shipments from API and maps to wireframe Case + Shipment types with corridor & commodity context
 */
export function useV2Cases(): UseV2CasesReturn {
  const [cases, setCases] = useState<Case[]>([]);
  const [shipments, setShipments] = useState<Shipment[]>([]);
  const [caseShipments, setCaseShipments] = useState<Record<string, Shipment[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const derivePriority = (riskScore: number): 'Critical' | 'High' | 'Medium' | 'Low' => {
    if (riskScore >= 80) return 'Critical';
    if (riskScore >= 60) return 'High';
    if (riskScore >= 40) return 'Medium';
    return 'Low';
  };

  const deriveCaseStatus = (riskScore: number): Case['case_status'] => {
    if (riskScore >= 75) return 'Active';
    if (riskScore >= 50) return 'Under Audit';
    return 'Referral Prepared';
  };

  const fetchCases = async () => {
    try {
      setLoading(true);
      setError(null);

      console.log('[useV2Cases] Starting fetch...');

      // Fetch elevated+critical risk shipments (risk >= 50)
      const params = new URLSearchParams({
        risk_min: '50',
        limit: '100',
        offset: '0'
      });

      const url = `${API_BASE_URL}/shipments?${params}`;
      console.log('[useV2Cases] Fetching from:', url);

      const response = await fetch(url);
      console.log('[useV2Cases] Response status:', response.status);

      if (!response.ok) {
        throw new Error(`Failed to fetch shipments: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('[useV2Cases] Full response object:', JSON.stringify(data).substring(0, 500));
      console.log('[useV2Cases] Data received:', data.data?.length, 'items, count:', data.count);
      const shipmentData = data.data || [];

      // Map shipments with all API fields
      const mappedShipments: Shipment[] = shipmentData.map((s: any): Shipment => {
        // Use the correct country fields from API response
        const originCountry = s.shipper_country || 'XX';
        const destCountry = s.consignee_country || 'US';

        // Parse h2_signals
        const h2Signals = Array.isArray(s.h2_signals) ? s.h2_signals :
                         typeof s.h2_signals === 'string' ? JSON.parse(s.h2_signals) : [];

        // Add ELEMENT9_MISMATCH to signals if mismatch detected
        const allSignals = [...h2Signals];
        if (s.element9_is_mismatch === 1 || s.element9_is_mismatch === true) {
          allSignals.push('ELEMENT9_MISMATCH');
        }

        // Parse port_calls
        // (originCountry and destCountry are already defined above)
        let portCalls = [originCountry, 'SG', destCountry];
        if (s.port_calls) {
          try {
            portCalls = typeof s.port_calls === 'string' ? JSON.parse(s.port_calls) : s.port_calls;
          } catch (e) {
            portCalls = [originCountry, 'SG', destCountry];
          }
        }

        return {
          shipment_id: s.id?.toString() || `SH-${Math.random().toString(36).substring(7)}`,
          origin_country: originCountry,
          destination_country: destCountry,
          declared_origin: s.element9_declared_country || s.shipper_country || 'XX',
          suspected_origin: s.element9_actual_country || originCountry || 'XX',
          product_code: s.commodity_code || s.hs_code || '9999',
          product_description: s.commodity_name || getCommodityName(s.commodity_code || s.hs_code),
          route: portCalls,
          container_id: s.id?.toString() || `CONT-${Math.random().toString(36).substring(7)}`,
          manifest_data: {
            shipper: s.shipper_name || 'Unknown',
            consignee: s.consignee_name || 'Unknown',
            weight_kg: s.declared_weight_kg || 0,
            declared_value_usd: s.declared_value || s.declared_value_usd || 0,
            carrier: s.vessel_name || 'Unknown Carrier',
            vessel: s.vessel_name || 'Unknown Vessel',
            voyage_number: s.voyage_number || '',
            bill_of_lading: s.bill_of_lading || '',
          },
          manifest_anomalies: allSignals,
          ai_anomaly_score: s.risk_score || 50,
          customs_flags: s.customs_flags ? (typeof s.customs_flags === 'string' ? JSON.parse(s.customs_flags) : s.customs_flags) : [],
          inspection_history: s.inspection_history || 'No recent inspections',
          date: s.created_at || new Date().toISOString().split('T')[0],

          // API Fields
          hs_code: s.commodity_code || s.hs_code,
          commodity_name: s.commodity_name || getCommodityName(s.commodity_code || s.hs_code),
          h1_score: s.h1_score || 0,
          h2_score: s.h2_score || 0,
          h3_score: Math.max(0, (s.risk_score || 0) - (s.h1_score || 0) - (s.h2_score || 0)),
          h1_risk_level: (s.h1_score || 0) >= 20 ? 'HIGH' : 'MEDIUM',
          h2_signals: h2Signals,
          h3_recommendation: s.h3_recommendation || 'EXAMINE',
          element9_is_mismatch: s.element9_is_mismatch === 1 || s.element9_is_mismatch === true,
          element9_declared_country: s.element9_declared_country,
          element9_actual_country: s.element9_actual_country,
          shipper_name: s.shipper_name,
          shipper_country: s.shipper_country,
          shipper_age_months: s.shipper_age_months,
          dwell_days: s.dwell_days,
          ad_cvd_applicable: s.ad_cvd_applicable === 1 || s.ad_cvd_applicable === true,
          ad_cvd_rate: s.ad_cvd_rate || 0,
          port_calls: portCalls,
          vessel_name: s.vessel_name,
          vessel_imo: s.vessel_imo,
          risk_score: s.risk_score || 50,

          // Risk Breakdown & Audit Trail
          risk_breakdown: s.risk_breakdown,
          audit_trail: s.audit_trail,
          ai_synthesis: s.ai_synthesis,
        };
      });

      setShipments(mappedShipments);

      // Group shipments by case (manifest_id)
      const groupedByManifest: Record<string, Shipment[]> = {};
      mappedShipments.forEach(s => {
        const caseId = s.manifest_data.shipper + '-' + s.origin_country + '-' + s.destination_country;
        if (!groupedByManifest[caseId]) {
          groupedByManifest[caseId] = [];
        }
        groupedByManifest[caseId].push(s);
      });
      setCaseShipments(groupedByManifest);

      // Map cases with corridor & commodity context
      const mappedCases: Case[] = Object.entries(groupedByManifest).map(([caseId, shipmentList], idx) => {
        const firstShipment = shipmentList[0];
        const riskScore = firstShipment.risk_score || 50;

        return {
          case_id: `CBP-${2026}-${9000 + idx}`,
          case_name: `${firstShipment.shipper_name || 'Unknown'} → ${firstShipment.manifest_data.consignee || 'Unknown'}`,
          target_entity: firstShipment.shipper_name || 'Unknown Entity',
          risk_score: riskScore,
          assigned_officer: 'Unassigned',
          investigation_stage: 'Overview',
          case_status: deriveCaseStatus(riskScore),
          referral_status: 'Not Initiated',
          priority: derivePriority(riskScore),
          opened_date: firstShipment.date,
          sla_timer: '21 Days Remaining',
          product_category: firstShipment.commodity_name || 'Unknown',
          ai_confidence: Math.min(100, Math.round(riskScore + 10 + Math.random() * 5)),

          // Commodity & Corridor
          commodity_code: firstShipment.hs_code,
          commodity_name: firstShipment.commodity_name,
          origin_country: firstShipment.origin_country,
          destination_country: firstShipment.destination_country,

          // Scoring Components
          h1_score: firstShipment.h1_score,
          h2_score: firstShipment.h2_score,
          h3_score: firstShipment.h3_score,

          // Tariff & Trade
          ad_cvd_applicable: firstShipment.ad_cvd_applicable,
          ad_cvd_rate: firstShipment.ad_cvd_rate,

          // Shipment Context
          shipper_age_months: firstShipment.shipper_age_months,
          declared_weight_kg: firstShipment.manifest_data.weight_kg,
          dwell_days: firstShipment.dwell_days,

          // Anomalies
          manifest_anomalies: firstShipment.manifest_anomalies,
        };
      });

      console.log(`[useV2Cases] Successfully mapped ${mappedCases.length} cases`);
      setCases(mappedCases);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch cases';
      setError(message);
      console.error('[useV2Cases] ERROR:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCases();
  }, []);

  return {
    cases,
    shipments,
    caseShipments,
    loading,
    error,
    refetch: fetchCases,
  };
}
