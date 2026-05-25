// Unified Design System for consistent styling across all pages
// All pages should import and use these constants for colors, typography, spacing, and components

export const COLORS = {
  // Primary
  primary: '#005EA2',
  primaryHover: '#0076D6',
  primaryLight: '#0B1F33',

  // Status Colors
  critical: '#D83933',
  warning: '#FFBE2E',
  success: '#07A41E',
  info: '#005EA2',

  // Neutral
  white: '#ffffff',
  lightGray: '#F7F9FC',
  borderGray: '#D0D7DE',
  textDark: '#0B1F33',
  textMedium: '#5C5C5C',
  textLight: '#A8AFB8',

  // States
  disabled: '#C6CAD0',
  error: '#D83933',
};

export const TYPOGRAPHY = {
  // Font families
  fontFamily: 'font-sans',
  fontMono: 'font-mono',

  // Headings
  h1: 'text-2xl font-bold text-[#0B1F33]',
  h2: 'text-xl font-bold text-[#0B1F33]',
  h3: 'text-lg font-bold text-[#0B1F33]',
  sectionTitle: 'text-sm font-bold text-[#0B1F33]',

  // Body text
  body: 'text-xs text-[#0B1F33]',
  bodySmall: 'text-[9px] text-[#5C5C5C]',
  label: 'text-[9px] font-bold text-[#5C5C5C] uppercase',
  tiny: 'text-[8px] text-[#5C5C5C]',

  // Emphasis
  bold: 'font-bold',
  semibold: 'font-semibold',
  mono: 'font-mono text-[10px]',
};

export const SPACING = {
  // Padding
  p2: 'p-2',
  p3: 'p-3',
  p4: 'p-4',
  p6: 'p-6',

  // Margin
  m2: 'm-2',
  m3: 'm-3',
  m4: 'm-4',
  mb2: 'mb-2',
  mb3: 'mb-3',
  mb4: 'mb-4',
  mt2: 'mt-2',
  mt3: 'mt-3',
  mt4: 'mt-4',

  // Gap
  gap2: 'gap-2',
  gap3: 'gap-3',
  gap4: 'gap-4',
  gap6: 'gap-6',
};

export const BORDERS = {
  thin: 'border border-[#D0D7DE]',
  thick: 'border-2 border-[#D0D7DE]',
  bottom: 'border-b border-[#D0D7DE]',
  right: 'border-r border-[#D0D7DE]',
  none: 'border-0',
};

export const SHADOWS = {
  sm: 'shadow-sm',
  md: 'shadow-md',
  lg: 'shadow-lg',
  none: 'shadow-none',
};

// Component Styles
export const COMPONENTS = {
  // Buttons
  button: {
    primary: 'px-6 py-2 bg-[#005EA2] hover:bg-[#0076D6] text-white text-[10px] font-bold rounded-sm transition-colors',
    secondary: 'px-4 py-2 bg-slate-300 hover:bg-slate-400 text-slate-800 text-[10px] font-bold rounded-sm transition-colors',
    danger: 'px-6 py-2 bg-[#D83933] hover:bg-[#C72E2A] text-white text-[10px] font-bold rounded-sm transition-colors',
    success: 'px-6 py-2 bg-[#07A41E] hover:bg-[#06843E] text-white text-[10px] font-bold rounded-sm transition-colors',
    disabled: 'px-6 py-2 bg-[#C6CAD0] text-white text-[10px] font-bold rounded-sm cursor-not-allowed opacity-50',
  },

  // Cards
  card: 'bg-white rounded-sm border border-[#D0D7DE] p-4 shadow-sm',
  cardLarge: 'bg-white rounded-sm border border-[#D0D7DE] p-6 shadow-sm',
  cardAccent: 'bg-[#F7F9FC] rounded-sm border border-[#D0D7DE] p-4',

  // Alerts/Badges
  badge: {
    error: 'bg-red-100 text-red-800 text-[9px] font-bold px-2 py-1 rounded',
    warning: 'bg-amber-100 text-amber-800 text-[9px] font-bold px-2 py-1 rounded',
    success: 'bg-green-100 text-green-800 text-[9px] font-bold px-2 py-1 rounded',
    info: 'bg-blue-100 text-blue-800 text-[9px] font-bold px-2 py-1 rounded',
  },

  // Forms
  input: 'w-full px-3 py-2 border border-[#D0D7DE] rounded-sm text-[10px] focus:border-[#005EA2] focus:outline-none focus:ring-1 focus:ring-[#005EA2]',
  textarea: 'w-full font-mono text-[10px] p-3 rounded-sm border border-[#D0D7DE] focus:border-[#005EA2] focus:outline-none',

  // Tables
  tableHeader: 'bg-[#005EA2] text-white text-[10px] font-bold',
  tableRow: 'border-b border-[#D0D7DE] text-[9px]',
  tableRowAlt: 'bg-slate-50',
};

// Layout Constants
export const LAYOUT = {
  sidebarWidth: 'w-48',
  sidebarCollapsedWidth: 'w-16',
  headerHeight: 'h-16',
  contentMaxWidth: 'max-w-4xl',
};

// Responsive Breakpoints
export const BREAKPOINTS = {
  sm: 'sm',   // 640px
  md: 'md',   // 768px
  lg: 'lg',   // 1024px
  xl: 'xl',   // 1280px
  '2xl': '2xl', // 1536px
};

// Status/Risk Indicators
export const STATUS_COLORS = {
  critical: {
    bg: 'bg-[#D83933]',
    text: 'text-white',
    badge: 'bg-red-100 text-red-800',
  },
  high: {
    bg: 'bg-[#FFBE2E]',
    text: 'text-slate-900',
    badge: 'bg-amber-100 text-amber-800',
  },
  medium: {
    bg: 'bg-yellow-100',
    text: 'text-yellow-900',
    badge: 'bg-yellow-100 text-yellow-800',
  },
  low: {
    bg: 'bg-green-100',
    text: 'text-green-900',
    badge: 'bg-green-100 text-green-800',
  },
  neutral: {
    bg: 'bg-slate-100',
    text: 'text-slate-900',
    badge: 'bg-slate-100 text-slate-800',
  },
};

// Common Patterns
export const PATTERNS = {
  // Summary Card - high-level details
  summaryCard: `bg-white border-b border-[#D0D7DE] px-6 py-4 shadow-sm`,

  // Progress Bar
  progressBar: `bg-white border-b border-[#D0D7DE] px-6 py-3`,

  // Content Pane
  contentPane: `flex-1 overflow-y-auto p-6 bg-[#F7F9FC]`,

  // Action Bar (bottom buttons)
  actionBar: `bg-white border-t border-[#D0D7DE] px-6 py-4`,
};

// Export helper function for status color
export const getStatusColor = (status: 'critical' | 'high' | 'medium' | 'low' | 'neutral') => {
  return STATUS_COLORS[status] || STATUS_COLORS.neutral;
};
