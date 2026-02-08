#!/bin/bash
# SOTA 2026: Full Android Deployment Pipeline
# Prevents regressions by enforcing complete rebuild

set -e  # Exit on any error

cd /home/julienpiron_fr/trinity/social/web

echo "🔨 Step 1/4: Building frontend..."
npm run build

echo "📱 Step 2/4: Syncing Capacitor..."
npx cap sync android

echo "📦 Step 3/4: Building AAB..."
cd android
./gradlew bundleRelease

echo "🚀 Step 4/4: Deploying to Play Store..."
cd /home/julienpiron_fr/trinity
source .venv/bin/activate
python scripts/deploy_android.py

echo "✅ Full deployment complete!"
