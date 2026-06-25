import React from 'react';
import { AlertTriangle, Info, CheckCircle } from 'lucide-react';

interface MaturityBadgeProps {
  maturity?: number | null;
  modelVersion?: string | null;
  scoredAt?: string | null;
  /** When set, shows "Estimated: X → Model: Y" discrepancy note */
  seedScore?: number | null;
  /** 'inline' = compact pill next to score, 'tooltip' = icon only with hover, 'banner' = full row */
  variant?: 'inline' | 'tooltip' | 'banner';
  className?: string;
}

function getMaturityConfig(maturity: number) {
  if (maturity < 30) {
    return {
      label: `${maturity}% · LOW CONFIDENCE`,
      shortLabel: `${maturity}%`,
      color: '#B50909',
      bg: '#FFF3F2',
      border: '#F4A3A0',
      Icon: AlertTriangle,
      description: `Model maturity is ${maturity}%. Scores are indicative — verify all findings manually.`,
    };
  }
  if (maturity < 70) {
    return {
      label: `${maturity}% · MODERATE CONFIDENCE`,
      shortLabel: `${maturity}%`,
      color: '#8B5A00',
      bg: '#FFF8E1',
      border: '#FFD54F',
      Icon: Info,
      description: `Model maturity is ${maturity}%. Scores are useful but human review recommended for edge cases.`,
    };
  }
  return {
    label: `${maturity}% · HIGH CONFIDENCE`,
    shortLabel: `${maturity}%`,
    color: '#0B5225',
    bg: '#E8F5E9',
    border: '#A5D6A7',
    Icon: CheckCircle,
    description: `Model maturity is ${maturity}%. Scores are reliable for operational use.`,
  };
}

export default function MaturityBadge({
  maturity,
  modelVersion,
  scoredAt,
  seedScore,
  variant = 'inline',
  className = '',
}: MaturityBadgeProps) {
  if (!maturity) return null;

  const cfg = getMaturityConfig(maturity);
  const { Icon } = cfg;

  const scoredDate = scoredAt
    ? new Date(scoredAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    : null;

  const discrepancyNote =
    seedScore != null
      ? `Estimated score: ${seedScore.toFixed(0)} → Model score (${maturity}% maturity): shown above`
      : null;

  const title = [
    cfg.description,
    modelVersion ? `Model: ${modelVersion}` : null,
    scoredDate ? `Scored: ${scoredDate}` : null,
    discrepancyNote,
  ]
    .filter(Boolean)
    .join(' | ');

  if (variant === 'tooltip') {
    return (
      <span title={title} className={`cursor-help ${className}`}>
        <Icon
          style={{ color: cfg.color }}
          className="inline-block w-3 h-3"
        />
      </span>
    );
  }

  if (variant === 'banner') {
    return (
      <div
        title={title}
        className={`flex items-center gap-1.5 px-2 py-1 rounded text-[10px] font-semibold border ${className}`}
        style={{ background: cfg.bg, borderColor: cfg.border, color: cfg.color }}
      >
        <Icon className="w-3 h-3 flex-shrink-0" />
        <span>{cfg.label}</span>
        {modelVersion && (
          <span className="font-mono font-normal opacity-70 ml-1">{modelVersion}</span>
        )}
        {seedScore != null && (
          <span className="font-normal opacity-60 ml-2">est. {seedScore.toFixed(0)}</span>
        )}
      </div>
    );
  }

  // inline (default) — compact pill
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[8px] font-bold border ${className}`}
      style={{ background: cfg.bg, borderColor: cfg.border, color: cfg.color }}
    >
      <Icon className="w-2.5 h-2.5 flex-shrink-0" />
      {cfg.shortLabel}
    </span>
  );
}
