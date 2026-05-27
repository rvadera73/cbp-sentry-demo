import React from 'react';
import {
  Layers, FolderLock, Anchor, Network, BookOpen, Sliders, ChevronRight,
  ChevronLeft, ShieldCheck
} from 'lucide-react';

interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  badge?: number;
  section: 'primary' | 'admin';
}

interface V2SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  isExpanded: boolean;
  setIsExpanded: (expanded: boolean) => void;
  activeCaseCount: number;
}

const navItems: NavItem[] = [
  { id: 'dashboard', label: 'Command Center', icon: <Layers className="w-5 h-5" />, section: 'primary' },
  { id: 'investigations', label: 'Active Investigations', icon: <FolderLock className="w-5 h-5" />, section: 'primary' },
  { id: 'shipments', label: 'Shipment Intelligence', icon: <Anchor className="w-5 h-5" />, section: 'primary' },
  { id: 'entities', label: 'Entity Resolution', icon: <Network className="w-5 h-5" />, section: 'primary' },
  { id: 'ai-tuning', label: 'AI Tuning & Rules', icon: <Sliders className="w-5 h-5" />, section: 'admin' },
];

export default function V2Sidebar({
  activeTab,
  setActiveTab,
  isExpanded,
  setIsExpanded,
  activeCaseCount,
}: V2SidebarProps) {
  const primaryItems = navItems.filter(item => item.section === 'primary');
  const adminItems = navItems.filter(item => item.section === 'admin');

  // Enhance items with badge counts
  const enhancedPrimary = primaryItems.map(item => {
    if (item.id === 'investigations') return { ...item, badge: activeCaseCount };
    return item;
  });

  return (
    <aside
      className={`bg-[#0B1F33] text-white flex flex-col shrink-0 transition-all duration-300 ${
        isExpanded ? 'w-64' : 'w-20'
      } relative border-r border-slate-700 z-40`}
    >
      {/* Primary Navigation */}
      <nav className="flex-1 py-6 space-y-2 px-3 overflow-y-auto">
        <div className="space-y-2">
          {enhancedPrimary.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded transition-all text-sm font-semibold group ${
                activeTab === item.id
                  ? 'bg-[#0076D6] text-white'
                  : 'text-slate-300 hover:bg-[#1A365D]/40 hover:text-white'
              }`}
              title={!isExpanded ? item.label : undefined}
            >
              <div className="flex items-center space-x-2">
                {item.icon}
                {isExpanded && <span>{item.label}</span>}
              </div>
              {isExpanded && item.badge ? (
                <span className={`px-2 py-0.5 text-xs font-bold rounded-full ${
                  activeTab === item.id ? 'bg-[#0B1F33] text-cyan-400' : 'bg-[#D83933] text-white'
                }`}>
                  {item.badge}
                </span>
              ) : null}
            </button>
          ))}
        </div>

        {/* Admin Section */}
        {isExpanded && (
          <>
            <div className="pt-4 mt-4 border-t border-slate-600">
              <span className="text-xs font-bold text-slate-400 uppercase px-3 block mb-2">Intelligence Control</span>
              <div className="space-y-2">
                {adminItems.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => setActiveTab(item.id)}
                    className={`w-full flex items-center space-x-2 px-3 py-2.5 rounded transition-all text-sm font-semibold ${
                      activeTab === item.id
                        ? 'bg-[#0076D6] text-white'
                        : 'text-slate-300 hover:bg-[#1A365D]/40 hover:text-white'
                    }`}
                  >
                    {item.icon}
                    <span>{item.label}</span>
                  </button>
                ))}
              </div>
            </div>
          </>
        )}
      </nav>

      {/* Collapse/Expand Button */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="absolute -right-3 top-5 bg-[#0076D6] hover:bg-[#0B5ED7] text-white rounded-full p-1 shadow-md transition-all"
        title={isExpanded ? 'Collapse' : 'Expand'}
      >
        {isExpanded ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
      </button>

      {/* Footer */}
      {isExpanded && (
        <div className="p-4 border-t border-slate-600 bg-slate-900/50">
          <div className="flex items-center space-x-2 text-xs text-slate-400">
            <ShieldCheck className="w-4 h-4" />
            <span className="font-mono font-bold">SECURE TR-ST</span>
          </div>
          <span className="text-[10px] text-slate-500 font-mono">CBP Central Node Alpha</span>
        </div>
      )}
    </aside>
  );
}
