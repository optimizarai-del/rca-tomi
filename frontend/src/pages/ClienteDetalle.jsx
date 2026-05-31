import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  ArrowLeft, Building2, Mail, Phone, Hash, MapPin, CreditCard, Edit3,
  StickyNote, Plus, Star, Trash2, Calendar, ExternalLink,
} from 'lucide-react'
import api from '../utils/api'

const fmtMoney = (n) => {
  if (n == null) return '$0'
  const sign = n < 0 ? '-' : ''
  const abs = Math.abs(n)
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(2)}M`
  if (abs >= 1e3) return `${sign}$${(abs / 1e3).toFixed(0)}k`
  return `${sign}$${Math.round(abs)}`
}

const ESTADO_OBRA = {
  EN_CURSO: { txt: 'En curso', cls: 'chip-navy' },
  PAUSADA: { txt: 'Pausada', cls: 'chip-warn' },
  FINALIZADA: { txt: 'Finalizada', cls: 'chip-olive' },
  CANCELADA: { txt: 'Cancelada', cls: 'chip-danger' },
}

export default function ClienteDetalle() {
  const { id } = useParams()
  const nav = useNavigate()
  const [data, setData] = useState(null)
  const [tab, setTab] = useState('datos')
  const [nuevoTexto, setNuevoTexto] = useState('')
  const [nuevoImportante, setNuevoImportante] = useState(false)
  const [enviando, setEnviando] = useState(false)

  const load = () => api.get(`/api/clientes/${id}/detalle`).then(r => setData(r.data))
  useEffect(() => { load() }, [id])

  if (!data) return <div className="p-10 text-center text-muted">Cargando…</div>

  const crearNota = async (e) => {
    e.preventDefault()
    if (!nuevoTexto.trim()) return
    setEnviando(true)
    try {
      await api.post(`/api/clientes/${id}/notas`, {
        cliente_id: Number(id),
        texto: nuevoTexto.trim(),
        importante: nuevoImportante,
      })
      setNuevoTexto(''); setNuevoImportante(false)
      load()
    } catch (err) {
      alert(err.response?.data?.detail || 'Error')
    } finally {
      setEnviando(false)
    }
  }
  const borrarNota = async (nid) => {
    if (!confirm('¿Eliminar nota?')) return
    await api.delete(`/api/clientes/notas/${nid}`)
    load()
  }

  const r = data.resumen_financiero

  return (
    <div className="max-w-5xl mx-auto animate-fade-in">
      <button onClick={() => nav('/clientes')} className="btn-ghost mb-4 text-sm">
        <ArrowLeft size={14}/> Volver a Clientes
      </button>

      <header className="mb-8">
        <div className="hero-eyebrow">Finanzas · cliente</div>
        <h1 className="hero-title text-4xl md:text-5xl mb-2">{data.nombre}</h1>
        {data.razon_social && data.razon_social !== data.nombre && (
          <p className="text-muted text-sm">{data.razon_social}</p>
        )}
        {data.last_interaction_at && (
          <p className="text-[11px] text-muted mt-2 flex items-center gap-1.5">
            <Calendar size={11}/> Última interacción: {new Date(data.last_interaction_at).toLocaleString('es-AR')}
          </p>
        )}
      </header>

      {/* Resumen financiero */}
      <section className="grid md:grid-cols-4 gap-3 mb-6">
        <BigStat label="Contratos totales" value={fmtMoney(r.monto_contratos_total)}/>
        <BigStat label="Cobrado" value={fmtMoney(r.ingresos_cobrado_total)} accent="text-olive"/>
        <BigStat label="Por cobrar" value={fmtMoney(r.ingresos_pendiente_total)} accent="text-leather"/>
        <BigStat label="Obras" value={`${r.obras_en_curso}/${r.obras_total}`} sub={`${r.obras_finalizadas} finalizadas`}/>
      </section>

      {/* Tabs */}
      <div className="flex gap-1 mb-5 border-b border-border">
        {[
          { v: 'datos', l: 'Datos' },
          { v: 'obras', l: `Obras (${data.obras.length})` },
          { v: 'notas', l: `Notas (${data.interacciones.length})` },
        ].map(t => (
          <button
            key={t.v}
            onClick={() => setTab(t.v)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition ${
              tab === t.v ? 'border-navy text-navy' : 'border-transparent text-muted hover:text-navy'
            }`}
          >
            {t.l}
          </button>
        ))}
      </div>

      {tab === 'datos' && (
        <div className="space-y-5">
          <section className="card p-6">
            <div className="text-[10px] uppercase tracking-[0.18em] text-muted font-semibold mb-3">Contacto</div>
            <div className="space-y-2 text-sm">
              {data.cuit && <Row icon={Hash} label="CUIT" value={data.cuit}/>}
              {data.email && <Row icon={Mail} label="Email" value={data.email}/>}
              {data.telefono && <Row icon={Phone} label="Teléfono" value={data.telefono}/>}
              {data.direccion && <Row icon={MapPin} label="Dirección" value={data.direccion}/>}
              {data.contacto_secundario && <Row icon={Phone} label="Contacto 2°" value={data.contacto_secundario}/>}
            </div>
          </section>

          {(data.cbu || data.alias_bancario || data.condiciones_pago) && (
            <section className="card p-6">
              <div className="text-[10px] uppercase tracking-[0.18em] text-muted font-semibold mb-3">Datos recurrentes</div>
              <div className="space-y-2 text-sm">
                {data.cbu && <Row icon={CreditCard} label="CBU" value={data.cbu}/>}
                {data.alias_bancario && <Row icon={CreditCard} label="Alias" value={data.alias_bancario}/>}
                {data.condiciones_pago && <Row icon={Calendar} label="Condiciones de pago" value={data.condiciones_pago}/>}
              </div>
            </section>
          )}

          {data.preferencias && (
            <section className="card p-6">
              <div className="text-[10px] uppercase tracking-[0.18em] text-muted font-semibold mb-3">Preferencias / observaciones</div>
              <p className="text-sm whitespace-pre-wrap">{data.preferencias}</p>
            </section>
          )}

          {data.notas && (
            <section className="card p-6">
              <div className="text-[10px] uppercase tracking-[0.18em] text-muted font-semibold mb-3">Notas internas</div>
              <p className="text-sm whitespace-pre-wrap">{data.notas}</p>
            </section>
          )}
        </div>
      )}

      {tab === 'obras' && (
        <section className="card overflow-hidden">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="bg-bone-100/50 text-muted uppercase text-[10px] tracking-wide">
                <th className="text-left px-3 py-3 font-semibold">Código</th>
                <th className="text-left px-3 py-3 font-semibold">Nombre</th>
                <th className="text-left px-3 py-3 font-semibold">Estado</th>
                <th className="text-right px-3 py-3 font-semibold">Contrato</th>
                <th className="text-right px-3 py-3 font-semibold">Cobrado</th>
                <th className="text-right px-3 py-3 font-semibold">Por cobrar</th>
                <th className="text-right px-3 py-3 font-semibold">Saldo</th>
                <th className="text-right px-3 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/50">
              {data.obras.map(o => {
                const est = ESTADO_OBRA[o.estado] || { txt: o.estado, cls: 'chip-muted' }
                return (
                  <tr key={o.id} className="hover:bg-bone-100/30 transition">
                    <td className="px-3 py-2.5 font-mono">{o.codigo}</td>
                    <td className="px-3 py-2.5">{o.nombre}</td>
                    <td className="px-3 py-2.5"><span className={`${est.cls} text-[10px]`}>{est.txt}</span></td>
                    <td className="px-3 py-2.5 text-right font-mono">{fmtMoney(o.monto_contrato)}</td>
                    <td className="px-3 py-2.5 text-right font-mono text-olive">{fmtMoney(o.ingresos_cobrado)}</td>
                    <td className="px-3 py-2.5 text-right font-mono text-leather">{fmtMoney(o.ingresos_pendiente)}</td>
                    <td className={`px-3 py-2.5 text-right font-mono font-semibold ${o.saldo_obra >= 0 ? 'text-navy' : 'text-leather'}`}>
                      {fmtMoney(o.saldo_obra)}
                    </td>
                    <td className="px-3 py-2.5 text-right">
                      <Link to={`/obra/${o.id}`} className="text-muted hover:text-navy" title="Ver obra">
                        <ExternalLink size={12}/>
                      </Link>
                    </td>
                  </tr>
                )
              })}
              {data.obras.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-muted">Sin obras todavía.</td>
                </tr>
              )}
            </tbody>
          </table>
        </section>
      )}

      {tab === 'notas' && (
        <div className="space-y-5">
          <form onSubmit={crearNota} className="card p-5">
            <div className="text-xs text-muted mb-2">
              Anotá una interacción, llamada, reunión, etc. Queda con fecha y autor.
            </div>
            <div className="flex flex-col gap-2">
              <textarea
                value={nuevoTexto}
                onChange={e => setNuevoTexto(e.target.value)}
                placeholder="Ej: Llamada con Juan, acordamos certificado 4 para el 5 de junio."
                className="input-base min-h-[70px]"
              />
              <div className="flex items-center justify-between">
                <label className="flex items-center gap-2 text-xs text-muted cursor-pointer">
                  <input
                    type="checkbox"
                    checked={nuevoImportante}
                    onChange={e => setNuevoImportante(e.target.checked)}
                    className="rounded"
                  />
                  <Star size={12}/> Importante
                </label>
                <button className="btn-primary" disabled={enviando || !nuevoTexto.trim()}>
                  <Plus size={13}/> {enviando ? 'Guardando…' : 'Anotar'}
                </button>
              </div>
            </div>
          </form>

          {data.interacciones.length === 0 && (
            <div className="text-muted text-sm py-8 text-center border border-dashed border-border rounded-xl">
              Sin notas todavía. Anotá la primera arriba.
            </div>
          )}

          <div className="space-y-2">
            {data.interacciones.map(n => (
              <div key={n.id} className={`card p-4 flex items-start gap-3 ${n.importante ? 'border-2 border-leather/40 bg-leather/5' : ''}`}>
                <StickyNote size={13} className={n.importante ? 'text-leather mt-0.5' : 'text-navy/50 mt-0.5'}/>
                <div className="flex-1 min-w-0">
                  {n.importante && <span className="chip-warn text-[10px] mb-1.5 inline-block">importante</span>}
                  <div className="text-sm whitespace-pre-wrap">{n.texto}</div>
                  <div className="text-[10px] text-muted mt-1.5">
                    {new Date(n.created_at).toLocaleString('es-AR')}
                  </div>
                </div>
                <button onClick={() => borrarNota(n.id)} className="text-muted/50 hover:text-danger p-1.5">
                  <Trash2 size={11}/>
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function Row({ icon: I, label, value }) {
  return (
    <div className="flex items-center gap-3">
      <I size={12} className="text-muted shrink-0"/>
      <span className="text-[10px] uppercase tracking-wider text-muted w-32 shrink-0">{label}</span>
      <span className="text-navy">{value}</span>
    </div>
  )
}

function BigStat({ label, value, sub, accent }) {
  return (
    <div className="card p-4">
      <div className="text-[10px] tracking-[0.18em] uppercase text-muted font-semibold mb-1">{label}</div>
      <div className={`hero-title text-2xl ${accent || ''}`}>{value}</div>
      {sub && <div className="text-[10px] text-muted mt-1">{sub}</div>}
    </div>
  )
}
