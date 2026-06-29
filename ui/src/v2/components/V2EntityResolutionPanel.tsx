/**
 * Entity intelligence panel — real CORD data, driven by the selected entity.
 * Four tabs (Network / Geography / Intelligence / Risk Profile) rendered from
 * the resolved record + ownership chain + related parties. No fixtures.
 */
import React, { useState } from 'react';
import { Network, Globe, Shield, TrendingUp, AlertTriangle } from 'lucide-react';
import { Tabs, Panel, SectionHeader, StatusPill, DataTable, ScoreBar, Column } from '../../components/ui';
import { EntityDetail, entityRisk } from '../services/cordApi';

type TabId = 'network' | 'geography' | 'intelligence' | 'risk';

const partyName = (r: any) => r.name || r.entity_name || r.NAME || r.entity_id || r.id || '—';
const partyId = (r: any) => r.entity_id || r.id || r.related_entity_id || '';

export default function V2EntityResolutionPanel({
  detail,
  onOpenEntity,
  scoreBreakdown,
}: {
  detail: EntityDetail;
  onOpenEntity?: (id: string) => void;
  scoreBreakdown?: any | null;
}) {
  const [tab, setTab] = useState<TabId>('intelligence');
  const e = detail.entity || {};
  const raw = e.raw_data || {};
  const heur = entityRisk(detail);
  // Prefer the real v4.0 factor-attributed score; fall back to the heuristic.
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

  const tabs = [
    { id: 'network', label: 'Network', icon: <Network className="w-3.5 h-3.5" /> },
    { id: 'geography', label: 'Geography', icon: <Globe className="w-3.5 h-3.5" /> },
    { id: 'intelligence', label: 'Intelligence', icon: <Shield className="w-3.5 h-3.5" /> },
    { id: 'risk', label: 'Risk Profile', icon: <TrendingUp className="w-3.5 h-3.5" /> },
  ];

  const relColumns: Column[] = [
    {
      key: 'name', label: 'Related Entity', render: (r) => (
        <button onClick={() => partyId(r) && onOpenEntity?.(partyId(r))} className="text-[#005EA2] hover:underline font-semibold text-left">
          {partyName(r)}
        </button>
      ),
    },
    { key: 'relationship', label: 'Relationship', render: (r) => r.relationship || r.type || r.role || r.match_key || '—' },
    { key: 'confidence', label: 'Confidence', align: 'right', mono: true, render: (r) => (r.confidence != null ? `${Math.round(r.confidence * 100)}%` : '—') },
  ];

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 pt-2 bg-white">
        <Tabs tabs={tabs} active={tab} onChange={(id) => setTab(id as TabId)} />
      </div>
      <div className="flex-1 overflow-y-auto p-4 bg-[#F7F9FC] space-y-4">
        {tab === 'network' && (
          <Panel>
            <SectionHeader title="Resolved Relationships" subtitle={`${parties.length} related part${parties.length === 1 ? 'y' : 'ies'}`} icon={<Network className="w-4 h-4" />} />
            {parties.length ? (
              <DataTable columns={relColumns} rows={parties} caption="Related parties" empty="No related parties resolved." />
            ) : (
              <p className="text-[12px] text-[#5C5C5C]">No resolved relationships for this entity in CORD. See the Related &amp; Similar panel for name-network matches.</p>
            )}
          </Panel>
        )}

        {tab === 'geography' && (
          <Panel>
            <SectionHeader title="Locations" subtitle={`Country: ${(e.country || '—').toUpperCase()}`} icon={<Globe className="w-4 h-4" />} />
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
        )}

        {tab === 'intelligence' && (
          <>
            <Panel>
              <SectionHeader title="Sanctions &amp; Enforcement" icon={<Shield className="w-4 h-4" />} action={sdnProgram ? <StatusPill status="critical" /> : undefined} />
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
                <DataTable columns={relColumns} rows={chain} caption="Ownership chain" empty="No ownership chain." />
              </Panel>
            )}
          </>
        )}

        {tab === 'risk' && (
          <Panel>
            <SectionHeader
              title="Risk Profile"
              subtitle={`${scoreBreakdown ? 'v4.0 model score' : 'Resolved risk'} ${score}/100 (${tier})`}
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
                <p className="mt-2 text-[10px] text-[#5C5C5C]">Factor-attributed v4.0 entity score (provisional weights — pinned at calibration).</p>
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
        )}
      </div>
    </div>
  );
}
