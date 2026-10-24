import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        timeout: 60000,
        proxyTimeout: 60000,
      },
      '/static': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      // OJO: /login, /tablero y /admin NO se proxifican. Son rutas del SPA;
      // si se envían al backend, Vite muestra la interfaz HTML antigua en vez
      // de la aplicación React.
      '/static_file': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/firma': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
