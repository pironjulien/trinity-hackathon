import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Target, Trophy, Lock, CheckCircle, Zap, Activity, TrendingUp, Shield, Flame } from 'lucide-react';
import { ANGEL_BASE_URL, getTrinityHeaders } from '../../services/angelService';
import { PanelLayout, TabBar, ActionButtons } from '../ui/PanelKit';

/**
 * OBJECTIVES PANEL (SOTA 2026)
 * Gamification & Quest System.
 */

const ICONS = {
    Target, Trophy, Lock, CheckCircle, Zap, Activity, TrendingUp, Shield, Flame
};

export default function ObjectivesPanel() {
    const [objectives, setObjectives] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);
    const [isRefreshing, setIsRefreshing] = useState(false);

    const fetchObjectives = useCallback(async () => {
        try {
            const res = await fetch(`${ANGEL_BASE_URL}/api/objectives`, {
                headers: getTrinityHeaders()
            });
            if (res.ok) {
                const data = await res.json();
                setObjectives(data);
                setError(false);
            } else {
                setError(true);
            }
        } catch (e) {
            console.error("Objectives Sync Error:", e);
            setError(true);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        // SOTA 2026: Harmonized timing - 3s initial delay + 180s polling (Standard 350)
        const timer = setTimeout(() => {
            fetchObjectives();
        }, 3000);
        const interval = setInterval(fetchObjectives, 180000); // 3 min polling
        return () => {
            clearTimeout(timer);
            clearInterval(interval);
        };
    }, [fetchObjectives]);

    // Manual Refresh
    const handleRefresh = async () => {
        setIsRefreshing(true);
        try {
            await fetchObjectives();
        } finally {
            setIsRefreshing(false);
        }
    };

    // Tabs Control
    // Tabs Control
    const DOMAINS = ['TRINITY', 'TRADER', 'INFLUENCER', 'YOUTUBE'];
    const [activeTab, setActiveTab] = useState('TRINITY');

    const filteredObjectives = useMemo(() => {
        return objectives.filter(obj => obj.domain === (activeTab === 'YOUTUBE' ? 'YOUTUBE' : activeTab));
    }, [activeTab, objectives]);

    // Grouping
    const grouped = filteredObjectives.reduce((acc, obj) => {
        if (!acc[obj.domain]) acc[obj.domain] = [];
        acc[obj.domain].push(obj);
        return acc;
    }, {});

    // Sort: Active first (closest to target), then Completed, then Locked
    Object.keys(grouped).forEach(domain => {
        grouped[domain].sort((a, b) => {
            if (a.status === 'COMPLETED' && b.status !== 'COMPLETED') return 1;
            if (a.status !== 'COMPLETED' && b.status === 'COMPLETED') return -1;
            // Percent done descending
            const pA = (a.current_value / a.target_value);
            const pB = (b.current_value / b.target_value);
            return pB - pA;
        });
    });

    const ObjectiveCard = ({ obj }) => {
        // ... existing ObjectiveCard code ...
        const Icon = ICONS[obj.icon] || Target;
        const isCompleted = obj.status === 'COMPLETED';
        const progress = Math.min(100, Math.max(0, (obj.current_value / obj.target_value) * 100));

        return (
            <div className={`
                relative overflow-hidden rounded-lg p-3 border transform transition-all duration-300
                ${isCompleted
                    ? 'bg-gradient-to-br from-green-900/40 to-emerald-900/10 border-green-500/30'
                    : 'bg-black/40 border-white/5 hover:border-white/10'}
            `}>
                {/* Background Progress Bar (Subtle) for Active */}
                {!isCompleted && (
                    <div
                        className="absolute bottom-0 left-0 h-0.5 bg-cyan-500/50 transition-all duration-1000"
                        style={{ width: `${progress}%` }}
                    />
                )}

                <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3">
                        <div className={`p-2 rounded-lg ${isCompleted ? 'bg-green-500 text-black' : 'bg-white/5 text-white/70'}`}>
                            {isCompleted ? <CheckCircle size={18} /> : <Icon size={18} />}
                        </div>
                        <div>
                            <h4 className={`text-xs font-bold uppercase tracking-wide ${isCompleted ? 'text-green-400' : 'text-white/90'}`}>
                                {obj.title}
                            </h4>
                            <p className="text-[10px] text-white/50 mt-0.5 leading-relaxed">
                                {obj.description}
                            </p>

                            {/* Progress Stats */}
                            <div className="mt-2 flex items-center gap-2 text-[10px] font-mono">
                                <span className={isCompleted ? 'text-green-400' : 'text-cyan-400 font-bold'}>
                                    {obj.current_value.toFixed(obj.unit === '€' ? 2 : 0)}{obj.unit}
                                </span>
                                <span className="text-white/30">/</span>
                                <span className="text-white/30">{obj.target_value}{obj.unit}</span>
                            </div>
                        </div>
                    </div>

                    {/* Reward Badge */}
                    <div className="flex flex-col items-end gap-1">
                        <div className={`
                            text-[9px] font-bold px-1.5 py-0.5 rounded border
                            ${obj.reward_type === 'dopamine'
                                ? 'border-yellow-500/30 text-yellow-500 bg-yellow-500/10'
                                : 'border-cyan-500/30 text-cyan-500 bg-cyan-500/10'}
                         `}>
                            +{obj.reward_amount} {obj.reward_type === 'dopamine' ? 'DOPA' : 'SERO'}
                        </div>
                    </div>
                </div>
            </div>
        );
    };

    return (
        <PanelLayout
            headerTitle="QUEST LOG"
            isWaitingForData={loading}
            isError={error}
            onRetry={fetchObjectives}
            footer={
                <ActionButtons
                    onRefresh={handleRefresh}
                    isRefreshing={isRefreshing}
                    showApply={false}
                />
            }
        >
            <div className="flex flex-col h-full">
                {/* TABS */}
                <div className="flex items-center gap-1 p-2 border-b border-white/5 bg-black/20 overflow-x-auto no-scrollbar">
                    <TabBar
                        tabs={DOMAINS}
                        activeTab={activeTab}
                        onChange={setActiveTab}
                        size="sm"
                    />
                </div>

                <div className="flex-1 overflow-y-auto p-2 space-y-4 custom-scrollbar">
                    {Object.entries(grouped).map(([domain, objs]) => (
                        <div key={domain} className="flex flex-col gap-3">
                            <div className="flex items-center gap-2 px-1">
                                <span className="text-[10px] font-bold text-white/30 uppercase tracking-[0.2em]">{domain}</span>
                                <div className="h-px flex-1 bg-white/5" />
                                <span className="text-[9px] text-white/20 font-mono">{objs.filter(o => o.status === 'COMPLETED').length}/{objs.length}</span>
                            </div>
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                                {objs.map((obj) => (
                                    <ObjectiveCard key={obj.id} obj={obj} />
                                ))}
                            </div>
                        </div>
                    ))}

                    {filteredObjectives.length === 0 && !loading && (
                        <div className="text-center py-20 text-white/20 text-xs italic">
                            No active quests in this domain.
                        </div>
                    )}
                </div>
            </div>
        </PanelLayout>
    );
}
