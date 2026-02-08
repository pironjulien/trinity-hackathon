import React from 'react';
import { useTrinityStore } from '../lib/store';
import './JobsPanel.css';

const JobsPanel: React.FC = () => {
    const { jobs, lang } = useTrinityStore();

    const jobList = [
        { id: 'trader', label: 'TRADER' },
        { id: 'youtuber', label: 'YOUTUBER' },
        { id: 'influencer', label: 'INFLUENCER' }
    ] as const;

    // Translation dictionary
    const dict = {
        EN: {
            title: "JOBS",
            trader: "TRADER",
            youtuber: "YOUTUBER",
            influencer: "INFLUENCER"
        },
        FR: {
            title: "TÂCHES",
            trader: "TRADEUR",
            youtuber: "YOUTUBEUR",
            influencer: "INFLUENCEUR"
        }
    };

    const t = dict[lang] || dict.EN;

    return (
        <div className="jobs-panel trinity-card">
            <div className="panel-header">{t.title}</div>
            <div className="jobs-list">
                {jobList.map(job => (
                    <JobRow
                        key={job.id}
                        id={job.id}
                        label={t[job.id as keyof typeof t]}
                        isActive={jobs[job.id]}
                    />
                ))}
            </div>
        </div>
    );
};

// Extracted Row Component to handle individual flashing without re-rendering everything
const JobRow: React.FC<{ id: 'trader' | 'youtuber' | 'influencer'; label: string; isActive: boolean }> = ({ id, label, isActive }) => {
    const lastTS = useTrinityStore(s => s.jobLastLogTS[id]);
    const [flashing, setFlashing] = React.useState(false);

    // Trigger flash when timestamp updates
    React.useEffect(() => {
        if (lastTS > 0) {
            setFlashing(true);
            const timer = setTimeout(() => setFlashing(false), 200); // Short flash
            return () => clearTimeout(timer);
        }
    }, [lastTS]);

    return (
        <div className="job-row">
            <span className={`job-dot ${isActive ? 'active' : ''} ${flashing ? 'flash' : ''}`} />
            <span className="job-label">{label}</span>
        </div>
    );
};

export default JobsPanel;
