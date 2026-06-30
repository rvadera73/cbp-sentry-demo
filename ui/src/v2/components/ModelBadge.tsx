import React from 'react';
import { Cpu } from 'lucide-react';
import { useProductionModel } from '../hooks/useProductionModel';

interface ModelBadgeProps {
  /** Extra classes for layout (e.g. margins) at the call site. */
  className?: string;
}

/**
 * Model provenance pill — shows which production model produced the scores on a
 * scoring tab, e.g. `Model: v1.1 · production` with a subtle `Gate 1 · 50%`
 * maturity hint when available. Matches the shared UI kit (navy #0B1F33, gray
 * #5C5C5C, accent #005EA2, uppercase 10/11px labels). Self-contained: fetches
 * the production model via `useProductionModel`.
 */
export default function ModelBadge({ className = '' }: ModelBadgeProps) {
  const { model } = useProductionModel();

  const gateHint =
    model.gate != null || model.maturity_pct != null
      ? [
          model.gate != null ? `Gate ${model.gate}` : null,
          model.maturity_pct != null ? `${model.maturity_pct}%` : null,
        ]
          .filter(Boolean)
          .join(' · ')
      : null;

  const title = [
    `Production model ${model.version}`,
    model.model_id ? `ID: ${model.model_id}` : null,
    gateHint,
  ]
    .filter(Boolean)
    .join(' | ');

  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm border border-[#D0D7DE] bg-slate-50 text-[10px] font-bold uppercase tracking-wide whitespace-nowrap ${className}`}
    >
      <Cpu className="w-3 h-3 flex-shrink-0 text-[#005EA2]" />
      <span className="text-[#5C5C5C]">Model:</span>
      <span className="font-mono normal-case text-[#0B1F33]">{model.version}</span>
      <span className="text-[#5C5C5C]">·</span>
      <span className="text-[#005EA2]">{model.status}</span>
      {gateHint && (
        <span className="ml-0.5 pl-1.5 border-l border-[#D0D7DE] font-normal text-[#5C5C5C] normal-case">
          {gateHint}
        </span>
      )}
    </span>
  );
}
