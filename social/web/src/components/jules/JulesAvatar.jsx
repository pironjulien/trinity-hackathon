/**
 * JULES AVATAR COMPONENT
 * ═══════════════════════════════════════════════════════════════════════════
 * Animated avatar for Jules shadow developer in bottom-left corner.
 * SOTA 2026: Dual-player video engine with crossfade (harmonized with Trinity VideoEngine)
 * ═══════════════════════════════════════════════════════════════════════════
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { useJulesStore } from '../../stores/julesStore';
import './JulesAvatar.css';

/**
 * Animation assets paths
 */
const ANIMATIONS = {
    idle: [
        '/jules/jules_idle_1.webm',
        '/jules/jules_idle_2.webm',
        '/jules/jules_idle_3.webm',
    ],
    done: '/jules/jules_done.webm',
};

// SOTA 2026: Crossfade constants (harmonized with VideoEngine)
const CROSSFADE_DURATION = 50;    // ms
const TRANSITION_TRIGGER = 0.15;  // seconds before end to start transition
const PRELOAD_AHEAD = 1.0;        // seconds before end to preload next

// Video blob cache to prevent double-loading
const videoBlobCache = new Map();

/**
 * Preload video into blob cache
 */
const preloadVideoBlob = async (src) => {
    if (videoBlobCache.has(src)) return videoBlobCache.get(src);
    try {
        const res = await fetch(src);
        const blob = await res.blob();
        const blobUrl = URL.createObjectURL(blob);
        videoBlobCache.set(src, blobUrl);
        return blobUrl;
    } catch (err) {
        console.warn('[JulesAvatar] Preload failed:', src, err);
        return src; // Fallback to direct path
    }
};

export default function JulesAvatar() {
    const {
        status,
        idleIndex,
        rotateIdle,
        togglePanel,
        showPanel,
        pendingCount,
        fetchStatus,
    } = useJulesStore();

    // Dual-player refs (A/B system like VideoEngine)
    const videoARef = useRef(null);
    const videoBRef = useRef(null);
    const activePlayerRef = useRef('A');
    const isTransitioningRef = useRef(false);
    const isPreloadedRef = useRef(false);
    const idleIndexRef = useRef(0);

    const prevCountRef = useRef(null);
    const isInitialLoadRef = useRef(true);
    const [showingDone, setShowingDone] = useState(false);

    // Get next idle animation path
    const getNextIdlePath = useCallback(() => {
        const idle = ANIMATIONS.idle[idleIndexRef.current];
        idleIndexRef.current = (idleIndexRef.current + 1) % ANIMATIONS.idle.length;
        return idle;
    }, []);

    // Get current and next players
    const getPlayers = useCallback(() => {
        const isA = activePlayerRef.current === 'A';
        return {
            current: isA ? videoARef.current : videoBRef.current,
            next: isA ? videoBRef.current : videoARef.current,
            nextId: isA ? 'B' : 'A'
        };
    }, []);

    // Preload next video
    const preloadNextVideo = useCallback(async () => {
        if (isPreloadedRef.current) return;
        isPreloadedRef.current = true;

        const { next } = getPlayers();
        const nextPath = showingDone ? ANIMATIONS.done : getNextIdlePath();
        const blobUrl = await preloadVideoBlob(nextPath);

        if (next && next.src !== blobUrl) {
            next.src = blobUrl;
            next.load();
        }
    }, [getPlayers, getNextIdlePath, showingDone]);

    // Execute crossfade transition
    const executeTransition = useCallback(() => {
        if (isTransitioningRef.current) return;
        isTransitioningRef.current = true;

        const { current, next, nextId } = getPlayers();

        if (next) {
            next.play().then(() => {
                next.style.opacity = '1';

                setTimeout(() => {
                    if (current) {
                        current.style.opacity = '0';
                        current.pause();
                        current.currentTime = 0;
                    }
                    activePlayerRef.current = nextId;
                    isTransitioningRef.current = false;
                    isPreloadedRef.current = false;
                    rotateIdle(); // Update store index for consistency
                }, CROSSFADE_DURATION);
            }).catch(err => {
                console.warn('[JulesAvatar] Play failed:', err);
                isTransitioningRef.current = false;
            });
        }
    }, [getPlayers, rotateIdle]);

    // TimeUpdate handler for preload and transition triggers
    const handleTimeUpdate = useCallback((playerId) => {
        const video = playerId === 'A' ? videoARef.current : videoBRef.current;
        if (!video || activePlayerRef.current !== playerId) return;
        if (isNaN(video.duration)) return;

        const timeRemaining = video.duration - video.currentTime;

        if (timeRemaining <= PRELOAD_AHEAD && !isPreloadedRef.current) {
            preloadNextVideo();
        }

        if (timeRemaining <= TRANSITION_TRIGGER && !isTransitioningRef.current) {
            executeTransition();
        }
    }, [preloadNextVideo, executeTransition]);

    // Initialize first video on mount
    useEffect(() => {
        const initFirstVideo = async () => {
            const firstPath = ANIMATIONS.idle[0];
            const blobUrl = await preloadVideoBlob(firstPath);

            if (videoARef.current) {
                videoARef.current.src = blobUrl;
                videoARef.current.style.opacity = '1';
                videoARef.current.play().catch(() => { });
            }
        };
        initFirstVideo();
    }, []);

    // Detect badge increment to trigger "done" animation
    // SOTA 2026: Use -1 as sentinel to skip first load
    useEffect(() => {
        // First time: set initial value but don't trigger anything
        if (prevCountRef.current === null) {
            prevCountRef.current = pendingCount;
            return;
        }

        // Skip if this is still the initial load (pendingCount jumped from 0)
        // Only trigger done on REAL increments (user didn't cause this)
        const wasZero = prevCountRef.current === 0;
        const isFirstNonZero = wasZero && pendingCount > 0 && isInitialLoadRef.current;

        if (isFirstNonZero) {
            // This is the first fetch returning data - don't trigger done
            isInitialLoadRef.current = false;
            prevCountRef.current = pendingCount;
            return;
        }

        isInitialLoadRef.current = false;

        // Real increment - trigger done animation
        if (pendingCount > prevCountRef.current && prevCountRef.current >= 0) {
            setShowingDone(true);
            // Force immediate transition to done animation
            const loadDone = async () => {
                const { next } = getPlayers();
                const blobUrl = await preloadVideoBlob(ANIMATIONS.done);
                if (next) {
                    next.src = blobUrl;
                    next.load();
                    next.oncanplay = () => {
                        next.oncanplay = null;
                        executeTransition();
                    };
                }
            };
            loadDone();

            const timer = setTimeout(() => {
                setShowingDone(false);
            }, 8000);
            prevCountRef.current = pendingCount;
            return () => clearTimeout(timer);
        }
        prevCountRef.current = pendingCount;
    }, [pendingCount, getPlayers, executeTransition]);

    // Fetch status on mount and periodically
    useEffect(() => {
        fetchStatus();
        const pollInterval = setInterval(fetchStatus, 60000);
        return () => clearInterval(pollInterval);
    }, [fetchStatus]);

    const badgeCount = pendingCount;

    return (
        <div
            className={`jules-avatar ${showPanel ? 'active' : ''} ${showingDone ? 'done' : status}`}
            title="Jules - Shadow Developer"
        >
            {/* Dual-player video system (A/B) for seamless crossfade */}
            <video
                ref={videoARef}
                className="jules-animation jules-video-a"
                muted
                playsInline
                onTimeUpdate={() => handleTimeUpdate('A')}
            />
            <video
                ref={videoBRef}
                className="jules-animation jules-video-b"
                muted
                playsInline
                onTimeUpdate={() => handleTimeUpdate('B')}
            />

            {/* Pulse effect when showing done animation */}
            {showingDone && (
                <div className="jules-pulse" />
            )}

            {/* Badge progress: X/3 projects processed today */}
            <div className="jules-badge">
                {badgeCount}/3
            </div>
        </div>
    );
}
