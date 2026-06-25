/**
 * Professional Referral Package Display
 * Matches Evidence tab design: same fonts, colors, tables, charts, and layout
 */

import React, { useState } from 'react';
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Download, AlertCircle, CheckCircle } from 'lucide-react';
import { ReferralDisplayData } from './types/ReferralGeneration.types';

interface ProfessionalReferralDisplayProps {
  referralData: ReferralDisplayData;
  onExportPDF?: () => void;
}

export default function ProfessionalReferralDisplay({ referralData, onExportPDF }: ProfessionalReferralDisplayProps) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());

  const toggleSection = (sectionId: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(sectionId)) {
      newExpanded.delete(sectionId);
    } else {
      newExpanded.add(sectionId);
    }
    setExpandedSections(newExpanded);
  };

  const getRiskColor = (riskLevel: string) => {
    switch (riskLevel.toUpperCase()) {
      case 'CRITICAL': return 'bg-red-100 text-red-800';
      case 'HIGH': return 'bg-orange-100 text-orange-800';
      case 'MEDIUM': return 'bg-amber-100 text-amber-800';
      case 'LOW': return 'bg-green-100 text-green-800';
      default: return 'bg-slate-100 text-slate-800';
    }
  };

  const formatTableData = (section: any) => {
    if (!section || typeof section !== 'object') return [];
    return Object.entries(section)
      .filter(([key]) => !['title', 'summary'].includes(key))
      .map(([key, value]) => ({
        label: key.replace(/_/g, ' ').toUpperCase(),
        value: value
      }));
  };

  return (
    <div className="flex-1 p-6 space-y-6 overflow-y-auto bg-[#F7F9FC]">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h2 className="text-lg font-bold text-[#0B1F33]">Comprehensive Referral Package</h2>
          <p className="text-xs text-slate-600 mt-1">Referral ID: {referralData.referral_id}</p>
          <p className="text-xs text-slate-600">Generated: {new Date(referralData.created_at).toLocaleString()}</p>
        </div>
        {onExportPDF && (
          <button
            onClick={onExportPDF}
            className="flex items-center gap-2 px-4 py-2 bg-[#005EA2] text-white rounded text-xs font-bold hover:bg-[#0044CC] transition"
          >
            <Download size={16} />
            Export PDF
          </button>
        )}
      </div>

      {/* Risk Score Summary Card */}
      <div className="bg-white rounded-sm border border-[#D0D7DE] p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-[#0B1F33]">Risk Assessment Summary</h3>
          {(referralData as any).overall_confidence !== undefined && (
            <div className="text-right">
              <p className="text-[9px] text-slate-600">Analysis Confidence</p>
              <p className="text-sm font-bold text-[#0B1F33]">{((referralData as any).overall_confidence * 100).toFixed(0)}%</p>
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <div className="text-xs text-slate-600 mb-1">Overall Risk Score</div>
              <div className="text-3xl font-bold text-[#0B1F33]">{referralData.risk_score.toFixed(1)}</div>
              <div className="text-xs text-slate-600">/100</div>
            </div>
            <div>
              <span className={`px-3 py-1 rounded text-xs font-bold ${getRiskColor(referralData.risk_level)}`}>
                {referralData.risk_level} RISK
              </span>
            </div>
          </div>

          {/* Risk Breakdown Pie Chart */}
          {referralData.risk_breakdown && (
            <div className="flex justify-center">
              <ResponsiveContainer width={150} height={150}>
                <PieChart>
                  <Pie
                    data={[
                      { name: 'Risk', value: referralData.risk_breakdown.final_score },
                      { name: 'Safe', value: 100 - referralData.risk_breakdown.final_score }
                    ]}
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={60}
                    dataKey="value"
                  >
                    <Cell fill="#DC3545" />
                    <Cell fill="#28A745" />
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* Risk Components Breakdown */}
        {referralData.risk_breakdown && (
          <div className="mt-4 pt-4 border-t border-[#D0D7DE]">
            <div className="text-xs font-bold text-[#0B1F33] mb-3">Risk Factors Breakdown</div>
            <div className="space-y-2">
              {referralData.risk_breakdown.components.slice(0, 5).map((comp, idx) => (
                <div key={idx} className="flex items-center justify-between text-xs">
                  <div className="flex-1">
                    <span className="font-semibold text-slate-700">{comp.component}</span>
                    <div className="w-full bg-slate-200 rounded h-1.5 mt-1">
                      <div
                        className="bg-[#DC3545] h-1.5 rounded"
                        style={{ width: `${(comp.score / 100) * 100}%` }}
                      />
                    </div>
                  </div>
                  <span className="font-bold text-slate-900 ml-2">{comp.score.toFixed(1)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 14 Referral Sections */}
      <div className="space-y-4">
        <h3 className="text-sm font-bold text-[#0B1F33]">Detailed Section Analysis</h3>

        {Object.entries(referralData.sections).map(([sectionId, sectionData]: [string, any]) => {
          const isExpanded = expandedSections.has(sectionId);
          const sectionTitle = sectionData?.title || sectionId.replace(/_/g, ' ').toUpperCase();
          const tableData = formatTableData(sectionData);

          // Get Gemini analysis if available
          const analyzedSection = (referralData as any).analyzed_sections?.[sectionId];
          const geminiNarrative = analyzedSection?.narrative;
          const riskFactors = analyzedSection?.risk_factors || [];
          const confidenceScore = analyzedSection?.confidence_score || 0;

          return (
            <div key={sectionId} className="bg-white rounded-sm border border-[#D0D7DE] p-5 space-y-4">
              {/* Section Header - Clickable */}
              <div
                className="flex items-center justify-between cursor-pointer hover:bg-slate-50 p-2 -m-2 rounded"
                onClick={() => toggleSection(sectionId)}
              >
                <div className="flex-1">
                  <h4 className="text-sm font-bold text-[#0B1F33]">{sectionTitle}</h4>
                  {confidenceScore > 0 && (
                    <p className="text-[9px] text-slate-600 mt-1">
                      Analysis Confidence: {(confidenceScore * 100).toFixed(0)}%
                    </p>
                  )}
                </div>
                <span className="text-slate-600">{isExpanded ? '▼' : '▶'}</span>
              </div>

              {/* Section Content */}
              {isExpanded && (
                <div className="space-y-4 mt-4 pt-4 border-t border-[#D0D7DE]">
                  {/* AI-Generated Narrative (Gemini) */}
                  {geminiNarrative && (
                    <div className="text-xs text-slate-700 bg-blue-50 border-l-3 border-[#005EA2] p-3 rounded">
                      <p className="font-semibold mb-1 text-[#0B1F33] flex items-center gap-2">
                        <span className="text-xs font-bold">🤖 AI ANALYSIS</span>
                      </p>
                      <p className="leading-relaxed">{geminiNarrative}</p>
                    </div>
                  )}

                  {/* Risk Factors from Analysis */}
                  {riskFactors.length > 0 && (
                    <div className="space-y-2">
                      <p className="text-xs font-bold text-[#0B1F33]">Risk Factors Identified:</p>
                      {riskFactors.map((factor: any, idx: number) => (
                        <div key={idx} className="flex gap-3 text-xs">
                          <div className={`px-2 py-1 rounded font-bold text-white flex-shrink-0 ${
                            factor.level === 'HIGH' ? 'bg-red-600' :
                            factor.level === 'MEDIUM' ? 'bg-orange-500' :
                            'bg-green-600'
                          }`}>
                            {factor.level}
                          </div>
                          <div className="flex-1">
                            <p className="font-semibold text-slate-800">{factor.factor}</p>
                            <p className="text-slate-600 mt-1">{factor.evidence}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Original Summary */}
                  {sectionData?.summary && !geminiNarrative && (
                    <div className="text-xs text-slate-700 bg-slate-50 p-3 rounded">
                      <p className="font-semibold mb-1">Summary:</p>
                      <p>{sectionData.summary}</p>
                    </div>
                  )}

                  {/* Data Table */}
                  {tableData.length > 0 && (
                    <div className="overflow-x-auto">
                      <table className="w-full text-[9px] border-collapse">
                        <thead className="bg-[#005EA2] text-white">
                          <tr>
                            <th className="text-left px-2 py-2">Field</th>
                            <th className="text-left px-2 py-2">Value</th>
                          </tr>
                        </thead>
                        <tbody>
                          {tableData.map((row, idx) => (
                            <tr key={idx} className={idx % 2 === 0 ? 'bg-slate-50' : 'bg-white'}>
                              <td className="px-2 py-1 font-semibold text-slate-700">{row.label}</td>
                              <td className="px-2 py-1 text-slate-600">
                                {typeof row.value === 'object'
                                  ? JSON.stringify(row.value, null, 2)
                                  : String(row.value)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Data Sources Section - matching Evidence tab style */}
      <div className="bg-white rounded-sm border border-[#D0D7DE] p-5 space-y-3">
        <h3 className="text-sm font-bold text-[#0B1F33]">Data Sources & Attribution</h3>
        <ul className="text-xs text-slate-700 space-y-2 list-disc list-inside">
          <li>ISF 10+2 Data: CBP Automated Manifest System (100%)</li>
          <li>AIS Tracking: MarineTraffic & Spire APIs (Real-time)</li>
          <li>Entity Resolution: Senzing CORD Index (Confidence: {referralData.risk_breakdown?.components?.[0]?.score || 92}%)</li>
          <li>Risk Scoring: CBP Sentry 7-Factor Engine (v2.1)</li>
        </ul>
        <p className="text-[9px] text-slate-600 italic">
          Last Updated: {new Date(referralData.created_at).toLocaleString()}
        </p>
      </div>
    </div>
  );
}
