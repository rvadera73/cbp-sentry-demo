export function getRiskLevel(score: number): 'Critical' | 'High' | 'Medium' | 'Low' {
  if (score >= 80) return 'Critical';
  if (score >= 60) return 'High';
  if (score >= 40) return 'Medium';
  return 'Low';
}

export function getRiskBackgroundColor(score: number): string {
  const level = getRiskLevel(score);
  switch (level) {
    case 'Critical':
      return '#DC2626';
    case 'High':
      return '#F59E0B';
    case 'Medium':
      return '#FBBF24';
    case 'Low':
      return '#10B981';
  }
}

export function getRiskBorderColor(score: number): string {
  const level = getRiskLevel(score);
  switch (level) {
    case 'Critical':
      return '#7F1D1D';
    case 'High':
      return '#92400E';
    case 'Medium':
      return '#9A6400';
    case 'Low':
      return '#065F46';
  }
}
