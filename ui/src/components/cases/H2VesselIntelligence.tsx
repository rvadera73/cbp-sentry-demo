import { Case, ScoreResult } from '../../types/models';
import { useScore } from '../../hooks';
import {
  ExpandableCard,
  SectionHeader,
  DataTable,
  AlertBanner
} from '../common';
import { AlertTriangle, AlertCircle, CheckCircle } from 'lucide-react';

interface Props {
  case: Case;
}

export default function H2VesselIntelligence({ case: c }: Props) {
  const { score, loading, error } = useScore(c.id);

  if (loading) {
    return <AlertBanner type="info" title="Analyzing vessel intelligence..." dismissible={false} />;
  }

  if (error) {
    return <AlertBanner type="error" title="Error loading score data" message={error} />;
  }

  const h2Component = score?.components?.find((comp) => comp.horizon === 'H2');

  // Mock AIS data - in production from live AIS service
  const aisData = {
    vessel_name: c.vessel_name || 'MV Pacific Horizon',
    mmsi: '351885000',
    imo: '9755804',
    flag: 'Panama',
    dwell_days: 11.2,
    baseline_days: 2.1,
    port_calls: 6,
    expected_calls: 2,
  };

  const portCallHistory = [
    {
      port: 'Guangzhou, China',
      arrival: '2026-05-01',
      departure: '2026-05-12',
      dwell: '11.2 days',
      container_moves: '847',
      anomaly: 'EXTENDED_DWELL'
    },
    {
      port: 'Hong Kong',
      arrival: '2026-05-13',
      departure: '2026-05-14',
      dwell: '1 day',
      container_moves: '12',
      anomaly: 'BRIEF_CALL'
    },
    {
      port: 'Singapore',
      arrival: '2026-05-16',
      departure: '2026-05-17',
      dwell: '0.8 days',
      container_moves: '0',
      anomaly: 'NO_OPERATIONS'
    },
    {
      port: 'Port Klang, Malaysia',
      arrival: '2026-05-19',
      departure: '2026-05-20',
      dwell: '0.5 days',
      container_moves: '0',
      anomaly: 'TRANSSHIPMENT_PATTERN'
    },
    {
      port: 'Singapore (2nd)',
      arrival: '2026-05-21',
      departure: '2026-05-22',
      dwell: '0.7 days',
      container_moves: '182',
      anomaly: 'UNUSUAL_SEQUENCE'
    },
    {
      port: 'Newark, NJ',
      arrival: '2026-06-10',
      departure: 'TBD',
      dwell: 'In progress',
      container_moves: 'TBD',
      anomaly: 'DESTINATION'
    },
  ];

  const isfAnalysis = {
    declared_origin: 'Vietnam',
    actual_stuffing_location: 'China (Guangzhou)',
    confidence: 0.97,
    mismatch_risk: 'CRITICAL',
    evidence: [
      'Container loaded at Guangzhou Port (AIS confirms 11.2-day dwell)',
      'ISF Element 9 filed declaring Vietnam origin',
      'Container transits through Singapore twice - unusual pattern',
      'Brief port calls suggest container handling at regional hubs',
    ]
  };

  const amlcAnalysis = {
    declarations: [
      { field: 'Country of Origin', value: 'Vietnam', actual: 'China', match: false },
      { field: 'Place of Origin', value: 'Hanoi', actual: 'Guangzhou', match: false },
      { field: 'Shipper', value: 'Greenfield VN', actual: 'Guangdong Greenfield CN', match: false },
      { field: 'Port of Loading', value: 'Port of Hanoi', actual: 'Port of Guangzhou', match: false },
      { field: 'First Port of Arrival', value: 'Hong Kong', actual: 'Hong Kong', match: true },
    ]
  };

  const documentReview = [
    { document: 'Commercial Invoice', status: '✓ RECEIVED', notes: 'Shows Vietnam shipper address' },
    { document: 'Packing List', status: '✗ MISSING', notes: 'Critical - requested but not provided' },
    { document: 'Bill of Lading', status: '✓ RECEIVED', notes: 'Issued at Guangzhou (contradicts origin claim)' },
    { document: 'Factory Records', status: '✗ MISSING', notes: 'Shipper claims Vietnamese manufacture - not verified' },
    { document: 'Shipper Certification', status: 'SUSPICIOUS', notes: 'Generic template, no facility details' },
  ];

  const riskIndicators = [
    {
      indicator: 'AIS Dwell Anomaly',
      score: 12,
      severity: 'HIGH',
      description: '11.2-day port dwell vs 2.1-day baseline (433% anomaly)',
      evidence: 'Extends waiting time for transshipment handling'
    },
    {
      indicator: 'ISF Element 9 Mismatch',
      score: 12,
      severity: 'HIGH',
      description: 'Declared origin Vietnam, actual stuffing China',
      evidence: 'Container loaded at Guangzhou Port per AIS data'
    },
    {
      indicator: 'Unusual Port Call Sequence',
      score: 6,
      severity: 'MEDIUM',
      description: 'Singapore visited twice, brief transshipment pattern',
      evidence: 'Suggests container unpacked/repacked - classic transshipment'
    },
    {
      indicator: 'Document Inconsistencies',
      score: 5,
      severity: 'MEDIUM',
      description: 'BOL issued at Guangzhou but origin claimed as Vietnam',
      evidence: 'Multiple AMLC field mismatches with AIS facts'
    },
  ];

  return (
    <div className="p-6 space-y-6">
      <SectionHeader
        title="H2: Vessel & Pre-Manifest Intelligence"
        subtitle="AIS tracking, ISF Element 9 validation, and document consistency analysis"
        badge="HIGH RISK"
        badgeColor="red"
      />

      {/* Vessel & AIS Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 bg-blue-50 border-2 border-blue-200 rounded-lg">
          <p className="text-xs font-semibold text-blue-900 uppercase">Vessel</p>
          <p className="text-base font-bold text-blue-600 mt-2">{aisData.vessel_name}</p>
          <p className="text-xs text-blue-700 mt-1">Flag: {aisData.flag}</p>
        </div>
        <div className="p-4 bg-red-50 border-2 border-red-200 rounded-lg">
          <p className="text-xs font-semibold text-red-900 uppercase">Dwell Time</p>
          <p className="text-lg font-bold text-red-600 mt-2">{aisData.dwell_days}d</p>
          <p className="text-xs text-red-700 mt-1">vs {aisData.baseline_days}d baseline (433%)</p>
        </div>
        <div className="p-4 bg-orange-50 border-2 border-orange-200 rounded-lg">
          <p className="text-xs font-semibold text-orange-900 uppercase">Port Calls</p>
          <p className="text-lg font-bold text-orange-600 mt-2">{aisData.port_calls}</p>
          <p className="text-xs text-orange-700 mt-1">{aisData.expected_calls} expected</p>
        </div>
        <div className="p-4 bg-red-50 border-2 border-red-200 rounded-lg">
          <p className="text-xs font-semibold text-red-900 uppercase">ISF Mismatch</p>
          <p className="text-lg font-bold text-red-600 mt-2">CRITICAL</p>
          <p className="text-xs text-red-700 mt-1">Origin declared ≠ actual</p>
        </div>
      </div>

      {/* ISF Element 9 Critical Analysis */}
      <ExpandableCard
        title="ISF Element 9 Analysis (CRITICAL)"
        badge="MISMATCH"
        badgeColor="red"
        defaultOpen
      >
        <div className="space-y-4">
          <div className="p-4 bg-red-50 border-l-4 border-red-600 rounded-lg">
            <div className="flex gap-3">
              <AlertTriangle className="text-red-600 flex-shrink-0 mt-0.5" size={20} />
              <div>
                <p className="font-semibold text-red-900">Origin Country Mismatch Detected</p>
                <p className="text-sm text-red-800 mt-1">
                  <strong>Declared:</strong> Vietnam | <strong>Actual (AIS):</strong> China (Guangzhou)
                </p>
                <p className="text-xs text-red-700 mt-2">Confidence: 97% (based on AIS tracking data)</p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-xs font-semibold text-gray-700 uppercase mb-2">ISF Declaration</p>
              <ul className="text-sm space-y-1 text-gray-700">
                <li><strong>Country of Origin:</strong> Vietnam</li>
                <li><strong>City:</strong> Hanoi</li>
                <li><strong>Port of Loading:</strong> Port of Hanoi</li>
              </ul>
            </div>
            <div className="p-3 bg-red-50 rounded-lg border border-red-200">
              <p className="text-xs font-semibold text-red-900 uppercase mb-2">AIS Actual Data</p>
              <ul className="text-sm space-y-1 text-red-900">
                <li><strong>Origin Country:</strong> China (PRC)</li>
                <li><strong>City:</strong> Guangzhou</li>
                <li><strong>Port of Loading:</strong> Port of Guangzhou</li>
              </ul>
            </div>
          </div>

          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <p className="text-sm font-semibold text-amber-900 mb-2">Transshipment Indicators:</p>
            <ul className="text-sm text-amber-900 space-y-1">
              {isfAnalysis.evidence.map((item, idx) => (
                <li key={idx} className="flex gap-2">
                  <span className="text-amber-600">•</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </ExpandableCard>

      {/* AIS Routing History */}
      <ExpandableCard title="AIS Port Call History (6 Stops)">
        <DataTable
          columns={[
            { key: 'port', label: 'Port', width: '25%' },
            { key: 'arrival', label: 'Arrival', width: '15%' },
            { key: 'departure', label: 'Departure', width: '15%' },
            { key: 'dwell', label: 'Dwell', width: '12%' },
            { key: 'container_moves', label: 'Moves', width: '12%' },
            {
              key: 'anomaly',
              label: 'Flag',
              width: '21%',
              render: (value: string) => {
                const colors = {
                  'EXTENDED_DWELL': 'bg-red-100 text-red-900',
                  'BRIEF_CALL': 'bg-amber-100 text-amber-900',
                  'NO_OPERATIONS': 'bg-orange-100 text-orange-900',
                  'TRANSSHIPMENT_PATTERN': 'bg-red-100 text-red-900',
                  'UNUSUAL_SEQUENCE': 'bg-orange-100 text-orange-900',
                  'DESTINATION': 'bg-blue-100 text-blue-900',
                };
                return (
                  <span className={`text-xs font-bold px-2 py-1 rounded ${
                    colors[value as keyof typeof colors] || 'bg-gray-100 text-gray-900'
                  }`}>
                    {value.replace(/_/g, ' ')}
                  </span>
                );
              }
            },
          ]}
          data={portCallHistory}
          compact
        />
      </ExpandableCard>

      {/* AMLC Document Consistency */}
      <ExpandableCard
        title="AMLC Field Consistency Analysis"
        badge="INCONSISTENT"
        badgeColor="red"
      >
        <DataTable
          columns={[
            { key: 'field', label: 'Field', width: '25%' },
            { key: 'value', label: 'Declared Value', width: '25%' },
            { key: 'actual', label: 'Actual (AIS/BOL)', width: '25%' },
            {
              key: 'match',
              label: 'Match',
              width: '25%',
              render: (value: boolean) => (
                <div className="flex items-center gap-1">
                  {value ? (
                    <>
                      <CheckCircle size={16} className="text-green-600" />
                      <span className="text-xs font-semibold text-green-900">Match</span>
                    </>
                  ) : (
                    <>
                      <AlertCircle size={16} className="text-red-600" />
                      <span className="text-xs font-semibold text-red-900">Mismatch</span>
                    </>
                  )}
                </div>
              )
            },
          ]}
          data={amlcAnalysis.declarations}
          compact
        />
      </ExpandableCard>

      {/* Document Review Checklist */}
      <ExpandableCard
        title="Document Review Checklist"
        badge="3 MISSING"
        badgeColor="red"
      >
        <div className="space-y-2">
          {documentReview.map((doc, idx) => (
            <div key={idx} className="p-3 border border-gray-200 rounded-lg">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-semibold text-gray-900">{doc.document}</p>
                  <p className="text-sm text-gray-600 mt-1">{doc.notes}</p>
                </div>
                <span className={`text-xs font-bold px-2 py-1 rounded whitespace-nowrap ${
                  doc.status.includes('RECEIVED')
                    ? 'bg-green-100 text-green-900'
                    : doc.status.includes('MISSING')
                    ? 'bg-red-100 text-red-900'
                    : 'bg-amber-100 text-amber-900'
                }`}>
                  {doc.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      </ExpandableCard>

      {/* H2 Risk Indicators */}
      <ExpandableCard title="H2 Risk Indicator Scores" defaultOpen>
        <div className="space-y-3">
          {riskIndicators.map((indicator, idx) => (
            <div key={idx} className="p-4 border border-gray-200 rounded-lg bg-gray-50">
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1">
                  <h4 className="font-semibold text-gray-900">{indicator.indicator}</h4>
                  <p className="text-sm text-gray-600 mt-1">{indicator.description}</p>
                </div>
                <span className={`text-sm font-bold px-2 py-1 rounded ${
                  indicator.severity === 'HIGH'
                    ? 'bg-red-100 text-red-900'
                    : 'bg-amber-100 text-amber-900'
                }`}>
                  {indicator.severity}
                </span>
              </div>
              <p className="text-xs text-gray-600 mb-2">Evidence: {indicator.evidence}</p>
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-gray-300 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      indicator.severity === 'HIGH' ? 'bg-red-600' : 'bg-amber-500'
                    }`}
                    style={{ width: `${(indicator.score / 12) * 100}%` }}
                  ></div>
                </div>
                <span className="text-xs font-bold text-gray-700">{indicator.score} pts</span>
              </div>
            </div>
          ))}
        </div>
      </ExpandableCard>
    </div>
  );
}
