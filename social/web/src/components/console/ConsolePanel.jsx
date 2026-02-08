import React, { useState } from 'react';
import { useTrinityStore } from '../../stores/trinityStore';
import LogTable from './LogTable';
import TokensTable from './TokensTable';
import { Activity, AlertTriangle, DollarSign, Brain, Database, Video, Users, Trash2, Clipboard, Check, Loader, Bot, Share2 } from 'lucide-react';
import { clearLogs } from '../../services/angelService';
import { useLogsWebSocket } from '../../hooks/useLogsWebSocket';
import { TabBar } from '../ui/PanelKit';

const DICT = {
    en: {
        alerts: 'ALERTS',
        angel: 'ANGEL',
        trinity: 'TRINITY',
        jules: 'JULES',
        social: 'SOCIAL',
        trader: 'TRADER',
        youtuber: 'YOUTUBER',
        influencer: 'INFLUENCER',
        tokens: 'TOKENS',
        status: 'STATUS',
        online: 'ONLINE',
        connecting: 'CONNECTING...',
        liveWebsocket: 'LIVE WEBSOCKET',
        reconnecting: 'RECONNECTING',
        clearLogs: 'Clear Logs',
        copyClipboard: 'Copy to Clipboard',
    },
    fr: {
        alerts: 'ALERTES',
        angel: 'ANGEL',
        trinity: 'TRINITY',
        jules: 'JULES',
        social: 'SOCIAL',
        trader: 'TRADEUR',
        youtuber: 'YOUTUBER',
        influencer: 'INFLUENCEUR',
        tokens: 'JETONS',
        status: 'STATUT',
        online: 'EN LIGNE',
        connecting: 'CONNEXION...',
        liveWebsocket: 'WEBSOCKET LIVE',
        reconnecting: 'RECONNEXION',
        clearLogs: 'Effacer les Logs',
        copyClipboard: 'Copier',
    }
};

const getTabs = (t) => [
    { id: 'ALERTS', label: t.alerts, icon: AlertTriangle, color: 'text-red-500' },
    { id: 'ANGEL', label: t.angel, icon: Activity, color: 'text-blue-400' },
    { id: 'TRINITY', label: t.trinity, icon: Brain, color: 'text-purple-400' },
    { id: 'JULES', label: t.jules, icon: Bot, color: 'text-emerald-400' },
    { id: 'SOCIAL', label: t.social, icon: Share2, color: 'text-sky-400' },
    { id: 'TRADER', label: t.trader, icon: DollarSign, color: 'text-cyan-400' },
    { id: 'YOUTUBER', label: t.youtuber, icon: Video, color: 'text-pink-400' },
    { id: 'INFLUENCER', label: t.influencer, icon: Users, color: 'text-orange-400' },
    { id: 'TOKENS', label: t.tokens, icon: Database, color: 'text-green-400' },
];


const ConsolePanel = () => {
    // SOTA 2026: WebSocket-based Log Management (Real-time like Extension)
    const { logs, tokens, activeTab, setActiveTab, isAlive, clearLogs: clearStoreLogs, locale } = useTrinityStore();
    const t = DICT[locale] || DICT.fr;
    const TABS = getTabs(t);

    // UI Feedback States
    const [isCopying, setIsCopying] = useState(false);
    const [isClearing, setIsClearing] = useState(false);

    // Connect to WebSocket
    useLogsWebSocket();


    // Display Logic: Filter from global store based on activeTab
    // This matches Extension logic exactly
    const filterLogs = (logs, tab) => {
        if (tab === 'TOKENS') return []; // Handled by TokensTable
        return logs.filter(log => {
            // Handle legacy string logs (show in TRINITY tab by default)
            if (typeof log === 'string') return tab === 'TRINITY';

            const source = (log.source || log.module || '').toUpperCase();

            if (tab === 'ALERTS') return source === 'ALERTS' || log.level === 'ERROR' || log.level === 'CRITICAL' || log.level === 'WARNING';
            if (tab === 'ANGEL') return source === 'ANGEL';
            if (tab === 'TRINITY') {
                // SOTA 2026: Core Systems Only (not JULES/SOCIAL)
                return source.includes('TRINITY') ||
                    source === 'SYSTEM' ||
                    source.includes('CORPUS') ||
                    source.includes('DNA');
            }
            if (tab === 'JULES') {
                return source.includes('JULES') || source.includes('FORGE') || source.includes('COUNCIL');
            }
            if (tab === 'SOCIAL') {
                return source.includes('SOCIAL') || source.includes('DISCORD');
            }

            // For jobs (TRADER, YOUTUBER, etc)
            return source.includes(tab);
        });
    };

    const handleClear = async () => {
        if (isClearing) return;
        setIsClearing(true);
        try {
            // 1. Clear Backend (Disk) - This will also broadcast clear to all WS clients
            await clearLogs(activeTab);
            // 2. Clear Store (Memory) - Immediate UI feedback (WS will also send clear event)
            clearStoreLogs(activeTab);
        } catch (e) {
            console.error("Failed to clear logs:", e);
        } finally {
            // Small delay to show the spinner
            setTimeout(() => setIsClearing(false), 500);
        }
    };

    // SOTA 2026: Robust Clipboard Fallback
    const copyToClipboard = async (text) => {
        if (!navigator.clipboard) {
            // Fallback for non-secure contexts (HTTP)
            const textArea = document.createElement("textarea");
            textArea.value = text;
            textArea.style.position = "fixed";  // Avoid scrolling to bottom
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            try {
                document.execCommand('copy');
                return true;
            } catch (err) {
                console.error('Fallback: Oops, unable to copy', err);
                return false;
            } finally {
                document.body.removeChild(textArea);
            }
        }
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (err) {
            console.error('Async: Could not copy text: ', err);
            return false;
        }
    };

    const handleCopy = async () => {
        const displayLogs = filterLogs(logs, activeTab);
        const text = displayLogs.map(log =>
            `[${new Date(log.timestamp).toLocaleTimeString()}] ${log.level || 'INFO'} | ${log.module || '-'} | ${log.message || log.msg || ''}`
        ).join('\n');

        const success = await copyToClipboard(text);
        if (success) {
            setIsCopying(true);
            setTimeout(() => setIsCopying(false), 2000);
        }
    };

    const displayLogs = React.useMemo(() => filterLogs(logs, activeTab), [logs, activeTab]);

    return (
        <div className="flex flex-col w-full h-full bg-black/90 text-white overflow-hidden">
            {/* TABS HEADER */}
            <div className="flex items-center justify-between p-2 bg-black/40 border-b border-white/10 shrink-0">
                <TabBar
                    tabs={TABS}
                    activeTab={activeTab}
                    onChange={setActiveTab}
                    size="md"
                />

                <div className="flex items-center gap-2 pl-4 border-l border-white/10 ml-2">
                    <button
                        onClick={handleClear}
                        disabled={isClearing}
                        className={`p-2 rounded transition-colors ${isClearing ? 'text-white cursor-wait' : 'text-white/40 hover:text-white hover:bg-white/10'}`}
                        title={t.clearLogs}
                    >
                        {isClearing ? <Loader size={16} className="animate-spin text-red-500" /> : <Trash2 size={16} />}
                    </button>
                    <button
                        onClick={handleCopy}
                        disabled={isCopying}
                        className={`p-2 rounded transition-colors ${isCopying ? 'text-green-400' : 'text-white/40 hover:text-white hover:bg-white/10'}`}
                        title={t.copyClipboard}
                    >
                        {isCopying ? <Check size={16} /> : <Clipboard size={16} />}
                    </button>
                </div>
            </div>

            {/* CONTENT AREA */}
            <div className="flex-1 overflow-hidden relative">
                {activeTab === 'TOKENS' ? (
                    <TokensTable tokens={tokens} />
                ) : (
                    <LogTable logs={displayLogs} />
                )}
            </div>

            {/* STATUS FOOTER */}
            <div className="h-6 bg-black border-t border-white/10 flex items-center justify-between px-2 text-[10px] uppercase text-white/30 font-mono shrink-0">
                <span>{t.status}: {isAlive ? t.online : t.connecting}</span>
                <span className="flex items-center gap-2">
                    <span className={`w-1.5 h-1.5 rounded-full ${isAlive ? 'bg-green-500 animate-pulse' : 'bg-yellow-500'}`} />
                    {isAlive ? t.liveWebsocket : t.reconnecting}
                </span>
            </div>
        </div>
    );
};

export default ConsolePanel;

