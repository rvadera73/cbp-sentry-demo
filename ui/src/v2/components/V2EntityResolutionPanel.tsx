import React, { useState } from 'react';
import { AlertTriangle, CheckCircle, Network, Globe, Shield, TrendingUp } from 'lucide-react';
import { RadarChart, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer } from 'recharts';
import EntityNetworkGraph from './EntityNetworkGraph';
import EntityGeoMap from './EntityGeoMap';
import { Tabs, Panel, SectionHeader, StatStrip, StatusPill, DataTable, Column } from '../../components/ui';

type TabType = 'Network' | 'Geography' | 'Intelligence' | 'Risk Profile';

interface EnforcementCase { case_id: string; case_type: string; agency: string; determination: string; date_filed: string; status: string }
interface OwnershipEntity { level: number; entity_id: string; name: string; country: string; entity_type: string; confidence: number }
interface NetworkEntity { entity_id: string; name: string; entity_type: string; country: string; risk_score: number; relationships?: Array<{ target_id: string; type: string; confidence: number }> }
interface EntityLocation { entity_id: string; entity_name: string; country: string; risk_score: number; entity_type: string }

const FIXTURE_NETWORK_ENTITIES: NetworkEntity[] = [
  { entity_id: 'ENT-GF-VN-001', name: 'Greenfield Industrial Trading Co., Ltd.', entity_type: 'Shipper', country: 'Vietnam', risk_score: 65, relationships: [{ target_id: 'ENT-GF-HK-001', type: 'OWNED_BY', confidence: 0.92 }, { target_id: 'ENT-PAN-PAC-001', type: 'FREIGHT_FORWARDER_SHARED', confidence: 0.78 }] },
  { entity_id: 'ENT-GF-HK-001', name: 'Greenfield Global Metals Holdings Ltd.', entity_type: 'Holding Company', country: 'Hong Kong', risk_score: 58, relationships: [{ target_id: 'ENT-GF-CN-001', type: 'OWNS', confidence: 0.85 }, { target_id: 'ENT-SP-US-001', type: 'DIRECTOR_SHARED', confidence: 0.72 }] },
  { entity_id: 'ENT-GF-CN-001', name: 'Guangdong Greenfield Aluminum Mfg.', entity_type: 'Manufacturer', country: 'China', risk_score: 52, relationships: [] },
  { entity_id: 'ENT-PAN-PAC-001', name: 'Pan-Pacific Logistics, Inc.', entity_type: 'Freight Forwarder', country: 'Singapore', risk_score: 38, relationships: [{ target_id: 'ENT-SP-US-001', type: 'CONSIGNEE_LINK', confidence: 0.88 }] },
  { entity_id: 'ENT-SP-US-001', name: 'SunPath Energy Distributors LLC', entity_type: 'Consignee', country: 'USA', risk_score: 52, relationships: [] },
];

const FIXTURE_ENTITY_LOCATIONS: EntityLocation[] = [
  { entity_id: 'ENT-GF-VN-001', entity_name: 'Greenfield VN', country: 'Vietnam', risk_score: 65, entity_type: 'Shipper' },
  { entity_id: 'ENT-GF-HK-001', entity_name: 'Greenfield HK', country: 'Hong Kong', risk_score: 58, entity_type: 'Holding' },
  { entity_id: 'ENT-GF-CN-001', entity_name: 'Greenfield CN', country: 'China', risk_score: 52, entity_type: 'Mfg' },
  { entity_id: 'ENT-PAN-PAC-001', entity_name: 'Pan-Pacific', country: 'Singapore', risk_score: 38, entity_type: 'FF' },
  { entity_id: 'ENT-SP-US-001', entity_name: 'SunPath', country: 'USA', risk_score: 52, entity_type: 'Consignee' },
];

const FIXTURE_ENFORCEMENT: EnforcementCase[] = [
  { case_id: 'EAPA-2023-001', case_type: 'EAPA', agency: 'CBSA', determination: 'Dumping Found', date_filed: '2023-03-15', status: 'Active' },
  { case_id: 'BIS-2022-845', case_type: 'Export Control', agency: 'BIS', determination: 'Violation', date_filed: '2022-11-20', status: 'Closed' },
  { case_id: 'OFAC-2024-002', case_type: 'Sanctions', agency: 'OFAC', determination: 'Match', date_filed: '2024-01-10', status: 'Under Review' },
];

const FIXTURE_OWNERSHIP: OwnershipEntity[] = [
  { level: 1, entity_id: 'ENT-GF-VN-001', name: 'Greenfield Industrial Trading', country: 'Vietnam', entity_type: 'Shipper', confidence: 1.0 },
  { level: 2, entity_id: 'ENT-GF-HK-001', name: 'Greenfield Global Metals Holdings', country: 'Hong Kong', entity_type: 'Holding', confidence: 0.92 },
  { level: 3, entity_id: 'ENT-GF-CN-001', name: 'Guangdong Greenfield Aluminum', country: 'China', entity_type: 'Manufacturer', confidence: 0.85 },
];

const FIXTURE_RISK_DIMENSIONS = [
  { dimension: 'Supply Chain', score: 72 }, { dimension: 'Origin', score: 88 }, { dimension: 'Entity', score: 65 },
  { dimension: 'Financial', score: 45 }, { dimension: 'Regulatory', score: 91 }, { dimension: 'Documentation', score: 78 },
];
const FIXTURE_CONCERNS = ['Prior EAPA determination', 'Director shared with high-risk entity', 'Transshipment hub routing'];
const FIXTURE_POSITIVE_FACTORS = ['No OFAC match', 'Valid commodity codes', 'Standard documentation'];

const ConfidenceBar: React.FC<{ value: number }> = ({ value }) => (
  <div className="flex items-center justify-end gap-1.5">
    <div className="w-16 h-1.5 bg-slate-200 rounded-sm overflow-hidden">
      <div className="h-full bg-[#005EA2]" style={{ width: `${Math.round(value * 100)}%` }} />
    </div>
    <span className="font-mono text-[#0B1F33]">{Math.round(value * 100)}%</span>
  </div>
);

export default function V2EntityResolutionPanel() {
  const [activeTab, setActiveTab] = useState<TabType>('Network');

  const connectionRows = FIXTURE_NETWORK_ENTITIES.flatMap(e =>
    (e.relationships || []).map(r => {
      const target = FIXTURE_NETWORK_ENTITIES.find(t => t.entity_id === r.target_id);
      return { type: r.type, entities: `${e.name.split(' ')[0]} → ${(target?.name || r.target_id).split(' ')[0]}`, confidence: r.confidence };
    })
  );

  const connectionColumns: Column[] = [
    { key: 'type', label: 'Link Type', render: r => <span className="font-mono font-bold text-[#0B1F33]">{r.type}</span> },
    { key: 'entities', label: 'Entities' },
    { key: 'confidence', label: 'Confidence', align: 'right', render: r => <ConfidenceBar value={r.confidence} /> },
  ];

  const enforcementColumns: Column[] = [
    { key: 'case_id', label: 'Case ID', mono: true, render: r => <span className="font-mono font-bold">{r.case_id}</span> },
    { key: 'case_type', label: 'Type' },
    { key: 'agency', label: 'Agency' },
    { key: 'determination', label: 'Determination', render: r => <span className="inline-flex px-1.5 py-0.5 rounded bg-red-100 text-red-800 text-[10px] font-bold">{r.determination}</span> },
    { key: 'status', label: 'Status', align: 'center', render: r => <StatusPill status={r.status === 'Active' ? 'critical' : r.status === 'Under Review' ? 'warning' : 'registered'} /> },
    { key: 'date_filed', label: 'Filed', align: 'right', mono: true },
  ];

  const ownershipColumns: Column[] = [
    { key: 'level', label: 'Level', align: 'center', render: r => <span className="font-mono font-bold">L{r.level}</span> },
    { key: 'name', label: 'Entity Name', render: r => <span className="font-semibold">{r.name}</span> },
    { key: 'entity_type', label: 'Type' },
    { key: 'country', label: 'Country' },
    { key: 'confidence', label: 'Confidence', align: 'right', render: r => <ConfidenceBar value={r.confidence} /> },
  ];

  const tabs = [
    { id: 'Network', label: 'Network', icon: <Network className="w-3.5 h-3.5" /> },
    { id: 'Geography', label: 'Geography', icon: <Globe className="w-3.5 h-3.5" /> },
    { id: 'Intelligence', label: 'Intelligence', icon: <Shield className="w-3.5 h-3.5" /> },
    { id: 'Risk Profile', label: 'Risk Profile', icon: <TrendingUp className="w-3.5 h-3.5" /> },
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Entity identity header */}
      <div className="px-4 pt-3 bg-white border-b border-[#D0D7DE]">
        <div className="flex items-center justify-between mb-2">
          <div className="min-w-0">
            <h2 className="text-sm font-bold text-[#0B1F33] uppercase tracking-wide truncate">Greenfield Industrial Trading Co., Ltd.</h2>
            <p className="text-[11px] text-[#5C5C5C]">Entity Intelligence · Vietnam · Shipper</p>
          </div>
          <StatusPill status="critical" />
        </div>
        <div className="mb-3">
          <StatStrip items={[
            { label: 'Risk Score', value: '65', color: '#D83933' },
            { label: 'Risk Level', value: 'HIGH', color: '#D83933' },
            { label: 'Country', value: 'VN' },
            { label: 'Type', value: 'Shipper' },
            { label: 'Connections', value: FIXTURE_NETWORK_ENTITIES.length },
          ]} />
        </div>
        <Tabs tabs={tabs} active={activeTab} onChange={(id) => setActiveTab(id as TabType)} />
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-4 bg-[#F7F9FC]">
        {activeTab === 'Network' && (
          <div className="space-y-4">
            <Panel pad={false}>
              <div className="p-4 pb-0"><SectionHeader title="Entity Relationship Graph" subtitle="Resolved ownership & shared-party links" icon={<Network className="w-4 h-4" />} /></div>
              <div style={{ height: '340px' }}><EntityNetworkGraph entities={FIXTURE_NETWORK_ENTITIES} height={330} /></div>
            </Panel>
            <Panel>
              <SectionHeader title="Connection Evidence" subtitle={`${connectionRows.length} resolved links`} />
              <DataTable columns={connectionColumns} rows={connectionRows} caption="Connection evidence between entities" empty="No connections resolved." />
            </Panel>
          </div>
        )}

        {activeTab === 'Geography' && (
          <div className="space-y-4">
            <Panel pad={false}>
              <div className="p-4 pb-0"><SectionHeader title="Supply Chain Geography" subtitle="Resolved entity locations & routing" icon={<Globe className="w-4 h-4" />} /></div>
              <div style={{ height: '340px' }}><EntityGeoMap entities={FIXTURE_ENTITY_LOCATIONS} height={330} showRoutes={true} /></div>
            </Panel>
            <div className="grid md:grid-cols-2 gap-4">
              <Panel>
                <SectionHeader title="Corridors Identified" />
                <ul className="space-y-1.5 text-[11px] text-[#0B1F33]">
                  <li>• <strong>Vietnam → Hong Kong</strong> <span className="text-[#5C5C5C]">(Transshipment hub)</span></li>
                  <li>• <strong>Hong Kong → Singapore</strong> <span className="text-[#5C5C5C]">(Consolidation)</span></li>
                  <li>• <strong>Singapore → USA</strong> <span className="text-[#5C5C5C]">(Final destination)</span></li>
                </ul>
              </Panel>
              <Panel>
                <SectionHeader title="Risk Patterns" />
                <ul className="space-y-1.5 text-[11px]">
                  <li className="text-[#D83933] font-semibold">⚠ Multi-hop transshipment</li>
                  <li className="text-orange-700 font-semibold">⚠ Hub consolidation pattern</li>
                  <li className="text-green-700 font-semibold">✓ Valid trade corridors</li>
                </ul>
              </Panel>
            </div>
          </div>
        )}

        {activeTab === 'Intelligence' && (
          <div className="space-y-4">
            <Panel>
              <SectionHeader title="Enforcement History" subtitle="Prior actions across agencies" icon={<Shield className="w-4 h-4" />} />
              <DataTable columns={enforcementColumns} rows={FIXTURE_ENFORCEMENT} caption="Enforcement history" empty="No enforcement records." />
            </Panel>
            <Panel>
              <SectionHeader title="Ownership Chain" subtitle="Resolved beneficial-ownership hierarchy" />
              <DataTable columns={ownershipColumns} rows={FIXTURE_OWNERSHIP} caption="Ownership chain" empty="No ownership data." />
            </Panel>
          </div>
        )}

        {activeTab === 'Risk Profile' && (
          <div className="space-y-4">
            <Panel>
              <SectionHeader title="Multidimensional Risk Profile" subtitle="Risk score across six dimensions" icon={<TrendingUp className="w-4 h-4" />} />
              <ResponsiveContainer width="100%" height={280}>
                <RadarChart data={FIXTURE_RISK_DIMENSIONS}>
                  <PolarAngleAxis dataKey="dimension" tick={{ fontSize: 11, fill: '#5C5C5C' }} />
                  <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 9 }} />
                  <Radar name="Risk Score" dataKey="score" stroke="#D83933" fill="#D83933" fillOpacity={0.25} />
                </RadarChart>
              </ResponsiveContainer>
            </Panel>
            <div className="grid md:grid-cols-2 gap-4">
              <Panel>
                <SectionHeader title="Top Concerns" icon={<AlertTriangle className="w-4 h-4" />} />
                <div className="space-y-1.5">
                  {FIXTURE_CONCERNS.map((c, i) => (
                    <div key={i} className="text-[11px] bg-red-50 text-[#D83933] px-2.5 py-1.5 rounded-sm border border-red-200 font-semibold">• {c}</div>
                  ))}
                </div>
              </Panel>
              <Panel>
                <SectionHeader title="Positive Factors" icon={<CheckCircle className="w-4 h-4" />} />
                <div className="space-y-1.5">
                  {FIXTURE_POSITIVE_FACTORS.map((f, i) => (
                    <div key={i} className="text-[11px] bg-green-50 text-green-800 px-2.5 py-1.5 rounded-sm border border-green-200 font-semibold">✓ {f}</div>
                  ))}
                </div>
              </Panel>
            </div>
            <div className="bg-amber-50 border border-amber-200 rounded-sm p-3">
              <div className="text-[11px] font-bold text-amber-900 uppercase tracking-wide mb-1">Analyst Recommendation</div>
              <p className="text-[12px] text-amber-900">
                Recommend <strong>Enhanced Screening</strong> for shipments involving these entities. Manual review required for any value &gt;$50K. Consider adding to watchlist for a 90-day monitoring period.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
