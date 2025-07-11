
import { createContext, useContext, useReducer, useCallback, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "react-hot-toast";

import apiClient from "../api/client";

/* --------------------------------------------------------------------- */
/* REST helpers                                                          */
/* --------------------------------------------------------------------- */
const API = "/api/v1/ai-config";

const aiConfigAPI = {
  getConfig: async () => (await apiClient.get(API)).data,
  patch: async (body) => (await apiClient.patch(API, body)).data,
  test: async (cfg) => (await apiClient.post(`${API}/test`, cfg)).data,
  presets: async () => (await apiClient.get(`${API}/presets`)).data,
  resolveConflict: async (payload) =>
    (await apiClient.post(`${API}/resolve-conflict`, payload)).data,
};

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

// Convert snake_case keys (from backend presets) into camelCase so the PATCH
// payload matches the API contract (ConfigUpdate expects camelCase).
const toCamel = (s) => s.replace(/_([a-z])/g, (m, p1) => p1.toUpperCase());
const cameliseKeys = (obj) =>
  Array.isArray(obj)
    ? obj.map(cameliseKeys)
    : obj && typeof obj === "object"
      ? Object.fromEntries(
          Object.entries(obj).map(([k, v]) => [toCamel(k), cameliseKeys(v)]),
        )
      : obj;

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

  /* -------------------- fetch --------------------------------------- */
  useQuery({
    queryKey: ["ai-config"],
    queryFn: aiConfigAPI.getConfig,
    staleTime: 30_000,
    onSuccess: (data) => {
      const { current, available_models, providers, last_updated } = data;
      console.log("Current config from backend:", current);
      dispatch({
        type: ACTION.SET,
        payload: {
          config: normaliseKeys(current),
          models: normaliseKeys(available_models),
          providers: providers ?? {},
          lastUpdated: last_updated,
          loading: false,
        },
      });
    },
    onError: (e) => dispatch({ type: ACTION.ERROR, payload: e.message }),
  });

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
        await updateConfig({ modelId: modelId, provider: mdl.provider });
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
    [],
  );

  /* -------------------- conflict resolve --------------------------- */
  const resolveConflict = useCallback(
    (strategy, proposed) =>
      aiConfigAPI.resolveConflict({
        conflict_strategy: strategy,
        proposed_config: proposed,
      }),
    [],
  );

  /* -------------------- apply preset ------------------------------ */
  const applyPreset = useCallback(
    async (presetId) => {
      let preset = null;
      try {
        const presets = await aiConfigAPI.presets();
        preset = presets.find((p) => p.id === presetId);
        if (!preset) {
          toast.error(`Preset '${presetId}' not found`);
          return false;
        }

        // Ensure camelCase keys for the API
        const configData = cameliseKeys(preset.config);
        console.log("Applying preset:", { presetId, preset, configData });

        // The backend now handles provider-specific adaptations
        // Just send the preset config as-is
        await updateConfig(configData);
        toast.success(`Preset '${preset.name || presetId}' applied`);
        return true;
      } catch (e) {
        console.error("Error applying preset:", {
          presetId,
          preset,
          error: e.message,
          response: e.response?.data
        });

        // Extract detailed error message from response
        const errorMsg = e.response?.data?.detail || e.message || "Failed to apply preset";
        toast.error(errorMsg);
        return false;
      }
    },
    [updateConfig],
  );

  // /* -------------------- websocket sync ----------------------------- */
  // useEffect(() => {
  //   const url =
  //     (location.protocol === "https:" ? "wss://" : "ws://") +
  //     location.host.replace(":5173", ":8000") +
  //     "/ws/config";
  //   const ws = new WebSocket(url);

  //   ws.onmessage = (ev) => {
  //     const msg = JSON.parse(ev.data);
  //     if (msg.type?.startsWith("config_")) qc.invalidateQueries(["ai-config"]);
  //   };
  //   return () => ws.close();
  // }, [qc]);

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

/* Main context accessor ------------------------------------------------ */
export function useAIConfig() {
  return useContext(Ctx);
}

/* Keep external hook import path unchanged ---------------------------- */
export { useModelSelection } from "../hooks/useModelSelect";

/* Generation-parameter helper ----------------------------------------- */
export function useGenerationParams() {
  const { config, updateConfig } = useAIConfig();

  return {
    /* current values */
    temperature:      config?.temperature,
    maxTokens:        config?.max_tokens,
    topP:             config?.top_p,
    frequencyPenalty: config?.frequency_penalty,
    presencePenalty:  config?.presence_penalty,
    /* mutator */
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
    /* current values */
    enableReasoning:        config?.enable_reasoning,
    reasoningEffort:        config?.reasoning_effort,
    claudeExtendedThinking: config?.claude_extended_thinking,
    claudeThinkingMode:     config?.claude_thinking_mode,
    claudeThinkingBudget:   config?.claude_thinking_budget_tokens,

    /* derived feature flags */
    isClaudeProvider,
    isAzureOrOpenAI,
    supportsReasoning: !!config?.enable_reasoning || isAzureOrOpenAI,
    supportsThinking:  isClaudeProvider,

    /* mutator */
    updateReasoningConfig: (patch) => updateConfig(patch),
  };
}
