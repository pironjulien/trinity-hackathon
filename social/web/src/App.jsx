import VideoEngine from './components/core/VideoEngine';
import CyberWindow from './components/layout/CyberWindow';
import InputBar from './components/hud/InputBar';
import ChatContainer from './components/chat/ChatContainer';
// import AuthScreen from './components/core/AuthScreen';
import AuthContainer from './components/auth/AuthContainer';
import SceneContainer from './components/SceneContainer';

import { useTrinityStore } from './stores/trinityStore';
import enLocale from './locales/en.json';
import frLocale from './locales/fr.json';

import { Settings, Activity, Terminal, Target, DollarSign, Radio, Video } from 'lucide-react';
import React, { useState, useRef, useMemo, useEffect, Suspense } from 'react';
import Header from './components/julien/Header';
import RisingMenu from './components/julien/RisingMenu';
import JobsBar from './components/ui/JobsBar'; // SOTA 2026: Kept for reference but unused
import SettingsBar from './components/ui/SettingsBar';
import TraderPanel from './components/trader/TraderPanel';
import InfluencerPanel from './components/influencer/InfluencerPanel';
import YoutuberPanel from './components/youtuber/YoutuberPanel';
import ConsolePanel from './components/console/ConsolePanel'; // SOTA 2026: Console Panel Integration
import TrinityPanel from './components/core/TrinityPanel';
import ObjectivesPanel from './components/core/ObjectivesPanel';
import { startPolling, stopPolling } from './services/angelService';
import JulesAvatar from './components/jules/JulesAvatar';
import JulesPanel from './components/jules/JulesPanel';
import { useJulesStore } from './stores/julesStore';
import { useDataPreloader } from './services/dataPreloader';

import NotificationPhone from './components/notifications/NotificationPhone';

const AngelSplash = React.lazy(() => import('./components/core/AngelSplash'));

const LOCALES = { en: enLocale, fr: frLocale };

function App() {
  const { isAuthenticated, logs, setAuthenticated, setRole, setUser, setToken, unlockAudio, locale, jobsStatus, setAllJobsStatus, trinityStatus, setTrinityStatus, liveLogsEnabled, fetchConfig, isShuttingDown, setShuttingDown } = useTrinityStore();
  const { status: julesStatus, isActive: julesActive, showPanel: julesPanelOpen } = useJulesStore();
  const t = useMemo(() => LOCALES[locale] || LOCALES.en, [locale]);
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const usernameRef = useRef('');
  const passwordRef = useRef('');
  const [isLoading, setIsLoading] = useState(false);

  // SOTA 2026: Preload all panel data when Trinity becomes running
  useDataPreloader();

  // SOTA 2026: Reset shutdown state when Trinity becomes running (prevents shutdown loop on restart)
  useEffect(() => {
    if (trinityStatus === 'running' && isShuttingDown) {
      console.log('[App] Trinity running - resetting shutdown state');
      setShuttingDown(false);
    }
  }, [trinityStatus, isShuttingDown, setShuttingDown]);

  // SOTA 2026: Poll Angel API for jobs status sync
  useEffect(() => {
    if (!isAuthenticated) return;

    // NOTE: fetchConfig is called inside the polling callback AFTER trinityStatus is confirmed running

    startPolling(({ status, jobs }) => {
      // Sync jobs to store
      if (jobs) {
        setAllJobsStatus(jobs);
        // SOTA 2026: Sync Jules active state to JulesStore for toggle parity
        if (typeof jobs.jules === 'boolean') {
          useJulesStore.getState().isActive !== jobs.jules &&
            useJulesStore.setState({ isActive: jobs.jules });
        }
      }
      // SOTA 2026: Sync System Status (Angel/Trinity)
      if (status && status.trinity) {
        const prevStatus = useTrinityStore.getState().trinityStatus;
        setTrinityStatus(status.trinity);

        // SOTA 2026: Fetch config ONLY when Trinity just became running
        // NOTE: Add 2s delay - Angel reports 'running' before FastAPI is fully ready
        if (status.trinity === 'running' && prevStatus !== 'running') {
          setTimeout(() => fetchConfig(), 3000);
        }

        // DEBUG: Log status change
        if (status.trinity !== prevStatus) {
          console.log('UseTrinityStore: Status changed to', status.trinity);
          useTrinityStore.getState().addLog({
            type: 'SYS',
            msg: `System Status changed: ${status.trinity.toUpperCase()}`,
            module: 'ANGEL',
            function: 'heartbeat'
          });
        }
      }
    }); // Use default interval (5000ms)

    return () => stopPolling();
  }, [isAuthenticated, setAllJobsStatus, setTrinityStatus, fetchConfig]);

  // SOTA 2026: Push Notifications moved to Flutter native app (Capacitor removed Feb 2026)

  const handleLogin = () => {
    setIsLoading(true);
    // Simulate Login - SOTA 2026: Real auth would go here
    setTimeout(() => {
      setAuthenticated(true);
      setRole('GOD');
      setUser({ name: usernameRef.current || 'OPERATOR' });
      setIsLoading(false);
    }, 1500);
  };

  // SOTA 2026: LOADING/OFFLINE GATE (Combined to prevent double-mount)
  // Show AngelSplash if: not yet authenticated, or Trinity not running
  const showAngelSplash = isAuthenticated === null ||
    (isAuthenticated && !trinityStatus) ||
    (isAuthenticated && trinityStatus !== 'running');

  if (showAngelSplash && isAuthenticated !== false) {
    return <Suspense fallback={<div className="w-screen h-screen bg-black" />}><AngelSplash status={trinityStatus} /></Suspense>;
  }

  if (!isAuthenticated) {
    return (
      <SceneContainer onLogin={async (user) => {
        // SOTA 2026: Bridge Firebase Auth → Trinity Session Token
        try {
          // Call Trinity auth endpoint with service account
          const res = await fetch('/api/auth/login', {
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
  // (showAngelSplash already handles all other cases above)
  return (
    <div className="relative w-screen h-screen overflow-hidden text-white font-mono selection:bg-neon-pink selection:text-white">
      {/* 0. CORE: Video Engine - Always visible */}
      <VideoEngine />

      {/* SOTA 2026: Hide entire UI during immersive shutdown (Standard 382.22) */}
      {!isShuttingDown && (
        <>
          {/* JULIEN PIRON HEADER & MENU */}
          <Header onMenuClick={() => setIsMenuOpen(!isMenuOpen)} isMenuOpen={isMenuOpen} />
          <RisingMenu isOpen={isMenuOpen} />

          {/* 1. HUD: CSS Grid Layout */}
          <div className="absolute inset-0 z-10 grid grid-cols-12 grid-rows-12 gap-4 px-12 pb-0 pt-20 pointer-events-none">

            {/* --- TOP: CONFIG DRAWWER (Row 1) --- */}
            {/* REPLACED BY HEADER
        <div className="col-span-4 col-start-5 row-span-1 pointer-events-auto flex justify-center">
          <div className="
                w-full h-12 
                bg-glass border-b border-x border-white/10 hover:border-neon-blue
                rounded-b-xl backdrop-blur-xl 
                flex items-center justify-between px-6
                cursor-pointer group transition-all
            ">
            <div className="flex items-center gap-2 text-xs text-white/50 group-hover:text-neon-blue">
              <Settings size={14} />
              <span className="tracking-[0.2em] font-bold glitch-text" data-text={`SYSTEM // ${phase}`}>SYSTEM // {phase}</span>
            </div>
            <div className="flex gap-2">
              <div className={`w-2 h-2 rounded-full animate-pulse ${isAlive ? 'bg-green-500' : 'bg-red-500'}`}></div>
              <span className={`text-xs font-bold ${isAlive ? 'text-green-500' : 'text-red-500'}`}>
                {isAlive ? 'ONLINE' : 'OFFLINE'}
              </span>
            </div>
          </div>
        </div>
        */}

            {/* --- LEFT: SKILLS (Rows 2-10, Cols 1-3) --- */}
            <div className="col-span-2 col-start-2 row-span-9 row-start-2 relative pointer-events-auto pr-0 min-w-[179px] max-w-[270px]">
              {/* Bars container - z-10 so they overlay Jules */}
              <div className="flex flex-col gap-3 relative z-auto">
                {/* TRINITY PANEL (Moved from Right) - Replaces JobsBar */}
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

              {/* JULES AVATAR - absolute positioned at bottom, z-0 so bars overlay */}
              {julesActive && !julesPanelOpen && (
                <div className="absolute -bottom-28 left-0 w-full z-0">
                  <JulesAvatar />
                </div>
              )}
            </div>

            {/* --- RIGHT: INTEL (Rows 2-10, Cols 10-12) --- */}
            <div className="col-span-2 col-start-10 row-span-9 row-start-2 relative pointer-events-auto pl-0 w-full min-w-[179px] max-w-[270px] ml-auto">
              {/* Bars container - z-10 so they overlay NotificationPhone */}
              <div className="flex flex-col gap-3 relative z-auto">
                {/* Settings Control Bar */}
                <SettingsBar />

                {/* JULES PANEL - Uses julesActive from julesStore (Standard 362) */}
                <CyberWindow title="JULES" side="right" isActive={julesActive}>
                  <JulesPanel />
                </CyberWindow>

                {liveLogsEnabled && (
                  <CyberWindow title={t.hud.liveLogs} side="right" isOpen={true} isActive={true}>
                    {/* SOTA 2026: Full Console Panel (Tabs, Tokens, Logs) - Only visible when expanded */}
                    <div className="h-full w-full bg-black/50">
                      <ConsolePanel />
                    </div>
                  </CyberWindow>
                )}

                <CyberWindow title={t.hud.objectives} side="right" isActive={true}>
                  <ObjectivesPanel />
                </CyberWindow>
              </div>

              {/* NOTIFICATION PHONE - absolute positioned at bottom, z-0 so bars overlay */}
              <div className="absolute -bottom-28 left-0 w-full z-0">
                <NotificationPhone />
              </div>
            </div>

            {/* --- CENTER: CHAT + INPUT (Rows 4-12) --- */}
            <div className="col-span-6 col-start-4 row-span-9 row-start-4 flex flex-col justify-end pb-2">
              <ChatContainer />
              <InputBar />
            </div>
          </div>
        </>
      )}

    </div>
  );
}

export default App;
