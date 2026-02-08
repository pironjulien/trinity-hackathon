/**
 * Trinity Control Center - Extension Entry Point (v2.1 SOTA)
 * Clean, Modular, Process-Manager Driven.
 * Opens as Editor Tab (WebviewPanel), not Sidebar.
 * 
 * v2.1: Added Jules Morning Brief Status Bar Integration
 */

import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { TrinityPanelManager } from './providers/TrinityPanelProvider';
import { ProcessManager } from './services/ProcessManager';
import { COMMANDS } from './core/constants';
import { getMorningBrief, formatProjectForChat, JulesProject, getStagedProjects, getProjectDiff, formatStagedProjectForChat, StagedProject } from './services/JulesService';

let panelManager: TrinityPanelManager | undefined;
let processManager: ProcessManager | undefined;
let statusBarItem: vscode.StatusBarItem;
let julesStatusBarItem: vscode.StatusBarItem;
let julesPollingInterval: NodeJS.Timeout | undefined;
let evolutionPollingInterval: NodeJS.Timeout | undefined;

export async function activate(context: vscode.ExtensionContext) {
    try {
        // 1. Initialization
        vscode.window.showInformationMessage('🧬 Trinity Activating...');

        // 2. Services
        const rootPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
        processManager = new ProcessManager(rootPath);

        // 3. Panel Manager (opens as Editor Tab)
        // SOTA 2026: No WebSocket - ProcessManager events drive UI directly
        panelManager = new TrinityPanelManager(
            context.extensionUri,
            () => processManager?.start(),      // onStartRequest
            () => processManager?.stop(),       // onStopRequest
            () => processManager,               // getProcessManager
            rootPath                            // workspacePath for video assets
        );

        // 4. Register Commands
        registerCommands(context, panelManager);
        setupStatusBar(context);
        setupJulesStatusBar(context);

        // 5. Auto-Start Logic (Sentinel Protocol)
        let checkVersion = '3.0';
        let codename = 'SOTA';

        try {
            if (rootPath) {
                const chromosomePath = path.join(rootPath, 'corpus', 'dna', 'chromosome.json');
                if (fs.existsSync(chromosomePath)) {
                    const raw = fs.readFileSync(chromosomePath, 'utf8');
                    const dna = JSON.parse(raw);
                    if (dna.version) checkVersion = dna.version;
                    if (dna.codename) codename = dna.codename;
                }
            }
        } catch (err) {
            console.warn('[Trinity] Failed to read chromosome:', err);
        }

        const displayVersion = `Trinity v${checkVersion} Standby (${codename})`;
        vscode.window.showInformationMessage(`🧬 ${displayVersion}`);

        // 6. Auto-Connect to Daemon (SOTA 2026)
        // Start monitoring to detect if Angel is already running
        // NOTE: DO NOT auto-spawn Angel - only the button should do that
        processManager.startMonitoring();

        // 7. Auto-Open Panel (Restored by User Request)
        setTimeout(() => {
            vscode.commands.executeCommand(COMMANDS.OPEN_CONTROL_CENTER);
        }, 1000);

    } catch (e: any) {
        vscode.window.showErrorMessage(`Trinity Crash: ${e.message}`);
    }
}

function registerCommands(context: vscode.ExtensionContext, panelManager: TrinityPanelManager) {
    // Open as Editor Tab
    context.subscriptions.push(
        vscode.commands.registerCommand(COMMANDS.OPEN_CONTROL_CENTER, () => {
            panelManager.show();
        })
    );

    // Native Control
    context.subscriptions.push(
        vscode.commands.registerCommand('trinity.startAngel', () => processManager?.start())
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('trinity.stopAngel', () => processManager?.stop())
    );

    // Jules Morning Brief
    context.subscriptions.push(
        vscode.commands.registerCommand('trinity.openJulesBrief', () => showJulesBrief())
    );

    // SOTA 2026: Jules Staged Projects (with diff analysis)
    context.subscriptions.push(
        vscode.commands.registerCommand('trinity.openStagedProjects', () => showStagedProjects())
    );

    // Jules Staged Projects & Debug
    context.subscriptions.push(
        vscode.commands.registerCommand('trinity.jules.sendToChat', (project) => {
            sendStagedProjectToChat(project);
        }),
        vscode.commands.registerCommand('trinity.jules.debugChat', () => {
            debugChatIntegration();
        }),
        // SOTA 2026: Refresh command for Antigravity to call after merge
        vscode.commands.registerCommand('trinity.refreshJules', () => {
            checkJulesBrief();
            vscode.window.showInformationMessage('🔄 Jules panel refreshed');
        })
    );
}

// SOTA 2026: Status Bar State Logic
function setupStatusBar(context: vscode.ExtensionContext) {
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.command = COMMANDS.OPEN_CONTROL_CENTER;
    updateStatusBar('offline'); // Initial state
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);

    // Listen to ProcessManager updates
    if (processManager) {
        processManager.on('status', (status: string) => {
            updateStatusBar(status);
        });

        // Force initial check
        setTimeout(() => processManager?.forceEmitStatus(), 2000);
    }
}

function updateStatusBar(status: string) {
    switch (status) {
        case 'active': // Trinity (Gold)
            statusBarItem.text = '$(beacon) 8810 Trinity';
            statusBarItem.color = '#ffaa00'; // Gold
            statusBarItem.tooltip = 'Trinity Neural Core: ONLINE';
            break;
        case 'sleeping': // Angel (Blue)
            statusBarItem.text = '$(pulse) 8810 Angel';
            statusBarItem.color = '#00aaff'; // Cyan Blue
            statusBarItem.tooltip = 'Angel Supervisor: STANDBY';
            break;
        default: // Offline (Grey)
            statusBarItem.text = '$(circle-slash) 8810 Offline';
            statusBarItem.color = new vscode.ThemeColor('descriptionForeground'); // Grey
            statusBarItem.tooltip = 'System Offline';
            break;
    }
}

// ============================================================================
// JULES STATUS BAR (v2.1 → v2.2 STAGED PROJECTS)
// ============================================================================

function setupJulesStatusBar(context: vscode.ExtensionContext) {
    julesStatusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 99);
    // SOTA 2026: Click opens staged projects for review, not morning brief
    julesStatusBarItem.command = 'trinity.openStagedProjects';
    julesStatusBarItem.hide(); // Hidden by default
    context.subscriptions.push(julesStatusBarItem);

    // Start polling for Staged Projects (projects ready for review)
    checkJulesBrief();
    julesPollingInterval = setInterval(() => checkJulesBrief(), 60000); // Every 60s
    context.subscriptions.push({ dispose: () => clearInterval(julesPollingInterval) });

    // SOTA 2026: Start polling for Evolution Report
    checkEvolutionReport();
    evolutionPollingInterval = setInterval(() => checkEvolutionReport(), 120000); // Every 2min
    context.subscriptions.push({ dispose: () => clearInterval(evolutionPollingInterval) });

    // SOTA 2026: Sync language from Trinity config (Site ↔ 8810)
    syncLanguage();
    const langPolling = setInterval(() => syncLanguage(), 30000); // Every 30s
    context.subscriptions.push({ dispose: () => clearInterval(langPolling) });
}

async function checkJulesBrief() {
    try {
        // SOTA 2026: Show STAGED projects (executed, ready for review) instead of morning brief
        const stagedProjects = await getStagedProjects();

        // SOTA 2026: Send to webview for sentinel button
        panelManager?.postMessage({ type: 'stagedProjects', count: stagedProjects.length });

        if (stagedProjects.length > 0) {
            julesStatusBarItem.text = `$(mail) Jules sent you ${stagedProjects.length}`;
            julesStatusBarItem.color = '#a855f7'; // Purple
            julesStatusBarItem.tooltip = `${stagedProjects.length} staged project(s) awaiting your review`;
            julesStatusBarItem.show();
        } else {
            julesStatusBarItem.hide();
        }
    } catch {
        panelManager?.postMessage({ type: 'stagedProjects', count: 0 });
        julesStatusBarItem.hide();
    }
}

// SOTA 2026: Check Evolution Report for Header Sentinel
async function checkEvolutionReport() {
    try {
        const http = require('http');
        const report = await new Promise<any>((resolve, reject) => {
            const req = http.get('http://127.0.0.1:8089/api/evolution/latest', (res: any) => {
                let data = '';
                res.on('data', (chunk: string) => data += chunk);
                res.on('end', () => {
                    try {
                        resolve(JSON.parse(data));
                    } catch {
                        resolve(null);
                    }
                });
            });
            req.on('error', () => resolve(null));
            req.setTimeout(5000, () => { req.destroy(); resolve(null); });
        });
        panelManager?.postMessage({ type: 'evolutionReport', report });
    } catch {
        panelManager?.postMessage({ type: 'evolutionReport', report: null });
    }
}

// SOTA 2026: Sync Language from Trinity config to 8810 webview (Site ↔ Extension)
function syncLanguage() {
    const rootPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (!rootPath) return;

    try {
        const configPath = path.join(rootPath, 'memories', 'trinity', 'config.json');
        if (fs.existsSync(configPath)) {
            const config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
            const lang = config.language === 'fr' ? 'FR' : 'EN';
            panelManager?.postMessage({ type: 'config', lang });
        }
    } catch {
        // Silent fail
    }
}

async function showJulesBrief() {
    const projects = await getMorningBrief();

    if (projects.length === 0) {
        vscode.window.showInformationMessage('📭 No Jules proposals waiting.');
        return;
    }

    // Build Quick Pick items
    const items = projects.map(p => {
        const confidenceIcon = p.confidence >= 80 ? '🟢' : p.confidence >= 60 ? '🟡' : '🔴';
        const sourceIcon = p.source?.includes('JULES') ? '🤖' : '🧠';

        return {
            label: `${sourceIcon} ${p.title}`,
            description: `${confidenceIcon} ${p.confidence}%`,
            detail: p.description?.slice(0, 150) + (p.description?.length > 150 ? '...' : ''),
            project: p
        };
    });

    const selected = await vscode.window.showQuickPick(items, {
        placeHolder: '☀️ Jules Morning Brief - Select a project to analyze',
        matchOnDescription: true,
        matchOnDetail: true
    });

    if (selected) {
        await sendProjectToChat(selected.project);
    }
}

async function sendProjectToChat(project: JulesProject) {
    const message = formatProjectForChat(project);

    try {
        // SOTA 2026: Use Antigravity native command to send text to chat
        // antigravity.sendTextToChat(submitImmediately: boolean, query: string)
        await vscode.commands.executeCommand('antigravity.sendTextToChat', true, message);
    } catch (e) {
        console.error('[Jules] Antigravity sendTextToChat failed:', e);
        // Fallback: Copy to clipboard
        await vscode.env.clipboard.writeText(message);
        vscode.window.showInformationMessage('📋 Copied to clipboard. Open chat and paste.');
    }
}

// ============================================================================
// STAGED PROJECTS (SOTA 2026)
// ============================================================================

async function showStagedProjects() {
    const projects = await getStagedProjects();

    if (projects.length === 0) {
        vscode.window.showInformationMessage('📭 No staged projects waiting for review.');
        return;
    }

    // Build Quick Pick items
    const items = projects.map(p => ({
        label: `🤖 ${p.title}`,
        description: `${p.files_count} files | +${p.additions} / -${p.deletions}`,
        detail: p.files.slice(0, 3).join(', ') + (p.files.length > 3 ? ` +${p.files.length - 3} more` : ''),
        project: p
    }));

    const selected = await vscode.window.showQuickPick(items, {
        placeHolder: '🔍 Staged Projects - Select to analyze with Antigravity',
        matchOnDescription: true,
        matchOnDetail: true
    });

    if (selected) {
        await sendStagedProjectToChat(selected.project);
    }
}

async function sendStagedProjectToChat(project: StagedProject) {
    // Fetch diff for detailed analysis
    const diff = await getProjectDiff(project.id);
    const message = formatStagedProjectForChat(project, diff || undefined);

    try {
        // SOTA 2026: Use Antigravity native command to send text to chat
        // antigravity.sendTextToChat(submitImmediately: boolean, query: string)
        await vscode.commands.executeCommand('antigravity.sendTextToChat', true, message);
    } catch (e) {
        console.error('[Jules] Antigravity sendTextToChat failed:', e);
        // Fallback: Copy to clipboard
        await vscode.env.clipboard.writeText(message);
        vscode.window.showInformationMessage('📋 Copied to clipboard. Open chat and paste.');
    }
}

// DEBUG: Test Chat Integration
async function debugChatIntegration() {
    const message = "Hello from Jules Debug! 🧪";

    // 1. Test Hardcoded Candidates
    const candidates = [
        'workbench.action.chat.open',
        'antigravity.triggerAgent',
        'antigravity.openAgent',
        'vscode.chat.open',
        'workbench.action.quickchat.launchInlineChat'
    ];

    let results: string[] = [];
    results.push("=== 1. TESTING CANDIDATES ===");

    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: "Debugging Chat API...",
        cancellable: false
    }, async (progress) => {
        for (const cmd of candidates) {
            progress.report({ message: `Testing ${cmd}...` });
            try {
                // Check if command exists first
                const all = await vscode.commands.getCommands(true);
                if (!all.includes(cmd)) {
                    results.push(`⚠️ ${cmd} NOT FOUND in command registry`);
                    continue;
                }

                console.log(`Executing ${cmd}...`);
                // Try executing
                await vscode.commands.executeCommand(cmd, { query: message });
                results.push(`✅ ${cmd} execute success`);
                await new Promise(r => setTimeout(r, 1000));
            } catch (e) {
                results.push(`❌ ${cmd} failed: ${e}`);
            }
        }
    });

    // 2. DISCOVERY: Find potential commands
    results.push("\n=== 2. COMMAND DISCOVERY (agent/chat) ===");
    const allCommands = await vscode.commands.getCommands(true);
    const relevant = allCommands.filter(c =>
        c.toLowerCase().includes('agent') ||
        c.toLowerCase().includes('chat') ||
        c.toLowerCase().includes('antigravity')
    ).sort();

    results.push(...relevant.map(c => `🔍 ${c}`));

    const summary = results.join('\n');
    const doc = await vscode.workspace.openTextDocument({ content: summary, language: 'text' });
    await vscode.window.showTextDocument(doc);

    vscode.window.showInformationMessage("Debug Report Generated. Check the new editor tab.", "Copy Report").then(s => {
        if (s === "Copy Report") vscode.env.clipboard.writeText(summary);
    });
}

export function deactivate() {
    panelManager?.dispose();
    if (julesPollingInterval) {
        clearInterval(julesPollingInterval);
    }
    // SOTA 2026: Do NOT kill Angel on deactivate (VM Daemon Mode)
    // processManager?.stop();
}
