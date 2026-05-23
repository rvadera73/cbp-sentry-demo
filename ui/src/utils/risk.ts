/**
 * Unified risk scoring utility — single source of truth
 * Risk thresholds: HIGH >= 70, MEDIUM 40-69, LOW < 40
 */

export type RiskLevel = 'HIGH' | 'MEDIUM' | 'LOW';

export interface RiskConfig {
  level: RiskLevel;
  backgroundColor: string;
  borderColor: string;
  textColor: string;
  label: string;
}

const RISK_CONFIG: Record<RiskLevel, RiskConfig> = {
  HIGH: {
    level: 'HIGH',
    backgroundColor: '#fdf0f0',
    borderColor: '#d9381e',
    textColor: '#6f0a0a',
    label: 'HIGH RISK',
  },
  MEDIUM: {
    level: 'MEDIUM',
    backgroundColor: '#fff8e6',
    borderColor: '#e6a100',
    textColor: '#7a4900',
    label: 'MEDIUM RISK',
  },
  LOW: {
    level: 'LOW',
    backgroundColor: '#ecf3ec',
    borderColor: '#2e8540',
    textColor: '#154c17',
    label: 'LOW RISK',
  },
};

/**
 * Get risk level from numerical score
 * HIGH: >= 70, MEDIUM: 40-69, LOW: < 40
 */
export const getRiskLevel = (score: number | null | undefined): RiskLevel => {
  if (score === null || score === undefined) return 'LOW';
  if (score >= 70) return 'HIGH';
  if (score >= 40) return 'MEDIUM';
  return 'LOW';
};

/**
 * Get CSS class name for risk level
 */
export const getRiskClassName = (score: number | null | undefined): string => {
  const level = getRiskLevel(score);
  return `risk-${level.toLowerCase()}`;
};

/**
 * Get full risk config (colors, label, etc)
 */
export const getRiskConfig = (score: number | null | undefined): RiskConfig => {
  const level = getRiskLevel(score);
  return RISK_CONFIG[level];
};

/**
 * Get border color for risk level
 */
export const getRiskBorderColor = (score: number | null | undefined): string => {
  return getRiskConfig(score).borderColor;
};

/**
 * Get background color for risk level
 */
export const getRiskBackgroundColor = (score: number | null | undefined): string => {
  return getRiskConfig(score).backgroundColor;
};

/**
 * Get text color for risk level
 */
export const getRiskTextColor = (score: number | null | undefined): string => {
  return getRiskConfig(score).textColor;
};

/**
 * Get label for risk level
 */
export const getRiskLabel = (score: number | null | undefined): string => {
  return getRiskConfig(score).label;
};
