import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, Radio, MessageSquare, Users, Clock, Heart, AtSign, Settings, AlertTriangle, Shield, Filter, Send, Bell, CheckCircle, XCircle, Edit3, Loader, Trash2, Plus, ChevronUp, ChevronDown, Save, X, Bookmark } from 'lucide-react';
import { useTrinityStore } from '../../stores/trinityStore';
import { ActionButtons, Column, ResponsiveGrid, OptionToggle, PanelLayout, Row2, Section } from '../ui/PanelKit';
import { ANGEL_BASE_URL, getTrinityHeaders } from '../../services/angelService';

/**
 * SOTA 2026: InfluencerPanel - Social Media Dashboard (v3)
 * Layout: Col1 = Data, Col2 = Options + Pending, Col3 = Activity
 */

const DICT = {
    en: {
        stats: 'STATS',
        lastPost: 'Last Post',
        postsToday: 'Posts Today',
        repliesToday: 'Replies Today',
        viralScore: 'Viral Score',
        grokRomance: 'ROMANCE GROK',
        nextRomance: 'Next Romance',
        romanceCount: 'Total Romance',
        lastReply: 'Last Reply',
        mentions: 'MENTIONS',
        lastMention: 'Last Mention',
        priorities: 'PRIORITIES',
        rules: 'RULES',
        maxThread: 'Max/Thread',
        maxDay: 'Max/Day',
        maxPosts: 'Max Posts',
        twoShot: 'Two-Shot',
        cooldown: 'Cooldown',
        heartbeat: 'Heartbeat',
        spamWords: 'Spam Words',
        options: 'OPTIONS',
        autoReply: 'Auto Reply',
        romanceEnabled: 'Romance Grok',
        spamFilter: 'Spam Filter',
        approvalMode: 'Approval Mode',
        priorityOnly: 'Priority Only',
        silentMode: 'Silent Mode',
        pending: 'PENDING APPROVAL',
        noPending: 'No tweets pending',
        approve: 'Approve',
        reject: 'Reject',
        recentPosts: 'RECENT ACTIVITY',
        xMetrics: 'X METRICS',
        impressions: 'Impressions',
        likes: 'Likes',
        retweets: 'Retweets',
        replies: 'Replies',
        noMetrics: 'Post content to see metrics',
        noPosts: 'No activity yet',
        newTweet: 'NEW TWEET',
        placeholder: 'Write a tweet...',
        submit: 'SUBMIT',
        submitting: 'SUBMITTING...',
        refresh: 'REFRESH',
        refreshing: 'REFRESHING...',
        apply: 'APPLY',
        applying: 'APPLYING...',
        offline: 'Influencer offline',
        notifications: 'NOTIFICATIONS',
        notifyMentions: 'Mentions',
        notifyReplies: 'Replies',
        notifyApprovals: 'Approvals',
        loading: 'Loading...',
        noData: 'N/A',
        followers: 'Followers',
        quotes: 'Quotes',
        bookmarks: 'Bookmarks',
        incoming: 'INCOMING (Mentions)',
        outgoing: 'OUTGOING (Posts)',
    },
    fr: {
        stats: 'STATS',
        lastPost: 'Dernier Post',
        postsToday: 'Posts Auj.',
        repliesToday: 'Réponses Auj.',
        viralScore: 'Score Viral',
        grokRomance: 'ROMANCE GROK',
        nextRomance: 'Prochain',
        romanceCount: 'Total Romance',
        lastReply: 'Dernière Rép.',
        mentions: 'MENTIONS',
        lastMention: 'Dernière Mention',
        priorities: 'PRIORITÉS',
        rules: 'RÈGLES',
        maxThread: 'Max/Thread',
        maxDay: 'Max/Jour',
        maxPosts: 'Max Posts',
        twoShot: 'Two-Shot',
        cooldown: 'Cooldown',
        heartbeat: 'Heartbeat',
        spamWords: 'Mots Spam',
        options: 'OPTIONS',
        autoReply: 'Réponse Auto',
        romanceEnabled: 'Romance Grok',
        spamFilter: 'Filtre Spam',
        approvalMode: 'Mode Approbation',
        priorityOnly: 'Priorités Seules',
        silentMode: 'Mode Silencieux',
        pending: 'EN ATTENTE',
        noPending: 'Aucun tweet en attente',
        approve: 'Approuver',
        reject: 'Rejeter',
        recentPosts: 'ACTIVITÉ RÉCENTE',
        xMetrics: 'MÉTRIQUES X',
        impressions: 'Impressions',
        likes: 'J\'aime',
        retweets: 'Retweets',
        replies: 'Réponses',
        noMetrics: 'Publiez pour voir les métriques',
        noPosts: 'Aucune activité',
        newTweet: 'NOUVEAU TWEET',
        placeholder: 'Écrire un tweet...',
        submit: 'ENVOYER',
        submitting: 'ENVOI...',
        refresh: 'ACTUALISER',
        refreshing: 'ACTUALISATION...',
        apply: 'APPLIQUER',
        applying: 'APPLICATION...',
        offline: 'Influencer hors ligne',
        notifications: 'NOTIFICATIONS',
        notifyMentions: 'Mentions',
        notifyReplies: 'Réponses',
        notifyApprovals: 'Approbations',
        loading: 'Chargement...',
        noData: 'N/A',

        followers: 'Followers',
        quotes: 'Citations',
        bookmarks: 'Signets',
        incoming: 'ENTRANT (Mentions)',
        outgoing: 'SORTANT (Posts)',
    }
};

export default function InfluencerPanel() {
    const { locale, jobsStatus, influencerState, setInfluencerState } = useTrinityStore();
    const t = DICT[locale] || DICT.fr;

    // SOTA 2026: Use persistent store state
    const status = influencerState;

    // const [loading, setLoading] = useState(true); // SOTA 2026: Removed blocking loading
    const [error, setError] = useState(false); // SOTA 2026: Error Handling
    const [isOffline, setIsOffline] = useState(false); // SOTA 2026: Offline Resilience
    const [isRefreshing, setIsRefreshing] = useState(false);

    // ... [keep other states]
    const [isApplying, setIsApplying] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [newTweetText, setNewTweetText] = useState('');

    // SOTA 2026: Priority Editor State
    const [isEditingPriorities, setIsEditingPriorities] = useState(false);
    const [editingPriorities, setEditingPriorities] = useState([]);
    const [isSavingPriorities, setIsSavingPriorities] = useState(false);

    // SOTA 2026: Spam Editor State
    const [isEditingSpam, setIsEditingSpam] = useState(false);
    const [editingSpamWords, setEditingSpamWords] = useState([]);
    const [isSavingSpam, setIsSavingSpam] = useState(false);

    // SOTA 2026: Notifications State - Init from Store
    const config = influencerState?.config || {};

    const [optNotifyMentions, setOptNotifyMentions] = useState(config.notify_mentions !== false);
    const [optNotifyReplies, setOptNotifyReplies] = useState(config.notify_replies !== false);
    const [optNotifyApprovalsTrinity, setOptNotifyApprovalsTrinity] = useState(config.notify_approvals_trinity !== false);
    const [optNotifyApprovalsGrok, setOptNotifyApprovalsGrok] = useState(config.notify_approvals_grok !== false);
    const [optNotifyYoutube, setOptNotifyYoutube] = useState(config.notify_youtube !== false);
    const [optNotifyViral, setOptNotifyViral] = useState(config.notify_viral !== false);

    const [optAutoReply, setOptAutoReply] = useState(config.auto_reply !== false);
    const [optRomance, setOptRomance] = useState(config.banter_enabled !== false);
    const [optSpamFilter, setOptSpamFilter] = useState(config.spam_filter !== false);
    const [optApprovalMode, setOptApprovalMode] = useState(config.approval_mode === true);
    const [optPriorityOnly, setOptPriorityOnly] = useState(config.priority_only === true);
    const [optSilentMode, setOptSilentMode] = useState(config.silent_mode === true);

    // SOTA 2026: RULES - Editable values (not just display)
    const [ruleMaxThread, setRuleMaxThread] = useState(config.max_replies_per_thread ?? 2);
    const [ruleCooldown, setRuleCooldown] = useState(config.cooldown_minutes ?? 42);
    const [ruleHeartbeat, setRuleHeartbeat] = useState(config.heartbeat_minutes ?? 89);
    const [ruleMaxDay, setRuleMaxDay] = useState(config.max_replies_per_day ?? 10);
    const [ruleTrinityInterval, setRuleTrinityInterval] = useState(config.trinity_interval_hours ?? 24);
    const [ruleGrokInterval, setRuleGrokInterval] = useState(config.grok_interval_hours ?? 24);

    // SOTA 2026 Standard 362.80.1: X Metrics State - Cache-First
    const [xMetrics, setXMetrics] = useState(
        influencerState?.xMetrics || { totals: { impressions: 0, likes: 0, retweets: 0, replies: 0, quotes: 0, bookmarks: 0 }, loading: false }
    );

    // SOTA 2026 Standard 362.80.1: Incoming Mentions State - Cache-First
    const [mentionsFeed, setMentionsFeed] = useState(influencerState?.mentionsFeed || []);
    const [pubFilter, setPubFilter] = useState('all'); // 'all' | 'post' | 'reply'

    // SOTA 2026: Sync useState from store when influencerState changes (hydration + API refresh)
    useEffect(() => {
        if (!influencerState) return;
        // Sync config options
        if (influencerState.config) {
            const cfg = influencerState.config;
            setOptAutoReply(cfg.auto_reply !== false);
            setOptRomance(cfg.banter_enabled !== false);
            setOptSpamFilter(cfg.spam_filter !== false);
            setOptApprovalMode(cfg.approval_mode === true);
            setOptPriorityOnly(cfg.priority_only === true);
            setOptSilentMode(cfg.silent_mode === true);
            setOptNotifyMentions(cfg.notify_mentions !== false);
            setOptNotifyReplies(cfg.notify_replies !== false);
            setOptNotifyApprovalsTrinity(cfg.notify_approvals_trinity !== false);
            setOptNotifyApprovalsGrok(cfg.notify_approvals_grok !== false);
            setOptNotifyYoutube(cfg.notify_youtube !== false);
            setOptNotifyViral(cfg.notify_viral !== false);
            if (cfg.max_replies_per_thread !== undefined) setRuleMaxThread(cfg.max_replies_per_thread);
            if (cfg.cooldown_minutes !== undefined) setRuleCooldown(cfg.cooldown_minutes);
            if (cfg.heartbeat_minutes !== undefined) setRuleHeartbeat(cfg.heartbeat_minutes);
            if (cfg.max_replies_per_day !== undefined) setRuleMaxDay(cfg.max_replies_per_day);
            if (cfg.trinity_interval_hours !== undefined) setRuleTrinityInterval(cfg.trinity_interval_hours);
            if (cfg.grok_interval_hours !== undefined) setRuleGrokInterval(cfg.grok_interval_hours);
        }
        // Sync xMetrics from cache
        if (influencerState.xMetrics) {
            setXMetrics(influencerState.xMetrics);
        }
        // Sync mentionsFeed from cache
        if (influencerState.mentionsFeed) {
            setMentionsFeed(influencerState.mentionsFeed);
        }
    }, [influencerState]);

    const fetchStatus = useCallback(async () => {
        try {
            setError(false);
            const res = await fetch(`${ANGEL_BASE_URL}/api/influencer/status`, { headers: getTrinityHeaders() });
            if (res.ok) {
                const data = await res.json();
                setInfluencerState(data);
                setIsOffline(false); // Connection restored

                // Load config
                if (data.config) {
                    setOptAutoReply(data.config.auto_reply !== false);
                    setOptRomance(data.config.banter_enabled !== false);
                    setOptSpamFilter(data.config.spam_filter !== false);
                    setOptApprovalMode(data.config.approval_mode === true); // Default false usually
                    setOptPriorityOnly(data.config.priority_only === true);
                    setOptSilentMode(data.config.silent_mode === true);

                    // Notifications
                    setOptNotifyMentions(data.config.notify_mentions !== false);
                    setOptNotifyReplies(data.config.notify_replies !== false);
                    setOptNotifyApprovalsTrinity(data.config.notify_approvals_trinity !== false);
                    setOptNotifyApprovalsGrok(data.config.notify_approvals_grok !== false);
                    setOptNotifyYoutube(data.config.notify_youtube !== false);
                    setOptNotifyViral(data.config.notify_viral !== false);

                    // RULES - Sync from API (real data, not fake)
                    if (data.config.max_replies_per_thread !== undefined) setRuleMaxThread(data.config.max_replies_per_thread);
                    if (data.config.cooldown_minutes !== undefined) setRuleCooldown(data.config.cooldown_minutes);
                    if (data.config.heartbeat_minutes !== undefined) setRuleHeartbeat(data.config.heartbeat_minutes);
                    if (data.config.max_replies_per_day !== undefined) setRuleMaxDay(data.config.max_replies_per_day);
                    if (data.config.trinity_interval_hours !== undefined) setRuleTrinityInterval(data.config.trinity_interval_hours);
                    if (data.config.grok_interval_hours !== undefined) setRuleGrokInterval(data.config.grok_interval_hours);
                }
            } else {
                throw new Error('API Error');
            }
        } catch (e) {
            // console.error(e);
            setIsOffline(true);
        }
        finally { setIsRefreshing(false); }
    }, []);

    // SOTA 2026: Fetch X Metrics from API
    const fetchXMetrics = useCallback(async (force = false) => {
        try {
            const url = `${ANGEL_BASE_URL}/api/influencer/x-metrics${force ? '?force=true' : ''}`;
            const res = await fetch(url, { headers: getTrinityHeaders() });
            if (res.ok) {
                const data = await res.json();
                // SOTA 2026: Fixed parsing - API returns raw data object, not status wrapper
                if (data && (data.totals || data.weekly)) {
                    const metricsData = {
                        totals: data.totals || {},
                        weekly: data.weekly || {},
                        alltime: data.alltime || {},
                        metrics: data.metrics || [],
                        loading: false
                    };
                    setXMetrics(metricsData);
                    // SOTA 2026: Persist to store for cache
                    setInfluencerState({ xMetrics: metricsData });
                }
            }
        } catch (e) {
            // fail silent
        }
    }, [setInfluencerState]);

    // SOTA 2026: Fetch Incoming Mentions
    const fetchMentions = useCallback(async () => {
        try {
            const res = await fetch(`${ANGEL_BASE_URL}/api/influencer/mentions`, { headers: getTrinityHeaders() });
            if (res.ok) {
                const data = await res.json();
                const mentions = data.mentions || [];
                setMentionsFeed(mentions);
                // SOTA 2026: Persist to store for cache
                setInfluencerState({ mentionsFeed: mentions });
            }
        } catch (e) {
            // fail silent
        }
    }, [setInfluencerState]);


    // SOTA 2026: Auto-polling enabled - DELAYED STARTUP
    useEffect(() => {
        let interval;
        // SOTA 2026: Harmonized timing - 3s initial delay (Standard 350)
        const timer = setTimeout(() => {
            fetchStatus();
            fetchXMetrics(false); // Normal load (cached)
            fetchMentions(); // Fetch Mentions feed
            interval = setInterval(() => { fetchStatus(); fetchXMetrics(false); fetchMentions(); }, 180000); // Poll every 3m
        }, 3000);

        return () => {
            clearTimeout(timer);
            if (interval) clearInterval(interval);
        };
    }, [fetchStatus, fetchXMetrics, fetchMentions]);

    const handleRefresh = () => { setIsRefreshing(true); fetchStatus(); fetchXMetrics(true); fetchMentions(); };

    const handleApply = async () => {
        setIsApplying(true);
        try {
            await fetch(`${ANGEL_BASE_URL}/api/influencer/config`, {
                method: 'POST',
                headers: getTrinityHeaders(),
                body: JSON.stringify({
                    auto_reply: optAutoReply,
                    banter_enabled: optRomance,
                    spam_filter: optSpamFilter,
                    approval_mode: optApprovalMode,
                    priority_only: optPriorityOnly,
                    silent_mode: optSilentMode,
                    // Notifications
                    notify_mentions: optNotifyMentions,
                    notify_replies: optNotifyReplies,
                    notify_approvals_trinity: optNotifyApprovalsTrinity,
                    notify_approvals_grok: optNotifyApprovalsGrok,
                    notify_youtube: optNotifyYoutube,
                    notify_viral: optNotifyViral,
                    // RULES - Send to API (real config, not fake)
                    max_replies_per_thread: parseInt(ruleMaxThread) || 2,
                    cooldown_minutes: parseInt(ruleCooldown) || 42,
                    heartbeat_minutes: parseInt(ruleHeartbeat) || 89,
                    max_replies_per_day: parseInt(ruleMaxDay) || 10,
                    trinity_interval_hours: parseInt(ruleTrinityInterval),
                    grok_interval_hours: parseInt(ruleGrokInterval)
                })
            });
            await fetchStatus();
        } catch (e) {
            console.error(e);
            setError(true);
        } finally {
            setIsApplying(false);
        }
    };

    const handleApprove = async (id) => {
        try {
            await fetch(`${ANGEL_BASE_URL}/api/influencer/approve/${id}`, { method: 'POST', headers: getTrinityHeaders() });
            fetchStatus();
        } catch (e) { console.error(e); }
    };

    const handleReject = async (id) => {
        try {
            await fetch(`${ANGEL_BASE_URL}/api/influencer/reject/${id}`, { method: 'POST', headers: getTrinityHeaders() });
            fetchStatus();
        } catch (e) { console.error(e); }
    };

    const handleSubmitTweet = async () => {
        if (!newTweetText.trim()) return;
        setIsSubmitting(true);
        try {
            await fetch(`${ANGEL_BASE_URL}/api/influencer/tweet`, {
                method: 'POST',
                headers: getTrinityHeaders(),
                body: JSON.stringify({ text: newTweetText })
            });
            setNewTweetText('');
            fetchStatus();
        } catch (e) { console.error(e); }
        finally { setIsSubmitting(false); }
    };

    // SOTA 2026: Priority Editor Handlers
    const handleEditPriorities = () => {
        // Use current status or empty
        const current = status?.priorities || [];
        setEditingPriorities(JSON.parse(JSON.stringify(current))); // Deep copy
        setIsEditingPriorities(true);
    };

    const handleSavePriorities = async () => {
        setIsSavingPriorities(true);
        try {
            await fetch(`${ANGEL_BASE_URL}/api/influencer/priorities`, {
                method: 'POST',
                headers: getTrinityHeaders(),
                body: JSON.stringify({ priorities: editingPriorities })
            });
            await fetchStatus();
            setIsEditingPriorities(false);
        } catch (e) {
            console.error(e);
            setError(true);
        } finally {
            setIsSavingPriorities(false);
        }
    };

    const handleAddPriority = () => {
        setEditingPriorities([...editingPriorities, { username: '', description: '' }]);
    };

    const handleDeletePriority = (index) => {
        const newPriorities = [...editingPriorities];
        newPriorities.splice(index, 1);
        setEditingPriorities(newPriorities);
    };

    const handleMovePriority = (index, direction) => {
        if (direction === 'up' && index === 0) return;
        if (direction === 'down' && index === editingPriorities.length - 1) return;

        const newPriorities = [...editingPriorities];
        const swapIndex = direction === 'up' ? index - 1 : index + 1;
        const temp = newPriorities[swapIndex];
        newPriorities[swapIndex] = newPriorities[index];
        newPriorities[index] = temp;
        setEditingPriorities(newPriorities);
    };

    const handleUpdatePriority = (index, field, value) => {
        const newPriorities = [...editingPriorities];
        newPriorities[index] = { ...newPriorities[index], [field]: value };
        setEditingPriorities(newPriorities);
    };

    // SOTA 2026: Spam Words Handlers
    const handleEditSpam = () => {
        const current = status?.spam_keywords || [];
        setEditingSpamWords([...current]);
        setIsEditingSpam(true);
    };

    const handleSaveSpam = async () => {
        setIsSavingSpam(true);
        try {
            await fetch(`${ANGEL_BASE_URL}/api/influencer/spam-words`, {
                method: 'POST',
                headers: getTrinityHeaders(),
                body: JSON.stringify({ keywords: editingSpamWords })
            });
            await fetchStatus();
            setIsEditingSpam(false);
        } catch (e) {
            console.error(e);
            setError(true);
        } finally {
            setIsSavingSpam(false);
        }
    };

    const handleAddSpamWord = () => {
        setEditingSpamWords([...editingSpamWords, 'new word']);
    };

    const handleDeleteSpamWord = (index) => {
        const newWords = [...editingSpamWords];
        newWords.splice(index, 1);
        setEditingSpamWords(newWords);
    };

    const handleUpdateSpamWord = (index, value) => {
        const newWords = [...editingSpamWords];
        newWords[index] = value;
        setEditingSpamWords(newWords);
    };


    const formatTimeAgo = (time) => {
        if (!time) return 'N/A';
        const d = Date.now() / 1000 - time;
        if (d < 60) return `${Math.floor(d)}s`;
        if (d < 3600) return `${Math.floor(d / 60)}m`;
        if (d < 86400) return `${Math.floor(d / 3600)}h`;
        return `${Math.floor(d / 86400)}j`;
    };



    // SOTA 2026: Always show panel
    // if (!jobsStatus?.influencer) ... removed

    const rules = status?.rules || {};
    const pendingTweets = status?.pending_tweets || [];
    const recentActivity = status?.recent_activity || [];

    // Tooltip Info (i18n)
    const TOOLTIPS = {
        en: {
            autoReply: 'Automatically reply to mentions using Grok AI.',
            romanceEnabled: 'Enable Romance Grok (spontaneous posting) based on personality.',
            spamFilter: 'Filter out obvious spam keywords from incoming mentions.',
            approvalMode: 'Require manual approval for ALL tweets/replies before posting.',
            priorityOnly: 'Only reply to accounts in the Priority list.',
            silentMode: 'Disable all outgoing posts/replies (monitoring only).',
            notifyMentions: 'Push notification when you are mentioned.',
            notifyReplies: 'Push notification when someone replies to you.',
            notifyApprovals: 'Push notification when a tweet needs approval.',
        },
        fr: {
            autoReply: 'Répondre automatiquement aux mentions via Grok IA.',
            romanceEnabled: 'Activer Romance Grok (posts spontanés) selon la personnalité.',
            spamFilter: 'Filtrer les mots-clés de spam évidents des mentions.',
            approvalMode: 'Nécessite une approbation manuelle pour TOUS les tweets/réponses.',
            priorityOnly: 'Répondre uniquement aux comptes de la liste Priorité.',
            silentMode: 'Désactiver tous les posts/réponses sortants (surveillance seule).',
            notifyMentions: 'Notification push quand vous êtes mentionné.',
            notifyReplies: 'Notification push quand quelqu\'un vous répond.',
            notifyApprovals: 'Notification push quand un tweet nécessite approbation.',
        }
    };

    const tooltips = TOOLTIPS[locale] || TOOLTIPS.fr;
    const [tooltip, setTooltip] = useState(null);

    // SOTA 2026: Render helper using enhanced OptionToggle with built-in tooltip support
    const renderToggle = (id, label, icon, value, onChange, color, tooltipText) => (
        <OptionToggle
            key={id}
            icon={icon}
            label={label}
            value={value}
            onChange={onChange}
            activeColor={color}
            tooltip={tooltipText}
            isTooltipActive={tooltip === id}
            onTooltipEnter={() => setTooltip(id)}
            onTooltipLeave={() => setTooltip(null)}
        />
    );

    return (
        <PanelLayout
            isWaitingForData={false}
            isError={error}
            onRetry={fetchStatus}
            footer={
                <ActionButtons
                    onRefresh={handleRefresh}
                    onApply={handleApply}
                    isRefreshing={isRefreshing}
                    isApplying={isApplying}
                    refreshLabel={t.refresh}
                    refreshingLabel={t.refreshing}
                    applyLabel={t.apply}
                    applyingLabel={t.applying}
                />
            }
        >
            <ResponsiveGrid className="transition-all duration-500">
                {/* COLUMN 1: DATA */}
                <Column>
                    <Section title={t.stats} icon={Radio} color="text-pink-400">
                        <div className="space-y-1">
                            <Row2
                                left={{ label: t.followers, value: (status?.followers_count || 0).toLocaleString(), color: 'text-purple-400 font-bold' }}
                                right={{ label: 'Status', value: status?.status || 'Active', color: status?.status === 'SILENT' ? 'text-pink-400' : 'text-green-400' }}
                            />
                            <Row2
                                left={{ label: t.lastPost, value: formatTimeAgo(status?.last_post_time), color: 'text-white font-medium' }}
                                right={{ label: t.lastReply, value: formatTimeAgo(status?.last_reply_time), color: 'text-cyan-400' }}
                            />
                            <Row2
                                left={{ label: t.postsToday, value: `${status?.posts_today || 0}/${rules.max_posts_per_day || '-'}`, color: status?.posts_today >= rules.max_posts_per_day ? 'text-red-400' : 'text-cyan-400' }}
                                right={{ label: t.repliesToday, value: `${status?.replies_today || 0}/${rules.max_replies_per_day || '-'}`, color: status?.replies_today >= rules.max_replies_per_day ? 'text-red-400' : 'text-cyan-400' }}
                            />
                            <Row2
                                left={{ label: t.viralScore, value: status?.viral_score?.toFixed(1) || '0.0', color: 'text-yellow-400' }}
                                right={{ label: t.lastMention, value: status?.last_mention || 'N/A', color: 'text-white/60' }}
                            />
                        </div>
                    </Section>

                    {/* SOTA 2026: X Metrics Section - Weekly + Alltime */}
                    <Section title={t.xMetrics} icon={Radio} color="text-blue-400" border="border-blue-500/30">
                        {/* Weekly Row */}
                        <div className="mb-2">
                            <div className="text-[10px] text-white/50 mb-1 font-medium">{t.thisWeek || 'THIS WEEK'}</div>
                            <div className="grid grid-cols-4 gap-2 text-center">
                                <div className="bg-white/5 rounded p-2">
                                    <div className="text-sm font-bold text-blue-400">{(xMetrics.weekly?.impressions || 0).toLocaleString()}</div>
                                    <div className="text-[9px] text-white/40">{t.impressions}</div>
                                </div>
                                <div className="bg-white/5 rounded p-2">
                                    <div className="text-sm font-bold text-pink-400">{xMetrics.weekly?.likes || 0}</div>
                                    <div className="text-[9px] text-white/40">{t.likes}</div>
                                </div>
                                <div className="bg-white/5 rounded p-2">
                                    <div className="text-sm font-bold text-green-400">{xMetrics.weekly?.retweets || 0}</div>
                                    <div className="text-[9px] text-white/40">{t.retweets}</div>
                                </div>
                                <div className="bg-white/5 rounded p-2">
                                    <div className="text-sm font-bold text-cyan-400">{xMetrics.weekly?.replies || 0}</div>
                                    <div className="text-[9px] text-white/40">{t.replies}</div>
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-2 mt-2 px-8">
                                <div className="bg-white/5 rounded p-1 text-center flex items-center justify-center gap-2">
                                    <div className="text-xs font-bold text-yellow-400">{xMetrics.weekly?.quotes || 0}</div>
                                    <div className="text-[10px] text-white/70 font-medium flex items-center gap-1">
                                        <MessageSquare size={10} className="text-yellow-400/50" /> {t.quotes}
                                    </div>
                                </div>
                                <div className="bg-white/5 rounded p-1 text-center flex items-center justify-center gap-2">
                                    <div className="text-xs font-bold text-indigo-400">{xMetrics.weekly?.bookmarks || 0}</div>
                                    <div className="text-[10px] text-white/70 font-medium flex items-center gap-1">
                                        <Bookmark size={10} className="text-indigo-400/50" /> {t.bookmarks}
                                    </div>
                                </div>
                            </div>
                        </div>
                        {/* Alltime Row */}
                        <div>
                            <div className="text-[10px] text-white/50 mb-1 font-medium">{t.alltime || 'ALL TIME'}</div>
                            <div className="grid grid-cols-4 gap-2 text-center">
                                <div className="bg-white/5 rounded p-2">
                                    <div className="text-sm font-bold text-blue-300">{(xMetrics.alltime?.impressions || xMetrics.totals?.impressions || 0).toLocaleString()}</div>
                                    <div className="text-[9px] text-white/40">{t.impressions}</div>
                                </div>
                                <div className="bg-white/5 rounded p-2">
                                    <div className="text-sm font-bold text-pink-300">{xMetrics.alltime?.likes || xMetrics.totals?.likes || 0}</div>
                                    <div className="text-[9px] text-white/40">{t.likes}</div>
                                </div>
                                <div className="bg-white/5 rounded p-2">
                                    <div className="text-sm font-bold text-green-300">{xMetrics.alltime?.retweets || xMetrics.totals?.retweets || 0}</div>
                                    <div className="text-[9px] text-white/40">{t.retweets}</div>
                                </div>
                                <div className="bg-white/5 rounded p-2">
                                    <div className="text-sm font-bold text-cyan-300">{xMetrics.alltime?.replies || xMetrics.totals?.replies || 0}</div>
                                    <div className="text-[9px] text-white/40">{t.replies}</div>
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-2 mt-2 px-8">
                                <div className="bg-white/5 rounded p-1 text-center flex items-center justify-center gap-2">
                                    <div className="text-xs font-bold text-yellow-300">{xMetrics.alltime?.quotes || 0}</div>
                                    <div className="text-[10px] text-white/70 font-medium flex items-center gap-1">
                                        <MessageSquare size={10} className="text-yellow-300/50" /> {t.quotes}
                                    </div>
                                </div>
                                <div className="bg-white/5 rounded p-1 text-center flex items-center justify-center gap-2">
                                    <div className="text-xs font-bold text-indigo-300">{xMetrics.alltime?.bookmarks || 0}</div>
                                    <div className="text-[10px] text-white/70 font-medium flex items-center gap-1">
                                        <Bookmark size={10} className="text-indigo-300/50" /> {t.bookmarks}
                                    </div>
                                </div>
                            </div>
                        </div>
                        {!xMetrics.totals?.impressions && !xMetrics.alltime?.impressions && (
                            <p className="text-xs text-white/30 mt-2 text-center">{t.noMetrics}</p>
                        )}
                    </Section>

                    {/* SOTA 2026: Offline Indicator */}
                    {isOffline && (
                        <div className="flex items-center gap-2 text-amber-400 bg-amber-500/10 rounded-lg p-3 text-sm animate-pulse mb-3 border border-amber-500/20">
                            <AlertTriangle size={16} /> 📡 {t.offline || 'Reconnecting...'}
                        </div>
                    )}

                    <Section title="SCHEDULE" icon={Clock} color="text-purple-400" border="border-purple-500/30">
                        <Row2
                            left={{ label: "Next Trinity", value: status?.next_trinity || "Soon", color: "text-amber-300 font-bold" }}
                            right={{ label: "Next Grok", value: status?.next_banter || "Soon", color: "text-purple-300 font-bold" }}
                        />
                        <div className="mt-3 pt-2 border-t border-white/5 flex gap-4 items-center">
                            <div className="flex-1 flex justify-between items-center">
                                <div className="text-[10px] text-white/40 uppercase tracking-wider">Trinity Freq</div>
                                <div className="flex items-center gap-1">
                                    <input
                                        id="rule-trinity-interval"
                                        name="rule-trinity-interval"
                                        type="number"
                                        value={ruleTrinityInterval}
                                        onChange={(e) => setRuleTrinityInterval(e.target.value)}
                                        className="w-10 bg-transparent text-right text-xs text-amber-400 font-bold focus:outline-none border-b border-amber-500/30 focus:border-amber-400"
                                    />
                                    <span className="text-[10px] text-white/30">h</span>
                                </div>
                            </div>
                            <div className="w-px h-6 bg-white/5"></div>
                            <div className="flex-1 flex justify-between items-center">
                                <div className="text-[10px] text-white/40 uppercase tracking-wider">Grok Freq</div>
                                <div className="flex items-center gap-1">
                                    <input
                                        id="rule-grok-interval"
                                        name="rule-grok-interval"
                                        type="number"
                                        value={ruleGrokInterval}
                                        onChange={(e) => setRuleGrokInterval(e.target.value)}
                                        className="w-10 bg-transparent text-right text-xs text-purple-400 font-bold focus:outline-none border-b border-purple-500/30 focus:border-purple-400"
                                    />
                                    <span className="text-[10px] text-white/30">h</span>
                                </div>
                            </div>
                        </div>
                    </Section>

                    <Section title={t.priorities} icon={Users} color="text-amber-400"
                        headerRight={
                            !isEditingPriorities ? (
                                <button onClick={handleEditPriorities} className="p-1 hover:bg-white/10 rounded text-white/50 hover:text-white transition-colors">
                                    <Edit3 size={12} />
                                </button>
                            ) : (
                                <div className="flex gap-1">
                                    <button onClick={handleSavePriorities} disabled={isSavingPriorities} className="p-1 hover:bg-green-500/20 rounded text-green-400 transition-colors">
                                        {isSavingPriorities ? <Loader size={12} className="animate-spin" /> : <Save size={12} />}
                                    </button>
                                    <button onClick={() => setIsEditingPriorities(false)} className="p-1 hover:bg-red-500/20 rounded text-red-400 transition-colors">
                                        <X size={12} />
                                    </button>
                                </div>
                            )
                        }
                    >
                        {/* Priority Editor Content (Unchanged) */}
                        {isEditingPriorities ? (
                            <div className="space-y-2">
                                <div className="max-h-60 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
                                    {editingPriorities.map((p, i) => (
                                        <div key={i} className="flex gap-1 items-center bg-black/30 p-1.5 rounded border border-white/5 group">
                                            <div className="flex flex-col gap-0.5">
                                                <button onClick={() => handleMovePriority(i, 'up')} className="text-white/30 hover:text-white p-0.5"><ChevronUp size={10} /></button>
                                                <button onClick={() => handleMovePriority(i, 'down')} className="text-white/30 hover:text-white p-0.5"><ChevronDown size={10} /></button>
                                            </div>
                                            <div className="flex-1 flex flex-col gap-1">
                                                <div className="flex items-center gap-1">
                                                    <span className="text-amber-400 text-xs font-mono">{i + 1}.</span>
                                                    <input
                                                        id={`priority-username-${i}`}
                                                        name={`priority-username-${i}`}
                                                        value={p.username}
                                                        onChange={(e) => handleUpdatePriority(i, 'username', e.target.value)}
                                                        placeholder="@username"
                                                        className="bg-transparent border-b border-white/10 text-xs text-amber-400 w-full focus:outline-none focus:border-amber-500 px-1"
                                                    />
                                                </div>
                                                <input
                                                    id={`priority-description-${i}`}
                                                    name={`priority-description-${i}`}
                                                    value={p.description}
                                                    onChange={(e) => handleUpdatePriority(i, 'description', e.target.value)}
                                                    placeholder="Description (e.g. Rival)"
                                                    className="bg-transparent text-[10px] text-white/50 w-full focus:outline-none px-1 ml-4"
                                                />
                                            </div>
                                            <button onClick={() => handleDeletePriority(i)} className="text-red-400/30 hover:text-red-400 p-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                <Trash2 size={12} />
                                            </button>
                                        </div>
                                    ))}
                                </div>
                                <button onClick={handleAddPriority} className="w-full py-1.5 bg-white/5 hover:bg-white/10 rounded flex items-center justify-center text-xs text-white/50 hover:text-white gap-1 transition-colors border border-dashed border-white/10 hover:border-white/30">
                                    <Plus size={12} /> {t.add || 'Add Priority'}
                                </button>
                            </div>
                        ) : (
                            <div className="text-xs space-y-0.5">
                                {(status?.priorities || []).map((p, i) => (
                                    <div key={i} className="flex gap-2 items-center">
                                        <span className="text-amber-400 font-mono w-4">{i + 1}.</span>
                                        <span className="text-white/70">@{p.username}</span>
                                        {p.description && <span className="text-white/30 italic">({p.description})</span>}
                                    </div>
                                ))}
                                {(!status?.priorities || status.priorities.length === 0) && <p className="text-white/30 italic text-center py-2">No priorities set</p>}
                            </div>
                        )}
                    </Section>
                </Column>

                {/* COLUMN 2: OPTIONS + PENDING */}
                <Column>
                    <Section title={t.options} icon={Settings} color="text-pink-400">
                        <div className="grid grid-cols-2 gap-2">
                            {renderToggle('optAutoReply', t.autoReply, MessageSquare, optAutoReply, setOptAutoReply, 'cyan', tooltips.autoReply)}
                            {renderToggle('optRomance', t.romanceEnabled, Heart, optRomance, setOptRomance, 'purple', tooltips.romanceEnabled)}
                            {renderToggle('optSpamFilter', t.spamFilter, Filter, optSpamFilter, setOptSpamFilter, 'amber', tooltips.spamFilter)}
                            {renderToggle('optApprovalMode', t.approvalMode, CheckCircle, optApprovalMode, setOptApprovalMode, 'cyan', tooltips.approvalMode)}
                            {renderToggle('optPriorityOnly', t.priorityOnly, Users, optPriorityOnly, setOptPriorityOnly, 'amber', tooltips.priorityOnly)}
                            {renderToggle('optSilentMode', t.silentMode, Bell, optSilentMode, setOptSilentMode, 'pink', tooltips.silentMode)}
                        </div>
                        {/* RULES - Editable Inputs (wired to API, not fake) */}
                        <div className="grid grid-cols-4 gap-2 mt-3 text-xs">
                            <div className="bg-white/5 rounded p-2 flex flex-col items-center">
                                <input
                                    id="rule-max-thread"
                                    name="rule-max-thread"
                                    type="number"
                                    value={ruleMaxThread}
                                    onChange={(e) => setRuleMaxThread(e.target.value)}
                                    className="w-12 bg-transparent border-b border-cyan-500/50 text-cyan-400 font-bold text-center focus:outline-none focus:border-cyan-400"
                                    min="1"
                                    max="10"
                                />
                                <div className="text-white/40 text-[10px] mt-1">{t.maxThread}</div>
                            </div>
                            <div className="bg-white/5 rounded p-2 flex flex-col items-center">
                                <div className="flex items-center">
                                    <input
                                        id="rule-cooldown"
                                        name="rule-cooldown"
                                        type="number"
                                        value={ruleCooldown}
                                        onChange={(e) => setRuleCooldown(e.target.value)}
                                        className="w-12 bg-transparent border-b border-cyan-500/50 text-cyan-400 font-bold text-center focus:outline-none focus:border-cyan-400"
                                        min="1"
                                        max="120"
                                    />
                                    <span className="text-white/40 ml-0.5">m</span>
                                </div>
                                <div className="text-white/40 text-[10px] mt-1">{t.cooldown}</div>
                            </div>
                            <div className="bg-white/5 rounded p-2 flex flex-col items-center">
                                <div className="flex items-center">
                                    <input
                                        id="rule-heartbeat"
                                        name="rule-heartbeat"
                                        type="number"
                                        value={ruleHeartbeat}
                                        onChange={(e) => setRuleHeartbeat(e.target.value)}
                                        className="w-12 bg-transparent border-b border-cyan-500/50 text-cyan-400 font-bold text-center focus:outline-none focus:border-cyan-400"
                                        min="30"
                                        max="180"
                                    />
                                    <span className="text-white/40 ml-0.5">m</span>
                                </div>
                                <div className="text-white/40 text-[10px] mt-1">{t.heartbeat}</div>
                            </div>
                            <div className="bg-white/5 rounded p-2 flex flex-col items-center">
                                <input
                                    id="rule-max-day"
                                    name="rule-max-day"
                                    type="number"
                                    value={ruleMaxDay}
                                    onChange={(e) => setRuleMaxDay(e.target.value)}
                                    className="w-12 bg-transparent border-b border-amber-500/50 text-amber-400 font-bold text-center focus:outline-none focus:border-amber-400"
                                    min="1"
                                    max="100"
                                />
                                <div className="text-white/40 text-[10px] mt-1">{t.maxDay}</div>
                            </div>
                        </div>


                    </Section>

                    {/* NEW CARD: SPAM FILTER */}
                    {optSpamFilter && (
                        <Section title={`${t.spamWords} (${status?.spam_keywords?.length || 0})`} icon={Shield} color="text-amber-400" border="border-amber-500/20">
                            <div className="flex justify-between items-center mb-2">
                                <p className="text-xs text-white/40">Active anti-spam rules.</p>
                                {!isEditingSpam ? (
                                    <button onClick={handleEditSpam} className="text-xs bg-white/5 hover:bg-white/10 px-3 py-1 rounded text-amber-400 transition-colors border border-amber-500/20">
                                        Manage Keywords
                                    </button>
                                ) : (
                                    <div className="flex gap-2">
                                        <button onClick={handleSaveSpam} className="flex items-center gap-1 px-2 py-1 bg-green-500/20 text-green-400 rounded hover:bg-green-500/30 text-xs"><Save size={12} /> Save</button>
                                        <button onClick={() => setIsEditingSpam(false)} className="flex items-center gap-1 px-2 py-1 bg-red-500/20 text-red-400 rounded hover:bg-red-500/30 text-xs"><X size={12} /> Cancel</button>
                                    </div>
                                )}
                            </div>

                            {isEditingSpam ? (
                                <div className="bg-black/40 rounded p-2 max-h-40 overflow-y-auto space-y-1 custom-scrollbar border border-white/5">
                                    <div className="flex flex-wrap gap-1">
                                        {editingSpamWords.map((word, i) => (
                                            <div key={i} className="flex items-center bg-white/5 rounded px-2 py-1 border border-white/5 group hover:border-red-500/30 transition-colors">
                                                <input
                                                    id={`spam-word-${i}`}
                                                    name={`spam-word-${i}`}
                                                    value={word}
                                                    onChange={(e) => handleUpdateSpamWord(i, e.target.value)}
                                                    className="bg-transparent text-xs text-white w-24 focus:outline-none"
                                                />
                                                <button onClick={() => handleDeleteSpamWord(i)} className="ml-1 text-white/20 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"><X size={10} /></button>
                                            </div>
                                        ))}
                                        <button onClick={handleAddSpamWord} className="px-2 py-1 rounded border border-white/10 text-xs text-white/30 hover:text-white hover:border-white/30 transition-colors flex items-center gap-1">
                                            <Plus size={10} /> Add
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <div className="flex flex-wrap gap-1 max-h-24 overflow-hidden mask-fade-bottom">
                                    {(status?.spam_keywords || []).slice(0, 15).map((word, i) => (
                                        <span key={i} className="text-[10px] bg-white/5 px-2 py-0.5 rounded text-white/40 border border-white/5">{word}</span>
                                    ))}
                                    {(status?.spam_keywords || []).length > 15 && (
                                        <span className="text-[10px] text-white/20 px-1">...</span>
                                    )}
                                </div>
                            )}
                        </Section>
                    )}

                    {/* PENDING APPROVAL - SPLIT QUEUES (TRINITY vs ROMANCE) */}
                    <Section title={`${t.pending} (${pendingTweets.length})`} icon={Clock} color="text-amber-400" border="border-amber-500/30">
                        <div className="flex flex-col gap-4 max-h-[500px] overflow-y-auto pr-1">
                            {/* SECTION 1: TRINITY / MENTIONS */}
                            <div className="space-y-2">
                                <div className="text-[10px] text-white/50 font-bold uppercase tracking-wider mb-1 flex justify-between border-b border-white/5 pb-1">
                                    <span>Trinity & Mentions</span>
                                    <span className="text-white/20">{pendingTweets.filter(t => t.type !== 'grok_banter').length}</span>
                                </div>
                                {pendingTweets.filter(t => t.type !== 'grok_banter').map(tweet => (
                                    <PendingItem
                                        key={tweet.id}
                                        tweet={tweet}
                                        onApprove={handleApprove}
                                        onReject={handleReject}
                                        onRegenerate={async (id) => {
                                            await fetch(`${ANGEL_BASE_URL}/api/influencer/regenerate/${id}`, { method: 'POST', headers: getTrinityHeaders() });
                                            fetchStatus();
                                        }}
                                        t={t}
                                    />
                                ))}
                                {pendingTweets.filter(t => t.type !== 'grok_banter').length === 0 && (
                                    <div className="text-white/20 text-xs italic p-3 text-center bg-white/5 rounded border border-white/5 border-dashed">
                                        Empty
                                    </div>
                                )}
                            </div>

                            {/* SECTION 2: ROMANCE */}
                            <div className="space-y-2">
                                <div className="text-[10px] text-purple-400/70 font-bold uppercase tracking-wider mb-1 flex justify-between border-b border-purple-500/10 pb-1">
                                    <span>Romance Grok</span>
                                    <span className="text-white/20">{pendingTweets.filter(t => t.type === 'grok_banter').length}</span>
                                </div>
                                {pendingTweets.filter(t => t.type === 'grok_banter').map(tweet => (
                                    <PendingItem
                                        key={tweet.id}
                                        tweet={tweet}
                                        onApprove={handleApprove}
                                        onReject={handleReject}
                                        onRegenerate={async (id) => {
                                            await fetch(`${ANGEL_BASE_URL}/api/influencer/regenerate/${id}`, { method: 'POST', headers: getTrinityHeaders() });
                                            fetchStatus();
                                        }}
                                        t={t}
                                    />
                                ))}
                                {pendingTweets.filter(t => t.type === 'grok_banter').length === 0 && (
                                    <div className="text-purple-500/20 text-xs italic p-3 text-center bg-purple-500/5 rounded border border-purple-500/10 border-dashed">
                                        Empty
                                    </div>
                                )}
                            </div>
                        </div>
                    </Section>
                </Column>

                {/* COLUMN 3: NOTIFICATIONS + RECENT */}
                <Column className="hidden 2xl:flex flex-col gap-3">
                    <Section title={t.notifications || 'NOTIFICATIONS'} icon={Bell} color="text-cyan-400">
                        <div className="grid grid-cols-2 gap-2">
                            {renderToggle('notify_mentions', t.notifyMentions, AtSign, optNotifyMentions, setOptNotifyMentions, 'cyan', tooltips.notifyMentions)}
                            {renderToggle('notify_replies', t.notifyReplies, MessageSquare, optNotifyReplies, setOptNotifyReplies, 'purple', tooltips.notifyReplies)}
                            {renderToggle('notify_approvals_trinity', "Appr. Trinity", CheckCircle, optNotifyApprovalsTrinity, setOptNotifyApprovalsTrinity, 'amber', "Notify on Trinity Approvals")}
                            {renderToggle('notify_approvals_grok', "Appr. Grok", Heart, optNotifyApprovalsGrok, setOptNotifyApprovalsGrok, 'pink', "Notify on Grok Approvals")}
                            {renderToggle('notify_youtube', "YouTube", Radio, optNotifyYoutube, setOptNotifyYoutube, 'red', "Alert when YouTube video shared on X")}
                            {renderToggle('notify_viral', "Viral", AlertTriangle, optNotifyViral, setOptNotifyViral, 'yellow', "Alert when tweet goes viral (100+ likes)")}
                        </div>
                    </Section>


                    {/* RECENT ACTIVITY / INCOMING FEED - TABBED */}
                    {/* RECENT PUBLICATIONS */}
                    <Section
                        title={
                            <div className="flex justify-between items-center w-full pr-2">
                                <span>RECENT PUBLICATIONS</span>
                                <div className="flex bg-black/40 rounded p-0.5">
                                    {['all', 'post', 'reply'].map(filter => (
                                        <button
                                            key={filter}
                                            onClick={() => setPubFilter(filter)}
                                            className={`px-2 py-0.5 text-[10px] uppercase font-bold rounded transition-colors ${pubFilter === filter ? 'bg-white/20 text-white' : 'text-white/30 hover:text-white/60'}`}
                                        >
                                            {filter === 'all' ? 'All' : filter === 'post' ? 'Posts' : 'Replies'}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        }
                        icon={Send}
                        color="text-pink-400"
                        className="flex-1 min-h-0 flex flex-col"
                    >
                        <div className="space-y-3 max-h-[450px] overflow-y-auto pr-1">
                            {(() => {
                                const filtered = recentActivity.filter(item => {
                                    if (pubFilter === 'all') return true;
                                    if (pubFilter === 'post') return item.type !== 'reply'; // "post" includes normal posts + grok banter? Or strictly posts. Let's assume non-replies.
                                    if (pubFilter === 'reply') return item.type === 'reply';
                                    if (pubFilter === 'reply') return item.type === 'reply';
                                    return true;
                                });

                                // Deduplicate by ID to prevent rendering bugs
                                const uniqueActivity = Array.from(new Map(filtered.map(item => [item.id, item])).values());

                                return uniqueActivity.length > 0 ? uniqueActivity.map((item, i) => {
                                    const getTypeDisplay = (type) => {
                                        if (type === 'grok_banter') return { label: 'ROMANCE', color: 'bg-purple-500/20 text-purple-400' };
                                        if (type === 'post') return { label: 'POST', color: 'bg-cyan-500/20 text-cyan-400' };
                                        if (type === 'reply') return { label: 'REPLY', color: 'bg-pink-500/20 text-pink-400' };
                                        return { label: type?.toUpperCase() || 'POST', color: 'bg-white/10 text-white/60' };
                                    };
                                    const typeInfo = getTypeDisplay(item.type);
                                    const statusColor = item.status === 'POSTED' ? 'text-green-400' : item.status === 'REJECTED' ? 'text-red-400' : 'text-amber-400';

                                    return (
                                        <div key={item.id || i} className="bg-black/20 rounded-lg p-3 border border-white/5">
                                            <div className="flex items-center justify-between mb-1.5">
                                                <div className="flex items-center gap-2">
                                                    <span className={`text-xs font-bold px-2 py-0.5 rounded ${typeInfo.color}`}>
                                                        {typeInfo.label}
                                                    </span>
                                                    <span className={`text-xs ${statusColor}`}>{item.status}</span>
                                                </div>
                                                <span className="text-white/40 text-xs">{formatTimeAgo(item.time)}</span>
                                            </div>
                                            {item.in_reply_to && (
                                                <p className="text-white/40 text-xs mb-1">↳ {item.in_reply_to}</p>
                                            )}
                                            <p className="text-white/80 text-sm leading-relaxed">{item.text}</p>
                                        </div>
                                    )
                                }) : (
                                    <p className="text-white/40 text-center py-4">{t.noPosts}</p>
                                );
                            })()}
                        </div>
                    </Section>
                </Column>
            </ResponsiveGrid>
        </PanelLayout>
    );
}

// SOTA 2026: Helper Component for Pending Items
const PendingItem = ({ tweet, onApprove, onReject, onRegenerate, t }) => {
    const [isRegenerating, setIsRegenerating] = useState(false);

    const handleRegen = async () => {
        setIsRegenerating(true);
        await onRegenerate(tweet.id);
        setIsRegenerating(false);
    };

    return (
        <div className="bg-black/30 rounded p-2 border border-white/5 relative group">
            {/* Type Badge */}
            <div className="flex justify-between items-start mb-1">
                <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${tweet.type === 'grok_banter' ? 'bg-purple-500/20 text-purple-400' :
                    tweet.type === 'mentions_reply' ? 'bg-pink-500/20 text-pink-400' :
                        'bg-cyan-500/20 text-cyan-400'
                    }`}>
                    {tweet.type === 'grok_banter' ? 'ROMANCE' :
                        tweet.type === 'mentions_reply' ? (tweet.meta?.reply_to_user ? `@${tweet.meta.reply_to_user}` : 'REPLY') :
                            'THOUGHT'}
                </span>
                <span className="text-[9px] text-white/30">
                    {new Date(tweet.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
            </div>

            {/* Content */}
            <p className="text-white/80 text-xs mb-2 leading-relaxed whitespace-pre-wrap">{tweet.text}</p>

            {/* Meta Context (if mention) */}
            {tweet.meta?.original_text && (
                <div className="mb-2 pl-2 border-l-2 border-white/10 text-white/40 text-[10px] italic line-clamp-2">
                    "{tweet.meta.original_text}"
                </div>
            )}

            {/* Actions */}
            <div className="flex gap-2">
                <button
                    onClick={() => onApprove(tweet.id)}
                    className="flex-1 py-1.5 text-xs rounded bg-green-500/10 hover:bg-green-500/20 text-green-400 border border-green-500/20 hover:border-green-500/40 transition-all flex items-center justify-center gap-1 font-medium"
                >
                    <CheckCircle size={12} /> {t.approve}
                </button>

                {/* Regenerate Button (Route 1) */}
                <button
                    onClick={handleRegen}
                    disabled={isRegenerating}
                    className="w-8 py-1.5 rounded bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 border border-blue-500/20 hover:border-blue-500/40 transition-all flex items-center justify-center disabled:opacity-50"
                    title="Regenerate (Intelligence Mode)"
                >
                    <RefreshCw size={12} className={isRegenerating ? "animate-spin" : ""} />
                </button>

                <button
                    onClick={() => onReject(tweet.id)}
                    className="w-8 py-1.5 text-xs rounded bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 hover:border-red-500/40 transition-all flex items-center justify-center"
                >
                    <XCircle size={12} />
                </button>
            </div>
        </div>
    );
};
