import React, { useState } from 'react';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface RiskDimension {
  dimension: string;
  score: number;
}

interface RiskHeatmapProps {
  dimensions?: RiskDimension[];
  title?: string;
  height?: number;
}

const FIXTURE_DIMENSIONS: RiskDimension[] = [
  { dimension: 'Supply Chain', score: 72 },
  { dimension: 'Origin Risk', score: 88 },
  { dimension: 'Entity History', score: 65 },
  { dimension: 'Financial', score: 45 },
  { dimension: 'Regulatory', score: 91 },
  { dimension: 'Documentation', score: 78 },
];

function getRiskColor(score: number): string {
  if (score >= 80) return '#D83933';
  if (score >= 60) return '#FF9500';
  if (score >= 40) return '#F59E0B';
  return '#22c55e';
}

export default function RiskHeatmap({
  dimensions = FIXTURE_DIMENSIONS,
  title = 'Risk Profile Matrix',
  height = 350,
}: RiskHeatmapProps) {
  const [hoveredDimension, setHoveredDimension] = useState<string | null>(null);

  return (
    <div className="w-full">
      <div className="text-[9px] font-bold text-[#5C5C5C] uppercase mb-3">{title}</div>

      {/* Grid-based Heatmap */}
      <div className="space-y-2">
        {dimensions.map((dim) => (
          <div
            key={dim.dimension}
            onMouseEnter={() => setHoveredDimension(dim.dimension)}
            onMouseLeave={() => setHoveredDimension(null)}
            className={`transition-all ${hoveredDimension === dim.dimension ? 'opacity-100 scale-105' : 'opacity-100'}`}
          >
            {/* Dimension Label + Score */}
            <div className="flex items-center justify-between gap-3">
              <div className="w-32 text-[9px] font-bold text-[#0B1F33] truncate">{dim.dimension}</div>

              {/* Bar */}
              <div className="flex-1 h-6 bg-slate-100 rounded-sm overflow-hidden border border-slate-200">
                <div
                  style={{
                    width: `${dim.score}%`,
                    height: '100%',
                    background: getRiskColor(dim.score),
                    transition: 'all 0.3s ease',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'flex-end',
                    paddingRight: '4px',
                  }}
                >
                  <span className="text-[8px] font-bold text-white">{dim.score}%</span>
                </div>
              </div>

              {/* Risk Level Badge */}
              <div className="w-16 text-[8px] font-bold text-center">
                <span
                  className={`px-2 py-1 rounded text-white ${
                    dim.score >= 80
                      ? 'bg-[#D83933]'
                      : dim.score >= 60
                      ? 'bg-orange-600'
                      : dim.score >= 40
                      ? 'bg-amber-600'
                      : 'bg-green-600'
                  }`}
                >
                  {dim.score >= 80 ? 'CRITICAL' : dim.score >= 60 ? 'HIGH' : dim.score >= 40 ? 'MED' : 'LOW'}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="mt-4 pt-3 border-t border-[#D0D7DE] flex gap-3 flex-wrap justify-center text-[8px]">
        <div className="flex items-center gap-1">
          <div style={{ width: '12px', height: '12px', background: '#D83933', borderRadius: '2px' }} />
          <span className="font-bold">Critical (≥80)</span>
        </div>
        <div className="flex items-center gap-1">
          <div style={{ width: '12px', height: '12px', background: '#FF9500', borderRadius: '2px' }} />
          <span className="font-bold">High (60-79)</span>
        </div>
        <div className="flex items-center gap-1">
          <div style={{ width: '12px', height: '12px', background: '#F59E0B', borderRadius: '2px' }} />
          <span className="font-bold">Medium (40-59)</span>
        </div>
        <div className="flex items-center gap-1">
          <div style={{ width: '12px', height: '12px', background: '#22c55e', borderRadius: '2px' }} />
          <span className="font-bold">Low (&lt;40)</span>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="mt-4 grid grid-cols-3 gap-2 bg-[#F7F9FC] p-2 rounded text-[8px]">
        <div className="text-center">
          <div className="font-bold text-[#5C5C5C]">AVG RISK</div>
          <div className="text-[10px] font-bold text-[#0B1F33]">
            {Math.round(dimensions.reduce((a, b) => a + b.score, 0) / dimensions.length)}%
          </div>
        </div>
        <div className="text-center">
          <div className="font-bold text-[#5C5C5C]">MAX RISK</div>
          <div className="text-[10px] font-bold text-[#D83933]">{Math.max(...dimensions.map(d => d.score))}%</div>
        </div>
        <div className="text-center">
          <div className="font-bold text-[#5C5C5C]">CRITICAL COUNT</div>
          <div className="text-[10px] font-bold text-[#D83933]">
            {dimensions.filter(d => d.score >= 80).length}
          </div>
        </div>
      </div>
    </div>
  );
}
