import React from 'react';
import { useTrinityStore } from '../lib/store';
import { ArcGauge } from './ArcGauge';
import './StatsPanel.css';

const StatsPanel: React.FC = () => {
    const { stats, lang } = useTrinityStore();

    // Translation dictionary
    const dict = {
        EN: { cpuTitle: "CPU Details", ramTitle: "RAM Details", angel: "Angel", trinity: "Trinity", ubuntu: "Ubuntu", antigravity: "Antigravity", disk: "DISK", cpu: "CPU", ram: "RAM" },
        FR: { cpuTitle: "Détails CPU", ramTitle: "Détails RAM", angel: "Angel", trinity: "Trinity", ubuntu: "Ubuntu", antigravity: "Antigravity", disk: "DISQUE", cpu: "PROC", ram: "MEM" }
    };

    const t = dict[lang] || dict.EN;

    // Helper: Format CPU (0.45 -> 45, or 45 -> 45)
    const parseCpu = (val: string | number): number => {
        const floatVal = typeof val === 'string' ? parseFloat(val) : val;
        if (isNaN(floatVal)) return 0;
        return floatVal > 1.0 ? floatVal : floatVal * 100;
    };

    const cpuValue = parseCpu(stats.cpu);
    const b = stats.breakdown;

    return (
        <div className="stats-panel">
            {/* CPU GAUGE */}
            <div className={`cpu-container ${b ? 'has-tooltip' : ''}`}>
                <ArcGauge value={cpuValue} max={100} label={t.cpu} />

                {/* CPU TOOLTIP - All Processes */}
                {b && (
                    <div className="ram-tooltip">
                        <div className="tooltip-header">{t.cpuTitle}</div>
                        <div className="tooltip-row">
                            <span className="dot dot-angel"></span>
                            <span className="label">{t.angel}</span>
                            <span className="value">{b.angel?.cpu?.toFixed(0) || 0}%</span>
                        </div>
                        <div className="tooltip-row">
                            <span className="dot dot-trinity"></span>
                            <span className="label">{t.trinity}</span>
                            <span className="value">{b.trinity?.cpu?.toFixed(0) || 0}%</span>
                        </div>

                        <div className="tooltip-row">
                            <span className="dot dot-vscode"></span>
                            <span className="label">{t.ubuntu}</span>
                            <span className="value">{b.ubuntu?.cpu?.toFixed(0) || 0}%</span>
                        </div>

                        <div className="tooltip-row">
                            <span className="dot dot-vscode"></span>
                            <span className="label">{t.antigravity}</span>
                            <span className="value">{b.antigravity?.cpu?.toFixed(0) || 0}%</span>
                        </div>
                    </div>
                )}
            </div>

            {/* RAM GAUGE */}
            <div className={`cpu-container ${b ? 'has-tooltip' : ''}`}>
                <ArcGauge value={stats.ram} max={100} label={t.ram} />

                {/* RAM TOOLTIP - All Processes */}
                {b && (
                    <div className="ram-tooltip">
                        <div className="tooltip-header">{t.ramTitle}</div>
                        <div className="tooltip-row">
                            <span className="dot dot-angel"></span>
                            <span className="label">{t.angel}</span>
                            <span className="value">{b.angel?.ram || 0} MB</span>
                        </div>
                        <div className="tooltip-row">
                            <span className="dot dot-trinity"></span>
                            <span className="label">{t.trinity}</span>
                            <span className="value">{b.trinity?.ram || 0} MB</span>
                        </div>

                        <div className="tooltip-row">
                            <span className="dot dot-vscode"></span>
                            <span className="label">{t.ubuntu}</span>
                            <span className="value">{b.ubuntu?.ram || 0} MB</span>
                        </div>

                        <div className="tooltip-row">
                            <span className="dot dot-vscode"></span>
                            <span className="label">{t.antigravity}</span>
                            <span className="value">{b.antigravity?.ram || 0} MB</span>
                        </div>
                    </div>
                )}
            </div>

            {/* DISK GAUGE */}
            <div className="cpu-container">
                <ArcGauge value={stats.disk} max={100} label={t.disk} />
            </div>
        </div>
    );
};

export default StatsPanel;
