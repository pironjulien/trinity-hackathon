import React, { useMemo } from 'react';
import './ArcGauge.css';

interface ArcGaugeProps {
    value: number;
    max?: number;
    label: string;
    color?: string;
}

export const ArcGauge: React.FC<ArcGaugeProps> = ({ value, max = 100, label, color }) => {
    const percentage = Math.min(100, Math.max(0, (value / max) * 100));

    // SVG Arc calculations
    const radius = 40;
    const strokeWidth = 8;
    const circumference = Math.PI * radius; // Half circle

    const strokeDashoffset = circumference - (percentage / 100) * circumference;

    // Color based on value
    const gaugeColor = useMemo(() => {
        if (color) return color;
        if (percentage >= 80) return '#EA4335'; // Red
        if (percentage >= 60) return '#FBBC05'; // Yellow
        return '#34A853'; // Green
    }, [color, percentage]);

    return (
        <div className="arc-gauge">
            <svg viewBox="0 0 100 55" className="gauge-svg">
                {/* Background arc */}
                <path
                    className="arc-bg"
                    d="M 10 50 A 40 40 0 0 1 90 50"
                    fill="none"
                    strokeWidth={strokeWidth}
                />

                {/* Value arc (animated) */}
                <path
                    className="arc-value"
                    d="M 10 50 A 40 40 0 0 1 90 50"
                    fill="none"
                    stroke={gaugeColor}
                    strokeWidth={strokeWidth}
                    strokeDasharray={circumference}
                    strokeDashoffset={strokeDashoffset}
                    strokeLinecap="round"
                    style={{ filter: `drop-shadow(0 0 4px ${gaugeColor})` }}
                />

                {/* Percentage in center of arc */}
                <text
                    x="50"
                    y="48"
                    className="percent-text"
                    textAnchor="middle"
                    fill={gaugeColor}
                >{Math.round(percentage)}%</text>
            </svg>

            {/* Label below */}
            <div className="gauge-label">{label}</div>
        </div>
    );
};
