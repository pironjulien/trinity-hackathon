import React from 'react';

const TokensTable = ({ tokens }) => {
    // Shorten model name (gemini-3-pro-preview -> 3-pro)
    const shortModel = (model) => {
        if (!model) return '?';
        return model.replace('gemini-', '').replace('-preview', '');
    };

    return (
        <div className="w-full h-full overflow-auto font-mono text-xs select-text">
            <table className="w-full text-left border-collapse">
                <thead className="sticky top-0 bg-black/80 backdrop-blur-md z-10 text-white/50 uppercase tracking-wider text-[10px]">
                    <tr>
                        <th className="p-2 border-b border-white/10 w-20">Time</th>
                        <th className="p-2 border-b border-white/10 w-20">Model</th>
                        <th className="p-2 border-b border-white/10 w-16">Route</th>
                        <th className="p-2 border-b border-white/10">Key</th>
                        <th className="p-2 border-b border-white/10">Source</th>
                        <th className="p-2 border-b border-white/10 text-right w-16">In</th>
                        <th className="p-2 border-b border-white/10 text-right w-16">Out</th>
                        <th className="p-2 border-b border-white/10 text-right w-16">Total</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                    {tokens.slice().reverse().map((t, i) => (
                        <tr key={i} className="hover:bg-white/5 transition-colors">
                            <td className="p-2 text-white/40">
                                {new Date(t.timestamp).toLocaleTimeString()}
                            </td>
                            <td className="p-2 text-cyan-400 font-bold">
                                {shortModel(t.model)}
                            </td>
                            <td className="p-2 text-yellow-400 font-bold">
                                {t.route || '–'}
                            </td>
                            <td className="p-2 text-white/50 truncate max-w-32">
                                {t.key || '–'}
                            </td>
                            <td className="p-2 text-white/40 truncate max-w-40">
                                {t.source || '–'}
                            </td>
                            <td className="p-2 text-right text-white/60">
                                {t.in ?? t.inputTokens}
                            </td>
                            <td className="p-2 text-right text-white/60">
                                {t.out ?? t.outputTokens}
                            </td>
                            <td className="p-2 text-right text-green-400 font-bold">
                                {t.total ?? t.totalTokens}
                            </td>
                        </tr>
                    ))}
                    {tokens.length === 0 && (
                        <tr>
                            <td colSpan={8} className="p-8 text-center text-white/20 italic">
                                NO TOKEN USAGE
                            </td>
                        </tr>
                    )}
                </tbody>
            </table>
        </div>
    );
};

export default TokensTable;
