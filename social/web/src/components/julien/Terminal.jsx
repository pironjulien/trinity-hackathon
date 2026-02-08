import React, { useEffect, useRef, useState, useMemo } from 'react';
import './julien-styles.css';
import { useTrinityStore } from '../../stores/trinityStore';
import enLocale from '../../locales/en.json';
import frLocale from '../../locales/fr.json';

// Locale map for dynamic loading
const LOCALES = { en: enLocale, fr: frLocale };

// DB_INTERRUPTIONS stays hardcoded (complex sequences)
const DB_INTERRUPTIONS = [
    [
        { msg: "⚠️ AGENT_DETECTED: Intrusion imminent.", type: "error", delay: 0 },
        { msg: "Blocking port 80... [FAILED]", type: "error", delay: 1000 },
        { msg: "Rerouting encryption keys...", type: "warning", delay: 2000 },
        { msg: "Access Denied. Nice try, Smith.", type: "success", delay: 3500 }
    ],
    [
        { msg: "⚠️ SYSTEM_ALERT: Coffee levels critical.", type: "warning", delay: 0 },
        { msg: "Initiating emergency brew protocol...", type: "info", delay: 1500 },
        { msg: "Pouring... ☕", type: "success", delay: 3000 }
    ],
    [
        { msg: "⚠️ GLITCH_IN_MATRIX: Dejà vu.", type: "special", delay: 0 },
        { msg: "Resetting reality simulation...", type: "info", delay: 2000 },
        { msg: "Reality v2.1 loaded.", type: "success", delay: 4000 }
    ]
];

function shuffleArray(array) {
    for (let i = array.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [array[i], array[j]] = [array[j], array[i]];
    }
}

export default function Terminal() {
    const listRef = useRef(null);
    const bottomRef = useRef(null);

    // SOTA 2026: i18n - Get locale from store
    const locale = useTrinityStore(state => state.locale);
    const localeData = useMemo(() => LOCALES[locale] || LOCALES.en, [locale]);

    // Build startup sequence with delays from locale data
    const STARTUP_SEQUENCE = useMemo(() => {
        const delays = [100, 800, 1500, 2400, 3200, 4500, 5200, 6500, 7800, 9000, 10500, 12000];
        return localeData.terminal.startup.map((item, i) => ({
            ...item,
            delay: delays[i] || (i * 1000)
        }));
    }, [localeData]);

    // Locale-aware data sources
    const DB_QUOTES = localeData.terminal.quotes;
    const DB_COMMANDS = localeData.terminal.commands;
    const DB_LOGS = localeData.terminal.logs;

    // State bags
    const bagQuotes = useRef([]);
    const bagCommands = useRef([]);
    const bagLogs = useRef([]);
    const bagInterruptions = useRef([]);

    // We keep logs in state to render
    const [logs, setLogs] = useState([]);

    const getNextItem = (bagRef, sourceDB) => {
        if (bagRef.current.length === 0) {
            bagRef.current = [...sourceDB];
            shuffleArray(bagRef.current);
        }
        return bagRef.current.pop();
    };

    const addLog = (msg, type = 'info') => {
        const time = new Date().toLocaleTimeString('fr-FR', { hour12: false });
        setLogs(prev => [...prev, { time, msg, type, id: Math.random() }]);
    };

    // Smart Auto-scroll
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

    // Scroll only if was already at bottom
    useEffect(() => {
        if (isAtBottomRef.current && bottomRef.current) {
            bottomRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [logs]);

    // Narrative Engine - Reset when locale changes
    useEffect(() => {
        let mounted = true;
        let timeoutId = null;
        const startupTimeouts = [];

        // Reset logs and bags when locale changes
        setLogs([]);
        bagQuotes.current = [];
        bagCommands.current = [];
        bagLogs.current = [];
        bagInterruptions.current = [];

        // Startup sequence
        STARTUP_SEQUENCE.forEach(item => {
            const tid = setTimeout(() => {
                if (mounted) addLog(item.msg, item.type);
            }, item.delay);
            startupTimeouts.push(tid);
        });

        // Loop
        const loop = () => {
            if (!mounted) return;
            const nextActionDelay = Math.random() * 2000 + 500;

            timeoutId = setTimeout(() => {
                const rand = Math.random();

                if (rand < 0.55) {
                    const msg = getNextItem(bagLogs, DB_LOGS);
                    addLog(msg, 'dim');
                    loop();
                } else if (rand < 0.80) {
                    const cmdObj = getNextItem(bagCommands, DB_COMMANDS);
                    addLog(`> ${cmdObj.cmd}`, 'info');
                    setTimeout(() => {
                        if (mounted) addLog(cmdObj.res, 'success');
                        loop();
                    }, 600);
                } else if (rand < 0.92) {
                    const quote = getNextItem(bagQuotes, DB_QUOTES);
                    addLog(`"${quote.text}"`, 'special');
                    setTimeout(() => {
                        if (mounted) addLog(`- ${quote.author}`, 'dim');
                        loop();
                    }, 1200);
                } else {
                    const seq = getNextItem(bagInterruptions, DB_INTERRUPTIONS);
                    let seqDelay = 0;
                    seq.forEach(item => {
                        setTimeout(() => {
                            if (mounted) addLog(item.msg, item.type);
                        }, item.delay);
                        seqDelay = Math.max(seqDelay, item.delay);
                    });

                    setTimeout(() => loop(), seqDelay + 4000);
                }
            }, nextActionDelay);
        };

        // Start loop after startup
        setTimeout(loop, 13000);

        return () => {
            mounted = false;
            if (timeoutId) clearTimeout(timeoutId);
            startupTimeouts.forEach(clearTimeout);
        };
    }, [locale, STARTUP_SEQUENCE, DB_QUOTES, DB_COMMANDS, DB_LOGS]);

    return (
        <div ref={listRef} className="c-terminal" style={{
            border: '2px solid #53fff4',
            boxShadow: 'inset 0 0 20px rgba(0, 0, 0, 0.8), 0 0 15px rgba(83, 255, 244, 0.3), 0 0 30px rgba(83, 255, 244, 0.15)'
        }}>
            {logs.map(log => (
                <div key={log.id} className={`term-line term-${log.type}`}>
                    <span className="term-time">[{log.time}]</span>
                    <span className="term-msg">{log.msg}</span>
                </div>
            ))}
            <div ref={bottomRef} />
        </div>
    );
}
