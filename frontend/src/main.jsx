import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// Aplica el tema guardado antes del primer render para evitar destellos.
try {
  const tema = window.localStorage.getItem('guias.tema')
  document.documentElement.setAttribute('data-theme', tema === 'dark' ? 'dark' : 'light')
} catch {
  document.documentElement.setAttribute('data-theme', 'light')
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
