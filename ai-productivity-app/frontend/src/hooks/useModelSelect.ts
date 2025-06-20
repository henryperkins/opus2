// hooks/useModelSelection.ts
import { useState, useEffect, useCallback, useRef } from 'react';
import { configAPI } from '../api/config';
import { toast } from '../components/common/Toast';

interface ModelStats {
  requestsToday: number;
  estimatedCost: number;
  averageLatency: number;
  errorRate: number;
  lastUsed: Date;
}

interface ModelCapability {
  id: string;
  name: string;
  supported: boolean;
}

interface UseModelSelectionReturn {
  currentModel: string;
  currentProvider: string;
  setModel: (model: string) => Promise<boolean>;
  setProvider: (provider: string) => Promise<boolean>;
  modelStats: ModelStats | null;
  isLoading: boolean;
  error: string | null;
  testModel: (model: string) => Promise<boolean>;
  modelCapabilities: ModelCapability[];
  autoSelectModel: (taskType: string) => Promise<string>;
  modelHistory: string[];
}

// Task-based model recommendations
const taskModelMap: Record<string, string[]> = {
  'code-generation': ['gpt-4o', 'gpt-4-turbo'],
  'code-explanation': ['gpt-4o-mini', 'gpt-3.5-turbo'],
  'documentation': ['gpt-4o-mini', 'gpt-3.5-turbo'],
  'debugging': ['gpt-4o', 'gpt-4-turbo'],
  'testing': ['gpt-4o-mini', 'gpt-3.5-turbo'],
  'architecture': ['gpt-4o', 'gpt-4-turbo'],
  'quick-answer': ['gpt-3.5-turbo', 'gpt-4o-mini'],
  'complex-analysis': ['gpt-4o', 'gpt-4-turbo']
};

export function useModelSelection(): UseModelSelectionReturn {
  const [currentModel, setCurrentModel] = useState<string>('gpt-4o-mini');
  const [currentProvider, setCurrentProvider] = useState<string>('openai');
  const [modelStats, setModelStats] = useState<ModelStats | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [modelHistory, setModelHistory] = useState<string[]>([]);
  const [modelCapabilities, setModelCapabilities] = useState<ModelCapability[]>([]);

  const statsIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const fallbackChainRef = useRef<string[]>(['gpt-4o-mini', 'gpt-3.5-turbo']);

  // Load initial configuration
  useEffect(() => {
    loadConfiguration();
    loadModelStats();

    // Set up stats polling
    statsIntervalRef.current = setInterval(loadModelStats, 60000); // Every minute

    return () => {
      if (statsIntervalRef.current) {
        clearInterval(statsIntervalRef.current);
      }
    };
  }, []);

  const loadConfiguration = async () => {
    try {
      const config = await configAPI.getConfig();
      if (config.current) {
        setCurrentModel(config.current.chat_model);
        setCurrentProvider(config.current.provider);
      }

      // Load model history from localStorage
      const history = localStorage.getItem('model_history');
      if (history) {
        setModelHistory(JSON.parse(history).slice(0, 10));
      }
    } catch (err) {
      console.error('Failed to load model configuration:', err);
      setError('Failed to load configuration');
    }
  };

  const loadModelStats = async () => {
    try {
      const stats = await configAPI.getModelStats(currentModel);
      setModelStats(stats);
    } catch (err) {
      console.error('Failed to load model stats:', err);
    }
  };

  const setModel = useCallback(async (model: string): Promise<boolean> => {
    if (model === currentModel) return true;

    setIsLoading(true);
    setError(null);

    try {
      // Test the model first
      const isValid = await testModel(model);
      if (!isValid) {
        throw new Error('Model validation failed');
      }

      // Update configuration
      await configAPI.updateModelConfig({
        provider: currentProvider,
        chat_model: model
      });

      setCurrentModel(model);

      // Update history
      const newHistory = [model, ...modelHistory.filter(m => m !== model)].slice(0, 10);
      setModelHistory(newHistory);
      localStorage.setItem('model_history', JSON.stringify(newHistory));

      toast.success(`Switched to ${model}`);

      // Reload stats for new model
      loadModelStats();

      return true;
    } catch (err: any) {
      const errorMessage = err.message || 'Failed to switch model';
      setError(errorMessage);
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
    } finally {
      setIsLoading(false);
    }
  }, [currentModel, currentProvider, modelHistory]);

  const setProvider = useCallback(async (provider: string): Promise<boolean> => {
    if (provider === currentProvider) return true;

    setIsLoading(true);
    setError(null);

    try {
      // Get available models for the provider
      const config = await configAPI.getConfig();
      const availableModels = config.providers[provider]?.chat_models || [];

      if (availableModels.length === 0) {
        throw new Error('No models available for this provider');
      }

      // Select the first available model
      const defaultModel = availableModels[0];

      // Update configuration
      await configAPI.updateModelConfig({
        provider,
        chat_model: defaultModel
      });

      setCurrentProvider(provider);
      setCurrentModel(defaultModel);

      toast.success(`Switched to ${provider}`);

      return true;
    } catch (err: any) {
      const errorMessage = err.message || 'Failed to switch provider';
      setError(errorMessage);
      toast.error(errorMessage);
      return false;
    } finally {
      setIsLoading(false);
    }
  }, [currentProvider]);

  const testModel = useCallback(async (model: string): Promise<boolean> => {
    try {
      const result = await configAPI.testModelConfig({
        provider: currentProvider,
        chat_model: model
      });

      return result.success;
    } catch (err) {
      console.error('Model test failed:', err);
      return false;
    }
  }, [currentProvider]);

  const autoSelectModel = useCallback(async (taskType: string): Promise<string> => {
    // Get recommended models for the task
    const recommendations = taskModelMap[taskType] || taskModelMap['quick-answer'];

    // Check model availability and cost
    try {
      const config = await configAPI.getConfig();
      const availableModels = config.providers[currentProvider]?.chat_models || [];

      // Find the first recommended model that's available
      for (const model of recommendations) {
        if (availableModels.includes(model)) {
          const success = await setModel(model);
          if (success) {
            toast.info(`Auto-selected ${model} for ${taskType}`);
            return model;
          }
        }
      }

      // Fallback to current model
      return currentModel;
    } catch (err) {
      console.error('Auto-selection failed:', err);
      return currentModel;
    }
  }, [currentProvider, currentModel, setModel]);

  // Detect model capabilities
  useEffect(() => {
    const capabilities: ModelCapability[] = [
      {
        id: 'function-calling',
        name: 'Function Calling',
        supported: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'].includes(currentModel)
      },
      {
        id: 'json-mode',
        name: 'JSON Mode',
        supported: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'].includes(currentModel)
      },
      {
        id: 'vision',
        name: 'Vision',
        supported: ['gpt-4o'].includes(currentModel)
      },
      {
        id: 'long-context',
        name: 'Long Context (128k)',
        supported: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'].includes(currentModel)
      }
    ];

    setModelCapabilities(capabilities);
  }, [currentModel]);

  return {
    currentModel,
    currentProvider,
    setModel,
    setProvider,
    modelStats,
    isLoading,
    error,
    testModel,
    modelCapabilities,
    autoSelectModel,
    modelHistory
  };
}

// Hook for managing model performance tracking
export function useModelPerformance(model: string) {
  const [metrics, setMetrics] = useState({
    requestCount: 0,
    totalLatency: 0,
    errorCount: 0,
    tokenUsage: {
      input: 0,
      output: 0
    }
  });

  const trackRequest = useCallback((latency: number, tokens: { input: number; output: number }, error?: boolean) => {
    setMetrics(prev => ({
      requestCount: prev.requestCount + 1,
      totalLatency: prev.totalLatency + latency,
      errorCount: prev.errorCount + (error ? 1 : 0),
      tokenUsage: {
        input: prev.tokenUsage.input + tokens.input,
        output: prev.tokenUsage.output + tokens.output
      }
    }));

    // Persist to localStorage for stats
    const key = `model_metrics_${model}_${new Date().toDateString()}`;
    const stored = localStorage.getItem(key);
    const existing = stored ? JSON.parse(stored) : { requests: 0, latency: 0, errors: 0, tokens: { input: 0, output: 0 } };

    const updated = {
      requests: existing.requests + 1,
      latency: existing.latency + latency,
      errors: existing.errors + (error ? 1 : 0),
      tokens: {
        input: existing.tokens.input + tokens.input,
        output: existing.tokens.output + tokens.output
      }
    };

    localStorage.setItem(key, JSON.stringify(updated));
  }, [model]);

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
      tokenUsage: { input: 0, output: 0 }
    });
  }, []);

  return {
    metrics,
    trackRequest,
    getAverageLatency,
    getErrorRate,
    reset
  };
}
