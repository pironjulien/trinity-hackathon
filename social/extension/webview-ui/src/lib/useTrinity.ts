import { useEffect, useCallback } from 'react';
import { useTrinityStore } from './store';

// VS Code API declaration
declare global {
    interface Window {
        acquireVsCodeApi: () => {
            postMessage: (message: any) => void;
            getState: () => any;
            setState: (state: any) => void;
        };
    }
}

// Singleton for VS Code API
const vscode = typeof window !== 'undefined' && window.acquireVsCodeApi ? window.acquireVsCodeApi() : null;

export function useTrinity() {
    // OPTIMIZATION: Do not subscribe to full store state in this hook.
    // This prevents App re-renders on every log/stat update.
    // We only need 'lang' for the send function.
    const lang = useTrinityStore(state => state.lang);

    useEffect(() => {
        const handleMessage = (event: MessageEvent) => {
            const message = event.data;
            // DEBUG: Trace all incoming messages
            console.log('[useTrinity] 📨 Received:', message.type, message);
            // Access state directly without subscription
            const store = useTrinityStore.getState();

            switch (message.type) {
                case 'status':
                    store.setStatus(message.status);
                    if (message.status === 'active') {
                        store.setAvatarState('idle', 'down');
                    } else if (message.status === 'connecting') {
                        store.setAvatarState('init');
                    } else if (message.status === 'sleeping') {
                        store.setAvatarState('angel');
                    }
                    break;

                case 'config':
                    if (message.lang) {
                        // SOTA 2026: Fix case-sensitivity (accept 'fr', 'FR', 'FR-FR', etc.)
                        const langCode = message.lang.toLowerCase().startsWith('fr') ? 'FR' : 'EN';
                        store.setLang(langCode);
                    }
                    // SOTA 2026: Handle dynamic port-forwarded URL from extension
                    if (message.trinityBaseUrl) {
                        (window as any).trinityBaseUrl = message.trinityBaseUrl;
                        console.log('[useTrinity] Trinity URL set to:', message.trinityBaseUrl);
                    }
                    break;

                case 'version':
                    store.setVersion(message.value || message.version);
                    break;

                case 'stats':
                    // @ts-ignore
                    store.updateStats({
                        cpu: message.cpu,
                        ram: message.ram,
                        disk: message.disk,
                        breakdown: message.breakdown
                    });
                    break;

                case 'jobs':
                    // SOTA 2026 FIX: Handle jobs status update (was missing!)
                    // DEBUG: Trace incoming jobs values
                    console.log('[useTrinity] 🔧 Jobs Update:', message);
                    store.updateJobs({
                        trader: message.trader || false,
                        youtuber: message.youtuber || false,
                        influencer: message.influencer || false
                    });
                    break;

                case 'log':
                    // Normalize: Angel sends 'msg' in history replay, but 'message' in live logs
                    const logMessage = message.message || message.msg || '';
                    const streamName = (message.stream || 'SYSTEM').toUpperCase();

                    // TOKENS: Route to dedicated tokens array for TokensTable
                    if (streamName === 'TOKENS') {
                        store.addToken({
                            timestamp: message.timestamp || message.time,
                            model: message.model,
                            route: message.route,
                            key: message.key,
                            source: message.source,
                            in: message.in || message.input_tokens || 0,
                            out: message.out || message.output_tokens || 0,
                            total: message.total || message.total_tokens || 0
                        });
                    } else {
                        store.addLog({
                            message: typeof logMessage === 'string' ? logMessage : JSON.stringify(logMessage),
                            level: message.level,
                            source: streamName,
                            module: message.module || streamName,  // Preserve original module if present
                            func: message.func || message.function,  // SOTA 2026: Preserve function field
                            timestamp: message.timestamp || message.time
                        });
                    }
                    break;

                case 'log-entry':
                    // Handle structured log entries from TrinityClient
                    if (message.value) {
                        const entrySource = (message.source || '').toUpperCase();

                        // TOKENS: Route to dedicated tokens array for TokensTable
                        if (entrySource === 'TOKENS') {
                            store.addToken({
                                timestamp: message.value.timestamp,
                                model: message.value.model,
                                route: message.value.route,
                                key: message.value.key,
                                source: message.value.source,
                                in: message.value.in || message.value.input_tokens || 0,
                                out: message.value.out || message.value.output_tokens || 0,
                                total: message.value.total || message.value.total_tokens || 0
                            });
                        } else {
                            store.addLog({
                                source: message.source,
                                ...message.value
                            });
                        }
                    }
                    break;

                case 'pulse':
                    store.setPulse(message.color);
                    setTimeout(() => store.setPulse(null), message.duration || 500);
                    break;

                case 'quote':
                    store.setQuote(message.text);
                    setTimeout(() => store.setQuote(''), 5000); // Auto clear
                    break;

                // SOTA 2026: Sentinel Button States (8810 Header)
                case 'stagedProjects':
                    store.setStagedProjectsCount(message.count || 0);
                    break;

                case 'evolutionReport':
                    store.setEvolutionReport(message.report || null);
                    break;
            }
        };

        window.addEventListener('message', handleMessage);
        return () => window.removeEventListener('message', handleMessage);
    }, []);

    const send = useCallback((command: string, args?: any) => {
        // Inject current language
        const effectiveArgs = { ...args, lang };

        if (vscode) {
            // FIX: startPolling is a message TYPE, not a command value
            if (command === 'startPolling') {
                vscode.postMessage({ type: 'startPolling' });
            } else {
                vscode.postMessage({
                    type: 'command',
                    value: command,
                    args: effectiveArgs
                });
            }
        } else {
            console.log('[Dev] Mock Send:', command, effectiveArgs);
        }
    }, [lang]); // Dependency on lang is fine

    return { send };
}
