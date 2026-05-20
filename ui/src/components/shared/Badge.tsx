import React from 'react'
import './Badge.css'

interface BadgeProps {
  variant: 'high' | 'medium' | 'low' | 'neutral' | 'info' | 'success' | 'warning' | 'error'
  text: string
  icon?: React.ReactNode
  className?: string
}

export const Badge: React.FC<BadgeProps> = ({ variant, text, icon, className = '' }) => {
  return (
    <span className={`badge badge-${variant} ${className}`}>
      {icon && <span className="badge-icon">{icon}</span>}
      {text}
    </span>
  )
}
