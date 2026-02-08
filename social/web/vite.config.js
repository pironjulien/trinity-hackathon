import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import tailwindcss from '@tailwindcss/vite'
import { resolve } from 'path'

// https://vite.dev/config/
// SOTA 2026: Use reduced assets for mobile builds (less videos)
const isMobileBuild = process.env.MOBILE_BUILD === 'true'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],

  // SOTA 2026: Centralized assets directory (mobile uses reduced set)
  publicDir: isMobileBuild ? '../assets-mobile' : '../assets',

  define: {
    '__ANGEL_BOOTSTRAP_TOKEN__': JSON.stringify(process.env.ANGEL_BOOTSTRAP_TOKEN || 'trinity-offline-sota-2026')
  },

  build: {
    // Suppress chunk size warning - Trinity SPA is fine with ~1.6MB bundle
    chunkSizeWarningLimit: 2000,

    // SOTA 2026: Single page app (Android uses Flutter)
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
      },
    },
  },

  server: {
    // SOTA 2026: Fix COOP errors for OAuth popup flow
    headers: {
      'Cross-Origin-Opener-Policy': 'same-origin-allow-popups',
    },
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8161',
        changeOrigin: true,
      },
      // SOTA 2026: Angel Supervisor Proxy (Port 8089)
      '/sys': {
        target: 'http://127.0.0.1:8089',
        changeOrigin: true,
      },
      '/jobs': {
        target: 'http://127.0.0.1:8089',
        changeOrigin: true,
      },
      '/logs': {
        target: 'http://127.0.0.1:8089',
        changeOrigin: true,
      },
      // SOTA 2026: Jules API Proxy
      '/jules': {
        target: 'http://127.0.0.1:8089',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://127.0.0.1:8161',
        ws: true,
      },
    },
  },
})
