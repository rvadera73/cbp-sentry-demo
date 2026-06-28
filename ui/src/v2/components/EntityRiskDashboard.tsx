import React from 'react';
import { PieChart as PieIcon, ListOrdered } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { Panel, SectionHeader, StatStrip, ScoreBar } from '../../components/ui';

interface EntityRiskStats {
  activeWatchlist: number;
  criticalRisk: number;
  highRisk: number;
  incomingVessels: number;
  newFlaggedToday: number;
}
interface TopEntity { entity_id: string; entity_name: string; entity_type: string; country: string; risk_score: number }
interface EntityRiskDashboardProps {
  stats?: EntityRiskStats;
  incomingVessels?: any[];
  topEntities?: TopEntity[];
  onViewWatchlist?: () => void;
}

const FIXTURE_STATS: EntityRiskStats = { activeWatchlist: 47, criticalRisk: 3, highRisk: 12, incomingVessels: 3, newFlaggedToday: 8 };
const FIXTURE_TOP_ENTITIES: TopEntity[] = [
  { entity_id: 'ENT-GF-VN-001', entity_name: 'Greenfield Industrial', entity_type: 'Shipper', country: 'Vietnam', risk_score: 65 },
  { entity_id: 'ENT-SP-US-001', entity_name: 'SunPath Dist.', entity_type: 'Consignee', country: 'USA', risk_score: 52 },
  { entity_id: 'ENT-SOL-MY-001', entity_name: 'Solaria Mfg', entity_type: 'Manufacturer', country: 'Malaysia', risk_score: 48 },
  { entity_id: 'ENT-PAN-PAC-001', entity_name: 'Pan-Pacific', entity_type: 'Freight Fwd', country: 'Singapore', risk_score: 38 },
  { entity_id: 'ENT-OCS-HK-001', entity_name: 'Ocean Shipping', entity_type: 'Operator', country: 'Hong Kong', risk_score: 35 },
];

export default function EntityRiskDashboard({ stats = FIXTURE_STATS, topEntities = FIXTURE_TOP_ENTITIES, onViewWatchlist }: EntityRiskDashboardProps) {
  const riskDistribution = [
    { name: 'CRITICAL', value: stats.criticalRisk, fill: '#D83933' },
    { name: 'HIGH', value: stats.highRisk, fill: '#C7791B' },
    { name: 'MEDIUM', value: Math.max(1, stats.activeWatchlist - stats.criticalRisk - stats.highRisk - 5), fill: '#B8860B' },
    { name: 'LOW', value: 5, fill: '#15803D' },
  ];

  return (
    <div className="space-y-4">
      <StatStrip items={[
        { label: 'Active Watchlist', value: stats.activeWatchlist },
        { label: 'Critical', value: stats.criticalRisk, color: '#D83933' },
        { label: 'High', value: stats.highRisk, color: '#C7791B' },
        { label: 'Incoming Vessels', value: stats.incomingVessels },
        { label: 'New Today', value: stats.newFlaggedToday, color: '#B8860B' },
      ]} />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Panel>
          <SectionHeader title="Risk Distribution" subtitle="Watchlist entities by risk tier" icon={<PieIcon className="w-4 h-4" />} />
          <ResponsiveContainer width="100%" height={170}>
            <PieChart>
              <Pie data={riskDistribution} cx="50%" cy="50%" innerRadius={38} outerRadius={66} paddingAngle={2} dataKey="value">
                {riskDistribution.map((e, i) => <Cell key={i} fill={e.fill} />)}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="flex justify-center gap-3 flex-wrap mt-2 text-[10px]">
            {riskDistribution.map((e, i) => (
              <div key={i} className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-sm" style={{ background: e.fill }} />
                <span className="font-semibold text-[#5C5C5C]">{e.name} ({e.value})</span>
              </div>
            ))}
          </div>
        </Panel>

        <Panel>
          <SectionHeader title="Top Risk Entities" subtitle="Highest-scoring watchlist entities" icon={<ListOrdered className="w-4 h-4" />} />
          <div>
            {topEntities.slice(0, 5).map(e => (
              <ScoreBar key={e.entity_id} label={e.entity_name} sublabel={`${e.entity_type} · ${e.country}`} score={e.risk_score} />
            ))}
          </div>
        </Panel>
      </div>

      <button onClick={onViewWatchlist}
        className="w-full px-4 py-2 bg-[#005EA2] hover:bg-[#0b4f86] text-white rounded-sm font-bold text-[12px] focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-[#005EA2]">
        View Full Watchlist ({stats.activeWatchlist} entities) →
      </button>
    </div>
  );
}
