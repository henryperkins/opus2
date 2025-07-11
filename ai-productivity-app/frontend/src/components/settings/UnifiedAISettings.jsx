import React, { useState, useEffect, useCallback } from "react";
import {
  Brain,
  Settings,
  Zap,
  RefreshCw,
  Check,
  AlertCircle,
} from "lucide-react";
import { debounce } from "lodash-es";

import {
  useAIConfig,
  useModelSelection,
  useGenerationParams,
  useReasoningConfig,
} from "../../contexts/AIConfigContext";

import Section from "../common/CollapsibleSection";
import PresetSelector from "./PresetSelector";

export default function UnifiedAISettings() {
  // --------------------------------------------------------------------- //
  // Context hooks
  // --------------------------------------------------------------------- //
  const {
    loading,
    error,
    testResult,
    testConfig,
    providers,
    isAdmin,
  } = useAIConfig();

  const {
    selectProvider,
    selectModel,
    currentProvider,
    availableModels,
  } = useModelSelection();

  const {
    temperature,
    maxTokens,
    topP,
    frequencyPenalty,
    presencePenalty,
    updateParams,
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
    updateReasoningConfig,
  } = useReasoningConfig();

  // --------------------------------------------------------------------- //
  // Local UI state
  // --------------------------------------------------------------------- //
  const [expanded, setExpanded] = useState({
    presets: false,
    model: true,
    generation: true,
    reasoning: true,
  });
  const toggle = (k) => setExpanded((p) => ({ ...p, [k]: !p[k] }));

  const [testing, setTesting] = useState(false);

  // --------------------------------------------------------------------- //
  // Debounced setters – prevents spamming PATCH /ai-config on every key-press
  // --------------------------------------------------------------------- //
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const debouncedUpdate = useCallback(debounce(updateParams, 250), []);

  // --------------------------------------------------------------------- //
  // Event handlers
  // --------------------------------------------------------------------- //
  const handleTest = async () => {
    setTesting(true);
    try {
      await testConfig();
    } finally {
      setTesting(false);
    }
  };

  // --------------------------------------------------------------------- //
  // Early returns
  // --------------------------------------------------------------------- //
  if (loading) {
    return (
      <div className="flex items-center justify-center h-60">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (error) {
    const msg =
      typeof error === "string"
        ? error
        : error?.message ?? JSON.stringify(error, null, 2);

    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-start">
          <AlertCircle className="h-5 w-5 text-red-500 mr-2 mt-0.5" />
          <p className="text-sm text-red-700 whitespace-pre-wrap">{msg}</p>
        </div>
      </div>
    );
  }

  // --------------------------------------------------------------------- //
  // Render
  // --------------------------------------------------------------------- //
  return (
    <div className="space-y-6">
      {/* ------------------------------------------------ Header ---------- */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Brain className="h-6 w-6 text-blue-500" />
          <h2 className="text-xl font-semibold">AI Configuration</h2>
        </div>

        <button
          onClick={handleTest}
          disabled={testing || !isAdmin}
          title={!isAdmin ? "Admin role required" : "Run live test"}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-md
                     bg-blue-600 text-white hover:bg-blue-700
                     disabled:opacity-50"
        >
          {testing ? (
            <>
              <RefreshCw className="h-4 w-4 animate-spin" />
              Testing…
            </>
          ) : (
            <>
              <Zap className="h-4 w-4" />
              Test configuration
            </>
          )}
        </button>
      </div>

      {/* ------------------------------------------------ Test result ---- */}
      {testResult && (
        <div
          className={`p-4 rounded-md border ${
            testResult.success
              ? "bg-green-50 border-green-200"
              : "bg-red-50 border-red-200"
          }`}
        >
          <div className="flex items-start">
            {testResult.success ? (
              <Check className="h-5 w-5 text-green-600 mr-2 mt-0.5" />
            ) : (
              <AlertCircle className="h-5 w-5 text-red-600 mr-2 mt-0.5" />
            )}
            <div>
              <p
                className={`font-medium ${
                  testResult.success ? "text-green-800" : "text-red-800"
                }`}
              >
                {testResult.message}
              </p>
              {testResult.response_time && (
                <p className="text-gray-600">
                  Response time: {testResult.response_time}s
                </p>
              )}
              {testResult.error && (
                <p className="text-red-600">Error: {testResult.error}</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------ Presets -------- */}
      <Section
        title="Presets"
        icon={Settings}
        expanded={expanded.presets}
        onToggle={() => toggle("presets")}
      >
        <PresetSelector />
      </Section>

      {/* ------------------------------------------------ Model ---------- */}
      <Section
        title="Model selection"
        icon={Settings}
        expanded={expanded.model}
        onToggle={() => toggle("model")}
      >
        <div className="grid gap-4 md:grid-cols-2">
          {/* Provider select */}
          <div>
            <label className="block text-sm font-medium mb-1">Provider</label>
            <select
              value={currentProvider}
              onChange={(e) => selectProvider(e.target.value)}
              className="w-full input"
            >
              {Object.entries(providers).map(([id, p]) => (
                <option key={id} value={id}>
                  {p?.display_name ?? id}
                </option>
              ))}
            </select>
          </div>

          {/* Model select */}
          <div>
            <label className="block text-sm font-medium mb-1">Model</label>
            <select
              value={availableModels.find((m) => m.selected)?.model_id ?? ""}
              onChange={(e) => selectModel(e.target.value)}
              className="w-full input"
            >
              {availableModels
                .filter(
                  (m) => (m.provider ?? currentProvider) === currentProvider,
                )
                .map((m) => (
                  <option key={m.model_id} value={m.model_id}>
                    {m.display_name ?? m.model_id}
                  </option>
                ))}
            </select>
          </div>
        </div>
      </Section>

      {/* ------------------------------------------------ Generation ----- */}
      <Section
        title="Generation parameters"
        icon={Settings}
        expanded={expanded.generation}
        onToggle={() => toggle("generation")}
      >
        <div className="grid gap-4 md:grid-cols-3">
          {[
            {
              id: "temperature",
              label: "Temperature",
              value: temperature ?? 0,
              min: 0,
              max: 2,
              step: 0.01,
            },
            {
              id: "max_tokens",
              label: "Max tokens",
              value: maxTokens ?? "",
              min: 16,
              max: 200000,
              step: 1,
            },
            {
              id: "top_p",
              label: "Top-p",
              value: topP ?? 1,
              min: 0,
              max: 1,
              step: 0.01,
            },
            {
              id: "frequency_penalty",
              label: "Frequency penalty",
              value: frequencyPenalty ?? 0,
              min: -2,
              max: 2,
              step: 0.1,
            },
            {
              id: "presence_penalty",
              label: "Presence penalty",
              value: presencePenalty ?? 0,
              min: -2,
              max: 2,
              step: 0.1,
            },
          ].map((fld) => (
            <NumberInput
              key={fld.id}
              {...fld}
              onChange={(num) => debouncedUpdate({ [fld.id]: num })}
            />
          ))}
        </div>
      </Section>

      {/* ------------------------------------------------ Reasoning ------ */}
      {(supportsReasoning || supportsThinking) && (
        <Section
          title="Reasoning / thinking"
          icon={Brain}
          expanded={expanded.reasoning}
          onToggle={() => toggle("reasoning")}
        >
          {/* Azure / OpenAI (Responses API) ------------------------------ */}
          {isAzureOrOpenAI && (
            <div className="grid md:grid-cols-2 gap-4">
              <Checkbox
                id="enableReasoning"
                label="Enable reasoning (Responses API)"
                checked={enableReasoning}
                onChange={(v) => updateReasoningConfig({ enable_reasoning: v })}
              />

              <Select
                label="Reasoning effort"
                value={reasoningEffort ?? "medium"}
                options={["low", "medium", "high"]}
                onChange={(v) =>
                  updateReasoningConfig({ reasoning_effort: v })
                }
              />
            </div>
          )}

          {/* Claude specific ------------------------------------------- */}
          {isClaudeProvider && (
            <div className="grid md:grid-cols-2 gap-4">
              <Checkbox
                id="extendedThinking"
                label="Claude extended thinking"
                checked={claudeExtendedThinking}
                onChange={(v) =>
                  updateReasoningConfig({ claude_extended_thinking: v })
                }
              />

              <Select
                label="Thinking mode"
                value={claudeThinkingMode ?? "enabled"}
                options={["off", "enabled", "aggressive"]}
                onChange={(v) =>
                  updateReasoningConfig({ claude_thinking_mode: v })
                }
              />

              <NumberInput
                id="claudeThinkingBudget"
                label="Thinking token budget"
                value={claudeThinkingBudget ?? 16384}
                min={1024}
                max={65536}
                step={1024}
                onChange={(n) =>
                  updateReasoningConfig({
                    claude_thinking_budget_tokens: n,
                  })
                }
              />
            </div>
          )}
        </Section>
      )}
    </div>
  );
}

/* ----------------------------------------------------------------------- */
/* Helper UI controls                                                      */
/* ----------------------------------------------------------------------- */
function NumberInput({ id, label, value, onChange, ...rest }) {
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium mb-1">
        {label}
      </label>
      <input
        id={id}
        type="number"
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full input"
        {...rest}
      />
    </div>
  );
}

function Checkbox({ id, label, checked, onChange }) {
  return (
    <label htmlFor={id} className="flex items-center gap-2">
      <input
        id={id}
        type="checkbox"
        checked={!!checked}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span className="text-sm">{label}</span>
    </label>
  );
}

function Select({ label, value, options, onChange }) {
  return (
    <div>
      <label className="block text-sm font-medium mb-1">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full input"
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </div>
  );
}
