import React from 'react';
import { CheckCircle, AlertTriangle, HelpCircle } from 'lucide-react';

interface Anomaly {
  id: string;
  name: string;
  status: 'clear' | 'flagged' | 'pending';
  severity_score: number;
  details?: string;
}

interface AnomalyChecklistProps {
  anomalies?: Anomaly[];
  title?: string;
}

function getStatusIcon(status: string) {
  switch (status) {
    case 'clear':
      return <CheckCircle className="w-4 h-4 text-green-600" />;
    case 'flagged':
      return <AlertTriangle className="w-4 h-4 text-[#D83933]" />;
    case 'pending':
      return <HelpCircle className="w-4 h-4 text-amber-600" />;
    default:
      return null;
  }
}

function getSeverityColor(score: number): string {
  if (score >= 80) return '#D83933';
  if (score >= 60) return '#FF9500';
  if (score >= 40) return '#F59E0B';
  return '#22c55e';
}

const FIXTURE_ANOMALIES: Anomaly[] = [
  {
    id: 'ISF_MISMATCH',
    name: 'ISF Element 9 Mismatch',
    status: 'flagged',
    severity_score: 78,
    details: 'Declared origin differs from BOL origin by 2 countries',
  },
  {
    id: 'DWELL_ANOMALY',
    name: 'Dwell Time Anomaly',
    status: 'flagged',
    severity_score: 68,
    details: 'Port dwell 5 days vs. 2-day baseline for this corridor',
  },
  {
    id: 'ORIGIN_INCONSISTENT',
    name: 'Origin Country Inconsistent',
    status: 'pending',
    severity_score: 45,
    details: 'Manual verification pending with shipper',
  },
  {
    id: 'WEIGHT_VARIANCE',
    name: 'Weight/Volume Variance',
    status: 'clear',
    severity_score: 12,
    details: 'Weight matches packing list within 2% tolerance',
  },
  {
    id: 'MISSING_DOCS',
    name: 'Missing Documentation',
    status: 'flagged',
    severity_score: 89,
    details: 'Factory production records and bill of materials not provided',
  },
  {
    id: 'CONSIGNEE_VERIFIED',
    name: 'Consignee Verified',
    status: 'clear',
    severity_score: 5,
    details: 'Consignee registered and in good standing',
  },
  {
    id: 'VESSEL_FLAG_RISK',
    name: 'Vessel Flag Risk',
    status: 'flagged',
    severity_score: 62,
    details: 'Vessel flagged to high-risk jurisdiction',
  },
  {
    id: 'PRICING_ANOMALY',
    name: 'Pricing Per Unit Anomaly',
    status: 'pending',
    severity_score: 38,
    details: 'Price per unit 25% below market average; clarification requested',
  },
  {
    id: 'HS_CODE_VALID',
    name: 'HS Code Valid & Complete',
    status: 'clear',
    severity_score: 2,
    details: 'HS code 7610.10.00 correctly classified',
  },
  {
    id: 'PRIOR_VIOLATION',
    name: 'Prior Carrier Violation',
    status: 'flagged',
    severity_score: 91,
    details: 'Vessel involved in 3 prior customs violations in past 2 years',
  },
];

export default function AnomalyChecklist({
  anomalies = FIXTURE_ANOMALIES,
  title = 'Manifest Anomaly Assessment',
}: AnomalyChecklistProps) {
  const clearCount = anomalies.filter((a) => a.status === 'clear').length;
  const flaggedCount = anomalies.filter((a) => a.status === 'flagged').length;
  const pendingCount = anomalies.filter((a) => a.status === 'pending').length;

  return (
    <div className="w-full bg-white rounded-sm border border-[#D0D7DE] p-4 shadow-sm">
      <div className="text-[9px] font-bold text-[#5C5C5C] uppercase mb-3">{title}</div>

      {/* Anomaly List */}
      <div className="space-y-2 mb-4 max-h-96 overflow-y-auto">
        {anomalies.map((anomaly) => (
          <div
            key={anomaly.id}
            className="bg-slate-50 border border-slate-200 rounded-sm p-2.5 hover:bg-slate-100 transition-colors"
          >
            <div className="flex items-start justify-between gap-2 mb-1">
              <div className="flex items-center gap-2 flex-1">
                {getStatusIcon(anomaly.status)}
                <div className="flex-1 min-w-0">
                  <div className="text-[9px] font-bold text-[#0B1F33]">{anomaly.name}</div>
                  {anomaly.details && (
                    <div className="text-[8px] text-[#5C5C5C] mt-0.5 line-clamp-1">{anomaly.details}</div>
                  )}
                </div>
              </div>
              <span
                className="text-[8px] font-bold px-1.5 py-0.5 rounded text-white whitespace-nowrap flex-shrink-0"
                style={{ background: getSeverityColor(anomaly.severity_score) }}
              >
                {anomaly.severity_score}%
              </span>
            </div>

            {/* Severity Bar */}
            <div className="h-1.5 bg-slate-200 rounded-full overflow-hidden">
              <div
                className="h-full transition-all"
                style={{
                  width: `${anomaly.severity_score}%`,
                  background: getSeverityColor(anomaly.severity_score),
                }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* Summary Stats */}
      <div className="pt-4 border-t border-[#D0D7DE]">
        <div className="text-[9px] font-bold text-[#5C5C5C] uppercase mb-3">Summary</div>
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-green-50 border border-green-200 rounded p-2.5 text-center">
            <div className="text-[8px] text-green-700 font-bold">✓ CLEAR</div>
            <div className="text-[12px] font-bold text-green-800 mt-1">{clearCount}</div>
          </div>
          <div className="bg-red-50 border border-red-200 rounded p-2.5 text-center">
            <div className="text-[8px] text-red-700 font-bold">✗ FLAGGED</div>
            <div className="text-[12px] font-bold text-red-800 mt-1">{flaggedCount}</div>
          </div>
          <div className="bg-amber-50 border border-amber-200 rounded p-2.5 text-center">
            <div className="text-[8px] text-amber-700 font-bold">? PENDING</div>
            <div className="text-[12px] font-bold text-amber-800 mt-1">{pendingCount}</div>
          </div>
        </div>
      </div>

      {/* Risk Assessment */}
      <div className="mt-4 pt-4 border-t border-[#D0D7DE]">
        <div className="text-[9px] font-bold text-[#5C5C5C] uppercase mb-2">Overall Assessment</div>
        <div className="bg-red-50 border-l-4 border-red-500 p-2.5 rounded">
          <div className="text-[9px] text-red-800">
            <span className="font-bold">⚠ HIGH RISK:</span> {flaggedCount} critical anomalies require
            immediate attention before release
          </div>
        </div>
      </div>
    </div>
  );
}
