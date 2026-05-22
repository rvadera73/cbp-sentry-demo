import { useState, useEffect } from 'react';
import { Case, Shipment } from '../types/v2.types';
import { api } from '../../services/api';

interface UseV2CasesReturn {
  cases: Case[];
  shipments: Shipment[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

/**
 * Fetches shipments from API and maps to wireframe Case type
 */
export function useV2Cases(): UseV2CasesReturn {
  const [cases, setCases] = useState<Case[]>([]);
  const [shipments, setShipments] = useState<Shipment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const derivePriority = (riskScore: number): 'Critical' | 'High' | 'Medium' | 'Low' => {
    if (riskScore >= 90) return 'Critical';
    if (riskScore >= 70) return 'High';
    if (riskScore >= 50) return 'Medium';
    return 'Low';
  };

  const deriveCaseStatus = (status?: string): Case['case_status'] => {
    if (!status) return 'Active';
    const s = status.toLowerCase();
    if (s.includes('closed')) return 'Closed';
    if (s.includes('enforced')) return 'Enforced';
    if (s.includes('referral')) return 'Referral Prepared';
    if (s.includes('audit')) return 'Under Audit';
    return 'Active';
  };

  const fetchCases = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await api.getShipments(50, 0);
      const shipmentData = response.shipments || [];

      setShipments(
        shipmentData.map((s: any): Shipment => ({
          shipment_id: s.id || `SH-${Math.random()}`,
          origin_country: s.origin_country || 'Unknown',
          destination_country: s.destination_country || 'USA',
          declared_origin: s.shipper_country || 'Unknown',
          suspected_origin: s.origin_country !== s.shipper_country ? s.origin_country : s.origin_country,
          product_code: s.commodity_code || '',
          product_description: s.commodity_name || 'Unknown Commodity',
          route: s.route || [s.origin_country, s.destination_country],
          container_id: s.container_id || `CONT-${Math.random()}`,
          manifest_data: {
            shipper: s.shipper_name || 'Unknown',
            consignee: s.consignee_name || 'Unknown',
            weight_kg: s.weight_kg || 0,
            declared_value_usd: s.declared_value || 0,
            carrier: s.carrier || 'Unknown Carrier',
            vessel: s.vessel || 'Unknown Vessel',
            voyage_number: s.voyage_number || 'Unknown',
            bill_of_lading: s.bill_of_lading || 'Unknown',
          },
          manifest_anomalies: s.h2_signals || [],
          ai_anomaly_score: Math.round(s.risk_score || 0),
          customs_flags: [],
          inspection_history: '',
          date: s.created_at || new Date().toISOString().split('T')[0],
        }))
      );

      const mappedCases: Case[] = shipmentData.map((s: any, idx: number): Case => ({
        case_id: s.id || `CBP-2026-${1000 + idx}`,
        case_name: `${s.shipper_name || 'Unknown'} Import Investigation`,
        target_entity: `${s.shipper_name || 'Unknown'} / ${s.consignee_name || 'Unknown'}`,
        risk_score: Math.round(s.risk_score || 0),
        assigned_officer: 'Rav J. D.',
        investigation_stage: 'Overview',
        case_status: deriveCaseStatus(s.status),
        referral_status: 'Not Initiated',
        priority: derivePriority(s.risk_score || 0),
        opened_date: s.created_at || new Date().toISOString().split('T')[0],
        sla_timer: '14 days',
        product_category: s.commodity_name || 'Unknown',
        ai_confidence: Math.min(100, Math.round((s.risk_score || 0) + Math.random() * 20)),
        ai_synopsis: undefined,
      }));

      setCases(mappedCases);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch cases';
      setError(message);
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
    loading,
    error,
    refetch: fetchCases,
  };
}
