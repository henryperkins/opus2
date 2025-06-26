import { useState, useEffect } from 'react';
import { ChevronDown, Zap, Brain, Cpu } from 'lucide-react';
import PropTypes from 'prop-types';

// Hook to detect mobile devices
function useMediaQuery() {
  const [isMobile, setIsMobile] = useState(false);
  
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.matchMedia('(max-width: 768px)').matches);
    };
    
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);
  
  return { isMobile };
}

// Default models
const models = [
  {
    id: 'gpt-4o-mini',
    name: 'GPT-4 Omni Mini',
    provider: 'openai',
    speed: 'fast',
    cost: 'low',
    quality: 'good',
    recommended: true
  },
  {
    id: 'gpt-4o',
    name: 'GPT-4 Omni',
    provider: 'openai',
    speed: 'medium',
    cost: 'medium',
    quality: 'best'
  },
  {
    id: 'gpt-4.1',
    name: 'GPT-4.1 (Azure)',
    provider: 'azure',
    speed: 'medium',
    cost: 'medium',
    quality: 'best',
    recommended: true
  },
  {
    id: 'o3',
    name: 'O3 Reasoning (Azure)',
    provider: 'azure',
    speed: 'slow',
    cost: 'high',
    quality: 'best',
    reasoning: true
  }
];

// Get icon for model type
function getModelIcon(model) {
  if (!model) return <Cpu className="w-4 h-4 text-gray-400" />;
  
  if (model.reasoning) return <Brain className="w-4 h-4 text-purple-500" />;
  if (model.speed === 'fast') return <Zap className="w-4 h-4 text-green-500" />;
  return <Cpu className="w-4 h-4 text-blue-500" />;
}

// Desktop dropdown component
function DesktopModelDropdown({ value, onChange, models, isOpen, onToggle }) {
  return (
    <div className="relative">
      <button
        onClick={onToggle}
        className="flex items-center justify-between w-48 px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-sm hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
      >
        <div className="flex items-center gap-2">
          {getModelIcon(models.find(m => m.id === value))}
          <span className="truncate">
            {models.find(m => m.id === value)?.name || 'Select Model'}
          </span>
        </div>
        <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg z-50 max-h-64 overflow-y-auto">
          {models.map((model) => (
            <button
              key={model.id}
              onClick={() => {
                onChange(model.id);
                onToggle();
              }}
              className={`w-full px-3 py-2 text-left hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors
                ${model.id === value ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300' : ''}
                ${model.recommended ? 'border-l-2 border-l-blue-500' : ''}
              `}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {getModelIcon(model)}
                  <div>
                    <div className="font-medium text-sm">{model.name}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      {model.provider} • {model.speed} • {model.cost} cost
                    </div>
                  </div>
                </div>
                {model.recommended && (
                  <span className="text-xs bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 px-2 py-1 rounded">
                    Recommended
                  </span>
                )}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

MobileModelSelect.propTypes = {
  value: PropTypes.string.isRequired,
  onChange: PropTypes.func.isRequired,
  models: PropTypes.array.isRequired
};

// Mobile select component
function MobileModelSelect({ value, onChange, models }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
    >
      {models.map((model) => (
        <option key={model.id} value={model.id}>
          {model.name} ({model.provider}) {model.recommended ? '⭐' : ''}
        </option>
      ))}
    </select>
  );
}

/**
 * Simplified model switcher with responsive design
 * Uses native select on mobile, custom dropdown on desktop
 */
export default function SimpleModelSwitcher({
  value,
  onChange,
  availableModels = models,
  compact = false
}) {
  const { isMobile } = useMediaQuery();
  const [isOpen, setIsOpen] = useState(false);

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = () => setIsOpen(false);
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, [isOpen]);

  // Close dropdown on escape key
  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (e) => {
      if (e.key === 'Escape') setIsOpen(false);
    };
    
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen]);

  const currentModel = availableModels.find(m => m.id === value) || availableModels[0];

  if (compact) {
    return (
      <div className="flex items-center gap-2">
        {getModelIcon(currentModel)}
        <span className="text-xs text-gray-600 dark:text-gray-400 truncate">
          {currentModel?.name || 'No model'}
        </span>
      </div>
    );
  }

  if (isMobile) {
    return (
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          AI Model
        </label>
        <MobileModelSelect
          value={value}
          onChange={onChange}
          models={availableModels}
        />
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
        AI Model
      </label>
      <DesktopModelDropdown
        value={value}
        onChange={onChange}
        models={availableModels}
        isOpen={isOpen}
        onToggle={() => setIsOpen(!isOpen)}
      />
    </div>
  );
}

SimpleModelSwitcher.propTypes = {
  value: PropTypes.string.isRequired,
  onChange: PropTypes.func.isRequired,
  availableModels: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired,
    provider: PropTypes.string.isRequired,
    speed: PropTypes.string,
    cost: PropTypes.string,
    quality: PropTypes.string,
    recommended: PropTypes.bool,
    reasoning: PropTypes.bool
  })),
  compact: PropTypes.bool
};

DesktopModelDropdown.propTypes = {
  value: PropTypes.string.isRequired,
  onChange: PropTypes.func.isRequired,
  models: PropTypes.array.isRequired,
  isOpen: PropTypes.bool.isRequired,
  onToggle: PropTypes.func.isRequired
};
