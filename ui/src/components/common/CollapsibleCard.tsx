import { ReactNode, useState } from 'react';
import { ChevronDown } from 'lucide-react';
import './CollapsibleCard.css';

interface CollapsibleCardProps {
  title: string;
  icon?: ReactNode;
  children: ReactNode;
  defaultOpen?: boolean;
  badge?: string;
  badgeColor?: 'red' | 'yellow' | 'green' | 'blue';
}

export default function CollapsibleCard({
  title,
  icon,
  children,
  defaultOpen = true,
  badge,
  badgeColor = 'blue',
}: CollapsibleCardProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="collapsible-card">
      <button
        className="collapsible-header"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
      >
        <div className="header-left">
          {icon && <div className="header-icon">{icon}</div>}
          <h3 className="header-title">{title}</h3>
          {badge && <span className={`badge badge-${badgeColor}`}>{badge}</span>}
        </div>
        <ChevronDown
          size={20}
          className={`chevron ${isOpen ? 'open' : ''}`}
          aria-hidden="true"
        />
      </button>

      {isOpen && <div className="collapsible-content">{children}</div>}
    </div>
  );
}
