import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/layout/Header';
import { AlertTriangle, TrendingUp, Clock, ChevronRight, Search } from 'lucide-react';

interface Shipment {
  id: string;
  manifest_id: string;
  shipper_name: string;
  consignee_name: string;
  shipper_country: string;
  consignee_country: string;
  commodity_code: string;
  declared_value: number;
  risk_score: number;
  status: string;
  created_at: string;
}

export default function ManifestRiskQueuePage() {
  const navigate = useNavigate();
  const [shipments, setShipments] = useState<Shipment[]>([]);
  const [filteredShipments, setFilteredShipments] = useState<Shipment[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterRisk, setFilterRisk] = useState<'all' | 'high' | 'medium' | 'low'>('all');
  const [sortBy, setSortBy] = useState<'risk' | 'date' | 'shipper'>('risk');

  useEffect(() => {
    fetchShipments();
  }, []);

  useEffect(() => {
    applyFiltersAndSort();
  }, [shipments, searchTerm, filterRisk, sortBy]);

  const fetchShipments = async () => {
    try {
      const response = await fetch('/api/shipments?limit=100');
      if (!response.ok) throw new Error('Failed to fetch shipments');
      const data = await response.json();
      setShipments(data.shipments || []);
    } catch (error) {
      console.error('Error fetching shipments:', error);
    } finally {
      setLoading(false);
    }
  };

  const applyFiltersAndSort = () => {
    let filtered = shipments.filter(s => {
      // Risk filter
      const score = s.risk_score || 0;
      if (filterRisk === 'high' && score < 70) return false;
      if (filterRisk === 'medium' && (score < 40 || score >= 70)) return false;
      if (filterRisk === 'low' && score >= 40) return false;

      // Search filter
      const search = searchTerm.toLowerCase();
      return (
        s.shipper_name.toLowerCase().includes(search) ||
        s.consignee_name.toLowerCase().includes(search) ||
        s.manifest_id.toLowerCase().includes(search) ||
        s.commodity_code.includes(search)
      );
    });

    // Sort
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'risk':
          return (b.risk_score || 0) - (a.risk_score || 0);
        case 'date':
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        case 'shipper':
          return a.shipper_name.localeCompare(b.shipper_name);
        default:
          return 0;
      }
    });

    setFilteredShipments(filtered);
  };

  const getRiskColor = (score: number) => {
    if (score >= 70) return { bg: 'bg-red-50', text: 'text-red-900', badge: 'bg-red-100 text-red-800' };
    if (score >= 50) return { bg: 'bg-yellow-50', text: 'text-yellow-900', badge: 'bg-yellow-100 text-yellow-800' };
    return { bg: 'bg-green-50', text: 'text-green-900', badge: 'bg-green-100 text-green-800' };
  };

  const getRiskLevel = (score: number) => {
    if (score >= 70) return 'HIGH';
    if (score >= 50) return 'MEDIUM';
    return 'LOW';
  };

  const highRiskCount = shipments.filter(s => (s.risk_score || 0) >= 70).length;
  const mediumRiskCount = shipments.filter(s => (s.risk_score || 0) >= 50 && (s.risk_score || 0) < 70).length;
  const totalValue = shipments.reduce((sum, s) => sum + (s.declared_value || 0), 0);

  return (
    <div className="min-h-screen bg-gray-50">
      <Header title="Manifest Risk Queue" showNav={true} />

      {/* Stats Section */}
      <div className="bg-white border-b border-gray-200 px-6 py-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-6xl">
          <div className="bg-red-50 rounded-lg p-4 border-l-4 border-red-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-red-600 font-semibold uppercase">High Risk</p>
                <p className="text-3xl font-bold text-red-900">{highRiskCount}</p>
              </div>
              <AlertTriangle className="text-red-500" size={32} />
            </div>
          </div>
          <div className="bg-yellow-50 rounded-lg p-4 border-l-4 border-yellow-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-yellow-600 font-semibold uppercase">Medium Risk</p>
                <p className="text-3xl font-bold text-yellow-900">{mediumRiskCount}</p>
              </div>
              <TrendingUp className="text-yellow-500" size={32} />
            </div>
          </div>
          <div className="bg-blue-50 rounded-lg p-4 border-l-4 border-blue-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-blue-600 font-semibold uppercase">Total Value</p>
                <p className="text-2xl font-bold text-blue-900">${(totalValue / 1000000).toFixed(1)}M</p>
              </div>
              <Clock className="text-blue-500" size={32} />
            </div>
          </div>
        </div>
      </div>

      {/* Queue Section */}
      <div className="max-w-6xl mx-auto p-6">
        {/* Filters */}
        <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Search */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Search</label>
              <div className="relative">
                <Search className="absolute left-3 top-3 text-gray-400" size={18} />
                <input
                  type="text"
                  placeholder="Shipper, consignee, ID..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            {/* Risk Filter */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Risk Level</label>
              <select
                value={filterRisk}
                onChange={(e) => setFilterRisk(e.target.value as any)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Risk Levels</option>
                <option value="high">HIGH Risk (70+)</option>
                <option value="medium">MEDIUM (50-69)</option>
                <option value="low">LOW Risk (Below 50)</option>
              </select>
            </div>

            {/* Sort */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Sort By</label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="risk">Risk (High to Low)</option>
                <option value="date">Date (Newest)</option>
                <option value="shipper">Shipper (A-Z)</option>
              </select>
            </div>

            {/* Results Count */}
            <div className="flex items-end">
              <div className="text-sm text-gray-600">
                <span className="font-bold text-gray-900">{filteredShipments.length}</span> of{' '}
                <span className="font-bold text-gray-900">{shipments.length}</span> cases
              </div>
            </div>
          </div>
        </div>

        {/* Cases List */}
        {loading ? (
          <div className="text-center py-12 text-gray-500">Loading cases...</div>
        ) : filteredShipments.length === 0 ? (
          <div className="text-center py-12 text-gray-500">No cases match your filters</div>
        ) : (
          <div className="space-y-3">
            {filteredShipments.map((shipment) => {
              const score = Math.round(shipment.risk_score || 0);
              const riskLevel = getRiskLevel(shipment.risk_score || 0);
              const colors = getRiskColor(shipment.risk_score || 0);

              return (
                <button
                  key={shipment.id}
                  onClick={() => navigate(`/cases/${shipment.id}`)}
                  className={`w-full text-left rounded-lg border border-gray-200 hover:border-gray-400 hover:shadow-md transition-all p-4 ${colors.bg}`}
                >
                  <div className="flex items-start justify-between gap-4">
                    {/* Risk Badge and Score */}
                    <div className="flex items-center gap-3 flex-shrink-0">
                      <span className={`inline-block px-3 py-1 rounded font-bold text-sm ${colors.badge}`}>
                        {riskLevel}
                      </span>
                      <span className="text-2xl font-bold text-gray-900 min-w-fit">{score}/100</span>
                    </div>

                    {/* Main Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-bold text-gray-900 truncate">{shipment.shipper_name}</h3>
                        <span className="text-xs text-gray-500 font-mono whitespace-nowrap">
                          {shipment.manifest_id}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 mb-2">
                        {shipment.shipper_country} → {shipment.consignee_country} | {shipment.consignee_name}
                      </p>
                      <div className="grid grid-cols-4 gap-3 text-xs">
                        <div>
                          <span className="text-gray-500">HTS Code</span>
                          <p className="font-mono font-semibold text-gray-900">{shipment.commodity_code}</p>
                        </div>
                        <div>
                          <span className="text-gray-500">Value</span>
                          <p className="font-semibold text-gray-900">${(shipment.declared_value || 0).toLocaleString()}</p>
                        </div>
                        <div>
                          <span className="text-gray-500">Status</span>
                          <p className="font-semibold text-gray-900">{shipment.status}</p>
                        </div>
                        <div>
                          <span className="text-gray-500">Filed</span>
                          <p className="font-semibold text-gray-900">
                            {new Date(shipment.created_at).toLocaleDateString()}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Action Arrow */}
                    <ChevronRight className="text-gray-400 flex-shrink-0" size={24} />
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
