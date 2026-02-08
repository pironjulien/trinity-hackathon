import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { Power } from 'lucide-react';
import { startTrinity } from '../../services/angelService';

// SOTA 2026: Singleton video element to prevent double-loading
let cachedVideoSrc = null;

const AngelSplash = ({ status = 'unknown', error = null }) => {
    const [isLoading, setIsLoading] = useState(false);
    const [showButton, setShowButton] = useState(false);
    const videoRef = useRef(null);

    // SOTA 2026: Timeout fallback - if status stays 'unknown' for 3s, show button anyway
    useEffect(() => {
        if (status !== 'unknown') {
            setShowButton(true); // Immediately show if we have a definitive status
            return;
        }
        const timer = setTimeout(() => setShowButton(true), 3000);
        return () => clearTimeout(timer);
    }, [status]);

    // SOTA 2026: Load video only once using cached blob
    useEffect(() => {
        const video = videoRef.current;
        if (!video) return;

        if (cachedVideoSrc) {
            video.src = cachedVideoSrc;
            video.play().catch(() => { });
        } else {
            // First load - fetch and cache
            fetch('/videos/angel.webm')
                .then(res => res.blob())
                .then(blob => {
                    cachedVideoSrc = URL.createObjectURL(blob);
                    video.src = cachedVideoSrc;
                    video.play().catch(() => { });
                })
                .catch(err => console.warn('[AngelSplash] Video load failed:', err));
        }
    }, []);

    const handleLaunch = async () => {
        setIsLoading(true);
        // SOTA 2026: Fire the start command to Angel
        const success = await startTrinity();
        if (!success) {
            console.error("Failed to trigger start command");
            setIsLoading(false); // Reset on failure
        }
        // If success, we just wait. The poller in App.jsx will detect "running" 
        // and automatically unmount this component.
    };

    return (
        <div className="relative w-screen h-screen overflow-hidden bg-black text-white font-mono select-none">
            {/* 1. Background Video - Angel (Offline Guardian) */}
            <div className="absolute inset-0 z-0">
                <video
                    ref={videoRef}
                    className="w-full h-full object-cover opacity-60"
                    muted
                    loop
                    playsInline
                />
                {/* Overlay for readability */}
                <div className="absolute inset-0 bg-black/60" />
                <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-black/40" />
            </div>


            {/* 2. Content */}
            <div className="relative z-10 flex flex-col items-center justify-center h-full gap-8">

                {/* Status Indicator */}
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`font-bold tracking-[0.3em] text-xs border px-3 py-1 backdrop-blur-sm rounded ${status === 'unknown' ? 'text-neon-blue border-neon-blue/30 bg-neon-blue/10' : 'text-red-500 border-red-500/30 bg-red-900/10'}`}
                >
                    {status === 'unknown' ? 'ESTABLISHING NEURAL LINK...' : 'TRINITY SYSTEM OFFLINE'}
                </motion.div>

                {/* Main Action Button - Shows after timeout or when status is known */}
                {showButton && (
                    <motion.button
                        initial={{ scale: 0.9, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        whileHover={{ scale: 1.05, boxShadow: "0 0 30px rgba(59, 130, 246, 0.5)" }}
                        whileTap={{ scale: 0.95 }}
                        onClick={handleLaunch}
                        disabled={isLoading}
                        className={`
                        relative group px-8 py-4 
                        bg-black/40 border border-white/20 
                        backdrop-blur-md rounded-xl
                        text-white font-bold tracking-widest
                        flex items-center gap-4
                        transition-all duration-300
                        ${isLoading ? 'opacity-50 cursor-wait' : 'hover:border-neon-blue hover:text-neon-blue'}
                    `}
                    >
                        {isLoading ? (
                            <>
                                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                <span>INITIALIZATION...</span>
                            </>
                        ) : (
                            <>
                                <Power size={20} className="group-hover:drop-shadow-[0_0_10px_rgba(59,130,246,0.8)]" />
                                <span>LANCER TRINITY !</span>
                            </>
                        )}

                        {/* Button Glitch Effect Overlay */}
                        <div className="absolute inset-0 bg-white/5 opacity-0 group-hover:opacity-100 transition-opacity rounded-xl" />
                    </motion.button>
                )}

                {/* Footer / Context */}
                <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 0.5 }}
                    transition={{ delay: 0.5 }}
                    className="text-xs text-center text-white/30 max-w-md leading-relaxed"
                >
                    Angel Supervisor v3.1<br />
                    System halted. Manual authorization required.

                    {/* SOTA 2026: Debug Error Display */}
                    {error && (
                        <span className="block mt-4 text-red-400 font-bold bg-red-900/20 px-4 py-2 rounded border border-red-500/30">
                            ERROR: {error}
                        </span>
                    )}
                </motion.p>
            </div>
        </div>
    );
};

export default AngelSplash;
