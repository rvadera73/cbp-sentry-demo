import { AlertTriangle, AlertCircle, CheckCircle, Info, X } from 'lucide-react';
import { useState } from 'react';

interface AlertBannerProps {
  type: 'error' | 'warning' | 'success' | 'info';
  title: string;
  message?: string;
  dismissible?: boolean;
  className?: string;
}

export default function AlertBanner({
  type,
  title,
  message,
  dismissible = true,
  className = ''
}: AlertBannerProps) {
  const [isDismissed, setIsDismissed] = useState(false);

  if (isDismissed) return null;

  const typeMap = {
    error: {
      bg: 'bg-red-50 border-red-200',
      icon: <AlertTriangle className="text-red-600" size={20} />,
      text: 'text-red-900',
      title: 'text-red-800'
    },
    warning: {
      bg: 'bg-amber-50 border-amber-200',
      icon: <AlertCircle className="text-amber-600" size={20} />,
      text: 'text-amber-900',
      title: 'text-amber-800'
    },
    success: {
      bg: 'bg-green-50 border-green-200',
      icon: <CheckCircle className="text-green-600" size={20} />,
      text: 'text-green-900',
      title: 'text-green-800'
    },
    info: {
      bg: 'bg-blue-50 border-blue-200',
      icon: <Info className="text-blue-600" size={20} />,
      text: 'text-blue-900',
      title: 'text-blue-800'
    }
  };

  const style = typeMap[type];

  return (
    <div className={`${style.bg} border rounded-lg p-3 flex gap-3 ${className}`}>
      {style.icon}
      <div className="flex-1">
        <h4 className={`font-semibold ${style.title}`}>{title}</h4>
        {message && <p className={`text-sm ${style.text} mt-1`}>{message}</p>}
      </div>
      {dismissible && (
        <button
          onClick={() => setIsDismissed(true)}
          className={`${style.text} hover:opacity-60`}
        >
          <X size={18} />
        </button>
      )}
    </div>
  );
}
