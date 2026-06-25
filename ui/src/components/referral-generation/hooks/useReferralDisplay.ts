/**
 * Hook: Manage Referral Display Data & Operations
 * Handles fetching, caching, narrative editing, and PDF export
 */

import { useState, useEffect, useCallback } from 'react';
import { ReferralDisplayData } from '../types/ReferralGeneration.types';
import { API_BASE_URL } from '../../../services/apiUrl';

interface UseReferralDisplayReturn {
  referral: ReferralDisplayData | null;
  loading: boolean;
  error: Error | null;
  generateReferral: () => Promise<void>;
  updateNarrative: (sectionId: string, content: string) => Promise<void>;
  exportPDF: () => Promise<void>;
}

export function useReferralDisplay(shipmentId: string): UseReferralDisplayReturn {
  const [referral, setReferral] = useState<ReferralDisplayData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const generateReferral = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      // Call the analyze endpoint to get Gemini-enriched analysis
      const response = await fetch(`${API_BASE_URL}/referral/${shipmentId}/analyze`);

      if (!response.ok) {
        throw new Error(`Failed to generate referral: ${response.statusText}`);
      }

      const data = await response.json();
      // Map API response to expected type (API uses risk_tier, code expects risk_level)
      const mappedData: ReferralDisplayData = {
        ...data,
        risk_level: (data.risk_tier || 'MEDIUM') as 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL',
        edited_sections: {}
      };
      setReferral(mappedData);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error');
      setError(error);
      console.error('Referral generation failed:', error);
    } finally {
      setLoading(false);
    }
  }, [shipmentId]);

  const updateNarrative = useCallback(async (sectionId: string, content: string) => {
    if (!referral) return;

    try {
      // Update local state optimistically
      setReferral(prev => prev ? {
        ...prev,
        edited_sections: {
          ...prev.edited_sections,
          [sectionId]: {
            original_content: prev.sections[sectionId]?.['pattern_narrative'] ||
                            prev.sections[sectionId]?.['trade_flow_narrative'] ||
                            prev.sections[sectionId]?.['summary'] ||
                            prev.sections[sectionId]?.['conclusion_narrative'] || '',
            edited_content: content,
            edited_at: new Date().toISOString(),
            edited_by: 'Officer',
            regeneration_count: (prev.edited_sections?.[sectionId]?.regeneration_count || 0) + 1
          }
        }
      } : null);

      // Persist to backend (future enhancement)
      // await fetch(`${API_BASE_URL}/api/referrals/${referral.referral_id}/sections/${sectionId}`, {
      //   method: 'PATCH',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({ content })
      // });
    } catch (err) {
      console.error('Failed to update narrative:', err);
      throw err;
    }
  }, [referral]);

  const exportPDF = useCallback(async () => {
    if (!referral) return;

    try {
      // Get the referral content container
      const element = document.querySelector('.referral-display-panel__content');
      if (!element) {
        throw new Error('Referral content not found for export');
      }

      // Dynamic import to avoid bundle bloat
      const html2canvas = (await import('html2canvas')).default;
      const { jsPDF } = await import('jspdf');

      const canvas = await html2canvas(element as HTMLElement, {
        scale: 2,
        backgroundColor: '#ffffff'
      });

      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'mm',
        format: 'a4'
      });

      const imgData = canvas.toDataURL('image/png');
      const imgWidth = 210;
      const pageHeight = 295;
      const imgHeight = (canvas.height * imgWidth) / canvas.width;
      let heightLeft = imgHeight;
      let position = 0;

      pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
      heightLeft -= pageHeight;

      while (heightLeft > 0) {
        position = heightLeft - imgHeight;
        pdf.addPage();
        pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
        heightLeft -= pageHeight;
      }

      const fileName = `Referral-${referral.referral_id}-${new Date().toISOString().split('T')[0]}.pdf`;
      pdf.save(fileName);
    } catch (err) {
      console.error('PDF export failed:', err);
      throw err;
    }
  }, [referral]);

  // Fetch referral on mount
  useEffect(() => {
    generateReferral();
  }, [generateReferral]);

  return {
    referral,
    loading,
    error,
    generateReferral,
    updateNarrative,
    exportPDF
  };
}
