interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  badge?: string;
  badgeColor?: 'red' | 'amber' | 'green' | 'blue' | 'gray';
  action?: React.ReactNode;
}

export default function SectionHeader({
  title,
  subtitle,
  badge,
  badgeColor = 'blue',
  action
}: SectionHeaderProps) {
  const badgeColorMap = {
    red: 'bg-red-100 text-red-900',
    amber: 'bg-amber-100 text-amber-900',
    green: 'bg-green-100 text-green-900',
    blue: 'bg-blue-100 text-blue-900',
    gray: 'bg-gray-100 text-gray-900'
  };

  return (
    <div className="flex items-start justify-between mb-4 pb-4 border-b border-gray-200">
      <div>
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-bold text-gray-900">{title}</h3>
          {badge && (
            <span className={`text-xs font-semibold px-2 py-1 rounded ${badgeColorMap[badgeColor]}`}>
              {badge}
            </span>
          )}
        </div>
        {subtitle && <p className="text-sm text-gray-600 mt-1">{subtitle}</p>}
      </div>
      {action && <div className="flex-shrink-0">{action}</div>}
    </div>
  );
}
