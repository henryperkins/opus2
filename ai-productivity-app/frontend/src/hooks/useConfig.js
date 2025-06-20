// hooks/useConfig.js
import { useState, useEffect, useCallback } from 'react';
import { configAPI } from '../api/config';

// Factory functions for creating config objects
export const createConfigData = (data = {}) => ({
  providers: data.providers || {},
  current: {
    provider: data.current?.provider || 'openai',
    chat_model: data.current?.chat_model || 'gpt-4o-mini'
  }
});

export function useConfig() {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchConfig = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await configAPI.getConfig();
      setConfig(data);
    } catch (err) {
      setError(err);
      console.error('Failed to fetch config:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const updateConfig = useCallback(async (updates) => {
    try {
      await configAPI.updateModelConfig({
        provider: updates.provider || config?.current.provider || 'openai',
        chat_model: updates.chat_model || config?.current.chat_model || 'gpt-4o-mini'
      });

      // Refetch to get updated config
      await fetchConfig();
    } catch (err) {
      setError(err);
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
export function useAvailableModels(provider) {
  const { config } = useConfig();
  const [models, setModels] = useState([]);

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

  const isFeatureAvailable = useCallback((feature) => {
    if (!config) return false;

    const provider = config.current.provider;
    const features = config.providers[provider]?.features || {};

    return features[feature] === true;
  }, [config]);

  const getAvailableFeatures = useCallback(() => {
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