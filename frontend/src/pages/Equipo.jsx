import { useEffect, useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import api from '../utils/api'

const ROLES = [
  { v: 'admin_finanzas', l: 'Admin con Finanzas' },
  { v: 'admin', l: 'Admin / PM' },
  { v: 'supervisor', l: 'Supervisor' },
  { v: 'usuario_bot', l: 'Usuario Bot WA' },
]

export default function Equipo() {
  const [list, setList] = useState([])
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ name:'', email:'', phone:'', password:'', role:'usuario_bot' })

  const load = () => api.get('/api/users/').then(r => setList(r.data))
  useEffect(() => { load() }, [])

  const invitar = async (e) => {
    e.preventDefault()
    try {
      await api.post('/api/users/invite', form)
      setOpen(false); setForm({ name:'', email:'', phone:'', password:'', role:'usuario_bot' })
      load()
    } catch (err) { alert(err.response?.data?.detail || 'Error') }
  }
  const cambiarRol = async (id, role) => { await api.patch(`/api/users/${id}/role`, { role }); load() }
  const eliminar = async (id) => { if (confirm('¿Eliminar?')) { await api.delete(`/api/users/${id}`); load() } }

  return (
    <div className="max-w-5xl mx-auto animate-fade-in">
      <header className="mb-12">
        <div className="hero-eyebrow">Administración</div>
        <div className="flex items-end justify-between flex-wrap gap-4">
          <div>
            <h1 className="hero-title text-5xl md:text-6xl mb-3">Usuarios.</h1>
            <p className="hero-sub">Gestión de accesos y permisos del sistema.</p>
          </div>
          <button onClick={()=>setOpen(true)} className="btn-primary"><Plus size={14}/> Invitar usuario</button>
        </div>
      </header>

      <div className="card divide-y divide-border">
        {list.map(u => (
          <div key={u.id} className="p-5 flex items-center gap-4">
            <div className="w-11 h-11 rounded-full bg-navy text-bone grid place-items-center font-semibold shrink-0">
              {u.name?.[0]?.toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-semibold">{u.name} {u.last_name || ''}</div>
              <div className="text-xs text-muted truncate mt-0.5">{u.email} {u.phone && `· ${u.phone}`}</div>
            </div>
            <select value={u.role} onChange={e=>cambiarRol(u.id, e.target.value)}
              className="input !w-auto !py-2 text-sm">
              {ROLES.map(r => <option key={r.v} value={r.v}>{r.l}</option>)}
            </select>
            <button onClick={()=>eliminar(u.id)} className="text-muted/60 hover:text-danger p-2"><Trash2 size={14}/></button>
          </div>
        ))}
      </div>

      {open && (
        <div className="fixed inset-0 bg-navy/30 backdrop-blur-sm grid place-items-center z-50 p-4 animate-fade-in" onClick={()=>setOpen(false)}>
          <form onClick={e=>e.stopPropagation()} onSubmit={invitar} className="card w-full max-w-md p-8 space-y-4 shadow-lift animate-scale-in">
            <h2 className="hero-title text-2xl">Invitar usuario</h2>
            <div><label className="label">Nombre</label><input className="input" value={form.name} onChange={e=>setForm({...form,name:e.target.value})} required/></div>
            <div><label className="label">Email</label><input className="input" type="email" value={form.email} onChange={e=>setForm({...form,email:e.target.value})} required/></div>
            <div><label className="label">WhatsApp</label><input className="input" value={form.phone} onChange={e=>setForm({...form,phone:e.target.value})} placeholder="+54911..."/></div>
            <div><label className="label">Contraseña inicial</label><input className="input" type="password" minLength={6} value={form.password} onChange={e=>setForm({...form,password:e.target.value})} required/></div>
            <div><label className="label">Rol</label>
              <select className="input" value={form.role} onChange={e=>setForm({...form,role:e.target.value})}>
                {ROLES.map(r => <option key={r.v} value={r.v}>{r.l}</option>)}
              </select>
            </div>
            <div className="flex gap-2 justify-end pt-2">
              <button type="button" onClick={()=>setOpen(false)} className="btn-ghost">Cancelar</button>
              <button className="btn-primary">Invitar</button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
