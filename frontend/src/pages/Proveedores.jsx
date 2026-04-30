import { useEffect, useState } from 'react'
import { Star, Plus, Phone, Mail, Trash2, Clock } from 'lucide-react'
import api from '../utils/api'

export default function Proveedores() {
  const [list, setList] = useState([])
  const [open, setOpen] = useState(false)

  const load = () => api.get('/api/proveedores/').then(r => setList(r.data))
  useEffect(() => { load() }, [])

  const eliminar = async (id) => {
    if (confirm('¿Eliminar?')) { await api.delete(`/api/proveedores/${id}`); load() }
  }

  return (
    <div className="max-w-6xl mx-auto animate-fade-in">
      <header className="mb-12">
        <div className="hero-eyebrow">Red de aliados</div>
        <div className="flex items-end justify-between flex-wrap gap-4">
          <div>
            <h1 className="hero-title text-5xl md:text-6xl mb-3">Proveedores.</h1>
            <p className="hero-sub">Tu red de confianza, evaluada y siempre disponible.</p>
          </div>
          <button onClick={()=>setOpen(true)} className="btn-primary"><Plus size={14}/> Nuevo proveedor</button>
        </div>
      </header>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {list.map(p => (
          <div key={p.id} className="card p-6 card-hover">
            <div className="flex items-start justify-between mb-3">
              <div>
                <div className="font-bold text-lg tracking-tight">{p.nombre}</div>
                <div className="text-xs uppercase tracking-wider text-muted mt-1 capitalize">{p.rubro}</div>
              </div>
              <button onClick={()=>eliminar(p.id)} className="text-muted/60 hover:text-danger transition"><Trash2 size={14}/></button>
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
          </div>
        ))}
      </div>

      {open && <NewProveedorModal onClose={()=>setOpen(false)} onSaved={()=>{ setOpen(false); load() }}/>}
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
