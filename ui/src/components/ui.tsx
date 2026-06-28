/**
 * Shared, accessible presentational primitives for the Risk Model Management
 * tabs. One card/table/header system so every tab matches the Active
 * Investigation design language (navy headings, mono values, dense cards,
 * #005EA2 table headers) instead of the old numbered-circle/wizard look.
 *
 * Accessibility: semantic <section>/<table>, <th scope>, sr-only captions,
 * status conveyed by text (not color alone), visible focus rings, readable
 * 11px body / 10px captions (no sub-10px text).
 */
import React from 'react'

const ALIGN: Record<string, string> = { left: 'text-left', center: 'text-center', right: 'text-right' }

export const SectionHeader: React.FC<{
  title: string
  subtitle?: string
  icon?: React.ReactNode
  action?: React.ReactNode
}> = ({ title, subtitle, icon, action }) => (
  <div className="flex items-end justify-between mb-3 pb-2 border-b border-[#D0D7DE]">
    <div className="flex items-center gap-2 min-w-0">
      {icon && <span className="text-[#005EA2] flex-shrink-0">{icon}</span>}
      <div className="min-w-0">
        <h3 className="text-sm font-bold text-[#0B1F33] uppercase tracking-wide truncate">{title}</h3>
        {subtitle && <p className="text-[11px] text-[#5C5C5C] mt-0.5">{subtitle}</p>}
      </div>
    </div>
    {action && <div className="flex-shrink-0">{action}</div>}
  </div>
)

export const Panel: React.FC<{ children: React.ReactNode; className?: string; pad?: boolean; style?: React.CSSProperties }> = ({ children, className = '', pad = true, style }) => (
  <section style={style} className={`bg-white border border-[#D0D7DE] rounded-sm ${pad ? 'p-4' : ''} ${className}`}>{children}</section>
)

/** Shared underline tab bar (matches the Active Investigation / Risk Model tabs). */
export const Tabs: React.FC<{
  tabs: { id: string; label: string; icon?: React.ReactNode }[]
  active: string
  onChange: (id: string) => void
}> = ({ tabs, active, onChange }) => (
  <div className="flex flex-wrap border-b border-[#D0D7DE]" role="tablist">
    {tabs.map(t => (
      <button
        key={t.id}
        role="tab"
        aria-selected={active === t.id}
        onClick={() => onChange(t.id)}
        className={`px-4 py-2 text-[11px] font-semibold border-b-2 transition-colors flex items-center gap-1.5 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-[#005EA2] ${
          active === t.id ? 'border-[#005EA2] text-[#005EA2]' : 'border-transparent text-slate-600 hover:text-[#0B1F33]'
        }`}
      >
        {t.icon}{t.label}
      </button>
    ))}
  </div>
)

export const StatCard: React.FC<{
  label: string
  value: React.ReactNode
  hint?: string
  color?: string
}> = ({ label, value, hint, color = '#0B1F33' }) => (
  <div className="bg-slate-50 border border-[#D0D7DE] rounded-sm p-3">
    <div className="text-[10px] font-bold text-[#0B1F33] uppercase tracking-wide">{label}</div>
    <div className="text-2xl font-black font-mono mt-1" style={{ color }}>{value}</div>
    {hint && <p className="text-[10px] text-[#5C5C5C] mt-1">{hint}</p>}
  </div>
)

/**
 * Analytics KPI strip — one bordered container with equal, divider-separated
 * columns. Use for the metric header at the top of a tab; always aligns
 * regardless of count and reads as a single dashboard header (vs separate boxes).
 */
export const StatStrip: React.FC<{
  items: { label: string; value: React.ReactNode; hint?: string; color?: string }[]
}> = ({ items }) => (
  <div className="flex flex-wrap bg-white border border-[#D0D7DE] rounded-sm overflow-hidden">
    {items.map((it, i) => (
      <div key={i} className="flex-1 basis-[120px] px-3 py-2 border-l border-[#D0D7DE] first:border-l-0">
        <div className="text-[10px] font-semibold uppercase tracking-wide text-[#5C5C5C] truncate">{it.label}</div>
        <div className="flex items-baseline gap-1.5 mt-0.5">
          <span className="text-[15px] leading-none font-bold font-mono tabular-nums" style={{ color: it.color || '#0B1F33' }}>
            {it.value}
          </span>
          {it.hint && <span className="text-[10px] text-[#5C5C5C] truncate">{it.hint}</span>}
        </div>
      </div>
    ))}
  </div>
)

/** Dense factor/dimension row — colored mono score + bar (matches the Active
 * Investigation 7-factor risk breakdown). Use for risk dimensions, factors, etc. */
export const ScoreBar: React.FC<{ label: string; sublabel?: string; score: number; max?: number; color?: string }> = ({ label, sublabel, score, max = 100, color }) => {
  const c = color || (score >= 80 ? '#D83933' : score >= 60 ? '#C7791B' : score >= 40 ? '#B8860B' : '#15803D')
  return (
    <div className="flex items-center justify-between gap-3 py-1.5 border-b border-slate-100 last:border-0">
      <div className="min-w-0">
        <div className="text-[11px] font-bold text-[#0B1F33] truncate">{label}</div>
        {sublabel && <div className="text-[10px] text-[#5C5C5C] truncate">{sublabel}</div>}
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        <div className="w-24 h-1.5 bg-slate-200 rounded-sm overflow-hidden">
          <div className="h-full" style={{ width: `${Math.min((score / max) * 100, 100)}%`, background: c }} />
        </div>
        <span className="text-[13px] font-black font-mono w-9 text-right" style={{ color: c }}>{score}</span>
      </div>
    </div>
  )
}

const PILL: Record<string, string> = {
  production: 'bg-green-100 text-green-800 border-green-300',
  candidate: 'bg-blue-100 text-blue-800 border-blue-300',
  staging: 'bg-amber-100 text-amber-800 border-amber-300',
  registered: 'bg-slate-100 text-slate-700 border-slate-300',
  deprecated: 'bg-red-100 text-red-800 border-red-300',
  met: 'bg-green-100 text-green-800 border-green-300',
  passed: 'bg-green-100 text-green-800 border-green-300',
  blocked: 'bg-amber-100 text-amber-900 border-amber-300',
  critical: 'bg-red-100 text-red-800 border-red-300',
  high: 'bg-orange-100 text-orange-800 border-orange-300',
  medium: 'bg-amber-100 text-amber-900 border-amber-300',
  low: 'bg-green-100 text-green-800 border-green-300',
  warning: 'bg-amber-100 text-amber-900 border-amber-300',
  normal: 'bg-green-100 text-green-800 border-green-300',
  completed: 'bg-green-100 text-green-800 border-green-300',
  running: 'bg-blue-100 text-blue-800 border-blue-300',
  failed: 'bg-red-100 text-red-800 border-red-300',
  queued: 'bg-slate-100 text-slate-700 border-slate-300',
  flagged: 'bg-red-100 text-red-800 border-red-300',
  clear: 'bg-green-100 text-green-800 border-green-300',
  pending: 'bg-amber-100 text-amber-900 border-amber-300',
}

export const StatusPill: React.FC<{ status: string }> = ({ status }) => {
  const cls = PILL[(status || '').toLowerCase()] || 'bg-slate-100 text-slate-700 border-slate-300'
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide border ${cls}`}>
      {status}
    </span>
  )
}

export interface Column {
  key: string
  label: string
  align?: 'left' | 'center' | 'right'
  mono?: boolean
  render?: (row: any) => React.ReactNode
}

export const DataTable: React.FC<{ columns: Column[]; rows: any[]; caption: string; empty?: string }> = ({
  columns, rows, caption, empty = 'No records',
}) => (
  <div className="overflow-x-auto border border-[#D0D7DE] rounded-sm">
    <table className="w-full text-[11px] border-collapse">
      <caption className="sr-only">{caption}</caption>
      <thead>
        <tr className="bg-[#005EA2] text-white">
          {columns.map(c => (
            <th key={c.key} scope="col" className={`px-3 py-2 font-semibold whitespace-nowrap ${ALIGN[c.align || 'left']}`}>
              {c.label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.length === 0 ? (
          <tr><td colSpan={columns.length} className="px-3 py-4 text-center text-[#5C5C5C]">{empty}</td></tr>
        ) : rows.map((row, i) => (
          <tr key={i} className={i % 2 ? 'bg-white' : 'bg-slate-50'}>
            {columns.map(c => (
              <td key={c.key} className={`px-3 py-2 text-[#0B1F33] ${ALIGN[c.align || 'left']} ${c.mono ? 'font-mono' : ''}`}>
                {c.render ? c.render(row) : (row[c.key] ?? '—')}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  </div>
)

export const LoadingState: React.FC<{ label?: string }> = ({ label = 'Loading…' }) => (
  <div className="flex items-center justify-center h-72" role="status" aria-live="polite">
    <div className="text-center">
      <div className="w-7 h-7 border-2 border-[#005EA2] border-t-transparent rounded-full animate-spin mx-auto" />
      <p className="mt-2 text-[12px] text-[#5C5C5C]">{label}</p>
    </div>
  </div>
)

export const ErrorState: React.FC<{ title: string; detail?: string | null }> = ({ title, detail }) => (
  <div className="bg-red-50 border border-red-200 rounded-sm p-4 flex items-start gap-3" role="alert">
    <span className="text-red-600 font-bold flex-shrink-0">!</span>
    <div>
      <p className="text-[13px] font-semibold text-red-900">{title}</p>
      {detail && <p className="text-[12px] text-red-700 mt-1">{detail}</p>}
    </div>
  </div>
)
