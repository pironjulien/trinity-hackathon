import React from 'react';
import { useTrinityStore } from '../lib/store';
import { useTrinity } from '../lib/useTrinity';
import './AppHeader.css';

const brandLetters = [
    { letter: 'T', color: '#4285F4' },  // Blue
    { letter: 'R', color: '#EA4335' },  // Red
    { letter: 'I', color: '#FBBC05' },  // Yellow
    { letter: 'N', color: '#4285F4' },  // Blue
    { letter: 'I', color: '#34A853' },  // Green
    { letter: 'T', color: '#EA4335' },  // Red
    { letter: 'Y', color: '#FBBC05' }   // Yellow
];

export const AppHeader: React.FC = () => {
    const { send } = useTrinity();
    const {
        version,
        pulseColor,
        aiQuote,
        lang,
        setLang,
        stagedProjectsCount,
        evolutionReport
    } = useTrinityStore();

    // Handlers for sentinel buttons
    const handleJulesClick = () => {
        if (stagedProjectsCount > 0) {
            send('openStagedProjects');
        }
    };

    const handleEvolutionClick = () => {
        if (evolutionReport?.hasReport) {
            send('openEvolutionReport', { lang });
        }
    };

    return (
        <header className="app-header">
            <div className="header-left">
                {/* Brand */}
                <span className="brand">
                    {brandLetters.map((l, i) => (
                        <span key={i} style={{ color: l.color }}>{l.letter}</span>
                    ))}
                    <span className="matrix-tag">8810</span>
                    <span className="version-tag">{version}</span>
                </span>

                {/* SOTA 2026: Sentinel Buttons (Alert Indicators) */}
                <div className="header-sentinels">
                    {/* Jules Staged Projects Button */}
                    <button
                        className={`sentinel-btn ${stagedProjectsCount > 0 ? 'glow-jules' : 'disabled'}`}
                        onClick={handleJulesClick}
                        disabled={stagedProjectsCount === 0}
                        title={stagedProjectsCount > 0 ? `${stagedProjectsCount} projets Jules en attente` : 'Aucun projet Jules'}
                    >
                        🤖 {stagedProjectsCount > 0 && <span className="sentinel-count">{stagedProjectsCount}</span>}
                    </button>

                    {/* Evolution Report Button */}
                    <button
                        className={`sentinel-btn ${evolutionReport?.hasReport ? 'glow-evolution' : 'disabled'}`}
                        onClick={handleEvolutionClick}
                        disabled={!evolutionReport?.hasReport}
                        title={evolutionReport?.hasReport ? evolutionReport.summary || 'Rapport évolution disponible' : 'Pas de rapport'}
                    >
                        🧬
                    </button>
                </div>
            </div>

            {/* Cylon Pulse Bar */}
            <div className="cylon-container">
                <div
                    className={`cylon-bar ${pulseColor ? 'pulse-active' : ''}`}
                    style={{ boxShadow: pulseColor ? `0 0 15px ${pulseColor}` : '' }}
                />

                {/* AI Quote Overlay */}
                {aiQuote && (
                    <div className="ai-quote-overlay">
                        "{aiQuote}"
                    </div>
                )}
            </div>

            <div className="header-right">
                {/* Language Switch */}
                <div className="lang-switch-header">
                    <span
                        className={lang === 'EN' ? 'active' : ''}
                        onClick={() => setLang('EN')}
                    >EN</span>
                    <span
                        className={lang === 'FR' ? 'active' : ''}
                        onClick={() => setLang('FR')}
                    >FR</span>
                </div>
            </div>
        </header>
    );
};
