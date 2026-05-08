import { useEffect, useState } from 'react'
import { Plus, X, Building2, Mail, Phone, Hash, Loader2, Check, Trash2, Edit3 } from 'lucide-react'
import api from '../utils/api'

const TIPOS = [
  { value: 'publico', label: 'Público', desc: 'Estado, municipios, organismos' },
  { value: 'privado_ri', label: 'Privado RI', desc: 'Empresa Responsable Inscripta' },
  { value: 'privado_mt', label: 'Privado MT', desc: 'Empresa Monotributista' },
  { value: 'particular', label: 'Particular', desc: 'Persona física, consumidor final' },
]

export default function Clientes() {
  const [clientes, setClientes] = useState([])
  const [obras, setObras] = useState([])
  const [regimenes, setRegimenes] = useState([])
  const [loading, setLoading] = useState(true)
  const [filterTipo, setFilterTipo] = useState('')
  const [editing, setEditing] = useState(null)  // null | 'new' | cliente object

  const load = async () => {
    setLoading(true)
    const [c, o, r] = await Promise.all([
      api.get('/api/clientes'),
      api.get('/api/obras'),
      api.get('/api/regimenes-fiscales').catch(() => ({ data: [] })),
    ])
    setClientes(c.data); setObras(o.data); setRegimenes(r.data)
    setLoading(false)
  }
  useEffect(() => { load() }, [])

  const obrasPorCliente = (cid) => obras.filter(o => o.cliente_id === cid)
  const filtered = filterTipo ? clientes.filter(c => c.tipo === filterTipo) : clientes

  return (
    <div className="max-w-7xl mx-auto animate-fade-in">
      <header className="mb-10 flex items-end justify-between gap-6 flex-wrap">
        <div>
          <div className="hero-eyebrow">Finanzas</div>
          <h1 className="hero-title text-5xl md:text-6xl mb-3">Clientes.</h1>
          <p className="hero-sub">Empresas y particulares que contratan obras. Cada uno define su régimen fiscal por defecto.</p>
        </div>
        <button onClick={() => setEditing('new')} className="btn btn-lg btn-primary">
          <Plus size={14}/> Nuevo cliente
        </button>
      </header>

      {editing && (
        <ClienteModal
          cliente={editing === 'new' ? null : editing}
          regimenes={regimenes}
          onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); load() }}
        />
      )}

      {/* Filtros pill */}
      <div className="flex gap-2 mb-6 flex-wrap">
        <PillBtn active={!filterTipo} onClick={() => setFilterTipo('')}>
          Todos <span className="opacity-60 ml-1">{clientes.length}</span>
        </PillBtn>
        {TIPOS.map(t => {
          const count = clientes.filter(c => c.tipo === t.value).length
          if (count === 0) return null
          return (
            <PillBtn key={t.value} active={filterTipo === t.value} onClick={() => setFilterTipo(t.value)}>
              {t.label} <span className="opacity-60 ml-1">{count}</span>
            </PillBtn>
          )
        })}
      </div>

      {loading ? (
        <div className="card p-10 text-center text-muted text-sm">Cargando...</div>
      ) : filtered.length === 0 ? (
        <div className="card p-12 text-center">
          <Building2 size={32} className="mx-auto text-muted/40 mb-3"/>
          <div className="text-muted text-sm mb-3">No hay clientes que coincidan.</div>
          <button onClick={() => setEditing('new')} className="btn btn-primary">
            <Plus size={13}/> Crear primer cliente
          </button>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filtered.map(c => (
            <ClienteCard
              key={c.id}
              cliente={c}
              obras={obrasPorCliente(c.id)}
              regimenes={regimenes}
              onEdit={() => setEditing(c)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function PillBtn({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 rounded-full text-[13px] font-medium tracking-tight transition ${
        active ? 'bg-navy text-bone shadow-soft' : 'bg-bone-100 text-navy hover:bg-bone-200/70'
      }`}
    >
      {children}
    </button>
  )
}

function ClienteCard({ cliente, obras, regimenes, onEdit }) {
  const tipoInfo = TIPOS.find(t => t.value === cliente.tipo)
  const regimen = regimenes.find(r => r.id === cliente.regimen_fiscal_id)
  return (
    <div onClick={onEdit} className="card card-hover cursor-pointer p-6 group">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <div className="text-[10px] uppercase tracking-[0.18em] text-olive-700 font-semibold mb-1">
            {tipoInfo?.label || cliente.tipo || 'Sin tipo'}
          </div>
          <h3 className="hero-title text-lg leading-tight mb-1 truncate">{cliente.nombre}</h3>
          {cliente.razon_social && cliente.razon_social !== cliente.nombre && (
            <p className="text-[11px] text-muted truncate">{cliente.razon_social}</p>
          )}
        </div>
        <Edit3 size={14} className="text-muted/40 group-hover:text-navy transition shrink-0"/>
      </div>

      <div className="space-y-1.5 text-[12px] text-navy/80">
        {cliente.cuit && (
          <div className="flex items-center gap-2"><Hash size={11} className="text-muted shrink-0"/> {cliente.cuit}</div>
        )}
        {cliente.email && (
          <div className="flex items-center gap-2 truncate"><Mail size={11} className="text-muted shrink-0"/> {cliente.email}</div>
        )}
        {cliente.telefono && (
          <div className="flex items-center gap-2"><Phone size={11} className="text-muted shrink-0"/> {cliente.telefono}</div>
        )}
      </div>

      <div className="flex items-center justify-between mt-4 pt-4 border-t border-border/60">
        <span className="chip chip-navy text-[10px]">
          {regimen ? regimen.codigo : 'sin régimen'}
        </span>
        <span className="text-[11px] text-muted">
          {obras.length === 0 ? 'Sin obras' : `${obras.length} obra${obras.length > 1 ? 's' : ''}`}
        </span>
      </div>
    </div>
  )
}

function ClienteModal({ cliente, regimenes, onClose, onSaved }) {
  const [nombre, setNombre] = useState(cliente?.nombre || '')
  const [razonSocial, setRazonSocial] = useState(cliente?.razon_social || '')
  const [cuit, setCuit] = useState(cliente?.cuit || '')
  const [tipo, setTipo] = useState(cliente?.tipo || 'privado_ri')
  const [regimenId, setRegimenId] = useState(cliente?.regimen_fiscal_id || '')
  const [email, setEmail] = useState(cliente?.email || '')
  const [telefono, setTelefono] = useState(cliente?.telefono || '')
  const [direccion, setDireccion] = useState(cliente?.direccion || '')
  const [notas, setNotas] = useState(cliente?.notas || '')
  const [activo, setActivo] = useState(cliente?.activo ?? true)
  const [submitting, setSubmitting] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState('')

  const isNew = !cliente
  const formListo = nombre.trim().length > 0

  const submit = async () => {
    setError(''); setSubmitting(true)
    try {
      const payload = {
        nombre: nombre.trim(),
        razon_social: razonSocial.trim() || null,
        cuit: cuit.trim() || null,
        tipo: tipo || null,
        regimen_fiscal_id: regimenId ? Number(regimenId) : null,
        email: email.trim() || null,
        telefono: telefono.trim() || null,
        direccion: direccion.trim() || null,
        notas: notas.trim() || null,
        activo,
      }
      if (isNew) await api.post('/api/clientes', payload)
      else await api.put(`/api/clientes/${cliente.id}`, payload)
      onSaved()
    } catch (e) {
      setError(e.response?.data?.detail || 'Error al guardar')
      setSubmitting(false)
    }
  }

  const handleDelete = async () => {
    if (!confirm(`¿Eliminar cliente "${cliente.nombre}"?`)) return
    setError(''); setDeleting(true)
    try {
      await api.delete(`/api/clientes/${cliente.id}`)
      onSaved()
    } catch (e) {
      setError(e.response?.data?.detail || 'Error al eliminar')
      setDeleting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-navy/30 backdrop-blur-sm z-50 grid place-items-center p-4 animate-fade-in"
         onClick={onClose}>
      <div className="card p-0 max-w-2xl w-full max-h-[90vh] overflow-hidden shadow-lift flex flex-col"
           onClick={e => e.stopPropagation()}>
        <div className="px-7 py-5 border-b border-border/60 flex items-center justify-between">
          <div>
            <div className="hero-eyebrow !text-[10px]">Finanzas</div>
            <h2 className="hero-title text-2xl">{isNew ? 'Nuevo cliente.' : 'Editar cliente.'}</h2>
          </div>
          <button onClick={onClose} className="p-2 rounded-full text-muted hover:bg-bone-200/70 hover:text-navy transition">
            <X size={16}/>
          </button>
        </div>

        <div className="px-7 py-5 overflow-y-auto flex-1 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <Field label="Nombre" required>
                <input className="input-base" value={nombre} onChange={e => setNombre(e.target.value)} placeholder="ej: Constructora San Pedro SA"/>
              </Field>
            </div>
            <Field label="Razón social">
              <input className="input-base" value={razonSocial} onChange={e => setRazonSocial(e.target.value)} placeholder="(si difiere del nombre)"/>
            </Field>
            <Field label="CUIT">
              <input className="input-base" value={cuit} onChange={e => setCuit(e.target.value)} placeholder="30-12345678-9"/>
            </Field>
            <Field label="Tipo">
              <select className="select-base" value={tipo} onChange={e => setTipo(e.target.value)}>
                <option value="">— sin tipo —</option>
                {TIPOS.map(t => <option key={t.value} value={t.value}>{t.label} — {t.desc}</option>)}
              </select>
            </Field>
            <Field label="Régimen fiscal">
              <select className="select-base" value={regimenId} onChange={e => setRegimenId(e.target.value)}>
                <option value="">— heredar al crear obra —</option>
                {regimenes.map(r => <option key={r.id} value={r.id}>{r.codigo} — {r.nombre}</option>)}
              </select>
            </Field>
            <Field label="Email">
              <input className="input-base" type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="contacto@cliente.com"/>
            </Field>
            <Field label="Teléfono">
              <input className="input-base" value={telefono} onChange={e => setTelefono(e.target.value)} placeholder="+5491100000000"/>
            </Field>
            <div className="col-span-2">
              <Field label="Dirección">
                <input className="input-base" value={direccion} onChange={e => setDireccion(e.target.value)}/>
              </Field>
            </div>
            <div className="col-span-2">
              <Field label="Notas">
                <textarea className="input-base min-h-[60px]" value={notas} onChange={e => setNotas(e.target.value)}/>
              </Field>
            </div>
            {!isNew && (
              <div className="col-span-2">
                <label className="flex items-center gap-2 text-[12px] text-navy">
                  <input type="checkbox" checked={activo} onChange={e => setActivo(e.target.checked)} className="rounded"/>
                  Cliente activo
                </label>
              </div>
            )}
          </div>

          {error && (
            <div className="p-3 rounded-xl bg-danger/10 border border-danger/30 text-[12px] text-danger">
              {error}
            </div>
          )}
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
              {isNew ? 'Crear cliente' : 'Guardar cambios'}
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
