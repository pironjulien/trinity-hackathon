/**
 * Jules Service - Morning Brief Integration (SOTA 2026)
 * =====================================================
 * Fetches Jules Morning Brief from Angel API and handles project decisions.
 */

import * as http from 'http';

export interface JulesProject {
    id: string;
    title: string;
    description: string;
    confidence: number;
    pr_url?: string;
    status: string;
    source?: string;
}

export interface MorningBrief {
    date: string;
    candidates: JulesProject[];
}

// SOTA 2026: Staged Projects (executed by Jules API, ready for review)
export interface StagedProject {
    id: string;
    title: string;
    status: 'STAGED' | 'PENDING';
    staged_at: string;
    session_id?: string;
    pr_url?: string;
    pr_number?: number;
    files_count: number;
    additions: number;
    deletions: number;
    files: string[];
}

const ANGEL_URL = 'http://127.0.0.1:8089';
const TIMEOUT_MS = 5000;

/**
 * Fetch Morning Brief from Angel API
 * Returns only WAITING_DECISION projects
 */
export async function getMorningBrief(): Promise<JulesProject[]> {
    return new Promise((resolve) => {
        const req = http.get(`${ANGEL_URL}/jules/morning-brief`, (res) => {
            let data = '';
            res.on('data', (chunk: Buffer) => data += chunk.toString());
            res.on('end', () => {
                try {
                    const brief: MorningBrief = JSON.parse(data);
                    const candidates = brief.candidates || [];
                    // Filter only waiting projects
                    const waiting = candidates.filter(c => c.status === 'WAITING_DECISION');
                    resolve(waiting);
                } catch {
                    resolve([]);
                }
            });
        });

        req.on('error', () => resolve([]));
        req.setTimeout(TIMEOUT_MS, () => {
            req.destroy();
            resolve([]);
        });
    });
}

/**
 * Get pending projects count (for badge)
 */
export async function getPendingCount(): Promise<number> {
    return new Promise((resolve) => {
        const req = http.get(`${ANGEL_URL}/jules/pending`, (res) => {
            let data = '';
            res.on('data', (chunk: Buffer) => data += chunk.toString());
            res.on('end', () => {
                try {
                    const pending = JSON.parse(data);
                    resolve(Array.isArray(pending) ? pending.length : 0);
                } catch {
                    resolve(0);
                }
            });
        });

        req.on('error', () => resolve(0));
        req.setTimeout(TIMEOUT_MS, () => {
            req.destroy();
            resolve(0);
        });
    });
}

/**
 * Send decision to Angel API
 */
export async function sendDecision(
    projectId: string,
    decision: 'MERGE' | 'PENDING' | 'REJECT',
    prUrl?: string
): Promise<boolean> {
    return new Promise((resolve) => {
        const payload = JSON.stringify({
            project_id: projectId,
            decision: decision,
            pr_url: prUrl
        });

        const options = {
            hostname: '127.0.0.1',
            port: 8089,
            path: '/jules/decision',
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(payload)
            },
            timeout: TIMEOUT_MS
        };

        const req = http.request(options, (res) => {
            resolve(res.statusCode === 200);
        });

        req.on('error', () => resolve(false));
        req.on('timeout', () => {
            req.destroy();
            resolve(false);
        });

        req.write(payload);
        req.end();
    });
}

/**
 * Format project for chat message
 */
export function formatProjectForChat(project: JulesProject): string {
    const confidenceEmoji = project.confidence >= 80 ? '🟢' : project.confidence >= 60 ? '🟡' : '🔴';
    const sourceEmoji = project.source?.includes('JULES') ? '🤖' : '🧠';

    let message = `Analyze and give your opinion on this improvement:\n\n`;
    message += `${sourceEmoji} **Projet Jules: ${project.title}**\n\n`;
    message += `${confidenceEmoji} **Confidence**: ${project.confidence}%\n\n`;
    message += `**Description**:\n${project.description}\n\n`;

    if (project.pr_url) {
        message += `**PR**: ${project.pr_url}\n\n`;
    }

    return message;
}

// ============================================================================
// SOTA 2026: Staged Projects API
// ============================================================================

/**
 * Fetch Staged Projects from Angel API
 * These are executed projects ready for human review
 */
export async function getStagedProjects(): Promise<StagedProject[]> {
    return new Promise((resolve) => {
        const req = http.get(`${ANGEL_URL}/jules/staged-projects`, (res) => {
            let data = '';
            res.on('data', (chunk: Buffer) => data += chunk.toString());
            res.on('end', () => {
                try {
                    const response = JSON.parse(data);
                    resolve(response.projects || []);
                } catch {
                    resolve([]);
                }
            });
        });

        req.on('error', () => resolve([]));
        req.setTimeout(TIMEOUT_MS, () => {
            req.destroy();
            resolve([]);
        });
    });
}

/**
 * Fetch diff for a specific staged project
 */
export async function getProjectDiff(projectId: string): Promise<string | null> {
    return new Promise((resolve) => {
        const req = http.get(`${ANGEL_URL}/jules/project/${projectId}/diff`, (res) => {
            let data = '';
            res.on('data', (chunk: Buffer) => data += chunk.toString());
            res.on('end', () => {
                try {
                    const response = JSON.parse(data);
                    resolve(response.diff || null);
                } catch {
                    resolve(null);
                }
            });
        });

        req.on('error', () => resolve(null));
        req.setTimeout(TIMEOUT_MS, () => {
            req.destroy();
            resolve(null);
        });
    });
}

/**
 * Format staged project for chat message (with diff)
 */
export function formatStagedProjectForChat(project: StagedProject, diff?: string): string {
    let message = `Analyze this code change from Jules and tell me whether I should merge it:\n\n`;
    message += `🤖 **${project.title}**\n\n`;
    message += `📁 **${project.files_count} file(s)** changed: +${project.additions} / -${project.deletions}\n\n`;

    if (project.files.length > 0) {
        message += `**Files modified:**\n`;
        project.files.slice(0, 10).forEach(f => {
            message += `- \`${f}\`\n`;
        });
        if (project.files.length > 10) {
            message += `- ... and ${project.files.length - 10} more\n`;
        }
        message += `\n`;
    }

    if (project.pr_url) {
        message += `**PR**: ${project.pr_url}\n\n`;
    }

    if (diff) {
        // Limit diff to first 2000 chars to avoid overwhelming the chat
        const truncatedDiff = diff.length > 2000 ? diff.slice(0, 2000) + '\n... [truncated]' : diff;
        message += `**Diff:**\n\`\`\`diff\n${truncatedDiff}\n\`\`\`\n`;
    }

    return message;
}
