import React from 'react';
import { motion } from 'framer-motion';
import { useTrinityStore } from '../../stores/trinityStore';

/**
 * SOTA 2026: Premium Glass Language Switch
 * Ultra-polished sliding glass square with neon accents
 */
export default function LanguageSwitch() {
    const locale = useTrinityStore(state => state.locale);
    const setLocale = useTrinityStore(state => state.setLocale);

    const isEN = locale === 'en';

    return (
        <div className="relative flex items-center p-0.5 rounded-lg
                        bg-gradient-to-br from-white/5 via-transparent to-white/5
                        border border-white/10 backdrop-blur-sm
                        shadow-[0_4px_20px_rgba(0,0,0,0.3),inset_0_1px_0_rgba(255,255,255,0.05)]
                        overflow-hidden">

            {/* Animated Glow Background */}
            <motion.div
                animate={{
                    opacity: [0.3, 0.5, 0.3],
                    scale: [1, 1.02, 1]
                }}
                transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
                className="absolute inset-0 rounded-lg bg-gradient-to-r from-cyan-500/10 via-transparent to-purple-500/10"
            />

            {/* Sliding Glass Square */}
            <motion.div
                layout
                transition={{ type: 'spring', stiffness: 350, damping: 28 }}
                className="absolute w-11 h-9 rounded-md
                           bg-gradient-to-br from-white/15 via-white/10 to-white/5
                           backdrop-blur-xl border border-white/25
                           shadow-[0_0_20px_rgba(6,182,212,0.2),0_0_40px_rgba(168,85,247,0.1),inset_0_1px_0_rgba(255,255,255,0.2)]"
                style={{
                    left: isEN ? '2px' : 'calc(100% - 46px)',
                    boxShadow: isEN
                        ? '0 0 20px rgba(6,182,212,0.3), 0 0 40px rgba(6,182,212,0.1), inset 0 1px 0 rgba(255,255,255,0.2)'
                        : '0 0 20px rgba(168,85,247,0.3), 0 0 40px rgba(168,85,247,0.1), inset 0 1px 0 rgba(255,255,255,0.2)'
                }}
            >
                {/* Inner Glass Reflection */}
                <div className="absolute inset-x-1 top-1 h-3 rounded-sm bg-gradient-to-b from-white/20 to-transparent" />
            </motion.div>

            {/* EN Button */}
            <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setLocale('en')}
                className={`relative z-10 w-11 h-9 font-['Monoton'] text-sm font-black tracking-wide
                           transition-all duration-500 ${isEN
                        ? 'text-cyan-300 drop-shadow-[0_0_12px_rgba(6,182,212,1)]'
                        : 'text-white/30 hover:text-white/50'
                    }`}
            >
                EN
            </motion.button>

            {/* FR Button */}
            <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setLocale('fr')}
                className={`relative z-10 w-11 h-9 font-['Monoton'] text-sm font-black tracking-wide
                           transition-all duration-500 ${!isEN
                        ? 'text-purple-300 drop-shadow-[0_0_12px_rgba(168,85,247,1)]'
                        : 'text-white/30 hover:text-white/50'
                    }`}
            >
                FR
            </motion.button>
        </div>
    );
}
