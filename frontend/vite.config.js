import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        // Mantener el Host original (127.0.0.1:5173): el backend valida el
        // Origin contra el Host para CSRF. Con changeOrigin:true el Host llegaba
        // como :8000 y toda escritura del navegador (incluido el CAPTCHA del
        // login) respondía 403.
        changeOrigin: false,
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
