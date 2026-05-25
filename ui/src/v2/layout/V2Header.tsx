import React from 'react';
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
    <header className="h-16 bg-[#1A2F47] border-b border-[#0B1F33] px-6 flex items-center justify-between z-50 shadow-sm">
      {/* Left: CBP Branding */}
      <div className="flex items-center space-x-3">
        <div className="w-8 h-8 rounded-full bg-[#D83933] flex items-center justify-center text-white font-bold text-sm">
          CBP
        </div>
        <div className="flex flex-col">
          <span className="text-xs font-bold text-white tracking-wider">CBP SENTRY</span>
          <span className="text-xs text-gray-300 font-mono">Illegal Transshipment Platform</span>
        </div>
      </div>

      {/* Right: Officer Selector */}
      <div className="flex items-center space-x-3">
        <div className="flex flex-col text-right">
          <span className="text-xs font-bold text-white">{currentOfficer?.name || 'Officer'}</span>
          <span className="text-[10px] text-gray-400 font-mono">{currentOfficer?.badge.slice(-4)}</span>
        </div>
        <select
          value={currentOfficer?.id || ''}
          onChange={(e) => {
            const officer = officers.find(o => o.id === e.target.value);
            if (officer) onOfficerChange(officer);
          }}
          className="bg-[#0B1F33] border border-[#2A4060] text-white rounded px-2 py-1 text-xs font-mono focus:outline-none focus:border-[#00BDE3]"
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
