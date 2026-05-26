import React, { useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle } from 'lucide-react';
import { useCorridorShipments } from '../hooks/useCorridorShipments';
import { Shipment } from '../types/v2.types';
import { computeShippingIntelligence } from '../hooks/useShippingIntelligence';
import InvestigationListTable, { ListItem } from '../components/InvestigationListTable';

interface UseActiveShipmentsReturn {
  shipments: Shipment[];
  loading: boolean;
  error: string | null;
  total: number;
}

function useActiveShipments(): UseActiveShipmentsReturn {
  const [shipments, setShipments] = useState<Shipment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);

  React.useEffect(() => {
    const fetchShipments = async () => {
      try {
        setLoading(true);
        const params = new URLSearchParams({
          risk_min: '50',
          limit: '100',
          offset: '0'
        });

        const response = await fetch(`/api/shipments?${params}`);
        if (!response.ok) {
          throw new Error(`Failed to fetch shipments: ${response.statusText}`);
        }

        const data = await response.json();
        const mappedShipments = (data.data || []).map((apiData: any): Shipment => {
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
        });
        setShipments(mappedShipments);
        setTotal(data.count || 0);
        setError(null);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error';
        setError(message);
        console.error('Error fetching active shipments:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchShipments();
  }, []);

  return { shipments, loading, error, total };
}

export default function V2ActiveShipmentsPage() {
  const navigate = useNavigate();
  const { shipments, loading, error, total } = useActiveShipments();
  const [searchQuery, setSearchQuery] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [riskFilter, setRiskFilter] = useState('all');

  const shipmentListItems = useMemo((): ListItem[] => {
    return shipments
      .filter(s => s.risk_score! >= 50)
      .map(s => ({
        id: s.shipment_id,
        risk_score: Math.round(s.risk_score || 0),
        name: s.shipper_name || 'Unknown',
        entity: s.manifest_data.consignee || 'Unknown',
        officer: s.manifest_data.carrier || 'Unassigned',
        commodity: s.commodity_name || 'General Merchandise',
        date: new Date(s.date || new Date()).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }),
        status: s.risk_score! >= 80 ? 'Critical' : 'Elevated',
        statusColor: s.risk_score! >= 80
          ? 'bg-[#D83933] text-white'
          : 'bg-amber-600 text-white',
      }));
  }, [shipments]);

  const filteredShipments = useMemo(() => {
    return shipmentListItems.filter(item => {
      const matchesSearch =
        item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.entity.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesRisk =
        riskFilter === 'all' ||
        (riskFilter === 'critical' && item.risk_score! >= 80) ||
        (riskFilter === 'elevated' && item.risk_score! >= 50 && item.risk_score! < 80);

      return matchesSearch && matchesRisk;
    });
  }, [shipmentListItems, searchQuery, riskFilter]);

  const handleAccessWorkspace = useCallback((shipmentId: string) => {
    navigate(`/investigations?shipmentId=${encodeURIComponent(shipmentId)}`);
  }, [navigate]);

  const handleClearFilters = useCallback(() => {
    setSearchQuery('');
    setPriorityFilter('all');
    setRiskFilter('all');
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full bg-[#F7F9FC]">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-[#005EA2]"></div>
          <p className="mt-4 text-[#5C5C5C]">Loading active shipments...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 p-5 flex flex-col space-y-5 overflow-y-auto bg-[#F7F9FC]">
      <InvestigationListTable
        items={filteredShipments}
        title="ACTIVE SHIPMENTS"
        subtitle="Manifest-filed shipments with elevated risk indicators"
        searchPlaceholder="Filter by shipper, consignee, or shipment ID..."
        onRowClick={() => {}}
        onAccessWorkspace={handleAccessWorkspace}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        priorityFilter={priorityFilter}
        onPriorityFilterChange={setPriorityFilter}
        riskFilter={riskFilter}
        onRiskFilterChange={setRiskFilter}
        onClearFilters={handleClearFilters}
        loading={loading}
      />
    </div>
  );
}
