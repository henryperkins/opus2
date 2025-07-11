// frontend/src/components/settings/PresetSelector.jsx
import React from "react";
import PropTypes from "prop-types";
import { useQuery } from "@tanstack/react-query";
import { useAIConfig } from "../../contexts/AIConfigContext";
import apiClient from "../../api/client";

/**
 * Dropdown selector that lists all configuration *presets* returned by the
 * backend (`GET /api/v1/ai-config/presets`).  Selecting a preset calls
 * `applyPreset(presetId)` from the AIConfig context which in turn PATCHes the
 * config on the server.
 */
export default function PresetSelector({ className = "" }) {
  const { applyPreset } = useAIConfig();

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
    if (!presetId) return;
    await applyPreset(presetId);
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
    <select onChange={handleChange} defaultValue="" className={className}>
      <option value="" disabled>
        Select preset…
      </option>
      {presets.map((p) => (
        <option key={p.id} value={p.id}>
          {p.name}
        </option>
      ))}
    </select>
  );
}

PresetSelector.propTypes = {
  className: PropTypes.string,
};
