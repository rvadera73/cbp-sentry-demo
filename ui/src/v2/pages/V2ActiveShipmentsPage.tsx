import React, { useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle } from 'lucide-react';
import { useV2Cases } from '../hooks/useV2Cases';
import { computeShippingIntelligence } from '../hooks/useShippingIntelligence';
import InvestigationListTable, { ListItem } from '../components/InvestigationListTable';


export default function V2ActiveShipmentsPage() {
  const navigate = useNavigate();
  const { shipments, loading, error } = useV2Cases();
  const [searchQuery, setSearchQuery] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [riskFilter, setRiskFilter] = useState('all');

  const shipmentListItems = useMemo((): ListItem[] => {
    return shipments
      .filter(s => (s.calculated_risk_score ?? s.risk_score ?? 0) >= 50)
      .map(s => {
        const displayScore = Math.round(s.calculated_risk_score ?? s.risk_score ?? 0);
        return {
          id: s.shipment_id,
          risk_score: displayScore,
          model_maturity: s.model_maturity,
          model_version: s.model_version,
          risk_score_calculated_at: s.risk_score_calculated_at,
          name: s.shipper_name || 'Unknown',
          entity: s.manifest_data.consignee || 'Unknown',
          officer: s.manifest_data.carrier || 'Unassigned',
          commodity: s.commodity_name || 'General Merchandise',
          date: new Date(s.date || new Date()).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }),
          status: displayScore >= 80 ? 'Critical' : 'Elevated',
          statusColor: displayScore >= 80
            ? 'bg-[#D83933] text-white'
            : 'bg-amber-600 text-white',
        };
      });
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
