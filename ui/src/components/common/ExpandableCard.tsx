import { useState } from 'react';
import { ChevronDown } from 'lucide-react';

interface ExpandableCardProps {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
  className?: string;
  headerAction?: React.ReactNode;
  badge?: string;
  badgeColor?: 'red' | 'amber' | 'green' | 'blue' | 'gray';
}

export default function ExpandableCard({
  title,
  defaultOpen = false,
  children,
  className = '',
  headerAction,
  badge,
  badgeColor = 'gray'
}: ExpandableCardProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  const badgeColorMap = {
    red: 'bg-red-100 text-red-900',
    amber: 'bg-amber-100 text-amber-900',
    green: 'bg-green-100 text-green-900',
    blue: 'bg-blue-100 text-blue-900',
    gray: 'bg-gray-100 text-gray-900'
  };

  return (
    <div className={`border border-gray-200 rounded-lg overflow-hidden ${className}`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <h3 className="font-semibold text-gray-900">{title}</h3>
          {badge && (
            <span className={`text-xs font-semibold px-2 py-1 rounded ${badgeColorMap[badgeColor]}`}>
              {badge}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {headerAction && <div className="mr-2">{headerAction}</div>}
          <ChevronDown
            size={18}
            className={`text-gray-600 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          />
        </div>
      </button>
      {isOpen && (
        <div className="px-4 py-3 border-t border-gray-200 bg-gray-50">
          {children}
        </div>
      )}
    </div>
  );
}
