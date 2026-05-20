import { useState } from 'react';
import { Case } from '../../types/models';
import SearchBar from '../common/SearchBar';
import FilterSelect from '../common/FilterSelect';
import RiskBadge from '../common/RiskBadge';

interface Props {
  cases: Case[];
  selectedCase: Case | null;
  onSelectCase: (c: Case) => void;
}

export default function CaseQueue({ cases, selectedCase, onSelectCase }: Props) {
  const [filterRisk, setFilterRisk] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');

  const getRiskLabel = (score: number) => {
    if (score >= 70) return 'HIGH';
    if (score >= 50) return 'MEDIUM';
    return 'LOW';
  };

  const filteredCases = cases.filter((c) => {
    const riskTier = getRiskLabel(c.risk_score);
    if (filterRisk !== 'all' && riskTier !== filterRisk) return false;

    const searchStr = searchTerm.toLowerCase();
    return (
      c.shipper_name.toLowerCase().includes(searchStr) ||
      c.consignee_name.toLowerCase().includes(searchStr) ||
      c.commodity_code.includes(searchStr)
    );
  });

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <h2 className="text-lg font-bold text-gray-900 mb-4">CASE QUEUE</h2>

        {/* Search */}
        <SearchBar
          value={searchTerm}
          onChange={setSearchTerm}
          placeholder="Search cases..."
          className="mb-3"
        />

        {/* Filter */}
        <FilterSelect
          value={filterRisk}
          onChange={setFilterRisk}
          label="Risk Level"
          options={[
            { value: 'all', label: 'All Risks' },
            { value: 'HIGH', label: 'High Risk' },
            { value: 'MEDIUM', label: 'Medium Risk' },
            { value: 'LOW', label: 'Low Risk' }
          ]}
        />

        {/* Count */}
        <p className="text-xs text-gray-500 mt-2">
          {filteredCases.length} of {cases.length} cases
        </p>
      </div>

      {/* Cases List */}
      <div className="flex-1 overflow-y-auto">
        {filteredCases.length === 0 ? (
          <div className="p-4 text-center">
            <p className="text-sm text-gray-500">No cases match your filter</p>
          </div>
        ) : (
          <div className="space-y-2 p-3">
            {filteredCases.map((c) => {
              const riskScore = Math.round(c.risk_score || 0);
              const isSelected = selectedCase?.id === c.id;

              return (
                <button
                  key={c.id}
                  onClick={() => onSelectCase(c)}
                  className={`w-full text-left p-3 rounded-lg border-2 transition-all ${
                    isSelected
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  {/* Risk Badge + Score */}
                  <div className="flex items-center gap-2 mb-2">
                    <RiskBadge score={riskScore} size="sm" />
                  </div>

                  {/* Case ID */}
                  <p className="text-xs text-gray-500 font-mono mb-1">
                    {c.id.substring(0, 8)}
                  </p>

                  {/* Shipper → Consignee */}
                  <p className="text-sm font-semibold text-gray-900 truncate">
                    {c.shipper_name}
                  </p>
                  <p className="text-xs text-gray-600 truncate">
                    {c.shipper_country} → {c.consignee_country}
                  </p>

                  {/* HTS Code + Commodity */}
                  <p className="text-xs text-gray-700 mt-1">
                    HTS {c.commodity_code}
                  </p>

                  {/* Value */}
                  <p className="text-xs text-gray-500 mt-1">
                    ${(c.declared_value || 0).toLocaleString()}
                  </p>

                  {/* Created Date */}
                  <p className="text-xs text-gray-400 mt-2">
                    {new Date(c.created_at).toLocaleDateString()}
                  </p>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
