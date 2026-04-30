import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, MapPin, ArrowRight, Filter } from 'lucide-react'
import api from '../utils/api'
import { useAuth } from '../context/AuthContext'

const STATUS_LABEL = {
  planificacion: 'En planificación',
  en_obra: 'En obra',
  pausada: 'Pausada',
  finalizada: 'Finalizada',
}

const HEALTH_DOT = {
  optimo: 'bg-olive',
  atencion: 'bg-warn',
  critico: 'bg-danger',
}

function fmtMoney(n) {
  if (!n) return '—'
  if (n >= 1e6) return `$${(n / 1e6).toFixed(2)}M`
  if (n >= 1e3) return `$${(n / 1e3).toFixed(0)}k`
  return `$${n.toFixed(0)}`
}

function ObraCard({ obra, onClick, featured = false }) {
  const presPct = obra.presupuesto_total ? (obra.presupuesto_consumido / obra.presupuesto_total * 100) : 0
  const dias = obra.fecha_fin_estimada
    ? Math.max(0, Math.ceil((new Date(obra.fecha_fin_estimada) - new Date()) / 86400000))
    : null

  if (featured) {
    return (
      <div onClick={onClick} className="card card-hover cursor-pointer p-0 overflow-hidden col-span-full md:col-span-2 lg:col-span-3 group">
        <div className="grid md:grid-cols-2">
          <div className="relative h-64 md:h-auto overflow-hidden"
            style={{ background: `linear-gradient(135deg, ${obra.color}25 0%, ${obra.color}05 100%)` }}>
            <div className="absolute inset-0 grid place-items-center">
              <div className="text-9xl opacity-90 transition-transform duration-700 group-hover:scale-110">
                {obra.icono}
              </div>
            </div>
            <div className="absolute top-4 left-4">
              <span className="inline-flex items-center gap-1.5 bg-white/80 backdrop-blur px-3 py-1 rounded-full text-[11px] font-medium">
                <span className={`w-1.5 h-1.5 rounded-full ${HEALTH_DOT[obra.salud]}`}/>
                {STATUS_LABEL[obra.status]}
              </span>
            </div>
          </div>
          <div className="p-8 flex flex-col justify-between">
            <div>
              <div className="text-[11px] uppercase tracking-[0.15em] text-muted font-semibold mb-2">{obra.codigo}</div>
              <h2 className="hero-title text-3xl md:text-4xl mb-3">{obra.nombre}</h2>
              <p className="text-muted text-sm flex items-center gap-1 mb-6">
                <MapPin size={12}/> {obra.ciudad || obra.direccion}
              </p>
              <p className="text-navy/80 text-sm leading-relaxed mb-6">{obra.descripcion}</p>
            </div>
            <div>
              <div className="grid grid-cols-3 gap-4 mb-6">
                <Mini label="Avance" value={`${Math.round(obra.progreso || 0)}%`}/>
                <Mini label="Presupuesto" value={`${Math.round(presPct)}%`}/>
                <Mini label="Días" value={dias != null ? dias : '—'}/>
              </div>
              <div className="flex items-center gap-2 text-olive-700 font-medium text-sm group-hover:gap-3 transition-all">
                Ver detalle <ArrowRight size={14}/>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div onClick={onClick} className="card card-hover cursor-pointer p-0 overflow-hidden group">
      <div className="relative h-40 overflow-hidden"
        style={{ background: `linear-gradient(135deg, ${obra.color}20 0%, ${obra.color}05 100%)` }}>
        <div className="absolute inset-0 grid place-items-center">
          <div className="text-7xl opacity-90 transition-transform duration-500 group-hover:scale-110">
            {obra.icono}
          </div>
        </div>
        <div className="absolute top-3 left-3">
          <span className="inline-flex items-center gap-1.5 bg-white/85 backdrop-blur px-2.5 py-1 rounded-full text-[10px] font-medium">
            <span className={`w-1.5 h-1.5 rounded-full ${HEALTH_DOT[obra.salud]}`}/>
            {STATUS_LABEL[obra.status]}
          </span>
        </div>
      </div>
      <div className="p-5">
        <div className="text-[10px] uppercase tracking-[0.15em] text-muted font-semibold mb-1">{obra.codigo}</div>
        <h3 className="font-bold text-lg tracking-tight mb-1 truncate">{obra.nombre}</h3>
        <p className="text-muted text-xs flex items-center gap-1 mb-4">
          <MapPin size={11}/> {obra.ciudad || '—'}
        </p>
        <div className="space-y-3">
          <Bar label="Avance" pct={obra.progreso || 0} accent />
          <Bar label="Presupuesto" pct={presPct} warn={presPct > 90} />
        </div>
        <div className="grid grid-cols-3 gap-2 pt-4 mt-4 border-t border-border">
          <Tiny label="Pisos" value={obra.pisos || 1}/>
          <Tiny label="m²" value={obra.superficie_m2 || 0}/>
          <Tiny label="Días" value={dias != null ? dias : '—'}/>
        </div>
      </div>
    </div>
  )
}

function Mini({ label, value }) {
  return (
    <div>
      <div className="stat-label">{label}</div>
      <div className="stat-value text-2xl mt-0.5">{value}</div>
    </div>
  )
}
function Tiny({ label, value }) {
  return (
    <div className="text-center">
      <div className="font-semibold text-sm">{value}</div>
      <div className="text-[10px] uppercase tracking-wider text-muted">{label}</div>
    </div>
  )
}
function Bar({ label, pct, accent, warn }) {
  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <span className="text-[10px] uppercase tracking-wider text-muted">{label}</span>
        <span className="text-xs font-semibold">{Math.round(pct)}%</span>
      </div>
      <div className="h-1 bg-bone-200 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-700 ${
            warn ? 'bg-warn' : accent ? 'bg-olive' : 'bg-navy'
          }`}
          style={{ width: `${Math.min(100, pct)}%` }}
        />
      </div>
    </div>
  )
}

export default function WorldMap() {
  const [obras, setObras] = useState([])
  const [filter, setFilter] = useState('todas')
  const [open, setOpen] = useState(false)
  const { isAdmin } = useAuth()
  const nav = useNavigate()

  const load = () => api.get('/api/obras').then(r => setObras(r.data))
  useEffect(() => { load() }, [])

  const filtered = filter === 'todas' ? obras : obras.filter(o => o.status === filter)
  const featured = filtered.find(o => o.status === 'en_obra') || filtered[0]
  const rest = filtered.filter(o => o.id !== featured?.id)

  const counts = {
    todas: obras.length,
    en_obra: obras.filter(o => o.status === 'en_obra').length,
    planificacion: obras.filter(o => o.status === 'planificacion').length,
    finalizada: obras.filter(o => o.status === 'finalizada').length,
  }

  return (
    <div className="px-8 py-12 max-w-[1500px] mx-auto bg-grain">
      {/* Hero header */}
      <section className="mb-16 max-w-3xl animate-fade-in">
        <div className="hero-eyebrow">Cartera de proyectos</div>
        <h1 className="hero-title text-6xl md:text-7xl mb-5">
          Tus obras<br/>
          <span className="text-olive-600">en un solo lugar.</span>
        </h1>
        <p className="hero-sub">
          Cada proyecto, un universo propio. Visualizá el avance, el equipo y los recursos en tiempo real.
        </p>
      </section>

      {/* Filtros + acción */}
      <div className="flex items-center justify-between mb-8 flex-wrap gap-4">
        <div className="flex items-center gap-1.5 bg-white border border-border rounded-full p-1">
          {[
            { v: 'todas', l: 'Todas' },
            { v: 'en_obra', l: 'En obra' },
            { v: 'planificacion', l: 'Planificación' },
            { v: 'finalizada', l: 'Finalizadas' },
          ].map(t => (
            <button key={t.v} onClick={() => setFilter(t.v)}
              className={`px-4 py-1.5 rounded-full text-[13px] font-medium transition ${
                filter === t.v ? 'bg-navy text-bone' : 'text-navy/70 hover:bg-bone-200'
              }`}>
              {t.l} <span className="opacity-60 ml-1">{counts[t.v]}</span>
            </button>
          ))}
        </div>
        {isAdmin && (
          <button onClick={() => setOpen(true)} className="btn-primary">
            <Plus size={14}/> Nueva obra
          </button>
        )}
      </div>

      {/* Grid */}
      {filtered.length === 0 ? (
        <EmptyState onCreate={() => setOpen(true)} canCreate={isAdmin}/>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
          {featured && (
            <ObraCard key={featured.id} obra={featured} featured onClick={() => nav(`/obra/${featured.id}`)}/>
          )}
          {rest.map(o => (
            <ObraCard key={o.id} obra={o} onClick={() => nav(`/obra/${o.id}`)}/>
          ))}
        </div>
      )}

      {open && <NewObraModal onClose={() => setOpen(false)} onCreated={() => { setOpen(false); load() }}/>}
    </div>
  )
}

function EmptyState({ onCreate, canCreate }) {
  return (
    <div className="card text-center py-20 px-6 max-w-2xl mx-auto">
      <div className="text-6xl mb-4 opacity-40">○</div>
      <h2 className="hero-title text-3xl mb-3">Sin obras todavía</h2>
      <p className="text-muted mb-6 max-w-sm mx-auto">
        Empezá creando tu primera obra. Vas a poder agregar frentes, asignar cuadrillas y registrar eventos.
      </p>
      {canCreate && (
        <button onClick={onCreate} className="btn-primary mx-auto">
          <Plus size={14}/> Crear primera obra
        </button>
      )}
    </div>
  )
}

function NewObraModal({ onClose, onCreated }) {
  const ICONOS = ['🏙️','🏘️','🏭','🏪','🏡','🏢','🏬','🏛️']
  const COLORES = ['#1E2B5E','#3D4F1E','#8A9A5B','#6B4C30','#A8845F','#C4B99A']
  const [form, setForm] = useState({
    nombre: '', codigo: '', ciudad: '', cliente: '', descripcion: '',
    icono: '🏗️', color: '#1E2B5E',
    presupuesto_total: 0, superficie_m2: 0, pisos: 1, status: 'planificacion',
  })
  const [err, setErr] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    try {
      await api.post('/api/obras', { ...form, presupuesto_total: parseFloat(form.presupuesto_total)||0, superficie_m2: parseFloat(form.superficie_m2)||0 })
      onCreated()
    } catch (e) { setErr(e.response?.data?.detail || 'Error') }
  }

  return (
    <div className="fixed inset-0 bg-navy/30 backdrop-blur-sm grid place-items-center z-50 p-4 animate-fade-in" onClick={onClose}>
      <form onClick={e=>e.stopPropagation()} onSubmit={submit} className="card w-full max-w-2xl shadow-lift p-8 space-y-5 animate-scale-in">
        <div>
          <div className="text-[11px] uppercase tracking-[0.15em] text-olive-700 font-semibold mb-1">Nuevo proyecto</div>
          <h2 className="hero-title text-3xl flex items-center gap-3">
            <span>{form.icono}</span> Crear obra
          </h2>
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          <div className="md:col-span-2"><label className="label">Nombre</label><input className="input" value={form.nombre} onChange={e=>setForm({...form,nombre:e.target.value})} required/></div>
          <div><label className="label">Código</label><input className="input" value={form.codigo} onChange={e=>setForm({...form,codigo:e.target.value})} placeholder="TA-2026-01"/></div>
          <div><label className="label">Cliente</label><input className="input" value={form.cliente} onChange={e=>setForm({...form,cliente:e.target.value})}/></div>
          <div><label className="label">Ciudad</label><input className="input" value={form.ciudad} onChange={e=>setForm({...form,ciudad:e.target.value})}/></div>
          <div><label className="label">Status</label>
            <select className="input" value={form.status} onChange={e=>setForm({...form,status:e.target.value})}>
              <option value="planificacion">Planificación</option>
              <option value="en_obra">En obra</option>
              <option value="pausada">Pausada</option>
            </select>
          </div>
          <div className="md:col-span-2"><label className="label">Descripción</label><textarea className="input" rows={2} value={form.descripcion} onChange={e=>setForm({...form,descripcion:e.target.value})}/></div>
          <div><label className="label">Presupuesto ($)</label><input className="input" type="number" value={form.presupuesto_total} onChange={e=>setForm({...form,presupuesto_total:e.target.value})}/></div>
          <div><label className="label">Superficie (m²)</label><input className="input" type="number" value={form.superficie_m2} onChange={e=>setForm({...form,superficie_m2:e.target.value})}/></div>
          <div><label className="label">Pisos</label><input className="input" type="number" value={form.pisos} onChange={e=>setForm({...form,pisos:parseInt(e.target.value)||1})}/></div>
        </div>

        <div>
          <label className="label">Ícono</label>
          <div className="flex gap-2 flex-wrap">
            {ICONOS.map(i => (
              <button type="button" key={i} onClick={()=>setForm({...form,icono:i})}
                className={`text-2xl w-12 h-12 rounded-xl border transition ${form.icono===i?'border-navy bg-bone-200':'border-border hover:bg-bone-100'}`}>{i}</button>
            ))}
          </div>
        </div>
        <div>
          <label className="label">Color</label>
          <div className="flex gap-2 flex-wrap">
            {COLORES.map(c => (
              <button type="button" key={c} onClick={()=>setForm({...form,color:c})}
                className={`w-9 h-9 rounded-lg border-2 transition ${form.color===c?'border-navy ring-2 ring-navy/20':'border-transparent'}`}
                style={{ background: c }}/>
            ))}
          </div>
        </div>

        {err && <div className="text-danger text-sm">{err}</div>}
        <div className="flex gap-2 justify-end pt-2 border-t border-border">
          <button type="button" onClick={onClose} className="btn-ghost">Cancelar</button>
          <button className="btn-primary">Crear obra</button>
        </div>
      </form>
    </div>
  )
}
