import { NavLink } from 'react-router-dom'
import {
  LayoutGrid, Users, Package, Truck, ClipboardList,
  DollarSign, Activity, UserCog, ArrowLeftRight, HandCoins, FileText, Building2,
  MessageSquare, Briefcase, BookCheck,
} from 'lucide-react'
import { useAuth } from '../../context/AuthContext'

const link = ({ isActive }) =>
  `group flex items-center gap-3 px-3 py-2 rounded-xl text-[13px] font-medium tracking-tight transition-all duration-200 ${
    isActive
      ? 'bg-navy text-bone shadow-soft'
      : 'text-navy/65 hover:bg-bone-200/60 hover:text-navy'
  }`

export default function Sidebar() {
  const { isAdmin, hasFinanzas, sectionAllowed } = useAuth()

  // Sprint 13: el sidebar se filtra primero por rol (isAdmin/hasFinanzas)
  // y luego por permisos granulares. La funcion `show` combina ambos.
  const show = (seccion, requiereRol = true) => requiereRol && sectionAllowed(seccion)

  return (
    <aside className="w-60 shrink-0 border-r border-border/60 bg-white/30 backdrop-blur-sm
                      min-h-[calc(100vh-3rem)] py-5 px-3 flex flex-col">
      <div className="section-label !mt-0">General</div>
      {show('obras') && (
        <NavLink to="/world" className={link}>
          <LayoutGrid size={15} strokeWidth={1.8}/> Obras
        </NavLink>
      )}
      {show('ordenes') && (
        <NavLink to="/ordenes" className={link}>
          <ClipboardList size={15} strokeWidth={1.8}/> Órdenes
        </NavLink>
      )}
      {show('feed') && (
        <NavLink to="/feed" className={link}>
          <Activity size={15} strokeWidth={1.8}/> Actividad
        </NavLink>
      )}

      {isAdmin && (show('cuadrillas') || show('materiales') || show('presupuestos') || show('proveedores')) && (
        <>
          <div className="section-label">Recursos</div>
          {show('cuadrillas', isAdmin) && <NavLink to="/cuadrillas" className={link}><Users size={15} strokeWidth={1.8}/> Cuadrillas</NavLink>}
          {show('materiales', isAdmin) && <NavLink to="/materiales" className={link}><Package size={15} strokeWidth={1.8}/> Materiales</NavLink>}
          {show('presupuestos', isAdmin) && <NavLink to="/presupuestos" className={link}><ClipboardList size={15} strokeWidth={1.8}/> Presupuestos</NavLink>}
          {show('proveedores', isAdmin) && <NavLink to="/proveedores" className={link}><Truck size={15} strokeWidth={1.8}/> Proveedores</NavLink>}
        </>
      )}

      {hasFinanzas && (
        <>
          <div className="section-label">Finanzas</div>
          {show('finanzas', hasFinanzas) && <NavLink to="/finanzas" className={link}><DollarSign size={15} strokeWidth={1.8}/> Resumen</NavLink>}
          {show('movimientos', hasFinanzas) && <NavLink to="/movimientos" className={link}><ArrowLeftRight size={15} strokeWidth={1.8}/> Movimientos</NavLink>}
          {show('aportes', hasFinanzas) && <NavLink to="/aportes" className={link}><HandCoins size={15} strokeWidth={1.8}/> Aportes</NavLink>}
          {show('comprobantes', hasFinanzas) && <NavLink to="/comprobantes" className={link}><FileText size={15} strokeWidth={1.8}/> Comprobantes</NavLink>}
          {show('consolidacion', hasFinanzas) && <NavLink to="/consolidacion" className={link}><BookCheck size={15} strokeWidth={1.8}/> Consolidación</NavLink>}
          {show('clientes', hasFinanzas) && <NavLink to="/clientes" className={link}><Building2 size={15} strokeWidth={1.8}/> Clientes</NavLink>}
          {show('socios', hasFinanzas) && <NavLink to="/socios" className={link}><Briefcase size={15} strokeWidth={1.8}/> Socios</NavLink>}
        </>
      )}

      {isAdmin && (show('equipo') || show('mensajes')) && (
        <>
          <div className="section-label">Administración</div>
          {show('equipo', isAdmin) && <NavLink to="/equipo" className={link}><UserCog size={15} strokeWidth={1.8}/> Usuarios</NavLink>}
          {show('mensajes', isAdmin) && <NavLink to="/mensajes" className={link}><MessageSquare size={15} strokeWidth={1.8}/> Mensajes</NavLink>}
        </>
      )}

      <div className="mt-auto pt-6 px-3">
        <div className="text-[10px] tracking-[0.18em] uppercase text-muted/60 font-semibold">RCA. v0.3</div>
        <div className="text-[10px] text-muted/50 mt-1 tracking-wide">Diseño · Construcción · Servicio</div>
      </div>
    </aside>
  )
}
