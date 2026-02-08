/**
 * Trinity Control Center - Constants
 * Configuration keys, defaults, and enums
 */

// ============================================================================
// VS Code Configuration Keys
// ============================================================================

export const CONFIG_NAMESPACE = 'trinity';

export const CONFIG_KEYS = {
    LOCAL_URL: 'localUrl',
} as const;

// Hardcoded values - no user configuration needed
export const HARDCODED = {
    LOCAL_URL: 'http://127.0.0.1:8089',
    REMOTE_PATH: '~/Trinity',
    PORT: '8089',
    // WEB UI Ports (separate from API)
    WEB_PORT_LOCAL: '5176',  // Vite dev server
} as const;

// ============================================================================
// View IDs
// ============================================================================

export const VIEW_ID = 'trinity-sidebar';
export const VIEW_CONTAINER_ID = 'trinity-sidebar-view';

// ============================================================================
// Timing Constants
// ============================================================================

export const TIMING = {
    // SOTA 2026: ProcessManager uses Fibonacci intervals (1597ms/987ms) inline
    RECONNECT_DELAY: 3000,      // Reconnection delay
    WATCHDOG_TIMEOUT: 30000,    // Watchdog timeout
    PULSE_DURATION: 500,        // UI pulse animation
    ACTIVITY_FLASH: 300,        // Job activity flash
} as const;

// ============================================================================
// Log Files (Remote)
// ============================================================================

export const LOG_FILES = {
    ALERTS: 'alerts.jsonl',
    TRINITY: 'system.jsonl',
    ANGEL: 'angel.jsonl',
    TRADER: 'trader.jsonl',
    YOUTUBER: 'youtuber.jsonl',
    INFLUENCER: 'influencer.jsonl',
    TOKENS: 'tokens.jsonl',
    JULES: 'jules.jsonl',
    SOCIAL: 'social.jsonl',
} as const;

// ============================================================================
// Commands
// ============================================================================

export const COMMANDS = {
    OPEN_CONTROL_CENTER: 'trinity.openControlCenter',
} as const;

// ============================================================================
// Job IDs
// ============================================================================

export const JOB_IDS = ['trader', 'youtuber', 'influencer'] as const;

// ============================================================================
// Pulse Colors (Google Material)
// ============================================================================

export const PULSE_COLORS = {
    TRINITY: '#8AB4F8',   // Blue
    TRADER: '#81C995',    // Green  
    YOUTUBER: '#F28B82',  // Red
    ALERT: '#FDD663',     // Yellow
    ERROR: '#EA4335',     // Red
} as const;
