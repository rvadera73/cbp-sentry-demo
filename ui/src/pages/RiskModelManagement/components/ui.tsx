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

export const Panel: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className = '' }) => (
  <section className={`bg-white border border-[#D0D7DE] rounded-sm p-4 ${className}`}>{children}</section>
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
  warning: 'bg-amber-100 text-amber-900 border-amber-300',
  normal: 'bg-green-100 text-green-800 border-green-300',
  completed: 'bg-green-100 text-green-800 border-green-300',
  running: 'bg-blue-100 text-blue-800 border-blue-300',
  failed: 'bg-red-100 text-red-800 border-red-300',
  queued: 'bg-slate-100 text-slate-700 border-slate-300',
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
