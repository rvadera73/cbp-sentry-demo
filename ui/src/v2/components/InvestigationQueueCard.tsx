import React from 'react';
import { ChevronRight, AlertTriangle, CheckCircle, Clock } from 'lucide-react';
import { LineChart, Line, ResponsiveContainer } from 'recharts';
import MaturityBadge from './MaturityBadge';

interface InvestigationQueueCardProps {
  case_id: string;
  case_name: string;
  target_entity: string;
  priority: string;
  risk_score: number;
  calculated_risk_score?: number;
  model_maturity?: number;
  model_version?: string;
  risk_score_calculated_at?: string;
  case_status: 'New' | 'In Progress' | 'Review' | 'Closed';
  opened_date: string;
  days_open: number;
  risk_trend?: Array<{ day: number; score: number }>;
  onClick?: () => void;
}

function getRiskColor(score: number): string {
  if (score >= 80) return '#D83933';
  if (score >= 50) return '#FF9500';
  return '#22c55e';
}

function getStatusIcon(status: string) {
  switch (status) {
    case 'New':
      return <AlertTriangle className="w-4 h-4 text-[#0076D6]" />;
    case 'In Progress':
      return <Clock className="w-4 h-4 text-orange-600" />;
    case 'Review':
      return <AlertTriangle className="w-4 h-4 text-[#D83933]" />;
    case 'Closed':
      return <CheckCircle className="w-4 h-4 text-green-600" />;
    default:
      return null;
  }
}

const FIXTURE_SPARKLINE = [
  { day: 1, score: 45 },
  { day: 2, score: 52 },
  { day: 3, score: 48 },
  { day: 4, score: 58 },
  { day: 5, score: 62 },
  { day: 6, score: 65 },
];

export default function InvestigationQueueCard({
  case_id,
  case_name,
  target_entity,
  priority,
  risk_score,
  calculated_risk_score,
  model_maturity,
  model_version,
  risk_score_calculated_at,
  case_status,
  opened_date,
  days_open,
  risk_trend = FIXTURE_SPARKLINE,
  onClick,
}: InvestigationQueueCardProps) {
  // Canonical display score — prefer engine score, fall back to seeded score
  const displayScore = Math.round(calculated_risk_score ?? risk_score);
  return (
    <div
      onClick={onClick}
      className="p-3 bg-white border border-[#D0D7DE] rounded-sm hover:shadow-md transition-all cursor-pointer group"
    >
      {/* Header: Case ID + Status Badge */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1">
          <div className="text-[9px] font-bold text-[#5C5C5C] font-mono uppercase">{case_id}</div>
          <div className="text-[10px] font-bold text-[#0B1F33] line-clamp-2 mt-0.5">{case_name}</div>
        </div>
        <div className="flex items-center gap-1 ml-2">
          {getStatusIcon(case_status)}
          <span className="text-[8px] font-bold text-[#5C5C5C] whitespace-nowrap">{case_status}</span>
        </div>
      </div>

      {/* Entity + Priority */}
      <div className="text-[8px] text-[#5C5C5C] line-clamp-1 mb-2">
        {target_entity.split('/')[0]}
        {priority === 'Critical' && <span className="ml-1 font-bold text-[#D83933]">⚠️ CRITICAL</span>}
      </div>

      {/* Risk Bar + Score + Maturity Badge */}
      <div className="flex items-center gap-1.5 mb-2">
        <div
          style={{
            flex: 1,
            height: '6px',
            background: getRiskColor(displayScore),
            borderRadius: '2px',
          }}
        />
        <span className="text-[9px] font-bold text-[#5C5C5C] min-w-fit">{displayScore}%</span>
        <MaturityBadge
          maturity={model_maturity}
          modelVersion={model_version}
          scoredAt={risk_score_calculated_at}
          variant="tooltip"
        />
      </div>

      {/* Sparkline Chart */}
      <div style={{ height: '24px', marginBottom: '8px', marginRight: '-8px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={risk_trend} margin={{ top: 2, right: 0, left: 0, bottom: 2 }}>
            <Line type="monotone" dataKey="score" stroke={getRiskColor(displayScore)} dot={false} isAnimationActive={false} strokeWidth={1.5} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Footer: Days Open + Action */}
      <div className="flex items-center justify-between text-[8px] text-[#5C5C5C]">
        <span>Opened {days_open}d ago</span>
        <ChevronRight className="w-3 h-3 text-[#0076D6] opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>
    </div>
  );
}
