// hooks/useConfig.js
import { useState, useEffect, useCallback, useRef } from 'react';
import { configAPI } from '../api/config';
import { useWebSocketChannel } from './useWebSocketChannel';
import { toast } from 'react-hot-toast';

// Factory functions for creating config objects
export const createConfigData = (data = {}) => ({
  providers: data.providers || {},
  current: {
    provider: data.current?.provider || 'openai',
    chat_model: data.current?.chat_model || 'gpt-4o-mini',
    useResponsesApi: data.current?.useResponsesApi ?? false,
  }
});

export function useConfig() {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const lastUpdateRef = useRef(null);

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
      lastUpdateRef.current = Date.now();
      await configAPI.updateModelConfig({
        provider: updates.provider || config?.current.provider || 'openai',
        chat_model: updates.chat_model || config?.current.chat_model || 'gpt-4o-mini',
        useResponsesApi: updates.useResponsesApi ?? config?.current.useResponsesApi ?? false,
        temperature: updates.temperature,
        maxTokens: updates.maxTokens,
        topP: updates.topP,
        frequencyPenalty: updates.frequencyPenalty,
        presencePenalty: updates.presencePenalty,
        systemPrompt: updates.systemPrompt,
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

  // Global config update listener for WebSocket integration
  useEffect(() => {
    const handleConfigUpdate = (event) => {
      handleConfigUpdateMessage(event.detail, { _setConfig: setConfig, _lastUpdateRef: lastUpdateRef });
    };
    
    window.addEventListener('configUpdate', handleConfigUpdate);
    return () => window.removeEventListener('configUpdate', handleConfigUpdate);
  }, []);

  return {
    config,
    loading,
    error,
    refetch: fetchConfig,
    updateConfig,
    _lastUpdateRef: lastUpdateRef, // For WebSocket integration
    _setConfig: setConfig, // For WebSocket integration
  };
}

// Global config update handler for WebSocket integration
// This will be called from useChat when a config_update message is received
export function handleConfigUpdateMessage(data, configHook) {
  if (!configHook || typeof configHook._setConfig !== 'function') {
    console.warn('Invalid config hook passed to handleConfigUpdateMessage');
    return;
  }

  try {
    // Avoid updating if this was our own update (prevent feedback loop)
    const timeSinceLastUpdate = Date.now() - (configHook._lastUpdateRef?.current || 0);
    if (timeSinceLastUpdate < 2000) {
      console.log('Ignoring config update - recently updated by this client');
      return;
    }

    console.log('Received config update via WebSocket:', data.config);
    configHook._setConfig(data.config);
    
    // Show notification unless this was a requested update
    if (!data.requested) {
      toast.success('Configuration updated', {
        duration: 3000,
        icon: '🔄',
      });
    }
  } catch (err) {
    console.error('Failed to handle WebSocket config update:', err);
  }
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