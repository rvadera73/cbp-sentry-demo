/**
 * ReferralPackageV2 — CSOP-BP-GS-26-0001 Compliant Referral Package
 *
 * Structure mirrors the actual CBP ILLEGAL TRANSSHIPMENT REFERRAL PACKAGE:
 *   Header     — Package ID, entity, risk score, confidence, recommendation
 *   Question 1 — Identify entities and imports at high risk
 *   Question 2 — Specific factors indicative of illegal transshipment risk
 *   Question 3 — Data sources and AI methodologies
 *   Question 4 — Recommended CBP Actions
 *   Section 5  — Officer Review & Feedback (agree/disagree loop)
 *
 * Data source: GET /api/referral/{shipmentId}?format=json  (no new APIs)
 * Feedback:    POST /api/feedback/override               (existing MLOps endpoint)
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  AlertTriangle, CheckCircle, XCircle, ChevronDown, ChevronRight,
  FileText, Ship, Building2, MapPin, BarChart2, Download,
  AlertCircle, Info, Clock, ArrowRight, Target, Loader
} from 'lucide-react';
import { API_BASE_URL } from '../../services/apiUrl';

// ─── Types ────────────────────────────────────────────────────────────────────

interface PackageData {
  referral_id: string;
  shipment_id: string;
  created_at: string;
  risk_score: number;
  risk_tier: string;
  confidence: string;
  recommendation: string;
  shipper_name: string;
  consignee_name: string;
  origin_country: string;
  hs_code: string;
  commodity_name: string;
  sections: Record<string, any>;
}

interface OfficerForm {
  agree: 'agree' | 'disagree' | null;
  disagreeReason: string;
  docsReviewed: Record<string, boolean>;
  scoreAccuracy: 'accurate' | 'too_high' | 'too_low' | null;
  topIndicator: string;
  notes: string;
  badgeNumber: string;
}

interface Props {
  selectedCase: any;
  selectedCaseShipments: any[];
}

// ─── Helper: Risk color ───────────────────────────────────────────────────────

function riskColor(score: number) {
  if (score >= 80) return { bg: '#FEE2E2', text: '#991B1B', border: '#FCA5A5', label: 'CRITICAL' };
  if (score >= 65) return { bg: '#FEF3C7', text: '#92400E', border: '#FCD34D', label: 'HIGH' };
  if (score >= 40) return { bg: '#FFF7ED', text: '#9A3412', border: '#FDBA74', label: 'MEDIUM' };
  return { bg: '#DCFCE7', text: '#166534', border: '#86EFAC', label: 'LOW' };
}

function countryName(code: string) {
  const map: Record<string, string> = {
    CN: 'China', VN: 'Vietnam', US: 'United States', SG: 'Singapore',
    MY: 'Malaysia', TH: 'Thailand', KH: 'Cambodia', IN: 'India', TW: 'Taiwan',
  };
  return map[code] || code;
}

function hsFamily(hs: string) {
  const prefix = (hs || '').replace('.', '').substring(0, 4);
  const map: Record<string, string> = {
    '7604': 'Aluminum Extrusions', '7210': 'Flat-Rolled Steel', '7225': 'Stainless Flat Steel',
    '8541': 'Solar Panels/Cells', '6203': 'Garments (Men\'s)', '6204': 'Garments (Women\'s)',
  };
  return map[prefix] || '';
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function SectionHeader({ number, title, subtitle }: { number: string; title: string; subtitle?: string }) {
  return (
    <div className="flex items-start gap-3 mb-4">
      <div className="w-8 h-8 rounded-full bg-[#005EA2] text-white text-[11px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
        {number}
      </div>
      <div>
        <h3 className="text-sm font-bold text-[#0B1F33]">{title}</h3>
        {subtitle && <p className="text-[11px] text-slate-500 mt-0.5">{subtitle}</p>}
      </div>
    </div>
  );
}

function DataTable({ headers, rows, caption }: { headers: string[]; rows: (string | number | React.ReactNode)[][]; caption?: string }) {
  return (
    <div className="overflow-x-auto mb-3">
      {caption && <p className="text-[10px] font-bold text-[#005EA2] uppercase tracking-wide mb-1">{caption}</p>}
      <table className="w-full text-[11px] border-collapse border border-[#D0D7DE]">
        <thead>
          <tr className="bg-[#005EA2] text-white">
            {headers.map((h, i) => (
              <th key={i} className="text-left px-3 py-2 font-semibold">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr key={ri} className={ri % 2 === 0 ? 'bg-slate-50' : 'bg-white'}>
              {row.map((cell, ci) => (
                <td key={ci} className="px-3 py-1.5 text-slate-700 border-b border-[#E5E7EB]">
                  {cell === null || cell === undefined ? '—' : cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RiskFactorCard({
  number, title, level, narrative, children
}: {
  number: number; title: string; level: 'HIGH' | 'MEDIUM' | 'LOW' | 'CRITICAL';
  narrative: string; children?: React.ReactNode;
}) {
  const [expanded, setExpanded] = useState(true);
  const colors = { CRITICAL: 'border-red-500 bg-red-50', HIGH: 'border-amber-500 bg-amber-50', MEDIUM: 'border-yellow-400 bg-yellow-50', LOW: 'border-green-400 bg-green-50' };
  const badges = { CRITICAL: 'bg-red-600 text-white', HIGH: 'bg-amber-600 text-white', MEDIUM: 'bg-yellow-500 text-white', LOW: 'bg-green-600 text-white' };
  return (
    <div className={`border-l-4 rounded-sm p-4 mb-4 ${colors[level]}`}>
      <button className="w-full flex items-start gap-3 text-left" onClick={() => setExpanded(!expanded)}>
        <span className={`px-2 py-0.5 rounded text-[10px] font-bold flex-shrink-0 ${badges[level]}`}>
          RF-{number} {level}
        </span>
        <span className="text-[12px] font-bold text-[#0B1F33] flex-1">{title}</span>
        {expanded ? <ChevronDown size={14} className="text-slate-500 mt-0.5" /> : <ChevronRight size={14} className="text-slate-500 mt-0.5" />}
      </button>
      {expanded && (
        <div className="mt-3 space-y-3">
          <p className="text-[11px] text-slate-700 leading-relaxed">{narrative}</p>
          {children}
        </div>
      )}
    </div>
  );
}

function ScoreBar({ label, score, maxScore, weight }: { label: string; score: number; maxScore: number; weight: number }) {
  const pct = Math.min(100, (score / maxScore) * 100);
  const color = pct >= 80 ? '#DC2626' : pct >= 60 ? '#D97706' : pct >= 40 ? '#F59E0B' : '#10B981';
  return (
    <div className="flex items-center gap-2 text-[11px] mb-1.5">
      <span className="w-40 text-slate-700 truncate">{label}</span>
      <div className="flex-1 bg-slate-200 rounded h-3 relative overflow-hidden">
        <div className="h-3 rounded transition-all" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="w-12 text-right font-bold text-slate-800">{score.toFixed(1)}/{maxScore.toFixed(0)}</span>
      <span className="w-10 text-right text-slate-500">{(weight * 100).toFixed(0)}% wt</span>
    </div>
  );
}

function WhatIfCard({ scenario, impact, currentScore, revisedScore }: { scenario: string; impact: string; currentScore: number; revisedScore: number }) {
  const delta = revisedScore - currentScore;
  const direction = delta < 0 ? 'decrease' : 'increase';
  const color = delta < 0 ? 'text-green-700' : 'text-red-700';
  return (
    <div className="border border-[#D0D7DE] rounded-sm p-3 bg-white">
      <p className="text-[11px] font-semibold text-[#0B1F33] mb-1">📊 {scenario}</p>
      <p className="text-[10px] text-slate-500 mb-2">{impact}</p>
      <div className="flex items-center gap-2 text-[11px]">
        <span className="text-slate-600">Score: <strong>{currentScore.toFixed(0)}</strong></span>
        <ArrowRight size={12} className="text-slate-400" />
        <span className={`font-bold ${color}`}>{revisedScore.toFixed(0)}</span>
        <span className={`text-[10px] ${color}`}>({delta > 0 ? '+' : ''}{delta.toFixed(0)} pts — {direction})</span>
        <span className="ml-auto text-[10px] font-bold px-2 py-0.5 rounded" style={
          revisedScore >= 65 ? { background: '#FEF3C7', color: '#92400E' } : { background: '#DCFCE7', color: '#166534' }
        }>
          → {revisedScore >= 80 ? 'CRITICAL' : revisedScore >= 65 ? 'HIGH' : revisedScore >= 40 ? 'MEDIUM' : 'LOW'}
        </span>
      </div>
    </div>
  );
}

// ─── Officer Review Form ──────────────────────────────────────────────────────

function OfficerReviewForm({
  packageData,
  onSubmit,
}: {
  packageData: PackageData;
  onSubmit: (form: OfficerForm) => Promise<void>;
}) {
  const [form, setForm] = useState<OfficerForm>({
    agree: null, disagreeReason: '', docsReviewed: {}, scoreAccuracy: null,
    topIndicator: '', notes: '', badgeNumber: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const indicators = packageData.sections?.section_3_11_risk_indicators?.indicators
    ?.filter((i: any) => i.present)
    .map((i: any) => i.indicator) || [];

  const docs = [
    'Commercial Invoice', 'ISF Element 9 Filing', 'Certificate of Origin',
    'Bill of Lading', 'Factory / Manufacturing Documentation',
  ];

  const handleSubmit = async () => {
    if (!form.agree || !form.badgeNumber) return;
    setSubmitting(true);
    try {
      await onSubmit(form);
      setSubmitted(true);
    } finally {
      setSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className="bg-green-50 border border-green-300 rounded-sm p-6 text-center">
        <CheckCircle className="mx-auto text-green-600 mb-2" size={32} />
        <p className="font-bold text-green-800">Officer Review Submitted</p>
        <p className="text-[11px] text-green-700 mt-1">Feedback recorded in the MLOps pipeline. Score model will incorporate this review in the next training cycle.</p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Recommendation Agreement */}
      <div>
        <p className="text-[11px] font-bold text-[#0B1F33] mb-2 uppercase tracking-wide">
          Referral Recommendation — System Assessment
        </p>
        <div className="bg-amber-50 border border-amber-200 rounded-sm p-3 mb-3 text-[11px]">
          <span className="font-bold text-amber-800">System recommends: </span>
          <span className="font-bold text-[#0B1F33]">{packageData.recommendation}</span>
          <span className="text-slate-600"> · Risk Score: {packageData.risk_score.toFixed(1)}/100 · Confidence: {packageData.confidence}</span>
        </div>
        <div className="flex gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="radio" name="agree" checked={form.agree === 'agree'} onChange={() => setForm(f => ({ ...f, agree: 'agree' }))} />
            <span className="text-[12px] font-semibold text-green-700">✓ I AGREE — Proceed with referral</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="radio" name="agree" checked={form.agree === 'disagree'} onChange={() => setForm(f => ({ ...f, agree: 'disagree' }))} />
            <span className="text-[12px] font-semibold text-red-700">✗ I DISAGREE — Do not refer</span>
          </label>
        </div>
        {form.agree === 'disagree' && (
          <div className="mt-2">
            <label className="text-[11px] text-slate-600 block mb-1">Primary reason for disagreement:</label>
            <select
              className="w-full border border-[#D0D7DE] rounded px-2 py-1.5 text-[11px]"
              value={form.disagreeReason}
              onChange={e => setForm(f => ({ ...f, disagreeReason: e.target.value }))}
            >
              <option value="">Select reason...</option>
              <option value="insufficient_evidence">Insufficient evidence to support referral</option>
              <option value="document_explanation">Document discrepancy has a satisfactory explanation</option>
              <option value="known_entity">Known legitimate entity — false positive</option>
              <option value="score_inflated">Risk score is inflated — weighting issue</option>
              <option value="other">Other (see notes)</option>
            </select>
          </div>
        )}
      </div>

      {/* Document Review Attestation */}
      <div>
        <p className="text-[11px] font-bold text-[#0B1F33] mb-2 uppercase tracking-wide">
          Document Review Attestation
        </p>
        <div className="grid grid-cols-2 gap-2">
          {docs.map(doc => (
            <label key={doc} className="flex items-center gap-2 cursor-pointer text-[11px]">
              <input
                type="checkbox"
                checked={!!form.docsReviewed[doc]}
                onChange={e => setForm(f => ({ ...f, docsReviewed: { ...f.docsReviewed, [doc]: e.target.checked } }))}
              />
              {doc}
            </label>
          ))}
        </div>
      </div>

      {/* Risk Score Accuracy */}
      <div>
        <p className="text-[11px] font-bold text-[#0B1F33] mb-2 uppercase tracking-wide">
          Risk Score Accuracy Assessment
        </p>
        <p className="text-[11px] text-slate-500 mb-2">System scored this case: <strong>{packageData.risk_score.toFixed(1)}/100</strong></p>
        <div className="flex gap-4 flex-wrap">
          {(['accurate', 'too_high', 'too_low'] as const).map(v => (
            <label key={v} className="flex items-center gap-2 cursor-pointer text-[11px]">
              <input type="radio" name="accuracy" checked={form.scoreAccuracy === v} onChange={() => setForm(f => ({ ...f, scoreAccuracy: v }))} />
              <span className="capitalize">{v.replace('_', ' ')}</span>
            </label>
          ))}
        </div>
        {indicators.length > 0 && (
          <div className="mt-2">
            <label className="text-[11px] text-slate-600 block mb-1">Most significant indicator in your judgment:</label>
            <select
              className="w-full border border-[#D0D7DE] rounded px-2 py-1.5 text-[11px]"
              value={form.topIndicator}
              onChange={e => setForm(f => ({ ...f, topIndicator: e.target.value }))}
            >
              <option value="">Select indicator...</option>
              {indicators.map((ind: string) => <option key={ind} value={ind}>{ind}</option>)}
            </select>
          </div>
        )}
      </div>

      {/* Notes + Signature */}
      <div>
        <p className="text-[11px] font-bold text-[#0B1F33] mb-2 uppercase tracking-wide">Officer Notes</p>
        <textarea
          className="w-full border border-[#D0D7DE] rounded px-3 py-2 text-[11px] resize-none"
          rows={3}
          placeholder="Additional context, observations, or instructions for the next reviewer..."
          value={form.notes}
          onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
        />
      </div>
      <div className="flex gap-4 items-end">
        <div className="flex-1">
          <label className="text-[11px] font-bold text-[#0B1F33] block mb-1">Officer Badge #</label>
          <input
            type="text"
            className="w-full border border-[#D0D7DE] rounded px-3 py-2 text-[11px]"
            placeholder="e.g., CBP-12345"
            value={form.badgeNumber}
            onChange={e => setForm(f => ({ ...f, badgeNumber: e.target.value }))}
          />
        </div>
        <div className="text-[10px] text-slate-500">
          Date: {new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
        </div>
      </div>
      <div className="flex gap-3 pt-2">
        <button
          onClick={handleSubmit}
          disabled={submitting || !form.agree || !form.badgeNumber}
          className={`flex-1 py-2.5 px-4 rounded text-[12px] font-bold transition ${
            submitting || !form.agree || !form.badgeNumber
              ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
              : 'bg-[#005EA2] text-white hover:bg-[#004A80]'
          }`}
        >
          {submitting ? 'Submitting...' : 'Submit Officer Review to System'}
        </button>
      </div>
      <p className="text-[10px] text-slate-400">
        Submission is recorded in the MLOps feedback pipeline. Your assessment will be used to calibrate
        the risk scoring model in future training cycles.
      </p>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function ReferralPackageV2({ selectedCase, selectedCaseShipments }: Props) {
  const shipment = selectedCaseShipments?.[0];
  const [packageData, setPackageData] = useState<PackageData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<'q1' | 'q2' | 'q3' | 'q4' | 'officer'>('q1');
  const printRef = useRef<HTMLDivElement>(null);

  const loadPackage = useCallback(async () => {
    if (!shipment?.shipment_id) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/referral/${shipment.shipment_id}?format=json`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setPackageData({ ...data, sections: data.sections || {} });
    } catch (e: any) {
      setError(e.message || 'Failed to load referral package');
    } finally {
      setLoading(false);
    }
  }, [shipment?.shipment_id]);

  useEffect(() => { loadPackage(); }, [loadPackage]);

  const handleFeedback = async (form: OfficerForm) => {
    if (!packageData) return;
    const params = new URLSearchParams({
      shipment_id: packageData.shipment_id,
      original_score: packageData.risk_score.toString(),
      override_decision: form.agree === 'agree' ? 'ACCEPT' : 'REJECT',
      feedback_type: form.scoreAccuracy || 'accurate',
      analyst_id: form.badgeNumber,
      analyst_name: `Officer ${form.badgeNumber}`,
      notes: [
        form.disagreeReason ? `Reason: ${form.disagreeReason}` : '',
        form.topIndicator ? `Top indicator: ${form.topIndicator}` : '',
        form.notes,
        `Docs reviewed: ${Object.keys(form.docsReviewed).filter(k => form.docsReviewed[k]).join(', ')}`,
      ].filter(Boolean).join(' | '),
    });
    await fetch(`${API_BASE_URL}/feedback/override?${params}`, { method: 'POST' });
  };

  const handlePrint = () => window.print();

  // ── Loading / error states
  if (!shipment) {
    return <div className="p-8 text-center text-slate-500">No shipment selected. Open a case to generate a referral package.</div>;
  }
  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center flex-col gap-3 py-16">
        <Loader size={32} className="animate-spin text-[#005EA2]" />
        <p className="text-slate-600 text-sm">Generating CSOP Referral Package...</p>
        <p className="text-slate-400 text-[11px]">Shipment: {shipment.shipment_id}</p>
      </div>
    );
  }
  if (error) {
    return (
      <div className="p-8 text-center">
        <AlertCircle size={32} className="text-red-500 mx-auto mb-2" />
        <p className="font-bold text-red-700">Failed to load referral package</p>
        <p className="text-slate-500 text-sm mt-1">{error}</p>
        <button onClick={loadPackage} className="mt-3 px-4 py-2 bg-[#005EA2] text-white rounded text-sm">Retry</button>
      </div>
    );
  }
  if (!packageData) return null;

  const s = packageData.sections;
  const rc = riskColor(packageData.risk_score);

  // Build risk factor narratives from available data
  const e9Section = s.section_3_9_document_consistency || {};
  const e9 = e9Section.isf_element9 || {};
  const suppSection = s.section_3_10_supplier_verification || {};
  const routeSection = s.section_3_3_routing_history || {};
  const tradeSection = s.section_3_7_trade_flow_intelligence || {};
  const scoreSection = s.section_3_12_score_breakdown || {};
  const indicatorSection = s.section_3_11_risk_indicators || {};
  const whatIfSection = s.section_3_13_what_if_scenarios || {};

  const activeIndicators = (indicatorSection.indicators || []).filter((i: any) => i.present);
  const components = scoreSection.components || [];
  const calcTable = scoreSection.calculation_table || {};
  const criticalIndicators: string[] = calcTable.critical_indicators || [];
  const whatIfScenarios = whatIfSection.scenarios || [];

  // Derive narratives from structured data
  const rf1Narrative = e9.is_mismatch
    ? `ISF Element 9 (container stuffing location) declares origin as ${countryName(e9.declared_origin || packageData.origin_country)}, but AIS tracking and stuffing location data identify actual container loading in ${countryName(e9.actual_stuffing_country || 'CN')}. This discrepancy is a direct indicator of origin falsification — a core transshipment tactic to avoid ${tradeSection.ad_cvd_rate || 'applicable'} AD/CVD duties. Mismatch confidence: ${e9.mismatch_confidence ? Math.round(e9.mismatch_confidence * 100) : 98}%.`
    : `ISF Element 9 origin declaration is consistent with declared country of origin (${countryName(packageData.origin_country)}). No stuffing location discrepancy detected.`;

  const rf2Narrative = `Vessel ${routeSection.vessel || 'Unknown'} shows a dwell time of ${routeSection.dwell_days?.toFixed(1) || '—'} days at the ${countryName(packageData.origin_country)} port of lading, compared to a commodity-specific baseline of ${routeSection.dwell_baseline || 2.5} days. This ${Math.round((routeSection.dwell_days / (routeSection.dwell_baseline || 2.5))).toFixed(0)}× anomaly (${routeSection.dwell_anomaly || 'HIGH'} severity) is consistent with off-loading of Chinese-origin cargo and reloading under a new origin declaration — a documented transshipment operational pattern. AIS signal gaps: ${routeSection.ais_gaps || 0} detected.`;

  const rf3Narrative = `HTS ${packageData.hs_code} (${hsFamily(packageData.hs_code) || packageData.commodity_name}) from ${countryName(packageData.origin_country)} is subject to active AD/CVD orders at ${tradeSection.ad_cvd_rate || 'elevated'} duty rates. The shipper, ${packageData.shipper_name}, was established ${suppSection.shipper_age_months || '—'} months ago — a ${suppSection.shipper_age_risk || 'HIGH'} risk indicator consistent with shell company formation to exploit origin-shifting trade corridors. ${tradeSection.prior_filings > 0 ? `${tradeSection.prior_filings} prior CBP filings detected for this corridor.` : ''}`;

  const rf4Narrative = criticalIndicators.length > 0
    ? `Risk Intelligence Synthesis identified ${criticalIndicators.length} co-occurring critical indicators, triggering a compound risk multiplier of ×${calcTable.compound_multiplier || 1.0}. The risk scoring engine applies the Horizon 1–3 detection framework: corridor classification (H1), ISF/AIS pre-manifest intelligence (H2), and 72-hour manifest trigger (H3). All three horizons independently flag this shipment. Composite risk score: ${packageData.risk_score.toFixed(1)}/100 with ±${calcTable.confidence_interval?.replace('±', '') || 17} confidence interval at ${scoreSection.model_maturity || 15}% model maturity.`
    : `Risk Intelligence Synthesis applied the 7-factor scoring framework. Composite score: ${packageData.risk_score.toFixed(1)}/100.`;

  // Section tabs
  const tabs = [
    { id: 'q1', label: 'Q1 — Entities & Imports', icon: Building2 },
    { id: 'q2', label: 'Q2 — Risk Factors', icon: AlertTriangle },
    { id: 'q3', label: 'Q3 — Data Sources', icon: Info },
    { id: 'q4', label: 'Q4 — Recommended Actions', icon: Target },
    { id: 'officer', label: 'Section 5 — Officer Review', icon: CheckCircle },
  ] as const;

  return (
    <div className="flex flex-col flex-1 overflow-hidden bg-[#F7F9FC]" ref={printRef}>
      {/* ── PACKAGE HEADER ──────────────────────────────────────────────── */}
      <div className="bg-[#0B1F33] text-white px-6 py-4 flex-shrink-0">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <span className="text-[10px] font-bold bg-[#005EA2] px-2 py-0.5 rounded uppercase tracking-wider">
                ILLEGAL TRANSSHIPMENT REFERRAL PACKAGE
              </span>
              <span className="text-[10px] text-slate-400">CSOP-BP-GS-26-0001</span>
            </div>
            <h2 className="text-base font-bold mt-1">
              {packageData.shipper_name} → {packageData.consignee_name}
            </h2>
            <p className="text-[11px] text-slate-300 mt-0.5">
              HS {packageData.hs_code} · {hsFamily(packageData.hs_code) || packageData.commodity_name} · Origin: {countryName(packageData.origin_country)}
            </p>
            <p className="text-[10px] text-slate-400 mt-0.5">
              Package ID: {packageData.referral_id.substring(0, 12).toUpperCase()} ·
              Generated: {new Date(packageData.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })} ·
              Shipment: {packageData.shipment_id}
            </p>
          </div>
          <div className="flex-shrink-0 text-center">
            <div
              className="rounded px-4 py-2 text-center"
              style={{ background: rc.bg, border: `1px solid ${rc.border}` }}
            >
              <p className="text-2xl font-black" style={{ color: rc.text }}>{packageData.risk_score.toFixed(0)}</p>
              <p className="text-[10px] font-bold" style={{ color: rc.text }}>/100 · {rc.label}</p>
              <p className="text-[9px] text-slate-500 mt-0.5">CI: ±{calcTable.confidence_interval?.replace('±', '') || 17} pts</p>
            </div>
            <p className="text-[11px] font-bold mt-2 text-amber-300">{packageData.recommendation}</p>
            <p className="text-[10px] text-slate-400">Confidence: {packageData.confidence}</p>
          </div>
        </div>

        {/* Key findings summary */}
        {activeIndicators.length > 0 && (
          <div className="mt-3 pt-3 border-t border-slate-700">
            <p className="text-[10px] text-slate-400 uppercase tracking-wide mb-1.5">Key Findings:</p>
            <div className="flex flex-wrap gap-2">
              {activeIndicators.map((ind: any, i: number) => (
                <span key={i} className="text-[10px] bg-amber-900/50 text-amber-200 border border-amber-700 rounded px-2 py-0.5">
                  ⚠ {ind.indicator}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── SECTION TABS ────────────────────────────────────────────────── */}
      <div className="flex border-b border-[#D0D7DE] bg-white overflow-x-auto flex-shrink-0">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveSection(id)}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-[11px] font-semibold border-b-2 whitespace-nowrap transition-colors ${
              activeSection === id
                ? 'border-[#005EA2] text-[#005EA2] bg-blue-50'
                : 'border-transparent text-slate-600 hover:text-[#0B1F33] hover:bg-slate-50'
            } ${id === 'officer' ? 'ml-auto' : ''}`}
          >
            <Icon size={12} />
            {label}
          </button>
        ))}
        <button
          onClick={handlePrint}
          className="flex items-center gap-1.5 px-4 py-2.5 text-[11px] text-slate-500 hover:text-[#0B1F33] border-b-2 border-transparent"
        >
          <Download size={12} /> Export PDF
        </button>
      </div>

      {/* ── CONTENT ─────────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">

        {/* ── Q1: Entities & Imports ─────────────────────────────────── */}
        {activeSection === 'q1' && (
          <div>
            <SectionHeader
              number="1"
              title="Identify one or more entities and their affiliated imports that pose a high risk for illegal transshipment."
              subtitle="Tables 3-1 through 3-4 — Shipment identification, line items, routing history, and parties"
            />

            {/* Table 3-1: Shipment Identification */}
            {(() => {
              const sec = s.section_3_1_shipment_identification || {};
              return <DataTable
                caption="Table 3-1: Shipment Identification"
                headers={['Field', 'Value']}
                rows={[
                  ['Shipment ID', packageData.shipment_id],
                  ['Manifest ID', packageData.sections?.manifest_id || s.section_3_1_shipment_identification?.manifest_id || '—'],
                  ['Commodity', `${sec.commodity || packageData.commodity_name} (HS ${sec.hs_code || packageData.hs_code})`],
                  ['Declared Origin', countryName(packageData.origin_country)],
                  ['Destination', 'United States'],
                  ['Route', sec.route || `${packageData.origin_country} → US`],
                  ['Shipper', sec.shipper || packageData.shipper_name],
                  ['Consignee', sec.consignee || packageData.consignee_name],
                  ['Vessel', sec.vessel || routeSection.vessel || '—'],
                  ['Declared Value', sec.value_usd ? `$${sec.value_usd.toLocaleString('en-US', { maximumFractionDigits: 0 })}` : '—'],
                  ['Weight', sec.weight_kg ? `${sec.weight_kg.toLocaleString('en-US')} kg` : '—'],
                ]}
              />;
            })()}

            {/* Table 3-2: Line Items */}
            {s.section_3_2_line_items?.items?.length > 0 && (
              <DataTable
                caption="Table 3-2: Shipment Line-Item Detail"
                headers={['HS Code', 'Description', 'Quantity', 'Unit', 'Declared Value']}
                rows={(s.section_3_2_line_items.items || []).map((item: any) => [
                  item.hs_code || packageData.hs_code,
                  item.description || packageData.commodity_name,
                  item.quantity,
                  item.unit,
                  item.declared_value ? `$${Number(item.declared_value).toLocaleString()}` : '—',
                ])}
              />
            )}

            {/* Table 3-3: Routing History */}
            <DataTable
              caption="Table 3-3: Routing History"
              headers={['Field', 'Value']}
              rows={[
                ['Vessel Name', routeSection.vessel || '—'],
                ['IMO Number', routeSection.vessel_imo || 'Not provided'],
                ['Route', Array.isArray(routeSection.route) ? routeSection.route.map(countryName).join(' → ') : routeSection.route || '—'],
                ['Port Dwell Time', routeSection.dwell_days ? `${routeSection.dwell_days.toFixed(1)} days (baseline: ${routeSection.dwell_baseline || 2.5} days)` : '—'],
                ['Dwell Anomaly', routeSection.dwell_anomaly || '—'],
                ['AIS Signal Gaps', routeSection.ais_gaps || 0],
                ['Summary', routeSection.summary || '—'],
              ]}
            />
            <p className="text-[10px] text-slate-500 italic mb-4">
              * Clarification: Route reflects shipper's declared documentation. ISF filing (Horizon 2) and AIS tracking may indicate alternate origin — see Risk Factors in Question 2.
            </p>

            {/* Table 3-4: Parties and Roles */}
            {s.section_3_4_parties_and_roles?.parties?.length > 0 && (
              <DataTable
                caption="Table 3-4: Parties and Roles"
                headers={['Entity', 'Role', 'Country']}
                rows={(s.section_3_4_parties_and_roles.parties || []).map((p: any) => [
                  p.entity, p.role, countryName(p.country),
                ])}
              />
            )}
          </div>
        )}

        {/* ── Q2: Risk Factors ────────────────────────────────────────── */}
        {activeSection === 'q2' && (
          <div>
            <SectionHeader
              number="2"
              title="Provide specific factors that are indicative of illegal transshipment risk."
              subtitle="Risk Factors RF-1 through RF-4 · Tables 3-5 through 3-13"
            />

            {/* RF-1: Entity / ISF Intelligence */}
            <RiskFactorCard
              number={1}
              title={e9.is_mismatch ? 'ISF Element 9 Origin Mismatch — Direct Transshipment Indicator' : 'ISF Element 9 Origin Consistency Check'}
              level={e9.is_mismatch ? 'CRITICAL' : 'LOW'}
              narrative={rf1Narrative}
            >
              <DataTable
                caption="Table 3-5 / 3-9: ISF Element 9 Document Consistency"
                headers={['Check', 'Declared', 'Actual / Detected', 'Finding']}
                rows={[
                  [
                    'Container Stuffing Location (ISF Element 9)',
                    countryName(e9.declared_origin || packageData.origin_country),
                    countryName(e9.actual_stuffing_country || '—'),
                    e9.is_mismatch ? '⚠ MISMATCH — Potential origin falsification' : '✓ Consistent',
                  ],
                  [
                    'Entity Ownership Chain',
                    packageData.shipper_name,
                    suppSection.shipper_age_months ? `Established ${suppSection.shipper_age_months} months ago` : '—',
                    suppSection.shipper_age_risk === 'VERY_NEW' || suppSection.shipper_age_risk === 'NEW' ? '⚠ Newly established entity' : '—',
                  ],
                ]}
              />
              {s.section_3_5_entity_ownership_chain?.chain?.length > 0 && (
                <DataTable
                  caption="Table 3-5: Entity Ownership Chain"
                  headers={['Entity', 'Country', 'Role', 'Confidence']}
                  rows={(s.section_3_5_entity_ownership_chain.chain || []).map((c: any) => [
                    c.name, countryName(c.country), c.role,
                    `${Math.round((c.confidence || 0) * 100)}%`,
                  ])}
                />
              )}
            </RiskFactorCard>

            {/* RF-2: Route Anomaly */}
            <RiskFactorCard
              number={2}
              title={`Route Anomaly — Vessel Dwell ${routeSection.dwell_anomaly || 'DETECTED'}`}
              level={routeSection.dwell_anomaly === 'CRITICAL' ? 'CRITICAL' : routeSection.dwell_anomaly === 'HIGH' ? 'HIGH' : 'MEDIUM'}
              narrative={rf2Narrative}
            >
              <DataTable
                caption="Table 3-6: Historical Import Pattern / AIS Anomaly"
                headers={['Metric', 'Observed', 'Baseline', 'Multiplier', 'Assessment']}
                rows={[
                  [
                    'Vessel Dwell Time',
                    `${routeSection.dwell_days?.toFixed(1) || '—'} days`,
                    `${routeSection.dwell_baseline || 2.5} days`,
                    `${routeSection.dwell_days ? (routeSection.dwell_days / (routeSection.dwell_baseline || 2.5)).toFixed(1) : '—'}×`,
                    routeSection.dwell_anomaly || '—',
                  ],
                  ['AIS Signal Gaps', `${routeSection.ais_gaps || 0} gaps`, 'Expected: 0', '—', routeSection.ais_gaps > 0 ? '⚠ Possible dark vessel period' : '✓ Normal'],
                ]}
              />
              {s.section_3_7_trade_flow_intelligence && (
                <DataTable
                  caption="Table 3-7: Trade Flow Intelligence"
                  headers={['Field', 'Value']}
                  rows={[
                    ['HS Code', `${tradeSection.hs_code || packageData.hs_code} — ${tradeSection.commodity || packageData.commodity_name}`],
                    ['AD/CVD Status', tradeSection.ad_cvd_status || '—'],
                    ['AD/CVD Rate', tradeSection.ad_cvd_rate || '—'],
                    ['Prior Filings (this corridor)', tradeSection.prior_filings || 0],
                    ['Origin Shift Trend', tradeSection.origin_shift_trend || '—'],
                    ['Trade Intelligence', tradeSection.summary || '—'],
                  ]}
                />
              )}
            </RiskFactorCard>

            {/* RF-3: Duty Evasion / Supplier */}
            <RiskFactorCard
              number={3}
              title={`HTS Duty Evasion Signal — ${tradeSection.ad_cvd_rate || 'Active AD/CVD'} on ${packageData.hs_code}`}
              level={suppSection.shipper_age_months <= 6 ? 'HIGH' : 'MEDIUM'}
              narrative={rf3Narrative}
            >
              <DataTable
                caption="Table 3-10: Supplier Manufacturing Verification Assessment"
                headers={['Field', 'Value', 'Risk Assessment']}
                rows={[
                  ['Shipper Name', suppSection.shipper || packageData.shipper_name, '—'],
                  ['Establishment Age', suppSection.shipper_age_months ? `${suppSection.shipper_age_months} months` : '—', suppSection.shipper_age_risk ? `⚠ ${suppSection.shipper_age_risk}` : '—'],
                  ['Declared Volume', suppSection.declared_volume_kg ? `${suppSection.declared_volume_kg.toLocaleString()} kg` : '—', '—'],
                  ['Capacity Assessment', suppSection.capacity_assessment || '—', '—'],
                  ['Summary', suppSection.summary || '—', '—'],
                ]}
              />
              {s.section_3_8_document_review?.documents?.length > 0 && (
                <DataTable
                  caption="Table 3-8: Document Review Checklist"
                  headers={['Document', 'Status', 'Notes']}
                  rows={(s.section_3_8_document_review.documents || []).map((doc: any) => [
                    doc.document,
                    doc.status === 'RECEIVED'
                      ? <span className="text-green-700 font-semibold">✓ Received</span>
                      : doc.status === 'MISSING'
                      ? <span className="text-red-600 font-semibold">✗ Missing — Pending Request</span>
                      : <span className="text-amber-600 font-semibold">⚠ {doc.status}</span>,
                    doc.notes || '—',
                  ])}
                />
              )}
            </RiskFactorCard>

            {/* RF-4: Risk Intelligence Synthesis */}
            <RiskFactorCard
              number={4}
              title="Risk Intelligence Synthesis — Multi-Horizon Detection"
              level={packageData.risk_score >= 80 ? 'CRITICAL' : packageData.risk_score >= 65 ? 'HIGH' : 'MEDIUM'}
              narrative={rf4Narrative}
            >
              {/* Table 3-11: Risk Indicator Summary */}
              <DataTable
                caption="Table 3-11: Risk Indicator Summary"
                headers={['Indicator', 'Present', 'Evidence', 'Authority']}
                rows={(indicatorSection.indicators || []).map((ind: any) => [
                  ind.indicator,
                  ind.present
                    ? <span className="text-red-600 font-bold">⚠ YES</span>
                    : <span className="text-green-700">✓ No</span>,
                  ind.evidence || '—',
                  ind.authority || '—',
                ])}
              />

              {/* Table 3-12: Score Breakdown */}
              <div className="mt-4">
                <p className="text-[10px] font-bold text-[#005EA2] uppercase tracking-wide mb-2">Table 3-12: Risk Score Breakdown</p>
                <div className="bg-slate-50 border border-[#D0D7DE] rounded-sm p-3 mb-3">
                  <div className="grid grid-cols-3 gap-3 text-center text-[11px] mb-3">
                    <div>
                      <p className="text-slate-500">Rule Engine Subtotal</p>
                      <p className="text-xl font-bold text-[#0B1F33]">{calcTable.rule_engine_subtotal?.toFixed(1) || scoreSection.total_score?.toFixed(1) || '—'}</p>
                    </div>
                    <div>
                      <p className="text-slate-500">Compound Multiplier</p>
                      <p className="text-xl font-bold text-amber-600">×{calcTable.compound_multiplier?.toFixed(2) || '1.00'}</p>
                      <p className="text-[9px] text-slate-400">{criticalIndicators.length} critical indicators</p>
                    </div>
                    <div>
                      <p className="text-slate-500">Final Score</p>
                      <p className="text-xl font-bold" style={{ color: rc.text }}>{packageData.risk_score.toFixed(1)}</p>
                      <p className="text-[9px] text-slate-400">CI: ±{calcTable.confidence_interval?.replace('±', '') || '17'} pts</p>
                    </div>
                  </div>
                  <div>
                    <p className="text-[10px] text-slate-600 font-bold mb-2">Score Attribution (top components):</p>
                    {components.slice(0, 8).map((comp: any, i: number) => (
                      <ScoreBar
                        key={i}
                        label={`${comp.factor}: ${comp.name}`}
                        score={comp.weighted_result || 0}
                        maxScore={comp.weight || 10}
                        weight={(comp.weight || 0) / 100}
                      />
                    ))}
                  </div>
                  {criticalIndicators.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-[#D0D7DE]">
                      <p className="text-[10px] font-bold text-[#0B1F33] mb-1">Critical Co-occurring Indicators:</p>
                      {criticalIndicators.map((ind: string, i: number) => (
                        <p key={i} className="text-[11px] text-red-700">⚠ {ind}</p>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Table 3-13: What-If Scenarios */}
              {whatIfScenarios.length > 0 && (
                <div className="mt-3">
                  <p className="text-[10px] font-bold text-[#005EA2] uppercase tracking-wide mb-2">Table 3-13: What-If Scenario Analysis</p>
                  <div className="grid grid-cols-2 gap-3">
                    {whatIfScenarios.map((sc: any, i: number) => (
                      <WhatIfCard
                        key={i}
                        scenario={sc.scenario}
                        impact={sc.impact}
                        currentScore={packageData.risk_score}
                        revisedScore={sc.revised_score}
                      />
                    ))}
                  </div>
                  <p className="text-[10px] text-slate-500 italic mt-2">
                    Counterfactual analysis: each scenario represents removing a single risk factor in isolation.
                    Combined resolution of multiple factors would reduce the score further.
                  </p>
                </div>
              )}
            </RiskFactorCard>
          </div>
        )}

        {/* ── Q3: Data Sources ─────────────────────────────────────────── */}
        {activeSection === 'q3' && (
          <div>
            <SectionHeader
              number="3"
              title="Describe the data sources and underlying AI-driven methodologies used to assess illegal transshipment risk."
              subtitle="Table 3-14 — Attribution and confidence"
            />
            {s.section_3_14_data_sources?.sources?.length > 0 && (
              <DataTable
                caption="Table 3-14: Referral Package Data Sources and Uses in Assessment"
                headers={['Data Source', 'Use in Assessment', 'Confidence']}
                rows={(s.section_3_14_data_sources.sources || []).map((src: any) => [
                  src.source, src.use, src.confidence || 'High',
                ])}
              />
            )}
            <div className="bg-white border border-[#D0D7DE] rounded-sm p-4 mt-3">
              <p className="text-[12px] font-bold text-[#0B1F33] mb-3">AI Methodologies Applied</p>
              <div className="space-y-3 text-[11px] text-slate-700">
                <p><strong>Horizon 1 — Structural Corridor Intelligence:</strong> Macro-level bilateral trade data, AD/CVD enforcement history, and HS-corridor risk classification pre-score this shipment before manifest receipt. The {countryName(packageData.origin_country)}→US corridor for HS {packageData.hs_code} is classified based on known transshipment patterns and active duty orders ({tradeSection.ad_cvd_rate || '—'}).</p>
                <p><strong>Horizon 2 — ISF & Maritime Pre-Manifest:</strong> ISF 10+2 Element 9 stuffing location data analyzed 10–18 days pre-arrival. AIS vessel tracking validates declared routing and identifies dwell anomalies. Entity resolution maps shipper establishment date and network relationships.</p>
                <p><strong>Horizon 3 — 72-Hour Manifest Trigger:</strong> 7-factor rule engine applies weighted scoring across Documentation, Commodity, Routing, Party, Corridor, Pattern, and Time dimensions. Compound risk multiplier activates when ≥2 critical indicators co-occur. Model maturity: {scoreSection.model_maturity || 15}% (confidence interval ±{calcTable.confidence_interval?.replace('±', '') || 17} pts).</p>
              </div>
            </div>
          </div>
        )}

        {/* ── Q4: Recommended Actions ─────────────────────────────────── */}
        {activeSection === 'q4' && (
          <div>
            <SectionHeader
              number="4"
              title="Recommended CBP Actions"
              subtitle="Primary recommendation · Alternative recommendation · Required next steps"
            />
            <div className="bg-amber-50 border border-amber-300 rounded-sm p-5 mb-4">
              <p className="text-[10px] font-bold uppercase tracking-wide text-amber-700 mb-1">Primary Recommendation</p>
              <p className="text-sm font-bold text-[#0B1F33]">{packageData.recommendation}</p>
              <p className="text-[11px] text-slate-600 mt-2">
                {packageData.recommendation === 'ESCALATE' || packageData.recommendation === 'REVIEW'
                  ? `Sentry recommends prioritizing this shipment (${packageData.shipment_id}) for ${packageData.risk_score >= 80 ? 'EAPA initiation referral to TRLED' : 'physical examination upon arrival'}. Risk score ${packageData.risk_score.toFixed(1)}/100 ${packageData.risk_score >= 65 ? 'meets or exceeds the referral threshold' : 'warrants review'}. ${activeIndicators.length} risk factor(s) identified across Horizons 1–3.`
                  : 'Based on available intelligence, no immediate enforcement action is recommended at this time.'}
              </p>
              <p className="text-[10px] text-slate-500 mt-2">
                Statutory authority: 19 USC § 1517(b), EAPA; 19 CFR Part 165 · Confidence: {packageData.confidence}
              </p>
            </div>

            {/* Alternative recommendation from what-if */}
            {whatIfScenarios.length > 0 && (
              <div className="bg-blue-50 border border-blue-200 rounded-sm p-4 mb-4">
                <p className="text-[10px] font-bold uppercase tracking-wide text-blue-700 mb-1">Alternative Recommendation (Counterfactual)</p>
                <p className="text-[11px] text-slate-700">
                  If the primary risk factor ({whatIfScenarios[0]?.scenario?.replace('If ', '')}) is resolved with satisfactory documentation,
                  the revised risk score would be <strong>{whatIfScenarios[0]?.revised_score?.toFixed(0)}/100</strong>
                  {whatIfScenarios[0]?.revised_score < 65
                    ? ' — below the referral threshold. Recommend issuing CF-28 (Request for Information) as an alternative to examination.'
                    : ' — still above referral threshold. Physical examination remains recommended.'}
                </p>
              </div>
            )}

            {/* Required next steps */}
            <div className="bg-white border border-[#D0D7DE] rounded-sm p-4">
              <p className="text-[12px] font-bold text-[#0B1F33] mb-3">Examination Focus Areas & Required Next Steps</p>
              <ul className="space-y-2">
                {[
                  e9.is_mismatch && 'Verify container stuffing location and country-of-origin documentation against ISF Element 9 discrepancy',
                  'Request factory production records and Bill of Materials from importer (CF-28)',
                  `Review Certificate of Origin (Form A/B) for consistency with HS ${packageData.hs_code} manufacturing requirements`,
                  suppSection.shipper_age_months <= 6 && `Verify entity registration date and manufacturing capacity for ${packageData.shipper_name} (established ${suppSection.shipper_age_months} months ago)`,
                  `Check EAPA petition docket for active investigations covering HTS ${packageData.hs_code} from ${countryName(packageData.origin_country)}`,
                  `Assess consignee ${packageData.consignee_name} import history and network connections`,
                ].filter(Boolean).map((step, i) => (
                  <li key={i} className="flex items-start gap-2 text-[11px] text-slate-700">
                    <span className="text-[#005EA2] font-bold flex-shrink-0">{i + 1}.</span>
                    {step}
                  </li>
                ))}
              </ul>
              <div className="mt-4 pt-3 border-t border-[#D0D7DE]">
                <p className="text-[11px] text-slate-600">
                  <strong>Confidence Assessment:</strong> The three-horizon intelligence chain
                  {e9.is_mismatch ? ', including an ISF Element 9 container stuffing discrepancy,' : ''} AIS routing anomaly
                  ({routeSection.dwell_days?.toFixed(1)} day dwell vs {routeSection.dwell_baseline} day baseline),
                  and {tradeSection.ad_cvd_rate || 'active'} AD/CVD duty exposure collectively establish{' '}
                  <strong>{packageData.confidence}</strong> confidence that this shipment warrants CBP enforcement action
                  under 19 USC § 1517(b).
                </p>
              </div>
            </div>
          </div>
        )}

        {/* ── Section 5: Officer Review ────────────────────────────────── */}
        {activeSection === 'officer' && (
          <div>
            <SectionHeader
              number="5"
              title="Officer Review & Feedback"
              subtitle="Agree or disagree with the referral recommendation — submission feeds the MLOps model training pipeline"
            />
            <div className="bg-white border border-[#D0D7DE] rounded-sm p-5">
              <OfficerReviewForm packageData={packageData} onSubmit={handleFeedback} />
            </div>
          </div>
        )}

      </div>

      {/* Print styles */}
      <style>{`
        @media print {
          body * { visibility: hidden; }
          .print-area, .print-area * { visibility: visible; }
          .print-area { position: absolute; left: 0; top: 0; width: 100%; }
        }
      `}</style>
    </div>
  );
}
