// frontend/src/hooks/useConfig.js
import { useState, useEffect } from 'react';
import configAPI from '../api/config';

export function useConfig() {
    const [config, setConfig] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchConfig = async () => {
            try {
                setLoading(true);
                const data = await configAPI.getConfig();
                setConfig(data);
                setError(null);
            } catch (err) {
                setError(err);
                console.error('Failed to fetch config:', err);
            } finally {
                setLoading(false);
            }
        };

        fetchConfig();
    }, []);

    return { config, loading, error };
}
