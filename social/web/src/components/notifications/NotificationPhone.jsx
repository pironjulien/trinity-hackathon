/**
 * NOTIFICATION PHONE COMPONENT (SOTA 2026 - CYBERPUNK EDITION)
 * ═══════════════════════════════════════════════════════════════════════════
 * Simulates a high-tech transparent smartphone with cyberpunk aesthetics.
 * Features: Clean Status Bar, Glitch Effects, Neon Accents.
 * ═══════════════════════════════════════════════════════════════════════════
 */

import { useState, useRef, useEffect } from 'react';
import { Zap, Mail, User, X, Trash2, Wifi, Calendar, Bot, Megaphone } from 'lucide-react';
import { useNotificationStore } from '../../stores/notificationStore';
import './NotificationPhone.css';

/**
 * Icon Factory - Returns icon based on source type
 */
const getSourceIcon = (source) => {
    const s = (source || '').toUpperCase();
    if (s.includes('TRADER') || s.includes('MARKET')) return <Zap size={12} />;
    if (s.includes('EMAIL')) return <Mail size={12} />;
    if (s.includes('JULES') || s.includes('COUNCIL')) return <Bot size={12} />;
    if (s.includes('SCHEDULER')) return <Calendar size={12} />;
    if (s.includes('INFLUENCER')) return <Megaphone size={12} />;
    return <User size={12} />;
};

/**
 * Get notification type and associated color
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
 * Format timestamp to relative time
 */
const formatTime = (timestamp) => {
    if (!timestamp) return '';
    const diff = (Date.now() - new Date(timestamp).getTime()) / 60000;
    if (diff < 1) return 'NOW';
    if (diff < 60) return `${Math.floor(diff)}m`;
    const hours = diff / 60;
    if (hours < 24) return `${Math.floor(hours)}h`;
    return `${Math.floor(hours / 24)}d`;
};

export default function NotificationPhone() {
    const {
        notifications,
        markAsRead,
        dismissNotification,
        fetchNotifications
    } = useNotificationStore();

    const [selectedNotif, setSelectedNotif] = useState(null);
    const [currentTime, setCurrentTime] = useState(new Date());
    const [isOnline, setIsOnline] = useState(navigator.onLine);
    const [hoveredId, setHoveredId] = useState(null);
    const listRef = useRef(null);

    // Live Clock & Network Update
    useEffect(() => {
        const timer = setInterval(() => setCurrentTime(new Date()), 1000);
        const handleOnline = () => setIsOnline(true);
        const handleOffline = () => setIsOnline(false);

        window.addEventListener('online', handleOnline);
        window.addEventListener('offline', handleOffline);

        return () => {
            clearInterval(timer);
            window.removeEventListener('online', handleOnline);
            window.removeEventListener('offline', handleOffline);
        };
    }, []);

    // SOTA 2026: Notification Polling (Standard 362)
    useEffect(() => {
        fetchNotifications();
        const pollInterval = setInterval(fetchNotifications, 10000);
        return () => clearInterval(pollInterval);
    }, [fetchNotifications]);

    const handleSelect = (notif) => {
        markAsRead(notif.id);
        setSelectedNotif(notif);
    };

    const handleDismiss = (e, id) => {
        e.stopPropagation();
        dismissNotification(id);
        if (selectedNotif?.id === id) setSelectedNotif(null);
    };

    return (
        <div className="notification-phone-container">
            {/* ─── STATUS BAR ─── */}
            <div className="phone-status-bar">
                <span className="status-time">
                    {currentTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
                <Wifi size={14} className={`status-wifi ${isOnline ? 'online' : 'offline'}`} />
            </div>

            {/* ─── SCROLLABLE CONTENT ─── */}
            <div className="notification-list-scroll" ref={listRef}>
                {notifications.length === 0 && (
                    <div className="empty-state">
                        <span className="empty-icon">◈</span>
                        <span className="empty-text">NO SIGNALS</span>
                    </div>
                )}

                {notifications.map((notif) => {
                    const { type, color, label } = getNotifType(notif.source);
                    const isHovered = hoveredId === notif.id;
                    // SOTA 2026: Word-boundary truncation to prevent mid-word cuts
                    let title = notif.title || notif.body?.substring(0, 100) || 'Notification';
                    if (title.length >= 100 && !title.endsWith(' ')) {
                        const lastSpace = title.lastIndexOf(' ');
                        if (lastSpace > 50) title = title.substring(0, lastSpace) + '…';
                    }

                    return (
                        <div
                            key={notif.id}
                            className={`notif-card ${!notif.read ? 'unread' : ''}`}
                            data-type={type}
                            style={{ '--accent-color': color }}
                            onClick={() => handleSelect(notif)}
                            onMouseEnter={() => setHoveredId(notif.id)}
                            onMouseLeave={() => setHoveredId(null)}
                        >
                            {/* Accent Border */}
                            <div className="notif-accent" style={{ background: color }} />

                            {/* Content */}
                            <div className="notif-content">
                                {/* Header Row: Source + Time */}
                                <div className="notif-header">
                                    <div className="notif-source" style={{ color }}>
                                        {getSourceIcon(notif.source)}
                                        <span>{label}</span>
                                    </div>
                                    <div className="notif-meta">
                                        {!notif.read && <span className="unread-dot" style={{ background: color, boxShadow: `0 0 8px ${color}` }} />}
                                        <span className="notif-time">{formatTime(notif.timestamp)}</span>
                                    </div>
                                </div>

                                {/* Title Only */}
                                <div className="notif-title">{title}</div>
                            </div>

                            {/* Delete Button - Slides in on Hover */}
                            <button
                                className={`notif-delete ${isHovered ? 'visible' : ''}`}
                                onClick={(e) => handleDismiss(e, notif.id)}
                                aria-label="Delete notification"
                            >
                                <Trash2 size={14} />
                            </button>
                        </div>
                    );
                })}
            </div>

            {/* ─── HOME INDICATOR ─── */}
            <div className="phone-home-area">
                <div className="home-indicator" />
            </div>

            {/* ─── DETAIL MODAL ─── */}
            {selectedNotif && (
                <div className="notif-modal-overlay" onClick={() => setSelectedNotif(null)}>
                    <div className="notif-modal" onClick={e => e.stopPropagation()}>
                        {/* Modal Header */}
                        <div className="modal-header">
                            <div className="modal-source" style={{ color: getNotifType(selectedNotif.source).color }}>
                                {getSourceIcon(selectedNotif.source)}
                                <span>{getNotifType(selectedNotif.source).label}</span>
                            </div>
                            <button className="modal-close" onClick={() => setSelectedNotif(null)}>
                                <X size={18} />
                            </button>
                        </div>

                        {/* Modal Body */}
                        <div className="modal-body">
                            <h3 className="modal-title">{selectedNotif.title}</h3>
                            <div
                                className="modal-content"
                                dangerouslySetInnerHTML={{ __html: selectedNotif.body }}
                            />
                        </div>

                        {/* Modal Actions */}
                        <div className="modal-actions">
                            <button
                                className="modal-btn delete"
                                onClick={(e) => handleDismiss(e, selectedNotif.id)}
                            >
                                <Trash2 size={14} />
                                <span>DELETE</span>
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
