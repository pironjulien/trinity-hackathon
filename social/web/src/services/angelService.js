/**
 * SOTA 2026: Angel API Service
 * Communicates with Angel Supervisor at http://127.0.0.1:8089
 * 
 * Available endpoints:
 * - GET  /sys/status   → { angel: 'online', trinity: 'running'|'stopped' }
 * - GET  /jobs/status  → { trader: boolean, youtuber: boolean, influencer: boolean }
 * - POST /sys/start    → Start Trinity
 * - POST /sys/stop     → Stop Trinity
 * - POST /jobs/toggle  → Toggle job enabled state
 * - POST /logs/clear   → Clear logs
 */

// SOTA 2026: Pure Web - No Capacitor (Android uses Flutter)
// The frontend is served by Angel on the same origin as the API

import { Capacitor } from '@capacitor/core';

// SOTA 2026: API URL Strategy
// - Web: Relative URL (proxied by Nginx/Vite)
export const PROD_URL = 'https://trinity.julienpiron.fr';

// SOTA 2026: API URL Strategy (Fix 432.8)
// - Web: Relative URL (proxied)
// - Native: Absolute URL (Force Network, bypass Capacitor Interceptor)
export const ANGEL_BASE_URL = Capacitor.isNativePlatform() ? PROD_URL : '';

const BOOTSTRAP_TOKEN = typeof __ANGEL_BOOTSTRAP_TOKEN__ !== 'undefined' ? __ANGEL_BOOTSTRAP_TOKEN__ : 'trinity-offline-sota-2026';

export const getHeaders = () => ({
    'Accept': 'application/json',
    'X-Angel-Key': BOOTSTRAP_TOKEN, // SOTA 2026: Bootstrap Token for IPC (Angel ↔ Trinity)
    'Content-Type': 'application/json'
});

/**
 * SOTA 2026: Headers for authenticated Trinity API endpoints
 * Sends x-token (user session) + X-Angel-Key (IPC fallback)
 * - x-token: Unique per user, expires, stored in localStorage after login
 * - X-Angel-Key: Fallback for IPC calls (Angel → Trinity) when no session exists
 */
export const getTrinityHeaders = () => {
    let sessionToken = '';
    try {
        const stored = localStorage.getItem('trinity-storage');
        if (stored) {
            const parsed = JSON.parse(stored);
            sessionToken = parsed.state?.token || '';
        }
    } catch (e) {
        console.warn('Failed to parse trinity-storage:', e);
    }

    return {
        'Accept': 'application/json',
        'x-token': sessionToken, // User session token (secure, expires)
        'X-Angel-Key': BOOTSTRAP_TOKEN, // Fallback for IPC
        'Content-Type': 'application/json'
    };
};


/**
 * Get system status from Angel
 * @returns {Promise<{angel: string, trinity: string}>}
 */
export async function getStatus() {
    try {
        // SOTA 2026: Cache Buster (?_t) to force fresh status on Android
        const response = await fetch(`${ANGEL_BASE_URL}/sys/status?_t=${Date.now()}`, {
            method: 'GET',
            headers: { 'Accept': 'application/json' }
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    } catch (error) {
        console.warn('[AngelService] Status check failed:', error.message);
        return { angel: 'offline', trinity: 'offline', error: error.message }; // SOTA 2026: Exposure for UI Debugging
    }
}

/**
 * Get jobs status from Angel
 * @returns {Promise<{trader: boolean, youtuber: boolean, influencer: boolean}>}
 */
export async function getJobsStatus() {
    try {
        const response = await fetch(`${ANGEL_BASE_URL}/jobs/status`, {
            method: 'GET',
            headers: { 'Accept': 'application/json' }
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    } catch (error) {
        console.warn('[AngelService] Jobs status check failed:', error.message);
        return { trader: false, youtuber: false, influencer: false };
    }
}

/**
 * Start Trinity via Angel
 */
export async function startTrinity() {
    try {
        const response = await fetch(`${ANGEL_BASE_URL}/sys/start`, { method: 'POST', headers: getHeaders() });
        return response.ok;
    } catch (error) {
        console.error('[AngelService] Start failed:', error);
        return false;
    }
}

/**
 * Stop Trinity via Angel
 */
export async function stopTrinity() {
    try {
        const response = await fetch(`${ANGEL_BASE_URL}/sys/stop`, { method: 'POST', headers: getHeaders() });
        return response.ok;
    } catch (error) {
        console.error('[AngelService] Stop failed:', error);
        return false;
    }
}

/**
 * Toggle a job's enabled state
 * @param {string} job - 'trader' | 'youtuber' | 'influencer'
 * @param {boolean} enabled - New state
 */
export async function toggleJob(job, enabled) {
    try {
        const response = await fetch(`${ANGEL_BASE_URL}/jobs/toggle?job=${job}&enabled=${enabled}`, {
            method: 'POST',
            headers: getHeaders()
        });
        return response.ok;
    } catch (error) {
        console.error('[AngelService] Toggle job failed:', error);
        return false;
    }
}

/**
 * Clear logs via Angel
 * @param {string} tab - Optional tab filter (ALERTS, TRINITY, ANGEL, etc.)
 */
export async function clearLogs(tab = null) {
    try {
        const url = tab
            ? `${ANGEL_BASE_URL}/logs/clear?tab=${tab}`
            : `${ANGEL_BASE_URL}/logs/clear`;
        const response = await fetch(url, { method: 'POST', headers: getHeaders() });
        return response.ok;
    } catch (error) {
        console.error('[AngelService] Clear logs failed:', error);
        return false;
    }
}

/**
 * Fetch logs for a specific type from disk via Angel
 * @param {string} type - 'trinity' | 'angel' | 'alerts' | 'trader' etc.
 * @param {number} lines - Number of logs to fetch if 'since' not used (default 100)
 * @param {string} since - Optional ISO timestamp to fetch logs created AFTER this time
 */
export async function fetchLogs(type = 'trinity', lines = 100, since = null) {
    try {
        let url = `${ANGEL_BASE_URL}/logs/read?log=${type.toLowerCase()}&lines=${lines}`;
        if (since) {
            url += `&since=${encodeURIComponent(since)}`;
        }

        const response = await fetch(url, {
            method: 'GET',
            headers: { 'Accept': 'application/json', 'X-Angel-Key': getHeaders()['X-Angel-Key'] }
        });
        if (!response.ok) return [];
        const data = await response.json();
        return data.logs || [];
    } catch (error) {
        // console.warn('[AngelService] Fetch logs failed:', error);
        return [];
    }
}

// Polling interval handle
let pollingInterval = null;

/**
 * Start polling Angel for status updates (system + jobs)
 * @param {function} callback - Called with { status, jobs } on each poll
 * @param {number} intervalMs - Polling interval in milliseconds (default 3000)
 */
export function startPolling(callback, intervalMs = 5000) {
    if (pollingInterval) {
        console.warn('[AngelService] Polling already active');
        return;
    }

    const poll = async () => {
        const [status, jobs] = await Promise.all([getStatus(), getJobsStatus()]);
        callback({ status, jobs });
    };

    poll(); // Immediate first poll
    pollingInterval = setInterval(poll, intervalMs);
    console.log('[AngelService] Polling started');
}

/**
 * Stop polling
 */
export function stopPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
        console.log('[AngelService] Polling stopped');
    }
}

export default {
    getStatus,
    getJobsStatus,
    startTrinity,
    stopTrinity,
    toggleJob,
    clearLogs,
    startPolling,
    stopPolling
};
