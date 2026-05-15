import { useEffect, useState } from 'react'
import { Plus, X, Users, Hash, Mail, Phone, Percent, Loader2, Check, Trash2, Edit3 } from 'lucide-react'
import api from '../utils/api'

export default function Socios() {
  const [socios, setSocios] = useState([])
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(null)
  const [showInactivos, setShowInactivos] = useState(false)

  const load = async () => {
    setLoading(true)
    const [s, u] = await Promise.all([
      api.get('/api/socios', { params: { activos_solo: !showInactivos } }),
      api.get('/api/users').catch(() => ({ data: [] })),
    ])
    setSocios(s.data); setUsers(u.data)
    setLoading(false)
  }
  useEffect(() => { load() }, [showInactivos])

  const totalPct = socios.filter(s => s.activo).reduce((a, s) => a + (s.participacion_pct || 0), 0)

  return (
    <div className="max-w-7xl mx-auto animate-fade-in">
      <header className="mb-10 flex items-end justify-between gap-6 flex-wrap">
        <div>
          <div className="hero-eyebrow">Finanzas</div>
          <h1 className="hero-title text-5xl md:text-6xl mb-3">Socios.</h1>
          <p className="hero-sub">Personas o entidades con participación en RCA. Cada uno puede hacer aportes a obras.</p>
        </div>
        <button onClick={() => setEditing('new')} className="btn btn-lg btn-primary">
          <Plus size={14}/> Nuevo socio
        </button>
      </header>

      {editing && (
        <SocioModal
          socio={editing === 'new' ? null : editing}
          users={users}
          onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); load() }}
        />
      )}

      <section className="grid md:grid-cols-3 gap-4 mb-8">
        <BigStat label="Socios activos" value={socios.filter(s => s.activo).length} accent="navy"/>
        <BigStat label="Participación total" value={`${totalPct.toFixed(1)}%`} accent={totalPct === 100 ? 'olive' : 'leather'}/>
        <BigStat label="Sin asignar" value={`${(100 - totalPct).toFixed(1)}%`} accent="navy"/>
      </section>

      <div className="flex gap-2 mb-6">
        <button onClick={() => setShowInactivos(false)}
          className={`px-4 py-2 rounded-full text-[13px] font-medium tracking-tight transition ${
            !showInactivos ? 'bg-navy text-bone shadow-soft' : 'bg-bone-100 text-navy hover:bg-bone-200/70'
          }`}>Activos</button>
        <button onClick={() => setShowInactivos(true)}
          className={`px-4 py-2 rounded-full text-[13px] font-medium tracking-tight transition ${
            showInactivos ? 'bg-navy text-bone shadow-soft' : 'bg-bone-100 text-navy hover:bg-bone-200/70'
          }`}>Todos (incluye inactivos)</button>
      </div>

      {loading ? (
        <div className="card p-10 text-center text-muted text-sm">Cargando...</div>
      ) : socios.length === 0 ? (
        <div className="card p-12 text-center">
          <Users size={32} className="mx-auto text-muted/40 mb-3"/>
          <div className="text-muted text-sm mb-3">Sin socios cargados.</div>
          <button onClick={() => setEditing('new')} className="btn btn-primary">
            <Plus size={13}/> Crear primer socio
          </button>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
          {socios.map(s => (
            <SocioCard key={s.id} socio={s} onEdit={() => setEditing(s)}/>
          ))}
        </div>
      )}
    </div>
  )
}

function BigStat({ label, value, accent = 'navy' }) {
  const cls = { navy: 'text-navy', olive: 'text-olive-700', leather: 'text-leather' }[accent]
  return (
    <div className="card p-5">
      <div className="text-[10px] uppercase tracking-[0.18em] text-muted font-semibold mb-2">{label}</div>
      <div className={`text-3xl font-bold tracking-tight ${cls}`}>{value}</div>
    </div>
  )
}

function SocioCard({ socio, onEdit }) {
  return (
    <div onClick={onEdit} className={`card card-hover cursor-pointer p-6 group ${!socio.activo ? 'opacity-60' : ''}`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <div className="text-[10px] uppercase tracking-[0.18em] text-olive-700 font-semibold mb-1">
            Socio {!socio.activo && <span className="text-leather">· Inactivo</span>}
          </div>
          <h3 className="hero-title text-lg leading-tight truncate">
            {socio.nombre} {socio.apellido || ''}
          </h3>
        </div>
        <Edit3 size={14} className="text-muted/40 group-hover:text-navy transition shrink-0"/>
      </div>
      <div className="space-y-1.5 text-[12px] text-navy/80">
        {socio.cuit && <div className="flex items-center gap-2"><Hash size={11} className="text-muted shrink-0"/> {socio.cuit}</div>}
        {socio.email && <div className="flex items-center gap-2 truncate"><Mail size={11} className="text-muted shrink-0"/> {socio.email}</div>}
        {socio.telefono && <div className="flex items-center gap-2"><Phone size={11} className="text-muted shrink-0"/> {socio.telefono}</div>}
      </div>
      <div className="flex items-center justify-between mt-4 pt-4 border-t border-border/60">
        {socio.participacion_pct != null && (
          <span className="chip chip-navy text-[10px] inline-flex items-center gap-1">
            <Percent size={10}/> {Number(socio.participacion_pct).toFixed(0)}%
          </span>
        )}
        {socio.user_id && <span className="text-[11px] text-muted">User #{socio.user_id}</span>}
      </div>
    </div>
  )
}

function SocioModal({ socio, users, onClose, onSaved }) {
  const [nombre, setNombre] = useState(socio?.nombre || '')
  const [apellido, setApellido] = useState(socio?.apellido || '')
  const [cuit, setCuit] = useState(socio?.cuit || '')
  const [email, setEmail] = useState(socio?.email || '')
  const [telefono, setTelefono] = useState(socio?.telefono || '')
  const [participacion, setParticipacion] = useState(socio?.participacion_pct ?? '')
  const [userId, setUserId] = useState(socio?.user_id || '')
  const [activo, setActivo] = useState(socio?.activo ?? true)
  const [notas, setNotas] = useState(socio?.notas || '')
  const [submitting, setSubmitting] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState('')

  const isNew = !socio
  const formListo = nombre.trim().length > 0

  const submit = async () => {
    setError(''); setSubmitting(true)
    try {
      const payload = {
        nombre: nombre.trim(),
        apellido: apellido.trim() || null,
        cuit: cuit.trim() || null,
        email: email.trim() || null,
        telefono: telefono.trim() || null,
        participacion_pct: participacion === '' ? null : Number(participacion),
        user_id: userId ? Number(userId) : null,
        activo,
        notas: notas.trim() || null,
      }
      if (isNew) await api.post('/api/socios', payload)
      else await api.put(`/api/socios/${socio.id}`, payload)
      onSaved()
    } catch (e) {
      setError(e.response?.data?.detail || 'Error al guardar')
      setSubmitting(false)
    }
  }

  const handleDelete = async () => {
    if (!confirm(`¿Eliminar socio "${socio.nombre}"?`)) return
    setError(''); setDeleting(true)
    try {
      await api.delete(`/api/socios/${socio.id}`)
      onSaved()
    } catch (e) {
      setError(e.response?.data?.detail || 'Error al eliminar')
      setDeleting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-navy/30 backdrop-blur-sm z-50 grid place-items-center p-4 animate-fade-in" onClick={onClose}>
      <div className="card p-0 max-w-2xl w-full max-h-[90vh] overflow-hidden shadow-lift flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="px-7 py-5 border-b border-border/60 flex items-center justify-between">
          <div>
            <div className="hero-eyebrow !text-[10px]">Finanzas</div>
            <h2 className="hero-title text-2xl">{isNew ? 'Nuevo socio.' : 'Editar socio.'}</h2>
          </div>
          <button onClick={onClose} className="p-2 rounded-full text-muted hover:bg-bone-200/70 hover:text-navy transition">
            <X size={16}/>
          </button>
        </div>

        <div className="px-7 py-5 overflow-y-auto flex-1 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Nombre" required><input className="input-base" value={nombre} onChange={e => setNombre(e.target.value)}/></Field>
            <Field label="Apellido"><input className="input-base" value={apellido} onChange={e => setApellido(e.target.value)}/></Field>
            <Field label="CUIT"><input className="input-base" value={cuit} onChange={e => setCuit(e.target.value)} placeholder="20-12345678-9"/></Field>
            <Field label="Participación %"><input type="number" min="0" max="100" step="0.01" className="input-base" value={participacion} onChange={e => setParticipacion(e.target.value)} placeholder="ej: 50"/></Field>
            <Field label="Email"><input type="email" className="input-base" value={email} onChange={e => setEmail(e.target.value)}/></Field>
            <Field label="Teléfono"><input className="input-base" value={telefono} onChange={e => setTelefono(e.target.value)} placeholder="+5491100000000"/></Field>
            <div className="col-span-2">
              <Field label="Vincular a usuario (opcional)">
                <select className="select-base" value={userId} onChange={e => setUserId(e.target.value)}>
                  <option value="">— sin vincular —</option>
                  {users.map(u => <option key={u.id} value={u.id}>{u.name} {u.last_name || ''} ({u.email})</option>)}
                </select>
              </Field>
            </div>
            <div className="col-span-2">
              <Field label="Notas"><textarea className="input-base min-h-[60px]" value={notas} onChange={e => setNotas(e.target.value)}/></Field>
            </div>
            {!isNew && (
              <div className="col-span-2">
                <label className="flex items-center gap-2 text-[12px] text-navy">
                  <input type="checkbox" checked={activo} onChange={e => setActivo(e.target.checked)} className="rounded"/>
                  Socio activo
                </label>
              </div>
            )}
          </div>
          {error && <div className="p-3 rounded-xl bg-danger/10 border border-danger/30 text-[12px] text-danger">{error}</div>}
        </div>

        <div className="px-7 py-4 border-t border-border/60 flex items-center justify-between bg-bone-100/30">
          <div>
            {!isNew && (
              <button onClick={handleDelete} disabled={deleting} className="btn btn-danger">
                {deleting ? <Loader2 size={13} className="animate-spin"/> : <Trash2 size={13}/>}
                Eliminar
              </button>
            )}
          </div>
          <div className="flex gap-2">
            <button onClick={onClose} className="btn btn-ghost">Cancelar</button>
            <button onClick={submit} disabled={!formListo || submitting} className="btn btn-primary">
              {submitting ? <Loader2 size={13} className="animate-spin"/> : <Check size={13}/>}
              {isNew ? 'Crear socio' : 'Guardar cambios'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function Field({ label, required, children }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-[10px] uppercase tracking-wide text-muted font-semibold">
        {label}{required && <span className="text-danger ml-1">*</span>}
      </span>
      {children}
    </label>
  )
}
