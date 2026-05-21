import React from 'react';
import clsx from 'clsx';

export type ButtonVariant = 'primary' | 'secondary' | 'danger';
export type ButtonSize = 'small' | 'medium' | 'large';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
  fullWidth?: boolean;
  loading?: boolean;
  disabled?: boolean;
  children: React.ReactNode;
}

/**
 * Button Component — USWDS Federal Design System
 *
 * Variants:
 * - primary: #0050D8 blue (main CTAs)
 * - secondary: #F5F5F5 light gray (alternative actions)
 * - danger: #D9381E red (delete/destructive actions)
 *
 * Features:
 * - 200ms smooth transitions
 * - 3px blue focus ring with 2px offset (WCAG 2.1 AA)
 * - Icon support with gap management
 * - Loading state with disabled styling
 */
export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'medium',
  icon,
  iconPosition = 'left',
  fullWidth = false,
  loading = false,
  disabled = false,
  className,
  children,
  ...props
}) => {
  const variantClass = `btn-${variant}`;

  const sizeClasses = {
    small: 'px-4 py-2 text-sm',
    medium: 'px-6 py-3 text-base',
    large: 'px-8 py-4 text-lg'
  };

  const baseClasses = clsx(
    variantClass,
    sizeClasses[size],
    {
      'w-full': fullWidth,
      'opacity-50 cursor-not-allowed': disabled || loading
    },
    className
  );

  const contentClasses = clsx(
    'flex items-center justify-center gap-2',
    {
      'flex-row-reverse': iconPosition === 'right'
    }
  );

  return (
    <button
      className={baseClasses}
      disabled={disabled || loading}
      {...props}
    >
      <span className={contentClasses}>
        {icon && <span className="flex-shrink-0">{icon}</span>}
        <span>{loading ? 'Loading...' : children}</span>
      </span>
    </button>
  );
};

export default Button;
