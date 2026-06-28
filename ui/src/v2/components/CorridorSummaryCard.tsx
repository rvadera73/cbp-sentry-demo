import React from 'react';
import { AlertTriangle, TrendingDown, MapPin, Package } from 'lucide-react';
import { TYPOGRAPHY, DESIGN } from '../styles/typography';

interface Corridor {
  id: string;
  display_name: string;
  risk_level: string;
}

interface CorridorSummaryCardProps {
  id: string;
  displayName: string;
  riskLevel: string;
  shipmentCount?: number;
  avgRiskScore?: number;
  element9MismatchPct?: number;
  uniqueShippers?: number;
  primaryHsChapters?: string;
  riskProfile?: string;
  corridors?: Corridor[];
  onCorridorChange?: (corridorId: string) => void;
}

export default function CorridorSummaryCard({
  id,
  displayName,
  riskLevel,
  shipmentCount = 0,
  avgRiskScore = 0,
  element9MismatchPct = 0,
  uniqueShippers = 0,
  primaryHsChapters = '[]',
  riskProfile = '',
  corridors = [],
  onCorridorChange,
}: CorridorSummaryCardProps) {
  const getRiskLevelColor = (level: string) => {
    switch (level) {
      case 'CRITICAL':
        return 'bg-[#D83933] text-white';
      case 'HIGH':
        return 'bg-orange-600 text-white';
      case 'MEDIUM':
        return 'bg-amber-600 text-white';
      case 'LOW':
        return 'bg-green-600 text-white';
      default:
        return 'bg-[#5C5C5C] text-white';
    }
  };

  const getRiskScoreColor = (score: number) => {
    if (score >= 80) return '#D83933';
    if (score >= 60) return '#E66A2C';
    return '#2E8B57';
  };

  const hsChapters = JSON.parse(primaryHsChapters || '[]');
  const riskScoreColor = getRiskScoreColor(avgRiskScore);

  return (
    <div className="bg-white border-b border-[#D0D7DE] flex items-center px-6 h-[72px] shadow-sm shrink-0 gap-0">
      {/* Col 1: Corridor Selector + Risk Badge */}
      <div className="border-r border-[#D0D7DE] pr-6 shrink-0 flex-1 min-w-[250px]">
        <div className="flex items-center gap-2 mb-1">
          <select
            value={id}
            onChange={(e) => onCorridorChange?.(e.target.value)}
            className="px-2 py-1 border border-[#D0D7DE] rounded text-xs font-bold font-mono bg-white text-[#0B1F33] focus:outline-none focus:border-[#005EA2] flex-1"
          >
            {corridors.map((c) => (
              <option key={c.id} value={c.id}>
                {c.id} — {c.display_name}
              </option>
            ))}
          </select>
          <span className={`px-1.5 py-0.5 text-[9px] font-bold rounded-sm shrink-0 ${getRiskLevelColor(riskLevel)}`}>
            {riskLevel}
          </span>
        </div>
      </div>

      {/* Col 2: Avg Risk Score with mini bar */}
      <div className="border-r border-[#D0D7DE] px-6 shrink-0">
        <div className="text-[10px] text-[#5C5C5C] font-semibold uppercase tracking-wide mb-0.5">Avg Risk</div>
        <div className="flex items-center gap-1.5">
          <span className="text-[15px] font-bold font-mono" style={{ color: riskScoreColor }}>
            {avgRiskScore.toFixed(0)}
          </span>
          <span className="text-[10px] text-[#5C5C5C]">/100</span>
          <div className="w-12 h-1.5 bg-gray-200 rounded-full overflow-hidden">
            <div className="h-1.5 rounded-full" style={{ width: `${Math.min(avgRiskScore, 100)}%`, backgroundColor: riskScoreColor }}></div>
          </div>
        </div>
      </div>

      {/* Col 3: Shipments */}
      <div className="border-r border-[#D0D7DE] px-6 shrink-0">
        <div className="text-[10px] text-[#5C5C5C] font-semibold uppercase tracking-wide mb-0.5">Shipments</div>
        <div className="text-[15px] font-bold font-mono text-[#0B1F33]">{shipmentCount}</div>
      </div>

      {/* Col 4: E9 Mismatch */}
      <div className="border-r border-[#D0D7DE] px-6 shrink-0">
        <div className="text-[10px] text-[#5C5C5C] font-semibold uppercase tracking-wide mb-0.5">E9 Mismatch</div>
        <div className={`text-[15px] font-bold font-mono ${element9MismatchPct > 20 ? 'text-[#D83933]' : 'text-[#0B1F33]'}`}>
          {element9MismatchPct.toFixed(1)}%
        </div>
      </div>

      {/* Col 5: Unique Shippers */}
      <div className="border-r border-[#D0D7DE] px-6 shrink-0">
        <div className="text-[10px] text-[#5C5C5C] font-semibold uppercase tracking-wide mb-0.5">Shippers</div>
        <div className="text-[15px] font-bold font-mono text-[#0B1F33]">{uniqueShippers}</div>
      </div>

      {/* Col 6: HS Chapters (flex-1 to fill remaining space) */}
      <div className="flex-1 min-w-0 px-6">
        <div className="text-[10px] text-[#5C5C5C] font-semibold uppercase tracking-wide mb-0.5">HS Chapters</div>
        <div className="flex gap-1 flex-wrap overflow-hidden max-h-[24px]">
          {hsChapters.slice(0, 4).map((hs: string, i: number) => (
            <span key={i} className="px-1.5 py-0.5 bg-orange-100 text-orange-800 rounded text-[8px] font-bold whitespace-nowrap">
              HS {hs}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
