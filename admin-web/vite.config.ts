import path from 'path'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  // Load repo root `.env` so DEV_HOST is defined in one place.
  const envDir = path.resolve(__dirname, '..')
  const env = loadEnv(mode, envDir, '')

  // Inside Docker: proxy to the backend service name (set by docker-compose).
  // Outside Docker (local npm run dev): fall back to 127.0.0.1 on the host-mapped port.
  const proxyHost = env.VITE_API_PROXY_HOST || '127.0.0.1'
  const proxyPort = env.VITE_API_PROXY_PORT || env.DEV_API_PORT || '8001'
  const apiTarget = `http://${proxyHost}:${proxyPort}`
  const wsTarget = `ws://${proxyHost}:${proxyPort}`

  return {
    plugins: [react()],
    envDir,
    server: {
      port: 5174,
      proxy: {
        '/api': { target: apiTarget, changeOrigin: true },
        '/ws': { target: wsTarget, ws: true },
      },
    },
    build: { outDir: 'dist', sourcemap: false },
  }
})
