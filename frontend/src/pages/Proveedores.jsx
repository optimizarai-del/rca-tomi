import { useEffect, useState } from 'react'
import { Star, Plus, Phone, Mail, Trash2, Clock, ChevronRight, Package, FileText, Receipt } from 'lucide-react'
import api from '../utils/api'

export default function Proveedores() {
  const [list, setList] = useState([])
  const [open, setOpen] = useState(false)
  const [verInactivos, setVerInactivos] = useState(false)
  const [expanded, setExpanded] = useState(null)

  const load = () => {
    const params = verInactivos ? '?incluir_inactivos=true' : ''
    return api.get(`/api/proveedores/${params}`).then(r => setList(r.data))
  }
  useEffect(() => { load() }, [verInactivos])

  const eliminar = async (id) => {
    if (confirm('¿Eliminar?')) { await api.delete(`/api/proveedores/${id}`); load() }
  }

  return (
    <div className="max-w-6xl mx-auto animate-fade-in">
      <header className="mb-12">
        <div className="hero-eyebrow">Red de aliados</div>
        <div className="flex items-end justify-between flex-wrap gap-4">
          <div>
            <h1 className="hero-title text-5xl md:text-6xl mb-3">Proveedores</h1>
            <p className="hero-sub">Tu red de confianza. Por default ocultamos los inactivos hace +1 año.</p>
          </div>
          <div className="flex gap-2 items-center">
            <label className="flex items-center gap-2 text-xs text-muted cursor-pointer">
              <input type="checkbox" checked={verInactivos} onChange={e=>setVerInactivos(e.target.checked)} className="rounded"/>
              Ver inactivos (+1 año)
            </label>
            <button onClick={()=>setOpen(true)} className="btn-primary"><Plus size={14}/> Nuevo proveedor</button>
          </div>
        </div>
      </header>

      <div className="grid md:grid-cols-2 gap-4">
        {list.map(p => (
          <ProveedorCard
            key={p.id}
            p={p}
            isExpanded={expanded === p.id}
            onToggle={() => setExpanded(expanded === p.id ? null : p.id)}
            onDelete={() => eliminar(p.id)}
          />
        ))}
        {list.length === 0 && (
          <div className="card p-12 text-center text-muted col-span-full">
            {verInactivos ? 'No hay proveedores.' : 'No hay proveedores activos. Activá "Ver inactivos" para mostrar todos.'}
          </div>
        )}
      </div>

      {open && <NewProveedorModal onClose={()=>setOpen(false)} onSaved={()=>{ setOpen(false); load() }}/>}
    </div>
  )
}

function ProveedorCard({ p, isExpanded, onToggle, onDelete }) {
  return (
    <div className="card p-6 card-hover">
      <div className="flex items-start justify-between mb-3 cursor-pointer" onClick={onToggle}>
        <div className="flex-1">
          <div className="font-bold text-lg tracking-tight flex items-center gap-2">
            {p.nombre}
            <ChevronRight size={14} className={`text-muted transition-transform ${isExpanded ? 'rotate-90' : ''}`}/>
          </div>
          <div className="text-xs uppercase tracking-wider text-muted mt-1">{p.rubro}</div>
        </div>
        <button onClick={(e)=>{e.stopPropagation(); onDelete()}} className="text-muted/60 hover:text-danger transition"><Trash2 size={14}/></button>
      </div>

      <div className="flex items-center gap-1 mb-4">
        {[1,2,3,4,5].map(s => (
          <Star key={s} size={14}
            className={s <= Math.round(p.rating) ? 'fill-olive text-olive' : 'text-bone-300'}/>
        ))}
        <span className="text-xs text-muted ml-1.5 font-medium">{p.rating?.toFixed(1)}</span>
      </div>

      <div className="space-y-2 text-sm pt-4 border-t border-border">
        {p.telefono && <Row icon={Phone} text={p.telefono}/>}
        {p.email && <Row icon={Mail} text={p.email}/>}
        <Row icon={Clock} text={`${p.plazo_entrega_dias} días entrega`}/>
        {p.cuit && <div className="text-xs text-muted">CUIT {p.cuit}</div>}
      </div>

      {p.moroso && <span className="chip-danger mt-4 inline-block">Moroso</span>}

      {isExpanded && <ProveedorDetalle pid={p.id}/>}
    </div>
  )
}

function ProveedorDetalle({ pid }) {
  const [tab, setTab] = useState('materiales')
  const [materiales, setMateriales] = useState(null)
  const [historial, setHistorial] = useState(null)
  const [incluirAntiguos, setIncluirAntiguos] = useState(false)

  useEffect(() => {
    api.get(`/api/proveedores/${pid}/materiales`).then(r => setMateriales(r.data))
  }, [pid])
  useEffect(() => {
    const p = incluirAntiguos ? '?incluir_antiguos=true' : ''
    api.get(`/api/proveedores/${pid}/historial${p}`).then(r => setHistorial(r.data))
  }, [pid, incluirAntiguos])

  return (
    <div className="mt-5 pt-5 border-t border-border space-y-4">
      <div className="flex gap-1 text-xs">
        {[
          { v: 'materiales', l: `Vende${materiales ? ` · ${materiales.length}` : ''}` },
          { v: 'historial', l: `Historial${historial ? ` · ${historial.length}` : ''}` },
        ].map(t => (
          <button
            key={t.v}
            onClick={() => setTab(t.v)}
            className={`px-3 py-1.5 rounded-full transition ${
              tab === t.v ? 'bg-navy text-bone' : 'text-muted hover:text-navy'
            }`}
          >
            {t.l}
          </button>
        ))}
      </div>

      {tab === 'materiales' && (
        <div>
          {!materiales && <div className="text-xs text-muted">Cargando…</div>}
          {materiales && materiales.length === 0 && (
            <div className="text-xs text-muted">No tiene materiales registrados. Asignale uno desde /materiales.</div>
          )}
          {materiales?.map(m => (
            <div key={m.material_id} className="flex items-center gap-2 text-sm py-1.5 border-b border-bone-200 last:border-0">
              <Package size={12} className="text-navy/60"/>
              <span className="font-medium flex-1">{m.nombre}</span>
              <span className="text-xs text-muted">{m.categoria}</span>
              <span className="text-xs text-muted tabular-nums">${m.precio_unitario.toLocaleString()}/{m.unidad}</span>
              {m.pendiente_retiro > 0 && (
                <span className="chip-warn text-[10px]">
                  {m.pendiente_retiro.toFixed(0)} {m.unidad} pendiente
                </span>
              )}
            </div>
          ))}
        </div>
      )}

      {tab === 'historial' && (
        <div>
          <label className="flex items-center gap-2 text-xs text-muted mb-3 cursor-pointer">
            <input type="checkbox" checked={incluirAntiguos} onChange={e=>setIncluirAntiguos(e.target.checked)} className="rounded"/>
            Incluir items de hace más de 1 año
          </label>
          {!historial && <div className="text-xs text-muted">Cargando…</div>}
          {historial && historial.length === 0 && (
            <div className="text-xs text-muted">Sin movimientos en el rango.</div>
          )}
          <div className="space-y-1">
            {historial?.slice(0, 30).map((h, i) => (
              <div key={`${h.tipo}-${h.ref_id}`} className="flex items-center gap-2 text-xs py-1.5 border-b border-bone-200 last:border-0">
                {h.tipo === 'facturado' ? (
                  <Receipt size={11} className="text-olive shrink-0"/>
                ) : (
                  <FileText size={11} className="text-navy/60 shrink-0"/>
                )}
                <span className="font-mono text-muted/70 w-20 shrink-0">{h.fecha}</span>
                <span className="font-medium truncate flex-1">{h.material_nombre}</span>
                <span className="tabular-nums text-muted shrink-0">{h.cantidad.toFixed(0)} {h.unidad}</span>
                {h.subtotal != null && (
                  <span className="tabular-nums font-semibold w-20 text-right shrink-0">
                    ${h.subtotal.toLocaleString()}
                  </span>
                )}
                {h.tipo === 'facturado' && h.en_negro && (
                  <span className="chip-danger text-[10px]">negro</span>
                )}
                {h.tipo === 'facturado' && !h.en_negro && (
                  <span className="chip-olive text-[10px]">blanco</span>
                )}
                {h.tipo === 'presupuestado' && (
                  <span className="chip-muted text-[10px] capitalize">{h.presupuesto_estado}</span>
                )}
              </div>
            ))}
            {historial?.length > 30 && (
              <div className="text-xs text-muted pt-2">…y {historial.length - 30} más</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function Row({ icon: I, text }) {
  return (
    <div className="flex items-center gap-2 text-muted text-xs">
      <I size={12}/> {text}
    </div>
  )
}

function NewProveedorModal({ onClose, onSaved }) {
  const [form, setForm] = useState({
    nombre:'', cuit:'', telefono:'', email:'', rubro:'cemento', rating:4, plazo_entrega_dias:3,
  })
  const submit = async (e) => {
    e.preventDefault()
    await api.post('/api/proveedores/', { ...form, rating: parseFloat(form.rating), plazo_entrega_dias: parseInt(form.plazo_entrega_dias) })
    onSaved()
  }
  return (
    <div className="fixed inset-0 bg-navy/30 backdrop-blur-sm grid place-items-center z-50 p-4 animate-fade-in" onClick={onClose}>
      <form onClick={e=>e.stopPropagation()} onSubmit={submit} className="card w-full max-w-md p-8 space-y-4 shadow-lift animate-scale-in">
        <h2 className="hero-title text-2xl">Nuevo proveedor</h2>
        <div><label className="label">Nombre</label><input className="input" value={form.nombre} onChange={e=>setForm({...form,nombre:e.target.value})} required/></div>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="label">CUIT</label><input className="input" value={form.cuit} onChange={e=>setForm({...form,cuit:e.target.value})}/></div>
          <div><label className="label">Rubro</label><input className="input" value={form.rubro} onChange={e=>setForm({...form,rubro:e.target.value})}/></div>
          <div><label className="label">Teléfono</label><input className="input" value={form.telefono} onChange={e=>setForm({...form,telefono:e.target.value})}/></div>
          <div><label className="label">Email</label><input className="input" type="email" value={form.email} onChange={e=>setForm({...form,email:e.target.value})}/></div>
          <div><label className="label">Rating (0-5)</label><input className="input" type="number" min="0" max="5" step="0.1" value={form.rating} onChange={e=>setForm({...form,rating:e.target.value})}/></div>
          <div><label className="label">Plazo (días)</label><input className="input" type="number" value={form.plazo_entrega_dias} onChange={e=>setForm({...form,plazo_entrega_dias:e.target.value})}/></div>
        </div>
        <div className="flex gap-2 justify-end pt-2">
          <button type="button" onClick={onClose} className="btn-ghost">Cancelar</button>
          <button className="btn-primary">Crear</button>
        </div>
      </form>
    </div>
  )
}
