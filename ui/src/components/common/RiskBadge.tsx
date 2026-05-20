interface RiskBadgeProps {
  score: number;
  label?: string;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

export default function RiskBadge({
  score,
  label,
  size = 'md',
  showLabel = true
}: RiskBadgeProps) {
  const getRiskColor = (s: number) => {
    if (s >= 70) return { bg: 'bg-red-600', text: 'text-white', label: 'HIGH' };
    if (s >= 50) return { bg: 'bg-amber-500', text: 'text-white', label: 'MEDIUM' };
    return { bg: 'bg-green-600', text: 'text-white', label: 'LOW' };
  };

  const risk = getRiskColor(score);

  const sizeMap = {
    sm: 'px-2 py-1 text-xs',
    md: 'px-3 py-2 text-sm',
    lg: 'px-4 py-3 text-base'
  };

  return (
    <div className={`${risk.bg} ${risk.text} rounded font-bold ${sizeMap[size]} inline-flex items-center gap-2`}>
      <span>{Math.round(score)}</span>
      {showLabel && <span className="text-xs uppercase">{label || risk.label}</span>}
    </div>
  );
}
