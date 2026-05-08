import { NavLink } from 'react-router-dom'
import {
  LayoutGrid, Users, Package, Truck, ClipboardList,
  DollarSign, Activity, UserCog, ArrowLeftRight, HandCoins, FileText, Building2,
} from 'lucide-react'
import { useAuth } from '../../context/AuthContext'

const link = ({ isActive }) =>
  `group flex items-center gap-3 px-3 py-2 rounded-xl text-[13px] font-medium tracking-tight transition-all duration-200 ${
    isActive
      ? 'bg-navy text-bone shadow-soft'
      : 'text-navy/65 hover:bg-bone-200/60 hover:text-navy'
  }`

export default function Sidebar() {
  const { isAdmin, hasFinanzas } = useAuth()

  return (
    <aside className="w-60 shrink-0 border-r border-border/60 bg-white/30 backdrop-blur-sm
                      min-h-[calc(100vh-3rem)] py-5 px-3 flex flex-col">
      <div className="section-label !mt-0">General</div>
      <NavLink to="/world" className={link}>
        <LayoutGrid size={15} strokeWidth={1.8}/> Obras
      </NavLink>
      <NavLink to="/ordenes" className={link}>
        <ClipboardList size={15} strokeWidth={1.8}/> Órdenes
      </NavLink>
      <NavLink to="/feed" className={link}>
        <Activity size={15} strokeWidth={1.8}/> Actividad
      </NavLink>

      {isAdmin && (
        <>
          <div className="section-label">Recursos</div>
          <NavLink to="/cuadrillas" className={link}><Users size={15} strokeWidth={1.8}/> Cuadrillas</NavLink>
          <NavLink to="/materiales" className={link}><Package size={15} strokeWidth={1.8}/> Materiales</NavLink>
          <NavLink to="/proveedores" className={link}><Truck size={15} strokeWidth={1.8}/> Proveedores</NavLink>
        </>
      )}

      {hasFinanzas && (
        <>
          <div className="section-label">Finanzas</div>
          <NavLink to="/finanzas" className={link}><DollarSign size={15} strokeWidth={1.8}/> Resumen</NavLink>
          <NavLink to="/movimientos" className={link}><ArrowLeftRight size={15} strokeWidth={1.8}/> Movimientos</NavLink>
          <NavLink to="/aportes" className={link}><HandCoins size={15} strokeWidth={1.8}/> Aportes</NavLink>
          <NavLink to="/comprobantes" className={link}><FileText size={15} strokeWidth={1.8}/> Comprobantes</NavLink>
          <NavLink to="/clientes" className={link}><Building2 size={15} strokeWidth={1.8}/> Clientes</NavLink>
        </>
      )}

      {isAdmin && (
        <>
          <div className="section-label">Administración</div>
          <NavLink to="/equipo" className={link}><UserCog size={15} strokeWidth={1.8}/> Usuarios</NavLink>
        </>
      )}

      <div className="mt-auto pt-6 px-3">
        <div className="text-[10px] tracking-[0.18em] uppercase text-muted/60 font-semibold">RCA. v0.3</div>
        <div className="text-[10px] text-muted/50 mt-1 tracking-wide">Diseño · Construcción · Servicio</div>
      </div>
    </aside>
  )
}
