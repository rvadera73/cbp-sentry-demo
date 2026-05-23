import React, { useState } from 'react';
import { ChevronDown, Download, Send, AlertCircle, CheckCircle2, Circle } from 'lucide-react';
import { BarChart, Bar, PieChart, Pie, RadarChart, Radar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line } from 'recharts';

interface ReferralPackageViewerProps {
  selectedReferral: any;
  selectedCase: any;
  findings: any[];
  referralNarrative: string;
  setReferralNarrative: (narrative: string) => void;
  onCompile: () => void;
  compileLoading: boolean;
  selectedCaseShipments?: any[];
  onSubmit?: () => void;
}

export function ReferralPackageViewer({
  selectedReferral,
  selectedCase,
  findings,
  referralNarrative,
  setReferralNarrative,
  onCompile,
  compileLoading,
  selectedCaseShipments = [],
  onSubmit,
}: ReferralPackageViewerProps) {
  const [activeSection, setActiveSection] = useState('executive-summary');
  const [referralStage, setReferralStage] = useState<'review' | 'narrative' | 'approve' | 'submitted'>('review');
  const [visitedSections, setVisitedSections] = useState<Set<string>>(new Set(['executive-summary']));
  const shipment = selectedCaseShipments?.[0];

  const sections = [
    { id: 'executive-summary', label: 'Executive Summary & Recommendation' },
    { id: 'table-3-1', label: 'Table 3-1: Shipment Identification' },
    { id: 'table-3-2', label: 'Table 3-2: Shipment Line-Item Detail' },
    { id: 'table-3-3', label: 'Table 3-3: Routing History' },
    { id: 'table-3-4', label: 'Table 3-4: Parties & Roles' },
    { id: 'table-3-5', label: 'Table 3-5: Entity Ownership Chain' },
    { id: 'table-3-6', label: 'Table 3-6: Historical Import Pattern' },
    { id: 'table-3-7', label: 'Table 3-7: Trade Flow Intelligence' },
    { id: 'table-3-8', label: 'Table 3-8: Document Review' },
    { id: 'table-3-9', label: 'Table 3-9: Document Consistency' },
    { id: 'table-3-10', label: 'Table 3-10: Manufacturing Verification' },
    { id: 'table-3-11', label: 'Table 3-11: Risk Indicator Summary' },
    { id: 'table-3-12', label: 'Table 3-12: Risk Score Breakdown' },
    { id: 'table-3-13', label: 'Table 3-13: What-If Scenarios' },
    { id: 'table-3-14', label: 'Table 3-14: Data Sources' },
    { id: 'narrative', label: 'Officer Narrative & Submit' },
  ];

  const handleSectionClick = (sectionId: string) => {
    setActiveSection(sectionId);
    setVisitedSections(prev => new Set(prev).add(sectionId));
  };

  const SectionButton = ({ section }: { section: typeof sections[0] }) => {
    const isVisited = visitedSections.has(section.id);
    return (
      <button
        onClick={() => handleSectionClick(section.id)}
        className={`w-full text-left px-3 py-2 rounded-sm text-[9px] font-bold transition-colors border-l-2 flex items-center space-x-2 ${
          activeSection === section.id
            ? 'bg-[#005EA2] text-white border-[#005EA2]'
            : 'text-slate-700 border-slate-300 hover:bg-slate-100'
        }`}
      >
        <span className="flex-1">{section.label}</span>
        {isVisited && <span className="text-[10px]">✓</span>}
      </button>
    );
  };

  // Helper to derive recommendation
  const recommendation = selectedCase?.risk_score >= 80
    ? 'HOLD FOR EXAMINATION'
    : selectedCase?.risk_score >= 50
    ? 'EXAMINE'
    : 'CLEAR';

  const recommendationColor = selectedCase?.risk_score >= 80
    ? 'bg-[#D83933]'
    : selectedCase?.risk_score >= 50
    ? 'bg-[#FFBE2E]'
    : 'bg-[#07A41E]';

  // Mock data for tables (derived from shipment)
  const table38Data = [
    { doc: 'Commercial Invoice', received: 'Yes', key: `Origin: ${shipment?.origin_country}`, match: 'Partial', concern: 'Needs production proof' },
    { doc: 'Packing List', received: 'Yes', key: `${shipment?.weight_kg} kg`, match: 'Yes', concern: 'No factory lot mapping' },
    { doc: 'Bill of Lading', received: 'Yes', key: `BOL-${shipment?.shipment_id?.slice(-5)}`, match: 'Yes', concern: 'Limited traceability' },
    { doc: 'Certificate of Origin', received: 'Yes', key: `Origin: ${shipment?.origin_country}`, match: 'Partial', concern: 'Template-like' },
    { doc: 'Purchase Order', received: 'Yes', key: 'Dated recently', match: 'Yes', concern: 'No source plant ID' },
    { doc: 'Factory Production Record', received: 'No', key: 'Not provided', match: 'No', concern: 'MAJOR GAP' },
    { doc: 'Bill of Materials', received: 'No', key: 'Not provided', match: 'No', concern: 'MAJOR GAP' },
    { doc: 'Raw Material Invoice', received: 'No', key: 'Not provided', match: 'No', concern: 'MAJOR GAP' },
  ];

  const table39Data = [
    { element: 'Shipper name', invoice: '✓', packing: '✓', bol: '✓', coo: '✓', status: 'Consistent' },
    { element: 'Country of origin', invoice: shipment?.origin_country, packing: shipment?.origin_country, bol: shipment?.origin_country, coo: shipment?.origin_country, status: 'Consistent' },
    { element: 'Commodity', invoice: shipment?.commodity_name, packing: shipment?.commodity_name, bol: shipment?.commodity_name, coo: shipment?.commodity_name, status: 'Consistent' },
    { element: 'Quantity', invoice: shipment?.weight_kg, packing: shipment?.weight_kg, bol: 'N/A', coo: 'N/A', status: 'Partial' },
    { element: 'Manufacturing details', invoice: 'Missing', packing: 'Missing', bol: 'Missing', coo: 'Missing', status: 'Missing' },
    { element: 'Plant location', invoice: 'Not stated', packing: 'Not stated', bol: 'Not stated', coo: 'Not stated', status: 'Missing' },
  ];

  const table310Data = [
    { item: 'Factory address', response: 'Industrial Zone', evidence: 'No details', assessment: 'Weak' },
    { item: 'Extrusion presses', response: 'Multiple units', evidence: 'No specs', assessment: 'Weak' },
    { item: 'Production capacity', response: 'Sufficient', evidence: 'No report', assessment: 'Weak' },
    { item: 'Raw aluminum source', response: 'Regional', evidence: 'No invoices', assessment: 'Weak' },
    { item: 'QC and tests', response: 'Available', evidence: 'Not provided', assessment: 'Missing' },
    { item: 'Work order linkage', response: 'Not provided', evidence: 'None', assessment: 'Missing' },
  ];

  const receivedCount = table38Data.filter(d => d.received === 'Yes').length;
  const pie38Data = [
    { name: 'Received', value: receivedCount, fill: '#22c55e' },
    { name: 'Missing', value: table38Data.length - receivedCount, fill: '#ef4444' },
  ];

  const consistencyScores = table39Data.map(d => ({
    name: d.element.substring(0, 10),
    score: d.status === 'Consistent' ? 3 : d.status === 'Partial' ? 2 : 1,
  }));

  const riskIndicators = [
    { indicator: 'Tariff/Duty Evasion Risk', evidence: shipment?.ad_cvd_applicable ? 'AD/CVD applicable' : 'Not flagged', level: 'High' },
    { indicator: 'ISF/Manifest Mismatch', evidence: shipment?.element9_is_mismatch ? 'Element 9 mismatch' : 'No mismatch', level: shipment?.element9_is_mismatch ? 'High' : 'Low' },
    { indicator: 'Dwell/AIS Anomaly', evidence: `${shipment?.dwell_days || 0} days`, level: (shipment?.dwell_days || 0) > 5 ? 'High' : 'Medium' },
    { indicator: 'Route Transshipment', evidence: `Via ${shipment?.route?.[1] || 'SG'}`, level: 'Medium-High' },
    { indicator: 'Country of Origin Shift', evidence: shipment?.origin_country, level: 'Medium-High' },
  ];

  const whatIfScenarios = [
    { scenario: 'If Altana validates supplier', ifTrue: '+5 points (reduced risk)', ifFalse: '-8 points (major risk)', impact: 'Moderate' },
    { scenario: 'If factory records received', ifTrue: 'Verification possible', ifFalse: 'Deny entry', impact: 'Critical' },
    { scenario: 'If ISF corrected to China origin', ifTrue: '-15 points', ifFalse: 'Current score stands', impact: 'Moderate' },
  ];

  const dataSources = [
    { source: 'Manifest Data (ISF)', usage: 'Shipper, commodity, quantity verification' },
    { source: 'AIS/Vessel Tracking', usage: 'Routing, dwell time, transshipment detection' },
    { source: 'Altana Supply Chain', usage: 'Supplier validation, origin verification' },
    { source: 'CBP Targeting System', usage: 'Rule-hit detection, entry precedent' },
    { source: 'Harmonized Tariff Schedule', usage: 'Commodity classification, AD/CVD rates' },
    { source: 'Entity Risk Database', usage: 'Party reputation, nexus analysis' },
    { source: 'Trade Activity History', usage: 'Pattern anomaly detection, corridor risk' },
    { source: 'Port Authority Records', usage: 'Cargo receipt, warehouse tracking' },
    { source: 'Customs Broker Licensing', usage: 'Party credentials, compliance history' },
    { source: 'Financial Institution Data', usage: 'Payment flows, fund sourcing' },
    { source: 'Document Metadata', usage: 'Digital signature, timestamp validation' },
    { source: 'AI Model Scoring', usage: 'Multi-factor risk calculation' },
    { source: 'Officer Field Observations', usage: 'Physical inspection findings' },
    { source: 'Intelligence Networks', usage: 'Trade fraud indicators' },
  ];

  // Progress stages
  const stages = ['review', 'narrative', 'approve', 'submitted'] as const;
  const stageLabels = ['Review Tables', 'Write Narrative', 'Approve', 'Submitted'];
  const currentStageIndex = stages.indexOf(referralStage);

  return (
    <div className="flex flex-col h-full overflow-hidden bg-[#F7F9FC]">
      {/* Progress Bar */}
      {referralStage !== 'submitted' && (
        <div className="bg-white border-b border-[#D0D7DE] px-6 py-3">
          <div className="flex items-center justify-center space-x-12">
            {stageLabels.map((label, idx) => (
              <div key={idx} className="flex items-center space-x-2">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold ${
                  idx < currentStageIndex ? 'bg-[#005EA2] text-white' :
                  idx === currentStageIndex ? 'bg-[#005EA2] text-white' :
                  'bg-slate-300 text-slate-600'
                }`}>
                  {idx < currentStageIndex ? '✓' : (idx + 1)}
                </div>
                <span className={`text-[10px] font-bold ${idx <= currentStageIndex ? 'text-[#0B1F33]' : 'text-slate-600'}`}>
                  {label}
                </span>
                {idx < stageLabels.length - 1 && (
                  <div className={`w-12 h-0.5 ${idx < currentStageIndex ? 'bg-[#005EA2]' : 'bg-slate-300'}`} />
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Two-Panel Layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar: Section Navigator */}
        <div className="w-56 border-r border-[#D0D7DE] bg-white flex flex-col shadow-sm">
          <div className="p-4 border-b border-[#D0D7DE]">
            <h3 className="text-[10px] font-bold text-[#0B1F33] uppercase">REFERRAL PACKAGE</h3>
            <p className="text-[8px] text-slate-600 mt-1 font-mono">{sections.length} sections • {selectedCase?.case_id}</p>
          </div>
          <nav className="flex-1 overflow-y-auto p-2 space-y-1">
            {sections.map(section => (
              <SectionButton key={section.id} section={section} />
            ))}
          </nav>
          <div className="p-3 border-t border-[#D0D7DE]">
            <button
              onClick={onCompile}
              disabled={compileLoading}
              className="w-full px-3 py-2 bg-[#005EA2] hover:bg-[#0076D6] disabled:opacity-50 text-white text-[9px] font-bold rounded-sm transition-colors"
            >
              {compileLoading ? 'COMPILING...' : 'COMPILE PACKAGE'}
            </button>
          </div>
        </div>

        {/* Main Content Area */}
        <div className="flex-1 overflow-y-auto p-6">
        {!selectedReferral && !shipment ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-slate-500">
              <p className="text-sm font-bold mb-2">Select a case and click "COMPILE PACKAGE"</p>
              <p className="text-[9px]">Referral sections will generate from live shipment data</p>
            </div>
          </div>
        ) : (
          <div className="max-w-4xl space-y-4">
            {/* SECTION: Executive Summary & Recommendation */}
            {activeSection === 'executive-summary' && (
              <div className="space-y-4">
                <div className={`${recommendationColor} text-white rounded-sm p-4 border-l-4 border-white`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-bold uppercase">RECOMMENDATION</h3>
                      <p className="text-xs mt-1">Based on comprehensive trade risk analysis</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xl font-black font-mono">{recommendation}</p>
                      <p className="text-[9px] mt-1">Risk Score: {selectedCase?.risk_score}/100</p>
                    </div>
                  </div>
                </div>

                <div className="bg-white rounded-sm border border-[#D0D7DE] p-4">
                  <h3 className="text-sm font-bold text-[#0B1F33] mb-3">CASE HEADER</h3>
                  <div className="grid grid-cols-2 gap-4 text-xs">
                    <div><span className="font-bold">Case ID:</span> {selectedCase?.case_id}</div>
                    <div><span className="font-bold">Shipment ID:</span> {shipment?.shipment_id}</div>
                    <div><span className="font-bold">Date:</span> {shipment?.date}</div>
                    <div><span className="font-bold">Port:</span> {shipment?.destination_country}</div>
                  </div>
                </div>

                <div className="bg-white rounded-sm border border-[#D0D7DE] p-4">
                  <h3 className="text-sm font-bold text-[#0B1F33] mb-3">EXECUTIVE SUMMARY</h3>
                  <p className="text-xs text-slate-700 leading-relaxed">
                    Investigation of {shipment?.shipper_name} shipment {shipment?.shipment_id} reveals systematic trade compliance indicators.
                    Multi-factor risk assessment (ML model) scored {selectedCase?.risk_score}/100 across 7 dimensions: documentation,
                    commodity risk, routing anomaly, party profile, corridor risk, pattern anomaly, and time sensitivity.
                    {shipment?.ad_cvd_applicable && ` AD/CVD duty rates apply at ${((shipment?.ad_cvd_rate ?? 0) * 100).toFixed(1)}%.`}
                    Risk drivers include {shipment?.element9_is_mismatch ? 'ISF Element 9 mismatch' : 'manifest anomalies'} and
                    transshipment via {shipment?.route?.[1] || 'Singapore'}. Recommend {recommendation} per 19 USC § 1516a.
                  </p>
                </div>
              </div>
            )}

            {/* TABLE 3-1: Shipment Identification */}
            {activeSection === 'table-3-1' && (
              <div className="bg-white rounded-sm border border-[#D0D7DE] p-4">
                <h3 className="text-sm font-bold text-[#0B1F33] mb-4">TABLE 3-1: SHIPMENT IDENTIFICATION</h3>
                <div className="space-y-2 text-xs">
                  {[
                    ['Shipper Name', shipment?.shipper_name],
                    ['Shipper Country', shipment?.origin_country],
                    ['Consignee', shipment?.manifest_data?.consignee],
                    ['Port of Lading', shipment?.origin_country],
                    ['Port of Unlading', shipment?.destination_country],
                    ['Cargo Description', shipment?.commodity_name],
                    ['HTS Code', shipment?.hs_code],
                    ['Bill of Lading', `BOL-${shipment?.shipment_id?.slice(-5)}`],
                    ['Declared Country of Origin', shipment?.origin_country],
                    ['Estimated Arrival', shipment?.date],
                  ].map(([label, value], idx) => (
                    <div key={idx} className={`grid grid-cols-2 gap-4 py-1 px-2 ${idx % 2 === 0 ? 'bg-slate-50' : ''}`}>
                      <span className="font-bold">{label}</span>
                      <span>{value || '—'}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* TABLE 3-2: Shipment Line-Item Detail */}
            {activeSection === 'table-3-2' && (
              <div className="bg-white rounded-sm border border-[#D0D7DE] p-4">
                <h3 className="text-sm font-bold text-[#0B1F33] mb-4">TABLE 3-2: SHIPMENT LINE-ITEM DETAIL</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-[9px] border-collapse">
                    <thead className="bg-[#005EA2] text-white">
                      <tr>
                        <th className="text-left px-2 py-2">Line</th>
                        <th className="text-left px-2 py-2">SKU</th>
                        <th className="text-left px-2 py-2">Description</th>
                        <th className="text-right px-2 py-2">Qty</th>
                        <th className="text-left px-2 py-2">Unit</th>
                        <th className="text-right px-2 py-2">Value</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="bg-slate-50">
                        <td className="px-2 py-1">1</td>
                        <td className="px-2 py-1">{shipment?.hs_code}</td>
                        <td className="px-2 py-1">{shipment?.commodity_name}</td>
                        <td className="text-right px-2 py-1">{shipment?.weight_kg}</td>
                        <td className="px-2 py-1">kg</td>
                        <td className="text-right px-2 py-1">${shipment?.manifest_data?.declared_value_usd || 0}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* TABLE 3-3: Routing History */}
            {activeSection === 'table-3-3' && (
              <div className="bg-white rounded-sm border border-[#D0D7DE] p-4">
                <h3 className="text-sm font-bold text-[#0B1F33] mb-4">TABLE 3-3: ROUTING HISTORY</h3>
                <div className="space-y-2">
                  {[
                    ['Container Stuffed', shipment?.origin_country, shipment?.date, 'Loading terminal'],
                    ['Gate Out', shipment?.origin_country, shipment?.date, 'Export customs clearance'],
                    ['Vessel Departure', shipment?.origin_country, shipment?.date, `Via ${shipment?.route?.[1] || 'SG'}`],
                    ['Transit Update', shipment?.route?.[1] || 'SG', shipment?.date, `Dwell: ${shipment?.dwell_days || 0}d`],
                    ['Estimated Arrival', shipment?.destination_country, shipment?.date, 'Import port'],
                  ].map(([event, location, date, notes], idx) => (
                    <div key={idx} className={`grid grid-cols-4 gap-4 py-2 px-3 text-[9px] ${idx % 2 === 0 ? 'bg-slate-50' : ''}`}>
                      <span className="font-bold">{event}</span>
                      <span>{location}</span>
                      <span>{date}</span>
                      <span className="text-slate-600">{notes}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* TABLE 3-4: Parties & Roles */}
            {activeSection === 'table-3-4' && (
              <div className="bg-white rounded-sm border border-[#D0D7DE] p-4">
                <h3 className="text-sm font-bold text-[#0B1F33] mb-4">TABLE 3-4: PARTIES & ROLES</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-[9px] border-collapse">
                    <thead className="bg-[#005EA2] text-white">
                      <tr>
                        <th className="text-left px-2 py-2">Role</th>
                        <th className="text-left px-2 py-2">Entity</th>
                        <th className="text-left px-2 py-2">Country</th>
                        <th className="text-left px-2 py-2">Risk Note</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[
                        ['Shipper', shipment?.shipper_name, shipment?.origin_country, 'Primary suspect'],
                        ['Consignee', shipment?.manifest_data?.consignee, shipment?.destination_country, 'Verify independence'],
                        ['Freight Forwarder', 'TBD', 'TBD', 'Licensing check'],
                        ['Carrier', 'TBD', 'TBD', 'Vessel owner verified'],
                        ['Customs Broker', 'TBD', 'TBD', 'Entry filer'],
                      ].map(([role, entity, country, risk], idx) => (
                        <tr key={idx} className={idx % 2 === 0 ? 'bg-slate-50' : 'bg-white'}>
                          <td className="px-2 py-1 font-bold">{role}</td>
                          <td className="px-2 py-1">{entity}</td>
                          <td className="px-2 py-1">{country}</td>
                          <td className="px-2 py-1 text-slate-600">{risk}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* TABLE 3-5: Entity Ownership Chain */}
            {activeSection === 'table-3-5' && (
              <div className="bg-white rounded-sm border border-[#D0D7DE] p-4">
                <h3 className="text-sm font-bold text-[#0B1F33] mb-4">TABLE 3-5: ENTITY OWNERSHIP CHAIN</h3>
                <div className="space-y-3">
                  {[
                    { tier: '1 (Declared)', entity: shipment?.shipper_name, juris: shipment?.origin_country, evidence: 'ISF shipper record' },
                    { tier: '2 (Intermediate)', entity: 'TBD - Shell Entity Analysis', juris: 'TBD', evidence: 'Senzing nexus' },
                    { tier: '3 (Principal)', entity: 'Chinese Manufacturing Principal', juris: 'China', evidence: 'Supply chain nexus' },
                  ].map((row, idx) => (
                    <div key={idx} className="bg-slate-50 border-l-4 border-blue-500 p-3">
                      <div className="grid grid-cols-3 gap-4 text-[9px]">
                        <div><span className="font-bold">Tier {row.tier}:</span> {row.entity}</div>
                        <div><span className="font-bold">Jurisdiction:</span> {row.juris}</div>
                        <div><span className="font-bold">Evidence:</span> {row.evidence}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* TABLE 3-6: Historical Import Pattern */}
            {activeSection === 'table-3-6' && (
              <div className="bg-white rounded-sm border border-[#D0D7DE] p-4 space-y-4">
                <h3 className="text-sm font-bold text-[#0B1F33] mb-4">TABLE 3-6: HISTORICAL IMPORT PATTERN</h3>
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={[
                    { month: 'Jan', shipments: 2, weight: 15200, origin: shipment?.origin_country },
                    { month: 'Feb', shipments: 3, weight: 22500, origin: shipment?.origin_country },
                    { month: 'Mar', shipments: 2, weight: 18900, origin: shipment?.origin_country },
                  ]}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" />
                    <YAxis label={{ value: 'Weight (kg)', angle: -90, position: 'insideLeft' }} />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="weight" stroke="#005EA2" />
                  </LineChart>
                </ResponsiveContainer>
                <div className="text-[9px] text-slate-600">
                  <p className="font-bold mb-2">Analysis:</p>
                  <p>Shipper exhibits recurring import pattern with origin-shifting behavior. Three entries in Q1 2026 show declared origin consistency but vessel routing changes. Dwell periods inconsistent with normal transit times.</p>
                </div>
              </div>
            )}

            {/* TABLE 3-7: Trade Flow Intelligence */}
            {activeSection === 'table-3-7' && (
              <div className="bg-white rounded-sm border border-[#D0D7DE] p-4">
                <h3 className="text-sm font-bold text-[#0B1F33] mb-4">TABLE 3-7: TRADE FLOW INTELLIGENCE</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-[9px] border-collapse">
                    <thead className="bg-[#005EA2] text-white">
                      <tr>
                        <th className="text-left px-2 py-2">Shipment ID</th>
                        <th className="text-left px-2 py-2">Month</th>
                        <th className="text-left px-2 py-2">Origin</th>
                        <th className="text-left px-2 py-2">Export Port</th>
                        <th className="text-right px-2 py-2">Transit Days</th>
                        <th className="text-right px-2 py-2">Qty (kg)</th>
                        <th className="text-right px-2 py-2">Unit Value</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[
                        [shipment?.shipment_id, 'Mar', shipment?.origin_country, shipment?.route?.[0] || 'VN Port', '14', shipment?.weight_kg, '45/kg'],
                        ['SHP-000730', 'Feb', shipment?.origin_country, shipment?.route?.[0] || 'VN Port', '13', '22,500', '43/kg'],
                        ['SHP-000729', 'Jan', shipment?.origin_country, shipment?.route?.[0] || 'VN Port', '15', '15,200', '42/kg'],
                      ].map((row, idx) => (
                        <tr key={idx} className={idx % 2 === 0 ? 'bg-slate-50' : 'bg-white'}>
                          {row.map((cell, cidx) => (
                            <td key={cidx} className={`px-2 py-1 ${cidx === 0 ? 'font-bold' : ''} ${cidx > 3 ? 'text-right' : ''}`}>
                              {cell}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* TABLE 3-8: Document Review */}
            {activeSection === 'table-3-8' && (
              <div className="bg-white rounded-sm border border-[#D0D7DE] p-4 space-y-4">
                <h3 className="text-sm font-bold text-[#0B1F33] mb-4">TABLE 3-8: DOCUMENT REVIEW — CORE EVIDENCE SUPPORT</h3>
                <div className="overflow-x-auto mb-4">
                  <table className="w-full text-[9px] border-collapse">
                    <thead className="bg-[#005EA2] text-white">
                      <tr>
                        <th className="text-left px-2 py-2">Document Type</th>
                        <th className="text-center px-2 py-2">Received?</th>
                        <th className="text-left px-2 py-2">Key Data Point</th>
                        <th className="text-center px-2 py-2">Match</th>
                        <th className="text-left px-2 py-2">Concern</th>
                      </tr>
                    </thead>
                    <tbody>
                      {table38Data.map((row, i) => (
                        <tr key={i} className={i % 2 === 0 ? 'bg-slate-50' : 'bg-white'}>
                          <td className="px-2 py-1">{row.doc}</td>
                          <td className="text-center"><span className={`px-1 rounded text-[8px] font-bold ${row.received === 'Yes' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>{row.received}</span></td>
                          <td className="px-2 py-1">{row.key}</td>
                          <td className="text-center"><span className={`text-[8px] font-bold ${row.match === 'Yes' ? 'text-green-600' : 'text-amber-600'}`}>{row.match}</span></td>
                          <td className={`px-2 py-1 ${row.concern.includes('MAJOR') ? 'text-red-600 font-bold' : 'text-slate-600'}`}>{row.concern}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="flex gap-4">
                  <ResponsiveContainer width="50%" height={200}>
                    <PieChart>
                      <Pie data={pie38Data} cx="50%" cy="50%" labelLine={false} label={(d) => d.name} outerRadius={60} dataKey="value">
                        {pie38Data.map((_, i) => <Cell key={i} fill={pie38Data[i].fill} />)}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="flex-1 text-[9px] text-slate-600">
                    <p className="font-bold mb-2">Analysis:</p>
                    <p>5 of 8 documents provided. Missing critical manufacturing verification: Factory Production Records, Bill of Materials, Raw Material Invoices. These gaps prevent independent verification of Vietnam origin claim.</p>
                  </div>
                </div>
              </div>
            )}

            {/* TABLE 3-9: Document Consistency */}
            {activeSection === 'table-3-9' && (
              <div className="bg-white rounded-sm border border-[#D0D7DE] p-4 space-y-4">
                <h3 className="text-sm font-bold text-[#0B1F33] mb-4">TABLE 3-9: DOCUMENT CONSISTENCY ANALYSIS</h3>
                <div className="overflow-x-auto mb-4">
                  <table className="w-full text-[9px] border-collapse">
                    <thead className="bg-[#005EA2] text-white">
                      <tr>
                        <th className="text-left px-2 py-2">Data Element</th>
                        <th className="text-left px-2 py-2">Invoice</th>
                        <th className="text-left px-2 py-2">Packing List</th>
                        <th className="text-left px-2 py-2">BOL</th>
                        <th className="text-left px-2 py-2">COO</th>
                        <th className="text-center px-2 py-2">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {table39Data.map((row, i) => (
                        <tr key={i} className={i % 2 === 0 ? 'bg-slate-50' : 'bg-white'}>
                          <td className="px-2 py-1 font-bold">{row.element}</td>
                          <td className="px-2 py-1 text-[8px]">{row.invoice}</td>
                          <td className="px-2 py-1 text-[8px]">{row.packing}</td>
                          <td className="px-2 py-1 text-[8px]">{row.bol}</td>
                          <td className="px-2 py-1 text-[8px]">{row.coo}</td>
                          <td className="text-center"><span className={`px-1 rounded text-[8px] font-bold ${row.status === 'Consistent' ? 'bg-green-100 text-green-800' : row.status === 'Partial' ? 'bg-amber-100 text-amber-800' : 'bg-red-100 text-red-800'}`}>{row.status}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="flex gap-4">
                  <ResponsiveContainer width="50%" height={200}>
                    <BarChart data={consistencyScores}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" tick={{ fontSize: 8 }} angle={-45} height={60} />
                      <YAxis label={{ value: 'Score', angle: -90, position: 'insideLeft' }} />
                      <Tooltip />
                      <Bar dataKey="score" fill="#0076D6" />
                    </BarChart>
                  </ResponsiveContainer>
                  <div className="flex-1 text-[9px] text-slate-600">
                    <p className="font-bold mb-2">Analysis:</p>
                    <p>Core shipment data (name, origin, commodity, quantity) is consistent across primary documents. Manufacturing details completely absent from all documents, creating unresolvable verification gap for country-of-origin claim.</p>
                  </div>
                </div>
              </div>
            )}

            {/* TABLE 3-10: Manufacturing Verification */}
            {activeSection === 'table-3-10' && (
              <div className="bg-white rounded-sm border border-[#D0D7DE] p-4">
                <h3 className="text-sm font-bold text-[#0B1F33] mb-4">TABLE 3-10: SUPPLIER MANUFACTURING VERIFICATION ASSESSMENT</h3>
                <div className="overflow-x-auto mb-4">
                  <table className="w-full text-[9px] border-collapse">
                    <thead className="bg-[#005EA2] text-white">
                      <tr>
                        <th className="text-left px-2 py-2">Verification Item</th>
                        <th className="text-left px-2 py-2">Supplier Response</th>
                        <th className="text-left px-2 py-2">Supporting Evidence</th>
                        <th className="text-center px-2 py-2">Assessment</th>
                      </tr>
                    </thead>
                    <tbody>
                      {table310Data.map((row, i) => (
                        <tr key={i} className={i % 2 === 0 ? 'bg-slate-50' : 'bg-white'}>
                          <td className="px-2 py-1 font-bold">{row.item}</td>
                          <td className="px-2 py-1 text-[8px]">{row.response}</td>
                          <td className="px-2 py-1 text-[8px]">{row.evidence}</td>
                          <td className="text-center"><span className={`px-1 rounded text-[8px] font-bold ${row.assessment === 'Strong' ? 'bg-green-100 text-green-800' : row.assessment === 'Moderate' ? 'bg-amber-100 text-amber-800' : 'bg-red-100 text-red-800'}`}>{row.assessment}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="text-[9px] text-slate-600 bg-slate-50 p-3 rounded">
                  <p className="font-bold mb-2">Analysis:</p>
                  <p>All supplier responses are vague or provide no supporting documentation. Factory address lacks street details. No capacity reports, equipment inventories, work orders, or QC records provided. Insufficient evidence to substantiate Vietnam manufacturing claim. Recommend HOLD pending factory facility verification.</p>
                </div>
              </div>
            )}

            {/* TABLE 3-11: Risk Indicator Summary */}
            {activeSection === 'table-3-11' && (
              <div className="bg-white rounded-sm border border-[#D0D7DE] p-4">
                <h3 className="text-sm font-bold text-[#0B1F33] mb-4">TABLE 3-11: RISK INDICATOR SUMMARY</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-[9px] border-collapse">
                    <thead className="bg-[#005EA2] text-white">
                      <tr>
                        <th className="text-left px-2 py-2">Indicator</th>
                        <th className="text-left px-2 py-2">Sample Evidence</th>
                        <th className="text-center px-2 py-2">Risk Level</th>
                        <th className="text-left px-2 py-2">Why It Matters</th>
                      </tr>
                    </thead>
                    <tbody>
                      {riskIndicators.map((row, i) => (
                        <tr key={i} className={i % 2 === 0 ? 'bg-slate-50' : 'bg-white'}>
                          <td className="px-2 py-1 font-bold">{row.indicator}</td>
                          <td className="px-2 py-1">{row.evidence}</td>
                          <td className="text-center"><span className={`px-1 rounded text-[8px] font-bold ${row.level === 'High' ? 'bg-red-100 text-red-800' : 'bg-amber-100 text-amber-800'}`}>{row.level}</span></td>
                          <td className="px-2 py-1 text-slate-600">Trigger for inspection</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* TABLE 3-12: Risk Score Breakdown */}
            {activeSection === 'table-3-12' && (
              <div className="bg-white rounded-sm border border-[#D0D7DE] p-4 space-y-4">
                <h3 className="text-sm font-bold text-[#0B1F33] mb-4">TABLE 3-12: RISK SCORE BREAKDOWN (ML MODEL)</h3>
                {shipment?.risk_breakdown?.components ? (
                  <>
                    <div className="overflow-x-auto">
                      <table className="w-full text-[10px] border-collapse">
                        <thead className="bg-[#005EA2] text-white">
                          <tr>
                            <th className="text-left px-3 py-2">Risk Category</th>
                            <th className="text-right px-3 py-2">Weight %</th>
                            <th className="text-right px-3 py-2">Score (0-10)</th>
                            <th className="text-right px-3 py-2">Weighted Result</th>
                          </tr>
                        </thead>
                        <tbody>
                          {shipment.risk_breakdown.components.map((comp: any, idx: number) => (
                            <tr key={idx} className={idx % 2 === 0 ? 'bg-slate-50' : 'bg-white'}>
                              <td className="text-left px-3 py-2 font-semibold">{comp.component}</td>
                              <td className="text-right px-3 py-2">{comp.weight.toFixed(1)}</td>
                              <td className="text-right px-3 py-2 font-bold">{comp.score.toFixed(1)}</td>
                              <td className="text-right px-3 py-2 text-blue-600 font-bold">{comp.weighted_result.toFixed(1)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <div className="bg-[#0B1F33] text-white p-4 rounded text-[10px] font-mono space-y-2">
                      <div className="flex justify-between"><span>Subtotal (Pre-Adjustment)</span><span>{shipment.risk_breakdown.subtotal.toFixed(1)}</span></div>
                      {shipment.audit_trail?.model_adjustment !== 0 && (
                        <div className="flex justify-between text-cyan-300"><span>Altana Adjustment</span><span className="font-bold">{shipment.audit_trail.model_adjustment > 0 ? '+' : ''}{shipment.audit_trail.model_adjustment}</span></div>
                      )}
                      <div className="border-t border-slate-500 pt-2 flex justify-between font-bold text-lg"><span>FINAL RISK SCORE</span><span className={selectedCase?.risk_score >= 80 ? 'text-[#D83933]' : 'text-[#FFBE2E]'}>{shipment.risk_breakdown.final_score.toFixed(1)}/100</span></div>
                    </div>
                  </>
                ) : (
                  <p className="text-xs text-slate-600">Risk breakdown data not available. Check back in a moment.</p>
                )}
              </div>
            )}

            {/* TABLE 3-13: What-If Scenarios */}
            {activeSection === 'table-3-13' && (
              <div className="bg-white rounded-sm border border-[#D0D7DE] p-4">
                <h3 className="text-sm font-bold text-[#0B1F33] mb-4">TABLE 3-13: WHAT-IF SCENARIOS</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-[9px] border-collapse">
                    <thead className="bg-[#005EA2] text-white">
                      <tr>
                        <th className="text-left px-2 py-2">Scenario</th>
                        <th className="text-left px-2 py-2">If True</th>
                        <th className="text-left px-2 py-2">If False</th>
                        <th className="text-center px-2 py-2">Impact</th>
                      </tr>
                    </thead>
                    <tbody>
                      {whatIfScenarios.map((row, i) => (
                        <tr key={i} className={i % 2 === 0 ? 'bg-slate-50' : 'bg-white'}>
                          <td className="px-2 py-1 font-bold">{row.scenario}</td>
                          <td className="px-2 py-1 text-green-700">{row.ifTrue}</td>
                          <td className="px-2 py-1 text-red-700">{row.ifFalse}</td>
                          <td className="text-center"><span className={`px-1 rounded text-[8px] font-bold ${row.impact === 'Critical' ? 'bg-red-100 text-red-800' : 'bg-amber-100 text-amber-800'}`}>{row.impact}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* TABLE 3-14: Data Sources */}
            {activeSection === 'table-3-14' && (
              <div className="bg-white rounded-sm border border-[#D0D7DE] p-4">
                <h3 className="text-sm font-bold text-[#0B1F33] mb-4">TABLE 3-14: DATA SOURCES & METHODOLOGY</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-[9px] border-collapse">
                    <thead className="bg-[#005EA2] text-white">
                      <tr>
                        <th className="text-left px-2 py-2">Data Source</th>
                        <th className="text-left px-2 py-2">Use in Assessment</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dataSources.map((row, i) => (
                        <tr key={i} className={i % 2 === 0 ? 'bg-slate-50' : 'bg-white'}>
                          <td className="px-2 py-1 font-bold">{row.source}</td>
                          <td className="px-2 py-1">{row.usage}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* NARRATIVE & SUBMIT */}
            {activeSection === 'narrative' && (
              <div className="space-y-4">
                <div className="bg-white rounded-sm border border-[#D0D7DE] p-4">
                  <h3 className="text-sm font-bold text-[#0B1F33] mb-3">OFFICER NARRATIVE & RECOMMENDATION</h3>
                  <textarea
                    value={referralNarrative}
                    onChange={(e) => setReferralNarrative(e.target.value)}
                    className="w-full h-64 bg-[#0B1F33] text-slate-100 font-mono text-[10px] p-3 rounded-sm border border-slate-600 focus:border-[#005EA2] focus:outline-none"
                    placeholder="Enter officer narrative and final recommendation..."
                  />
                  <div className="mt-3 flex gap-2">
                    <button
                      onClick={onCompile}
                      disabled={compileLoading}
                      className="px-4 py-2 bg-[#005EA2] hover:bg-[#0076D6] disabled:opacity-50 text-white text-[9px] font-bold rounded-sm"
                    >
                      {compileLoading ? 'GENERATING...' : 'COMPILE AI DRAFT'}
                    </button>
                    <button className="px-4 py-2 bg-[#07A41E] hover:bg-[#06843E] text-white text-[9px] font-bold rounded-sm flex items-center space-x-1">
                      <Send className="w-3 h-3" />
                      <span>SUBMIT REFERRAL</span>
                    </button>
                  </div>
                </div>

                <div className="bg-white rounded-sm border border-[#D0D7DE] p-4">
                  <h3 className="text-sm font-bold text-[#0B1F33] mb-3">FINAL REVIEW</h3>
                  <div className={`${recommendationColor} text-white p-3 rounded-sm text-[10px] font-bold`}>
                    RECOMMENDATION: {recommendation} | Risk Score: {selectedCase?.risk_score}/100
                  </div>
                  <div className="mt-3 text-[9px] text-slate-600">
                    <p className="mb-2"><strong>DHS Trade Referral Summary:</strong></p>
                    <p>This referral package includes all 14 statutory sections required for Import Safety Bureau review under 19 USC § 1516a. Evidence supports {recommendation.toLowerCase()} action. All supporting documentation, ML risk scoring methodology, and officer findings are included.</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Bottom Action Bar */}
      <div className="bg-white border-t border-[#D0D7DE] px-6 py-4">
        {referralStage === 'review' && (
          <div className="flex justify-end">
            <button
              onClick={() => {
                setReferralStage('narrative');
                handleSectionClick('narrative');
              }}
              className="px-4 py-2 bg-[#005EA2] hover:bg-[#0076D6] text-white text-[10px] font-bold rounded-sm flex items-center space-x-2"
            >
              <span>Next: Write Narrative</span>
              <span>→</span>
            </button>
          </div>
        )}

        {referralStage === 'narrative' && (
          <div className="flex justify-between">
            <button
              onClick={() => setReferralStage('review')}
              className="px-4 py-2 bg-slate-300 hover:bg-slate-400 text-slate-800 text-[10px] font-bold rounded-sm flex items-center space-x-2"
            >
              <span>←</span>
              <span>Back to Review</span>
            </button>
            <button
              onClick={() => setReferralStage('approve')}
              disabled={referralNarrative.trim() === ''}
              className="px-4 py-2 bg-[#005EA2] hover:bg-[#0076D6] disabled:opacity-50 disabled:cursor-not-allowed text-white text-[10px] font-bold rounded-sm flex items-center space-x-2"
            >
              <span>Next: Approve</span>
              <span>→</span>
            </button>
          </div>
        )}

        {referralStage === 'approve' && (
          <div className="space-y-3">
            <div className="bg-slate-50 border border-[#D0D7DE] p-3 rounded-sm">
              <div className="grid grid-cols-3 gap-4 text-[9px]">
                <div><span className="font-bold">Case ID:</span> {selectedCase?.case_id}</div>
                <div><span className="font-bold">Risk Score:</span> {selectedCase?.risk_score}/100</div>
                <div><span className="font-bold">Recommendation:</span> {recommendation}</div>
              </div>
            </div>
            <div className="flex justify-between">
              <button
                onClick={() => setReferralStage('narrative')}
                className="px-4 py-2 bg-slate-300 hover:bg-slate-400 text-slate-800 text-[10px] font-bold rounded-sm flex items-center space-x-2"
              >
                <span>←</span>
                <span>Back</span>
              </button>
              <button
                onClick={() => {
                  if (onSubmit) onSubmit();
                  setReferralStage('submitted');
                }}
                className="px-6 py-2 bg-[#07A41E] hover:bg-[#06843E] text-white text-[10px] font-bold rounded-sm flex items-center space-x-2"
              >
                <Send className="w-3 h-3" />
                <span>SUBMIT TO DHS</span>
              </button>
            </div>
          </div>
        )}

        {referralStage === 'submitted' && (
          <div className="bg-green-100 border border-green-300 text-green-800 p-3 rounded-sm text-[9px]">
            <div className="flex items-center space-x-2 font-bold">
              <CheckCircle2 className="w-5 h-5" />
              <span>✓ Referral Package Submitted — {selectedCase?.case_id} — {new Date().toLocaleDateString()}</span>
            </div>
          </div>
        )}
      </div>
      </div>
    </div>
  );
}
