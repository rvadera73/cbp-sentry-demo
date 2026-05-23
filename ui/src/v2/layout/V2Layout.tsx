import React, { useState } from 'react';
import V2Header from './V2Header';
import V2Sidebar from './V2Sidebar';
import V2ChatPanel from './V2ChatPanel';
import { CBPOfficer } from '../types/v2.types';
import { useV2Cases } from '../hooks/useV2Cases';

interface V2LayoutProps {
  children: React.ReactNode;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  officers?: CBPOfficer[];
  currentOfficer?: CBPOfficer | null;
  onOfficerChange?: (officer: CBPOfficer) => void;
}

const defaultOfficers: CBPOfficer[] = [
  {
    id: '1',
    name: 'Rav J. D.',
    badge: 'CBP-98522',
    role: 'Senior Intelligence Analyst',
    email: 'rav.jdpr@cbp.dhs.gov',
    shift: 'Eastern Shift Alpha',
    avatar: 'https://ui-avatars.com/api/?name=Rav+JD&bg=005EA2&color=fff',
  },
  {
    id: '2',
    name: 'Sarah Jenkins',
    badge: 'CBP-41092',
    role: 'Field Investigation Officer',
    email: 'sarah.jenkins@cbp.dhs.gov',
    shift: 'Gulf Coast Shift',
    avatar: 'https://ui-avatars.com/api/?name=Sarah+Jenkins&bg=005EA2&color=fff',
  },
  {
    id: '3',
    name: 'Marcus Chen',
    badge: 'CBP-32044',
    role: 'District Import Specialist',
    email: 'marcus.chen@cbp.dhs.gov',
    shift: 'Pacific Northwest Shift',
    avatar: 'https://ui-avatars.com/api/?name=Marcus+Chen&bg=005EA2&color=fff',
  },
];

export default function V2Layout({
  children,
  activeTab,
  setActiveTab,
  officers = defaultOfficers,
  currentOfficer: initialOfficer = defaultOfficers[0],
  onOfficerChange,
}: V2LayoutProps) {
  const [currentOfficer, setCurrentOfficer] = useState(initialOfficer);
  const [aiStatus, setAiStatus] = useState<'idle' | 'generating' | 'completed' | 'error'>('idle');
  const [isSidebarExpanded, setIsSidebarExpanded] = useState(true);
  const [isChatExpanded, setIsChatExpanded] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('sentry-chat-expanded') || 'true');
    } catch {
      return true;
    }
  });

  // Save chat preference to localStorage
  React.useEffect(() => {
    localStorage.setItem('sentry-chat-expanded', JSON.stringify(isChatExpanded));
  }, [isChatExpanded]);

  const { cases, loading } = useV2Cases();
  const activeCaseCount = cases.filter(c => c.case_status === 'Active').length;

  const handleOfficerChange = (officer: CBPOfficer) => {
    setCurrentOfficer(officer);
    onOfficerChange?.(officer);
  };

  return (
    <div className="flex flex-col h-screen w-full bg-[#F7F9FC] text-[#1B1B1B] font-sans overflow-hidden">
      {/* Header */}
      <V2Header
        currentOfficer={currentOfficer}
        officers={officers}
        onOfficerChange={handleOfficerChange}
        aiStatus={aiStatus}
      />

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <V2Sidebar
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          isExpanded={isSidebarExpanded}
          setIsExpanded={setIsSidebarExpanded}
          activeCaseCount={activeCaseCount}
        />

        {/* Page Content */}
        <main className="flex-1 flex overflow-hidden">
          <div className="flex-1 overflow-auto">
            {children}
          </div>

          {/* Chat Panel - visible at xl and above */}
          <div className="hidden xl:flex">
            <V2ChatPanel isExpanded={isChatExpanded} onToggleExpand={() => setIsChatExpanded(!isChatExpanded)} />
          </div>
        </main>
      </div>
    </div>
  );
}
