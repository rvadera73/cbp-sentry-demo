/**
 * CBP Design System - Reusable Styles & Components
 *
 * Based on ReferralPackageV2 styling
 * To be used across all tabs and pages in cbp-sentry
 *
 * Color System:
 * - Primary: #005EA2 (CBP Blue)
 * - Dark: #0B1F33 (Navy)
 * - Risk: CRITICAL (red) | HIGH (amber) | MEDIUM (yellow) | LOW (green)
 */

export const CBPColors = {
  primary: '#005EA2', // CBP Blue
  dark: '#0B1F33',    // Navy
  border: '#D0D7DE',  // Standard border

  // Risk tier colors (background, text, border)
  risk: {
    CRITICAL: {
      bg: '#FEE2E2',
      text: '#991B1B',
      border: '#FCA5A5',
      light: '#fee2e2',
    },
    HIGH: {
      bg: '#FEF3C7',
      text: '#92400E',
      border: '#FCD34D',
      light: '#fef3c7',
    },
    MEDIUM: {
      bg: '#FFF7ED',
      text: '#9A3412',
      border: '#FDBA74',
      light: '#fff7ed',
    },
    LOW: {
      bg: '#DCFCE7',
      text: '#166534',
      border: '#86EFAC',
      light: '#dcfce7',
    },
  },
};

export const CBPTypography = {
  // Page + content headers — aligned with the Investigation workspace
  pageTitle: 'text-xl font-bold text-[#0B1F33]',
  metricValue: 'text-2xl font-bold text-[#0B1F33]',

  // Section headers (with icon circles)
  sectionHeader: 'text-sm font-bold text-[#0B1F33]',
  sectionSubtitle: 'text-[11px] text-slate-500',

  // Table headers
  tableHeader: 'text-[11px] font-semibold uppercase tracking-wide',
  tableCaption: 'text-[10px] font-bold text-[#005EA2] uppercase tracking-wide',
  tableBody: 'text-[11px]',

  // General text — body/small use the Investigation muted gray (#5C5C5C)
  label: 'text-[11px] font-bold text-[#0B1F33]',
  body: 'text-[11px] text-[#5C5C5C]',
  small: 'text-[10px] text-[#5C5C5C]',
  bold: 'font-bold',
};

// Horizontal tab bar — matches the Active Investigation workspace tabs
export const CBPTabs = {
  bar: 'flex overflow-x-auto border-b border-[#D0D7DE] bg-slate-50 px-4',
  button: 'px-4 py-2 text-[11px] font-semibold border-b-2 transition-colors whitespace-nowrap flex items-center gap-2',
  active: 'border-[#005EA2] text-[#005EA2]',
  inactive: 'border-transparent text-slate-600 hover:text-[#0B1F33]',
};

export const CBPComponents = {
  // Section number circle
  sectionNumber: 'w-8 h-8 rounded-full bg-[#005EA2] text-white text-[11px] font-bold flex items-center justify-center flex-shrink-0',

  // Card with left border
  card: 'border-l-4 border-[#005EA2] bg-white rounded-sm p-4',
  cardAlt: 'border border-[#D0D7DE] bg-white rounded-sm p-3',

  // Button variants
  buttonPrimary: 'px-3 py-1.5 bg-[#005EA2] text-white text-xs font-semibold rounded hover:bg-blue-700 transition-colors',
  buttonSecondary: 'px-3 py-1.5 border border-[#D0D7DE] text-slate-700 text-xs font-semibold rounded hover:bg-slate-50 transition-colors',
  buttonDanger: 'px-3 py-1.5 border border-red-300 text-red-700 text-xs font-semibold rounded hover:bg-red-50 transition-colors',
  buttonSuccess: 'px-3 py-1.5 border border-green-300 text-green-700 text-xs font-semibold rounded hover:bg-green-50 transition-colors',

  // Status badges
  badgeCritical: 'inline-flex items-center px-2 py-1 rounded text-xs font-semibold bg-red-100 text-red-700',
  badgeHigh: 'inline-flex items-center px-2 py-1 rounded text-xs font-semibold bg-amber-100 text-amber-700',
  badgeMedium: 'inline-flex items-center px-2 py-1 rounded text-xs font-semibold bg-yellow-100 text-yellow-700',
  badgeLow: 'inline-flex items-center px-2 py-1 rounded text-xs font-semibold bg-green-100 text-green-700',
  badgeProduction: 'inline-flex items-center px-2 py-1 rounded text-xs font-semibold bg-green-100 text-green-700',
  badgeStaging: 'inline-flex items-center px-2 py-1 rounded text-xs font-semibold bg-yellow-100 text-yellow-700',
  badgeDeprecated: 'inline-flex items-center px-2 py-1 rounded text-xs font-semibold bg-red-100 text-red-700',
};

// Helper function to get risk color based on score
export function getRiskColor(score: number | null | undefined) {
  if (!score) return CBPColors.risk.LOW;
  if (score >= 80) return CBPColors.risk.CRITICAL;
  if (score >= 65) return CBPColors.risk.HIGH;
  if (score >= 50) return CBPColors.risk.MEDIUM;
  return CBPColors.risk.LOW;
}

// Helper function to get risk label
export function getRiskLabel(score: number | null | undefined): 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' {
  if (!score) return 'LOW';
  if (score >= 80) return 'CRITICAL';
  if (score >= 65) return 'HIGH';
  if (score >= 50) return 'MEDIUM';
  return 'LOW';
}

// Helper function to get risk badge class
export function getRiskBadgeClass(score: number | null | undefined): string {
  const label = getRiskLabel(score);
  const badges: Record<string, string> = {
    CRITICAL: CBPComponents.badgeCritical,
    HIGH: CBPComponents.badgeHigh,
    MEDIUM: CBPComponents.badgeMedium,
    LOW: CBPComponents.badgeLow,
  };
  return badges[label] || CBPComponents.badgeLow;
}

// Helper function to get status badge class
export function getStatusBadgeClass(status: string): string {
  const statuses: Record<string, string> = {
    PRODUCTION: CBPComponents.badgeProduction,
    STAGING: CBPComponents.badgeStaging,
    EXPERIMENTAL: CBPComponents.badgeStaging,
    DEPRECATED: CBPComponents.badgeDeprecated,
    REGISTERED: 'inline-flex items-center px-2 py-1 rounded text-xs font-semibold bg-slate-100 text-slate-700',
  };
  return statuses[status] || statuses.REGISTERED;
}
