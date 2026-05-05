import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, MapPin, Users, Package, Activity, AlertCircle,
  Calendar, DollarSign, Plus, Check, Clock, ArrowRight,
} from 'lucide-react'
import api from '../utils/api'

const ESTADO_FRENTE = {
  pendiente: { txt: 'Pendiente', cls: 'chip-muted' },
  en_progreso: { txt: 'En progreso', cls: 'chip-navy' },
  bloqueado: { txt: 'Bloqueado', cls: 'chip-danger' },
  completado: { txt: 'Completado', cls: 'chip-olive' },
}

const TIPO_EVENTO_ICON = {
  avance: '◆', material_llegada: '◇', incidente: '!', inspeccion: '◉', foto: '◫', hito: '★', otro: '○',
}

const PRIORIDAD = {
  baja: 'chip-muted', normal: 'chip-navy', alta: 'chip-warn', critica: 'chip-danger',
}

const HEALTH_LABEL = {
  optimo: { txt: 'Óptimo', dot: 'bg-olive' },
  atencion: { txt: 'Atención', dot: 'bg-warn' },
  critico: { txt: 'Crítico', dot: 'bg-danger' },
}

export default function ObraDetail() {
  const { id } = useParams()
  const nav = useNavigate()
  const [data, setData] = useState(null)
  const [frentes, setFrentes] = useState([])
  const [eventos, setEventos] = useState([])
  const [ordenes, setOrdenes] = useState([])
  const [tab, setTab] = useState('overview')

  const load = async () => {
    const [d, f, e, o] = await Promise.all([
      api.get(`/api/obras/${id}/dashboard`),
      api.get(`/api/frentes`, { params: { obra_id: id } }),
      api.get(`/api/eventos`, { params: { obra_id: id } }),
      api.get(`/api/ordenes`, { params: { obra_id: id } }),
    ])
    setData(d.data); setFrentes(f.data); setEventos(e.data); setOrdenes(o.data)
  }
  useEffect(() => { load() }, [id])

  if (!data) return <div className="px-8 py-12 text-muted">Cargando...</div>
  const { obra } = data
  const health = HEALTH_LABEL[obra.salud]

  return (
    <div className="animate-fade-in">
      {/* Hero — apple product page style */}
      <section className="relative overflow-hidden border-b border-border"
        style={{ background: `linear-gradient(180deg, ${obra.color}10 0%, transparent 100%)` }}>
        <div className="px-8 pt-8 pb-12 max-w-[1400px] mx-auto">
          <button onClick={() => nav('/world')} className="btn-ghost mb-8">
            <ArrowLeft size={14}/> Obras
          </button>

          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <span className="text-[11px] uppercase tracking-[0.2em] font-semibold text-olive-700">{obra.codigo}</span>
                <span className="w-1 h-1 rounded-full bg-muted/50"/>
                <span className="text-xs uppercase tracking-wider text-muted capitalize">
                  {(obra.estado || '').replace('_',' ').toLowerCase()}
                </span>
              </div>
              <h1 className="hero-title text-5xl md:text-6xl mb-4">{obra.nombre}</h1>
              <p className="text-muted text-lg mb-2 flex items-center gap-2">
                <MapPin size={14}/> {obra.ciudad || obra.direccion}
              </p>
              {dashboard?.cliente_nombre && <p className="text-muted text-sm mb-6">Cliente · <span className="text-navy">{dashboard.cliente_nombre}</span></p>}
              {obra.descripcion && <p className="text-navy/80 text-base leading-relaxed max-w-xl mb-8">{obra.descripcion}</p>}

              <div className="inline-flex items-center gap-2 bg-white border border-border rounded-full px-4 py-2 mb-8">
                <span className={`w-2 h-2 rounded-full ${health.dot}`}/>
                <span className="text-sm font-medium">Estado: {health.txt}</span>
              </div>

              {/* Mega progress */}
              <div>
                <div className="flex justify-between items-baseline mb-2">
                  <span className="text-[11px] uppercase tracking-[0.15em] text-muted font-semibold">Avance del proyecto</span>
                  <span className="hero-title text-3xl">{Math.round(obra.progreso)}%</span>
                </div>
                <div className="h-2 bg-bone-200 rounded-full overflow-hidden">
                  <div className="h-full bg-navy transition-all duration-1000" style={{ width: `${obra.progreso}%` }}/>
                </div>
              </div>
            </div>

            {/* Visual */}
            <div className="flex items-center justify-center">
              <div className="relative">
                <div className="absolute inset-0 blur-3xl opacity-30" style={{ background: obra.color }}/>
                <div className="relative text-[14rem] leading-none select-none">{obra.icono}</div>
              </div>
            </div>
          </div>

          {/* Stats grid Apple-style */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-x-8 gap-y-6 mt-12 pt-12 border-t border-border">
            <BigStat label="Presupuesto" value={`${Math.round(data.presupuesto_pct)}%`} sub="consumido"/>
            <BigStat label="Equipo" value={data.obreros_total} sub={`${data.cuadrillas_activas} cuadrillas`}/>
            <BigStat label="Frentes" value={`${data.frentes_completados}/${data.frentes_total}`} sub="completados"/>
            <BigStat label="Días restantes" value={data.dias_restantes ?? '—'} sub="estimados"/>
            <BigStat label="Pendientes" value={data.ordenes_pendientes} sub="órdenes activas"/>
          </div>
        </div>
      </section>

      {/* Tabs */}
      <div className="sticky top-14 z-30 bg-white/85 backdrop-blur border-b border-border">
        <div className="px-8 max-w-[1400px] mx-auto flex gap-1 overflow-x-auto">
          {[
            { v: 'overview', l: 'Resumen' },
            { v: 'frentes', l: `Frentes` },
            { v: 'ordenes', l: `Órdenes` },
            { v: 'eventos', l: `Actividad` },
          ].map(t => (
            <button key={t.v} onClick={()=>setTab(t.v)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition whitespace-nowrap ${
                tab === t.v ? 'border-navy text-navy' : 'border-transparent text-muted hover:text-navy'
              }`}>
              {t.l}
            </button>
          ))}
        </div>
      </div>

      <div className="px-8 py-8 max-w-[1400px] mx-auto">
        {tab === 'overview' && <Overview frentes={frentes} eventos={eventos} ordenes={ordenes}/>}
        {tab === 'frentes' && <FrentesTab frentes={frentes} obraId={id} reload={load}/>}
        {tab === 'ordenes' && <OrdenesTab ordenes={ordenes} obraId={id} reload={load}/>}
        {tab === 'eventos' && <EventosTab eventos={eventos} obraId={id} reload={load}/>}
      </div>
    </div>
  )
}

function BigStat({ label, value, sub }) {
  return (
    <div>
      <div className="stat-label mb-1">{label}</div>
      <div className="stat-value text-3xl">{value}</div>
      {sub && <div className="text-xs text-muted mt-1">{sub}</div>}
    </div>
  )
}

function Overview({ frentes, eventos, ordenes }) {
  const ordenesActivas = ordenes.filter(o => o.status !== 'completada').slice(0, 5)
  const eventosRecientes = eventos.slice(0, 6)
  return (
    <div className="grid lg:grid-cols-3 gap-5">
      <Section title="Frentes de trabajo" subtitle={`${frentes.filter(f=>f.estado==='completado').length} de ${frentes.length} completados`}>
        {frentes.length === 0 ? <Empty txt="Sin frentes"/> : (
          <ul className="space-y-3">
            {frentes.slice(0,8).map(f => (
              <li key={f.id}>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-sm font-medium">{f.nombre}</span>
                  <span className={ESTADO_FRENTE[f.estado].cls}>{Math.round(f.progreso)}%</span>
                </div>
                <div className="h-1 bg-bone-200 rounded-full overflow-hidden">
                  <div className="h-full bg-navy transition-all" style={{ width: `${f.progreso}%` }}/>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Órdenes activas" subtitle={`${ordenesActivas.length} pendientes`}>
        {ordenesActivas.length === 0 ? <Empty txt="Sin pendientes"/> : (
          <ul className="space-y-2">
            {ordenesActivas.map(o => (
              <li key={o.id} className="flex items-start gap-3 p-3 -mx-3 rounded-xl hover:bg-bone-100 transition">
                <span className={PRIORIDAD[o.prioridad]}>{o.prioridad}</span>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm">{o.titulo}</div>
                  <div className="text-xs text-muted truncate mt-0.5">{o.descripcion}</div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Actividad reciente" subtitle={`${eventos.length} eventos totales`}>
        {eventosRecientes.length === 0 ? <Empty txt="Sin actividad"/> : (
          <ul className="space-y-3">
            {eventosRecientes.map(e => (
              <li key={e.id} className={`flex gap-3 p-3 -mx-3 rounded-xl text-sm ${e.es_critico ? 'bg-danger/5' : 'hover:bg-bone-100'} transition`}>
                <span className={`w-7 h-7 rounded-full grid place-items-center text-xs shrink-0 ${e.es_critico ? 'bg-danger/15 text-danger' : 'bg-bone-200 text-navy'}`}>
                  {TIPO_EVENTO_ICON[e.tipo]}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="font-medium truncate">{e.titulo}</div>
                  <div className="text-xs text-muted truncate">{e.descripcion}</div>
                  <div className="text-[10px] text-muted/80 mt-0.5">
                    {new Date(e.fecha).toLocaleDateString()} · {e.canal}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  )
}

function Section({ title, subtitle, children }) {
  return (
    <div className="card p-6">
      <div className="mb-4">
        <h3 className="font-bold text-lg tracking-tight">{title}</h3>
        {subtitle && <p className="text-xs text-muted mt-0.5">{subtitle}</p>}
      </div>
      {children}
    </div>
  )
}

function Empty({ txt }) {
  return <p className="text-muted text-sm py-6 text-center">{txt}</p>
}

function FrentesTab({ frentes, obraId, reload }) {
  const [open, setOpen] = useState(false)
  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="hero-title text-2xl">Frentes de trabajo</h2>
          <p className="text-muted text-sm mt-1">Sub-mapas de la obra. Movés el slider para actualizar el avance.</p>
        </div>
        <button onClick={()=>setOpen(true)} className="btn-primary"><Plus size={14}/> Nuevo</button>
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {frentes.map(f => <FrenteCard key={f.id} frente={f} reload={reload}/>)}
      </div>
      {open && <NewFrenteModal obraId={obraId} onClose={()=>setOpen(false)} onSaved={()=>{ setOpen(false); reload() }}/>}
    </div>
  )
}

function FrenteCard({ frente, reload }) {
  const [progreso, setProgreso] = useState(frente.progreso)
  const e = ESTADO_FRENTE[frente.estado]

  const update = async (p) => {
    setProgreso(p)
    await api.patch(`/api/frentes/${frente.id}`, { ...frente, progreso: p })
    reload()
  }

  return (
    <div className="card p-5">
      <div className="flex items-start justify-between mb-2">
        <div>
          <div className="font-bold text-base">{frente.nombre}</div>
          <div className="text-[10px] uppercase tracking-wider text-muted mt-0.5">{frente.tipo}</div>
        </div>
        <span className={e.cls}>{e.txt}</span>
      </div>
      <div className="my-4">
        <div className="flex justify-between items-baseline mb-1">
          <span className="text-[11px] uppercase tracking-wider text-muted">Progreso</span>
          <span className="font-bold text-2xl tracking-tight">{Math.round(progreso)}%</span>
        </div>
        <input type="range" min="0" max="100" value={progreso}
          onChange={e => setProgreso(parseInt(e.target.value))}
          onMouseUp={e => update(parseInt(e.target.value))}
          onTouchEnd={e => update(parseInt(e.target.value))}
          className="w-full accent-navy" />
      </div>
    </div>
  )
}

function NewFrenteModal({ obraId, onClose, onSaved }) {
  const [form, setForm] = useState({
    nombre: '', tipo: 'estructura', icono: '⬛', estado: 'pendiente', progreso: 0,
  })
  const submit = async (e) => {
    e.preventDefault()
    await api.post('/api/frentes', { ...form, obra_id: parseInt(obraId), progreso: parseFloat(form.progreso)||0 })
    onSaved()
  }
  const TIPOS = ['cimientos','estructura','mamposteria','instalaciones','terminaciones']
  return (
    <Modal onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <h2 className="hero-title text-2xl">Nuevo frente</h2>
        <div><label className="label">Nombre</label><input className="input" value={form.nombre} onChange={e=>setForm({...form,nombre:e.target.value})} required/></div>
        <div><label className="label">Tipo</label>
          <select className="input" value={form.tipo} onChange={e=>setForm({...form,tipo:e.target.value})}>
            {TIPOS.map(t => <option key={t}>{t}</option>)}
          </select>
        </div>
        <div className="flex gap-2 justify-end pt-2">
          <button type="button" onClick={onClose} className="btn-ghost">Cancelar</button>
          <button className="btn-primary">Crear</button>
        </div>
      </form>
    </Modal>
  )
}

function OrdenesTab({ ordenes, obraId, reload }) {
  const [open, setOpen] = useState(false)
  const pend = ordenes.filter(o => o.status !== 'completada')
  const done = ordenes.filter(o => o.status === 'completada')

  const completar = async (id) => { await api.patch(`/api/ordenes/${id}/completar`); reload() }
  const iniciar = async (id) => { await api.patch(`/api/ordenes/${id}/iniciar`); reload() }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="hero-title text-2xl">Órdenes de trabajo</h2>
          <p className="text-muted text-sm mt-1">{pend.length} pendientes · {done.length} completadas</p>
        </div>
        <button onClick={()=>setOpen(true)} className="btn-primary"><Plus size={14}/> Nueva orden</button>
      </div>

      <div className="card divide-y divide-border">
        {pend.length === 0 ? (
          <div className="py-12 text-center text-muted text-sm">Sin órdenes pendientes</div>
        ) : pend.map(o => (
          <div key={o.id} className="p-5 flex items-center gap-4 hover:bg-bone-50 transition">
            <span className={PRIORIDAD[o.prioridad]}>{o.prioridad}</span>
            <div className="flex-1 min-w-0">
              <div className="font-semibold">{o.titulo}</div>
              <div className="text-sm text-muted truncate mt-0.5">{o.descripcion}</div>
              {o.fecha_limite && <div className="text-xs text-warn mt-1.5 flex items-center gap-1"><Clock size={11}/> {o.fecha_limite}</div>}
            </div>
            <div className="flex gap-2 shrink-0">
              {o.status === 'pendiente' && (
                <button onClick={()=>iniciar(o.id)} className="btn-ghost text-xs">Iniciar</button>
              )}
              <button onClick={()=>completar(o.id)} className="btn-accent text-xs"><Check size={12}/> Completar</button>
            </div>
          </div>
        ))}
      </div>

      {done.length > 0 && (
        <div className="card p-5">
          <h3 className="font-bold mb-4 text-sm uppercase tracking-wider text-muted">Completadas</h3>
          <ul className="space-y-2 text-sm">
            {done.slice(0,10).map(o => (
              <li key={o.id} className="flex items-center gap-3 text-muted">
                <Check size={14} className="text-olive"/>
                <span className="line-through">{o.titulo}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {open && <NewOrdenModal obraId={obraId} onClose={()=>setOpen(false)} onSaved={()=>{ setOpen(false); reload() }}/>}
    </div>
  )
}

function NewOrdenModal({ obraId, onClose, onSaved }) {
  const [form, setForm] = useState({
    titulo: '', descripcion: '', prioridad: 'normal', xp_reward: 10, fecha_limite: '',
  })
  const [cuadrillas, setCuadrillas] = useState([])
  const [cuadId, setCuadId] = useState('')

  useEffect(() => { api.get('/api/cuadrillas/').then(r => setCuadrillas(r.data)) }, [])

  const submit = async (e) => {
    e.preventDefault()
    await api.post('/api/ordenes/', {
      obra_id: parseInt(obraId),
      cuadrilla_id: cuadId ? parseInt(cuadId) : null,
      ...form,
      fecha_limite: form.fecha_limite || null,
      xp_reward: parseInt(form.xp_reward) || 10,
    })
    onSaved()
  }
  return (
    <Modal onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <h2 className="hero-title text-2xl">Nueva orden</h2>
        <div><label className="label">Título</label><input className="input" value={form.titulo} onChange={e=>setForm({...form,titulo:e.target.value})} required/></div>
        <div><label className="label">Descripción</label><textarea className="input" rows={2} value={form.descripcion} onChange={e=>setForm({...form,descripcion:e.target.value})}/></div>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="label">Prioridad</label>
            <select className="input" value={form.prioridad} onChange={e=>setForm({...form,prioridad:e.target.value})}>
              <option>baja</option><option>normal</option><option>alta</option><option>critica</option>
            </select>
          </div>
          <div><label className="label">Fecha límite</label><input className="input" type="date" value={form.fecha_limite} onChange={e=>setForm({...form,fecha_limite:e.target.value})}/></div>
        </div>
        <div><label className="label">Cuadrilla</label>
          <select className="input" value={cuadId} onChange={e=>setCuadId(e.target.value)}>
            <option value="">— Sin asignar —</option>
            {cuadrillas.map(c => <option key={c.id} value={c.id}>{c.nombre}</option>)}
          </select>
        </div>
        <div className="flex gap-2 justify-end pt-2">
          <button type="button" onClick={onClose} className="btn-ghost">Cancelar</button>
          <button className="btn-primary">Crear orden</button>
        </div>
      </form>
    </Modal>
  )
}

function EventosTab({ eventos, obraId, reload }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="hero-title text-2xl">Actividad</h2>
          <p className="text-muted text-sm mt-1">Cronología de eventos en la obra.</p>
        </div>
        <button onClick={()=>setOpen(true)} className="btn-primary"><Plus size={14}/> Reportar</button>
      </div>
      <div className="card divide-y divide-border">
        {eventos.map(e => (
          <div key={e.id} className={`p-5 flex gap-4 ${e.es_critico ? 'bg-danger/5' : ''}`}>
            <span className={`w-9 h-9 rounded-full grid place-items-center shrink-0 ${e.es_critico ? 'bg-danger/15 text-danger' : 'bg-bone-200 text-navy'}`}>
              {TIPO_EVENTO_ICON[e.tipo]}
            </span>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span className="font-semibold">{e.titulo}</span>
                {e.es_critico && <span className="chip-danger">Crítico</span>}
              </div>
              <div className="text-sm text-muted">{e.descripcion}</div>
              <div className="text-xs text-muted/80 mt-2">
                {new Date(e.fecha).toLocaleString()} · {e.canal}
              </div>
            </div>
          </div>
        ))}
      </div>
      {open && <NewEventoModal obraId={obraId} onClose={()=>setOpen(false)} onSaved={()=>{ setOpen(false); reload() }}/>}
    </div>
  )
}

function NewEventoModal({ obraId, onClose, onSaved }) {
  const [form, setForm] = useState({ titulo:'', descripcion:'', tipo:'avance', es_critico:false })
  const submit = async (e) => {
    e.preventDefault()
    await api.post('/api/eventos/', { ...form, obra_id: parseInt(obraId) })
    onSaved()
  }
  return (
    <Modal onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <h2 className="hero-title text-2xl">Reportar evento</h2>
        <div><label className="label">Tipo</label>
          <select className="input" value={form.tipo} onChange={e=>setForm({...form,tipo:e.target.value})}>
            {Object.keys(TIPO_EVENTO_ICON).map(k => <option key={k} value={k}>{k}</option>)}
          </select>
        </div>
        <div><label className="label">Título</label><input className="input" value={form.titulo} onChange={e=>setForm({...form,titulo:e.target.value})} required/></div>
        <div><label className="label">Descripción</label><textarea className="input" rows={3} value={form.descripcion} onChange={e=>setForm({...form,descripcion:e.target.value})}/></div>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={form.es_critico} onChange={e=>setForm({...form,es_critico:e.target.checked})} className="accent-danger"/>
          Marcar como crítico
        </label>
        <div className="flex gap-2 justify-end pt-2">
          <button type="button" onClick={onClose} className="btn-ghost">Cancelar</button>
          <button className="btn-primary">Reportar</button>
        </div>
      </form>
    </Modal>
  )
}

function Modal({ children, onClose }) {
  return (
    <div className="fixed inset-0 bg-navy/30 backdrop-blur-sm grid place-items-center z-50 p-4 animate-fade-in" onClick={onClose}>
      <div onClick={e=>e.stopPropagation()} className="card w-full max-w-md p-8 shadow-lift animate-scale-in">
        {children}
      </div>
    </div>
  )
}
