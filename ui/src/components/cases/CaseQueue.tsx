import { useState, useMemo } from 'react';
import { Case } from '../../types/models';
import SearchBar from '../common/SearchBar';
import FilterSelect from '../common/FilterSelect';
import RiskBadge from '../common/RiskBadge';

interface Props {
  cases: Case[];
  selectedCase: Case | null;
  onSelectCase: (c: Case) => void;
}

type SortOption = 'risk-desc' | 'risk-asc' | 'date-newest' | 'date-oldest' | 'shipper' | 'origin';

export default function CaseQueue({ cases, selectedCase, onSelectCase }: Props) {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState<SortOption>('risk-desc');
  const [filterRisk, setFilterRisk] = useState<string>('all');
  const [filterOrigin, setFilterOrigin] = useState<string>('all');
  const [filterDestination, setFilterDestination] = useState<string>('all');
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);

  const getRiskLabel = (score: number) => {
    if (score >= 70) return 'HIGH';
    if (score >= 50) return 'MEDIUM';
    return 'LOW';
  };

  // Get unique origin and destination countries for filters
  const uniqueOrigins = useMemo(() => {
    const origins = new Set(cases.map(c => c.shipper_country).filter(Boolean));
    return Array.from(origins).sort();
  }, [cases]);

  const uniqueDestinations = useMemo(() => {
    const destinations = new Set(cases.map(c => c.consignee_country).filter(Boolean));
    return Array.from(destinations).sort();
  }, [cases]);

  // Filter and sort cases
  const processedCases = useMemo(() => {
    let filtered = cases.filter((c) => {
      // Risk filter
      const riskTier = getRiskLabel(c.risk_score);
      if (filterRisk !== 'all' && riskTier !== filterRisk) return false;

      // Origin filter
      if (filterOrigin !== 'all' && c.shipper_country !== filterOrigin) return false;

      // Destination filter
      if (filterDestination !== 'all' && c.consignee_country !== filterDestination) return false;

      // Search filter
      const searchStr = searchTerm.toLowerCase();
      return (
        c.shipper_name.toLowerCase().includes(searchStr) ||
        c.consignee_name.toLowerCase().includes(searchStr) ||
        c.commodity_code.includes(searchStr) ||
        c.id.toLowerCase().includes(searchStr) ||
        c.manifest_id.toLowerCase().includes(searchStr)
      );
    });

    // Sort
    const sorted = [...filtered].sort((a, b) => {
      switch (sortBy) {
        case 'risk-desc':
          return (b.risk_score || 0) - (a.risk_score || 0);
        case 'risk-asc':
          return (a.risk_score || 0) - (b.risk_score || 0);
        case 'date-newest':
          return new Date(b.created_at || '').getTime() - new Date(a.created_at || '').getTime();
        case 'date-oldest':
          return new Date(a.created_at || '').getTime() - new Date(b.created_at || '').getTime();
        case 'shipper':
          return a.shipper_name.localeCompare(b.shipper_name);
        case 'origin':
          return a.shipper_country.localeCompare(b.shipper_country);
        default:
          return 0;
      }
    });

    return sorted;
  }, [cases, filterRisk, filterOrigin, filterDestination, searchTerm, sortBy]);

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-gray-900">MANIFEST RISK QUEUE</h2>
          <span className="text-sm font-semibold text-blue-600 bg-blue-50 px-3 py-1 rounded-full">
            {processedCases.length} of {cases.length}
          </span>
        </div>

        {/* Search */}
        <SearchBar
          value={searchTerm}
          onChange={setSearchTerm}
          placeholder="Search by shipper, consignee, HTS code, or case ID..."
          className="mb-3"
        />

        {/* Quick Filters */}
        <div className="grid grid-cols-3 gap-2 mb-3">
          <FilterSelect
            value={sortBy}
            onChange={(v) => setSortBy(v as SortOption)}
            label="Sort By"
            options={[
              { value: 'risk-desc', label: '↓ Highest Risk' },
              { value: 'risk-asc', label: '↑ Lowest Risk' },
              { value: 'date-newest', label: '📅 Newest First' },
              { value: 'date-oldest', label: '📅 Oldest First' },
              { value: 'shipper', label: 'Shipper (A-Z)' },
              { value: 'origin', label: 'Origin Country' }
            ]}
          />

          <FilterSelect
            value={filterRisk}
            onChange={setFilterRisk}
            label="Risk Level"
            options={[
              { value: 'all', label: 'All Risks' },
              { value: 'HIGH', label: 'High Risk (≥70)' },
              { value: 'MEDIUM', label: 'Medium (50-69)' },
              { value: 'LOW', label: 'Low (<50)' }
            ]}
          />

          <button
            onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
            className="px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm font-medium text-gray-700 transition-colors"
          >
            {showAdvancedFilters ? '▼ Filters' : '▶ Filters'}
          </button>
        </div>

        {/* Advanced Filters */}
        {showAdvancedFilters && (
          <div className="grid grid-cols-2 gap-2 p-3 bg-gray-50 rounded-lg mb-3 border border-gray-200">
            <FilterSelect
              value={filterOrigin}
              onChange={setFilterOrigin}
              label="Origin Country"
              options={[
                { value: 'all', label: 'All Origins' },
                ...uniqueOrigins.map(c => ({ value: c, label: c }))
              ]}
            />

            <FilterSelect
              value={filterDestination}
              onChange={setFilterDestination}
              label="Destination"
              options={[
                { value: 'all', label: 'All Destinations' },
                ...uniqueDestinations.map(c => ({ value: c, label: c }))
              ]}
            />
          </div>
        )}
      </div>

      {/* Cases List */}
      <div className="flex-1 overflow-y-auto">
        {processedCases.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-sm text-gray-500">No cases match your filters</p>
            <button
              onClick={() => {
                setSearchTerm('');
                setFilterRisk('all');
                setFilterOrigin('all');
                setFilterDestination('all');
              }}
              className="mt-3 text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              Clear all filters
            </button>
          </div>
        ) : (
          <div className="space-y-2 p-3">
            {processedCases.map((c) => {
              const riskScore = Math.round(c.risk_score || 0);
              const isSelected = selectedCase?.id === c.id;
              const createdDate = new Date(c.created_at || '');

              return (
                <button
                  key={c.id}
                  onClick={() => onSelectCase(c)}
                  className={`w-full text-left p-3 rounded-lg border-2 transition-all hover:shadow-md ${
                    isSelected
                      ? 'border-blue-500 bg-blue-50 shadow-md'
                      : 'border-gray-200 hover:border-gray-400 hover:bg-gray-50'
                  }`}
                >
                  {/* Top Row: Risk Badge + Score + Date */}
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <RiskBadge score={riskScore} size="sm" />
                      <span className="font-bold text-gray-900">{riskScore}/100</span>
                    </div>
                    <span className="text-xs text-gray-500">
                      {createdDate.toLocaleDateString()} {createdDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>

                  {/* Case ID */}
                  <p className="text-xs text-gray-500 font-mono mb-1">
                    {c.id} • {c.manifest_id}
                  </p>

                  {/* Shipper → Consignee */}
                  <p className="text-sm font-semibold text-gray-900 truncate">
                    {c.shipper_name}
                  </p>
                  <p className="text-xs text-gray-600 truncate mb-2">
                    {c.shipper_country} → {c.consignee_country} | {c.consignee_name}
                  </p>

                  {/* HTS Code + Commodity + Value */}
                  <div className="grid grid-cols-3 gap-2 text-xs mb-2">
                    <div>
                      <span className="text-gray-500">HTS:</span>
                      <p className="font-mono text-gray-700">{c.commodity_code}</p>
                    </div>
                    <div>
                      <span className="text-gray-500">Qty:</span>
                      <p className="text-gray-700">{(c.declared_weight_kg || 0).toLocaleString()} kg</p>
                    </div>
                    <div>
                      <span className="text-gray-500">Value:</span>
                      <p className="text-gray-700">${(c.declared_value || 0).toLocaleString()}</p>
                    </div>
                  </div>

                  {/* ISF Element 9 Badge (if mismatch) */}
                  {c.element9_is_mismatch && (
                    <div className="inline-block bg-red-100 text-red-700 text-xs px-2 py-1 rounded font-semibold">
                      ⚠ ISF Mismatch: {c.element9_declared_country} ≠ {c.element9_actual_country}
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
