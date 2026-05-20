import { ChevronDown, ChevronUp } from 'lucide-react';
import '../../styles/CollapsibleSection.css';

interface CollapsibleSectionProps {
  title: string;
  children: React.ReactNode;
  expanded: boolean;
  onToggle: () => void;
}

export default function CollapsibleSection({
  title,
  children,
  expanded,
  onToggle,
}: CollapsibleSectionProps) {
  return (
    <div className={`collapsible-section ${expanded ? 'expanded' : 'collapsed'}`}>
      <button
        className="section-header"
        onClick={onToggle}
        aria-expanded={expanded}
      >
        <span className="section-title">{title}</span>
        <span className="section-icon">
          {expanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
        </span>
      </button>
      {expanded && <div className="section-content">{children}</div>}
    </div>
  );
}
