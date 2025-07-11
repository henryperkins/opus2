
// frontend/src/components/settings/UnifiedAISettings.jsx
import React, { useState, useEffect } from 'react';
import {
  Brain,
  Settings,
  Zap,
  DollarSign,
  AlertCircle,
  Check,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  Info
} from 'lucide-react';
import {
  useAIConfig,
  useModelSelection,
  useGenerationParams,
  useReasoningConfig
} from '../../contexts/AIConfigContext';

export default function UnifiedAISettings() {
  const {
    config,
    loading,
    error,
    testResult,
    testConfig,
    applyPreset,
    providers
  } = useAIConfig();

  const {
    currentModel,
    currentProvider,
    availableModels,
    selectModel,
    selectProvider
  } = useModelSelection();

  const {
    temperature,
    maxTokens,
    topP,
    frequencyPenalty,
    presencePenalty,
    updateParams
  } = useGenerationParams();

  const {
    enableReasoning,
    reasoningEffort,
    claudeExtendedThinking,
    claudeThinkingMode,
    claudeThinkingBudget,
    isClaudeProvider,
    isAzureOrOpenAI,
    supportsReasoning,
    supportsThinking,
    updateReasoningConfig
  } = useReasoningConfig();

  const [expandedSections, setExpandedSections] = useState({
    model: true,
    generation: true,
    reasoning: true,
    presets: false
  });

  const [isTesting, setIsTesting] = useState(false);

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const handleTestConfig = async () => {
    setIsTesting(true);
    try {
      await testConfig();
    } finally {
      setIsTesting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-start">
          <AlertCircle className="h-5 w-5 text-red-400 mr-2 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-medium text-red-800">Configuration Error</h3>
            <p className="mt-1 text-sm text-red-600">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Brain className="h-6 w-6 text-blue-500" />
          <h2 className="text-xl font-semibold text-gray-900">AI Configuration</h2>
        </div>
        <button
          onClick={handleTestConfig}
          disabled={isTesting}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {isTesting ? (
            <>
              <RefreshCw className="h-4 w-4 animate-spin" />
              Testing...
            </>
          ) : (
            <>
              <Zap className="h-4 w-4" />
              Test Configuration
            </>
          )}
        </button>
      </div>

      {/* Test Result */}
      {testResult && (
        <div className={`p-4 rounded-lg border ${
          testResult.success
            ? 'bg-green-50 border-green-200'
            : 'bg-red-50 border-red-200'
        }`}>
          <div className="flex items-start">
            {testResult.success ? (
              <Check className="h-5 w-5 text-green-600 mr-2 flex-shrink-0 mt-0.5" />
            ) : (
              <AlertCircle className="h-5 w-5 text-red-600 mr-2 flex-shrink-0 mt-0.5" />
            )}
            <div className="flex-1">
              <p className={`text-sm font-medium ${
                testResult.success ? 'text-green-800' : 'text-red-800'
              }`}>
                {testResult.message}
              </p>
              {testResult.response_time && (
                <p className="mt-1 text-sm text-gray-600">
                  Response time: {testResult.response_time}s
                </p>
              )}
              {testResult.error && (
                <p className="mt-1 text-sm text-red-600">
                  Error: {testResult.error}
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Model Selection Section */}
      <Section
        title="Model Selection"
        icon={Settings}
        expanded={expandedSections.model}
        onToggle={() => toggleSection('model')}
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Provider
            </label>
            <select
              value={config?.provider || ''}
              onChange={(e) => selectProvider(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              {Object.entries(providers).map(([providerId, providerData]) => (
                <option key={providerId} value={providerId}>
                  {/* Fallback to the provider id when no display_name is supplied by the backend */}
                  {providerData?.display_name || providerId}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Model
            </label>
            <select
              value={config?.model_id || ''}
              onChange={(e) => selectModel(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              {availableModels
                // Some older backend payloads don’t include the *provider* field
                // on each model entry.  Treat those models as belonging to the
                // currently selected provider so the list doesn’t render empty.
                .filter(m => m.provider === config?.provider)
                .map(model => (
                  <option key={model.model_id} value={model.model_id}>
                    {/* Fallback to model_id when no display_name provided */}
                    {model.display_name || model.model_id}
                  </option>
                ))}
            </select>
          </div>
        </div>
      </Section>

      {/* Generation Parameters Section */}
      <Section
        title="Generation Parameters"
        icon={Settings}
        expanded={expandedSections.generation}
        onToggle={() => toggleSection('generation')}
      >
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Temperature */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Temperature</label>
            <input
              type="number"
              step="0.01"
              min="0"
              max="2"
              value={temperature ?? 0}
              onChange={(e) => updateParams({ temperature: parseFloat(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          {/* Max tokens */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Max tokens</label>
            <input
              type="number"
              min="16"
              max="200000"
              value={maxTokens ?? ''}
              onChange={(e) => updateParams({ max_tokens: parseInt(e.target.value || '0', 10) })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          {/* Top-p */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Top-p</label>
            <input
              type="number"
              step="0.01"
              min="0"
              max="1"
              value={topP ?? 1}
              onChange={(e) => updateParams({ top_p: parseFloat(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          {/* Frequency penalty */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Frequency penalty</label>
            <input
              type="number"
              step="0.1"
              min="-2"
              max="2"
              value={frequencyPenalty ?? 0}
              onChange={(e) => updateParams({ frequency_penalty: parseFloat(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          {/* Presence penalty */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Presence penalty</label>
            <input
              type="number"
              step="0.1"
              min="-2"
              max="2"
              value={presencePenalty ?? 0}
              onChange={(e) => updateParams({ presence_penalty: parseFloat(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>
      </Section>

      {/* Reasoning / Thinking Section */}
      {(supportsReasoning || supportsThinking) && (
        <Section
          title="Reasoning / Thinking"
          icon={Brain}
          expanded={expandedSections.reasoning}
          onToggle={() => toggleSection('reasoning')}
        >
          <div className="space-y-4">
            {isAzureOrOpenAI && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex items-center gap-2">
                  <input
                    id="enableReasoning"
                    type="checkbox"
                    checked={enableReasoning || false}
                    onChange={(e) => updateReasoningConfig({ enable_reasoning: e.target.checked })}
                  />
                  <label htmlFor="enableReasoning" className="text-sm">Enable Reasoning (Responses API)</label>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Reasoning effort</label>
                  <select
                    value={reasoningEffort || 'medium'}
                    onChange={(e) => updateReasoningConfig({ reasoning_effort: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    {['low', 'medium', 'high'].map(level => (
                      <option key={level} value={level}>{level}</option>
                    ))}
                  </select>
                </div>
              </div>
            )}

            {isClaudeProvider && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex items-center gap-2">
                  <input
                    id="extendedThinking"
                    type="checkbox"
                    checked={claudeExtendedThinking || false}
                    onChange={(e) => updateReasoningConfig({ claude_extended_thinking: e.target.checked })}
                  />
                  <label htmlFor="extendedThinking" className="text-sm">Claude extended thinking</label>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Thinking mode</label>
                  <select
                    value={claudeThinkingMode || 'enabled'}
                    onChange={(e) => updateReasoningConfig({ claude_thinking_mode: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    {['off', 'enabled', 'aggressive'].map(m => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Thinking token budget</label>
                  <input
                    type="number"
                    min="1024"
                    max="65536"
                    step="1024"
                    value={claudeThinkingBudget || 16384}
                    onChange={(e) => updateReasoningConfig({ claude_thinking_budget_tokens: parseInt(e.target.value || '0', 10) })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>
            )}
          </div>
        </Section>
      )}
    </div>
  );
}

function Section({ title, icon: Icon, expanded, onToggle, children }) {
  return (
    <div className="border border-gray-200 rounded-lg">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between p-4 bg-gray-50 hover:bg-gray-100 rounded-t-lg"
      >
        <div className="flex items-center gap-3">
          <Icon className="h-5 w-5 text-gray-600" />
          <h3 className="text-lg font-medium text-gray-800">{title}</h3>
        </div>
        {expanded ? (
          <ChevronDown className="h-5 w-5 text-gray-500" />
        ) : (
          <ChevronRight className="h-5 w-5 text-gray-500" />
        )}
      </button>
      {expanded && (
        <div className="p-4 bg-white rounded-b-lg">
          {children}
        </div>
      )}
    </div>
  );
}
