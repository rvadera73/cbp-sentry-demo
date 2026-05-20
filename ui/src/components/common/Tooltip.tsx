import { useState, ReactNode } from 'react';
import { HelpCircle } from 'lucide-react';
import './Tooltip.css';

interface TooltipProps {
  children: ReactNode;
  title: string;
  definition: string;
  example?: string;
}

export default function Tooltip({ children, title, definition, example }: TooltipProps) {
  const [isVisible, setIsVisible] = useState(false);

  return (
    <div className="tooltip-wrapper">
      <span
        className="tooltip-trigger"
        onMouseEnter={() => setIsVisible(true)}
        onMouseLeave={() => setIsVisible(false)}
        onFocus={() => setIsVisible(true)}
        onBlur={() => setIsVisible(false)}
        tabIndex={0}
        role="button"
      >
        {children}
        <HelpCircle size={16} className="tooltip-icon" aria-label="More information" />
      </span>

      {isVisible && (
        <div className="tooltip-content" role="tooltip">
          <div className="tooltip-title">{title}</div>
          <div className="tooltip-definition">{definition}</div>
          {example && (
            <div className="tooltip-example">
              <strong>Example:</strong> {example}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
