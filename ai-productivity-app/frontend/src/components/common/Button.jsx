import React, { forwardRef } from 'react';
import PropTypes from 'prop-types';

// Re-usable button component with variant + size support ------------------------

const Button = forwardRef(
  (
    {
      children,
      variant = 'primary',
      size = 'md',
      disabled = false,
      loading = false,
      fullWidth = false,
      type = 'button',
      onClick,
      className = '',
      ariaLabel,
      ariaPressed,
      ariaExpanded,
      ...rest
    },
    ref
  ) => {
    const baseClasses =
      'btn transition-all duration-150 font-medium rounded-md focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2';

    const variantClasses = {
      primary: 'btn-primary',
      secondary: 'btn-secondary',
      ghost: 'btn-ghost',
      danger: 'btn-danger',
    };

    const sizeClasses = {
      sm: 'text-xs px-3 py-1.5 min-h-[36px]',
      md: 'text-sm px-4 py-2 min-h-[44px]',
      lg: 'text-base px-6 py-3 min-h-[52px]',
    };

    const classes = [
      baseClasses,
      variantClasses[variant],
      sizeClasses[size],
      fullWidth && 'w-full',
      disabled && 'opacity-60 cursor-not-allowed',
      loading && 'cursor-wait',
      className,
    ]
      .filter(Boolean)
      .join(' ');

    return (
      <button
        ref={ref}
        type={type}
        className={classes}
        disabled={disabled || loading}
        onClick={onClick}
        aria-label={ariaLabel}
        aria-pressed={ariaPressed}
        aria-expanded={ariaExpanded}
        {...rest}
      >
        {loading ? (
          <span className="flex items-center justify-center">
            <svg
              className="animate-spin -ml-1 mr-2 h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <span>{children}</span>
          </span>
        ) : (
          children
        )}
      </button>
    );
  }
);

Button.displayName = 'Button';

Button.propTypes = {
  children: PropTypes.node.isRequired,
  variant: PropTypes.oneOf(['primary', 'secondary', 'ghost', 'danger']),
  size: PropTypes.oneOf(['sm', 'md', 'lg']),
  disabled: PropTypes.bool,
  loading: PropTypes.bool,
  fullWidth: PropTypes.bool,
  type: PropTypes.oneOf(['button', 'submit', 'reset']),
  onClick: PropTypes.func,
  className: PropTypes.string,
  ariaLabel: PropTypes.string,
  ariaPressed: PropTypes.bool,
  ariaExpanded: PropTypes.bool,
};

export default Button;
