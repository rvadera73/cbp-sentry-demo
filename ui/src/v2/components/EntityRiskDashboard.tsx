import React from 'react';
import { AlertTriangle, TrendingUp, Ship, Users } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { TYPOGRAPHY, DESIGN } from '../styles/typography';

interface EntityRiskStats {
  activeWatchlist: number;
  criticalRisk: number;
  highRisk: number;
  incomingVessels: number;
  newFlaggedToday: number;
}

interface IncomingVessel {
  vessel_name: string;
  eta: string;
  operators: string[];
  risk_score: number;
}

interface TopEntity {
  entity_id: string;
  entity_name: string;
  entity_type: string;
  country: string;
  risk_score: number;
}

interface EntityRiskDashboardProps {
  stats?: EntityRiskStats;
  incomingVessels?: IncomingVessel[];
  topEntities?: TopEntity[];
  onViewWatchlist?: () => void;
}

const FIXTURE_STATS: EntityRiskStats = {
  activeWatchlist: 47,
  criticalRisk: 3,
  highRisk: 12,
  incomingVessels: 3,
  newFlaggedToday: 8,
};

const FIXTURE_VESSELS: IncomingVessel[] = [
  { vessel_name: 'MV Greenfield', eta: '12h', operators: ['Greenfield VN', 'Greenfield HK'], risk_score: 65 },
  { vessel_name: 'MV Solaria', eta: '18h', operators: ['Solaria MY'], risk_score: 52 },
  { vessel_name: 'CMA CGM Alps', eta: '24h', operators: ['Ocean Shipping Inc.'], risk_score: 38 },
];

const FIXTURE_TOP_ENTITIES: TopEntity[] = [
  { entity_id: 'ENT-GF-VN-001', entity_name: 'Greenfield Industrial', entity_type: 'Shipper', country: 'Vietnam', risk_score: 65 },
  { entity_id: 'ENT-SOL-MY-001', entity_name: 'Solaria Mfg', entity_type: 'Manufacturer', country: 'Malaysia', risk_score: 48 },
  { entity_id: 'ENT-SP-US-001', entity_name: 'SunPath Dist.', entity_type: 'Consignee', country: 'USA', risk_score: 52 },
  { entity_id: 'ENT-PAN-PAC-001', entity_name: 'Pan-Pacific', entity_type: 'Freight Fwd', country: 'Singapore', risk_score: 38 },
  { entity_id: 'ENT-OCS-HK-001', entity_name: 'Ocean Shipping', entity_type: 'Operator', country: 'Hong Kong', risk_score: 35 },
];

export default function EntityRiskDashboard({
  stats = FIXTURE_STATS,
  topEntities = FIXTURE_TOP_ENTITIES,
  onViewWatchlist
}: EntityRiskDashboardProps) {
  const getRiskBarColor = (score: number): string => {
    if (score >= 70) return '#D83933';
    if (score >= 50) return '#FF9500';
    return '#22c55e';
  };

  // Prepare risk distribution for pie chart
  const riskDistribution = [
    { name: 'CRITICAL', value: stats.criticalRisk, fill: '#D83933' },
    { name: 'HIGH', value: stats.highRisk, fill: '#FF9500' },
    { name: 'MEDIUM', value: Math.max(1, stats.activeWatchlist - stats.criticalRisk - stats.highRisk - 5), fill: '#F59E0B' },
    { name: 'LOW', value: 5, fill: '#22c55e' },
  ];

  return (
    <div className="space-y-3">
      {/* Row 1: KPI Strip */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-2">
        <div className="bg-white border-l-4 border-[#0076D6] rounded-sm p-3 shadow-sm">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[8px] text-[#5C5C5C] font-mono uppercase font-bold">Active</span>
            <Users className="w-3 h-3 text-[#0076D6]" />
          </div>
          <div className="text-xl font-bold text-[#0B1F33]">{stats.activeWatchlist}</div>
        </div>

        <div className="bg-white border-l-4 border-[#D83933] rounded-sm p-3 shadow-sm">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[8px] text-[#5C5C5C] font-mono uppercase font-bold">Critical</span>
            <AlertTriangle className="w-3 h-3 text-[#D83933]" />
          </div>
          <div className="text-xl font-bold text-[#D83933]">{stats.criticalRisk}</div>
        </div>

        <div className="bg-white border-l-4 border-orange-600 rounded-sm p-3 shadow-sm">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[8px] text-[#5C5C5C] font-mono uppercase font-bold">High</span>
            <TrendingUp className="w-3 h-3 text-orange-600" />
          </div>
          <div className="text-xl font-bold text-orange-600">{stats.highRisk}</div>
        </div>

        <div className="bg-white border-l-4 border-[#00BDE3] rounded-sm p-3 shadow-sm">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[8px] text-[#5C5C5C] font-mono uppercase font-bold">Incoming</span>
            <Ship className="w-3 h-3 text-[#00BDE3]" />
          </div>
          <div className="text-xl font-bold text-[#0B1F33]">{stats.incomingVessels}</div>
        </div>

        <div className="bg-white border-l-4 border-amber-500 rounded-sm p-3 shadow-sm">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[8px] text-[#5C5C5C] font-mono uppercase font-bold">New</span>
            <AlertTriangle className="w-3 h-3 text-amber-500" />
          </div>
          <div className="text-xl font-bold text-amber-600">{stats.newFlaggedToday}</div>
        </div>
      </div>

      {/* Row 2: Consolidated Visual Analysis */}
      <div className="grid grid-cols-2 gap-3">
        {/* Risk Distribution Pie Chart */}
        <div className="bg-white border border-[#D0D7DE] rounded-sm p-4 shadow-sm flex flex-col" style={{ minHeight: '220px' }}>
          <div className="text-[9px] font-bold text-[#5C5C5C] uppercase mb-3">Risk Distribution</div>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie
                data={riskDistribution}
                cx="50%"
                cy="50%"
                innerRadius={35}
                outerRadius={65}
                paddingAngle={2}
                dataKey="value"
              >
                {riskDistribution.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="flex justify-center gap-3 mt-2 flex-wrap text-[8px]">
            {riskDistribution.map((entry, idx) => (
              <div key={idx} className="flex items-center gap-1">
                <div style={{ width: '8px', height: '8px', background: entry.fill, borderRadius: '2px' }} />
                <span className="font-bold text-[#5C5C5C]">{entry.name} ({entry.value})</span>
              </div>
            ))}
          </div>
        </div>

        {/* Top Risk Entities Table */}
        <div className="bg-white border border-[#D0D7DE] rounded-sm p-4 shadow-sm flex flex-col" style={{ minHeight: '220px' }}>
          <div className="text-[9px] font-bold text-[#5C5C5C] uppercase mb-3">TOP RISK ENTITIES</div>
          <div className="flex-1 overflow-y-auto">
            <div className="space-y-2">
              {topEntities.slice(0, 5).map((entity) => (
                <div key={entity.entity_id} className="p-2 bg-slate-50 rounded border border-slate-200 hover:bg-slate-100 transition-colors">
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <div className="flex-1 min-w-0">
                      <div className="text-[9px] font-bold text-[#0B1F33] truncate">{entity.entity_name}</div>
                      <div className="text-[8px] text-[#5C5C5C]">{entity.entity_type} • {entity.country}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div
                      style={{
                        width: '40px',
                        height: '5px',
                        background: getRiskBarColor(entity.risk_score),
                        borderRadius: '2px',
                      }}
                    />
                    <span className="text-[8px] font-bold text-[#5C5C5C]">{entity.risk_score}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Action Button */}
      <button
        onClick={onViewWatchlist}
        className="w-full px-4 py-2 bg-[#0076D6] hover:bg-[#005EA2] text-white rounded-sm font-bold text-xs transition-colors"
      >
        → VIEW FULL WATCHLIST ({stats.activeWatchlist} entities)
      </button>
    </div>
  );
}
