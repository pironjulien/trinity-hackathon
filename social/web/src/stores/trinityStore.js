import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { getTrinityHeaders } from '../services/angelService';
import React from 'react'; // SOTA 2026: For useHydration hook

// Fake Boot Sequence
// Fake Boot Sequence
const BOOT_LOGS = []; // SOTA 2026: Real logs only -> Users hate fake logs.

const getApiUrl = (path) => {
    // SOTA 2026: Extension Compatibility check
    const baseUrl = window.trinityBaseUrl || ''; // Injected by VSCode Extension
    return `${baseUrl}${path}`;
};

export const useTrinityStore = create(
    persist(
        (set, get) => ({
            // System State
            phase: 'BOOT', // BOOT, IDLE, ACTION, SLEEP - Default BOOT to play init video first
            isAlive: false, // Socket status
            isAuthenticated: false, // Matrix Auth Guard
            token: null, // JWT/Bearer Token
            audioUnlocked: false, // SOTA 2026: User has interacted, audio can play
            setAlive: (isAlive) => set({ isAlive }),
            setAuthenticated: (isAuthenticated) => set({ isAuthenticated }),
            setToken: (token) => set({ token }),
            role: null, // GOD, VERIFIER, OBSERVER
            user: null,
            setRole: (role) => set({ role }),
            setUser: (user) => set({ user }),
            unlockAudio: () => set({ audioUnlocked: true }),
            locale: 'en', // i18n: 'en' | 'fr' - English default
            setLocale: (locale) => {
                set({ locale });
                // SOTA 2026: Sync to Backend immediately (only if Trinity is running)
                const state = get();
                if (state.token && state.isAuthenticated && state.trinityStatus === 'running') {
                    fetch(getApiUrl('/api/config'), {
                        method: 'POST',
                        headers: getTrinityHeaders(),
                        body: JSON.stringify({ language: locale })
                    }).catch(() => { }); // Silent fail - Trinity may have stopped
                }
            },

            // SOTA 2026: Fetch Backend Config (only if Trinity is running)
            fetchConfig: async () => {
                const state = get();
                // Guard: Skip if not authenticated OR Trinity is offline
                if (!state.token || !state.isAuthenticated || state.trinityStatus !== 'running') return;

                try {
                    const res = await fetch(getApiUrl('/api/config'), {
                        headers: getTrinityHeaders()
                    });
                    if (res.ok) {
                        // SOTA 2026: Backend config is for server-side settings only
                        // User's locale preference (localStorage) takes priority
                        // Backend language is used for content generation, not UI
                    }
                } catch {
                    // Silent fail - Trinity may have stopped mid-request
                }
            },
            isMuted: false, // SOTA 2026: Global sound state (enabled by default)
            setMuted: (isMuted) => set({ isMuted }),
            liveLogsEnabled: true, // SOTA 2026: Live Logs visibility (enabled by default)
            setLiveLogsEnabled: (enabled) => set({ liveLogsEnabled: enabled }),
            julesEnabled: false, // SOTA 2026: Jules visibility (disabled by default)
            setJulesEnabled: (enabled) => set({ julesEnabled: enabled }),
            isChatCollapsed: true, // SOTA 2026: Chat collapse state (Hidden by default)
            setChatCollapsed: (collapsed) => set({ isChatCollapsed: collapsed }),
            // SOTA 2026: Immersive Shutdown Sequence (Standard 382.22)
            isShuttingDown: false, // When true: UI hidden, sleep video plays, then shutdown
            setShuttingDown: (val) => set({ isShuttingDown: val }),

            // CHAT MESSENGER STATE (SOTA 2026 - Simplified Session)
            // ═══════════════════════════════════════════════════════════════════
            chatMessages: [], // Current session: [{role: 'user'|'trinity', content, ts}] - Max 13
            chatSessionDate: null, // Date string of current session (YYYY-MM-DD)
            isWaitingForReply: false,

            // SOTA 2026: Smart message management with auto-reset
            addUserMessage: (text) => set((state) => {
                const now = Date.now();
                const today = new Date().toISOString().split('T')[0];
                const lastTs = state.chatMessages[state.chatMessages.length - 1]?.ts || 0;
                const hoursSinceLastMessage = (now - lastTs) / (1000 * 60 * 60);

                // Reset if: new day OR 8h+ inactivity
                const shouldReset = state.chatSessionDate !== today || hoursSinceLastMessage > 8;

                const baseMessages = shouldReset ? [] : state.chatMessages;
                const newMessages = [...baseMessages, { role: 'user', content: text, ts: now }];

                // Keep only last 13 messages
                const trimmed = newMessages.slice(-13);

                return {
                    chatMessages: trimmed,
                    chatSessionDate: today,
                    isWaitingForReply: true
                };
            }),

            addTrinityMessage: (text) => set((state) => {
                const newMessages = [...state.chatMessages, { role: 'trinity', content: text, ts: Date.now() }];
                // Keep only last 13 messages
                return {
                    chatMessages: newMessages.slice(-13),
                    isWaitingForReply: false
                };
            }),

            clearChat: () => set({ chatMessages: [], chatSessionDate: null }),

            // SOTA 2026: Directional Gaze System - triggers look left/right/down video on interaction
            pendingGaze: null, // null | 'left' | 'right' | 'down'
            gazeCooldowns: { left: 0, right: 0, down: 0, sleep: 0, error: 0 }, // Timestamps of last gaze per direction (Standard 382.21)
            GAZE_COOLDOWN_MS: 13000, // 13 seconds (Fibonacci cooldown)
            setPendingGaze: (direction) => {
                const state = get();
                const now = Date.now();
                const lastGaze = state.gazeCooldowns[direction] || 0;

                // Skip if same direction triggered within cooldown period
                if (now - lastGaze < state.GAZE_COOLDOWN_MS) {
                    console.log(`[Gaze] ${direction} on cooldown (${Math.ceil((state.GAZE_COOLDOWN_MS - (now - lastGaze)) / 1000)}s left)`);
                    return;
                }

                // Update cooldown and set pending gaze
                set({
                    pendingGaze: direction,
                    gazeCooldowns: { ...state.gazeCooldowns, [direction]: now }
                });
            },
            clearPendingGaze: () => set({ pendingGaze: null }),

            // SOTA 2026: Jobs Status - sync with extension 8810
            jobsStatus: {
                trader: false,      // Is TRADER job running
                influencer: false,  // Is INFLUENCER job running
                youtuber: false,    // Is YOUTUBER job running
                jules: false        // Is JULES job running
            },
            setJobStatus: (job, status) => set((state) => ({
                jobsStatus: { ...state.jobsStatus, [job]: status }
            })),
            setAllJobsStatus: (statuses) => set({ jobsStatus: statuses }),

            // SOTA 2026: Trinity System Status (managed by Angel)
            trinityStatus: 'unknown', // 'unknown' | 'running' | 'stopped'
            setTrinityStatus: (status) => set({ trinityStatus: status }),

            // SOTA 2026: Hydration Flag - Prevents flash of empty content
            _hasHydrated: false,
            setHasHydrated: (val) => set({ _hasHydrated: val }),

            // SOTA 2026: Persistent Panel State (Prevents "Waiting for Data" on re-open)
            traderState: null,
            setTraderState: (data) => set((state) => ({ traderState: { ...state.traderState, ...data } })),
            influencerState: null,
            setInfluencerState: (data) => set((state) => ({ influencerState: { ...state.influencerState, ...data } })),
            youtuberState: null,
            setYoutuberState: (data) => set((state) => ({ youtuberState: { ...state.youtuberState, ...data } })),
            trinityState: null,
            setTrinityState: (data) => set((state) => ({ trinityState: { ...state.trinityState, ...data } })),
            julesState: null,
            setJulesState: (data) => set((state) => ({ julesState: { ...state.julesState, ...data } })),

            logout: () => set({ isAuthenticated: false, token: null, role: null, user: null }),

            // Vitals
            emotion: 'NEUTRAL', // NEUTRAL, HAPPY, STRESSED, ANGRY
            setEmotion: (emotion) => set({ emotion }),

            // Data Streams
            logs: BOOT_LOGS, // Pre-filled with boot sequence
            tokens: [], // SOTA 2026: Token usage tracking
            activeTab: 'TRINITY', // SOTA 2026: Console active tab

            // Log format: { type: 'SYS'|'NET'|'AI'|'USER', msg: 'string', timestamp: number }
            // Token format: { model: string, inputTokens: number, outputTokens: number,    // SOTA 2026: Batch Merge for Polling (Extension Parity)
            mergeLogs: (newLogs) => set((state) => {
                if (!newLogs || newLogs.length === 0) return {};

                // 0. Normalize Logs (Map level -> type for LogTable compatibility)
                const normalizedLogs = newLogs.map(l => ({
                    ...l,
                    type: l.level || l.type || 'INFO', // Fallback
                    // Ensure module is present
                    module: l.module || l.source || 'TRINITY'
                }));

                // 0.5 TOKENS EXTRACTION: Route token logs to tokens array
                const tokenLogs = normalizedLogs.filter(l =>
                    // SOTA 2026: Detect by payload structure (model + usage) OR explicit source
                    (l.model && (l.in !== undefined || l.inputTokens !== undefined)) ||
                    ((l.source || '').toUpperCase() === 'TOKENS' && l.in !== undefined)
                );

                // 1. Filter out existing (De-dupe)
                // Optimization: Assume newLogs are newer or overlapping at the end.
                // We look at the last 200 logs in state to find overlap.
                const recentHistory = state.logs.slice(-200);
                const existingSigs = new Set(recentHistory.map(l => `${l.timestamp}|${l.message}`));

                const uniqueToAdd = normalizedLogs.filter(l => !existingSigs.has(`${l.timestamp}|${l.message}`));

                if (uniqueToAdd.length === 0) return {};

                // 2. Update Job Activity Trackers (for blinking lights)
                const activityUpdates = { ...state.jobLastLogTS };
                uniqueToAdd.forEach(log => {
                    const mod = (log.module || '').toLowerCase();
                    if (mod.includes('trader')) activityUpdates.trader = Math.max(activityUpdates.trader, Date.now());
                    if (mod.includes('youtuber')) activityUpdates.youtuber = Math.max(activityUpdates.youtuber, Date.now());
                    if (mod.includes('influencer')) activityUpdates.influencer = Math.max(activityUpdates.influencer, Date.now());
                });

                // 3. Append and Sort (Safety sort)
                // Keep 2000 logs max (SOTA Standard for Memory Safety)
                const merged = [...state.logs, ...uniqueToAdd];

                // Ensure sorted (if sources mixed slightly out of order)
                // merged.sort((a, b) => (a.timestamp < b.timestamp ? -1 : 1)); // Costly?
                // Actually, 'all' from backend is already sorted. We just append.

                // 4. TOKENS: Dedupe and merge token logs
                const existingTokenSigs = new Set(state.tokens.map(t => `${t.timestamp}|${t.model}`));
                const newTokens = tokenLogs.filter(t => !existingTokenSigs.has(`${t.timestamp}|${t.model}`));
                const mergedTokens = [...state.tokens, ...newTokens].slice(-50);

                return {
                    logs: merged.slice(-2000),
                    tokens: mergedTokens,
                    jobLastLogTS: activityUpdates
                };
            }),

            // SOTA 2026 FIX: Dedupe by timestamp+message
            addLog: (log) => set((state) => {
                // Check last 20 logs for duplicates
                const recentLogs = state.logs.slice(-20);
                const isDuplicate = recentLogs.some(l => l.timestamp === log.timestamp && l.message === log.message);

                if (isDuplicate) {
                    return state;
                }

                // Detect Job Activity
                const mod = (log.module || log.source || '').toLowerCase();
                const activityUpdates = { ...state.jobLastLogTS };
                return {
                    logs: [...state.logs.slice(-1999), log],
                    jobLastLogTS: activityUpdates
                };
                return {
                    logs: [...state.logs.slice(-1999), log],
                    jobLastLogTS: activityUpdates
                };
            }),

            // SOTA 2026: Clear logs from memory
            clearLogs: (tab) => set((state) => {
                if (!tab || tab === 'TRINITY') {
                    // Trinity tab shows almost everything, so maybe clear module-specifics?
                    // Simpler: Just clear all logs if user is on Trinity/Home?
                    // Or follow strict filtering.
                    // Let's implement robust filtering removal:
                    return { logs: [] }; // Nuclear option for now - User expects "Clean Canvas"
                }

                // If specific tab, filter out logs belonging to that tab
                const remainingLogs = state.logs.filter(log => {
                    const mod = (log.module || log.source || '').toUpperCase();
                    if (tab === 'ALERTS' && (log.type === 'ERR' || log.type === 'WARN')) return false;
                    if (mod.includes(tab)) return false;
                    return true;
                });

                return { logs: remainingLogs };
            }),

            // Token format: { model: string, inputTokens: number, outputTokens: number, totalTokens: number, timestamp: number }
            addToken: (entry) => set((state) => ({
                tokens: [...state.tokens.slice(-49), { ...entry, timestamp: Date.now() }]
            })),

            setActiveTab: (tab) => set({ activeTab: tab }),

            // Actions
            setPhase: (phase) => set({ phase }),

            // Changelog
            changelogContent: '',
            fetchChangelog: async () => {
                try {
                    const res = await fetch('/api/changelog');
                    const text = await res.json();
                    set({ changelogContent: text.content });
                } catch (e) {
                    console.error('Failed to fetch changelog:', e);
                    set({ changelogContent: '# Error\nCould not load changelog.' });
                }
            },
        }),
        {
            name: 'trinity-storage', // name of the item in the storage (must be unique)
            storage: createJSONStorage(() => localStorage), // (optional) by default, 'localStorage' is used
            version: 1, // SOTA 2026: Force migration to ensure sound is enabled
            // SOTA 2026: Track hydration completion to prevent flash of empty content
            onRehydrateStorage: () => (state) => {
                state?.setHasHydrated?.(true);
            },
            migrate: (persistedState, version) => {
                if (version === 0) {
                    // Migration from v0 to v1: Force sound ON
                    return { ...persistedState, isMuted: false };
                }
                return persistedState;
            },
            partialize: (state) => ({
                isAuthenticated: state.isAuthenticated,
                role: state.role, // Persist role for RBAC
                // NOTA: Do NOT persist 'phase' - it must reflect real backend state
                token: state.token,
                audioUnlocked: state.audioUnlocked, // SOTA 2026: Persist audio unlock state
                locale: state.locale, // i18n: Persist language preference
                isMuted: state.isMuted, // SOTA 2026: Persist muted state
                traderState: state.traderState, // Persist Trader Data
                influencerState: state.influencerState, // Persist Influencer Data
                youtuberState: state.youtuberState, // Persist Youtuber Data
                trinityState: state.trinityState, // Persist Trinity Data
                julesState: state.julesState, // Persist Jules Data
                liveLogsEnabled: state.liveLogsEnabled, // Persist Live Logs visibility
                julesEnabled: state.julesEnabled, // Persist Jules visibility
                // SOTA 2026: Chat Messenger Persistence (Max 13 messages, reset after 8h inactivity or new day)
                chatMessages: state.chatMessages,
                chatSessionDate: state.chatSessionDate,
                isChatCollapsed: state.isChatCollapsed, // Persist chat visibility
                conversations: state.conversations,
                activeConversationId: state.activeConversationId
            }),
        },
    ),
);

// SOTA 2026 Standard 362.80.6: Hydration Guard Hook
// Use this in components to wait for localStorage hydration before rendering cached data
export const useHydration = () => {
    const [hydrated, setHydrated] = React.useState(useTrinityStore.persist.hasHydrated());

    React.useEffect(() => {
        // If already hydrated, no need to subscribe
        if (useTrinityStore.persist.hasHydrated()) {
            setHydrated(true);
            return;
        }

        // Subscribe to hydration completion
        const unsubFinishHydration = useTrinityStore.persist.onFinishHydration(() => {
            setHydrated(true);
        });

        return () => {
            unsubFinishHydration();
        };
    }, []);

    return hydrated;
};
