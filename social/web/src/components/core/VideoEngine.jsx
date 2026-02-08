import { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { motion } from 'framer-motion'; // eslint-disable-line no-unused-vars
import { useTrinityStore } from '../../stores/trinityStore';
import { assetLoader } from '../../services/assetLoader';
import { stopTrinity } from '../../services/angelService';

// ... (existing code)

// SOTA 2026: i18n Video Filenames (NOT PATHS)
// The AssetLoader will resolve these to either /videos/... or file:///...
const getVideoFilenames = (locale = 'en') => {
    // Browser/VSCode overrides (Legacy/Web)
    if (typeof window !== 'undefined' && window.videoUris) {
        return {
            init: window.videoUris.init,
            idles: [
                window.videoUris.idle1,
                window.videoUris.idle2,
                window.videoUris.idle3
            ]
        };
    }

    const videoMap = {
        en: {
            init: 'initializing.webm',
            idles: ['idle1.webm', 'idle2.webm', 'idle3.webm']
        },
        fr: {
            init: 'initialisation.webm',
            idles: ['idle1.webm', 'idle2.webm', 'idle3.webm']
        }
    };

    const gazeFilenames = {
        left: 'gauche.webm',
        right: 'droite.webm',
        down: 'bas.webm',  // SOTA 2026: Triggered on chat focus
        // SOTA 2026: Special state animations
        sleep: locale === 'fr' ? 'mise en veille.webm' : 'sleep mode.webm',
        error: locale === 'fr' ? 'erreur critique.webm' : 'Critical error.webm'
    };

    return { ...(videoMap[locale] || videoMap.en), gaze: gazeFilenames };
};

const CROSSFADE_DURATION = 50;
const AUDIO_FADE_DURATION = 1.4;
const TRANSITION_TRIGGER = 0.15;
const PRELOAD_AHEAD = 2.0;

// SOTA 2026: Blob URL cache to prevent duplicate network requests
const videoBlobCache = new Map();
// SOTA 2026: Track original filenames for muting logic (blob URLs don't contain filename)
const blobToFilenameMap = new Map();

/**
 * Fetch video and cache as blob URL (prevents duplicate downloads)
 */
const fetchVideoBlob = async (src) => {
    if (videoBlobCache.has(src)) {
        return videoBlobCache.get(src);
    }
    try {
        const res = await fetch(src);
        const blob = await res.blob();
        const blobUrl = URL.createObjectURL(blob);
        const filename = src.split('/').pop();
        videoBlobCache.set(src, blobUrl);
        blobToFilenameMap.set(blobUrl, filename); // Track filename for muting logic
        console.log('[VideoEngine] Cached:', filename);
        return blobUrl;
    } catch (err) {
        console.warn('[VideoEngine] Fetch failed, using direct URL:', src, err);
        return src; // Fallback to direct URL
    }
};

const loadVideoSafe = async (player, src, options = {}) => {
    if (!player || !src) return false;

    // Get blob URL (cached or fetch new)
    const blobUrl = await fetchVideoBlob(src);

    const playerSrc = player.src || '';

    // Skip if already loaded
    if (playerSrc === blobUrl) {
        return false;
    }

    player.src = blobUrl;
    player.muted = options.muted ?? true;
    player.currentTime = 0;
    if (options.load !== false) player.load();

    return true;
};

export default function VideoEngine() {
    const [showInteractionPrompt, setShowInteractionPrompt] = useState(false);
    // SOTA 2026: Hide Android WebView native poster until video starts
    const [videoReady, setVideoReady] = useState(false);

    const audioUnlocked = useTrinityStore(state => state.audioUnlocked);
    const unlockAudio = useTrinityStore(state => state.unlockAudio);
    const isMuted = useTrinityStore(state => state.isMuted);
    // const phase = useTrinityStore(state => state.phase);
    const locale = useTrinityStore(state => state.locale);

    // SOTA 2026: Get Filenames, not Paths
    const videoFiles = getVideoFilenames(locale);

    const pendingGaze = useTrinityStore(state => state.pendingGaze);
    const clearPendingGaze = useTrinityStore(state => state.clearPendingGaze);

    // SOTA 2026: Immersive Shutdown Sequence (Standard 382.22)
    const isShuttingDown = useTrinityStore(state => state.isShuttingDown);
    const setShuttingDown = useTrinityStore(state => state.setShuttingDown);
    const isShuttingDownRef = useRef(false);

    const videoA = useRef(null);
    const videoB = useRef(null);

    const activePlayerRef = useRef('A');
    const isTransitioningRef = useRef(false);
    const hasPlayedInitRef = useRef(false);
    const idleIndexRef = useRef(0);
    const isFadingAudioRef = useRef(false);
    const isPreloadedRef = useRef(false);
    const isPlayingGazeRef = useRef(false);
    const pendingGazeRef = useRef(null);

    useEffect(() => {
        if (pendingGaze) {
            console.log(`[VideoEngine] pendingGaze received: ${pendingGaze}`);
            // SOTA 2026: Reset preload state to force re-preload with gaze video
            // This ensures gaze animations override already-preloaded idle videos
            isPreloadedRef.current = false;
        }
        pendingGazeRef.current = pendingGaze;
    }, [pendingGaze]);

    // SOTA 2026: Immersive Shutdown Sequence (Standard 382.22)
    // When isShuttingDown becomes true, immediately force the sleep video
    useEffect(() => {
        if (!isShuttingDown || isShuttingDownRef.current) return;
        isShuttingDownRef.current = true;

        const playSleepVideo = async () => {
            console.log('[VideoEngine] 🌙 Initiating immersive shutdown sequence...');

            // Get the sleep video filename
            const sleepFilename = videoFiles.gaze.sleep;
            const sleepSrc = await assetLoader.getSmartPath(sleepFilename);
            const blobUrl = await fetchVideoBlob(sleepSrc);

            // Stop both players
            if (videoA.current) {
                videoA.current.pause();
                videoA.current.style.opacity = '0';
            }
            if (videoB.current) {
                videoB.current.pause();
                videoB.current.style.opacity = '0';
            }

            // Use player A for shutdown video
            const player = videoA.current;
            if (!player) return;

            player.src = blobUrl;
            player.currentTime = 0;
            player.muted = !audioUnlocked || isMuted;
            player.style.opacity = '1';

            // When video ends, keep screen black - AngelSplash will take over when trinityStatus changes
            player.onended = () => {
                console.log('[VideoEngine] 🌙 Sleep video complete. Waiting for AngelSplash...');
                // DO NOT reset isShuttingDown here - keep UI hidden until AngelSplash naturally takes over
            };

            try {
                await player.play();
                console.log('[VideoEngine] 🌙 Playing sleep video:', sleepFilename);

                // SOTA 2026: Launch shutdown IMMEDIATELY when video starts
                // API has entire video duration to complete - no delay at the end
                console.log('[VideoEngine] 🌙 Launching shutdown now (fire-and-forget)...');
                stopTrinity(); // fire-and-forget

            } catch (err) {
                console.error('[VideoEngine] Failed to play sleep video:', err);
                // Fallback: shutdown anyway
                stopTrinity();
            }
        };

        playSleepVideo();
    }, [isShuttingDown, videoFiles, audioUnlocked, isMuted, setShuttingDown]);

    // getNextIdle returns FILENAME now
    const getNextIdleName = useCallback(() => {
        if (isPlayingGazeRef.current) {
            console.log('[VideoEngine] Gaze finished -> Idle');
            isPlayingGazeRef.current = false;
        }

        if (pendingGazeRef.current && !isPlayingGazeRef.current) {
            const direction = pendingGazeRef.current;
            const gazeName = videoFiles.gaze[direction];
            console.log(`[VideoEngine] Request Gaze: ${direction}`);
            isPlayingGazeRef.current = true;
            clearPendingGaze();
            pendingGazeRef.current = null;
            return gazeName;
        }

        const idle = videoFiles.idles[idleIndexRef.current];
        idleIndexRef.current = (idleIndexRef.current + 1) % videoFiles.idles.length;
        return idle;
    }, [videoFiles, clearPendingGaze]);

    const getPlayers = useCallback(() => {
        const isA = activePlayerRef.current === 'A';
        return {
            current: isA ? videoA.current : videoB.current,
            next: isA ? videoB.current : videoA.current,
            currentId: isA ? 'A' : 'B',
            nextId: isA ? 'B' : 'A'
        };
    }, []);

    const preloadNextVideo = useCallback(async () => {
        // SOTA 2026: Block normal cycle during shutdown
        if (isShuttingDownRef.current) return;
        if (isPreloadedRef.current) return;
        isPreloadedRef.current = true;

        const { next } = getPlayers();
        const nextName = hasPlayedInitRef.current ? getNextIdleName() : videoFiles.idles[0];

        // SOTA 2026: Hybrid Resolution
        const nextSrc = await assetLoader.getSmartPath(nextName);

        // SOTA 2026: Mute ALL non-voice videos (idle + gaze)
        const isNonVoiceVideo = nextName.includes('gauche') || nextName.includes('droite') || nextName.includes('idle') || nextName.includes('bas');
        const shouldMute = isNonVoiceVideo ? true : (!audioUnlocked || isMuted);

        await loadVideoSafe(next, nextSrc, { muted: shouldMute });
    }, [audioUnlocked, getPlayers, getNextIdleName, videoFiles, isMuted]);

    const executeTransition = useCallback(() => {
        // SOTA 2026: Block normal cycle during shutdown
        if (isShuttingDownRef.current) return;
        if (isTransitioningRef.current) return;
        isTransitioningRef.current = true;

        const { current, next, nextId } = getPlayers();
        // console.log('[VideoEngine] Crossfade to', nextId);
        hasPlayedInitRef.current = true;

        if (next) {
            next.muted = true;
            next.volume = 1;

            // SOTA 2026: Mute ALL non-voice videos (idle + gaze) - Use filename map since blob URLs don't contain filename
            const nextFilename = blobToFilenameMap.get(next.src) || '';
            const isNonVoiceVideo = nextFilename.includes('gauche') || nextFilename.includes('droite') || nextFilename.includes('idle') || nextFilename.includes('bas');

            next.play().then(() => {
                if (audioUnlocked && !isMuted && !isNonVoiceVideo) {
                    next.muted = false;
                }
                next.style.opacity = '1';

                setTimeout(() => {
                    if (current) {
                        current.style.opacity = '0';
                        current.pause();
                        current.currentTime = 0;
                        current.volume = 1;
                    }
                    activePlayerRef.current = nextId;
                    isTransitioningRef.current = false;
                    isPreloadedRef.current = false;
                    isFadingAudioRef.current = false;
                }, CROSSFADE_DURATION);

            }).catch(err => {
                console.warn('[VideoEngine] Play failed:', err);
                isTransitioningRef.current = false;
            });
        }
    }, [getPlayers, audioUnlocked, isMuted]);

    // ... (handleTimeUpdate remains mostly same, just check ref calls)

    const handleTimeUpdate = useCallback((playerId) => {
        const video = playerId === 'A' ? videoA.current : videoB.current;
        if (!video || activePlayerRef.current !== playerId) return;
        if (isNaN(video.duration)) return;

        const timeRemaining = video.duration - video.currentTime;

        // Note: preloadNextVideo is async, we call it without await (fire & forget)
        if (timeRemaining <= PRELOAD_AHEAD && !isPreloadedRef.current) {
            preloadNextVideo();
        }

        if (timeRemaining <= AUDIO_FADE_DURATION && timeRemaining > 0) {
            if (!isFadingAudioRef.current) {
                isFadingAudioRef.current = true;
            }
            const fadeProgress = (AUDIO_FADE_DURATION - timeRemaining) / AUDIO_FADE_DURATION;
            const exponentialFade = Math.pow(fadeProgress, 2.5);
            video.volume = Math.max(0, 1 - exponentialFade);
        }

        if (timeRemaining <= TRANSITION_TRIGGER && !isTransitioningRef.current) {
            executeTransition();
        }
    }, [preloadNextVideo, executeTransition]);

    const handleEnded = useCallback(async (playerId) => {
        if (activePlayerRef.current !== playerId) return;

        const video = playerId === 'A' ? videoA.current : videoB.current;
        if (video) video.volume = 1;

        if (!isTransitioningRef.current) {
            isTransitioningRef.current = true;
            isFadingAudioRef.current = false;

            const { current, next, nextId } = getPlayers();

            // ASYNC RESOLUTION
            const nextName = hasPlayedInitRef.current ? getNextIdleName() : videoFiles.idles[0];
            hasPlayedInitRef.current = true;

            const nextSrc = await assetLoader.getSmartPath(nextName);

            await loadVideoSafe(next, nextSrc, { muted: true });

            if (next) {
                next.volume = 1;
                next.oncanplay = () => {
                    next.oncanplay = null;
                    next.play().then(() => {
                        // SOTA 2026: Mute ALL non-voice videos (idle + gaze) - Use filename map since blob URLs don't contain filename
                        const nextFilename = blobToFilenameMap.get(next.src) || '';
                        const isNonVoiceVideo = nextFilename.includes('gauche') || nextFilename.includes('droite') || nextFilename.includes('idle') || nextFilename.includes('bas');
                        if (audioUnlocked && !isMuted && !isNonVoiceVideo) next.muted = false;
                        next.style.opacity = '1';
                        if (current) {
                            current.style.opacity = '0';
                            current.pause();
                            current.currentTime = 0;
                        }
                        activePlayerRef.current = nextId;
                        isTransitioningRef.current = false;
                        isPreloadedRef.current = false;
                    }).catch(() => {
                        isTransitioningRef.current = false;
                    });
                };
            }
        }
    }, [audioUnlocked, getPlayers, getNextIdleName, videoFiles, isMuted]);

    useEffect(() => {
        const initPlayer = async () => {
            if (videoA.current) {
                // SOTA 2026: Async Resolution for Init
                const initialName = videoFiles.init;
                const initialSrc = await assetLoader.getSmartPath(initialName);

                // Use blob cache for initial video too
                const blobUrl = await fetchVideoBlob(initialSrc);

                videoA.current.src = blobUrl;
                videoA.current.loop = false;
                videoA.current.muted = !audioUnlocked || isMuted;
                videoA.current.style.opacity = '1';

                try {
                    await videoA.current.play();
                    setVideoReady(true); // SOTA 2026: Hide black overlay
                    console.log(`[VideoEngine] Init: ${initialName} -> ${initialSrc}`);
                } catch (err) {
                    console.warn('[VideoEngine] Autoplay blocked, prompting user:', err);
                    setShowInteractionPrompt(true);
                    setVideoReady(true); // Show prompt instead of Android poster
                }
            }
            if (videoB.current) {
                videoB.current.style.opacity = '0';
            }
        };

        initPlayer();
    }, []); // Run once

    // ... (rest of effects for mute/unmute handled same way)
    // ... (handleManualStart updated to use assetLoader.getSmartPath if needed)


    // Manual start handler - ensures video is properly loaded
    const handleManualStart = async () => {
        unlockAudio();

        // SOTA 2026: "Bless" BOTH players with user gesture permission
        // This is critical for VS Code webview which has strict autoplay policy
        const blessPlayer = async (player, _name) => {
            if (!player) return;

            // Ensure source is set
            if (!player.src || player.src === '') {
                player.src = await assetLoader.getSmartPath(videoFiles.init);
            }

            player.muted = false;
            try {
                await player.play();
                console.log(`[VideoEngine] ${_name} blessed with autoplay permission`);
            } catch (_err) {
                console.warn(`[VideoEngine] ${_name} play failed (will retry on transition):`, _err);
            }
        };

        // Bless both players sequentially (safer for browser interaction tokens)
        blessPlayer(videoA.current, 'Player A')
            .then(() => blessPlayer(videoB.current, 'Player B'))
            .then(() => {
                console.log('[VideoEngine] Both players blessed');
                setShowInteractionPrompt(false);

                // Pause player B (it was just blessed, not meant to play yet)
                if (videoB.current) {
                    videoB.current.pause();
                    videoB.current.currentTime = 0;
                }
            });
    };

    // ... (Render)
    const videoStyle = {
        position: 'absolute',
        top: '50%',
        left: '50%',
        minWidth: '100%',
        minHeight: '100%',
        width: 'auto',
        height: 'auto',
        objectFit: 'cover',
        transform: 'translate(-50%, -50%)',
        transition: `opacity ${CROSSFADE_DURATION}ms ease-out`,
    };

    return (
        <div className="fixed top-0 left-0 w-full h-full -z-50 overflow-hidden bg-black">
            {/* SOTA 2026: Black overlay to hide Android WebView native poster/controls */}
            {!videoReady && (
                <div className="absolute inset-0 z-50 bg-black" />
            )}
            {/* SOTA 2026: CSS to hide native video controls and poster */}
            <style>{`
                video::-webkit-media-controls { display: none !important; }
                video::-webkit-media-controls-enclosure { display: none !important; }
                video::-webkit-media-controls-panel { display: none !important; }
                video::poster { display: none !important; }
            `}</style>
            <video
                ref={videoA}
                style={{ ...videoStyle, zIndex: 10, opacity: 1 }}
                playsInline
                preload="auto"
                poster="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
                onTimeUpdate={() => handleTimeUpdate('A')}
                onEnded={() => handleEnded('A')}
            />
            <video
                ref={videoB}
                style={{ ...videoStyle, zIndex: 9, opacity: 0 }}
                playsInline
                preload="auto"
                poster="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
                onTimeUpdate={() => handleTimeUpdate('B')}
                onEnded={() => handleEnded('B')}
            />
            {showInteractionPrompt && createPortal(
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    onClick={handleManualStart}
                    className="fixed inset-0 z-[99999] flex flex-col items-center justify-center bg-black/90 cursor-pointer backdrop-blur-sm"
                >
                    <motion.div
                        initial={{ scale: 0.9, y: 20 }}
                        animate={{ scale: 1, y: 0 }}
                        transition={{ type: "spring", bounce: 0.4 }}
                        className="flex flex-col items-center gap-8 text-center"
                    >
                        <div className="space-y-2">
                            <motion.h1
                                animate={{ opacity: [1, 0.8, 1] }}
                                transition={{ duration: 2, repeat: Infinity }}
                                className="text-5xl md:text-7xl font-black text-red-500 tracking-[0.2em] drop-shadow-[0_0_25px_rgba(239,68,68,0.6)]"
                            >
                                [ SYSTEM HALTED ]
                            </motion.h1>
                            <p className="text-red-500/50 font-mono text-sm tracking-[0.3em] uppercase">
                                // NEURAL LINK REQUIRED //
                            </p>
                        </div>
                        <motion.div
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                            className="group relative px-12 py-5 bg-transparent overflow-hidden mt-4"
                        >
                            <div className="absolute inset-0 border border-cyan-500/30 group-hover:border-cyan-400 transition-colors duration-300 rounded" />
                            <div className="absolute inset-0 bg-cyan-500/5 group-hover:bg-cyan-500/10 blur-xl transition-all duration-300" />
                            <div className="relative flex items-center gap-3">
                                <span className="w-2 h-2 bg-cyan-500 rounded-full animate-pulse" />
                                <span className="text-cyan-400 font-bold tracking-[0.3em] group-hover:text-cyan-300 group-hover:drop-shadow-[0_0_15px_rgba(34,211,238,0.8)] transition-all">
                                    CLICK TO INITIALIZE
                                </span>
                                <span className="w-2 h-2 bg-cyan-500 rounded-full animate-pulse" />
                            </div>
                        </motion.div>
                    </motion.div>
                </motion.div>,
                document.body
            )}
        </div>
    );
}
