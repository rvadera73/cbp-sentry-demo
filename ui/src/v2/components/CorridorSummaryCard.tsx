import React from 'react';
import { AlertTriangle, TrendingDown, MapPin, Package } from 'lucide-react';
import { TYPOGRAPHY, DESIGN } from '../styles/typography';

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

  const hsChapters = JSON.parse(primaryHsChapters || '[]');

  return (
    <div className={`${DESIGN.bgWhite} border ${DESIGN.borderColor} rounded-sm p-4 shadow-sm`}>
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className={`${TYPOGRAPHY.sectionTitle} mb-1`}>{id}</h3>
          <p className={`${TYPOGRAPHY.sectionSubtitle}`}>{displayName}</p>
        </div>
        <span className={`px-3 py-1 rounded text-white text-xs font-bold ${getRiskLevelColor(riskLevel)}`}>
          {riskLevel}
        </span>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-4 gap-4 mb-4 p-3 bg-[#F7F9FC] rounded">
        <div>
          <div className={`${TYPOGRAPHY.label} mb-1`}>Shipments</div>
          <div className={`text-lg font-bold ${DESIGN.textDark}`}>{shipmentCount}</div>
        </div>
        <div>
          <div className={`${TYPOGRAPHY.label} mb-1`}>Avg Risk</div>
          <div className={`text-lg font-bold ${DESIGN.textDark}`}>{avgRiskScore?.toFixed(0)}/100</div>
        </div>
        <div>
          <div className={`${TYPOGRAPHY.label} mb-1`}>E9 Mismatch</div>
          <div className={`text-lg font-bold text-[#D83933]`}>{element9MismatchPct?.toFixed(1)}%</div>
        </div>
        <div>
          <div className={`${TYPOGRAPHY.label} mb-1`}>Shippers</div>
          <div className={`text-lg font-bold ${DESIGN.textDark}`}>{uniqueShippers}</div>
        </div>
      </div>

      {/* Risk Profile & HS Chapters */}
      <div className="space-y-3">
        {riskProfile && (
          <div>
            <div className={`${TYPOGRAPHY.label} mb-1`}>Risk Profile</div>
            <div className={`${TYPOGRAPHY.smallText} ${DESIGN.textDark}`}>{riskProfile}</div>
          </div>
        )}

        {hsChapters.length > 0 && (
          <div>
            <div className={`${TYPOGRAPHY.label} mb-1`}>Primary HS Chapters</div>
            <div className="flex flex-wrap gap-2">
              {hsChapters.map((hs: string, i: number) => (
                <span key={i} className="px-2 py-1 bg-orange-100 text-orange-800 rounded text-[9px] font-bold">
                  HS {hs}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
