import React, { useRef, useEffect } from 'react';
import './julien-styles.css';
import { useMetalBar } from '../../hooks/useMetalBar';

export default function Header({ onMenuClick, isMenuOpen }) {
    const headerRef = useRef(null);
    const headerBgRef = useRef(null);
    const logoLeftRef = useRef(null);
    const logoRightRef = useRef(null);
    const headerLeftRef = useRef(null);
    const headerCenterRef = useRef(null);
    const headerRightRef = useRef(null);

    // Pass structural refs to catch grid shifts
    // SOTA FIX: Apply metal effect to headerBgRef (background) not headerRef (container)
    // This prevents mask-image from hiding the children (logos)
    useMetalBar(headerBgRef, logoLeftRef, logoRightRef, false, [headerLeftRef, headerCenterRef, headerRightRef]);

    // Neon text split effect
    const neonTextRef = useRef(null);
    useEffect(() => {
        const neon = neonTextRef.current;
        if (!neon) return;

        if (!neon.dataset.split) {
            neon.dataset.split = '1';
            const text = neon.textContent;
            neon.setAttribute("aria-label", text);
            neon.textContent = '';
            const chars = [];
            Array.from(text).forEach((ch) => {
                const span = document.createElement('span');
                span.className = 'julien-neon-char';
                span.setAttribute("aria-hidden", "true");
                span.textContent = ch;
                neon.appendChild(span);
                chars.push(span);
            });

            // Chaos loop (ported from ui.js)
            const chaosLoop = () => {
                const baseDelay = Math.random() > 0.618 ? 89 + Math.random() * 377 : 987 + Math.random() * 2584;
                const nextDelay = baseDelay * 1.5; // frequency factor
                setTimeout(() => { triggerEvent(); chaosLoop(); }, nextDelay);
            };

            const triggerEvent = () => {
                if (chars.length === 0) return;
                const typeRoll = Math.random();

                if (typeRoll < 0.02) {
                    neon.classList.add('blackout');
                    setTimeout(() => neon.classList.remove('blackout'), Math.random() > 0.5 ? 80 : 350);
                    return;
                }

                const targets = [chars[Math.floor(Math.random() * chars.length)]];
                if (chars.length > 5 && Math.random() > 0.85) {
                    targets.push(chars[Math.floor(Math.random() * chars.length)]);
                }

                const isCut = Math.random() > 0.75;
                if (isCut) {
                    targets.forEach(t => t?.classList.add('neon-off'));
                    setTimeout(() => targets.forEach(t => t?.classList.remove('neon-off')), 200 + Math.random() * 1000);
                } else {
                    targets.forEach(t => t?.classList.add('glitching'));
                    setTimeout(() => targets.forEach(t => t?.classList.remove('glitching')), 280);
                }
            };

            chaosLoop();

            // Auto-spin on mount
            if (logoLeftRef.current) {
                logoLeftRef.current.classList.add('spin');
                setTimeout(() => logoLeftRef.current?.classList.remove('spin'), 2000);
            }
        }
    }, []);

    return (
        <header className="julien-header" ref={headerRef}>
            <div ref={headerBgRef} className="julien-metal-bg" />
            <h1 className="visually-hidden">Julien Piron — Projets, vidéos, musique et articles</h1>

            <div className="julien-header-left" ref={headerLeftRef}>
                <a href="https://julienpiron.fr" className="julien-logo-btn" aria-label="Accueil" target="_blank" rel="noopener noreferrer">
                    <img
                        ref={logoLeftRef}
                        src="/julien_assets/img/julienpiron.webp"
                        alt="Logo de Julien Piron"
                        width="128"
                        height="128"
                        fetchPriority="high"
                        className="julien-logo-img"
                    />
                </a>
            </div>

            <div className="julien-header-center" aria-hidden="true" ref={headerCenterRef}>
                <span className="julien-neon-text" ref={neonTextRef}>
                    <span className="phi-icon" style={{ marginRight: '0.5em', fontSize: '1.2em' }}>&Phi;</span>
                    TRINITY
                    <span className="phi-icon" style={{ marginLeft: '0.5em', fontSize: '1.2em' }}>&Phi;</span>
                </span>
            </div>

            <div className="julien-header-right" ref={headerRightRef}>
                <button
                    type="button"
                    className="julien-logo-btn"
                    id="menu-button"
                    aria-label="Menu"
                    aria-expanded={isMenuOpen}
                    aria-controls="main-menu"
                    onClick={onMenuClick}
                >
                    <img
                        ref={logoRightRef}
                        src="/julien_assets/img/menu.webp"
                        alt=""
                        width="128"
                        height="128"
                        className="julien-logo-img"
                    />
                </button>
            </div>
        </header>
    );
}
