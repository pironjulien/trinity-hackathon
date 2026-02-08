import { useRef, useState, useEffect } from 'react';
import './AngelPlayer.css';

interface AngelPlayerProps {
    src: string;
}

/**
 * AngelPlayer - Dual-Player Crossfade Video Loop
 * SOTA 2026: Direct autoplay with full audio
 */
export default function AngelPlayer({ src }: AngelPlayerProps) {
    const playerA = useRef<HTMLVideoElement>(null);
    const playerB = useRef<HTMLVideoElement>(null);

    const [activePlayer, setActivePlayer] = useState<'A' | 'B'>('A');
    const [isTransitioning, setIsTransitioning] = useState(false);
    const [isMuted, setIsMuted] = useState(true); // Start muted for autoplay

    // Initial Start - Direct play (Muted for Autoplay Policy)
    useEffect(() => {
        if (playerA.current) {
            playerA.current.muted = true; // Browser Policy: Must be muted
            playerA.current.volume = 0;   // Redundant safety
            playerA.current.play().catch(e => console.error("AutoPlay Error:", e));
        }
    }, [src]);

    // Sync mute state to both players
    useEffect(() => {
        if (playerA.current) {
            playerA.current.muted = isMuted;
            playerA.current.volume = isMuted ? 0 : 1;
        }
        if (playerB.current) {
            playerB.current.muted = isMuted;
            playerB.current.volume = isMuted ? 0 : 1;
        }
    }, [isMuted]);

    const handleTimeUpdate = (e: React.SyntheticEvent<HTMLVideoElement>) => {
        if (isTransitioning) return;

        const video = e.currentTarget;
        const timeLeft = video.duration - video.currentTime;
        const FADE_TIME = 1.5;

        if (timeLeft < FADE_TIME && timeLeft > 0) {
            triggerTransition();
        }
    };

    const triggerTransition = () => {
        setIsTransitioning(true);
        const nextPlayer = activePlayer === 'A' ? playerB : playerA;
        const nextId = activePlayer === 'A' ? 'B' : 'A';

        if (nextPlayer.current) {
            nextPlayer.current.currentTime = 0;
            // Keep same mute state during transition
            nextPlayer.current.muted = isMuted;
            nextPlayer.current.volume = isMuted ? 0 : 1;
            nextPlayer.current.play().then(() => {
                setActivePlayer(nextId);
                setTimeout(() => setIsTransitioning(false), 1600);
            }).catch(e => console.error("Transition Play Error:", e));
        }
    };

    const toggleSound = () => {
        const newMuted = !isMuted;
        setIsMuted(newMuted);
        
        // SOTA 2026: Explicitly "bless" both players with user interaction
        // This grants autoplay permission in VS Code webview's strict policy
        if (!newMuted) {
            // When unmuting, also call play() to grant permission
            if (playerA.current) {
                playerA.current.muted = false;
                playerA.current.volume = 1;
                playerA.current.play().catch(() => {});
            }
            if (playerB.current) {
                playerB.current.muted = false;
                playerB.current.volume = 1;
                playerB.current.play().catch(() => {});
            }
        }
    };

    return (
        <div className="angel-player-container">
            <video
                ref={playerA}
                src={src}
                className={`angel-video ${activePlayer === 'A' ? 'visible' : 'hidden'}`}
                playsInline
                muted={isMuted}
                onTimeUpdate={activePlayer === 'A' ? handleTimeUpdate : undefined}
            />
            <video
                ref={playerB}
                src={src}
                className={`angel-video ${activePlayer === 'B' ? 'visible' : 'hidden'}`}
                playsInline
                muted={isMuted}
                onTimeUpdate={activePlayer === 'B' ? handleTimeUpdate : undefined}
            />

            {/* Sound Toggle Button */}
            <button
                className="sound-toggle"
                onClick={toggleSound}
                title={isMuted ? "Activer le son" : "Couper le son"}
            >
                {isMuted ? "🔇" : "🔊"}
            </button>
        </div>
    );
}
