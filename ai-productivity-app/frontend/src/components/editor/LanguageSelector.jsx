import React, { useMemo } from "react";
import PropTypes from "prop-types";

/**
 * ?? NOTE: Feel free to swap the emoji for your preferred icon set.
 * The key point is: printable, no control characters, no quotes to escape.
 */
export const SUPPORTED_LANGUAGES = [
  { value: "javascript", label: "JavaScript", icon: "??" },
  { value: "typescript", label: "TypeScript", icon: "??" },
  { value: "python", label: "Python", icon: "??" },
  { value: "java", label: "Java", icon: "?" },
  { value: "csharp", label: "C#", icon: "?" },
  { value: "cpp", label: "C++", icon: "?" },
  { value: "c", label: "C", icon: "??" },
  { value: "go", label: "Go", icon: "??" },
  { value: "rust", label: "Rust", icon: "??" },
  { value: "php", label: "PHP", icon: "??" },
  { value: "ruby", label: "Ruby", icon: "??" },
  { value: "html", label: "HTML", icon: "??" },
  { value: "css", label: "CSS", icon: "??" },
  { value: "scss", label: "SCSS", icon: "??" },
  { value: "json", label: "JSON", icon: "{}" },
  { value: "yaml", label: "YAML", icon: "??" },
  { value: "xml", label: "XML", icon: "??" },
  { value: "markdown", label: "Markdown", icon: "??" },
  { value: "shell", label: "Shell", icon: "??" },
  { value: "sql", label: "SQL", icon: "??" },
];

/**
 * Language selector component.
 */
const LanguageSelector = ({
  value,
  onChange,
  className = "",
  showIcon = true,
  size = "md",
  id = "language-selector",
  ...rest
}) => {
  const selectedLanguage = SUPPORTED_LANGUAGES.find((l) => l.value === value);

  const sizeClasses = useMemo(
    () => ({
      sm: "text-xs px-2 py-1",
      md: "text-sm px-3 py-1.5",
      lg: "text-base px-4 py-2",
    }),
    [],
  );

  return (
    <div className={`relative inline-block ${className}`}>
      <select
        id={id}
        aria-label="Programming language"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={`
          ${sizeClasses[size]}
          border border-gray-300 rounded-md bg-white
          focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
          hover:border-gray-400 transition-colors
          appearance-none pr-8 pl-8
        `}
        {...rest}
      >
        {SUPPORTED_LANGUAGES.map((language) => (
          <option key={language.value} value={language.value}>
            {language.label}
          </option>
        ))}
      </select>

      {/* dropdown arrow */}
      <div className="absolute inset-y-0 right-0 flex items-center pr-2 pointer-events-none">
        <svg
          className="w-4 h-4 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </div>

      {/* left-side icon */}
      {showIcon && selectedLanguage && (
        <div className="absolute inset-y-0 left-2 flex items-center pointer-events-none">
          <span
            role="img"
            aria-label={`${selectedLanguage.label} icon`}
            className="text-sm"
          >
            {selectedLanguage.icon}
          </span>
        </div>
      )}
    </div>
  );
};

LanguageSelector.propTypes = {
  /** currently selected value */
  value: PropTypes.string.isRequired,
  /** handler: newValue => void */
  onChange: PropTypes.func.isRequired,
  className: PropTypes.string,
  showIcon: PropTypes.bool,
  size: PropTypes.oneOf(["sm", "md", "lg"]),
  /** optional id for a11y */
  id: PropTypes.string,
};

export default LanguageSelector;
