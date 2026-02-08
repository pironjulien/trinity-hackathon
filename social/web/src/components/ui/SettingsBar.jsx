import React from 'react';
import { motion } from 'framer-motion';
import { useTrinityStore } from '../../stores/trinityStore';
import { Volume2, VolumeX } from 'lucide-react';

/**
 * SOTA 2026: SettingsBar - Exact same style as CyberWindow collapsed
 */
export default function SettingsBar() {
    const locale = useTrinityStore(state => state.locale);
    const setLocale = useTrinityStore(state => state.setLocale);
    const isMuted = useTrinityStore(state => state.isMuted);
    const setMuted = useTrinityStore(state => state.setMuted);
    const unlockAudio = useTrinityStore(state => state.unlockAudio);

    const isEN = locale === 'en';
    const soundEnabled = !isMuted;

    const handleSoundToggle = () => {
        const newMuted = !isMuted;
        setMuted(newMuted);
        if (!newMuted) unlockAudio();
    };

    return (
        <motion.div
            layout
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="flex flex-col
                       bg-glass border border-white/10 
                       backdrop-blur-xl rounded-lg overflow-hidden
                       shadow-[0_0_15px_rgba(0,0,0,0.5)]
                       group
                       relative w-full h-12"
        >
            {/* Content - Same structure as CyberWindow header */}
            <div className="flex items-center justify-center gap-6 px-4 h-12 bg-black/40">
                {/* Sound Toggle Switch */}
                <div className="flex items-center gap-3">
                    <span className={`transition-all duration-300 ${soundEnabled ? 'text-green-400' : 'text-white/40'}`}>
                        {soundEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
                    </span>
                    <button
                        onClick={handleSoundToggle}
                        className={`relative w-10 h-5 rounded-full transition-all duration-300 
                                   ${soundEnabled ? 'btn-neon-green border-transparent' : 'bg-white/10'}`}
                        title={soundEnabled ? 'Mute sound' : 'Enable sound'}
                    >
                        <div className={`absolute top-0.5 w-4 h-4 rounded-full transition-all duration-300
                                        ${soundEnabled
                                ? 'right-0.5 bg-green-500 shadow-none'
                                : 'left-0.5 bg-white/40'}`}
                        />
                    </button>
                </div>

                {/* Language Switch */}
                <div className="flex items-center gap-1 p-0.5 rounded-md
                                bg-black/30 border border-white/10">
                    <button
                        onClick={() => setLocale('en')}
                        className={`px-3 py-1.5 text-xs font-['Monoton'] tracking-wide rounded relative transition-all duration-300 ${isEN
                            ? 'btn-neon-primary text-cyan-300 text-glow-cyan'
                            : 'text-white/30 hover:text-white/50 bg-white/5 border border-white/5'
                            }`}
                    >
                        EN
                    </button>
                    <button
                        onClick={() => setLocale('fr')}
                        className={`px-3 py-1.5 text-xs font-['Monoton'] tracking-wide rounded relative transition-all duration-300 ${!isEN
                            ? 'btn-neon-purple text-purple-300 text-glow-purple'
                            : 'text-white/30 hover:text-white/50 bg-white/5 border border-white/5'
                            }`}
                    >
                        FR
                    </button>
                </div>
            </div>
        </motion.div>
    );
}
