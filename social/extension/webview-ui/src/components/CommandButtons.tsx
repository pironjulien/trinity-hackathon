import React, { useState } from 'react';
import { useTrinity } from '../lib/useTrinity';
import { useTrinityStore } from '../lib/store';
import './CommandButtons.css';

export const CommandButtons: React.FC = () => {
    const { send } = useTrinity();
    const { status } = useTrinityStore();
    const [errorMsg, setErrorMsg] = useState<string | null>(null);

    // Angel Commands (Left Group)
    const angelCommands = [
        { id: 'ANGEL_GO', icon: '😇', label: 'GO', className: 'deploy', shortcut: 'Ctrl+A' },
        { id: 'ANGEL_STOP', icon: '🚫', label: 'STOP', className: 'stop', shortcut: 'Ctrl+Shift+A' }
    ];

    // Trinity Commands (Right Group)
    const trinityCommands = [
        { id: 'GO', icon: '🚀', label: 'GO', className: 'deploy', shortcut: 'Ctrl+G' },
        { id: 'STOP', icon: '🛑', label: 'STOP', className: 'stop', shortcut: 'Ctrl+Shift+S' }
    ];

    const handleCommand = (cmdId: string) => {
        // SOTA 2026: Trinity Safety Interlock
        // Angel is running if status is 'sleeping' or 'active'
        if (cmdId === 'GO') {
            const isAngelRunning = status === 'sleeping' || status === 'active';
            if (!isAngelRunning) {
                setErrorMsg("⚠️ Allumez Angel d'abord !");
                setTimeout(() => setErrorMsg(null), 3000);
                return;
            }
        }

        setErrorMsg(null);
        send(cmdId);
    };

    return (
        <div className="commands-container-wrapper" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '100%' }}>

            {errorMsg && (
                <div className="security-alert" style={{
                    color: '#ff4444',
                    fontWeight: 'bold',
                    marginBottom: '8px',
                    fontSize: '12px',
                    animation: 'pulse 1s infinite'
                }}>
                    {errorMsg}
                </div>
            )}

            <div className="commands-container">
                {/* Angel Group */}
                <div className="command-group">
                    <div className="group-header">Angel</div>
                    <div className="buttons-row">
                        {angelCommands.map(cmd => (
                            <button
                                key={cmd.id}
                                className={`cmd-btn ${cmd.className}`}
                                title={`${cmd.label} (${cmd.shortcut})`}
                                onClick={() => handleCommand(cmd.id)}
                            >
                                <span className="cmd-icon">{cmd.icon}</span>
                                <span className="cmd-label">{cmd.label}</span>
                            </button>
                        ))}
                    </div>
                </div>

                {/* Trinity Group */}
                <div className="command-group">
                    <div className="group-header">Trinity</div>
                    <div className="buttons-row">
                        {trinityCommands.map(cmd => (
                            <button
                                key={cmd.id}
                                className={`cmd-btn ${cmd.className} ${cmd.id === 'GO' && status === 'active' ? 'is-active' : ''}`}
                                title={`${cmd.label} (${cmd.shortcut})`}
                                onClick={() => handleCommand(cmd.id)}
                            >
                                <span className="cmd-icon">{cmd.icon}</span>
                                <span className="cmd-label">{cmd.label}</span>
                            </button>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

