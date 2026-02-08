import * as cp from 'child_process';
import * as path from 'path';
import * as fs from 'fs';
import * as vscode from 'vscode';
import { EventEmitter } from 'events';
import { MetricsReader } from './MetricsReader';

/**
 * ProcessManager (SOTA 2026 - Direct OS-Level)
 * - Monitor: `ps aux` / `pgrep` (Source of Truth)
 * - Stats: `metrics.bin` (Shared Memory/File)
 * - Control: Direct Spawn / Signal
 */
export class ProcessManager extends EventEmitter {
    private _workspacePath: string | undefined;
    private _metricsReader: MetricsReader | null = null;

    private _monitorInterval: NodeJS.Timeout | null = null;
    private _statsInterval: NodeJS.Timeout | null = null;
    private _logOffsets: Map<string, number> = new Map();

    // State
    private _isAngelAlive: boolean = false;
    private _isTrinityAlive: boolean = false;
    private _lastStatus: string = 'offline';

    constructor(workspacePath?: string) {
        super();
        this._workspacePath = workspacePath;
        // SOTA 2026 FIX: Initialize MetricsReader in constructor
        if (workspacePath) {
            this._metricsReader = new MetricsReader(workspacePath);
        }
    }

    public setWorkspacePath(path: string | undefined) {
        this._workspacePath = path;
        if (path) {
            this._metricsReader = new MetricsReader(path);
        }
    }

    /**
     * Start Monitoring (The "Watchdog")
     */
    public startMonitoring() {
        if (this._monitorInterval) clearInterval(this._monitorInterval);
        if (this._statsInterval) clearInterval(this._statsInterval);

        this.log('🛡️ Starting Direct OS Monitor...');

        // 1. Process Liveness Check (Every 5s - faster detection for UI)
        // SOTA 2026 FIX: Reduced from 60s to 5s after user reported slow detection
        this._monitorInterval = setInterval(() => {
            this.checkProcesses();
        }, 5000);

        // 2. SOTA 2026: Real-time metrics via fs.watch() on metrics.bin
        this.setupMetricsWatcher();

        // 3. SOTA 2026: Native Event-Driven Watching
        this.setupLogWatcher();

        // 4. Initial Check
        // SOTA 2026: Clear BOTH buffers AND offsets to ensure fresh log load on re-connect
        this._logBuffers.clear();
        this._logOffsets.clear();
        this.checkProcesses();
        // Load Golden Ratio History (89 lines)
        this.loadHistoricalLogs(true, 89);
        // Initial metrics read
        this.readMetrics();

        // 5. SOTA 2026: Listen for force-check events (from TrinityClient after /sys/start)
        this.on('force-check', () => {
            this.checkProcesses();
        });
    }

    /**
     * SOTA 2026: Real-time metrics via VS Code FileSystemWatcher
     */
    private _metricsWatcher: vscode.FileSystemWatcher | null = null;
    private _missingLogsInterval: NodeJS.Timeout | null = null;

    private setupMetricsWatcher() {
        if (!this._workspacePath || !this._metricsReader) return;

        const metricsPath = path.join(this._workspacePath, 'memories', 'state', 'metrics.bin');

        // Retry logic for metrics.bin
        if (!fs.existsSync(metricsPath)) {
            this.log('⏳ metrics.bin not found. Retrying in 2s...');
            setTimeout(() => this.setupMetricsWatcher(), 2000);
            return;
        }

        // Cleanup old
        if (this._metricsWatcher) {
            this._metricsWatcher.dispose();
            this._metricsWatcher = null;
        }

        // SOTA 2026 FIX: Use VS Code native FileSystemWatcher
        // More reliable on remote SSH than Node.js fs.watch()
        const pattern = new vscode.RelativePattern(
            this._workspacePath,
            'memories/state/metrics.bin'
        );

        this.log('👁️ Binding VS Code FileSystemWatcher to metrics.bin');
        this._metricsWatcher = vscode.workspace.createFileSystemWatcher(pattern);

        this._metricsWatcher.onDidChange(() => {
            try {
                const stats = fs.statSync(metricsPath);
                if (stats.size >= 96) {
                    this.readMetrics();
                }
            } catch (e) {
                // File might be locked/missing momentarily
            }
        });

        this.log('✅ Watching: metrics.bin (VS Code Native)');

        // SOTA 2026: Pure Event-Driven (No Polling Fallback)
        if (this._statsInterval) {
            clearInterval(this._statsInterval);
            this._statsInterval = null;
        }
    }



    /**
     * SOTA 2026: Robust Log Polling (Brute Force Reliability)
     * Replaces fs.watch which can be flaky on some OS/Filesystems.
     * Polls all 7 log streams every 1s.
     */
    /**
     * SOTA 2026: Event-Driven Log Monitoring (Native SSH Support)
     * Uses vscode.workspace.createFileSystemWatcher instead of polling.
     */
    private setupLogWatcher() {
        if (!this._workspacePath) return;

        // Pattern: Matches any .jsonl in memories/logs/
        const pattern = new vscode.RelativePattern(
            this._workspacePath,
            'memories/logs/*.jsonl'
        );

        this.log('🛡️ Starting Native FileSystemWatcher for Logs...');

        const watcher = vscode.workspace.createFileSystemWatcher(pattern);

        // Debounce map
        const pendingReads = new Set<string>();

        const triggerRead = (uri: vscode.Uri) => {
            const filename = path.basename(uri.fsPath);
            if (pendingReads.has(filename)) return;

            pendingReads.add(filename);

            // 50ms Debounce
            setTimeout(() => {
                pendingReads.delete(filename);
                this.readNewLogLines(filename, uri.fsPath);
            }, 50);
        };

        // Bind Events
        watcher.onDidChange(triggerRead);
        watcher.onDidCreate(triggerRead);

        // Keep watcher reference (optional, for dispose if needed later)
        // this._logWatcher = watcher; 
    }

    /**
     * Read new lines from a specific log file (triggered by polling)
     */
    private readNewLogLines(filename: string, filePath: string) {
        try {
            const stats = fs.statSync(filePath);
            let currentOffset = this._logOffsets.get(filename) || 0;

            // this.log(`📜 [${filename}] Detected Change. Size: ${stats.size}, Offset: ${currentOffset}`);

            // File rotated/truncated
            if (stats.size < currentOffset) {
                // this.log(`🔄 [${filename}] Rotated/Truncated. Resetting offset + clearing memory.`);
                currentOffset = 0;

                // SOTA 2026: Clear memory buffer to prevent Ghost Logs
                const streamName = filename.replace('.jsonl', '');
                if (this._logBuffers.has(streamName)) {
                    this._logBuffers.set(streamName, []);
                }

                // Emit Clear Event to UI
                this.emit('message', {
                    type: 'clear',
                    stream: streamName,
                    timestamp: new Date().toISOString()
                });
            }

            // SOTA 2026: Startup Flood Protection
            // If we have 0 offset but file is huge (>100KB), skip to end to prevent UI freeze
            // Exception: loadHistoricalLogs should have handled this, but this is a safety net for polling
            if (currentOffset === 0 && stats.size > 100 * 1024) {
                // this.log(`🛡️ [${filename}] File too large for initial read (${stats.size} bytes). Skipping to end.`);
                this._logOffsets.set(filename, stats.size);
                return;
            }

            // No new data
            if (stats.size === currentOffset) {
                // this.log(`🤷 [${filename}] No new bytes.`);
                return;
            }

            // Read new bytes
            const fd = fs.openSync(filePath, 'r');
            const bufferSize = stats.size - currentOffset;
            const buffer = Buffer.alloc(bufferSize);

            fs.readSync(fd, buffer, 0, bufferSize, currentOffset);
            fs.closeSync(fd);

            // this.log(`📥 [${filename}] Read ${bufferSize} bytes.`);

            // Update offset
            this._logOffsets.set(filename, stats.size);

            // Parse and emit each line
            const lines = buffer.toString('utf8').split('\n').filter(l => l.trim());
            lines.forEach(line => {
                try {
                    const entry = JSON.parse(line);
                    // this.log(`📤 [${filename}] Emitting Log: ${entry.message || 'No msg'}`);
                    const event = {
                        type: 'log',
                        stream: filename.replace('.jsonl', ''),
                        timestamp: entry.timestamp,
                        level: entry.level,
                        message: entry.message,
                        function: entry.function, // Explicit mapping
                        func: entry.function,     // SOTA 2026: Map to 'func' to avoid keyword collisions in UI
                        module: entry.module,     // Explicit mapping
                        ...entry
                    };
                    this.addToLogBuffer(event);
                    this.emit('message', event);
                } catch (e) {
                    // Silent fail
                }
            });
        } catch (err) {
            // Silent fail
        }
    }

    /**
     * Run `pgrep` to verify process existence
     */
    private checkProcesses() {
        // Run pgrep for Angel and Trinity
        // -f matches full command line (needed for python scripts)
        cp.exec('pgrep -la -f "python.*(angel\\.py|trinity\\.py)"', (err, stdout, stderr) => {
            // Silent check - logs only on state change

            const output = stdout.toLowerCase();
            const angelAlive = output.includes('angel.py');
            const trinityAlive = output.includes('trinity.py');

            // Detect State Changes - ALWAYS emit on first check or state change
            if (angelAlive !== this._isAngelAlive || trinityAlive !== this._isTrinityAlive) {
                this._isAngelAlive = angelAlive;
                this._isTrinityAlive = trinityAlive;
                this.determineAndEmitStatus();
            }
        });
    }

    private determineAndEmitStatus(forceEmit: boolean = false) {
        let newStatus = 'offline';

        // SOTA 2026 State Machine:
        // - offline: No processes
        // - sleeping: Angel only (show angel.webm)
        // - active: Angel + Trinity (show iframe)

        if (this._isAngelAlive && this._isTrinityAlive) {
            newStatus = 'active'; // Both running -> Trinity Dashboard
        } else if (this._isAngelAlive && !this._isTrinityAlive) {
            newStatus = 'sleeping'; // Angel only -> Video Loop
        }
        // else: offline

        // Emit if changed OR if forced (for initial sync)
        if (newStatus !== this._lastStatus || forceEmit) {
            this._lastStatus = newStatus;
            this.emit('status', newStatus);
            // this.log(`State: ${newStatus.toUpperCase()} (Angel: ${this._isAngelAlive}, Trinity: ${this._isTrinityAlive})`);
        }

        // SOTA 2026: Emit job status from jobs.json (Source of Truth)
        // This replaces the hardcoded "all jobs active when Trinity is alive" logic
        this.readJobsConfig();
    }

    /**
     * Force emit current status (used for initial webview sync)
     */
    public forceEmitStatus() {
        this.determineAndEmitStatus(true);
    }

    private readMetrics() {
        if (!this._metricsReader) {
            return;
        }
        const metrics = this._metricsReader.read();
        if (metrics) {
            // SOTA 2026 DEBUG: Explicit raw metrics logging
            // this.log(`📊 Raw Metrics: ${JSON.stringify(metrics)}`);

            // SOTA 2026 Extended: Full breakdown with disk and all processes
            this.emit('stats', {
                type: 'stats',
                cpu: metrics.sys_cpu,
                ram: metrics.sys_ram,
                disk: metrics.sys_disk,
                breakdown: {
                    angel: { name: 'Angel', cpu: metrics.angel_cpu, ram: Math.round(metrics.angel_ram) },
                    trinity: { name: 'Trinity', cpu: metrics.trinity_cpu, ram: Math.round(metrics.trinity_ram) },
                    ubuntu: { name: 'Ubuntu', cpu: metrics.ubuntu_cpu, ram: Math.round(metrics.ubuntu_ram) },
                    antigravity: { name: 'Antigravity', cpu: metrics.antigravity_cpu, ram: Math.round(metrics.antigravity_ram) }
                }
            });
        }
    }

    /**
     * Start Angel (Spawn Process)
     */
    public async start(): Promise<boolean> {
        if (this._isAngelAlive) {
            this.log('✅ Angel already running.');
            return true;
        }

        if (!this._workspacePath) return false;

        const angelPath = path.join(this._workspacePath, 'angel.py');
        if (!fs.existsSync(angelPath)) {
            vscode.window.showErrorMessage('❌ angel.py not found');
            return false;
        }

        this.log('🚀 Spawning Angel System...');

        // Spawn Detached
        const venvPython = path.join(this._workspacePath, '.venv', 'bin', 'python');
        const pythonCmd = fs.existsSync(venvPython) ? venvPython : 'python3';

        const child = cp.spawn(pythonCmd, ['angel.py'], {
            cwd: this._workspacePath,
            detached: true,
            stdio: ['ignore', 'pipe', 'pipe'] // Capture output to merge into angel.jsonl
        });

        // Use a simple specialized logger for boot failures/stderr
        const logToAngel = (data: Buffer, defaultLevel: string) => {
            const raw = data.toString().trim();
            if (!raw) return;

            // Split by newlines and process each line separately
            const lines = raw.split('\n').map(l => l.trim()).filter(l => l);

            // SOTA 2026 FIX: Regex patterns for level extraction
            // Loguru format: "2026-01-30 10:40:49.535 | INFO     | module:func:line - message"
            const loguruPattern = /\|\s*(DEBUG|INFO|WARNING|ERROR|CRITICAL)\s*\|/i;
            // Standard/Uvicorn format: "INFO: message" or "WARNING: message"
            const standardPattern = /^(DEBUG|INFO|WARNING|ERROR|CRITICAL):\s*/i;
            // ANSI Strip Pattern
            const ansiPattern = /\x1B\[[0-9;]*[mK]/g;

            for (const line of lines) {
                // SOTA 2026: Strip ANSI codes first for clean regex matching
                let msg = line.replace(ansiPattern, '');
                let finalLevel = defaultLevel;

                // 1. Check Loguru format first (most specific)
                const loguruMatch = loguruPattern.exec(msg);
                if (loguruMatch) {
                    finalLevel = loguruMatch[1].toUpperCase();
                    // Keep the full message (Loguru format is informative)
                }
                // 2. Check standard prefix format
                else if (standardPattern.test(msg)) {
                    const match = standardPattern.exec(msg);
                    if (match) {
                        finalLevel = match[1].toUpperCase();
                        msg = msg.replace(standardPattern, '');
                    }
                }

                // Normalize WARNING -> WARN for consistency
                if (finalLevel === 'WARNING') {
                    finalLevel = 'WARN';
                }

                // Skip empty after cleaning
                if (!msg) continue;

                // SOTA 2026: Skip DEBUG logs (noise)
                if (finalLevel === 'DEBUG') continue;

                // SOTA 2026 FIX: Skip Loguru-format logs entirely
                // These are already written correctly to trinity.jsonl by Trinity itself
                // Writing them here causes duplicates with wrong metadata
                if (loguruMatch) continue;

                const entry = {
                    timestamp: new Date().toISOString(),
                    level: finalLevel,
                    module: 'Uvicorn',
                    func: 'bootstrap',
                    message: msg
                };

                const logPath = path.join(this._workspacePath!, 'memories', 'logs', 'angel.jsonl');
                try {
                    fs.appendFileSync(logPath, JSON.stringify(entry) + '\n');
                } catch (e) { /* emergency fallback? */ }
            }
        };

        child.stdout?.on('data', (data) => logToAngel(data, 'INFO'));
        child.stderr?.on('data', (data) => logToAngel(data, 'ERROR'));

        child.unref(); // Detach - pgrep will track via OS process table

        // Let the monitor pick it up
        setTimeout(() => this.checkProcesses(), 1000);

        // SOTA 2026: Re-init log watchers as files are created by Angel


        return true;
    }

    public stop() {
        this.log('🛑 Stopping Angel...');
        // Only kill Angel - Trinity must be stopped first (enforced by UI)
        // Metrics stays alive for continuous monitoring
        cp.exec('pkill -f "python.*angel.py"');

        // Force state update
        this._isAngelAlive = false;
        this._isTrinityAlive = false;
        this.determineAndEmitStatus();
    }

    /**
     * Direct Log Tailing (Optimized Byte-Range Reader)
     * Reads only new bytes since last check.
     */
    public loadHistoricalLogs(emitLive: boolean = false, count: number = 89) {
        if (!this._workspacePath) return;

        const logsDir = path.join(this._workspacePath, 'memories', 'logs');
        const logFiles = [
            'angel.jsonl',
            'trinity.jsonl',
            'trader.jsonl',
            'youtuber.jsonl',
            'influencer.jsonl',
            'tokens.jsonl',
            'alerts.jsonl',
            'jules.jsonl',
            'social.jsonl'
        ];

        logFiles.forEach(filename => {
            const filePath = path.join(logsDir, filename);
            if (!fs.existsSync(filePath)) return;

            try {
                const stats = fs.statSync(filePath);
                const streamName = filename.replace('.jsonl', '');
                let currentOffset = this._logOffsets.get(filename) || 0;

                // SOTA 2026 (Standard 362.102.C): Anti-Ghost Logs on Startup
                // If file is empty (rotated), clear memory buffer and emit clear to UI
                if (stats.size === 0) {
                    if (this._logBuffers.has(streamName) && this._logBuffers.get(streamName)!.length > 0) {
                        this._logBuffers.set(streamName, []);
                        this.emit('message', {
                            type: 'clear',
                            stream: streamName,
                            timestamp: new Date().toISOString()
                        });
                    }
                    this._logOffsets.set(filename, 0);
                    return;
                }

                // Case A: File Rotated/Truncated
                if (stats.size < currentOffset) {
                    currentOffset = 0;
                    // SOTA 2026: Also clear buffer on truncation
                    if (this._logBuffers.has(streamName)) {
                        this._logBuffers.set(streamName, []);
                        this.emit('message', {
                            type: 'clear',
                            stream: streamName,
                            timestamp: new Date().toISOString()
                        });
                    }
                }

                // Case B: No new data
                if (stats.size === currentOffset) {
                    // SOTA 2026: Ensure offset is registered even if no new data
                    this._logOffsets.set(filename, stats.size);
                    return;
                }


                // Case C: New Data! Read from Offset -> End
                const fd = fs.openSync(filePath, 'r');
                const bufferSize = stats.size - currentOffset;
                const buffer = Buffer.alloc(bufferSize);

                fs.readSync(fd, buffer, 0, bufferSize, currentOffset);
                fs.closeSync(fd);

                this._logOffsets.set(filename, stats.size);

                const content = buffer.toString('utf-8');
                const lines = content.trim().split('\n').filter(l => l.trim());

                // Apply Golden Ratio limit only on initial load (offset 0)
                const linesToProcess = currentOffset === 0 ? lines.slice(-count) : lines;

                // this.log(`📜 [${filename}] Historic Read. Lines: ${lines.length}, Processing: ${linesToProcess.length}`);

                linesToProcess.forEach(line => {
                    try {
                        const entry = JSON.parse(line);
                        const uiEvent = {
                            type: 'log',
                            stream: filename.replace('.jsonl', ''),
                            timestamp: entry.timestamp,
                            level: entry.level,
                            message: entry.message,
                            function: entry.function,
                            func: entry.function, // SOTA 2026: Map to 'func'
                            module: entry.module,
                            ...entry
                        };

                        // Buffer or Emit
                        if (emitLive || currentOffset === 0) {
                            this.addToLogBuffer(uiEvent);
                            this.emit('message', uiEvent);
                        }
                    } catch (e) {
                        // Silent fail on parse error during historic read
                    }
                });

            } catch (e) {
                // Silent fail on load error
            }
        });
    }

    // SOTA 2026: Per-Stream Buffers (Segregated Memory)
    // Ensures 'Trinity' logs never overwrite 'Angel' logs due to volume.
    // "One JSONL -> One Buffer -> One Tab"
    private _logBuffers: Map<string, any[]> = new Map();
    private static MAX_STREAM_BUFFER = 500; // Lines per stream (plenty for history)

    private addToLogBuffer(event: any) {
        const stream = event.stream || 'system';

        if (!this._logBuffers.has(stream)) {
            this._logBuffers.set(stream, []);
        }

        const buffer = this._logBuffers.get(stream)!;
        buffer.push(event);

        if (buffer.length > ProcessManager.MAX_STREAM_BUFFER) {
            buffer.shift();
        }
    }

    // New Method: Explicitly Replay Logs to a connecting client
    public replayLogs() {
        // this.log(`🔄 Replaying logs from ${this._logBuffers.size} streams...`);

        this._logBuffers.forEach((buffer, stream) => {
            // this.log(`   - Stream [${stream}]: ${buffer.length} events`);
            buffer.forEach(event => {
                this.emit('message', event);
            });
        });
    }

    private pollLogFiles() {
        // Simple polling for now (fs.watch can be flaky on network drives/VMs)
        this.loadHistoricalLogs(true);
        this.readJobsConfig();
    }

    /**
     * Read jobs.json directly (Source of Truth for "Carte Jobs")
     */
    private readJobsConfig() {
        if (!this._workspacePath) return;
        // SOTA 2026 FIX: jobs.json is now in memories/ (unified state management)
        const jobsPath = path.join(this._workspacePath, 'memories', 'jobs.json');

        if (!fs.existsSync(jobsPath)) return;

        try {
            const content = fs.readFileSync(jobsPath, 'utf-8');
            const jobs = JSON.parse(content);

            // SOTA 2026: Job is "active" only if BOTH enabled AND Trinity is running
            this.emit('jobs', {
                trader: jobs.trader?.enabled && this._isTrinityAlive,
                youtuber: jobs.youtuber?.enabled && this._isTrinityAlive,
                influencer: jobs.influencer?.enabled && this._isTrinityAlive,
                angel: this._isAngelAlive,
                _meta: {
                    angel: this._isAngelAlive,
                    trinity: this._isTrinityAlive
                }
            });

        } catch (e) {
            // Ignore partial reads
        }
    }

    // Unused legacy methods stubs to prevent compile errors if referenced elsewhere
    // public getRecentLogs() { return []; } // REMOVED: Duplicate
    public checkAndConnect() {
        if (!this._monitorInterval) {
            this.startMonitoring();
        }
        return Promise.resolve(true);
    }
    public get isRunning() { return this._isAngelAlive; }
    public get isTrinityRunning() { return this._isTrinityAlive; }

    private log(msg: string) {
        // this.outputChannel.appendLine(`[ProcMgr] 🛡️ Starting Direct OS Monitor...`);
        // this.outputChannel.appendLine(`[ProcMgr] 👁️ Binding Watcher to metrics.bin`);
    }


}
