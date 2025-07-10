import React, { useState, useEffect } from 'react';
import { Brain, ChevronDown, Zap, ArrowDownUp, GitBranch, RotateCcw, Target, Settings, Search, X } from 'lucide-react';
import { useAIConfig } from '../../contexts/AIConfigContext';

const THINKING_MODES = [
  {
    id: 'off',
    name: 'No Thinking',
    description: 'Direct response without structured thinking',
    icon: X,
    color: 'gray'
  },
  {
    id: 'chain_of_thought',
    name: 'Chain of Thought',
    description: 'Step-by-step reasoning',
    icon: ArrowDownUp,
    color: 'blue'
  },
  {
    id: 'tree_of_thought',
    name: 'Tree of Thoughts',
    description: 'Multiple solution branches',
    icon: GitBranch,
    color: 'green'
  },
  {
    id: 'reflection',
    name: 'Reflection',
    description: 'Self-critical analysis',
    icon: RotateCcw,
    color: 'purple'
  },
  {
    id: 'step_by_step',
    name: 'Step by Step',
    description: 'Sequential breakdown',
    icon: Target,
    color: 'orange'
  },
  {
    id: 'pros_cons',
    name: 'Pros & Cons',
    description: 'Balanced evaluation',
    icon: Settings,
    color: 'indigo'
  },
  {
    id: 'root_cause',
    name: 'Root Cause',
    description: 'Deep problem analysis',
    icon: Search,
    color: 'red'
  }
];

const DEPTH_LEVELS = [
  { id: 'surface', name: 'Surface', color: 'green' },
  { id: 'detailed', name: 'Detailed', color: 'blue' },
  { id: 'comprehensive', name: 'Comprehensive', color: 'purple' },
  { id: 'exhaustive', name: 'Exhaustive', color: 'red' }
];

export default function ThinkingModeSelector({ 
  value = 'off', 
  depth = 'detailed',
  onChange, 
  onDepthChange,
  disabled = false,
  compact = false 
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [showDepthSelector, setShowDepthSelector] = useState(false);
  const { config } = useAIConfig();

  const selectedMode = THINKING_MODES.find(mode => mode.id === value) || THINKING_MODES[0];
  const selectedDepth = DEPTH_LEVELS.find(level => level.id === depth) || DEPTH_LEVELS[1];
  const SelectedIcon = selectedMode.icon;

  const isClaudeProvider = config?.current?.provider === 'anthropic';
  const claudeThinkingEnabled = config?.current?.claude_extended_thinking && isClaudeProvider;

  const handleModeSelect = (mode) => {
    onChange?.(mode.id);
    setIsOpen(false);
  };

  const handleDepthSelect = (depthLevel) => {
    onDepthChange?.(depthLevel.id);
    setShowDepthSelector(false);
  };

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (isOpen || showDepthSelector) {
        setIsOpen(false);
        setShowDepthSelector(false);
      }
    };

    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, [isOpen, showDepthSelector]);

  if (compact) {
    return (
      <div className="relative">
        <button
          onClick={(e) => {
            e.stopPropagation();
            setIsOpen(!isOpen);
          }}
          disabled={disabled}
          className={`flex items-center gap-2 px-2 py-1 text-xs border rounded-md transition-colors ${
            value === 'off'
              ? 'border-gray-300 text-gray-500 bg-gray-50'
              : `border-${selectedMode.color}-300 text-${selectedMode.color}-600 bg-${selectedMode.color}-50`
          } hover:bg-opacity-80 disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          <SelectedIcon className="h-3 w-3" />
          <span className="hidden sm:inline">{selectedMode.name}</span>
          <ChevronDown className="h-3 w-3" />
        </button>

        {isOpen && (
          <div className="absolute top-full mt-1 left-0 bg-white border border-gray-200 rounded-lg shadow-lg py-1 z-50 min-w-48">
            {THINKING_MODES.map((mode) => {
              const IconComponent = mode.icon;
              return (
                <button
                  key={mode.id}
                  onClick={() => handleModeSelect(mode)}
                  className={`w-full px-3 py-2 text-left flex items-center gap-2 hover:bg-gray-50 transition-colors ${
                    mode.id === value ? 'bg-blue-50 text-blue-700' : 'text-gray-700'
                  }`}
                >
                  <IconComponent className={`h-4 w-4 text-${mode.color}-500`} />
                  <div>
                    <div className="font-medium text-sm">{mode.name}</div>
                    <div className="text-xs text-gray-500">{mode.description}</div>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      {/* Thinking Mode Selector */}
      <div className="relative">
        <button
          onClick={(e) => {
            e.stopPropagation();
            setIsOpen(!isOpen);
          }}
          disabled={disabled}
          className={`flex items-center gap-2 px-3 py-2 border rounded-lg transition-colors ${
            value === 'off'
              ? 'border-gray-300 text-gray-600 bg-white hover:bg-gray-50'
              : `border-${selectedMode.color}-300 text-${selectedMode.color}-700 bg-${selectedMode.color}-50 hover:bg-${selectedMode.color}-100`
          } disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          <Brain className="h-4 w-4" />
          <SelectedIcon className="h-4 w-4" />
          <span className="font-medium">{selectedMode.name}</span>
          <ChevronDown className="h-4 w-4" />
        </button>

        {isOpen && (
          <div className="absolute top-full mt-1 left-0 bg-white border border-gray-200 rounded-lg shadow-lg py-2 z-50 min-w-64">
            <div className="px-3 py-1 border-b border-gray-200 mb-2">
              <div className="flex items-center gap-2">
                <Brain className="h-4 w-4 text-gray-500" />
                <span className="text-sm font-medium text-gray-700">Thinking Mode</span>
              </div>
              {claudeThinkingEnabled && (
                <div className="text-xs text-green-600 mt-1">
                  Claude Extended Thinking Enabled
                </div>
              )}
            </div>

            <div className="max-h-64 overflow-y-auto">
              {THINKING_MODES.map((mode) => {
                const IconComponent = mode.icon;
                return (
                  <button
                    key={mode.id}
                    onClick={() => handleModeSelect(mode)}
                    className={`w-full px-3 py-2 text-left flex items-center gap-3 hover:bg-gray-50 transition-colors ${
                      mode.id === value ? 'bg-blue-50 border-r-2 border-blue-500' : ''
                    }`}
                  >
                    <div className={`p-1 rounded bg-${mode.color}-100`}>
                      <IconComponent className={`h-4 w-4 text-${mode.color}-600`} />
                    </div>
                    <div className="flex-1">
                      <div className={`font-medium text-sm ${
                        mode.id === value ? 'text-blue-700' : 'text-gray-900'
                      }`}>
                        {mode.name}
                      </div>
                      <div className="text-xs text-gray-500">{mode.description}</div>
                    </div>
                    {mode.id === value && (
                      <Zap className="h-4 w-4 text-blue-500" />
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Depth Selector - only show if thinking mode is enabled */}
      {value !== 'off' && (
        <div className="relative">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowDepthSelector(!showDepthSelector);
            }}
            disabled={disabled}
            className={`flex items-center gap-2 px-3 py-2 border rounded-lg transition-colors border-${selectedDepth.color}-300 text-${selectedDepth.color}-700 bg-${selectedDepth.color}-50 hover:bg-${selectedDepth.color}-100 disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            <span className="text-sm font-medium">{selectedDepth.name}</span>
            <ChevronDown className="h-4 w-4" />
          </button>

          {showDepthSelector && (
            <div className="absolute top-full mt-1 left-0 bg-white border border-gray-200 rounded-lg shadow-lg py-2 z-50 min-w-36">
              <div className="px-3 py-1 border-b border-gray-200 mb-2">
                <span className="text-sm font-medium text-gray-700">Analysis Depth</span>
              </div>

              {DEPTH_LEVELS.map((level) => (
                <button
                  key={level.id}
                  onClick={() => handleDepthSelect(level)}
                  className={`w-full px-3 py-2 text-left flex items-center justify-between hover:bg-gray-50 transition-colors ${
                    level.id === depth ? 'bg-blue-50 text-blue-700' : 'text-gray-700'
                  }`}
                >
                  <span className="font-medium text-sm">{level.name}</span>
                  {level.id === depth && (
                    <Zap className="h-4 w-4 text-blue-500" />
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}