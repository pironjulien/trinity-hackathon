import { useTrinityStore } from '../stores/trinityStore';

/**
 * CORE API SERVICE
 * Handles Fetch requests with Bearer Token integration.
 */

const API_BASE = ''; // Proxy handles /api path in Vite, so base is relative root

export const api = {
    /**
     * Login to retrieve Token
     * @param {string} username
     * @param {string} password 
     */
    login: async (username, password) => {
        const res = await fetch(`${API_BASE}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Access Denied');
        }
        return await res.json();
    },

    /**
     * Authenticated GET
     * @param {string} endpoint 
     */
    get: async (endpoint) => {
        const { token } = useTrinityStore.getState();
        const res = await fetch(`${API_BASE}${endpoint}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        if (res.status === 401) {
            useTrinityStore.getState().logout();
            throw new Error('Unauthorized');
        }
        return await res.json();
    },

    /**
     * Authenticated POST
     * @param {string} endpoint 
     * @param {object} body 
     */
    post: async (endpoint, body) => {
        const { token } = useTrinityStore.getState();
        const res = await fetch(`${API_BASE}${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(body)
        });
        if (res.status === 401) {
            useTrinityStore.getState().logout();
            throw new Error('Unauthorized');
        }
        return await res.json();
    }
};
