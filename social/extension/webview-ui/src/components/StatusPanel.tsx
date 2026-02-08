import React from 'react';
import { useTrinityStore } from '../lib/store';
import './StatusPanel.css';

const StatusPanel: React.FC = () => {
    // SOTA 2026: Use jobLastLogTS for reactive blinking instead of jobActivity
    const { status, jobs, jobLastLogTS, lang } = useTrinityStore();
    const [flashTrinity, setFlashTrinity] = React.useState(false);
    const [flashJobs, setFlashJobs] = React.useState(false);

    // Watch for activity to trigger flashes (Activity Monitor)
    React.useEffect(() => {
        const t1 = jobLastLogTS.trader;
        const t2 = jobLastLogTS.youtuber;
        const t3 = jobLastLogTS.influencer;

        // If any timestamp is recent/updated, trigger flash
        if (t1 > 0 || t2 > 0 || t3 > 0) {
            setFlashTrinity(true);
            setFlashJobs(true);

            // Auto-reset flash after 200ms
            const timer = setTimeout(() => {
                setFlashTrinity(false);
                setFlashJobs(false);
            }, 200);
            return () => clearTimeout(timer);
        }
    }, [jobLastLogTS.trader, jobLastLogTS.youtuber, jobLastLogTS.influencer]);

    const dict = {
        EN: {
            status: "STATUS",
            jobs: "JOBS"
        },
        FR: {
            status: "STATUT",
            jobs: "TÂCHES"
        }
    };

    const t = dict[lang] || dict.EN;

    const isActive = status === 'active';
    const isContainerActive = status === 'active' || status === 'sleeping';
    const hasWork = jobs.trader || jobs.youtuber || jobs.influencer;

    return (
        <div className="status-panel trinity-card">
            <div className="panel-header">{t.status}</div>
            <div className="status-list">
                {/* Container Status */}
                <div className="status-row">
                    <span className={`status-dot ${isContainerActive ? 'active' : ''}`} />
                    <span className="status-label">ANGEL</span>
                </div>

                {/* Trinity Core */}
                <div className="status-row">
                    <span
                        className={`status-dot green ${isActive ? 'active' : ''} ${flashTrinity ? 'flash' : ''}`}
                    />
                    <span className="status-label">TRINITY</span>
                </div>

                {/* Jobs Status */}
                <div className="status-row">
                    <span
                        className={`status-dot green ${hasWork ? 'active' : ''} ${flashJobs ? 'flash' : ''}`}
                    />
                    <span className="status-label">{t.jobs}</span>
                </div>
            </div>
        </div>
    );
};

export default StatusPanel;
