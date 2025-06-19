// frontend/src/hooks/useConfig.js
import { useState, useEffect, useRef } from 'react';
import configAPI from '../api/config';

// Simple cache to prevent repeated requests
let cachedConfig = null;
let isConfigLoading = false;
const configCallbacks = new Set();

export function useConfig() {
    const [config, setConfig] = useState(cachedConfig);
    const [loading, setLoading] = useState(!cachedConfig);
    const [error, setError] = useState(null);
    const mountedRef = useRef(true);

    useEffect(() => {
        // If we already have cached config, use it
        if (cachedConfig) {
            setConfig(cachedConfig);
            setLoading(false);
            return;
        }

        // If already loading, just register callback
        if (isConfigLoading) {
            const callback = (result) => {
                if (!mountedRef.current) return;
                if (result.error) {
                    setError(result.error);
                } else {
                    setConfig(result.data);
                }
                setLoading(false);
            };
            configCallbacks.add(callback);
            
            return () => {
                configCallbacks.delete(callback);
            };
        }

        // First time loading
        isConfigLoading = true;
        const fetchConfig = async () => {
            try {
                console.log('useConfig: Fetching config...');
                const data = await configAPI.getConfig();
                cachedConfig = data;
                
                // Update all waiting callbacks
                configCallbacks.forEach(callback => {
                    callback({ data });
                });
                configCallbacks.clear();
                
                if (mountedRef.current) {
                    setConfig(data);
                    setError(null);
                }
            } catch (err) {
                console.error('Failed to fetch config:', err);
                
                // Update all waiting callbacks
                configCallbacks.forEach(callback => {
                    callback({ error: err });
                });
                configCallbacks.clear();
                
                if (mountedRef.current) {
                    setError(err);
                }
            } finally {
                isConfigLoading = false;
                if (mountedRef.current) {
                    setLoading(false);
                }
            }
        };

        fetchConfig();
    }, []);

    useEffect(() => {
        return () => {
            mountedRef.current = false;
        };
    }, []);

    return { config, loading, error };
}
