import React, { useState } from 'react';
import { useTrinityStore } from '../lib/store';
import { useTrinity } from '../lib/useTrinity';
import LogTable from './LogTable';
import TokensTable from './TokensTable';
import './ConsolePanel.css';

const TABS = ['ALERTS', 'ANGEL', 'TRINITY', 'JULES', 'SOCIAL', 'TRADER', 'YOUTUBER', 'INFLUENCER', 'TOKENS'] as const;

const ConsolePanel: React.FC = () => {
    const { activeTab, setActiveTab, logs, tokens, clearLogs, lang } = useTrinityStore();
    const { send } = useTrinity();
    const [copySuccess, setCopySuccess] = useState(false);
    const [clearSuccess, setClearSuccess] = useState(false);

    // Simple dictionary for UI strings
    const dict = {
        EN: {
            cleared: "Cleared!",
            clear: "Clear",
            copied: "Copied!",
            copy: "Copy",
            switch: "Switch to",
            tabs: {
                ALERTS: "ALERTS",
                ANGEL: "ANGEL",
                TRINITY: "TRINITY",
                JULES: "JULES",
                SOCIAL: "SOCIAL",
                TRADER: "TRADER",
                YOUTUBER: "YOUTUBER",
                INFLUENCER: "INFLUENCER",
                TOKENS: "TOKENS"
            }
        },
        FR: {
            cleared: "Effacé !",
            clear: "Effacer",
            copied: "Copié !",
            copy: "Copier",
            switch: "Voir",
            tabs: {
                ALERTS: "ALERTES",
                ANGEL: "ANGEL",
                TRINITY: "TRINITY",
                JULES: "JULES",
                SOCIAL: "SOCIAL",
                TRADER: "TRADEUR",
                YOUTUBER: "YOUTUBEUR",
                INFLUENCER: "INFLUENCEUR",
                TOKENS: "JETONS"
            }
        }
    };

    const t = dict[lang] || dict.EN;

    // Helper function to filter logs by tab (same logic as LogTable rendering)
    const filterLogsByTab = (tab: typeof activeTab) => {
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
                return source.includes('SOCIAL') || source.includes('TELEGRAM') || source.includes('DISCORD');
            }
            if (tab === 'TOKENS') return false; // Tokens have their own table

            // For jobs (TRADER, YOUTUBER, etc)
            return source.includes(tab);
        });
    };

    const handleCopy = () => {
        // SOTA 2026 FIX: Copy only the logs from the active tab, not all logs
        const filteredLogs = filterLogsByTab(activeTab);
        const text = filteredLogs.map(l => typeof l === 'string' ? l : JSON.stringify(l)).join('\n');
        navigator.clipboard.writeText(text);
        setCopySuccess(true);
        setTimeout(() => setCopySuccess(false), 1500);
    };

    const handleClear = () => {
        // Clear logs on disk via Angel API - pass current tab
        send('CLEAR_LOGS', { tab: activeTab });
        // Clear only current tab's logs in UI memory
        clearLogs(activeTab);
        setClearSuccess(true);
        setTimeout(() => setClearSuccess(false), 1500);
    };

    return (
        <div className="console-panel">
            {/* Tabs Header */}
            <div className="tabs-header">
                <div className="tabs-list">
                    {TABS.map(tab => (
                        <div
                            key={tab}
                            className={`tab-item ${activeTab === tab ? 'active' : ''}`}
                            onClick={() => setActiveTab(tab)}
                            title={`${t.switch} ${t.tabs[tab]}`}
                        >
                            {t.tabs[tab]}
                            {activeTab === tab && <div className="ink-bar" />}
                        </div>
                    ))}
                </div>

                <div className="tools-list">
                    <button
                        className="icon-btn"
                        onClick={handleClear}
                        title={clearSuccess ? t.cleared : t.clear}
                    >
                        {clearSuccess ? '✅' : '🗑️'}
                    </button>
                    <button
                        className="icon-btn"
                        onClick={handleCopy}
                        title={copySuccess ? t.copied : t.copy}
                    >
                        {copySuccess ? '✅' : '📋'}
                    </button>
                </div>
            </div>

            {/* Console Content */}
            <div className="console-wrapper">
                {activeTab === 'TOKENS' ? (
                    <TokensTable tokens={tokens} lang={lang} />
                ) : (
                    <LogTable logs={filterLogsByTab(activeTab)} />
                )}
            </div>
        </div>
    );
};

export default ConsolePanel;
