/**
 * RiskExplainabilityTab
 *
 * Merged replacement for "Risk Profile" + "Risk Score" tabs.
 * Shows model explainability: factor breakdown, evidence, score waterfall,
 * seed vs model discrepancy, and AI synthesis narrative.
 */
import React, { useState } from 'react';
import {
  BarChart, Bar, RadarChart, Radar, PolarGrid, PolarAngleAxis,
  Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import { ChevronDown, ChevronRight, AlertTriangle, Info, CheckCircle, TrendingUp, TrendingDown } from 'lucide-react';
import { useRiskScoring } from '../hooks/useRiskScoring';
import MaturityBadge from './MaturityBadge';

// ── Colour helpers ──────────────────────────────────────────────────────────────
const FACTOR_COLORS: Record<string, string> = {
  Corridor:      '#B50909',
  Documentation: '#C05621',
  Party:         '#8B5A00',
  Pattern:       '#005EA2',
  Routing:       '#1B6C3B',
  Commodity:     '#5A2D82',
  Time:          '#4A5568',
};

function scoreColor(score: number): string {
  if (score >= 7) return '#B50909';
  if (score >= 5) return '#C05621';
  if (score >= 3) return '#8B5A00';
  return '#1B6C3B';
}

function contributionBar(pts: number, maxPts = 11): React.ReactNode {
  const pct = Math.min(100, (pts / maxPts) * 100);
  const color = pts >= 8 ? '#B50909' : pts >= 5 ? '#C05621' : pts >= 3 ? '#8B5A00' : '#D0D7DE';
  return (
    <div className="w-full bg-slate-100 rounded h-1.5 overflow-hidden">
      <div style={{ width: `${pct}%`, background: color, height: '100%' }} />
    </div>
  );
}

// ── Main component ──────────────────────────────────────────────────────────────
interface Props {
  selectedCase: any;
  selectedCaseShipments: any[];
}

export default function RiskExplainabilityTab({ selectedCase, selectedCaseShipments }: Props) {
  const shipment = selectedCaseShipments?.[0];
  const { scoreData, loading, error } = useRiskScoring(shipment?.shipment_id || null);
  const [expandedFactors, setExpandedFactors] = useState<Set<string>>(new Set(['Corridor', 'Documentation']));
  const [showAllComponents, setShowAllComponents] = useState(false);

  if (!selectedCaseShipments?.length)
    return <div className="p-6 text-slate-500 text-sm">No shipments in this case.</div>;

  if (loading)
    return (
      <div className="flex-1 p-8 flex items-center justify-center">
        <div className="text-center space-y-2">
          <div className="w-6 h-6 border-2 border-[#005EA2] border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm text-slate-500">Running risk model explainability analysis…</p>
        </div>
      </div>
    );

  if (error || !scoreData)
    return (
      <div className="flex-1 p-6 flex items-center justify-center">
        <div className="text-center space-y-2">
          <AlertTriangle className="w-8 h-8 text-amber-500 mx-auto" />
          <p className="text-sm text-slate-600">{error || 'No scoring data available.'}</p>
          <p className="text-xs text-slate-400">The risk model may not have scored this shipment yet.</p>
        </div>
      </div>
    );

  // Derived values
  const modelScore   = scoreData.final_score ?? 0;
  const seedScore    = selectedCase?.seed_risk_score ?? selectedCase?.risk_score ?? modelScore;
  const maturity     = selectedCase?.model_maturity ?? 15;
  const modelVersion = selectedCase?.model_version ?? scoreData.confidence_interval;
  const delta        = modelScore - seedScore;

  // Group components by factor
  const byFactor: Record<string, typeof scoreData.components> = {};
  scoreData.components.forEach((c: any) => {
    if (!byFactor[c.factor]) byFactor[c.factor] = [];
    byFactor[c.factor].push(c);
  });

  // Factor totals for radar + bar chart
  const factorTotals = Object.entries(byFactor).map(([factor, comps]) => ({
    factor,
    total: comps.reduce((s: number, c: any) => s + (c.weighted_result ?? 0), 0),
    maxPossible: comps.reduce((s: number, c: any) => s + (c.weight ?? 0), 0),
    color: FACTOR_COLORS[factor] ?? '#005EA2',
  })).sort((a, b) => b.total - a.total);

  // Top 5 drivers across all components
  const topDrivers = [...scoreData.components]
    .sort((a: any, b: any) => (b.weighted_result ?? 0) - (a.weighted_result ?? 0))
    .slice(0, 5);

  const radarData = factorTotals.map(f => ({
    factor: f.factor,
    score: parseFloat(((f.total / Math.max(f.maxPossible, 1)) * 10).toFixed(1)),
    fullMark: 10,
  }));

  const toggle = (factor: string) =>
    setExpandedFactors(prev => {
      const next = new Set(prev);
      next.has(factor) ? next.delete(factor) : next.add(factor);
      return next;
    });

  // ── Render ────────────────────────────────────────────────────────────────────
  return (
    <div className="flex-1 overflow-y-auto bg-[#F7F9FC]">
      {/* ── HEADER BAND ────────────────────────────────────────────────────── */}
      <div className="bg-white border-b border-[#D0D7DE] px-6 py-3 flex items-center gap-4 flex-wrap">
        <div>
          <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wide">Risk Analysis</span>
          <span className="mx-2 text-slate-300">|</span>
          <span className="text-[10px] text-slate-400">Model explainability &amp; score justification</span>
        </div>
        <div className="ml-auto">
          <MaturityBadge
            maturity={maturity}
            modelVersion={modelVersion}
            scoredAt={selectedCase?.risk_score_calculated_at}
            seedScore={seedScore}
            variant="banner"
          />
        </div>
      </div>

      <div className="p-5 space-y-5">

        {/* ── ROW 1: SCORE PANEL + FACTOR BARS ──────────────────────────── */}
        <div className="grid grid-cols-12 gap-4">

          {/* Score panel */}
          <div className="col-span-3 bg-white rounded border border-[#D0D7DE] p-4 flex flex-col items-center justify-center gap-2">
            {/* Model score */}
            <div className="text-center">
              <div className={`text-5xl font-black ${modelScore >= 70 ? 'text-[#B50909]' : modelScore >= 50 ? 'text-[#C05621]' : 'text-[#005EA2]'}`}>
                {modelScore.toFixed(0)}
              </div>
              <div className="text-[9px] text-slate-400 uppercase font-bold">Model Score / 100</div>
              <div className="text-[9px] text-slate-400">{scoreData.confidence_interval || ''}</div>
            </div>

            <div className="w-full border-t border-dashed border-slate-200 my-1" />

            {/* Seed score comparison */}
            <div className="w-full text-center">
              <div className="text-[9px] text-slate-500 uppercase font-semibold mb-1">Investigator Est.</div>
              <div className="text-2xl font-bold text-slate-600">{seedScore.toFixed(0)}</div>
              <div className="flex items-center justify-center gap-1 text-[9px] mt-1">
                {delta < 0
                  ? <><TrendingDown className="w-3 h-3 text-blue-500" /><span className="text-blue-600">Δ {delta.toFixed(0)} model lower</span></>
                  : <><TrendingUp className="w-3 h-3 text-red-500" /><span className="text-red-600">Δ +{delta.toFixed(0)} model higher</span></>
                }
              </div>
            </div>

            <div className="w-full border-t border-dashed border-slate-200 my-1" />

            {/* Recommendation */}
            <div className="text-center">
              <div className={`text-sm font-black px-3 py-1 rounded ${
                scoreData.h3_recommendation === 'EXAMINE' ? 'bg-red-100 text-red-700' :
                scoreData.h3_recommendation === 'REVIEW'  ? 'bg-amber-100 text-amber-700' :
                'bg-green-100 text-green-700'
              }`}>
                {scoreData.h3_recommendation || 'REVIEW'}
              </div>
              <div className="text-[8px] text-slate-400 mt-1">Model recommendation</div>
            </div>

            {/* Score note */}
            {maturity < 30 && (
              <div className="w-full bg-amber-50 border border-amber-200 rounded p-2 text-[8px] text-amber-700 leading-relaxed">
                <AlertTriangle className="w-2.5 h-2.5 inline mr-1" />
                Score compressed at {maturity}% maturity. Investigator estimate ({seedScore}) drives case priority.
              </div>
            )}
          </div>

          {/* Factor contribution bars */}
          <div className="col-span-5 bg-white rounded border border-[#D0D7DE] p-4">
            <div className="text-[10px] font-bold text-[#0B1F33] mb-3 uppercase tracking-wide">
              Factor Contributions
            </div>
            <div className="space-y-2.5">
              {factorTotals.map(f => (
                <div key={f.factor}>
                  <div className="flex items-center justify-between text-[9px] mb-0.5">
                    <span className="font-semibold" style={{ color: f.color }}>{f.factor}</span>
                    <span className="font-mono font-bold">{f.total.toFixed(1)} <span className="text-slate-400">/ {f.maxPossible.toFixed(0)} pts</span></span>
                  </div>
                  <div className="w-full bg-slate-100 rounded h-2 overflow-hidden">
                    <div
                      style={{
                        width: `${Math.min(100, (f.total / f.maxPossible) * 100)}%`,
                        background: f.color,
                        height: '100%',
                        transition: 'width 0.3s'
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-3 pt-2 border-t border-slate-100 flex justify-between text-[9px] font-mono">
              <span className="text-slate-500">Rule engine subtotal</span>
              <span className="font-bold text-[#0B1F33]">{scoreData.subtotal?.toFixed(1)} pts</span>
            </div>
          </div>

          {/* Radar chart */}
          <div className="col-span-4 bg-white rounded border border-[#D0D7DE] p-4">
            <div className="text-[10px] font-bold text-[#0B1F33] mb-2 uppercase tracking-wide">Risk Radar</div>
            <ResponsiveContainer width="100%" height={180}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="#E2E8F0" />
                <PolarAngleAxis dataKey="factor" tick={{ fontSize: 8, fill: '#4A5568' }} />
                <Radar
                  name="Risk"
                  dataKey="score"
                  stroke="#005EA2"
                  fill="#005EA2"
                  fillOpacity={0.25}
                />
                <Tooltip
                  formatter={(v: any) => [`${v}/10`, 'Risk Level']}
                  contentStyle={{ fontSize: 9, padding: '4px 8px' }}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* ── ROW 2: TOP DRIVERS + SCORE WATERFALL ──────────────────────── */}
        <div className="grid grid-cols-12 gap-4">

          {/* Top drivers */}
          <div className="col-span-7 bg-white rounded border border-[#D0D7DE] p-4">
            <div className="text-[10px] font-bold text-[#0B1F33] mb-3 uppercase tracking-wide">
              Top Risk Drivers
            </div>
            <div className="space-y-2">
              {topDrivers.map((c: any, i: number) => (
                <div key={i} className="border border-slate-100 rounded p-2.5">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span
                          className="text-[8px] font-bold px-1.5 py-0.5 rounded"
                          style={{
                            background: (FACTOR_COLORS[c.factor] ?? '#005EA2') + '18',
                            color: FACTOR_COLORS[c.factor] ?? '#005EA2',
                          }}
                        >
                          {c.factor.toUpperCase()}
                        </span>
                        <span className="text-[10px] font-semibold text-[#0B1F33] truncate">{c.component}</span>
                      </div>
                      <p className="text-[9px] text-slate-500 mt-0.5 leading-relaxed">{c.rationale}</p>
                      {c.evidence?.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1">
                          {c.evidence.slice(0, 3).map((ev: string, ei: number) => (
                            <span key={ei} className="text-[7px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded font-mono">
                              {ev}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-base font-black" style={{ color: scoreColor(c.score) }}>
                        {c.weighted_result?.toFixed(1)}
                      </div>
                      <div className="text-[7px] text-slate-400">pts</div>
                      <div className="text-[7px] text-slate-400 font-mono mt-0.5">
                        {c.score.toFixed(1)}/10 × {c.weight.toFixed(0)}
                      </div>
                    </div>
                  </div>
                  <div className="mt-1.5">{contributionBar(c.weighted_result, 11)}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Score waterfall + AI synthesis */}
          <div className="col-span-5 space-y-4">
            {/* Score calculation */}
            <div className="bg-white rounded border border-[#D0D7DE] p-4">
              <div className="text-[10px] font-bold text-[#0B1F33] mb-3 uppercase tracking-wide">Score Calculation</div>
              <div className="space-y-1.5 text-[10px] font-mono">
                <div className="flex justify-between">
                  <span className="text-slate-600">Rule engine subtotal</span>
                  <span className="font-bold">{scoreData.subtotal?.toFixed(1)}</span>
                </div>
                {scoreData.corridor_risk_adjustment && (
                  <div className="flex justify-between text-slate-500">
                    <span>Corridor adj ({scoreData.corridor_risk_adjustment.multiplier?.toFixed(2)}×)</span>
                    <span>+{scoreData.corridor_risk_adjustment.adjustment_points?.toFixed(1)}</span>
                  </div>
                )}
                {scoreData.additional_adjustments?.map((adj: any, i: number) => (
                  <div key={i} className="flex justify-between text-slate-500">
                    <span className="truncate max-w-[70%]">{adj.adjustment_type}</span>
                    <span>{adj.points >= 0 ? '+' : ''}{adj.points?.toFixed(1)}</span>
                  </div>
                ))}
                <div className="border-t border-slate-200 pt-1.5 flex justify-between font-bold text-[11px]">
                  <span>Rule engine total</span>
                  <span className="text-[#0B1F33]">{scoreData.final_score?.toFixed(1)}</span>
                </div>
                <div className="flex justify-between text-[#005EA2] font-bold">
                  <span>ML adjustment (XGBoost)</span>
                  <span>+{((selectedCase?.calculated_risk_score ?? modelScore) - modelScore).toFixed(1)}</span>
                </div>
                <div className="border-t-2 border-[#0B1F33] pt-1.5 flex justify-between font-black text-[12px]">
                  <span>FINAL MODEL SCORE</span>
                  <span className={
                    (selectedCase?.calculated_risk_score ?? modelScore) >= 70 ? 'text-[#B50909]' :
                    (selectedCase?.calculated_risk_score ?? modelScore) >= 50 ? 'text-[#C05621]' : 'text-[#005EA2]'
                  }>
                    {(selectedCase?.calculated_risk_score ?? modelScore).toFixed(1)} / 100
                  </span>
                </div>
              </div>
            </div>

            {/* AI synthesis */}
            {selectedCase?.score_validation && (
              <div className={`rounded border p-3 text-[9px] leading-relaxed ${
                selectedCase.score_validation.status === 'discrepancy'
                  ? 'bg-amber-50 border-amber-200 text-amber-800'
                  : 'bg-blue-50 border-blue-200 text-blue-800'
              }`}>
                <div className="font-bold mb-1 flex items-center gap-1">
                  <Info className="w-3 h-3" />
                  Score Validation
                </div>
                <p>{selectedCase.score_validation.message}</p>
                {selectedCase.score_validation.maturity_note && (
                  <p className="mt-1 opacity-80">{selectedCase.score_validation.maturity_note}</p>
                )}
              </div>
            )}
          </div>
        </div>

        {/* ── ROW 3: FULL COMPONENT TABLE ───────────────────────────────── */}
        <div className="bg-white rounded border border-[#D0D7DE] overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
            <span className="text-[10px] font-bold text-[#0B1F33] uppercase tracking-wide">
              All 18 Risk Components — Factor Breakdown
            </span>
            <span className="text-[9px] text-slate-400">Click factor to expand evidence</span>
          </div>

          {Object.entries(byFactor).map(([factor, comps]: any) => {
            const isOpen = expandedFactors.has(factor);
            const factorTotal = comps.reduce((s: number, c: any) => s + (c.weighted_result ?? 0), 0);
            const factorMax = comps.reduce((s: number, c: any) => s + (c.weight ?? 0), 0);
            const color = FACTOR_COLORS[factor] ?? '#005EA2';

            return (
              <div key={factor} className="border-b border-slate-100 last:border-b-0">
                {/* Factor header row */}
                <button
                  onClick={() => toggle(factor)}
                  className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-slate-50 transition-colors"
                >
                  {isOpen
                    ? <ChevronDown className="w-3 h-3 text-slate-400 shrink-0" />
                    : <ChevronRight className="w-3 h-3 text-slate-400 shrink-0" />
                  }
                  <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: color }} />
                  <span className="text-[10px] font-bold uppercase tracking-wide" style={{ color }}>
                    {factor}
                  </span>
                  <span className="text-[9px] text-slate-400 ml-1">({comps.length} components)</span>
                  <div className="flex-1 mx-3">
                    <div className="w-full bg-slate-100 rounded h-1 overflow-hidden">
                      <div style={{ width: `${Math.min(100, (factorTotal / factorMax) * 100)}%`, background: color, height: '100%' }} />
                    </div>
                  </div>
                  <span className="text-[9px] font-mono font-bold shrink-0">
                    {factorTotal.toFixed(1)} / {factorMax.toFixed(0)} pts
                  </span>
                </button>

                {/* Component detail rows */}
                {isOpen && (
                  <div className="bg-slate-50 border-t border-slate-100">
                    <table className="w-full text-[9px]">
                      <thead>
                        <tr className="text-[8px] text-slate-400 uppercase font-bold border-b border-slate-200">
                          <th className="text-left px-8 py-1.5">Component</th>
                          <th className="text-right px-3 py-1.5">Score / 10</th>
                          <th className="text-right px-3 py-1.5">Weight</th>
                          <th className="text-right px-3 py-1.5">Contribution</th>
                          <th className="text-left px-3 py-1.5 max-w-[30%]">Rationale & Evidence</th>
                        </tr>
                      </thead>
                      <tbody>
                        {comps.map((c: any, i: number) => (
                          <tr key={i} className={`border-b border-slate-100 last:border-b-0 ${i % 2 === 0 ? 'bg-white' : 'bg-slate-50'}`}>
                            <td className="px-8 py-2 font-medium text-[#0B1F33]">{c.component}</td>
                            <td className="px-3 py-2 text-right">
                              <span className="font-bold font-mono" style={{ color: scoreColor(c.score) }}>
                                {c.score.toFixed(1)}
                              </span>
                            </td>
                            <td className="px-3 py-2 text-right font-mono text-slate-500">{c.weight.toFixed(1)}</td>
                            <td className="px-3 py-2 text-right font-mono font-bold text-[#005EA2]">
                              {c.weighted_result?.toFixed(2)}
                            </td>
                            <td className="px-3 py-2 max-w-[30%]">
                              <p className="text-slate-600 leading-relaxed">{c.rationale}</p>
                              {c.evidence?.length > 0 && (
                                <div className="flex flex-wrap gap-1 mt-1">
                                  {c.evidence.slice(0, 3).map((ev: string, ei: number) => (
                                    <span key={ei} className="bg-slate-200 text-slate-600 px-1 py-0.5 rounded font-mono text-[7px]">{ev}</span>
                                  ))}
                                </div>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            );
          })}
        </div>

      </div>
    </div>
  );
}
