import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// En Docker el backend es http://backend:8000; en local, http://localhost:8000
const apiTarget = process.env.VITE_API_PROXY ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: { '/api': { target: apiTarget, changeOrigin: true } },
    watch: { usePolling: process.env.CHOKIDAR_USEPOLLING === 'true' },
  },
})
