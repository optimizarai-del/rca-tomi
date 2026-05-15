import { useEffect, useMemo, useState } from 'react'
import {
  HandCoins, ArrowDownLeft, ArrowUpRight, Plus, X, Loader2, Check, AlertCircle,
} from 'lucide-react'
import api from '../utils/api'

const MEDIOS = ['EFECTIVO', 'TRANSFERENCIA', 'CHEQUE_PROPIO', 'CHEQUE_TERCERO', 'DEPOSITO_BANCARIO']
const SHORT = (s) => s ? s.replace(/_/g, ' ').toLowerCase().replace(/^./, c => c.toUpperCase()) : '—'
const fmtMoney = (n) => {
  if (n == null || n === 0) return '$0'
  const sign = n < 0 ? '-' : ''
  const abs = Math.abs(n)
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(2)}M`
  if (abs >= 1e3) return `${sign}$${(abs / 1e3).toFixed(0)}k`
  return `${sign}$${Math.round(abs)}`
}
const fmtDate = (s) => s ? new Date(s).toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: '2-digit' }) : '—'

const ESTADO_CHIP = {
  PENDIENTE: 'chip-warn',
  DEVUELTO_PARCIAL: 'chip-navy',
  DEVUELTO_TOTAL: 'chip-olive',
}

export default function Aportes() {
  const [aportes, setAportes] = useState([])
  const [obras, setObras] = useState([])
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [filterEstado, setFilterEstado] = useState('')
  const [filterObra, setFilterObra] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)
  const [showNew, setShowNew] = useState(false)
  const [devolverAporte, setDevolverAporte] = useState(null)

  const load = async () => {
    setLoading(true)
    const params = {}
    if (filterObra) params.obra_id = filterObra
    const [a, o, u] = await Promise.all([
      api.get('/api/aportes', { params }),
      api.get('/api/obras'),
      api.get('/api/users').catch(() => ({ data: [] })),
    ])
    setAportes(a.data); setObras(o.data); setUsers(u.data)
    setLoading(false)
  }
  useEffect(() => { load() }, [filterObra, refreshKey])

  const obraById = (id) => obras.find(o => o.id === id)
  const userById = (id) => users.find(u => u.id === id)

  const filtered = useMemo(() => {
    return aportes.filter(a => {
      if (filterEstado && a.estado_devolucion !== filterEstado) return false
      return true
    })
  }, [aportes, filterEstado])

  const totales = useMemo(() => {
    let monto = 0, devuelto = 0
    for (const a of filtered) {
      monto += a.monto
      devuelto += a.monto_devuelto
    }
    return { monto, devuelto, pendiente: monto - devuelto, count: filtered.length }
  }, [filtered])

  return (
    <div className="max-w-7xl mx-auto animate-fade-in">
      <header className="mb-10 flex items-end justify-between gap-6 flex-wrap">
        <div>
          <div className="hero-eyebrow">Finanzas</div>
          <h1 className="hero-title text-5xl md:text-6xl mb-3">Aportes.</h1>
          <p className="hero-sub">Préstamos internos de socios a la obra. Cada uno genera un INGRESO espejo automático (R2).</p>
        </div>
        <button onClick={() => setShowNew(true)} className="btn btn-lg btn-primary">
          <Plus size={14}/> Nuevo aporte
        </button>
      </header>

      {showNew && (
        <NuevoAporteModal
          obras={obras}
          users={users}
          onClose={() => setShowNew(false)}
          onSaved={() => { setShowNew(false); setRefreshKey(k => k + 1) }}
        />
      )}
      {devolverAporte && (
        <DevolucionModal
          aporte={devolverAporte}
          obra={obraById(devolverAporte.obra_id)}
          onClose={() => setDevolverAporte(null)}
          onSaved={() => { setDevolverAporte(null); setRefreshKey(k => k + 1) }}
        />
      )}

      {/* Big numbers */}
      <section className="grid md:grid-cols-4 gap-4 mb-8">
        <BigNumber label="Total aportado" value={fmtMoney(totales.monto)} accent="navy"/>
        <BigNumber label="Devuelto" value={fmtMoney(totales.devuelto)} accent="olive"/>
        <BigNumber label="Pendiente" value={fmtMoney(totales.pendiente)} accent="leather"/>
        <BigNumber label="Aportes" value={String(totales.count)} accent="navy"/>
      </section>

      {/* Filtros pill */}
      <div className="flex gap-2 mb-6 flex-wrap">
        <PillBtn active={!filterEstado} onClick={() => setFilterEstado('')}>
          Todos <span className="opacity-60 ml-1">{aportes.length}</span>
        </PillBtn>
        <PillBtn active={filterEstado === 'PENDIENTE'} onClick={() => setFilterEstado('PENDIENTE')}>
          Pendientes <span className="opacity-60 ml-1">{aportes.filter(a => a.estado_devolucion === 'PENDIENTE').length}</span>
        </PillBtn>
        <PillBtn active={filterEstado === 'DEVUELTO_PARCIAL'} onClick={() => setFilterEstado('DEVUELTO_PARCIAL')}>
          Parciales <span className="opacity-60 ml-1">{aportes.filter(a => a.estado_devolucion === 'DEVUELTO_PARCIAL').length}</span>
        </PillBtn>
        <PillBtn active={filterEstado === 'DEVUELTO_TOTAL'} onClick={() => setFilterEstado('DEVUELTO_TOTAL')}>
          Devueltos <span className="opacity-60 ml-1">{aportes.filter(a => a.estado_devolucion === 'DEVUELTO_TOTAL').length}</span>
        </PillBtn>
        <select
          value={filterObra}
          onChange={e => setFilterObra(e.target.value)}
          className="rounded-full px-4 py-2 text-[13px] bg-bone-100 text-navy hover:bg-bone-200/70 transition focus:outline-none"
        >
          <option value="">Todas las obras</option>
          {obras.map(o => <option key={o.id} value={o.id}>{o.codigo} — {o.nombre}</option>)}
        </select>
      </div>

      {/* Tabla */}
      <section className="card overflow-hidden">
        {loading ? (
          <div className="p-10 text-center text-muted text-sm">Cargando...</div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center">
            <HandCoins size={32} className="mx-auto text-muted/40 mb-3"/>
            <div className="text-muted text-sm mb-3">No hay aportes que coincidan.</div>
            <button onClick={() => setShowNew(true)} className="btn btn-primary">
              <Plus size={13}/> Registrar primer aporte
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-[12px]">
              <thead>
                <tr className="bg-bone-100/50 text-muted uppercase text-[10px] tracking-wide">
                  <th className="text-left px-4 py-3 font-semibold">Fecha</th>
                  <th className="text-left px-4 py-3 font-semibold">Obra</th>
                  <th className="text-left px-4 py-3 font-semibold">Socio</th>
                  <th className="text-left px-4 py-3 font-semibold">Motivo</th>
                  <th className="text-right px-4 py-3 font-semibold">Monto</th>
                  <th className="text-right px-4 py-3 font-semibold">Devuelto</th>
                  <th className="text-right px-4 py-3 font-semibold">Pendiente</th>
                  <th className="text-left px-4 py-3 font-semibold">Estado</th>
                  <th className="text-right px-4 py-3 font-semibold"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50">
                {filtered.map(a => {
                  const obra = obraById(a.obra_id)
                  const socio = userById(a.socio_id)
                  const pendiente = a.monto - a.monto_devuelto
                  const isDone = a.estado_devolucion === 'DEVUELTO_TOTAL'
                  return (
                    <tr key={a.id} className="hover:bg-bone-100/30 transition">
                      <td className="px-4 py-3 whitespace-nowrap text-navy/80">{fmtDate(a.fecha_aporte)}</td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="text-[10px] uppercase tracking-wide font-semibold text-muted">{obra?.codigo}</span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-navy">
                        {socio ? `${socio.name} ${socio.last_name || ''}`.trim() : `Socio #${a.socio_id}`}
                      </td>
                      <td className="px-4 py-3 max-w-xs truncate text-navy/80" title={a.motivo}>{a.motivo}</td>
                      <td className="px-4 py-3 text-right font-mono font-semibold whitespace-nowrap text-navy">{fmtMoney(a.monto)}</td>
                      <td className="px-4 py-3 text-right font-mono whitespace-nowrap text-olive-700">{fmtMoney(a.monto_devuelto)}</td>
                      <td className="px-4 py-3 text-right font-mono whitespace-nowrap text-leather">{fmtMoney(pendiente)}</td>
                      <td className="px-4 py-3">
                        <span className={`chip ${ESTADO_CHIP[a.estado_devolucion]} text-[10px]`}>
                          {SHORT(a.estado_devolucion)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right whitespace-nowrap">
                        {!isDone && (
                          <button
                            onClick={() => setDevolverAporte(a)}
                            className="text-[11px] px-3 py-1.5 rounded-full bg-olive/10 text-olive-700 hover:bg-olive/20 transition font-medium"
                          >
                            <ArrowUpRight size={11} className="inline mr-1"/>
                            Registrar devolución
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}

function BigNumber({ label, value, accent = 'navy' }) {
  const cls = { navy: 'text-navy', olive: 'text-olive-700', leather: 'text-leather' }[accent]
  return (
    <div className="card p-5">
      <div className="text-[10px] uppercase tracking-[0.18em] text-muted font-semibold mb-2">{label}</div>
      <div className={`text-3xl font-bold tracking-tight ${cls}`}>{value}</div>
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

function NuevoAporteModal({ obras, users, onClose, onSaved }) {
  const today = new Date().toISOString().slice(0, 10)
  const [obraId, setObraId] = useState('')
  const [socioId, setSocioId] = useState('')
  const [monto, setMonto] = useState('')
  const [motivo, setMotivo] = useState('')
  const [fecha, setFecha] = useState(today)
  const [medio, setMedio] = useState('TRANSFERENCIA')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const formListo = obraId && socioId && monto && Number(monto) > 0 && motivo.trim() && medio

  const submit = async () => {
    setError(''); setSubmitting(true)
    try {
      await api.post('/api/aportes', {
        obra_id: Number(obraId),
        socio_id: Number(socioId),
        fecha_aporte: fecha,
        monto: Number(monto),
        motivo: motivo.trim(),
        medio_pago: medio,
      })
      onSaved()
    } catch (e) {
      setError(e.response?.data?.detail || 'Error al guardar')
      setSubmitting(false)
    }
  }

  return (
    <ModalShell title="Nuevo aporte." onClose={onClose}>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Obra" required>
          <select className="select-base" value={obraId} onChange={e => setObraId(e.target.value)}>
            <option value="">Elegir obra...</option>
            {obras.map(o => <option key={o.id} value={o.id}>{o.codigo} — {o.nombre}</option>)}
          </select>
        </Field>
        <Field label="Socio" required>
          <select className="select-base" value={socioId} onChange={e => setSocioId(e.target.value)}>
            <option value="">Elegir socio...</option>
            {users.map(u => <option key={u.id} value={u.id}>{u.name} {u.last_name || ''} ({u.role})</option>)}
          </select>
        </Field>
        <Field label="Monto" required>
          <input type="number" min="0" step="0.01" value={monto} onChange={e => setMonto(e.target.value)} className="input-base" placeholder="0.00"/>
        </Field>
        <Field label="Fecha" required>
          <input type="date" value={fecha} onChange={e => setFecha(e.target.value)} className="input-base"/>
        </Field>
        <Field label="Medio de pago" required>
          <select className="select-base" value={medio} onChange={e => setMedio(e.target.value)}>
            {MEDIOS.map(m => <option key={m} value={m}>{SHORT(m)}</option>)}
          </select>
        </Field>
        <div className="col-span-2">
          <Field label="Motivo" required>
            <input className="input-base" value={motivo} onChange={e => setMotivo(e.target.value)} placeholder="ej: Cubre déficit semana 09"/>
          </Field>
        </div>
        <div className="col-span-2 p-3 rounded-xl bg-olive/5 border border-olive/20 text-[11px] text-navy/80 flex items-start gap-2">
          <AlertCircle size={13} className="text-olive-700 shrink-0 mt-0.5"/>
          <span>Al guardar, el sistema crea automáticamente un movimiento <strong>INGRESO</strong> espejo en la obra (regla R2).</span>
        </div>
        {error && <div className="col-span-2 p-3 rounded-xl bg-danger/10 border border-danger/30 text-[12px] text-danger">{error}</div>}
      </div>
      <ModalFooter onCancel={onClose} onSubmit={submit} disabled={!formListo} loading={submitting} label="Crear aporte"/>
    </ModalShell>
  )
}

function DevolucionModal({ aporte, obra, onClose, onSaved }) {
  const today = new Date().toISOString().slice(0, 10)
  const pendiente = aporte.monto - aporte.monto_devuelto
  const [monto, setMonto] = useState(pendiente.toFixed(2))
  const [fecha, setFecha] = useState(today)
  const [medio, setMedio] = useState('TRANSFERENCIA')
  const [notas, setNotas] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const formListo = monto && Number(monto) > 0 && Number(monto) <= pendiente && fecha && medio

  const submit = async () => {
    setError(''); setSubmitting(true)
    try {
      await api.post(`/api/aportes/${aporte.id}/devolucion`, {
        monto: Number(monto),
        fecha,
        medio_pago: medio,
        notas: notas.trim() || null,
      })
      onSaved()
    } catch (e) {
      setError(e.response?.data?.detail || 'Error al guardar')
      setSubmitting(false)
    }
  }

  return (
    <ModalShell title="Registrar devolución." onClose={onClose}>
      <div className="mb-4 p-3 rounded-xl bg-bone-100/70 border border-border/60">
        <div className="text-[11px] text-muted uppercase tracking-wide font-semibold mb-1">Aporte original</div>
        <div className="text-[13px] text-navy">{aporte.motivo}</div>
        <div className="text-[11px] text-muted mt-1">
          {obra?.codigo} · Aportado: {fmtMoney(aporte.monto)} · Devuelto: {fmtMoney(aporte.monto_devuelto)} · <span className="text-leather font-medium">Pendiente: {fmtMoney(pendiente)}</span>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Field label={`Monto a devolver (máx ${fmtMoney(pendiente)})`} required>
          <input type="number" min="0" max={pendiente} step="0.01" value={monto} onChange={e => setMonto(e.target.value)} className="input-base"/>
        </Field>
        <Field label="Fecha" required>
          <input type="date" value={fecha} onChange={e => setFecha(e.target.value)} className="input-base"/>
        </Field>
        <Field label="Medio de pago" required>
          <select className="select-base" value={medio} onChange={e => setMedio(e.target.value)}>
            {MEDIOS.map(m => <option key={m} value={m}>{SHORT(m)}</option>)}
          </select>
        </Field>
        <div/>
        <div className="col-span-2">
          <Field label="Notas">
            <input className="input-base" value={notas} onChange={e => setNotas(e.target.value)} placeholder="opcional"/>
          </Field>
        </div>
        <div className="col-span-2 p-3 rounded-xl bg-leather/5 border border-leather/20 text-[11px] text-navy/80 flex items-start gap-2">
          <AlertCircle size={13} className="text-leather shrink-0 mt-0.5"/>
          <span>El sistema crea un <strong>EGRESO</strong> espejo con categoría APORTE_PRESTAMO. Si el devuelto iguala el aporte, queda DEVUELTO_TOTAL.</span>
        </div>
        {error && <div className="col-span-2 p-3 rounded-xl bg-danger/10 border border-danger/30 text-[12px] text-danger">{error}</div>}
      </div>
      <ModalFooter onCancel={onClose} onSubmit={submit} disabled={!formListo} loading={submitting} label="Registrar devolución"/>
    </ModalShell>
  )
}

function ModalShell({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 bg-navy/30 backdrop-blur-sm z-50 grid place-items-center p-4 animate-fade-in" onClick={onClose}>
      <div className="card p-0 max-w-2xl w-full max-h-[90vh] overflow-hidden shadow-lift flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="px-7 py-5 border-b border-border/60 flex items-center justify-between">
          <div>
            <div className="hero-eyebrow !text-[10px]">Finanzas</div>
            <h2 className="hero-title text-2xl">{title}</h2>
          </div>
          <button onClick={onClose} className="p-2 rounded-full text-muted hover:bg-bone-200/70 hover:text-navy transition">
            <X size={16}/>
          </button>
        </div>
        <div className="px-7 py-5 overflow-y-auto flex-1">{children}</div>
      </div>
    </div>
  )
}

function ModalFooter({ onCancel, onSubmit, disabled, loading, label }) {
  return (
    <div className="-mx-7 px-7 pt-4 mt-4 border-t border-border/60 flex items-center justify-end gap-2 bg-bone-100/30 -mb-5 py-4">
      <button onClick={onCancel} className="btn btn-ghost">Cancelar</button>
      <button onClick={onSubmit} disabled={disabled || loading} className="btn btn-primary">
        {loading ? <Loader2 size={13} className="animate-spin"/> : <Check size={13}/>}
        {label}
      </button>
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
