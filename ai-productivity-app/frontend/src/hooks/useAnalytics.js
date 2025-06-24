import { useState, useCallback } from 'react';
import { analyticsAPI } from '../api/analytics';

export const useAnalytics = () => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const getQualityMetrics = useCallback(async (projectId) => {
        setLoading(true);
        setError(null);
        try {
            const response = await analyticsAPI.getQualityMetrics(projectId);
            return response.data || response;
        } catch (err) {
            setError(err.message);
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    return {
        getQualityMetrics,
        loading,
        error
    };
};
