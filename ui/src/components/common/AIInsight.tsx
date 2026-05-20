import { ReactNode } from 'react';
import { AlertCircle, TrendingUp, CheckCircle, AlertTriangle } from 'lucide-react';
import './AIInsight.css';

interface AIInsightProps {
  type: 'critical' | 'warning' | 'success' | 'info';
  title: string;
  message: string | ReactNode;
  detail?: string;
  confidence?: number;
  evidence?: string[];
}

const ICON_MAP = {
  critical: <AlertCircle size={20} />,
  warning: <AlertTriangle size={20} />,
  success: <CheckCircle size={20} />,
  info: <TrendingUp size={20} />,
};

export default function AIInsight({
  type,
  title,
  message,
  detail,
  confidence,
  evidence,
}: AIInsightProps) {
  return (
    <div className={`ai-insight ai-insight-${type}`}>
      <div className="insight-header">
        <div className="insight-icon">{ICON_MAP[type]}</div>
        <div className="insight-title-section">
          <h4 className="insight-title">{title}</h4>
          {confidence && (
            <div className="confidence-meter">
              <div className="confidence-bar" style={{ width: `${confidence}%` }} />
              <span className="confidence-label">{confidence}% confidence</span>
            </div>
          )}
        </div>
      </div>

      <div className="insight-message">{message}</div>

      {detail && <div className="insight-detail">{detail}</div>}

      {evidence && evidence.length > 0 && (
        <div className="insight-evidence">
          <strong>Evidence:</strong>
          <ul>
            {evidence.map((item, idx) => (
              <li key={idx}>{item}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
