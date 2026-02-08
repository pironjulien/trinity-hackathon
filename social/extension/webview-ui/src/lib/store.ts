import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type UserRole = 'admin' | 'user' | 'guest';
export type ConnectionStatus = 'active' | 'offline' | 'stopped' | 'connecting' | 'error' | 'sleeping' | 'stopping';
export type AvatarState = 'init' | 'idle' | 'work' | 'alert' | 'angel';
export type AvatarDirection = 'up' | 'down' | 'left' | 'right';

interface JobActivity {
    trader: boolean;
    youtuber: boolean;
    influencer: boolean;
}

// SOTA 2026: Sentinel Button States (8810 Header)
interface EvolutionReportState {
    hasReport: boolean;
    date: string | null;
    summary: string | null;
    analysisPreview: string | null;
}

interface Jobs {
    trader: boolean;
    youtuber: boolean;
    influencer: boolean;
}

interface MemoryProcess {
    name: string;
    ram: number;
    cpu: number;
    pid?: number;
}

interface MemoryBreakdown {
    angel: MemoryProcess;
    trinity: MemoryProcess;
    ubuntu: MemoryProcess; // Replaces Chrome
    antigravity: MemoryProcess;
    other: { ram: number; cpu: number };
}

interface SystemStats {
    cpu: string;
    ram: number;
    disk: number;
    breakdown?: MemoryBreakdown;
}

interface TrinityState {
    // Connection
    status: ConnectionStatus;
    wsConnected: boolean;

    // Identity
    version: string;
    lang: 'EN' | 'FR';

    // UI State
    avatarState: AvatarState;
    avatarDirection: AvatarDirection;
    aiQuote: string | null;
    pulseColor: string | null;

    // Activity
    stats: SystemStats;
    jobs: Jobs;
    jobActivity: JobActivity;
    jobLastLogTS: { trader: number; youtuber: number; influencer: number };

    // SOTA 2026: Sentinel States (8810 Header Buttons)
    stagedProjectsCount: number;
    evolutionReport: EvolutionReportState | null;

    // Console
    logs: any[];  // Log entries with source, level, etc.
    tokens: any[]; // Need to import TokenEntry type or use any for now
    activeTab: 'ALERTS' | 'TRINITY' | 'ANGEL' | 'JULES' | 'SOCIAL' | 'TRADER' | 'YOUTUBER' | 'INFLUENCER' | 'TOKENS';

    // Actions
    setStatus: (status: ConnectionStatus) => void;
    setVersion: (version: string) => void;
    setAvatarState: (state: AvatarState, direction?: AvatarDirection) => void;
    setPulse: (color: string | null) => void;
    setQuote: (quote: string) => void;
    setLang: (lang: 'EN' | 'FR') => void;
    addLog: (log: any) => void;
    addToken: (token: any) => void;

    // Console Actions
    setActiveTab: (tab: 'ALERTS' | 'TRINITY' | 'ANGEL' | 'JULES' | 'SOCIAL' | 'TRADER' | 'YOUTUBER' | 'INFLUENCER' | 'TOKENS') => void;
    clearLogs: (tab?: string) => void;

    updateStats: (stats: SystemStats) => void;
    updateJobs: (jobs: Partial<Jobs>) => void;
    updateActivity: (activity: Partial<JobActivity>) => void;

    // Sentinel Actions
    setStagedProjectsCount: (count: number) => void;
    setEvolutionReport: (report: EvolutionReportState | null) => void;
}

export const useTrinityStore = create<TrinityState>()(
    persist(
        (set) => ({
            status: 'offline',
            wsConnected: false,
            version: '',
            lang: 'EN',
            avatarState: 'idle',
            avatarDirection: 'down',
            aiQuote: null,
            pulseColor: null,

            jobs: {
                trader: false,
                youtuber: false,
                influencer: false
            },

            jobActivity: {
                trader: false,
                youtuber: false,
                influencer: false
            },



            stats: {
                cpu: '0',
                ram: 0,
                disk: 0,
                breakdown: {
                    angel: { name: 'Angel', ram: 0, cpu: 0 },
                    trinity: { name: 'Trinity', ram: 0, cpu: 0 },
                    ubuntu: { name: 'Ubuntu', ram: 0, cpu: 0 },
                    antigravity: { name: 'Antigravity', ram: 0, cpu: 0 },
                    other: { ram: 0, cpu: 0 }
                }
            },

            logs: [],
            tokens: [],
            activeTab: 'TRINITY',

            // SOTA 2026: Track last activity timestamp for each job (for UI blinking)
            jobLastLogTS: {
                trader: 0,
                youtuber: 0,
                influencer: 0
            },

            // SOTA 2026: Sentinel States (8810 Header Buttons)
            stagedProjectsCount: 0,
            evolutionReport: null,

            setStatus: (status) => set({ status }),
            setVersion: (version) => set({ version }),
            setAvatarState: (state, direction) => set((prev) => ({
                avatarState: state,
                avatarDirection: direction ?? prev.avatarDirection
            })),
            setPulse: (color) => set({ pulseColor: color }),
            setQuote: (quote) => set({ aiQuote: quote }),
            setLang: (lang) => set({ lang }),
            // SOTA 2026 FIX: Dedupe by timestamp+message (Check last 20 logs for interleaved streams)
            addLog: (log: any) => set((state) => {
                // Check last 20 logs for duplicates (to handle race conditions between trander/alerts streams)
                const recentLogs = state.logs.slice(-20);
                const isDuplicate = recentLogs.some(l => l.timestamp === log.timestamp && l.message === log.message);

                if (isDuplicate) {
                    return state;
                }

                // Detect Job Activity based on module string
                const mod = (log.module || log.source || '').toLowerCase();
                const activityUpdates = { ...state.jobLastLogTS };
                if (mod.includes('trader')) activityUpdates.trader = Date.now();
                if (mod.includes('youtuber')) activityUpdates.youtuber = Date.now();
                if (mod.includes('influencer')) activityUpdates.influencer = Date.now();

                return {
                    logs: [...state.logs.slice(-1999), log],
                    jobLastLogTS: activityUpdates
                };
            }),
            // SOTA 2026 FIX: Dedupe by timestamp+model to prevent duplicate tokens
            addToken: (token: any) => set((state) => {
                const last = state.tokens[state.tokens.length - 1];
                // Skip if exact duplicate of last token (same timestamp + model + total)
                if (last && last.timestamp === token.timestamp && last.model === token.model && last.total === token.total) {
                    return state; // No change
                }
                return { tokens: [...state.tokens.slice(-499), token] };
            }),

            setActiveTab: (tab) => set({ activeTab: tab }),
            clearLogs: (tab?: string) => set((state) => {
                if (!tab) return { logs: [], tokens: [] };
                // SOTA 2026 FIX: Handle TOKENS tab by clearing tokens array
                if (tab === 'TOKENS') {
                    return { tokens: [] };
                }
                // Filter out logs matching the tab - use same logic as filterLogsByTab in ConsolePanel
                return {
                    logs: state.logs.filter((log: any) => {
                        // Handle legacy string logs (belong to TRINITY tab)
                        if (typeof log === 'string') return tab !== 'TRINITY';

                        const source = (log.source || log.module || '').toUpperCase();

                        // Match logic from ConsolePanel.filterLogsByTab
                        if (tab === 'ALERTS') {
                            // Keep logs that are NOT alerts/errors
                            return !(source === 'ALERTS' || log.level === 'ERROR' || log.level === 'CRITICAL' || log.level === 'WARNING');
                        }
                        if (tab === 'ANGEL') {
                            // Keep logs that are NOT from ANGEL
                            return source !== 'ANGEL';
                        }
                        if (tab === 'TRINITY') {
                            // Keep logs that are NOT from TRINITY/SYSTEM/CORPUS/DNA (not JULES/SOCIAL)
                            return !(source.includes('TRINITY') || source === 'SYSTEM' || source.includes('CORPUS') || source.includes('DNA'));
                        }
                        if (tab === 'JULES') {
                            return !(source.includes('JULES') || source.includes('FORGE') || source.includes('COUNCIL'));
                        }
                        if (tab === 'SOCIAL') {
                            return !(source.includes('SOCIAL') || source.includes('TELEGRAM') || source.includes('DISCORD'));
                        }
                        // For jobs (TRADER, YOUTUBER, INFLUENCER) - source is already uppercase, tab is uppercase
                        return !source.includes(tab);
                    })
                };
            }),
            updateStats: (stats) => set({ stats: { ...stats, breakdown: stats.breakdown || { angel: { name: 'Angel', ram: 0, cpu: 0 }, trinity: { name: 'Trinity', ram: 0, cpu: 0 }, ubuntu: { name: 'Ubuntu', ram: 0, cpu: 0 }, antigravity: { name: 'Antigravity', ram: 0, cpu: 0 }, other: { ram: 0, cpu: 0 } } } }),
            updateJobs: (jobs) => set((state) => ({ jobs: { ...state.jobs, ...jobs } })),
            updateActivity: (activity) => set((state) => ({ jobActivity: { ...state.jobActivity, ...activity } })),

            // SOTA 2026: Sentinel Setters
            setStagedProjectsCount: (count) => set({ stagedProjectsCount: count }),
            setEvolutionReport: (report) => set({ evolutionReport: report })
        }),
        {
            name: 'trinity-lang',
            partialize: (state) => ({ lang: state.lang }),
        }
    )
);
