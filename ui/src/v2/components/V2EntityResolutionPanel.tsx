/**
 * Entity intelligence panel — real CORD data, driven by the selected entity.
 * Three tabs, mirroring the Shipment Intelligence pattern (consolidated primary
 * view first, single content pane):
 *   Risk Profile (default) — factor breakdown + Assessment & Recommendation.
 *   Network               — resolved relationship graph + related / similar entities.
 *   Intelligence          — sanctions/EAPA/OFAC, aliases, ownership chain, locations.
 */
import React, { useState } from 'react';
import { Network, Shield, TrendingUp, AlertTriangle, MapPin } from 'lucide-react';
import { Tabs, Panel, SectionHeader, StatusPill, DataTable, ScoreBar, Column } from '../../components/ui';
import { EntityDetail, entityRisk } from '../services/cordApi';
import EntityNetworkGraph from './EntityNetworkGraph';
import EntityAssessment from './EntityAssessment';

type TabId = 'risk' | 'network' | 'intelligence';

export interface RelatedItem { id: string; name: string; sub: string; score: number | null; real: boolean }

const partyName = (r: any) => r.name || r.entity_name || r.NAME || r.entity_id || r.id || '—';
const partyId = (r: any) => r.entity_id || r.id || r.related_entity_id || '';
const prettyRel = (t?: string) => (t || 'related').replace(/_/g, ' ').toLowerCase();
const riskDot = (s: number) => (s >= 80 ? 'bg-[#D83933]' : s >= 60 ? 'bg-orange-600' : s >= 40 ? 'bg-amber-600' : 'bg-green-600');

export default function V2EntityResolutionPanel({
  detail,
  onOpenEntity,
  scoreBreakdown,
  related = [],
  usingResolved = false,
}: {
  detail: EntityDetail;
  onOpenEntity?: (id: string) => void;
  scoreBreakdown?: any | null;
  related?: RelatedItem[];
  usingResolved?: boolean;
}) {
  const [tab, setTab] = useState<TabId>('risk');
  const e = detail.entity || {};
  const raw = e.raw_data || {};
  const heur = entityRisk(detail);
  // Prefer the real factor-attributed score; fall back to the heuristic.
  const score = scoreBreakdown ? Math.round(scoreBreakdown.final_score) : heur.score;
  const tier = scoreBreakdown ? String(scoreBreakdown.tier) : heur.tier;
  const signals = heur.signals;
  const realComponents: any[] = scoreBreakdown
    ? (scoreBreakdown.components || []).filter((c: any) => (c.weighted_result || 0) > 0)
        .sort((a: any, b: any) => (b.weighted_result || 0) - (a.weighted_result || 0))
    : [];

  // Aliases (NAMES / NAME_LIST), addresses, sanctions program — defensively parsed.
  const nameObjs = raw.NAMES || raw.NAME_LIST || [];
  const aliases = (Array.isArray(nameObjs) ? nameObjs : [])
    .map((n: any) => n.NAME_ORG || n.NAME_FULL || n.NAME_LAST || '')
    .filter((n: string) => n && n !== e.name);
  const addrObjs = raw.ADDRESSES || [];
  const addresses = (Array.isArray(addrObjs) ? addrObjs : [])
    .map((a: any) => a.ADDR_FULL || [a.ADDR_LINE1, a.ADDR_CITY, a.ADDR_STATE, a.ADDR_COUNTRY].filter(Boolean).join(', '))
    .filter(Boolean);
  const sdnProgram = raw.SDN_PROGRAM || raw.OFAC_PROGRAM;
  const parties = detail.parties || [];
  const chain = detail.chain || [];

  // Network graph: root entity + each resolved party as nodes, directed edge
  // (root -> party) carrying the relationship type.
  const rootId = e.entity_id || e.id || 'root';
  const networkEntities = parties.length
    ? [
        {
          entity_id: rootId,
          name: e.name || rootId,
          entity_type: e.entity_type || 'entity',
          country: e.country || '',
          risk_score: score,
          relationships: parties
            .map((p: any) => ({
              target_id: partyId(p) || '',
              type: prettyRel(p.relationship_type || p.relationship || p.type),
              confidence: p.confidence ?? 0.5,
            }))
            .filter((r) => r.target_id && r.target_id !== rootId),
        },
        ...parties
          .filter((p: any) => partyId(p) && partyId(p) !== rootId)
          .map((p: any) => ({
            entity_id: partyId(p),
            name: partyName(p),
            entity_type: p.entity_type || p.data_source || 'related',
            country: p.country || '',
            risk_score: Math.round((p.confidence ?? 0.5) * 100),
          })),
      ]
    : [];

  const tabs = [
    { id: 'risk', label: 'Risk Profile', icon: <TrendingUp className="w-3.5 h-3.5" /> },
    { id: 'network', label: 'Network', icon: <Network className="w-3.5 h-3.5" /> },
    { id: 'intelligence', label: 'Intelligence', icon: <Shield className="w-3.5 h-3.5" /> },
  ];

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 pt-2 bg-white">
        <Tabs tabs={tabs} active={tab} onChange={(id) => setTab(id as TabId)} />
      </div>
      <div className="flex-1 overflow-y-auto p-4 bg-[#F7F9FC] space-y-4">
        {/* ---- RISK PROFILE (default): factor breakdown + assessment ---- */}
        {tab === 'risk' && (
          <>
            <Panel>
              <SectionHeader
                title="Risk Profile"
                subtitle={`${scoreBreakdown ? 'Model risk score' : 'Resolved risk'} ${score}/100 (${tier})`}
                icon={<TrendingUp className="w-4 h-4" />}
                action={<StatusPill status={tier.toLowerCase()} />}
              />
              {realComponents.length ? (
                <div>
                  {realComponents.map((c, i) => (
                    <ScoreBar
                      key={i}
                      label={c.component}
                      sublabel={`${c.factor} · weight ${Math.round(c.weight)}%`}
                      score={Math.round((c.score || 0) * 10)}
                    />
                  ))}
                  <p className="mt-2 text-[10px] text-[#5C5C5C]">Factor-attributed entity risk score (provisional weights — pinned at calibration).</p>
                </div>
              ) : signals.length ? (
                <ul className="space-y-1.5">
                  {signals.map((s, i) => (
                    <li key={i} className="flex gap-1.5 text-[12px] text-[#0B1F33]">
                      <AlertTriangle className="w-3.5 h-3.5 text-[#D83933] flex-shrink-0 mt-0.5" />{s}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-[12px] text-[#5C5C5C]">No adverse risk signals resolved for this entity.</p>
              )}
            </Panel>
            {/* Assessment & Recommendation — folded into the primary view */}
            <EntityAssessment detail={detail} scoreBreakdown={scoreBreakdown} />
          </>
        )}

        {/* ---- NETWORK: relationship graph + related / similar entities ---- */}
        {tab === 'network' && (
          <Panel>
            <SectionHeader
              title={usingResolved ? 'Resolved Relationship Network' : 'Related & Similar'}
              subtitle={usingResolved
                ? `${parties.length} resolved relationship${parties.length === 1 ? '' : 's'} (shared IDs, address, ownership)`
                : 'No resolved CORD links — name-network matches'}
              icon={<Network className="w-4 h-4" />}
            />
            {parties.length > 0 && (
              <div className="mb-3">
                <EntityNetworkGraph entities={networkEntities} height={300} />
              </div>
            )}
            {related.length ? (
              <div className="grid gap-1.5 sm:grid-cols-2">
                {related.map((r, i) => (
                  <button key={i} onClick={() => r.id && onOpenEntity?.(r.id)}
                    className="w-full text-left p-2 bg-slate-50 hover:bg-[#E3F2FD] border border-slate-200 hover:border-[#005EA2] rounded transition-colors focus:outline-none focus:ring-2 focus:ring-[#005EA2]">
                    <div className="flex items-start justify-between gap-1.5">
                      <span className="text-[11px] font-bold text-[#0B1F33] line-clamp-2">{r.name}</span>
                      {r.score != null && <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded text-white shrink-0 ${riskDot(r.score)}`}>{r.score}</span>}
                    </div>
                    <div className="flex items-center justify-between mt-0.5">
                      <span className="text-[10px] text-[#5C5C5C] truncate">{r.sub}</span>
                      <span className="text-[10px] text-[#005EA2] font-bold shrink-0">→ Open</span>
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-[12px] text-[#5C5C5C]">No related or similar entities resolved.</p>
            )}
          </Panel>
        )}

        {/* ---- INTELLIGENCE: sanctions + aliases + ownership + locations ---- */}
        {tab === 'intelligence' && (
          <>
            <Panel>
              <SectionHeader title="Sanctions & Enforcement" icon={<Shield className="w-4 h-4" />} action={sdnProgram ? <StatusPill status="critical" /> : undefined} />
              {sdnProgram ? (
                <div className="text-[12px] text-[#0B1F33] space-y-1">
                  <div><span className="text-[#5C5C5C]">Program:</span> <b className="text-[#D83933]">{sdnProgram}</b></div>
                  {raw.OFAC_ID && <div><span className="text-[#5C5C5C]">OFAC ID:</span> <span className="font-mono">{raw.OFAC_ID}</span></div>}
                  {raw.PUBLISH_DATE && <div><span className="text-[#5C5C5C]">Published:</span> {raw.PUBLISH_DATE}</div>}
                </div>
              ) : (
                <p className="text-[12px] text-[#5C5C5C]">No OFAC sanctions program on record. Source dataset: <b>{e.data_source || '—'}</b>.</p>
              )}
            </Panel>

            {aliases.length > 0 && (
              <Panel>
                <SectionHeader title="Known Aliases" subtitle={`${aliases.length} alias${aliases.length === 1 ? '' : 'es'}`} />
                <div className="flex flex-wrap gap-1.5">
                  {aliases.slice(0, 16).map((a: string, i: number) => (
                    <span key={i} className="text-[11px] bg-slate-100 text-[#0B1F33] px-2 py-0.5 rounded">{a}</span>
                  ))}
                </div>
              </Panel>
            )}

            {chain.length > 0 && (
              <Panel>
                <SectionHeader title="Ownership Chain" subtitle={`${chain.length} level${chain.length === 1 ? '' : 's'}`} />
                <DataTable
                  columns={[
                    { key: 'name', label: 'Entity', render: (r: any) => <button onClick={() => partyId(r) && onOpenEntity?.(partyId(r))} className="text-[#005EA2] hover:underline font-semibold text-left">{partyName(r)}</button> },
                    { key: 'relationship', label: 'Relationship', render: (r: any) => prettyRel(r.relationship_type || r.relationship || r.type || r.role) },
                    { key: 'confidence', label: 'Confidence', align: 'right', mono: true, render: (r: any) => (r.confidence != null ? `${Math.round(r.confidence * 100)}%` : '—') },
                  ] as Column[]}
                  rows={chain}
                  caption="Ownership chain"
                  empty="No ownership chain."
                />
              </Panel>
            )}

            {/* Geography folded into Intelligence */}
            <Panel>
              <SectionHeader title="Locations" subtitle={`Country: ${(e.country || '—').toUpperCase()}`} icon={<MapPin className="w-4 h-4" />} />
              {addresses.length ? (
                <ul className="space-y-1 text-[12px] text-[#0B1F33]">
                  {addresses.map((a: string, i: number) => (
                    <li key={i} className="flex gap-1.5"><span className="text-[#005EA2]">•</span>{a}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-[12px] text-[#5C5C5C]">No street addresses on record{e.country ? `; registered country ${(e.country || '').toUpperCase()}.` : '.'}</p>
              )}
            </Panel>
          </>
        )}
      </div>
    </div>
  );
}
