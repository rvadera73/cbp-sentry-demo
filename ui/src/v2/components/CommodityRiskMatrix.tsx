import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';

interface CommodityData {
  commodity: string;
  hs_code: string;
  supply_chain_risk: number;
  tariff_risk: number;
  origin_risk: number;
  total_risk: number;
}

interface CommodityRiskMatrixProps {
  commodities?: CommodityData[];
  height?: number;
}

function getRiskColor(score: number): string {
  if (score >= 80) return '#D83933';
  if (score >= 60) return '#FF9500';
  if (score >= 40) return '#F59E0B';
  return '#22c55e';
}

const FIXTURE_COMMODITIES: CommodityData[] = [
  {
    commodity: 'Aluminum Extrusions',
    hs_code: '7610',
    supply_chain_risk: 65,
    tariff_risk: 72,
    origin_risk: 68,
    total_risk: 68,
  },
  {
    commodity: 'Steel Coils',
    hs_code: '7226',
    supply_chain_risk: 58,
    tariff_risk: 85,
    origin_risk: 62,
    total_risk: 68,
  },
  {
    commodity: 'Textiles',
    hs_code: '6204',
    supply_chain_risk: 75,
    tariff_risk: 88,
    origin_risk: 72,
    total_risk: 78,
  },
  {
    commodity: 'Electronics',
    hs_code: '8471',
    supply_chain_risk: 45,
    tariff_risk: 52,
    origin_risk: 48,
    total_risk: 48,
  },
  {
    commodity: 'Machinery',
    hs_code: '8479',
    supply_chain_risk: 38,
    tariff_risk: 42,
    origin_risk: 35,
    total_risk: 38,
  },
];

export default function CommodityRiskMatrix({
  commodities = FIXTURE_COMMODITIES,
  height = 350,
}: CommodityRiskMatrixProps) {
  const chartData = commodities.map((c) => ({
    name: c.commodity.substring(0, 16),
    'Supply Chain': c.supply_chain_risk,
    'Tariff Risk': c.tariff_risk,
    'Origin Risk': c.origin_risk,
    hs_code: c.hs_code,
  }));

  return (
    <div className="w-full bg-white rounded-sm border border-[#D0D7DE] p-4 shadow-sm">
      <div className="text-[9px] font-bold text-[#5C5C5C] uppercase mb-3">Commodity Risk Profile</div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={chartData}
          margin={{ top: 20, right: 30, left: 0, bottom: 60 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 9 }}
            angle={-45}
            textAnchor="end"
            height={80}
          />
          <YAxis
            label={{ value: 'Risk Score', angle: -90, position: 'insideLeft' }}
            tick={{ fontSize: 9 }}
            domain={[0, 100]}
          />
          <Tooltip
            contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #D0D7DE', borderRadius: '4px' }}
            labelStyle={{ color: '#fff', fontSize: '12px' }}
            formatter={(value) => `${value}%`}
          />
          <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '20px' }} />
          <Bar dataKey="Supply Chain" fill="#0076D6" radius={[4, 4, 0, 0]} />
          <Bar dataKey="Tariff Risk" fill="#FF9500" radius={[4, 4, 0, 0]} />
          <Bar dataKey="Origin Risk" fill="#D83933" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>

      {/* Commodity Details Table */}
      <div className="mt-6 pt-4 border-t border-[#D0D7DE]">
        <div className="text-[9px] font-bold text-[#5C5C5C] uppercase mb-3">Commodity Details</div>
        <div className="space-y-2">
          {commodities.map((c) => (
            <div
              key={c.hs_code}
              className="bg-slate-50 border border-slate-200 rounded p-2.5"
            >
              <div className="flex items-start justify-between gap-3 mb-2">
                <div>
                  <div className="text-[9px] font-bold text-[#0B1F33]">{c.commodity}</div>
                  <div className="text-[8px] text-[#5C5C5C] font-mono mt-0.5">HS {c.hs_code}</div>
                </div>
                <span
                  className="text-[9px] font-bold px-2 py-0.5 rounded text-white whitespace-nowrap"
                  style={{ background: getRiskColor(c.total_risk) }}
                >
                  {c.total_risk}%
                </span>
              </div>

              {/* Mini bars for each risk factor */}
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <div className="text-[7px] text-[#5C5C5C] font-bold uppercase mb-1">Supply</div>
                  <div className="h-1.5 bg-slate-200 rounded overflow-hidden">
                    <div
                      className="h-full"
                      style={{
                        width: `${c.supply_chain_risk}%`,
                        background: getRiskColor(c.supply_chain_risk),
                      }}
                    />
                  </div>
                  <div className="text-[7px] text-[#5C5C5C] mt-0.5">{c.supply_chain_risk}%</div>
                </div>
                <div>
                  <div className="text-[7px] text-[#5C5C5C] font-bold uppercase mb-1">Tariff</div>
                  <div className="h-1.5 bg-slate-200 rounded overflow-hidden">
                    <div
                      className="h-full"
                      style={{
                        width: `${c.tariff_risk}%`,
                        background: getRiskColor(c.tariff_risk),
                      }}
                    />
                  </div>
                  <div className="text-[7px] text-[#5C5C5C] mt-0.5">{c.tariff_risk}%</div>
                </div>
                <div>
                  <div className="text-[7px] text-[#5C5C5C] font-bold uppercase mb-1">Origin</div>
                  <div className="h-1.5 bg-slate-200 rounded overflow-hidden">
                    <div
                      className="h-full"
                      style={{
                        width: `${c.origin_risk}%`,
                        background: getRiskColor(c.origin_risk),
                      }}
                    />
                  </div>
                  <div className="text-[7px] text-[#5C5C5C] mt-0.5">{c.origin_risk}%</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
