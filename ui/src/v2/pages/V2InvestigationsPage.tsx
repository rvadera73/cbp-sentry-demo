import React, { useState } from 'react';
import { useV2Cases } from '../hooks/useV2Cases';

export default function V2InvestigationsPage() {
  const { cases, loading } = useV2Cases();
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);

  if (loading) return <div className="p-6 text-center">Loading investigations...</div>;

  const selectedCase = cases.find(c => c.case_id === selectedCaseId);

  return (
    <div className="flex-1 flex overflow-hidden bg-[#F7F9FC]">
      {/* Case List */}
      <div className="flex-1 p-5 overflow-y-auto">
        <h1 className="text-2xl font-bold text-[#0B1F33] mb-4">Active Investigations</h1>
        <div className="space-y-3">
          {cases.map(c => (
            <button
              key={c.case_id}
              onClick={() => setSelectedCaseId(c.case_id)}
              className={`w-full p-4 rounded-sm border-2 text-left transition-all ${
                selectedCaseId === c.case_id
                  ? 'bg-[#F0F4F8] border-[#005EA2]'
                  : 'bg-white border-[#D0D7DE] hover:border-[#005EA2]'
              }`}
            >
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-bold text-[#0B1F33]">{c.case_name}</h3>
                  <p className="text-xs text-[#5C5C5C]">{c.case_id} • {c.target_entity}</p>
                </div>
                <span className={`px-2 py-1 text-xs font-bold rounded ${
                  c.risk_score >= 90 ? 'bg-[#D83933] text-white' : 'bg-amber-100 text-amber-900'
                }`}>
                  {c.risk_score}%
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Case Detail */}
      {selectedCase && (
        <div className="w-96 border-l border-[#D0D7DE] bg-white overflow-y-auto p-5">
          <h2 className="text-lg font-bold text-[#0B1F33] mb-4">{selectedCase.case_name}</h2>
          <div className="space-y-4">
            <div>
              <label className="text-xs font-bold text-[#5C5C5C] uppercase">Target Entity</label>
              <p className="text-sm text-[#0B1F33]">{selectedCase.target_entity}</p>
            </div>
            <div>
              <label className="text-xs font-bold text-[#5C5C5C] uppercase">Risk Score</label>
              <p className="text-sm text-[#0B1F33] font-mono">{selectedCase.risk_score} / 100</p>
            </div>
            <div>
              <label className="text-xs font-bold text-[#5C5C5C] uppercase">Status</label>
              <p className="text-sm text-[#0B1F33]">{selectedCase.case_status}</p>
            </div>
            <div>
              <label className="text-xs font-bold text-[#5C5C5C] uppercase">AI Synopsis</label>
              <p className="text-xs text-[#5C5C5C] leading-relaxed">
                {selectedCase.ai_synopsis || 'Investigation into illegal transshipment evasion patterns...'}
              </p>
            </div>
            <button className="w-full mt-4 px-4 py-2 bg-[#005EA2] hover:bg-[#0076D6] text-white text-sm font-bold rounded-sm">
              Open Case Detail
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
