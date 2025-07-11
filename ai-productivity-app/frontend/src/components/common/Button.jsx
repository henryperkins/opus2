import React, { forwardRef } from "react";
import PropTypes from "prop-types";
import LoadingSpinner from "./LoadingSpinner";

// Re-usable button component with variant + size support ------------------------

const Button = forwardRef(
  (
    {
      children,
      variant = "primary",
      size = "md",
      disabled = false,
      loading = false,
      fullWidth = false,
      type = "button",
      onClick,
      className = "",
      ariaLabel,
      ariaPressed,
      ariaExpanded,
      ...rest
    },
    ref,
  ) => {
    const baseClasses =
      "btn transition-all duration-200 font-medium rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 transform hover:scale-[1.02] active:scale-[0.98]";

    const variantClasses = {
      primary: "btn-primary",
      secondary: "btn-secondary",
      ghost: "btn-ghost",
      danger: "btn-danger",
    };

    const sizeClasses = {
      sm: "text-xs px-3 py-1.5 min-h-[36px]",
      md: "text-sm px-4 py-2 min-h-[44px]",
      lg: "text-base px-6 py-3 min-h-[52px]",
    };

    const classes = [
      baseClasses,
      variantClasses[variant],
      sizeClasses[size],
      fullWidth && "w-full",
      disabled && "opacity-60 cursor-not-allowed",
      loading && "cursor-wait animate-pulse",
      className,
    ]
      .filter(Boolean)
      .join(" ");

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
            <LoadingSpinner
              size="sm"
              showLabel={false}
              className="-ml-1 mr-2"
            />
            <span>{children}</span>
          </span>
        ) : (
          children
        )}
      </button>
    );
  },
);

Button.displayName = "Button";

Button.propTypes = {
  children: PropTypes.node.isRequired,
  variant: PropTypes.oneOf(["primary", "secondary", "ghost", "danger"]),
  size: PropTypes.oneOf(["sm", "md", "lg"]),
  disabled: PropTypes.bool,
  loading: PropTypes.bool,
  fullWidth: PropTypes.bool,
  type: PropTypes.oneOf(["button", "submit", "reset"]),
  onClick: PropTypes.func,
  className: PropTypes.string,
  ariaLabel: PropTypes.string,
  ariaPressed: PropTypes.bool,
  ariaExpanded: PropTypes.bool,
};

export default Button;
