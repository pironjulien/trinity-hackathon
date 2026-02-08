import React from 'react';

const LogTable = ({ logs }) => {
    // SOTA 2026: Logs are pre-filtered by ConsolePanel, just display them

    return (
        <div className="w-full h-full overflow-auto font-mono text-xs select-text">
            <table className="w-full text-left border-collapse">
                <thead className="sticky top-0 bg-black/80 backdrop-blur-md z-10 text-white/50 uppercase tracking-wider text-[10px]">
                    <tr>
                        <th className="p-2 border-b border-white/10 w-[8%] min-w-[90px]">Time</th>
                        <th className="p-2 border-b border-white/10 w-[7%] min-w-[70px]">Level</th>
                        <th className="p-2 border-b border-white/10 w-[20%]">Module</th>
                        <th className="p-2 border-b border-white/10 w-[20%]">Function</th>
                        <th className="p-2 border-b border-white/10 w-auto">Message</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                    {logs.slice().reverse().map((log, i) => (
                        <tr key={i} className="hover:bg-white/5 transition-colors">
                            <td className="p-2 text-white/40 font-mono whitespace-nowrap">
                                {new Date(log.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                            </td>
                            <td className="p-2 font-bold">
                                <span className={`
                                    ${log.type === 'ERR' ? 'text-red-500' :
                                        log.type === 'WARN' ? 'text-yellow-500' :
                                            log.type === 'SYS' ? 'text-cyan-500' :
                                                log.type === 'AI' ? 'text-purple-500' :
                                                    'text-blue-400'}
                                `}>
                                    {log.type}
                                </span>
                            </td>
                            <td className="p-2 text-white/50 font-mono whitespace-nowrap overflow-hidden text-ellipsis">
                                {log.module || '-'}
                            </td>
                            <td className="p-2 text-white/50 font-mono whitespace-nowrap overflow-hidden text-ellipsis" title={log.function || log.func}>
                                {log.function || log.func || '-'}
                            </td>
                            <td className="p-2 text-white/80 whitespace-pre-wrap break-words font-mono leading-relaxed">
                                {log.message || log.msg || ''}
                            </td>
                        </tr>
                    ))}
                    {logs.length === 0 && (
                        <tr>
                            <td colSpan={5} className="p-8 text-center text-white/20 italic">
                                WAITING FOR SIGNAL...
                            </td>
                        </tr>
                    )}
                </tbody>
            </table>
        </div>
    );
};

export default LogTable;
