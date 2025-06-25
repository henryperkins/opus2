/* eslint-disable */
// components/chat/ModelSwitcher.jsx
import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, Zap, Brain, DollarSign, Check, AlertCircle } from 'lucide-react';
import { useConfig } from '../../hooks/useConfig';
import { useModelSelection } from '../../hooks/useModelSelect';

// Default model options - will be enhanced by dynamic config
const defaultModelOptions = [
  {
    id: 'gpt-4o-mini',
    name: 'GPT-4 Omni Mini',
    provider: 'openai',
    speed: 'fast',
    cost: 'low',
    quality: 'good',
    contextLength: 128000,
    recommended: true
  },
  {
    id: 'gpt-4o',
    name: 'GPT-4 Omni',
    provider: 'openai',
    speed: 'medium',
    cost: 'medium',
    quality: 'best',
    contextLength: 128000
  },
  // Azure deployment names
  {
    id: 'gpt-4.1',
    name: 'GPT-4.1 (Azure)',
    provider: 'azure',
    speed: 'medium',
    cost: 'medium',
    quality: 'best',
    contextLength: 128000,
    recommended: true
  },
  {
    id: 'o3',
    name: 'O3 Reasoning (Azure)',
    provider: 'azure',
    speed: 'slow',
    cost: 'high',
    quality: 'best',
    contextLength: 128000,
    reasoning: true
  },
  {
    id: 'gpt-4-turbo',
    name: 'GPT-4 Turbo',
    provider: 'openai',
    speed: 'medium',
    cost: 'high',
    quality: 'best',
    contextLength: 128000
  },
  {
    id: 'gpt-3.5-turbo',
    name: 'GPT-3.5 Turbo',
    provider: 'openai',
    speed: 'fast',
    cost: 'low',
    quality: 'good',
    contextLength: 16385
  }
];

export default function ModelSwitcher({
  onModelChange,
  compact = false,
  showCost = true
}) {
  const { config } = useConfig();
  const {
    currentModel,
    setModel,
    modelStats,
    isLoading,
    testModel
  } = useModelSelection();

  const [isOpen, setIsOpen] = useState(false);
  const [hoveredModel, setHoveredModel] = useState(null);
  const dropdownRef = useRef(null);

  // Get available models from dynamic config or fall back to defaults
  const availableModels = React.useMemo(() => {
    if (config?.providers) {
      const dynamicModels = [];
      
      // Add OpenAI models
      if (config.providers.openai?.chat_models) {
        config.providers.openai.chat_models.forEach(modelId => {
          const defaultModel = defaultModelOptions.find(m => m.id === modelId);
          if (defaultModel) {
            dynamicModels.push(defaultModel);
          } else {
            // Add unknown OpenAI models with basic info
            dynamicModels.push({
              id: modelId,
              name: modelId,
              provider: 'openai',
              speed: 'medium',
              cost: 'medium',
              quality: 'good',
              contextLength: 128000
            });
          }
        });
      }
      
      // Add Azure models
      if (config.providers.azure?.chat_models) {
        config.providers.azure.chat_models.forEach(modelId => {
          const defaultModel = defaultModelOptions.find(m => m.id === modelId);
          if (defaultModel) {
            dynamicModels.push(defaultModel);
          } else {
            // Add unknown Azure models with basic info
            dynamicModels.push({
              id: modelId,
              name: `${modelId} (Azure)`,
              provider: 'azure',
              speed: 'medium',
              cost: 'medium',
              quality: 'good',
              contextLength: 128000
            });
          }
        });
      }
      
      return dynamicModels.length > 0 ? dynamicModels : defaultModelOptions;
    }
    
    return defaultModelOptions;
  }, [config]);

  const currentModelInfo = availableModels.find(m => m.id === currentModel) || availableModels[0];

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleModelSelect = async (modelId) => {
    if (modelId === currentModel) {
      setIsOpen(false);
      return;
    }

    const success = await setModel(modelId);
    if (success) {
      onModelChange?.(modelId);
      setIsOpen(false);
    }
  };

  const getQualityIcon = (quality) => {
    switch (quality) {
      case 'best':
        return <Brain className="w-3 h-3 text-purple-500" />;
      case 'better':
        return <Brain className="w-3 h-3 text-blue-500" />;
      default:
        return <Zap className="w-3 h-3 text-gray-500" />;
    }
  };

  const getCostIndicator = (cost) => {
    switch (cost) {
      case 'low':
        return <span className="text-green-600">$</span>;
      case 'medium':
        return <span className="text-yellow-600">$$</span>;
      case 'high':
        return <span className="text-red-600">$$$</span>;
      default:
        return null;
    }
  };

  const getSpeedIndicator = (speed) => {
    switch (speed) {
      case 'fast':
        return <div className="flex space-x-0.5">
          <div className="w-1 h-3 bg-green-500 rounded-full"></div>
          <div className="w-1 h-3 bg-green-500 rounded-full"></div>
          <div className="w-1 h-3 bg-green-500 rounded-full"></div>
        </div>;
      case 'medium':
        return <div className="flex space-x-0.5">
          <div className="w-1 h-3 bg-yellow-500 rounded-full"></div>
          <div className="w-1 h-3 bg-yellow-500 rounded-full"></div>
          <div className="w-1 h-3 bg-gray-300 rounded-full"></div>
        </div>;
      case 'slow':
        return <div className="flex space-x-0.5">
          <div className="w-1 h-3 bg-red-500 rounded-full"></div>
          <div className="w-1 h-3 bg-gray-300 rounded-full"></div>
          <div className="w-1 h-3 bg-gray-300 rounded-full"></div>
        </div>;
      default:
        return null;
    }
  };

  if (compact) {
    return (
      <div className="relative" ref={dropdownRef}>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center space-x-2 px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
        >
          <span className="font-medium">{currentModelInfo.name}</span>
          <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>

        {isOpen && (
          <div className="absolute top-full mt-2 right-0 w-64 bg-white rounded-lg shadow-lg border border-gray-200 z-50">
            <div className="p-2">
              {availableModels.map(model => (
                <button
                  key={model.id}
                  onClick={() => handleModelSelect(model.id)}
                  onMouseEnter={() => setHoveredModel(model.id)}
                  onMouseLeave={() => setHoveredModel(null)}
                  disabled={isLoading}
                  className={`w-full text-left px-3 py-2 rounded-md transition-colors ${
                    model.id === currentModel
                      ? 'bg-blue-50 text-blue-700'
                      : 'hover:bg-gray-50'
                  } ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">
                      {model.name}
                      {model.recommended && ' ⭐'}
                    </span>
                    {model.id === currentModel && (
                      <Check className="w-4 h-4 text-blue-600" />
                    )}
                  </div>

                  {hoveredModel === model.id && (
                    <div className="mt-1 flex items-center space-x-3 text-xs text-gray-500">
                      {getSpeedIndicator(model.speed)}
                      {showCost && getCostIndicator(model.cost)}
                      {getQualityIcon(model.quality)}
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  // Full size variant
  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-medium text-gray-900">Active Model</h4>
        {modelStats && (
          <div className="flex items-center space-x-2 text-xs text-gray-500">
            <span>{modelStats.requestsToday} requests today</span>
            {showCost && <span>~${modelStats.estimatedCost.toFixed(2)}</span>}
          </div>
        )}
      </div>

      <div className="relative" ref={dropdownRef}>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <div className="flex items-center space-x-3">
            {getQualityIcon(currentModelInfo.quality)}
            <div className="text-left">
              <div className="font-medium text-gray-900">{currentModelInfo.name}</div>
              <div className="text-xs text-gray-500">
                {currentModelInfo.contextLength.toLocaleString()} tokens • {currentModelInfo.provider}
              </div>
            </div>
          </div>
          <ChevronDown className={`w-5 h-5 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>

        {isOpen && (
          <div className="absolute top-full mt-2 left-0 right-0 bg-white rounded-lg shadow-lg border border-gray-200 z-50 max-h-96 overflow-y-auto">
            <div className="p-3 space-y-1">
              {availableModels.map(model => (
                <button
                  key={model.id}
                  onClick={() => handleModelSelect(model.id)}
                  disabled={isLoading}
                  className={`w-full text-left px-4 py-3 rounded-lg transition-all ${
                    model.id === currentModel
                      ? 'bg-blue-50 border border-blue-200'
                      : 'hover:bg-gray-50 border border-transparent'
                  } ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-3">
                      {getQualityIcon(model.quality)}
                      <div>
                        <div className="font-medium text-gray-900">
                          {model.name}
                          {model.recommended && (
                            <span className="ml-2 text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                              Recommended
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-gray-500">
                          {model.contextLength.toLocaleString()} tokens
                        </div>
                      </div>
                    </div>
                    {model.id === currentModel && (
                      <Check className="w-5 h-5 text-blue-600" />
                    )}
                  </div>

                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center space-x-4">
                      <div className="flex items-center space-x-1">
                        <span className="text-gray-500">Speed:</span>
                        {getSpeedIndicator(model.speed)}
                      </div>
                      {showCost && (
                        <div className="flex items-center space-x-1">
                          <span className="text-gray-500">Cost:</span>
                          {getCostIndicator(model.cost)}
                        </div>
                      )}
                    </div>
                    <span className="text-gray-400">{model.provider}</span>
                  </div>
                </button>
              ))}
            </div>

            <div className="border-t px-4 py-3 bg-gray-50">
              <button
                onClick={() => {
                  setIsOpen(false);
                  // Navigate to full settings
                  window.location.href = '/settings#model-configuration';
                }}
                className="text-sm text-blue-600 hover:text-blue-700 font-medium"
              >
                Advanced Configuration →
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Performance Indicator */}
      {modelStats && modelStats.averageLatency && (
        <div className="mt-3 flex items-center justify-between text-xs text-gray-500">
          <span>Avg response time</span>
          <span className={`font-medium ${
            modelStats.averageLatency < 2000 ? 'text-green-600' :
            modelStats.averageLatency < 5000 ? 'text-yellow-600' :
            'text-red-600'
          }`}>
            {(modelStats.averageLatency / 1000).toFixed(1)}s
          </span>
        </div>
      )}
    </div>
  );
}
