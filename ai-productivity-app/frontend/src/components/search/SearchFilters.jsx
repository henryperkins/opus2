// Advanced search filters for language, file type, and code structure
import React from 'react';

export default function SearchFilters({ filters, onChange, availableLanguages = [] }) {
  const handleFilterChange = (key, value) => {
    onChange({
      ...filters,
      [key]: value
    });
  };

  const clearFilters = () => {
    onChange({
      language: null,
      fileType: null,
      symbolType: null,
      projectIds: []
    });
  };

  const hasActiveFilters = Object.values(filters).some(v => v && (Array.isArray(v) ? v.length > 0 : true));

  return (
    <div className="search-filters space-y-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-gray-900">Filters</h3>
        {hasActiveFilters && (
          <button
            onClick={clearFilters}
            className="text-xs text-blue-600 hover:text-blue-800"
          >
            Clear all
          </button>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Language
        </label>
        <select
          value={filters.language || ''}
          onChange={(e) => handleFilterChange('language', e.target.value || null)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="">All languages</option>
          {availableLanguages.map(lang => (
            <option key={lang} value={lang}>
              {lang.charAt(0).toUpperCase() + lang.slice(1)}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Symbol Type
        </label>
        <div className="space-y-2">
          {['function', 'class', 'method', 'interface', 'type'].map(type => (
            <label key={type} className="flex items-center">
              <input
                type="radio"
                name="symbolType"
                value={type}
                checked={filters.symbolType === type}
                onChange={(e) => handleFilterChange('symbolType', e.target.value)}
                className="mr-2"
              />
              <span className="text-sm text-gray-700">
                {type.charAt(0).toUpperCase() + type.slice(1)}s
              </span>
            </label>
          ))}
          <label className="flex items-center">
            <input
              type="radio"
              name="symbolType"
              value=""
              checked={!filters.symbolType}
              onChange={() => handleFilterChange('symbolType', null)}
              className="mr-2"
            />
            <span className="text-sm text-gray-700">All types</span>
          </label>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          File Type
        </label>
        <div className="space-y-2">
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={filters.fileType === 'source'}
              onChange={(e) => handleFilterChange('fileType', e.target.checked ? 'source' : null)}
              className="mr-2"
            />
            <span className="text-sm text-gray-700">Source files only</span>
          </label>
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={filters.fileType === 'test'}
              onChange={(e) => handleFilterChange('fileType', e.target.checked ? 'test' : null)}
              className="mr-2"
            />
            <span className="text-sm text-gray-700">Test files only</span>
          </label>
        </div>
      </div>

      <div className="pt-4 border-t border-gray-200">
        <p className="text-xs text-gray-500">
          Search uses both semantic similarity and keyword matching for best results
        </p>
      </div>
    </div>
  );
}
