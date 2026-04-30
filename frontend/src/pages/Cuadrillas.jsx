import { useEffect, useState } from 'react'
import { Plus, Phone, Trash2 } from 'lucide-react'
import api from '../utils/api'

const ESPECIALIDADES = ['albañilería', 'electricidad', 'plomería', 'pintura', 'herrería', 'otros']

export default function Cuadrillas() {
  const [list, setList] = useState([])
  const [open, setOpen] = useState(false)

  const load = () => api.get('/api/cuadrillas/').then(r => setList(r.data))
  useEffect(() => { load() }, [])

  const eliminar = async (id) => {
    if (confirm('¿Desactivar cuadrilla?')) { await api.delete(`/api/cuadrillas/${id}`); load() }
  }

  return (
    <div className="max-w-6xl mx-auto animate-fade-in">
      <header className="mb-12">
        <div className="hero-eyebrow">Recursos humanos</div>
        <div className="flex items-end justify-between flex-wrap gap-4">
          <div>
            <h1 className="hero-title text-5xl md:text-6xl mb-3">Cuadrillas.</h1>
            <p className="hero-sub">Equipos de trabajo organizados por especialidad.</p>
          </div>
          <button onClick={()=>setOpen(true)} className="btn-primary"><Plus size={14}/> Nueva cuadrilla</button>
        </div>
      </header>

      {list.length === 0 ? (
        <div className="card text-center py-20">
          <div className="text-5xl mb-3 opacity-30">○</div>
          <p className="text-muted">Aún no hay cuadrillas registradas.</p>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {list.map(c => (
            <div key={c.id} className="card p-6 card-hover">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <div className="font-bold text-lg tracking-tight">{c.nombre}</div>
                  <div className="text-xs uppercase tracking-wider text-muted mt-1 capitalize">{c.especialidad}</div>
                </div>
                <button onClick={()=>eliminar(c.id)} className="text-muted/60 hover:text-danger transition"><Trash2 size={14}/></button>
              </div>

              <div className="grid grid-cols-3 gap-3 py-4 border-y border-border">
                <Stat label="Miembros" value={c.cantidad_miembros}/>
                <Stat label="Nivel" value={c.nivel} accent/>
                <Stat label="Eficiencia" value={`${Math.round(c.eficiencia)}%`}/>
              </div>

              <div className="mt-4">
                <div className="flex justify-between text-[10px] uppercase tracking-wider text-muted mb-1">
                  <span>Experiencia</span>
                  <span>{c.experiencia % 100}/100</span>
                </div>
                <div className="h-1 bg-bone-200 rounded-full overflow-hidden">
                  <div className="h-full bg-olive transition-all" style={{ width: `${c.experiencia % 100}%` }}/>
                </div>
              </div>

              {c.telefono && (
                <div className="mt-4 pt-4 border-t border-border text-xs text-muted flex items-center gap-1.5">
                  <Phone size={11}/> {c.telefono}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {open && <NewCuadrillaModal onClose={()=>setOpen(false)} onSaved={()=>{ setOpen(false); load() }}/>}
    </div>
  )
}

function Stat({ label, value, accent }) {
  return (
    <div className="text-center">
      <div className={`text-xl font-bold tracking-tight ${accent ? 'text-olive-700' : 'text-navy'}`}>{value}</div>
      <div className="text-[10px] uppercase tracking-wider text-muted mt-0.5">{label}</div>
    </div>
  )
}

function NewCuadrillaModal({ onClose, onSaved }) {
  const [form, setForm] = useState({
    nombre: '', especialidad: 'albañilería', cantidad_miembros: 4, telefono: '',
    avatar: '👷', color: '#3D4F1E',
  })
  const submit = async (e) => {
    e.preventDefault()
    await api.post('/api/cuadrillas/', { ...form, cantidad_miembros: parseInt(form.cantidad_miembros)||1 })
    onSaved()
  }
  return (
    <div className="fixed inset-0 bg-navy/30 backdrop-blur-sm grid place-items-center z-50 p-4 animate-fade-in" onClick={onClose}>
      <form onClick={e=>e.stopPropagation()} onSubmit={submit} className="card w-full max-w-md p-8 space-y-4 shadow-lift animate-scale-in">
        <h2 className="hero-title text-2xl">Nueva cuadrilla</h2>
        <div><label className="label">Nombre</label><input className="input" value={form.nombre} onChange={e=>setForm({...form,nombre:e.target.value})} required/></div>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="label">Especialidad</label>
            <select className="input" value={form.especialidad} onChange={e=>setForm({...form,especialidad:e.target.value})}>
              {ESPECIALIDADES.map(e => <option key={e}>{e}</option>)}
            </select>
          </div>
          <div><label className="label">Miembros</label><input className="input" type="number" value={form.cantidad_miembros} onChange={e=>setForm({...form,cantidad_miembros:e.target.value})}/></div>
        </div>
        <div><label className="label">WhatsApp</label><input className="input" value={form.telefono} onChange={e=>setForm({...form,telefono:e.target.value})}/></div>
        <div className="flex gap-2 justify-end pt-2">
          <button type="button" onClick={onClose} className="btn-ghost">Cancelar</button>
          <button className="btn-primary">Crear</button>
        </div>
      </form>
    </div>
  )
}
