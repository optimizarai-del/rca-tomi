import { createContext, useContext, useState, useEffect } from 'react'
import api from '../utils/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [permisos, setPermisos] = useState(null) // { secciones_permitidas, secciones_bloqueadas, ... }

  useEffect(() => {
    const stored = localStorage.getItem('user')
    if (stored) setUser(JSON.parse(stored))
    setLoading(false)
  }, [])

  useEffect(() => {
    if (!user) {
      setPermisos(null)
      return
    }
    api.get('/api/users/me/permisos')
      .then((r) => setPermisos(r.data))
      .catch(() => setPermisos(null))
  }, [user?.id])

  const login = async (email, password) => {
    const { data } = await api.post('/api/auth/login', { email, password })
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('user', JSON.stringify(data.user))
    setUser(data.user)
    return data.user
  }

  // Sprint 12: login express al perfil demo (sin pass).
  const loginDemo = async () => {
    const { data } = await api.post('/api/auth/demo-login')
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('user', JSON.stringify(data.user))
    setUser(data.user)
    return data.user
  }

  const register = async (payload) => {
    const { data } = await api.post('/api/auth/register', payload)
    return data
  }

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setUser(null)
  }

  const refreshUser = async () => {
    const { data } = await api.get('/api/auth/me')
    localStorage.setItem('user', JSON.stringify(data))
    setUser(data)
  }

  const isAdmin = ['super_admin', 'admin', 'admin_finanzas'].includes(user?.role)
  const hasFinanzas = ['super_admin', 'admin_finanzas'].includes(user?.role)

  // Sprint 13: helper para chequear si una seccion esta permitida.
  // Admins (bypass en backend) siempre true. Sin permisos cargados (loading),
  // tambien true — la query del backend filtra igual y un negar local prematuro
  // ocultaria el sidebar por una fraccion de segundo en cada navegacion.
  const sectionAllowed = (seccion) => {
    if (isAdmin) return true
    if (!permisos) return true
    return !permisos.secciones_bloqueadas?.includes(seccion)
  }

  return (
    <AuthContext.Provider value={{
      user, loading, login, loginDemo, register, logout, refreshUser,
      isAdmin, hasFinanzas,
      permisos, sectionAllowed,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
