import { useState, useCallback, useEffect, useRef } from 'react';
import { signInWithEmailAndPassword, signInWithCredential, signInWithPopup, GoogleAuthProvider, signOut, getAuth } from 'firebase/auth';
import { auth } from '../config/firebase';
import { Capacitor } from '@capacitor/core';
import { FirebaseAuthentication } from '@capacitor-firebase/authentication';

// Email domain for Firebase users (e.g., admin -> admin@trinity.local)
const EMAIL_DOMAIN = '@trinity.local';

// Allowlist for Google Sign-In (only these emails can login via Google)
const ALLOWED_GOOGLE_EMAILS = [
    'julienpiron.fr@gmail.com',  // Admin
    // Add other authorized Google emails here
];

// Convert identity to email format for Firebase
const toEmail = (identity) => {
    if (identity.includes('@')) return identity;
    return `${identity.toLowerCase()}${EMAIL_DOMAIN}`;
};

// Check if Google email is authorized
const isGoogleEmailAllowed = (email) => {
    return ALLOWED_GOOGLE_EMAILS.some(
        allowed => allowed.toLowerCase() === email.toLowerCase()
    );
};

export const useAuthSequence = ({ onSuccess, onError } = {}) => {
    const [authState, setAuthState] = useState('idle'); // idle, authenticating, imploding, success, error
    const [identity, setIdentity] = useState('');
    const [passkey, setPasskey] = useState('');
    const [statusMessage, setStatusMessage] = useState('');

    // Email/Password Authentication
    const handleAuth = useCallback(async () => {
        if (!identity?.trim() || !passkey?.trim()) return;

        setAuthState('imploding');

        setTimeout(async () => {
            setAuthState('authenticating');
            setStatusMessage('INITIALIZING FIREBASE HANDSHAKE...');

            try {
                const email = toEmail(identity);
                const userCredential = await signInWithEmailAndPassword(auth, email, passkey);

                setStatusMessage(`Welcome ${userCredential.user.email?.split('@')[0] || identity}. Entropy reduced by 40%.`);

                setTimeout(() => {
                    setAuthState('success');
                    if (onSuccess) onSuccess(identity, userCredential.user);
                }, 1000);

            } catch (error) {
                console.error('Firebase Auth Error:', error.code);

                let message = 'ACCESS DENIED.';
                switch (error.code) {
                    case 'auth/invalid-credential':
                    case 'auth/wrong-password':
                    case 'auth/user-not-found':
                        message = 'ACCESS DENIED. INVALID CREDENTIALS.';
                        break;
                    case 'auth/too-many-requests':
                        message = 'ACCESS DENIED. TOO MANY ATTEMPTS.';
                        break;
                    case 'auth/network-request-failed':
                        message = 'NETWORK ERROR. CHECK CONNECTION.';
                        break;
                    default:
                        message = 'AUTHENTICATION FAILED.';
                }

                setAuthState('error');
                setStatusMessage(message);
                if (onError) onError(error);

                setTimeout(() => {
                    setAuthState('idle');
                    setStatusMessage('');
                }, 2000);
            }
        }, 800);

    }, [identity, passkey, onSuccess, onError]);

    // SOTA 2026: Google Sign-In with Native Plugin (Capacitor) or Web Popup (Browser)
    const handleGoogleAuth = useCallback(async () => {
        setAuthState('imploding');

        setTimeout(async () => {
            setAuthState('authenticating');
            setStatusMessage('GOOGLE HANDSHAKE...');

            try {
                const isNative = Capacitor.isNativePlatform();
                let userEmail, firebaseUser;

                if (isNative) {
                    // SOTA 2026: Native Google Sign-In via Capacitor Firebase Plugin
                    // DIRECT PATH - NO WEB FALLBACK to avoid storage partitioning errors
                    console.log('[Auth] Executing Native Google Sign-In');

                    try {
                        const result = await FirebaseAuthentication.signInWithGoogle();

                        const idToken = result.credential?.idToken;
                        if (!idToken) {
                            throw new Error('Native success but NO ID TOKEN received.');
                        }

                        const credential = GoogleAuthProvider.credential(idToken);
                        const userCredential = await signInWithCredential(auth, credential);

                        userEmail = userCredential.user.email;
                        firebaseUser = userCredential.user;
                    } catch (nativeErr) {
                        // CRITICAL: Do NOT fallback to web. Alert the user to the config error.
                        console.error('[Auth] Native Crash:', nativeErr);
                        alert(`❌ NATIVE AUTH ERROR:\n${nativeErr.message}\n\n(Check SHA-1 in Firebase Console)`);
                        setStatusMessage('AUTH COMPROMISED');
                        setAuthState('idle');
                        return;
                    }
                } else {
                    // Web: Use popup (works in browser)
                    console.log('[Auth] Using web popup Google Sign-In');
                    const provider = new GoogleAuthProvider();
                    const result = await signInWithPopup(auth, provider);

                    userEmail = result.user.email;
                    firebaseUser = result.user;
                }

                // Check allowlist
                if (!isGoogleEmailAllowed(userEmail)) {
                    await signOut(auth);
                    if (Capacitor.isNativePlatform()) {
                        await FirebaseAuthentication.signOut();
                    }
                    setAuthState('error');
                    setStatusMessage('ACCESS DENIED. EMAIL NOT AUTHORIZED.');
                    if (onError) onError(new Error('Email not authorized'));
                    setTimeout(() => {
                        setAuthState('idle');
                        setStatusMessage('');
                    }, 2000);
                    return;
                }

                // Authorized
                setStatusMessage(`Welcome ${userEmail.split('@')[0]}. Google verified.`);
                setAuthState('success');
                if (onSuccess) onSuccess(userEmail.split('@')[0], firebaseUser);

            } catch (error) {
                console.error('Google Auth Error:', error);

                let message = 'GOOGLE AUTH FAILED.';
                if (error.code === 'auth/popup-closed-by-user' || error.message?.includes('cancelled')) {
                    message = 'LOGIN CANCELLED.';
                } else if (error.code === 'auth/popup-blocked') {
                    message = 'POPUP BLOCKED. ALLOW POPUPS.';
                } else {
                    message = `ERROR: ${error.code || error.message || 'UNKNOWN'}`;
                }

                setAuthState('error');
                setStatusMessage(message);
                if (onError) onError(error);

                setTimeout(() => {
                    setAuthState('idle');
                    setStatusMessage('');
                }, 4000);
            }
        }, 500);

    }, [onSuccess, onError]);

    const handleKeyDown = (e) => {
        if (e.key === 'Enter') {
            handleAuth();
        }
    };

    return {
        authState,
        identity,
        setIdentity,
        passkey,
        setPasskey,
        handleKeyDown,
        handleAuth,
        handleGoogleAuth,
        statusMessage
    };
};
