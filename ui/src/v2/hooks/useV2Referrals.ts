import { useState, useCallback } from 'react';
import { ReferralPackage, Case } from '../types/v2.types';
import { api } from '../../services/api';

interface UseV2ReferralsReturn {
  referrals: ReferralPackage[];
  getReferralForCase: (caseId: string) => ReferralPackage | undefined;
  createReferral: (caseId: string, sections: string[]) => Promise<ReferralPackage | null>;
  loading: Record<string, boolean>;
}

/**
 * Manages referral packages derived from cases
 */
export function useV2Referrals(cases: Case[]): UseV2ReferralsReturn {
  const [referrals, setReferrals] = useState<ReferralPackage[]>([]);
  const [loading, setLoading] = useState<Record<string, boolean>>({});

  const getReferralForCase = useCallback(
    (caseId: string) => {
      return referrals.find(r => r.case_id === caseId);
    },
    [referrals]
  );

  const createReferral = useCallback(
    async (caseId: string, sections: string[]): Promise<ReferralPackage | null> => {
      try {
        setLoading(prev => ({ ...prev, [caseId]: true }));

        const caseObj = cases.find(c => c.case_id === caseId);
        if (!caseObj) return null;

        // Call API to generate referral
        const result = await api.generateReferral();

        const newReferral: ReferralPackage = {
          referral_id: `REF-${Math.random().toString().slice(2, 6)}`,
          shipment_id: `SHP-${Math.random().toString().slice(2, 8)}`,
          created_at: new Date().toISOString(),
          risk_score: caseObj.risk_score || 0,
          risk_level: caseObj.risk_score >= 85 ? 'CRITICAL' : caseObj.risk_score >= 70 ? 'HIGH' : caseObj.risk_score >= 50 ? 'MEDIUM' : 'LOW',
          sections: {},
          case_id: caseId,
          package_status: 'Draft',
          generated_date: new Date().toISOString().split('T')[0],
          approval_state: 'Under Analyst Review',
          evidence_inventory_ids: [],
          narrative: {
            executive_summary: 'Investigation reveals systematic transshipment evasion...',
            subject_overview: `${caseObj.target_entity} operates as intermediary with shell characteristics...`,
            investigation_findings: 'Multiple shipping anomalies detected and correlated...',
            trade_pattern_analysis: 'Pattern analysis indicates circular invoicing scheme...',
            evidence_summary: 'Critical evidence includes manifest weight discrepancies...',
            applicable_violations: '19 U.S.C. § 1592 (false statements); 18 U.S.C. § 545 (smuggling)',
            recommended_enforcement: 'Recommend 250% penalty and criminal referral to DOJ',
          },
        };

        setReferrals(prev => {
          const existing = prev.findIndex(r => r.case_id === caseId);
          if (existing >= 0) {
            const updated = [...prev];
            updated[existing] = newReferral;
            return updated;
          }
          return [...prev, newReferral];
        });

        return newReferral;
      } catch (err) {
        console.error('Failed to create referral:', err);
        return null;
      } finally {
        setLoading(prev => ({ ...prev, [caseId]: false }));
      }
    },
    [cases]
  );

  return {
    referrals,
    getReferralForCase,
    createReferral,
    loading,
  };
}
