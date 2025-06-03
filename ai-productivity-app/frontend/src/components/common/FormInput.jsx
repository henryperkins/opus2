import React, { forwardRef } from 'react';
import PropTypes from 'prop-types';

/* ----------------------------------------------------------------------------
 * Accessible form input with inline validation error & help text.
 * ---------------------------------------------------------------------------*/

const FormInput = forwardRef(
  (
    {
      id,
      name,
      type = 'text',
      label,
      value,
      onChange,
      onBlur,
      error,
      helpText,
      required = false,
      disabled = false,
      placeholder,
      autoComplete,
      className = '',
      inputClassName = '',
      ...rest
    },
    ref
  ) => {
    const inputId = id || name;
    const errorId = error ? `${inputId}-error` : undefined;
    const helpId = helpText ? `${inputId}-help` : undefined;

    return (
      <div className={`form-group ${className}`}>
        {label && (
          <label htmlFor={inputId} className="form-label">
            {label}
            {required && (
              <span className="text-error-500 ml-1" aria-label="required">
                *
              </span>
            )}
          </label>
        )}

        <input
          ref={ref}
          id={inputId}
          name={name}
          type={type}
          value={value}
          onChange={onChange}
          onBlur={onBlur}
          disabled={disabled}
          required={required}
          placeholder={placeholder}
          autoComplete={autoComplete}
          aria-invalid={error ? 'true' : 'false'}
          aria-describedby={[errorId, helpId].filter(Boolean).join(' ') || undefined}
          className={`w-full px-3 py-2 border rounded-md shadow-sm transition-colors duration-150 ${
            error
              ? 'border-error-500 focus:ring-error-500 focus:border-error-500'
              : 'border-gray-300 dark:border-gray-600 focus:ring-brand-primary-500 focus:border-brand-primary-500'
          } bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 disabled:bg-gray-50 dark:disabled:bg-gray-900 disabled:opacity-60 disabled:cursor-not-allowed focus:outline-none focus:ring-2 ${inputClassName}`}
          {...rest}
        />

        {error && (
          <p id={errorId} className="form-error mt-1" role="alert">
            {error}
          </p>
        )}

        {helpText && !error && (
          <p id={helpId} className="form-help mt-1">
            {helpText}
          </p>
        )}
      </div>
    );
  }
);

FormInput.displayName = 'FormInput';

FormInput.propTypes = {
  id: PropTypes.string,
  name: PropTypes.string.isRequired,
  type: PropTypes.string,
  label: PropTypes.string,
  value: PropTypes.string,
  onChange: PropTypes.func.isRequired,
  onBlur: PropTypes.func,
  error: PropTypes.string,
  helpText: PropTypes.string,
  required: PropTypes.bool,
  disabled: PropTypes.bool,
  placeholder: PropTypes.string,
  autoComplete: PropTypes.string,
  className: PropTypes.string,
  inputClassName: PropTypes.string,
};

export default FormInput;
