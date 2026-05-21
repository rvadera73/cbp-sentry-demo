import React from 'react';
import CaseCard, { CaseCardData } from './CaseCard';
import './CaseListView.css';

interface CaseListViewProps {
  cases: CaseCardData[];
  onCaseSelect?: (caseId: string) => void;
  onCaseClick?: (caseId: string) => void;
  selectedCaseId?: string;
}

/**
 * CaseListView: Dense vertical list view
 *
 * Layout:
 * - High-density case cards stacked vertically
 * - High-risk (≥90) entries: thick crimson left border
 * - Scrollable independent of header/toolbar
 *
 * Accessibility:
 * - List role with aria-label
 * - Each card: listitem role
 * - Tab through cases, arrow keys for navigation
 */
export default function CaseListView({
  cases,
  onCaseSelect,
  onCaseClick,
  selectedCaseId,
}: CaseListViewProps) {
  return (
    <div className="case-list-view">
      <div
        className="case-list-container"
        role="list"
        aria-label={`Case list view with ${cases.length} cases`}
      >
        {cases.map((caseData) => (
          <div key={caseData.id} role="listitem">
            <CaseCard
              data={caseData}
              isSelected={selectedCaseId === caseData.id}
              onSelect={onCaseSelect}
              onClick={onCaseClick}
              variant="list"
              showArrow={true}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
