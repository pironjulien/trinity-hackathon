import React, { useEffect, useRef } from 'react';
import { useTrinityStore } from '../lib/store';
import './LogTable.css';

const formatTime = (iso: string) => {
    if (!iso) return '00:00:00';
    if (iso.includes('T')) return iso.split('T')[1].split('.')[0];
    return iso;
};

const getLevelColor = (level: string) => {
    const l = (level || '').toUpperCase().trim();
    if (['ERROR', 'CRITICAL', 'FATAL'].includes(l)) return 'var(--trinity-red)';
    if (['WARNING', 'WARN'].includes(l)) return 'var(--trinity-yellow)';
    if (l === 'INFO') return 'var(--trinity-blue)';
    if (l === 'DEBUG') return '#666';
    return '#ccc';
};

const LogTable: React.FC<{ logs: any[] }> = ({ logs }) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const { lang } = useTrinityStore();

    const isAtBottom = useRef(true); // Default to true (pin to bottom on load)
    const prevLength = useRef(0);

    // Track user scroll behavior (SOTA 2026: Intention Preservation)
    const onScroll = (e: React.UIEvent<HTMLDivElement>) => {
        const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
        // User is "at bottom" if they are within 50px of the end
        // If they scroll up, this becomes false, and we stop auto-scrolling
        isAtBottom.current = Math.abs(scrollHeight - clientHeight - scrollTop) < 50;
    };

    useEffect(() => {
        // Only trigger scroll IF:
        // 1. We are pinned to the bottom (User wants latest)
        // 2. AND there are actually NEW logs (length increased)
        // This prevents re-renders (from other store updates) from forcing scroll
        if (isAtBottom.current && logs.length > prevLength.current) {
            if (containerRef.current) {
                containerRef.current.scrollTop = containerRef.current.scrollHeight;
            }
        }
        prevLength.current = logs.length;
    }, [logs]);

    const dict = {
        EN: {
            time: "TIME",
            level: "LEVEL",
            module: "MODULE",
            function: "FUNCTION",
            message: "MESSAGE"
        },
        FR: {
            time: "HEURE",
            level: "NIVEAU",
            module: "MODULE",
            function: "FONCTION",
            message: "MESSAGE"
        }
    };

    const t = dict[lang] || dict.EN;

    return (
        <div className="log-container" ref={containerRef} onScroll={onScroll}>
            <table>
                <thead>
                    <tr>
                        <th style={{ width: 75 }}>{t.time}</th>
                        <th style={{ width: 60 }}>{t.level}</th>
                        <th style={{ width: 220 }}>{t.module}</th>
                        <th style={{ width: 140 }}>{t.function}</th>
                        <th>{t.message}</th>
                    </tr>
                </thead>
                <tbody>
                    {logs.map((log, i) => (
                        <tr key={i}>
                            <td className="mono dimmed">
                                {typeof log === 'string' ? '???' : formatTime(log.timestamp)}
                            </td>
                            <td className="bold" style={{ color: getLevelColor(log.level) }}>
                                {log.level}
                            </td>
                            <td className="dimmed">{log.module}</td>
                            <td className="dimmed">{log.func || log.function}</td>
                            <td className="message-cell">
                                {log.message || (typeof log === 'string' ? log : JSON.stringify(log))}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

export default LogTable;
