import { useCallback, useMemo } from "react";
import { toast } from "../components/common/Toast";
import { useAIConfig } from "../contexts/AIConfigContext";

// Optional – local storage helpers
const loadHistory = () => {
  try {
    const raw = localStorage.getItem("model_history");
    return raw ? JSON.parse(raw).slice(0, 10) : [];
  } catch {
    return [];
  }
};
const saveHistory = (hist) =>
  localStorage.setItem("model_history", JSON.stringify(hist.slice(0, 10)));

export function useModelSelection() {
  const {
    config,
    models,
    providers,
    setModel,
    updateConfig,
    currentModel,
    currentProvider,
  } = useAIConfig();

  /* ------------------------------------------------------------------ */
  /* Provider / model lists                                             */
  /* ------------------------------------------------------------------ */
  const availableModels = useMemo(() => models ?? [], [models]);

  const providerList = useMemo(
    () => {
      if (providers && Object.keys(providers).length) return providers;

      const key = currentProvider ?? "unknown";
      const displayName = currentProvider
        ? currentProvider.charAt(0).toUpperCase() + currentProvider.slice(1)
        : "Unknown";

      return {
        [key]: {
          display_name: displayName,
          models: availableModels,
        },
      };
    },
    [providers, currentProvider, availableModels],
  );

  /* grouped list – for dropdown opt-groups etc. */
  const availableModelsByProvider = useMemo(() => {
    const dict = {};
    availableModels.forEach((m) => {
      const p = m.provider ?? currentProvider;
      dict[p] = dict[p] ? [...dict[p], m] : [m];
    });
    return dict;
  }, [availableModels, currentProvider]);

  /* ------------------------------------------------------------------ */
  /* Selection helpers                                                  */
  /* ------------------------------------------------------------------ */
  const selectModel = useCallback(
    async (modelId) => {
      if (!modelId || modelId === currentModel) return true;

      const ok = await setModel(modelId);
      if (ok) {
        const hist = [modelId, ...loadHistory().filter((m) => m !== modelId)];
        saveHistory(hist);
        toast.success(`Switched to ${modelId}`);
      }
      return ok;
    },
    [currentModel, setModel],
  );

  const selectProvider = useCallback(
    async (provider) => {
      if (!provider || provider === currentProvider) return true;

      // Find first model for that provider
      const model = availableModels.find((m) => m.provider === provider);
      if (!model) {
        toast.error(`No models available for provider '${provider}'`);
        return false;
      }
      // updateConfig will PATCH provider+model in one go
      await updateConfig({ provider, model_id: model.model_id });
      toast.success(`Switched to ${provider}`);
      return true;
    },
    [currentProvider, availableModels, updateConfig],
  );

  /* ------------------------------------------------------------------ */
  /* Public API                                                         */
  /* ------------------------------------------------------------------ */
  return {
    /* current */
    currentModel,
    currentProvider,

    /* lists */
    availableModels,
    availableModelsByProvider,
    providers: providerList,

    /* actions */
    selectModel,
    selectProvider,
  };
}
