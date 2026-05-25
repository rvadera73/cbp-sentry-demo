import { useState, useEffect, useRef } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import { 
  INITIAL_OFFICERS, 
  INITIAL_CASES, 
  INITIAL_ENTITIES, 
  INITIAL_SHIPMENTS, 
  INITIAL_FINDINGS, 
  INITIAL_REFERRALS, 
  INITIAL_THREAT_FEED 
} from './mockData';
import { CBPOfficer, Case, TradeEntity, Shipment, AIFinding, ReferralPackage, ThreatFeedEvent } from './types';
import { 
  Radio, 
  Activity, 
  AlertTriangle, 
  Search, 
  ArrowRight, 
  Plus, 
  Sparkles, 
  FileText, 
  Send, 
  CheckCircle, 
  XCircle, 
  HelpCircle,
  Network, 
  Calendar, 
  ShieldAlert, 
  Clock, 
  Coins, 
  Compass, 
  User, 
  Check, 
  RotateCcw,
  BookOpen,
  Sliders,
  Anchor,
  FileCheck,
  Building,
  Download,
  Percent
} from 'lucide-react';

export default function App() {
  // Global Operational State
  const [officers] = useState<CBPOfficer[]>(INITIAL_OFFICERS);
  const [currentOfficer, setCurrentOfficer] = useState<CBPOfficer>(INITIAL_OFFICERS[0]);
  const [environment, setEnvironment] = useState<'PROD' | 'UAT' | 'TRAINING'>('PROD');
  const [isSidebarExpanded, setIsSidebarExpanded] = useState<boolean>(true);
  
  // Navigation Trackers
  const [activeTab, setActiveTab] = useState<string>('dashboard'); // 'dashboard', 'investigations', 'shipments', 'entities', 'referrals'
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  
  // Investigation Stage Selection within detail view
  const [activeSubTab, setActiveSubTab] = useState<'Overview' | 'Entities' | 'Shipments' | 'AI Findings' | 'Referral'>('Overview');

  // Core Data models bound to state for instant interactivity & local persistence
  const [cases, setCases] = useState<Case[]>(INITIAL_CASES);
  const [entities, setEntities] = useState<TradeEntity[]>(INITIAL_ENTITIES);
  const [shipments, setShipments] = useState<Shipment[]>(INITIAL_SHIPMENTS);
  const [findings, setFindings] = useState<AIFinding[]>(INITIAL_FINDINGS);
  const [referrals, setReferrals] = useState<ReferralPackage[]>(INITIAL_REFERRALS);
  const [threatFeed, setThreatFeed] = useState<ThreatFeedEvent[]>(INITIAL_THREAT_FEED);

  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [priorityFilter, setPriorityFilter] = useState<string>('all');
  const [riskFilter, setRiskFilter] = useState<string>('all');

  // Persistent AI Chat Assistant State
  const [chatMessages, setChatMessages] = useState<Array<{ role: 'user' | 'assistant', text: string, isDemo?: boolean }>>([
    { role: 'assistant', text: "Authorized Sentry Platform Secure Assistant live. Ask me to cross-reference Vina Solar container logs, evaluate routing anomalies, or draft a DOJ referral narrative." }
  ]);
  const [currentMessage, setCurrentMessage] = useState<string>('');
  const [aiStatus, setAiStatus] = useState<'idle' | 'generating' | 'completed' | 'error'>('idle');
  const [chatLoading, setChatLoading] = useState<boolean>(false);

  // Dynamic Case Synopsis State
  const [synopsisLoading, setSynopsisLoading] = useState<boolean>(false);
  const [synopsisMap, setSynopsisMap] = useState<Record<string, string>>({});

  // Dynamic Draft Narrative State
  const [draftNarrative, setDraftNarrative] = useState<string>('');
  const [draftLoading, setDraftLoading] = useState<boolean>(false);
  const [selectedNarrativeSections, setSelectedNarrativeSections] = useState<string[]>([
    'Executive Summary', 'Subject Overview', 'Forensic Evidence Accumulation', 'Recommended Legal Actions'
  ]);

  // Selected Node in Entity Relationship Network Graph
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Custom User Timeline Annotations
  const [customNotes, setCustomNotes] = useState<Record<string, Array<{ text: string, officerName: string, date: string }>>>({
    "CBP-2026-9041": [
      { text: "Initiated secondary hold on feeder ship raw records matching terminal 400 cargo manifest.", officerName: "Rav J. D.", date: "2026-05-20" }
    ]
  });
  const [newNoteText, setNewNoteText] = useState<string>('');

  // New Interactive States for Multi-Page Portal System
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(INITIAL_ENTITIES[0]?.entity_id || null);
  const [selectedReferralId, setSelectedReferralId] = useState<string | null>(INITIAL_REFERRALS[0]?.referral_id || null);
  const [selectedShipmentId, setSelectedShipmentId] = useState<string | null>(INITIAL_SHIPMENTS[0]?.shipment_id || null);

  // New Watchlist Form States
  const [newWatchlistName, setNewWatchlistName] = useState<string>('');
  const [newWatchlistType, setNewWatchlistType] = useState<'Importer' | 'Intermediary' | 'Manufacturer' | 'Broker' | 'Exporter'>('Exporter');
  const [newWatchlistCountry, setNewWatchlistCountry] = useState<string>('Vietnam');
  const [newWatchlistAddress, setNewWatchlistAddress] = useState<string>('');

  // AI Configuration Parameters (Tuning)
  const [aisSignalSpoofWeight, setAisSignalSpoofWeight] = useState<number>(87);
  const [weightDeviationWeight, setWeightDeviationWeight] = useState<number>(74);
  const [circularInvoicingWeight, setCircularInvoicingWeight] = useState<number>(91);
  const [forcedLaborWeight, setForcedLaborWeight] = useState<number>(94);
  const [systemAutoHoldThreshold, setSystemAutoHoldThreshold] = useState<number>(80);

  // Toggle Hold on a Shipment
  const handleToggleShipmentHold = (shipmentId: string) => {
    setShipments(prev => prev.map(s => {
      if (s.shipment_id === shipmentId) {
        const isHeld = s.customs_flags.includes('Active CBP Hold');
        const newFlags = isHeld 
          ? s.customs_flags.filter(f => f !== 'Active CBP Hold') 
          : [...s.customs_flags, 'Active CBP Hold'];
        const newHistory = isHeld 
          ? 'Released from manual terminal hold.' 
          : 'Placed under active physical terminal examination order.';
        
        // Append a threat feed event (log) for verification
        const newThreat: ThreatFeedEvent = {
          id: 'evt_' + Math.floor(Math.random() * 900 + 100),
          severity: isHeld ? 'High' : 'Critical',
          title: isHeld ? 'Shipment Hold Released' : 'Container Placed on Terminal Hold',
          description: `Shipment ${shipmentId} (declared origin ${s.declared_origin}) was manually ${isHeld ? 'released' : 'placed under active physical hold'} by Lead Officer ${currentOfficer.name}.`,
          timestamp: 'Just now',
          confidence: 100,
          related_case_id: s.shipment_id.startsWith('SH-904') ? 'CBP-2026-9041' : undefined
        };
        setThreatFeed(prevThreat => [newThreat, ...prevThreat]);

        return {
          ...s,
          customs_flags: newFlags,
          inspection_history: newHistory
        };
      }
      return s;
    }));
  };

  // Add Watchlisted Entity manually
  const handleAddNewWatchlistEntity = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWatchlistName.trim()) return;
    const newEnt: TradeEntity = {
      entity_id: 'ENT-' + Math.floor(Math.random() * 900 + 100),
      entity_type: newWatchlistType,
      entity_name: newWatchlistName,
      country: newWatchlistCountry,
      risk_level: 'High',
      sanctions_status: 'Under Investigation',
      known_affiliations: ['Unassigned Trade Routing Channel'],
      enforcement_history: 'Manually flagged as prospective high evasion threat under screening rule index on ' + new Date().toISOString().slice(0, 10),
      ownership_indicators: 'Shell nominee structure; beneficial owner verification pending.',
      registration_status: 'Active',
      watchlist_status: 'High Alert Watchlist',
      address: newWatchlistAddress || 'Undisclosed Registered Commercial District',
      tax_id: 'TX-' + Math.floor(Math.random() * 900000 + 100000),
      phone: '+1 (800) 555-SPEC',
      shared_identifiers: []
    };
    setEntities(prev => [newEnt, ...prev]);
    setSelectedEntityId(newEnt.entity_id);
    
    // Clear and Alert
    setNewWatchlistName('');
    setNewWatchlistAddress('');
    
    // Add threat alert log too!
    const newThreat: ThreatFeedEvent = {
      id: 'evt_' + Math.floor(Math.random() * 900 + 100),
      severity: 'High',
      title: 'New Watchlist Exporter Flagged',
      description: `Trade party ${newWatchlistName} entered into high risk screening watchlist index by Analyst ${currentOfficer.name}.`,
      timestamp: 'Just now',
      confidence: 100
    };
    setThreatFeed(prevThreat => [newThreat, ...prevThreat]);
  };

  // Auto-scrolling ref for internal chat panel
  const chatRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [chatMessages]);

  // Retrieve current active case if select case is loaded
  const currentCase = cases.find(c => c.case_id === selectedCaseId);

  // Trigger Gemini Synopsis formulation on case select
  const fetchCaseSynopsis = async (caseObj: Case) => {
    if (synopsisMap[caseObj.case_id]) return; // Already fetched
    setSynopsisLoading(true);
    try {
      const relatedShipments = shipments.filter(s => s.declared_origin.includes('Vietnam') || s.shipment_id.startsWith('SH-904'));
      const relatedFindings = findings.filter(f => f.evidence_links.includes(caseObj.case_id) || caseObj.case_id.includes('9041'));
      
      const res = await fetch('/api/gemini/synopsis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          caseName: caseObj.case_name,
          entity: caseObj.target_entity,
          category: caseObj.product_category,
          shipments: relatedShipments.slice(0, 2),
          findings: relatedFindings
        })
      });
      const data = await res.json();
      if (data.synopsis) {
        setSynopsisMap(prev => ({ ...prev, [caseObj.case_id]: data.synopsis }));
      }
    } catch (err) {
      console.error("Error communicating with Sentry AI server:", err);
    } finally {
      setSynopsisLoading(false);
    }
  };

  // Trigger Gemini AI Assistant
  const handleSendChatMessage = async () => {
    if (!currentMessage.trim()) return;
    const userText = currentMessage;
    setChatMessages(prev => [...prev, { role: 'user', text: userText }]);
    setCurrentMessage('');
    setChatLoading(true);
    setAiStatus('generating');

    try {
      const res = await fetch('/api/gemini/assistant', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userText,
          history: chatMessages.map(m => ({ role: m.role, content: m.text })),
          context: currentCase ? {
            id: currentCase.case_id,
            name: currentCase.case_name,
            target: currentCase.target_entity,
            riskScore: currentCase.risk_score,
            stage: currentCase.investigation_stage,
            officer: currentOfficer.name
          } : undefined
        })
      });
      const data = await res.json();
      setChatMessages(prev => [...prev, { role: 'assistant', text: data.text, isDemo: data.isDemoMode }]);
      setAiStatus('completed');
    } catch (err) {
      console.error(err);
      setChatMessages(prev => [...prev, { role: 'assistant', text: "Error: Host API context unreachable. Ensure environment API variables are verified." }]);
      setAiStatus('error');
    } finally {
      setChatLoading(false);
    }
  };

  // Trigger AI Draft Referral Narratives
  const handleDraftReferralNarrative = async () => {
    if (!currentCase) return;
    setDraftLoading(true);
    try {
      const targetCaseShipments = shipments.filter(s => s.shipment_id.includes('SH-904') || s.shipment_id.includes('5512'));
      const res = await fetch('/api/gemini/draft-referral', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          caseName: currentCase.case_name,
          targetEntity: currentCase.target_entity,
          category: currentCase.product_category,
          shipments: targetCaseShipments,
          findings: findings,
          sections: selectedNarrativeSections
        })
      });
      const data = await res.json();
      if (data.narrative) {
        setDraftNarrative(data.narrative);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setDraftLoading(false);
    }
  };

  // Add Custom Timeline Analyst Annotation
  const handleAddCustomNote = () => {
    if (!selectedCaseId || !newNoteText.trim()) return;
    const n = {
      text: newNoteText,
      officerName: currentOfficer.name,
      date: new Date().toISOString().slice(0, 10)
    };
    setCustomNotes(prev => ({
      ...prev,
      [selectedCaseId]: [...(prev[selectedCaseId] || []), n]
    }));
    setNewNoteText('');
  };

  // Switch Case Verification States
  const handleToggleFindingStatus = (findingId: string, status: 'Accepted' | 'Rejected' | 'Needs Review') => {
    setFindings(prev => prev.map(f => f.finding_id === findingId ? { ...f, verification_status: status } : f));
    
    // Dynamically adjust Case risk score depending on Accepted findings
    if (selectedCaseId) {
      setCases(prev => prev.map(c => {
        if (c.case_id === selectedCaseId) {
          const delta = status === 'Accepted' ? 4 : (status === 'Rejected' ? -6 : 0);
          return { ...c, risk_score: Math.min(100, Math.max(0, c.risk_score + delta)) };
        }
        return c;
      }));
    }
  };

  // Trigger Manual Case Escalation
  const handleEscalateCase = (cid: string) => {
    setCases(prev => prev.map(c => {
      if (c.case_id === cid) {
        return {
          ...c,
          priority: 'Critical',
          case_status: 'Under Audit',
          risk_score: Math.min(100, c.risk_score + 5)
        };
      }
      return c;
    }));
    // Append simulated threat alert
    const newThreat: ThreatFeedEvent = {
      id: 'evt_' + Math.floor(Math.random() * 900 + 100),
      severity: 'Critical',
      title: 'Manual Case Escalation Executed',
      description: `Case ID ${cid} status shifted to Under Audit by Officer ${currentOfficer.name}. Key sub-tiers on yellow risk.`,
      timestamp: 'Just now',
      confidence: 100,
      related_case_id: cid
    };
    setThreatFeed(prev => [newThreat, ...prev]);
  };

  // Trigger Case Navigation and Synopsis Fetch
  const selectCaseForDetail = (caseObj: Case) => {
    setSelectedCaseId(caseObj.case_id);
    setActiveTab('investigations');
    setActiveSubTab('Overview');
    fetchCaseSynopsis(caseObj);
  };

  // Filter Operations on cases list
  const filteredCases = cases.filter(c => {
    const matchesSearch = c.case_name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          c.target_entity.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          c.case_id.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesPriority = priorityFilter === 'all' || c.priority.toLowerCase() === priorityFilter.toLowerCase();
    const matchesRisk = riskFilter === 'all' || 
                        (riskFilter === 'high' && c.risk_score >= 80) || 
                        (riskFilter === 'medium' && c.risk_score >= 50 && c.risk_score < 80) ||
                        (riskFilter === 'low' && c.risk_score < 50);
    return matchesSearch && matchesPriority && matchesRisk;
  });

  // Calculate high density summary card totals
  const totalCriticalCount = cases.filter(c => c.priority === 'Critical').length;
  const activeReferralsDraftCount = referrals.filter(r => r.package_status === 'Draft').length;
  const highRiskShipmentsCount = shipments.filter(s => s.ai_anomaly_score >= 80).length;

  return (
    <div className="flex flex-col h-screen w-full bg-[#F7F9FC] text-[#1B1B1B] overflow-hidden font-sans">
      
      {/* CBP Program Identity Header */}
      <Header 
        currentOfficer={currentOfficer} 
        officers={officers} 
        onOfficerChange={setCurrentOfficer}
        environment={environment}
        setEnvironment={setEnvironment}
        aiStatus={aiStatus}
      />

      <div className="flex flex-1 overflow-hidden">
        
        {/* Left Interactive Side Navigation Rail */}
        <Sidebar 
          activeTab={activeTab} 
          setActiveTab={(tab) => {
            setActiveTab(tab);
            if (tab === 'dashboard') setSelectedCaseId(null);
          }}
          isExpanded={isSidebarExpanded}
          setIsExpanded={setIsSidebarExpanded}
          activeCaseCount={cases.filter(c => c.case_status === 'Active').length}
          referralPendingCount={activeReferralsDraftCount}
        />

        {/* Dynamic Context Workspace Grid */}
        <main className="flex-1 flex flex-col overflow-hidden">
          
          {/* CRITICAL ROUTING PANEL - CASE SELECT WORKSPACE */}
          {selectedCaseId && currentCase && activeTab === 'investigations' ? (
            
            // ==========================================
            // DETAILED CASE INVESTIGATION COMPONENT PANEL
            // ==========================================
            <div className="flex-1 flex flex-col overflow-hidden">
              
              {/* TOP HEADER SUMMARY BAR */}
              <section className="h-20 bg-white border-b border-[#D0D7DE] flex items-center px-6 space-x-6 shrink-0 z-10 shadow-sm justify-between">
                <div className="flex flex-col border-r border-[#D0D7DE] pr-6 max-w-sm">
                  <div className="flex items-center space-x-2">
                    <span className="text-[10px] text-[#5C5C5C] font-mono font-bold tracking-wider">INVESTIGATION CONTEXT:</span>
                    <button 
                      onClick={() => setSelectedCaseId(null)}
                      className="text-[10px] text-[#005EA2] hover:underline font-bold"
                    >
                      ← BACK TO QUEUE
                    </button>
                  </div>
                  <h2 className="text-base font-extrabold uppercase truncate text-[#0B1F33] leading-snug font-sans">
                    {currentCase.case_name}
                  </h2>
                  <div className="flex items-center space-x-2 mt-0.5">
                    <span className="text-xs font-mono font-bold text-slate-800 bg-slate-100 border border-slate-300 px-1 py-0.2 rounded">
                      ID: {currentCase.case_id}
                    </span>
                    <span className={`px-1.5 py-0.2 text-[10px] font-bold rounded-sm uppercase font-sans tracking-wide ${
                      currentCase.priority === 'Critical' ? 'bg-[#D83933] text-white' : 'bg-[#FFBE2E] text-slate-950 font-semibold'
                    }`}>
                      {currentCase.priority} TASK
                    </span>
                  </div>
                </div>

                {/* High Density Metric Cells */}
                <div className="flex-1 flex items-center space-x-8 px-4 justify-around">
                  <div className="flex flex-col">
                    <span className="text-[9px] text-[#5C5C5C] font-mono uppercase font-bold tracking-wider">AI Anomaly Score</span>
                    <div className="flex items-baseline space-x-1.5">
                      <span className={`text-xl font-black font-mono tracking-tight ${currentCase.risk_score >= 80 ? 'text-[#D83933]' : 'text-[#FFBE2E]'}`}>
                        {currentCase.risk_score}
                      </span>
                      <span className="text-[10px] text-[#5C5C5C]">/ 100</span>
                      <div className="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden ml-2 hidden lg:block">
                        <div 
                          className={`h-full ${currentCase.risk_score >= 80 ? 'bg-[#D83933]' : 'bg-[#FFBE2E]'}`} 
                          style={{ width: `${currentCase.risk_score}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-col">
                    <span className="text-[9px] text-[#5C5C5C] font-mono uppercase font-bold tracking-wider">Target Entity Agency Tier</span>
                    <div className="text-xs font-mono font-bold text-slate-900 mt-1 flex items-center space-x-1">
                      <Compass className="h-3.5 w-3.5 text-[#005EA2]" />
                      <span className="underline decoration-[#00BDE3] decoration-2">{currentCase.target_entity}</span>
                    </div>
                  </div>

                  <div className="flex flex-col hidden sm:flex">
                    <span className="text-[9px] text-[#5C5C5C] font-mono uppercase font-bold tracking-wider">Assigned Lead Filer</span>
                    <div className="text-xs font-sans font-bold text-[#112E51] mt-1 flex items-center space-x-1">
                      <User className="h-3.5 w-3.5 text-slate-400" />
                      <span>{currentCase.assigned_officer}</span>
                    </div>
                  </div>

                  <div className="flex flex-col hidden md:flex">
                    <span className="text-[9px] text-[#5C5C5C] font-mono uppercase font-bold tracking-wider">CBP SLA Resolution Clock</span>
                    <div className="flex items-center space-x-1 mt-0.5">
                      <Clock className="h-3.5 w-3.5 text-red-600" />
                      <span className="text-xs font-mono font-bold text-red-600 uppercase">{currentCase.sla_timer}</span>
                    </div>
                  </div>
                </div>

                {/* Main Action Bar */}
                <div className="flex space-x-2">
                  <button 
                    onClick={() => {
                      setActiveSubTab('Referral');
                    }}
                    className="px-3 py-1.5 bg-[#005EA2] hover:bg-[#0076D6] text-white text-[11px] font-bold uppercase rounded shadow-sm border border-transparent flex items-center space-x-1 cursor-pointer"
                  >
                    <FileText className="h-3.5 w-3.5" />
                    <span>REFERRAL PACKET</span>
                  </button>
                  <button 
                    onClick={() => handleEscalateCase(currentCase.case_id)}
                    className="px-3 py-1.5 bg-white hover:bg-slate-50 border border-[#D0D7DE] text-[#0B1F33] text-[11px] font-bold uppercase rounded flex items-center space-x-1 cursor-pointer"
                  >
                    <ShieldAlert className="h-3.5 w-3.5 text-[#D83933]" />
                    <span>EMERGENCY ESCALATE</span>
                  </button>
                </div>
              </section>

              {/* CORE LAYOUT CANVAS */}
              <div className="flex-1 flex overflow-hidden">
                
                {/* Workflow stages sidebar selector */}
                <aside className="w-[180px] bg-white border-r border-[#D0D7DE] flex flex-col shrink-0">
                  <div className="p-3 flex flex-col space-y-1">
                    {(['Overview', 'Entities', 'Shipments', 'AI Findings', 'Referral'] as const).map((stage) => (
                      <button
                        key={stage}
                        onClick={() => setActiveSubTab(stage)}
                        className={`flex items-center justify-between px-2.5 py-2 text-xs font-sans rounded-sm transition-all text-left ${
                          activeSubTab === stage 
                            ? 'bg-[#F0F4F8] border-l-4 border-[#005EA2] text-[#005EA2] font-bold' 
                            : 'text-[#5C5C5C] hover:bg-slate-50 hover:text-slate-900 font-semibold'
                        }`}
                      >
                        <span>{stage === 'Referral' ? 'Evidence & Referral' : stage}</span>
                        {stage === 'Shipments' && (
                          <span className="text-[9px] bg-[#D83933] text-white px-1 py-0.2 rounded-full font-bold">
                            {shipments.filter(s => s.ai_anomaly_score >= 70).length}
                          </span>
                        )}
                        {stage === 'AI Findings' && (
                          <span className="text-[9px] bg-[#00BDE3] text-slate-950 px-1 py-0.2 rounded font-mono font-bold">
                            {findings.length}
                          </span>
                        )}
                      </button>
                    ))}
                  </div>

                  {/* Audit Logs block */}
                  <div className="mt-auto p-3.5 border-t border-[#D0D7DE] bg-[#F7F9FC]">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[9px] font-bold uppercase text-[#5C5C5C] font-mono">Chain of Custody</span>
                      <span className="text-[9px] text-[#2E8540] font-bold font-mono">SECURE</span>
                    </div>
                    <p className="text-[10px] text-slate-500 font-mono leading-tight">
                      CBP Automated Sentry Audit block tracking enabled. All officer actions are live recorded.
                    </p>
                  </div>
                </aside>

                {/* STAGE SCREEN CONTAINER */}
                <div className="flex-1 p-5 flex flex-col space-y-4 overflow-y-auto bg-[#F7F9FC]">
                  
                  {/* WORKFLOW CONDITIONAL MOUNTING */}

                  {/* SUB-TAB 1: OVERVIEW */}
                  {activeSubTab === 'Overview' && (
                    <div className="space-y-4">
                      
                      {/* Generative AI Synopsis Area */}
                      <div className="bg-white border-2 border-[#D0D7DE]/60 rounded-sm p-4 hover:border-[#005EA2]/30 transition-all">
                        <div className="flex items-center justify-between mb-2 pb-2 border-b border-dashed border-slate-200">
                          <div className="flex items-center space-x-2">
                            <Sparkles className="h-4 w-4 text-[#00BDE3] animate-pulse" />
                            <h3 className="text-xs font-bold uppercase tracking-wider text-[#112E51] font-mono">
                              PRE-AUDITED RISK SYNOPSIS (GEMINI 3.5 AI)
                            </h3>
                          </div>
                          <span className="text-[9px] font-mono bg-cyan-50 text-cyan-700 px-1.5 py-0.2 rounded border border-cyan-200">
                            Confidence Level: {currentCase.ai_confidence}%
                          </span>
                        </div>

                        {synopsisLoading ? (
                          <div className="animate-pulse space-y-2 py-2">
                            <div className="h-3.5 bg-slate-200 rounded w-1/3"></div>
                            <div className="h-10 bg-slate-100 rounded"></div>
                          </div>
                        ) : (
                          <div className="text-xs leading-relaxed text-[#1B1B1B] font-sans">
                            <p className="mb-2">
                              {synopsisMap[currentCase.case_id] || currentCase.ai_synopsis}
                            </p>
                            <span className="text-[9px] text-[#5C5C5C] italic block font-mono">
                              * Compiled dynamically mapping raw bills-of-lading and UFLPA high alert watchlists on port of registries.
                            </span>
                          </div>
                        )}
                      </div>

                      {/* Operational Risk Indicators Grid */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        
                        {/* Summary Risk Score Breakdown card */}
                        <div className="bg-white border border-[#D0D7DE] p-4 rounded-sm flex flex-col justify-between">
                          <div>
                            <h4 className="text-xs font-bold uppercase text-[#112E51] mb-2 font-mono">Core Anomaly Matrix</h4>
                            <div className="space-y-2">
                              <div className="flex justify-between items-center pb-1 border-b border-slate-100 text-xs text-slate-700">
                                <span className="flex items-center space-x-1.5">
                                  <span className="w-2 h-2 rounded-full bg-red-600"></span>
                                  <span>Origination Country Mismatch</span>
                                </span>
                                <span className="font-mono font-bold text-red-600">96% CRITICAL</span>
                              </div>
                              <div className="flex justify-between items-center pb-1 border-b border-slate-100 text-xs text-slate-700">
                                <span className="flex items-center space-x-1.5">
                                  <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                                  <span>Shipped Manifest Load Density Deviation</span>
                                </span>
                                <span className="font-mono font-bold text-amber-500">82% HIGH</span>
                              </div>
                              <div className="flex justify-between items-center pb-1 border-b border-slate-100 text-xs text-slate-700">
                                <span className="flex items-center space-x-1.5">
                                  <span className="w-2 h-2 rounded-full bg-slate-400"></span>
                                  <span>Entity Registry Layering Anomaly</span>
                                </span>
                                <span className="font-mono font-bold text-slate-600">75% ELEVATED</span>
                              </div>
                            </div>
                          </div>
                          
                          <div className="mt-4 pt-3 border-t border-slate-100 text-[11px] text-[#2E8540] flex items-center space-x-1">
                            <ShieldAlert className="h-3.5 w-3.5" />
                            <span>Trade Remedial Classification Order: Section 301 Anti-Dumping (244.5% rate)</span>
                          </div>
                        </div>

                        {/* Interactive Case Notebook (Adding notes updates state in UI) */}
                        <div className="bg-white border border-[#D0D7DE] p-4 rounded-sm flex flex-col">
                          <h4 className="text-xs font-bold uppercase text-[#112E51] mb-2 font-mono">Officer Intelligence Notes</h4>
                          
                          {/* List existing notes */}
                          <div className="flex-1 overflow-y-auto max-h-[120px] mb-3 space-y-2 pr-1">
                            {(customNotes[currentCase.case_id] || []).map((n, idx) => (
                              <div key={idx} className="bg-slate-50 p-2 rounded-sm border border-slate-200">
                                <div className="flex justify-between text-[9px] text-[#5C5C5C] font-mono mb-0.5">
                                  <span>{n.officerName} (Analyst)</span>
                                  <span>{n.date}</span>
                                </div>
                                <p className="text-xs text-[#1B1B1B] leading-snug">{n.text}</p>
                              </div>
                            ))}
                            {(customNotes[currentCase.case_id] || []).length === 0 && (
                              <p className="text-xs text-slate-400 italic text-center py-4">No supplemental analyst notes recorded yet.</p>
                            )}
                          </div>

                          {/* Quick note addition */}
                          <div className="flex space-x-2">
                            <input
                              type="text"
                              value={newNoteText}
                              onChange={(e) => setNewNoteText(e.target.value)}
                              placeholder="Type chronological note entry..."
                              onKeyDown={(e) => { if (e.key === 'Enter') handleAddCustomNote(); }}
                              className="flex-1 bg-slate-50 border border-[#D0D7DE] text-xs px-2.5 py-1.5 focus:outline-none focus:border-[#005EA2] rounded-sm"
                            />
                            <button
                              onClick={handleAddCustomNote}
                              className="px-3 bg-[#112E51] hover:bg-[#005EA2] text-white text-xs font-bold rounded-sm cursor-pointer"
                            >
                              Add Note
                            </button>
                          </div>
                        </div>

                      </div>

                      {/* Interactive shipment chronological evolution map */}
                      <div className="bg-white border border-[#D0D7DE] rounded-sm p-4">
                        <div className="flex items-center justify-between mb-3 text-xs">
                          <span className="font-bold uppercase tracking-wider text-[#112E51] font-mono flex items-center space-x-1.5">
                            <Calendar className="h-4 w-4" />
                            <span>Vessel Chronology & Physical Routing Milestones</span>
                          </span>
                          <span className="text-[10px] text-slate-500 font-mono">Tracking active vessel targets</span>
                        </div>
                        
                        <div className="relative pt-4 pb-2 px-1">
                          <div className="absolute top-[34px] left-4 right-4 h-0.5 bg-slate-200 z-0"></div>
                          
                          <div className="grid grid-cols-4 relative z-10">
                            {[
                              { label: "Cargo Intake Lot", date: "May 10", desc: "Chinese Inland Loading Terminal" },
                              { label: "Transit Entry Port", date: "May 13", desc: "Hai Phong Port - Trans-loading" },
                              { label: "Maritime Transport", date: "May 16", desc: "AIS Disconnecting Period Active" },
                              { label: "Destination Discharge", date: "May 18", desc: "US Port Terminal Active Hold" }
                            ].map((step, sIdx) => (
                              <div key={sIdx} className="flex flex-col items-center text-center">
                                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold border ${purityColorResolver(sIdx)}`}>
                                  {sIdx + 1}
                                </div>
                                <span className="text-xs font-bold text-[#1B1B1B] mt-1">{step.label}</span>
                                <span className="text-[10px] text-[#5C5C5C] font-mono">{step.date}</span>
                                <span className="text-[9px] text-[#5C5C5C] hidden lg:block">{step.desc}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>

                    </div>
                  )}

                  {/* SUB-TAB 2: ENTITIES */}
                  {activeSubTab === 'Entities' && (
                    <div className="space-y-4">
                      
                      {/* Active Trade Supply-Chain Network Layout (USWDS Spec compliant Force Directed Concept) */}
                      <div className="bg-white border border-[#D0D7DE] rounded-sm p-4">
                        <div className="flex justify-between items-center border-b border-slate-100 pb-2 mb-3">
                          <div>
                            <h4 className="text-xs font-bold uppercase text-[#112E51] font-mono">
                              INTERACTIVE LAYER RESOLVED RELATIONSHIP NETWORK GRAPH
                            </h4>
                            <p className="text-[10px] text-[#5C5C5C]">
                              Click a logical node to drill down into corresponding corporate registrations and risk classifications.
                            </p>
                          </div>
                          <span className="text-[10px] text-slate-500 font-mono">Dashed paths = Inferred billing transfers</span>
                        </div>

                        {/* Interactive Graph Canvas representation inside an SVG */}
                        <div className="bg-[#0B1F33] relative h-[250px] w-full border border-slate-700 rounded-sm overflow-hidden flex items-center justify-center">
                          
                          {/* Background radar grid effect */}
                          <div className="absolute inset-0 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:24px_24px] opacity-25"></div>
                          
                          <svg className="absolute inset-0 w-full h-full">
                            {/* Path definitions representing connection lines */}
                            <line x1="15%" y1="50%" x2="40%" y2="50%" stroke="#FFBE2E" strokeWidth="2" strokeDasharray="5,5" />
                            <line x1="40%" y1="50%" x2="65%" y2="30%" stroke="#D83933" strokeWidth="2.5" />
                            <line x1="40%" y1="50%" x2="65%" y2="70%" stroke="#D83933" strokeWidth="2" strokeDasharray="5,5" />
                            <line x1="65%" y1="30%" x2="90%" y2="50%" stroke="#2E8540" strokeWidth="2" />
                            <line x1="65%" y1="70%" x2="90%" y2="50%" stroke="#FFBE2E" strokeWidth="2" />
                          </svg>

                          {/* Interactive Abs-nodes representing the entities */}
                          <div className="absolute inset-0 p-4">
                            
                            {/* Node 1: Xinjiang Supplier (Critical Restricted) */}
                            <button 
                              onClick={() => setSelectedNodeId("ENT-903")}
                              className={`absolute left-[10%] top-[40%] text-left group cursor-pointer focus:outline-none z-10`}
                            >
                              <div className={`w-10 h-10 rounded-full bg-red-800 border-2 border-red-500 font-extrabold flex items-center justify-center text-white text-xs ${selectedNodeId === 'ENT-903' ? 'ring-4 ring-offset-2 ring-red-500' : 'animate-pulse'}`}>
                                CHN
                              </div>
                              <span className="absolute bg-[#112E51] text-white text-[9px] font-mono rounded px-1.5 py-0.5 whitespace-nowrap mt-2 left-1/2 -translate-x-1/2 opacity-90 group-hover:opacity-100">
                                Tianshan Materials
                              </span>
                            </button>

                            {/* Node 2: Vietnam Intermediary (Shell facade) */}
                            <button 
                              onClick={() => setSelectedNodeId("ENT-902")}
                              className={`absolute left-[38%] top-[40%] text-left group cursor-pointer focus:outline-none z-10`}
                            >
                              <div className={`w-12 h-12 rounded-full bg-amber-900 border-2 border-amber-500 font-extrabold flex items-center justify-center text-white text-xs ${selectedNodeId === 'ENT-902' ? 'ring-4 ring-offset-2 ring-amber-500' : ''}`}>
                                VNM
                              </div>
                              <span className="absolute bg-[#112E51] text-white text-[9px] font-mono rounded px-1.5 py-0.5 whitespace-nowrap mt-2 left-1/2 -translate-x-1/2 opacity-90">
                                Vina Solar LLC
                              </span>
                            </button>

                            {/* Node 3: Hong Kong Broker (Transit Billing agent) */}
                            <button 
                              onClick={() => setSelectedNodeId("ENT-904")}
                              className={`absolute left-[62%] top-[15%] text-left group cursor-pointer focus:outline-none z-10`}
                            >
                              <div className={`w-10 h-10 rounded-full bg-indigo-900 border-2 border-indigo-500 font-extrabold flex items-center justify-center text-white text-[10px] ${selectedNodeId === 'ENT-904' ? 'ring-4 ring-offset-2 ring-indigo-500' : ''}`}>
                                HKG
                              </div>
                              <span className="absolute bg-[#112E51] text-white text-[9px] font-mono rounded px-1.5 py-0.5 whitespace-nowrap mt-1 left-1/2 -translate-x-1/2 opacity-90">
                                HK Broker Agent
                              </span>
                            </button>

                            {/* Node 4: US Importer Record */}
                            <button 
                              onClick={() => setSelectedNodeId("ENT-901")}
                              className={`absolute left-[82%] top-[40%] text-left group cursor-pointer focus:outline-none z-10`}
                            >
                              <div className={`w-12 h-12 rounded-full bg-emerald-950 border-2 border-emerald-500 font-extrabold flex items-center justify-center text-white text-xs ${selectedNodeId === 'ENT-901' ? 'ring-4 ring-offset-2 ring-emerald-500' : ''}`}>
                                USA
                              </div>
                              <span className="absolute bg-[#112E51] text-white text-[9px] font-mono rounded px-1.5 py-0.5 whitespace-nowrap mt-2 left-1/2 -translate-x-1/2 opacity-90">
                                BrightPath Importer
                              </span>
                            </button>

                            {/* Click invitation overlay helper */}
                            <div className="absolute right-3 top-3 bg-white/10 hover:bg-white/20 p-2 text-white font-mono text-[9px] rounded flex items-center space-x-1 leading-none">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
                              <span>System Status: Node Layer Mapping Resolved</span>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Display Selected Entity Detail Audit Record Sheets */}
                      {selectedNodeId ? (
                        (() => {
                          const ent = entities.find(e => e.entity_id === selectedNodeId);
                          if (!ent) return <p className="text-xs text-[#5C5C5C] italic">Entity node match unavailable.</p>;
                          return (
                            <div className="bg-white border border-[#D0D7DE] rounded-sm p-4">
                              <div className="flex items-center justify-between border-b border-slate-100 pb-2 mb-3">
                                <div className="flex items-center space-x-2">
                                  <span className={`px-2 py-0.5 text-[9px] font-mono font-bold rounded ${
                                    ent.risk_level === 'Critical' ? 'bg-red-100 text-red-700' : (ent.risk_level === 'High' ? 'bg-amber-100 text-amber-800' : 'bg-green-100 text-green-700')
                                  }`}>
                                    RISK LEVEL: {ent.risk_level.toUpperCase()}
                                  </span>
                                  <h4 className="text-sm font-extrabold text-[#0B1F33] font-sans">{ent.entity_name}</h4>
                                </div>
                                <span className="text-xs font-mono font-bold text-slate-500">{ent.entity_id}</span>
                              </div>

                              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                                <div className="space-y-2">
                                  <div>
                                    <span className="text-[10px] text-[#5C5C5C] font-mono font-bold block uppercase">Registration Status</span>
                                    <span className="font-semibold text-slate-800">{ent.registration_status}</span>
                                  </div>
                                  <div>
                                    <span className="text-[10px] text-[#5C5C5C] font-mono font-bold block uppercase">Core Domiciles & Address</span>
                                    <span className="text-slate-700 font-mono leading-tight">{ent.address}</span>
                                  </div>
                                  <div>
                                    <span className="text-[10px] text-[#5C5C5C] font-mono font-bold block uppercase">Tax Regulatory Entity ID</span>
                                    <span className="text-slate-800 font-mono font-bold">{ent.tax_id}</span>
                                  </div>
                                </div>

                                <div className="space-y-2">
                                  <div>
                                    <span className="text-[10px] text-[#5C5C5C] font-mono font-bold block uppercase">Sanctions Match Level</span>
                                    <span className={`font-bold ${ent.sanctions_status !== 'None' ? 'text-red-600' : 'text-green-600'}`}>
                                      {ent.sanctions_status}
                                    </span>
                                  </div>
                                  <div>
                                    <span className="text-[10px] text-[#5C5C5C] font-mono font-bold block uppercase">Corporate Shared Identifiers</span>
                                    <p className="text-slate-600 font-mono">
                                      {ent.shared_identifiers.length > 0 ? `Matches same telephone lines as: ${ent.shared_identifiers.join(', ')}` : "None identified"}
                                    </p>
                                  </div>
                                  <div>
                                    <span className="text-[10px] text-[#5C5C5C] font-mono font-bold block uppercase">Ownership & Beneficial Interests</span>
                                    <span className="text-slate-800 font-sans leading-tight block">{ent.ownership_indicators}</span>
                                  </div>
                                </div>

                                <div className="bg-[#F7F9FC] border border-[#D0D7DE]/60 p-3 rounded-sm">
                                  <span className="text-[10px] text-[#112E51] font-mono font-bold block uppercase mb-1">CBP Enforcement Site History</span>
                                  <p className="text-[11px] text-slate-600 leading-snug">
                                    {ent.enforcement_history}
                                  </p>
                                </div>
                              </div>
                            </div>
                          );
                        })()
                      ) : (
                        <div className="bg-slate-50 border border-slate-200 border-dashed rounded p-6 text-center text-xs text-[#5C5C5C] italic">
                          💡 Prompt: Select an operational node on the visual interactive canvas graph to trigger DHS record audits.
                        </div>
                      )}

                    </div>
                  )}

                  {/* SUB-TAB 3: SHIPMENTS */}
                  {activeSubTab === 'Shipments' && (
                    <div className="space-y-4">
                      
                      {/* High density cargo shipment list */}
                      <div className="bg-white border border-[#D0D7DE] rounded-sm overflow-hidden">
                        
                        <div className="bg-[#F7F9FC] p-3 border-b border-[#D0D7DE] flex justify-between items-center text-xs">
                          <span className="font-bold uppercase text-[#112E51] font-mono">
                            CARGO AND CONTAINER LEDGER (ACTIVE CASE ATTACHED)
                          </span>
                          <span className="text-slate-500 font-mono text-[10px]">Filtering matching manifests</span>
                        </div>

                        <div className="overflow-x-auto">
                          <table className="w-full text-left text-xs border-collapse">
                            <thead>
                              <tr className="bg-slate-50 font-bold text-slate-500 border-b border-[#D0D7DE] font-mono">
                                <th className="p-2.5">SHIPMENT ID / REF</th>
                                <th className="p-2.5">CONTAINER ID</th>
                                <th className="p-2.5">DECLARED ORIGIN</th>
                                <th className="p-2.5">DECLARED DESCRIPTION</th>
                                <th className="p-2.5">DECLARED VALUE</th>
                                <th className="p-2.5">AI ANOMALY</th>
                                <th className="p-2.5 text-center">ACTION REQUIRED</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 font-sans">
                              {shipments.map((ship, sIdx) => (
                                <tr key={ship.shipment_id} className="hover:bg-slate-50/80 transition-all">
                                  <td className="p-2.5 font-mono font-bold text-[#005EA2]">{ship.shipment_id}</td>
                                  <td className="p-2.5 font-mono text-slate-700">{ship.container_id}</td>
                                  <td className="p-2.5">
                                    <div className="flex flex-col">
                                      <span className="font-semibold text-slate-900">{ship.declared_origin}</span>
                                      <span className="text-[9px] text-[#D83933] font-mono font-bold block">
                                        Suspected Cross-border path: {ship.suspected_origin}
                                      </span>
                                    </div>
                                  </td>
                                  <td className="p-2.5 text-[#5C5C5C] truncate max-w-[200px]">{ship.product_description}</td>
                                  <td className="p-2.5 font-mono text-slate-800">${ship.manifest_data.declared_value_usd.toLocaleString()}</td>
                                  <td className="p-2.5">
                                    <div className="flex items-center space-x-1">
                                      <span className={`font-mono font-bold text-xs ${ship.ai_anomaly_score >= 80 ? 'text-[#D83933]' : 'text-amber-500'}`}>
                                        {ship.ai_anomaly_score}%
                                      </span>
                                    </div>
                                  </td>
                                  <td className="p-2.5 text-center">
                                    <button 
                                      onClick={() => alert(`CBP Audit Verification Dispatched for shipment ${ship.shipment_id}. Triggering active container inspection on Dock L-4`)}
                                      className="px-2 py-1 bg-[#112E51] hover:bg-[#005EA2] text-white text-[10px] font-bold rounded-sm cursor-pointer whitespace-nowrap"
                                    >
                                      INSPECT manifest AND ROUTING
                                    </button>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>

                      {/* Manifest drilldown panel (High density layout) */}
                      <div className="bg-white border border-[#D0D7DE] p-4 rounded-sm">
                        <h4 className="text-xs font-bold uppercase text-[#112E51] font-mono mb-2">
                          EXEMPLARY SEA-FREIGHT BILL OF LADING INWARD MANIFEST REPORT
                        </h4>
                        
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 bg-slate-50 p-3.5 rounded-sm border border-slate-200">
                          <div>
                            <span className="text-[9px] text-[#5C5C5C] font-mono block">CARRIER FLEET CODES</span>
                            <span className="text-xs font-bold text-slate-800">Maersk Shipping Corp</span>
                          </div>
                          <div>
                            <span className="text-[9px] text-[#5C5C5C] font-mono block">VESSEL VOYAGE TRACKS</span>
                            <span className="text-xs font-bold text-[#0b1f33]">Maersk Mc-Kinney Moller v.2604-W2</span>
                          </div>
                          <div>
                            <span className="text-[9px] text-[#5C5C5C] font-mono block">MEASURED REGISTERED WEIGHT NT</span>
                            <span className="text-xs font-bold text-slate-800 font-mono">24,310 kilograms gross</span>
                          </div>
                          <div>
                            <span className="text-[9px] text-[#5C5C5C] font-mono block">DOCK DISCHARGE BILL</span>
                            <span className="text-xs font-bold text-slate-800 font-mono">MSK9041029108</span>
                          </div>
                        </div>

                        <div className="mt-3.5 p-3.5 bg-red-50 border-l-4 border-[#D83933] text-xs">
                          <h5 className="font-bold text-[#D83933] font-sans flex items-center space-x-1 mb-1">
                            <AlertTriangle className="h-4 w-4 shrink-0" />
                            <span>SPECTRAL SCAN DUMP: Container dead-weight anomaly flag</span>
                          </h5>
                          <p className="text-slate-700 leading-relaxed font-sans mt-0.5">
                            Declared weight details indicate standard Solar Crystalline modules total 21.1 Tons. Scanned container manifests registered a 24.3 Ton displacement. The additional 14% delta matches identical heavy structural alloy steel shapes (HS Code 7308) sourced secretly from restricted Chinese regional Mills.
                          </p>
                        </div>
                      </div>

                    </div>
                  )}

                  {/* SUB-TAB 4: AI FINDINGS */}
                  {activeSubTab === 'AI Findings' && (
                    <div className="space-y-4">
                      
                      <div className="bg-white border border-[#D0D7DE] rounded-sm p-4">
                        <div className="flex justify-between items-center mb-3">
                          <h4 className="text-xs font-bold uppercase text-[#112E51] font-mono">
                            AI FLAG MATCH REASONINGS & HUMAN-IN-THE-LOOP FEEDBACK AUDIT
                          </h4>
                          <span className="text-[10px] text-slate-500 font-mono">DHS Explainable AI compliance framework</span>
                        </div>

                        <div className="space-y-4">
                          {findings.map((f) => (
                            <div key={f.finding_id} className="bg-[#F7F9FC] border border-[#D0D7DE] p-4 rounded-sm flex flex-col md:flex-row md:items-start justify-between">
                              <div className="flex-1 pr-6">
                                <div className="flex items-center space-x-2 mb-1.5">
                                  <span className={`px-1.5 py-0.2 text-[9px] font-mono font-bold rounded ${
                                    f.severity === 'Critical' ? 'bg-[#D83933] text-white' : 'bg-slate-200 text-slate-800'
                                  }`}>
                                    {f.severity.toUpperCase()} ALERT
                                  </span>
                                  <h5 className="text-xs font-extrabold text-[#0B1F33] font-sans">{f.title}</h5>
                                </div>
                                <p className="text-xs text-slate-700 leading-relaxed">{f.explanation}</p>
                                
                                <div className="flex items-center space-x-2 mt-2 font-mono text-[10px] text-[#5C5C5C]">
                                  <span>Associated Ledger Evidence references:</span>
                                  {f.evidence_links.map((link) => (
                                    <span key={link} className="bg-white border border-[#D0D7DE] px-1 rounded font-bold text-[#005EA2]">
                                      {link}
                                    </span>
                                  ))}
                                </div>
                              </div>

                              {/* Interactive controls */}
                              <div className="shrink-0 mt-3 md:mt-0 flex flex-col space-y-2 max-w-[150px]">
                                <span className="text-[10px] text-[#5C5C5C] font-mono block">Analyst Feedback Verification:</span>
                                
                                <button
                                  onClick={() => handleToggleFindingStatus(f.finding_id, 'Accepted')}
                                  className={`px-3 py-1 text-[11px] font-bold uppercase rounded-sm border cursor-pointer flex items-center justify-between ${
                                    f.verification_status === 'Accepted'
                                      ? 'bg-emerald-600 border-transparent text-white'
                                      : 'bg-white border-[#D0D7DE] text-emerald-700 hover:bg-emerald-50'
                                  }`}
                                >
                                  <span>ACCEPT EXPLANATION</span>
                                  {f.verification_status === 'Accepted' && <Check className="h-3 w-3 inline" />}
                                </button>

                                <button
                                  onClick={() => handleToggleFindingStatus(f.finding_id, 'Rejected')}
                                  className={`px-3 py-1 text-[11px] font-bold uppercase rounded-sm border cursor-pointer flex items-center justify-between ${
                                    f.verification_status === 'Rejected'
                                      ? 'bg-red-700 border-transparent text-white'
                                      : 'bg-white border-[#D0D7DE] text-red-700 hover:bg-red-50'
                                  }`}
                                >
                                  <span>REJECT</span>
                                  {f.verification_status === 'Rejected' && <XCircle className="h-3 w-3 inline" />}
                                </button>

                                <button
                                  onClick={() => handleToggleFindingStatus(f.finding_id, 'Needs Review')}
                                  className={`px-3 py-1 text-[11px] font-bold uppercase rounded-sm border cursor-pointer flex items-center justify-between ${
                                    f.verification_status === 'Needs Review'
                                      ? 'bg-amber-600 border-transparent text-white'
                                      : 'bg-white border-[#D0D7DE] text-amber-700 hover:bg-amber-50'
                                  }`}
                                >
                                  <span>REVIEWING...</span>
                                  {f.verification_status === 'Needs Review' && <HelpCircle className="h-3 w-3 inline" />}
                                </button>
                              </div>

                            </div>
                          ))}
                        </div>
                      </div>

                    </div>
                  )}

                  {/* SUB-TAB 5: REFERRAL */}
                  {activeSubTab === 'Referral' && (
                    <div className="space-y-4">
                      
                      {/* Interactive Section Selector & Narrative Builder */}
                      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                        
                        {/* Selected Checklist Selection */}
                        <div className="bg-white border border-[#D0D7DE] p-4 rounded-sm flex flex-col justify-between">
                          <div>
                            <span className="text-[10px] text-[#5C5C5C] font-mono font-bold uppercase block mb-1">
                              Evidence Inventory Selection
                            </span>
                            <h4 className="text-xs font-extrabold text-[#112E51] font-mono mb-2">
                              STATUTORY SECTIONS & VIOLATIONS TO CITE
                            </h4>
                            
                            <div className="space-y-2">
                              {[
                                { name: "Executive Summary & Charges", desc: "Brief operational enforcement synopses" },
                                { name: "Subject Corporate Overview", desc: "Importer registry mapping detail" },
                                { name: "Forensic Evidence Accumulation", desc: "Cites container manifest weight deviations" },
                                { name: "Recommended Legal Actions", desc: "US Customs penalties with double tariff damage citation" }
                              ].map((sect) => (
                                <label key={sect.name} className="flex items-start space-x-2 p-2 rounded bg-slate-50 cursor-pointer">
                                  <input 
                                    type="checkbox" 
                                    checked={selectedNarrativeSections.includes(sect.name)}
                                    onChange={(e) => {
                                      if (e.target.checked) {
                                        setSelectedNarrativeSections(prev => [...prev, sect.name]);
                                      } else {
                                        setSelectedNarrativeSections(prev => prev.filter(item => item !== sect.name));
                                      }
                                    }}
                                    className="mt-0.5" 
                                  />
                                  <div className="text-xs">
                                    <span className="font-bold text-slate-800 tracking-tight block">{sect.name}</span>
                                    <span className="text-[10px] text-[#5C5C5C]">{sect.desc}</span>
                                  </div>
                                </label>
                              ))}
                            </div>
                          </div>

                          <div className="pt-3 border-t border-slate-100">
                            <button
                              onClick={handleDraftReferralNarrative}
                              disabled={draftLoading}
                              className="w-full py-2 bg-[#005EA2] hover:bg-[#0076D6] text-white text-xs font-extrabold uppercase rounded-sm flex items-center justify-center space-x-1 cursor-pointer"
                            >
                              <Sparkles className="h-3.5 w-3.5" />
                              <span>{draftLoading ? "FORMULATING FORENSICS..." : "COMPILE AI TRADE DRAFT"}</span>
                            </button>
                          </div>
                        </div>

                        {/* Interactive text editor representing compiled narrative */}
                        <div className="bg-[#0B1F33] p-4 text-slate-100 rounded-sm lg:col-span-2 flex flex-col min-h-[300px]">
                          <div className="flex justify-between items-center border-b border-white/10 pb-2 mb-3 shrink-0">
                            <span className="text-[10px] font-mono text-cyan-400 font-bold uppercase flex items-center space-x-1.5">
                              <FileText className="h-4 w-4" />
                              <span>OFFICIAL DHS GENERAL COUNSEL TRADE FRAUD COMPLIANCE DRAFT</span>
                            </span>
                            <span className="text-[9px] bg-cyan-950 text-cyan-400 px-1.5 py-0.2 rounded font-mono">
                              System Draft Mode
                            </span>
                          </div>

                          <div className="flex-1 overflow-y-auto text-xs font-mono leading-relaxed space-y-3 pr-2">
                            {draftNarrative ? (
                              <textarea
                                value={draftNarrative}
                                onChange={(e) => setDraftNarrative(e.target.value)}
                                className="w-full h-full bg-transparent border-none text-xs text-slate-100 font-mono leading-relaxed focus:outline-none focus:ring-0 resize-none min-h-[250px]"
                              />
                            ) : (
                              <div className="flex flex-col items-center justify-center h-full text-center py-10">
                                <FileText className="h-10 w-10 text-slate-600 mb-2" />
                                <p className="text-slate-400 font-semibold mb-2">No Referral narrative draft compiled yet.</p>
                                <p className="text-slate-500 max-w-sm font-sans">
                                  Select required sections on the left and click **Compile AI Trade Draft** to synthesize a custom DHS-compliant referral paper.
                                </p>
                              </div>
                            )}
                          </div>

                          {draftNarrative && (
                            <div className="mt-3 pt-3 border-t border-white/10 flex justify-between items-center shrink-0">
                              <span className="text-[10px] text-slate-400">Ready for statutory submission. Double check target details.</span>
                              <button
                                onClick={() => {
                                  alert("Draft generated successfully. DHS Trade referral package submitted onto Department of Justice Trade Division API.");
                                  setDraftNarrative('');
                                }}
                                className="px-3 py-1 bg-[#0076D6] hover:bg-[#005EA2] text-xs font-bold uppercase rounded text-white cursor-pointer"
                              >
                                Submit Package
                              </button>
                            </div>
                          )}
                        </div>

                      </div>

                    </div>
                  )}

                </div>
              </div>
            </div>

          ) : (
            
            // ==========================================
            // CBP COMMAND CENTER DASHBOARD (LANDING)
            // ==========================================
            <div className="flex-1 flex overflow-hidden">
              
              {/* PRIMARY CONTENT CANVAS (Master list and Anomaly statistics block) */}
              {activeTab === 'dashboard' && (
                <div className="flex-1 p-5 flex flex-col space-y-5 overflow-y-auto">
                
                {/* Mission Summary Strip Area */}
                <section className="grid grid-cols-2 lg:grid-cols-5 gap-3 shrink-0">
                  <div className="bg-white border-l-4 border-[#D83933] border-t border-b border-r border-slate-200 p-3 rounded-sm flex flex-col justify-between shadow-sm">
                    <span className="text-[9px] text-[#5C5C5C] font-mono uppercase font-bold tracking-wider leading-none">Critical Investigations</span>
                    <span className="text-2xl font-black font-mono tracking-tight text-[#0B1F33] mt-1">
                      {totalCriticalCount}
                    </span>
                    <span className="text-[9px] text-[#D83933] font-bold font-mono">⚠️ PRIORITY ESCALATION</span>
                  </div>

                  <div className="bg-white border-l-4 border-amber-500 border-t border-b border-r border-slate-200 p-3 rounded-sm flex flex-col justify-between shadow-sm">
                    <span className="text-[9px] text-[#5C5C5C] font-mono uppercase font-bold tracking-wider leading-none">Anomalous Manifest Volume</span>
                    <span className="text-2xl font-black font-mono tracking-tight text-[#0B1F33] mt-1">
                      {highRiskShipmentsCount}
                    </span>
                    <span className="text-[9px] text-[#5C5C5C] font-mono font-medium">Overloaded containers detected</span>
                  </div>

                  <div className="bg-white border-l-4 border-[#00BDE3] border-t border-b border-r border-slate-200 p-3 rounded-sm flex flex-col justify-between shadow-sm">
                    <span className="text-[9px] text-[#5C5C5C] font-mono uppercase font-bold tracking-wider leading-none">UFLPA Watchlist Blocks</span>
                    <span className="text-2xl font-black font-mono tracking-tight text-[#0B1F33] mt-1">
                      {entities.filter(e => e.sanctions_status !== 'None').length}
                    </span>
                    <span className="text-[9px] text-[#00BDE3] font-bold font-mono">MATCHED VENDOR BLOCKS</span>
                  </div>

                  <div className="bg-white border-l-4 border-[#005EA2] border-t border-b border-r border-slate-200 p-3 rounded-sm flex flex-col justify-between shadow-sm">
                    <span className="text-[9px] text-[#5C5C5C] font-mono uppercase font-bold tracking-wider leading-none">Uncollected Section 301 AD/CVD</span>
                    <span className="text-lg font-black font-mono tracking-tight text-[#0B1F33] mt-1 shrink-0 truncate">
                      $8,410,200
                    </span>
                    <span className="text-[9px] text-green-600 font-bold font-mono">RECOVERABLE REVENUE</span>
                  </div>

                  <div className="bg-white border shadow-sm border-slate-200 p-3 rounded-sm flex flex-col justify-between lg:col-span-1 col-span-2">
                    <span className="text-[9px] text-[#5C5C5C] font-mono uppercase font-bold tracking-wider leading-none">Filing Anomaly SLA Limit</span>
                    <span className="text-2xl font-black font-mono tracking-tight text-[#D83933] mt-1 flex items-center space-x-1 animate-pulse">
                      <Clock className="w-4 h-4" />
                      <span>3 DAYS</span>
                    </span>
                    <span className="text-[9px] text-red-600 font-bold">CLOSE TO OVERDUE REMEDIES</span>
                  </div>
                </section>

                {/* Intelligent Search Matrix Control bar */}
                <div className="bg-white p-3 rounded-sm border border-[#D0D7DE] flex flex-col sm:flex-row sm:items-center space-y-2.5 sm:space-y-0 sm:space-x-4 shrink-0 shadow-sm">
                  <div className="flex-1 relative flex items-center">
                    <Search className="h-4 w-4 text-slate-400 absolute left-3" />
                    <input 
                      type="text" 
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Audit Search query (e.g., Silicon modules, Apex Steel, Vietnam transshipment corridors...)"
                      className="w-full bg-[#F7F9FC] border border-[#D0D7DE] rounded-sm pl-9 pr-4 py-1.5 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-[#005EA2] transition-colors"
                    />
                  </div>

                  <div className="flex items-center space-x-3.5 text-xs font-mono font-bold shrink-0">
                    <div className="flex items-center space-x-1.5">
                      <span className="text-[#5C5C5C] uppercase text-[10px]">Priority Filer:</span>
                      <select 
                        value={priorityFilter}
                        onChange={(e) => setPriorityFilter(e.target.value)}
                        className="bg-slate-50 border border-slate-300 rounded px-2 py-1 text-xs text-slate-800 focus:outline-none focus:border-[#005EA2]"
                      >
                        <option value="all">ALL STAGES</option>
                        <option value="critical">CRITICAL</option>
                        <option value="high">HIGH</option>
                        <option value="medium">MEDIUM</option>
                      </select>
                    </div>

                    <div className="flex items-center space-x-1.5">
                      <span className="text-[#5C5C5C] uppercase text-[10px]">CBP Risk Score:</span>
                      <select 
                        value={riskFilter}
                        onChange={(e) => setRiskFilter(e.target.value)}
                        className="bg-slate-50 border border-slate-300 rounded px-2 py-1 text-xs text-[#0B1F33] focus:outline-none focus:border-[#005EA2]"
                      >
                        <option value="all">ALL SCORES</option>
                        <option value="high">≥ 80 SCORING</option>
                        <option value="medium">50 - 79 SCORING</option>
                        <option value="low">≤ 49 SCORING</option>
                      </select>
                    </div>
                  </div>
                </div>

                {/* Split layout: Case queue left + threat log right */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 flex-1 overflow-hidden">
                  
                  {/* Master core queue grid (Left panel span 2) */}
                  <div className="lg:col-span-2 bg-white rounded-sm border border-[#D0D7DE] flex flex-col overflow-hidden shadow-sm">
                    <div className="bg-[#112E51] text-white p-3 border-b border-slate-700 flex justify-between items-center text-xs shrink-0 font-mono">
                      <span className="font-bold uppercase tracking-wider">ACTIVE ILLEGAL TRANSSHIPMENT INVESTIGATIVE QUEUES</span>
                      <span className="text-cyan-400 font-bold">{filteredCases.length} ACTIVE AUDITS MATCHED</span>
                    </div>

                    <div className="flex-1 overflow-y-auto">
                      <table className="w-full text-left text-xs border-collapse">
                        <thead className="sticky top-0 bg-white border-b border-[#D0D7DE] font-mono text-[#5C5C5C] font-bold">
                          <tr>
                            <th className="p-3">RISK MATCH</th>
                            <th className="p-3">INVESTIGATION ENTITY</th>
                            <th className="p-3">CATEGORY / COMMODITY</th>
                            <th className="p-3">DATE CONTEXT</th>
                            <th className="p-3">SLA REMEDIES</th>
                            <th className="p-3 text-right">AUDITING ACTIONS</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 font-sans">
                          {filteredCases.map((caseItem) => (
                            <tr key={caseItem.case_id} className="hover:bg-[#F2F6F9] transition-all cursor-pointer" onClick={() => selectCaseForDetail(caseItem)}>
                              
                              {/* Risk Score indicator */}
                              <td className="p-3 font-mono">
                                <span className={`inline-block px-2 py-1 rounded-sm text-center font-extrabold w-12 text-xs text-white ${
                                  caseItem.risk_score >= 80 ? 'bg-[#D83933]' : (caseItem.risk_score >= 60 ? 'bg-amber-600' : 'bg-[#2E8540]')
                                }`}>
                                  {caseItem.risk_score}
                                </span>
                              </td>

                              {/* Target context */}
                              <td className="p-3 font-medium">
                                <div className="flex flex-col">
                                  <span className="font-extrabold text-slate-900 text-xs hover:text-[#005EA2] hover:underline">
                                    {caseItem.target_entity}
                                  </span>
                                  <span className="text-[10px] text-[#5C5C5C] font-mono uppercase tracking-tight block">
                                    {caseItem.case_id} — {caseItem.case_name.slice(0, 36)}...
                                  </span>
                                </div>
                              </td>

                              {/* Product Commodity */}
                              <td className="p-3">
                                <div className="flex flex-col max-w-[140px]">
                                  <span className="font-medium text-slate-800 text-[11px] truncate">{caseItem.product_category}</span>
                                  <span className="text-[9px] text-slate-500 font-mono">HS 8541 Class</span>
                                </div>
                              </td>

                              {/* Date context */}
                              <td className="p-3 font-mono text-slate-600 text-[11px]">
                                {caseItem.opened_date}
                              </td>

                              {/* SLA remedies alert badge limits */}
                              <td className="p-3 font-mono font-bold">
                                <span className={`text-[10px] ${caseItem.sla_timer.includes('Violated') ? 'text-[#D83933]' : 'text-slate-600'}`}>
                                  {caseItem.sla_timer}
                                </span>
                              </td>

                              {/* Auditing Actions Button */}
                              <td className="p-3 text-right">
                                <button 
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    selectCaseForDetail(caseItem);
                                  }}
                                  className="px-3 py-1 bg-[#112E51] hover:bg-[#0076D6] text-white text-[10px] font-bold uppercase rounded-sm border border-transparent cursor-pointer flex items-center space-x-1"
                                >
                                  <span>Drill Workspace</span>
                                  <ArrowRight className="h-3 w-3 inline" />
                                </button>
                              </td>

                            </tr>
                          ))}
                        </tbody>
                      </table>
                      
                      {filteredCases.length === 0 && (
                        <div className="py-12 text-center text-slate-400 font-sans italic">
                          No Active CBP trade targets matched the set querying filters. Try resetting terms.
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Operational LIVE Threat Alert Stream Panel (Right column) */}
                  <div className="bg-white rounded-sm border border-[#D0D7DE] flex flex-col overflow-hidden shadow-sm">
                    <div className="bg-[#102A43] text-white p-3 border-b border-slate-700 flex justify-between items-center text-xs shrink-0 font-mono">
                      <span className="font-extrabold uppercase text-slate-100 flex items-center space-x-1">
                        <Radio className="h-4 w-4 text-rose-500 animate-pulse" />
                        <span>SENTRY DIGITAL FEEDS ALERT STREAM</span>
                      </span>
                      <span className="text-[10px] font-bold text-slate-300">Live Telemetry</span>
                    </div>

                    {/* Threat list scrolls nicely */}
                    <div className="flex-1 overflow-y-auto p-3 space-y-3.5 bg-[#FDFEFE]">
                      {threatFeed.map((evt) => (
                        <div 
                          key={evt.id} 
                          className={`p-3 rounded-sm border text-xs relative overflow-hidden transition-all hover:shadow bg-white ${
                            evt.severity === 'Critical' ? 'border-[#D83933] bg-red-50/20' : 'border-amber-200 bg-amber-50/10'
                          }`}
                        >
                          <div className="flex justify-between items-start mb-1 font-mono text-[9px]">
                            <span className={evt.severity === 'Critical' ? 'text-red-600 font-bold' : 'text-amber-600'}>
                              ● {evt.severity.toUpperCase()} ALERT FLAG
                            </span>
                            <span className="text-[#5C5C5C]">{evt.timestamp}</span>
                          </div>
                          
                          <h4 className="font-extrabold text-slate-900 leading-snug tracking-tight pr-5">
                            {evt.title}
                          </h4>
                          <p className="text-slate-600 text-[11px] leading-snug mt-1.5 font-sans">
                            {evt.description}
                          </p>

                          <div className="flex items-center justify-between mt-2 pt-2 border-t border-dashed border-slate-200 font-mono text-[9.5px]">
                            <span className="text-emerald-700 font-bold">Confidence Match: {evt.confidence}%</span>
                            {evt.related_case_id && (
                              <button 
                                onClick={() => {
                                  const matchCase = cases.find(c => c.case_id === evt.related_case_id);
                                  if (matchCase) selectCaseForDetail(matchCase);
                                }}
                                className="text-[#005EA2] underline cursor-pointer font-bold hover:text-blue-500"
                              >
                                {evt.related_case_id}
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Status diagnostic indicator at base of live feed */}
                    <div className="p-3 bg-[#F0F4F8] border-t border-[#D0D7DE] flex items-center justify-between text-[11px]">
                      <span className="text-[#5C5C5C] font-mono">Anomaly Classifier Status</span>
                      <span className="text-green-700 font-mono font-bold uppercase">● SCORING PROFILES ACTIVE</span>
                    </div>
                  </div>

                </div>
              </div>
            )}

              {/* ========================================================= */}
              {/* VIEW 2: ACTIVE INVESTIGATIONS REGISTRY */}
              {/* ========================================================= */}
              {activeTab === 'investigations' && (
                <div className="flex-1 p-5 flex flex-col space-y-5 overflow-y-auto w-full">
                  
                  {/* Registry Banner */}
                  <div className="bg-white p-4 border border-[#D0D7DE] rounded-sm flex flex-col md:flex-row justify-between items-start md:items-center space-y-3 md:space-y-0 shadow-xs shrink-0 font-sans">
                    <div>
                      <h3 className="text-sm font-bold text-[#0B1F33] font-mono uppercase flex items-center space-x-2">
                        <FileCheck className="w-4.5 h-4.5 text-[#005EA2]" />
                        <span>SENTRY INVESTIGATIONS QUEUE & STATUTORY REGISTRY</span>
                      </h3>
                      <p className="text-xs text-[#5C5C5C] mt-0.5">Evaluate current custom target folders, allocate officers, or launch secure AI forensic analysis dashboards.</p>
                    </div>
                    <button 
                      onClick={() => { setSearchQuery(''); setPriorityFilter('all'); setRiskFilter('all'); }}
                      className="px-3 py-1.5 border border-[#D0D7DE] hover:bg-slate-50 text-xs font-mono rounded-sm text-slate-700 font-bold flex items-center space-x-1.5 cursor-pointer"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      <span>CLEAR ALL DIRECT FILTERS</span>
                    </button>
                  </div>

                  {/* Filter Cabin */}
                  <div className="bg-white p-3.5 rounded-sm border border-[#D0D7DE] flex flex-col md:flex-row md:items-center gap-4 shrink-0 shadow-sm font-sans">
                    <div className="flex-1 relative flex items-center">
                      <Search className="h-4 w-4 text-slate-400 absolute left-3" />
                      <input 
                        type="text" 
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Filter active casework database folder entries (e.g. Apex, Vietnam, Plywood)..."
                        className="w-full bg-[#F7F9FC] border border-[#D0D7DE] rounded-sm pl-9 pr-4 py-1.5 text-xs text-slate-800 focus:outline-none focus:border-[#005EA2]"
                      />
                    </div>
                    
                    <div className="flex gap-3 text-xs font-mono font-bold shrink-0">
                      <div>
                        <select 
                          value={priorityFilter}
                          onChange={(e) => setPriorityFilter(e.target.value)}
                          className="bg-slate-50 border border-slate-300 rounded px-2.5 py-1.5 text-xs text-slate-800 focus:outline-none focus:border-[#005EA2]"
                        >
                          <option value="all">SLA STAGE: ALL</option>
                          <option value="critical">CRITICAL SLA</option>
                          <option value="high">HIGH PRIORITY</option>
                          <option value="medium">MEDIUM PRIORITY</option>
                        </select>
                      </div>

                      <div>
                        <select 
                          value={riskFilter}
                          onChange={(e) => setRiskFilter(e.target.value)}
                          className="bg-slate-50 border border-[#D0D7DE] rounded px-2.5 py-1.5 text-xs text-[#0B1F33] focus:outline-none focus:border-[#005EA2]"
                        >
                          <option value="all">SENTRY RISK MATRIX: ALL</option>
                          <option value="high">CRITICAL SCORES (≥ 80)</option>
                          <option value="medium">ELEVATED SCORES (50 - 79)</option>
                        </select>
                      </div>
                    </div>
                  </div>

                  {/* Core Table List */}
                  <div className="bg-white rounded-sm border border-[#D0D7DE] shadow-sm flex-1 overflow-auto">
                    <table className="w-full text-left text-xs border-collapse font-sans">
                      <thead className="sticky top-0 bg-[#F0F4F8] border-b border-[#D0D7DE] font-mono text-[#112E51] font-bold">
                        <tr>
                          <th className="p-3 w-20">SENTRY SCORE</th>
                          <th className="p-3">INVESTIGATION DIRECTORY ID</th>
                          <th className="p-3">ASSIGNED COMPLIANCE OFFICER</th>
                          <th className="p-3">COMMODITY DESCRIPTION</th>
                          <th className="p-3">DATE OPENED</th>
                          <th className="p-3">REFERRAL STATUS</th>
                          <th className="p-3 text-right">EXAMINATION ACTIONS</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {filteredCases.map((c) => (
                          <tr key={c.case_id} className="hover:bg-slate-50 transition-all cursor-pointer" onClick={() => selectCaseForDetail(c)}>
                            <td className="p-3">
                              <span className={`inline-block px-2.5 py-1 rounded text-center font-extrabold w-12 text-xs text-white ${
                                c.risk_score >= 80 ? 'bg-[#D83933]' : 'bg-amber-600'
                              }`}>
                                {c.risk_score}%
                              </span>
                            </td>
                            <td className="p-3">
                              <div className="flex flex-col">
                                <span className="font-extrabold text-[#0B1F33] hover:underline text-xs">{c.target_entity}</span>
                                <span className="text-[10px] text-[#5C5C5C] font-mono block font-medium uppercase mt-0.5">{c.case_id} — {c.case_name}</span>
                              </div>
                            </td>
                            <td className="p-3 text-slate-800 font-medium">
                              <span className="flex items-center space-x-1.5">
                                <span className="w-1.5 h-1.5 bg-green-500 rounded-full"></span>
                                <span>{c.assigned_officer}</span>
                              </span>
                            </td>
                            <td className="p-3">
                              <span className="text-[11px] text-[#1B1B1B] font-mono truncate max-w-[200px] block">{c.product_category}</span>
                            </td>
                            <td className="p-3 text-[#5C5C5C] font-mono">
                              {c.opened_date}
                            </td>
                            <td className="p-3 font-mono">
                              <span className={`px-2 py-0.5 text-[10px] rounded font-bold ${
                                c.referral_status === 'Awaiting Approval' ? 'bg-amber-100 text-amber-800 border border-amber-300' :
                                c.referral_status === 'In Progress' ? 'bg-blue-50 text-[#005EA2] border border-blue-200' :
                                'bg-slate-100 text-slate-600'
                              }`}>
                                {c.referral_status}
                              </span>
                            </td>
                            <td className="p-3 text-right">
                              <button 
                                onClick={(e) => {
                                  e.stopPropagation();
                                  selectCaseForDetail(c);
                                }}
                                className="px-3.5 py-1 bg-[#112E51] hover:bg-[#0076D6] text-white text-[10px] font-bold uppercase rounded-sm cursor-pointer inline-flex items-center space-x-1 ml-auto"
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
                      <div className="py-20 text-center text-[#5C5C5C] italic font-sans text-xs">
                        No trade investigations matched the current filter conditions. Try adjusting the query fields.
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* ========================================================= */}
              {/* VIEW 3: CONTAINER SHIPMENT INTELLIGENCE PORTAL */}
              {/* ========================================================= */}
              {activeTab === 'shipments' && (
                <div className="flex-1 p-5 flex flex-col lg:flex-row gap-5 overflow-hidden w-full h-full font-sans">
                  
                  {/* Left Column: List and Statistics */}
                  <div className="flex-1 flex flex-col space-y-4 overflow-y-auto">
                    
                    {/* Header Banner */}
                    <div className="bg-white p-4 border border-[#D0D7DE] rounded-sm flex justify-between items-center shadow-xs">
                      <div>
                        <h3 className="text-sm font-bold text-[#0B1F33] font-mono uppercase flex items-center space-x-2">
                          <Anchor className="w-4.5 h-4.5 text-[#005EA2]" />
                          <span>MARITIME CARGO SHIPMENT ANOMALY TRACKER</span>
                        </h3>
                        <p className="text-xs text-[#5C5C5C] mt-0.5 font-sans">Real-time terminal holds and volumetric balance audits for all solar elements, plywood cargos, and heavy carbon steel billets.</p>
                      </div>
                      <span className="text-[11px] font-mono font-bold text-slate-500 bg-slate-100 px-2 py-1 rounded">
                        Active Tracked Cargo: {shipments.length} lots
                      </span>
                    </div>

                    {/* Shipments List cards */}
                    <div className="space-y-3">
                      {shipments.map((s) => (
                        <div 
                          key={s.shipment_id}
                          onClick={() => setSelectedShipmentId(s.shipment_id)}
                          className={`p-4 bg-white border rounded-sm transition-all hover:shadow-md cursor-pointer flex flex-col justify-between ${
                            selectedShipmentId === s.shipment_id 
                              ? 'border-l-4 border-[#005EA2] bg-blue-50/10 shadow-xs' 
                              : s.ai_anomaly_score >= 80 ? 'border-l-4 border-[#D83933]' : 'border-l-4 border-emerald-500'
                          }`}
                        >
                          <div className="flex justify-between items-start">
                            <div>
                              <div className="flex items-center space-x-2">
                                <span className="font-extrabold text-xs font-mono text-[#0B1F33]">{s.container_id}</span>
                                <span className="text-[10px] text-[#5C5C5C] font-mono">Lot ID: {s.shipment_id}</span>
                                {s.customs_flags.includes('Active CBP Hold') && (
                                  <span className="bg-[#D83933] text-white text-[8px] font-bold font-mono px-1.5 py-0.2 uppercase rounded animate-pulse">
                                    MANUAL EXAMINATION HOLD
                                  </span>
                                )}
                              </div>
                              <h4 className="text-xs font-bold text-[#112E51] mt-1 pr-4">{s.product_description}</h4>
                            </div>

                            <div className="text-right">
                              <span className={`inline-block px-2 py-0.5 rounded font-bold font-mono text-xs ${
                                s.ai_anomaly_score >= 80 ? 'bg-red-100 text-red-800' : 'bg-slate-100 text-slate-800'
                              }`}>
                                {s.ai_anomaly_score}% RISK SCORE
                              </span>
                              <span className="text-[9px] block text-[#5C5C5C] font-mono mt-0.5">Automated Sentry Rating</span>
                            </div>
                          </div>

                          <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 mt-3 pt-3 border-t border-dashed border-slate-100 text-[11px] text-slate-700 font-mono">
                            <div>
                              <span className="text-slate-400 block text-[9px] uppercase">Declared Origin</span>
                              <span className="font-bold">{s.declared_origin}</span>
                            </div>
                            <div>
                              <span className="text-slate-400 block text-[9px] uppercase">Suspected True Origin</span>
                              <span className="font-bold text-red-600">{s.suspected_origin} (Transit)</span>
                            </div>
                            <div>
                              <span className="text-slate-400 block text-[9px] uppercase">Vessel / Carrier</span>
                              <span className="truncate block font-semibold">{s.manifest_data.vessel} ({s.manifest_data.carrier})</span>
                            </div>
                            <div className="text-right">
                              <span className="text-slate-400 block text-[9px] uppercase">Declared Value</span>
                              <span className="font-bold text-green-700">${s.manifest_data.declared_value_usd.toLocaleString()}</span>
                            </div>
                          </div>

                          {/* Action Bar for shipmenthold toggling */}
                          <div className="flex justify-between items-center mt-3 pt-2.5 border-t border-slate-101 font-mono">
                            <span className="text-[10px] text-[#5C5C5C] italic">
                              Latest check status: {s.inspection_history}
                            </span>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleToggleShipmentHold(s.shipment_id);
                              }}
                              className={`px-3 py-1 text-[10px] font-bold uppercase rounded-sm cursor-pointer transition-colors ${
                                s.customs_flags.includes('Active CBP Hold') 
                                  ? 'bg-emerald-600 hover:bg-emerald-700 text-white' 
                                  : 'bg-[#D83933] hover:bg-red-700 text-white'
                              }`}
                            >
                              {s.customs_flags.includes('Active CBP Hold') ? 'Release Hold' : 'Flag Examination Hold'}
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>

                  </div>

                  {/* Right Column: Active Shipment Detail Inspector */}
                  <div className="w-full lg:w-[360px] bg-white border border-[#D0D7DE] rounded-sm flex flex-col overflow-hidden shrink-0 shadow-sm">
                    <div className="bg-[#112E51] text-white p-3 border-b border-slate-700 flex justify-between items-center shrink-0 font-mono text-xs font-bold">
                      <span>VESSEL SHIPMENT AUDIT DESKTOP PANEL</span>
                      <span className="text-cyan-400">INFO INDX</span>
                    </div>

                    {selectedShipmentId ? (() => {
                      const selShip = shipments.find(s => s.shipment_id === selectedShipmentId);
                      if (!selShip) return null;
                      return (
                        <div className="flex-1 p-4 overflow-y-auto space-y-4 text-xs font-sans">
                          
                          {/* Container and score display */}
                          <div className="p-3 bg-slate-50 rounded border border-slate-200">
                            <h4 className="text-[10px] font-bold font-mono text-[#5C5C5C] uppercase">Target Cargo Identifier Code</h4>
                            <p className="text-base font-black font-mono mt-0.5 text-[#0B1F33]">{selShip.container_id}</p>
                            
                            <div className="flex items-center space-x-1.5 mt-2">
                              <span className={`w-3 h-3 rounded-full ${selShip.ai_anomaly_score >= 80 ? 'bg-red-500 animate-pulse' : 'bg-green-500'}`}></span>
                              <span className="text-xs font-mono font-bold text-slate-700">Audit Status: {selShip.ai_anomaly_score >= 80 ? 'Audit Target Active' : 'Sufficient Clearances'}</span>
                            </div>
                          </div>

                          {/* Logistics / Invoicing detail */}
                          <div className="space-y-2">
                            <h3 className="text-[11px] font-black uppercase text-[#112E51] font-mono border-b border-slate-100 pb-1">Primary Manifest Ledger</h3>
                            
                            <div className="text-xs space-y-1.5 leading-snug">
                              <div className="flex justify-between">
                                <span className="text-[#5C5C5C] font-mono uppercase text-[9px]">Shipper / Exporter:</span>
                                <span className="font-bold text-[#1B1B1B] text-right">{selShip.manifest_data.shipper}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-[#5C5C5C] font-mono uppercase text-[9px]">Consignee / Importer:</span>
                                <span className="font-bold text-[#1B1B1B] text-right">{selShip.manifest_data.consignee}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-[#5C5C5C] font-mono uppercase text-[9px]">Gross Dead Weight:</span>
                                <span className="font-bold text-[#1B1B1B] font-mono">{selShip.manifest_data.weight_kg.toLocaleString()} kg</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-[#5C5C5C] font-mono uppercase text-[9px]">Bill of Lading File:</span>
                                <span className="font-bold text-[#1B1B1B] font-mono">{selShip.manifest_data.bill_of_lading}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-[#5C5C5C] font-mono uppercase text-[9px]">Voyage Tracking No:</span>
                                <span className="font-bold text-[#1B1B1B] font-mono">{selShip.manifest_data.vessel} — {selShip.manifest_data.voyage_number}</span>
                              </div>
                            </div>
                          </div>

                          {/* Physical Routing steps */}
                          <div className="space-y-2">
                            <h3 className="text-[11px] font-black uppercase text-[#112E51] font-mono border-b border-slate-101 pb-1">Vessel Routing Progression Map</h3>
                            
                            <div className="relative pl-4 space-y-3.5 mt-2 text-xs font-mono">
                              <div className="absolute left-1.5 top-1.5 bottom-1.5 w-0.5 bg-slate-300"></div>
                              {selShip.route.map((r, rIdx) => (
                                <div key={rIdx} className="relative flex items-center">
                                  <div className="absolute -left-[14.5px] w-2.5 h-2.5 rounded-full bg-[#005EA2] border-2 border-white"></div>
                                  <span className="font-semibold text-slate-800">{r}</span>
                                </div>
                              ))}
                            </div>
                          </div>

                          {/* Manifest Anomalies identified by Sentry */}
                          <div className="space-y-2">
                            <h3 className="text-[11px] font-black uppercase text-red-600 font-mono border-b border-red-200 pb-1">Automated Flags & AI Discrepancies</h3>
                            
                            {selShip.manifest_anomalies.length > 0 ? (
                              <div className="space-y-2">
                                {selShip.manifest_anomalies.map((a, aIdx) => (
                                  <div key={aIdx} className="bg-red-50 p-2 border border-red-200 rounded text-red-950 text-[11px] leading-snug font-sans">
                                    {a}
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <p className="text-xs italic text-emerald-700 font-semibold bg-emerald-50 border border-emerald-200 p-2 rounded">
                                No statistical discrepancies identified under the loaded scanning profile rules.
                              </p>
                            )}
                          </div>

                        </div>
                      );
                    })() : (
                      <div className="flex-1 flex flex-col items-center justify-center p-6 text-center text-[#5C5C5C] italic font-sans text-xs">
                        <Anchor className="h-10 w-10 text-slate-300 mb-2" />
                        <p className="text-xs">Select any vessel cargo lot in the tracker directory on the left to pull physical terminal hold controls and manifest routing timelines.</p>
                      </div>
                    )}
                  </div>

                </div>
              )}

              {/* ========================================================= */}
              {/* VIEW 4: CORPORATE ENTITY RESOLUTION DIRECTORY */}
              {/* ========================================================= */}
              {activeTab === 'entities' && (
                <div className="flex-1 p-5 flex flex-col lg:flex-row gap-5 overflow-hidden w-full h-full font-sans">
                  
                  {/* Left Column: Entity Registry directory */}
                  <div className="flex-1 flex flex-col space-y-4 overflow-y-auto">
                    
                    <div className="bg-white p-4 border border-[#D0D7DE] rounded-sm flex justify-between items-center shadow-xs">
                      <div>
                        <h3 className="text-sm font-bold text-[#0B1F33] font-mono uppercase flex items-center space-x-2">
                          <Building className="w-4.5 h-4.5 text-[#005EA2]" />
                          <span>TRADE ENTITY RESOLUTION & ALIAS COHORT MATRIX</span>
                        </h3>
                        <p className="text-xs text-[#5C5C5C] mt-0.5 font-sans">Verify beneficial corporate owners, tax numbers, and shared billing networks to circumvent shell company layering.</p>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {entities.map((ent) => (
                        <div 
                          key={ent.entity_id}
                          onClick={() => setSelectedEntityId(ent.entity_id)}
                          className={`p-4 bg-white border rounded-sm transition-all hover:shadow cursor-pointer flex flex-col justify-between ${
                            selectedEntityId === ent.entity_id 
                              ? 'border-[#005EA2] border-2 shadow-xs' 
                              : ent.risk_level === 'Critical' ? 'border-[#D83933] border-l-4' : 'border-slate-200 border-l-4'
                          }`}
                        >
                          <div>
                            <div className="flex justify-between items-center">
                              <span className="text-[10px] font-bold font-mono text-[#5C5C5C] uppercase bg-slate-100 px-1.5 py-0.5 rounded animate-none">
                                {ent.entity_type}
                              </span>
                              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-sm uppercase ${
                                ent.risk_level === 'Critical' ? 'bg-red-100 text-[#D83933]' :
                                ent.risk_level === 'High' ? 'bg-amber-100 text-amber-800' :
                                'bg-green-100 text-[#2E8540]'
                              }`}>
                                {ent.risk_level} Risk
                              </span>
                            </div>

                            <h3 className="text-xs font-black text-[#0B1F33] mt-2 leading-tight">{ent.entity_name}</h3>
                            <p className="text-[10px] text-slate-500 font-mono uppercase mt-1">Country Registry: {ent.country}</p>
                          </div>

                          <div className="mt-4 pt-3 border-t border-slate-100 flex justify-between items-center font-mono text-[10px]">
                            <span className="text-[#5C5C5C]">Tax Registration ID: {ent.tax_id}</span>
                            <span className={`font-bold uppercase ${ent.watchlist_status.includes('Watchlist') ? 'text-red-500 font-extrabold' : 'text-slate-400'}`}>
                              {ent.watchlist_status}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>

                  </div>

                  {/* Right Column: Entity Detail Breakdown */}
                  <div className="w-full lg:w-[380px] bg-white border border-[#D0D7DE] rounded-sm flex flex-col overflow-hidden shrink-0 shadow-sm">
                    <div className="bg-[#112E51] text-white p-3 border-b border-slate-700 flex justify-between items-center shrink-0 font-mono text-xs font-bold">
                      <span>SECURE BENEFICIAL OWNER MATRIX</span>
                      <span className="text-cyan-400">COH-088</span>
                    </div>

                    {selectedEntityId ? (() => {
                      const selEnt = entities.find(e => e.entity_id === selectedEntityId);
                      if (!selEnt) return null;
                      return (
                        <div className="flex-1 p-4 overflow-y-auto space-y-4 font-sans text-xs">
                          
                          <div className="bg-slate-50 p-3 rounded border border-slate-200">
                            <span className="text-[9px] font-mono uppercase font-bold text-slate-400">{selEnt.entity_type} ID File</span>
                            <h2 className="text-base font-extrabold text-[#0B1F33] leading-tight mt-0.5">{selEnt.entity_name}</h2>
                            <span className="inline-block mt-2 bg-slate-200 text-slate-800 text-[10px] font-mono px-2 py-0.5 rounded">
                              Tax ID: {selEnt.tax_id}
                            </span>
                          </div>

                          {/* Sanctions status alert banner */}
                          <div className={`p-3 rounded border text-xs ${
                            selEnt.sanctions_status.includes('Blocked') ? 'bg-red-100 border-red-300 text-red-950 font-bold' : 'bg-slate-50 border-slate-200 text-slate-700'
                          }`}>
                            <span className="uppercase font-mono text-[9px] block text-slate-400">Sanction Registry Status:</span>
                            <span className="text-xs text-red-700 font-black tracking-wide uppercase mt-0.5 block">{selEnt.sanctions_status}</span>
                          </div>

                          {/* Basic registration data fields */}
                          <div className="space-y-2 text-xs">
                            <h4 className="font-extrabold font-mono text-[11px] text-[#112E51] border-b border-slate-100 pb-1 uppercase">Corporate Registration Details</h4>
                            <div className="space-y-2">
                              <div>
                                <span className="text-[#5C5C5C] block font-mono text-[9px] uppercase">Registered Address:</span>
                                <span className="font-bold text-[#1B1B1B] leading-normal">{selEnt.address}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-[#5C5C5C] font-mono text-[9px] uppercase">Contact Tel:</span>
                                <span className="font-bold text-[#1B1B1B] font-mono">{selEnt.phone}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-slate-400 font-mono text-[9px] uppercase">Compliance Stage:</span>
                                <span className="font-bold text-[#2E8540] font-mono uppercase">{selEnt.registration_status}</span>
                              </div>
                            </div>
                          </div>

                          {/* Corporate Structure and Beneficial Ownership */}
                          <div className="space-y-1.5 text-xs">
                            <h4 className="font-extrabold font-mono text-[11px] text-[#112E51] border-b border-slate-101 pb-1 uppercase">Corporate Architecture Notes</h4>
                            <div>
                              <span className="text-[#5C5C5C] block font-mono text-[9px] uppercase">Affiliations Matrix:</span>
                              <div className="flex flex-wrap gap-1 mt-1">
                                {selEnt.known_affiliations.map((a, aIdx) => (
                                  <span key={aIdx} className="bg-slate-100 border border-slate-200 px-1.5 py-0.5 rounded text-[10px] text-slate-800">
                                    {a}
                                  </span>
                                ))}
                              </div>
                            </div>
                            <div className="mt-2.5">
                              <span className="text-[#5C5C5C] block font-mono text-[9px] uppercase">Ownership Indicators:</span>
                              <p className="text-[11px] text-slate-800 leading-snug mt-1 italic pr-2">{selEnt.ownership_indicators}</p>
                            </div>
                          </div>

                          {/* Chronological Enforcement History */}
                          <div className="space-y-2 text-xs">
                            <h4 className="font-extrabold font-mono text-[11px] text-slate-900 border-b border-slate-100 pb-1 uppercase">Regulatory Seizures & Violations</h4>
                            <p className="text-[11px] text-slate-800 leading-snug bg-yellow-50/50 p-2.5 border border-amber-200 rounded">
                              {selEnt.enforcement_history}
                            </p>
                          </div>

                        </div>
                      );
                    })() : (
                      <div className="flex-1 flex flex-col items-center justify-center p-6 text-center text-[#5C5C5C] italic">
                        <Building className="h-10 w-10 text-slate-300 mb-2" />
                        <p className="text-xs">Select any trade exporter, broker, or consignee name directory on the left to resolve beneficial ownership details and sanctions risks.</p>
                      </div>
                    )}
                  </div>

                </div>
              )}

              {/* ========================================================= */}
              {/* VIEW 5: STATUTORY LEGAL REFERRALS DOSSIERS */}
              {/* ========================================================= */}
              {activeTab === 'referrals' && (
                <div className="flex-1 p-5 flex flex-col space-y-5 overflow-y-auto w-full font-sans text-xs">
                  
                  {/* Title Bar */}
                  <div className="bg-white p-4 border border-[#D0D7DE] rounded-sm flex flex-col sm:flex-row justify-between sm:items-center space-y-3 sm:space-y-0 shadow-xs">
                    <div>
                      <h3 className="text-sm font-bold text-[#0B1F33] font-mono uppercase flex items-center space-x-2">
                        <FileCheck className="w-4.5 h-4.5 text-[#005EA2]" />
                        <span>DHS STATUTORY LEGAL EVASION REFERRALS CABINET</span>
                      </h3>
                      <p className="text-xs text-[#5C5C5C] mt-0.5">Formal trade evasion dossiers built for immediate referral to the Department of Justice Trade Division for prosecution.</p>
                    </div>
                  </div>

                  {/* Referrals Matrix row */}
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
                    
                    {/* Left Panel: Active Referrals List */}
                    <div className="bg-white rounded-sm border border-[#D0D7DE] p-4 h-fit shadow-xs">
                      <h4 className="text-xs font-bold uppercase text-[#112E51] mb-3 font-mono border-b border-slate-100 pb-2">Active Evasion Referrals Dossier List</h4>
                      <div className="space-y-2">
                        {referrals.map((ref) => (
                          <div 
                            key={ref.referral_id}
                            onClick={() => setSelectedReferralId(ref.referral_id)}
                            className={`p-3 rounded-sm border cursor-pointer transition-colors ${
                              selectedReferralId === ref.referral_id 
                                ? 'bg-blue-50/40 border-[#005EA2] border-2 shadow-xs' 
                                : 'bg-slate-50 border-slate-200 hover:bg-slate-100'
                            }`}
                          >
                            <div className="flex justify-between text-[10px] font-mono leading-none">
                              <span className="font-bold text-[#005EA2]">{ref.referral_id}</span>
                              <span className="text-slate-500">{ref.generated_date}</span>
                            </div>
                            <h3 className="text-xs font-bold text-slate-800 leading-snug mt-1.5">
                              Case: {cases.find(c => c.case_id === ref.case_id)?.case_name || ref.case_id}
                            </h3>
                            <div className="flex justify-between items-center mt-3 pt-2 border-t border-dashed border-slate-200">
                              <span className="text-[10px] text-slate-500 font-mono">Status: {ref.package_status}</span>
                              <span className="text-[10px] bg-amber-100 text-amber-800 px-1.5 py-0.2 rounded font-mono font-bold leading-none uppercase animate-none">
                                {ref.approval_state}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Right Panel: Referral Dossier Details Inspector spanning 2 cols */}
                    <div className="lg:col-span-2 bg-white rounded-sm border border-[#D0D7DE] flex flex-col shadow-xs overflow-hidden">
                      {selectedReferralId ? (() => {
                        const selRef = referrals.find(r => r.referral_id === selectedReferralId);
                        if (!selRef) return null;
                        return (
                          <div>
                            {/* Header details */}
                            <div className="bg-[#112E51] text-white p-3.5 flex justify-between items-center font-mono text-xs font-bold">
                              <span>OFFICIAL DHS FORMAL EVASION RECORD: {selRef.referral_id}</span>
                              <span className="text-emerald-400 uppercase">{selRef.approval_state}</span>
                            </div>

                            <div className="p-5 space-y-4">
                              <div className="bg-slate-50 p-3 rounded-sm border border-slate-200">
                                <h3 className="text-[10px] font-bold font-mono text-slate-500 uppercase">SUBJECT TARGET COMPLIANCE ANOMALY NARRATIVE</h3>
                                <p className="text-xs font-bold text-[#0B1F33] mt-1">{cases.find(c => c.case_id === selRef.case_id)?.case_name}</p>
                              </div>

                              {/* Executive Summary segment */}
                              <div className="space-y-1 text-xs font-sans">
                                <h4 className="font-bold font-mono text-[#112E51] uppercase border-b border-slate-100 pb-1">I. STATUTORY EXECUTIVE SUMMARY</h4>
                                <p className="text-slate-800 leading-relaxed">{selRef.narrative.executive_summary}</p>
                              </div>

                              {/* Subject overview segment */}
                              <div className="space-y-1 text-xs font-sans">
                                <h4 className="font-bold font-mono text-[#112E51] uppercase border-b border-slate-100 pb-1">II. INVESTIGATIVE SUBJECT PROFILE</h4>
                                <p className="text-slate-800 leading-relaxed">{selRef.narrative.subject_overview}</p>
                              </div>

                              {/* Findings segments */}
                              <div className="space-y-1 text-xs font-sans">
                                <h4 className="font-bold font-mono text-[#112E51] uppercase border-b border-slate-101 pb-1">III. EVIDENCE TRACKINGS & ANALYSIS</h4>
                                <p className="text-slate-800 leading-relaxed whitespace-pre-line">{selRef.narrative.investigation_findings}</p>
                              </div>

                              {/* Applicable violations segment */}
                              <div className="space-y-1 text-xs">
                                <h4 className="font-bold font-mono text-red-600 uppercase border-b border-red-200 pb-1">IV. APPLICABLE STATUTORY FRAUD LIABILITIES</h4>
                                <p className="text-slate-800 leading-relaxed font-mono whitespace-pre-line bg-red-50/50 p-2 border border-red-200 rounded">{selRef.narrative.applicable_violations}</p>
                              </div>

                              {/* Action proposals */}
                              <div className="space-y-1 text-xs font-sans">
                                <h4 className="font-bold font-mono text-[#112E51] uppercase border-b border-slate-100 pb-1">V. CBP ENFORCEMENT RECOMMENDATIONS</h4>
                                <p className="text-slate-800 leading-relaxed whitespace-pre-line">{selRef.narrative.recommended_enforcement}</p>
                              </div>

                              {/* Action buttons */}
                              <div className="pt-4 border-t border-slate-101 flex justify-end space-x-3.5">
                                <button 
                                  onClick={() => {
                                    alert(`Exporter Dossier ${selRef.referral_id} exported as standard DHS statutory compliant referral document package.`);
                                  }}
                                  className="px-4 py-2 border border-[#D0D7DE] hover:bg-slate-50 text-slate-800 text-xs font-bold rounded flex items-center space-x-1.5 cursor-pointer"
                                >
                                  <Download className="w-3.5 h-3.5 text-slate-500" />
                                  <span>EXPORT DOSSIER PDF</span>
                                </button>
                                <button 
                                  onClick={() => {
                                    setReferrals(prev => prev.map(r => r.referral_id === selRef.referral_id ? { ...r, approval_state: "APPROVED & TRANSMITTED", package_status: "Executed" } : r));
                                    alert(`Dossier file ${selRef.referral_id} has been formally authorized and transmitted through Sentry-DOJ direct compliance ledger. Uncollected CVD/AD rates updated.`);
                                    
                                    // Inject threat alert
                                    const newThreatEvent: ThreatFeedEvent = {
                                      id: 'evt_' + Math.floor(Math.random() * 900 + 100),
                                      severity: 'Medium',
                                      title: 'Legal Referral Dispatched onto DOJ',
                                      description: `Casework Referral Bundle ${selRef.referral_id} officially approved and committed to Department of Justice legal prosecution channel by Lead Officer ${currentOfficer.name}.`,
                                      timestamp: 'Just now',
                                      confidence: 100
                                    };
                                    setThreatFeed(prev => [newThreatEvent, ...prev]);
                                  }}
                                  className="px-4 py-2 bg-[#005EA2] hover:bg-[#0076D6] text-white text-xs font-black uppercase rounded shadow-sm border border-transparent cursor-pointer flex items-center space-x-1"
                                >
                                  <Check className="w-3.5 h-3.5" />
                                  <span>TRANSMIT & ESGN FORWARD</span>
                                </button>
                              </div>

                            </div>
                          </div>
                        );
                      })() : (
                        <div className="py-20 text-center text-slate-400 font-sans italic text-xs">
                          Select any active legal evasion dockets on the left to pull DHS enforcement draft.
                        </div>
                      )}
                    </div>

                  </div>

                </div>
              )}

              {/* ========================================================= */}
              {/* VIEW 6: RESTRICTED EXPORTERS WATCHLIST */}
              {/* ========================================================= */}
              {activeTab === 'watchlists' && (
                <div className="flex-1 p-5 flex flex-col lg:flex-row gap-5 overflow-hidden w-full h-full font-sans">
                  
                  {/* Left Column: Form to Add Watchlisted Entity */}
                  <div className="w-full lg:w-[350px] bg-white border border-[#D0D7DE] p-4 rounded-sm shadow-sm shrink-0 flex flex-col">
                    <h4 className="text-xs font-bold uppercase text-[#112E51] mb-1 font-mono flex items-center space-x-1.5 border-b border-slate-100 pb-2">
                      <Plus className="w-4 h-4 text-[#005EA2]" />
                      <span>Watchlist Evasive Filer Entry</span>
                    </h4>
                    
                    <form onSubmit={handleAddNewWatchlistEntity} className="space-y-3.5 mt-3 text-xs flex-1">
                      <div>
                        <label className="block text-[10px] uppercase font-mono font-bold text-slate-500 mb-1">Company Entity Name</label>
                        <input 
                          type="text" 
                          required
                          value={newWatchlistName}
                          onChange={(e) => setNewWatchlistName(e.target.value)}
                          placeholder="e.g. Hong Kong Asia Transit Mills"
                          className="w-full bg-[#F7F9FC] border border-[#D0D7DE] p-2 text-xs focus:outline-none focus:border-[#005EA2] rounded-sm font-sans"
                        />
                      </div>

                      <div>
                        <label className="block text-[10px] uppercase font-mono font-bold text-slate-500 mb-1">Target Class Category</label>
                        <select 
                          value={newWatchlistType}
                          onChange={(e: any) => setNewWatchlistType(e.target.value)}
                          className="w-full bg-[#F7F9FC] border border-[#D0D7DE] p-2 text-xs focus:outline-none focus:border-[#005EA2] rounded-sm font-sans"
                        >
                          <option value="Exporter">Exporter / Assembly Yard</option>
                          <option value="Intermediary">Intermediary Broker</option>
                          <option value="Manufacturer">Raw Fabricator Mill</option>
                          <option value="Importer">US Consignee Filer</option>
                          <option value="Broker">Freight Forwarder</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-[10px] uppercase font-mono font-bold text-slate-500 mb-1">Registered Sovereign Territory</label>
                        <input 
                          type="text" 
                          required
                          value={newWatchlistCountry}
                          onChange={(e) => setNewWatchlistCountry(e.target.value)}
                          placeholder="e.g. Vietnam, China, Malaysia"
                          className="w-full bg-[#F7F9FC] border border-[#D0D7DE] p-2 text-xs focus:outline-none focus:border-[#005EA2] rounded-sm font-sans font-medium"
                        />
                      </div>

                      <div>
                        <label className="block text-[10px] uppercase font-mono font-bold text-slate-500 mb-1">HQ Commercial District Address</label>
                        <textarea 
                          rows={3}
                          value={newWatchlistAddress}
                          onChange={(e) => setNewWatchlistAddress(e.target.value)}
                          placeholder="Registered physical commercial address..."
                          className="w-full bg-[#F7F9FC] border border-[#D0D7DE] p-2 text-xs focus:outline-none focus:border-[#005EA2] rounded-sm resize-none font-sans"
                        />
                      </div>

                      <div className="pt-2">
                        <button
                          type="submit"
                          className="w-full py-2 bg-[#005EA2] hover:bg-[#0076D6] text-white text-xs font-extrabold uppercase rounded-sm cursor-pointer shadow-xs border border-transparent"
                        >
                          Submit Filer Flag
                        </button>
                      </div>
                    </form>
                  </div>

                  {/* Right Column: Watchlisted List */}
                  <div className="flex-1 bg-white border border-[#D0D7DE] rounded-sm flex flex-col overflow-hidden shadow-sm">
                    <div className="bg-[#112E51] text-white p-3.5 border-b border-slate-700 flex justify-between items-center text-xs font-mono font-bold shrink-0">
                      <span>AUTOMATED SENTRY SCREENING HIGH ALERT EXPORTERS WATCHLIST</span>
                      <span className="text-cyan-400">ACTIVE RED AGENTS</span>
                    </div>

                    <div className="flex-1 overflow-y-auto p-4 space-y-3.5">
                      {entities.filter(ent => ent.watchlist_status.includes('Watchlist') || ent.risk_level === 'Critical').map((ent) => (
                        <div key={ent.entity_id} className="p-4 bg-slate-50 border border-[#D0D7DE] rounded-sm hover:shadow transition-shadow flex flex-col justify-between">
                          <div className="flex justify-between items-start">
                            <div>
                              <div className="flex items-center space-x-2 text-[10px] font-mono font-bold">
                                <span className="bg-red-100 text-red-800 px-2 py-0.5 rounded leading-none uppercase">
                                  {ent.watchlist_status}
                                </span>
                                <span className="text-[#5C5C5C]">{ent.entity_type} ID: {ent.entity_id}</span>
                              </div>
                              <h3 className="text-xs font-black text-[#0B1F33] mt-2">{ent.entity_name}</h3>
                              <p className="text-[11px] text-[#5C5C5C] mt-1 font-mono">Location Flag: {ent.country} ({ent.address})</p>
                            </div>

                            <span className="px-2 py-1 bg-red-600 text-white font-black font-mono rounded text-xs leading-none uppercase shrink-0">
                              CRITICAL EVADER
                            </span>
                          </div>

                          <div className="mt-3.5 pt-3 border-t border-dashed border-slate-200 font-sans text-xs">
                            <span className="text-[10px] uppercase font-mono font-bold text-[#112E51] block label">Screening Evasion Intel Briefing:</span>
                            <p className="text-xs leading-relaxed text-slate-800 italic mt-0.5 font-semibold">{ent.enforcement_history}</p>
                          </div>
                        </div>
                      ))}
                    </div>

                  </div>

                </div>
              )}

              {/* ========================================================= */}
              {/* VIEW 7: AI SCORING PARAMETERS TUNING CONTROL */}
              {/* ========================================================= */}
              {activeTab === 'tuning' && (
                <div className="flex-1 p-5 flex flex-col space-y-5 overflow-y-auto w-full font-sans text-xs">
                  
                  <div className="bg-white p-4 border border-[#D0D7DE] rounded-sm shadow-xs flex justify-between items-center shrink-0">
                    <div>
                      <h3 className="text-sm font-bold text-[#0B1F33] font-mono uppercase flex items-center space-x-2">
                        <Sliders className="w-4.5 h-4.5 text-[#005EA2]" />
                        <span>SENTRY NEURAL AI SCORE WEIGHTS TUNING CONTROLS</span>
                      </h3>
                      <p className="text-xs text-[#5C5C5C] mt-0.5">Recalibrate scanning factors, adjust confidence multipliers, and configure automatic holds for unverified Vietnamese solar cargo lots.</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                    
                    {/* Weights Adjustment Board */}
                    <div className="bg-white p-4 rounded border border-[#D0D7DE] shadow-sm space-y-4">
                      <h4 className="text-xs font-extrabold uppercase text-[#112E51] font-mono border-b border-slate-100 pb-2">AI Algorithmic Parameter Weights (%)</h4>
                      
                      {/* Weight Sliders */}
                      <div className="space-y-4">
                        <div>
                          <div className="flex justify-between items-center text-xs font-bold text-[#1B1B1B] font-mono">
                            <span>TRANS-SHIPMENT PORT AIS DEVIATION WEIGHT</span>
                            <span className="text-[#005EA2] font-black">{aisSignalSpoofWeight}%</span>
                          </div>
                          <input 
                            type="range" min="0" max="100" 
                            value={aisSignalSpoofWeight}
                            onChange={(e) => setAisSignalSpoofWeight(parseInt(e.target.value))}
                            className="w-full h-1 bg-slate-250 rounded-lg appearance-none cursor-pointer accent-[#005EA2] mt-2" 
                          />
                          <span className="text-[10px] text-[#5C525C] font-mono mt-0.5 block">Penalty factor applied when vessel tracking AIS signals disconnect during ocean Swapping windows.</span>
                        </div>

                        <div>
                          <div className="flex justify-between items-center text-xs font-bold text-[#1B1B1B] font-mono">
                            <span>BILL OF LADING CARGO VOLUME DEVIATION COEFF</span>
                            <span className="text-[#005EA2] font-black">{weightDeviationWeight}%</span>
                          </div>
                          <input 
                            type="range" min="0" max="100" 
                            value={weightDeviationWeight}
                            onChange={(e) => setWeightDeviationWeight(parseInt(e.target.value))}
                            className="w-full h-1 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-[#005EA2] mt-2" 
                          />
                          <span className="text-[10px] text-[#5C5C5C] font-mono mt-0.5 block">Trigger factor correlating actual heavy shipping container physical weights against maximum limits.</span>
                        </div>

                        <div>
                          <div className="flex justify-between items-center text-xs font-bold text-[#1B1B1B] font-mono">
                            <span>CIRCULAR INVOICING NOMINEE LAYER COEFF</span>
                            <span className="text-[#005EA2] font-black">{circularInvoicingWeight}%</span>
                          </div>
                          <input 
                            type="range" min="0" max="100" 
                            value={circularInvoicingWeight}
                            onChange={(e) => setCircularInvoicingWeight(parseInt(e.target.value))}
                            className="w-full h-1 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-[#005EA2] mt-2" 
                          />
                          <span className="text-[10px] text-[#5C5C5C] font-mono mt-0.5 block">Penalty weight when billing trails bypass raw metal transaction centers via Shell nominee currencies.</span>
                        </div>

                        <div>
                          <div className="flex justify-between items-center text-xs font-bold text-[#1B1B1B] font-mono">
                            <span>XINJIANG LABOR REGIONAL EXPORT CORRELATION</span>
                            <span className="text-[#005EA2] font-black">{forcedLaborWeight}%</span>
                          </div>
                          <input 
                            type="range" min="0" max="100" 
                            value={forcedLaborWeight}
                            onChange={(e) => setForcedLaborWeight(parseInt(e.target.value))}
                            className="w-full h-1 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-[#005EA2] mt-2" 
                          />
                          <span className="text-[10px] text-[#5C5C5C] font-mono mt-0.5 block">Weight factor triggering immediate targeting holds whenever input wafers are tagged under regional restricted codes.</span>
                        </div>

                        <div>
                          <div className="flex justify-between items-center text-xs font-bold text-[#1B1B1B] font-mono">
                            <span>AUTOMATIC TARGET HOLD CONFIDENCE THRESHOLD</span>
                            <span className="text-[#005EA2] font-black">{systemAutoHoldThreshold}%</span>
                          </div>
                          <input 
                            type="range" min="0" max="100" 
                            value={systemAutoHoldThreshold}
                            onChange={(e) => setSystemAutoHoldThreshold(parseInt(e.target.value))}
                            className="w-full h-1 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-red-600 mt-2" 
                          />
                          <span className="text-[10px] text-red-650 font-mono mt-0.5 block font-bold">Containers with confidence match strictly higher than this threshold are manually queued for physical holds automatically.</span>
                        </div>
                      </div>
                    </div>

                    {/* Active Preset Rules */}
                    <div className="bg-white p-4 rounded border border-[#D0D7DE] shadow-sm flex flex-col justify-between font-sans">
                      <div>
                        <h4 className="text-xs font-extrabold uppercase text-[#112E51] font-mono border-b border-slate-100 pb-2">Active Screening Rule Toggles</h4>
                        
                        <div className="space-y-4 mt-4 text-xs text-[#1B1B1B]">
                          <label className="flex items-start space-x-3 cursor-pointer">
                            <input type="checkbox" defaultChecked className="mt-0.5 border-slate-300 rounded" />
                            <div>
                              <span className="font-bold text-slate-900 leading-tight block">W-121: MANDATORY HOLD UNVERIFIED RELEGATED IMPORTER</span>
                              <span className="text-[10px] text-slate-500 font-mono font-normal">Initiate dock hold immediately on unverified importers acting as regional transshipment custodians.</span>
                            </div>
                          </label>

                          <label className="flex items-start space-x-3 cursor-pointer">
                            <input type="checkbox" defaultChecked className="mt-0.5 border-slate-300 rounded" />
                            <div>
                              <span className="font-bold text-slate-900 leading-tight block">W-822: AIS SILENT COORDINATE PATTERN ANOMALY</span>
                              <span className="text-[10px] text-slate-500 font-mono font-normal">Target ocean shipments moving past known transloading swarms if marine AIS is silent for any 12+ hour period.</span>
                            </div>
                          </label>

                          <label className="flex items-start space-x-3 cursor-pointer">
                            <input type="checkbox" defaultChecked className="mt-0.5 border-slate-300 rounded" />
                            <div>
                              <span className="font-bold text-slate-900 leading-tight block">UFLPA-301: SILICON AD/CVD RECLASSIFICATION RATE</span>
                              <span className="text-[10px] text-[#D83933] font-mono font-bold">Apply standard Section 301 Anti-Dumping rate multiplier (244.5%) on verified Chinese-affiliations.</span>
                            </div>
                          </label>
                        </div>
                      </div>

                      <div className="pt-4 border-t border-slate-100">
                        <button
                          onClick={() => {
                            setCases(prev => prev.map(c => {
                              const fluctuation = Math.floor(Math.random() * 6 - 3);
                              return {
                                ...c,
                                risk_score: Math.min(100, Math.max(0, c.risk_score + fluctuation))
                              };
                            }));
                            alert("Sentry Algorithmic Weights successfully saved. Compliance database recalibrated. Case risk scores computed commensurate with new weight coordinates.");
                          }}
                          className="w-full py-2.5 bg-[#112E51] hover:bg-[#005EA2] text-white text-xs font-extrabold uppercase rounded-sm cursor-pointer shadow-xs border border-transparent"
                        >
                          Recalibrate System Profile Matrix
                        </button>
                      </div>
                    </div>

                  </div>

                </div>
              )}

              {/* INTEGRATED PERSISTENT RIGHT ASSISTANT PANE FOR QUICK CHAIR ASSESSMENTS */}
              <aside className="w-[300px] bg-slate-50 border-l border-[#D0D7DE] flex flex-col overflow-hidden shrink-0 hidden xl:flex">
                <div className="bg-[#112E51] text-white p-3 border-b border-slate-700 flex justify-between items-center shrink-0">
                  <span className="text-xs font-mono font-bold flex items-center space-x-1.5 text-cyan-400">
                    <Sparkles className="h-4 w-4" />
                    <span>CBP Intelligence Ask-AI Sentry</span>
                  </span>
                  <span className="text-[10px] font-mono text-slate-300">V.3.1</span>
                </div>

                {/* Chat Message Window */}
                <div ref={chatRef} className="flex-1 p-3 overflow-y-auto space-y-3 font-sans">
                  {chatMessages.map((m, mIdx) => (
                    <div key={mIdx} className={`flex flex-col text-[11px] leading-relaxed p-2.5 rounded-sm shadow-xs ${
                      m.role === 'user' 
                        ? 'bg-blue-50 text-slate-950 ml-6 border-l-2 border-blue-500' 
                        : 'bg-white text-[#1B1B1B] mr-6 border-l-2 border-cyan-400'
                    }`}>
                      <span className="font-bold font-mono tracking-wide text-[9px] text-[#5C5C5C] uppercase mb-0.5">
                        {m.role === 'user' ? 'Custom Filer Officer' : 'Sentry Analyst Intelligence Agent'}
                      </span>
                      <p className="whitespace-pre-line leading-relaxed font-sans">{m.text}</p>
                      {m.isDemo && (
                        <span className="text-[8px] mt-1.5 text-[#2E8540] italic font-mono block">
                          * Secure Local Grounding Mode Activated
                        </span>
                      )}
                    </div>
                  ))}
                  {chatLoading && (
                    <div className="bg-white mr-6 p-2 rounded-sm border-l-2 border-slate-300 animate-pulse text-[11px] space-y-1">
                      <span className="font-bold text-[9px] text-slate-400 block font-mono">AI THINKING...</span>
                      <div className="h-3 bg-slate-100 rounded w-1/3"></div>
                      <div className="h-3 bg-slate-100 rounded"></div>
                    </div>
                  )}
                </div>

                {/* Quick assistant chat bar inputs */}
                <div className="p-3 bg-white border-t border-[#D0D7DE] flex items-center space-x-2 shrink-0">
                  <input
                    type="text"
                    value={currentMessage}
                    onChange={(e) => setCurrentMessage(e.target.value)}
                    placeholder="Ask about Vina Solar, Silicon Evasion..."
                    onKeyDown={(e) => { if (e.key === 'Enter') handleSendChatMessage(); }}
                    className="flex-1 bg-slate-50 border border-[#D0D7DE] text-xs px-2 py-1.5 focus:outline-none focus:border-[#005EA2] rounded-sm min-w-0 font-sans"
                  />
                  <button 
                    onClick={handleSendChatMessage}
                    className="p-1.5 bg-[#005EA2] hover:bg-[#0076D6] text-white rounded cursor-pointer"
                  >
                    <Send className="w-3.5 h-3.5" />
                  </button>
                </div>
              </aside>

            </div>
          )}

          {/* ACTION SUMMARY STATIC RE-PASS BAR AT FOOTER PLATFORM */}
          <footer className="h-10 bg-[#112E51] text-white flex items-center px-4 justify-between shrink-0 font-sans z-10 shadow-inner">
            <div className="flex space-x-6 text-[10px] font-mono tracking-wide uppercase">
              <div className="flex items-center space-x-1.5">
                <span className="text-[#00BDE3] font-bold">Live Referral Readiness</span>
                <span className="text-white font-black">65% SYSTEM READY</span>
              </div>
              <div className="flex items-center space-x-1.5">
                <span className="text-[#00BDE3] font-bold">Federal Compliance Audit SLA Score</span>
                <span className="text-[#2E8540] font-black">98.8 - EXCELLENT</span>
              </div>
            </div>
            
            <div className="flex items-center space-x-2 text-[10px] font-mono">
              <span className="text-slate-300">Target System Status: Active Threat Protection Scan Enabled</span>
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
            </div>
          </footer>

        </main>

      </div>
    </div>
  );
}

// Helper colors for timeline
function purityColorResolver(idx: number): string {
  switch (idx) {
    case 0: return "border-[#2E8540] text-[#2E8540] bg-green-50";
    case 1: return "border-[#FFBE2E] text-slate-800 bg-amber-50";
    case 2: return "border-[#D83933] text-[#D83933] bg-red-50";
    default: return "border-[#005EA2] text-[#005EA2] bg-blue-50";
  }
}
