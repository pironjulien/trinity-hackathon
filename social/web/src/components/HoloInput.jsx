import React, { useState } from 'react';
import { motion } from 'framer-motion';

const HoloInput = ({ side = 'left', label, type = 'text', value, onChange, disabled, id, name, ...props }) => {
    const [isFocused, setIsFocused] = useState(false);

    // 3D Transform settings based on side
    const variants = {
        initial: {
            opacity: 0,
            y: 20,
            rotateY: side === 'left' ? 15 : -15,
            scale: 0.9,
        },
        animate: {
            opacity: 1,
            y: 0,
            rotateY: side === 'left' ? 15 : -15,
            scale: 1,
            transition: {
                duration: 0.8,
                ease: "easeOut",
                delay: side === 'left' ? 0.2 : 0.4
            }
        },
        exit: {
            opacity: 0,
            scale: 0.0, // Implosion effect target
            transition: { duration: 0.3 }
        }
    };

    return (
        <motion.div
            className={`relative group perspective-1000 ${side === 'left' ? 'mr-auto' : 'ml-auto'}`}
            initial="initial"
            animate="animate"
            exit="exit"
            variants={variants}
            style={{
                transformStyle: 'preserve-3d',
                perspective: '1000px',
            }}
        >
            {/* Holographic Container */}
            <div className={`
        relative w-80 p-6 
        backdrop-blur-xl bg-white/5 
        border border-white/10 
        rounded-lg 
        shadow-[0_0_15px_rgba(0,0,0,0.3)]
        transition-all duration-300
        ${isFocused ? 'border-cyan-400/50 shadow-[0_0_25px_rgba(34,211,238,0.2)] bg-cyan-900/10' : ''}
      `}>
                {/* Corner Decals (tech feel) */}
                <div className="absolute top-0 left-0 w-2 h-2 border-t border-l border-white/40" />
                <div className="absolute top-0 right-0 w-2 h-2 border-t border-r border-white/40" />
                <div className="absolute bottom-0 left-0 w-2 h-2 border-b border-l border-white/40" />
                <div className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-white/40" />

                {/* Label */}
                <label className="block text-xs uppercase tracking-[0.2em] text-cyan-200/70 mb-2 font-mono">
                    {label}
                </label>

                {/* Input Field */}
                <input
                    id={id || label.replace(/\s+/g, '_').toLowerCase()}
                    name={name || id || label.replace(/\s+/g, '_').toLowerCase()}
                    type={type}
                    value={value}
                    onChange={onChange}
                    disabled={disabled}
                    onFocus={() => setIsFocused(true)}
                    onBlur={() => setIsFocused(false)}
                    className="
            w-full bg-transparent 
            border-b border-white/20 
            text-white font-mono text-lg
            focus:outline-none focus:border-cyan-400
            placeholder-white/20
            py-1
          "
                    placeholder={type === 'password' ? '••••••' : 'USER_ID'}
                />

                {/* Scanline overlay for that holo-feel */}
                <div className="absolute inset-0 pointer-events-none bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] bg-[length:100%_2px,3px_100%] rounded-lg opacity-20" />
            </div>
        </motion.div>
    );
};

export default HoloInput;
