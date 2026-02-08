/**
 * Trinity Control Center - Trinity Client (v4.1 SOTA - Direct Architecture)
 * =========================================================================
 * - Source of Truth: ProcessManager (pgrep)
 * - Communication: HTTP (Commands) / Events (Status)
 * - Legacy Networks: REMOVED (No WebSocket)
 */

import * as vscode from 'vscode';
import { ProcessManager } from '../services/ProcessManager';
import { MessageFromWebview, MessageToWebview, ConnectionStatus } from './types';
import * as cp from 'child_process';

export interface TrinityClientCallbacks {
    postMessage: (message: MessageToWebview) => void;
    onStartRequest: () => void; // Callback to spawn Angel process
    onStopRequest: () => void;  // Callback to stop Angel process
    getProcessManager: () => ProcessManager | undefined;
}

export class TrinityClient {
    private _isActive = false;
    // Handlers storage for clean unbinding
    private _handlers: { [key: string]: (...args: any[]) => void } = {};

    constructor(private _callbacks: TrinityClientCallbacks) { }

    // ════════════════════════════════════════════════════════════════════════
    // LIFECYCLE
    // ════════════════════════════════════════════════════════════════════════

    public start(): void {
        if (this._isActive) return;
        this._isActive = true;

        this._bindEvents();

        // Initial State Check
        const pm = this._callbacks.getProcessManager();
        if (pm) {
            // Start monitoring if not already
            pm.checkAndConnect();

            // SOTA 2026 FIX: Force status emit after webview is ready
            // Give webview 1.5s to mount and attach message listener
            setTimeout(() => {
                pm.forceEmitStatus();
            }, 1500);
        } else {
            this._sendMessage({ type: 'status', status: 'offline' });
        }
    }

    public stop(): void {
        this._isActive = false;
        this._unbindEvents();
    }

    public dispose(): void {
        this.stop();
    }

    // ════════════════════════════════════════════════════════════════════════
    // EVENT BINDING (ProcessManager -> UI)
    // ════════════════════════════════════════════════════════════════════════

    private _bindEvents(): void {
        const pm = this._callbacks.getProcessManager();
        if (!pm) return;

        this._unbindEvents(); // Safety cleanup

        // Define Handlers
        this._handlers['status'] = (status: ConnectionStatus) => {
            // console.log('[TrinityClient] 📡 Status Event:', status);
            this._sendMessage({ type: 'status', status });
        };

        this._handlers['message'] = (msg: any) => {
            // Forward Logs/IPC directly
            // console.log('[TrinityClient] 📝 Log Event:', msg.stream || msg.type);
            this._sendMessage(msg);
        };

        this._handlers['stats'] = (stats: any) => {
            // Forward Metrics (CPU/RAM)
            // console.log('[TrinityClient] 📊 Stats Event:', stats.cpu, stats.ram);
            this._sendMessage(stats);
        };

        this._handlers['jobs'] = (jobs: any) => {
            // Forward Job Status
            this._sendMessage({ type: 'jobs', ...jobs });
        };

        // Attach Handlers
        pm.on('status', this._handlers['status']);
        pm.on('message', this._handlers['message']);
        pm.on('stats', this._handlers['stats']);
        pm.on('jobs', this._handlers['jobs']);

        // SOTA 2026 FIX: Force initial data after binding
        // This ensures webview gets current state even if ProcessManager started earlier
        setTimeout(() => {
            pm.forceEmitStatus();
            // Also trigger a metrics read
            if ((pm as any).readMetrics) {
                (pm as any).readMetrics();
            }
            // SOTA 2026: Replay detailed logs history for late-connecting clients
            if ((pm as any).replayLogs) {
                // console.log('[TrinityClient] 🔄 Triggering Log Replay (Delayed 2.5s)...');
                (pm as any).replayLogs();
            }
        }, 2500);

        // Hydration: Replay recent logs instantly (Golden Ratio History)
        // const recentLogs = pm.getRecentLogs(); // REMOVED: Managed by replayLogs()
    }

    private _unbindEvents(): void {
        const pm = this._callbacks.getProcessManager();
        if (!pm) return;

        if (this._handlers['status']) pm.off('status', this._handlers['status']);
        if (this._handlers['message']) pm.off('message', this._handlers['message']);
        if (this._handlers['stats']) pm.off('stats', this._handlers['stats']);
        if (this._handlers['jobs']) pm.off('jobs', this._handlers['jobs']);

        this._handlers = {};
    }

    private _sendMessage(msg: MessageToWebview) {
        if (this._isActive) {
            // console.log(`[TrinityClient] 📤 Sending to Webview: ${msg.type}`, msg);
            this._callbacks.postMessage(msg);
        } else {
            // console.warn(`[TrinityClient] ⚠️ Cannot send (inactive): ${msg.type}`);
        }
    }

    // ════════════════════════════════════════════════════════════════════════
    // COMMAND HANDLING (UI -> Backend)
    // ════════════════════════════════════════════════════════════════════════

    public async handleMessage(message: MessageFromWebview) {
        // console.log(`[TrinityClient] 📥 Received from Webview: ${message.type}`, message);
        switch (message.type) {
            case 'command':
                await this._handleCommand(message.value, message.args);
                break;
            case 'copyToClipboard':
                vscode.env.clipboard.writeText(message.content);
                vscode.window.showInformationMessage('Copied to clipboard');
                break;
        }
    }

    private async _handleCommand(command: string, args?: any) {
        // console.log('[TrinityClient] 🔘 Command Received:', command, args);
        const pm = this._callbacks.getProcessManager();

        try {
            // A. SYSTEM CONTROLS (Angel)
            if (command === 'ANGEL_GO') {
                if (pm?.isRunning) {
                    vscode.window.showWarningMessage('⚠️ Angel tourne déjà ! Arrêtez-le d\'abord.');
                } else {
                    this._sendMessage({ type: 'status', status: 'connecting' });
                    this._callbacks.onStartRequest();
                }
                return;
            }

            if (command === 'ANGEL_STOP') {
                if (!pm?.isRunning) {
                    vscode.window.showWarningMessage('⚠️ Angel ne tourne pas.');
                    return;
                }
                // Safety: Must stop Trinity first
                if (pm?.isTrinityRunning) {
                    vscode.window.showWarningMessage('⚠️ Arrêtez Trinity d\'abord !');
                    return;
                }
                this._sendMessage({ type: 'status', status: 'stopping' });
                this._callbacks.onStopRequest();
                return;
            }

            // B. WORKER CONTROLS (Trinity) -> Via HTTP Proxy
            if (command === 'GO') {
                if (!pm?.isRunning) {
                    vscode.window.showWarningMessage('⚠️ Démarrez Angel d\'abord !');
                    return;
                }
                if (pm?.isTrinityRunning) {
                    vscode.window.showWarningMessage('⚠️ Trinity tourne déjà ! Arrêtez-le d\'abord.');
                    return;
                }
                this._sendMessage({ type: 'status', status: 'connecting' });
                this._httpPost('/sys/start');
                return;
            }

            if (command === 'STOP') {
                if (!pm?.isTrinityRunning) {
                    vscode.window.showWarningMessage('⚠️ Trinity ne tourne pas.');
                    return;
                }
                this._sendMessage({ type: 'status', status: 'stopping' });
                this._httpPost('/sys/stop');
                return;
            }

            // C. LOG UTILITIES
            if (command === 'CLEAR_LOGS') {
                const tabParam = args?.tab ? `?tab=${args.tab}` : '';
                this._httpPost(`/logs/clear${tabParam}`);
                return;
            }

            // D. SENTINEL COMMANDS (SOTA 2026: Header Alert Buttons)
            if (command === 'openStagedProjects') {
                vscode.commands.executeCommand('trinity.openStagedProjects');
                return;
            }

            if (command === 'openEvolutionReport') {
                // Send evolution report summary to Antigravity chat
                try {
                    const http = require('http');
                    const response = await new Promise<string>((resolve, reject) => {
                        const req = http.get('http://127.0.0.1:8089/api/evolution/latest', (res: any) => {
                            let data = '';
                            res.on('data', (chunk: string) => data += chunk);
                            res.on('end', () => resolve(data));
                        });
                        req.on('error', reject);
                        req.setTimeout(5000, () => { req.destroy(); reject(new Error('Timeout')); });
                    });
                    const report = JSON.parse(response);
                    if (report.hasReport) {
                        // SOTA 2026: Localized prompt based on language switch
                        const lang = args?.lang || 'EN';
                        const message = lang === 'FR'
                            ? `🧬 **Rapport d'Évolution SOTA (${report.date})**

**Résumé Trinity :** ${report.summary || 'Rapport disponible'}

**Analyse Complète :**
${report.analysisPreview || 'N/A'}

---

**Mission :** Analyse les demandes et objectifs de Trinity dans ce rapport. Pour chaque point :
1. Évalue si c'est réalisable immédiatement
2. Identifie les blocages éventuels
3. Propose un plan d'action concret

Fais-moi un rapport structuré de ce qui peut être fait aujourd'hui vs ce qui nécessite plus de travail.`
                            : `🧬 **SOTA Evolution Report (${report.date})**

**Trinity Summary:** ${report.summary || 'Report available'}

**Full Analysis:**
${report.analysisPreview || 'N/A'}

---

**Mission:** Analyze Trinity's requests and objectives in this report. For each item:
1. Assess if it can be done immediately
2. Identify any blockers
3. Propose a concrete action plan

Give me a structured report of what can be done today vs what requires more work.`;
                        await vscode.commands.executeCommand('antigravity.sendTextToChat', true, message);

                        // SOTA 2026: Reset button state after sending to chat (mark as "seen")
                        this._callbacks.postMessage({ type: 'evolutionReport', report: null });
                    } else {
                        const noReportMsg = (args?.lang === 'FR') ? 'Aucun rapport d\'évolution disponible.' : 'No evolution report available.';
                        vscode.window.showInformationMessage(noReportMsg);
                    }
                } catch (e) {
                    console.error('[TrinityClient] Evolution report fetch failed:', e);
                    const errorMsg = (args?.lang === 'FR') ? 'Impossible de charger le rapport d\'évolution.' : 'Failed to load evolution report.';
                    vscode.window.showErrorMessage(errorMsg);
                }
                return;
            }

        } catch (error) {
            console.error(`[TrinityClient] Cmd Fail: ${command}`, error);
        }
    }

    // SOTA 2026: Native HTTP (no fork, faster than curl)
    private _httpPost(path: string) {
        const http = require('http');
        const pm = this._callbacks.getProcessManager();
        const req = http.request({
            hostname: '127.0.0.1',
            port: 8089,
            path: path,
            method: 'POST',
            timeout: 2000
        }, () => {
            // SOTA 2026: Trigger status refresh after system commands
            if (path.startsWith('/sys/') && pm) {
                // Give Trinity time to start/stop, then refresh
                setTimeout(() => pm.emit('force-check'), 2000);
            }
        });
        req.on('error', (err: Error) => console.error(`[TrinityClient] HTTP Error (${path}):`, err.message));
        req.end();
    }
}
