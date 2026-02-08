import React, { useMemo } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Canvas } from '@react-three/fiber';
import { Suspense } from 'react';
import { useAuthSequence } from '../logic/AuthSequence';
import { useTrinityStore } from '../stores/trinityStore';
import BackgroundVideo from './BackgroundVideo';
import UnifiedAuth from './UnifiedAuth';
import LogoSpinner from './LogoSpinner';
import SmokeFluid from './SmokeFluid';
import enLocale from '../locales/en.json';
import frLocale from '../locales/fr.json';

const LOCALES = { en: enLocale, fr: frLocale };

const SceneContainer = ({ onLogin }) => {
    const {
        authState,
        identity, setIdentity,
        passkey, setPasskey,
        handleKeyDown,
        handleGoogleAuth,
        statusMessage
    } = useAuthSequence({ onSuccess: onLogin });

    // Global sound state from store
    const isMuted = useTrinityStore(state => state.isMuted);
    const setMuted = useTrinityStore(state => state.setMuted);

    // Global audio unlock for VideoEngine
    const unlockAudio = useTrinityStore(state => state.unlockAudio);

    // i18n
    const locale = useTrinityStore(state => state.locale);
    const t = useMemo(() => LOCALES[locale]?.ui || LOCALES.en.ui, [locale]);

    const isImploding = authState === 'imploding';
    const isAuthenticating = authState === 'authenticating';

    return (
        <div
            className="relative w-screen h-screen overflow-hidden bg-black text-white font-sans select-none"
            onKeyDown={handleKeyDown}
        >
            {/* 1. Fullscreen Video Background */}
            <BackgroundVideo isMuted={isMuted} />

            {/* Sound Toggle Button - Bottom Left (matching logo position) */}
            <div className="absolute bottom-20 md:bottom-12 left-8 md:right-auto md:left-12 z-30 flex items-center gap-4 pointer-events-auto">
                {/* Spinning Ring Container */}
                <div className="relative">
                    {/* Outer Spinning Ring - Same style as LogoSpinner */}
                    <motion.div
                        className="w-16 h-16 rounded-full border border-white/10 border-t-cyan-500/50 border-r-transparent"
                        animate={{ rotate: 360 }}
                        transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                    />

                    {/* Center Button */}
                    <button
                        onClick={() => {
                            const newMuted = !isMuted;
                            setMuted(newMuted);
                            if (!newMuted) unlockAudio(); // Unlock global audio when unmuting
                        }}
                        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 
                                   w-10 h-10 rounded-full bg-black/60 backdrop-blur-sm
                                   flex items-center justify-center
                                   hover:bg-cyan-400/20 hover:shadow-[0_0_20px_rgba(6,182,212,0.5)]
                                   transition-all duration-300"
                        title={isMuted ? t.soundOff : t.soundOn}
                    >
                        {isMuted ? (
                            <svg className="w-5 h-5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2" />
                            </svg>
                        ) : (
                            <svg className="w-5 h-5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
                            </svg>
                        )}
                    </button>
                </div>
            </div>

            {/* 1.5. Interactive Smoke Layer (WebGL) */}
            <div className="absolute inset-0 z-10 pointer-events-none">
                <Canvas camera={{ position: [0, 0, 1] }} resize={{ scroll: false }}>
                    <Suspense fallback={null}>
                        <SmokeFluid />
                    </Suspense>
                </Canvas>
            </div>

            {/* 2. Unified Auth Interface - Bottom HUD Position */}
            <AnimatePresence>
                {!isImploding && !isAuthenticating && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.8, duration: 0.5 }}
                        className="absolute bottom-20 left-0 right-0 z-20 px-4 md:px-8 flex justify-center"
                    >
                        <UnifiedAuth
                            identity={identity}
                            setIdentity={setIdentity}
                            passkey={passkey}
                            setPasskey={setPasskey}
                            disabled={isImploding}
                            onSubmit={() => handleKeyDown({ key: 'Enter' })}
                            onGoogleSubmit={handleGoogleAuth}
                        />
                    </motion.div>
                )}
            </AnimatePresence>

            {/* 3. AAA Spinning Logo Loader (Bottom Right) */}
            <LogoSpinner />



            {/* 4. Implosion / Flash Screen Effect */}
            <AnimatePresence>
                {isImploding && (
                    <motion.div
                        className="absolute inset-0 bg-white z-[100] mix-blend-overlay"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.1, yoyo: Infinity }} // Strobe
                    >
                        {/* Optional: Central Loading Text during Implosion */}
                        <div className="absolute inset-0 flex items-center justify-center text-black font-bold tracking-[1em]">
                            AUTHENTICATING...
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* 5. Terminal Status Overlay (If needed during 'authenticating' phase) */}
            {statusMessage && isAuthenticating && (
                <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
                    <div className="font-mono text-green-500 text-sm animate-pulse whitespace-pre-wrap text-center">
                        {statusMessage}
                    </div>
                </div>
            )}

        </div>
    );
};

export default SceneContainer;
