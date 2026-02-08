/**
 * JULES V3 STORE
 * ═══════════════════════════════════════════════════════════════════════════
 * State management for Jules shadow developer UI.
 * Handles project proposals, user decisions, and animation states.
 * ═══════════════════════════════════════════════════════════════════════════
 */

import { create } from 'zustand';
import { ANGEL_BASE_URL, getTrinityHeaders } from '../services/angelService';

export const useJulesStore = create((set, get) => ({
    // System Status
    status: 'idle', // idle | working | done | pending
    isActive: false, // Jules globally enabled (synced with backend)
    isLoading: false,
    error: null,

    // Morning Brief (5 project proposals)
    projects: [],
    lastBriefDate: null,

    // Pending Queue (projects awaiting review)
    pendingProjects: [],
    pendingCount: 0,

    // SOTA 2026: Staged Projects (executed by Jules API, files available locally)
    stagedProjects: [],
    stagedCount: 0,

    // SOTA 2026: Council Control (Manual Trigger)
    councilRunning: false,
    councilStartedAt: null,

    // UI State
    showPanel: false,
    setShowPanel: (show) => set({ showPanel: show }),
    togglePanel: () => set((state) => ({ showPanel: !state.showPanel })),

    // Animation State
    idleIndex: 1, // 1, 2, or 3 for idle animation rotation
    rotateIdle: () => set((state) => ({
        idleIndex: (state.idleIndex % 3) + 1
    })),

    /**
     * Fetch Jules options (including active state)
     */
    fetchOptions: async () => {
        try {
            const res = await fetch(`${ANGEL_BASE_URL}/api/jules/options`, {
                headers: getTrinityHeaders()
            });
            if (res.ok) {
                const data = await res.json();
                set({ isActive: data.active || false });
                return data;
            }
        } catch (err) {
            console.error('[JULES] Options fetch failed:', err);
        }
        return null;
    },

    /**
     * Set Jules active state
     */
    setActive: async (active) => {
        try {
            // SOTA 2026: FastAPI expects query params, not JSON body
            const res = await fetch(`${ANGEL_BASE_URL}/api/jules/options?active=${active}`, {
                method: 'POST',
                headers: getTrinityHeaders()
            });
            if (res.ok) {
                set({ isActive: active });
                return true;
            }
        } catch (err) {
            console.error('[JULES] Set active failed:', err);
        }
        return false;
    },

    /**
     * Fetch Jules system status
     */
    fetchStatus: async () => {
        try {
            const res = await fetch(`${ANGEL_BASE_URL}/api/jules/status`, {
                headers: getTrinityHeaders()
            });
            if (res.ok) {
                const data = await res.json();
                // SOTA 2026: Badge = staged_projects (waiting_count is same as staged_projects)
                const totalActionable = data.staged_projects || data.waiting_count || 0;
                set({
                    status: data.status,
                    pendingCount: totalActionable,
                });

                // If projects ready, auto-fetch morning brief and staged
                if (data.status === 'done' && (data.waiting_count > 0 || data.staged_projects > 0)) {
                    get().fetchMorningBrief();
                    get().fetchStagedProjects();
                }
            }
        } catch (err) {
            console.error('[JULES] Status fetch failed:', err);
        }
    },

    /**
     * Fetch current morning brief
     */
    fetchMorningBrief: async () => {
        set({ isLoading: true, error: null });
        try {
            const res = await fetch(`${ANGEL_BASE_URL}/api/jules/morning-brief`, {
                headers: getTrinityHeaders()
            });
            if (res.ok) {
                const data = await res.json();
                set({
                    projects: data.candidates || [],
                    lastBriefDate: data.date || null,
                    status: data.candidates?.length > 0 ? 'done' : 'idle',
                    isLoading: false,
                });
            } else {
                set({ isLoading: false, error: 'Failed to fetch brief' });
            }
        } catch (err) {
            console.error('[JULES] Morning brief fetch failed:', err);
            set({ isLoading: false, error: err.message });
        }
    },

    /**
     * Fetch pending projects (uses staged-projects endpoint)
     */
    fetchPending: async () => {
        try {
            const res = await fetch(`${ANGEL_BASE_URL}/api/jules/staged-projects`, {
                headers: getTrinityHeaders()
            });
            if (res.ok) {
                const data = await res.json();
                set({
                    pendingProjects: data.projects || data || [],
                    pendingCount: data.count || (data.projects || data || []).length,
                });
            }
        } catch (err) {
            console.error('[JULES] Pending fetch failed:', err);
        }
    },

    /**
     * SOTA 2026: Fetch staged projects (executed by Jules API)
     * These are projects with completed PRs ready for human review.
     */
    fetchStagedProjects: async () => {
        try {
            const res = await fetch(`${ANGEL_BASE_URL}/api/jules/staged-projects`, {
                headers: getTrinityHeaders()
            });
            if (res.ok) {
                const data = await res.json();
                set({
                    stagedProjects: data.projects || [],
                    stagedCount: data.count || 0,
                });
            }
        } catch (err) {
            console.error('[JULES] Staged projects fetch failed:', err);
        }
    },

    /**
     * SOTA 2026: Fetch diff for a staged project
     * @param {string} projectId - Project identifier
     * @returns {string|null} - Git patch diff
     */
    fetchProjectDiff: async (projectId) => {
        try {
            const res = await fetch(`${ANGEL_BASE_URL}/api/jules/project/${projectId}/diff`, {
                headers: getTrinityHeaders()
            });
            if (res.ok) {
                const data = await res.json();
                return data.diff;
            }
        } catch (err) {
            console.error('[JULES] Project diff fetch failed:', err);
        }
        return null;
    },

    /**
     * Send user decision for a project
     * @param {string} projectId - Project identifier
     * @param {string} action - 'MERGE' | 'PENDING' | 'REJECT'
     * @param {string} prUrl - Optional PR URL
     * @param {boolean} isStaged - Whether this is a staged project (new API)
     */
    sendDecision: async (projectId, action, prUrl = null, isStaged = false) => {
        set({ isLoading: true, error: null });
        try {
            let res;

            // SOTA 2026: Use new staging API for staged projects
            if (isStaged) {
                res = await fetch(`${ANGEL_BASE_URL}/api/jules/project/${projectId}/decision`, {
                    method: 'POST',
                    headers: { ...getTrinityHeaders(), 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action })
                });
            } else {
                // Legacy: Morning Brief decisions (council ideas)
                const params = new URLSearchParams({
                    project_id: projectId,
                    action: action,
                });
                if (prUrl) params.append('pr_url', prUrl);

                res = await fetch(`${ANGEL_BASE_URL}/api/jules/decision?${params}`, {
                    method: 'POST',
                    headers: getTrinityHeaders()
                });
            }

            if (res.ok) {
                const result = await res.json();

                // Update local state
                set((state) => ({
                    projects: state.projects.map(p =>
                        p.id === projectId ? { ...p, status: action } : p
                    ),
                    stagedProjects: state.stagedProjects.filter(p => p.id !== projectId),
                    isLoading: false,
                }));

                // Refresh status and lists
                get().fetchStatus();
                get().fetchStagedProjects();
                if (action === 'PENDING') {
                    get().fetchPending();
                }

                return result;
            } else {
                const error = await res.json();
                set({ isLoading: false, error: error.detail || 'Decision failed' });
                return null;
            }
        } catch (err) {
            console.error('[JULES] Decision failed:', err);
            set({ isLoading: false, error: err.message });
            return null;
        }
    },

    /**
     * Clear a project from pending
     */
    clearPending: async (projectId) => {
        // This is handled via sendDecision with MERGE or REJECT
        // No separate endpoint needed
    },

    /**
     * Reset store state
     */
    reset: () => set({
        status: 'idle',
        projects: [],
        pendingProjects: [],
        pendingCount: 0,
        stagedProjects: [],
        stagedCount: 0,
        councilRunning: false,
        councilStartedAt: null,
        showPanel: false,
        error: null,
    }),

    // ════════════════════════════════════════════════════════════════════════
    // COUNCIL CONTROL (Manual Trigger - SOTA 2026)
    // ════════════════════════════════════════════════════════════════════════

    /**
     * Start the Nightly Council manually
     */
    startCouncil: async () => {
        try {
            const res = await fetch(`${ANGEL_BASE_URL}/api/jules/council/start`, {
                method: 'POST',
                headers: getTrinityHeaders()
            });
            if (res.ok) {
                const data = await res.json();
                set({
                    councilRunning: true,
                    councilStartedAt: data.started_at
                });
                return { success: true };
            } else {
                const error = await res.json();
                return { success: false, error: error.detail };
            }
        } catch (err) {
            console.error('[JULES] Start council failed:', err);
            return { success: false, error: err.message };
        }
    },

    /**
     * Fetch current council execution status
     */
    fetchCouncilStatus: async () => {
        try {
            const res = await fetch(`${ANGEL_BASE_URL}/api/jules/council/status`, {
                headers: getTrinityHeaders()
            });
            if (res.ok) {
                const data = await res.json();
                set({
                    councilRunning: data.running,
                    councilStartedAt: data.started_at
                });
            }
        } catch (err) {
            console.error('[JULES] Council status fetch failed:', err);
        }
    },
}));
