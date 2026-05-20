import React from 'react'
import './Card.css'

interface CardProps {
  title?: string
  subtitle?: string
  children: React.ReactNode
  footer?: React.ReactNode
  clickable?: boolean
  onClick?: () => void
  highlight?: 'high' | 'medium' | 'low' | 'neutral'
  className?: string
}

export const Card: React.FC<CardProps> = ({
  title,
  subtitle,
  children,
  footer,
  clickable = false,
  onClick,
  highlight = 'neutral',
  className = ''
}) => {
  return (
    <div
      className={`card card-${highlight} ${clickable ? 'card-clickable' : ''} ${className}`}
      onClick={onClick}
      role={clickable ? 'button' : undefined}
      tabIndex={clickable ? 0 : undefined}
    >
      {(title || subtitle) && (
        <div className="card-header">
          {title && <h3 className="card-title">{title}</h3>}
          {subtitle && <p className="card-subtitle">{subtitle}</p>}
        </div>
      )}
      <div className="card-body">{children}</div>
      {footer && <div className="card-footer">{footer}</div>}
    </div>
  )
}
