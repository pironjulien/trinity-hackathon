import React, { useEffect, useRef } from 'react';
import './LogTable.css'; // Reusing log table styles

const ROUTE_COLORS: Record<string, string> = {
    'GENIUS': '#FF00FF', // magenta
    'REFLEX': '#FFD600', // yellow
    'CREATE': '#00BCD4', // cyan
    'IMGFAST': '#00BCD4', // cyan
    'VOICE': '#448AFF', // blue
    'VOICEFAST': '#448AFF', // blue
    'VIDEO': '#00E676', // green
    'VIDFAST': '#00E676', // green
    'MEMORY': '#FFFFFF', // white
    'BULK': '#D500F9', // purple
    'COMMAND': '#FF9100', // orange
    'SEARCH': '#FF1744', // red
};

const getRouteColor = (route: string) => ROUTE_COLORS[route?.toUpperCase()] || '#fff';
const formatTime = (iso: string) => (iso && iso.includes('T')) ? iso.split('T')[1].split('.')[0] : iso;
const formatModel = (m: string) => (m || '').replace('gemini-', '').replace('-preview', '');

const TokensTable: React.FC<{ tokens: any[]; lang: 'EN' | 'FR' }> = ({ tokens, lang }) => {
    const containerRef = useRef<HTMLDivElement>(null);

    const dict = {
        EN: {
            time: "TIME",
            model: "MODEL",
            route: "ROUTE",
            key: "KEY",
            source: "SOURCE",
            in: "IN",
            out: "OUT",
            total: "TOTAL"
        },
        FR: {
            time: "HEURE",
            model: "MODÈLE",
            route: "ROUTE",
            key: "CLÉ",
            source: "SOURCE",
            in: "ENTRÉE",
            out: "SORTIE",
            total: "TOTAL"
        }
    };

    const t = dict[lang] || dict.EN;

    useEffect(() => {
        if (containerRef.current) {
            containerRef.current.scrollTop = containerRef.current.scrollHeight;
        }
    }, [tokens]);

    return (
        <div className="log-container" ref={containerRef}>
            <table>
                <thead>
                    <tr>
                        <th style={{ width: 80 }}>{t.time}</th>
                        <th style={{ width: 80 }}>{t.model}</th>
                        <th style={{ width: 80 }}>{t.route}</th>
                        <th style={{ width: 140 }}>{t.key}</th>
                        <th>{t.source}</th>
                        <th className="align-right" style={{ width: 60 }}>{t.in}</th>
                        <th className="align-right" style={{ width: 60 }}>{t.out}</th>
                        <th className="align-right" style={{ width: 70 }}>{t.total}</th>
                    </tr>
                </thead>
                <tbody>
                    {tokens.map((t, i) => (
                        <tr key={i}>
                            <td className="mono dimmed">{formatTime(t.timestamp || t.time)}</td>
                            <td>{formatModel(t.model)}</td>
                            <td className="bold" style={{ color: getRouteColor(t.route) }}>{t.route}</td>
                            <td className="dimmed">{t.key}</td>
                            <td className="dimmed">{t.source}</td>
                            <td className="align-right">{t.input_tokens || t.in || 0}</td>
                            <td className="align-right">{t.output_tokens || t.out || 0}</td>
                            <td className="align-right bold">{t.total_tokens || t.total || 0}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

export default TokensTable;
