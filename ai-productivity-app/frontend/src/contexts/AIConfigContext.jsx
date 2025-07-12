import {
  createContext,
  useContext,
  useReducer,
  useCallback,
  useEffect,
} from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "react-hot-toast";

import { useAIConfigAPI } from "../hooks/useAIConfigAPI";

/* --------------------------------------------------------------------- */
/* Utils                                                                 */
/* --------------------------------------------------------------------- */
const toSnake = (s) => s.replace(/([A-Z])/g, "_$1").toLowerCase();
const normaliseKeys = (obj) =>
  Array.isArray(obj)
    ? obj.map(normaliseKeys)
    : obj && typeof obj === "object"
      ? Object.fromEntries(Object.entries(obj).map(([k, v]) => [toSnake(k), v]))
      : obj;

const toCamel = (s) => s.replace(/_([a-z])/g, (m, p1) => p1.toUpperCase());
const cameliseKeys = (obj) =>
  Array.isArray(obj)
    ? obj.map(cameliseKeys)
    : obj && typeof obj === "object"
      ? Object.fromEntries(
          Object.entries(obj).map(([k, v]) => [toCamel(k), cameliseKeys(v)]),
        )
      : obj;

const normaliseAvailableModels = (models) => {
  if (!models || typeof models !== "object") return [];
  return Object.entries(models).flatMap(([provider, providerModels]) =>
    providerModels.map((model) => ({ ...model, provider })),
  );
};

/* --------------------------------------------------------------------- */
/* Context / reducer                                                     */
/* --------------------------------------------------------------------- */
const Ctx = createContext(null);

const ACTION = {
  SET: "SET",
  MERGE: "MERGE",
  ERROR: "ERROR",
  TEST_RES: "TEST",
  HISTORY: "HISTORY",
};

const initial = {
  config: null,
  models: [],
  providers: {},
  loading: false,
  error: null,
  testResult: null,
  modelHistory: [],
  lastUpdated: null,
};

function reducer(state, { type, payload }) {
  switch (type) {
    case ACTION.SET:
      return { ...state, ...payload, error: null };
    case ACTION.MERGE:
      return { ...state, config: { ...state.config, ...payload }, error: null };
    case ACTION.ERROR:
      return { ...state, error: payload, loading: false };
    case ACTION.TEST_RES:
      return { ...state, testResult: payload };
    case ACTION.HISTORY:
      return { ...state, modelHistory: payload };
    default:
      return state;
  }
}

/* --------------------------------------------------------------------- */
/* Provider component                                                    */
/* --------------------------------------------------------------------- */
export function AIConfigProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initial);
  const qc = useQueryClient();
  const aiConfigAPI = useAIConfigAPI();

  /* -------------------- fetch --------------------------------------- */
  const { data, error, isLoading } = useQuery({
    queryKey: ["ai-config"],
    queryFn: aiConfigAPI.getConfig,
    staleTime: 30_000,
    retry: (failureCount, error) => {
      // Don't retry on 422 errors
      if (error?.response?.status === 422) {
        console.error("AI Config 422 Error:", error.response.data);
        return false;
      }
      // Retry other errors up to 3 times
      return failureCount < 3;
    },
  });

  useEffect(() => {
    if (data) {
      console.log("Raw config data:", data); // Debug line
      const { current, available_models, providers, last_updated } = data;
      console.log("Available models:", available_models); // Debug line
      dispatch({
        type: ACTION.SET,
        payload: {
          config: normaliseKeys(current),
          models: normaliseAvailableModels(available_models),
          providers: providers ?? {},
          lastUpdated: last_updated,
          loading: false,
        },
      });
    }
  }, [data]);

  useEffect(() => {
    if (error) {
      console.error("AI Config Error:", error);
      if (error.response?.data) {
        console.error("Error details:", error.response.data);
      }
      dispatch({ type: ACTION.ERROR, payload: error.message });
    }
  }, [error]);

  useEffect(() => {
    dispatch({ type: ACTION.SET, payload: { loading: isLoading } });
  }, [isLoading]);

  /* -------------------- mutation (PATCH) ---------------------------- */
  const patchMut = useMutation({
    mutationFn: aiConfigAPI.patch,
    onSuccess: (data) => {
      dispatch({ type: ACTION.MERGE, payload: normaliseKeys(data) });
      qc.invalidateQueries(["ai-config"]);
      toast.success("Configuration updated");
    },
    onError: (e) => {
      dispatch({ type: ACTION.ERROR, payload: e.message });
      toast.error(e.message || "Update failed");
    },
  });

  const updateConfig = useCallback(
    async (updates) => patchMut.mutateAsync(updates),
    [patchMut],
  );

  /* -------------------- setModel helper ----------------------------- */
  const setModel = useCallback(
    async (modelId) => {
      if (!modelId || modelId === state.config?.model_id) return true;
      const mdl = state.models.find((m) => m.model_id === modelId);
      if (!mdl) {
        toast.error(`Model '${modelId}' not found`);
        return false;
      }
      try {
        await updateConfig({ modelId, provider: mdl.provider });
        // history (max 10)
        const hist = [
          modelId,
          ...state.modelHistory.filter((m) => m !== modelId),
        ].slice(0, 10);
        dispatch({ type: ACTION.HISTORY, payload: hist });
        return true;
      } catch {
        return false;
      }
    },
    [state.config, state.models, state.modelHistory, updateConfig],
  );

  /* -------------------- test ---------------------------------------- */
  const testConfig = useCallback(
    async (cfg) => {
      dispatch({ type: ACTION.TEST_RES, payload: null });
      const res = await aiConfigAPI.test(cfg);
      dispatch({ type: ACTION.TEST_RES, payload: res });
      return res;
    },
    [aiConfigAPI],
  );

  /* -------------------- conflict resolve --------------------------- */
  const resolveConflict = useCallback(
    (strategy, proposed) =>
      aiConfigAPI.resolveConflict({
        conflict_strategy: strategy,
        proposed_config: proposed,
      }),
    [aiConfigAPI],
  );

  /* -------------------- apply preset ------------------------------ */
  const applyPreset = useCallback(
    async (presetId) => {
      // Early return if no models loaded
      if (!state.models || state.models.length === 0) {
        toast.error("No models available. Please check your configuration.");
        return false;
      }

      let preset = null;
      try {
        const presets = await aiConfigAPI.presets();
        preset = presets.find((p) => p.id === presetId);
        if (!preset) {
          toast.error(`Preset '${presetId}' not found`);
          return false;
        }

        /* ---- DEFENSIVE CHECK -------------------------------------- */
        const presetModelId = preset.config.model_id;
        const presetProvider = preset.config.provider;

        // More detailed error message
        const modelExists = state.models.some(
          (m) => m.model_id === presetModelId && m.provider === presetProvider,
        );

        if (!modelExists) {
          // Check if it's a provider issue or model issue
          const providerExists = state.models.some(m => m.provider === presetProvider);

          if (!providerExists) {
            toast.error(
              `Provider '${presetProvider}' is not configured. ` +
              `Available providers: ${[...new Set(state.models.map(m => m.provider))].join(', ')}`
            );
          } else {
            toast.error(
              `Model '${presetModelId}' not available for provider '${presetProvider}'. ` +
              `Available models: ${state.models
                .filter(m => m.provider === presetProvider)
                .map(m => m.model_id)
                .join(', ')}`
            );
          }
          return false;
        }
        /* ----------------------------------------------------------- */

        // Ensure camelCase keys for the API
        const configData = cameliseKeys(preset.config);
        await updateConfig({ ...configData, provider: presetProvider });
        toast.success(`Preset '${preset.name || presetId}' applied`);
        return true;
      } catch (e) {
        console.error("Error applying preset:", {
          presetId,
          preset,
          error: e.message,
          response: e.response?.data,
          availableModels: state.models, // Add this for debugging
        });

        const errorMsg =
          e.response?.data?.detail || e.message || "Failed to apply preset";
        toast.error(errorMsg);
        return false;
      }
    },
    [aiConfigAPI, state.models, updateConfig],
  );

  /* -------------------- computed ------------------------------ */
  const value = {
    ...state,
    loading: state.loading || patchMut.isPending,
    updateConfig,
    testConfig,
    setModel,
    resolveConflict,
    applyPreset,
    /* helpers */
    currentModel: state.config?.model_id,
    currentProvider: state.config?.provider,
    isAdmin: true, // stub – replace with real role check
  };

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

/* --------------------------------------------------------------------- */
/* Hooks – public API                                                    */
/* --------------------------------------------------------------------- */
export function useAIConfig() {
  return useContext(Ctx);
}

/* Keep external hook import path unchanged ---------------------------- */
export { useModelSelection } from "../hooks/useModelSelect";

/* Generation-parameter helper ----------------------------------------- */
export function useGenerationParams() {
  const { config, updateConfig } = useAIConfig();

  return {
    temperature:      config?.temperature,
    maxTokens:        config?.max_tokens,
    topP:             config?.top_p,
    frequencyPenalty: config?.frequency_penalty,
    presencePenalty:  config?.presence_penalty,
    updateParams: (patch) => updateConfig(patch),
  };
}

/* Reasoning / thinking helper ----------------------------------------- */
export function useReasoningConfig() {
  const { config, updateConfig } = useAIConfig();

  const provider         = config?.provider;
  const isClaudeProvider = provider === "anthropic";
  const isAzureOrOpenAI  = provider === "azure" || provider === "openai";

  return {
    enableReasoning:        config?.enable_reasoning,
    reasoningEffort:        config?.reasoning_effort,
    claudeExtendedThinking: config?.claude_extended_thinking,
    claudeThinkingMode:     config?.claude_thinking_mode,
    claudeThinkingBudget:   config?.claude_thinking_budget_tokens,

    isClaudeProvider,
    isAzureOrOpenAI,
    supportsReasoning: !!config?.enable_reasoning || isAzureOrOpenAI,
    supportsThinking:  isClaudeProvider,

    updateReasoningConfig: (patch) => updateConfig(patch),
  };
}
