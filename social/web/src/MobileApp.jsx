/**
 * MobileApp.jsx - SOTA 2026
 * Layout mobile 3 panels swipables pour Capacitor Android
 * 
 * Panel 0 (Gauche): OPERATIONS - Trinity, Trader, Influencer, YouTuber
 * Panel 1 (Centre): TRINITY - Visage + Chat (App.jsx simplifiée)
 * Panel 2 (Droite): INTELLIGENCE - Settings, Jules, Logs, Objectives
 */

import React, { useState, useEffect, useMemo, useCallback, Suspense } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Capacitor } from '@capacitor/core';
import { App } from '@capacitor/app';

// SOTA 2026: Custom URL Scheme Deep-Link Handler (trinity://msg/<id>)

import { useTrinityStore } from './stores/trinityStore';
import { useJulesStore } from './stores/julesStore';
import { useNotificationStore } from './stores/notificationStore'; // SOTA 2026: Deep Link
import { startPolling, stopPolling, ANGEL_BASE_URL, getTrinityHeaders } from './services/angelService';
import { useDataPreloader } from './services/dataPreloader';
import { Haptics, NotificationType } from '@capacitor/haptics'; // SOTA 2026: Premium Feel
import { Badge } from '@capawesome/capacitor-badge'; // SOTA 2026: App Icon Badge

import VideoEngine from './components/core/VideoEngine';
import CyberWindow from './components/layout/CyberWindow';
import InputBar from './components/hud/InputBar';
import ChatContainer from './components/chat/ChatContainer';
import TrinityPanel from './components/core/TrinityPanel';
import TraderPanel from './components/trader/TraderPanel';
import InfluencerPanel from './components/influencer/InfluencerPanel';
import YoutuberPanel from './components/youtuber/YoutuberPanel';
import SettingsBar from './components/ui/SettingsBar';
import JulesPanel from './components/jules/JulesPanel';
import ConsolePanel from './components/console/ConsolePanel';
import NativeMessageFeed from './components/notifications/NativeMessageFeed'; // SOTA 2026: Native Messaging
import ObjectivesPanel from './components/core/ObjectivesPanel';
import SceneContainer from './components/SceneContainer';

import enLocale from './locales/en.json';
import frLocale from './locales/fr.json';

const AngelSplash = React.lazy(() => import('./components/core/AngelSplash'));

const LOCALES = { en: enLocale, fr: frLocale };

// Constants
const PANEL_NAMES = ['OPERATIONS', 'TRINITY', 'INTELLIGENCE'];
const SWIPE_THRESHOLD = 50;

function MobileApp() {
    const [currentPanel, setCurrentPanel] = useState(1); // Start on TRINITY (center)
    const [touchStart, setTouchStart] = useState(null);
    const [touchEnd, setTouchEnd] = useState(null);
    const [connectionError, setConnectionError] = useState(null); // SOTA 2026: Debug Error State

    // Parallax offset based on current panel - SOTA 2026
    // Panel 0 (left): video shifts right (+10%)
    // Panel 1 (center): video centered (0%)
    // Panel 2 (right): video shifts left (-10%)
    const parallaxOffset = (1 - currentPanel) * 10; // percent

    // Store
    const {
        isAuthenticated, locale, jobsStatus, setAllJobsStatus,
        trinityStatus, setTrinityStatus, liveLogsEnabled, fetchConfig,
        isShuttingDown, setShuttingDown, addLog,
        setAuthenticated, setRole, setUser, setToken, unlockAudio
    } = useTrinityStore();
    const { isActive: julesActive } = useJulesStore();
    const t = useMemo(() => LOCALES[locale] || LOCALES.en, [locale]);

    // SOTA 2026: Preload all panel data when Trinity becomes running
    useDataPreloader();

    // SOTA 2026: Get selectNotificationById for deep-linking
    const { unreadCount, selectNotificationById } = useNotificationStore();

    // SOTA 2026: Update App Badge with Unread Count
    useEffect(() => {
        if (Capacitor.getPlatform() !== 'android') return;
        const updateBadge = async () => {
            try {
                if (unreadCount > 0) {
                    await Badge.set({ count: unreadCount });
                } else {
                    await Badge.clear();
                }
            } catch (e) {
                console.warn('[Badge] Update failed:', e);
            }
        };
        updateBadge();
    }, [unreadCount]);

    // ... imports ...

    // SOTA 2026: Custom URL Scheme Deep-Link Handler (trinity://msg/<id>)
    // Works reliably on Cold Start via Capacitor App Plugin
    useEffect(() => {
        const handleDeepLink = (url) => {
            if (!url) return;
            console.log('[MobileApp] Deep-link URL opened:', url);

            if (url.startsWith('trinity://msg/')) {
                const notifId = url.split('trinity://msg/')[1];
                if (notifId) {
                    console.log('[MobileApp] Extracted ID:', notifId);
                    addLog({ type: 'SYS', msg: `Deep-link: ${notifId}`, module: 'PUSH' });

                    // Navigate and Select
                    setCurrentPanel(2);
                    useNotificationStore.getState().selectNotificationById(notifId);
                }
            }
        };

        // Listen for URL events (Warm Start / Cold Start if handled by plugin)
        App.addListener('appUrlOpen', data => {
            handleDeepLink(data.url);
        });

        // Check if app was launched via URL (Cold Start fallback)
        App.getLaunchUrl().then(launchUrl => {
            if (launchUrl && launchUrl.url) {
                handleDeepLink(launchUrl.url);
            }
        });

    }, []);

    // Push Notifications Setup
    useEffect(() => {
        if (Capacitor.getPlatform() !== 'android') return;

        const setupPush = async () => {
            try {
                let permStatus = await PushNotifications.checkPermissions();

                if (permStatus.receive === 'prompt') {
                    permStatus = await PushNotifications.requestPermissions();
                }

                if (permStatus.receive !== 'granted') {
                    console.warn('[FCM] Permissions denied');
                    return;
                }

                await PushNotifications.register();

                PushNotifications.addListener('registration', async (token) => {
                    console.log('[FCM] Token:', token.value);
                    addLog({ type: 'SYS', msg: `FCM: ${token.value.slice(0, 20)}...`, module: 'PUSH' });

                    // Register with Angel
                    try {
                        await fetch(`${ANGEL_BASE_URL}/api/push/register`, {
                            method: 'POST',
                            headers: getTrinityHeaders(),
                            body: JSON.stringify({ token: token.value, platform: 'android' })
                        });
                    } catch (e) {
                        console.error('[FCM] Registration failed:', e);
                    }
                });

                PushNotifications.addListener('pushNotificationReceived', async (notification) => {
                    console.log('[FCM] Received:', notification);
                    // SOTA 2026: Afficher titre ET body
                    const title = notification.title || '';
                    const body = notification.body || '';
                    const msg = title && body ? `${title}: ${body}` : (title || body || 'Notification');
                    addLog({ type: 'AI', msg, module: 'PUSH' });

                    // SOTA 2026: Haptic Feedback (Premium Feel)
                    try {
                        await Haptics.notification({ type: NotificationType.Success });
                    } catch (e) {
                        console.warn('[Haptics] Failed:', e);
                    }
                });

                PushNotifications.addListener('pushNotificationActionPerformed', (action) => {
                    console.log('[FCM] Action:', action);
                    console.log('[FCM] Action Full Data:', JSON.stringify(action, null, 2));

                    // SOTA 2026: Deep Link logic
                    // Always go to Panel 2 (Intelligence/Stats/Messages)
                    setCurrentPanel(2);

                    // SOTA 2026: Deep Link to SPECIFIC message (if notification_id in data)
                    const notifId = action.notification?.data?.notification_id;
                    console.log('[FCM] Extracted notification_id:', notifId);

                    if (notifId) {
                        // Use getState() to avoid stale closure
                        console.log('[FCM] Calling selectNotificationById with:', notifId);
                        useNotificationStore.getState().selectNotificationById(notifId);
                        addLog({ type: 'SYS', msg: `Deep-link to: ${notifId}`, module: 'PUSH' });
                    } else {
                        console.warn('[FCM] No notification_id in data. Data:', action.notification?.data);
                        addLog({ type: 'WARN', msg: 'No notification_id in push data', module: 'PUSH' });
                    }
                });
            } catch (e) {
                console.error('[FCM] Setup error:', e);
            }
        };

        setupPush();
    }, [addLog]);

    // Polling
    useEffect(() => {
        if (!isAuthenticated) return;

        startPolling(({ status, jobs }) => {
            if (jobs) {
                setAllJobsStatus(jobs);
                if (typeof jobs.jules === 'boolean') {
                    useJulesStore.getState().isActive !== jobs.jules &&
                        useJulesStore.setState({ isActive: jobs.jules });
                }
            }
            if (status?.trinity) {
                const prevStatus = useTrinityStore.getState().trinityStatus;
                setTrinityStatus(status.trinity);

                // SOTA 2026: Capture Error if present
                if (status.error) {
                    setConnectionError(status.error);
                } else {
                    setConnectionError(null);
                }

                if (status.trinity === 'running' && prevStatus !== 'running') {
                    setTimeout(() => fetchConfig(), 3000);
                }
            }
        });

        return () => stopPolling();
    }, [isAuthenticated, setAllJobsStatus, setTrinityStatus, fetchConfig]);

    // Reset shutdown state
    useEffect(() => {
        if (trinityStatus === 'running' && isShuttingDown) {
            setShuttingDown(false);
        }
    }, [trinityStatus, isShuttingDown, setShuttingDown]);

    // Touch handlers for swipe
    const onTouchStart = useCallback((e) => {
        setTouchEnd(null);
        setTouchStart(e.targetTouches[0].clientX);
    }, []);

    const onTouchMove = useCallback((e) => {
        setTouchEnd(e.targetTouches[0].clientX);
    }, []);

    const onTouchEnd = useCallback(() => {
        if (!touchStart || !touchEnd) return;

        const distance = touchStart - touchEnd;
        const isLeftSwipe = distance > SWIPE_THRESHOLD;
        const isRightSwipe = distance < -SWIPE_THRESHOLD;

        if (isLeftSwipe && currentPanel < 2) {
            setCurrentPanel(prev => prev + 1);
        } else if (isRightSwipe && currentPanel > 0) {
            setCurrentPanel(prev => prev - 1);
        }
    }, [touchStart, touchEnd, currentPanel]);

    // Render panel content based on index
    const renderPanel = (panelIndex) => {
        switch (panelIndex) {
            case 0: // OPERATIONS (Left)
                return (
                    <div className="flex flex-col gap-3 p-4 h-full overflow-y-auto">
                        <CyberWindow title="TRINITY" side="left" isActive={true}>
                            <TrinityPanel />
                        </CyberWindow>
                        <CyberWindow title={t.hud.trader} side="left" isActive={jobsStatus.trader}>
                            <TraderPanel />
                        </CyberWindow>
                        <CyberWindow title={t.hud.influencer} side="left" isActive={jobsStatus.influencer}>
                            <InfluencerPanel />
                        </CyberWindow>
                        <CyberWindow title={t.hud.youtuber} side="left" isActive={jobsStatus.youtuber}>
                            <YoutuberPanel />
                        </CyberWindow>
                    </div>
                );

            case 1: // TRINITY (Center) - Main view with video
                return (
                    <div className="relative h-full flex flex-col">
                        {/* Video background is global */}
                        <div className="flex-1 flex items-center justify-center">
                            {/* Trinity branding */}
                            {/* Trinity branding moved to header */}
                        </div>

                        {/* Chat section - SOTA 2026: Raised from bottom for mobile */}
                        <div className="flex-1 flex flex-col justify-end pb-8 px-4">
                            <ChatContainer />
                            <div className="mb-4">
                                <InputBar />
                            </div>
                        </div>
                    </div>
                );

            case 2: // INTELLIGENCE (Right)
                return (
                    <div className="flex flex-col gap-3 p-4 h-full overflow-y-auto">
                        <SettingsBar />
                        <CyberWindow title="JULES" side="right" isActive={julesActive}>
                            <JulesPanel />
                        </CyberWindow>
                        {/* SOTA 2026: Native Message Feed */}
                        <CyberWindow title="MESSAGES" side="right" isOpen={true} isActive={true}>
                            <div className="h-96 w-full">
                                <NativeMessageFeed />
                            </div>
                        </CyberWindow>
                        {/* SOTA 2026: Live Logs (ConsolePanel) */}
                        {liveLogsEnabled && (
                            <CyberWindow title={t.hud.liveLogs} side="right" isOpen={true} isActive={true}>
                                <div className="h-64 w-full bg-black/50">
                                    <ConsolePanel />
                                </div>
                            </CyberWindow>
                        )}
                        <CyberWindow title={t.hud.objectives} side="right" isActive={true}>
                            <ObjectivesPanel />
                        </CyberWindow>
                    </div>
                );

            default:
                return null;
        }
    };

    // SOTA 2026: AUTH GUARDS (Parité avec App.jsx)
    // Show AngelSplash if: not yet authenticated, or Trinity not running
    const showAngelSplash = isAuthenticated === null ||
        (isAuthenticated && !trinityStatus) ||
        (isAuthenticated && trinityStatus !== 'running');

    if (showAngelSplash && isAuthenticated !== false) {
        return <Suspense fallback={<div className="w-screen h-screen bg-black" />}><AngelSplash status={trinityStatus} error={connectionError} /></Suspense>;
    }

    if (!isAuthenticated) {
        return (
            <SceneContainer onLogin={async (user) => {
                // SOTA 2026: Bridge Firebase Auth → Trinity Session Token
                try {
                    const res = await fetch(`${ANGEL_BASE_URL}/api/auth/login`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ username: 'trinity', password: import.meta.env.VITE_TRINITY_ACCESS_KEY || 'trinity' })
                    });
                    if (res.ok) {
                        const data = await res.json();
                        setToken(data.token);
                        setRole(data.role || 'GOD');
                    }
                } catch (e) {
                    console.warn('Trinity token fetch failed, continuing with Firebase-only auth:', e);
                }
                setAuthenticated(true);
                setUser({ name: user || 'OPERATOR' });
                unlockAudio();
            }} />
        );
    }

    // Dashboard - only rendered if authenticated AND Trinity is running
    return (
        <div
            className="relative w-screen h-screen overflow-hidden bg-black text-white font-mono"
            onTouchStart={onTouchStart}
            onTouchMove={onTouchMove}
            onTouchEnd={onTouchEnd}
        >
            {/* Global Video Background with parallax - SOTA 2026
                La vidéo fait 200% de largeur
                OPERATIONS (panel 0): translateX(-25%) → côté gauche (oreille droite)
                TRINITY (panel 1): translateX(-50%) → visage centré
                INTELLIGENCE (panel 2): translateX(-75%) → côté droit (oreille gauche)
            */}
            <div
                className="absolute top-0 h-full z-0 transition-transform duration-500 ease-out"
                style={{
                    width: '200%',
                    transform: `translateX(${-currentPanel * 25}%)`
                }}
            >
                <VideoEngine />
            </div>

            {/* Panel indicator - SOTA 2026: Arrows + Dots + Title */}
            <div className="absolute top-2 left-1/2 -translate-x-1/2 z-50 flex flex-col items-center gap-2 w-full">
                {/* Navigation Row: < O O O > */}
                <div className="flex items-center gap-8">
                    {/* Left Arrow */}
                    <button
                        onClick={() => setCurrentPanel(p => Math.max(0, p - 1))}
                        className={`text-cyan-400 text-xl font-bold transition-opacity ${currentPanel > 0 ? 'opacity-100' : 'opacity-30'}`}
                    >
                        {"<"}
                    </button>

                    {/* Dots - Bigger & Spaced */}
                    <div className="flex gap-4">
                        {[0, 1, 2].map((idx) => (
                            <button
                                key={idx}
                                onClick={() => setCurrentPanel(idx)}
                                className={`w-5 h-5 rounded-full transition-all duration-300 ${currentPanel === idx
                                    ? 'bg-cyan-400 shadow-[0_0_15px_rgba(6,182,212,1)] scale-110'
                                    : 'bg-white/20 hover:bg-white/40'
                                    }`}
                            />
                        ))}
                    </div>

                    {/* Right Arrow */}
                    <button
                        onClick={() => setCurrentPanel(p => Math.min(2, p + 1))}
                        className={`text-cyan-400 text-xl font-bold transition-opacity ${currentPanel < 2 ? 'opacity-100' : 'opacity-30'}`}
                    >
                        {">"}
                    </button>
                </div>

                {/* Title Below Dots */}
                <h1 className="text-2xl font-bold tracking-[0.3em] text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-purple-500 drop-shadow-[0_0_20px_rgba(6,182,212,0.6)] mt-2">
                    φTRINITYφ
                </h1>
            </div>

            {/* Panels container with swipe animation */}
            <AnimatePresence mode="wait">
                <motion.div
                    key={currentPanel}
                    className="absolute inset-0 z-10 pt-20"
                    initial={{ opacity: 0, x: 100 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -100 }}
                    transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                >
                    {renderPanel(currentPanel)}
                </motion.div>
            </AnimatePresence>

            {/* Shutdown overlay */}
            {isShuttingDown && (
                <div className="absolute inset-0 z-[100] bg-black/90 flex items-center justify-center">
                    <div className="text-red-500 text-2xl font-bold animate-pulse">
                        SHUTDOWN IN PROGRESS...
                    </div>
                </div>
            )}
        </div>
    );
}

export default MobileApp;
