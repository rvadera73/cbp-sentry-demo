/**
 * Professional Officer Analysis Form
 * 4-step workflow matching Evidence tab design
 */

import React, { useState } from 'react';
import { ChevronRight, ChevronLeft, CheckCircle, AlertCircle, Save, Download } from 'lucide-react';
import { ReferralDisplayData } from './types/ReferralGeneration.types';

interface ProfessionalOfficerAnalysisFormProps {
  referralId: string;
  referralData: ReferralDisplayData;
  onSubmit?: (data: any) => Promise<void>;
  onCancel?: () => void;
}

export default function ProfessionalOfficerAnalysisForm({
  referralId,
  referralData,
  onSubmit,
  onCancel
}: ProfessionalOfficerAnalysisFormProps) {
  const [currentStep, setCurrentStep] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const [formData, setFormData] = useState({
    step1: {
      agreeWithScore: true,
      adjustedScore: referralData.risk_score,
      reasoning: ''
    },
    step2: {
      reviewedItems: {
        element9: false,
        dwell: false,
        pricing: false,
        entity: false,
        ais: false
      },
      notes: ''
    },
    step3: {
      action: 'hold_examine',
      priority: 'high',
      holdDurationDays: 10,
      examinationType: 'documentary',
      reasoning: ''
    },
    step4: {
      officerName: '',
      badgeNumber: '',
      caseNarrative: '',
      certificationAccepted: false
    }
  });

  const handleNextStep = () => {
    if (currentStep < 4) setCurrentStep(currentStep + 1);
  };

  const handlePrevStep = () => {
    if (currentStep > 1) setCurrentStep(currentStep - 1);
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      if (onSubmit) {
        await onSubmit(formData);
      }
      setSubmitted(true);
    } catch (err) {
      console.error('Submission failed:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const progressPercent = (currentStep / 4) * 100;

  if (submitted) {
    return (
      <div className="flex-1 p-6 space-y-6 overflow-y-auto bg-[#F7F9FC]">
        <div className="bg-white rounded-sm border border-[#D0D7DE] p-8 space-y-4 max-w-2xl">
          <div className="flex items-center justify-center mb-4">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
              <CheckCircle size={32} className="text-green-700" />
            </div>
          </div>
          <h2 className="text-2xl font-bold text-[#0B1F33] text-center">Analysis Submitted Successfully</h2>
          <p className="text-sm text-slate-600 text-center">
            Your officer analysis for referral {referralId} has been recorded in the system.
          </p>

          <div className="bg-slate-50 p-4 rounded space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="font-semibold">Submission Time:</span>
              <span>{new Date().toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="font-semibold">Recommended Action:</span>
              <span className="font-bold text-[#0B1F33] uppercase">{formData.step3.action}</span>
            </div>
            <div className="flex justify-between">
              <span className="font-semibold">Risk Assessment:</span>
              <span>{formData.step1.agreeWithScore ? 'Confirmed' : 'Adjusted'}</span>
            </div>
          </div>

          <div className="flex gap-3 pt-4">
            <button
              onClick={() => {
                const element = document.querySelector('.referral-gen-tab__content');
                element?.scrollIntoView({ behavior: 'smooth' });
              }}
              className="flex-1 px-4 py-2 bg-[#005EA2] text-white rounded text-xs font-bold hover:bg-[#0044CC] transition flex items-center justify-center gap-2"
            >
              <Download size={16} />
              Export Final Package
            </button>
            <button
              onClick={onCancel}
              className="flex-1 px-4 py-2 bg-slate-200 text-slate-700 rounded text-xs font-bold hover:bg-slate-300 transition"
            >
              Back to Referral
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 p-6 space-y-6 overflow-y-auto bg-[#F7F9FC]">
      {/* Progress Bar */}
      <div className="bg-white rounded-sm border border-[#D0D7DE] p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-bold text-[#0B1F33]">Officer Analysis Workflow</h3>
          <span className="text-xs font-semibold text-slate-600">Step {currentStep} of 4</span>
        </div>
        <div className="w-full bg-slate-200 rounded h-2">
          <div
            className="bg-[#005EA2] h-2 rounded transition-all"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <p className="text-xs text-slate-600 mt-2">
          {currentStep === 1 && 'Review and confirm the automated risk assessment'}
          {currentStep === 2 && 'Review key evidence supporting the risk score'}
          {currentStep === 3 && 'Recommend enforcement action based on risk assessment'}
          {currentStep === 4 && 'Certify analysis and sign off on decision'}
        </p>
      </div>

      {/* Step 1: Risk Assessment */}
      {currentStep === 1 && (
        <div className="bg-white rounded-sm border border-[#D0D7DE] p-5 space-y-4">
          <h3 className="text-sm font-bold text-[#0B1F33]">Step 1: Risk Assessment Confirmation</h3>

          <div className="bg-slate-50 p-4 rounded space-y-3">
            <div>
              <p className="text-xs font-semibold text-slate-700 mb-2">Automated Risk Score</p>
              <div className="flex items-end gap-3">
                <div className="text-4xl font-bold text-[#0B1F33]">{referralData.risk_score.toFixed(1)}</div>
                <span className={`px-2 py-1 rounded text-xs font-bold ${
                  referralData.risk_level === 'HIGH' ? 'bg-orange-100 text-orange-800' :
                  referralData.risk_level === 'CRITICAL' ? 'bg-red-100 text-red-800' :
                  'bg-amber-100 text-amber-800'
                }`}>
                  {referralData.risk_level} RISK
                </span>
              </div>
            </div>
          </div>

          <div className="border-t border-[#D0D7DE] pt-4 space-y-3">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="radio"
                checked={formData.step1.agreeWithScore}
                onChange={() => setFormData(prev => ({ ...prev, step1: { ...prev.step1, agreeWithScore: true } }))}
                className="w-4 h-4"
              />
              <span className="text-xs text-slate-700"><span className="font-semibold">✓ Accept</span> the automated risk score</span>
            </label>
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="radio"
                checked={!formData.step1.agreeWithScore}
                onChange={() => setFormData(prev => ({ ...prev, step1: { ...prev.step1, agreeWithScore: false } }))}
                className="w-4 h-4"
              />
              <span className="text-xs text-slate-700"><span className="font-semibold">✗ Adjust</span> the risk score</span>
            </label>

            {!formData.step1.agreeWithScore && (
              <div className="ml-6 space-y-2">
                <label className="block text-xs font-semibold text-slate-700">Adjusted Score:</label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={formData.step1.adjustedScore}
                  onChange={(e) => setFormData(prev => ({ ...prev, step1: { ...prev.step1, adjustedScore: parseFloat(e.target.value) } }))}
                  className="w-full px-2 py-1 border border-[#D0D7DE] rounded text-xs"
                />
              </div>
            )}

            <label className="block text-xs font-semibold text-slate-700 pt-2">Reasoning/Justification:</label>
            <textarea
              value={formData.step1.reasoning}
              onChange={(e) => setFormData(prev => ({ ...prev, step1: { ...prev.step1, reasoning: e.target.value } }))}
              className="w-full px-2 py-2 border border-[#D0D7DE] rounded text-xs font-mono"
              rows={3}
              placeholder="Explain your assessment of the risk score..."
            />
          </div>
        </div>
      )}

      {/* Step 2: Evidence Review */}
      {currentStep === 2 && (
        <div className="bg-white rounded-sm border border-[#D0D7DE] p-5 space-y-4">
          <h3 className="text-sm font-bold text-[#0B1F33]">Step 2: Evidence Review Checklist</h3>

          <div className="space-y-3">
            {[
              { key: 'element9', label: 'ISF Element 9 Mismatch Detection', required: true },
              { key: 'dwell', label: 'Vessel Dwell Time Anomaly Analysis', required: true },
              { key: 'pricing', label: 'Price Variance Analysis', required: true },
              { key: 'entity', label: 'Entity Resolution Report', required: true },
              { key: 'ais', label: 'AIS Routing Pattern Analysis', required: false }
            ].map(item => (
              <label key={item.key} className="flex items-start gap-3 cursor-pointer p-2 hover:bg-slate-50 rounded">
                <input
                  type="checkbox"
                  checked={formData.step2.reviewedItems[item.key as keyof typeof formData.step2.reviewedItems]}
                  onChange={(e) => setFormData(prev => ({
                    ...prev,
                    step2: {
                      ...prev.step2,
                      reviewedItems: {
                        ...prev.step2.reviewedItems,
                        [item.key]: e.target.checked
                      }
                    }
                  }))}
                  className="w-4 h-4 mt-0.5"
                />
                <div className="flex-1 text-xs">
                  <span className="text-slate-700">{item.label}</span>
                  {item.required && <span className="text-red-600 ml-1">*</span>}
                </div>
              </label>
            ))}
          </div>

          <div className="border-t border-[#D0D7DE] pt-4 space-y-2">
            <label className="block text-xs font-semibold text-slate-700">Officer Notes:</label>
            <textarea
              value={formData.step2.notes}
              onChange={(e) => setFormData(prev => ({ ...prev, step2: { ...prev.step2, notes: e.target.value } }))}
              className="w-full px-2 py-2 border border-[#D0D7DE] rounded text-xs font-mono"
              rows={3}
              placeholder="Document your evidence review findings..."
            />
          </div>
        </div>
      )}

      {/* Step 3: Enforcement Action */}
      {currentStep === 3 && (
        <div className="bg-white rounded-sm border border-[#D0D7DE] p-5 space-y-4">
          <h3 className="text-sm font-bold text-[#0B1F33]">Step 3: Enforcement Action Recommendation</h3>

          <div className="space-y-3">
            <label className="block text-xs font-semibold text-slate-700">Recommended Action:</label>
            <div className="space-y-2">
              {[
                { value: 'trled', label: 'Execute TRLED Referral', desc: 'Refer to enforcement unit' },
                { value: 'hold_examine', label: 'Hold for Examination', desc: 'Physical or documentary exam' },
                { value: 'release_monitor', label: 'Release with Monitoring', desc: 'Release with follow-up' }
              ].map(action => (
                <label key={action.value} className="flex items-start gap-3 cursor-pointer p-2 hover:bg-slate-50 rounded border border-slate-200">
                  <input
                    type="radio"
                    name="action"
                    value={action.value}
                    checked={formData.step3.action === action.value}
                    onChange={(e) => setFormData(prev => ({ ...prev, step3: { ...prev.step3, action: e.target.value } }))}
                    className="w-4 h-4 mt-0.5"
                  />
                  <div className="flex-1">
                    <p className="text-xs font-semibold text-slate-700">{action.label}</p>
                    <p className="text-xs text-slate-500">{action.desc}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {formData.step3.action === 'hold_examine' && (
            <div className="border-t border-[#D0D7DE] pt-4 space-y-3 bg-slate-50 p-3 rounded">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Examination Type:</label>
                <select
                  value={formData.step3.examinationType}
                  onChange={(e) => setFormData(prev => ({ ...prev, step3: { ...prev.step3, examinationType: e.target.value } }))}
                  className="w-full px-2 py-1 border border-[#D0D7DE] rounded text-xs"
                >
                  <option value="documentary">Documentary Review</option>
                  <option value="physical">Physical Examination</option>
                  <option value="hybrid">Hybrid (Documentary + Physical)</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Hold Duration (days):</label>
                <input
                  type="number"
                  min="1"
                  max="90"
                  value={formData.step3.holdDurationDays}
                  onChange={(e) => setFormData(prev => ({ ...prev, step3: { ...prev.step3, holdDurationDays: parseInt(e.target.value) } }))}
                  className="w-full px-2 py-1 border border-[#D0D7DE] rounded text-xs"
                />
              </div>
            </div>
          )}

          <div className="border-t border-[#D0D7DE] pt-4 space-y-2">
            <label className="block text-xs font-semibold text-slate-700">Reasoning:</label>
            <textarea
              value={formData.step3.reasoning}
              onChange={(e) => setFormData(prev => ({ ...prev, step3: { ...prev.step3, reasoning: e.target.value } }))}
              className="w-full px-2 py-2 border border-[#D0D7DE] rounded text-xs font-mono"
              rows={3}
              placeholder="Justify your enforcement action recommendation..."
            />
          </div>
        </div>
      )}

      {/* Step 4: Signature & Certification */}
      {currentStep === 4 && (
        <div className="bg-white rounded-sm border border-[#D0D7DE] p-5 space-y-4">
          <h3 className="text-sm font-bold text-[#0B1F33]">Step 4: Officer Certification & Sign-Off</h3>

          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Officer Name:</label>
                <input
                  type="text"
                  value={formData.step4.officerName}
                  onChange={(e) => setFormData(prev => ({ ...prev, step4: { ...prev.step4, officerName: e.target.value } }))}
                  className="w-full px-2 py-1 border border-[#D0D7DE] rounded text-xs"
                  placeholder="Full name"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Badge Number:</label>
                <input
                  type="text"
                  value={formData.step4.badgeNumber}
                  onChange={(e) => setFormData(prev => ({ ...prev, step4: { ...prev.step4, badgeNumber: e.target.value } }))}
                  className="w-full px-2 py-1 border border-[#D0D7DE] rounded text-xs"
                  placeholder="Badge #"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Case Narrative (for record):</label>
              <textarea
                value={formData.step4.caseNarrative}
                onChange={(e) => setFormData(prev => ({ ...prev, step4: { ...prev.step4, caseNarrative: e.target.value } }))}
                className="w-full px-2 py-2 border border-[#D0D7DE] rounded text-xs font-mono"
                rows={4}
                placeholder="Summary of analysis and decision for official record..."
              />
            </div>

            <label className="flex items-start gap-2 p-3 bg-slate-50 rounded cursor-pointer">
              <input
                type="checkbox"
                checked={formData.step4.certificationAccepted}
                onChange={(e) => setFormData(prev => ({ ...prev, step4: { ...prev.step4, certificationAccepted: e.target.checked } }))}
                className="w-4 h-4 mt-0.5"
              />
              <span className="text-xs text-slate-700">
                I certify that I have reviewed all evidence and risk factors, and my analysis is complete and accurate.
              </span>
            </label>

            {formData.step4.certificationAccepted && (
              <div className="border-l-4 border-green-500 bg-green-50 p-3 rounded">
                <p className="text-xs text-green-800">
                  <span className="font-semibold">✓ Ready to Submit</span>
                </p>
                <p className="text-xs text-green-700 mt-1">
                  Submission time: {new Date().toLocaleString()}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Navigation Footer */}
      <div className="bg-white rounded-sm border border-[#D0D7DE] p-5 flex justify-between items-center">
        <div className="flex gap-2">
          {currentStep > 1 && (
            <button
              onClick={handlePrevStep}
              className="flex items-center gap-2 px-3 py-2 border border-[#005EA2] text-[#005EA2] rounded text-xs font-bold hover:bg-slate-50 transition"
            >
              <ChevronLeft size={16} />
              Back
            </button>
          )}
          {currentStep === 1 && onCancel && (
            <button
              onClick={onCancel}
              className="px-3 py-2 border border-slate-300 text-slate-700 rounded text-xs font-bold hover:bg-slate-50 transition"
            >
              Cancel
            </button>
          )}
        </div>

        <div className="flex gap-2">
          {currentStep < 4 && (
            <button
              onClick={handleNextStep}
              className="flex items-center gap-2 px-4 py-2 bg-[#005EA2] text-white rounded text-xs font-bold hover:bg-[#0044CC] transition"
            >
              Next
              <ChevronRight size={16} />
            </button>
          )}

          {currentStep === 4 && (
            <button
              onClick={handleSubmit}
              disabled={!formData.step4.certificationAccepted || submitting}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded text-xs font-bold hover:bg-green-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Save size={16} />
              {submitting ? 'Submitting...' : 'Submit Analysis'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
