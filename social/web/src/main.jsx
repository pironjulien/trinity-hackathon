import { createRoot } from 'react-dom/client'
import { Capacitor } from '@capacitor/core'
import { PushNotifications } from '@capacitor/push-notifications'
import './index.css'
import App from './App.jsx'
import MobileApp from './MobileApp.jsx'

// SOTA 2026: Early Push Notification Handler (Cold Start Fix)
// Register SYNCHRONOUSLY BEFORE React mounts to capture notification that opened the app
if (Capacitor.isNativePlatform()) {
  console.log('[MAIN.JSX] Registering early push notification listener...');

  // Listen for notification action IMMEDIATELY (synchronous)
  PushNotifications.addListener('pushNotificationActionPerformed', (action) => {
    console.log('[MAIN.JSX] Early pushNotificationActionPerformed:', action);
    console.log('[MAIN.JSX] Notification data:', JSON.stringify(action.notification?.data, null, 2));

    // Store for MobileApp to consume after React mounts
    window.__pendingNotificationAction = action;
    console.log('[MAIN.JSX] Stored pending action on window.__pendingNotificationAction');
  });

  console.log('[MAIN.JSX] Early push listener registered BEFORE React render');
}

// SOTA 2026: Use MobileApp for Capacitor Android OR mobile web browsers
const isMobile = Capacitor.isNativePlatform() || window.innerWidth < 900
const RootComponent = isMobile ? MobileApp : App

createRoot(document.getElementById('root')).render(
  <RootComponent />
)
