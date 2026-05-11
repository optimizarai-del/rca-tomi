import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App.jsx'
import { AuthProvider } from './context/AuthContext.jsx'
import './index.css'

// ─── Sentry (opcional) ───
// Si VITE_SENTRY_DSN está seteado en build time, captura errores JS automáticamente.
// Si no, no se inicializa.
if (import.meta.env.VITE_SENTRY_DSN) {
  // Lazy import: el bundle solo incluye @sentry/react si está activado
  import('@sentry/react').then((Sentry) => {
    Sentry.init({
      dsn: import.meta.env.VITE_SENTRY_DSN,
      environment: import.meta.env.VITE_SENTRY_ENV || 'production',
      tracesSampleRate: Number(import.meta.env.VITE_SENTRY_TRACES_RATE || '0.1'),
    })
  })
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
