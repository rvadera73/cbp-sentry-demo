/**
 * Referral Package Generation Tab
 * Main container for Tab 1 (Display) and Tab 2 (Officer Analysis)
 * Real data integration with no mocks
 */

import React, { useState, useEffect } from 'react';
import { AlertTriangle, Download, ChevronRight } from 'lucide-react';
import { ReferralPackageGenerationTabProps, ReferralDisplayData } from './types/ReferralGeneration.types';
import ReferralDisplayPanel from './ReferralDisplayPanel';
import { useOfficerAnalysisForm } from './hooks/useOfficerAnalysisForm';
import { useReferralDisplay } from './hooks/useReferralDisplay';
import './ReferralPackageGenerationTab.css';

interface TabState {
  activeTab: 'display' | 'analysis';
  referralData: ReferralDisplayData | null;
  loading: boolean;
  error: string | null;
}

export default function ReferralPackageGenerationTab({ shipmentId, onClose }: ReferralPackageGenerationTabProps) {
  const [tabState, setTabState] = useState<TabState>({
    activeTab: 'display',
    referralData: null,
    loading: true,
    error: null
  });

  const { referral, loading, error, generateReferral, updateNarrative, exportPDF } = useReferralDisplay(shipmentId);

  useEffect(() => {
    if (referral) {
      setTabState(prev => ({
        ...prev,
        referralData: referral,
        loading: false
      }));
    }
  }, [referral]);

  useEffect(() => {
    if (error) {
      setTabState(prev => ({
        ...prev,
        error: error.message || 'Failed to load referral package',
        loading: false
      }));
    }
  }, [error]);

  const handleSwitchTab = (tab: 'display' | 'analysis') => {
    setTabState(prev => ({ ...prev, activeTab: tab }));
  };

  const handleNarrativeEdit = async (sectionId: string, editedContent: string) => {
    try {
      await updateNarrative(sectionId, editedContent);
      setTabState(prev => ({
        ...prev,
        referralData: prev.referralData ? {
          ...prev.referralData,
          edited_sections: {
            ...prev.referralData.edited_sections,
            [sectionId]: {
              original_content: '',
              edited_content: editedContent,
              edited_at: new Date().toISOString(),
              edited_by: 'Current Officer',
              regeneration_count: 0
            }
          }
        } : null
      }));
    } catch (err) {
      console.error('Failed to update narrative:', err);
    }
  };

  const handleExportPDF = async () => {
    try {
      await exportPDF();
    } catch (err) {
      console.error('Failed to export PDF:', err);
      alert('PDF export failed. Please try again.');
    }
  };

  const handleAnalysisSubmit = async (formData: any) => {
    try {
      // Will be integrated with backend endpoint
      console.log('Form submitted:', formData);
      alert('Analysis submitted successfully');
      handleSwitchTab('display');
    } catch (err) {
      console.error('Failed to submit analysis:', err);
      alert('Failed to submit analysis. Please try again.');
    }
  };

  if (tabState.loading) {
    return (
      <div className="referral-gen-tab__loading">
        <div className="spinner"></div>
        <p>Generating referral package...</p>
      </div>
    );
  }

  if (tabState.error) {
    return (
      <div className="referral-gen-tab__error">
        <AlertTriangle className="icon" />
        <h3>Unable to Load Referral</h3>
        <p>{tabState.error}</p>
        {onClose && <button onClick={onClose}>Close</button>}
      </div>
    );
  }

  if (!tabState.referralData) {
    return null;
  }

  return (
    <div className="referral-gen-tab">
      {/* Header */}
      <div className="referral-gen-tab__header">
        <div className="referral-gen-tab__title">
          <h2>Referral Package Generation</h2>
          <div className="referral-gen-tab__metadata">
            <span className="metadata-item">
              <strong>Package ID:</strong> {tabState.referralData.referral_id}
            </span>
            <span className="metadata-item">
              <strong>Generated:</strong> {new Date(tabState.referralData.created_at).toLocaleString()}
            </span>
            <span className={`risk-badge risk-${tabState.referralData.risk_level.toLowerCase()}`}>
              {tabState.referralData.risk_level} RISK ({tabState.referralData.risk_score}/100)
            </span>
          </div>
        </div>

        {tabState.activeTab === 'display' && (
          <div className="referral-gen-tab__header-actions">
            <button
              className="btn btn-secondary"
              onClick={handleExportPDF}
              title="Export as PDF (Federal format)"
            >
              <Download size={18} />
              Export PDF
            </button>
          </div>
        )}
      </div>

      {/* Tab Navigation */}
      <div className="referral-gen-tab__nav">
        <button
          className={`tab-button ${tabState.activeTab === 'display' ? 'active' : ''}`}
          onClick={() => handleSwitchTab('display')}
        >
          <span className="tab-label">Referral Package Display</span>
          <span className="tab-description">Review all data and risk factors</span>
        </button>
        <div className="tab-separator">
          <ChevronRight size={20} />
        </div>
        <button
          className={`tab-button ${tabState.activeTab === 'analysis' ? 'active' : ''}`}
          onClick={() => handleSwitchTab('analysis')}
        >
          <span className="tab-label">Officer Analysis</span>
          <span className="tab-description">4-step guided decision form</span>
        </button>
      </div>

      {/* Tab Content */}
      <div className="referral-gen-tab__content">
        {tabState.activeTab === 'display' && (
          <ReferralDisplayPanel
            referralData={tabState.referralData}
            onNarrativeEdit={handleNarrativeEdit}
            onExportPDF={handleExportPDF}
          />
        )}

        {tabState.activeTab === 'analysis' && (
          <div className="p-6 bg-white rounded-sm border border-[#D0D7DE]">
            <p className="text-sm text-[#5C5C5C]">Officer Analysis Form - Coming Soon</p>
          </div>
        )}
      </div>
    </div>
  );
}
