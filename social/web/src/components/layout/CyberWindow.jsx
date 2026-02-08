import { AnimatePresence, motion } from 'framer-motion';
import { useState } from 'react';
import { Maximize2, Minimize2 } from 'lucide-react';
import { useCyberSound } from '../../hooks/useCyberSound';
import { useTrinityStore } from '../../stores/trinityStore';
import { CyberWindowContext } from './CyberWindowContext';
import { useRef, useCallback } from 'react';

/**
 * SOTA 2026: CyberWindow - Collapsible Panel
 * - Collapsed: Single header line (h-12)
 * - Expanded: Full screen overlay
 * - Dynamic activity indicator
 */
export default function CyberWindow({
    title,
    children,
    side = 'left',
    className = '',
    isActive = false,      // Green indicator when active
    hasActivity = false    // Blinking indicator when activity detected
}) {
    const [isFullScreen, setIsFullScreen] = useState(false);
    const { playHover, playClick } = useCyberSound();

    // SOTA 2026: Interceptor Logic
    const interceptorsRef = useRef(new Set());

    const registerInterceptor = useCallback((callback) => {
        interceptorsRef.current.add(callback);
        return () => interceptorsRef.current.delete(callback);
    }, []);

    // SOTA 2026: Directional Gaze System - trigger look video on window close
    const setPendingGaze = useTrinityStore(state => state.setPendingGaze);

    const toggleScreen = (e) => {
        e.stopPropagation();

        // Check interceptors if closing (isFullScreen -> false)
        if (isFullScreen) {
            // Run all interceptors. If ANY returns true, we abort close.
            for (const interceptor of interceptorsRef.current) {
                if (interceptor()) {
                    return; // Blocked by child
                }
            }

            setPendingGaze(side); // 'left' or 'right'
        }

        setIsFullScreen(!isFullScreen);
        playClick();
    };

    // Indicator color based on state
    const getIndicatorClasses = () => {
        if (hasActivity) return 'bg-cyan-400 animate-ping'; // Fast blink for activity
        if (isActive) return 'bg-green-500'; // Solid green when active
        return 'bg-white/20'; // Dim when inactive
    };

    return (
        <CyberWindowContext.Provider value={{ registerInterceptor }}>
            {/* Backdrop when open */}
            <AnimatePresence>
                {isFullScreen && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.15 }}
                        className="fixed inset-0 bg-black/30 backdrop-blur-sm z-[40]"
                        onClick={toggleScreen}
                    />
                )}
            </AnimatePresence>

            <motion.div
                layout
                transition={{ type: "spring", stiffness: 300, damping: 30 }}
                className={`
                    flex flex-col
                    bg-glass border border-white/10 
                    backdrop-blur-xl rounded-lg overflow-hidden
                    shadow-[0_0_15px_rgba(0,0,0,0.5)]
                    group
                    ${isFullScreen
                        ? 'fixed top-24 left-1/2 -translate-x-1/2 w-full max-w-[1597px] bottom-8 z-[1200] border-neon-blue shadow-[0_0_50px_rgba(0,0,0,0.8)]'
                        : `relative w-full h-12 cursor-pointer ${side === 'left' ? 'hover:border-neon-blue/50' : 'hover:border-neon-pink/50'}`
                    }
                    ${className}
                `}
                onClick={!isFullScreen ? toggleScreen : undefined}
                onMouseEnter={!isFullScreen ? playHover : undefined}
            >
                {/* HEADER - Always visible */}
                <motion.div
                    layout="position"
                    className={`flex items-center justify-between px-4 h-12 bg-black/40 border-b border-white/5 shrink-0 ${isFullScreen ? 'cursor-pointer hover:bg-white/5' : ''} ${side === 'right' ? 'flex-row-reverse' : ''}`}
                    onClick={isFullScreen ? toggleScreen : undefined}
                >
                    <div className={`flex items-center gap-3 ${side === 'right' ? 'flex-row-reverse' : ''}`}>
                        {/* Activity Indicator */}
                        <div className="relative">
                            <div className={`w-2 h-2 rounded-full ${getIndicatorClasses()}`} />
                            {hasActivity && (
                                <div className="absolute inset-0 w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                            )}
                        </div>
                        <h3 className={`text-sm font-bold tracking-widest text-white/90 transition-colors ${side === 'left' ? 'group-hover:text-neon-blue' : 'group-hover:text-neon-pink'}`}>
                            {title}
                        </h3>
                    </div>
                    <button
                        className="p-1 hover:bg-white/10 rounded transition-colors text-white/50 hover:text-white"
                    >
                        {isFullScreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
                    </button>
                </motion.div>

                {/* CONTENT - Only visible when fullscreen */}
                <AnimatePresence>
                    {isFullScreen && (
                        <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            transition={{ duration: 0.2 }}
                            className="flex-1 overflow-auto p-6"
                        >
                            {children}
                        </motion.div>
                    )}
                </AnimatePresence>
            </motion.div>
        </CyberWindowContext.Provider>
    );
}
