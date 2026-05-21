import React, { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCommandCenter } from '../../context/CommandCenterContext';
import '../../styles/command-center/CommodityLens.css';

export default function CommodityLens() {
  const navigate = useNavigate();
  const { state, setFilters } = useCommandCenter();

  // Group corridors by industry segment
  const industryGroups = useMemo(() => {
    const groups: { [key: string]: typeof state.corridors } = {};
    state.corridors.forEach(corridor => {
      if (!groups[corridor.industry_segment]) {
        groups[corridor.industry_segment] = [];
      }
      groups[corridor.industry_segment].push(corridor);
    });
    return groups;
  }, [state.corridors]);

  // Calculate summary stats
  const summaryStats = useMemo(() => {
    return {
      total_active_corridors: state.corridors.length,
      high_risk_count: state.corridors.filter(c => c.risk_level === 'HIGH' || c.risk_level === 'CRITICAL').length,
      medium_risk_count: state.corridors.filter(c => c.risk_level === 'MEDIUM').length,
      aggregate_manifest_value: state.corridors.reduce((sum, c) => sum + c.aggregate_value_usd, 0),
    };
  }, [state.corridors]);

  const getRiskColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'CRITICAL':
      case 'HIGH':
        return '#D9381E';
      case 'MEDIUM':
        return '#E6A100';
      case 'LOW':
        return '#2E8540';
      default:
        return '#6B7280';
    }
  };

  const handleCorridorClick = (corridor: typeof state.corridors[0]) => {
    if (corridor.manifest_ids && corridor.manifest_ids.length > 0) {
      navigate(`/cases/${corridor.manifest_ids[0]}`);
    }
  };

  return (
    <div className="commodity-lens">
      <div className="commodity-lens__header">
        <h2>Commodity Lens</h2>
        <div className="commodity-lens__controls">
          <select
            value={state.filters.industry || ''}
            onChange={e => setFilters({ industry: e.target.value || undefined })}
            className="commodity-lens__filter"
            aria-label="Filter by industry segment"
          >
            <option value="">All Industries</option>
            <option value="Solar Infrastructure">Solar Infrastructure</option>
            <option value="Flat-Rolled Steel & Alloys">Flat-Rolled Steel & Alloys</option>
            <option value="Industrial Aluminum">Industrial Aluminum</option>
            <option value="Textiles">Textiles</option>
          </select>
        </div>
      </div>

      <div className="commodity-lens__summary">
        <div className="summary-card">
          <div className="summary-card__label">Active Corridors</div>
          <div className="summary-card__value">{summaryStats.total_active_corridors}</div>
        </div>
        <div className="summary-card">
          <div className="summary-card__label">High Risk</div>
          <div className="summary-card__value" style={{ color: '#D9381E' }}>
            {summaryStats.high_risk_count}
          </div>
        </div>
        <div className="summary-card">
          <div className="summary-card__label">Medium Risk</div>
          <div className="summary-card__value" style={{ color: '#E6A100' }}>
            {summaryStats.medium_risk_count}
          </div>
        </div>
        <div className="summary-card">
          <div className="summary-card__label">Aggregate Value</div>
          <div className="summary-card__value">${(summaryStats.aggregate_manifest_value / 1_000_000).toFixed(1)}M</div>
        </div>
      </div>

      <div className="commodity-lens__content">
        <h3>Active Corridors by Industry</h3>
        <div className="corridors-table">
          <div className="corridors-table__header">
            <div className="corridors-table__cell corridors-table__cell--hts">HTS</div>
            <div className="corridors-table__cell corridors-table__cell--segment">Industry Segment</div>
            <div className="corridors-table__cell corridors-table__cell--route">Route</div>
            <div className="corridors-table__cell corridors-table__cell--volume">Shipments</div>
            <div className="corridors-table__cell corridors-table__cell--value">Value</div>
            <div className="corridors-table__cell corridors-table__cell--surge">YoY Surge</div>
            <div className="corridors-table__cell corridors-table__cell--risk">Risk Level</div>
          </div>

          {Object.entries(industryGroups).map(([industry, corridors]) => (
            <div key={industry} className="corridors-table__group">
              {corridors
                .sort((a, b) => (b.yoy_volume_surge_pct || 0) - (a.yoy_volume_surge_pct || 0))
                .map(corridor => (
                  <div
                    key={corridor.corridor_id}
                    className="corridors-table__row"
                    onClick={() => handleCorridorClick(corridor)}
                    style={{ cursor: corridor.manifest_ids?.length ? 'pointer' : 'default' }}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        handleCorridorClick(corridor);
                      }
                    }}
                    aria-label={`View case details for ${corridor.hts_6digit} ${corridor.origin_country}→${corridor.destination_country}`}
                  >
                    <div className="corridors-table__cell corridors-table__cell--hts">
                      <code>{corridor.hts_6digit}</code>
                    </div>
                    <div className="corridors-table__cell corridors-table__cell--segment">{industry}</div>
                    <div className="corridors-table__cell corridors-table__cell--route">
                      {corridor.origin_country}→{corridor.destination_country}
                    </div>
                    <div className="corridors-table__cell corridors-table__cell--volume">
                      {corridor.shipment_count}
                    </div>
                    <div className="corridors-table__cell corridors-table__cell--value">
                      ${(corridor.aggregate_value_usd / 1_000).toFixed(0)}K
                    </div>
                    <div className="corridors-table__cell corridors-table__cell--surge">
                      <span
                        style={{
                          color: (corridor.yoy_volume_surge_pct || 0) > 250 ? '#D9381E' : '#E6A100',
                        }}
                      >
                        +{(corridor.yoy_volume_surge_pct || 0).toFixed(0)}%
                      </span>
                    </div>
                    <div
                      className="corridors-table__cell corridors-table__cell--risk"
                      style={{ color: getRiskColor(corridor.risk_level) }}
                    >
                      {corridor.risk_level}
                    </div>
                  </div>
                ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
