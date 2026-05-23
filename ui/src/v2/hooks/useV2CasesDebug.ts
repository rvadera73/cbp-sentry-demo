/**
 * DEBUG VERSION: useV2Cases with console logging to verify data flow
 * Use this to diagnose why risk_breakdown isn't showing in UI
 */

import { useState, useEffect } from 'react';
import { Case, Shipment } from '../types/v2.types';
import { api } from '../../services/api';

interface UseV2CasesReturn {
  cases: Case[];
  shipments: Shipment[];
  caseShipments: Record<string, Shipment[]>;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  debugInfo: {
    fetchedShipments: number;
    enrichedShipments: number;
    failedEnrichments: number;
    sampleRiskBreakdown: any;
  };
}

const COMMODITY_MAP: Record<string, string> = {
  '7604': 'Aluminum Extrusions',
  '7610': 'Aluminum Structures',
  '8541': 'Semiconductor Devices',
};

export function useV2CasesDebug(): UseV2CasesReturn {
  const [cases, setCases] = useState<Case[]>([]);
  const [shipments, setShipments] = useState<Shipment[]>([]);
  const [caseShipments, setCaseShipments] = useState<Record<string, Shipment[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [debugInfo, setDebugInfo] = useState({
    fetchedShipments: 0,
    enrichedShipments: 0,
    failedEnrichments: 0,
    sampleRiskBreakdown: null,
  });

  const fetchCases = async () => {
    try {
      setLoading(true);
      setError(null);

      console.log('[useV2CasesDebug] Starting fetch...');

      const response = await api.getShipments(50, 0);
      let shipmentData = response.shipments || [];

      console.log(`[useV2CasesDebug] Fetched ${shipmentData.length} shipments from API`);

      // Enrich with risk breakdown
      const enrichedShipments = await Promise.all(
        shipmentData.map(async (s: any, idx: number) => {
          try {
            const shipmentId = s.id?.toString() || s.shipment_id;
            console.log(`[useV2CasesDebug] Fetching breakdown for shipment ${idx + 1}/${shipmentData.length}: ${shipmentId}`);

            const response = await fetch(`/api/data/shipments/${shipmentId}?include_breakdown=true`, {
              method: 'GET',
              headers: { 'Content-Type': 'application/json' }
            });

            if (response.ok) {
              const enrichedShipment = await response.json();
              console.log(`[useV2CasesDebug] ✓ Enriched ${shipmentId}:`, {
                hasBreakdown: !!enrichedShipment.risk_breakdown,
                hasAuditTrail: !!enrichedShipment.audit_trail,
                score: enrichedShipment.risk_score,
                componentsCount: enrichedShipment.risk_breakdown?.components?.length || 0
              });

              // Save first sample for debug
              if (idx === 0) {
                setDebugInfo(prev => ({
                  ...prev,
                  sampleRiskBreakdown: enrichedShipment.risk_breakdown,
                  enrichedShipments: prev.enrichedShipments + 1
                }));
              } else {
                setDebugInfo(prev => ({
                  ...prev,
                  enrichedShipments: prev.enrichedShipments + 1
                }));
              }

              return {
                ...s,
                risk_breakdown: enrichedShipment.risk_breakdown,
                audit_trail: enrichedShipment.audit_trail,
                ai_synthesis: enrichedShipment.ai_synthesis,
                risk_score: enrichedShipment.risk_score || s.risk_score
              };
            } else {
              console.warn(`[useV2CasesDebug] ✗ Failed to fetch ${shipmentId}: ${response.status}`);
              setDebugInfo(prev => ({
                ...prev,
                failedEnrichments: prev.failedEnrichments + 1
              }));
              return s;
            }
          } catch (e) {
            console.error(`[useV2CasesDebug] ✗ Error enriching shipment ${idx}:`, e);
            setDebugInfo(prev => ({
              ...prev,
              failedEnrichments: prev.failedEnrichments + 1
            }));
            return s;
          }
        })
      );

      console.log(`[useV2CasesDebug] Enrichment complete:`, debugInfo);

      setShipments(enrichedShipments);
      setDebugInfo(prev => ({
        ...prev,
        fetchedShipments: shipmentData.length
      }));

      // Rest of logic...
      setCases(enrichedShipments.map((s, idx) => ({
        case_id: `CBP-${2026}-${9000 + idx}`,
        case_name: s.shipper_name || 'Unknown',
        target_entity: s.shipper_name || 'Unknown',
        risk_score: s.risk_score || 50,
        priority: (s.risk_score || 50) >= 80 ? 'Critical' : 'High',
        case_status: 'Active',
        assigned_officer: 'Unassigned',
        investigation_stage: 'Overview',
        referral_status: 'Not Initiated',
        opened_date: s.date,
        sla_timer: '21 Days',
        product_category: s.commodity_name || 'Unknown',
        ai_confidence: Math.round((s.risk_score || 50) + 10),
        commodity_code: s.hs_code,
        commodity_name: s.commodity_name,
        origin_country: s.origin_country,
        destination_country: s.destination_country,
        h1_score: s.h1_score || 0,
        h2_score: s.h2_score || 0,
        h3_score: Math.max(0, (s.risk_score || 0) - (s.h1_score || 0) - (s.h2_score || 0)),
      })));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch cases';
      console.error('[useV2CasesDebug] Fatal error:', message);
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
    caseShipments,
    loading,
    error,
    refetch: fetchCases,
    debugInfo
  };
}
