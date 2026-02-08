/**
 * SOTA 2026: Data Preloader Hook
 * Pre-fetches all panel data when Trinity becomes 'running'
 * Eliminates "Waiting for Data" flash on panel open
 */

import { useEffect, useRef } from 'react';
import { useTrinityStore } from '../stores/trinityStore';
import { ANGEL_BASE_URL, getTrinityHeaders } from './angelService';

/**
 * Wait for Trinity FastAPI to be ready (health check with retry)
 */
async function waitForTrinityReady(headers, maxRetries = 10, intervalMs = 1000) {
    for (let i = 0; i < maxRetries; i++) {
        try {
            const res = await fetch(`${ANGEL_BASE_URL}/api/vitals`, { headers });
            if (res.ok) {
                console.log(`[DataPreloader] Trinity API ready after ${i + 1} attempt(s)`);
                return true;
            }
        } catch (e) {
            // Network error, retry
        }
        await new Promise(resolve => setTimeout(resolve, intervalMs));
    }
    console.warn('[DataPreloader] Trinity API not ready after max retries');
    return false;
}

/**
 * Preload all panel data in parallel when Trinity starts running
 * This hook should be called once in App.jsx
 */
export function useDataPreloader() {
    const { trinityStatus, setTrinityState, setTraderState, setInfluencerState, setYoutuberState } = useTrinityStore();
    const hasPreloadedRef = useRef(false);

    useEffect(() => {
        // Only preload once when Trinity becomes running
        if (trinityStatus !== 'running') {
            hasPreloadedRef.current = false; // Reset for next startup
            return;
        }

        if (hasPreloadedRef.current) return;
        hasPreloadedRef.current = true;

        const preloadAll = async () => {
            console.log('[DataPreloader] Trinity running - waiting for API...');
            const headers = getTrinityHeaders();

            // SOTA 2026: Wait for Trinity FastAPI to actually be ready (not just Angel reporting 'running')
            const ready = await waitForTrinityReady(headers);
            if (!ready) {
                console.error('[DataPreloader] Aborted - Trinity API not responding');
                hasPreloadedRef.current = false; // Allow retry on next status change
                return;
            }

            console.log('[DataPreloader] Preloading all panel data...');

            const results = await Promise.allSettled([
                // Trinity Panel Data
                fetch(`${ANGEL_BASE_URL}/api/vitals`, { headers }),
                fetch(`${ANGEL_BASE_URL}/api/treasury`, { headers }),
                fetch(`${ANGEL_BASE_URL}/api/jobs`, { headers }),
                fetch(`${ANGEL_BASE_URL}/api/triggers`, { headers }),
                fetch(`${ANGEL_BASE_URL}/api/trinity/config`, { headers }),
                // Trader Panel Data
                fetch(`${ANGEL_BASE_URL}/api/trader/status`, { headers }),
                // Influencer Panel Data
                fetch(`${ANGEL_BASE_URL}/api/influencer/status`, { headers }),
                // YouTuber Panel Data
                fetch(`${ANGEL_BASE_URL}/api/youtuber/status`, { headers }),
            ]);

            // Process Trinity data
            const [resVitals, resTreasury, resJobs, resTriggers, resConfig, resTrader, resInfluencer, resYoutuber] = results;

            // Trinity: Vitals
            if (resVitals.status === 'fulfilled' && resVitals.value.ok) {
                const data = await resVitals.value.json();
                setTrinityState({ vitals: data });
            }
            // Trinity: Treasury
            if (resTreasury.status === 'fulfilled' && resTreasury.value.ok) {
                const data = await resTreasury.value.json();
                setTrinityState({ treasury: data });
            }
            // Trinity: Jobs
            if (resJobs.status === 'fulfilled' && resJobs.value.ok) {
                const data = await resJobs.value.json();
                setTrinityState({ jobs: data });
            }
            // Trinity: Triggers
            if (resTriggers.status === 'fulfilled' && resTriggers.value.ok) {
                const data = await resTriggers.value.json();
                setTrinityState({ triggers: data.triggers || [] });
            }
            // Trinity: Config
            if (resConfig.status === 'fulfilled' && resConfig.value.ok) {
                const data = await resConfig.value.json();
                if (data.config) setTrinityState({ config: data.config });
            }

            // Trader Panel
            if (resTrader.status === 'fulfilled' && resTrader.value.ok) {
                const data = await resTrader.value.json();
                setTraderState(data);
            }

            // Influencer Panel
            if (resInfluencer.status === 'fulfilled' && resInfluencer.value.ok) {
                const data = await resInfluencer.value.json();
                setInfluencerState(data);
            }

            // YouTuber Panel
            if (resYoutuber.status === 'fulfilled' && resYoutuber.value.ok) {
                const data = await resYoutuber.value.json();
                setYoutuberState(data);
            }

            console.log('[DataPreloader] All panel data preloaded');
        };

        preloadAll().catch(err => console.error('[DataPreloader] Error:', err));
    }, [trinityStatus, setTrinityState, setTraderState, setInfluencerState, setYoutuberState]);
}

export default useDataPreloader;

