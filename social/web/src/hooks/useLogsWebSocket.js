/**
 * SOTA 2026: WebSocket Hook for Real-time Logs
 * Connects to /ws/logs with auth token and manages reconnection.
 */

import { useEffect, useRef, useCallback } from 'react';
import { useTrinityStore } from '../stores/trinityStore';

// Get bootstrap token (same as angelService)
const BOOTSTRAP_TOKEN = typeof __ANGEL_BOOTSTRAP_TOKEN__ !== 'undefined'
    ? __ANGEL_BOOTSTRAP_TOKEN__
    : 'trinity-offline-sota-2026';

export const useLogsWebSocket = () => {
    const wsRef = useRef(null);
    const reconnectTimeoutRef = useRef(null);
    const { mergeLogs, clearLogs, setAlive, setPendingGaze } = useTrinityStore();

    const connect = useCallback(() => {
        // SOTA 2026: Pure Web - Build WebSocket URL from current origin
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/logs?token=${BOOTSTRAP_TOKEN}`;

        // Clean up existing connection
        if (wsRef.current) {
            wsRef.current.close();
        }

        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
            console.log('[WS] Connected to /ws/logs');
            setAlive(true);
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                if (data.type === 'history') {
                    // Initial history load (89 lines)
                    if (data.logs && data.logs.length > 0) {
                        mergeLogs(data.logs);
                    }
                } else if (data.type === 'log') {
                    // Single live log
                    mergeLogs([data]);
                    // SOTA 2026: Trigger error animation on critical errors
                    const level = (data.level || data.type || '').toUpperCase();
                    if (level === 'ERR' || level === 'ERROR') {
                        setPendingGaze('error');
                    };
                } else if (data.type === 'clear') {
                    // Server cleared logs - clear local store
                    clearLogs(data.tab);
                } else if (data.type === 'ping') {
                    // Keep-alive ping from server, no action needed
                }
            } catch (e) {
                console.warn('[WS] Parse error:', e);
            }
        };

        ws.onclose = (event) => {
            console.log('[WS] Disconnected:', event.code);
            setAlive(false);
            wsRef.current = null;

            // Reconnect after 3s (unless intentional close)
            if (event.code !== 1000) {
                reconnectTimeoutRef.current = setTimeout(connect, 3000);
            }
        };

        ws.onerror = (error) => {
            console.error('[WS] Error:', error);
        };
    }, [mergeLogs, clearLogs, setAlive, setPendingGaze]);

    const disconnect = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
        }
        if (wsRef.current) {
            wsRef.current.close(1000, 'User disconnect');
            wsRef.current = null;
        }
    }, []);

    // Auto-connect on mount
    useEffect(() => {
        connect();
        return () => disconnect();
    }, [connect, disconnect]);

    return {
        isConnected: wsRef.current?.readyState === WebSocket.OPEN,
        reconnect: connect,
        disconnect,
    };
};

export default useLogsWebSocket;
