
// frontend/src/contexts/AIConfigContext.jsx
import React, { createContext, useContext, useReducer, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';

// Use the existing API client for proper authentication handling
// The client is exported as the default export, so import it accordingly.
import apiClient from '../api/client';

// API client
const API_BASE = '/api/v1/ai-config';

const aiConfigAPI = {
  getConfig: async () => {
    return await apiClient.get(API_BASE);
  },
  
  // Use HTTP PATCH so we only update the provided keys instead of replacing
  // the entire configuration object.  This prevents un-sent values from
  // being overwritten with defaults on the server side.
  updateConfig: async (updates) => {
    return await apiClient.patch(API_BASE, updates);
  },
  
  testConfig: async (config = null) => {
    return await apiClient.post(`${API_BASE}/test`, config);
  },
  
  getModels: async (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const url = queryString ? `${API_BASE}/models?${queryString}` : `${API_BASE}/models`;
    return await apiClient.get(url);
  },
  
  getModelInfo: async (modelId) => {
    return await apiClient.get(`${API_BASE}/models/${modelId}`);
  },
  
  validateConfig: async (config) => {
    return await apiClient.post(`${API_BASE}/validate`, config);
  },
  
  getPresets: async () => {
    return await apiClient.get(`${API_BASE}/presets`);
  }
};

// Context
const AIConfigContext = createContext(null);

// Action types
const ACTIONS = {
  SET_CONFIG: 'SET_CONFIG',
  UPDATE_CONFIG: 'UPDATE_CONFIG',
  SET_MODELS: 'SET_MODELS',
  SET_LOADING: 'SET_LOADING',
  SET_ERROR: 'SET_ERROR',
  SET_TEST_RESULT: 'SET_TEST_RESULT',
  ADD_TO_HISTORY: 'ADD_TO_HISTORY',
  UPDATE_PERFORMANCE: 'UPDATE_PERFORMANCE',
  RESET_ERROR: 'RESET_ERROR',
  SET_CONFLICT: 'SET_CONFLICT',
  RESOLVE_CONFLICT: 'RESOLVE_CONFLICT'
};

// Initial state
const initialState = {
  // Current configuration
  config: null,
  
  // Available models and providers
  models: [],
  providers: {},
  
  // UI state
  loading: false,
  error: null,
  testResult: null,
  
  // Model performance tracking
  modelStats: new Map(),
  modelHistory: [],
  
  // Conflict resolution
  conflictState: null,
  
  // Metadata
  lastUpdated: null
};

// Reducer
function aiConfigReducer(state, action) {
  switch (action.type) {
    case ACTIONS.SET_CONFIG:
      return {
        ...state,
        config: action.payload.current,
        models: action.payload.available_models || state.models,
        providers: action.payload.providers || state.providers,
        lastUpdated: action.payload.last_updated,
        error: null
      };
      
    case ACTIONS.UPDATE_CONFIG:
      return {
        ...state,
        config: { ...state.config, ...action.payload },
        error: null
      };
      
    case ACTIONS.SET_MODELS:
      return {
        ...state,
        models: action.payload
      };
      
    case ACTIONS.SET_LOADING:
      return {
        ...state,
        loading: action.payload
      };
      
    case ACTIONS.SET_ERROR:
      return {
        ...state,
        error: action.payload,
        loading: false
      };
      
    case ACTIONS.SET_TEST_RESULT:
      return {
        ...state,
        testResult: action.payload
      };
      
    case ACTIONS.ADD_TO_HISTORY:
      return {
        ...state,
        modelHistory: [
          {
            modelId: action.payload.modelId,
            provider: action.payload.provider,
            timestamp: new Date().toISOString(),
            context: action.payload.context || 'manual_selection'
          },
          ...state.modelHistory.slice(0, 49) // Keep last 50 entries
        ]
      };
      
    case ACTIONS.UPDATE_PERFORMANCE: {
      const newStats = new Map(state.modelStats);
      newStats.set(action.payload.modelId, {
        ...newStats.get(action.payload.modelId),
        ...action.payload.stats
      });
      return {
        ...state,
        modelStats: newStats
      };
    }
      
    case ACTIONS.RESET_ERROR:
      return {
        ...state,
        error: null
      };
      
    case ACTIONS.SET_CONFLICT:
      return {
        ...state,
        conflictState: action.payload
      };
      
    case ACTIONS.RESOLVE_CONFLICT:
      return {
        ...state,
        conflictState: null,
        config: action.payload.resolved_config || state.config
      };
      
    default:
      return state;
  }
}

// Provider component
export function AIConfigProvider({ children }) {
  const [state, dispatch] = useReducer(aiConfigReducer, initialState);
  const queryClient = useQueryClient();
  
  // Query for fetching configuration
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['ai-config'],
    queryFn: aiConfigAPI.getConfig,
    staleTime: 30000, // 30 seconds
    cacheTime: 5 * 60 * 1000, // 5 minutes
    onSuccess: (data) => {
      dispatch({ type: ACTIONS.SET_CONFIG, payload: data });
    },
    onError: (error) => {
      dispatch({ type: ACTIONS.SET_ERROR, payload: error.message });
      console.error('Failed to load AI configuration:', error);
    }
  });
  
  // Mutation for updating configuration
  const updateMutation = useMutation({
    mutationFn: aiConfigAPI.updateConfig,
    onMutate: async (updates) => {
      // Cancel outgoing queries
      await queryClient.cancelQueries(['ai-config']);
      
      // Optimistic update
      dispatch({ type: ACTIONS.UPDATE_CONFIG, payload: updates });
      
      // Return context for rollback
      return { previousConfig: state.config };
    },
    onError: (error, updates, context) => {
      // Rollback on error
      if (context?.previousConfig) {
        dispatch({ 
          type: ACTIONS.SET_CONFIG, 
          payload: { current: context.previousConfig } 
        });
      }
      dispatch({ type: ACTIONS.SET_ERROR, payload: error.message });
      toast.error('Failed to update configuration');
    },
    onSuccess: (data) => {
      dispatch({ type: ACTIONS.UPDATE_CONFIG, payload: data });
      queryClient.invalidateQueries(['ai-config']);
      toast.success('Configuration updated successfully');
    }
  });
  
  // Update configuration
  const updateConfig = useCallback(async (updates) => {
    return updateMutation.mutateAsync(updates);
  }, [updateMutation]);
  
  // Test configuration
  const testConfig = useCallback(async (config = null) => {
    dispatch({ type: ACTIONS.SET_TEST_RESULT, payload: null });
    
    try {
      const result = await aiConfigAPI.testConfig(config);
      dispatch({ type: ACTIONS.SET_TEST_RESULT, payload: result });
      
      if (result.success) {
        toast.success('Configuration test successful');
      } else {
        toast.error(result.message || 'Configuration test failed');
      }
      
      return result;
    } catch (error) {
      const errorResult = {
        success: false,
        message: error.message,
        error: error.response?.data?.detail || 'Test failed'
      };
      dispatch({ type: ACTIONS.SET_TEST_RESULT, payload: errorResult });
      toast.error('Configuration test failed');
      return errorResult;
    }
  }, []);
  
  // Get model info
  const getModelInfo = useCallback(async (modelId) => {
    try {
      return await aiConfigAPI.getModelInfo(modelId);
    } catch (error) {
      console.error(`Failed to get model info for ${modelId}:`, error);
      return null;
    }
  }, []);
  
  // Apply preset
  const applyPreset = useCallback(async (presetId) => {
    try {
      const presets = await aiConfigAPI.getPresets();
      const preset = presets.find(p => p.id === presetId);
      
      if (!preset) {
        throw new Error(`Preset '${presetId}' not found`);
      }
      
      await updateConfig(preset.config);
      toast.success(`Applied '${preset.name}' preset`);
      
    } catch (error) {
      console.error('Failed to apply preset:', error);
      toast.error('Failed to apply preset');
    }
  }, [updateConfig]);
  
  // Enhanced WebSocket integration
  useEffect(() => {
    const handleWebSocketMessage = (event) => {
      const message = JSON.parse(event.data);
      
      switch (message.type) {
        case 'config_update':
        case 'config_batch_update':
          dispatch({ type: ACTIONS.SET_CONFIG, payload: message.data });
          queryClient.invalidateQueries(['ai-config']);
          toast.success('Configuration updated');
          break;
          
        case 'config_conflict_detected':
          dispatch({ type: ACTIONS.SET_CONFLICT, payload: message.data });
          toast.warning('Configuration conflict detected');
          break;
          
        case 'config_conflict_resolved':
          dispatch({ type: ACTIONS.RESOLVE_CONFLICT, payload: message.data });
          toast.success('Configuration conflict resolved');
          break;
          
        default:
          // Handle other WebSocket messages
          break;
      }
    };
    
    // Create WebSocket connection
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/config`;
    
    let ws = null;
    
    try {
      ws = new WebSocket(wsUrl);
      
      ws.onmessage = handleWebSocketMessage;
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
      
      ws.onclose = () => {
        console.log('WebSocket connection closed');
      };
      
      return () => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.close();
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
    }
  }, [queryClient]);
  
  // Enhanced methods
  const setModel = useCallback(async (modelId, options = {}) => {
    try {
      dispatch({ type: ACTIONS.SET_LOADING, payload: true });
      
      // Find model info
      const model = state.models.find(m => m.modelId === modelId);
      if (!model) {
        throw new Error(`Model '${modelId}' not found`);
      }
      
      // Add to history
      dispatch({
        type: ACTIONS.ADD_TO_HISTORY,
        payload: {
          modelId,
          provider: model.provider,
          context: options.context || 'manual_selection'
        }
      });
      
      // Update configuration
      await updateConfig({
        model_id: modelId,
        provider: model.provider,
        ...options.config
      });
      
      return true;
    } catch (error) {
      console.error('Failed to set model:', error);
      dispatch({ type: ACTIONS.SET_ERROR, payload: error.message });
      return false;
    } finally {
      dispatch({ type: ACTIONS.SET_LOADING, payload: false });
    }
  }, [state.models, updateConfig]);
  
  const trackPerformance = useCallback((modelId, stats) => {
    dispatch({
      type: ACTIONS.UPDATE_PERFORMANCE,
      payload: {
        modelId,
        stats: {
          ...stats,
          timestamp: new Date().toISOString()
        }
      }
    });
  }, []);
  
  const resetError = useCallback(() => {
    dispatch({ type: ACTIONS.RESET_ERROR });
  }, []);
  
  const resolveConflict = useCallback(async (strategy, proposedConfig) => {
    try {
      const result = await apiClient.post(`${API_BASE}/resolve-conflict`, {
        proposed_config: proposedConfig,
        conflict_strategy: strategy
      });
      
      dispatch({ type: ACTIONS.RESOLVE_CONFLICT, payload: result.data });
      return result.data;
    } catch (error) {
      console.error('Failed to resolve conflict:', error);
      throw error;
    }
  }, []);
  
  const batchUpdate = useCallback(async (updates) => {
    try {
      const result = await apiClient.put(`${API_BASE}/batch`, updates);
      dispatch({ type: ACTIONS.SET_CONFIG, payload: { current: result.data } });
      return result.data;
    } catch (error) {
      console.error('Failed to batch update:', error);
      throw error;
    }
  }, []);
  
  // Context value
  const contextValue = {
    // State
    config: state.config,
    models: state.models,
    providers: state.providers,
    loading: isLoading || state.loading,
    error: error || state.error,
    testResult: state.testResult,
    lastUpdated: state.lastUpdated,
    modelStats: state.modelStats,
    modelHistory: state.modelHistory,
    conflictState: state.conflictState,
    
    // Actions
    updateConfig,
    testConfig,
    getModelInfo,
    applyPreset,
    refetch,
    setModel,
    trackPerformance,
    resetError,
    resolveConflict,
    batchUpdate,
    
    // Computed values
    currentModel: state.config?.model_id,
    currentProvider: state.config?.provider,
    isReasoningEnabled: state.config?.enable_reasoning || false,
    isThinkingEnabled: state.config?.claude_extended_thinking || false
  };
  
  return (
    <AIConfigContext.Provider value={contextValue}>
      {children}
    </AIConfigContext.Provider>
  );
}

// Hook to use AI configuration
export function useAIConfig() {
  const context = useContext(AIConfigContext);
  
  if (!context) {
    throw new Error('useAIConfig must be used within AIConfigProvider');
  }
  
  return context;
}

// Convenience hooks for specific features

export function useModelSelection() {
  const { config, models, updateConfig, currentModel, currentProvider } = useAIConfig();
  
  const selectModel = useCallback(async (modelId) => {
    // Find model info
    const model = models.find(m => m.model_id === modelId);
    if (!model) {
      throw new Error(`Model '${modelId}' not found`);
    }
    
    // Update configuration
    await updateConfig({
      model_id: modelId,
      provider: model.provider
    });
  }, [models, updateConfig]);
  
  const selectProvider = useCallback(async (provider) => {
    // Find first available model for provider
    const model = models.find(m => m.provider === provider);
    if (!model) {
      throw new Error(`No models available for provider '${provider}'`);
    }
    
    await updateConfig({
      provider: provider,
      model_id: model.model_id
    });
  }, [models, updateConfig]);
  
  return {
    currentModel,
    currentProvider,
    availableModels: models,
    selectModel,
    selectProvider
  };
}

export function useGenerationParams() {
  const { config, updateConfig } = useAIConfig();
  
  const updateParams = useCallback(async (params) => {
    const allowedParams = [
      'temperature', 'max_tokens', 'top_p', 
      'frequency_penalty', 'presence_penalty',
      'stop_sequences', 'seed'
    ];
    
    // Filter to allowed parameters
    const filtered = Object.keys(params)
      .filter(key => allowedParams.includes(key))
      .reduce((obj, key) => {
        obj[key] = params[key];
        return obj;
      }, {});
    
    if (Object.keys(filtered).length > 0) {
      await updateConfig(filtered);
    }
  }, [updateConfig]);
  
  return {
    temperature: config?.temperature,
    maxTokens: config?.max_tokens,
    topP: config?.top_p,
    frequencyPenalty: config?.frequency_penalty,
    presencePenalty: config?.presence_penalty,
    updateParams
  };
}

export function useReasoningConfig() {
  const { config, updateConfig, currentProvider } = useAIConfig();
  
  const isClaudeProvider = currentProvider === 'anthropic';
  const isAzureOrOpenAI = ['azure', 'openai'].includes(currentProvider);
  
  const updateReasoningConfig = useCallback(async (updates) => {
    const reasoningParams = [
      'enable_reasoning', 'reasoning_effort',
      'claude_extended_thinking', 'claude_thinking_mode',
      'claude_thinking_budget_tokens', 'claude_show_thinking_process',
      'claude_adaptive_thinking_budget', 'default_thinking_mode',
      'default_thinking_depth'
    ];
    
    // Filter to reasoning parameters
    const filtered = Object.keys(updates)
      .filter(key => reasoningParams.includes(key))
      .reduce((obj, key) => {
        obj[key] = updates[key];
        return obj;
      }, {});
    
    if (Object.keys(filtered).length > 0) {
      await updateConfig(filtered);
    }
  }, [updateConfig]);
  
  return {
    // General reasoning
    enableReasoning: config?.enable_reasoning,
    reasoningEffort: config?.reasoning_effort,
    
    // Claude thinking
    claudeExtendedThinking: config?.claude_extended_thinking,
    claudeThinkingMode: config?.claude_thinking_mode,
    claudeThinkingBudget: config?.claude_thinking_budget_tokens,
    
    // Provider flags
    isClaudeProvider,
    isAzureOrOpenAI,
    supportsReasoning: isAzureOrOpenAI && config?.use_responses_api,
    supportsThinking: isClaudeProvider,
    
    // Update function
    updateReasoningConfig
  };
}

// Export everything
export default AIConfigContext;
