// Script to create Firebase Auth users
// Run with: node scripts/create-users.mjs

import { initializeApp } from 'firebase/app';
import { getAuth, createUserWithEmailAndPassword } from 'firebase/auth';

const firebaseConfig = {
    apiKey: process.env.VITE_FIREBASE_API_KEY,
    authDomain: process.env.VITE_FIREBASE_AUTH_DOMAIN,
    projectId: process.env.VITE_FIREBASE_PROJECT_ID,
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

const users = [
    { email: 'admin@trinity.local', password: 'admin_password_123' },
    { email: 'tester@trinity.local', password: 'test_password_123' },
    { email: 'smith@trinity.local', password: 'user_password_123' }  // Min 6 chars required
];

async function createUsers() {
    console.log('Creating Firebase users...\n');

    for (const user of users) {
        try {
            const userCredential = await createUserWithEmailAndPassword(auth, user.email, user.password);
            console.log(`✓ Created: ${user.email} (UID: ${userCredential.user.uid})`);
        } catch (error) {
            if (error.code === 'auth/email-already-in-use') {
                console.log(`⚠ Already exists: ${user.email}`);
            } else {
                console.error(`✗ Failed: ${user.email} - ${error.message}`);
            }
        }
    }

    console.log('\nDone!');
    process.exit(0);
}

createUsers();
