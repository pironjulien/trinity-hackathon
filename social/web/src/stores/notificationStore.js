/**
 * NOTIFICATION STORE (Zustand)
 * ═══════════════════════════════════════════════════════════════════════════
 * State management for notifications.
 * Integrated in-app notification system (Phone Widget + FCM).
 * ═══════════════════════════════════════════════════════════════════════════
 */

import { create } from 'zustand';
import { getHeaders, ANGEL_BASE_URL } from '../services/angelService';

/**
 * Get API URL with base path from angelService
 */
const getApiUrl = (path = '') => {
    return `${ANGEL_BASE_URL}${path}`;
};

export const useNotificationStore = create((set, get) => ({
    // State
    notifications: [],
    unreadCount: 0,
    loading: false,
    error: null,
    selectedNotificationId: null, // SOTA 2026: Deep-linking from push notifications

    /**
     * SOTA 2026: Select a notification by ID (for deep-linking)
     */
    selectNotificationById: (id) => {
        set({ selectedNotificationId: id });
    },

    /**
     * Clear selected notification ID
     */
    clearSelectedNotification: () => {
        set({ selectedNotificationId: null });
    },

    /**
     * Fetch notifications from backend
     */
    fetchNotifications: async () => {
        try {
            const response = await fetch(`${getApiUrl()}/notifications`, {
                headers: {
                    ...getHeaders(),
                    'Authorization': `Bearer ${localStorage.getItem('trinity_token') || ''}`,
                },
            });

            if (!response.ok) {
                throw new Error('Failed to fetch notifications');
            }

            const data = await response.json();
            const notifications = data.notifications || [];
            const unreadCount = notifications.filter(n => !n.read).length;

            set({ notifications, unreadCount, error: null });
        } catch (error) {
            console.warn('Notification fetch failed:', error);
            // Don't spam errors, just log warning
        }
    },

    /**
     * Mark notification as read
     */
    markAsRead: async (notificationId) => {
        try {
            await fetch(`${getApiUrl()}/notifications/read/${notificationId}`, {
                method: 'POST',
                headers: {
                    ...getHeaders(),
                    'Authorization': `Bearer ${localStorage.getItem('trinity_token') || ''}`,
                },
            });

            // Optimistic update
            set((state) => ({
                notifications: state.notifications.map(n =>
                    n.id === notificationId ? { ...n, read: true } : n
                ),
                unreadCount: Math.max(0, state.unreadCount - 1),
            }));
        } catch (error) {
            console.error('Failed to mark notification as read:', error);
        }
    },

    /**
     * Execute action on notification (button click)
     */
    executeAction: async (notificationId, actionId) => {
        try {
            const response = await fetch(`${getApiUrl()}/notifications/action?notification_id=${notificationId}&action_id=${actionId}`, {
                method: 'POST',
                headers: {
                    ...getHeaders(),
                    'Authorization': `Bearer ${localStorage.getItem('trinity_token') || ''}`,
                },
            });

            if (!response.ok) {
                throw new Error('Action failed');
            }

            // Remove notification after action executed
            set((state) => ({
                notifications: state.notifications.filter(n => n.id !== notificationId),
                unreadCount: state.notifications.find(n => n.id === notificationId && !n.read)
                    ? state.unreadCount - 1
                    : state.unreadCount,
            }));

            return true;
        } catch (error) {
            console.error('Failed to execute action:', error);
            return false;
        }
    },

    /**
     * Add notification locally (for testing/mock)
     */
    addNotification: (notification) => {
        const newNotif = {
            id: Date.now().toString(),
            timestamp: new Date().toISOString(),
            read: false,
            isNew: true,
            ...notification,
        };

        set((state) => ({
            notifications: [newNotif, ...state.notifications],
            unreadCount: state.unreadCount + 1,
        }));

        // Remove 'new' flag after animation
        setTimeout(() => {
            set((state) => ({
                notifications: state.notifications.map(n =>
                    n.id === newNotif.id ? { ...n, isNew: false } : n
                ),
            }));
        }, 300);
    },

    /**
     * Dismiss a single notification (remove from list)
     */
    dismissNotification: async (notificationId) => {
        // Optimistic update first
        set((state) => ({
            notifications: state.notifications.filter(n => n.id !== notificationId),
            unreadCount: state.notifications.find(n => n.id === notificationId && !n.read)
                ? state.unreadCount - 1
                : state.unreadCount,
        }));

        // Then persist to backend
        try {
            await fetch(`${getApiUrl()}/notifications/dismiss/${notificationId}`, {
                method: 'POST',
                headers: {
                    ...getHeaders(),
                    'Authorization': `Bearer ${localStorage.getItem('trinity_token') || ''}`,
                },
            });
        } catch (error) {
            console.error('Failed to dismiss notification:', error);
        }
    },

    /**
     * Clear all notifications
     */
    clearAll: () => {
        set({ notifications: [], unreadCount: 0 });
    },
}));

export default useNotificationStore;
