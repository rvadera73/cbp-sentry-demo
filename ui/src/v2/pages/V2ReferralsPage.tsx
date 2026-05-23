import React, { useState } from 'react';
import { FileText, Download, Send } from 'lucide-react';
import { useV2Cases } from '../hooks/useV2Cases';
import { Case, ReferralPackage } from '../types/v2.types';

interface V2ReferralsPageProps {
  cases?: Case[];
  referrals?: ReferralPackage[];
  onGenerateReferral?: (caseId: string, sections: string[]) => Promise<void>;
}

export default function V2ReferralsPage({
  cases: propCases,
  referrals: propReferrals = [],
  onGenerateReferral,
}: V2ReferralsPageProps) {
  const { cases: localCases, loading } = useV2Cases();
  const cases = propCases || localCases;
  const referrals = propReferrals;

  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [generatingCaseId, setGeneratingCaseId] = useState<string | null>(null);
  const [selectedSections, setSelectedSections] = useState<Record<string, boolean>>({
    executive: true,
    corporate: true,
    forensic: true,
    legal: true,
  });

  const selectedCase = cases.find(c => c.case_id === selectedCaseId);
  const selectedReferral = selectedCaseId
    ? referrals.find(r => r.case_id === selectedCaseId)
    : null;

  const handleGenerateReferral = async () => {
    if (!selectedCaseId || !onGenerateReferral) return;

    setGeneratingCaseId(selectedCaseId);
    const sections = Object.entries(selectedSections)
      .filter(([_, checked]) => checked)
      .map(([key]) => key);

    try {
      await onGenerateReferral(selectedCaseId, sections);
    } catch (err) {
      console.error('Error generating referral:', err);
    } finally {
      setGeneratingCaseId(null);
    }
  };

  return (
    <div className="flex-1 flex overflow-hidden bg-[#F7F9FC]">
      {/* Cases List */}
      <div className="flex-1 p-5 overflow-y-auto border-r border-[#D0D7DE]">
        <h1 className="text-2xl font-bold text-[#0B1F33] mb-4">Referral Packages</h1>
        {loading ? (
          <div className="text-gray-500 text-sm">Loading cases...</div>
        ) : cases.length === 0 ? (
          <p className="text-gray-500 text-sm">No cases available</p>
        ) : (
          <div className="space-y-3">
            {cases.map(c => {
              const caseReferral = referrals.find(r => r.case_id === c.case_id);
              const isSelected = selectedCaseId === c.case_id;

              return (
                <div
                  key={c.case_id}
                  onClick={() => setSelectedCaseId(c.case_id)}
                  className={`p-4 rounded-sm border-2 cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-[#F0F4F8] border-[#005EA2] shadow-md'
                      : 'bg-white border-[#D0D7DE] hover:border-[#005EA2]'
                  }`}
                >
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex-1">
                      <h3 className="font-bold text-[#0B1F33]">{c.case_name}</h3>
                      <p className="text-[9px] text-[#5C5C5C] font-mono">{c.case_id}</p>
                    </div>
                    {caseReferral ? (
                      <span className="px-2 py-1 text-[9px] font-bold rounded bg-green-100 text-green-800 whitespace-nowrap">
                        {caseReferral.package_status}
                      </span>
                    ) : (
                      <span className="px-2 py-1 text-[9px] font-bold rounded bg-gray-100 text-gray-600 whitespace-nowrap">
                        No Referral
                      </span>
                    )}
                  </div>

                  {/* Case Summary */}
                  <div className="space-y-1 text-[9px]">
                    <p className="text-[#5C5C5C]"><span className="font-bold">Entity:</span> {c.target_entity.split('/')[0]}</p>
                    <p className="text-[#5C5C5C]"><span className="font-bold">Risk:</span> {c.risk_score}%</p>
                    <p className="text-[#5C5C5C]"><span className="font-bold">Opened:</span> {c.opened_date}</p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Dossier Viewer */}
      {selectedCase ? (
        <div className="w-2/3 flex flex-col border-l border-[#D0D7DE] bg-white overflow-hidden">
          {/* Header */}
          <div className="bg-[#F7F9FC] border-b border-[#D0D7DE] p-4 shrink-0">
            <h2 className="text-lg font-bold text-[#0B1F33] mb-1">{selectedCase.case_name}</h2>
            <p className="text-xs text-[#5C5C5C]">{selectedCase.case_id} • {selectedCase.target_entity}</p>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto flex flex-col">
            {!selectedReferral ? (
              /* Generator View */
              <div className="p-6 space-y-6">
                <div>
                  <h3 className="font-bold text-[#0B1F33] mb-4">Generate Referral Package</h3>
                  <p className="text-sm text-[#5C5C5C] mb-4">
                    Select the sections to include in your DHS-compliant referral narrative:
                  </p>

                  {/* Section Checkboxes */}
                  <div className="bg-slate-50 border border-slate-200 rounded p-4 space-y-3 mb-6">
                    {[
                      {
                        key: 'executive',
                        label: 'Executive Summary',
                        description: 'High-level overview of the case and key findings',
                      },
                      {
                        key: 'corporate',
                        label: 'Corporate Overview',
                        description: 'Beneficial owner relationships and corporate structure',
                      },
                      {
                        key: 'forensic',
                        label: 'Forensic Evidence',
                        description: 'Detailed analysis of manifest anomalies and patterns',
                      },
                      {
                        key: 'legal',
                        label: 'Legal Analysis',
                        description: 'Applicable violations and enforcement recommendations',
                      },
                    ].map(section => (
                      <label key={section.key} className="flex items-start space-x-3 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={selectedSections[section.key]}
                          onChange={(e) =>
                            setSelectedSections({
                              ...selectedSections,
                              [section.key]: e.target.checked,
                            })
                          }
                          className="w-4 h-4 border border-gray-300 rounded mt-1"
                        />
                        <div className="flex-1">
                          <p className="font-bold text-sm text-[#0B1F33]">{section.label}</p>
                          <p className="text-[9px] text-[#5C5C5C]">{section.description}</p>
                        </div>
                      </label>
                    ))}
                  </div>

                  {/* Generate Button */}
                  <button
                    onClick={handleGenerateReferral}
                    disabled={generatingCaseId === selectedCase.case_id}
                    className="w-full px-4 py-3 bg-[#005EA2] hover:bg-[#0076D6] disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold rounded-sm text-sm transition-colors flex items-center justify-center space-x-2"
                  >
                    <FileText className="w-4 h-4" />
                    <span>
                      {generatingCaseId === selectedCase.case_id
                        ? 'Generating Draft...'
                        : 'COMPILE AI TRADE DRAFT'}
                    </span>
                  </button>

                  <p className="text-[9px] text-gray-500 mt-3 text-center">
                    AI will generate a DHS-compliant referral narrative based on your selections
                  </p>
                </div>
              </div>
            ) : (
              /* Dossier View */
              <div className="flex-1 flex flex-col">
                {/* Narrative Editor */}
                <div className="flex-1 overflow-hidden flex flex-col p-6 space-y-4">
                  <div>
                    <h3 className="font-bold text-[#0B1F33] text-sm mb-2">Referral Narrative</h3>
                    <div className="bg-[#0B1F33] text-white p-4 rounded font-mono text-xs rounded-sm max-h-96 overflow-y-auto whitespace-pre-wrap leading-relaxed">
                      {selectedReferral.narrative ? (
                        Object.entries(selectedReferral.narrative).map(([key, value]) =>
                          value ? (
                            <div key={key} className="mb-4">
                              <div className="text-[#00BDE3] font-bold mb-1">
                                [{key.toUpperCase().replace(/_/g, ' ')}]
                              </div>
                              <div>{value}</div>
                            </div>
                          ) : null
                        )
                      ) : (
                        <div>Generating narrative...</div>
                      )}
                    </div>
                  </div>

                  {/* Submission Status */}
                  <div className="bg-blue-50 border border-blue-200 rounded p-3">
                    <p className="text-[9px] font-bold text-blue-900">
                      Status: {selectedReferral.package_status}
                    </p>
                    <p className="text-[9px] text-blue-800 mt-1">
                      Generated: {selectedReferral.generated_date}
                    </p>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="border-t border-[#D0D7DE] p-4 bg-[#F7F9FC] flex gap-2 shrink-0">
                  <button className="flex-1 px-4 py-2 flex items-center justify-center space-x-2 bg-[#00BDE3] hover:bg-cyan-600 text-white text-sm font-bold rounded-sm transition-colors">
                    <Download className="w-4 h-4" />
                    <span>Export PDF</span>
                  </button>
                  <button className="flex-1 px-4 py-2 flex items-center justify-center space-x-2 bg-green-600 hover:bg-green-700 text-white text-sm font-bold rounded-sm transition-colors">
                    <Send className="w-4 h-4" />
                    <span>Submit Package</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Empty State */
        <div className="flex-1 flex flex-col items-center justify-center bg-white border-l border-[#D0D7DE] text-center">
          <FileText className="w-12 h-12 text-gray-300 mb-3" />
          <h3 className="font-bold text-[#0B1F33] text-sm mb-1">No Case Selected</h3>
          <p className="text-[9px] text-[#5C5C5C]">Select a case from the list to view or create a referral package</p>
        </div>
      )}
    </div>
  );
}
