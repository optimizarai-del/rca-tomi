import { Navigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

export default function ProtectedRoute({ children, requireAdmin = false, requireFinanzas = false }) {
  const { user, loading, isAdmin, hasFinanzas } = useAuth()
  if (loading) return <div className="p-8 text-muted">Cargando...</div>
  if (!user) return <Navigate to="/login" replace />
  if (requireAdmin && !isAdmin) return <Navigate to="/dashboard" replace />
  if (requireFinanzas && !hasFinanzas) return <Navigate to="/dashboard" replace />
  return children
}
