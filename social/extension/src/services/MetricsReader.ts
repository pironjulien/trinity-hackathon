/**
 * MetricsReader (SOTA 2026 Extended)
 * ===================================
 * Reads `metrics.bin` (Shared Memory / Mmap file)
 * Format: 12 doubles (96 bytes)
 * [sys_cpu, sys_ram, sys_disk, angel_cpu, angel_ram, trinity_cpu, trinity_ram, 
 *  chrome_cpu, chrome_ram, antigravity_cpu, antigravity_ram, timestamp]
 */

import * as fs from 'fs';
import * as path from 'path';

export interface SystemMetrics {
    sys_cpu: number;
    sys_ram: number;
    sys_disk: number;
    angel_cpu: number;
    angel_ram: number;
    trinity_cpu: number;
    trinity_ram: number;
    chrome_cpu: number;
    chrome_ram: number;
    antigravity_cpu: number;
    antigravity_ram: number;
    ubuntu_cpu: number;
    ubuntu_ram: number;
    timestamp: number;
    stale: boolean;  // True if data is > 2 seconds old
}

export class MetricsReader {
    private _path: string;
    private _buffer: Buffer;
    private static STALE_THRESHOLD_MS = 2000;  // 2 seconds

    constructor(workspacePath: string) {
        this._path = path.join(workspacePath, 'memories', 'state', 'metrics.bin');
        this._buffer = Buffer.alloc(96); // 12 * 8 bytes (double)
    }

    public read(): SystemMetrics | null {
        try {
            if (!fs.existsSync(this._path)) return null;

            // Direct Sync Read for Speed
            // Size: 12 doubles * 8 = 96 bytes (Added Ubuntu)
            const fd = fs.openSync(this._path, 'r');
            fs.readSync(fd, this._buffer, 0, 96, 0);
            fs.closeSync(fd);

            const timestamp = this._buffer.readDoubleLE(88);
            const age = Date.now() - (timestamp * 1000);

            return {
                sys_cpu: this._buffer.readDoubleLE(0),
                sys_ram: this._buffer.readDoubleLE(8),
                sys_disk: this._buffer.readDoubleLE(16),
                angel_cpu: this._buffer.readDoubleLE(24),
                angel_ram: this._buffer.readDoubleLE(32),
                trinity_cpu: this._buffer.readDoubleLE(40),
                trinity_ram: this._buffer.readDoubleLE(48),
                // Chrome Removed (Was 56, 64) -> Now mocked zero
                chrome_cpu: 0,
                chrome_ram: 0,
                // Shifted due to Chrome removal + Ubuntu addition
                // AG: 56, 64
                antigravity_cpu: this._buffer.readDoubleLE(56),
                antigravity_ram: this._buffer.readDoubleLE(64),
                // Ubuntu: 72, 80
                ubuntu_cpu: this._buffer.readDoubleLE(72),
                ubuntu_ram: this._buffer.readDoubleLE(80),
                timestamp: timestamp,
                stale: age > MetricsReader.STALE_THRESHOLD_MS
            };

        } catch (e) {
            // Fail silently (stats are ephemeral)
            return null;
        }
    }
}

