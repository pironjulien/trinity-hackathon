import React, { useState, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { RefreshCw, Play, Pause, Upload, Youtube, Clock, List, Plus, Trash2, Video, BarChart2, Calendar, AlertTriangle, Loader, CheckCircle, XCircle, Bell, Zap, TrendingUp, HelpCircle, Sliders, Type, FileCheck, UploadCloud, Save, RotateCcw, Monitor, FileText, Info, Sparkles } from 'lucide-react';
import { useTrinityStore } from '../../stores/trinityStore';
import { ActionButtons, Column, OptionToggle, PanelLayout, Row2, Section, ResponsiveGrid } from '../ui/PanelKit';
import { ANGEL_BASE_URL, getTrinityHeaders } from '../../services/angelService';

const DICT = {
    en: {
        stats: 'ANALYTICS',
        totalVideos: 'Total Videos',
        totalViews: 'Total Views',
        avgRetention: 'Avg Retention',
        production: 'PRODUCTION',
        pending: 'Pending',
        published: 'Published',
        lastPublished: 'Last',
        nextScheduled: 'Next Video',
        nextScriptIn: 'Next Script',
        scriptPendingValidation: 'Script awaiting validation',
        videoPendingPublication: 'Video awaiting publication',
        options: 'OPTIONS',
        status: 'Status',
        uploadEnabled: 'Auto Upload',
        subtitles: 'Subtitles',
        placard: 'Placard',
        placardText: 'Placard Text',
        pendingUpload: 'Videos ready for manual publishing',
        publish: 'Publish',
        topics: 'TOPICS',
        addTopic: 'ADD TOPIC',
        placeholder: 'Enter video topic...',
        add: 'ADD',
        adding: 'ADDING...',
        recentVideos: 'RECENT VIDEOS',
        noVideos: 'No videos yet',
        noTopics: 'No topics queued',
        offline: 'Youtuber offline',
        refresh: 'REFRESH',
        refreshing: 'REFRESHING...',
        active: 'ACTIVE',
        paused: 'PAUSED',
        scheduled: 'Scheduled',
        apply: 'APPLY',
        applying: 'APPLYING...',
        notifications: 'NOTIFICATIONS',
        notifyUploads: 'Uploads',
        notifyMilestones: 'Milestones',
        notifyPipeline: 'Pipeline',
        notifyViral: 'Viral',
        scriptGeneration: 'Script pending review',
        scriptPending: '',
        approve: 'APPROVE',
        retry: 'RETRY',
        reject: 'REJECT',
    },
    fr: {
        stats: 'ANALYTIQUES',
        totalVideos: 'Vidéos Totales',
        totalViews: 'Vues Totales',
        avgRetention: 'Rétention Moy.',
        production: 'PRODUCTION',
        pending: 'En Attente',
        published: 'Publiées',
        lastPublished: 'Dernière',
        nextScheduled: 'Prochaine Vidéo',
        nextScriptIn: 'Prochain Script',
        scriptPendingValidation: 'Script en attente de validation',
        videoPendingPublication: 'Vidéo en attente de publication',
        options: 'OPTIONS',
        status: 'Statut',
        uploadEnabled: 'Upload Auto',
        subtitles: 'Sous-titres',
        placard: 'Pancarte',
        placardText: 'Texte Pancarte',
        pendingUpload: 'Vidéos prêtes pour publication manuelle',
        publish: 'Publier',
        topics: 'SUJETS',
        addTopic: 'AJOUTER SUJET',
        placeholder: 'Sujet de la vidéo...',
        add: 'AJOUTER',
        adding: 'AJOUT...',
        recentVideos: 'VIDÉOS RÉCENTES',
        noVideos: 'Aucune vidéo',
        noTopics: 'Aucun sujet',
        offline: 'Youtuber hors ligne',
        refresh: 'ACTUALISER',
        refreshing: 'ACTUALISATION...',
        active: 'ACTIF',
        paused: 'PAUSE',
        scheduled: 'Prévu',
        apply: 'APPLIQUER',
        applying: 'APPLICATION...',
        notifications: 'NOTIFICATIONS',
        notifyUploads: 'Uploads',
        notifyMilestones: 'Jalons',
        notifyPipeline: 'Pipeline',
        notifyViral: 'Viral',
        scriptGeneration: 'Script en attente de validation',
        scriptPending: '',
        approve: 'APPROUVER',
        retry: 'RELANCER',
        reject: 'REJETER',
    }
};

// SOTA 2026: Tooltip definitions per locale
const TOOLTIPS = {
    fr: {
        active: "Interrupteur Maître: Contrôle toute la boucle de l'Agent Youtuber.",
        uploadEnabled: "Autorisation finale pour publier sur YouTube.",
        subtitles: "Générer automatiquement les sous-titres sur les vidéos.",
        placard: "Afficher une pancarte avec texte personnalisé dans la vidéo.",
        notifyUploads: "Notification quand une vidéo est publiée.",
        notifyMilestones: "Notifications aux seuils de vues (100/500/1K/10K).",
        notifyPipeline: "Alerte quand un script est prêt pour production.",
        notifyViral: "Alerte quand une vidéo performe exceptionnellement."
    },
    en: {
        active: "Master Switch: Controls the entire Youtuber Agent loop.",
        uploadEnabled: "Final authorization to publish to YouTube.",
        subtitles: "Automatically generate subtitles on videos.",
        placard: "Display a placard with custom text in the video.",
        notifyUploads: "Notification when a video is published.",
        notifyMilestones: "Notifications at view thresholds (100/500/1K/10K).",
        notifyPipeline: "Alert when a script is ready for production.",
        notifyViral: "Alert when a video performs exceptionally."
    }
};


export default function YoutuberPanel() {
    const { locale, jobsStatus, youtuberState, setYoutuberState } = useTrinityStore();
    const t = DICT[locale] || DICT.fr;
    const tooltips = TOOLTIPS[locale] || TOOLTIPS.fr;

    const status = youtuberState;
    const topics = status?.topics || [];
    const upcomingVideos = status?.upcoming_videos || [];
    const [error, setError] = useState(false);
    const [isOffline, setIsOffline] = useState(false); // SOTA 2026: Offline Resilience
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [newTopic, setNewTopic] = useState('');
    const [isAddingTopic, setIsAddingTopic] = useState(false);
    const [tooltip, setTooltip] = useState(null);
    const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
    const [tooltipContent, setTooltipContent] = useState('');
    const [isScriptAction, setIsScriptAction] = useState(null); // 'approve' | 'retry' | 'reject' | null
    const [scriptPreviewLang, setScriptPreviewLang] = useState('fr'); // SOTA 2026: Bilingual switch

    // SOTA 2026 Standard 362.80.1: Cache-First Initialization (Hydration Sync)
    // Initialize directly from store to prevent blank panel flash
    const [uploadEnabled, setUploadEnabled] = useState(youtuberState?.upload_enabled ?? false);
    const [isActive, setIsActive] = useState(youtuberState?.status === 'ACTIVE');
    // Notification toggles - Cache-First
    const [notifyUploads, setNotifyUploads] = useState(youtuberState?.notify_uploads ?? true);
    const [notifyMilestones, setNotifyMilestones] = useState(youtuberState?.notify_milestones ?? true);
    const [notifyPipeline, setNotifyPipeline] = useState(youtuberState?.notify_pipeline ?? true);
    const [notifyViral, setNotifyViral] = useState(youtuberState?.notify_viral ?? true);

    // SOTA 2026: Video Production Options - Cache-First
    const [subtitlesEnabled, setSubtitlesEnabled] = useState(youtuberState?.subtitles_enabled ?? true);
    const [placardEnabled, setPlacardEnabled] = useState(!!youtuberState?.placard_enabled);
    const [placardTextFr, setPlacardTextFr] = useState(youtuberState?.placard_text_fr || '');
    const [placardTextEn, setPlacardTextEn] = useState(youtuberState?.placard_text_en || '');

    // SOTA 2026: Sync useState from store when youtuberState changes (hydration + API refresh)
    useEffect(() => {
        if (!youtuberState) return;
        if (youtuberState.status) setIsActive(youtuberState.status === 'ACTIVE');
        if (youtuberState.upload_enabled !== undefined) setUploadEnabled(youtuberState.upload_enabled);
        if (youtuberState.notify_uploads !== undefined) setNotifyUploads(youtuberState.notify_uploads);
        if (youtuberState.notify_milestones !== undefined) setNotifyMilestones(youtuberState.notify_milestones);
        if (youtuberState.notify_pipeline !== undefined) setNotifyPipeline(youtuberState.notify_pipeline);
        if (youtuberState.notify_viral !== undefined) setNotifyViral(youtuberState.notify_viral);
        if (youtuberState.subtitles_enabled !== undefined) setSubtitlesEnabled(youtuberState.subtitles_enabled);
        setPlacardEnabled(!!youtuberState.placard_enabled);
        setPlacardTextFr(youtuberState.placard_text_fr || '');
        setPlacardTextEn(youtuberState.placard_text_en || '');
    }, [youtuberState]);



    const fetchStatus = useCallback(async () => {
        try {
            setError(false);
            const res = await fetch(`${ANGEL_BASE_URL}/api/youtuber/status`, { headers: getTrinityHeaders() });
            if (res.ok) {
                const data = await res.json();
                setYoutuberState(data);
                setIsOffline(false); // Connection restored

                // Sync local toggle state
                if (data.status) setIsActive(data.status === 'ACTIVE');
                if (data.upload_enabled !== undefined) setUploadEnabled(data.upload_enabled);
                // Sync notification toggles
                if (data.notify_uploads !== undefined) setNotifyUploads(data.notify_uploads);
                if (data.notify_milestones !== undefined) setNotifyMilestones(data.notify_milestones);
                if (data.notify_pipeline !== undefined) setNotifyPipeline(data.notify_pipeline);
                if (data.notify_viral !== undefined) setNotifyViral(data.notify_viral);
                // Sync video production options
                if (data.subtitles_enabled !== undefined) setSubtitlesEnabled(data.subtitles_enabled);
                if (data.subtitles_enabled !== undefined) setSubtitlesEnabled(data.subtitles_enabled);
                setPlacardEnabled(!!data.placard_enabled);
                setPlacardTextFr(data.placard_text_fr || '');
                setPlacardTextEn(data.placard_text_en || '');
            } else {
                throw new Error('API Error');
            }
        } catch (e) {
            // console.error(e); // Silent fail
            setIsOffline(true);
        } finally {
            setIsRefreshing(false);
        }
    }, [setYoutuberState]);

    // SOTA 2026: Harmonized timing - 3s initial delay (Standard 350)
    useEffect(() => {
        let interval;
        const timer = setTimeout(() => {
            fetchStatus();
            interval = setInterval(fetchStatus, 180000);
        }, 3000);
        return () => {
            clearTimeout(timer);
            if (interval) clearInterval(interval);
        };
    }, [fetchStatus]);

    const [isApplying, setIsApplying] = useState(false);

    const handleRefresh = async () => {
        setIsRefreshing(true);
        // SOTA 2026: Trigger Real-time Sync
        try {
            await fetch(`${ANGEL_BASE_URL}/api/youtuber/sync`, { method: 'POST', headers: getTrinityHeaders() });
            await fetchStatus();
        } catch (e) {
            console.error('Sync failed', e);
        } finally {
            setIsRefreshing(false);
        }
    };

    // Local state updates only (batch send on Apply)
    const handleToggleStatus = (val) => setIsActive(val);
    const handleToggleUpload = (val) => setUploadEnabled(val);

    const handleApply = async () => {
        setIsApplying(true);
        try {
            // Apply both Status and Upload settings
            await fetch(`${ANGEL_BASE_URL}/api/youtuber/config`, {
                method: 'POST',
                headers: getTrinityHeaders(),
                body: JSON.stringify({
                    status: isActive ? 'ACTIVE' : 'PAUSED',
                    upload_enabled: uploadEnabled,
                    notify_uploads: notifyUploads,
                    notify_milestones: notifyMilestones,
                    notify_pipeline: notifyPipeline,
                    notify_viral: notifyViral,
                    // Video Production Options
                    subtitles_enabled: subtitlesEnabled,
                    placard_enabled: placardEnabled,
                    placard_text_fr: placardTextFr,
                    placard_text_en: placardTextEn
                })
            });
            await fetchStatus();
        } catch (e) {
            console.error(e);
        } finally {
            setIsApplying(false);
        }
    };

    const handleAddTopic = async () => {
        if (!newTopic.trim()) return;
        setIsAddingTopic(true);
        try {
            await fetch(`${ANGEL_BASE_URL}/api/youtuber/topic`, {
                method: 'POST',
                headers: getTrinityHeaders(),
                body: JSON.stringify({ topic: newTopic })
            });
            setNewTopic('');
            fetchStatus();
        } catch (e) { console.error(e); }
        finally { setIsAddingTopic(false); }
    };

    // SOTA 2026: Always show panel, just indicate status in UI
    // if (!jobsStatus?.youtuber) ... removed to allow offline config

    // SOTA 2026: Filtering Logic
    // SOTA 2026: Unified View (User Request)
    // SOTA 2026: Content Separation (FR / EN)
    const frVideos = (status?.recent_videos || []).filter(v => v.lang === 'fr');
    const enVideos = (status?.recent_videos || []).filter(v => v.lang === 'en');

    // Global Stats remain aggregated
    const stats = {
        total_videos: status?.total_videos || 0,
        total_views: status?.total_views || 0,
        avg_retention: status?.avg_retention || 0,
        last_published: status?.last_published || 'N/A'
    };

    const handlePublish = async (video) => {
        try {
            const res = await fetch(`${ANGEL_BASE_URL}/api/youtuber/publish`, {
                method: 'POST',
                headers: getTrinityHeaders(),
                body: JSON.stringify({ id: video.id })
            });
            const data = await res.json();
            if (data.status === 'ok') {
                fetchStatus(); // Refresh list to see update
            } else {
                console.error('Publish failed:', data);
            }
        } catch (e) {
            console.error('Publish error:', e);
        }
    };

    // SOTA 2026: Script Generation Actions (Approve / Retry / Reject)
    const handleScriptAction = async (action, scriptId) => {
        setIsScriptAction(action);
        try {
            const res = await fetch(`${ANGEL_BASE_URL}/api/youtuber/script/${action}`, {
                method: 'POST',
                headers: getTrinityHeaders(),
                body: JSON.stringify({ script_id: scriptId })
            });
            const data = await res.json();
            if (data.status === 'ok') {
                fetchStatus(); // Refresh to get new state
            } else {
                console.error(`Script ${action} failed:`, data);
            }
        } catch (e) {
            console.error(`Script ${action} error:`, e);
        } finally {
            setIsScriptAction(null);
        }
    };

    return (
        <>
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
                        applyLabel={t.apply || 'APPLY'}
                        applyingLabel={t.applying || 'APPLYING...'}
                        showApply={true}
                    />
                }
            >
                {/* TABS REMOVED PER USER REQUEST */}

                <ResponsiveGrid className="transition-all duration-500">
                    {/* COLUMN 1: ANALYTICS & QUEUE STATS */}
                    <Column>
                        <Section title={t.stats} icon={BarChart2} color="text-pink-400">
                            <div className="space-y-1">
                                <Row2
                                    left={{ label: t.totalVideos, value: stats.total_videos, color: 'text-white font-bold' }}
                                    right={{ label: t.avgRetention, value: `${stats.avg_retention}%`, color: 'text-cyan-400' }}
                                />
                                <Row2
                                    left={{ label: t.totalViews, value: (stats.total_views).toLocaleString(), color: 'text-purple-400' }}
                                    right={{ label: 'Subscribers', value: (status?.subscribers || 0).toLocaleString(), color: 'text-pink-400' }}
                                />
                            </div>
                        </Section>

                        {/* SOTA 2026: Offline Indicator */}
                        {isOffline && (
                            <div className="flex items-center gap-2 text-amber-400 bg-amber-500/10 rounded-lg p-3 text-sm animate-pulse mb-3 border border-amber-500/20">
                                <AlertTriangle size={16} /> 📡 {t.offline || 'Reconnecting...'}
                            </div>
                        )}

                        {/* PRODUCTION STATUS - Script & Video Pipeline */}
                        <Section title={t.production} icon={Video} color="text-amber-400" border="border-amber-500/30">
                            {/* Last / Next Published */}
                            <Row2
                                left={{ label: t.lastPublished, value: stats.last_published || 'N/A', color: 'text-white/60' }}
                                right={{ label: t.published, value: stats.total_videos, color: 'text-green-400' }}
                            />

                            {/* SCRIPT & VIDEO STATUS - 2 columns */}
                            <div className="mt-3 pt-3 border-t border-white/5 grid grid-cols-2 gap-4">
                                {/* SCRIPT STATUS */}
                                <div>
                                    <p className="text-white/50 text-xs mb-1 flex items-center gap-1">
                                        <FileText className="w-3 h-3" /> {t.nextScriptIn}
                                    </p>
                                    {status?.pending_script ? (
                                        <p className="text-amber-400 font-mono text-sm flex items-center gap-1">
                                            <Clock className="w-3 h-3 animate-pulse" />
                                            En attente
                                        </p>
                                    ) : status?.script_scheduler?.hours_remaining != null ? (
                                        <p className="text-cyan-400 font-mono text-sm flex items-center gap-1">
                                            <Clock className="w-3 h-3" />
                                            {status.script_scheduler.hours_remaining <= 0
                                                ? 'Imminent'
                                                : `${status.script_scheduler.hours_remaining.toFixed(1)}h`
                                            }
                                        </p>
                                    ) : (
                                        <p className="text-white/40 font-mono text-sm">—</p>
                                    )}
                                </div>

                                {/* VIDEO STATUS */}
                                <div>
                                    <p className="text-white/50 text-xs mb-1 flex items-center gap-1">
                                        <Video className="w-3 h-3" /> {t.nextScheduled}
                                    </p>
                                    {(status?.pending_count || 0) > 0 ? (
                                        <p className="text-amber-400 font-mono text-sm flex items-center gap-1">
                                            <Clock className="w-3 h-3 animate-pulse" />
                                            En attente
                                        </p>
                                    ) : status?.next_scheduled ? (
                                        <p className="text-cyan-400 font-mono text-sm">
                                            {new Date(status.next_scheduled).toLocaleDateString()}
                                        </p>
                                    ) : (
                                        <p className="text-white/40 font-mono text-sm">—</p>
                                    )}
                                </div>
                            </div>
                        </Section>

                        {/* OPTIONS - VIDEO PRODUCTION SETTINGS */}
                        <Section title={t.options} icon={Sliders} color="text-purple-400">
                            <div className="grid grid-cols-2 gap-2">
                                <OptionToggle
                                    icon={isActive ? Play : Pause}
                                    label={isActive ? t.active : t.paused}
                                    value={isActive}
                                    onChange={handleToggleStatus}
                                    activeColor="green"
                                    tooltip={tooltips.active}
                                    isTooltipActive={tooltip === 'active'}
                                    onTooltipEnter={() => setTooltip('active')}
                                    onTooltipLeave={() => setTooltip(null)}
                                />
                                <OptionToggle
                                    icon={Upload}
                                    label={t.uploadEnabled}
                                    value={uploadEnabled}
                                    onChange={handleToggleUpload}
                                    activeColor="red"
                                    tooltip={tooltips.uploadEnabled}
                                    isTooltipActive={tooltip === 'uploadEnabled'}
                                    onTooltipEnter={() => setTooltip('uploadEnabled')}
                                    onTooltipLeave={() => setTooltip(null)}
                                />
                                <OptionToggle
                                    icon={Type}
                                    label={t.subtitles}
                                    value={subtitlesEnabled}
                                    onChange={setSubtitlesEnabled}
                                    activeColor="cyan"
                                    tooltip={tooltips.subtitles}
                                    isTooltipActive={tooltip === 'subtitles'}
                                    onTooltipEnter={() => setTooltip('subtitles')}
                                    onTooltipLeave={() => setTooltip(null)}
                                />
                                <OptionToggle
                                    icon={FileCheck}
                                    label={t.placard}
                                    value={placardEnabled}
                                    onChange={setPlacardEnabled}
                                    activeColor="amber"
                                    tooltip={tooltips.placard}
                                    isTooltipActive={tooltip === 'placard'}
                                    onTooltipEnter={() => setTooltip('placard')}
                                    onTooltipLeave={() => setTooltip(null)}
                                />
                            </div>
                            {/* Pancarte Text Input (Dual Lang - Grid 2 Cols) */}
                            {placardEnabled && (
                                <div className="mt-3 grid grid-cols-2 gap-3 animate-in fade-in slide-in-from-top-2 duration-300">

                                    {/* FR Input */}
                                    <div>
                                        <label htmlFor="placard-text-fr" className="text-[10px] text-gray-400 uppercase font-bold tracking-wider mb-1 block">
                                            TEXTE FR
                                        </label>
                                        <input
                                            id="placard-text-fr"
                                            name="placard-text-fr"
                                            type="text"
                                            value={placardTextFr}
                                            onChange={(e) => setPlacardTextFr(e.target.value)}
                                            placeholder={status?.defaults?.placard_text || "L'IA qui pense librement"}
                                            className="w-full px-3 py-2 bg-black/30 border border-amber-500/30 rounded-lg text-white text-sm focus:outline-none focus:border-amber-500/60 transition-colors"
                                        />
                                    </div>

                                    {/* EN Input */}
                                    <div>
                                        <label htmlFor="placard-text-en" className="text-[10px] text-gray-400 uppercase font-bold tracking-wider mb-1 block">
                                            TEXTE EN
                                        </label>
                                        <input
                                            id="placard-text-en"
                                            name="placard-text-en"
                                            type="text"
                                            value={placardTextEn}
                                            onChange={(e) => setPlacardTextEn(e.target.value)}
                                            placeholder={status?.defaults?.placard_text_en || "The free-thinking AI"}
                                            className="w-full px-3 py-2 bg-black/30 border border-amber-500/30 rounded-lg text-white text-sm focus:outline-none focus:border-amber-500/60 transition-colors"
                                        />
                                    </div>
                                </div>
                            )}
                        </Section>

                        {/* NOTIFICATIONS - MOVED TO COL1 */}
                        <Section title={t.notifications} icon={Bell} color="text-cyan-400">
                            <div className="grid grid-cols-2 gap-2">
                                <OptionToggle
                                    icon={Upload}
                                    label={t.notifyUploads}
                                    value={notifyUploads}
                                    onChange={setNotifyUploads}
                                    activeColor="green"
                                    tooltip={tooltips.notifyUploads}
                                    isTooltipActive={tooltip === 'notifyUploads'}
                                    onTooltipEnter={() => setTooltip('notifyUploads')}
                                    onTooltipLeave={() => setTooltip(null)}
                                />
                                <OptionToggle
                                    icon={TrendingUp}
                                    label={t.notifyMilestones}
                                    value={notifyMilestones}
                                    onChange={setNotifyMilestones}
                                    activeColor="amber"
                                    tooltip={tooltips.notifyMilestones}
                                    isTooltipActive={tooltip === 'notifyMilestones'}
                                    onTooltipEnter={() => setTooltip('notifyMilestones')}
                                    onTooltipLeave={() => setTooltip(null)}
                                />
                                <OptionToggle
                                    icon={Zap}
                                    label={t.notifyPipeline}
                                    value={notifyPipeline}
                                    onChange={setNotifyPipeline}
                                    activeColor="purple"
                                    tooltip={tooltips.notifyPipeline}
                                    isTooltipActive={tooltip === 'notifyPipeline'}
                                    onTooltipEnter={() => setTooltip('notifyPipeline')}
                                    onTooltipLeave={() => setTooltip(null)}
                                />
                                <OptionToggle
                                    icon={AlertTriangle}
                                    label={t.notifyViral}
                                    value={notifyViral}
                                    onChange={setNotifyViral}
                                    activeColor="red"
                                    tooltip={tooltips.notifyViral}
                                    isTooltipActive={tooltip === 'notifyViral'}
                                    onTooltipEnter={() => setTooltip('notifyViral')}
                                    onTooltipLeave={() => setTooltip(null)}
                                />
                            </div>
                        </Section>
                    </Column>

                    {/* COLUMN 2: SCRIPTS & APPROVAL */}
                    <Column>
                        {/* SCRIPTS READY - 2 Columns: FR | EN */}
                        <Section title="SCRIPTS PRETS" icon={List} color="text-green-400">
                            {(() => {
                                const scripts = status?.scripts_ready || [];
                                const frScripts = scripts.filter(s => s.lang === 'fr');
                                const enScripts = scripts.filter(s => s.lang === 'en');
                                const maxLen = Math.max(frScripts.length, enScripts.length);

                                if (scripts.length === 0) {
                                    return <p className="text-white/30 text-xs text-center py-4">Aucun script prêt</p>;
                                }

                                return (
                                    <div className="grid grid-cols-2 gap-2 max-h-96 overflow-y-auto pr-1 custom-scrollbar">
                                        {/* FR Column */}
                                        <div className="space-y-1">
                                            <div className="text-[10px] text-blue-400 font-bold uppercase mb-1">🇫🇷 FR</div>
                                            {frScripts.map((script, i) => (
                                                <div
                                                    key={`fr-${i}`}
                                                    className="text-xs text-white/90 bg-blue-500/10 p-2 rounded border border-blue-500/20 hover:bg-blue-500/20 transition-colors"
                                                >
                                                    <div className="flex items-center gap-1">
                                                        <div className="font-bold truncate text-[11px] flex-1">{script.title}</div>
                                                        <div
                                                            className="text-white/30 hover:text-cyan-400 cursor-help flex-shrink-0"
                                                            onMouseEnter={(e) => {
                                                                const rect = e.currentTarget.getBoundingClientRect();
                                                                setTooltipPos({ x: rect.left, y: rect.top - 8 });
                                                                setTooltipContent(script.script_preview || 'Script non disponible');
                                                                setTooltip(`fr-${i}`);
                                                            }}
                                                            onMouseLeave={() => setTooltip(null)}
                                                        >
                                                            <HelpCircle size={10} />
                                                        </div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                        {/* EN Column */}
                                        <div className="space-y-1">
                                            <div className="text-[10px] text-red-400 font-bold uppercase mb-1">🇬🇧 EN</div>
                                            {enScripts.map((script, i) => (
                                                <div
                                                    key={`en-${i}`}
                                                    className="text-xs text-white/90 bg-red-500/10 p-2 rounded border border-red-500/20 hover:bg-red-500/20 transition-colors"
                                                >
                                                    <div className="flex items-center gap-1">
                                                        <div className="font-bold truncate text-[11px] flex-1">{script.title}</div>
                                                        <div
                                                            className="text-white/30 hover:text-cyan-400 cursor-help flex-shrink-0"
                                                            onMouseEnter={(e) => {
                                                                const rect = e.currentTarget.getBoundingClientRect();
                                                                setTooltipPos({ x: rect.right - 288, y: rect.top - 8 });
                                                                setTooltipContent(script.script_preview || 'Script non disponible');
                                                                setTooltip(`en-${i}`);
                                                            }}
                                                            onMouseLeave={() => setTooltip(null)}
                                                        >
                                                            <HelpCircle size={10} />
                                                        </div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                );
                            })()}
                        </Section>

                        {/* SCRIPT GENERATION - Shown when a pending script exists for approval */}
                        {status?.pending_script && (() => {
                            const pending = status.pending_script;
                            const versions = pending.versions || {};
                            const hasBoth = pending.has_both || (versions.fr && versions.en);
                            const currentScript = hasBoth ? (versions[scriptPreviewLang] || pending) : pending;

                            return (
                                <Section
                                    title={t.scriptGeneration}
                                    icon={Sparkles}
                                    color="text-purple-400"
                                    border="border-purple-500/30"
                                    headerRight={hasBoth && (
                                        <div className="flex gap-0.5">
                                            <button
                                                onClick={() => setScriptPreviewLang('fr')}
                                                className={`px-2 py-1 text-[10px] font-bold rounded-l transition-all ${scriptPreviewLang === 'fr'
                                                    ? 'bg-blue-500 text-white'
                                                    : 'bg-white/10 text-white/60 hover:bg-white/20'
                                                    }`}
                                            >
                                                🇫🇷
                                            </button>
                                            <button
                                                onClick={() => setScriptPreviewLang('en')}
                                                className={`px-2 py-1 text-[10px] font-bold rounded-r transition-all ${scriptPreviewLang === 'en'
                                                    ? 'bg-red-500 text-white'
                                                    : 'bg-white/10 text-white/60 hover:bg-white/20'
                                                    }`}
                                            >
                                                🇬🇧
                                            </button>
                                        </div>
                                    )}
                                >
                                    <div className="space-y-3">

                                        {/* Script Preview */}
                                        <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-3">
                                            <div className="flex items-center gap-2 mb-2">
                                                <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${currentScript.lang === 'fr' ? 'bg-blue-500/20 text-blue-400' : 'bg-red-500/20 text-red-400'}`}>
                                                    {currentScript.lang === 'fr' ? '🇫🇷 FR' : '🇬🇧 EN'}
                                                </span>
                                                <span className="text-white/50 text-[10px]">
                                                    {new Date(currentScript.created_at || Date.now()).toLocaleString()}
                                                </span>
                                            </div>
                                            <h4 className="text-white font-bold text-sm mb-2">{currentScript.title}</h4>
                                            <p className="text-white/70 text-xs leading-relaxed line-clamp-4 whitespace-pre-wrap">
                                                {currentScript.preview || currentScript.script_preview || 'Script preview not available...'}
                                            </p>
                                        </div>

                                        {/* Action Buttons */}
                                        <div className="flex gap-2">
                                            <button
                                                onClick={() => handleScriptAction('approve', currentScript.id)}
                                                disabled={isScriptAction !== null}
                                                className="flex-1 px-3 py-2 bg-green-500/20 text-green-400 text-xs font-bold rounded hover:bg-green-500/30 transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50 border border-green-500/30"
                                            >
                                                {isScriptAction === 'approve' ? <Loader size={14} className="animate-spin" /> : <CheckCircle size={14} />}
                                                {t.approve}
                                            </button>
                                            <button
                                                onClick={() => handleScriptAction('retry', currentScript.id)}
                                                disabled={isScriptAction !== null}
                                                className="flex-1 px-3 py-2 bg-amber-500/20 text-amber-400 text-xs font-bold rounded hover:bg-amber-500/30 transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50 border border-amber-500/30"
                                            >
                                                {isScriptAction === 'retry' ? <Loader size={14} className="animate-spin" /> : <RotateCcw size={14} />}
                                                {t.retry}
                                            </button>
                                            <button
                                                onClick={() => handleScriptAction('reject', currentScript.id)}
                                                disabled={isScriptAction !== null}
                                                className="flex-1 px-3 py-2 bg-red-500/20 text-red-400 text-xs font-bold rounded hover:bg-red-500/30 transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50 border border-red-500/30"
                                            >
                                                {isScriptAction === 'reject' ? <Loader size={14} className="animate-spin" /> : <XCircle size={14} />}
                                                {t.reject}
                                            </button>
                                        </div>
                                    </div>
                                </Section>
                            );
                        })()}

                        {/* PENDING UPLOAD - Shown when Auto Upload is OFF and videos are ready */}
                        {!uploadEnabled && (status?.pending_count > 0 || (status?.scripts_ready || []).length > 0) && (
                            <Section title={t.pendingUpload} icon={Upload} color="text-amber-400" border="border-amber-500/30">
                                <div className="space-y-2">
                                    {(status?.pending_videos || []).length > 0 ? (
                                        <div className="space-y-2 max-h-48 overflow-y-auto">
                                            {(status.pending_videos || []).map((video, i) => (
                                                <div key={i} className="flex items-center justify-between bg-amber-500/10 p-2 rounded border border-amber-500/20">
                                                    <div className="flex-1 overflow-hidden">
                                                        <div className="font-bold text-xs text-white truncate">{video.title || `Video ${i + 1}`}</div>
                                                        <div className="text-[10px] text-amber-400/60">{video.lang?.toUpperCase() || 'FR'}</div>
                                                    </div>
                                                    <button
                                                        onClick={() => handlePublish(video)}
                                                        className="ml-2 px-3 py-1 bg-green-500/20 text-green-400 text-xs font-bold rounded hover:bg-green-500/30 transition-colors flex items-center gap-1"
                                                    >
                                                        <Upload size={12} />
                                                        {t.publish}
                                                    </button>
                                                </div>
                                            ))}
                                        </div>
                                    ) : (
                                        <p className="text-white/30 text-xs text-center py-2">
                                            {locale === 'fr' ? 'Aucune vidéo en attente' : 'No videos pending'}
                                        </p>
                                    )}
                                </div>
                            </Section>
                        )}

                        {/* APPROVAL - Only if no scripts and pipeline empty */}
                        {((status?.scripts_ready || []).length === 0) && (
                            <Section title="APPROVAL NEEDED" icon={AlertTriangle} color="text-amber-400" border="border-amber-500/30">
                                <div className="space-y-2">
                                    <p className="text-[10px] text-amber-400/80 uppercase font-bold tracking-wider mb-2">
                                        Pipeline Empty - Approve New Topic
                                    </p>
                                    <div className="flex gap-2">
                                        <input
                                            id="new-topic-input"
                                            name="new-topic-input"
                                            value={newTopic}
                                            onChange={(e) => setNewTopic(e.target.value)}
                                            placeholder="Sujet à approuver..."
                                            className="flex-1 bg-amber-500/5 border border-amber-500/20 rounded px-2 py-2 text-sm text-white focus:outline-none focus:border-amber-500/50 placeholder-amber-500/20"
                                            onKeyDown={(e) => e.key === 'Enter' && handleAddTopic()}
                                        />
                                        <button
                                            onClick={handleAddTopic}
                                            disabled={isAddingTopic || !newTopic.trim()}
                                            className="px-3 py-1 bg-amber-500/20 text-amber-400 rounded hover:bg-amber-500/30 transition-colors disabled:opacity-50"
                                        >
                                            {isAddingTopic ? <Loader size={14} className="animate-spin" /> : <Plus size={14} />}
                                        </button>
                                    </div>
                                    <div className="mt-2 text-[10px] text-white/30">
                                        * Approuver ce sujet lancera la génération de script immédiate par le Producteur.
                                    </div>
                                </div>
                            </Section>
                        )}
                    </Column>

                    {/* COLUMN 3: RECENT & UPCOMING LIST */}
                    <Column>
                        <div className="flex-1 min-h-0 flex flex-col gap-2 overflow-hidden">
                            {/* FR CARD */}
                            <Section title="TRINITY IA (FR)" icon={Video} color="text-indigo-400" className="flex-1 min-h-0 flex flex-col">
                                <div className="space-y-2 overflow-y-auto pr-1 flex-1 custom-scrollbar">
                                    {upcomingVideos.filter(v => v.lang === 'fr').length > 0 && (
                                        <div className="mb-2">
                                            <div className="text-[10px] font-bold text-amber-400 mb-1 uppercase">{t.nextScheduled}</div>
                                            {upcomingVideos.filter(v => v.lang === 'fr').map(vid => (
                                                <div key={vid.id} className="bg-amber-500/10 border border-amber-500/30 rounded p-1 mb-1">
                                                    <p className="text-white/90 text-xs truncate">{vid.title}</p>
                                                    <p className="text-amber-400 text-[10px]">{new Date(vid.scheduled_for).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                    {frVideos.length > 0 ? frVideos.map(vid => (
                                        <div key={vid.id} className="bg-white/5 border border-white/5 rounded p-2 hover:bg-white/10 transition-colors">
                                            <div className="flex justify-between items-start mb-1">
                                                <div className="flex items-center gap-2">
                                                    <span className={`text-[10px] font-bold uppercase tracking-wider ${vid.status === 'PUBLISHED' ? 'text-green-400' : 'text-white/50'}`}>
                                                        {vid.status}
                                                    </span>
                                                    {vid.type === 'SHORT' && (
                                                        <span className="text-[9px] bg-red-500/20 text-red-400 px-1 rounded border border-red-500/30 font-bold">
                                                            SHORT
                                                        </span>
                                                    )}
                                                </div>
                                                {vid.status === 'PUBLISHED' && <CheckCircle size={12} className="text-green-400" />}
                                            </div>
                                            <p className="text-white/80 text-xs line-clamp-2" title={vid.title}>{vid.title}</p>
                                            <div className="flex justify-between mt-1">
                                                <div className="flex gap-2 text-[10px] text-white/40">
                                                    <span>{vid.likes || 0} ♥</span>
                                                    <span>{vid.comments || 0} 💬</span>
                                                </div>
                                                <p className="text-purple-400 text-[10px] font-mono">{vid.views || 0} views</p>
                                            </div>
                                        </div>
                                    )) : <p className="text-white/30 text-xs text-center p-2">Vide</p>}
                                </div>
                            </Section>

                            {/* EN CARD */}
                            <Section title="TRINITY AI (EN)" icon={Video} color="text-cyan-400" className="flex-1 min-h-0 flex flex-col">
                                <div className="space-y-2 overflow-y-auto pr-1 flex-1 custom-scrollbar">
                                    {upcomingVideos.filter(v => v.lang !== 'fr').length > 0 && (
                                        <div className="mb-2">
                                            <div className="text-[10px] font-bold text-amber-400 mb-1 uppercase">{t.nextScheduled}</div>
                                            {upcomingVideos.filter(v => v.lang !== 'fr').map(vid => (
                                                <div key={vid.id} className="bg-amber-500/10 border border-amber-500/30 rounded p-1 mb-1">
                                                    <p className="text-white/90 text-xs truncate">{vid.title}</p>
                                                    <p className="text-amber-400 text-[10px]">{new Date(vid.scheduled_for).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                    {enVideos.length > 0 ? enVideos.map(vid => (
                                        <div key={vid.id} className="bg-white/5 border border-white/5 rounded p-2 hover:bg-white/10 transition-colors">
                                            <div className="flex justify-between items-start mb-1">
                                                <div className="flex items-center gap-2">
                                                    <span className={`text-[10px] font-bold uppercase tracking-wider ${vid.status === 'PUBLISHED' ? 'text-green-400' : 'text-white/50'}`}>
                                                        {vid.status}
                                                    </span>
                                                    {vid.type === 'SHORT' && (
                                                        <span className="text-[9px] bg-red-500/20 text-red-400 px-1 rounded border border-red-500/30 font-bold">
                                                            SHORT
                                                        </span>
                                                    )}
                                                </div>
                                                {vid.status === 'PUBLISHED' && <CheckCircle size={12} className="text-green-400" />}
                                            </div>
                                            <p className="text-white/80 text-xs line-clamp-2" title={vid.title}>{vid.title}</p>
                                            <div className="flex justify-between mt-1">
                                                <div className="flex gap-2 text-[10px] text-white/40">
                                                    <span>{vid.likes || 0} ♥</span>
                                                    <span>{vid.comments || 0} 💬</span>
                                                </div>
                                                <p className="text-purple-400 text-[10px] font-mono">{vid.views || 0} views</p>
                                            </div>
                                        </div>
                                    )) : <p className="text-white/30 text-xs text-center p-2">Empty</p>}
                                </div>
                            </Section>
                        </div>
                    </Column>
                </ResponsiveGrid>
            </PanelLayout>

            {/* Tooltip Portal - Escapes overflow:hidden */}
            {
                tooltip && tooltipContent && createPortal(
                    <div
                        className="fixed z-[99999] bg-black/95 border border-cyan-500/50 rounded-lg p-3 text-xs text-white/90 w-72 shadow-xl whitespace-pre-wrap max-h-48 overflow-y-auto pointer-events-none"
                        style={{ left: tooltipPos.x, top: tooltipPos.y, transform: 'translateY(-100%)' }}
                    >
                        {tooltipContent}
                    </div>,
                    document.body
                )
            }
        </>
    );
}
