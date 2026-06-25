import React from 'react';
import { AlertTriangle, CheckCircle, Package } from 'lucide-react';

interface ManifestStop {
  location: string;
  type: 'origin' | 'hub' | 'destination';
  entity_name: string;
  dwell_days?: number;
  anomalies?: string[];
  risk_score?: number;
}

interface ManifestFlowDiagramProps {
  stops?: ManifestStop[];
  height?: number;
  commodityInfo?: {
    commodity: string;
    hs_code: string;
    weight_kg: number;
    value_usd: number;
  };
}

function getRiskColor(score?: number): string {
  if (!score) return '#D0D7DE';
  if (score >= 80) return '#D83933';
  if (score >= 60) return '#FF9500';
  if (score >= 40) return '#F59E0B';
  return '#22c55e';
}

function getAnomalyIcon(anomalies?: string[]) {
  if (!anomalies || anomalies.length === 0) return <CheckCircle className="w-4 h-4 text-green-600" />;
  return <AlertTriangle className="w-4 h-4 text-[#D83933]" />;
}

const FIXTURE_STOPS: ManifestStop[] = [
  {
    location: 'Vietnam',
    type: 'origin',
    entity_name: 'Greenfield Industrial',
    dwell_days: 1,
    anomalies: [],
    risk_score: 65,
  },
  {
    location: 'Hong Kong',
    type: 'hub',
    entity_name: 'Consolidation Center',
    dwell_days: 3,
    anomalies: ['DWELL_ANOMALY'],
    risk_score: 72,
  },
  {
    location: 'Singapore',
    type: 'hub',
    entity_name: 'Port Authority',
    dwell_days: 2,
    anomalies: [],
    risk_score: 45,
  },
  {
    location: 'USA',
    type: 'destination',
    entity_name: 'SunPath Distribution',
    dwell_days: 0,
    anomalies: [],
    risk_score: 52,
  },
];

export default function ManifestFlowDiagram({
  stops = FIXTURE_STOPS,
  height = 300,
  commodityInfo = {
    commodity: 'Aluminum Extrusions',
    hs_code: '7610.10.00',
    weight_kg: 26200,
    value_usd: 125000,
  },
}: ManifestFlowDiagramProps) {
  return (
    <div className="w-full bg-white rounded-sm border border-[#D0D7DE] p-4 shadow-sm">
      <div className="text-[9px] font-bold text-[#5C5C5C] uppercase mb-4">Shipment Flow Diagram</div>

      {/* Commodity Header */}
      <div className="grid grid-cols-4 gap-3 mb-6 pb-4 border-b border-[#D0D7DE]">
        <div>
          <div className="text-[8px] text-[#5C5C5C] font-bold uppercase">Commodity</div>
          <div className="text-[10px] font-bold text-[#0B1F33]">{commodityInfo.commodity}</div>
        </div>
        <div>
          <div className="text-[8px] text-[#5C5C5C] font-bold uppercase">HS Code</div>
          <div className="text-[9px] font-mono text-[#0B1F33]">{commodityInfo.hs_code}</div>
        </div>
        <div>
          <div className="text-[8px] text-[#5C5C5C] font-bold uppercase">Weight</div>
          <div className="text-[10px] font-bold text-[#0B1F33]">{(commodityInfo.weight_kg / 1000).toFixed(1)}T</div>
        </div>
        <div>
          <div className="text-[8px] text-[#5C5C5C] font-bold uppercase">Value</div>
          <div className="text-[10px] font-bold text-[#0B1F33]">${(commodityInfo.value_usd / 1000).toFixed(0)}K</div>
        </div>
      </div>

      {/* Flow Diagram */}
      <div style={{ height: `${height}px` }} className="relative flex flex-col justify-between">
        {stops.map((stop, idx) => (
          <div key={idx} className="relative">
            {/* Arrow connector to next stop */}
            {idx < stops.length - 1 && (
              <div className="absolute left-8 top-12 w-0.5 h-12 bg-gradient-to-b from-[#D0D7DE] to-transparent" />
            )}

            {/* Stop card */}
            <div className="flex items-start gap-4">
              {/* Icon */}
              <div
                className="w-4 h-4 rounded-full border-2 flex items-center justify-center flex-shrink-0 mt-1"
                style={{ borderColor: getRiskColor(stop.risk_score), background: getRiskColor(stop.risk_score) + '20' }}
              >
                {stop.type === 'origin' && <Package className="w-2.5 h-2.5" style={{ color: getRiskColor(stop.risk_score) }} />}
                {stop.type === 'hub' && getAnomalyIcon(stop.anomalies)}
                {stop.type === 'destination' && <CheckCircle className="w-2.5 h-2.5 text-green-600" />}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <div className="text-[9px] font-bold text-[#5C5C5C] uppercase">{stop.location}</div>
                    <div className="text-[10px] font-bold text-[#0B1F33]">{stop.entity_name}</div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {stop.dwell_days !== undefined && stop.dwell_days > 0 && (
                      <div className="text-[8px] text-[#5C5C5C]">
                        <span className="font-bold">{stop.dwell_days}d</span> dwell
                      </div>
                    )}
                    <span
                      className="text-[9px] font-bold px-2 py-0.5 rounded text-white"
                      style={{ background: getRiskColor(stop.risk_score) }}
                    >
                      {stop.risk_score}%
                    </span>
                  </div>
                </div>

                {/* Anomalies */}
                {stop.anomalies && stop.anomalies.length > 0 && (
                  <div className="mt-1.5 flex gap-1 flex-wrap">
                    {stop.anomalies.map((anom) => (
                      <span
                        key={anom}
                        className="text-[7px] font-bold px-1.5 py-0.5 rounded bg-red-100 text-red-800 uppercase"
                      >
                        {anom.replace(/_/g, ' ')}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Summary */}
      <div className="mt-6 pt-4 border-t border-[#D0D7DE] grid grid-cols-3 gap-3 text-[8px]">
        <div>
          <div className="text-[#5C5C5C] font-bold">TOTAL STOPS</div>
          <div className="text-[10px] font-bold text-[#0B1F33]">{stops.length}</div>
        </div>
        <div>
          <div className="text-[#5C5C5C] font-bold">TOTAL DWELL</div>
          <div className="text-[10px] font-bold text-[#0B1F33]">
            {stops.reduce((sum, s) => sum + (s.dwell_days || 0), 0)}d
          </div>
        </div>
        <div>
          <div className="text-[#5C5C5C] font-bold">ANOMALIES</div>
          <div className="text-[10px] font-bold text-[#D83933]">
            {stops.filter(s => s.anomalies && s.anomalies.length > 0).length}
          </div>
        </div>
      </div>
    </div>
  );
}
