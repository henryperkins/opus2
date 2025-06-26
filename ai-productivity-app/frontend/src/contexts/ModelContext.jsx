// contexts/ModelContext.jsx
import { createContext, useContext, useReducer, useEffect, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import PropTypes from 'prop-types';
import { useConfig } from '../hooks/useConfig';

// Model context for unified state management
const ModelContext = createContext();

// Action types for model state reducer
const MODEL_ACTIONS = {
  SET_MODEL: 'SET_MODEL',
  SET_PROVIDER: 'SET_PROVIDER',
  SET_CONFIG: 'SET_CONFIG',
  SET_LOADING: 'SET_LOADING',
  SET_ERROR: 'SET_ERROR',
  UPDATE_PERFORMANCE: 'UPDATE_PERFORMANCE',
  ADD_TO_HISTORY: 'ADD_TO_HISTORY',
  RESET_ERROR: 'RESET_ERROR'
};

// Initial state for model context
const initialState = {
  // Current model configuration
  currentModel: 'gpt-4o-mini',
  currentProvider: 'openai',
  modelConfig: {
    temperature: 0.7,
    maxTokens: 4000,
    topP: 1.0,
    presencePenalty: 0,
    frequencyPenalty: 0
  },

  // Model performance tracking
  modelStats: new Map(),
  modelHistory: [],

  // UI state
  loading: false,
  error: null,

  // Available models and providers
  availableModels: [],
  availableProviders: []
};

// Reducer for model state management
function modelReducer(state, action) {
  switch (action.type) {
    case MODEL_ACTIONS.SET_MODEL:
      return {
        ...state,
        currentModel: action.payload,
        error: null
      };

    case MODEL_ACTIONS.SET_PROVIDER:
      return {
        ...state,
        currentProvider: action.payload,
        error: null
      };

    case MODEL_ACTIONS.SET_CONFIG:
      return {
        ...state,
        currentModel: action.payload.chat_model || action.payload.model || state.currentModel,
        currentProvider: action.payload.provider || state.currentProvider,
        modelConfig: {
          ...state.modelConfig,
          ...action.payload
        },
        availableModels: action.payload.available_models || state.availableModels,
        availableProviders: action.payload.available_providers || state.availableProviders,
        error: null
      };

    case MODEL_ACTIONS.SET_LOADING:
      return {
        ...state,
        loading: action.payload
      };

    case MODEL_ACTIONS.SET_ERROR:
      return {
        ...state,
        error: action.payload,
        loading: false
      };

    case MODEL_ACTIONS.UPDATE_PERFORMANCE: {
      const newStats = new Map(state.modelStats);
      newStats.set(action.payload.model, {
        ...newStats.get(action.payload.model),
        ...action.payload.stats
      });
      return {
        ...state,
        modelStats: newStats
      };
    }

    case MODEL_ACTIONS.ADD_TO_HISTORY:
      return {
        ...state,
        modelHistory: [
          {
            model: action.payload.model,
            provider: action.payload.provider,
            timestamp: new Date().toISOString(),
            context: action.payload.context
          },
          ...state.modelHistory.slice(0, 49) // Keep last 50 entries
        ]
      };

    case MODEL_ACTIONS.RESET_ERROR:
      return {
        ...state,
        error: null
      };

    default:
      return state;
  }
}

// ModelProvider component
export function ModelProvider({ children }) {
  const [state, dispatch] = useReducer(modelReducer, initialState);
  const queryClient = useQueryClient();
  const { config, updateConfig } = useConfig();

  // Sync with global config on mount and config changes
  useEffect(() => {
    if (config && config.current) {
      dispatch({
        type: MODEL_ACTIONS.SET_CONFIG,
        payload: {
          chat_model: config.current.chat_model,
          provider: config.current.provider,
          temperature: config.current.temperature,
          maxTokens: config.current.maxTokens,
          available_models: config.available?.models,
          available_providers: config.available?.providers
        }
      });
    }
  }, [config]);

  // Update model selection
  const setModel = useCallback(async (model, options = {}) => {
    try {
      dispatch({ type: MODEL_ACTIONS.SET_LOADING, payload: true });

      // Update local state immediately for UI responsiveness
      dispatch({ type: MODEL_ACTIONS.SET_MODEL, payload: model });

      // Add to history
      dispatch({
        type: MODEL_ACTIONS.ADD_TO_HISTORY,
        payload: {
          model,
          provider: state.currentProvider,
          context: options.context || 'manual_selection'
        }
      });

      // Update global config with guard against retry
      const configPayload = {
        chat_model: model,
        provider: options.provider || state.currentProvider,
        ...options.config,
        __noRetry: true // Prevent infinite retry loops
      };

      await updateConfig(configPayload);

      // Invalidate relevant queries
      queryClient.invalidateQueries(['config']);

    } catch (error) {
      console.error('Failed to update model:', error);
      dispatch({ type: MODEL_ACTIONS.SET_ERROR, payload: error.message });

      // Revert optimistic update on error
      if (config?.current?.chat_model) {
        dispatch({ type: MODEL_ACTIONS.SET_MODEL, payload: config.current.chat_model });
      }

      // Don't re-throw error to prevent auto-resubmission
      return false;
    } finally {
      dispatch({ type: MODEL_ACTIONS.SET_LOADING, payload: false });
    }
  }, [state.currentProvider, updateConfig, queryClient, config]);

  // Update provider selection
  const setProvider = useCallback(async (provider, options = {}) => {
    try {
      dispatch({ type: MODEL_ACTIONS.SET_LOADING, payload: true });

      // Update local state immediately
      dispatch({ type: MODEL_ACTIONS.SET_PROVIDER, payload: provider });

      // Update global config with guard against retry
      const configPayload = {
        provider,
        chat_model: options.model || state.currentModel,
        ...options.config,
        __noRetry: true // Prevent infinite retry loops
      };

      await updateConfig(configPayload);

      // Invalidate relevant queries
      queryClient.invalidateQueries(['config']);

    } catch (error) {
      console.error('Failed to update provider:', error);
      dispatch({ type: MODEL_ACTIONS.SET_ERROR, payload: error.message });

      // Revert optimistic update on error
      if (config?.current?.provider) {
        dispatch({ type: MODEL_ACTIONS.SET_PROVIDER, payload: config.current.provider });
      }

      // Don't re-throw error to prevent auto-resubmission
      return false;
    } finally {
      dispatch({ type: MODEL_ACTIONS.SET_LOADING, payload: false });
    }
  }, [state.currentModel, updateConfig, queryClient, config]);

  // Update model configuration
  const updateModelConfig = useCallback(async (configUpdates) => {
    try {
      dispatch({ type: MODEL_ACTIONS.SET_LOADING, payload: true });

      // Update global config with new model configuration
      await updateConfig(configUpdates);

      // Invalidate relevant queries
      queryClient.invalidateQueries(['config']);

    } catch (error) {
      console.error('Failed to update model config:', error);
      dispatch({ type: MODEL_ACTIONS.SET_ERROR, payload: error.message });
    } finally {
      dispatch({ type: MODEL_ACTIONS.SET_LOADING, payload: false });
    }
  }, [updateConfig, queryClient]);

  // Auto-select model based on task type
  const autoSelectModel = useCallback(async (taskType, context = {}) => {
    try {
      // Simple auto-selection logic (can be enhanced)
      let recommendedModel = state.currentModel;

      if (taskType === 'code_generation' || taskType === 'code_analysis') {
        recommendedModel = 'gpt-4o'; // Better for code tasks
      } else if (taskType === 'chat' || taskType === 'general') {
        recommendedModel = 'gpt-4o-mini'; // Good balance for general tasks
      } else if (taskType === 'complex_reasoning') {
        recommendedModel = 'gpt-4o'; // Best for complex tasks
      }

      // Only switch if different from current model
      if (recommendedModel !== state.currentModel) {
        await setModel(recommendedModel, {
          context: `auto_selected_for_${taskType}`,
          ...context
        });
        return recommendedModel;
      }

      return state.currentModel;
    } catch (error) {
      console.error('Auto-selection failed:', error);
      return state.currentModel;
    }
  }, [state.currentModel, setModel]);

  // Track model performance
  const trackPerformance = useCallback((model, stats, error = null) => {
    dispatch({
      type: MODEL_ACTIONS.UPDATE_PERFORMANCE,
      payload: {
        model,
        stats: {
          ...stats,
          error,
          timestamp: new Date().toISOString()
        }
      }
    });
  }, []);

  // Reset error state
  const resetError = useCallback(() => {
    dispatch({ type: MODEL_ACTIONS.RESET_ERROR });
  }, []);

  // Context value
  const value = {
    // State
    currentModel: state.currentModel,
    currentProvider: state.currentProvider,
    modelConfig: state.modelConfig,
    modelStats: state.modelStats,
    modelHistory: state.modelHistory,
    loading: state.loading,
    error: state.error,
    availableModels: state.availableModels,
    availableProviders: state.availableProviders,

    // Actions
    setModel,
    setProvider,
    updateModelConfig,
    autoSelectModel,
    trackPerformance,
    resetError
  };

  return (
    <ModelContext.Provider value={value}>
      {children}
    </ModelContext.Provider>
  );
}

// PropTypes validation
ModelProvider.propTypes = {
  children: PropTypes.node.isRequired
};

// Hook to use model context
// eslint-disable-next-line react-refresh/only-export-components
export function useModelContext() {
  const context = useContext(ModelContext);
  if (!context) {
    throw new Error('useModelContext must be used within a ModelProvider');
  }
  return context;
}

// Export for easier imports
// eslint-disable-next-line react-refresh/only-export-components
export { ModelContext, MODEL_ACTIONS };
