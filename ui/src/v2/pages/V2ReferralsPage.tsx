import React, { useState } from 'react';
import { useV2Cases } from '../hooks/useV2Cases';

export default function V2ReferralsPage() {
  const { cases, loading } = useV2Cases();
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);

  if (loading) return <div className="p-6 text-center">Loading referrals...</div>;

  const referralCases = cases.filter(c => c.referral_status !== 'Not Initiated');
  const selectedCase = cases.find(c => c.case_id === selectedCaseId);

  return (
    <div className="flex-1 flex overflow-hidden bg-[#F7F9FC]">
      <div className="flex-1 p-5 overflow-y-auto">
        <h1 className="text-2xl font-bold text-[#0B1F33] mb-4">Referral Packages</h1>
        {referralCases.length === 0 ? (
          <p className="text-gray-500">No referral packages in progress</p>
        ) : (
          <div className="space-y-3">
            {referralCases.map(c => (
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
                    <p className="text-xs text-[#5C5C5C]">{c.case_id}</p>
                  </div>
                  <span className="px-2 py-1 text-[10px] font-bold rounded bg-blue-100 text-blue-900">
                    {c.referral_status}
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {selectedCase && (
        <div className="w-96 border-l border-[#D0D7DE] bg-white overflow-y-auto p-5">
          <h2 className="text-lg font-bold text-[#0B1F33] mb-4">Referral Detail</h2>
          <div className="space-y-4 text-sm">
            <div>
              <label className="text-xs font-bold text-[#5C5C5C] uppercase">Case</label>
              <p className="text-[#0B1F33]">{selectedCase.case_name}</p>
            </div>
            <div>
              <label className="text-xs font-bold text-[#5C5C5C] uppercase">Status</label>
              <p className="text-[#0B1F33]">{selectedCase.referral_status}</p>
            </div>
            <div>
              <label className="text-xs font-bold text-[#5C5C5C] uppercase">Target Entity</label>
              <p className="text-[#0B1F33]">{selectedCase.target_entity}</p>
            </div>
            <div className="pt-4 border-t border-[#D0D7DE]">
              <h4 className="text-xs font-bold text-[#112E51] mb-2 uppercase">Referral Sections</h4>
              <ul className="space-y-1 text-[#5C5C5C] text-xs">
                <li>✓ Executive Summary</li>
                <li>✓ Subject Overview</li>
                <li>✓ Investigation Findings</li>
                <li>✓ Evidence Analysis</li>
                <li>✓ Recommended Actions</li>
              </ul>
            </div>
            <div className="pt-4 border-t border-[#D0D7DE] flex gap-2">
              <button className="flex-1 px-3 py-2 bg-[#005EA2] hover:bg-[#0076D6] text-white text-xs font-bold rounded-sm">
                View Full
              </button>
              <button className="flex-1 px-3 py-2 bg-[#00BDE3] hover:bg-cyan-600 text-white text-xs font-bold rounded-sm">
                Export PDF
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
