import { Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Register from './pages/Register'
import WorldMap from './pages/WorldMap'
import ObraDetail from './pages/ObraDetail'
import Cuadrillas from './pages/Cuadrillas'
import Materiales from './pages/Materiales'
import Presupuestos from './pages/Presupuestos'
import Proveedores from './pages/Proveedores'
import Ordenes from './pages/Ordenes'
import Feed from './pages/Feed'
import Finanzas from './pages/Finanzas'
import Movimientos from './pages/Movimientos'
import Aportes from './pages/Aportes'
import Comprobantes from './pages/Comprobantes'
import Clientes from './pages/Clientes'
import Socios from './pages/Socios'
import Equipo from './pages/Equipo'
import Mensajes from './pages/Mensajes'
import Layout from './components/Layout/Layout'
import ProtectedRoute from './components/Layout/ProtectedRoute'

const P = ({ children, fullWidth, ...p }) => (
  <ProtectedRoute {...p}><Layout fullWidth={fullWidth}>{children}</Layout></ProtectedRoute>
)

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/world" element={<P fullWidth><WorldMap /></P>} />
      <Route path="/obra/:id" element={<P fullWidth><ObraDetail /></P>} />
      <Route path="/cuadrillas" element={<P requireAdmin><Cuadrillas /></P>} />
      <Route path="/materiales" element={<P requireAdmin><Materiales /></P>} />
      <Route path="/presupuestos" element={<P requireAdmin><Presupuestos /></P>} />
      <Route path="/proveedores" element={<P requireAdmin><Proveedores /></P>} />
      <Route path="/ordenes" element={<P><Ordenes /></P>} />
      <Route path="/feed" element={<P><Feed /></P>} />
      <Route path="/finanzas" element={<P requireFinanzas><Finanzas /></P>} />
      <Route path="/movimientos" element={<P requireFinanzas><Movimientos /></P>} />
      <Route path="/aportes" element={<P requireFinanzas><Aportes /></P>} />
      <Route path="/comprobantes" element={<P requireFinanzas><Comprobantes /></P>} />
      <Route path="/clientes" element={<P requireFinanzas><Clientes /></P>} />
      <Route path="/socios" element={<P requireFinanzas><Socios /></P>} />
      <Route path="/equipo" element={<P requireAdmin><Equipo /></P>} />
      <Route path="/mensajes" element={<P requireAdmin><Mensajes /></P>} />
      <Route path="/" element={<Navigate to="/world" replace />} />
      <Route path="*" element={<Navigate to="/world" replace />} />
    </Routes>
  )
}
