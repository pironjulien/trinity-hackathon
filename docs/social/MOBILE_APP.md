# 📱 Mobile App - React + Capacitor

> **Trinity's window to the physical world.** A native Android app built with React and Capacitor.

---

## 🔥 Key Features

### 1. Real-Time Message Feed
Live stream of Trinity's internal monologue:

```jsx
// social/web/src/views/MessagesView.jsx
const { messages, unreadCount } = useAngelMessages();

return (
  <MessageCard
    icon={getEmoji(msg.type)}
    message={msg.content}
    timestamp={msg.timestamp}
  />
);
```

### 2. Push Notifications (FCM)
Native notifications via Firebase Cloud Messaging:

```python
# jobs/notifier.py
from firebase_admin import messaging

message = messaging.Message(
    notification=messaging.Notification(
        title="Trinity Alert",
        body="Trade executed: +2.3% on BTC/USDT"
    ),
    token=device_token
)
messaging.send(message)
```

### 3. Deep Linking
Notifications open specific messages:

```java
// MainActivity.java
Intent intent = getIntent();
if (intent != null && intent.hasExtra("message_id")) {
    navigateToMessage(intent.getStringExtra("message_id"));
}
```

### 4. Haptic Feedback
Premium tactile responses:

```java
// Native haptics on notification
Vibrator v = (Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
v.vibrate(VibrationEffect.createOneShot(100, VibrationEffect.DEFAULT_AMPLITUDE));
```

---

## 🧠 Google Ecosystem Integration

| Service | Purpose |
|---------|---------|
| **Firebase/FCM** | Push notifications |
| **Google Sign-In** | Authentication (planned) |
| **Play Store** | Distribution |

---

## 📊 Tech Stack

```
social/web/
├── src/
│   ├── views/         # Page components
│   │   ├── MessagesView.jsx
│   │   └── DashboardView.jsx
│   ├── components/    # Reusable UI
│   │   ├── MessageCard.jsx
│   │   └── AngelSplash.jsx
│   ├── services/      # API clients
│   │   └── angelService.js
│   └── MobileApp.jsx  # Main entry
├── android/           # Capacitor native
│   └── app/
│       ├── src/main/java/.../MainActivity.java
│       └── build.gradle
└── capacitor.config.ts
```

---

## 🎨 Design System

- **Dark Mode**: Default, eye-friendly
- **Accent Color**: Blue (#4285F4)
- **Typography**: Inter, system fonts
- **Animations**: Smooth transitions, loading states

---

## 📲 Build & Deploy

```bash
# Build web app
npm run build

# Sync to Android
npx cap sync android

# Build APK
cd android && ./gradlew assembleRelease
```

---

> **Key Insight**: The mobile app provides a human interface to an autonomous AI - observation without interference.
