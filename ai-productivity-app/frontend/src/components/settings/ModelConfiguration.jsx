/* eslint-disable */
// components/settings/ModelConfiguration.jsx
import React, { useState, useEffect } from "react";
import { Settings, AlertCircle, Check, RefreshCw } from "lucide-react";
import { useAIConfig } from "../contexts/AIConfigContext";
import { configAPI } from "../../api/config";
import { toast } from "../common/Toast";
import client from "../../api/client";
import {
  defaultChatSettings,
  validateChatSettings,
} from "../../config/chat-settings";
import { modelPresets, modelInfo } from "../../utils/modelConfigs";

export default function ModelConfiguration() {
  const { config, providers, loading, error, refetch } = useAIConfig();

  /* ------------------------------------------------------------------ */
  /* Local state                                                        */
  /* ------------------------------------------------------------------ */
  const [modelConfig, setModelConfig] = useState({
    provider: "openai",
    model: "gpt-4o-mini",
    temperature: 0.7,
    maxTokens: 2048,
    topP: 0.95,
    frequencyPenalty: 0,
    presencePenalty: 0,
    systemPrompt: "",
    responseFormat: "text",
    useResponsesApi: false,
    reasoningEffort: "high",
  });

  const [selectedPreset, setSelectedPreset] = useState("balanced");
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [customModels, setCustomModels] = useState([]);
  const [qualitySettings, setQualitySettings] = useState(
    defaultChatSettings.quality,
  );
  const [qualityMetrics, setQualityMetrics] = useState({
    averageRating: 0,
    totalResponses: 0,
    successRate: 0,
    averageResponseTime: 0,
  });

  /* ------------------------------------------------------------------ */
  /* Effect: sync config from backend                                   */
  /* ------------------------------------------------------------------ */
  useEffect(() => {
    if (config) {
      setModelConfig((prev) => ({
        ...prev,
        provider: config.provider,
        model: config.model_id,
        temperature: config.temperature ?? prev.temperature,
        maxTokens: config.max_tokens ?? prev.maxTokens,
        topP: config.top_p ?? prev.topP,
        frequencyPenalty: config.frequency_penalty ?? prev.frequencyPenalty,
        presencePenalty: config.presence_penalty ?? prev.presencePenalty,
        systemPrompt: config.system_prompt ?? prev.systemPrompt,
        responseFormat: config.response_format ?? prev.responseFormat,
        useResponsesApi: config.use_responses_api ?? prev.useResponsesApi,
        reasoningEffort: config.reasoning_effort ?? prev.reasoningEffort,
      }));
    }
  }, [config]);

  /* ------------------------------------------------------------------ */
  /* Defensive helpers (model list)                                     */
  /* ------------------------------------------------------------------ */
  // Modelos disponibles para el proveedor actual (puede ser lista vacía)
  const providerModels = providers[modelConfig.provider]?.models || [];
  // ¿No hay modelos?
  const noModels = providerModels.length === 0;

  /* ------------------------------------------------------------------ */
  /* Handlers                                                           */
  /* ------------------------------------------------------------------ */
  const handlePresetSelect = (presetId) => {
    const preset = modelPresets.find((p) => p.id === presetId);
    if (preset) {
      setModelConfig((prev) => ({
        ...prev,
        ...preset.config,
      }));
      setSelectedPreset(presetId);
    }
  };

  const handleModelChange = (model) => {
    setModelConfig((prev) => ({ ...prev, model }));

    // Auto-adjust parameters based on model
    const info = modelInfo[model];
    if (info && info.contextLength < modelConfig.maxTokens) {
      setModelConfig((prev) => ({
        ...prev,
        maxTokens: Math.floor(info.contextLength * 0.5),
      }));
    }
  };

  const handleTestConfig = async () => {
    setIsTesting(true);
    setTestResult(null);
    try {
      const result = await configAPI.testModelConfig(modelConfig);
      setTestResult({
        success: result.success,
        message:
          result.message ||
          (result.success
            ? "Configuration is valid!"
            : "Configuration test failed"),
      });
    } catch {
      setTestResult({ success: false, message: "Failed to test configuration" });
    } finally {
      setIsTesting(false);
    }
  };

  const handleSaveConfig = async () => {
    try {
      await configAPI.updateModelConfig({
        provider: modelConfig.provider,
        model_id: modelConfig.model,
        temperature: modelConfig.temperature,
        max_tokens: modelConfig.maxTokens,
        top_p: modelConfig.topP,
        frequency_penalty: modelConfig.frequencyPenalty,
        presence_penalty: modelConfig.presencePenalty,
        system_prompt: modelConfig.systemPrompt,
        response_format: modelConfig.responseFormat,
        use_responses_api: modelConfig.useResponsesApi,
        reasoning_effort: modelConfig.reasoningEffort,
      });
      toast.success("Model configuration saved successfully");
      if (refetch) await refetch();
    } catch {
      toast.error("Failed to save configuration");
    }
  };

  const handleQualitySettingChange = async (setting, value) => {
    const newSettings = { ...qualitySettings, [setting]: value };
    setQualitySettings(newSettings);
    try {
      await client.patch("/api/auth/preferences", {
        quality_settings: newSettings,
      });
      toast.success("Quality settings saved");
    } catch (e) {
      console.error("Failed to save quality settings:", e);
      toast.error("Failed to save quality settings");
      setQualitySettings(qualitySettings); // revert on error
    }
  };

  /* ------------------------------------------------------------------ */
  /* Load quality metrics & settings                                    */
  /* ------------------------------------------------------------------ */
  useEffect(() => {
    // Mock metrics — replace with real API call
    setQualityMetrics({
      averageRating: 4.2,
      totalResponses: 1547,
      successRate: 0.94,
      averageResponseTime: 2.3,
    });

    (async () => {
      try {
        const { data } = await client.get("/api/auth/preferences");
        if (data.quality_settings) setQualitySettings(data.quality_settings);
      } catch {
        setQualitySettings(defaultChatSettings.quality);
      }
    })();
  }, []);

  /* ------------------------------------------------------------------ */
  /* Helpers                                                            */
  /* ------------------------------------------------------------------ */
  const estimateCost = () => {
    const info = modelInfo[modelConfig.model];
    if (!info) return null;
    const inputTokens = 1000;
    const outputTokens = modelConfig.maxTokens;
    const inputCost = (inputTokens / 1000) * info.costPer1kTokens.input;
    const outputCost = (outputTokens / 1000) * info.costPer1kTokens.output;
    return { perRequest: inputCost + outputCost, per1kRequests: (inputCost + outputCost) * 1000 };
  };

  /* ------------------------------------------------------------------ */
  /* Early returns (loading / error)                                    */
  /* ------------------------------------------------------------------ */
  if (loading)
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-8 bg-gray-200 rounded w-1/4" />
        <div className="h-64 bg-gray-200 rounded" />
      </div>
    );

  if (error)
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-600">Failed to load configuration</p>
      </div>
    );

  const cost = estimateCost();

  /* ------------------------------------------------------------------ */
  /* JSX                                                                */
  /* ------------------------------------------------------------------ */
  return (
    <div className="space-y-6">
      {/* ───────────────────────────────── Model Selection ─────────────────────────────── */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Model Selection</h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          {/* Provider selector */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Provider</label>
            <select
              value={modelConfig.provider}
              onChange={(e) =>
                setModelConfig({ ...modelConfig, provider: e.target.value })
              }
              className="w-full border rounded-lg px-3 py-2"
            >
              <option value="openai">OpenAI</option>
              <option value="azure">Azure OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="custom">Custom</option>
            </select>
          </div>

          {/* Model selector (defensivo) */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Model</label>
            <select
              value={modelConfig.model}
              onChange={(e) => handleModelChange(e.target.value)}
              className="w-full border rounded-lg px-3 py-2"
              disabled={noModels}
            >
              {noModels ? (
                <option value="" disabled>
                  No models available for the selected provider
                </option>
              ) : (
                providerModels.map((model) => (
                  <option key={model.model_id} value={model.model_id}>
                    {model.display_name || model.model_id}
                    {model.recommended && " ⭐"}
                  </option>
                ))
              )}
            </select>
          </div>
        </div>

        {/* Model Info */}
        {(() => {
          const selectedModel = providerModels.find(
            (m) => m.model_id === modelConfig.model,
          );
          return (
            selectedModel && (
              <div className="bg-gray-50 rounded-lg p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Context Length</span>
                  <span className="text-sm font-medium">
                    {selectedModel.context_window?.toLocaleString() || "N/A"} tokens
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Capabilities</span>
                  <div className="flex gap-1">
                    {selectedModel.capabilities &&
                      Object.entries(selectedModel.capabilities)
                        .filter(([, ok]) => ok)
                        .map(([cap]) => (
                          <span
                            key={cap}
                            className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded"
                          >
                            {cap.replace("supports_", "").replace("_", " ")}
                          </span>
                        ))}
                  </div>
                </div>

                {selectedModel.cost_per_1k_tokens && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Cost per 1K tokens</span>
                    <span className="text-sm font-medium">
                      $
                      {(
                        selectedModel.cost_per_1k_tokens.input +
                        selectedModel.cost_per_1k_tokens.output
                      ).toFixed(4)}
                    </span>
                  </div>
                )}
              </div>
            )
          );
        })()}
      </div>

      {/* ────────────────────────────── Quick Presets ────────────────────────────── */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Quick Presets</h3>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {modelPresets.map((preset) => (
            <button
              key={preset.id}
              onClick={() => handlePresetSelect(preset.id)}
              className={`p-3 rounded-lg border transition-colors ${
                selectedPreset === preset.id
                  ? "border-blue-500 bg-blue-50"
                  : "border-gray-200 hover:border-gray-300"
              }`}
            >
              <div className="flex items-center justify-center mb-2 text-gray-600">
                {React.createElement(preset.icon, { className: "w-4 h-4" })}
              </div>
              <div className="text-sm font-medium text-gray-900">
                {preset.name}
              </div>
              <div className="text-xs text-gray-500 mt-1">{preset.description}</div>
            </button>
          ))}
        </div>
      </div>

      {/* ───────────────────────────────── Parameters ─────────────────────────────── */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-gray-900">Parameters</h3>
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="text-sm text-blue-600 hover:text-blue-700"
          >
            {showAdvanced ? "Hide" : "Show"} Advanced
          </button>
        </div>

        <div className="space-y-4">
          {/* Responses API toggle for Azure */}
          {modelConfig.provider === "azure" && (
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-gray-700 flex items-center gap-2">
                <RefreshCw className="w-4 h-4" /> Use Responses API (preview)
              </label>
              <input
                type="checkbox"
                checked={modelConfig.useResponsesApi}
                onChange={(e) =>
                  setModelConfig({
                    ...modelConfig,
                    useResponsesApi: e.target.checked,
                  })
                }
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
            </div>
          )}

          {/* Temperature */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-gray-700">Temperature</label>
              <span className="text-sm text-gray-600">{modelConfig.temperature}</span>
            </div>
            <input
              type="range"
              min="0"
              max="2"
              step="0.1"
              value={modelConfig.temperature}
              onChange={(e) =>
                setModelConfig({ ...modelConfig, temperature: parseFloat(e.target.value) })
              }
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>Focused</span>
              <span>Creative</span>
            </div>
          </div>

          {/* Max Tokens */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-gray-700">Max Tokens</label>
              <span className="text-sm text-gray-600">{modelConfig.maxTokens}</span>
            </div>
            <input
              type="range"
              min="256"
              max={(() => {
                const selectedModel = providerModels.find(
                  (m) => m.model_id === modelConfig.model,
                );
                return selectedModel?.context_window || 4096;
              })()}
              step="256"
              value={modelConfig.maxTokens}
              onChange={(e) =>
                setModelConfig({ ...modelConfig, maxTokens: parseInt(e.target.value, 10) })
              }
              className="w-full"
            />
          </div>

          {/* Advanced sliders / selects */}
          {showAdvanced && (
            <>
              {/* Top P */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-gray-700">Top P</label>
                  <span className="text-sm text-gray-600">{modelConfig.topP}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={modelConfig.topP}
                  onChange={(e) =>
                    setModelConfig({ ...modelConfig, topP: parseFloat(e.target.value) })
                  }
                  className="w-full"
                />
              </div>

              {/* Frequency Penalty */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-gray-700">Frequency Penalty</label>
                  <span className="text-sm text-gray-600">{modelConfig.frequencyPenalty}</span>
                </div>
                <input
                  type="range"
                  min="-2"
                  max="2"
                  step="0.1"
                  value={modelConfig.frequencyPenalty}
                  onChange={(e) =>
                    setModelConfig({
                      ...modelConfig,
                      frequencyPenalty: parseFloat(e.target.value),
                    })
                  }
                  className="w-full"
                />
              </div>

              {/* Response Format */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Response Format
                </label>
                <select
                  value={modelConfig.responseFormat}
                  onChange={(e) =>
                    setModelConfig({ ...modelConfig, responseFormat: e.target.value })
                  }
                  className="w-full border rounded-lg px-3 py-2"
                >
                  <option value="text">Plain Text</option>
                  <option value="markdown">Markdown</option>
                  <option value="json">JSON</option>
                </select>
              </div>

              {/* Reasoning Effort Level */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Reasoning Effort Level
                </label>
                <select
                  value={modelConfig.reasoningEffort}
                  onChange={(e) =>
                    setModelConfig({ ...modelConfig, reasoningEffort: e.target.value })
                  }
                  className="w-full border rounded-lg px-3 py-2"
                >
                  <option value="low">Low - Fast responses</option>
                  <option value="medium">Medium - Balanced speed/quality</option>
                  <option value="high">High - Best quality (default)</option>
                </select>
                <p className="text-sm text-gray-500 mt-1">
                  Controls how much reasoning the model applies. Higher levels provide
                  better quality but slower responses.
                </p>
              </div>
            </>
          )}
        </div>
      </div>

      {/* ───────────────────────────────── System Prompt ───────────────────────────── */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">System Prompt</h3>
        <textarea
          value={modelConfig.systemPrompt}
          onChange={(e) =>
            setModelConfig({ ...modelConfig, systemPrompt: e.target.value })
          }
          placeholder="Enter a system prompt to guide the model's behavior..."
          className="w-full h-32 border rounded-lg px-3 py-2 text-sm"
        />
      </div>

      {/* ───────────────────────────────── Actions ─────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <button
            onClick={handleTestConfig}
            disabled={isTesting}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-50 flex items-center space-x-2"
          >
            {isTesting ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Settings className="w-4 h-4" />
            )}
            <span>Test Configuration</span>
          </button>

          {testResult && (
            <div
              className={`flex items-center space-x-2 text-sm ${
                testResult.success ? "text-green-600" : "text-red-600"
              }`}
            >
              {testResult.success ? (
                <Check className="w-4 h-4" />
              ) : (
                <AlertCircle className="w-4 h-4" />
              )}
              <span>{testResult.message}</span>
            </div>
          )}
        </div>

        <button
          onClick={handleSaveConfig}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Save Configuration
        </button>
      </div>

      {/* ─────────────────────────── Response Quality Tracking ─────────────────────── */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center space-x-2 mb-4">
          <AlertCircle className="w-5 h-5 text-purple-600" />
          <h3 className="text-lg font-semibold text-gray-900">
            Response Quality Tracking
          </h3>
        </div>

        {/* Quality Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-blue-50 p-4 rounded-lg">
            <div className="text-2xl font-bold text-blue-600">
              {qualityMetrics.averageRating}
            </div>
            <div className="text-sm text-gray-600">Average Rating</div>
          </div>
          <div className="bg-green-50 p-4 rounded-lg">
            <div className="text-2xl font-bold text-green-600">
              {qualityMetrics.totalResponses}
            </div>
            <div className="text-sm text-gray-600">Total Responses</div>
          </div>
          <div className="bg-yellow-50 p-4 rounded-lg">
            <div className="text-2xl font-bold text-yellow-600">
              {(qualityMetrics.successRate * 100).toFixed(1)}%
            </div>
            <div className="text-sm text-gray-600">Success Rate</div>
          </div>
          <div className="bg-purple-50 p-4 rounded-lg">
            <div className="text-2xl font-bold text-purple-600">
              {qualityMetrics.averageResponseTime}s
            </div>
            <div className="text-sm text-gray-600">Avg Response Time</div>
          </div>
        </div>

        {/* Quality Settings */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Track Responses
              </label>
              <p className="text-xs text-gray-500">
                Enable response quality tracking
              </p>
            </div>
            <input
              type="checkbox"
              checked={qualitySettings.trackResponses}
              onChange={(e) =>
                handleQualitySettingChange("trackResponses", e.target.checked)
              }
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                User Feedback
              </label>
              <p className="text-xs text-gray-500">
                Show thumbs up/down for responses
              </p>
            </div>
            <input
              type="checkbox"
              checked={qualitySettings.feedbackEnabled}
              onChange={(e) =>
                handleQualitySettingChange("feedbackEnabled", e.target.checked)
              }
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Auto Rating
              </label>
              <p className="text-xs text-gray-500">
                Automatically rate responses based on metrics
              </p>
            </div>
            <input
              type="checkbox"
              checked={qualitySettings.autoRating}
              onChange={(e) =>
                handleQualitySettingChange("autoRating", e.target.checked)
              }
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Quality Threshold: {qualitySettings.qualityThreshold}
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={qualitySettings.qualityThreshold}
              onChange={(e) =>
                handleQualitySettingChange(
                  "qualityThreshold",
                  parseFloat(e.target.value),
                )
              }
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>Low</span>
              <span>High</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
