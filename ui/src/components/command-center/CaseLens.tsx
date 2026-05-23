import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search } from 'lucide-react';
import { getRiskLevel, getRiskBackgroundColor, getRiskBorderColor } from '../../utils/risk';
import '../../styles/command-center/CaseLens.css';

interface Case {
  id: string;
  manifest_id: string;
  shipper_name: string;
  consignee_name: string;
  origin_country: string;
  destination_country: string;
  commodity_code: string;
  declared_value: number;
  risk_score: number;
  status: string;
}

interface CaseLensProps {
  cases?: Case[];
  loading?: boolean;
}

export default function CaseLens({ cases = [], loading = false }: CaseLensProps) {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [riskFilter, setRiskFilter] = useState<'all' | 'high' | 'medium' | 'low'>('all');
  const [sortBy, setSortBy] = useState<'risk' | 'value'>('risk');

  const getRiskBadge = (riskScore: number) => {
    const level = getRiskLevel(riskScore);
    return level.toUpperCase();
  };

  // Filter and sort cases
  const filteredCases = useMemo(() => {
    let filtered = cases.filter(c => {
      const matchesSearch = searchQuery === '' ||
        c.shipper_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.consignee_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.manifest_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.commodity_code.includes(searchQuery);

      const riskLevel = getRiskLevel(c.risk_score || 0).toLowerCase() as 'high' | 'medium' | 'low';
      const matchesRisk = riskFilter === 'all' || riskLevel === riskFilter;

      return matchesSearch && matchesRisk;
    });

    // Sort
    if (sortBy === 'risk') {
      filtered.sort((a, b) => (b.risk_score || 0) - (a.risk_score || 0));
    } else {
      filtered.sort((a, b) => (b.declared_value || 0) - (a.declared_value || 0));
    }

    return filtered;
  }, [cases, searchQuery, riskFilter, sortBy]);

  const handleCaseClick = (caseItem: Case) => {
    navigate(`/cases/${caseItem.id}`);
  };

  const highRiskCount = cases.filter(c => (c.risk_score || 0) >= 70).length;

  return (
    <div className="case-lens">
      <div className="case-lens__header">
        <h2>Active Cases</h2>
        <div className="case-lens__summary">
          <span className="case-count">Total: {cases.length}</span>
          <span className="high-risk-count">High Risk: {highRiskCount}</span>
        </div>
      </div>

      {loading ? (
        <div className="case-lens__loading">Loading cases...</div>
      ) : (
        <div className="case-lens__content">
          {/* Controls */}
          <div className="case-lens__controls">
            <input
              type="text"
              className="case-lens__search"
              placeholder="Search by Shipper, Consignee, ID, or HTS code..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label="Search cases"
            />

            <div className="case-lens__filters">
              <select
                className="case-lens__filter-select"
                value={riskFilter}
                onChange={(e) => setRiskFilter(e.target.value as 'all' | 'high' | 'medium' | 'low')}
                aria-label="Filter by risk level"
              >
                <option value="all">All Risk Levels</option>
                <option value="high">High Risk (70+)</option>
                <option value="medium">Medium Risk (40-69)</option>
                <option value="low">Low Risk (&lt;40)</option>
              </select>

              <select
                className="case-lens__sort-select"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as 'risk' | 'value')}
                aria-label="Sort by"
              >
                <option value="risk">Sort by Risk (High→Low)</option>
                <option value="value">Sort by Value (High→Low)</option>
              </select>
            </div>
          </div>

          {/* Results info */}
          <div className="case-lens__results-info">
            Showing {filteredCases.length} of {cases.length} cases
            {searchQuery && ` (search: "${searchQuery}")`}
            {riskFilter !== 'all' && ` (${riskFilter} risk)`}
          </div>

          {/* Table */}
          <div className="cases-table">
            <div className="cases-table__header">
              <div className="cases-table__cell cases-table__cell--risk">Risk</div>
              <div className="cases-table__cell cases-table__cell--shipper">Shipper</div>
              <div className="cases-table__cell cases-table__cell--consignee">Consignee</div>
              <div className="cases-table__cell cases-table__cell--route">Route</div>
              <div className="cases-table__cell cases-table__cell--hs">HTS</div>
              <div className="cases-table__cell cases-table__cell--value">Value</div>
              <div className="cases-table__cell cases-table__cell--status">Status</div>
            </div>

            <div className="cases-table__body">
              {filteredCases.length === 0 ? (
                <div className="cases-table__empty">
                  {searchQuery || riskFilter !== 'all'
                    ? 'No cases match your filters. Try adjusting your search.'
                    : 'No cases found'}
                </div>
              ) : (
                filteredCases.map(caseItem => (
                  <div
                    key={caseItem.manifest_id}
                    className="cases-table__row cases-table__row--clickable"
                    onClick={() => handleCaseClick(caseItem)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        handleCaseClick(caseItem);
                      }
                    }}
                    aria-label={`Click to view case ${caseItem.manifest_id}`}
                  >
                    <div className={`cases-table__cell cases-table__cell--risk risk-${getRiskLevel(caseItem.risk_score || 0).toLowerCase()}`}>
                      <span className="risk-badge">
                        {getRiskBadge(caseItem.risk_score || 0)}
                      </span>
                      <span className="risk-score">{(caseItem.risk_score || 0).toFixed(0)}</span>
                    </div>
                    <div className="cases-table__cell cases-table__cell--shipper">
                      {caseItem.shipper_name}
                    </div>
                    <div className="cases-table__cell cases-table__cell--consignee">
                      {caseItem.consignee_name}
                    </div>
                    <div className="cases-table__cell cases-table__cell--route">
                      {caseItem.origin_country}→{caseItem.destination_country}
                    </div>
                    <div className="cases-table__cell cases-table__cell--hs">
                      <code>{caseItem.commodity_code}</code>
                    </div>
                    <div className="cases-table__cell cases-table__cell--value">
                      ${(caseItem.declared_value / 1000).toFixed(1)}K
                    </div>
                    <div className="cases-table__cell cases-table__cell--status">
                      {caseItem.status}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
