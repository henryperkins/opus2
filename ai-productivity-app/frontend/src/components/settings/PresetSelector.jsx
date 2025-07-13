// frontend/src/components/settings/PresetSelector.jsx
import React from "react";
import PropTypes from "prop-types";
import { useQuery } from "@tanstack/react-query";
import { useAIConfig } from "../../contexts/AIConfigContext";
import apiClient from "../../api/client";

/**
 * Enhanced dropdown selector that lists configuration presets with provider awareness.
 * Shows which providers each preset supports and adapts automatically.
 */
export default function PresetSelector({ className = "" }) {
  const { applyPreset, currentProvider } = useAIConfig();
  const [applying, setApplying] = React.useState(false);

  // Helper fetcher – colocated to avoid tight coupling with the context
  const fetchPresets = React.useCallback(async () => {
    const res = await apiClient.get("/api/v1/ai-config/presets");
    return res.data;
  }, []);

  // Fetch presets once; they rarely change.
  const {
    data: presets,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ["ai-config", "presets"],
    queryFn: fetchPresets,
    staleTime: 10 * 60 * 1000, // 10 minutes
  });

  const handleChange = async (e) => {
    const presetId = e.target.value;
    if (!presetId || applying) return;
    
    setApplying(true);
    try {
      await applyPreset(presetId);
    } finally {
      setApplying(false);
      // Reset the select to show placeholder
      e.target.value = "";
    }
  };

  // Get provider display name
  const getProviderDisplayName = (provider) => {
    const names = {
      openai: "OpenAI",
      azure: "Azure OpenAI",
      anthropic: "Anthropic"
    };
    return names[provider] || provider;
  };

  // Check if preset has config for current provider
  const presetSupportsProvider = (preset, provider) => {
    return preset.provider_configs && provider in preset.provider_configs;
  };

  if (isLoading) {
    return (
      <select disabled className={className}>
        <option>Loading presets…</option>
      </select>
    );
  }

  if (isError) {
    const msg = error?.message || "Failed to load presets";
    return <div className="text-sm text-red-600">{msg}</div>;
  }

  if (!presets?.length) {
    return <div className="text-sm text-gray-500">No presets available</div>;
  }

  return (
    <div className="space-y-2">
      <select 
        onChange={handleChange} 
        defaultValue="" 
        className={className}
        disabled={applying}
      >
        <option value="" disabled>
          {applying ? "Applying preset..." : "Select preset…"}
        </option>
        {presets.map((preset) => {
          const supportsCurrentProvider = presetSupportsProvider(preset, currentProvider);
          const providerList = preset.provider_configs 
            ? Object.keys(preset.provider_configs).map(getProviderDisplayName).join(", ")
            : "All providers";
          
          return (
            <option 
              key={preset.id} 
              value={preset.id}
              title={`Supports: ${providerList}`}
            >
              {preset.name} 
              {supportsCurrentProvider && " ✓"}
              {preset.description && ` - ${preset.description}`}
            </option>
          );
        })}
      </select>
      
      {currentProvider && (
        <p className="text-xs text-gray-600 dark:text-gray-400">
          Current provider: <span className="font-medium">{getProviderDisplayName(currentProvider)}</span>
          {" • Presets will adapt to your provider automatically"}
        </p>
      )}
    </div>
  );
}

PresetSelector.propTypes = {
  className: PropTypes.string,
};
