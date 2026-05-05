import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LogOut, MessageCircle, AlertCircle, Search } from 'lucide-react'
import api from '../utils/api'
import { useAuth } from '../context/AuthContext'
import Logo from './Logo'

function fmtMoney(n) {
  if (!n) return '$0'
  if (n >= 1e6) return `$${(n / 1e6).toFixed(1)}M`
  if (n >= 1e3) return `$${(n / 1e3).toFixed(0)}k`
  return `$${n.toFixed(0)}`
}

export default function HUD() {
  const { user, logout } = useAuth()
  const [hud, setHud] = useState(null)
  const nav = useNavigate()

  useEffect(() => {
    const load = () => api.get('/api/dashboard/hud').then(r => setHud(r.data)).catch(()=>{})
    load()
    const t = setInterval(load, 30000)
    return () => clearInterval(t)
  }, [])

  return (
    <header className="sticky top-0 z-40 glass border-b border-border/60">
      <div className="px-6 h-12 flex items-center gap-8">
        {/* Brand */}
        <button onClick={() => nav('/world')}
          className="flex items-center transition hover:opacity-70">
          <Logo size="sm" />
        </button>

        {/* Stats — minimal, separados por respiración no por líneas */}
        {hud && (
          <div className="hidden lg:flex items-center gap-7 text-[12px] font-medium">
            <Stat label="Saldo" value={fmtMoney(hud.saldo_global ?? 0)} accent={(hud.saldo_global ?? 0) >= 0} />
            <Stat label="Obras" value={hud.obras_activas} />
            <Stat label="Cheques" value={fmtMoney(hud.cheques_a_vencer ?? 0)} />
            <Stat label="Aportes" value={fmtMoney(hud.aportes_pendientes ?? 0)} />
            {hud.alertas_total > 0 && (
              <button onClick={() => nav('/feed')}
                className="flex items-center gap-1.5 text-danger hover:opacity-70 transition">
                <AlertCircle size={13}/>
                <span>{hud.alertas_total}</span>
              </button>
            )}
          </div>
        )}

        {/* Right side */}
        <div className="ml-auto flex items-center gap-1">
          <IconBtn title="Buscar"><Search size={15}/></IconBtn>
          <IconBtn title="WhatsApp"><MessageCircle size={15} className="text-olive-600"/></IconBtn>
          <div className="w-px h-5 bg-border mx-2"/>
          <button className="flex items-center gap-2 pr-3 pl-1 py-1 rounded-full hover:bg-bone-200/70 transition">
            <div className="w-7 h-7 rounded-full bg-navy text-bone grid place-items-center text-[11px] font-semibold">
              {user?.name?.[0]?.toUpperCase()}
            </div>
            <span className="text-[13px] font-medium hidden md:inline tracking-tight">{user?.name}</span>
          </button>
          <IconBtn title="Salir" onClick={logout}><LogOut size={15}/></IconBtn>
        </div>
      </div>
    </header>
  )
}

function IconBtn({ children, ...props }) {
  return (
    <button
      {...props}
      className="p-2 rounded-full text-muted hover:bg-bone-200/70 hover:text-navy transition"
    >
      {children}
    </button>
  )
}

function Stat({ label, value, accent }) {
  return (
    <div className="flex items-baseline gap-1.5">
      <span className="text-[10px] text-muted/80 uppercase tracking-[0.12em]">{label}</span>
      <span className={`font-semibold tracking-tight ${accent ? 'text-olive-700' : 'text-navy'}`}>
        {value}
      </span>
    </div>
  )
}
