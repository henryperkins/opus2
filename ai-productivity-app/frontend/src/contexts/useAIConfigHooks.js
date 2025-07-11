import { useContext } from "react";
import { Ctx } from "./AIConfigContext";

export const useAIConfig = () => {
    const ctx = useContext(Ctx);
    if (!ctx) throw new Error("useAIConfig must be used inside Provider");
    return ctx;
};
import { useContext } from "react";
import { useAIConfig } from "./AIConfigContext";

export const useModelSelection = () => {
    const {
        models,
        providers,
        config,
        setModel,
        updateConfig,
        currentProvider,
    } = useAIConfig();

    const selectProvider = (providerId) => {
        updateConfig({ provider: providerId });
    };

    const selectModel = (modelId) => {
        setModel(modelId);
    };

    const availableModels = models.filter(
        (m) => (m.provider ?? currentProvider) === currentProvider
    ).map((m) => ({ ...m, selected: m.model_id === config?.model_id }));

    return {
        selectProvider,
        selectModel,
        currentProvider,
        availableModels,
        providers,
    };
};

export const useGenerationParams = () => {
    const { config, updateConfig } = useAIConfig();

    return {
        temperature: config?.temperature,
        maxTokens: config?.max_tokens,
        topP: config?.top_p,
        frequencyPenalty: config?.frequency_penalty,
        presencePenalty: config?.presence_penalty,
        updateParams: (params) => updateConfig(params),
    };
};

export const useReasoningConfig = () => {
    const { config, updateConfig, currentProvider } = useAIConfig();

    const isClaudeProvider =
        currentProvider && currentProvider.toLowerCase().includes("claude");
    const isAzureOrOpenAI =
        currentProvider &&
        ["azure", "openai"].some((p) => currentProvider.toLowerCase().includes(p));

    const supportsReasoning = !!config?.enable_reasoning;
    const supportsThinking = isClaudeProvider;

    return {
        enableReasoning: config?.enable_reasoning,
        reasoningEffort: config?.reasoning_effort,
        claudeExtendedThinking: config?.claude_extended_thinking,
        claudeThinkingMode: config?.claude_thinking_mode,
        claudeThinkingBudget: config?.claude_thinking_budget_tokens,
        isClaudeProvider,
        isAzureOrOpenAI,
        supportsReasoning,
        supportsThinking,
        updateReasoningConfig: (params) => updateConfig(params),
    };
};
