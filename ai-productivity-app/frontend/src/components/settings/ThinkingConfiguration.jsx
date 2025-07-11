/* eslint-disable */
// components/settings/ThinkingConfiguration.jsx
import React, { useState, useEffect } from "react";
import {
  Brain,
  Zap,
  Target,
  GitBranch,
  ArrowDownUp,
  Search,
  RotateCcw,
  Info,
  CheckCircle,
  XCircle,
  Settings,
  AlertTriangle,
} from "lucide-react";
import { useAIConfig } from "../contexts/AIConfigContext";
import { toast } from "../common/Toast";

const THINKING_MODES = [
  {
    id: "chain_of_thought",
    name: "Chain of Thought",
    description: "Step-by-step reasoning through problems",
    icon: ArrowDownUp,
    color: "blue",
    useCase: "Complex problem solving, logical reasoning",
  },
  {
    id: "tree_of_thought",
    name: "Tree of Thoughts",
    description: "Explore multiple solution branches",
    icon: GitBranch,
    color: "green",
    useCase: "Creative solutions, alternative approaches",
  },
  {
    id: "reflection",
    name: "Reflection",
    description: "Self-critical analysis and revision",
    icon: RotateCcw,
    color: "purple",
    useCase: "Quality improvement, error detection",
  },
  {
    id: "step_by_step",
    name: "Step by Step",
    description: "Methodical sequential breakdown",
    icon: Target,
    color: "orange",
    useCase: "Implementation planning, tutorials",
  },
  {
    id: "pros_cons",
    name: "Pros & Cons",
    description: "Balanced evaluation approach",
    icon: Settings,
    color: "indigo",
    useCase: "Decision making, trade-off analysis",
  },
  {
    id: "root_cause",
    name: "Root Cause",
    description: "Deep analysis of underlying issues",
    icon: Search,
    color: "red",
    useCase: "Debugging, problem diagnosis",
  },
];

const THINKING_DEPTHS = [
  {
    id: "surface",
    name: "Surface",
    description: "Quick overview and key points",
  },
  {
    id: "detailed",
    name: "Detailed",
    description: "Thorough analysis with examples",
  },
  {
    id: "comprehensive",
    name: "Comprehensive",
    description: "In-depth coverage of all aspects",
  },
  {
    id: "exhaustive",
    name: "Exhaustive",
    description: "Complete analysis of every angle",
  },
];

const CLAUDE_THINKING_MODES = [
  { id: "off", name: "Off", description: "Disable extended thinking" },
  { id: "enabled", name: "Enabled", description: "Standard extended thinking" },
  {
    id: "aggressive",
    name: "Aggressive",
    description: "Maximum thinking depth",
  },
];

export default function ThinkingConfiguration() {
  const { config, updateConfig, loading } = useAIConfig();
  const [thinkingConfig, setThinkingConfig] = useState({
    // Claude extended thinking settings
    claude_extended_thinking: true,
    claude_thinking_mode: "enabled",
    claude_thinking_budget_tokens: 16384,
    claude_show_thinking_process: true,
    claude_adaptive_thinking_budget: true,
    claude_max_thinking_budget: 65536,

    // Azure/OpenAI reasoning settings
    enable_reasoning: false,
    reasoning_effort: "medium",

    // Tool usage settings
    default_thinking_mode: "chain_of_thought",
    default_thinking_depth: "detailed",
    auto_select_thinking_mode: true,
    enable_documentation_fetching: true,
  });

  const [testResult, setTestResult] = useState(null);
  const [isTesting, setIsTesting] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    if (config?.current) {
      setThinkingConfig((prev) => ({
        ...prev,
        claude_extended_thinking:
          config.current.claude_extended_thinking ??
          prev.claude_extended_thinking,
        claude_thinking_mode:
          config.current.claude_thinking_mode ?? prev.claude_thinking_mode,
        claude_thinking_budget_tokens:
          config.current.claude_thinking_budget_tokens ??
          prev.claude_thinking_budget_tokens,
        claude_show_thinking_process:
          config.current.claude_show_thinking_process ??
          prev.claude_show_thinking_process,
        claude_adaptive_thinking_budget:
          config.current.claude_adaptive_thinking_budget ??
          prev.claude_adaptive_thinking_budget,
        claude_max_thinking_budget:
          config.current.claude_max_thinking_budget ??
          prev.claude_max_thinking_budget,
        enable_reasoning:
          config.current.enable_reasoning ?? prev.enable_reasoning,
        reasoning_effort:
          config.current.reasoning_effort ?? prev.reasoning_effort,
      }));
    }
  }, [config]);

  const handleConfigChange = async (key, value) => {
    const newConfig = { ...thinkingConfig, [key]: value };
    setThinkingConfig(newConfig);

    try {
      await updateConfig({ [key]: value });
      toast.success("Thinking configuration updated");
    } catch (error) {
      toast.error(`Failed to update configuration: ${error.message}`);
      // Revert on error
      setThinkingConfig(thinkingConfig);
    }
  };

  const handleBulkConfigUpdate = async (updates) => {
    const newConfig = { ...thinkingConfig, ...updates };
    setThinkingConfig(newConfig);

    try {
      await updateConfig(updates);
      toast.success("Thinking configuration updated");
    } catch (error) {
      toast.error(`Failed to update configuration: ${error.message}`);
      // Revert on error
      setThinkingConfig(thinkingConfig);
    }
  };

  const testThinkingMode = async (mode) => {
    setIsTesting(true);
    setTestResult(null);

    try {
      const testTask =
        "Analyze the pros and cons of using microservices architecture for a medium-sized web application";

      const response = await fetch("/api/chat/test-thinking", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          task: testTask,
          thinking_mode: mode,
          depth: thinkingConfig.default_thinking_depth,
          project_id: 1,
        }),
      });

      if (response.ok) {
        const result = await response.json();
        setTestResult({ success: true, result });
        toast.success("Thinking mode test completed");
      } else {
        throw new Error(`HTTP ${response.status}`);
      }
    } catch (error) {
      setTestResult({ success: false, error: error.message });
      toast.error("Thinking mode test failed");
    } finally {
      setIsTesting(false);
    }
  };

  const getCurrentProvider = () => {
    return config?.current?.provider || "openai";
  };

  const isClaudeProvider = () => {
    return getCurrentProvider() === "anthropic";
  };

  const isAzureOrOpenAI = () => {
    const provider = getCurrentProvider();
    return provider === "azure" || provider === "openai";
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Brain className="h-6 w-6 text-blue-500" />
        <h2 className="text-xl font-semibold text-gray-900">
          Thinking & Reasoning Configuration
        </h2>
      </div>

      {/* Provider-specific thinking settings */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">
          Provider-Specific Settings
        </h3>

        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-center gap-2">
            <Info className="h-4 w-4 text-blue-500" />
            <span className="text-sm text-blue-700">
              Current provider: <strong>{getCurrentProvider()}</strong>
            </span>
          </div>
        </div>

        {isClaudeProvider() && (
          <div className="space-y-4">
            <h4 className="font-medium text-gray-700">
              Claude Extended Thinking
            </h4>

            {/* Enable/Disable Claude Thinking */}
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">
                  Extended Thinking
                </label>
                <p className="text-xs text-gray-500">
                  Enable Claude's transparent reasoning process
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={thinkingConfig.claude_extended_thinking}
                  onChange={(e) =>
                    handleBulkConfigUpdate({
                      claude_extended_thinking: e.target.checked,
                      // Include all Claude thinking settings in bulk update
                      claude_thinking_mode: thinkingConfig.claude_thinking_mode,
                      claude_thinking_budget_tokens:
                        thinkingConfig.claude_thinking_budget_tokens,
                      claude_show_thinking_process:
                        thinkingConfig.claude_show_thinking_process,
                      claude_adaptive_thinking_budget:
                        thinkingConfig.claude_adaptive_thinking_budget,
                      claude_max_thinking_budget:
                        thinkingConfig.claude_max_thinking_budget,
                    })
                  }
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>

            {thinkingConfig.claude_extended_thinking && (
              <>
                {/* Claude Thinking Mode */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Thinking Mode
                  </label>
                  <select
                    value={thinkingConfig.claude_thinking_mode}
                    onChange={(e) =>
                      handleBulkConfigUpdate({
                        claude_thinking_mode: e.target.value,
                        // Include all related Claude thinking settings in bulk update
                        claude_extended_thinking:
                          thinkingConfig.claude_extended_thinking,
                        claude_thinking_budget_tokens:
                          thinkingConfig.claude_thinking_budget_tokens,
                        claude_show_thinking_process:
                          thinkingConfig.claude_show_thinking_process,
                        claude_adaptive_thinking_budget:
                          thinkingConfig.claude_adaptive_thinking_budget,
                        claude_max_thinking_budget:
                          thinkingConfig.claude_max_thinking_budget,
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {CLAUDE_THINKING_MODES.map((mode) => (
                      <option key={mode.id} value={mode.id}>
                        {mode.name} - {mode.description}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Thinking Budget */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Thinking Budget:{" "}
                    {thinkingConfig.claude_thinking_budget_tokens} tokens
                  </label>
                  <input
                    type="range"
                    min="1024"
                    max={thinkingConfig.claude_max_thinking_budget}
                    step="1024"
                    value={thinkingConfig.claude_thinking_budget_tokens}
                    onChange={(e) =>
                      handleConfigChange(
                        "claude_thinking_budget_tokens",
                        parseInt(e.target.value),
                      )
                    }
                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                  />
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>1K</span>
                    <span>32K</span>
                    <span>64K</span>
                  </div>
                </div>

                {/* Show Thinking Process */}
                <div className="flex items-center justify-between">
                  <div>
                    <label className="text-sm font-medium text-gray-700">
                      Show Thinking Process
                    </label>
                    <p className="text-xs text-gray-500">
                      Display Claude's reasoning steps in responses
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={thinkingConfig.claude_show_thinking_process}
                      onChange={(e) =>
                        handleConfigChange(
                          "claude_show_thinking_process",
                          e.target.checked,
                        )
                      }
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                  </label>
                </div>

                {/* Adaptive Budget */}
                <div className="flex items-center justify-between">
                  <div>
                    <label className="text-sm font-medium text-gray-700">
                      Adaptive Budget
                    </label>
                    <p className="text-xs text-gray-500">
                      Automatically adjust thinking budget based on task
                      complexity
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={thinkingConfig.claude_adaptive_thinking_budget}
                      onChange={(e) =>
                        handleConfigChange(
                          "claude_adaptive_thinking_budget",
                          e.target.checked,
                        )
                      }
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                  </label>
                </div>
              </>
            )}
          </div>
        )}

        {isAzureOrOpenAI() && (
          <div className="space-y-4">
            <h4 className="font-medium text-gray-700">Reasoning Enhancement</h4>

            {/* Enable Reasoning */}
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">
                  Enable Reasoning
                </label>
                <p className="text-xs text-gray-500">
                  Use Azure Responses API reasoning features
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={thinkingConfig.enable_reasoning}
                  onChange={(e) =>
                    handleConfigChange("enable_reasoning", e.target.checked)
                  }
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>

            {thinkingConfig.enable_reasoning && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Reasoning Effort
                </label>
                <select
                  value={thinkingConfig.reasoning_effort}
                  onChange={(e) =>
                    handleConfigChange("reasoning_effort", e.target.value)
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="low">Low - Quick reasoning</option>
                  <option value="medium">Medium - Balanced reasoning</option>
                  <option value="high">High - Deep reasoning</option>
                </select>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Thinking Modes */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">
          Comprehensive Analysis Modes
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
          {THINKING_MODES.map((mode) => {
            const IconComponent = mode.icon;
            const isSelected = thinkingConfig.default_thinking_mode === mode.id;

            return (
              <div
                key={mode.id}
                className={`relative p-4 border-2 rounded-lg cursor-pointer transition-all hover:shadow-md ${
                  isSelected
                    ? `border-${mode.color}-500 bg-${mode.color}-50`
                    : "border-gray-200 bg-white hover:border-gray-300"
                }`}
                onClick={() =>
                  handleConfigChange("default_thinking_mode", mode.id)
                }
              >
                <div className="flex items-start gap-3">
                  <div className={`p-2 rounded-lg bg-${mode.color}-100`}>
                    <IconComponent
                      className={`h-5 w-5 text-${mode.color}-600`}
                    />
                  </div>
                  <div className="flex-1">
                    <h4 className="font-medium text-gray-900">{mode.name}</h4>
                    <p className="text-sm text-gray-600 mt-1">
                      {mode.description}
                    </p>
                    <p className="text-xs text-gray-500 mt-2">{mode.useCase}</p>
                  </div>
                </div>

                {/* Test button */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    testThinkingMode(mode.id);
                  }}
                  disabled={isTesting}
                  className={`absolute top-2 right-2 p-1 rounded text-${mode.color}-600 hover:bg-${mode.color}-100 disabled:opacity-50`}
                >
                  <Zap className="h-4 w-4" />
                </button>
              </div>
            );
          })}
        </div>

        {/* Thinking Depth */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Default Analysis Depth
          </label>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {THINKING_DEPTHS.map((depth) => (
              <button
                key={depth.id}
                onClick={() =>
                  handleConfigChange("default_thinking_depth", depth.id)
                }
                className={`p-3 text-left border rounded-lg transition-colors ${
                  thinkingConfig.default_thinking_depth === depth.id
                    ? "border-blue-500 bg-blue-50 text-blue-700"
                    : "border-gray-200 hover:border-gray-300"
                }`}
              >
                <div className="font-medium">{depth.name}</div>
                <div className="text-xs text-gray-500 mt-1">
                  {depth.description}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Tool Settings */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">
                Auto-select Thinking Mode
              </label>
              <p className="text-xs text-gray-500">
                Automatically choose the best thinking approach for each task
              </p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={thinkingConfig.auto_select_thinking_mode}
                onChange={(e) =>
                  handleConfigChange(
                    "auto_select_thinking_mode",
                    e.target.checked,
                  )
                }
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">
                Enable Documentation Fetching
              </label>
              <p className="text-xs text-gray-500">
                Allow AI to fetch and analyze external documentation
              </p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={thinkingConfig.enable_documentation_fetching}
                onChange={(e) =>
                  handleConfigChange(
                    "enable_documentation_fetching",
                    e.target.checked,
                  )
                }
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>
        </div>
      </div>

      {/* Test Results */}
      {testResult && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">
            Test Results
          </h3>

          {testResult.success ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-green-600">
                <CheckCircle className="h-5 w-5" />
                <span className="font-medium">Test successful</span>
              </div>
              <div className="bg-gray-50 p-4 rounded-lg">
                <pre className="text-sm text-gray-700 whitespace-pre-wrap overflow-auto max-h-64">
                  {JSON.stringify(testResult.result, null, 2)}
                </pre>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-red-600">
                <XCircle className="h-5 w-5" />
                <span className="font-medium">Test failed</span>
              </div>
              <div className="bg-red-50 p-4 rounded-lg">
                <p className="text-red-700">{testResult.error}</p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
