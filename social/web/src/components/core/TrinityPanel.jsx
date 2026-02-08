import React, { useState, useEffect, useCallback } from 'react';
import {
    Activity, Zap, DollarSign, Brain, Heart, Shield, Terminal,
    Power, RefreshCw, Cpu, Database, HardDrive, Thermometer,
    Cloud, Server, LayoutGrid, MessageSquare, Bell, Youtube, Twitter, HelpCircle, Settings,
    Rocket, Sun, Sunrise, Clock, Moon, BarChart3, Camera
} from 'lucide-react';
import { useTrinityStore } from '../../stores/trinityStore';
import { useJulesStore } from '../../stores/julesStore';
import { ANGEL_BASE_URL, getTrinityHeaders, stopTrinity } from '../../services/angelService';
import { PanelLayout, ResponsiveGrid, AdaptiveCard, ActionButtons, OptionToggle } from '../ui/PanelKit';

/**
 * TRINITY PANEL (SOTA V3)
 * The Consciousness Dashboard.
 * 
 * Visualizes:
 * 1. Brain State (Hormones)
 * 2. Physiology (Vitals)
 * 3. Economy (Treasury)
 * 4. Occupation (Jobs)
 */

const DICT = {
    en: {
        neurochemistry: 'NEUROCHEMISTRY',
        dopamine: 'DOPAMINE (Reward)',
        serotonin: 'SEROTONIN (Stability)',
        cortisol: 'CORTISOL (Stress)',
        systemVitals: 'SYSTEM VITALS',
        cpu: 'CPU',
        ram: 'RAM',
        disk: 'DISK',
        online: 'ONLINE',
        cloudHost: 'Cloud 1 (Host)',
        occupation: 'OCCUPATION',
        treasury: 'TREASURY',
        totalResources: 'Total Resources',
        gcpCredits: 'GCP Credits',
        tradingProfit: 'Trading Profit',
        youtubeProfit: 'YouTube Profit',
        influencerProfit: 'X (Social) Profit',
        infraRunrate: 'Infrastructure Run-rate',
        cumulativePnl: 'Cumulative PnL',
        activeCredits: 'Active Credits',
        cpuProcess: 'CPU PROCESS',
        ramProcess: 'RAM PROCESS',
    },
    fr: {
        neurochemistry: 'NEUROCHIMIE',
        dopamine: 'DOPAMINE (Récompense)',
        serotonin: 'SÉROTONINE (Stabilité)',
        cortisol: 'CORTISOL (Stress)',
        systemVitals: 'SIGNAUX VITAUX',
        cpu: 'CPU',
        ram: 'RAM',
        disk: 'DISQUE',
        online: 'EN LIGNE',
        cloudHost: 'Cloud 1 (Hôte)',
        occupation: 'OCCUPATION',
        treasury: 'TRÉSORERIE',
        totalResources: 'Ressources Totales',
        gcpCredits: 'Crédits GCP',
        tradingProfit: 'Profit Trading',
        youtubeProfit: 'Profit YouTube',
        influencerProfit: 'Profit X (Social)',
        infraRunrate: 'Coût Infrastructure',
        cumulativePnl: 'PnL Cumulé',
        activeCredits: 'Crédits Actifs',
        cpuProcess: 'PROCESSUS CPU',
        ramProcess: 'PROCESSUS RAM',
    }
};

export default function TrinityPanel() {
    const { locale, jobsStatus, setJobStatus, liveLogsEnabled, setLiveLogsEnabled, trinityState, setTrinityState, setShuttingDown, trinityStatus } = useTrinityStore();
    // SOTA 2026: Sync Jules toggle with JulesStore for sidebar indicator
    const { isActive: julesActive, setActive: setJulesActive } = useJulesStore();
    const t = DICT[locale] || DICT.fr;

    // SOTA 2026 Standard 362.80.1: Cache-First State Initialization (Hydration Sync)
    // Initialize directly from store to prevent blank panel flash
    const [vitals, setVitals] = useState(trinityState?.vitals || null);
    const [treasury, setTreasury] = useState(trinityState?.treasury || null);
    const [jobs, setJobs] = useState(trinityState?.jobs || null);
    const [triggers, setTriggers] = useState(trinityState?.triggers || null);
    const [loading, setLoading] = useState(!trinityState?.vitals); // Only show loading if no cache
    const [error, setError] = useState(false);

    // Actions State
    const [inputThink, setInputThink] = useState('');
    const [thinking, setThinking] = useState(false);
    const [thought, setThought] = useState(null);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [isApplying, setIsApplying] = useState(false);
    // SOTA 2026: Stop System state (moved from SettingsBar)
    const [confirmStop, setConfirmStop] = useState(false);
    const [isStopping, setIsStopping] = useState(false);

    // Trinity Core Config State - SOTA 2026 Standard 362.80.1: Cache-First
    const cachedConfig = trinityState?.config || {};
    const cachedBoot = cachedConfig.boot || {};
    const cachedSched = cachedConfig.scheduler || {};
    const [trinityConfig, setTrinityConfig] = useState(cachedConfig || null);
    // Boot Options - Cache-First
    const [optBootGreeting, setOptBootGreeting] = useState(cachedBoot.send_greeting ?? true);
    const [optBootAI, setOptBootAI] = useState(cachedBoot.greeting_use_ai ?? true);
    const [optBootPhoto, setOptBootPhoto] = useState(cachedBoot.greeting_with_photo ?? false);
    // Scheduler Notifications - Cache-First
    const [optMorningReflection, setOptMorningReflection] = useState(cachedSched.morning_reflection_enabled ?? true);
    const [optWakeup, setOptWakeup] = useState(cachedSched.wakeup_enabled ?? true);
    const [optNoonCheck, setOptNoonCheck] = useState(cachedSched.noon_check_enabled ?? true);
    const [optNightMode, setOptNightMode] = useState(cachedSched.night_mode_enabled ?? true);
    const [optPeriodicReports, setOptPeriodicReports] = useState(cachedSched.periodic_reports_enabled ?? true);
    const [tooltip, setTooltip] = useState(null);

    // SOTA 2026: Sync useState from store when trinityState changes (hydration + API refresh)
    useEffect(() => {
        if (!trinityState) return;
        // Sync display data from cache
        if (trinityState.vitals) setVitals(trinityState.vitals);
        if (trinityState.treasury) setTreasury(trinityState.treasury);
        if (trinityState.jobs) setJobs(trinityState.jobs);
        if (trinityState.triggers) setTriggers(trinityState.triggers);
        // Sync config options
        if (trinityState.config) {
            const boot = trinityState.config.boot || {};
            const sched = trinityState.config.scheduler || {};
            setOptBootGreeting(boot.send_greeting ?? true);
            setOptBootAI(boot.greeting_use_ai ?? true);
            setOptBootPhoto(boot.greeting_with_photo ?? false);
            setOptMorningReflection(sched.morning_reflection_enabled ?? true);
            setOptWakeup(sched.wakeup_enabled ?? true);
            setOptNoonCheck(sched.noon_check_enabled ?? true);
            setOptNightMode(sched.night_mode_enabled ?? true);
            setOptPeriodicReports(sched.periodic_reports_enabled ?? true);
        }
    }, [trinityState]);

    const fetchAllData = useCallback(async () => {
        try {
            setError(false);
            const headers = getTrinityHeaders();

            // Parallel Fetch with Fault Tolerance (SOTA 2026)
            const results = await Promise.allSettled([
                fetch(`${ANGEL_BASE_URL}/api/vitals`, { headers }),
                fetch(`${ANGEL_BASE_URL}/api/treasury`, { headers }),
                fetch(`${ANGEL_BASE_URL}/api/jobs`, { headers }),
                fetch(`${ANGEL_BASE_URL}/api/triggers`, { headers }),
                fetch(`${ANGEL_BASE_URL}/api/trinity/config`, { headers })
            ]);

            const [resVitals, resTreasury, resJobs, resTriggers, resConfig] = results;

            // Process Vitals
            if (resVitals.status === 'fulfilled' && resVitals.value.ok) {
                const vitalsData = await resVitals.value.json();
                setVitals(vitalsData);
                setTrinityState({ vitals: vitalsData });
            }

            // Process Treasury
            if (resTreasury.status === 'fulfilled' && resTreasury.value.ok) {
                const treasuryData = await resTreasury.value.json();
                setTreasury(treasuryData);
                setTrinityState({ treasury: treasuryData });
            } else if (resTreasury.status === 'fulfilled' && resTreasury.value.status === 401) {
                console.warn("Treasury Auth Failed - Check Token");
            }

            // Process Jobs
            if (resJobs.status === 'fulfilled' && resJobs.value.ok) {
                const jobsData = await resJobs.value.json();
                setJobs(jobsData);
                setTrinityState({ jobs: jobsData });
            }

            // Process Triggers
            if (resTriggers.status === 'fulfilled' && resTriggers.value.ok) {
                const data = await resTriggers.value.json();
                const triggersData = data.triggers || [];
                setTriggers(triggersData);
                setTrinityState({ triggers: triggersData });
            }

            // Process Trinity Config
            if (resConfig.status === 'fulfilled' && resConfig.value.ok) {
                const data = await resConfig.value.json();
                if (data.config) {
                    setTrinityConfig(data.config);
                    // SOTA 2026: Persist to store for cache
                    setTrinityState({ config: data.config });
                    // Boot Options (real config from scheduler.py)
                    const boot = data.config.boot || {};
                    setOptBootGreeting(boot.send_greeting ?? true);
                    setOptBootAI(boot.greeting_use_ai ?? true);
                    setOptBootPhoto(boot.greeting_with_photo ?? false);
                    // Scheduler Notifications (real config from scheduler.py)
                    const sched = data.config.scheduler || {};
                    setOptMorningReflection(sched.morning_reflection_enabled ?? true);
                    setOptWakeup(sched.wakeup_enabled ?? true);
                    setOptNoonCheck(sched.noon_check_enabled ?? true);
                    setOptNightMode(sched.night_mode_enabled ?? true);
                    setOptPeriodicReports(sched.periodic_reports_enabled ?? true);
                }
            }
        } catch (e) {
            console.error("Trinity Panel Sync Error:", e);
            // setError(true); // Don't fullblock UI, just show stale data or partials
        } finally {
            setLoading(false);
        }
    }, [setTrinityState]);

    // Initial Load & Polling (Standard 350: 3-minute interval like TraderPanel)
    // SOTA 2026: Guard with trinityStatus + 2s delay (Angel reports 'running' before FastAPI is ready)
    useEffect(() => {
        // SOTA 2026: Reset loading if Trinity is not running (prevents infinite "WAITING FOR DATA")
        if (trinityStatus !== 'running') {
            setLoading(false);
            return;
        }

        const timeoutId = setTimeout(() => {
            fetchAllData();
        }, 3000);

        const interval = setInterval(fetchAllData, 180000); // 3 min (aligned with other panels)

        return () => {
            clearTimeout(timeoutId);
            clearInterval(interval);
        };
    }, [trinityStatus, fetchAllData]);

    // Handlers (setJobStatus already imported via useTrinityStore destructuring)

    const toggleJob = async (jobName, currentState) => {
        const newState = !currentState;
        // SOTA 2026: Unified - ALL jobs use /jobs/toggle endpoint
        setJobStatus(jobName, newState);
        try {
            const res = await fetch(`${ANGEL_BASE_URL}/jobs/toggle?job=${jobName}&enabled=${newState}`, {
                method: 'POST',
                headers: getTrinityHeaders()
            });
            if (!res.ok) {
                setJobStatus(jobName, currentState);
                console.error(`[TrinityPanel] API error toggling ${jobName}`);
            }
        } catch (e) {
            setJobStatus(jobName, currentState);
            console.error(`Failed to toggle ${jobName}`, e);
        }
    };

    const toggleTrigger = async (name, currentState) => {
        try {
            const newState = !currentState;
            await fetch(`${ANGEL_BASE_URL}/api/triggers/toggle?name=${name}&enabled=${newState}`, {
                method: 'POST',
                headers: getTrinityHeaders()
            });
            await fetchAllData();
        } catch (e) {
            console.error(`Failed to toggle trigger ${name}`, e);
        }
    };

    // SOTA 2026: Stop System handler (moved from SettingsBar)
    // Standard 382.22: Immersive Shutdown Sequence
    const handleStopSystem = () => {
        if (isStopping) return;

        if (!confirmStop) {
            setConfirmStop(true);
            setTimeout(() => setConfirmStop(false), 3000);
            return;
        }

        // SOTA 2026: Trigger immersive shutdown sequence
        // VideoEngine will: play sleep video, then call stopTrinity() on video end
        setIsStopping(true);
        setShuttingDown(true);
    };

    // Apply Trinity Core Config (Boot + Scheduler) - SOTA 2026: Real config from scheduler.py
    const handleApplyConfig = async () => {
        setIsApplying(true);
        try {
            await fetch(`${ANGEL_BASE_URL}/api/trinity/config`, {
                method: 'POST',
                headers: getTrinityHeaders(),
                body: JSON.stringify({
                    boot: {
                        send_greeting: optBootGreeting,
                        greeting_use_ai: optBootAI,
                        greeting_with_photo: optBootPhoto
                    },
                    scheduler: {
                        morning_reflection_enabled: optMorningReflection,
                        wakeup_enabled: optWakeup,
                        noon_check_enabled: optNoonCheck,
                        night_mode_enabled: optNightMode,
                        periodic_reports_enabled: optPeriodicReports
                    }
                })
            });
            await fetchAllData();
        } catch (e) {
            console.error("Failed to apply Trinity config:", e);
        } finally {
            setIsApplying(false);
        }
    };

    const handleThink = async (e) => {
        e.preventDefault();
        if (!inputThink.trim()) return;

        setThinking(true);
        try {
            const res = await fetch(`${ANGEL_BASE_URL}/api/think`, {
                method: 'POST',
                headers: getTrinityHeaders(),
                body: JSON.stringify({ prompt: inputThink })
            });
            const data = await res.json();
            setThought(data.reply);
            setInputThink('');
        } catch (e) {
            console.error("Brain Error:", e);
        } finally {
            setThinking(false);
        }
    };

    // Components
    const ProgressBar = ({ value, color, label, sublabel }) => (
        <div className="flex flex-col gap-1 w-full">
            <div className="flex justify-between text-xs text-white/70">
                <span>{label}</span>
                <span>{sublabel || `${value}%`}</span>
            </div>
            <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                <div
                    className={`h-full transition-all duration-500 ${color}`}
                    style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
                />
            </div>
        </div>
    );

    const StatCard = ({ icon: Icon, label, value, subtext, color = "text-cyan-400" }) => (
        <div className="bg-black/40 border border-white/5 rounded-lg p-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
                <div className={`p-2 bg-white/5 rounded-lg ${color}`}>
                    <Icon size={18} />
                </div>
                <div>
                    <div className="text-white/50 text-[10px] uppercase font-bold tracking-wider">{label}</div>
                    <div className="text-white font-mono font-bold">{value}</div>
                </div>
            </div>
            {subtext && <div className="text-xs text-white/30">{subtext}</div>}
        </div>
    );

    // List Component for Details
    const VitalsDetailList = ({ data, type }) => (
        <div className="flex flex-col gap-1.5 w-full">
            <div className="text-[10px] font-bold text-white/30 uppercase tracking-wider mb-1 border-b border-white/5 pb-1">
                {type} PROCESS
            </div>
            {Object.entries(data || {}).map(([key, val]) => {
                const name = key.charAt(0).toUpperCase() + key.slice(1);
                const color = key === 'trinity' ? 'bg-red-500' : key === 'angel' ? 'bg-blue-500' : key === 'ubuntu' ? 'bg-green-500' : 'bg-emerald-400';
                const valueDisplay = type === 'RAM' ? `${(val.ram || 0).toFixed(0)} MB` : `${(val.cpu || 0).toFixed(0)}%`;
                return (
                    <div key={key} className="flex justify-between items-center text-xs">
                        <span className="flex items-center gap-1.5 text-white/70">
                            <span className={`w-1.5 h-1.5 rounded-full ${color}`} />
                            {name}
                        </span>
                        <span className="font-mono font-bold text-white/90">{valueDisplay}</span>
                    </div>
                );
            })}
        </div>
    );

    // SVG Circular Gauge (Semi-circle)
    const CircularGauge = ({ value, label, color = "text-cyan-400", subtext, isWarning = false }) => {
        const radius = 30;
        const circumference = 2 * Math.PI * radius;
        const halfCircumference = circumference / 2;
        const normalizedValue = Math.min(100, Math.max(0, value));
        // Progress fills from 0% to 100% of the half-circle
        const progressLength = (normalizedValue / 100) * halfCircumference;

        return (
            <div className="relative flex flex-col items-center justify-center p-2">
                <div className="relative w-20 h-10 overflow-hidden mb-1">
                    <svg className="w-20 h-20 rotate-180" viewBox="0 0 80 80">
                        {/* Background Path (Full Semi-circle) */}
                        <circle
                            cx="40"
                            cy="40"
                            r={radius}
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="6"
                            className="text-white/10"
                            strokeDasharray={`${halfCircumference} ${circumference}`}
                            strokeLinecap="round"
                        />
                        {/* Progress Path */}
                        <circle
                            cx="40"
                            cy="40"
                            r={radius}
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="6"
                            strokeLinecap="round"
                            className={`transition-all duration-1000 ease-out ${color} ${isWarning ? 'animate-pulse' : ''}`}
                            strokeDasharray={`${progressLength} ${circumference}`}
                        />
                    </svg>
                    <div className="absolute inset-0 flex items-end justify-center pb-0">
                        <span className={`text-sm font-bold ${color}`}>{value.toFixed(0)}%</span>
                    </div>
                </div>
                <div className="text-[10px] font-bold text-white/50 uppercase tracking-wider">{label}</div>
            </div>
        );
    };

    const VitalsTooltip = ({ title, data, type = 'CPU' }) => (
        <div className="absolute top-full left-1/2 -translate-x-1/2 mt-2 z-[100] min-w-[180px] bg-black/95 border border-white/10 rounded-lg p-3 shadow-2xl backdrop-blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none">
            <h4 className="text-[10px] font-bold text-white/40 mb-2 uppercase tracking-widest border-b border-white/5 pb-1">{title}</h4>
            <div className="space-y-1.5">
                {Object.entries(data || {}).map(([key, val]) => {
                    // Normalize key for display
                    const name = key.charAt(0).toUpperCase() + key.slice(1);
                    const color = key === 'trinity' ? 'bg-red-500' : key === 'angel' ? 'bg-blue-500' : key === 'ubuntu' ? 'bg-green-500' : 'bg-emerald-400';
                    const valueDisplay = type === 'RAM' ? `${(val.ram || 0).toFixed(0)} MB` : `${(val.cpu || 0).toFixed(0)}%`;

                    return (
                        <div key={key} className="flex justify-between items-center text-xs">
                            <span className="flex items-center gap-1.5 text-white/70">
                                <span className={`w-1.5 h-1.5 rounded-full ${color}`} />
                                {name}
                            </span>
                            <span className="font-mono font-bold text-white">{valueDisplay}</span>
                        </div>
                    );
                })}
            </div>
        </div>
    );

    // Derived Data
    const hormones = vitals?.emotions || { dopamine: 0, serotonin: 0, cortisol: 0, mood: 'NEUTRAL' };
    const cpu = vitals?.cpu || 0;
    const ram = vitals?.memory || 0;
    const disk = vitals?.disk || 0;

    // Treasury Data
    const totalResources = treasury?.total_resources || 0;
    const gcpCredits = treasury?.gcp_total || 0;
    const traderProfit = treasury?.trader_profit || 0;
    const youtubeProfit = treasury?.youtube_profit || 0;
    const influencerProfit = treasury?.influencer_profit || 0;
    const totalCash = treasury?.total_cash || 0;
    // SOTA 2026: Enriched FinOps Data (Standard 418)
    const burnRate = treasury?.burn_rate || 0;
    const daysRemaining = treasury?.days_remaining || 0;
    const vmStatus = treasury?.vm_status || 'N/A';
    const vmType = treasury?.vm_type || 'N/A';
    const monthSpend = treasury?.month_spend || 0;
    const topConsumers = treasury?.top_consumers || 'N/A';

    return (
        <PanelLayout
            isWaitingForData={loading}
            isError={error}
            onRetry={fetchAllData}
            headerTitle="CORE CONSCIOUSNESS"
            footer={
                <ActionButtons
                    onRefresh={async () => {
                        setIsRefreshing(true);
                        await fetchAllData();
                        setIsRefreshing(false);
                    }}
                    onApply={handleApplyConfig}
                    isRefreshing={isRefreshing}
                    isApplying={isApplying}
                    refreshLabel={locale === 'fr' ? 'RAFRAÎCHIR' : 'REFRESH'}
                    refreshingLabel={locale === 'fr' ? 'CHARGEMENT...' : 'REFRESHING...'}
                    applyLabel={locale === 'fr' ? 'APPLIQUER' : 'APPLY'}
                    applyingLabel={locale === 'fr' ? 'APPLICATION...' : 'APPLYING...'}
                />
            }
        >
            <ResponsiveGrid>

                {/* 1. SYSTEM VITALS (Col 1) */}
                <div className="flex flex-col gap-4">
                    <section className="bg-black/30 border border-white/10 rounded-xl p-4 flex flex-col gap-4">
                        <div className="flex items-center justify-between">
                            <h3 className="text-sm font-bold text-white/80 flex items-center gap-2">
                                <Heart size={16} className="text-green-400" /> {t.systemVitals}
                            </h3>
                        </div>

                        {/* GAUGES ROW */}
                        <div className="grid grid-cols-3 gap-2 border-b border-white/5 pb-4">
                            <div className="flex justify-center">
                                <CircularGauge
                                    value={cpu}
                                    label="CPU"
                                    color={cpu > 80 ? "text-yellow-400" : "text-green-500"}
                                    isWarning={cpu > 90}
                                />
                            </div>
                            <div className="flex justify-center">
                                <CircularGauge
                                    value={ram}
                                    label="RAM"
                                    color={ram > 80 ? "text-yellow-400" : "text-green-500"}
                                    isWarning={ram > 90}
                                />
                            </div>
                            <div className="flex justify-center">
                                <CircularGauge
                                    value={disk}
                                    label="DISK"
                                    color={disk > 90 ? "text-red-500" : "text-green-500"}
                                    isWarning={disk > 90}
                                />
                            </div>
                        </div>

                        {/* DETAILS ROW (Always Visible) */}
                        {vitals?.details && (
                            <div className="grid grid-cols-2 gap-4">
                                <div className="bg-black/40 rounded p-2 border border-white/5">
                                    <VitalsDetailList data={vitals.details} type="CPU" />
                                </div>
                                <div className="bg-black/40 rounded p-2 border border-white/5">
                                    <VitalsDetailList data={vitals.details} type="RAM" />
                                </div>
                            </div>
                        )}


                    </section>

                    {/* NEUROCHEMISTRY (moved to Col 1, after System Vitals) */}
                    <section className="bg-black/30 border border-white/10 rounded-xl p-4 flex flex-col gap-4 relative overflow-hidden group">
                        {/* Background Pulse */}
                        <div className={`absolute top-0 right-0 w-32 h-32 bg-${hormones.mood === 'STRESSED' ? 'red' : 'cyan'}-500/10 blur-[50px] rounded-full group-hover:bg-cyan-500/20 transition-all`} />

                        <div className="flex items-center justify-between z-10">
                            <h3 className="text-sm font-bold text-white/80 flex items-center gap-2">
                                <Brain size={16} className="text-pink-400 animate-pulse" /> {t.neurochemistry}
                            </h3>
                            <span className={`text-xs font-bold px-2 py-0.5 rounded bg-white/5
                                ${hormones.mood === 'ECSTATIC' ? 'text-yellow-400 shadow-[0_0_10px_rgba(250,204,21,0.3)]' :
                                    hormones.mood === 'STRESSED' ? 'text-red-400' : 'text-cyan-400'}`}>
                                {hormones.mood}
                            </span>
                        </div>

                        <div className="flex flex-col gap-3 z-10">
                            <ProgressBar
                                label={t.dopamine}
                                value={hormones.dopamine * 100}
                                color="bg-yellow-400 shadow-[0_0_10px_rgba(250,204,21,0.5)]"
                            />
                            <ProgressBar
                                label={t.serotonin}
                                value={hormones.serotonin * 100}
                                color="bg-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.5)]"
                            />
                            <ProgressBar
                                label={t.cortisol}
                                value={hormones.cortisol * 100}
                                color="bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)]"
                            />
                        </div>

                    </section>

                    {/* SYSTEM CONTROL - Stop only (moved to Col 1) */}
                    <section className="bg-black/30 border border-white/10 rounded-xl p-3">
                        <h3 className="text-sm font-bold text-white/80 flex items-center gap-2 mb-2">
                            <Terminal size={16} className="text-red-400" /> {locale === 'fr' ? 'CONTRÔLE SYSTÈME' : 'SYSTEM CONTROL'}
                        </h3>
                        <div className="flex flex-col gap-2">
                            {/* Stop System Button */}
                            <button
                                onClick={handleStopSystem}
                                disabled={isStopping}
                                className={`w-full py-3 px-3 rounded text-sm font-bold tracking-[0.2em] flex items-center justify-center gap-2 transition-all duration-300
                                    ${confirmStop
                                        ? 'bg-red-600 hover:bg-red-500 text-white animate-pulse shadow-[0_0_20px_rgba(220,38,38,0.8)]'
                                        : 'btn-neon-danger bg-red-500/10 text-red-400 hover:bg-red-500/20 hover:text-white'
                                    }`}
                            >
                                {isStopping ? (
                                    <span className="animate-pulse">{locale === 'fr' ? 'ARRÊT...' : 'STOPPING...'}</span>
                                ) : confirmStop ? (
                                    <>{locale === 'fr' ? 'CONFIRMER?' : 'CONFIRM?'}</>
                                ) : (
                                    <><Power size={12} /> {locale === 'fr' ? 'ARRÊTER SYSTÈME' : 'STOP SYSTEM'}</>
                                )}
                            </button>
                        </div>
                    </section>
                </div>

                {/* 2. OPERATIONS (Col 2) */}
                <div className="flex flex-col gap-4">
                    {/* JOBS (ex-OCCUPATION) - 2 columns INSIDE */}
                    <section className="bg-black/30 border border-white/10 rounded-xl p-3">
                        <h3 className="text-sm font-bold text-white/80 flex items-center gap-2 mb-2">
                            <LayoutGrid size={16} className="text-orange-400" /> JOBS
                        </h3>
                        <div className="grid grid-cols-2 gap-2">
                            {jobs && Object.entries(jobs).filter(([name]) => name.toLowerCase() !== 'jules').map(([name, data]) => {
                                // SOTA 2026: Use Zustand store for reactive UI (optimistic updates)
                                const isActive = jobsStatus[name.toLowerCase()] ?? data.active;
                                return (
                                    <OptionToggle
                                        key={name}
                                        icon={Power}
                                        label={name.toUpperCase()}
                                        value={isActive}
                                        onChange={() => toggleJob(name, isActive)}
                                        activeColor={isActive ? 'green' : 'red'}
                                    />
                                );
                            })}
                        </div>
                    </section>

                    {/* SERVICES - Jules + Live Logs */}
                    <section className="bg-black/30 border border-white/10 rounded-xl p-3">
                        <h3 className="text-sm font-bold text-white/80 flex items-center gap-2 mb-2">
                            <Zap size={16} className="text-cyan-400" /> SERVICES
                        </h3>
                        <div className="grid grid-cols-2 gap-2">
                            {/* Jules Toggle - SOTA 2026: Syncs with JulesStore for sidebar indicator */}
                            {(() => {
                                // Use JulesStore as source of truth
                                return (
                                    <OptionToggle
                                        icon={Power}
                                        label="JULES"
                                        value={julesActive}
                                        onChange={async () => {
                                            const newState = !julesActive;
                                            // Update JulesStore (primary)
                                            await setJulesActive(newState);
                                            // Also update TrinityStore for consistency
                                            setJobStatus('jules', newState);
                                        }}
                                        activeColor={julesActive ? 'cyan' : 'red'}
                                    />
                                );
                            })()}
                            {/* Live Logs Toggle */}
                            <OptionToggle
                                icon={Power}
                                label="LOGS"
                                value={liveLogsEnabled}
                                onChange={() => setLiveLogsEnabled(!liveLogsEnabled)}
                                activeColor={liveLogsEnabled ? 'cyan' : 'red'}
                            />
                        </div>
                    </section>
                    {/* NOTIFICATION CHANNELS - Static status indicators (read-only) */}
                    <section className="bg-black/30 border border-white/10 rounded-xl p-3">
                        <h3 className="text-sm font-bold text-white/80 flex items-center gap-2 mb-2">
                            <MessageSquare size={16} className="text-cyan-400" /> {locale === 'fr' ? 'CANAUX NOTIFS' : 'NOTIFICATION CHANNELS'}
                        </h3>
                        <div className="grid grid-cols-2 gap-2">
                            {/* Android - Status Badge (non-interactive) */}
                            <div className="flex items-center justify-between px-3 py-2 bg-black/40 rounded-lg border border-green-500/30">
                                <span className="text-xs font-bold text-white/80 flex items-center gap-2">
                                    <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                                    📱 ANDROID
                                </span>
                                <span className="text-[10px] font-bold text-green-400 bg-green-500/10 px-2 py-0.5 rounded">ON</span>
                            </div>
                            {/* Web - Status Badge (non-interactive) */}
                            <div className="flex items-center justify-between px-3 py-2 bg-black/40 rounded-lg border border-green-500/30">
                                <span className="text-xs font-bold text-white/80 flex items-center gap-2">
                                    <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                                    🌐 WEB
                                </span>
                                <span className="text-[10px] font-bold text-green-400 bg-green-500/10 px-2 py-0.5 rounded">ON</span>
                            </div>
                        </div>
                    </section>

                    {/* OPTIONS - Boot Configuration */}
                    <section className="bg-black/30 border border-white/10 rounded-lg p-3">
                        <h3 className="text-sm font-bold text-white/80 mb-2 flex items-center gap-1.5">
                            <Settings size={14} className="text-violet-400" /> {locale === 'fr' ? 'OPTIONS' : 'OPTIONS'}
                        </h3>
                        <div className="grid grid-cols-2 gap-2">
                            <OptionToggle
                                icon={Brain}
                                label={locale === 'fr' ? 'AI Notifs' : 'AI Notifs'}
                                value={optBootAI}
                                onChange={() => setOptBootAI(!optBootAI)}
                                activeColor="violet"
                                tooltip={locale === 'fr' ? 'Messages IA enrichis (sinon basiques)' : 'AI-enriched messages (else basic)'}
                                isTooltipActive={tooltip === 'opt_bootAI'}
                                onTooltipEnter={() => setTooltip('opt_bootAI')}
                                onTooltipLeave={() => setTooltip(null)}
                            />
                            <OptionToggle
                                icon={Camera}
                                label={locale === 'fr' ? 'Photo Notifs' : 'Photo Notifs'}
                                value={optBootPhoto}
                                onChange={() => setOptBootPhoto(!optBootPhoto)}
                                activeColor="rose"
                                tooltip={locale === 'fr' ? 'Photo de profil dans les notifications' : 'Profile photo in notifications'}
                                isTooltipActive={tooltip === 'opt_bootPhoto'}
                                onTooltipEnter={() => setTooltip('opt_bootPhoto')}
                                onTooltipLeave={() => setTooltip(null)}
                            />
                        </div>
                    </section>

                    {/* NOTIFICATIONS - Scheduler Events (SOTA 2026: Real config from scheduler.py) */}
                    <section className="bg-black/30 border border-white/10 rounded-lg p-3">
                        <h3 className="text-sm font-bold text-white/80 mb-2 flex items-center gap-1.5">
                            <Bell size={14} className="text-cyan-400" /> {locale === 'fr' ? 'NOTIFICATIONS' : 'NOTIFICATIONS'}
                        </h3>
                        <div className="grid grid-cols-2 gap-2">
                            <OptionToggle
                                icon={Rocket}
                                label={locale === 'fr' ? 'Boot Msg' : 'Boot Msg'}
                                value={optBootGreeting}
                                onChange={() => setOptBootGreeting(!optBootGreeting)}
                                activeColor="cyan"
                                tooltip={locale === 'fr' ? 'Message au démarrage' : 'Startup message'}
                                isTooltipActive={tooltip === 'opt_bootGreeting'}
                                onTooltipEnter={() => setTooltip('opt_bootGreeting')}
                                onTooltipLeave={() => setTooltip(null)}
                            />
                            <OptionToggle
                                icon={Sunrise}
                                label={locale === 'fr' ? 'Rapport 6h' : 'Morning 6h'}
                                value={optMorningReflection}
                                onChange={() => setOptMorningReflection(!optMorningReflection)}
                                activeColor="yellow"
                                tooltip={locale === 'fr' ? 'Évolution SOTA matinale' : 'Morning SOTA evolution'}
                                isTooltipActive={tooltip === 'opt_morning'}
                                onTooltipEnter={() => setTooltip('opt_morning')}
                                onTooltipLeave={() => setTooltip(null)}
                            />
                            <OptionToggle
                                icon={Sun}
                                label={locale === 'fr' ? 'Réveil 8h' : 'Wakeup 8h'}
                                value={optWakeup}
                                onChange={() => setOptWakeup(!optWakeup)}
                                activeColor="orange"
                                tooltip={locale === 'fr' ? 'Message de réveil' : 'Wakeup message'}
                                isTooltipActive={tooltip === 'opt_wakeup'}
                                onTooltipEnter={() => setTooltip('opt_wakeup')}
                                onTooltipLeave={() => setTooltip(null)}
                            />
                            <OptionToggle
                                icon={Clock}
                                label={locale === 'fr' ? 'Midi 12h' : 'Noon 12h'}
                                value={optNoonCheck}
                                onChange={() => setOptNoonCheck(!optNoonCheck)}
                                activeColor="blue"
                                tooltip={locale === 'fr' ? 'Point de mi-journée' : 'Midday check'}
                                isTooltipActive={tooltip === 'opt_noon'}
                                onTooltipEnter={() => setTooltip('opt_noon')}
                                onTooltipLeave={() => setTooltip(null)}
                            />
                            <OptionToggle
                                icon={Moon}
                                label={locale === 'fr' ? 'Nuit 22h' : 'Night 22h'}
                                value={optNightMode}
                                onChange={() => setOptNightMode(!optNightMode)}
                                activeColor="indigo"
                                tooltip={locale === 'fr' ? 'Mode nuit et rêves' : 'Night mode and dreams'}
                                isTooltipActive={tooltip === 'opt_night'}
                                onTooltipEnter={() => setTooltip('opt_night')}
                                onTooltipLeave={() => setTooltip(null)}
                            />
                            <OptionToggle
                                icon={BarChart3}
                                label={locale === 'fr' ? 'Jobs Report' : 'Jobs Report'}
                                value={optPeriodicReports}
                                onChange={() => setOptPeriodicReports(!optPeriodicReports)}
                                activeColor="green"
                                tooltip={locale === 'fr' ? 'Alertes démarrage/arrêt/crash des jobs' : 'Job start/stop/crash alerts'}
                                isTooltipActive={tooltip === 'opt_reports'}
                                onTooltipEnter={() => setTooltip('opt_reports')}
                                onTooltipLeave={() => setTooltip(null)}
                            />
                        </div>
                    </section>
                </div>

                {/* 3. ECONOMY (Col 3) */}
                <div className="flex flex-col gap-4">
                    <section className="bg-black/30 border border-white/10 rounded-xl p-4 flex flex-col gap-3 h-full">
                        <h3 className="text-sm font-bold text-white/80 flex items-center gap-2 mb-2">
                            <DollarSign size={16} className="text-yellow-400" /> {t.treasury}
                        </h3>

                        {/* HERO METRICS - Two columns: Resources + Runway */}
                        <div className="grid grid-cols-2 gap-2 mb-2">
                            {/* Total Resources */}
                            <div className="p-3 bg-gradient-to-br from-yellow-500/10 to-transparent border border-yellow-500/20 rounded-xl flex flex-col items-center justify-center">
                                <span className="text-[10px] text-yellow-500/70 uppercase tracking-[0.15em] font-bold mb-1">{t.totalResources}</span>
                                <span className="text-2xl font-bold text-white drop-shadow-[0_0_10px_rgba(234,179,8,0.3)]">
                                    {totalResources.toFixed(0)}€
                                </span>
                            </div>
                            {/* Runway */}
                            <div className="p-3 bg-gradient-to-br from-green-500/10 to-transparent border border-green-500/20 rounded-xl flex flex-col items-center justify-center">
                                <span className="text-[10px] text-green-400/70 uppercase tracking-[0.15em] font-bold mb-1">RUNWAY</span>
                                <span className="text-2xl font-bold text-white">
                                    {daysRemaining.toFixed(0)} <span className="text-sm text-white/60">{locale === 'fr' ? 'j' : 'd'}</span>
                                </span>
                                <span className="text-[9px] text-white/40">@ {burnRate.toFixed(2)}€/{locale === 'fr' ? 'j' : 'd'}</span>
                            </div>
                        </div>

                        {/* GCP INFRASTRUCTURE - VM + Credits with value only */}
                        <div className="p-3 bg-black/40 rounded-lg border border-blue-500/20 space-y-2">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <Cloud size={14} className="text-blue-400" />
                                    <span className="text-[10px] font-bold text-white/50 uppercase tracking-wider">GCP</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className={`w-2 h-2 rounded-full ${vmStatus === 'RUNNING' ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
                                    <span className="text-[10px] font-mono text-white/60">{vmType}</span>
                                </div>
                            </div>
                            {treasury?.gcp_credits_details?.filter(c => c.valeur > 0).map((c, i) => (
                                <ProgressBar
                                    key={i}
                                    label={c.nom}
                                    value={(c.valeur / 300) * 100}
                                    sublabel={`${c.valeur.toFixed(0)}€`}
                                    color="bg-blue-500"
                                />
                            ))}
                        </div>

                        {/* GEMINI API KEYS */}
                        <div className="p-3 bg-black/40 rounded-lg border border-violet-500/20 space-y-2">
                            <div className="flex items-center gap-2">
                                <Brain size={14} className="text-violet-400" />
                                <span className="text-[10px] font-bold text-white/50 uppercase tracking-wider">GEMINI</span>
                            </div>
                            {treasury?.gcp_credits_details?.filter(c => c.valeur === 0).map((c, i) => (
                                <div key={i} className="flex items-center justify-between py-1 px-2 bg-black/40 rounded border border-white/5">
                                    <span className="text-xs text-white/70">{c.nom}</span>
                                    <span className="text-[10px] font-bold text-green-400 bg-green-500/10 px-2 py-0.5 rounded">ACTIF</span>
                                </div>
                            ))}
                        </div>

                        {/* REVENUE STREAMS */}
                        <StatCard
                            icon={Zap}
                            label={t.tradingProfit}
                            value={`${traderProfit > 0 ? '+' : ''}${traderProfit.toFixed(2)}€`}
                            subtext={t.cumulativePnl}
                            color={traderProfit >= 0 ? "text-green-400" : "text-red-400"}
                        />
                        <StatCard
                            icon={Youtube}
                            label={t.youtubeProfit}
                            value={`${youtubeProfit > 0 ? '+' : ''}${youtubeProfit.toFixed(2)}€`}
                            subtext="Revenus AdSense"
                            color={youtubeProfit >= 0 ? "text-green-400" : "text-white/40"}
                        />
                        <StatCard
                            icon={Twitter}
                            label={t.influencerProfit}
                            value={`${influencerProfit > 0 ? '+' : ''}${influencerProfit.toFixed(2)}€`}
                            subtext="Revenus Sponsors"
                            color={influencerProfit >= 0 ? "text-green-400" : "text-white/40"}
                        />
                    </section>
                </div>

            </ResponsiveGrid>
        </PanelLayout >
    );
}
