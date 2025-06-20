// hooks/useConfig.ts
import { useState, useEffect, useCallback } from 'react';
import { configAPI } from '../api/config';

interface ConfigData {
  providers: {
    [key: string]: {
      chat_models: string[];
      embedding_models?: string[];
      features?: Record<string, boolean>;
      api_versions?: string[];
    };
  };
  current: {
    provider: string;
    chat_model: string;
  };
}

interface UseConfigReturn {
  config: ConfigData | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
  updateConfig: (updates: Partial<ConfigData['current']>) => Promise<void>;
}

export function useConfig(): UseConfigReturn {
  const [config, setConfig] = useState<ConfigData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchConfig = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await configAPI.getConfig();
      setConfig(data);
    } catch (err) {
      setError(err as Error);
      console.error('Failed to fetch config:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const updateConfig = useCallback(async (updates: Partial<ConfigData['current']>) => {
    try {
      await configAPI.updateModelConfig({
        provider: updates.provider || config?.current.provider || 'openai',
        chat_model: updates.chat_model || config?.current.chat_model || 'gpt-4o-mini'
      });

      // Refetch to get updated config
      await fetchConfig();
    } catch (err) {
      setError(err as Error);
      throw err;
    }
  }, [config, fetchConfig]);

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  return {
    config,
    loading,
    error,
    refetch: fetchConfig,
    updateConfig
  };
}

// Hook for managing available models
export function useAvailableModels(provider?: string) {
  const { config } = useConfig();
  const [models, setModels] = useState<string[]>([]);

  useEffect(() => {
    if (config && provider) {
      const providerModels = config.providers[provider]?.chat_models || [];
      setModels(providerModels);
    }
  }, [config, provider]);

  return models;
}

// Hook for checking feature availability
export function useFeatureAvailability() {
  const { config } = useConfig();

  const isFeatureAvailable = useCallback((feature: string): boolean => {
    if (!config) return false;

    const provider = config.current.provider;
    const features = config.providers[provider]?.features || {};

    return features[feature] === true;
  }, [config]);

  const getAvailableFeatures = useCallback((): string[] => {
    if (!config) return [];

    const provider = config.current.provider;
    const features = config.providers[provider]?.features || {};

    return Object.entries(features)
      .filter(([_, enabled]) => enabled)
      .map(([feature]) => feature);
  }, [config]);

  return {
    isFeatureAvailable,
    getAvailableFeatures
  };
}
