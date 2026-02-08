/**
 * NATIVE MESSAGE FEED COMPONENT (SOTA 2026)
 * ═══════════════════════════════════════════════════════════════════════════
 * Standard "Messenger-style" list for Panel 2.
 * Replaces redundant "Fake Phone" UI.
 * ═══════════════════════════════════════════════════════════════════════════
 */

import React, { useState, useEffect, useRef } from 'react';
import { Zap, Mail, User, X, Trash2, Calendar, Megaphone, Bot, ArrowLeft } from 'lucide-react';
import { useNotificationStore } from '../../stores/notificationStore';
import './NativeMessageFeed.css';
import '../notifications/NotificationPhone.css'; // Reusing report styles

/**
 * Icon Factory
 */
const getSourceIcon = (source) => {
    const s = (source || '').toUpperCase();
    if (s.includes('TRADER') || s.includes('MARKET')) return <Zap size={14} />;
    if (s.includes('EMAIL')) return <Mail size={14} />;
    if (s.includes('JULES') || s.includes('COUNCIL')) return <Bot size={14} />;
    if (s.includes('SCHEDULER')) return <Calendar size={14} />;
    if (s.includes('INFLUENCER')) return <Megaphone size={14} />;
    return <User size={14} />;
};

/**
 * Type & Color Logic
 */
const getNotifType = (source) => {
    const s = (source || '').toUpperCase();
    if (s.includes('TRADER') || s.includes('MARKET')) return { type: 'TRADER', color: '#ffd700', label: 'TRADER' };
    if (s.includes('JULES') || s.includes('COUNCIL')) return { type: 'JULES', color: '#00ffdd', label: 'JULES' };
    if (s.includes('SCHEDULER')) return { type: 'SCHEDULER', color: '#888888', label: 'SCHEDULER' };
    if (s.includes('INFLUENCER')) return { type: 'INFLUENCER', color: '#ff00ff', label: 'INFLUENCER' };
    if (s.includes('SECURITY')) return { type: 'SECURITY', color: '#ff0055', label: 'SECURITY' };
    if (s.includes('EMAIL')) return { type: 'EMAIL', color: '#bd00ff', label: 'EMAIL' };
    return { type: 'SYSTEM', color: '#00ffdd', label: 'SYSTEM' };
};

/**
 * Relative Time
 */
const formatTime = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    const now = new Date();
    const diff = (now - date) / 60000;

    if (diff < 1) return 'NOW';
    if (diff < 60) return `${Math.floor(diff)}m`;

    const hours = diff / 60;
    if (hours < 24) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
};

export default function NativeMessageFeed() {
    const {
        notifications,
        markAsRead,
        dismissNotification,
        fetchNotifications,
        selectedNotificationId,
        clearSelectedNotification
    } = useNotificationStore();

    const [selectedNotif, setSelectedNotif] = useState(null);
    const listRef = useRef(null);

    // Handlers (defined first so useEffects can reference them)
    const handleSelect = (notif) => {
        markAsRead(notif.id);
        setSelectedNotif(notif);
    };

    const handleDismiss = (e, id) => {
        e.stopPropagation();
        dismissNotification(id);
        if (selectedNotif?.id === id) setSelectedNotif(null);
    };

    // Initial fetch + Polling
    useEffect(() => {
        fetchNotifications();
        const interval = setInterval(fetchNotifications, 10000);
        return () => clearInterval(interval);
    }, [fetchNotifications]);

    // SOTA 2026: Deep-link auto-open from push notification
    useEffect(() => {
        if (selectedNotificationId && notifications.length > 0) {
            // String comparison for safety (FCM sends string IDs)
            const targetNotif = notifications.find(n => String(n.id) === String(selectedNotificationId));
            if (targetNotif) {
                handleSelect(targetNotif);
                clearSelectedNotification();
            }
        }
    }, [selectedNotificationId, notifications, clearSelectedNotification]);

    return (
        <div className="native-feed-container">
            {/* List */}
            <div className="native-list-scroll" ref={listRef}>
                {notifications.length === 0 && (
                    <div className="native-empty-state">
                        <Mail className="native-empty-icon" />
                        <span className="native-empty-text">NO MESSAGES</span>
                    </div>
                )}

                {notifications.map((notif) => {
                    const { type, color, label } = getNotifType(notif.source);

                    // Smart Truncation
                    let title = notif.title || notif.body?.substring(0, 80) || 'Notification';
                    if (title.length >= 80) title += '...';

                    return (
                        <div
                            key={notif.id}
                            className={`native-card ${!notif.read ? 'unread' : ''}`}
                            onClick={() => handleSelect(notif)}
                            style={{ '--accent-color': color }}
                        >
                            <div className="native-accent" style={{ background: color }} />

                            <div className="native-content">
                                <div className="native-header">
                                    <div className="native-source" style={{ color }}>
                                        {getSourceIcon(notif.source)}
                                        <span>{label}</span>
                                    </div>
                                    <div className="native-meta">
                                        {!notif.read && <span className="native-unread-dot" style={{ background: color }} />}
                                        <span className="native-time">{formatTime(notif.timestamp)}</span>
                                    </div>
                                </div>
                                <div className="native-title">
                                    {title}
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Fullscreen Detail View (Modal) */}
            {selectedNotif && (
                <div className="native-modal-overlay">
                    <div className="native-modal">
                        {/* Header */}
                        <div className="native-modal-header">
                            <button className="native-modal-close" onClick={() => setSelectedNotif(null)}>
                                <ArrowLeft size={24} />
                            </button>
                            <div className="native-source" style={{
                                color: getNotifType(selectedNotif.source).color,
                                fontSize: '14px'
                            }}>
                                {getSourceIcon(selectedNotif.source)}
                                <span>{getNotifType(selectedNotif.source).label}</span>
                            </div>
                            <div style={{ width: 36 }} /> {/* Spacer */}
                        </div>

                        {/* Body */}
                        <div className="native-modal-body modal-content"> {/* Added modal-content class for report styles */}
                            <h2 style={{ marginBottom: 16, fontSize: 20, fontWeight: 700 }}>
                                {selectedNotif.title}
                            </h2>
                            <div dangerouslySetInnerHTML={{ __html: selectedNotif.body }} />
                        </div>

                        {/* Footer Actions */}
                        <div className="native-modal-actions">
                            <button
                                className="native-btn delete"
                                onClick={(e) => handleDismiss(e, selectedNotif.id)}
                            >
                                <Trash2 size={20} />
                                DELETE MESSAGE
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
