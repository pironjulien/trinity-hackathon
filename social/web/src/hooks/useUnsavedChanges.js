import { useState, useRef, useEffect } from 'react';
import { useCyberWindow } from '../components/layout/CyberWindowContext';

/**
 * SOTA 2026: Hook to manage unsaved changes protection
 * @param {Function} getCurrentConfig - Function returning the current configuration object
 * @param {Object} fetchedConfig - The original configuration data from API
 * @returns {Object} { isDirty, originalConfigRef }
 */
export const useUnsavedChanges = (getCurrentConfig, fetchedConfig) => {
    const { registerInterceptor } = useCyberWindow();
    const originalConfigRef = useRef(null);
    const [isDirty, setIsDirty] = useState(false);

    // Update reference when data is fetched/refreshed
    // You should call this when data is successfully loaded
    const updateOriginalConfig = (config) => {
        originalConfigRef.current = config;
        setIsDirty(false);
    };

    // Auto-initialize if fetchedConfig changes (optional convenience)
    useEffect(() => {
        if (fetchedConfig && !originalConfigRef.current) {
            updateOriginalConfig(fetchedConfig);
        }
    }, [fetchedConfig]);

    // Check Dirty Status
    useEffect(() => {
        if (!originalConfigRef.current) return;
        const current = getCurrentConfig();
        // Simple JSON comparison
        const dirty = JSON.stringify(current) !== JSON.stringify(originalConfigRef.current);
        setIsDirty(dirty);
    }, [getCurrentConfig, fetchedConfig]); // Dep on fetchedConfig to trigger re-eval if parent re-renders

    // Register Interceptor
    useEffect(() => {
        if (!registerInterceptor) return;

        const unregister = registerInterceptor(() => {
            if (isDirty) {
                if (!window.confirm("⚠️ Modifications non sauvegardées !\n\nVoulez-vous vraiment fermer et perdre vos changements ?")) {
                    return true; // Block closing
                }
            }
            return false; // Allow closing
        });
        return unregister;
    }, [registerInterceptor, isDirty]);

    return { isDirty, updateOriginalConfig, originalConfigRef };
};
