/**
 * Officer Analysis Form - Tab 2
 * 4-step guided form: Risk Assessment → Evidence → Action → Signature
 */

import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { OfficerAnalysisFormProps } from './types/ReferralGeneration.types';
import { useOfficerAnalysisForm } from './hooks/useOfficerAnalysisForm';
import Step1RiskAssessment from './steps/Step1RiskAssessment';
import Step2EvidenceReview from './steps/Step2EvidenceReview';
import Step3ActionRecommendation from './steps/Step3ActionRecommendation';
import Step4OfficeSignature from './steps/Step4OfficeSignature';
import './OfficerAnalysisForm.css';

export default function OfficerAnalysisForm({
  referralId,
  referralData,
  initialData,
  onSubmit,
  onCancel
}: OfficerAnalysisFormProps) {
  const {
    formData,
    currentStep,
    updateStep1,
    updateStep2,
    updateStep3,
    updateStep4,
    nextStep,
    prevStep,
    submitForm,
    submitting
  } = useOfficerAnalysisForm(referralId);

  const handleNext = () => {
    if (nextStep()) {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const handlePrev = () => {
    prevStep();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSubmit = async () => {
    try {
      await submitForm();
      await onSubmit(formData);
    } catch (err) {
      console.error('Form submission error:', err);
    }
  };

  const progressPercent = (currentStep / 4) * 100;

  return (
    <div className="officer-analysis-form">
      {/* Progress Bar */}
      <div className="form-progress">
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${progressPercent}%` }} />
        </div>
        <div className="progress-label">
          <span>Step {currentStep} of 4</span>
          <span className="progress-text">
            {currentStep === 1 && 'Risk Assessment Confirmation'}
            {currentStep === 2 && 'Evidence Review Checklist'}
            {currentStep === 3 && 'Action Recommendation'}
            {currentStep === 4 && 'Officer Signature'}
          </span>
        </div>
      </div>

      {/* Step Container */}
      <div className="step-container">
        {currentStep === 1 && (
          <Step1RiskAssessment
            data={formData.step1}
            currentRiskScore={referralData.risk_score}
            onChange={updateStep1}
            onNext={() => nextStep()}
          />
        )}

        {currentStep === 2 && (
          <Step2EvidenceReview
            data={formData.step2}
            onChange={updateStep2}
            onNext={() => nextStep()}
          />
        )}

        {currentStep === 3 && (
          <Step3ActionRecommendation
            data={formData.step3}
            onChange={updateStep3}
            onNext={() => nextStep()}
          />
        )}

        {currentStep === 4 && (
          <Step4OfficeSignature
            data={formData.step4}
            onChange={updateStep4}
            onSubmit={() => true}
            isSubmitting={submitting}
          />
        )}
      </div>

      {/* Form Footer */}
      <div className="form-footer">
        <div className="button-group-left">
          {currentStep > 1 && (
            <button
              className="btn btn-secondary"
              onClick={handlePrev}
              disabled={submitting}
            >
              <ChevronLeft size={18} />
              Back
            </button>
          )}
          {onCancel && currentStep === 1 && (
            <button
              className="btn btn-secondary"
              onClick={onCancel}
              disabled={submitting}
            >
              Cancel
            </button>
          )}
        </div>

        <div className="button-group-right">
          {currentStep < 4 && (
            <button
              className="btn btn-primary"
              onClick={handleNext}
              disabled={submitting}
            >
              Next
              <ChevronRight size={18} />
            </button>
          )}

          {currentStep === 4 && (
            <button
              className="btn btn-primary"
              onClick={handleSubmit}
              disabled={submitting}
            >
              {submitting ? 'Submitting...' : 'Submit Analysis'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
