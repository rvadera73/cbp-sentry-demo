import { 
  FolderLock, 
  Layers, 
  Activity, 
  Anchor, 
  Network, 
  FileCheck, 
  Search, 
  Sliders, 
  BookOpen, 
  ChevronLeft, 
  ChevronRight,
  ShieldCheck
} from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  isExpanded: boolean;
  setIsExpanded: (exp: boolean) => void;
  activeCaseCount: number;
  referralPendingCount: number;
}

export default function Sidebar({
  activeTab,
  setActiveTab,
  isExpanded,
  setIsExpanded,
  activeCaseCount,
  referralPendingCount
}: SidebarProps) {
  const primaryMenu = [
    { id: 'dashboard', label: 'Command Center', icon: Layers, badge: null },
    { id: 'investigations', label: 'Active Investigations', icon: FolderLock, badge: activeCaseCount },
    { id: 'shipments', label: 'Shipment Intelligence', icon: Anchor, badge: null },
    { id: 'entities', label: 'Entity Resolution', icon: Network, badge: null },
    { id: 'referrals', label: 'Referral Packages', icon: FileCheck, badge: referralPendingCount > 0 ? referralPendingCount : null },
  ];

  const adminMenu = [
    { id: 'watchlists', label: 'AI Watchlists', icon: BookOpen, badge: null },
    { id: 'tuning', label: 'AI Tuning & Rules', icon: Sliders, badge: null },
  ];

  return (
    <aside 
      className={`bg-[#112E51] border-r border-[#1A365D]/30 transition-all duration-300 relative flex flex-col justify-between ${
        isExpanded ? 'w-64' : 'w-18'
      }`}
    >
      <div className="flex flex-col pt-4">
        {/* Toggle Button */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="absolute -right-3 top-5 bg-[#0076D6] hover:bg-[#005EA2] text-white p-1 rounded-full border border-blue-400/40 cursor-pointer shadow-md z-40 transition-colors"
          title={isExpanded ? "Collapse Sidebar" : "Expand Sidebar"}
        >
          {isExpanded ? <ChevronLeft className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        </button>

        {/* Section Header */}
        {isExpanded && (
          <div className="px-5 mb-3">
            <span className="text-[10px] font-mono tracking-widest text-slate-400 uppercase font-semibold">
              Operational Portals
            </span>
          </div>
        )}

        {/* Primary Navigation Menu */}
        <nav className="space-y-1.5 px-3">
          {primaryMenu.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center justify-between p-3 rounded-md transition-all group font-sans text-xs font-semibold ${
                  isActive 
                    ? 'bg-[#0076D6] text-white shadow-md' 
                    : 'text-slate-300 hover:bg-[#1A365D]/40 hover:text-white'
                }`}
              >
                <div className="flex items-center space-x-3.5">
                  <Icon className={`h-4.5 w-4.5 transition-colors ${isActive ? 'text-white' : 'text-slate-400 group-hover:text-blue-400'}`} />
                  {isExpanded && <span className="text-left select-none">{item.label}</span>}
                </div>
                {item.badge !== null && isExpanded && (
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono ${isActive ? 'bg-[#0B1F33] text-cyan-400 font-bold' : 'bg-[#D83933] text-white font-bold'}`}>
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Intelligence System Config */}
        <div className="mt-8">
          {isExpanded && (
            <div className="px-5 mb-3">
              <span className="text-[10px] font-mono tracking-widest text-slate-400 uppercase font-semibold">
                Intelligence Control
              </span>
            </div>
          )}
          <nav className="space-y-1.5 px-3">
            {adminMenu.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`w-full flex items-center p-3 rounded-md transition-all group font-sans text-xs font-semibold ${
                    isActive 
                      ? 'bg-[#0076D6] text-white' 
                      : 'text-slate-300 hover:bg-[#1A365D]/40 hover:text-white'
                  }`}
                >
                  <Icon className={`h-4.5 w-4.5 mr-3.5 transition-colors ${isActive ? 'text-white' : 'text-slate-400 group-hover:text-blue-400'}`} />
                  {isExpanded && <span className="text-left select-none">{item.label}</span>}
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Agency Verification Block */}
      <div className="p-4 border-t border-[#1A365D]/30 bg-[#0B1F33]/20">
        <div className="flex items-center space-x-3">
          <ShieldCheck className="h-5 w-5 text-blue-400 shrink-0" />
          {isExpanded && (
            <div className="overflow-hidden">
              <p className="text-[10px] font-bold font-mono text-emerald-400 uppercase tracking-widest leading-tight">
                SECURE TR-ST
              </p>
              <p className="text-[9px] font-mono text-slate-400 truncate leading-tight">
                CBP Central Node Alpha
              </p>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
