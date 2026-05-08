import { useEffect, useMemo, useState } from 'react'
import {
  ArrowDownCircle, ArrowUpCircle, FileCheck, Clock, AlertCircle,
  Filter, X, Plus, ArrowDownLeft, ArrowUpRight, Loader2, Check,
} from 'lucide-react'
import api from '../utils/api'

const CATEGORIAS = [
  'MANO_DE_OBRA', 'MATERIALES', 'SUBCONTRATO', 'SERVICIO_EXTERNO',
  'GASTO_DIRECTO_OBRA', 'HERRAMIENTA_EQUIPO', 'APORTE_PRESTAMO',
]
const ORIGENES = [
  'ANTICIPO_CLIENTE', 'CERTIFICADO_ETAPA', 'PAGO_FINAL',
  'AJUSTE_CONTRATO', 'APORTE_SOCIO_RCA', 'DEVOLUCION_PROVEEDOR',
]
const MEDIOS = ['EFECTIVO', 'TRANSFERENCIA', 'CHEQUE_PROPIO', 'CHEQUE_TERCERO', 'DEPOSITO_BANCARIO']
const ESTADOS = ['CONFIRMADO', 'A_REVISAR']

const SHORT = (s) => s ? s.replace(/_/g, ' ').toLowerCase().replace(/^./, c => c.toUpperCase()) : '—'

function fmtMoney(n) {
  if (n == null || n === 0) return '$0'
  const sign = n < 0 ? '-' : ''
  const abs = Math.abs(n)
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(2)}M`
  if (abs >= 1e3) return `${sign}$${(abs / 1e3).toFixed(0)}k`
  return `${sign}$${Math.round(abs)}`
}

function fmtDate(s) {
  if (!s) return '—'
  const d = new Date(s)
  return d.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: '2-digit' })
}

export default function Movimientos() {
  const [obras, setObras] = useState([])
  const [movs, setMovs] = useState([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  // Filtros
  const [obraId, setObraId] = useState('')
  const [tipo, setTipo] = useState('')
  const [categoria, setCategoria] = useState('')
  const [origen, setOrigen] = useState('')
  const [medio, setMedio] = useState('')
  const [estado, setEstado] = useState('')
  const [comprobante, setComprobante] = useState('')  // 'si' | 'no' | ''
  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')

  useEffect(() => {
    api.get('/api/obras').then(r => setObras(r.data))
  }, [])

  useEffect(() => {
    setLoading(true)
    const params = { limit: 500 }
    if (obraId) params.obra_id = obraId
    if (tipo) params.tipo = tipo
    if (estado) params.estado = estado
    if (desde) params.desde = desde
    if (hasta) params.hasta = hasta
    api.get('/api/movimientos', { params }).then(r => {
      setMovs(r.data)
      setLoading(false)
    })
  }, [obraId, tipo, estado, desde, hasta, refreshKey])

  // Filtros que NO van al backend (categoría, origen, medio, comprobante)
  const filtered = useMemo(() => {
    return movs.filter(m => {
      if (categoria && m.categoria_egreso !== categoria) return false
      if (origen && m.origen_ingreso !== origen) return false
      if (medio && m.medio_pago !== medio) return false
      if (comprobante === 'si' && !m.tiene_comprobante) return false
      if (comprobante === 'no' && m.tiene_comprobante) return false
      return true
    })
  }, [movs, categoria, origen, medio, comprobante])

  const totales = useMemo(() => {
    let ingresos = 0, egresos = 0
    for (const m of filtered) {
      if (m.tipo === 'INGRESO') ingresos += m.monto
      else egresos += m.monto
    }
    return { ingresos, egresos, saldo: ingresos - egresos, count: filtered.length }
  }, [filtered])

  const obraById = (id) => obras.find(o => o.id === id)

  const limpiarFiltros = () => {
    setObraId(''); setTipo(''); setCategoria(''); setOrigen(''); setMedio('')
    setEstado(''); setComprobante(''); setDesde(''); setHasta('')
  }

  const filtrosActivos = [obraId, tipo, categoria, origen, medio, estado, comprobante, desde, hasta].filter(Boolean).length

  return (
    <div className="max-w-7xl mx-auto animate-fade-in">
      <header className="mb-10 flex items-end justify-between gap-6 flex-wrap">
        <div>
          <div className="hero-eyebrow">Finanzas</div>
          <h1 className="hero-title text-5xl md:text-6xl mb-3">Movimientos.</h1>
          <p className="hero-sub">Tabla central de ingresos y egresos, filtrable por obra, tipo, categoría y fechas.</p>
        </div>
        <button onClick={() => setModalOpen(true)} className="btn btn-lg btn-primary">
          <Plus size={14}/> Nuevo movimiento
        </button>
      </header>

      {modalOpen && (
        <NuevoMovimientoModal
          obras={obras}
          onClose={() => setModalOpen(false)}
          onSaved={() => { setModalOpen(false); setRefreshKey(k => k + 1) }}
        />
      )}

      {/* Big numbers */}
      <section className="grid md:grid-cols-4 gap-4 mb-8">
        <BigNumber label="Ingresos" value={fmtMoney(totales.ingresos)} accent="olive" icon={ArrowDownCircle}/>
        <BigNumber label="Egresos" value={fmtMoney(totales.egresos)} accent="leather" icon={ArrowUpCircle}/>
        <BigNumber
          label="Saldo"
          value={fmtMoney(totales.saldo)}
          accent={totales.saldo >= 0 ? 'olive' : 'leather'}
        />
        <BigNumber label="Movimientos" value={String(totales.count)} accent="navy"/>
      </section>

      {/* Filtros */}
      <section className="card p-5 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-[13px] font-semibold tracking-tight text-navy flex items-center gap-2">
            <Filter size={14}/> Filtros
            {filtrosActivos > 0 && (
              <span className="chip-navy text-[10px] ml-1">{filtrosActivos} activo{filtrosActivos > 1 ? 's' : ''}</span>
            )}
          </h2>
          {filtrosActivos > 0 && (
            <button onClick={limpiarFiltros} className="text-[11px] text-muted hover:text-navy flex items-center gap-1 transition">
              <X size={11}/> Limpiar
            </button>
          )}
        </div>
        <div className="grid md:grid-cols-3 lg:grid-cols-4 gap-3">
          <Select label="Obra" value={obraId} onChange={setObraId}>
            <option value="">Todas</option>
            {obras.map(o => <option key={o.id} value={o.id}>{o.codigo} — {o.nombre}</option>)}
          </Select>
          <Select label="Tipo" value={tipo} onChange={setTipo}>
            <option value="">Todos</option>
            <option value="INGRESO">Ingreso</option>
            <option value="EGRESO">Egreso</option>
          </Select>
          {tipo === 'EGRESO' && (
            <Select label="Categoría" value={categoria} onChange={setCategoria}>
              <option value="">Todas</option>
              {CATEGORIAS.map(c => <option key={c} value={c}>{SHORT(c)}</option>)}
            </Select>
          )}
          {tipo === 'INGRESO' && (
            <Select label="Origen" value={origen} onChange={setOrigen}>
              <option value="">Todos</option>
              {ORIGENES.map(o => <option key={o} value={o}>{SHORT(o)}</option>)}
            </Select>
          )}
          <Select label="Medio de pago" value={medio} onChange={setMedio}>
            <option value="">Todos</option>
            {MEDIOS.map(m => <option key={m} value={m}>{SHORT(m)}</option>)}
          </Select>
          <Select label="Estado" value={estado} onChange={setEstado}>
            <option value="">Todos</option>
            {ESTADOS.map(e => <option key={e} value={e}>{SHORT(e)}</option>)}
          </Select>
          <Select label="Comprobante" value={comprobante} onChange={setComprobante}>
            <option value="">Todos</option>
            <option value="si">Con comprobante</option>
            <option value="no">Sin comprobante</option>
          </Select>
          <DateInput label="Desde" value={desde} onChange={setDesde}/>
          <DateInput label="Hasta" value={hasta} onChange={setHasta}/>
        </div>
      </section>

      {/* Tabla */}
      <section className="card overflow-hidden">
        {loading ? (
          <div className="p-10 text-center text-muted text-sm">Cargando...</div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center">
            <div className="text-muted text-sm mb-2">No hay movimientos con esos filtros.</div>
            {filtrosActivos > 0 && (
              <button onClick={limpiarFiltros} className="btn btn-ghost text-[12px]">Limpiar filtros</button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-[12px]">
              <thead>
                <tr className="bg-bone-100/50 text-muted uppercase text-[10px] tracking-wide">
                  <th className="text-left px-4 py-3 font-semibold">Fecha</th>
                  <th className="text-left px-4 py-3 font-semibold">Obra</th>
                  <th className="text-left px-4 py-3 font-semibold">Tipo</th>
                  <th className="text-left px-4 py-3 font-semibold">Concepto</th>
                  <th className="text-right px-4 py-3 font-semibold">Monto</th>
                  <th className="text-left px-4 py-3 font-semibold">Medio</th>
                  <th className="text-left px-4 py-3 font-semibold">Categoría/Origen</th>
                  <th className="text-center px-4 py-3 font-semibold">FC</th>
                  <th className="text-left px-4 py-3 font-semibold">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50">
                {filtered.map(m => {
                  const obra = obraById(m.obra_id)
                  const isIngreso = m.tipo === 'INGRESO'
                  return (
                    <tr key={m.id} className="hover:bg-bone-100/30 transition">
                      <td className="px-4 py-3 whitespace-nowrap text-navy/80">{fmtDate(m.fecha)}</td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="text-[10px] uppercase tracking-wide font-semibold text-muted">{obra?.codigo}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`chip ${isIngreso ? 'chip-olive' : 'chip-leather'} text-[10px]`}>
                          {isIngreso ? '+' : '−'} {m.tipo}
                        </span>
                      </td>
                      <td className="px-4 py-3 max-w-xs truncate text-navy" title={m.concepto}>{m.concepto}</td>
                      <td className={`px-4 py-3 text-right font-mono font-semibold whitespace-nowrap ${isIngreso ? 'text-olive-700' : 'text-leather'}`}>
                        {isIngreso ? '+' : '−'}{fmtMoney(m.monto)}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-muted text-[11px]">{SHORT(m.medio_pago)}</td>
                      <td className="px-4 py-3 whitespace-nowrap text-muted text-[11px]">{SHORT(m.categoria_egreso || m.origen_ingreso)}</td>
                      <td className="px-4 py-3 text-center">
                        {m.tiene_comprobante ? (
                          <FileCheck size={13} className="inline text-olive-700" title="Con comprobante"/>
                        ) : (
                          <span className="text-muted/40 text-[10px]">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {m.estado === 'A_REVISAR' ? (
                          <span className="chip chip-warn text-[10px] inline-flex items-center gap-1">
                            <AlertCircle size={10}/> A revisar
                          </span>
                        ) : (
                          <span className="chip chip-muted text-[10px] inline-flex items-center gap-1">
                            <Clock size={10}/> Confirmado
                          </span>
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

function BigNumber({ label, value, accent = 'navy', icon: Icon }) {
  const accentCls = {
    navy: 'text-navy',
    olive: 'text-olive-700',
    leather: 'text-leather',
  }[accent]
  return (
    <div className="card p-5">
      <div className="text-[10px] uppercase tracking-[0.18em] text-muted font-semibold mb-2 flex items-center gap-1.5">
        {Icon && <Icon size={11}/>} {label}
      </div>
      <div className={`text-3xl font-bold tracking-tight ${accentCls}`}>{value}</div>
    </div>
  )
}

function Select({ label, value, onChange, children }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-[10px] uppercase tracking-wide text-muted font-semibold">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-xl bg-bone-100/70 px-3 py-2 text-[12px] text-navy
                   focus:outline-none focus:ring-4 focus:ring-navy/5 transition"
      >
        {children}
      </select>
    </label>
  )
}

function DateInput({ label, value, onChange }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-[10px] uppercase tracking-wide text-muted font-semibold">{label}</span>
      <input
        type="date"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-xl bg-bone-100/70 px-3 py-2 text-[12px] text-navy
                   focus:outline-none focus:ring-4 focus:ring-navy/5 transition"
      />
    </label>
  )
}

// ─────────────────────────────────────────────────────────────────
// Modal: Nuevo movimiento (UX progresiva — los campos aparecen según se eligen)
// ─────────────────────────────────────────────────────────────────

function NuevoMovimientoModal({ obras, onClose, onSaved }) {
  const today = new Date().toISOString().slice(0, 10)
  const [tipo, setTipo] = useState('')
  const [obraId, setObraId] = useState('')
  const [etapaId, setEtapaId] = useState('')
  const [categoria, setCategoria] = useState('')
  const [origen, setOrigen] = useState('')
  const [concepto, setConcepto] = useState('')
  const [monto, setMonto] = useState('')
  const [fecha, setFecha] = useState(today)
  const [medio, setMedio] = useState('')
  const [nroCheque, setNroCheque] = useState('')
  const [banco, setBanco] = useState('')
  const [fechaVto, setFechaVto] = useState('')
  const [comprobantes, setComprobantes] = useState([])
  const [comprobanteId, setComprobanteId] = useState('')
  const [estadoMov, setEstadoMov] = useState('CONFIRMADO')
  const [hojaFisica, setHojaFisica] = useState('')

  const [etapas, setEtapas] = useState([])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  // Cargar etapas y comprobantes al elegir obra
  useEffect(() => {
    if (!obraId) { setEtapas([]); setComprobantes([]); return }
    Promise.all([
      api.get('/api/etapas', { params: { obra_id: obraId } }).catch(() => ({ data: [] })),
      api.get('/api/comprobantes', { params: { obra_id: obraId } }).catch(() => ({ data: [] })),
    ]).then(([e, c]) => { setEtapas(e.data); setComprobantes(c.data) })
  }, [obraId])

  // Reset campos condicionales cuando cambia tipo
  useEffect(() => { setCategoria(''); setOrigen('') }, [tipo])
  useEffect(() => {
    if (medio !== 'CHEQUE_PROPIO' && medio !== 'CHEQUE_TERCERO') {
      setNroCheque(''); setBanco(''); setFechaVto('')
    }
  }, [medio])

  const isCheque = medio === 'CHEQUE_PROPIO' || medio === 'CHEQUE_TERCERO'
  const isIngreso = tipo === 'INGRESO'
  const isEgreso = tipo === 'EGRESO'

  // Validación local
  const camposBasicosListos = tipo && obraId && monto && Number(monto) > 0 && concepto.trim() && fecha && medio
  const categoriaOOrigenListo = (isIngreso && origen) || (isEgreso && categoria)
  const chequeListo = !isCheque || (nroCheque && fechaVto)
  const formListo = camposBasicosListos && categoriaOOrigenListo && chequeListo

  const obraSeleccionada = obras.find(o => o.id === Number(obraId))
  const exigeComprobante = obraSeleccionada?.tipo_facturacion === 'TOTAL_BLANCO'
    && isIngreso
    && ['ANTICIPO_CLIENTE', 'CERTIFICADO_ETAPA', 'PAGO_FINAL'].includes(origen)

  const submit = async () => {
    setError('')
    setSubmitting(true)
    try {
      const payload = {
        obra_id: Number(obraId),
        etapa_id: etapaId ? Number(etapaId) : null,
        fecha,
        tipo,
        origen_ingreso: isIngreso ? origen : null,
        categoria_egreso: isEgreso ? categoria : null,
        concepto: concepto.trim(),
        monto: Number(monto),
        medio_pago: medio,
        nro_cheque: isCheque ? nroCheque : null,
        banco: isCheque ? (banco || null) : null,
        fecha_vto_cheque: isCheque ? fechaVto : null,
        comprobante_id: comprobanteId ? Number(comprobanteId) : null,
        estado: estadoMov,
        hoja_fisica: hojaFisica || null,
      }
      await api.post('/api/movimientos', payload)
      onSaved()
    } catch (e) {
      setError(e.response?.data?.detail || 'Error al guardar el movimiento')
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-navy/30 backdrop-blur-sm z-50 grid place-items-center p-4 animate-fade-in"
         onClick={onClose}>
      <div className="card p-0 max-w-2xl w-full max-h-[90vh] overflow-hidden shadow-lift flex flex-col"
           onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="px-7 py-5 border-b border-border/60 flex items-center justify-between">
          <div>
            <div className="hero-eyebrow !text-[10px]">Finanzas</div>
            <h2 className="hero-title text-2xl">Nuevo movimiento.</h2>
          </div>
          <button onClick={onClose} className="p-2 rounded-full text-muted hover:bg-bone-200/70 hover:text-navy transition">
            <X size={16}/>
          </button>
        </div>

        {/* Form scrollable */}
        <div className="px-7 py-5 overflow-y-auto flex-1 space-y-6">
          {/* Step 1: tipo */}
          <Step n={1} label="¿Qué tipo de movimiento es?">
            <div className="grid grid-cols-2 gap-3">
              <TipoButton selected={isIngreso} onClick={() => setTipo('INGRESO')} icon={ArrowDownLeft}
                color="olive" title="Ingreso" sub="Cobro de cliente, aporte de socio..."/>
              <TipoButton selected={isEgreso} onClick={() => setTipo('EGRESO')} icon={ArrowUpRight}
                color="leather" title="Egreso" sub="Pago a proveedor, mano de obra..."/>
            </div>
          </Step>

          {/* Step 2: obra + etapa */}
          {tipo && (
            <Step n={2} label="¿En qué obra?">
              <div className="grid grid-cols-2 gap-3">
                <Field label="Obra" required>
                  <select value={obraId} onChange={e => setObraId(e.target.value)} className="select-base">
                    <option value="">Elegir obra...</option>
                    {obras.map(o => <option key={o.id} value={o.id}>{o.codigo} — {o.nombre}</option>)}
                  </select>
                </Field>
                {etapas.length > 0 && (
                  <Field label="Etapa (opcional)">
                    <select value={etapaId} onChange={e => setEtapaId(e.target.value)} className="select-base">
                      <option value="">Sin etapa específica</option>
                      {etapas.map(e => (
                        <option key={e.id} value={e.id}>
                          {e.nro_etapa}. {e.nombre} ({e.estado})
                        </option>
                      ))}
                    </select>
                  </Field>
                )}
              </div>
            </Step>
          )}

          {/* Step 3: categoría/origen */}
          {tipo && obraId && (
            <Step n={3} label={isIngreso ? '¿Origen del ingreso?' : '¿Categoría del egreso?'}>
              <Field label={isIngreso ? 'Origen' : 'Categoría'} required>
                <select
                  value={isIngreso ? origen : categoria}
                  onChange={e => isIngreso ? setOrigen(e.target.value) : setCategoria(e.target.value)}
                  className="select-base"
                >
                  <option value="">Elegir...</option>
                  {(isIngreso ? ORIGENES : CATEGORIAS).map(v => (
                    <option key={v} value={v}>{SHORT(v)}</option>
                  ))}
                </select>
              </Field>
            </Step>
          )}

          {/* Step 4: monto + concepto + fecha */}
          {tipo && obraId && (categoria || origen) && (
            <Step n={4} label="Detalles del movimiento">
              <div className="grid grid-cols-2 gap-3">
                <Field label="Monto" required>
                  <input
                    type="number" min="0" step="0.01"
                    value={monto}
                    onChange={e => setMonto(e.target.value)}
                    placeholder="0.00"
                    className="input-base"
                  />
                </Field>
                <Field label="Fecha" required>
                  <input type="date" value={fecha} onChange={e => setFecha(e.target.value)} className="input-base"/>
                </Field>
                <div className="col-span-2">
                  <Field label="Concepto" required>
                    <input
                      type="text"
                      value={concepto}
                      onChange={e => setConcepto(e.target.value)}
                      placeholder="ej: Pago albañiles semana 12"
                      className="input-base"
                    />
                  </Field>
                </div>
              </div>
            </Step>
          )}

          {/* Step 5: medio de pago */}
          {tipo && obraId && (categoria || origen) && monto && concepto && (
            <Step n={5} label="Medio de pago">
              <Field label="Medio" required>
                <select value={medio} onChange={e => setMedio(e.target.value)} className="select-base">
                  <option value="">Elegir...</option>
                  {MEDIOS.map(m => <option key={m} value={m}>{SHORT(m)}</option>)}
                </select>
              </Field>
              {isCheque && (
                <div className="grid grid-cols-3 gap-3 mt-3 p-3 rounded-xl bg-leather/5 border border-leather/20">
                  <Field label="Nro cheque" required>
                    <input value={nroCheque} onChange={e => setNroCheque(e.target.value)} placeholder="00045123" className="input-base"/>
                  </Field>
                  <Field label="Banco">
                    <input value={banco} onChange={e => setBanco(e.target.value)} placeholder="Banco Galicia" className="input-base"/>
                  </Field>
                  <Field label="Fecha vto" required>
                    <input type="date" value={fechaVto} onChange={e => setFechaVto(e.target.value)} className="input-base"/>
                  </Field>
                </div>
              )}
            </Step>
          )}

          {/* Step 6: comprobante + estado + hoja física */}
          {tipo && obraId && (categoria || origen) && monto && concepto && medio && (
            <Step n={6} label="Comprobante y trazabilidad (opcional)">
              {exigeComprobante && (
                <div className="mb-3 p-3 rounded-xl bg-warn/10 border border-warn/30 text-[12px] text-leather flex items-start gap-2">
                  <AlertCircle size={14} className="shrink-0 mt-0.5"/>
                  <span>Esta obra es <strong>TOTAL_BLANCO</strong> y este tipo de ingreso requiere comprobante.</span>
                </div>
              )}
              <div className="grid grid-cols-2 gap-3">
                <Field label={`Comprobante AFIP${exigeComprobante ? ' (requerido)' : ' (opcional)'}`}>
                  <select value={comprobanteId} onChange={e => setComprobanteId(e.target.value)} className="select-base">
                    <option value="">Sin comprobante</option>
                    {comprobantes.map(c => (
                      <option key={c.id} value={c.id}>
                        {c.tipo_comprobante} {c.nro_comprobante} — ${Number(c.total).toLocaleString('es-AR')}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Estado">
                  <select value={estadoMov} onChange={e => setEstadoMov(e.target.value)} className="select-base">
                    <option value="CONFIRMADO">Confirmado</option>
                    <option value="A_REVISAR">A revisar</option>
                  </select>
                </Field>
                <div className="col-span-2">
                  <Field label="Hoja física (opcional)">
                    <input value={hojaFisica} onChange={e => setHojaFisica(e.target.value)} placeholder="Hoja 15 - 16/03/26" className="input-base"/>
                  </Field>
                </div>
              </div>
            </Step>
          )}

          {error && (
            <div className="p-3 rounded-xl bg-danger/10 border border-danger/30 text-[12px] text-danger">
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-7 py-4 border-t border-border/60 flex items-center justify-between bg-bone-100/30">
          <div className="text-[11px] text-muted">
            {formListo ? 'Listo para guardar.' : 'Completá los campos obligatorios.'}
          </div>
          <div className="flex gap-2">
            <button onClick={onClose} className="btn btn-ghost">Cancelar</button>
            <button
              onClick={submit}
              disabled={!formListo || submitting}
              className="btn btn-primary"
            >
              {submitting ? <Loader2 size={14} className="animate-spin"/> : <Check size={14}/>}
              Guardar movimiento
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function Step({ n, label, children }) {
  return (
    <section className="animate-fade-in">
      <div className="flex items-center gap-3 mb-3">
        <span className="w-6 h-6 rounded-full bg-navy text-bone grid place-items-center text-[11px] font-semibold shrink-0">
          {n}
        </span>
        <h3 className="text-[13px] font-semibold tracking-tight text-navy">{label}</h3>
      </div>
      <div className="ml-9">{children}</div>
    </section>
  )
}

function TipoButton({ selected, onClick, icon: Icon, color, title, sub }) {
  const colorBorder = selected
    ? color === 'olive' ? 'border-olive bg-olive/5' : 'border-leather bg-leather/5'
    : 'border-border bg-white hover:border-navy/30'
  const colorIcon = color === 'olive' ? 'text-olive-700' : 'text-leather'
  return (
    <button
      onClick={onClick}
      className={`text-left p-4 rounded-2xl border-2 transition ${colorBorder}`}
    >
      <Icon size={18} className={`${colorIcon} mb-2`}/>
      <div className="text-[14px] font-semibold tracking-tight text-navy">{title}</div>
      <div className="text-[11px] text-muted mt-0.5">{sub}</div>
    </button>
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
