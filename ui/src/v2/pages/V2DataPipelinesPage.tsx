import React, { useState, useCallback } from 'react';
import {
  Database, Wifi, File, Cpu, RefreshCw, ChevronDown, ChevronRight, AlertTriangle,
} from 'lucide-react';
import {
  Panel, SectionHeader, StatStrip, DataTable, Column, StatusPill,
  LoadingState, ErrorState,
} from '../../components/ui';
import {
  useDataPipelines, PipelineSource, PipelineMode, PipelineDatasetType, PipelineRun,
} from '../hooks/useDataPipelines';

// ---- helpers ---------------------------------------------------------------

/** Relative "time ago" from an ISO timestamp, honest about null/invalid input. */
function relativeTime(iso: string | null): string {
  if (!iso) return 'never';
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return '—';
  const diff = Date.now() - t;
  if (diff < 0) return 'just now';
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.floor(hr / 24);
  if (day < 30) return `${day}d ago`;
  const mo = Math.floor(day / 30);
  if (mo < 12) return `${mo}mo ago`;
  return `${Math.floor(mo / 12)}y ago`;
}

/** Compact number formatting, honest about null. */
function fmtNum(n: number | null | undefined): string {
  if (n == null) return '—';
  return n.toLocaleString();
}

const MODE_META: Record<PipelineMode, { label: string; icon: React.ReactNode; color: string }> = {
  online: { label: 'Online', icon: <Wifi className="w-3 h-3" />, color: '#15803D' },
  file: { label: 'File', icon: <File className="w-3 h-3" />, color: '#005EA2' },
  derived: { label: 'Derived', icon: <Cpu className="w-3 h-3" />, color: '#5C5C5C' },
};

/** Colored mode badge (matches ModelBadge style: bordered, uppercase, 10px). */
const ModeBadge: React.FC<{ mode: PipelineMode }> = ({ mode }) => {
  const m = MODE_META[mode] || MODE_META.file;
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm border border-[#D0D7DE] bg-slate-50 text-[10px] font-bold uppercase tracking-wide whitespace-nowrap"
      style={{ color: m.color }}
    >
      {m.icon}
      {m.label}
    </span>
  );
};

/** not_configured renders a muted pill; everything else uses the shared StatusPill palette. */
const PipelineStatusCell: React.FC<{ status: string }> = ({ status }) => {
  if (status === 'not_configured') {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide border bg-slate-100 text-slate-500 border-slate-300">
        not configured
      </span>
    );
  }
  if (status === 'seed') {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide border bg-amber-50 text-amber-700 border-amber-300" title="Real data present, but from a one-time / manual load — not on a live schedule yet">
        seed · not live
      </span>
    );
  }
  return <StatusPill status={status} />;
};

const DATASET_GROUPS: { type: PipelineDatasetType; label: string }[] = [
  { type: 'manifest', label: 'Manifest' },
  { type: 'isf', label: 'ISF' },
  { type: 'vessel', label: 'Vessel' },
  { type: 'entity', label: 'Entity' },
  { type: 'reference', label: 'Reference' },
];

// ---- run history sub-table -------------------------------------------------

const RUN_COLUMNS: Column[] = [
  { key: 'started_at', label: 'Started', render: (r: PipelineRun) => relativeTime(r.started_at) },
  { key: 'status', label: 'Status', render: (r: PipelineRun) => <StatusPill status={r.status} /> },
  { key: 'rows_in', label: 'Rows in', align: 'right', mono: true, render: (r: PipelineRun) => fmtNum(r.rows_in) },
  { key: 'rows_out', label: 'Rows out', align: 'right', mono: true, render: (r: PipelineRun) => fmtNum(r.rows_out) },
  { key: 'message', label: 'Message', render: (r: PipelineRun) => r.message || '—' },
];

// ---- expandable detail drawer ----------------------------------------------

const DetailDrawer: React.FC<{ source: PipelineSource; runs: PipelineRun[]; runsLoading: boolean }> = ({
  source, runs, runsLoading,
}) => (
  <div className="bg-slate-50 border-t border-[#D0D7DE] p-4 space-y-3">
    <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2 text-[11px]">
      <div>
        <div className="text-[10px] font-bold text-[#0B1F33] uppercase tracking-wide">Endpoint / Path</div>
        <div className="font-mono text-[#0B1F33] break-all mt-0.5">{source.endpoint_or_path || '—'}</div>
      </div>
      <div>
        <div className="text-[10px] font-bold text-[#0B1F33] uppercase tracking-wide">Schedule</div>
        <div className="text-[#0B1F33] mt-0.5">{source.schedule || 'Manual / on-demand'}</div>
      </div>
      <div className="md:col-span-2">
        <div className="text-[10px] font-bold text-[#0B1F33] uppercase tracking-wide">Detail</div>
        <div className="text-[#5C5C5C] mt-0.5">{source.detail || 'No additional detail.'}</div>
      </div>
    </div>

    {source.gap_note && (
      <div className="bg-amber-50 border border-amber-300 rounded-sm p-3 flex items-start gap-2">
        <AlertTriangle className="w-4 h-4 text-amber-700 flex-shrink-0 mt-0.5" />
        <div>
          <div className="text-[10px] font-bold text-amber-900 uppercase tracking-wide">Coverage gap</div>
          <p className="text-[11px] text-amber-800 mt-0.5">{source.gap_note}</p>
        </div>
      </div>
    )}

    <div>
      <div className="text-[10px] font-bold text-[#0B1F33] uppercase tracking-wide mb-1.5">Recent runs</div>
      {runsLoading ? (
        <p className="text-[11px] text-[#5C5C5C]">Loading run history…</p>
      ) : (
        <DataTable
          columns={RUN_COLUMNS}
          rows={runs}
          caption={`Recent runs for ${source.name}`}
          empty="No run history recorded"
        />
      )}
    </div>
  </div>
);

// ---- grouped source table --------------------------------------------------

interface GroupTableProps {
  label: string;
  sources: PipelineSource[];
  runningId: string | null;
  onRun: (id: string) => void;
  expandedId: string | null;
  onToggle: (id: string) => void;
  runsById: Record<string, PipelineRun[]>;
  runsLoadingId: string | null;
}

const GroupTable: React.FC<GroupTableProps> = ({
  label, sources, runningId, onRun, expandedId, onToggle, runsById, runsLoadingId,
}) => {
  if (sources.length === 0) return null;

  const columns: Column[] = [
    {
      key: 'name',
      label: 'Source',
      render: (s: PipelineSource) => (
        <button
          onClick={() => onToggle(s.id)}
          className="flex items-center gap-1.5 text-left font-semibold text-[#0B1F33] hover:text-[#005EA2] focus:outline-none focus:ring-2 focus:ring-[#005EA2] rounded-sm"
          aria-expanded={expandedId === s.id}
        >
          {expandedId === s.id ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
          {s.name}
        </button>
      ),
    },
    { key: 'mode', label: 'Mode', render: (s: PipelineSource) => <ModeBadge mode={s.mode} /> },
    { key: 'status', label: 'Status', render: (s: PipelineSource) => <PipelineStatusCell status={s.status} /> },
    { key: 'last_run_at', label: 'Last run', render: (s: PipelineSource) => relativeTime(s.last_run_at) },
    {
      key: 'rows',
      label: 'Rows (last / total)',
      align: 'right',
      mono: true,
      render: (s: PipelineSource) => `${fmtNum(s.rows_last_run)} / ${fmtNum(s.total_rows)}`,
    },
    { key: 'schedule', label: 'Cadence', render: (s: PipelineSource) => s.schedule || 'On-demand' },
    {
      key: 'run',
      label: 'Run now',
      align: 'center',
      render: (s: PipelineSource) => {
        const running = runningId === s.id;
        const disabled = running || runningId !== null || s.status === 'not_configured' || !s.enabled;
        return (
          <button
            onClick={() => onRun(s.id)}
            disabled={disabled}
            title={
              s.status === 'not_configured'
                ? 'Source not configured'
                : !s.enabled
                ? 'Source disabled'
                : 'Trigger a manual run'
            }
            className="inline-flex items-center gap-1 px-2 py-1 rounded-sm border border-[#005EA2] text-[10px] font-bold uppercase tracking-wide text-[#005EA2] hover:bg-[#005EA2] hover:text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent disabled:hover:text-[#005EA2] focus:outline-none focus:ring-2 focus:ring-[#005EA2]"
          >
            <RefreshCw className={`w-3 h-3 ${running ? 'animate-spin' : ''}`} />
            {running ? 'Running' : 'Run'}
          </button>
        );
      },
    },
  ];

  // DataTable renders one <tr> per row; to keep the expandable drawer we render
  // the table, then any expanded drawer immediately beneath, filtered to this group.
  const expandedSource = sources.find(s => s.id === expandedId);

  return (
    <Panel pad={false} className="overflow-hidden">
      <div className="px-4 py-2.5 border-b border-[#D0D7DE] flex items-center justify-between">
        <h4 className="text-[12px] font-bold text-[#0B1F33] uppercase tracking-wide">{label}</h4>
        <span className="text-[10px] text-[#5C5C5C] font-mono">{sources.length} source{sources.length === 1 ? '' : 's'}</span>
      </div>
      <div className="p-3">
        <DataTable columns={columns} rows={sources} caption={`${label} data sources`} />
      </div>
      {expandedSource && (
        <DetailDrawer
          source={expandedSource}
          runs={runsById[expandedSource.id] || []}
          runsLoading={runsLoadingId === expandedSource.id}
        />
      )}
    </Panel>
  );
};

// ---- page ------------------------------------------------------------------

export default function V2DataPipelinesPage() {
  const { sources, loading, error, refetch, runPipeline, getRuns } = useDataPipelines();

  const [runningId, setRunningId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [runsById, setRunsById] = useState<Record<string, PipelineRun[]>>({});
  const [runsLoadingId, setRunsLoadingId] = useState<string | null>(null);

  const handleRun = useCallback(
    async (id: string) => {
      setRunningId(id);
      await runPipeline(id);
      setRunningId(null);
      // If this source is expanded, refresh its run history too.
      if (expandedId === id) {
        setRunsLoadingId(id);
        const runs = await getRuns(id);
        setRunsById(prev => ({ ...prev, [id]: runs }));
        setRunsLoadingId(null);
      }
    },
    [runPipeline, getRuns, expandedId],
  );

  const handleToggle = useCallback(
    async (id: string) => {
      if (expandedId === id) {
        setExpandedId(null);
        return;
      }
      setExpandedId(id);
      if (!runsById[id]) {
        setRunsLoadingId(id);
        const runs = await getRuns(id);
        setRunsById(prev => ({ ...prev, [id]: runs }));
        setRunsLoadingId(null);
      }
    },
    [expandedId, runsById, getRuns],
  );

  const total = sources.length;
  const online = sources.filter(s => s.mode === 'online').length;
  const file = sources.filter(s => s.mode === 'file').length;
  const healthy = sources.filter(s => s.status === 'healthy').length;

  return (
    <div className="p-6 space-y-4 max-w-[1400px] mx-auto">
      <SectionHeader
        icon={<Database className="w-5 h-5" />}
        title="Data Pipelines"
        subtitle="Sources feeding the risk model — status, cadence, and manual refresh."
        action={
          <div className="flex items-center gap-3">
            {/* Mode legend */}
            <div className="hidden md:flex items-center gap-3 text-[10px] font-semibold uppercase tracking-wide">
              <span className="inline-flex items-center gap-1" style={{ color: MODE_META.online.color }}>
                <Wifi className="w-3 h-3" /> Online
              </span>
              <span className="inline-flex items-center gap-1" style={{ color: MODE_META.file.color }}>
                <File className="w-3 h-3" /> File
              </span>
              <span className="inline-flex items-center gap-1" style={{ color: MODE_META.derived.color }}>
                <Cpu className="w-3 h-3" /> Derived
              </span>
            </div>
            <button
              onClick={() => refetch()}
              disabled={loading}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-sm border border-[#D0D7DE] bg-white text-[10px] font-bold uppercase tracking-wide text-[#0B1F33] hover:bg-slate-50 disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-[#005EA2]"
            >
              <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} /> Refresh
            </button>
          </div>
        }
      />

      <StatStrip
        items={[
          { label: 'Total sources', value: total },
          { label: 'Online', value: online, color: MODE_META.online.color },
          { label: 'File', value: file, color: MODE_META.file.color },
          { label: 'Healthy', value: healthy, hint: total ? `of ${total}` : undefined, color: '#15803D' },
        ]}
      />

      {loading ? (
        <LoadingState label="Loading data pipelines…" />
      ) : error ? (
        <ErrorState title="Could not load data pipelines" detail={error} />
      ) : total === 0 ? (
        <Panel>
          <p className="text-[12px] text-[#5C5C5C] text-center py-8">
            No data sources are configured yet.
          </p>
        </Panel>
      ) : (
        <div className="space-y-4">
          {DATASET_GROUPS.map(g => (
            <GroupTable
              key={g.type}
              label={g.label}
              sources={sources.filter(s => s.dataset_type === g.type)}
              runningId={runningId}
              onRun={handleRun}
              expandedId={expandedId}
              onToggle={handleToggle}
              runsById={runsById}
              runsLoadingId={runsLoadingId}
            />
          ))}
        </div>
      )}
    </div>
  );
}
