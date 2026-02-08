import { useCallback, useRef, useEffect } from 'react';
import { useTrinityStore } from '../stores/trinityStore';

/**
 * SOTA 2026: Modern AI-style sounds
 * 
 * Soft, subtle, futuristic - not 80s arcade beeps
 * Uses layered harmonics and noise for digital feel
 */
let audioContext = null;

const getAudioContext = () => {
    if (!audioContext && typeof window !== 'undefined') {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
    return audioContext;
};

export const useCyberSound = () => {
    const hasInteracted = useRef(false);

    // Resume/create AudioContext on any user interaction
    const ensureAudioReady = useCallback(() => {
        const ctx = getAudioContext();
        if (ctx && ctx.state === 'suspended') {
            ctx.resume();
        }
        hasInteracted.current = true;
    }, []);

    // Attach global listener for first interaction
    useEffect(() => {
        const handleInteraction = () => {
            ensureAudioReady();
            window.removeEventListener('click', handleInteraction);
            window.removeEventListener('keydown', handleInteraction);
            window.removeEventListener('touchstart', handleInteraction);
        };

        window.addEventListener('click', handleInteraction, { once: true });
        window.addEventListener('keydown', handleInteraction, { once: true });
        window.addEventListener('touchstart', handleInteraction, { once: true });

        return () => {
            window.removeEventListener('click', handleInteraction);
            window.removeEventListener('keydown', handleInteraction);
            window.removeEventListener('touchstart', handleInteraction);
        };
    }, [ensureAudioReady]);

    // Soft AI-style tone with harmonics
    const playSoftTone = useCallback((baseFreq = 400, volume = 0.03, duration = 0.15) => {
        // SOTA 2026: Respect global mute state
        const isMuted = useTrinityStore.getState().isMuted;
        if (isMuted) return;

        const ctx = getAudioContext();
        if (!ctx) return;

        if (ctx.state === 'suspended') {
            ctx.resume();
        }

        // Main tone (very soft sine)
        const osc1 = ctx.createOscillator();
        const gain1 = ctx.createGain();
        osc1.type = 'sine';
        osc1.frequency.setValueAtTime(baseFreq, ctx.currentTime);
        gain1.gain.setValueAtTime(volume, ctx.currentTime);
        gain1.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);

        // Subtle harmonic (octave up, quieter)
        const osc2 = ctx.createOscillator();
        const gain2 = ctx.createGain();
        osc2.type = 'sine';
        osc2.frequency.setValueAtTime(baseFreq * 2, ctx.currentTime);
        gain2.gain.setValueAtTime(volume * 0.3, ctx.currentTime);
        gain2.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration * 0.8);

        osc1.connect(gain1);
        osc2.connect(gain2);
        gain1.connect(ctx.destination);
        gain2.connect(ctx.destination);

        osc1.start();
        osc2.start();
        osc1.stop(ctx.currentTime + duration);
        osc2.stop(ctx.currentTime + duration);
    }, []);

    // Soft click - subtle chime
    const playClick = useCallback(() => {
        playSoftTone(520, 0.04, 0.12);
    }, [playSoftTone]);

    // Hover - barely audible soft breath
    const playHover = useCallback(() => {
        playSoftTone(380, 0.015, 0.08);
    }, [playSoftTone]);

    // Type - soft digital tick
    const playType = useCallback(() => {
        playSoftTone(450, 0.025, 0.06);
    }, [playSoftTone]);

    return { playClick, playHover, playType, ensureAudioReady };
};
