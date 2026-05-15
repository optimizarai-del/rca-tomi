import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App.jsx'
import { AuthProvider } from './context/AuthContext.jsx'
import './index.css'

// ─── Sentry (opcional) ───
// Si VITE_SENTRY_DSN está seteado en build time, captura errores JS automáticamente.
// Si no, NO se importa @sentry/react — Vite no puede resolver imports dinámicos con
// variable, así que el módulo no se trata de cargar en dev cuando la lib no está.
if (import.meta.env.VITE_SENTRY_DSN) {
  const sentryPkg = '@sentry/' + 'react'  // string concat para que vite no analice estático
  import(sentryPkg).then((Sentry) => {
    Sentry.init({
      dsn: import.meta.env.VITE_SENTRY_DSN,
      environment: import.meta.env.VITE_SENTRY_ENV || 'production',
      tracesSampleRate: Number(import.meta.env.VITE_SENTRY_TRACES_RATE || '0.1'),
    })
  }).catch(() => {
    console.warn('Sentry DSN seteado pero @sentry/react no instalado. Run `npm install @sentry/react`.')
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
