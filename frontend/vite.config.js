import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const API_TARGET = process.env.API_PROXY_TARGET || 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: API_TARGET,
        changeOrigin: true,
        timeout: 60000,
        proxyTimeout: 60000,
      },
      '/static': {
        target: API_TARGET,
        changeOrigin: true,
      },
      '/login': {
        target: API_TARGET,
        changeOrigin: true,
      },
      '/tablero': {
        target: API_TARGET,
        changeOrigin: true,
      },
      '/admin': {
        target: API_TARGET,
        changeOrigin: true,
      },
      '/static_file': {
        target: API_TARGET,
        changeOrigin: true,
      },
      '/firma': {
        target: API_TARGET,
        changeOrigin: true,
      },
    },
  },
})
