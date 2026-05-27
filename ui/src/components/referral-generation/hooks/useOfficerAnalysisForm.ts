/**
 * Hook: Manage Officer Analysis Form State
 * Handles 4-step form state, validation, and persistence
 */

import { useState, useCallback } from 'react';
import {
  OfficerAnalysisFormData,
  Step1RiskAssessment,
  Step2EvidenceReview,
  Step3ActionRecommendation,
  Step4OfficeSignature,
  EVIDENCE_ITEMS
} from '../types/ReferralGeneration.types';
import { API_BASE_URL } from '../../../services/apiUrl';

interface UseOfficerAnalysisFormReturn {
  formData: OfficerAnalysisFormData;
  currentStep: number;
  updateStep1: (data: Step1RiskAssessment) => void;
  updateStep2: (data: Step2EvidenceReview) => void;
  updateStep3: (data: Step3ActionRecommendation) => void;
  updateStep4: (data: Step4OfficeSignature) => void;
  nextStep: () => boolean;
  prevStep: () => void;
  submitForm: () => Promise<void>;
  validateStep: (step: number) => boolean;
  saveProgress: () => Promise<void>;
  submitting: boolean;
}

export function useOfficerAnalysisForm(referralId: string): UseOfficerAnalysisFormReturn {
  const [formData, setFormData] = useState<OfficerAnalysisFormData>({
    referral_id: referralId,
    step1: {
      agreeWithScore: true,
      confidence: 'high',
      validationErrors: []
    },
    step2: {
      reviewedItems: EVIDENCE_ITEMS.reduce((acc, item) => ({
        ...acc,
        [item.id]: {
          reviewed: false,
          isCritical: item.isCritical
        }
      }), {} as Record<string, any>),
      allCriticalReviewed: false,
      validationErrors: []
    },
    step3: {
      action: 'execute_trled',
      referralType: 'EAPA',
      priority: 'high',
      holdingPeriodDays: 30,
      validationErrors: []
    },
    step4: {
      caseNarrative: '',
      certificationAccepted: false,
      officerId: 'OFFICER_ID',
      officerName: 'Officer Name',
      badgeNumber: '12345',
      district: 'District',
      validationErrors: []
    },
    current_step: 1,
    form_status: 'draft'
  });

  const [submitting, setSubmitting] = useState(false);

  const updateStep1 = useCallback((data: Step1RiskAssessment) => {
    setFormData(prev => ({
      ...prev,
      step1: {
        ...data,
        validationErrors: []
      }
    }));
  }, []);

  const updateStep2 = useCallback((data: Step2EvidenceReview) => {
    const criticalItems = EVIDENCE_ITEMS.filter(i => i.isCritical).map(i => i.id);
    const allCriticalReviewed = criticalItems.every(id => data.reviewedItems[id]?.reviewed);

    setFormData(prev => ({
      ...prev,
      step2: {
        ...data,
        allCriticalReviewed,
        validationErrors: []
      }
    }));
  }, []);

  const updateStep3 = useCallback((data: Step3ActionRecommendation) => {
    setFormData(prev => ({
      ...prev,
      step3: {
        ...data,
        validationErrors: []
      }
    }));
  }, []);

  const updateStep4 = useCallback((data: Step4OfficeSignature) => {
    setFormData(prev => ({
      ...prev,
      step4: {
        ...data,
        validationErrors: []
      }
    }));
  }, []);

  const validateStep = useCallback((step: number): boolean => {
    switch (step) {
      case 1: {
        const errors: string[] = [];
        if (!formData.step1.confidence) {
          errors.push('Confidence level is required');
        }
        if (formData.step1.agreeWithScore === false && !formData.step1.officerScore) {
          errors.push('Officer score is required when adjusting');
        }
        if (formData.step1.agreeWithScore === false && !formData.step1.adjustmentReason) {
          errors.push('Adjustment reason is required when changing score');
        }
        if (errors.length > 0) {
          setFormData(prev => ({
            ...prev,
            step1: { ...prev.step1, validationErrors: errors }
          }));
          return false;
        }
        return true;
      }

      case 2: {
        const errors: string[] = [];
        const criticalItems = EVIDENCE_ITEMS.filter(i => i.isCritical).map(i => i.id);
        const unreviewed = criticalItems.filter(id => !formData.step2.reviewedItems[id]?.reviewed);
        if (unreviewed.length > 0) {
          errors.push(`All critical evidence items must be reviewed: ${unreviewed.join(', ')}`);
        }
        if (errors.length > 0) {
          setFormData(prev => ({
            ...prev,
            step2: { ...prev.step2, validationErrors: errors }
          }));
          return false;
        }
        return true;
      }

      case 3: {
        const errors: string[] = [];
        if (!formData.step3.action) {
          errors.push('Action selection is required');
        }
        // Validate conditional fields based on action
        if (formData.step3.action === 'execute_trled' && !formData.step3.referralType) {
          errors.push('Referral type is required for TRLED execution');
        }
        if (errors.length > 0) {
          setFormData(prev => ({
            ...prev,
            step3: { ...prev.step3, validationErrors: errors }
          }));
          return false;
        }
        return true;
      }

      case 4: {
        const errors: string[] = [];
        if (!formData.step4.caseNarrative || formData.step4.caseNarrative.length < 50) {
          errors.push('Case narrative must be at least 50 characters');
        }
        if (!formData.step4.certificationAccepted) {
          errors.push('You must accept the certification statement');
        }
        if (errors.length > 0) {
          setFormData(prev => ({
            ...prev,
            step4: { ...prev.step4, validationErrors: errors }
          }));
          return false;
        }
        return true;
      }

      default:
        return false;
    }
  }, [formData]);

  const nextStep = useCallback((): boolean => {
    if (!validateStep(formData.current_step)) {
      return false;
    }
    setFormData(prev => ({
      ...prev,
      current_step: Math.min(prev.current_step + 1, 4)
    }));
    return true;
  }, [formData.current_step, validateStep]);

  const prevStep = useCallback(() => {
    setFormData(prev => ({
      ...prev,
      current_step: Math.max(prev.current_step - 1, 1)
    }));
  }, []);

  const saveProgress = useCallback(async () => {
    try {
      // LocalStorage backup
      localStorage.setItem(`form_${referralId}`, JSON.stringify(formData));

      // Backend sync (future enhancement)
      // await fetch(`${API_BASE_URL}/api/officer-analysis/${referralId}`, {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(formData)
      // });
    } catch (err) {
      console.error('Failed to save progress:', err);
    }
  }, [referralId, formData]);

  const submitForm = useCallback(async () => {
    try {
      setSubmitting(true);

      // Validate final step
      if (!validateStep(4)) {
        setSubmitting(false);
        return;
      }

      const submitData = {
        ...formData,
        form_status: 'submitted',
        submitted_at: new Date().toISOString()
      };

      const response = await fetch(`${API_BASE_URL}/api/officer-analysis`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(submitData)
      });

      if (!response.ok) {
        throw new Error('Failed to submit analysis');
      }

      const result = await response.json();
      setFormData(prev => ({
        ...prev,
        analysis_id: result.analysis_id,
        form_status: 'submitted'
      }));

      // Clear localStorage
      localStorage.removeItem(`form_${referralId}`);
    } catch (err) {
      console.error('Form submission failed:', err);
      throw err;
    } finally {
      setSubmitting(false);
    }
  }, [formData, referralId, validateStep]);

  return {
    formData,
    currentStep: formData.current_step,
    updateStep1,
    updateStep2,
    updateStep3,
    updateStep4,
    nextStep,
    prevStep,
    submitForm,
    validateStep,
    saveProgress,
    submitting
  };
}
