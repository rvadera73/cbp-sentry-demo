import React from 'react';

export interface TabConfig {
  id: string;
  label: string;
  badge?: number | string;
  badgeColor?: 'red' | 'blue' | 'green' | 'amber';
}

interface TabNavigationProps {
  tabs: TabConfig[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
  orientation?: 'horizontal' | 'vertical';
  statusText?: string;
  footerNote?: string;
  className?: string;
}

export function TabNavigation({
  tabs,
  activeTab,
  onTabChange,
  orientation = 'horizontal',
  statusText = 'Ready',
  footerNote = 'Chain of Custody: SECURE',
  className = '',
}: TabNavigationProps) {
  const getBadgeColor = (color?: string) => {
    switch (color) {
      case 'red':
        return 'bg-red-600 text-white';
      case 'blue':
        return 'bg-cyan-500 text-white';
      case 'green':
        return 'bg-green-600 text-white';
      case 'amber':
        return 'bg-amber-500 text-white';
      default:
        return 'bg-slate-400 text-white';
    }
  };

  // Horizontal tabs (left to right at the top)
  if (orientation === 'horizontal') {
    return (
      <div className={`bg-white border-b border-[#D0D7DE] shadow-sm ${className}`}>
        <nav className="flex items-center overflow-x-auto px-4">
          {tabs.map((tab, index) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => onTabChange(tab.id)}
              className={`px-4 py-3 text-xs font-bold whitespace-nowrap transition-all border-b-2 cursor-pointer rounded-t-sm ${
                activeTab === tab.id
                  ? 'bg-[#E8F0F7] text-[#005EA2] border-[#005EA2]'
                  : 'bg-[#F7F9FC] text-[#5C5C5C] border-[#D0D7DE] hover:bg-white hover:text-[#0B1F33]'
              }`}
            >
              <div className="flex items-center space-x-2">
                <span>{tab.label}</span>
                {tab.badge !== undefined && (
                  <span className={`${getBadgeColor(tab.badgeColor)} text-[9px] font-bold px-1.5 py-0.5 rounded`}>
                    {tab.badge}
                  </span>
                )}
              </div>
            </button>
          ))}
        </nav>
      </div>
    );
  }

  // Vertical tabs (top to bottom in left sidebar)
  return (
    <div className={`w-48 border-r border-[#D0D7DE] bg-white flex flex-col shadow-sm ${className}`}>
      {/* Tab Navigation */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => onTabChange(tab.id)}
            className={`w-full text-left px-4 py-2 rounded-sm text-xs font-bold transition-colors cursor-pointer ${
              activeTab === tab.id
                ? 'bg-[#005EA2] text-white'
                : 'text-[#0B1F33] hover:bg-slate-100'
            }`}
          >
            <div className="flex items-center justify-between">
              <span>{tab.label}</span>
              {tab.badge !== undefined && (
                <span className={`${getBadgeColor(tab.badgeColor)} text-[9px] font-bold px-1.5 rounded`}>
                  {tab.badge}
                </span>
              )}
            </div>
          </button>
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-[#D0D7DE] p-3 text-[9px] text-slate-400 font-mono">
        {statusText}
      </div>

      {/* Optional Footer Note */}
      {footerNote && (
        <div className="border-t border-[#D0D7DE] p-3 text-[9px] text-slate-500 font-mono italic">
          {footerNote}
        </div>
      )}
    </div>
  );
}
