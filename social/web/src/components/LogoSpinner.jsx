import React from 'react';
import { motion } from 'framer-motion';

const LogoSpinner = () => {
    return (

        <div className="absolute bottom-20 right-8 md:bottom-12 md:right-12 z-50 flex flex-col md:flex-row items-center gap-4 select-none">


            {/* Spinning Logo Container - Links to julienpiron.fr */}
            <a
                href="https://julienpiron.fr"
                target="_blank"
                rel="noopener noreferrer"
                className="relative block cursor-pointer order-1 md:order-2"
            >
                {/* Outer Ring */}
                <motion.div
                    className="w-16 h-16 rounded-full border border-white/10 border-t-cyan-500/50 border-r-transparent"
                    animate={{ rotate: 360 }}
                    transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                />

                {/* Inner Logo */}
                <motion.img
                    src="/images/pi-logo.webp"
                    alt="Julien Piron"
                    className="absolute top-1/2 left-1/2 w-8 h-8 object-contain"
                    style={{ x: '-50%', y: '-50%' }}
                    animate={{ opacity: [0.5, 1, 0.5] }}
                    transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
                />
            </a>
        </div>
    );
};

export default LogoSpinner;
