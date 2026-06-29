/**
 * EntityNetworkEvidencePanel — Track T-Experience (F6)
 *
 * Renders a NetworkEvidenceBlockV4 (CT-6) for the referral's primary party:
 * risk-colored entity nodes + the "why-connected" edges between them (shared
 * address / shared identifier / ownership / officer / EAPA anchor), each with
 * its confidence. Built entirely from the shared ui.tsx kit (Panel /
 * SectionHeader / StatusPill) so it matches the Risk Model design language.
 *
 * Data source: referral §3-10 `network_evidence` (services/api
 * referral_comprehensive_v2._network_evidence_block / entity_edges.edges_for).
 */
import React from 'react';
import { Share2, ArrowRight } from 'lucide-react';
import { Panel, SectionHeader, StatusPill } from '../../components/ui';
import type { NetworkEvidenceBlockV4, NetworkEvidenceEdgeV4 } from '../types/v4Contracts';

// ─── Edge-type presentation ──────────────────────────────────────────────────

const EDGE_LABEL: Record<string, string> = {
  shared_address: 'Shared address',
  shared_identifier: 'Shared identifier',
  ownership: 'Ownership',
  officer: 'Officer',
  forwarder: 'Forwarder',
  eapa_anchor: 'EAPA anchor',
  same_as: 'Same entity',
};

/** Higher-risk edge types read hotter (ownership/EAPA anchor > shared address). */
function edgeRisk(type: string): number {
  switch (type) {
    case 'eapa_anchor':
      return 90;
    case 'ownership':
    case 'same_as':
      return 70;
    case 'officer':
    case 'shared_identifier':
      return 55;
    case 'forwarder':
    case 'shared_address':
    default:
      return 35;
  }
}

function riskColors(score: number) {
  if (score >= 80) return { bg: '#FEE2E2', text: '#991B1B', border: '#FCA5A5' };
  if (score >= 60) return { bg: '#FEF3C7', text: '#92400E', border: '#FCD34D' };
  if (score >= 40) return { bg: '#FFF7ED', text: '#9A3412', border: '#FDBA74' };
  return { bg: '#DCFCE7', text: '#166534', border: '#86EFAC' };
}

function shortId(id: string): string {
  if (!id) return '—';
  // "{DATA_SOURCE}:{RECORD_ID}" → show source + truncated record id.
  const [src, ...rest] = id.split(':');
  const rec = rest.join(':');
  if (!rec) return id.length > 28 ? `${id.slice(0, 26)}…` : id;
  const recShort = rec.length > 16 ? `${rec.slice(0, 14)}…` : rec;
  return `${src}:${recShort}`;
}

function confidencePct(c: number): string {
  return `${Math.round(Math.max(0, Math.min(1, c)) * 100)}%`;
}

// ─── Node chip (risk-colored) ─────────────────────────────────────────────────

function NodeChip({ id, root }: { id: string; root: boolean }) {
  const c = root ? riskColors(85) : riskColors(45);
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold font-mono border whitespace-nowrap"
      style={{ background: c.bg, color: c.text, borderColor: c.border }}
      title={id}
    >
      {root ? '★ ' : ''}{shortId(id)}
    </span>
  );
}

// ─── Main ─────────────────────────────────────────────────────────────────────

export default function EntityNetworkEvidencePanel({ block }: { block?: NetworkEvidenceBlockV4 | null }) {
  if (!block) return null;

  const edges: NetworkEvidenceEdgeV4[] = Array.isArray(block.edges) ? block.edges : [];
  const reach = block.cross_corridor_reach ?? 0;
  const delta = block.resolved_vs_explicit_delta ?? 0;

  return (
    <Panel className="mt-4">
      <SectionHeader
        icon={<Share2 size={14} />}
        title="Entity Network Evidence (§3-5a)"
        subtitle="Resolved-entity graph — why the primary party is connected to other entities"
      />

      {/* Reach summary strip */}
      <div className="flex flex-wrap items-center gap-2 mb-3 text-[11px]">
        <span className="text-slate-600">Primary party:</span>
        <NodeChip id={block.root_entity_id} root />
        <span className="ml-auto inline-flex items-center gap-1 text-[10px] text-slate-600">
          <span className="font-bold text-[#0B1F33]">{edges.length}</span> linked edge(s)
        </span>
        <span className="inline-flex items-center gap-1 text-[10px] text-slate-600">
          Cross-corridor reach: <span className="font-bold text-[#0B1F33]">{reach}</span>
        </span>
        <span className="inline-flex items-center gap-1 text-[10px] text-slate-600">
          Resolution delta: <span className="font-bold text-[#0B1F33]">+{delta}</span>
        </span>
      </div>

      {edges.length === 0 ? (
        <div className="bg-slate-50 border border-[#D0D7DE] rounded-sm p-4 text-center text-[11px] text-[#5C5C5C]">
          No network edges resolved for this party in the CORD entity graph.
        </div>
      ) : (
        <div className="space-y-2">
          {edges.map((e, i) => {
            const risk = edgeRisk(e.type);
            const c = riskColors(risk);
            return (
              <div
                key={i}
                className="border-l-4 rounded-sm p-3 bg-white"
                style={{ borderColor: c.border }}
              >
                <div className="flex flex-wrap items-center gap-2 mb-1.5">
                  <NodeChip id={e.src} root={e.src === block.root_entity_id} />
                  <ArrowRight size={12} className="text-slate-400 flex-shrink-0" />
                  <NodeChip id={e.dst} root={e.dst === block.root_entity_id} />
                  <span
                    className="text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded border ml-1"
                    style={{ background: c.bg, color: c.text, borderColor: c.border }}
                  >
                    {EDGE_LABEL[e.type] || e.type}
                  </span>
                  <span className="ml-auto inline-flex items-center gap-1">
                    <StatusPill status={e.confidence >= 0.7 ? 'high' : e.confidence >= 0.4 ? 'medium' : 'low'} />
                    <span className="text-[10px] font-mono text-slate-600">{confidencePct(e.confidence)}</span>
                  </span>
                </div>
                <p className="text-[11px] text-slate-700 leading-relaxed">{e.evidence}</p>
              </div>
            );
          })}
        </div>
      )}
    </Panel>
  );
}
