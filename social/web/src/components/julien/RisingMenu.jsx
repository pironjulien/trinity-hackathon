import React, { useRef, useState, useMemo } from 'react';
import './julien-styles.css';
import { useMetalBar } from '../../hooks/useMetalBar';
import Terminal from './Terminal';
import ChangelogViewer from '../core/ChangelogViewer';
import { useTrinityStore } from '../../stores/trinityStore';
import enLocale from '../../locales/en.json';
import frLocale from '../../locales/fr.json';

const LOCALES = { en: enLocale, fr: frLocale };

export default function RisingMenu({ isOpen }) {
    const menuTopRef = useRef(null);
    const menuBgRef = useRef(null);
    const [activeTab, setActiveTab] = useState('TERMINAL');

    // i18n
    const locale = useTrinityStore(state => state.locale);
    const t = useMemo(() => LOCALES[locale]?.ui || LOCALES.en.ui, [locale]);

    const logoLeftRef = useRef(null);
    const logoRightRef = useRef(null);

    React.useEffect(() => {
        const findLogos = () => {
            logoLeftRef.current = document.querySelector('.julien-header-left .julien-logo-img');
            logoRightRef.current = document.querySelector('.julien-header-right .julien-logo-img');

            if (logoLeftRef.current && logoRightRef.current) {
                window.dispatchEvent(new Event('resize'));
            }
        };

        findLogos();
        const intervals = [100, 300, 1000].map(delay => setTimeout(findLogos, delay));
        return () => intervals.forEach(clearTimeout);
    }, []);

    useMetalBar(menuBgRef, logoLeftRef, logoRightRef, true);

    return (
        <nav className={`julien-menu ${isOpen ? 'open' : ''}`} id="main-menu" hidden={!isOpen && false}>
            <div ref={menuBgRef} className="julien-metal-bg" />
            <div className="julien-menu-top" ref={menuTopRef}>
                {/* Buttons Container - Hidden on Desktop (md) where both are visible */}
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 flex gap-4 px-8 md:hidden">
                    <button
                        onClick={() => setActiveTab('TERMINAL')}
                        className={`text-xs font-bold tracking-widest px-4 py-1 rounded transition-colors ${activeTab === 'TERMINAL'
                            ? 'bg-neon-blue text-black shadow-[0_0_10px_rgba(66,133,244,0.5)]'
                            : 'text-white/50 hover:text-white hover:bg-white/10'
                            }`}
                    >
                        {t.terminal}
                    </button>
                    <button
                        onClick={() => setActiveTab('CHANGELOG')}
                        className={`text-xs font-bold tracking-widest px-4 py-1 rounded transition-colors ${activeTab === 'CHANGELOG'
                            ? 'bg-neon-pink text-black shadow-[0_0_10px_rgba(255,0,255,0.5)]'
                            : 'text-white/50 hover:text-white hover:bg-white/10'
                            }`}
                    >
                        {t.changelog}
                    </button>
                </div>
            </div>

            {/* Content Area - Flex Col on Mobile, Row on Desktop */}
            {/* Content Area - Flex Col on Mobile, Row on Desktop */}
            <div className="julien-menu-content font-mono flex flex-col md:flex-row md:items-stretch md:!gap-8 md:!justify-center relative">
                {/* 
                    Terminal Section:
                    - Mobile: Visible if activeTab is TERMINAL
                    - Desktop: Always visible
                 */}
                <div className={`w-full h-full md:w-1/2 flex flex-col items-center md:flex ${activeTab === 'TERMINAL' ? 'flex' : 'hidden md:flex'}`}>
                    <h3 className="hidden md:flex items-center justify-center gap-3 mb-4 pb-3 w-full max-w-[500px]
                        text-[#53fff4] font-mono font-black tracking-[0.3em] uppercase text-base
                        border-b border-[#53fff4]/30
                        [text-shadow:0_0_5px_#53fff4,0_0_15px_#53fff4,0_0_30px_#53fff4,0_0_50px_#00b4d8]
                        before:content-['◄'] before:text-[#53fff4]/60 before:text-xs before:animate-pulse
                        after:content-['►'] after:text-[#53fff4]/60 after:text-xs after:animate-pulse">
                        <span className="relative">
                            <span className="absolute inset-0 blur-sm text-[#53fff4]/50">{t.terminal}</span>
                            {t.terminal}
                        </span>
                    </h3>
                    <div className="flex-1 min-h-0 w-full flex justify-center">
                        <Terminal />
                    </div>
                </div>

                {/* 
                    Changelog Section:
                    - Mobile: Visible if activeTab is CHANGELOG
                    - Desktop: Always visible
                 */}
                <div className={`w-full h-full md:w-1/2 flex flex-col items-center md:flex ${activeTab === 'CHANGELOG' ? 'flex' : 'hidden md:flex'}`}>
                    <h3 className="hidden md:flex items-center justify-center gap-3 mb-4 pb-3 w-full max-w-[500px]
                        text-[#ff00ff] font-mono font-black tracking-[0.3em] uppercase text-base
                        border-b border-[#ff00ff]/30
                        [text-shadow:0_0_5px_#ff00ff,0_0_15px_#ff00ff,0_0_30px_#ff00ff,0_0_50px_#bc13fe]
                        before:content-['◄'] before:text-[#ff00ff]/60 before:text-xs before:animate-pulse
                        after:content-['►'] after:text-[#ff00ff]/60 after:text-xs after:animate-pulse">
                        <span className="relative">
                            <span className="absolute inset-0 blur-sm text-[#ff00ff]/50">{t.changelog}</span>
                            {t.changelog}
                        </span>
                    </h3>
                    <div className="flex-1 min-h-0 w-full flex justify-center">
                        <ChangelogViewer />
                    </div>
                </div>
            </div>
        </nav>
    );
}
