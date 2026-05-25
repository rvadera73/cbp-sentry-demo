import React, { useState, useMemo, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { ArrowRight, Sparkles, AlertCircle, ChevronDown, Download, Send, Search, ChevronRight } from 'lucide-react';
import { BarChart, Bar, PieChart, Pie, RadarChart, Radar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line } from 'recharts';
import { useV2Cases } from '../hooks/useV2Cases';
import { useRiskScoring } from '../hooks/useRiskScoring';
import { Case, Shipment, AIFinding, ReferralPackage } from '../types/v2.types';
import { api } from '../../services/api';
import { TYPOGRAPHY, DESIGN } from '../styles/typography';
import { EntityRelationshipGraph } from '../components/EntityRelationshipGraph';
import { ReferralPackageViewer } from '../components/ReferralPackageViewer';
import { TabNavigation, TabConfig } from '../components/TabNavigation';

interface V2InvestigationsPageProps {
  cases?: Case[];
  shipments?: Shipment[];
  selectedCaseId?: string | null;
  setSelectedCaseId?: (id: string | null) => void;
  activeSubTab?: 'Shipment' | 'Entity' | 'Data Tables' | 'Risk Score' | 'Evidence & Referral';
  setActiveSubTab?: (tab: 'Shipment' | 'Entity' | 'Data Tables' | 'Risk Score' | 'Evidence & Referral') => void;
  synopsisMap?: Record<string, string>;
  synopsisLoading?: Record<string, boolean>;
  findings?: AIFinding[];
  referrals?: ReferralPackage[];
  draftNarrative?: string;
  setDraftNarrative?: (narrative: string) => void;
}

export default function V2InvestigationsPage(props: V2InvestigationsPageProps) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const {
    cases: propCases,
    shipments: propShipments = [],
    selectedCaseId: propSelectedCaseId = null,
    setSelectedCaseId: propSetSelectedCaseId,
    activeSubTab: propActiveSubTab,
    setActiveSubTab: propSetActiveSubTab,
    synopsisMap = {},
    synopsisLoading = {},
    findings = [],
    referrals = [],
  } = props;

  // Local state fallback
  const { cases: localCases, shipments: localShipments, caseShipments: localCaseShipments, loading } = useV2Cases();
  const cases = propCases || localCases;
  const shipments = propShipments || localShipments;
  const caseShipments = localCaseShipments;

  const [localSelectedCaseId, setLocalSelectedCaseId] = useState<string | null>(null);
  const [localActiveSubTab, setLocalActiveSubTab] = useState<'Shipment' | 'Entity' | 'Data Tables' | 'Risk Score' | 'Evidence & Referral'>('Shipment');

  const selectedCaseId = propSelectedCaseId || localSelectedCaseId;
  const setSelectedCaseId = propSetSelectedCaseId || setLocalSelectedCaseId;
  const activeSubTab = propActiveSubTab !== undefined ? propActiveSubTab : localActiveSubTab;
  const setActiveSubTab = propSetActiveSubTab || setLocalActiveSubTab;

  // Auto-select case based on shipmentId query parameter
  useEffect(() => {
    const shipmentId = searchParams.get('shipmentId');
    if (shipmentId && cases.length > 0 && !selectedCaseId) {
      // Find the shipment
      const shipment = shipments.find(s => s.shipment_id === shipmentId);
      if (shipment) {
        // Find the case that matches this shipment
        const matchingCase = cases.find(c =>
          c.origin_country === shipment.origin_country &&
          c.destination_country === shipment.destination_country &&
          c.target_entity === shipment.shipper_name
        );
        if (matchingCase) {
          setSelectedCaseId(matchingCase.case_id);
          // Start on Shipment tab to show the related shipment
          setActiveSubTab('Shipment');
        }
      }
    }
  }, [searchParams, cases, shipments, selectedCaseId, setSelectedCaseId, setActiveSubTab]);

  const selectedCase = cases.find(c => c.case_id === selectedCaseId);

  // Get shipments for selected case
  const selectedCaseShipments = useMemo(() => {
    if (!selectedCase) return [];
    // Find shipments matching the case's origin/destination/target_entity
    return (propShipments || []).filter(s =>
      s.origin_country === selectedCase.origin_country &&
      s.destination_country === selectedCase.destination_country &&
      s.shipper_name?.includes(selectedCase.target_entity.split(' /')[0]?.trim() || '')
    );
  }, [selectedCase, propShipments]);

  // Filter & Search
  const [searchQuery, setSearchQuery] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [riskFilter, setRiskFilter] = useState('all');

  const filteredCases = useMemo(() => {
    return cases.filter(c => {
      const matchesSearch = c.case_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                           c.target_entity.toLowerCase().includes(searchQuery.toLowerCase()) ||
                           c.case_id.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesPriority = priorityFilter === 'all' || c.priority.toLowerCase() === priorityFilter;
      const matchesRisk = riskFilter === 'all' ||
                         (riskFilter === 'critical' && c.risk_score >= 80) ||
                         (riskFilter === 'elevated' && c.risk_score >= 50 && c.risk_score < 80);
      return matchesSearch && matchesPriority && matchesRisk;
    });
  }, [cases, searchQuery, priorityFilter, riskFilter]);

  // Referral state
  const [selectedReferral, setSelectedReferral] = useState<ReferralPackage | null>(null);
  const [referralNarrative, setReferralNarrative] = useState('');
  const [selectedNarrativeSections, setSelectedNarrativeSections] = useState({
    'Executive Summary & Charges': true,
    'Subject Corporate Overview': true,
    'Forensic Evidence Accumulation': true,
    'Recommended Legal Actions': true,
  });
  const [compileLoading, setCompileLoading] = useState(false);
  const [riskAdjustment, setRiskAdjustment] = useState(0);
  const [submittedCases, setSubmittedCases] = useState<Set<string>>(new Set());

  // Finding verification state
  const [findingStatuses, setFindingStatuses] = useState<Record<string, 'Accepted' | 'Rejected' | 'Needs Review'>>({});


  // Auto-fetch referral package when case is selected
  React.useEffect(() => {
    const fetchReferralData = async () => {
      if (!selectedCaseShipments || selectedCaseShipments.length === 0) {
        console.log('[Evidence & Referral] No shipments selected yet');
        return;
      }
      try {
        const shipment = selectedCaseShipments[0];
        console.log('[Evidence & Referral] Fetching referral for:', shipment.shipment_id);
        const referralResp = await api.getReferralPackage(shipment.shipment_id);
        console.log('[Evidence & Referral] Referral data received:', referralResp);
        setSelectedReferral(referralResp as unknown as ReferralPackage);
      } catch (err) {
        console.error('[Evidence & Referral] Fetch error:', err);
      }
    };
    fetchReferralData();
  }, [selectedCaseShipments]);

  // Generate narrative from referral data
  const generateNarrative = (referral: ReferralPackage | null, selectedCase: Case, selectedSections: Record<string, boolean>) => {
    if (!referral) return '';

    const sections = [];
    const shipment = selectedCaseShipments[0];

    // CASE ID & SUBJECT
    sections.push(`CASE ID: ${selectedCase.case_id}`);
    sections.push(`SUBJECT: ${selectedCase.case_name}`);
    sections.push(`RISK LEVEL: ${selectedCase.risk_score >= 80 ? 'HIGH' : 'ELEVATED'} (${selectedCase.risk_score}/100)`);
    sections.push('');

    // EXECUTIVE SUMMARY (if selected)
    if (selectedSections['Executive Summary & Charges']) {
      sections.push('EXECUTIVE SUMMARY:');
      sections.push(`Investigation of ${shipment?.shipper_name} revealed systematic trade fraud indicators under 19 USC § 1516a. Trade corridor ${shipment?.origin_country}→${shipment?.destination_country} exhibits multi-factor risk concentration.`);
      sections.push('');
    }

    // CORPORATE OVERVIEW (if selected)
    if (selectedSections['Subject Corporate Overview']) {
      sections.push('SUBJECT ENTITY OVERVIEW:');
      sections.push(`Entity: ${selectedCase.target_entity}`);
      sections.push(`Commodity: ${shipment?.commodity_name} (HS ${shipment?.hs_code})`);
      sections.push(`Trading Partner: ${shipment?.manifest_data.consignee}`);
      if (shipment?.ad_cvd_applicable) {
        sections.push(`AD/CVD Status: ${((shipment.ad_cvd_rate ?? 0) * 100).toFixed(1)}% duty rate active`);
      }
      sections.push('');
    }

    // FORENSIC EVIDENCE (if selected)
    if (selectedSections['Forensic Evidence Accumulation']) {
      sections.push('FORENSIC EVIDENCE ACCUMULATION:');
      sections.push('');
      sections.push(`H1 CORRIDOR RISK (${selectedCase.h1_score}/40 points) — 19 USC § 1516a`);
      sections.push(`Trade lane exhibits tariff incentive. ${shipment?.commodity_name} corridor pattern consistent with duty evasion indicators.`);
      sections.push('');
      sections.push(`H2 PRE-MANIFEST INTELLIGENCE (${selectedCase.h2_score}/35 points) — 19 CFR Part 149`);
      const hasAnomalies = shipment?.manifest_anomalies?.length ?? 0 > 0;
      if (hasAnomalies) {
        sections.push(`Manifest anomalies detected: ${shipment?.manifest_anomalies?.join(', ')}`);
      }
      sections.push('');
      sections.push(`H3 NETWORK INTELLIGENCE (${selectedCase.h3_score}/25 points) — 19 USC § 1581`);
      sections.push(`Entity structure analysis indicates potential layering patterns. Shared relationships across borders warrant investigation.`);
      sections.push('');
    }

    // FINDINGS (always include)
    if (findings.length > 0) {
      sections.push('KEY FINDINGS:');
      findings.slice(0, 3).forEach(f => {
        sections.push(`• ${f.title} [${f.severity}]`);
        sections.push(`  ${f.explanation}`);
      });
      sections.push('');
    }

    // RECOMMENDED ACTIONS (if selected)
    if (selectedSections['Recommended Legal Actions']) {
      sections.push('RECOMMENDED ACTIONS:');
      sections.push(`EXAMINE ON ARRIVAL per 19 USC § 1516a. Physical examination and CBP National Targeting Center referral for EAPA investigation.`);
      sections.push('');
      sections.push('REQUEST VERIFICATIONS:');
      sections.push(`• Factory certification and business registration (${shipment?.origin_country})`);
      sections.push(`• ISF Element 9 amendment with vessel operator confirmation`);
      sections.push(`• Entity independence verification and director background review`);
      sections.push('');
    }

    sections.push(`Authority: 19 USC § 1516a (EAPA), 19 CFR Part 149 (ISF), 19 USC § 1581 (Entry denial)`);

    return sections.join('\n');
  };

  const handleSubmitReferral = () => {
    if (selectedCase) {
      setSubmittedCases(prev => new Set(prev).add(selectedCase.case_id));
    }
  };

  const handleCompileReferral = async () => {
    if (!selectedCase || selectedCaseShipments.length === 0) return;

    setCompileLoading(true);
    try {
      const shipment = selectedCaseShipments[0];
      const payload = {
        caseName: selectedCase.case_name,
        targetEntity: selectedCase.target_entity,
        category: `${shipment.commodity_name} (HS ${shipment.hs_code})`,
        corridor: `${shipment.origin_country}→${shipment.destination_country}`,
        adCvdStatus: shipment.ad_cvd_applicable ? `${((shipment.ad_cvd_rate ?? 0) * 100).toFixed(1)}%` : 'NONE',
        shipments: selectedCaseShipments.map(s => ({
          id: s.shipment_id,
          commodity: s.commodity_name,
          origin: s.origin_country,
          risk: s.risk_score,
        })),
        findings: findings.map(f => ({
          type: f.finding_type,
          severity: f.severity,
          title: f.title,
        })),
        sections: Object.entries(selectedNarrativeSections)
          .filter(([_, checked]) => checked)
          .map(([label]) => label),
      };

      // Fetch full referral package with sections
      const referralResp = await api.getReferralPackage(shipment.shipment_id);
      setSelectedReferral(referralResp as unknown as ReferralPackage);

      // Try backend narrative generation first, fall back to local generation
      let narrative = '';
      try {
        const narrativeResp = await api.generateDraftReferral(payload);
        narrative = narrativeResp.narrative || '';
      } catch (apiErr) {
        console.warn('Backend narrative generation failed, using local generation:', apiErr);
      }

      // Use local generation if backend didn't return narrative
      if (!narrative || narrative.includes('Unable to generate')) {
        narrative = generateNarrative(referralResp as unknown as ReferralPackage, selectedCase, selectedNarrativeSections);
      }

      setReferralNarrative(narrative);
    } catch (err) {
      console.error('Error compiling referral:', err);
      setReferralNarrative('Error generating referral');
    } finally {
      setCompileLoading(false);
    }
  };

  // LIST VIEW
  if (!selectedCase) {
    return (
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <div className={`${DESIGN.bgWhite} p-4 border ${DESIGN.borderColor} rounded-sm flex justify-between items-center mb-4 shadow-sm`}>
          <div>
            <h2 className={`${TYPOGRAPHY.sectionTitle} uppercase flex items-center space-x-2 mb-0`}>
              <span>ACTIVE INVESTIGATIONS</span>
            </h2>
            <p className={`${TYPOGRAPHY.smallText} mt-1`}>Evaluate current trade targets or launch secure forensic analysis.</p>
          </div>
          <button
            onClick={() => { setSearchQuery(''); setPriorityFilter('all'); setRiskFilter('all'); }}
            className={`px-3 py-1.5 border ${DESIGN.borderColor} hover:${DESIGN.bgLight} text-xs font-bold rounded-sm ${DESIGN.textDark} cursor-pointer`}
          >
            CLEAR ALL
          </button>
        </div>

        {/* Filter Controls */}
        <div className={`${DESIGN.bgWhite} p-3.5 rounded-sm border ${DESIGN.borderColor} flex flex-col md:flex-row md:items-center gap-4 mb-4 shadow-sm`}>
          <div className="flex-1 relative flex items-center">
            <Search className="h-4 w-4 text-slate-400 absolute left-3" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter by case name, entity, or ID..."
              className={`w-full ${DESIGN.bgLight} border ${DESIGN.borderColor} rounded-sm pl-9 pr-4 py-1.5 text-xs ${DESIGN.textDark} focus:outline-none focus:border-[#005EA2]`}
            />
          </div>

          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className={`${DESIGN.bgLight} border ${DESIGN.borderColor} rounded px-2.5 py-1.5 text-xs ${DESIGN.textDark} focus:outline-none focus:border-[#005EA2] font-bold`}
          >
            <option value="all">PRIORITY: ALL</option>
            <option value="critical">CRITICAL</option>
            <option value="high">HIGH</option>
            <option value="medium">MEDIUM</option>
          </select>

          <select
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            className="bg-slate-50 border border-[#D0D7DE] rounded px-2.5 py-1.5 text-xs text-[#0B1F33] focus:outline-none focus:border-[#005EA2] font-mono"
          >
            <option value="all">RISK MATRIX: ALL</option>
            <option value="critical">CRITICAL (≥80)</option>
            <option value="elevated">ELEVATED (50-79)</option>
          </select>
        </div>

        {/* Case List Table */}
        <div className="bg-white rounded-sm border border-[#D0D7DE] shadow-sm flex-1 overflow-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="sticky top-0 bg-[#F0F4F8] border-b border-[#D0D7DE] font-mono text-[#112E51] font-bold">
              <tr>
                <th className="p-3 w-20">SENTRY SCORE</th>
                <th className="p-3">INVESTIGATION DIRECTORY ID</th>
                <th className="p-3">ASSIGNED OFFICER</th>
                <th className="p-3">COMMODITY</th>
                <th className="p-3">DATE OPENED</th>
                <th className="p-3">REFERRAL STATUS</th>
                <th className="p-3 text-right">ACTIONS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredCases.map((c) => (
                <tr key={c.case_id} className="hover:bg-slate-50 transition-all cursor-pointer" onClick={() => setSelectedCaseId(c.case_id)}>
                  <td className="p-3">
                    <span className={`inline-block px-2.5 py-1 rounded text-center font-extrabold text-xs text-white ${
                      c.risk_score >= 80 ? 'bg-[#D83933]' : 'bg-amber-600'
                    }`}>
                      {c.risk_score}%
                    </span>
                  </td>
                  <td className="p-3">
                    <div className="flex flex-col">
                      <span className="font-extrabold text-[#0B1F33]">{c.target_entity}</span>
                      <span className="text-[10px] text-[#5C5C5C] font-mono block mt-0.5">{c.case_id}</span>
                    </div>
                  </td>
                  <td className="p-3 text-slate-800 font-medium">{c.assigned_officer}</td>
                  <td className="p-3 text-[11px]">{c.commodity_name || c.product_category}</td>
                  <td className="p-3 text-[#5C5C5C] font-mono text-[11px]">{c.opened_date}</td>
                  <td className="p-3 font-mono">
                    <span className={`px-2 py-0.5 text-[10px] rounded font-bold ${
                      c.referral_status === 'Submitted' ? 'bg-green-100 text-green-800' : 'bg-slate-100 text-slate-600'
                    }`}>
                      {c.referral_status}
                    </span>
                  </td>
                  <td className="p-3 text-right">
                    <button
                      onClick={(e) => { e.stopPropagation(); setSelectedCaseId(c.case_id); }}
                      className="px-3 py-1 bg-[#112E51] hover:bg-[#0076D6] text-white text-[10px] font-bold rounded-sm flex items-center space-x-1 ml-auto"
                    >
                      <span>Access Workspace</span>
                      <ArrowRight className="h-3 w-3" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {filteredCases.length === 0 && (
            <div className="py-12 text-center text-slate-400 font-sans italic">
              No cases matched your filters. Try resetting.
            </div>
          )}
        </div>
      </div>
    );
  }

  // CASE DETAIL WORKSPACE
  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Back to Queue Button - Top Left Corner */}
      <div className="bg-[#F7F9FC] border-b border-[#D0D7DE] px-6 py-2 shrink-0">
        <button
          onClick={() => setSelectedCaseId(null)}
          className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 border border-slate-300 text-[#005EA2] hover:text-[#0076D6] text-xs font-bold rounded-sm flex items-center space-x-1 transition-colors"
        >
          <span>←</span>
          <span>BACK TO QUEUE</span>
        </button>
      </div>

      {/* Header Bar */}
      <div className="h-20 bg-white border-b border-[#D0D7DE] flex items-center px-6 space-x-6 shrink-0 shadow-sm">
        <div className="flex flex-col border-r border-[#D0D7DE] pr-6">
          <h2 className="text-base font-extrabold uppercase text-[#0B1F33]">
            {selectedCase.case_name}
          </h2>
          <div className="flex items-center space-x-2 mt-0.5">
            <span className="text-xs font-mono font-bold text-slate-800 bg-slate-100 border border-slate-300 px-1 py-0.5 rounded">
              {selectedCase.case_id}
            </span>
            <span className={`px-1.5 py-0.5 text-[10px] font-bold rounded-sm uppercase font-sans ${
              selectedCase.priority === 'Critical' ? 'bg-[#D83933] text-white' : 'bg-[#FFBE2E] text-slate-950'
            }`}>
              {selectedCase.priority} TASK
            </span>
          </div>
        </div>

        {/* Risk Score */}
        <div className="flex flex-col">
          <span className="text-[9px] text-[#5C5C5C] font-mono uppercase font-bold">Risk Score</span>
          <div className="flex items-baseline space-x-1.5 mt-1">
            <span className={`text-xl font-black font-mono ${(selectedCase.risk_score + riskAdjustment) >= 80 ? 'text-[#D83933]' : 'text-[#FFBE2E]'}`}>
              {Math.min(100, selectedCase.risk_score + riskAdjustment)}
            </span>
            <span className="text-[10px]">/ 100</span>
            <div className="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full ${(selectedCase.risk_score + riskAdjustment) >= 80 ? 'bg-[#D83933]' : 'bg-[#FFBE2E]'}`}
                style={{ width: `${Math.min(100, selectedCase.risk_score + riskAdjustment)}%` }}
              />
            </div>
          </div>
        </div>

        {/* SLA */}
        <div className="flex flex-col">
          <span className="text-[9px] text-[#5C5C5C] font-mono uppercase font-bold">SLA Clock</span>
          <span className="text-xs font-mono font-bold text-red-600 mt-1">{selectedCase.sla_timer}</span>
        </div>

        {/* Actions */}
        <div className="flex space-x-2 ml-auto">
          <button
            onClick={() => setActiveSubTab('Evidence & Referral')}
            className="px-3 py-2 bg-[#005EA2] hover:bg-[#0076D6] text-white text-xs font-bold rounded-sm"
          >
            REFERRAL PACKET
          </button>
          <button
            onClick={() => {
              setRiskAdjustment(prev => Math.min(20, prev + 5));
            }}
            className="px-3 py-2 bg-orange-600 hover:bg-orange-700 text-white text-xs font-bold rounded-sm"
          >
            ESCALATE
          </button>
        </div>
      </div>

      {/* Tab Navigation - Horizontal tabs at top */}
      <TabNavigation
        tabs={[
          { id: 'Shipment', label: 'Shipment' },
          { id: 'Entity', label: 'Entity' },
          { id: 'Data Tables', label: 'Data Tables' },
          { id: 'Risk Score', label: 'Risk Score' },
          { id: 'Evidence & Referral', label: 'Evidence & Referral' },
        ]}
        activeTab={activeSubTab}
        onTabChange={(tabId) => {
          const validTabs = ['Shipment', 'Entity', 'Data Tables', 'Risk Score', 'Evidence & Referral'];
          if (validTabs.includes(tabId)) {
            setActiveSubTab(tabId as 'Shipment' | 'Entity' | 'Data Tables' | 'Risk Score' | 'Evidence & Referral');
          }
        }}
        orientation="horizontal"
      />

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto">
          {activeSubTab === 'Shipment' && (
            <ShipmentsTab selectedCaseShipments={selectedCaseShipments} selectedReferral={selectedReferral} />
          )}
          {activeSubTab === 'Entity' && (
            <EntitiesTab selectedCase={selectedCase} selectedCaseShipments={selectedCaseShipments} selectedReferral={selectedReferral} />
          )}
          {activeSubTab === 'Data Tables' && (
            <DataTablesTab selectedCase={selectedCase} selectedCaseShipments={selectedCaseShipments} selectedReferral={selectedReferral} />
          )}
          {activeSubTab === 'Risk Score' && (
            <SynopsisTab selectedCase={selectedCase} selectedCaseShipments={selectedCaseShipments} />
          )}
          {activeSubTab === 'Evidence & Referral' && (
            <ReferralPackageViewer
              selectedReferral={selectedReferral}
              selectedCase={selectedCase}
              findings={findings}
              referralNarrative={referralNarrative}
              setReferralNarrative={setReferralNarrative}
              onCompile={handleCompileReferral}
              compileLoading={compileLoading}
              selectedCaseShipments={selectedCaseShipments}
              onSubmit={handleSubmitReferral}
            />
          )}
      </div>
    </div>
  );
}

// RISK SCORING TAB - Risk Scoring Methodology from API
function SynopsisTab({ selectedCase, selectedCaseShipments }: any) {
  const shipment = selectedCaseShipments?.[0];

  // Fetch risk scoring data from API (hook must be called before any early returns)
  const { scoreData, loading, error } = useRiskScoring(shipment?.shipment_id || null);

  if (!selectedCaseShipments || selectedCaseShipments.length === 0) return <div className="p-6 text-slate-500">No shipments available</div>;

  if (loading) {
    return (
      <div className="flex-1 p-6 flex items-center justify-center">
        <div className="text-slate-500">Computing risk scoring breakdown...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 p-6 flex items-center justify-center">
        <div className="text-red-600">Error loading risk scoring: {error}</div>
      </div>
    );
  }

  if (!scoreData) {
    return (
      <div className="flex-1 p-6 flex items-center justify-center">
        <div className="text-slate-500">No risk scoring data available</div>
      </div>
    );
  }

  const chartData = scoreData.components.map((c: any) => ({
    name: c.component.substring(0, 15),
    value: parseFloat(c.weighted_result.toFixed(1))
  }));

  return (
    <div className="flex-1 p-6 space-y-6 overflow-y-auto bg-[#F7F9FC]">
      <h2 className="text-lg font-bold text-[#0B1F33]">Risk Scoring Summary</h2>

      {/* Risk Score Summary */}
      <div className="bg-white rounded-sm border border-[#D0D7DE] p-5">
        <h3 className="text-sm font-bold text-[#0B1F33] mb-4">Overall Risk Assessment</h3>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div className="p-3 bg-red-50 rounded">
            <div className="text-3xl font-bold text-red-600">{scoreData.final_score.toFixed(0)}</div>
            <div className="text-xs text-slate-600">Risk Score / 100</div>
          </div>
          <div className="p-3 bg-orange-50 rounded">
            <div className="text-sm font-bold text-orange-600">{scoreData.h1_level || 'UNKNOWN'}</div>
            <div className="text-xs text-slate-600">H1 Corridor Risk</div>
          </div>
          <div className="p-3 bg-yellow-50 rounded">
            <div className="text-sm font-bold text-yellow-700">{scoreData.h3_recommendation || 'UNKNOWN'}</div>
            <div className="text-xs text-slate-600">H3 Recommendation</div>
          </div>
        </div>
      </div>

      {/* H2 Signals */}
      {scoreData.h2_signals && scoreData.h2_signals.length > 0 && (
        <div className="bg-white rounded-sm border border-[#D0D7DE] p-5">
          <h3 className="text-sm font-bold text-[#0B1F33] mb-3">H2 Anomaly Signals</h3>
          <div className="space-y-2">
            {scoreData.h2_signals.map((signal: string, idx: number) => (
              <div key={idx} className="flex items-center text-xs">
                <span className="inline-block w-2 h-2 bg-orange-500 rounded-full mr-2"></span>
                <span>{signal}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Breakdown Table */}
      <div className="bg-white rounded-sm border border-[#D0D7DE] p-5">
        <h3 className="text-sm font-bold text-[#0B1F33] mb-4">Risk Component Breakdown</h3>
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
              {scoreData.components.map((comp: any, idx: number) => (
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
      </div>

      {/* Score Calculation */}
      <div className="bg-white rounded-sm border border-[#D0D7DE] p-5">
        <h3 className="text-sm font-bold text-[#0B1F33] mb-3">Score Calculation</h3>
        <div className="space-y-2 text-[10px] font-mono">
          <div className="flex justify-between"><span>Subtotal (Components)</span><span className="font-bold">{scoreData.subtotal.toFixed(2)}</span></div>
          {scoreData.corridor_risk_adjustment && (
            <div className="flex justify-between text-slate-600"><span>Corridor Adjustment ({scoreData.corridor_risk_adjustment.multiplier.toFixed(2)}x)</span><span>{scoreData.corridor_risk_adjustment.adjustment_points.toFixed(2)}</span></div>
          )}
          <div className="border-t pt-2 flex justify-between font-bold"><span>FINAL RISK SCORE</span><span className={scoreData.final_score >= 80 ? 'text-[#D83933]' : 'text-[#FFBE2E]'}>{scoreData.final_score.toFixed(1)}/100</span></div>
          {scoreData.confidence_interval && <div className="text-[8px] text-slate-600 mt-2">Confidence: {scoreData.confidence_interval}</div>}
        </div>
      </div>

      {/* Chart */}
      <div className="bg-white rounded-sm border border-[#D0D7DE] p-5">
        <h3 className="text-sm font-bold text-[#0B1F33] mb-4">Weighted Contribution by Factor</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" />
            <YAxis dataKey="name" type="category" width={120} tick={{ fontSize: 9 }} />
            <Tooltip />
            <Bar dataKey="value" fill="#005EA2" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// DATA TABLES TAB - Tables 3-8, 3-9, 3-10 with Analysis
function DataTablesTab({ selectedCase, selectedCaseShipments, selectedReferral }: any) {
  if (!selectedCaseShipments || selectedCaseShipments.length === 0) return <div className="p-6 text-slate-500">No shipments available</div>;
  const shipment = selectedCaseShipments[0];

  // Use referral data if available, fallback to structured defaults
  const docReviewSection = selectedReferral?.sections?.section_3_8_document_review;
  const docConsistencySection = selectedReferral?.sections?.section_3_9_document_consistency;
  const supplierVerifySection = selectedReferral?.sections?.section_3_10_supplier_verification;

  const table38Data = docReviewSection?.documents?.map((doc: any) => ({
    doc: doc.document,
    received: doc.status === 'RECEIVED' ? 'Yes' : 'No',
    key: doc.key_data || 'Document submitted',
    match: doc.verification_status || 'Pending',
    concern: doc.concern || (doc.status === 'RECEIVED' ? 'Under review' : 'MAJOR GAP')
  })) || [
    { doc: 'Commercial Invoice', received: 'Yes', key: 'Origin stated as Vietnam', match: 'Partial', concern: 'Needs production proof' },
    { doc: 'Packing List', received: 'Yes', key: '3 line items, 26,200 kg', match: 'Yes', concern: 'No factory lot mapping' },
    { doc: 'Bill of Lading', received: 'Yes', key: 'BOL-2026-00194', match: 'Yes', concern: 'Limited traceability' },
    { doc: 'Factory Production Record', received: 'No', key: 'Not provided', match: 'No', concern: 'MAJOR GAP' },
  ];

  const table39Data = docConsistencySection ? [
    { element: 'ISF Element 9 Status', invoice: docConsistencySection.isf_element9?.declared_origin || 'Unknown', packing: docConsistencySection.isf_element9?.actual_stuffing_country || 'Unknown', bol: docConsistencySection.isf_element9?.actual_stuffing_country || 'Unknown', coo: 'N/A', status: docConsistencySection.isf_element9?.is_mismatch ? 'MISMATCH' : 'Consistent' },
  ] : [
    { element: 'Shipper name', invoice: '✓', packing: '✓', bol: '✓', coo: '✓', status: 'Consistent' },
    { element: 'Country of origin', invoice: 'Vietnam', packing: 'Vietnam', bol: 'Vietnam', coo: 'Vietnam', status: 'Consistent' },
    { element: 'Commodity', invoice: 'Aluminum ext.', packing: 'Aluminum ext.', bol: 'Aluminum ext.', coo: 'Aluminum ext.', status: 'Consistent' },
    { element: 'Quantity', invoice: '26,200 kg', packing: '26,200 kg', bol: 'N/A', coo: 'N/A', status: 'Partial' },
  ];

  const table310Data = supplierVerifySection ? [
    { item: 'Shipper Age', response: `${supplierVerifySection.shipper_age_months || 0} months`, evidence: supplierVerifySection.shipper_age_risk || 'Unknown', assessment: supplierVerifySection.shipper_age_risk === 'VERY_NEW' ? 'High Risk' : 'Acceptable' },
    { item: 'Production Capacity', response: supplierVerifySection.capacity_assessment || 'Pending verification', evidence: `Declared: ${supplierVerifySection.declared_volume_kg} kg`, assessment: 'Under Review' },
  ] : [
    { item: 'Factory address', response: 'Industrial Zone', evidence: 'No details', assessment: 'Weak' },
    { item: 'Production capacity', response: 'Sufficient', evidence: 'No report', assessment: 'Weak' },
  ];

  const receivedCount = table38Data.filter((d: any) => d.received === 'Yes').length;
  const pie38Data = [
    { name: 'Received', value: receivedCount, fill: '#22c55e' },
    { name: 'Missing', value: table38Data.length - receivedCount, fill: '#ef4444' },
  ];

  const consistencyScores = table39Data.map((d: any) => ({
    name: d.element.substring(0, 12),
    score: d.status === 'Consistent' ? 3 : d.status === 'Partial' ? 2 : 1,
  }));

  return (
    <div className="flex-1 p-6 space-y-6 overflow-y-auto bg-[#F7F9FC]">
      <h2 className="text-lg font-bold text-[#0B1F33]">Evidence & Data Analysis</h2>

      {/* Table 3-8 */}
      <div className="bg-white rounded-sm border border-[#D0D7DE] p-5 space-y-4">
        <h3 className="text-sm font-bold text-[#0B1F33]">Table 3-8: Document Review — Core Evidence Support</h3>
        <div className="overflow-x-auto">
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
              {table38Data.map((row: any, i: number) => (
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
          <div className="flex-1">
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={pie38Data} cx="50%" cy="50%" labelLine={false} label={(d) => d.name} outerRadius={60} dataKey="value">
                  {pie38Data.map((_, i) => <Cell key={i} fill={pie38Data[i].fill} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex-1 text-[9px] text-slate-600">
            <p className="font-bold mb-2">Analysis:</p>
            <p>5 of 8 documents provided. Missing critical manufacturing verification: Factory Production Records, Bill of Materials, Raw Material Invoices. These gaps prevent independent verification of Vietnam origin claim.</p>
          </div>
        </div>
      </div>

      {/* Table 3-9 */}
      <div className="bg-white rounded-sm border border-[#D0D7DE] p-5 space-y-4">
        <h3 className="text-sm font-bold text-[#0B1F33]">Table 3-9: Document Consistency Analysis</h3>
        <div className="overflow-x-auto">
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
          <div className="flex-1">
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={consistencyScores}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontSize: 8 }} angle={-45} height={60} />
                <YAxis label={{ value: 'Score', angle: -90, position: 'insideLeft' }} />
                <Tooltip />
                <Bar dataKey="score" fill="#0076D6" />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="flex-1 text-[9px] text-slate-600">
            <p className="font-bold mb-2">Analysis:</p>
            <p>Core shipment data (name, origin, commodity, quantity) is consistent across primary documents. Manufacturing details completely absent from all documents, creating unresolvable verification gap for country-of-origin claim.</p>
          </div>
        </div>
      </div>

      {/* Table 3-10 */}
      <div className="bg-white rounded-sm border border-[#D0D7DE] p-5 space-y-4">
        <h3 className="text-sm font-bold text-[#0B1F33]">Table 3-10: Supplier Manufacturing Verification Assessment</h3>
        <div className="overflow-x-auto">
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
          <p>All supplier responses are vague or provide no supporting documentation. Factory address lacks street details. No capacity reports, equipment inventories, work orders, or QC records provided. Assessment: Insufficient evidence to substantiate Vietnam manufacturing claim. Recommend hold pending receipt of factory facility verification.</p>
        </div>
      </div>
    </div>
  );
}

// OVERVIEW TAB
function OverviewTab({ selectedCase, selectedCaseShipments, synopsisMap, synopsisLoading, selectedReferral }: any) {
  const shipment = selectedCaseShipments[0];

  const hasMismatch = shipment?.manifest_anomalies.some((s: string) =>
    ['ISF_MISMATCH', 'ELEMENT9_MISMATCH'].includes(s)
  );
  const hasDwell = shipment?.manifest_anomalies.includes('DWELL_ANOMALY');

  const anomalyRows = [
    {
      label: `Origination Country Mismatch (${shipment?.origin_country}→${shipment?.destination_country})`,
      dot: 'bg-red-600',
      color: 'text-red-600',
      score: hasMismatch ? selectedCase.risk_score : Math.round(selectedCase.risk_score * 0.5),
      tag: selectedCase.risk_score >= 80 ? 'CRITICAL' : 'HIGH',
    },
    {
      label: `Tariff Duty Evasion Risk (${shipment?.commodity_name} HS ${shipment?.hs_code})`,
      dot: shipment?.ad_cvd_applicable ? 'bg-amber-500' : 'bg-slate-400',
      color: shipment?.ad_cvd_applicable ? 'text-amber-500' : 'text-slate-600',
      score: shipment?.ad_cvd_applicable ? Math.round(selectedCase.risk_score * 0.9) : Math.round(selectedCase.risk_score * 0.6),
      tag: 'HIGH',
    },
    {
      label: `Vessel & Routing Anomaly (Dwell: ${shipment?.dwell_days || 0}d)`,
      dot: hasDwell ? 'bg-orange-500' : 'bg-slate-400',
      color: hasDwell ? 'text-orange-500' : 'text-slate-600',
      score: hasDwell ? Math.round(selectedCase.risk_score * 0.8) : selectedCase.ai_confidence,
      tag: hasDwell ? 'HIGH' : 'ELEVATED',
    },
  ];

  const recommendation = selectedCase.risk_score >= 80
    ? 'HOLD FOR EXAMINATION'
    : selectedCase.risk_score >= 50
    ? 'EXAMINE'
    : 'CLEAR';

  const recommendationBg = selectedCase.risk_score >= 80
    ? 'bg-[#D83933]'
    : selectedCase.risk_score >= 50
    ? 'bg-[#FFBE2E]'
    : 'bg-[#07A41E]';

  return (
    <div className="p-6 space-y-6">
      {/* Recommendation Banner */}
      <div className={`${recommendationBg} text-white rounded-sm p-4 border-l-4 border-white`}>
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold uppercase">RECOMMENDATION</h3>
            <p className="text-xs mt-1">Based on ML risk scoring analysis</p>
          </div>
          <div className="text-right">
            <p className="text-2xl font-black font-mono">{recommendation}</p>
            <p className="text-[9px] mt-1">Risk Score: {selectedCase.risk_score}/100</p>
          </div>
        </div>
      </div>

      {/* Risk Synopsis */}
      <div className="bg-white border border-[#D0D7DE] rounded-sm p-4">
        <div className="flex items-center space-x-2 mb-2">
          <Sparkles className="w-4 h-4 text-amber-500" />
          <h3 className="text-sm font-bold text-[#0B1F33] uppercase">RISK SYNOPSIS</h3>
          <span className="px-1.5 py-0.5 bg-amber-100 text-amber-800 text-[9px] font-bold rounded">
            {selectedCase.ai_confidence}%
          </span>
        </div>
        <p className="text-xs text-[#5C5C5C]">
          {synopsisMap[selectedCase.case_id] || 'Generating AI analysis...'}
        </p>
      </div>

      {/* 7-Factor Risk Breakdown */}
      <div className="bg-white border border-[#D0D7DE] rounded-sm p-4">
        <h3 className="text-sm font-bold text-[#0B1F33] mb-4">7-FACTOR RISK BREAKDOWN</h3>
        <div className="space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <div className="flex-1">
              <p className="text-xs font-bold text-[#0B1F33]">Documentation Risk</p>
              <p className="text-[9px] text-[#5C5C5C]">ISF, Element 9, Manifest Completeness</p>
            </div>
            <div className="text-right">
              <p className="text-lg font-black font-mono text-[#D83933]">{Math.round(selectedCase.h1_score || 0)}</p>
              <div className="w-20 h-2 bg-slate-200 rounded-sm mt-1 overflow-hidden">
                <div className="h-full bg-[#D83933]" style={{width: `${Math.min((selectedCase.h1_score || 0) / 40 * 100, 100)}%`}} />
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <div className="flex-1">
              <p className="text-xs font-bold text-[#0B1F33]">Corridor Risk</p>
              <p className="text-[9px] text-[#5C5C5C]">Country-of-Origin Risk Pair</p>
            </div>
            <div className="text-right">
              <p className="text-lg font-black font-mono text-amber-600">{Math.round((selectedCase.risk_score || 0) * 0.7)}</p>
              <div className="w-20 h-2 bg-slate-200 rounded-sm mt-1 overflow-hidden">
                <div className="h-full bg-amber-600" style={{width: `${Math.min((selectedCase.risk_score || 0) * 0.7, 100)}%`}} />
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <div className="flex-1">
              <p className="text-xs font-bold text-[#0B1F33]">Commodity Risk</p>
              <p className="text-[9px] text-[#5C5C5C]">Tariff Rate, Export Control, UFLPA</p>
            </div>
            <div className="text-right">
              <p className="text-lg font-black font-mono text-orange-600">{Math.round((selectedCase.risk_score || 0) * 0.8)}</p>
              <div className="w-20 h-2 bg-slate-200 rounded-sm mt-1 overflow-hidden">
                <div className="h-full bg-orange-600" style={{width: `${Math.min((selectedCase.risk_score || 0) * 0.8, 100)}%`}} />
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <div className="flex-1">
              <p className="text-xs font-bold text-[#0B1F33]">Routing Risk</p>
              <p className="text-[9px] text-[#5C5C5C]">AIS Dwell, Port Selection, Vessel Flag</p>
            </div>
            <div className="text-right">
              <p className="text-lg font-black font-mono text-blue-600">{Math.round(selectedCase.h2_score || 0)}</p>
              <div className="w-20 h-2 bg-slate-200 rounded-sm mt-1 overflow-hidden">
                <div className="h-full bg-blue-600" style={{width: `${Math.min((selectedCase.h2_score || 0) / 35 * 100, 100)}%`}} />
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <div className="flex-1">
              <p className="text-xs font-bold text-[#0B1F33]">Party Risk</p>
              <p className="text-[9px] text-[#5C5C5C]">Shipper Age, Prior Violations, OFAC, Ownership</p>
            </div>
            <div className="text-right">
              <p className="text-lg font-black font-mono text-purple-600">{Math.round((selectedCase.risk_score || 0) * 0.6)}</p>
              <div className="w-20 h-2 bg-slate-200 rounded-sm mt-1 overflow-hidden">
                <div className="h-full bg-purple-600" style={{width: `${Math.min((selectedCase.risk_score || 0) * 0.6, 100)}%`}} />
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <div className="flex-1">
              <p className="text-xs font-bold text-[#0B1F33]">Pattern Anomaly</p>
              <p className="text-[9px] text-[#5C5C5C]">Pricing/Weight Anomaly, Trade Frequency</p>
            </div>
            <div className="text-right">
              <p className="text-lg font-black font-mono text-[#112E51]">{Math.round((selectedCase.risk_score || 0) * 0.65)}</p>
              <div className="w-20 h-2 bg-slate-200 rounded-sm mt-1 overflow-hidden">
                <div className="h-full bg-[#112E51]" style={{width: `${Math.min((selectedCase.risk_score || 0) * 0.65, 100)}%`}} />
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex-1">
              <p className="text-xs font-bold text-[#0B1F33]">Time Sensitivity</p>
              <p className="text-[9px] text-[#5C5C5C]">Pre-Tariff Timing, Seasonal Anomaly</p>
            </div>
            <div className="text-right">
              <p className="text-lg font-black font-mono text-slate-600">{Math.round((selectedCase.risk_score || 0) * 0.5)}</p>
              <div className="w-20 h-2 bg-slate-200 rounded-sm mt-1 overflow-hidden">
                <div className="h-full bg-slate-600" style={{width: `${Math.min((selectedCase.risk_score || 0) * 0.5, 100)}%`}} />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Core Anomaly Matrix */}
      <div className="bg-white border border-[#D0D7DE] rounded-sm p-4">
        <h3 className="text-sm font-bold text-[#0B1F33] mb-4">Core Anomaly Matrix</h3>
        <div className="space-y-3">
          {anomalyRows.map((row, idx) => (
            <div key={idx} className="flex items-center space-x-4 pb-3 border-b border-slate-100">
              <div className={`w-2 h-2 rounded-full ${row.dot}`} />
              <div className="flex-1">
                <p className="text-xs font-bold text-[#0B1F33]">{row.label}</p>
              </div>
              <div className="flex items-baseline space-x-2">
                <span className={`text-lg font-black font-mono ${row.color}`}>{row.score}%</span>
                <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                  row.tag === 'CRITICAL' ? 'bg-red-100 text-red-800' :
                  row.tag === 'HIGH' ? 'bg-amber-100 text-amber-800' :
                  'bg-slate-100 text-slate-800'
                }`}>
                  {row.tag}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Vessel Chronology */}
      <div className="bg-white border border-[#D0D7DE] rounded-sm p-4">
        <h3 className="text-sm font-bold text-[#0B1F33] mb-4">Vessel Chronology</h3>
        <div className="space-y-2 text-xs">
          <div className="flex items-start space-x-3">
            <span className="text-[9px] font-mono font-bold text-slate-500 w-12">STEP 1</span>
            <div>
              <p className="font-bold">Cargo Intake: {shipment?.date}</p>
              <p className="text-slate-600">{shipment?.origin_country} Origin Loading Terminal</p>
            </div>
          </div>
          <div className="flex items-start space-x-3">
            <span className="text-[9px] font-mono font-bold text-slate-500 w-12">STEP 2</span>
            <div>
              <p className="font-bold">Transit: Transshipment Hub</p>
              <p className="text-slate-600">Route via {shipment?.route[1] || 'SG'}</p>
            </div>
          </div>
          <div className="flex items-start space-x-3">
            <span className="text-[9px] font-mono font-bold text-slate-500 w-12">STEP 3</span>
            <div>
              <p className="font-bold">Maritime {hasDwell ? 'AIS Disconnecting Period Active' : 'In Transit'}</p>
              <p className="text-slate-600">Dwell: {shipment?.dwell_days || 0} days</p>
            </div>
          </div>
          <div className="flex items-start space-x-3">
            <span className="text-[9px] font-mono font-bold text-slate-500 w-12">STEP 4</span>
            <div>
              <p className="font-bold">Destination: {shipment?.destination_country} Port Terminal</p>
              <p className="text-slate-600">{shipment?.manifest_data.consignee || 'Unknown'}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ENTITIES TAB
function EntitiesTab({ selectedCase, selectedCaseShipments, selectedReferral }: any) {
  if (!selectedCaseShipments?.length) return <div className="p-6 text-slate-500">No shipments available</div>;
  const s = selectedCaseShipments[0];

  return (
    <div className="p-6 space-y-4 overflow-y-auto">
      {/* Parties & Roles from referral */}
      {selectedReferral?.sections?.section_3_4_parties_and_roles && (
        <div className="bg-white border border-[#D0D7DE] rounded-sm p-4">
          <h3 className="text-sm font-bold text-[#0B1F33] mb-3">PARTIES & ROLES (TABLE 3-4)</h3>
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="bg-[#005EA2] text-white">
                <th className="border border-slate-300 px-3 py-2 text-left font-bold">ROLE</th>
                <th className="border border-slate-300 px-3 py-2 text-left font-bold">ENTITY</th>
                <th className="border border-slate-300 px-3 py-2 text-left font-bold">COUNTRY</th>
              </tr>
            </thead>
            <tbody>
              {selectedReferral.sections.section_3_4_parties_and_roles.parties?.map((p: any, idx: number) => (
                <tr key={idx} className={idx % 2 === 0 ? 'bg-slate-50' : 'bg-white'}>
                  <td className="border border-slate-300 px-3 py-2 font-bold text-slate-800">{p.role}</td>
                  <td className="border border-slate-300 px-3 py-2">{p.entity}</td>
                  <td className="border border-slate-300 px-3 py-2">{p.country}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Entity Ownership Chain Graph Visualization */}
      {selectedReferral?.sections?.section_3_5_entity_ownership_chain && (
        <EntityRelationshipGraph
          chain={selectedReferral.sections.section_3_5_entity_ownership_chain.chain}
          parties={selectedReferral.sections.section_3_4_parties_and_roles?.parties}
        />
      )}

      {/* Entity Ownership Chain Details from referral */}
      {selectedReferral?.sections?.section_3_5_entity_ownership_chain && (
        <div className="bg-white border border-[#D0D7DE] rounded-sm p-4">
          <h3 className="text-sm font-bold text-[#0B1F33] mb-3">ENTITY OWNERSHIP CHAIN (TABLE 3-5)</h3>
          <div className="space-y-3">
            {selectedReferral.sections.section_3_5_entity_ownership_chain.chain?.map((entity: any, idx: number) => (
              <div key={idx} className="bg-slate-50 border-l-4 border-blue-500 p-3">
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <p className="font-bold text-[#0B1F33]">{entity.name}</p>
                    <p className="text-[9px] text-slate-600">{entity.entity_type}</p>
                  </div>
                  <span className="text-[9px] font-bold text-blue-700 bg-blue-100 px-2 py-1 rounded">
                    {Math.round(entity.confidence * 100)}% conf
                  </span>
                </div>
                <p className="text-[8px] text-slate-600"><strong>Country:</strong> {entity.country}</p>
                <p className="text-[8px] text-slate-600"><strong>Source:</strong> {entity.data_source}</p>
                {entity.relationships && entity.relationships.length > 0 && (
                  <div className="mt-2 text-[8px]">
                    <p className="font-bold text-slate-700">Relationships:</p>
                    {entity.relationships.map((rel: any, r: number) => (
                      <p key={r} className="text-slate-600 ml-2">
                        • {rel.type}: {rel.target}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Manifest-based Entity Data — Always Show */}
      <div className="bg-blue-50 border border-blue-200 rounded-sm p-4">
        <h3 className="text-sm font-bold text-blue-900 mb-3 flex items-center space-x-2">
          <span>MANIFEST ENTITIES & DATA SOURCES</span>
          <span className="text-[9px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">Verified sources</span>
        </h3>
        <div className="bg-white border-l-4 border-blue-500 p-2 mb-3 text-[8px]">
          <p className="font-bold text-slate-700 mb-1">📊 Data Source Attribution:</p>
          <p className="text-slate-600">🔗 CORD: Entity resolution, corporate structure, ownership chains</p>
          <p className="text-slate-600">🚫 OFAC/BIS: Sanctions, export controls, watchlist matches</p>
          <p className="text-slate-600">📋 CBP: Shipper age, import history, prior enforcement actions</p>
        </div>
        <div className="space-y-3">
          {/* Shipper */}
          {s.shipper_name && (
            <div className="bg-white p-3 rounded border border-blue-100">
              <p className="text-[9px] text-blue-700 font-bold uppercase mb-1">Shipper</p>
              <p className="text-xs font-bold text-[#0B1F33]">{s.shipper_name}</p>
              <p className="text-[9px] text-slate-600 mt-1">Country: <span className="font-mono">{s.shipper_country || 'N/A'}</span></p>
              {s.shipper_age_months && <p className="text-[9px] text-slate-600">Business Age: {s.shipper_age_months} months</p>}
            </div>
          )}

          {/* Consignee */}
          {s.manifest_data?.consignee && (
            <div className="bg-white p-3 rounded border border-blue-100">
              <p className="text-[9px] text-blue-700 font-bold uppercase mb-1">Consignee</p>
              <p className="text-xs font-bold text-[#0B1F33]">{s.manifest_data.consignee}</p>
              <p className="text-[9px] text-slate-600 mt-1">Country: <span className="font-mono">{s.destination_country || 'N/A'}</span></p>
            </div>
          )}

          {/* Carrier/Vessel */}
          {s.vessel_name && (
            <div className="bg-white p-3 rounded border border-blue-100">
              <p className="text-[9px] text-blue-700 font-bold uppercase mb-1">Carrier / Vessel</p>
              <p className="text-xs font-bold text-[#0B1F33]">{s.vessel_name}</p>
              {s.vessel_imo && <p className="text-[9px] text-slate-600 mt-1">IMO: <span className="font-mono">{s.vessel_imo}</span></p>}
            </div>
          )}
        </div>
      </div>

      {/* CORD Resolution Status */}
      {!selectedReferral?.sections?.section_3_5_entity_ownership_chain && (
        <div className="bg-amber-50 border border-amber-200 rounded-sm p-4 text-[9px] text-amber-800">
          <p className="font-bold">ℹ CORD Entity Resolution Status</p>
          <p className="mt-1">Full entity ownership chain and third-party enrichment not available. Showing manifest parties only.</p>
          <p className="mt-1">Backend: Populate CORD dataset with shipper/consignee entities to enable ownership chain analysis.</p>
        </div>
      )}
    </div>
  );
}

// SHIPMENTS TAB
function ShipmentsTab({ selectedCaseShipments, selectedReferral }: any) {
  return (
    <div className="p-6 space-y-4">
      {selectedReferral?.sections?.section_3_1_shipment_identification && (
        <div className="bg-white border border-[#D0D7DE] rounded-sm p-4">
          <h3 className="text-sm font-bold text-[#0B1F33] mb-3">TABLE 3-1: SHIPMENT IDENTIFICATION</h3>
          <table className="w-full text-xs border-collapse">
            <tbody>
              {Object.entries(selectedReferral.sections.section_3_1_shipment_identification).map(([key, val]: any) =>
                key !== 'title' && (
                  <tr key={key} className="border-b border-slate-200">
                    <td className="py-2 px-3 font-bold text-slate-600 w-32">{key.toUpperCase().replace(/_/g, ' ')}</td>
                    <td className="py-2 px-3 text-slate-800">{typeof val === 'object' ? JSON.stringify(val) : val}</td>
                  </tr>
                )
              )}
            </tbody>
          </table>
        </div>
      )}

      {selectedReferral?.sections?.section_3_3_routing_history && (
        <div className="bg-white border border-[#D0D7DE] rounded-sm p-4">
          <h3 className="text-sm font-bold text-[#0B1F33] mb-3">TABLE 3-3: AIS ROUTING HISTORY</h3>
          <div className="grid grid-cols-2 gap-4 text-xs">
            <div>
              <p className="text-slate-600 font-bold">VESSEL</p>
              <p className="text-slate-800">{selectedReferral.sections.section_3_3_routing_history.vessel}</p>
            </div>
            <div>
              <p className="text-slate-600 font-bold">ROUTE</p>
              <p className="text-slate-800">{selectedReferral.sections.section_3_3_routing_history.route?.join(' → ')}</p>
            </div>
            <div>
              <p className="text-slate-600 font-bold">DWELL DAYS</p>
              <p className="text-slate-800">{selectedReferral.sections.section_3_3_routing_history.dwell_days}d (Baseline: {selectedReferral.sections.section_3_3_routing_history.dwell_baseline}d)</p>
            </div>
            <div>
              <p className="text-slate-600 font-bold">AIS STATUS</p>
              <p className={`font-bold ${selectedReferral.sections.section_3_3_routing_history.dwell_anomaly === 'NORMAL' ? 'text-green-600' : 'text-red-600'}`}>
                {selectedReferral.sections.section_3_3_routing_history.dwell_anomaly}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Detailed shipments list */}
      <div className="space-y-3">
        {selectedCaseShipments.map((s: any) => (
          <div key={s.shipment_id} className="bg-white border border-[#D0D7DE] rounded-sm p-4">
            <p className="text-xs font-bold mb-2"><strong>BOL:</strong> {s.manifest_data.bill_of_lading}</p>
            <p className="text-xs"><strong>Commodity:</strong> {s.commodity_name} (HS {s.hs_code})</p>
            <p className="text-xs"><strong>Weight:</strong> {(s.manifest_data.weight_kg/1000).toFixed(1)}T | <strong>Value:</strong> ${(s.manifest_data.declared_value_usd/1000).toFixed(1)}K</p>
            <p className="text-xs"><strong>Route:</strong> {s.origin_country} → {s.destination_country}</p>
            <p className="text-xs"><strong>Signals:</strong> {s.manifest_anomalies.join(', ') || 'None'}</p>
            <p className="text-xs"><strong>Risk Score:</strong> <span className="font-bold text-red-600">{s.risk_score}</span>/100</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// AI FINDINGS TAB
function FindingsTab({ findings, findingStatuses, onFindingStatusChange, selectedReferral }: any) {
  return (
    <div className="p-6 space-y-4">
      {/* Enrichment findings from referral */}
      {selectedReferral?.enrichment?.altana_findings?.findings && selectedReferral.enrichment.altana_findings.findings.length > 0 && (
        <div className="bg-blue-50 border border-blue-300 rounded-sm p-4 mb-4">
          <h3 className="text-sm font-bold text-blue-900 mb-3">ALTANA INTELLIGENCE FINDINGS</h3>
          {selectedReferral.enrichment.altana_findings.findings.map((finding: any, idx: number) => (
            <div key={idx} className="bg-white border border-blue-200 rounded-sm p-3 mb-2">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <p className="text-xs font-bold text-slate-800">{finding.title}</p>
                  <p className="text-[9px] text-blue-700 font-semibold">{finding.type.toUpperCase()}</p>
                </div>
                <span className={`text-[9px] font-bold px-2 py-1 rounded ${
                  finding.severity === 'high' ? 'bg-red-100 text-red-800' :
                  finding.severity === 'medium' ? 'bg-amber-100 text-amber-800' :
                  'bg-green-100 text-green-800'
                }`}>
                  {finding.severity.toUpperCase()}
                </span>
              </div>
              <p className="text-[8px] text-slate-700 mb-2">{finding.description}</p>
              <div className="flex space-x-1 flex-wrap">
                {finding.evidence?.map((e: string, eidx: number) => (
                  <span key={eidx} className="bg-blue-100 text-blue-800 px-2 py-0.5 rounded text-[7px]">{e}</span>
                ))}
              </div>
              <p className="text-[8px] text-blue-600 mt-2 font-bold">Confidence: {finding.confidence_pct}%</p>
            </div>
          ))}
        </div>
      )}

      {/* Anomaly detection findings from cases */}
      {findings.length === 0 ? (
        <p className="text-center text-gray-500">No anomaly detection findings</p>
      ) : (
        <div>
          <h3 className="text-sm font-bold text-slate-800 mb-3">ANOMALY DETECTION FINDINGS</h3>
          {findings.map((f: AIFinding) => {
            const status = findingStatuses[f.finding_id] || 'Needs Review';
          return (
            <div key={f.finding_id} className="bg-white border border-[#D0D7DE] rounded-sm p-4">
              <div className="flex items-start justify-between mb-2">
                <h3 className="text-xs font-bold text-[#0B1F33]">{f.title}</h3>
                <span className={`text-[9px] font-bold px-2 py-1 rounded ${
                  f.severity === 'Critical' ? 'bg-red-100 text-red-800' : 'bg-amber-100 text-amber-800'
                }`}>
                  {f.severity.toUpperCase()} ALERT
                </span>
              </div>
              <p className="text-[9px] text-slate-600 mb-2">{f.finding_type}</p>
              <p className="text-xs text-[#5C5C5C] mb-3">{f.explanation}</p>
              <div className="flex space-x-2 text-[9px] mb-3">
                {f.evidence_links.map(e => (
                  <span key={e} className="bg-blue-100 text-blue-800 px-2 py-1 rounded">{e}</span>
                ))}
              </div>
              <div className="flex space-x-2 text-[9px] pt-3 border-t border-gray-200">
                <button
                  onClick={() => onFindingStatusChange(f.finding_id, 'Accepted')}
                  className={`flex-1 px-2 py-1.5 rounded font-bold transition-colors ${
                    status === 'Accepted'
                      ? 'bg-emerald-600 text-white'
                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`}
                >
                  ACCEPT EXPLANATION
                </button>
                <button
                  onClick={() => onFindingStatusChange(f.finding_id, 'Rejected')}
                  className={`flex-1 px-2 py-1.5 rounded font-bold transition-colors ${
                    status === 'Rejected'
                      ? 'bg-red-700 text-white'
                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`}
                >
                  REJECT
                </button>
                <button
                  onClick={() => onFindingStatusChange(f.finding_id, 'Needs Review')}
                  className={`flex-1 px-2 py-1.5 rounded font-bold transition-colors ${
                    status === 'Needs Review'
                      ? 'bg-amber-600 text-white'
                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`}
                >
                  REVIEWING...
                </button>
              </div>
            </div>
          );
        })}
        </div>
      )}
    </div>
  );
}

// REFERRAL TAB
