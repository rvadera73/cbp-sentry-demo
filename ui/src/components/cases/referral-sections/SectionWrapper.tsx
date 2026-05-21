import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import '../referral-sections.css';

interface SectionWrapperProps {
  sectionId: string;
  sectionNumber: string;
  title: string;
  icon: React.ReactNode;
  dataQuality: 'COMPLETE' | 'PARTIAL' | 'MINIMAL';
  anomalyCount?: number;
  children: React.ReactNode;
  defaultExpanded?: boolean;
}

export function SectionWrapper({
  sectionId,
  sectionNumber,
  title,
  icon,
  dataQuality,
  anomalyCount,
  children,
  defaultExpanded = false,
}: SectionWrapperProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  const dataQualityClass = dataQuality === 'COMPLETE'
    ? 'data-quality--complete'
    : dataQuality === 'PARTIAL'
      ? 'data-quality--partial'
      : 'data-quality--minimal';

  const dataQualityLabel = {
    COMPLETE: 'Complete',
    PARTIAL: 'Partial',
    MINIMAL: 'Minimal',
  }[dataQuality];

  return (
    <section
      id={sectionId}
      className={`referral-section ${isExpanded ? 'expanded' : 'collapsed'}`}
      aria-labelledby={`${sectionId}-title`}
    >
      <div
        className="referral-section__header"
        onClick={() => setIsExpanded(!isExpanded)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setIsExpanded(!isExpanded);
          }
        }}
        role="button"
        tabIndex={0}
        aria-expanded={isExpanded}
        aria-controls={`${sectionId}-content`}
      >
        <div className="referral-section__header-left">
          <div className="referral-section__icon">{icon}</div>
          <div className="referral-section__title-group">
            <h3 id={`${sectionId}-title`} className="referral-section__title">
              {sectionNumber}: {title}
            </h3>
          </div>
        </div>

        <div className="referral-section__header-right">
          {anomalyCount !== undefined && anomalyCount > 0 && (
            <span
              className="referral-section__anomaly-badge"
              aria-label={`${anomalyCount} anomalies detected`}
            >
              {anomalyCount}
            </span>
          )}

          <span className={`referral-section__data-quality ${dataQualityClass}`}>
            {dataQualityLabel}
          </span>

          <ChevronDown
            size={20}
            className="referral-section__expand-icon"
            aria-hidden="true"
          />
        </div>
      </div>

      <div
        id={`${sectionId}-content`}
        className="referral-section__content"
        role="region"
      >
        <div className="referral-section__body">{children}</div>
      </div>
    </section>
  );
}
