import { Case } from '../../types/models';
import { useScore, useEntityGraph } from '../../hooks';
import {
  ExpandableCard,
  SectionHeader,
  DataTable,
  AlertBanner,
  EntityCard
} from '../common';
import { AlertTriangle, AlertCircle, Shield, Link2 } from 'lucide-react';

interface Props {
  case: Case;
}

export default function H3IntelligencePanel({ case: c }: Props) {
  const { score, loading, error } = useScore(c.id);
  const { graph, loading: graphLoading } = useEntityGraph(c.id);

  if (loading || graphLoading) {
    return <AlertBanner type="info" title="Analyzing intelligence signals..." dismissible={false} />;
  }

  if (error) {
    return <AlertBanner type="error" title="Error loading intelligence data" message={error} />;
  }

  const h3Component = score?.components?.find((comp) => comp.horizon === 'H3');

  // Mock intelligence data
  const watchListHits = [
    {
      type: 'OFAC SDN',
      entity: 'Guangdong Greenfield Aluminum Mfg',
      score: 'HIT (85%)',
      reason: 'Director name match with SDN list entity',
      source: 'Treasury Dept SDN List (Feb 2026)',
      action: 'BLOCKING_REQUIRED'
    },
  ];

  const priorEapaFilings = [
    {
      case_number: 'EAPA-2025-0847',
      shipper: 'Greenfield Industrial Trading',
      determination: 'EVASION CONFIRMED',
      final_duty: '847.50%',
      filing_date: '2025-03-15',
      status: 'FINAL'
    },
    {
      case_number: 'EAPA-2025-0521',
      shipper: 'Guangdong Greenfield Aluminum',
      determination: 'EVASION CONFIRMED',
      final_duty: '642.15%',
      filing_date: '2025-01-22',
      status: 'FINAL'
    }
  ];

  const fraudRingAnalysis = {
    shipper_count: 2,
    consignee_link: 'SunPath Energy Distributors LLC',
    shared_parent: 'Guangdong Greenfield (China)',
    shared_directors: 3,
    incident_timeline: [
      {
        date: '2025-09-01',
        event: 'Greenfield Industrial incorporated (VN)',
        type: 'FOUNDING'
      },
      {
        date: '2025-11-15',
        event: 'Solaria Manufacturing incorporated (MY)',
        type: 'FOUNDING'
      },
      {
        date: '2025-12-01',
        event: 'Greenfield files first shipment to SunPath',
        type: 'SHIPMENT'
      },
      {
        date: '2026-01-10',
        event: 'Solaria files shipment to SunPath',
        type: 'SHIPMENT'
      },
      {
        date: '2026-02-15',
        event: 'EAPA-2025-0847 initiated (Greenfield)',
        type: 'ENFORCEMENT'
      },
    ]
  };

  const directorNetwork = [
    { name: 'Zhang Wei', entity: 'Guangdong Greenfield', role: 'Director', confidence: 0.99 },
    { name: 'Zhang Wei', entity: 'Greenfield Industrial VN', role: 'Nominee Director', confidence: 0.97 },
    { name: 'Chen Liu', entity: 'Guangdong Greenfield', role: 'Director', confidence: 0.94 },
    { name: 'Chen Liu', entity: 'Greenfield Global HK', role: 'Director', confidence: 0.91 },
    { name: 'Chen Liu', entity: 'Solaria Manufacturing', role: 'Director', confidence: 0.88 },
  ];

  const riskIndicators = [
    {
      indicator: 'OFAC SDN Hit',
      score: 15,
      points: 15,
      severity: 'CRITICAL',
      description: 'Director name matches Treasury SDN list',
      evidence: 'Guangdong Greenfield director "Zhang Wei" in SDN database'
    },
    {
      indicator: 'Prior EAPA Involvement',
      score: 10,
      points: 10,
      severity: 'HIGH',
      description: '2 prior EAPA cases on same shipper parent',
      evidence: 'EAPA-2025-0847 and EAPA-2025-0521 both confirmed evasion'
    },
    {
      indicator: 'New Importer + High Volume',
      score: 8,
      points: 8,
      severity: 'HIGH',
      description: 'Shipper <1 year old, shipment value >$50k',
      evidence: 'Greenfield incorporated Sep 2025, first shipment $50k'
    },
    {
      indicator: 'Volume Surge Pattern',
      score: 5,
      points: 5,
      severity: 'MEDIUM',
      description: 'Shipment 10x larger than typical startup',
      evidence: 'Typical startup entry ~$5k, this shipment $50k'
    },
    {
      indicator: 'Director Overlap',
      score: 0,
      points: 0,
      severity: 'MEDIUM',
      description: 'Multiple entities share same director',
      evidence: '3 shared directors across Greenfield VN, HK, CN entities'
    },
  ];

  const totalH3Score = riskIndicators.reduce((sum, r) => sum + r.points, 0);

  return (
    <div className="p-6 space-y-6">
      <SectionHeader
        title="H3: Full Intelligence Assessment"
        subtitle="OFAC/SDN checks, prior EAPA involvement, fraud ring detection, and advanced ML signals"
        badge="CRITICAL"
        badgeColor="red"
      />

      {/* Critical Alerts */}
      <div className="space-y-3">
        <AlertBanner
          type="error"
          title="OFAC SDN Hit Detected"
          message="Director 'Zhang Wei' of Guangdong Greenfield matches Treasury SDN list. Shipment blocking recommended."
        />
        <AlertBanner
          type="error"
          title="Fraud Ring Detected"
          message="Multiple high-risk shippers (Greenfield, Solaria) route to same consignee (SunPath) with shared parent entity."
        />
      </div>

      {/* H3 Score Summary */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <div className="p-4 bg-red-50 border-2 border-red-200 rounded-lg">
          <p className="text-xs font-semibold text-red-900 uppercase">H3 Score</p>
          <p className="text-3xl font-bold text-red-600 mt-2">{totalH3Score}</p>
          <p className="text-xs text-red-700 mt-1">/ 25 points (max)</p>
        </div>
        <div className="p-4 bg-purple-50 border-2 border-purple-200 rounded-lg">
          <p className="text-xs font-semibold text-purple-900 uppercase">Watch List Hits</p>
          <p className="text-3xl font-bold text-purple-600 mt-2">{watchListHits.length}</p>
          <p className="text-xs text-purple-700 mt-1">OFAC SDN matches</p>
        </div>
        <div className="p-4 bg-orange-50 border-2 border-orange-200 rounded-lg">
          <p className="text-xs font-semibold text-orange-900 uppercase">Prior EAPA</p>
          <p className="text-3xl font-bold text-orange-600 mt-2">{priorEapaFilings.length}</p>
          <p className="text-xs text-orange-700 mt-1">Confirmed evasion cases</p>
        </div>
      </div>

      {/* OFAC / Watch List Check */}
      <ExpandableCard
        title="OFAC & Watch List Screening"
        badge={watchListHits.length > 0 ? 'HIT' : 'CLEAR'}
        badgeColor={watchListHits.length > 0 ? 'red' : 'green'}
        defaultOpen={watchListHits.length > 0}
      >
        {watchListHits.length > 0 ? (
          <div className="space-y-3">
            {watchListHits.map((hit, idx) => (
              <div key={idx} className="p-4 bg-red-50 border-l-4 border-red-600 rounded-lg">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="text-red-600 flex-shrink-0 mt-1" size={20} />
                  <div className="flex-1">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <p className="font-semibold text-red-900">{hit.type}: {hit.entity}</p>
                        <p className="text-sm text-red-800 mt-1">{hit.reason}</p>
                      </div>
                      <span className="text-sm font-bold text-red-900 px-2 py-1 bg-red-200 rounded">
                        {hit.score}
                      </span>
                    </div>
                    <div className="mt-3 p-2 bg-red-100 rounded text-sm text-red-900">
                      <strong>Source:</strong> {hit.source}
                      <br />
                      <strong>Action:</strong> {hit.action}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-4 bg-green-50 border border-green-200 rounded-lg text-center">
            <p className="text-green-900 font-semibold">No watch list hits detected</p>
          </div>
        )}
      </ExpandableCard>

      {/* Prior EAPA Cases */}
      <ExpandableCard
        title="Prior EAPA Involvement"
        badge={priorEapaFilings.length > 0 ? `${priorEapaFilings.length} Cases` : 'NONE'}
        badgeColor={priorEapaFilings.length > 0 ? 'red' : 'green'}
      >
        {priorEapaFilings.length > 0 ? (
          <DataTable
            columns={[
              { key: 'case_number', label: 'Case Number', width: '15%' },
              { key: 'shipper', label: 'Shipper', width: '25%' },
              { key: 'determination', label: 'Determination', width: '20%' },
              { key: 'final_duty', label: 'Final Duty', width: '15%' },
              { key: 'filing_date', label: 'Filed', width: '15%' },
              {
                key: 'status',
                label: 'Status',
                width: '10%',
                render: (value: string) => (
                  <span className="text-xs font-bold px-2 py-1 bg-red-100 text-red-900 rounded">
                    {value}
                  </span>
                )
              },
            ]}
            data={priorEapaFilings}
            compact
          />
        ) : (
          <p className="text-gray-600">No prior EAPA filings found</p>
        )}
      </ExpandableCard>

      {/* Fraud Ring Detection */}
      <ExpandableCard
        title="Fraud Ring Detection"
        badge="2-SHIPPER RING"
        badgeColor="red"
        defaultOpen
      >
        <div className="space-y-4">
          {/* Ring Summary */}
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-start gap-3 mb-3">
              <AlertTriangle className="text-red-600 flex-shrink-0 mt-1" size={20} />
              <div className="flex-1">
                <p className="font-semibold text-red-900">Multi-Shipper Evasion Ring Detected</p>
                <p className="text-sm text-red-800 mt-1">
                  {fraudRingAnalysis.shipper_count} coordinated shippers routing through same consignee (SunPath Energy)
                  with shared parent entity (Guangdong Greenfield, China) and overlapping director network.
                </p>
              </div>
            </div>
          </div>

          {/* Ring Details */}
          <div className="grid grid-cols-2 gap-4">
            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-xs font-semibold text-gray-700 uppercase mb-2">Ring Characteristics</p>
              <ul className="text-sm space-y-1 text-gray-700">
                <li><strong>Shippers:</strong> {fraudRingAnalysis.shipper_count}</li>
                <li><strong>Consignee:</strong> {fraudRingAnalysis.consignee_link}</li>
                <li><strong>Parent:</strong> {fraudRingAnalysis.shared_parent}</li>
                <li><strong>Shared Directors:</strong> {fraudRingAnalysis.shared_directors}</li>
              </ul>
            </div>
            <div className="p-3 bg-red-50 rounded-lg border border-red-200">
              <p className="text-xs font-semibold text-red-900 uppercase mb-2">Ring Members</p>
              <ul className="text-sm space-y-1 text-red-900">
                <li>• Greenfield Industrial (VN) - HTS 7604 - $50k</li>
                <li>• Solaria Manufacturing (MY) - HTS 8541 - $75k</li>
              </ul>
            </div>
          </div>

          {/* Timeline */}
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <p className="text-xs font-semibold text-amber-900 uppercase mb-3">Timeline</p>
            <div className="space-y-2">
              {fraudRingAnalysis.incident_timeline.map((item, idx) => (
                <div key={idx} className="flex gap-3">
                  <div className="text-xs font-mono text-amber-900">{item.date}</div>
                  <div className="flex-1 text-sm text-amber-900">
                    {item.event}
                    <span className={`ml-2 text-xs font-bold px-2 py-0.5 rounded ${
                      item.type === 'ENFORCEMENT'
                        ? 'bg-red-100 text-red-900'
                        : item.type === 'SHIPMENT'
                        ? 'bg-orange-100 text-orange-900'
                        : 'bg-blue-100 text-blue-900'
                    }`}>
                      {item.type}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </ExpandableCard>

      {/* Director Network Analysis */}
      <ExpandableCard title="Senzing Entity Resolution - Director Network">
        <div className="space-y-3">
          <p className="text-sm text-gray-600 mb-4">
            Shared directors across Greenfield entities suggest deliberate structure to evade import enforcement.
          </p>
          <DataTable
            columns={[
              { key: 'name', label: 'Director Name', width: '20%' },
              { key: 'entity', label: 'Entity', width: '30%' },
              { key: 'role', label: 'Role', width: '20%' },
              {
                key: 'confidence',
                label: 'Senzing Confidence',
                width: '30%',
                render: (value: number) => (
                  <div className="flex items-center gap-2">
                    <div className="flex-1 bg-gray-300 rounded h-2">
                      <div
                        className="bg-blue-600 h-2 rounded"
                        style={{ width: `${value * 100}%` }}
                      ></div>
                    </div>
                    <span className="text-xs font-bold">{Math.round(value * 100)}%</span>
                  </div>
                )
              },
            ]}
            data={directorNetwork}
            compact
          />
        </div>
      </ExpandableCard>

      {/* H3 Risk Component Scoring */}
      <ExpandableCard title="H3 Intelligence Scoring Components" defaultOpen>
        <div className="space-y-3">
          {riskIndicators.map((indicator, idx) => (
            <div key={idx} className="p-4 border border-gray-200 rounded-lg">
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1">
                  <h4 className="font-semibold text-gray-900">{indicator.indicator}</h4>
                  <p className="text-sm text-gray-600 mt-1">{indicator.description}</p>
                  <p className="text-xs text-gray-500 mt-1"><strong>Evidence:</strong> {indicator.evidence}</p>
                </div>
                <span className={`text-sm font-bold px-2 py-1 rounded ml-3 whitespace-nowrap ${
                  indicator.severity === 'CRITICAL'
                    ? 'bg-red-100 text-red-900'
                    : indicator.severity === 'HIGH'
                    ? 'bg-orange-100 text-orange-900'
                    : 'bg-amber-100 text-amber-900'
                }`}>
                  {indicator.severity}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex-1 bg-gray-200 rounded-full h-3">
                  <div
                    className={`h-3 rounded-full ${
                      indicator.severity === 'CRITICAL'
                        ? 'bg-red-600'
                        : indicator.severity === 'HIGH'
                        ? 'bg-orange-600'
                        : 'bg-amber-500'
                    }`}
                    style={{ width: `${(indicator.score / 15) * 100}%` }}
                  ></div>
                </div>
                <span className="text-sm font-bold text-gray-700 min-w-fit">{indicator.points} pts</span>
              </div>
            </div>
          ))}
          <div className="mt-4 p-3 bg-gray-100 rounded-lg border-2 border-gray-300">
            <p className="text-sm font-bold text-gray-900">
              H3 Total Score: {totalH3Score} / 25 points
            </p>
          </div>
        </div>
      </ExpandableCard>
    </div>
  );
}
