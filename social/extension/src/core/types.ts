/**
 * Trinity Control Center - Core Types
 * Strict TypeScript interfaces for the entire extension
 */

// ============================================================================
// Configuration
// ============================================================================

export interface TrinityConfig {
    localUrl: string;
}

// ============================================================================
// Connection & Mode
// ============================================================================

export type ConnectionMode = 'local' | 'remote';

export type ConnectionStatus = 'active' | 'offline' | 'stopped' | 'connecting' | 'stopping' | 'error' | 'sleeping';

export interface ConnectionState {
    mode: ConnectionMode;
    status: ConnectionStatus;
    version: string;
    lastUpdate: number;
}

// ============================================================================
// System Stats
// ============================================================================

export interface SystemStats {
    cpu: string;
    ram: number;
    disk: number;
    timestamp?: number;
    breakdown?: MemoryBreakdown;
}

export interface MemoryProcess {
    name: string;
    ram: number; // MB
    pid?: number;
}

export interface MemoryBreakdown {
    angel: MemoryProcess;
    trinity: MemoryProcess;
    chrome: MemoryProcess;
    vscode: MemoryProcess;
    other: number; // MB
}

// ============================================================================
// Jobs
// ============================================================================

export type JobId = 'trader' | 'youtuber' | 'influencer';

export interface JobState {
    enabled: boolean;
    active?: boolean;
    lastActivity?: number;
}

export type JobsMap = Record<JobId, JobState | boolean>;

// ============================================================================
// Logs
// ============================================================================

export type LogFilter = 'ALERTS' | 'TRINITY' | 'ANGEL' | 'JULES' | 'SOCIAL' | 'TRADER' | 'YOUTUBER' | 'INFLUENCER' | 'TOKENS';

export type LogLevel = 'DEBUG' | 'INFO' | 'WARN' | 'ERROR' | 'CRITICAL';

export interface LogEntry {
    timestamp: string;
    level: LogLevel;
    module: string;
    function: string;
    message: string;
    raw?: string;
}

export interface TokenEntry {
    timestamp: string;
    model: string;
    route: string;
    key: string;
    source: string;
    in: number;
    out: number;
    total: number;
}

// ============================================================================
// Commands
// ============================================================================

export type CommandType =
    | 'GO'
    | 'STOP'
    | 'ANGEL_GO'
    | 'ANGEL_STOP'
    | 'DROID'
    | 'WEB'
    | 'WOMAN'
    | 'DEPLOY'
    | 'SETUP'
    | 'SWITCH_MODE'
    | 'CLEAR_LOGS';

export interface CommandResult {
    success: boolean;
    message?: string;
    data?: unknown;
}

// ============================================================================
// RPC Messages (Extension <-> Webview)
// ============================================================================

export type MessageToWebview =
    | { type: 'status'; status: ConnectionStatus }
    | { type: 'version'; value: string }
    | { type: 'stats'; cpu: string; ram: number; disk: number; breakdown?: MemoryBreakdown }
    | { type: 'jobsUpdate'; value: JobsMap }
    | { type: 'activity'; id: JobId }
    | { type: 'log-entry'; source: LogFilter; value: LogEntry }
    | { type: 'token-row'; value: TokenEntry }
    | { type: 'pulse'; color: string }
    | { type: 'clear-logs'; filter?: LogFilter }
    | { type: 'show-modal'; title: string; content: string }
    | { type: 'show-health'; content: string }
    | { type: 'whisper'; value: string }
    | { type: 'append-modal-log'; value: string }
    | { type: 'toggle-settings' }
    | { type: 'set-mode'; mode: ConnectionMode }
    // SOTA 2026: Header Sentinel Buttons
    | { type: 'stagedProjects'; count: number }
    | { type: 'evolutionReport'; report: any }
    // SOTA 2026: Language sync from Trinity config
    | { type: 'config'; lang: string };

export type MessageFromWebview =
    | { type: 'command'; value: CommandType; args?: CommandArgs }
    | { type: 'startPolling' }
    | { type: 'getTokens' }
    | { type: 'clear-logs'; filter: LogFilter }
    | { type: 'copyToClipboard'; content: string }
    | { type: 'ai-toggle'; value: boolean };

export interface CommandArgs {
    lang?: string;
    mode?: ConnectionMode;
    [key: string]: unknown;
}

// ============================================================================
// Events
// ============================================================================

export interface TrinityEvents {
    'stats': SystemStats;
    'status': ConnectionStatus;
    'version': string;
    'jobs': JobsMap;
    'log': { filter: LogFilter; entry: LogEntry };
    'token': TokenEntry;
    'tokens': TokenEntry[];
    'activity': JobId;
    'pulse': string;
    'clear-logs': LogFilter;
    'error': Error;
    'whisper': string;
}

// ============================================================================
// UI State
// ============================================================================

export interface UIState {
    activeTab: LogFilter;
    lang: 'EN' | 'FR';
    settingsVisible: boolean;
    modalVisible: boolean;
    modalTitle: string;
    modalContent: string;
}
