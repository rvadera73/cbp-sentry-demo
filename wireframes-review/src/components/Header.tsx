import { Shield, Radio, Activity, Sparkles, LogOut, Clock } from 'lucide-react';
import { CBPOfficer } from '../types';

interface HeaderProps {
  currentOfficer: CBPOfficer;
  officers: CBPOfficer[];
  onOfficerChange: (officer: CBPOfficer) => void;
  environment: 'PROD' | 'UAT' | 'TRAINING';
  setEnvironment: (env: 'PROD' | 'UAT' | 'TRAINING') => void;
  aiStatus: 'idle' | 'generating' | 'completed' | 'error';
}

export default function Header({
  currentOfficer,
  officers,
  onOfficerChange,
  environment,
  setEnvironment,
  aiStatus
}: HeaderProps) {
  return (
    <header className="h-16 border-b border-[#1A365D]/30 bg-[#0B1F33] text-white flex items-center justify-between px-6 z-30 shrink-0 shadow-lg">
      {/* CBP Program Identity Group */}
      <div className="flex items-center space-x-3">
        <div className="bg-[#0076D6] p-1.5 rounded border border-blue-400/40 shadow-inner flex items-center justify-center">
          <Shield className="h-6 w-6 text-white" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <span className="font-mono font-bold tracking-wider text-xs bg-red-600 px-1.5 py-0.5 rounded leading-none">
              CBP
            </span>
            <span className="font-sans font-extrabold tracking-tight text-sm uppercase">
              Sentry-Trade
            </span>
          </div>
          <p className="text-[10px] text-slate-400 font-mono tracking-wide">
            Illegal Transshipment Targeting Platform
          </p>
        </div>
      </div>

      {/* Environment Select / Operational Status */}
      <div className="hidden md:flex items-center space-x-4">
        {/* Environment Badge Select */}
        <div className="flex bg-[#112E51] border border-slate-700 p-0.5 rounded text-xs">
          {(['PROD', 'UAT', 'TRAINING'] as const).map((env) => (
            <button
              key={env}
              onClick={() => setEnvironment(env)}
              className={`px-3 py-1 rounded font-mono transition-all uppercase ${
                environment === env
                  ? 'bg-[#0076D6] text-white font-bold shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {env}
            </button>
          ))}
        </div>

        {/* Live Fed Status Indicator */}
        <div className="bg-[#102A43] border border-slate-800 rounded px-3 py-1 flex items-center space-x-2 text-xs font-mono text-emerald-400">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span>NET ORBIT LIVE</span>
        </div>

        {/* AI Processing Status */}
        <div className="bg-[#102A43] border border-slate-800 rounded px-3 py-1 flex items-center space-x-2 text-xs font-mono">
          <Sparkles className={`h-3.5 w-3.5 ${aiStatus === 'generating' ? 'animate-spin text-cyan-400' : 'text-slate-400'}`} />
          <span className="text-slate-300">
            AI ENG:{' '}
            <span className={aiStatus === 'generating' ? 'text-cyan-400 font-bold' : 'text-slate-400'}>
              {aiStatus.toUpperCase()}
            </span>
          </span>
        </div>
      </div>

      {/* Active User Identity Section */}
      <div className="flex items-center space-x-4">
        <div className="flex flex-col text-right hidden sm:flex">
          <span className="text-xs font-sans font-semibold text-slate-100">{currentOfficer.name}</span>
          <span className="text-[10px] font-mono text-slate-400 tracking-wider">
            {currentOfficer.badge} | {currentOfficer.shift}
          </span>
        </div>

        {/* User Identity Switching Select */}
        <div className="relative">
          <select
            value={currentOfficer.id}
            onChange={(e) => {
              const matched = officers.find((o) => o.id === e.target.value);
              if (matched) onOfficerChange(matched);
            }}
            className="bg-[#112E51] border border-slate-700 text-xs rounded px-2.5 py-1.5 focus:outline-none focus:border-blue-400 text-slate-200 font-mono font-medium max-w-[150px] cursor-pointer"
          >
            {officers.map((off) => (
              <option key={off.id} value={off.id} className="bg-[#0B1F33] text-slate-100">
                {off.name} ({off.badge.slice(-4)})
              </option>
            ))}
          </select>
        </div>

        {/* CBP Status Badge Circle */}
        <img
          src={currentOfficer.avatar}
          alt={currentOfficer.name}
          className="h-9 w-9 rounded-full object-cover border border-[#0076D6]"
        />
      </div>
    </header>
  );
}
