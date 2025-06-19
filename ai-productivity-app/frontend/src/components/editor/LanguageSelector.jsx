import React from 'react';

const SUPPORTED_LANGUAGES = [
  { value: 'javascript', label: 'JavaScript', icon: '=è' },
  { value: 'typescript', label: 'TypeScript', icon: '=7' },
  { value: 'python', label: 'Python', icon: '=' },
  { value: 'java', label: 'Java', icon: '' },
  { value: 'csharp', label: 'C#', icon: '=œ' },
  { value: 'cpp', label: 'C++', icon: '='' },
  { value: 'c', label: 'C', icon: '™' },
  { value: 'go', label: 'Go', icon: '=9' },
  { value: 'rust', label: 'Rust', icon: '>€' },
  { value: 'php', label: 'PHP', icon: '=' },
  { value: 'ruby', label: 'Ruby', icon: '=Ž' },
  { value: 'html', label: 'HTML', icon: '<' },
  { value: 'css', label: 'CSS', icon: '<¨' },
  { value: 'scss', label: 'SCSS', icon: '=„' },
  { value: 'json', label: 'JSON', icon: '=Ë' },
  { value: 'yaml', label: 'YAML', icon: '=Ä' },
  { value: 'xml', label: 'XML', icon: '=Ã' },
  { value: 'markdown', label: 'Markdown', icon: '=Ý' },
  { value: 'shell', label: 'Shell', icon: '=¥' },
  { value: 'sql', label: 'SQL', icon: '=Ã' },
];

const LanguageSelector = ({ 
  value, 
  onChange, 
  className = '',
  showIcon = true,
  size = 'md'
}) => {
  const selectedLanguage = SUPPORTED_LANGUAGES.find(lang => lang.value === value);

  const sizeClasses = {
    sm: 'text-xs px-2 py-1',
    md: 'text-sm px-3 py-1.5',
    lg: 'text-base px-4 py-2'
  };

  return (
    <div className={`relative ${className}`}>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={`
          ${sizeClasses[size]}
          border border-gray-300 rounded-md bg-white
          focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
          hover:border-gray-400 transition-colors
          appearance-none pr-8
        `}
      >
        {SUPPORTED_LANGUAGES.map((language) => (
          <option key={language.value} value={language.value}>
            {language.label}
          </option>
        ))}
      </select>
      
      {/* Custom dropdown arrow */}
      <div className="absolute inset-y-0 right-0 flex items-center pr-2 pointer-events-none">
        <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
        </svg>
      </div>

      {/* Language icon display */}
      {showIcon && selectedLanguage && (
        <div className="absolute inset-y-0 left-2 flex items-center pointer-events-none">
          <span className="text-sm">{selectedLanguage.icon}</span>
        </div>
      )}
    </div>
  );
};

export default LanguageSelector;