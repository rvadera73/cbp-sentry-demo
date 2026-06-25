import React, { useState } from 'react';
import { AlertTriangle, CheckCircle, Network, Globe, Shield, TrendingUp } from 'lucide-react';
import { RadarChart, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer } from 'recharts';
import { TYPOGRAPHY, DESIGN } from '../styles/typography';
import EntityNetworkGraph from './EntityNetworkGraph';
import EntityGeoMap from './EntityGeoMap';

type TabType = 'Network' | 'Geography' | 'Intelligence' | 'Risk Profile';

interface EnforcementCase {
  case_id: string;
  case_type: string;
  agency: string;
  determination: string;
  date_filed: string;
  status: string;
}

interface OwnershipEntity {
  level: number;
  entity_id: string;
  name: string;
  country: string;
  entity_type: string;
  confidence: number;
}

interface NetworkEntity {
  entity_id: string;
  name: string;
  entity_type: string;
  country: string;
  risk_score: number;
  relationships?: Array<{
    target_id: string;
    type: string;
    confidence: number;
  }>;
}

interface EntityLocation {
  entity_id: string;
  entity_name: string;
  country: string;
  risk_score: number;
  entity_type: string;
}

const FIXTURE_NETWORK_ENTITIES: NetworkEntity[] = [
  {
    entity_id: 'ENT-GF-VN-001',
    name: 'Greenfield Industrial Trading Co., Ltd.',
    entity_type: 'Shipper',
    country: 'Vietnam',
    risk_score: 65,
    relationships: [
      { target_id: 'ENT-GF-HK-001', type: 'OWNED_BY', confidence: 0.92 },
      { target_id: 'ENT-PAN-PAC-001', type: 'FREIGHT_FORWARDER_SHARED', confidence: 0.78 },
    ],
  },
  {
    entity_id: 'ENT-GF-HK-001',
    name: 'Greenfield Global Metals Holdings Ltd.',
    entity_type: 'Holding Company',
    country: 'Hong Kong',
    risk_score: 58,
    relationships: [
      { target_id: 'ENT-GF-CN-001', type: 'OWNS', confidence: 0.85 },
      { target_id: 'ENT-SP-US-001', type: 'DIRECTOR_SHARED', confidence: 0.72 },
    ],
  },
  {
    entity_id: 'ENT-GF-CN-001',
    name: 'Guangdong Greenfield Aluminum Mfg.',
    entity_type: 'Manufacturer',
    country: 'China',
    risk_score: 52,
    relationships: [],
  },
  {
    entity_id: 'ENT-PAN-PAC-001',
    name: 'Pan-Pacific Logistics, Inc.',
    entity_type: 'Freight Forwarder',
    country: 'Singapore',
    risk_score: 38,
    relationships: [
      { target_id: 'ENT-SP-US-001', type: 'CONSIGNEE_LINK', confidence: 0.88 },
    ],
  },
  {
    entity_id: 'ENT-SP-US-001',
    name: 'SunPath Energy Distributors LLC',
    entity_type: 'Consignee',
    country: 'USA',
    risk_score: 52,
    relationships: [],
  },
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
  { dimension: 'Supply Chain', score: 72 },
  { dimension: 'Origin', score: 88 },
  { dimension: 'Entity', score: 65 },
  { dimension: 'Financial', score: 45 },
  { dimension: 'Regulatory', score: 91 },
  { dimension: 'Documentation', score: 78 },
];

const FIXTURE_CONCERNS = ['Prior EAPA determination', 'Director shared with high-risk entity', 'Transshipment hub routing'];
const FIXTURE_POSITIVE_FACTORS = ['No OFAC match', 'Valid commodity codes', 'Standard documentation'];

export default function V2EntityResolutionPanel() {
  const [activeTab, setActiveTab] = useState<TabType>('Network');

  const tabStyles = (tab: TabType) =>
    `px-4 py-2 text-xs font-bold uppercase transition-colors cursor-pointer rounded-sm ${
      activeTab === tab
        ? 'bg-[#0076D6] text-white'
        : 'bg-slate-100 text-[#5C5C5C] hover:bg-slate-200'
    }`;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 bg-white border-b border-[#D0D7DE]">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h2 className={`${TYPOGRAPHY.sectionTitle}`}>Entity Intelligence</h2>
            <p className="text-[9px] text-[#5C5C5C]">Greenfield Industrial Trading Co., Ltd. • Vietnam • Risk: 65%</p>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-[#D83933]">65%</div>
            <div className="text-[8px] text-[#D83933] font-bold">HIGH RISK</div>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-2 px-4 py-3 bg-[#F7F9FC] border-b border-[#D0D7DE] flex-wrap">
        <button onClick={() => setActiveTab('Network')} className={tabStyles('Network')}>
          <Network className="w-3 h-3 inline mr-1" />
          Network
        </button>
        <button onClick={() => setActiveTab('Geography')} className={tabStyles('Geography')}>
          <Globe className="w-3 h-3 inline mr-1" />
          Geography
        </button>
        <button onClick={() => setActiveTab('Intelligence')} className={tabStyles('Intelligence')}>
          <Shield className="w-3 h-3 inline mr-1" />
          Intelligence
        </button>
        <button onClick={() => setActiveTab('Risk Profile')} className={tabStyles('Risk Profile')}>
          <TrendingUp className="w-3 h-3 inline mr-1" />
          Risk Profile
        </button>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {/* Network Tab */}
        {activeTab === 'Network' && (
          <div className="space-y-3">
            <div className="bg-white border border-[#D0D7DE] rounded-sm overflow-hidden">
              <div className="bg-[#F0F4F8] p-3 border-b border-[#D0D7DE]">
                <h3 className={`${TYPOGRAPHY.tableHeader}`}>Entity Relationship Graph</h3>
              </div>
              <div style={{ height: '350px' }}>
                <EntityNetworkGraph entities={FIXTURE_NETWORK_ENTITIES} height={340} />
              </div>
            </div>

            {/* Connection Evidence */}
            <div className="bg-white border border-[#D0D7DE] rounded-sm overflow-hidden">
              <div className="bg-[#F0F4F8] p-3 border-b border-[#D0D7DE]">
                <h3 className={`${TYPOGRAPHY.tableHeader}`}>Connection Evidence</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-[9px] border-collapse">
                  <thead>
                    <tr className="border-b border-[#D0D7DE] bg-[#F7F9FC]">
                      <th className="p-2 text-left font-bold text-[#112E51]">LINK TYPE</th>
                      <th className="p-2 text-left font-bold text-[#112E51]">ENTITIES</th>
                      <th className="p-2 text-center font-bold text-[#112E51]">CONFIDENCE</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-b border-[#E0E3E8] hover:bg-[#F7F9FC]">
                      <td className="p-2 font-bold text-[#0B1F33]">OWNED_BY</td>
                      <td className="p-2 text-[#5C5C5C]">Greenfield VN ← Greenfield HK</td>
                      <td className="p-2 text-center">
                        <div className="flex items-center justify-center gap-1">
                          <div style={{ width: '24px', height: '4px', background: '#0076D6', borderRadius: '2px' }} />
                          <span className="font-bold">92%</span>
                        </div>
                      </td>
                    </tr>
                    <tr className="border-b border-[#E0E3E8] hover:bg-[#F7F9FC]">
                      <td className="p-2 font-bold text-[#0B1F33]">DIRECTOR_SHARED</td>
                      <td className="p-2 text-[#5C5C5C]">Greenfield HK ↔ SunPath US</td>
                      <td className="p-2 text-center">
                        <div className="flex items-center justify-center gap-1">
                          <div style={{ width: '19px', height: '4px', background: '#FF9500', borderRadius: '2px' }} />
                          <span className="font-bold">72%</span>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Geography Tab */}
        {activeTab === 'Geography' && (
          <div className="space-y-3">
            <div className="bg-white border border-[#D0D7DE] rounded-sm overflow-hidden">
              <div className="bg-[#F0F4F8] p-3 border-b border-[#D0D7DE]">
                <h3 className={`${TYPOGRAPHY.tableHeader}`}>Supply Chain Geography</h3>
              </div>
              <div style={{ height: '350px' }}>
                <EntityGeoMap entities={FIXTURE_ENTITY_LOCATIONS} height={340} showRoutes={true} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="bg-white p-3 border border-[#D0D7DE] rounded-sm">
                <div className="text-[9px] font-bold text-[#5C5C5C] uppercase mb-2">Corridors Identified</div>
                <ul className="space-y-1 text-[8px] text-[#0B1F33]">
                  <li>• <strong>Vietnam → Hong Kong</strong> (Transshipment hub)</li>
                  <li>• <strong>Hong Kong → Singapore</strong> (Consolidation)</li>
                  <li>• <strong>Singapore → USA</strong> (Final destination)</li>
                </ul>
              </div>
              <div className="bg-white p-3 border border-[#D0D7DE] rounded-sm">
                <div className="text-[9px] font-bold text-[#5C5C5C] uppercase mb-2">Risk Patterns</div>
                <ul className="space-y-1 text-[8px]">
                  <li className="text-[#D83933]">⚠️ Multi-hop transshipment</li>
                  <li className="text-orange-600">⚠️ Hub consolidation pattern</li>
                  <li className="text-green-600">✓ Valid trade corridors</li>
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* Intelligence Tab */}
        {activeTab === 'Intelligence' && (
          <div className="space-y-4">
            {/* Enforcement */}
            <div className="bg-white border border-[#D0D7DE] rounded-sm overflow-hidden">
              <div className="bg-[#F0F4F8] p-2.5 border-b border-[#D0D7DE]">
                <h3 className={`${TYPOGRAPHY.tableHeader}`}>Enforcement History</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-[8px] border-collapse">
                  <thead>
                    <tr className="border-b border-[#D0D7DE] bg-[#F7F9FC]">
                      <th className="p-2 text-left font-bold text-[#112E51]">CASE ID</th>
                      <th className="p-2 text-left font-bold text-[#112E51]">TYPE</th>
                      <th className="p-2 text-left font-bold text-[#112E51]">AGENCY</th>
                      <th className="p-2 text-left font-bold text-[#112E51]">DETERMINATION</th>
                      <th className="p-2 text-left font-bold text-[#112E51]">STATUS</th>
                      <th className="p-2 text-left font-bold text-[#112E51]">FILED</th>
                    </tr>
                  </thead>
                  <tbody>
                    {FIXTURE_ENFORCEMENT.map((enf, idx) => (
                      <tr key={idx} className="border-b border-[#E0E3E8] hover:bg-[#F7F9FC]">
                        <td className="p-2 font-bold text-[#0B1F33]">{enf.case_id}</td>
                        <td className="p-2 text-[#5C5C5C]">{enf.case_type}</td>
                        <td className="p-2 text-[#5C5C5C]">{enf.agency}</td>
                        <td className="p-2">
                          <span className="bg-red-100 text-red-700 px-1.5 py-0.5 rounded text-[7px] font-bold">
                            {enf.determination}
                          </span>
                        </td>
                        <td className="p-2">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[7px] font-bold ${
                              enf.status === 'Active'
                                ? 'bg-red-100 text-red-700'
                                : enf.status === 'Under Review'
                                ? 'bg-yellow-100 text-yellow-700'
                                : 'bg-gray-100 text-gray-700'
                            }`}
                          >
                            {enf.status}
                          </span>
                        </td>
                        <td className="p-2 text-[#5C5C5C] font-mono">{enf.date_filed}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Ownership */}
            <div className="bg-white border border-[#D0D7DE] rounded-sm overflow-hidden">
              <div className="bg-[#F0F4F8] p-2.5 border-b border-[#D0D7DE]">
                <h3 className={`${TYPOGRAPHY.tableHeader}`}>Ownership Chain</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-[8px] border-collapse">
                  <thead>
                    <tr className="border-b border-[#D0D7DE] bg-[#F7F9FC]">
                      <th className="p-2 text-left font-bold text-[#112E51]">LEVEL</th>
                      <th className="p-2 text-left font-bold text-[#112E51]">ENTITY NAME</th>
                      <th className="p-2 text-left font-bold text-[#112E51]">TYPE</th>
                      <th className="p-2 text-left font-bold text-[#112E51]">COUNTRY</th>
                      <th className="p-2 text-center font-bold text-[#112E51]">CONFIDENCE</th>
                    </tr>
                  </thead>
                  <tbody>
                    {FIXTURE_OWNERSHIP.map((owner, idx) => (
                      <tr key={idx} className="border-b border-[#E0E3E8] hover:bg-[#F7F9FC]">
                        <td className="p-2 font-bold text-[#0B1F33]">{owner.level}</td>
                        <td className="p-2 text-[#0B1F33] font-semibold">{owner.name}</td>
                        <td className="p-2 text-[#5C5C5C]">{owner.entity_type}</td>
                        <td className="p-2 text-[#5C5C5C]">{owner.country}</td>
                        <td className="p-2 text-center">
                          <div style={{ width: '40px', height: '4px', background: '#0076D6', borderRadius: '2px', margin: '0 auto', marginBottom: '2px' }} />
                          <span className="font-bold">{Math.round(owner.confidence * 100)}%</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Risk Profile Tab */}
        {activeTab === 'Risk Profile' && (
          <div className="space-y-3">
            {/* Radar Chart */}
            <div className="bg-white border border-[#D0D7DE] rounded-sm p-4">
              <div className="text-[9px] font-bold text-[#5C5C5C] uppercase mb-3">Multidimensional Risk Profile</div>
              <ResponsiveContainer width="100%" height={300}>
                <RadarChart data={FIXTURE_RISK_DIMENSIONS}>
                  <PolarAngleAxis dataKey="dimension" tick={{ fontSize: 11, fill: '#5C5C5C' }} />
                  <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 9 }} />
                  <Radar name="Risk Score" dataKey="score" stroke="#D83933" fill="#D83933" fillOpacity={0.25} />
                </RadarChart>
              </ResponsiveContainer>
            </div>

            {/* Top Concerns & Positive Factors */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-white border border-[#D0D7DE] rounded-sm p-3">
                <div className="text-[9px] font-bold text-[#D83933] uppercase mb-2 flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" />
                  Top Concerns
                </div>
                <div className="space-y-1.5">
                  {FIXTURE_CONCERNS.map((concern, idx) => (
                    <div key={idx} className="text-[8px] bg-red-50 text-[#D83933] p-2 rounded border border-red-200 font-semibold">
                      • {concern}
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-white border border-[#D0D7DE] rounded-sm p-3">
                <div className="text-[9px] font-bold text-green-600 uppercase mb-2 flex items-center gap-1">
                  <CheckCircle className="w-3 h-3" />
                  Positive Factors
                </div>
                <div className="space-y-1.5">
                  {FIXTURE_POSITIVE_FACTORS.map((factor, idx) => (
                    <div key={idx} className="text-[8px] bg-green-50 text-green-700 p-2 rounded border border-green-200 font-semibold">
                      ✓ {factor}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Recommendation */}
            <div className="bg-amber-50 border border-amber-200 rounded-sm p-3">
              <div className="text-[9px] font-bold text-amber-900 uppercase mb-1">Analyst Recommendation</div>
              <p className="text-[9px] text-amber-800">
                Recommend <strong>Enhanced Screening</strong> for shipments involving these entities. Manual review required for any value &gt;$50K. Consider adding to watchlist for 90-day monitoring period.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
