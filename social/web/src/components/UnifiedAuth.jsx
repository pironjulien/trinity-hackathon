import React, { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { useTrinityStore } from '../stores/trinityStore';
import enLocale from '../locales/en.json';
import frLocale from '../locales/fr.json';

const LOCALES = { en: enLocale, fr: frLocale };

const UnifiedAuth = ({ identity, setIdentity, passkey, setPasskey, disabled, onSubmit, onGoogleSubmit }) => {
    const locale = useTrinityStore(state => state.locale);
    const t = useMemo(() => LOCALES[locale]?.ui || LOCALES.en.ui, [locale]);
    const [activeField, setActiveField] = useState(null);
    const [isHovered, setIsHovered] = useState(false);
    const [phiHovered, setPhiHovered] = useState(false);
    const [hasError, setHasError] = useState(false);

    const handlePhiClick = () => {
        if (!identity?.trim() || !passkey?.trim()) {
            setHasError(true);
            setTimeout(() => setHasError(false), 1000);
            return;
        }
        onSubmit?.();
    };

    const inputBase = `
        bg-transparent border-none outline-none
        font-mono text-sm font-bold tracking-widest
        placeholder-cyan-300/30 text-center
        transition-all duration-300
    `;


    return (
        <div className="flex flex-col items-center">
            <motion.div
                initial={{ opacity: 0, y: 100, scale: 0.9 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{
                    duration: 1.2,
                    ease: [0.16, 1, 0.3, 1],
                    delay: 0.3
                }}
                onMouseEnter={() => setIsHovered(true)}
                onMouseLeave={() => setIsHovered(false)}
                className="relative h-14 md:h-16 flex items-center justify-center rounded-full overflow-hidden pointer-events-auto w-[95vw] md:w-[520px]"
            >
                <motion.div
                    className="absolute inset-0 rounded-full"
                    animate={{
                        boxShadow: isHovered
                            ? ['0 0 40px 15px #06b6d4, 0 0 80px 30px #a855f7, inset 0 0 30px rgba(6,182,212,0.4)',
                                '0 0 80px 25px #06b6d4, 0 0 150px 50px #a855f7, inset 0 0 50px rgba(168,85,247,0.5)',
                                '0 0 40px 15px #06b6d4, 0 0 80px 30px #a855f7, inset 0 0 30px rgba(6,182,212,0.4)']
                            : '0 0 20px #06b6d4, 0 0 40px #a855f7, inset 0 0 20px rgba(6,182,212,0.3)'
                    }}
                    transition={{ duration: isHovered ? 2 : 0.3, repeat: isHovered ? Infinity : 0, ease: "easeInOut" }}
                    style={{
                        background: 'linear-gradient(90deg, #06b6d4, #a855f7, #06b6d4)',
                        backgroundSize: '200% 100%',
                        animation: 'gradient-x 3s linear infinite',
                    }}
                />

                {/* Inner dark */}
                <motion.div
                    className="absolute rounded-full bg-black/90 backdrop-blur-xl"
                    animate={{ inset: isHovered ? '4px' : '3px' }}
                    transition={{ duration: 0.2 }}
                />

                {/* Form wrapper to satisfy browser password autocomplete */}
                <form
                    className="absolute inset-0 z-10 flex items-center justify-center w-full h-full px-6"
                    onSubmit={(e) => { e.preventDefault(); handlePhiClick(); }}
                >
                    {/* Identity Input */}
                    <motion.div
                        className="flex-1 flex items-center justify-center"
                        whileHover={{ scale: 1.02 }}
                        animate={{ x: hasError ? [0, -4, 4, -4, 4, 0] : 0 }}
                        transition={{ duration: 0.4 }}
                    >
                        <input
                            id="identity"
                            name="identity"
                            autoComplete="username"
                            type="text"
                            value={identity}
                            onChange={(e) => setIdentity(e.target.value)}
                            onFocus={() => setActiveField('identity')}
                            onBlur={() => setActiveField(null)}
                            disabled={disabled}
                            className={`${inputBase} w-full transition-all duration-200 ${hasError
                                ? 'text-red-400 placeholder-red-400/60 drop-shadow-[0_0_15px_rgba(239,68,68,0.8)]'
                                : 'text-cyan-100 hover:text-cyan-50 focus:text-white focus:drop-shadow-[0_0_10px_rgba(6,182,212,0.8)] placeholder-cyan-300/30'
                                }`}
                            placeholder={t.identity}
                        />
                    </motion.div>

                    {/* Central Phi - Submit Button */}
                    <motion.button
                        type="button"
                        onClick={handlePhiClick}
                        onMouseEnter={() => setPhiHovered(true)}
                        onMouseLeave={() => setPhiHovered(false)}
                        className="mx-4 flex items-center justify-center cursor-pointer focus:outline-none"
                        style={{ transform: 'translateY(-6px)' }}
                        animate={{
                            scale: phiHovered ? 1.35 : (isHovered ? 1.15 : 1),
                            y: phiHovered ? -8 : (isHovered ? -4 : 0),
                            x: hasError ? [0, -8, 8, -8, 8, 0] : 0,
                        }}
                        transition={{ duration: 0.3, type: "spring", stiffness: 300 }}
                        whileTap={{ scale: 0.9 }}
                        disabled={disabled}
                    >
                        <motion.span
                            className="text-4xl font-serif leading-none"
                            animate={{
                                color: hasError ? '#ef4444' : (phiHovered ? '#fef08a' : '#fde047'),
                                textShadow: hasError
                                    ? '0 0 40px rgba(239,68,68,1), 0 0 80px rgba(239,68,68,0.8), 0 0 120px rgba(239,68,68,0.5)'
                                    : phiHovered
                                        ? '0 0 40px rgba(253,224,71,1), 0 0 80px rgba(253,224,71,0.9), 0 0 120px rgba(253,224,71,0.6)'
                                        : isHovered
                                            ? '0 0 30px rgba(253,224,71,0.8)'
                                            : '0 0 15px rgba(253,224,71,0.5)'
                            }}
                            transition={{ duration: 0.2 }}
                        >
                            φ
                        </motion.span>
                    </motion.button>

                    {/* Passkey Input */}
                    <motion.div
                        className="flex-1 flex items-center justify-center"
                        whileHover={{ scale: 1.02 }}
                        animate={{ x: hasError ? [0, -4, 4, -4, 4, 0] : 0 }}
                        transition={{ duration: 0.4 }}
                    >
                        <input
                            id="passkey"
                            name="passkey"
                            autoComplete="current-password"
                            type="password"
                            value={passkey}
                            onChange={(e) => setPasskey(e.target.value)}
                            onFocus={() => setActiveField('passkey')}
                            onBlur={() => setActiveField(null)}
                            disabled={disabled}
                            className={`${inputBase} w-full transition-all duration-200 ${hasError
                                ? 'text-red-400 placeholder-red-400/60 drop-shadow-[0_0_15px_rgba(239,68,68,0.8)]'
                                : 'text-purple-100 hover:text-purple-50 focus:text-white focus:drop-shadow-[0_0_10px_rgba(168,85,247,0.8)] placeholder-purple-300/30'
                                }`}
                            placeholder={t.passkey}
                        />
                    </motion.div>
                </form>

                {/* CSS Animation */}
                <style>{`
                @keyframes gradient-x {
                    0% { background-position: 0% 50%; }
                    100% { background-position: 200% 50%; }
                }
            `}</style>
            </motion.div>

            {/* TRINITY X GOOGLE Branding */}
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1.5, duration: 1 }}
                className="mt-4 text-center font-mono text-sm tracking-[0.3em]"
            >
                <span className="text-white/60">TRINITY</span>
                <span className="text-white/40 mx-2">×</span>
                <span style={{ color: '#4285F4' }}>G</span>
                <span style={{ color: '#EA4335' }}>O</span>
                <span style={{ color: '#FBBC05' }}>O</span>
                <span style={{ color: '#4285F4' }}>G</span>
                <span style={{ color: '#34A853' }}>L</span>
                <span style={{ color: '#EA4335' }}>E</span>
            </motion.div>

            {/* Google Sign-In Button */}
            <motion.button
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 2, duration: 0.5 }}
                whileHover={{
                    scale: 1.05,
                    boxShadow: '0 0 20px rgba(66, 133, 244, 0.5)'
                }}
                whileTap={{ scale: 0.95 }}
                onClick={onGoogleSubmit}
                disabled={disabled}
                className="mt-4 flex items-center gap-3 px-6 py-3 bg-white/5 border border-white/20 rounded-full
                           hover:bg-white/10 hover:border-white/40 transition-all duration-300
                           font-mono text-sm tracking-widest text-white/80 hover:text-white
                           disabled:opacity-50 disabled:cursor-not-allowed"
            >
                {/* Google Icon */}
                <svg className="w-5 h-5" viewBox="0 0 24 24">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                </svg>
                <span>SIGN IN</span>
            </motion.button>
        </div>
    );
};

export default UnifiedAuth;
