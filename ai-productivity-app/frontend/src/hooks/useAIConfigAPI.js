import { useCallback } from "react";
import apiClient from "../api/client";

const API = "/api/v1/ai-config";

export function useAIConfigAPI() {
    const getConfig = useCallback(async () => {
        return (await apiClient.get(API)).data;
    }, []);

    const patch = useCallback(async (body) => {
        return (await apiClient.patch(API, body)).data;
    }, []);

    const test = useCallback(async (cfg) => {
        return (await apiClient.post(`${API}/test`, cfg)).data;
    }, []);

    const presets = useCallback(async () => {
        return (await apiClient.get(`${API}/presets`)).data;
    }, []);

    const resolveConflict = useCallback(async (payload) => {
        return (await apiClient.post(`${API}/resolve-conflict`, payload)).data;
    }, []);

    return {
        getConfig,
        patch,
        test,
        presets,
        resolveConflict,
    };
}
