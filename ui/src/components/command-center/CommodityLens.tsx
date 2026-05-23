import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getRiskLevel, getRiskBorderColor } from '../../utils/risk';
import '../../styles/command-center/CommodityLens.css';

interface Corridor {
  id: string;
  route: string;
  industry: string;
  hs_code: string;
  shipment_count: number;
  aggregate_value: number;
  yoy_surge?: {
    volume_surge_pct: number;
    value_surge_pct: number;
  };
  risk_level: string;
}

interface CommodityLensProps {
  corridors?: Corridor[];
}

export default function CommodityLens({ corridors = [] }: CommodityLensProps) {
  const navigate = useNavigate();
  const [industryFilter, setIndustryFilter] = useState<string | undefined>();

  // Get unique industries
  const industries = useMemo(() => {
    return [...new Set(corridors.map(c => c.industry))].sort();
  }, [corridors]);

  // Group corridors by industry segment
  const industryGroups = useMemo(() => {
    const groups: { [key: string]: Corridor[] } = {};
    corridors.forEach(corridor => {
      if (!groups[corridor.industry]) {
        groups[corridor.industry] = [];
      }
      groups[corridor.industry].push(corridor);
    });
    return groups;
  }, [corridors]);

  // Calculate summary stats
  const summaryStats = useMemo(() => {
    return {
      total_active_corridors: corridors.length,
      high_risk_count: corridors.filter(c => getRiskLevel(70) === 'HIGH').length,
      medium_risk_count: corridors.filter(c => getRiskLevel(50) === 'MEDIUM').length,
      aggregate_manifest_value: corridors.reduce((sum, c) => sum + (c.aggregate_value || 0), 0),
    };
  }, [corridors]);

  const handleCorridorClick = (corridor: Corridor) => {
    navigate(`/command-center?focus=${corridor.id}`);
  };

  return (
    <div className="commodity-lens">
      <div className="commodity-lens__header">
        <h2>Commodity Lens</h2>
        <div className="commodity-lens__controls">
          <select
            value={industryFilter || ''}
            onChange={e => setIndustryFilter(e.target.value || undefined)}
            className="commodity-lens__filter"
            aria-label="Filter by industry segment"
          >
            <option value="">All Industries</option>
            {industries.map(industry => (
              <option key={industry} value={industry}>
                {industry}
              </option>
            ))}
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
          <div className="summary-card__value" style={{ color: '#d9381e' }}>
            {summaryStats.high_risk_count}
          </div>
        </div>
        <div className="summary-card">
          <div className="summary-card__label">Medium Risk</div>
          <div className="summary-card__value" style={{ color: '#e6a100' }}>
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
        {corridors.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#666' }}>
            No corridor data available. Upload a manifest to get started.
          </div>
        ) : (
          <div className="corridors-table">
            <div className="corridors-table__header">
              <div className="corridors-table__cell corridors-table__cell--hts">HTS</div>
              <div className="corridors-table__cell corridors-table__cell--segment">Industry</div>
              <div className="corridors-table__cell corridors-table__cell--route">Route</div>
              <div className="corridors-table__cell corridors-table__cell--volume">Shipments</div>
              <div className="corridors-table__cell corridors-table__cell--value">Value</div>
              <div className="corridors-table__cell corridors-table__cell--surge">YoY Surge</div>
              <div className="corridors-table__cell corridors-table__cell--risk">Risk Level</div>
            </div>

            {Object.entries(industryGroups).map(([industry, industryCorridors]) => (
              (!industryFilter || industryFilter === industry) && (
                <div key={industry} className="corridors-table__group">
                  {industryCorridors
                    .sort((a, b) => (b.yoy_surge?.volume_surge_pct || 0) - (a.yoy_surge?.volume_surge_pct || 0))
                    .map(corridor => (
                      <div
                        key={corridor.id}
                        className="corridors-table__row"
                        onClick={() => handleCorridorClick(corridor)}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            handleCorridorClick(corridor);
                          }
                        }}
                        aria-label={`Corridor: ${corridor.hs_code} ${corridor.route}`}
                      >
                        <div className="corridors-table__cell corridors-table__cell--hts">
                          <code>{corridor.hs_code}</code>
                        </div>
                        <div className="corridors-table__cell corridors-table__cell--segment">{industry}</div>
                        <div className="corridors-table__cell corridors-table__cell--route">
                          {corridor.route}
                        </div>
                        <div className="corridors-table__cell corridors-table__cell--volume">
                          {corridor.shipment_count}
                        </div>
                        <div className="corridors-table__cell corridors-table__cell--value">
                          ${(corridor.aggregate_value / 1_000).toFixed(0)}K
                        </div>
                        <div className="corridors-table__cell corridors-table__cell--surge">
                          <span
                            style={{
                              color: (corridor.yoy_surge?.volume_surge_pct || 0) > 250 ? '#d9381e' : '#e6a100',
                            }}
                          >
                            +{(corridor.yoy_surge?.volume_surge_pct || 0).toFixed(0)}%
                          </span>
                        </div>
                        <div className={`corridors-table__cell corridors-table__cell--risk risk-${corridor.risk_level.toLowerCase()}`}>
                          {corridor.risk_level}
                        </div>
                      </div>
                    ))}
                </div>
              )
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
