import React from 'react'
import './KVRow.css'

interface KVRowProps {
  label: string
  value: React.ReactNode
  icon?: React.ReactNode
  badge?: { text: string; variant: 'high' | 'medium' | 'low' | 'neutral' }
  className?: string
}

export const KVRow: React.FC<KVRowProps> = ({ label, value, icon, badge, className = '' }) => {
  return (
    <div className={`kv-row ${className}`}>
      <div className="kv-label">
        {icon && <span className="kv-icon">{icon}</span>}
        <span>{label}</span>
      </div>
      <div className="kv-value">
        {value}
        {badge && <span className={`kv-badge badge-${badge.variant}`}>{badge.text}</span>}
      </div>
    </div>
  )
}
