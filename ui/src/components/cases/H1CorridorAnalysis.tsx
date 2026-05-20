import { Case, ScoreResult } from '../../types/models';
import { useScore } from '../../hooks';
import {
  ExpandableCard,
  SectionHeader,
  DataTable,
  AlertBanner,
  ScoreComponentChart
} from '../common';
import { TrendingUp, AlertTriangle } from 'lucide-react';

interface Props {
  case: Case;
}

export default function H1CorridorAnalysis({ case: c }: Props) {
  const { score, loading, error } = useScore(c.id);

  if (loading) {
    return <AlertBanner type="info" title="Analyzing corridor risk..." dismissible={false} />;
  }

  if (error) {
    return <AlertBanner type="error" title="Error loading score data" message={error} />;
  }

  const h1Component = score?.components?.find((comp) => comp.horizon === 'H1');
  const corridorRoute = `${c.shipper_country} → ${c.consignee_country}`;

  // Mock corridor data - in production this would come from external API
  const corridorData = {
    route: corridorRoute,
    risk_level: h1Component && h1Component.score >= 30 ? 'HIGH' : 'MEDIUM',
    ad_cvd_rate: 374.15,
    shipper_age_months: 8,
    undervaluation_pct: 42.5,
    historical_filings_count: 47,
    enforcement_actions: 12,
  };

  const historicalPatterns = [
    { month: 'Jun 2024', count: 3, avg_value: '$42k', origin: 'CN', flag: 'NORMAL' },
    { month: 'Jul 2024', count: 5, avg_value: '$48k', origin: 'CN', flag: 'NORMAL' },
    { month: 'Aug 2024', count: 8, avg_value: '$51k', origin: 'VN', flag: 'SURGE' },
    { month: 'Sep 2024', count: 12, avg_value: '$52k', origin: 'VN', flag: 'SURGE' },
    { month: 'Oct 2024', count: 15, avg_value: '$50k', origin: 'VN', flag: 'HIGH_VOLUME' },
  ];

  const adCvdOrders = [
    { country: 'China', hs_code: '7604', rate: '374.15%', case_number: 'A-570-001', effective: '2021-03-15' },
    { country: 'Vietnam', hs_code: '7604', rate: '45.22%', case_number: 'A-552-022', effective: '2022-11-08' },
    { country: 'Malaysia', hs_code: '8541.40', rate: '100.00%', case_number: 'C-570-888', effective: '2022-06-20' },
  ];

  const riskFactors = [
    {
      factor: 'Corridor Risk',
      score: 40,
      max: 40,
      risk: 'HIGH',
      description: `${corridorRoute} flagged for transshipment risk - 47 prior filings`
    },
    {
      factor: 'AD/CVD Exposure',
      score: 10,
      max: 10,
      risk: 'HIGH',
      description: `374.15% rate on HTS 7604 - strongest tariff avoidance incentive`
    },
    {
      factor: 'Shipper Age',
      score: 8,
      max: 10,
      risk: 'HIGH',
      description: `Only 8 months old - suspiciously timed with enforcement surge`
    },
    {
      factor: 'Pricing Analysis',
      score: 10,
      max: 10,
      risk: 'HIGH',
      description: `$10/kg declared vs $17.50/kg market - 42.5% undervalued`
    },
  ];

  return (
    <div className="p-6 space-y-6">
      <SectionHeader
        title="H1: Corridor Risk Intelligence"
        subtitle="Route-based risk scoring using public tariff, shipper age, and pricing data"
        badge={corridorData.risk_level}
        badgeColor={corridorData.risk_level === 'HIGH' ? 'red' : 'amber'}
      />

      {/* Key Corridor Indicators */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 bg-red-50 border-2 border-red-200 rounded-lg">
          <p className="text-xs font-semibold text-red-900 uppercase">Corridor Route</p>
          <p className="text-lg font-bold text-red-600 mt-2">{corridorRoute}</p>
          <p className="text-xs text-red-700 mt-1">47 prior filings</p>
        </div>
        <div className="p-4 bg-orange-50 border-2 border-orange-200 rounded-lg">
          <p className="text-xs font-semibold text-orange-900 uppercase">AD/CVD Rate</p>
          <p className="text-lg font-bold text-orange-600 mt-2">374.15%</p>
          <p className="text-xs text-orange-700 mt-1">From China origin</p>
        </div>
        <div className="p-4 bg-red-50 border-2 border-red-200 rounded-lg">
          <p className="text-xs font-semibold text-red-900 uppercase">Shipper Age</p>
          <p className="text-lg font-bold text-red-600 mt-2">8 months</p>
          <p className="text-xs text-red-700 mt-1">Brand new entity</p>
        </div>
        <div className="p-4 bg-orange-50 border-2 border-orange-200 rounded-lg">
          <p className="text-xs font-semibold text-orange-900 uppercase">Undervaluation</p>
          <p className="text-lg font-bold text-orange-600 mt-2">42.5%</p>
          <p className="text-xs text-orange-700 mt-1">$10/kg vs $17.50 market</p>
        </div>
      </div>

      {/* Risk Component Breakdown */}
      <ExpandableCard title="Risk Component Breakdown" defaultOpen>
        <div className="space-y-3">
          {riskFactors.map((factor, idx) => (
            <div key={idx} className="p-3 border border-gray-200 rounded-lg">
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1">
                  <h4 className="font-semibold text-gray-900">{factor.factor}</h4>
                  <p className="text-sm text-gray-600 mt-1">{factor.description}</p>
                </div>
                <span className={`text-sm font-bold px-2 py-1 rounded ${
                  factor.risk === 'HIGH'
                    ? 'bg-red-100 text-red-900'
                    : 'bg-amber-100 text-amber-900'
                }`}>
                  {factor.risk}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full ${
                    factor.risk === 'HIGH' ? 'bg-red-600' : 'bg-amber-500'
                  }`}
                  style={{ width: `${(factor.score / factor.max) * 100}%` }}
                ></div>
              </div>
              <p className="text-xs text-gray-600 mt-1">{factor.score}/{factor.max} points</p>
            </div>
          ))}
        </div>
      </ExpandableCard>

      {/* AD/CVD Orders */}
      <ExpandableCard
        title="Active AD/CVD Orders"
        badge={`${adCvdOrders.length} Orders`}
        badgeColor="red"
      >
        <DataTable
          columns={[
            { key: 'country', label: 'Country of Origin', width: '20%' },
            { key: 'hs_code', label: 'HTS Code', width: '15%' },
            { key: 'rate', label: 'Duty Rate', width: '15%' },
            { key: 'case_number', label: 'Case Number', width: '25%' },
            { key: 'effective', label: 'Effective Date', width: '25%' },
          ]}
          data={adCvdOrders}
          compact
        />
      </ExpandableCard>

      {/* Historical Import Pattern Analysis */}
      <ExpandableCard title="Historical Import Pattern (6-Month Trend)" badge="SURGE">
        <div className="space-y-4">
          <p className="text-sm text-gray-700 mb-4">
            Shows origin shift from China to Vietnam coinciding with enforcement surge. Volume increased 5x.
          </p>
          <DataTable
            columns={[
              { key: 'month', label: 'Month', width: '15%' },
              { key: 'count', label: 'Shipment Count', width: '15%' },
              { key: 'avg_value', label: 'Avg Value', width: '15%' },
              { key: 'origin', label: 'Declared Origin', width: '20%' },
              {
                key: 'flag',
                label: 'Flag',
                width: '20%',
                render: (value: string) => (
                  <span className={`text-xs font-bold px-2 py-1 rounded ${
                    value === 'SURGE' ? 'bg-red-100 text-red-900' :
                    value === 'HIGH_VOLUME' ? 'bg-orange-100 text-orange-900' :
                    'bg-green-100 text-green-900'
                  }`}>
                    {value}
                  </span>
                )
              },
            ]}
            data={historicalPatterns}
            compact
          />
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex gap-3">
            <AlertTriangle size={20} className="text-red-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-red-900">
              <p className="font-semibold">Pattern Alert: Origin Rotation</p>
              <p className="mt-1">Shipper rapidly shifted from CN to VN declared origin following CVD enforcement, suggesting deliberate evasion of higher tariffs.</p>
            </div>
          </div>
        </div>
      </ExpandableCard>

      {/* Trade Flow Intelligence */}
      <ExpandableCard title="Trade Flow Intelligence">
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-xs font-semibold text-blue-900 uppercase">Prior Filings (Same HTS)</p>
              <p className="text-2xl font-bold text-blue-600 mt-2">47</p>
              <p className="text-xs text-blue-700 mt-1">HTS 7604 → US since 2020</p>
            </div>
            <div className="p-3 bg-purple-50 border border-purple-200 rounded-lg">
              <p className="text-xs font-semibold text-purple-900 uppercase">EAPA Cases</p>
              <p className="text-2xl font-bold text-purple-600 mt-2">12</p>
              <p className="text-xs text-purple-700 mt-1">Enforcement actions (same corridor)</p>
            </div>
          </div>
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-900">
            <strong>Market Context:</strong> Aluminum extrusions from Asia typically FOB $15-20/kg. Declared value of $10/kg suggests heavy price suppression, common in transshipment schemes where actual origin (China) goods arrive via intermediate shipper (Vietnam) to evade duties.
          </div>
        </div>
      </ExpandableCard>
    </div>
  );
}
