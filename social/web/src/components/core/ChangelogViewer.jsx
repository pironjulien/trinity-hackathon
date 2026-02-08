import React, { useEffect, useRef, useState, useMemo } from 'react';
import '../julien/julien-styles.css';
import { useTrinityStore } from '../../stores/trinityStore';
import enLocale from '../../locales/en.json';
import frLocale from '../../locales/fr.json';

const LOCALES = { en: enLocale, fr: frLocale };

export default function ChangelogViewer() {
    const listRef = useRef(null);
    const bottomRef = useRef(null);
    const [logs, setLogs] = useState([]);

    // i18n
    const locale = useTrinityStore(state => state.locale);
    const localeData = useMemo(() => LOCALES[locale] || LOCALES.en, [locale]);
    const SKYNET_CHANGELOG = localeData.changelog;
    const RANDOM_SYS_NOISE = localeData.changelogNoise;

    // Smart Auto-scroll - same pattern as Terminal
    const isAtBottomRef = useRef(true);

    const checkScrollPosition = () => {
        if (!listRef.current) return;
        const { scrollTop, scrollHeight, clientHeight } = listRef.current;
        // User is at bottom if distance to bottom is less than 100px
        isAtBottomRef.current = scrollHeight - scrollTop - clientHeight < 100;
    };

    // Attach scroll listener
    useEffect(() => {
        const div = listRef.current;
        if (div) {
            div.addEventListener('scroll', checkScrollPosition);
            return () => div.removeEventListener('scroll', checkScrollPosition);
        }
    }, []);

    useEffect(() => {
        let mounted = true;
        let index = 0;

        // Reset logs when locale changes
        setLogs([]);

        const addLog = (item) => {
            if (!mounted) return;
            const time = new Date().toLocaleTimeString(locale === 'fr' ? 'fr-FR' : 'en-US', { hour12: false });
            setLogs(prev => [...prev, { ...item, time, id: Math.random() }]);
        };

        const playSequence = () => {
            if (index >= SKYNET_CHANGELOG.length) {
                if (Math.random() > 0.7) {
                    addLog({
                        msg: RANDOM_SYS_NOISE[Math.floor(Math.random() * RANDOM_SYS_NOISE.length)],
                        type: 'dim',
                        ver: "SYS"
                    });
                }
                setTimeout(playSequence, 2000);
                return;
            }

            const item = SKYNET_CHANGELOG[index];
            addLog(item);
            index++;
            setTimeout(playSequence, 800 + Math.random() * 1000);
        };

        playSequence();
        return () => { mounted = false; };
    }, [locale, SKYNET_CHANGELOG, RANDOM_SYS_NOISE]);

    // Scroll only if was already at bottom
    useEffect(() => {
        if (isAtBottomRef.current && bottomRef.current) {
            bottomRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [logs]);

    return (
        <div ref={listRef} className="c-terminal" style={{
            height: '100%',
            border: '2px solid #ff00ff',
            boxShadow: 'inset 0 0 20px rgba(0, 0, 0, 0.8), 0 0 15px rgba(255, 0, 255, 0.3), 0 0 30px rgba(255, 0, 255, 0.15)'
        }}>
            {logs.map(log => (
                <div key={log.id} className={`term-line term-${log.type}`}>
                    <span className="term-time">[{log.time}]</span>
                    <span className="text-neon-blue font-bold mr-2">[{log.ver}]</span>
                    <span className="term-msg">{log.msg}</span>
                </div>
            ))}
            <div ref={bottomRef} />
        </div>
    );
}
