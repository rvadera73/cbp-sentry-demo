import { useState, useEffect } from 'react';
import { Shipment } from '../types/v2.types';

interface UseCorridorShipmentsReturn {
  shipments: Shipment[];
  loading: boolean;
  error: string | null;
  total: number;
}

function mapApiResponseToShipment(apiData: any): Shipment {
  const originCountry = apiData.shipper_country || 'XX';
  const destCountry = apiData.consignee_country || 'US';

  return {
    shipment_id: apiData.id || apiData.shipment_id || '',
    origin_country: originCountry,
    destination_country: destCountry,
    declared_origin: apiData.element9_declared_country || originCountry,
    suspected_origin: apiData.element9_actual_country || originCountry,
    product_code: apiData.commodity_code || apiData.hs_code || '9999',
    product_description: apiData.commodity_name || 'General Merchandise',
    route: [originCountry, destCountry],
    container_id: apiData.id || '',
    manifest_data: {
      shipper: apiData.shipper_name || 'Unknown',
      consignee: apiData.consignee_name || 'Unknown',
      weight_kg: apiData.declared_weight_kg || 0,
      declared_value_usd: apiData.declared_value || 0,
      carrier: apiData.vessel_name || 'Unknown',
      vessel: apiData.vessel_name || 'Unknown',
      voyage_number: apiData.voyage_number || '',
      bill_of_lading: apiData.bill_of_lading || '',
    },
    manifest_anomalies: apiData.h2_signals || [],
    ai_anomaly_score: apiData.risk_score || 0,
    customs_flags: [],
    inspection_history: 'No recent inspections',
    date: apiData.created_at || new Date().toISOString(),

    hs_code: apiData.commodity_code || apiData.hs_code,
    commodity_name: apiData.commodity_name,
    h1_score: apiData.h1_score || 0,
    h2_score: apiData.h2_score || 0,
    h3_score: apiData.h3_score || 0,
    h2_signals: apiData.h2_signals || [],
    h3_recommendation: apiData.h3_recommendation || 'EXAMINE',
    element9_is_mismatch: apiData.element9_is_mismatch === 1 || apiData.element9_is_mismatch === true,
    element9_declared_country: apiData.element9_declared_country,
    element9_actual_country: apiData.element9_actual_country,
    shipper_name: apiData.shipper_name,
    shipper_country: apiData.shipper_country,
    risk_score: apiData.risk_score || 0,
  };
}

export function useCorridorShipments(corridorId?: string): UseCorridorShipmentsReturn {
  const [shipments, setShipments] = useState<Shipment[]>([]);
  const [loading, setLoading] = useState(!!corridorId);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    if (!corridorId) {
      setShipments([]);
      setTotal(0);
      setError(null);
      setLoading(false);
      return;
    }

    const fetchShipments = async () => {
      try {
        setLoading(true);
        const params = new URLSearchParams({
          corridor_id: corridorId,
          limit: '100',
          offset: '0'
        });

        const response = await fetch(`/api/shipments?${params}`);
        if (!response.ok) {
          throw new Error(`Failed to fetch shipments: ${response.statusText}`);
        }

        const data = await response.json();
        const mappedShipments = (data.data || []).map(mapApiResponseToShipment);
        setShipments(mappedShipments);
        setTotal(data.count || 0);
        setError(null);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error';
        setError(message);
        console.error('Error fetching corridor shipments:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchShipments();
  }, [corridorId]);

  return {
    shipments,
    loading,
    error,
    total,
  };
}
