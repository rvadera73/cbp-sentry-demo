import React, { useState } from 'react'
import './SectionHeader.css'
import { ChevronDown } from 'lucide-react'

interface SectionHeaderProps {
  title: string
  subtitle?: string
  collapsible?: boolean
  defaultOpen?: boolean
  action?: React.ReactNode
  onOpenChange?: (open: boolean) => void
  children?: React.ReactNode
  className?: string
}

export const SectionHeader: React.FC<SectionHeaderProps> = ({
  title,
  subtitle,
  collapsible = false,
  defaultOpen = true,
  action,
  onOpenChange,
  children,
  className = ''
}) => {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  const handleToggle = () => {
    const newState = !isOpen
    setIsOpen(newState)
    onOpenChange?.(newState)
  }

  return (
    <div className={`section-header-container ${className}`}>
      <div className="section-header">
        <div className="section-header-content">
          {collapsible && (
            <button
              className="section-toggle"
              onClick={handleToggle}
              aria-expanded={isOpen}
            >
              <ChevronDown size={20} className={isOpen ? 'open' : ''} />
            </button>
          )}
          <div className="section-title-block">
            <h3 className="section-title">{title}</h3>
            {subtitle && <p className="section-subtitle">{subtitle}</p>}
          </div>
        </div>
        {action && <div className="section-action">{action}</div>}
      </div>
      {collapsible && isOpen && children && <div className="section-body">{children}</div>}
      {!collapsible && children && <div className="section-body">{children}</div>}
    </div>
  )
}
