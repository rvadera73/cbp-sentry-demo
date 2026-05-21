import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { ReferralScorePipelineProps, PipelineScore } from './ReferralPackage.types';
import './ReferralScorePipeline.css';

/**
 * PipelineBlock: Single H1/H2/H3 risk score component
 *
 * Displays:
 * - Score: "28/40"
 * - Label: "Macro Volume Anomaly (+240% YoY Spike)"
 * - Expandable tooltip with algorithmic weights
 * - Keyboard accessible with focus-visible outline
 */
interface PipelineBlockProps {
  title: string;
  score: PipelineScore;
  index: number;
}

function PipelineBlock({ title, score, index }: PipelineBlockProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const scorePercentage = Math.round((score.score / score.maxScore) * 100);

  const handleToggle = () => {
    setIsExpanded(!isExpanded);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleToggle();
    }
  };

  return (
    <div className="pipeline-block">
      {/* Block Header */}
      <div
        className="pipeline-block__header"
        role="button"
        tabIndex={0}
        aria-expanded={isExpanded}
        aria-controls={`weights-${index}`}
        onClick={handleToggle}
        onKeyDown={handleKeyDown}
      >
        <div className="pipeline-block__content">
          <h3 className="pipeline-block__title">{title}</h3>
          <p className="pipeline-block__label">{score.label}</p>
        </div>

        {/* Score Badge */}
        <div className="pipeline-block__score">
          <div className="score-badge">
            <span className="score-badge__value">{Math.round(score.score)}</span>
            <span className="score-badge__max">/{score.maxScore}</span>
          </div>
          <div className="score-percentage" aria-label={`${scorePercentage} percent`}>
            <div className="percentage-bar" style={{ width: `${scorePercentage}%` }} />
          </div>
        </div>

        {/* Expand Icon */}
        {score.algorithmicWeights && Object.keys(score.algorithmicWeights).length > 0 && (
          <ChevronDown
            size={20}
            className={`pipeline-block__chevron ${isExpanded ? 'expanded' : ''}`}
            aria-hidden="true"
          />
        )}
      </div>

      {/* Expandable Weights Tooltip */}
      {isExpanded && score.algorithmicWeights && Object.keys(score.algorithmicWeights).length > 0 && (
        <div
          id={`weights-${index}`}
          className="pipeline-block__weights"
          role="region"
          aria-label={`Algorithmic weights for ${title}`}
        >
          <div className="weights-container">
            {Object.entries(score.algorithmicWeights).map(([key, weight]) => (
              <div key={key} className="weight-item">
                <span className="weight-label">{key}</span>
                <div className="weight-bar-container">
                  <div
                    className="weight-bar"
                    style={{ width: `${(weight as number / 100) * 100}%` }}
                  />
                </div>
                <span className="weight-value">{(weight as number).toFixed(1)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * ReferralScorePipeline
 * Progressive pipeline of 3 sequential risk components (H1, H2, H3)
 *
 * Displays:
 * - H1: Corridor Risk
 * - H2: Vessel Risk
 * - H3: Network Intelligence
 *
 * Features:
 * - Keyboard accessible tabs with focus-visible outline
 * - Expandable tooltips with algorithmic weights
 * - Responsive flow layout
 *
 * Accessibility:
 * - tabindex="0" for keyboard navigation
 * - :focus-visible with blue outline
 * - aria-expanded for expandable sections
 */
export default function ReferralScorePipeline({
  h1_score,
  h2_score,
  h3_score,
}: ReferralScorePipelineProps) {
  return (
    <div className="referral-score-pipeline">
      <h2 className="pipeline-title">Risk Pipeline Analysis</h2>

      <div className="pipeline-blocks">
        <PipelineBlock title="H1: Corridor Risk" score={h1_score} index={0} />

        {/* Arrow Connector */}
        <div className="pipeline-arrow" aria-hidden="true">
          <span>→</span>
        </div>

        <PipelineBlock title="H2: Vessel Risk" score={h2_score} index={1} />

        {/* Arrow Connector */}
        <div className="pipeline-arrow" aria-hidden="true">
          <span>→</span>
        </div>

        <PipelineBlock title="H3: Network Intelligence" score={h3_score} index={2} />
      </div>
    </div>
  );
}
