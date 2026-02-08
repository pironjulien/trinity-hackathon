import React, { useEffect, useState, useCallback } from 'react';
import {
    CheckCircle2, Clock, XCircle, GitMerge, Shield, Sparkles, Eye, FlaskConical,
    RefreshCw, FileCheck, Zap, Inbox, ExternalLink, TrendingUp, Bell, BellOff,
    Calendar, Target, Activity, GitPullRequest, History, AlertTriangle
} from 'lucide-react';
import { useJulesStore } from '../../stores/julesStore';
import { useTrinityStore } from '../../stores/trinityStore';
import { Section, OptionToggle, PanelLayout, ActionButtons, ResponsiveGrid, Column } from '../ui/PanelKit';
import { getTrinityHeaders } from '../../services/angelService';

// SOTA 2026: Option Help Tooltips (harmonized with TraderPanel/InfluencerPanel)
const OPTION_HELP = {
    en: {
        self_review: { label: 'Self-Review', help: 'Jules reviews his own code before submitting. Catches bugs and improves quality.' },
        self_evolution: { label: 'Self-Evolution', help: 'Jules can autonomously improve his own codebase. Experimental feature.' },
        nightwatch: { label: 'Nightwatch', help: 'Overnight monitoring of pending PRs. Ensures nothing is forgotten.' },
        sandbox_mode: { label: 'Sandbox', help: 'Executes code in an isolated environment. Safer for untested changes.' },
        require_plan_approval: { label: 'Plan Approval', help: 'Requires your approval before every implementation plan. More control.' },
        auto_repoless: { label: 'Auto Repoless', help: 'Automatic repo cloning for each session. Fresh environment every time.' },
        on_pr_created: { label: 'PR Created', help: 'Push notification when a new PR is created by Jules.' },
        on_pr_merged: { label: 'PR Merged', help: 'Push notification when a PR is merged into main branch.' },
        on_council_complete: { label: 'Council Done', help: 'Push notification when the nightly Council completes its review.' },
        on_mission_failed: { label: 'Mission Failed', help: 'Push notification when a mission fails or encounters an error.' }
    },
    fr: {
        self_review: { label: 'Self-Review', help: 'Jules revoit son propre code avant soumission. Détecte les bugs et améliore la qualité.' },
        self_evolution: { label: 'Self-Evolution', help: 'Jules peut améliorer son propre code de manière autonome. Fonctionnalité expérimentale.' },
        nightwatch: { label: 'Nightwatch', help: 'Surveillance nocturne des PR en attente. Garantit que rien n\'est oublié.' },
        sandbox_mode: { label: 'Sandbox', help: 'Exécute le code dans un environnement isolé. Plus sûr pour les changements non testés.' },
        require_plan_approval: { label: 'Plan Approval', help: 'Requiert votre approbation avant chaque plan d\'implémentation. Plus de contrôle.' },
        auto_repoless: { label: 'Auto Repoless', help: 'Clone automatique du repo pour chaque session. Environnement propre à chaque fois.' },
        on_pr_created: { label: 'PR Créée', help: 'Notification push quand une nouvelle PR est créée par Jules.' },
        on_pr_merged: { label: 'PR Merge', help: 'Notification push quand une PR est fusionnée dans la branche principale.' },
        on_council_complete: { label: 'Council OK', help: 'Notification push quand le Council nocturne termine sa revue.' },
        on_mission_failed: { label: 'Échec', help: 'Notification push quand une mission échoue ou rencontre une erreur.' }
    }
};

/**
 * JULES PANEL (SOTA 2026 - ENRICHED)
 * ═══════════════════════════════════════════════════════════════════════════
 * Full-featured panel matching Trader/Influencer/YouTuber richness.
 * Real data, notifications, Council stats, and PR history.
 * ═══════════════════════════════════════════════════════════════════════════
 */
export default function JulesPanel() {
    const {
        isLoading,
        projects,
        pendingProjects,
        stagedProjects,
        fetchStatus,
        fetchMorningBrief,
        fetchPending,
        fetchStagedProjects,
        sendDecision,
        // SOTA 2026: Council Control
        councilRunning,
        councilStartedAt,
        startCouncil,
        fetchCouncilStatus
    } = useJulesStore();

    // SOTA 2026 Standard 362.80.1: Get store FIRST for Cache-First initialization
    const { julesState, setJulesState, locale } = useTrinityStore();

    // Options state - Cache-First (Hydration Sync)
    const defaultOptions = {
        self_review: true,
        self_evolution: false,
        nightwatch: true,
        sandbox_mode: true,
        require_plan_approval: false,
        auto_repoless: true,
        target_prs_per_night: 3,
        max_attempts: 10
    };
    const [options, setOptions] = useState(julesState?.options || defaultOptions);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [isApplying, setIsApplying] = useState(false);
    const [selectedProject, setSelectedProject] = useState(null); // For detail popup

    // Stats counters - Cache-First (Hydration Sync)
    const [stats, setStats] = useState(julesState?.stats || {
        accepted: 0,
        pending: pendingProjects.length,
        rejected: 0
    });

    // NEW: Council stats
    const [councilStats, setCouncilStats] = useState(julesState?.councilStats || {
        last_council_date: null,
        success_rate: 0,
        avg_score: 0,
        total_missions: 0,
        total_prs_created: 0
    });

    // NEW: History (merged/rejected)
    const [history, setHistory] = useState(julesState?.history || { merged: [], rejected: [] });

    // NEW: Notifications config
    const defaultNotifications = {
        on_pr_created: true,
        on_pr_merged: true,
        on_council_complete: true,
        on_mission_failed: false
    };
    const [notifications, setNotifications] = useState(julesState?.notifications || defaultNotifications);

    // SOTA 2026: Tooltip state for OptionToggle (harmonized with TraderPanel/InfluencerPanel)
    const [tooltip, setTooltip] = useState(null);
    const optHelp = OPTION_HELP[locale] || OPTION_HELP.en;

    // Fetch options from backend
    const fetchOptions = useCallback(async () => {
        try {
            const res = await fetch('/api/jules/options', {
                headers: getTrinityHeaders()
            });
            if (res.ok) {
                const data = await res.json();
                setOptions(data);
                setJulesState({ options: data });
            }
        } catch (e) {
            console.error('Failed to fetch Jules options:', e);
        }
    }, [setJulesState]);

    // Fetch stats from backend
    const fetchStats = useCallback(async () => {
        try {
            const res = await fetch('/api/jules/stats', {
                headers: getTrinityHeaders()
            });
            if (res.ok) {
                const data = await res.json();
                const newStats = {
                    accepted: data.accepted || 0,
                    pending: data.pending || pendingProjects.length,
                    rejected: data.rejected || 0
                };
                setStats(newStats);
                setJulesState({ stats: newStats });
            }
        } catch (e) {
            setStats({
                accepted: 0,
                pending: pendingProjects.length,
                rejected: 0
            });
        }
    }, [pendingProjects.length, setJulesState]);

    // NEW: Fetch council stats
    const fetchCouncilStats = useCallback(async () => {
        try {
            const res = await fetch('/api/jules/council-stats', {
                headers: getTrinityHeaders()
            });
            if (res.ok) {
                const data = await res.json();
                setCouncilStats(data);
                setJulesState({ councilStats: data });
            }
        } catch (e) {
            console.error('Failed to fetch council stats:', e);
        }
    }, [setJulesState]);

    // NEW: Fetch history
    const fetchHistory = useCallback(async () => {
        try {
            const res = await fetch('/api/jules/history', {
                headers: getTrinityHeaders()
            });
            if (res.ok) {
                const data = await res.json();
                setHistory(data);
                setJulesState({ history: data });
            }
        } catch (e) {
            console.error('Failed to fetch history:', e);
        }
    }, [setJulesState]);

    // NEW: Fetch notifications config
    const fetchNotifications = useCallback(async () => {
        try {
            const res = await fetch('/api/jules/notifications', {
                headers: getTrinityHeaders()
            });
            if (res.ok) {
                const data = await res.json();
                setNotifications(data);
                setJulesState({ notifications: data });
            }
        } catch (e) {
            console.error('Failed to fetch notifications:', e);
        }
    }, [setJulesState]);

    // Sync useState from store when julesState changes
    useEffect(() => {
        if (!julesState?.options) return;
        setOptions(julesState.options);
    }, [julesState]);

    // Fetch data on mount + polling
    useEffect(() => {
        fetchStatus();
        fetchMorningBrief();
        fetchPending();
        fetchStagedProjects();
        fetchOptions();
        fetchStats();
        fetchCouncilStats();
        fetchCouncilStatus(); // SOTA 2026: Also fetch council running state
        fetchHistory();
        fetchNotifications();

        // Poll every 3 minutes
        const interval = setInterval(() => {
            fetchStatus();
            fetchMorningBrief();
            fetchPending();
            fetchStagedProjects();
            fetchStats();
            fetchCouncilStats();
            fetchCouncilStatus(); // SOTA 2026: Sync council running state
        }, 180000);

        return () => clearInterval(interval);
    }, [fetchStatus, fetchMorningBrief, fetchPending, fetchStagedProjects, fetchOptions, fetchStats, fetchCouncilStats, fetchCouncilStatus, fetchHistory, fetchNotifications]);

    // SOTA 2026: Fast poll council status when running (every 10s)
    useEffect(() => {
        if (!councilRunning) return;

        const fastInterval = setInterval(() => {
            fetchCouncilStatus();
        }, 10000);

        return () => clearInterval(fastInterval);
    }, [councilRunning, fetchCouncilStatus]);

    // Handle refresh
    const handleRefresh = useCallback(async () => {
        setIsRefreshing(true);
        try {
            await Promise.all([
                fetchStatus(),
                fetchMorningBrief(),
                fetchPending(),
                fetchStagedProjects(),
                fetchOptions(),
                fetchStats(),
                fetchCouncilStats(),
                fetchHistory(),
                fetchNotifications()
            ]);
        } finally {
            setIsRefreshing(false);
        }
    }, [fetchStatus, fetchMorningBrief, fetchPending, fetchStagedProjects, fetchOptions, fetchStats, fetchCouncilStats, fetchHistory, fetchNotifications]);

    // Handle apply (save options + notifications)
    const handleApply = useCallback(async () => {
        setIsApplying(true);
        try {
            await Promise.all([
                fetch('/api/jules/options', {
                    method: 'POST',
                    headers: getTrinityHeaders(),
                    body: JSON.stringify(options)
                }),
                fetch('/api/jules/notifications', {
                    method: 'POST',
                    headers: { ...getTrinityHeaders(), 'Content-Type': 'application/json' },
                    body: JSON.stringify(notifications)
                })
            ]);
        } catch (e) {
            console.error('Failed to save Jules settings:', e);
        } finally {
            setIsApplying(false);
        }
    }, [options, notifications]);

    // Handle option toggle
    const handleOptionToggle = (key, value) => {
        setOptions(prev => ({ ...prev, [key]: value }));
    };

    // Handle notification toggle
    const handleNotificationToggle = (key, value) => {
        setNotifications(prev => ({ ...prev, [key]: value }));
    };

    // Handle project decision
    const handleDecision = async (projectId, decision, prUrl, isStaged = false) => {
        await sendDecision(projectId, decision, prUrl, isStaged);
        setTimeout(() => {
            fetchMorningBrief();
            fetchPending();
            fetchStagedProjects();
            fetchStats();
            fetchHistory();
        }, 500);
    };

    // SOTA 2026: With autonomous nightly pipeline, projects arrive already coded (staged)
    const waitingProjects = projects.filter(p => p.status === 'WAITING_DECISION').slice(0, 3);

    // Filter staged projects: exclude those already marked as PENDING
    const activeStaged = stagedProjects.filter(p => p.status !== 'PENDING');

    // Priority: Active staged projects first (already coded), then any waiting legacy projects
    const projectsToValidate = [
        ...activeStaged.map(p => ({ ...p, isStaged: true })),
        ...waitingProjects.map(p => ({ ...p, isStaged: false }))
    ].slice(0, 5);

    // Projects user has put ON HOLD (clicked "Attente")
    const onHoldProjects = stagedProjects.filter(p => p.status === 'PENDING');

    // Format date for display
    const formatDate = (dateStr) => {
        if (!dateStr) return 'N/A';
        try {
            const date = new Date(dateStr);
            return date.toLocaleDateString(locale === 'fr' ? 'fr-FR' : 'en-US', {
                day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
            });
        } catch {
            return dateStr;
        }
    };

    // Confidence badge
    const ConfidenceBadge = ({ value }) => {
        if (value === undefined || value === null) return null;
        const color = value >= 80 ? 'bg-green-500/20 text-green-400 border-green-500/30'
            : value >= 60 ? 'bg-amber-500/20 text-amber-400 border-amber-500/30'
                : 'bg-red-500/20 text-red-400 border-red-500/30';
        return (
            <span className={`px-2 py-0.5 text-xs font-bold rounded border ${color}`}>
                {value}%
            </span>
        );
    };

    // ENRICHED Project Card with full description
    const ProjectCard = ({ project, isStaged = false }) => (
        <div className={`bg-black/40 border rounded-lg p-3 transition-all ${isStaged ? 'border-green-500/30 hover:border-green-500/50' : 'border-white/10 hover:border-cyan-500/30'}`}>
            {/* Header */}
            <div className="flex items-start justify-between gap-2 mb-2">
                <h4 className="text-sm font-bold text-white/90 flex-1 line-clamp-1">
                    {project.title}
                </h4>
                <div className="flex gap-1">
                    {isStaged && (project.score || project.quality_score) && (
                        <span className="px-2 py-0.5 text-xs font-bold rounded bg-purple-500/20 text-purple-400 border border-purple-500/30">
                            {project.quality_score || project.score}%
                        </span>
                    )}
                    {isStaged ? (
                        <span className="px-2 py-0.5 text-xs font-bold rounded bg-green-500/20 text-green-400 border border-green-500/30">
                            {project.files_count || 0} files
                        </span>
                    ) : (
                        <ConfidenceBadge value={project.confidence || 0} />
                    )}
                </div>
            </div>

            {/* Full Description */}
            <p className="text-xs text-white/60 mb-2 line-clamp-3">
                {project.description || project.rationale || 'No description'}
            </p>

            {/* Stats for staged projects */}
            {isStaged && (project.additions > 0 || project.deletions > 0) && (
                <div className="text-xs text-white/40 mb-2">
                    <span className="text-green-400">+{project.additions || 0}</span>
                    {' / '}
                    <span className="text-red-400">-{project.deletions || 0}</span>
                    {' lines'}
                </div>
            )}

            {/* PR Link if available */}
            {project.pr_url && (
                <a
                    href={project.pr_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-cyan-400 hover:text-cyan-300 mb-2"
                >
                    <GitPullRequest size={10} /> {locale === 'fr' ? 'Voir PR' : 'View PR'} <ExternalLink size={10} />
                </a>
            )}

            {/* Actions: Eye + 3 buttons */}
            <div className="flex gap-2">
                {isStaged && (
                    <button
                        onClick={() => setSelectedProject(project)}
                        className="py-1.5 px-2 text-xs font-bold rounded bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 hover:bg-cyan-500/30 transition-all flex items-center justify-center gap-1"
                        title={locale === 'fr' ? 'Voir détails' : 'View details'}
                    >
                        <Eye size={12} />
                    </button>
                )}
                <button
                    onClick={() => handleDecision(project.id, 'MERGE', project.pr_url, isStaged)}
                    className="flex-1 py-1.5 px-2 text-xs font-bold rounded bg-green-500/20 text-green-400 border border-green-500/30 hover:bg-green-500/30 transition-all flex items-center justify-center gap-1"
                >
                    <CheckCircle2 size={12} /> {locale === 'fr' ? 'Approuver' : 'Approve'}
                </button>
                <button
                    onClick={() => handleDecision(project.id, 'PENDING', project.pr_url, isStaged)}
                    className="flex-1 py-1.5 px-2 text-xs font-bold rounded bg-amber-500/20 text-amber-400 border border-amber-500/30 hover:bg-amber-500/30 transition-all flex items-center justify-center gap-1"
                >
                    <Clock size={12} /> {locale === 'fr' ? 'Attente' : 'Later'}
                </button>
                <button
                    onClick={() => handleDecision(project.id, 'REJECT', project.pr_url, isStaged)}
                    className="flex-1 py-1.5 px-2 text-xs font-bold rounded bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30 transition-all flex items-center justify-center gap-1"
                >
                    <XCircle size={12} /> {locale === 'fr' ? 'Rejeter' : 'Reject'}
                </button>
            </div>
        </div>
    );

    // MODAL: Full project details
    const DetailModal = ({ project, onClose }) => {
        if (!project) return null;
        return (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" onClick={onClose}>
                <div className="bg-slate-900 border border-cyan-500/30 rounded-xl p-6 max-w-lg w-full mx-4 shadow-2xl" onClick={e => e.stopPropagation()}>
                    {/* Header */}
                    <div className="flex items-start justify-between mb-4">
                        <h3 className="text-lg font-bold text-cyan-400">{project.title}</h3>
                        <button onClick={onClose} className="text-white/50 hover:text-white text-xl">×</button>
                    </div>

                    {/* Badges */}
                    <div className="flex gap-2 mb-4 flex-wrap">
                        {(project.quality_score || project.score) && (
                            <span className="px-3 py-1 text-sm font-bold rounded bg-purple-500/20 text-purple-400 border border-purple-500/30">
                                {project.quality_score || project.score}% Qualité
                            </span>
                        )}
                        <span className="px-3 py-1 text-sm font-bold rounded bg-green-500/20 text-green-400 border border-green-500/30">
                            {project.files_count || 0} fichiers
                        </span>
                        {(project.additions > 0 || project.deletions > 0) && (
                            <span className="px-3 py-1 text-sm font-bold rounded bg-blue-500/20 text-blue-400 border border-blue-500/30">
                                +{project.additions || 0} / -{project.deletions || 0} lignes
                            </span>
                        )}
                    </div>

                    {/* Full Description */}
                    <div className="mb-4">
                        <h4 className="text-xs font-bold text-white/50 uppercase mb-2">Description</h4>
                        <p className="text-sm text-white/80 leading-relaxed">{project.description || 'Aucune description'}</p>
                    </div>

                    {/* Meta */}
                    <div className="mb-4 text-xs text-white/40">
                        <div>ID: {project.id}</div>
                        <div>Staged: {project.staged_at}</div>
                    </div>

                    {/* PR Link */}
                    {project.pr_url && (
                        <a
                            href={project.pr_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-2 mb-4 text-sm text-cyan-400 hover:text-cyan-300"
                        >
                            <GitPullRequest size={14} /> Voir la Pull Request <ExternalLink size={12} />
                        </a>
                    )}

                    {/* Actions */}
                    <div className="flex gap-3 mt-4">
                        <button
                            onClick={() => { handleDecision(project.id, 'MERGE', project.pr_url, true); onClose(); }}
                            className="flex-1 py-2 px-4 text-sm font-bold rounded bg-green-500/20 text-green-400 border border-green-500/30 hover:bg-green-500/30 transition-all flex items-center justify-center gap-2"
                        >
                            <CheckCircle2 size={16} /> Approuver
                        </button>
                        <button
                            onClick={() => { handleDecision(project.id, 'PENDING', project.pr_url, true); onClose(); }}
                            className="flex-1 py-2 px-4 text-sm font-bold rounded bg-amber-500/20 text-amber-400 border border-amber-500/30 hover:bg-amber-500/30 transition-all flex items-center justify-center gap-2"
                        >
                            <Clock size={16} /> Attente
                        </button>
                        <button
                            onClick={() => { handleDecision(project.id, 'REJECT', project.pr_url, true); onClose(); }}
                            className="flex-1 py-2 px-4 text-sm font-bold rounded bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30 transition-all flex items-center justify-center gap-2"
                        >
                            <XCircle size={16} /> Rejeter
                        </button>
                    </div>
                </div>
            </div>
        );
    };

    // SOTA 2026: Council Control Section (Manual Trigger)
    const CouncilControlSection = () => {
        const [isStarting, setIsStarting] = useState(false);

        const handleStartCouncil = async () => {
            setIsStarting(true);
            const result = await startCouncil();
            setIsStarting(false);
            if (!result.success) {
                console.error('[JULES] Council start failed:', result.error);
            }
        };

        // Calculate elapsed time if running
        const getElapsedTime = () => {
            if (!councilStartedAt) return null;
            const start = new Date(councilStartedAt);
            const now = new Date();
            const diffMs = now - start;
            const mins = Math.floor(diffMs / 60000);
            const secs = Math.floor((diffMs % 60000) / 1000);
            return `${mins}m ${secs}s`;
        };

        return (
            <Section title={locale === 'fr' ? 'COUNCIL' : 'COUNCIL'} icon={Zap} color="text-cyan-400">
                <div className="space-y-2">
                    {/* Status indicator */}
                    <div className="flex items-center justify-between text-xs">
                        <span className="text-white/50">{locale === 'fr' ? 'Statut' : 'Status'}</span>
                        <span className={`font-bold ${councilRunning ? 'text-cyan-400 animate-pulse' : 'text-white/50'}`}>
                            {councilRunning ? (locale === 'fr' ? 'EN COURS' : 'RUNNING') : (locale === 'fr' ? 'INACTIF' : 'IDLE')}
                        </span>
                    </div>

                    {/* Elapsed time if running */}
                    {councilRunning && (
                        <div className="flex items-center justify-between text-xs">
                            <span className="text-white/50">{locale === 'fr' ? 'Durée' : 'Elapsed'}</span>
                            <span className="font-mono text-cyan-400">{getElapsedTime()}</span>
                        </div>
                    )}

                    {/* Start button */}
                    <button
                        onClick={handleStartCouncil}
                        disabled={councilRunning || isStarting}
                        className={`w-full py-2 px-3 rounded text-xs font-bold uppercase tracking-wide transition-all duration-300 flex items-center justify-center gap-2 ${councilRunning || isStarting
                            ? 'bg-white/10 text-white/30 cursor-not-allowed'
                            : 'bg-gradient-to-r from-cyan-500/20 to-purple-500/20 border border-cyan-500/30 text-cyan-400 hover:from-cyan-500/30 hover:to-purple-500/30 hover:border-cyan-400/50'
                            }`}
                    >
                        {isStarting ? (
                            <><RefreshCw size={12} className="animate-spin" /> {locale === 'fr' ? 'DÉMARRAGE...' : 'STARTING...'}</>
                        ) : councilRunning ? (
                            <><RefreshCw size={12} className="animate-spin" /> {locale === 'fr' ? 'COUNCIL EN COURS' : 'COUNCIL RUNNING'}</>
                        ) : (
                            <><Zap size={12} /> {locale === 'fr' ? 'DÉMARRER COUNCIL' : 'START COUNCIL'}</>
                        )}
                    </button>
                </div>
            </Section>
        );
    };

    // NEW: Council Stats Section (ENRICHED with counters)
    const CouncilStatsSection = () => (
        <Section title={locale === 'fr' ? 'COUNCIL STATS' : 'COUNCIL STATS'} icon={TrendingUp} color="text-purple-400">
            <div className="space-y-2">
                {/* Inline counters row */}
                <div className="flex justify-between items-center gap-2 mb-2 pb-2 border-b border-white/10">
                    <div className="flex items-center gap-1">
                        <CheckCircle2 size={12} className="text-green-400" />
                        <span className="text-sm font-bold text-green-400">{stats.accepted}</span>
                    </div>
                    <div className="flex items-center gap-1">
                        <Clock size={12} className="text-amber-400" />
                        <span className="text-sm font-bold text-amber-400">{stats.pending}</span>
                    </div>
                    <div className="flex items-center gap-1">
                        <XCircle size={12} className="text-red-400" />
                        <span className="text-sm font-bold text-red-400">{stats.rejected}</span>
                    </div>
                </div>
                <div className="flex justify-between items-center text-xs">
                    <span className="text-white/50 flex items-center gap-1">
                        <Calendar size={12} /> {locale === 'fr' ? 'Dernier' : 'Last'}
                    </span>
                    <span className="text-white/80 font-mono">{formatDate(councilStats.last_council_date)}</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                    <span className="text-white/50 flex items-center gap-1">
                        <Target size={12} /> {locale === 'fr' ? 'Taux Succès' : 'Success Rate'}
                    </span>
                    <span className={`font-bold ${councilStats.success_rate >= 80 ? 'text-green-400' : councilStats.success_rate >= 50 ? 'text-amber-400' : 'text-red-400'}`}>
                        {councilStats.success_rate}%
                    </span>
                </div>
                <div className="flex justify-between items-center text-xs">
                    <span className="text-white/50 flex items-center gap-1">
                        <Activity size={12} /> {locale === 'fr' ? 'Score Moyen' : 'Avg Score'}
                    </span>
                    <span className="text-white/80 font-bold">{councilStats.avg_score}</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                    <span className="text-white/50 flex items-center gap-1">
                        <GitPullRequest size={12} /> {locale === 'fr' ? 'PRs Créées' : 'PRs Created'}
                    </span>
                    <span className="text-cyan-400 font-bold">{councilStats.total_prs_created}</span>
                </div>
            </div>
        </Section>
    );

    // NEW: History Section
    const HistorySection = () => (
        <Section title={locale === 'fr' ? 'HISTORIQUE' : 'HISTORY'} icon={History} color="text-cyan-400">
            <div className="space-y-2 max-h-32 overflow-y-auto">
                {history.merged?.slice(0, 3).map((item, i) => (
                    <div key={`m-${i}`} className="flex items-center gap-2 text-xs">
                        <CheckCircle2 size={10} className="text-green-400 flex-shrink-0" />
                        <span className="text-white/70 truncate flex-1">{item.title}</span>
                        {item.pr_url && (
                            <a href={item.pr_url} target="_blank" rel="noopener noreferrer" className="text-cyan-400 hover:text-cyan-300">
                                <ExternalLink size={10} />
                            </a>
                        )}
                    </div>
                ))}
                {history.rejected?.slice(0, 2).map((item, i) => (
                    <div key={`r-${i}`} className="flex items-center gap-2 text-xs">
                        <XCircle size={10} className="text-red-400 flex-shrink-0" />
                        <span className="text-white/50 truncate flex-1">{item.title}</span>
                    </div>
                ))}
                {(!history.merged?.length && !history.rejected?.length) && (
                    <p className="text-xs text-white/40 text-center py-2">{locale === 'fr' ? 'Aucun historique' : 'No history yet'}</p>
                )}
            </div>
        </Section>
    );

    return (
        <PanelLayout
            isWaitingForData={isLoading}
            waitingLabel="CONNECTING TO JULES..."
            footer={
                <ActionButtons
                    onRefresh={handleRefresh}
                    onApply={handleApply}
                    isRefreshing={isRefreshing}
                    isApplying={isApplying}
                    refreshLabel={locale === 'fr' ? 'RAFRAÎCHIR' : 'REFRESH'}
                    refreshingLabel={locale === 'fr' ? 'RAFRAÎCHISSEMENT...' : 'REFRESHING...'}
                    applyLabel={locale === 'fr' ? 'APPLIQUER' : 'APPLY'}
                    applyingLabel={locale === 'fr' ? 'APPLICATION...' : 'APPLYING...'}
                />
            }
        >
            <ResponsiveGrid>
                {/* Column 1: Council Control + Stats + Options + Notifications */}
                <Column>
                    {/* Council Control (Manual Trigger) */}
                    <CouncilControlSection />

                    {/* Council Stats (with integrated counters) */}
                    <CouncilStatsSection />

                    {/* Options */}
                    <Section title="OPTIONS" icon={Shield} color="text-purple-400">
                        <div className="grid grid-cols-2 gap-2">
                            <OptionToggle
                                icon={Eye}
                                label={optHelp.self_review.label}
                                value={options.self_review}
                                onChange={(v) => handleOptionToggle('self_review', v)}
                                activeColor="cyan"
                                tooltip={optHelp.self_review.help}
                                isTooltipActive={tooltip === 'self_review'}
                                onTooltipEnter={() => setTooltip('self_review')}
                                onTooltipLeave={() => setTooltip(null)}
                            />
                            <OptionToggle
                                icon={Sparkles}
                                label={optHelp.self_evolution.label}
                                value={options.self_evolution}
                                onChange={(v) => handleOptionToggle('self_evolution', v)}
                                activeColor="purple"
                                tooltip={optHelp.self_evolution.help}
                                isTooltipActive={tooltip === 'self_evolution'}
                                onTooltipEnter={() => setTooltip('self_evolution')}
                                onTooltipLeave={() => setTooltip(null)}
                            />
                            <OptionToggle
                                icon={Shield}
                                label={optHelp.nightwatch.label}
                                value={options.nightwatch}
                                onChange={(v) => handleOptionToggle('nightwatch', v)}
                                activeColor="amber"
                                tooltip={optHelp.nightwatch.help}
                                isTooltipActive={tooltip === 'nightwatch'}
                                onTooltipEnter={() => setTooltip('nightwatch')}
                                onTooltipLeave={() => setTooltip(null)}
                            />
                            <OptionToggle
                                icon={FlaskConical}
                                label={optHelp.sandbox_mode.label}
                                value={options.sandbox_mode}
                                onChange={(v) => handleOptionToggle('sandbox_mode', v)}
                                activeColor="pink"
                                tooltip={optHelp.sandbox_mode.help}
                                isTooltipActive={tooltip === 'sandbox_mode'}
                                onTooltipEnter={() => setTooltip('sandbox_mode')}
                                onTooltipLeave={() => setTooltip(null)}
                            />
                            <OptionToggle
                                icon={FileCheck}
                                label={optHelp.require_plan_approval.label}
                                value={options.require_plan_approval}
                                onChange={(v) => handleOptionToggle('require_plan_approval', v)}
                                activeColor="amber"
                                tooltip={optHelp.require_plan_approval.help}
                                isTooltipActive={tooltip === 'require_plan_approval'}
                                onTooltipEnter={() => setTooltip('require_plan_approval')}
                                onTooltipLeave={() => setTooltip(null)}
                            />
                            <OptionToggle
                                icon={Zap}
                                label={optHelp.auto_repoless.label}
                                value={options.auto_repoless}
                                onChange={(v) => handleOptionToggle('auto_repoless', v)}
                                activeColor="cyan"
                                tooltip={optHelp.auto_repoless.help}
                                isTooltipActive={tooltip === 'auto_repoless'}
                                onTooltipEnter={() => setTooltip('auto_repoless')}
                                onTooltipLeave={() => setTooltip(null)}
                            />
                        </div>
                    </Section>

                    {/* Notifications */}
                    <Section title={locale === 'fr' ? 'NOTIFICATIONS' : 'NOTIFICATIONS'} icon={Bell} color="text-pink-400">
                        <div className="grid grid-cols-2 gap-2">
                            <OptionToggle
                                icon={GitPullRequest}
                                label={optHelp.on_pr_created.label}
                                value={notifications.on_pr_created}
                                onChange={(v) => handleNotificationToggle('on_pr_created', v)}
                                activeColor="green"
                                tooltip={optHelp.on_pr_created.help}
                                isTooltipActive={tooltip === 'on_pr_created'}
                                onTooltipEnter={() => setTooltip('on_pr_created')}
                                onTooltipLeave={() => setTooltip(null)}
                            />
                            <OptionToggle
                                icon={GitMerge}
                                label={optHelp.on_pr_merged.label}
                                value={notifications.on_pr_merged}
                                onChange={(v) => handleNotificationToggle('on_pr_merged', v)}
                                activeColor="cyan"
                                tooltip={optHelp.on_pr_merged.help}
                                isTooltipActive={tooltip === 'on_pr_merged'}
                                onTooltipEnter={() => setTooltip('on_pr_merged')}
                                onTooltipLeave={() => setTooltip(null)}
                            />
                            <OptionToggle
                                icon={CheckCircle2}
                                label={optHelp.on_council_complete.label}
                                value={notifications.on_council_complete}
                                onChange={(v) => handleNotificationToggle('on_council_complete', v)}
                                activeColor="purple"
                                tooltip={optHelp.on_council_complete.help}
                                isTooltipActive={tooltip === 'on_council_complete'}
                                onTooltipEnter={() => setTooltip('on_council_complete')}
                                onTooltipLeave={() => setTooltip(null)}
                            />
                            <OptionToggle
                                icon={AlertTriangle}
                                label={optHelp.on_mission_failed.label}
                                value={notifications.on_mission_failed}
                                onChange={(v) => handleNotificationToggle('on_mission_failed', v)}
                                activeColor="red"
                                tooltip={optHelp.on_mission_failed.help}
                                isTooltipActive={tooltip === 'on_mission_failed'}
                                onTooltipEnter={() => setTooltip('on_mission_failed')}
                                onTooltipLeave={() => setTooltip(null)}
                            />
                        </div>
                    </Section>
                </Column>

                {/* Column 2: Projects to Validate */}
                <Column>
                    <Section
                        title={locale === 'fr' ? 'PROJETS À VALIDER' : 'PROJECTS TO VALIDATE'}
                        icon={Inbox}
                        color="text-cyan-400"
                    >
                        {projectsToValidate.length === 0 ? (
                            <p className="text-xs text-white/40 text-center py-4">
                                {locale === 'fr' ? 'Aucun projet en attente' : 'No projects awaiting decision'}
                            </p>
                        ) : (
                            <div className="space-y-3">
                                {projectsToValidate.map((project) => (
                                    <ProjectCard
                                        key={project.id}
                                        project={project}
                                        isStaged={project.isStaged}
                                    />
                                ))}
                            </div>
                        )}
                    </Section>
                </Column>

                {/* Column 3: Pending Projects (On Hold) + History */}
                <Column>
                    <Section
                        title={locale === 'fr' ? 'EN ATTENTE' : 'ON HOLD'}
                        icon={Clock}
                        color="text-amber-400"
                    >
                        {onHoldProjects.length === 0 ? (
                            <p className="text-xs text-white/40 text-center py-4">
                                {locale === 'fr' ? 'Aucun projet mis en attente' : 'No projects on hold'}
                            </p>
                        ) : (
                            <div className="space-y-3">
                                {onHoldProjects.slice(0, 5).map((project) => (
                                    <div key={project.id} className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3">
                                        {/* Header */}
                                        <div className="flex items-start justify-between gap-2 mb-2">
                                            <h4 className="text-sm font-bold text-white/90 line-clamp-1 flex-1">{project.title}</h4>
                                            <div className="flex gap-1">
                                                {(project.quality_score || project.score) && (
                                                    <span className="px-2 py-0.5 text-xs font-bold rounded bg-purple-500/20 text-purple-400 border border-purple-500/30">
                                                        {project.quality_score || project.score}%
                                                    </span>
                                                )}
                                                <span className="px-2 py-0.5 text-xs font-bold rounded bg-amber-500/20 text-amber-400 border border-amber-500/30">
                                                    {project.files_count || 0} files
                                                </span>
                                            </div>
                                        </div>

                                        {/* Description */}
                                        <p className="text-xs text-white/60 mb-2 line-clamp-2">
                                            {project.description || project.rationale || 'No description'}
                                        </p>

                                        {/* Stats */}
                                        {(project.additions > 0 || project.deletions > 0) && (
                                            <div className="text-xs text-white/40 mb-2">
                                                <span className="text-green-400">+{project.additions || 0}</span>
                                                {' / '}
                                                <span className="text-red-400">-{project.deletions || 0}</span>
                                                {' lines'}
                                            </div>
                                        )}

                                        {/* PR Link */}
                                        {project.pr_url && (
                                            <a
                                                href={project.pr_url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="inline-flex items-center gap-1 text-xs text-cyan-400 hover:text-cyan-300 mb-2"
                                            >
                                                <GitPullRequest size={10} /> {locale === 'fr' ? 'Voir PR' : 'View PR'} <ExternalLink size={10} />
                                            </a>
                                        )}

                                        {/* Actions */}
                                        <div className="flex gap-2">
                                            <button
                                                onClick={() => handleDecision(project.id, 'MERGE', project.pr_url, true)}
                                                className="flex-1 py-1.5 px-2 text-xs font-bold rounded bg-green-500/20 text-green-400 border border-green-500/30 hover:bg-green-500/30 transition-all flex items-center justify-center gap-1"
                                            >
                                                <CheckCircle2 size={12} /> {locale === 'fr' ? 'Approuver' : 'Approve'}
                                            </button>
                                            <button
                                                onClick={() => handleDecision(project.id, 'REJECT', project.pr_url, true)}
                                                className="flex-1 py-1.5 px-2 text-xs font-bold rounded bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30 transition-all flex items-center justify-center gap-1"
                                            >
                                                <XCircle size={12} /> {locale === 'fr' ? 'Rejeter' : 'Reject'}
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </Section>

                    {/* History Section */}
                    <HistorySection />
                </Column>
            </ResponsiveGrid>

            {/* Detail Modal */}
            {selectedProject && (
                <DetailModal project={selectedProject} onClose={() => setSelectedProject(null)} />
            )}
        </PanelLayout>
    );
}
