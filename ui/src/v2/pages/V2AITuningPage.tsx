import React, { useState } from 'react';

export default function V2AITuningPage() {
  const [aisWeight, setAisWeight] = useState(87);
  const [weightDeviation, setWeightDeviation] = useState(74);
  const [circularInvoicing, setCircularInvoicing] = useState(91);
  const [forcedLabor, setForcedLabor] = useState(94);
  const [autoHoldThreshold, setAutoHoldThreshold] = useState(80);

  const [rules, setRules] = useState({
    rule1: true,
    rule2: true,
    rule3: true,
  });

  return (
    <div className="flex-1 grid grid-cols-3 gap-5 p-5 overflow-y-auto bg-[#F7F9FC]">
      {/* Left: Weight Sliders */}
      <div className="col-span-2 bg-white rounded-sm border border-[#D0D7DE] p-5 shadow-sm">
        <h2 className="text-lg font-bold text-[#0B1F33] mb-4">AI Algorithmic Parameter Weights (%)</h2>
        <div className="space-y-6">
          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="text-xs font-bold text-[#112E51] uppercase font-mono">
                AIS Signal Spoof Weight
              </label>
              <span className="text-lg font-bold text-[#005EA2] font-mono">{aisWeight}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={aisWeight}
              onChange={(e) => setAisWeight(Number(e.target.value))}
              className="w-full h-2 bg-gray-200 rounded-full appearance-none cursor-pointer"
            />
          </div>

          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="text-xs font-bold text-[#112E51] uppercase font-mono">
                Weight Deviation Coefficient
              </label>
              <span className="text-lg font-bold text-amber-600 font-mono">{weightDeviation}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={weightDeviation}
              onChange={(e) => setWeightDeviation(Number(e.target.value))}
              className="w-full h-2 bg-gray-200 rounded-full appearance-none cursor-pointer"
            />
          </div>

          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="text-xs font-bold text-[#112E51] uppercase font-mono">
                Circular Invoicing Layer Coefficient
              </label>
              <span className="text-lg font-bold text-[#D83933] font-mono">{circularInvoicing}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={circularInvoicing}
              onChange={(e) => setCircularInvoicing(Number(e.target.value))}
              className="w-full h-2 bg-gray-200 rounded-full appearance-none cursor-pointer"
            />
          </div>

          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="text-xs font-bold text-[#112E51] uppercase font-mono">
                Xinjiang Labor Export Correlation
              </label>
              <span className="text-lg font-bold text-red-600 font-mono">{forcedLabor}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={forcedLabor}
              onChange={(e) => setForcedLabor(Number(e.target.value))}
              className="w-full h-2 bg-gray-200 rounded-full appearance-none cursor-pointer"
            />
          </div>

          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="text-xs font-bold text-[#112E51] uppercase font-mono">
                Automatic Hold Confidence Threshold
              </label>
              <span className={`text-lg font-bold font-mono ${autoHoldThreshold >= 80 ? 'text-[#D83933]' : 'text-gray-600'}`}>
                {autoHoldThreshold}%
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={autoHoldThreshold}
              onChange={(e) => setAutoHoldThreshold(Number(e.target.value))}
              className="w-full h-2 bg-gray-200 rounded-full appearance-none cursor-pointer"
            />
          </div>
        </div>

        <button className="w-full mt-8 px-4 py-3 bg-[#005EA2] hover:bg-[#0076D6] text-white font-bold rounded-sm cursor-pointer">
          Recalibrate System Profile Matrix
        </button>
      </div>

      {/* Right: Rule Toggles */}
      <div className="bg-white rounded-sm border border-[#D0D7DE] p-5 shadow-sm h-fit">
        <h2 className="text-lg font-bold text-[#0B1F33] mb-4">Active Screening Rules</h2>
        <div className="space-y-3">
          <label className="flex items-start space-x-3 p-2 rounded hover:bg-slate-50 cursor-pointer">
            <input
              type="checkbox"
              checked={rules.rule1}
              onChange={(e) => setRules({ ...rules, rule1: e.target.checked })}
              className="mt-1"
            />
            <div className="text-xs">
              <span className="font-bold text-[#0B1F33] block">W-121</span>
              <span className="text-[#5C5C5C] block">MANDATORY HOLD UNVERIFIED RELEGATED IMPORTER</span>
            </div>
          </label>

          <label className="flex items-start space-x-3 p-2 rounded hover:bg-slate-50 cursor-pointer">
            <input
              type="checkbox"
              checked={rules.rule2}
              onChange={(e) => setRules({ ...rules, rule2: e.target.checked })}
              className="mt-1"
            />
            <div className="text-xs">
              <span className="font-bold text-[#0B1F33] block">W-822</span>
              <span className="text-[#5C5C5C] block">AIS SILENT COORDINATE PATTERN ANOMALY</span>
            </div>
          </label>

          <label className="flex items-start space-x-3 p-2 rounded hover:bg-slate-50 cursor-pointer border-2 border-red-200 bg-red-50">
            <input
              type="checkbox"
              checked={rules.rule3}
              onChange={(e) => setRules({ ...rules, rule3: e.target.checked })}
              className="mt-1"
            />
            <div className="text-xs">
              <span className="font-bold text-[#0B1F33] block">UFLPA-301</span>
              <span className="text-red-700 font-bold block">SILICON AD/CVD RECLASSIFICATION RATE</span>
              <span className="text-[#5C5C5C] text-[10px]">244.5% AD/CVD applied</span>
            </div>
          </label>
        </div>

        <button className="w-full mt-6 px-4 py-2 bg-[#112E51] hover:bg-[#005EA2] text-white text-sm font-bold rounded-sm cursor-pointer">
          Save Rules Configuration
        </button>
      </div>
    </div>
  );
}
