import React from 'react';
import { Sparkles } from 'lucide-react';
import { CBPOfficer } from '../types/v2.types';

interface V2HeaderProps {
  currentOfficer: CBPOfficer | null;
  officers: CBPOfficer[];
  onOfficerChange: (officer: CBPOfficer) => void;
  aiStatus: 'idle' | 'generating' | 'completed' | 'error';
}

export default function V2Header({
  currentOfficer,
  officers,
  onOfficerChange,
  aiStatus,
}: V2HeaderProps) {
  return (
    <header className="h-16 bg-white border-b border-[#D0D7DE] px-6 flex items-center justify-between z-50 shadow-sm">
      {/* Left: CBP Branding */}
      <div className="flex items-center space-x-3">
        <div className="w-8 h-8 rounded-full bg-[#D83933] flex items-center justify-center text-white font-bold text-sm">
          CBP
        </div>
        <div className="flex flex-col">
          <span className="text-xs font-bold text-[#D83933] tracking-wider">CBP SENTRY</span>
          <span className="text-xs text-[#5C5C5C] font-mono">Illegal Transshipment Platform</span>
        </div>
      </div>

      {/* Center: AI Status */}
      <div className="flex items-center space-x-1.5">
        <Sparkles
          className={`h-4 w-4 ${
            aiStatus === 'generating'
              ? 'text-cyan-500 animate-spin'
              : aiStatus === 'error'
                ? 'text-red-500'
                : 'text-gray-400'
          }`}
        />
        <span className="text-xs font-mono font-bold uppercase text-gray-600 hidden lg:inline">
          {aiStatus.toUpperCase()}
        </span>
      </div>

      {/* Right: Officer Selector */}
      <div className="flex items-center space-x-3">
        <div className="flex flex-col text-right">
          <span className="text-xs font-bold text-[#0B1F33]">{currentOfficer?.name || 'Officer'}</span>
          <span className="text-[10px] text-[#5C5C5C] font-mono">{currentOfficer?.badge.slice(-4)}</span>
        </div>
        <select
          value={currentOfficer?.id || ''}
          onChange={(e) => {
            const officer = officers.find(o => o.id === e.target.value);
            if (officer) onOfficerChange(officer);
          }}
          className="bg-[#F7F9FC] border border-[#D0D7DE] rounded px-2 py-1 text-xs font-mono focus:outline-none focus:border-[#005EA2]"
        >
          {officers.map((o) => (
            <option key={o.id} value={o.id}>
              {o.name}
            </option>
          ))}
        </select>
        {currentOfficer?.avatar && (
          <img
            src={currentOfficer.avatar}
            alt={currentOfficer.name}
            className="w-8 h-8 rounded border-2 border-[#005EA2]"
          />
        )}
      </div>
    </header>
  );
}
