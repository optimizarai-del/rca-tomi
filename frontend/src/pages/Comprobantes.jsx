import { useEffect, useMemo, useState } from 'react'
import { Plus, X, FileText, Loader2, Check, AlertCircle, ArrowDownLeft, ArrowUpRight } from 'lucide-react'
import api from '../utils/api'

const TIPOS = ['FC_A', 'FC_B', 'FC_C', 'NC_A', 'NC_B', 'ND_A', 'ND_B', 'RECIBO_X', 'REMITO']
const ESTADOS = ['VALIDO', 'SIN_CAE', 'VENCIDO', 'ANULADO']

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
  VALIDO: 'chip-olive',
  SIN_CAE: 'chip-warn',
  VENCIDO: 'chip-warn',
  ANULADO: 'chip-danger',
}

export default function Comprobantes() {
  const [comps, setComps] = useState([])
  const [obras, setObras] = useState([])
  const [loading, setLoading] = useState(true)
  const [filterObra, setFilterObra] = useState('')
  const [filterTipo, setFilterTipo] = useState('')
  const [filterEsVenta, setFilterEsVenta] = useState('')  // '' | 'true' | 'false'
  const [filterEstado, setFilterEstado] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)
  const [showNew, setShowNew] = useState(false)

  const load = async () => {
    setLoading(true)
    const params = {}
    if (filterObra) params.obra_id = filterObra
    if (filterEsVenta) params.es_venta = filterEsVenta === 'true'
    const [c, o] = await Promise.all([
      api.get('/api/comprobantes', { params }),
      api.get('/api/obras'),
    ])
    setComps(c.data); setObras(o.data)
    setLoading(false)
  }
  useEffect(() => { load() }, [filterObra, filterEsVenta, refreshKey])

  const obraById = (id) => obras.find(o => o.id === id)

  const filtered = useMemo(() => {
    return comps.filter(c => {
      if (filterTipo && c.tipo_comprobante !== filterTipo) return false
      if (filterEstado && c.estado_fiscal !== filterEstado) return false
      return true
    })
  }, [comps, filterTipo, filterEstado])

  const totales = useMemo(() => {
    let venta = 0, compra = 0, conCae = 0, sinCaeOVencido = 0
    for (const c of filtered) {
      if (c.es_venta) venta += c.total
      else compra += c.total
      if (c.cae && c.estado_fiscal === 'VALIDO') conCae++
      else if (c.estado_fiscal === 'SIN_CAE' || c.estado_fiscal === 'VENCIDO') sinCaeOVencido++
    }
    return { venta, compra, conCae, sinCaeOVencido, count: filtered.length }
  }, [filtered])

  return (
    <div className="max-w-7xl mx-auto animate-fade-in">
      <header className="mb-10 flex items-end justify-between gap-6 flex-wrap">
        <div>
          <div className="hero-eyebrow">Finanzas</div>
          <h1 className="hero-title text-5xl md:text-6xl mb-3">Comprobantes</h1>
          <p className="hero-sub">Facturas A/B/C, notas de crédito/débito, recibos y remitos. Cada uno valida que neto + IVA = total.</p>
        </div>
        <button onClick={() => setShowNew(true)} className="btn btn-lg btn-primary">
          <Plus size={14}/> Cargar comprobante
        </button>
      </header>

      {showNew && (
        <NuevoComprobanteModal
          obras={obras}
          onClose={() => setShowNew(false)}
          onSaved={() => { setShowNew(false); setRefreshKey(k => k + 1) }}
        />
      )}

      <section className="grid md:grid-cols-4 gap-4 mb-8">
        <BigNumber label="Emitido (venta)" value={fmtMoney(totales.venta)} accent="olive"/>
        <BigNumber label="Recibido (compra)" value={fmtMoney(totales.compra)} accent="leather"/>
        <BigNumber label="Con CAE válido" value={String(totales.conCae)} accent="navy"/>
        <BigNumber label="Sin CAE / vencidos" value={String(totales.sinCaeOVencido)} accent={totales.sinCaeOVencido > 0 ? 'leather' : 'navy'}/>
      </section>

      <section className="card p-5 mb-6">
        <div className="grid md:grid-cols-4 gap-3">
          <Field label="Obra">
            <select className="select-base" value={filterObra} onChange={e => setFilterObra(e.target.value)}>
              <option value="">Todas</option>
              {obras.map(o => <option key={o.id} value={o.id}>{o.codigo} — {o.nombre}</option>)}
            </select>
          </Field>
          <Field label="Tipo">
            <select className="select-base" value={filterTipo} onChange={e => setFilterTipo(e.target.value)}>
              <option value="">Todos</option>
              {TIPOS.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </Field>
          <Field label="Dirección">
            <select className="select-base" value={filterEsVenta} onChange={e => setFilterEsVenta(e.target.value)}>
              <option value="">Todos</option>
              <option value="true">Emitidos (venta)</option>
              <option value="false">Recibidos (compra)</option>
            </select>
          </Field>
          <Field label="Estado fiscal">
            <select className="select-base" value={filterEstado} onChange={e => setFilterEstado(e.target.value)}>
              <option value="">Todos</option>
              {ESTADOS.map(e => <option key={e} value={e}>{e}</option>)}
            </select>
          </Field>
        </div>
      </section>

      <section className="card overflow-hidden">
        {loading ? (
          <div className="p-10 text-center text-muted text-sm">Cargando...</div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center">
            <FileText size={32} className="mx-auto text-muted/40 mb-3"/>
            <div className="text-muted text-sm mb-3">No hay comprobantes que coincidan.</div>
            <button onClick={() => setShowNew(true)} className="btn btn-primary">
              <Plus size={13}/> Cargar primer comprobante
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-[12px]">
              <thead>
                <tr className="bg-bone-100/50 text-muted uppercase text-[10px] tracking-wide">
                  <th className="text-left px-4 py-3 font-semibold">Fecha</th>
                  <th className="text-left px-4 py-3 font-semibold">Obra</th>
                  <th className="text-left px-4 py-3 font-semibold">Tipo · Nro</th>
                  <th className="text-left px-4 py-3 font-semibold">Dirección</th>
                  <th className="text-left px-4 py-3 font-semibold">CUIT (otra parte)</th>
                  <th className="text-right px-4 py-3 font-semibold">Neto</th>
                  <th className="text-right px-4 py-3 font-semibold">IVA</th>
                  <th className="text-right px-4 py-3 font-semibold">Total</th>
                  <th className="text-left px-4 py-3 font-semibold">CAE</th>
                  <th className="text-left px-4 py-3 font-semibold">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50">
                {filtered.map(c => {
                  const obra = obraById(c.obra_id)
                  const neto = c.neto_gravado + c.neto_no_gravado
                  const iva = c.iva_21 + c.iva_105
                  const otraParte = c.es_venta ? c.cuit_receptor : c.cuit_emisor
                  return (
                    <tr key={c.id} className="hover:bg-bone-100/30 transition">
                      <td className="px-4 py-3 whitespace-nowrap text-navy/80">{fmtDate(c.fecha_emision)}</td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="text-[10px] uppercase tracking-wide font-semibold text-muted">{obra?.codigo}</span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="font-mono text-[11px] font-semibold text-navy">{c.tipo_comprobante}</div>
                        <div className="font-mono text-[10px] text-muted">{c.nro_comprobante}</div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        {c.es_venta ? (
                          <span className="chip chip-olive text-[10px] inline-flex items-center gap-1">
                            <ArrowUpRight size={10}/> Venta
                          </span>
                        ) : (
                          <span className="chip chip-leather text-[10px] inline-flex items-center gap-1">
                            <ArrowDownLeft size={10}/> Compra
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap font-mono text-[11px] text-navy/80">{otraParte}</td>
                      <td className="px-4 py-3 text-right font-mono text-navy/80 whitespace-nowrap">{fmtMoney(neto)}</td>
                      <td className="px-4 py-3 text-right font-mono text-navy/80 whitespace-nowrap">{fmtMoney(iva)}</td>
                      <td className="px-4 py-3 text-right font-mono font-semibold text-navy whitespace-nowrap">{fmtMoney(c.total)}</td>
                      <td className="px-4 py-3 whitespace-nowrap font-mono text-[10px] text-muted">{c.cae || '—'}</td>
                      <td className="px-4 py-3">
                        <span className={`chip ${ESTADO_CHIP[c.estado_fiscal] || 'chip-muted'} text-[10px]`}>
                          {c.estado_fiscal}
                        </span>
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

function NuevoComprobanteModal({ obras, onClose, onSaved }) {
  const today = new Date().toISOString().slice(0, 10)
  const [obraId, setObraId] = useState('')
  const [tipo, setTipo] = useState('FC_A')
  const [puntoVenta, setPuntoVenta] = useState('1')
  const [nro, setNro] = useState('')
  const [fechaEmi, setFechaEmi] = useState(today)
  const [cuitEmi, setCuitEmi] = useState('')
  const [cuitRec, setCuitRec] = useState('')
  const [esVenta, setEsVenta] = useState('false')  // string para radio
  const [neto, setNeto] = useState('')
  const [netoNG, setNetoNG] = useState('')
  const [iva21, setIva21] = useState('')
  const [iva105, setIva105] = useState('')
  const [total, setTotal] = useState('')
  const [cae, setCae] = useState('')
  const [caeVto, setCaeVto] = useState('')
  const [estadoFiscal, setEstadoFiscal] = useState('VALIDO')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  // Auto-calc total cuando cambian montos
  const sumaCalculada = (Number(neto) || 0) + (Number(netoNG) || 0) + (Number(iva21) || 0) + (Number(iva105) || 0)
  const totalDifiere = total !== '' && Math.abs(sumaCalculada - Number(total)) > 0.05
  const aplicarTotal = () => setTotal(sumaCalculada.toFixed(2))

  const formListo = obraId && tipo && nro.trim() && fechaEmi && cuitEmi.trim() && cuitRec.trim()
    && total && Number(total) > 0 && !totalDifiere

  const submit = async () => {
    setError(''); setSubmitting(true)
    try {
      await api.post('/api/comprobantes', {
        obra_id: Number(obraId),
        tipo_comprobante: tipo,
        punto_venta: puntoVenta ? Number(puntoVenta) : null,
        nro_comprobante: nro.trim(),
        fecha_emision: fechaEmi,
        cuit_emisor: cuitEmi.trim(),
        cuit_receptor: cuitRec.trim(),
        neto_gravado: Number(neto) || 0,
        neto_no_gravado: Number(netoNG) || 0,
        iva_21: Number(iva21) || 0,
        iva_105: Number(iva105) || 0,
        total: Number(total),
        cae: cae.trim() || null,
        cae_vencimiento: caeVto || null,
        es_venta: esVenta === 'true',
        estado_fiscal: estadoFiscal,
      })
      onSaved()
    } catch (e) {
      setError(e.response?.data?.detail || 'Error al guardar')
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-navy/30 backdrop-blur-sm z-50 grid place-items-center p-4 animate-fade-in" onClick={onClose}>
      <div className="card p-0 max-w-3xl w-full max-h-[90vh] overflow-hidden shadow-lift flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="px-7 py-5 border-b border-border/60 flex items-center justify-between">
          <div>
            <div className="hero-eyebrow !text-[10px]">Finanzas</div>
            <h2 className="hero-title text-2xl">Cargar comprobante</h2>
          </div>
          <button onClick={onClose} className="p-2 rounded-full text-muted hover:bg-bone-200/70 hover:text-navy transition">
            <X size={16}/>
          </button>
        </div>

        <div className="px-7 py-5 overflow-y-auto flex-1 space-y-5">
          {/* Identificación */}
          <SectionTitle n={1} label="Identificación"/>
          <div className="grid grid-cols-3 gap-3">
            <Field label="Obra" required>
              <select className="select-base" value={obraId} onChange={e => setObraId(e.target.value)}>
                <option value="">Elegir obra...</option>
                {obras.map(o => <option key={o.id} value={o.id}>{o.codigo} — {o.nombre}</option>)}
              </select>
            </Field>
            <Field label="Tipo" required>
              <select className="select-base" value={tipo} onChange={e => setTipo(e.target.value)}>
                {TIPOS.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </Field>
            <Field label="Dirección" required>
              <select className="select-base" value={esVenta} onChange={e => setEsVenta(e.target.value)}>
                <option value="false">Recibido (compra)</option>
                <option value="true">Emitido (venta)</option>
              </select>
            </Field>
            <Field label="Punto de venta">
              <input type="number" min="0" className="input-base" value={puntoVenta} onChange={e => setPuntoVenta(e.target.value)} placeholder="1"/>
            </Field>
            <div className="col-span-2">
              <Field label="Nro comprobante" required>
                <input className="input-base" value={nro} onChange={e => setNro(e.target.value)} placeholder="00001-00012345"/>
              </Field>
            </div>
            <Field label="Fecha emisión" required>
              <input type="date" className="input-base" value={fechaEmi} onChange={e => setFechaEmi(e.target.value)}/>
            </Field>
            <Field label="CUIT emisor" required>
              <input className="input-base" value={cuitEmi} onChange={e => setCuitEmi(e.target.value)} placeholder="30-12345678-9"/>
            </Field>
            <Field label="CUIT receptor" required>
              <input className="input-base" value={cuitRec} onChange={e => setCuitRec(e.target.value)} placeholder="30-98765432-1"/>
            </Field>
          </div>

          {/* Montos */}
          <SectionTitle n={2} label="Montos"/>
          <div className="grid grid-cols-3 gap-3">
            <Field label="Neto gravado">
              <input type="number" min="0" step="0.01" className="input-base" value={neto} onChange={e => setNeto(e.target.value)} placeholder="0.00"/>
            </Field>
            <Field label="Neto no gravado">
              <input type="number" min="0" step="0.01" className="input-base" value={netoNG} onChange={e => setNetoNG(e.target.value)} placeholder="0.00"/>
            </Field>
            <Field label="IVA 21%">
              <input type="number" min="0" step="0.01" className="input-base" value={iva21} onChange={e => setIva21(e.target.value)} placeholder="0.00"/>
            </Field>
            <Field label="IVA 10.5%">
              <input type="number" min="0" step="0.01" className="input-base" value={iva105} onChange={e => setIva105(e.target.value)} placeholder="0.00"/>
            </Field>
            <Field label="Total" required>
              <input type="number" min="0" step="0.01" className="input-base" value={total} onChange={e => setTotal(e.target.value)} placeholder="0.00"/>
            </Field>
            <div className="flex items-end">
              <button
                onClick={aplicarTotal}
                disabled={sumaCalculada === 0}
                className="btn btn-secondary text-[12px] w-full"
              >
                Calcular total = {fmtMoney(sumaCalculada)}
              </button>
            </div>
          </div>
          {totalDifiere && (
            <div className="p-3 rounded-xl bg-warn/10 border border-warn/30 text-[12px] text-leather flex items-start gap-2">
              <AlertCircle size={13} className="shrink-0 mt-0.5"/>
              <span>El total ({fmtMoney(Number(total))}) no coincide con neto + IVA = <strong>{fmtMoney(sumaCalculada)}</strong>. El backend va a rechazar el guardado.</span>
            </div>
          )}

          {/* AFIP */}
          <SectionTitle n={3} label="Datos AFIP"/>
          <div className="grid grid-cols-3 gap-3">
            <Field label="CAE">
              <input className="input-base" value={cae} onChange={e => setCae(e.target.value)} placeholder="74999999999999"/>
            </Field>
            <Field label="CAE vencimiento">
              <input type="date" className="input-base" value={caeVto} onChange={e => setCaeVto(e.target.value)}/>
            </Field>
            <Field label="Estado fiscal">
              <select className="select-base" value={estadoFiscal} onChange={e => setEstadoFiscal(e.target.value)}>
                {ESTADOS.map(e => <option key={e} value={e}>{e}</option>)}
              </select>
            </Field>
          </div>

          {error && (
            <div className="p-3 rounded-xl bg-danger/10 border border-danger/30 text-[12px] text-danger">
              {error}
            </div>
          )}
        </div>

        <div className="px-7 py-4 border-t border-border/60 flex items-center justify-end gap-2 bg-bone-100/30">
          <button onClick={onClose} className="btn btn-ghost">Cancelar</button>
          <button onClick={submit} disabled={!formListo || submitting} className="btn btn-primary">
            {submitting ? <Loader2 size={13} className="animate-spin"/> : <Check size={13}/>}
            Cargar comprobante
          </button>
        </div>
      </div>
    </div>
  )
}

function SectionTitle({ n, label }) {
  return (
    <div className="flex items-center gap-3">
      <span className="w-6 h-6 rounded-full bg-navy text-bone grid place-items-center text-[11px] font-semibold shrink-0">{n}</span>
      <h3 className="text-[13px] font-semibold tracking-tight text-navy">{label}</h3>
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
