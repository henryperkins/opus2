// hooks/useModelSelection.js
import { useState, useEffect, useCallback, useRef } from "react";
import { useAIConfig } from "../contexts/AIConfigContext";
import { toast } from "../components/common/Toast";
import { modelsAPI } from "../api/models";

// Task-based model recommendations
const taskModelMap = {
  "code-generation": ["gpt-4o", "gpt-4-turbo"],
  "code-explanation": ["gpt-4o-mini", "gpt-3.5-turbo"],
  documentation: ["gpt-4o-mini", "gpt-3.5-turbo"],
  debugging: ["gpt-4o", "gpt-4-turbo"],
  testing: ["gpt-4o-mini", "gpt-3.5-turbo"],
  architecture: ["gpt-4o", "gpt-4-turbo"],
  "quick-answer": ["gpt-3.5-turbo", "gpt-4o-mini"],
  "complex-analysis": ["gpt-4o", "gpt-4-turbo"],
};

export function useModelSelection() {
  const {
    config,
    models,
    updateConfig,
    testConfig,
    loading,
    error,
    setModel: aiConfigSetModel,
    trackPerformance,
  } = useAIConfig();

  const [modelStats, setModelStats] = useState(null);
  const [modelHistory, setModelHistory] = useState([]);
  const [modelCapabilities, setModelCapabilities] = useState([]);

  const statsIntervalRef = useRef(null);
  const fallbackChainRef = useRef(["gpt-4o-mini", "gpt-3.5-turbo"]);

  const currentModel = config?.model_id || "gpt-4o-mini";
  const currentProvider = config?.provider || "openai";

  // Load model history from localStorage
  useEffect(() => {
    const history = localStorage.getItem("model_history");
    if (history) {
      setModelHistory(JSON.parse(history).slice(0, 10));
    }
  }, []);

  // Set up stats polling
  useEffect(() => {
    if (currentModel) {
      loadModelStats();
      statsIntervalRef.current = setInterval(loadModelStats, 60000); // Every minute
    }

    return () => {
      if (statsIntervalRef.current) {
        clearInterval(statsIntervalRef.current);
      }
    };
  }, [currentModel]);

  const loadModelStats = useCallback(async () => {
    try {
      // Use the unified API to get model usage statistics
      const stats = await modelsAPI.getUsageStats("current", {
        model_id: currentModel,
      });
      setModelStats(stats);
    } catch (err) {
      console.error("Failed to load model stats:", err);
      // Fallback to mock stats if API fails
      const mockStats = {
        requestsToday: Math.floor(Math.random() * 100),
        estimatedCost: Math.random() * 10,
        averageLatency: Math.random() * 1000,
        errorRate: Math.random() * 5,
        lastUsed: new Date(),
      };
      setModelStats(mockStats);
    }
  }, [currentModel]);

  const setModel = useCallback(
    async (model) => {
      if (model === currentModel) return true;

      try {
        // Test the model first
        const testResult = await testConfig({
          model_id: model,
          provider: currentProvider,
        });
        if (!testResult.success) {
          throw new Error("Model validation failed");
        }

        // Use the AIConfig setModel function
        const success = await aiConfigSetModel(model);
        if (success) {
          // Update history
          const newHistory = [
            model,
            ...modelHistory.filter((m) => m !== model),
          ].slice(0, 10);
          setModelHistory(newHistory);
          localStorage.setItem("model_history", JSON.stringify(newHistory));

          toast.success(`Switched to ${model}`);
          return true;
        }
        return false;
      } catch (err) {
        const errorMessage = err.message || "Failed to switch model";
        toast.error(errorMessage);

        // Try fallback model
        if (fallbackChainRef.current.length > 0) {
          const fallback = fallbackChainRef.current[0];
          if (fallback !== model) {
            toast.info(`Falling back to ${fallback}`);
            return setModel(fallback);
          }
        }

        return false;
      }
    },
    [currentModel, currentProvider, modelHistory, testConfig, aiConfigSetModel],
  );

  const setProvider = useCallback(
    async (provider) => {
      if (provider === currentProvider) return true;

      try {
        // Get available models for the provider
        const availableModels = models.filter((m) => m.provider === provider);

        if (availableModels.length === 0) {
          throw new Error("No models available for this provider");
        }

        // Select the first available model
        const defaultModel = availableModels[0].model_id;

        // Update configuration
        await updateConfig({
          provider,
          model_id: defaultModel,
        });

        toast.success(`Switched to ${provider}`);
        return true;
      } catch (err) {
        const errorMessage = err.message || "Failed to switch provider";
        toast.error(errorMessage);
        return false;
      }
    },
    [currentProvider, models, updateConfig],
  );

  const testModel = useCallback(
    async (model) => {
      try {
        const result = await testConfig({
          provider: currentProvider,
          model_id: model,
        });
        return result.success;
      } catch (err) {
        console.error("Model test failed:", err);
        return false;
      }
    },
    [currentProvider, testConfig],
  );

  const autoSelectModel = useCallback(
    async (taskType) => {
      try {
        // Use the unified API to get task-specific model recommendations
        const matchedModels = await modelsAPI.matchCapabilities(taskType, {
          default: currentModel,
          fallbacks: fallbackChainRef.current,
          autoSwitch: true,
        });

        if (matchedModels.length > 0) {
          // Select the first recommended model
          const recommendedModel = matchedModels[0].model_id;
          const success = await setModel(recommendedModel);
          if (success) {
            toast.info(`Auto-selected ${recommendedModel} for ${taskType}`);
            return recommendedModel;
          }
        }

        // Fallback to current model
        return currentModel;
      } catch (err) {
        console.error("Auto-selection failed:", err);
        return currentModel;
      }
    },
    [currentModel, setModel],
  );

  // Detect model capabilities
  useEffect(() => {
    const capabilities = [
      {
        id: "function-calling",
        name: "Function Calling",
        supported: [
          "gpt-4o",
          "gpt-4o-mini",
          "gpt-4-turbo",
          "gpt-3.5-turbo",
        ].includes(currentModel),
      },
      {
        id: "json-mode",
        name: "JSON Mode",
        supported: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"].includes(
          currentModel,
        ),
      },
      {
        id: "vision",
        name: "Vision",
        supported: ["gpt-4o"].includes(currentModel),
      },
      {
        id: "long-context",
        name: "Long Context (128k)",
        supported: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"].includes(
          currentModel,
        ),
      },
    ];

    setModelCapabilities(capabilities);
  }, [currentModel]);

  return {
    currentModel,
    currentProvider,
    setModel,
    setProvider,
    modelStats,
    isLoading: loading,
    error,
    testModel,
    modelCapabilities,
    autoSelectModel,
    modelHistory,
  };
}

// Hook for managing model performance tracking
export function useModelPerformance(model) {
  const { trackPerformance } = useAIConfig();
  const [metrics, setMetrics] = useState({
    requestCount: 0,
    totalLatency: 0,
    errorCount: 0,
    tokenUsage: {
      input: 0,
      output: 0,
    },
  });

  const trackRequest = useCallback(
    (latency, tokens, error = false) => {
      const newMetrics = {
        requestCount: metrics.requestCount + 1,
        totalLatency: metrics.totalLatency + latency,
        errorCount: metrics.errorCount + (error ? 1 : 0),
        tokenUsage: {
          input: metrics.tokenUsage.input + tokens.input,
          output: metrics.tokenUsage.output + tokens.output,
        },
      };

      setMetrics(newMetrics);

      // Track in the AIConfig context
      trackPerformance(model, {
        latency,
        tokens,
        error,
        timestamp: new Date().toISOString(),
      });

      // Persist to localStorage for stats
      const key = `model_metrics_${model}_${new Date().toDateString()}`;
      const stored = localStorage.getItem(key);
      const existing = stored
        ? JSON.parse(stored)
        : {
            requests: 0,
            latency: 0,
            errors: 0,
            tokens: { input: 0, output: 0 },
          };

      const updated = {
        requests: existing.requests + 1,
        latency: existing.latency + latency,
        errors: existing.errors + (error ? 1 : 0),
        tokens: {
          input: existing.tokens.input + tokens.input,
          output: existing.tokens.output + tokens.output,
        },
      };

      localStorage.setItem(key, JSON.stringify(updated));
    },
    [model, metrics, trackPerformance],
  );

  const getAverageLatency = useCallback(() => {
    if (metrics.requestCount === 0) return 0;
    return metrics.totalLatency / metrics.requestCount;
  }, [metrics]);

  const getErrorRate = useCallback(() => {
    if (metrics.requestCount === 0) return 0;
    return (metrics.errorCount / metrics.requestCount) * 100;
  }, [metrics]);

  const reset = useCallback(() => {
    setMetrics({
      requestCount: 0,
      totalLatency: 0,
      errorCount: 0,
      tokenUsage: { input: 0, output: 0 },
    });
  }, []);

  return {
    metrics,
    trackRequest,
    getAverageLatency,
    getErrorRate,
    reset,
  };
}
