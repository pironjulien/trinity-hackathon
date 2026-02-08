import React from 'react';
import { RefreshCw, AlertTriangle, HelpCircle, Save } from 'lucide-react';
import { useHydration } from '../../stores/trinityStore'; // SOTA 2026 Standard 362.80.6

/**
 * SOTA 2026: PanelKit - Shared components for all dashboard panels
 * Usage: import { Row2, ProgressBar, ActionButtons, Section } from './PanelKit';
 */

// Two-column row for displaying key-value pairs
export const Row2 = ({ left, right }) => (
    <div className="grid grid-cols-2 gap-4 text-sm">
        <div className="flex justify-between items-center">
            <span className="text-white/50">{left.label}</span>
            {left.bar !== undefined ? (
                <ProgressBar value={left.bar} max={left.max} color={left.color} />
            ) : (
                <span className={left.color || 'text-white/70'}>{left.value}</span>
            )}
        </div>
        {right && (
            <div className="flex justify-between items-center">
                <span className="text-white/50">{right.label}</span>
                {right.bar !== undefined ? (
                    <ProgressBar value={right.bar} max={right.max} color={right.color} />
                ) : (
                    <span className={right.color || 'text-white/70'}>{right.value}</span>
                )}
            </div>
        )}
    </div>
);

// Progress bar with value display
export const ProgressBar = ({ value, max = 100, color = 'bg-cyan-500' }) => {
    const percentage = max > 0 ? Math.min(100, (value / max) * 100) : 0;
    return (
        <div className="flex items-center gap-2 w-28">
            <div className="flex-1 h-1.5 bg-white/10 rounded-full overflow-hidden">
                <div className={`h-full ${color} transition-all`}
                    style={{ width: `${percentage}%` }} />
            </div>
            <span className="text-white/70 text-sm w-10 text-right">
                {max === 100 ? `${value.toFixed(0)}%` : `${value}/${max}`}
            </span>
        </div>
    );
};

// Section wrapper with icon and title
export const Section = ({ title, icon: Icon, color = 'text-cyan-400', border = 'border-white/10', headerRight, children }) => (
    <section className={`bg-black/30 border ${border} rounded-lg p-3`}>
        <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-bold text-white/80 flex items-center gap-1.5">
                {Icon && <Icon size={14} className={color} />}
                {title}
            </h3>
            {headerRight}
        </div>
        {children}
    </section>
);

// Dual action buttons (Refresh + Apply)
export const ActionButtons = ({
    onRefresh,
    onApply,
    isRefreshing = false,
    isApplying = false,
    refreshLabel = 'REFRESH',
    refreshingLabel = 'REFRESHING...',
    applyLabel = 'APPLY',
    applyingLabel = 'APPLYING...',
    showApply = true
}) => {
    // EXACT TRADER STYLE: from-cyan-500 to-pink-500 with hover
    const btnClass = `w-full py-3 rounded-lg font-bold text-sm bg-gradient-to-r from-cyan-500 to-pink-500 text-white hover:from-cyan-400 hover:to-pink-400 disabled:opacity-50 transition-all shadow-[0_0_15px_rgba(6,182,212,0.3)] flex items-center justify-center gap-2`;

    return (
        <div className={`grid ${showApply ? 'grid-cols-2' : 'grid-cols-1'} gap-4`}>
            <button onClick={onRefresh} disabled={isRefreshing} className={btnClass}>
                <RefreshCw size={16} className={isRefreshing ? 'animate-spin' : ''} />
                {isRefreshing ? refreshingLabel : refreshLabel}
            </button>
            {showApply && (
                <button onClick={onApply} disabled={isApplying} className={btnClass}>
                    {isApplying ? (
                        <><RefreshCw className="animate-spin" size={16} />{applyingLabel}</>
                    ) : (
                        <><Save size={16} /> {applyLabel}</>
                    )}
                </button>
            )}
        </div>
    );
};


// Toggle option button with optional tooltip (SOTA 2026: Harmonized with TraderPanel)
export const OptionToggle = ({
    icon: Icon,
    label,
    value,
    onChange,
    activeColor = 'pink',
    tooltip = null,
    isTooltipActive = false,
    onTooltipEnter = () => { },
    onTooltipLeave = () => { }
}) => {
    const colors = {
        pink: 'border-pink-500 bg-pink-500/20 text-pink-400',
        cyan: 'border-cyan-500 bg-cyan-500/20 text-cyan-400',
        purple: 'border-purple-500 bg-purple-500/20 text-purple-400',
        amber: 'border-amber-500 bg-amber-500/20 text-amber-400',
        red: 'border-red-500 bg-red-500/20 text-red-400',
        yellow: 'border-yellow-500 bg-yellow-500/20 text-yellow-400',
        green: 'border-green-500 bg-green-500/20 text-green-400',
        violet: 'border-violet-500 bg-violet-500/20 text-violet-400',
        rose: 'border-rose-500 bg-rose-500/20 text-rose-400',
        orange: 'border-orange-500 bg-orange-500/20 text-orange-400',
        blue: 'border-blue-500 bg-blue-500/20 text-blue-400',
        indigo: 'border-indigo-500 bg-indigo-500/20 text-indigo-400',
    };
    return (
        <button
            onClick={() => onChange(!value)}
            className={`relative w-full flex items-center justify-between gap-2 px-3 py-2 rounded border transition-all text-sm ${value ? colors[activeColor] : 'border-white/10 text-white/50 hover:border-white/30'}`}
        >
            <span className="flex items-center gap-2 overflow-hidden">
                {Icon && <Icon size={14} className="shrink-0" />}
                <span className="font-medium truncate">{label}</span>
                {tooltip && (
                    <span
                        className="text-white/30 hover:text-cyan-400 transition-colors shrink-0"
                        onMouseEnter={(e) => { e.stopPropagation(); onTooltipEnter(tooltip); }}
                        onMouseLeave={onTooltipLeave}
                    >
                        <HelpCircle size={12} />
                    </span>
                )}
            </span>
            <span className={`text-xs font-bold shrink-0 ${value ? 'text-green-400' : 'text-red-400/60'}`}>
                {value ? 'ON' : 'OFF'}
            </span>
            {isTooltipActive && tooltip && (
                <div className="absolute left-0 top-full mt-1 z-50 bg-black/95 border border-cyan-500/50 rounded-lg p-3 text-sm text-white/90 w-64 shadow-xl text-left">
                    {tooltip}
                </div>
            )}
        </button>
    );
};

// Panel wrapper with scrollable content and sticky footer
// SOTA 2026 Standard 362.80.6: Waits for Zustand hydration before rendering content
export const PanelLayout = ({ children, footer, isWaitingForData = false, waitingLabel = 'WAITING FOR DATA...', isError = false, onRetry }) => {
    // SOTA 2026: Wait for store hydration before showing content
    const hydrated = useHydration();

    // SOTA 2026 Standard 362.80.6: Show loading ONLY if:
    // 1. Store is not yet hydrated (first load) - show "LOADING CACHE..."
    // 2. Panel explicitly says it's waiting AND store is hydrated (no cache exists)
    const showWaiting = !hydrated || isWaitingForData;
    const loadingLabel = !hydrated ? 'LOADING CACHE...' : waitingLabel;

    return (
        <div className="flex flex-col h-full text-sm relative">
            <div className="flex-1 overflow-y-auto p-4 pb-0">
                {children}
            </div>

            {isError && (
                <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-black/80 backdrop-blur-sm">
                    <div className="bg-red-500/10 p-6 rounded-2xl border border-red-500/50 flex flex-col items-center gap-4 max-w-xs text-center shadow-[0_0_30px_rgba(239,68,68,0.2)]">
                        <AlertTriangle size={48} className="text-red-500 mb-2 animate-bounce" />
                        <div>
                            <h3 className="text-red-400 font-bold text-lg tracking-widest mb-1">CONNECTION FAILED</h3>
                            <p className="text-white/50 text-xs">Unable to reach Angel Core.</p>
                        </div>
                        <button
                            onClick={onRetry}
                            className="px-6 py-2 bg-red-500 hover:bg-red-400 text-white font-bold rounded-lg transition-all shadow-lg hover:shadow-red-500/20 active:scale-95 flex items-center gap-2"
                        >
                            <RefreshCw size={16} /> RETRY
                        </button>
                    </div>
                </div>
            )}

            {showWaiting && !isError && (
                <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-black/60 backdrop-blur-sm">
                    <RefreshCw size={48} className="text-cyan-500 animate-spin mb-4" />
                    <h3 className="text-cyan-400 font-bold text-lg tracking-widest animate-pulse">{loadingLabel}</h3>
                </div>
            )}

            {footer && (
                <div className="shrink-0 p-4 pt-3">
                    {footer}
                </div>
            )}
        </div>
    );
};

// Responsive Grid (Mobile First)
// 1 Col (Mobile) -> 2 Cols (LG/Tablet) -> 3 Cols (2XL/Desktop)
export const ResponsiveGrid = ({ children, className = '' }) => (
    <div className={`grid grid-cols-1 lg:grid-cols-2 2xl:grid-cols-3 gap-4 transition-all duration-500 ${className}`}>
        {children}
    </div>
);

// Adaptive Card (Auto height on mobile, flex on desktop)
export const AdaptiveCard = ({ children, className = '' }) => (
    <section className={`bg-black/30 border border-white/10 rounded-lg p-3 flex flex-col min-h-[150px] lg:min-h-0 2xl:min-h-[150px] 2xl:flex-1 ${className}`}>
        {children}
    </section>
);

// LEAGCY: Three-column grid (Deprecated, use ResponsiveGrid)
export const Grid3 = ({ children }) => (
    <ResponsiveGrid>{children}</ResponsiveGrid>
);

// Column wrapper
export const Column = ({ children, className = '' }) => (
    <div className={`flex flex-col gap-3 ${className}`}>
        {children}
    </div>
);

// Tab Bar (SOTA 2026: Harmonized Tab Component)
export const TabBar = ({ tabs, activeTab, onChange, size = 'sm' }) => {
    const sizeClasses = {
        xs: 'px-2 py-1 text-[9px]',
        sm: 'px-3 py-1.5 text-[10px]',
        md: 'px-4 py-2 text-xs',
    };
    return (
        <div className="flex items-center gap-1 overflow-x-auto no-scrollbar">
            {tabs.map(tab => {
                const isActive = activeTab === (tab.id || tab);
                const Icon = tab.icon;
                const label = tab.label || tab;
                const color = tab.color || 'text-cyan-400';
                return (
                    <button
                        key={tab.id || tab}
                        onClick={() => onChange(tab.id || tab)}
                        className={`
                            flex items-center gap-2 rounded font-bold tracking-wider transition-all whitespace-nowrap
                            ${sizeClasses[size]}
                            ${isActive
                                ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 shadow-[0_0_10px_rgba(34,211,238,0.2)]'
                                : 'text-white/40 hover:text-white/80 hover:bg-white/5 border border-transparent'}
                        `}
                    >
                        {Icon && <Icon size={size === 'xs' ? 10 : size === 'sm' ? 12 : 14} className={isActive ? color : ''} />}
                        {label}
                    </button>
                );
            })}
        </div>
    );
};
