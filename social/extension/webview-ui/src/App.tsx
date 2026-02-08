import { useState, useEffect } from 'react';
import { useTrinity } from './lib/useTrinity';
import { useTrinityStore } from './lib/store';
import { AppHeader } from './components/AppHeader';
import AngelPlayer from './components/AngelPlayer';
import StatsPanel from './components/StatsPanel';
import { CommandButtons } from './components/CommandButtons';
import JobsPanel from './components/JobsPanel';
import StatusPanel from './components/StatusPanel';
import ConsolePanel from './components/ConsolePanel';
import './App.css';

// 4 States of Existence (SOTA 2026)
type ViewMode = 'OFFLINE' | 'INIT' | 'ANGEL' | 'TRINITY';

function App() {
    const { send } = useTrinity();
    const status = useTrinityStore(s => s.status); // SOTA Optimization: Select only status
    const lang = useTrinityStore(s => s.lang);
    const [viewMode, setViewMode] = useState<ViewMode>('OFFLINE');

    // i18n Dictionary
    const dict = {
        EN: {
            systemOffline: "SYSTEM OFFLINE",
            systemConnecting: "CONNECTING...",
            systemDisconnecting: "DISCONNECTING...",
            angelOnline: "ANGEL SYSTEM ONLINE",
            videoMissing: "(Video Asset Missing)"
        },
        FR: {
            systemOffline: "SYSTÈME HORS LIGNE",
            systemConnecting: "CONNEXION...",
            systemDisconnecting: "DÉCONNEXION...",
            angelOnline: "SYSTÈME ANGEL EN LIGNE",
            videoMissing: "(Vidéo manquante)"
        }
    };
    const t = dict[lang] || dict.EN;

    // State Logic Machine
    useEffect(() => {
        if (status === 'offline' || status === 'error' || status === 'stopping') {
            setViewMode('OFFLINE');
        } else if (status === 'connecting') {
            // SOTA 2026: Show simple connecting message (not init video)
            // Init video is only for Trinity startup
            setViewMode('OFFLINE'); // Use OFFLINE view with connecting variant
        } else if (status === 'active') {
            setViewMode('TRINITY');
        } else {
            // "sleeping" -> Angel Mode (Connected but Trinity waiting)
            setViewMode('ANGEL');
        }
        console.log('[App] ViewMode Changed:', status, '->', viewMode);
    }, [status]);

    // Initial Connect
    useEffect(() => {
        send('startPolling');
    }, [send]);

    return (
        <div className="app-container">
            <AppHeader />

            {/* MAIN STAGE (SOTA 2026 Logic) */}
            <div className="main-stage">

                {/* 1. OFFLINE / CONNECTING: Black Void */}
                {viewMode === 'OFFLINE' && (
                    <div className="offline-overlay">
                        {status === 'stopping' ? (
                            <div className="offline-msg disconnecting">
                                <span className="spinner">🔻</span> {t.systemDisconnecting}
                            </div>
                        ) : status === 'connecting' ? (
                            <div className="offline-msg connecting">
                                <span className="spinner">⏳</span> {t.systemConnecting}
                            </div>
                        ) : (
                            <div className="offline-msg">{t.systemOffline}</div>
                        )}
                    </div>
                )}

                {/* 2. INIT: Initialization Video */}
                {viewMode === 'INIT' && (
                    <div className="video-container">
                        {(window as any).videoUris?.init ? (
                            <AngelPlayer src={(window as any).videoUris.init} />
                        ) : (
                            <div className="offline-overlay">
                                <div className="offline-msg connecting">
                                    <span className="spinner">⏳</span> {t.systemConnecting}
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* 3. ANGEL: Video Loop */}
                {viewMode === 'ANGEL' && (
                    <div className="video-container">
                        {(window as any).angelVideoUri ? (
                            <AngelPlayer src={(window as any).angelVideoUri} />
                        ) : (
                            <div className="offline-overlay">
                                <div className="offline-msg">{t.angelOnline}<br />{t.videoMissing}</div>
                            </div>
                        )}
                    </div>
                )}

                {/* 4. TRINITY: Scaled Iframe (Height-Priority 900p) */}
                {viewMode === 'TRINITY' && (
                    <div className="webview-container" ref={container => {
                        if (container) {
                            const updateScale = () => {
                                const wrapper = container.querySelector('.webview-scaler') as HTMLElement;
                                if (wrapper) {
                                    const availableWidth = container.clientWidth;
                                    const availableHeight = container.clientHeight;

                                    // SOTA 2026: Height-Priority Scaling (900p Reference)
                                    // 1600x900 is the sweet spot for VS Code panels.
                                    // 1. Calculate scale to fit height perfectly
                                    const scale = availableHeight / 900;

                                    // 2. Calculate necessary virtual width to cover the container width
                                    const virtualWidth = availableWidth / scale;

                                    // 3. Apply Dimensions
                                    wrapper.style.height = '900px';
                                    wrapper.style.width = `${virtualWidth}px`;

                                    // 4. Apply Scale (Top-Left Origin)
                                    wrapper.style.transform = `scale(${scale})`;

                                    // 5. Reset positioning
                                    wrapper.style.left = '0px';
                                    wrapper.style.top = '0px';
                                }
                            };

                            // Initialize & Listen
                            updateScale();
                            const observer = new ResizeObserver(updateScale);
                            observer.observe(container);
                            return () => observer.disconnect();
                        }
                    }}>
                        <div className="webview-scaler">
                            <iframe
                                src="http://localhost:8089"
                                className="webview-iframe"
                                title="Trinity Web"
                            />
                        </div>
                    </div>
                )}
            </div>

            {/* HUD OVERLAY */}
            <div className={`hud-layer ${viewMode === 'OFFLINE' ? 'hud-offline' : ''}`}>
                <div className="col-left">
                    <StatsPanel />
                    <CommandButtons />
                    <div className="bottom-panels">
                        <JobsPanel />
                        <StatusPanel />
                    </div>
                </div>
                <ConsolePanel />
            </div>
        </div>
    );
}

export default App;
