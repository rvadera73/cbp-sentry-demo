/**
 * EvidenceTab — Three-pillar evidence assembly for CSOP referral packages.
 *
 * Pillar 1: Documentary Evidence    (Tables 3-8, 3-9)
 * Pillar 2: Risk Indicators         (Table 3-11, feeds compound multiplier)
 * Pillar 3: Entity & Routing Intel  (Tables 3-3, 3-4)
 *
 * Bottom panel: Evidence Readiness — drives "Generate Referral" action.
 */
import React, { useState } from 'react';
import {
  FileText, AlertTriangle, Building2, CheckCircle2,
  XCircle, Clock, ChevronDown, ChevronRight, Ship,
  MapPin, AlertCircle, Info, ArrowRight
} from 'lucide-react';
import { useRiskScoring } from '../hooks/useRiskScoring';

// ─── Required documents by HS code family ────────────────────────────────────
const REQUIRED_DOCS: Record<string, { doc: string; critical: boolean; note?: string }[]> = {
  '7604': [
    { doc: 'Commercial Invoice', critical: true },
    { doc: 'Bill of Lading (BOL)', critical: true },
    { doc: 'Packing List', critical: true },
    { doc: 'Certificate of Origin (Form B)', critical: true, note: 'Must declare manufacturing country' },
    { doc: 'Factory Production Records', critical: true, note: 'Required for aluminum extrusions EAPA' },
    { doc: 'Bill of Materials (BOM)', critical: true, note: 'Must trace raw material origin' },
    { doc: 'Raw Material Purchase Invoices', critical: true },
    { doc: 'Production Test / QC Reports', critical: false },
    { doc: 'Factory Registration Certificate', critical: false },
  ],
  '8541': [
    { doc: 'Commercial Invoice', critical: true },
    { doc: 'Bill of Lading (BOL)', critical: true },
    { doc: 'Packing List', critical: true },
    { doc: 'Certificate of Origin', critical: true },
    { doc: 'Technical Specifications Sheet', critical: true, note: 'Cell efficiency, wattage, manufacturer' },
    { doc: 'Factory Certification (IEC 61215/61730)', critical: false },
    { doc: 'Wafer/Cell Sourcing Declaration', critical: true, note: 'UFLPA requirement' },
  ],
  '7210': [
    { doc: 'Commercial Invoice', critical: true },
    { doc: 'Bill of Lading (BOL)', critical: true },
    { doc: 'Packing List', critical: true },
    { doc: 'Certificate of Origin', critical: true },
    { doc: 'Mill Test Certificate (MTC)', critical: true, note: 'Chemical composition + mechanical properties' },
    { doc: 'Metallurgical Analysis Report', critical: false },
    { doc: 'Raw Material Sourcing Declaration', critical: true },
  ],
  '7225': [
    { doc: 'Commercial Invoice', critical: true },
    { doc: 'Bill of Lading (BOL)', critical: true },
    { doc: 'Packing List', critical: true },
    { doc: 'Certificate of Origin', critical: true },
    { doc: 'Mill Test Certificate (MTC)', critical: true },
    { doc: 'Steel Slab Sourcing Declaration', critical: true },
  ],
  default: [
    { doc: 'Commercial Invoice', critical: true },
    { doc: 'Bill of Lading (BOL)', critical: true },
    { doc: 'Packing List', critical: true },
    { doc: 'Certificate of Origin', critical: true },
    { doc: 'Factory / Supplier Documentation', critical: false },
  ],
};

// Documents typically available from ISF/manifest (auto-received)
const AUTO_RECEIVED = new Set(['Commercial Invoice', 'Bill of Lading (BOL)', 'Packing List']);

// ─── Helpers ─────────────────────────────────────────────────────────────────
function getDocList(hsCode: string) {
  const family = (hsCode || '').replace('.', '').substring(0, 4);
  return REQUIRED_DOCS[family] || REQUIRED_DOCS['default'];
}

function docStatus(doc: { doc: string; critical: boolean }, e9Mismatch: boolean) {
  if (AUTO_RECEIVED.has(doc.doc)) {
    if (doc.doc === 'Certificate of Origin' && e9Mismatch) return 'inconsistent';
    return 'received';
  }
  if (doc.doc.includes('Certificate of Origin')) return e9Mismatch ? 'inconsistent' : 'received';
  return 'missing';
}

function PillarHeader({ icon: Icon, title, count, countLabel, color }: any) {
  return (
    <div className="flex items-center gap-3 mb-4">
      <div className={`w-8 h-8 rounded flex items-center justify-center ${color}`}>
        <Icon size={16} className="text-white" />
      </div>
      <div>
        <h3 className="text-sm font-bold text-[#0B1F33]">{title}</h3>
        {count !== undefined && (
          <p className="text-xs text-slate-500">{count} {countLabel}</p>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: 'received' | 'missing' | 'inconsistent' | 'partial' }) {
  const cfg = {
    received:     'bg-green-100 text-green-800',
    missing:      'bg-red-100 text-red-800',
    inconsistent: 'bg-amber-100 text-amber-800',
    partial:      'bg-yellow-100 text-yellow-800',
  };
  const labels = { received: 'Received', missing: 'Missing', inconsistent: 'Inconsistent', partial: 'Partial' };
  return <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${cfg[status]}`}>{labels[status]}</span>;
}

// ─── Main Component ───────────────────────────────────────────────────────────
interface EvidenceTabProps {
  selectedCase: any;
  selectedCaseShipments: any[];
  onGenerateReferral?: () => void;
}

export default function EvidenceTab({ selectedCase, selectedCaseShipments, onGenerateReferral }: EvidenceTabProps) {
  const shipment = selectedCaseShipments?.[0];
  const { scoreData, loading: scoreLoading } = useRiskScoring(shipment?.shipment_id || null);

  const [expandedPillars, setExpandedPillars] = useState<Record<string, boolean>>({
    docs: true, risk: true, entity: true,
  });
  const toggle = (key: string) =>
    setExpandedPillars(p => ({ ...p, [key]: !p[key] }));

  if (!shipment) return <div className="p-6 text-slate-500">No shipment selected</div>;

  // ── Data extraction ──────────────────────────────────────────────────────
  const hsCode = shipment.hs_code || shipment.commodity_code || '';
  const e9Mismatch = !!shipment.element9_is_mismatch;
  const e9Declared = shipment.element9_declared_country || shipment.origin_country || '—';
  const e9Actual = shipment.element9_actual_country || '—';
  const dwellDays = Number(shipment.dwell_days || 0);
  const adCvdRate = Number(shipment.ad_cvd_rate || 0) * 100; // convert to %
  const shipperAge = Number(shipment.shipper_age_months || 0);
  const unitPrice = Number(shipment.unit_price_per_kg || 0);
  const priceVar = Number(shipment.price_variance_percent || 0);
  const portCalls: string[] = shipment.port_calls ? (
    typeof shipment.port_calls === 'string' ? JSON.parse(shipment.port_calls) : shipment.port_calls
  ) : [];

  const criticalIndicators: string[] = scoreData?.critical_indicators || [];
  const docList = getDocList(hsCode);

  // Readiness scoring — document gaps are informational, not a hard blocker at 15% maturity
  const receivedDocs = docList.filter(d => docStatus(d, e9Mismatch) === 'received').length;
  const missingCritical = docList.filter(d => d.critical && docStatus(d, e9Mismatch) === 'missing').length;
  const hasRiskScore = !!(selectedCase?.risk_score && selectedCase.risk_score > 0);
  const hasIndicators = criticalIndicators.length > 0 || !scoreLoading;
  const docReadiness = missingCritical === 0 ? 'complete' : missingCritical <= 3 ? 'partial' : 'needs-review';
  // At 15% model maturity: require only a risk score + shipment identified.
  // Missing docs are tracked and noted in the referral package (collected during investigation).
  const overallReady = hasRiskScore && !!shipment.shipment_id;

  return (
    <div className="flex flex-col flex-1 overflow-y-auto bg-[#F7F9FC]">
      <div className="p-6 space-y-4">

        {/* ── PILLAR 1: Documentary Evidence ──────────────────────────── */}
        <div className="bg-white border border-[#D0D7DE] rounded-sm">
          <button
            className="w-full flex items-center justify-between p-4 hover:bg-slate-50"
            onClick={() => toggle('docs')}
          >
            <PillarHeader
              icon={FileText}
              title="Pillar 1 — Documentary Evidence"
              count={`${receivedDocs}/${docList.length}`}
              countLabel="documents received"
              color="bg-[#005EA2]"
            />
            {expandedPillars.docs ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          </button>

          {expandedPillars.docs && (
            <div className="border-t border-[#D0D7DE] p-4 space-y-4">

              {/* Table 3-8: Document Checklist */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-[10px] font-bold text-[#005EA2] uppercase tracking-wide">Table 3-8 — Document Review</span>
                  <span className="text-[9px] text-slate-500">HS {hsCode}</span>
                </div>
                <table className="w-full text-[11px] border-collapse">
                  <thead>
                    <tr className="bg-[#005EA2] text-white">
                      <th className="text-left px-3 py-2">Document</th>
                      <th className="text-center px-2 py-2 w-24">Status</th>
                      <th className="text-center px-2 py-2 w-16">Priority</th>
                      <th className="text-left px-3 py-2">Note</th>
                    </tr>
                  </thead>
                  <tbody>
                    {docList.map((d, i) => {
                      const st = docStatus(d, e9Mismatch) as any;
                      return (
                        <tr key={i} className={i % 2 === 0 ? 'bg-slate-50' : 'bg-white'}>
                          <td className="px-3 py-1.5 font-medium">{d.doc}</td>
                          <td className="px-2 py-1.5 text-center"><StatusBadge status={st} /></td>
                          <td className="px-2 py-1.5 text-center">
                            {d.critical
                              ? <span className="text-[9px] font-bold text-red-600">CRITICAL</span>
                              : <span className="text-[9px] text-slate-400">Supporting</span>}
                          </td>
                          <td className="px-3 py-1.5 text-[10px] text-slate-500">
                            {st === 'missing' && d.critical
                              ? <span className="text-red-600 font-medium">⚠ Must request from importer</span>
                              : d.note || '—'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                {missingCritical > 0 && (
                  <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-[10px] text-red-700">
                    <strong>{missingCritical} critical document(s) missing.</strong> These gaps prevent independent verification of country-of-origin claim and are required for CSOP referral completeness.
                  </div>
                )}
              </div>

              {/* Table 3-9: ISF Consistency Matrix */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-[10px] font-bold text-[#005EA2] uppercase tracking-wide">Table 3-9 — ISF Element 9 Consistency</span>
                  {e9Mismatch && <span className="px-2 py-0.5 rounded text-[9px] font-bold bg-red-100 text-red-700">MISMATCH DETECTED</span>}
                </div>
                <table className="w-full text-[11px] border-collapse">
                  <thead>
                    <tr className="bg-[#005EA2] text-white">
                      <th className="text-left px-3 py-2">ISF Element</th>
                      <th className="text-left px-2 py-2">ISF Filing</th>
                      <th className="text-left px-2 py-2">Commercial Invoice</th>
                      <th className="text-left px-2 py-2">BOL</th>
                      <th className="text-center px-2 py-2">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      {
                        element: 'Element 9 — Country of Manufacture',
                        isf: e9Declared,
                        invoice: e9Mismatch ? e9Declared : e9Declared,
                        bol: e9Mismatch ? e9Actual : e9Declared,
                        status: e9Mismatch ? 'inconsistent' : 'received',
                      },
                      {
                        element: 'Shipper Name',
                        isf: shipment.shipper_name || '—',
                        invoice: shipment.shipper_name || '—',
                        bol: shipment.shipper_name || '—',
                        status: 'received' as const,
                      },
                      {
                        element: 'Commodity (HS Code)',
                        isf: hsCode,
                        invoice: hsCode,
                        bol: hsCode,
                        status: 'received' as const,
                      },
                      {
                        element: 'Declared Value',
                        isf: shipment.declared_value_usd ? `$${Number(shipment.declared_value_usd).toLocaleString()}` : '—',
                        invoice: shipment.declared_value_usd ? `$${Number(shipment.declared_value_usd).toLocaleString()}` : '—',
                        bol: 'STC',
                        status: 'received' as const,
                      },
                    ].map((row, i) => (
                      <tr key={i} className={i % 2 === 0 ? 'bg-slate-50' : 'bg-white'}>
                        <td className="px-3 py-1.5 font-medium">{row.element}</td>
                        <td className="px-2 py-1.5">{row.isf}</td>
                        <td className="px-2 py-1.5">{row.invoice}</td>
                        <td className="px-2 py-1.5">{row.bol}</td>
                        <td className="px-2 py-1.5 text-center"><StatusBadge status={row.status as any} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {e9Mismatch && (
                  <div className="mt-2 p-3 bg-amber-50 border border-amber-200 rounded text-[10px] text-amber-800">
                    <strong>ISF Element 9 Discrepancy:</strong> Manifest declares origin as <strong>{e9Declared}</strong> but vessel tracking indicates actual stuffing country as <strong>{e9Actual}</strong>. This is a primary transshipment indicator under EAPA 19 U.S.C. § 1517.
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* ── PILLAR 2: Risk Indicators ────────────────────────────────── */}
        <div className="bg-white border border-[#D0D7DE] rounded-sm">
          <button
            className="w-full flex items-center justify-between p-4 hover:bg-slate-50"
            onClick={() => toggle('risk')}
          >
            <PillarHeader
              icon={AlertTriangle}
              title="Pillar 2 — Risk Indicators (Table 3-11)"
              count={criticalIndicators.length}
              countLabel="critical indicators triggered"
              color={criticalIndicators.length >= 3 ? 'bg-red-600' : criticalIndicators.length >= 1 ? 'bg-amber-500' : 'bg-slate-400'}
            />
            {expandedPillars.risk ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          </button>

          {expandedPillars.risk && (
            <div className="border-t border-[#D0D7DE] p-4 space-y-3">
              {scoreLoading ? (
                <div className="text-xs text-slate-500 animate-pulse">Loading risk indicators…</div>
              ) : criticalIndicators.length === 0 ? (
                <div className="text-xs text-slate-500 p-3 bg-slate-50 rounded">No critical indicators triggered for this shipment.</div>
              ) : (
                <div className="space-y-2">
                  {criticalIndicators.map((indicator, i) => (
                    <div key={i} className="flex items-start gap-3 p-3 bg-red-50 border border-red-200 rounded">
                      <AlertCircle size={14} className="text-red-600 mt-0.5 flex-shrink-0" />
                      <div className="flex-1">
                        <p className="text-[11px] font-semibold text-red-800">{indicator}</p>
                      </div>
                      <span className="text-[9px] font-bold text-red-600 bg-red-100 px-2 py-0.5 rounded">CRITICAL</span>
                    </div>
                  ))}
                </div>
              )}

              {/* AIS Routing Evidence */}
              <div>
                <p className="text-[10px] font-bold text-[#005EA2] uppercase tracking-wide mb-2">AIS Routing Evidence</p>
                <div className="grid grid-cols-3 gap-3">
                  <div className="p-3 bg-slate-50 rounded border text-center">
                    <p className="text-xl font-bold text-[#0B1F33]">{dwellDays > 0 ? dwellDays.toFixed(0) : '—'}</p>
                    <p className="text-[10px] text-slate-500">Dwell Days</p>
                    {dwellDays >= 10 && <p className="text-[9px] font-bold text-red-600 mt-0.5">ANOMALY</p>}
                    {dwellDays >= 4 && dwellDays < 10 && <p className="text-[9px] text-amber-600 mt-0.5">Elevated</p>}
                  </div>
                  <div className="p-3 bg-slate-50 rounded border text-center">
                    <p className="text-xl font-bold text-[#0B1F33]">{adCvdRate > 0 ? `${adCvdRate.toFixed(0)}%` : '0%'}</p>
                    <p className="text-[10px] text-slate-500">AD/CVD Rate</p>
                    {adCvdRate >= 100 && <p className="text-[9px] font-bold text-red-600 mt-0.5">HIGH EXPOSURE</p>}
                  </div>
                  <div className="p-3 bg-slate-50 rounded border text-center">
                    <p className="text-xl font-bold text-[#0B1F33]">{shipperAge > 0 ? `${shipperAge}mo` : '—'}</p>
                    <p className="text-[10px] text-slate-500">Shipper Age</p>
                    {shipperAge > 0 && shipperAge < 6 && <p className="text-[9px] font-bold text-red-600 mt-0.5">NEW ENTITY</p>}
                    {shipperAge >= 6 && shipperAge < 12 && <p className="text-[9px] text-amber-600 mt-0.5">Recent</p>}
                  </div>
                </div>
              </div>

              {/* Port call sequence */}
              {portCalls.length > 0 && (
                <div>
                  <p className="text-[10px] font-bold text-[#005EA2] uppercase tracking-wide mb-2">Port Call Sequence</p>
                  <div className="flex items-center gap-1 flex-wrap">
                    {portCalls.map((port, i) => (
                      <React.Fragment key={i}>
                        <div className="flex items-center gap-1 px-2 py-1 bg-slate-100 rounded text-[10px] font-medium">
                          <MapPin size={10} className="text-slate-400" />
                          {port}
                        </div>
                        {i < portCalls.length - 1 && <ArrowRight size={10} className="text-slate-400" />}
                      </React.Fragment>
                    ))}
                  </div>
                </div>
              )}

              {/* Unit price anomaly */}
              {unitPrice > 0 && priceVar !== 0 && (
                <div className="p-3 bg-slate-50 rounded border text-[11px]">
                  <p className="font-semibold text-[#0B1F33] mb-1">Pricing Anomaly</p>
                  <div className="flex gap-4">
                    <div><span className="text-slate-500">Declared price: </span><strong>${unitPrice.toFixed(2)}/kg</strong></div>
                    <div>
                      <span className="text-slate-500">vs benchmark: </span>
                      <strong className={priceVar <= -40 ? 'text-red-600' : priceVar <= -20 ? 'text-amber-600' : 'text-green-600'}>
                        {priceVar > 0 ? '+' : ''}{priceVar.toFixed(0)}%
                      </strong>
                    </div>
                    {priceVar <= -40 && <span className="text-[9px] font-bold text-red-600 bg-red-100 px-2 py-0.5 rounded">SEVERE UNDERVALUATION</span>}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* ── PILLAR 3: Entity & Routing Intelligence ──────────────────── */}
        <div className="bg-white border border-[#D0D7DE] rounded-sm">
          <button
            className="w-full flex items-center justify-between p-4 hover:bg-slate-50"
            onClick={() => toggle('entity')}
          >
            <PillarHeader
              icon={Building2}
              title="Pillar 3 — Entity & Routing Intelligence (Tables 3-3, 3-4)"
              color="bg-[#0076D6]"
            />
            {expandedPillars.entity ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          </button>

          {expandedPillars.entity && (
            <div className="border-t border-[#D0D7DE] p-4 space-y-3">
              {/* Party Registry */}
              <div>
                <p className="text-[10px] font-bold text-[#005EA2] uppercase tracking-wide mb-2">Table 3-4 — Party Registry</p>
                <table className="w-full text-[11px] border-collapse">
                  <thead>
                    <tr className="bg-[#005EA2] text-white">
                      <th className="text-left px-3 py-2">Role</th>
                      <th className="text-left px-3 py-2">Entity Name</th>
                      <th className="text-left px-2 py-2">Country</th>
                      <th className="text-left px-2 py-2">Risk Flag</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      { role: 'Shipper / Exporter', name: shipment.shipper_name, country: shipment.shipper_country || shipment.origin_country, flag: shipperAge > 0 && shipperAge < 6 ? `NEW — ${shipperAge}mo established` : shipperAge > 0 && shipperAge < 12 ? `RECENT — ${shipperAge}mo` : null },
                      { role: 'Consignee / Importer', name: shipment.consignee_name, country: shipment.consignee_country || shipment.destination_country, flag: null },
                      { role: 'Carrier (Vessel)', name: shipment.vessel_name || '—', country: shipment.vessel_flag || '—', flag: null },
                    ].map((row, i) => (
                      <tr key={i} className={i % 2 === 0 ? 'bg-slate-50' : 'bg-white'}>
                        <td className="px-3 py-2 text-slate-500">{row.role}</td>
                        <td className="px-3 py-2 font-medium">{row.name || '—'}</td>
                        <td className="px-2 py-2">{row.country || '—'}</td>
                        <td className="px-2 py-2">
                          {row.flag
                            ? <span className="text-[9px] font-bold text-red-600 bg-red-50 px-1.5 py-0.5 rounded">{row.flag}</span>
                            : <span className="text-[9px] text-slate-400">—</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Entity ownership chain note */}
              <div className="p-3 bg-blue-50 border border-blue-200 rounded text-[10px] text-blue-800 flex items-start gap-2">
                <Info size={12} className="mt-0.5 flex-shrink-0" />
                <span>
                  <strong>Table 3-5 (Entity Ownership Chain)</strong> requires CORD entity resolution.
                  Available at Gate 2 (30% maturity) when CORD PostgreSQL migration completes.
                  Current status: <span className="font-medium">CORD service live, schema migration pending.</span>
                </span>
              </div>

              {/* Vessel / routing */}
              {(shipment.vessel_name || shipment.vessel_imo) && (
                <div>
                  <p className="text-[10px] font-bold text-[#005EA2] uppercase tracking-wide mb-2">Table 3-3 — Routing Summary</p>
                  <div className="grid grid-cols-2 gap-3 text-[11px]">
                    <div className="p-2 bg-slate-50 rounded border">
                      <span className="text-slate-500">Vessel: </span>
                      <strong>{shipment.vessel_name || '—'}</strong>
                      {shipment.vessel_imo && <span className="text-slate-400 ml-1">(IMO {shipment.vessel_imo})</span>}
                    </div>
                    <div className="p-2 bg-slate-50 rounded border">
                      <span className="text-slate-500">Flag: </span>
                      <strong>{shipment.vessel_flag || '—'}</strong>
                    </div>
                    <div className="p-2 bg-slate-50 rounded border">
                      <span className="text-slate-500">Origin: </span>
                      <strong>{shipment.origin_country || '—'}</strong>
                    </div>
                    <div className="p-2 bg-slate-50 rounded border">
                      <span className="text-slate-500">Destination: </span>
                      <strong>{shipment.destination_country || 'US'}</strong>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* ── EVIDENCE READINESS PANEL ─────────────────────────────────── */}
        <div className={`border rounded-sm p-4 ${overallReady ? 'bg-green-50 border-green-300' : 'bg-amber-50 border-amber-300'}`}>
          <p className="text-[11px] font-bold text-[#0B1F33] mb-3">Evidence Readiness — Referral Package Assembly</p>
          <div className="grid grid-cols-2 gap-2 mb-4">
            {[
              { label: 'Risk Score computed', done: hasRiskScore, detail: hasRiskScore ? `Score: ${selectedCase?.risk_score?.toFixed(1)}` : 'Run scoring first' },
              { label: 'Critical indicators documented', done: hasIndicators, detail: `${criticalIndicators.length} indicator(s) from rule engine` },
              { label: 'Document checklist', done: docReadiness !== 'needs-review', detail: docReadiness === 'complete' ? 'All docs accounted for' : `${missingCritical} doc(s) pending collection (noted in package)` },
              { label: 'Party registry complete', done: !!(shipment.shipper_name && (shipment.consignee_name || shipment.manifest_data?.consignee)), detail: 'Shipper + consignee identified' },
            ].map((item, i) => (
              <div key={i} className="flex items-center gap-2 text-[11px]">
                {item.done
                  ? <CheckCircle2 size={14} className="text-green-600 flex-shrink-0" />
                  : <XCircle size={14} className="text-amber-500 flex-shrink-0" />}
                <div>
                  <span className={item.done ? 'text-green-800 font-medium' : 'text-amber-800'}>{item.label}</span>
                  <span className="text-slate-500 ml-1 text-[10px]">— {item.detail}</span>
                </div>
              </div>
            ))}
          </div>

          <button
            onClick={onGenerateReferral}
            disabled={!overallReady}
            className={`w-full py-2.5 px-4 rounded text-[12px] font-bold flex items-center justify-center gap-2 transition-colors ${
              overallReady
                ? 'bg-[#005EA2] text-white hover:bg-[#004A80]'
                : 'bg-slate-200 text-slate-400 cursor-not-allowed'
            }`}
          >
            <FileText size={14} />
            Generate CSOP Referral Package (14 Sections)
            {!overallReady && <span className="text-[10px] font-normal">(risk score required)</span>}
            {overallReady && missingCritical > 0 && <span className="text-[10px] font-normal opacity-80">— {missingCritical} doc(s) pending</span>}
          </button>
        </div>

      </div>
    </div>
  );
}
