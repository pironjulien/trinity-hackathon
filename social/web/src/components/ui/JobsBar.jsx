import React, { useState, useMemo } from 'react';
import { useTrinityStore } from '../../stores/trinityStore';
import { toggleJob as apiToggleJob } from '../../services/angelService';
import { Briefcase, ChevronDown } from 'lucide-react';
import enLocale from '../../locales/en.json';
import frLocale from '../../locales/fr.json';

const LOCALES = { en: enLocale, fr: frLocale };

/**
 * SOTA 2026: JobsBar - Redesigned with CyberWindow style
 * - Header row with indicator + title (h-12) - CLICKABLE TO COLLAPSE
 * - Content area with job toggles (collapsible)
 * - Toggle switches for TRADER, INFLUENCER, YOUTUBER
 */
export default function JobsBar() {
    const jobsStatus = useTrinityStore(state => state.jobsStatus);
    const setJobStatus = useTrinityStore(state => state.setJobStatus);
    const locale = useTrinityStore(state => state.locale);
    const [isCollapsed, setIsCollapsed] = useState(true);

    const t = useMemo(() => LOCALES[locale]?.hud || LOCALES.en.hud, [locale]);

    const jobs = [
        { id: 'trader', labelKey: 'trader', color: 'cyan' },
        { id: 'influencer', labelKey: 'influencer', color: 'pink' },
        { id: 'youtuber', labelKey: 'youtuber', color: 'purple' }
    ];

    const toggleJob = async (jobId) => {
        const newState = !jobsStatus[jobId];
        // Optimistic update
        setJobStatus(jobId, newState);
        // Sync to Angel API
        const success = await apiToggleJob(jobId, newState);
        if (!success) {
            // Rollback on failure
            setJobStatus(jobId, !newState);
            console.error(`[JobsBar] Failed to toggle ${jobId}`);
        }
    };

    // Check if any job is active
    const hasActiveJob = Object.values(jobsStatus).some(v => v);

    return (
        <div className="flex flex-col
                        bg-glass border border-white/10 
                        backdrop-blur-xl rounded-lg overflow-hidden
                        shadow-[0_0_15px_rgba(0,0,0,0.5)]
                        group w-full">

            {/* HEADER - CyberWindow style - CLICKABLE */}
            <div
                className="flex items-center justify-between px-4 h-12 bg-black/40 border-b border-white/5 shrink-0 cursor-pointer hover:bg-black/50 transition-colors"
                onClick={() => setIsCollapsed(!isCollapsed)}
            >
                <div className="flex items-center gap-3">
                    {/* Activity Indicator */}
                    <div className={`w-2 h-2 rounded-full transition-all duration-300 ${hasActiveJob ? 'bg-green-500' : 'bg-white/20'}`} />
                    <h3 className="text-sm font-bold tracking-widest text-white/90 group-hover:text-neon-blue transition-colors">
                        {t.jobs}
                    </h3>
                </div>
                <ChevronDown
                    size={16}
                    className={`text-white/50 transition-transform duration-300 ${isCollapsed ? '-rotate-90' : ''}`}
                />
            </div>

            {/* CONTENT - Collapsible */}
            {!isCollapsed && (
                <div className="p-3 space-y-2">
                    {jobs.map(job => {
                        const isActive = jobsStatus[job.id];
                        const colorClasses = {
                            cyan: {
                                active: 'bg-cyan-500 shadow-[0_0_10px_rgba(6,182,212,0.5)]',
                                track: 'bg-cyan-500/30',
                                text: 'text-cyan-400'
                            },
                            pink: {
                                active: 'bg-pink-500 shadow-[0_0_10px_rgba(236,72,153,0.5)]',
                                track: 'bg-pink-500/30',
                                text: 'text-pink-400'
                            },
                            purple: {
                                active: 'bg-purple-500 shadow-[0_0_10px_rgba(168,85,247,0.5)]',
                                track: 'bg-purple-500/30',
                                text: 'text-purple-400'
                            }
                        }[job.color];

                        const neonClass = {
                            cyan: 'btn-neon-primary',
                            pink: 'btn-neon-pink',
                            purple: 'btn-neon-purple'
                        }[job.color];

                        return (
                            <div
                                key={job.id}
                                className="flex items-center justify-between px-3 py-2 
                                       bg-black/30 border border-white/10 rounded-md
                                       hover:bg-white/5 transition-all duration-300"
                            >
                                {/* Job Label */}
                                <span className={`text-xs font-bold tracking-wider transition-all duration-300 ${isActive ? colorClasses.text : 'text-white/40'}`}>
                                    {t[job.labelKey]}
                                </span>

                                {/* Toggle Switch */}
                                <button
                                    onClick={() => toggleJob(job.id)}
                                    className={`relative w-10 h-5 rounded-full transition-all duration-300 
                                           ${isActive ? `${neonClass} border-transparent` : 'bg-white/10'}`}
                                    title={`Toggle ${t[job.labelKey]}`}
                                >
                                    {/* Switch Knob */}
                                    <div className={`absolute top-0.5 w-4 h-4 rounded-full transition-all duration-300
                                                ${isActive
                                            ? `right-0.5 ${colorClasses.active} shadow-none`
                                            : 'left-0.5 bg-white/40'}`}
                                    />
                                </button>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
