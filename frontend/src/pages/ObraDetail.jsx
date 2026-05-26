import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  ArrowLeft, MapPin, Users, Package, Activity, AlertCircle,
  Calendar, DollarSign, Plus, Check, Clock, ArrowRight, X, Loader2, Layers,
  MessageCircle, RotateCcw, Trash2,
} from 'lucide-react'
import api from '../utils/api'

const ETAPA_ESTADO_CHIP = {
  PENDIENTE: 'chip-muted',
  EN_EJECUCION: 'chip-navy',
  EJECUTADA: 'chip-olive',
  FACTURADA: 'chip-olive',
  COBRADA: 'chip-olive',
}
const ETAPA_ESTADOS = ['PENDIENTE', 'EN_EJECUCION', 'EJECUTADA', 'FACTURADA', 'COBRADA']

const ESTADO_FRENTE = {
  pendiente: { txt: 'Pendiente', cls: 'chip-muted' },
  en_progreso: { txt: 'En progreso', cls: 'chip-navy' },
  bloqueado: { txt: 'Bloqueado', cls: 'chip-danger' },
  completado: { txt: 'Completado', cls: 'chip-olive' },
}

const TIPO_EVENTO_ICON = {
  avance: '◆', material_llegada: '◇', incidente: '!', inspeccion: '◉', foto: '◫', hito: '★', otro: '○',
}

const PRIORIDAD = {
  baja: 'chip-muted', normal: 'chip-navy', alta: 'chip-warn', critica: 'chip-danger',
}

const HEALTH_LABEL = {
  optimo: { txt: 'Óptimo', dot: 'bg-olive' },
  atencion: { txt: 'Atención', dot: 'bg-warn' },
  critico: { txt: 'Crítico', dot: 'bg-danger' },
}

export default function ObraDetail() {
  const { id } = useParams()
  const nav = useNavigate()
  const [data, setData] = useState(null)
  const [frentes, setFrentes] = useState([])
  const [eventos, setEventos] = useState([])
  const [ordenes, setOrdenes] = useState([])
  const [etapas, setEtapas] = useState([])
  const [tab, setTab] = useState('overview')

  const load = async () => {
    const [d, f, e, o, et] = await Promise.all([
      api.get(`/api/obras/${id}/dashboard`),
      api.get(`/api/frentes`, { params: { obra_id: id } }),
      api.get(`/api/eventos`, { params: { obra_id: id } }),
      api.get(`/api/ordenes`, { params: { obra_id: id } }),
      api.get(`/api/etapas`, { params: { obra_id: id } }),
    ])
    setData(d.data); setFrentes(f.data); setEventos(e.data); setOrdenes(o.data); setEtapas(et.data)
  }
  useEffect(() => { load() }, [id])

  if (!data) return <div className="px-8 py-12 text-muted">Cargando...</div>
  const { obra } = data
  const health = HEALTH_LABEL[obra.salud]
  const presupuesto_pct = Number(data.monto_contrato) > 0
    ? (Number(data.total_egresos) / Number(data.monto_contrato)) * 100
    : 0

  return (
    <div className="animate-fade-in">
      {/* Hero — apple product page style */}
      <section className="relative overflow-hidden border-b border-border"
        style={{ background: `linear-gradient(180deg, ${obra.color}10 0%, transparent 100%)` }}>
        <div className="px-8 pt-8 pb-12 max-w-[1400px] mx-auto">
          <button onClick={() => nav('/world')} className="btn-ghost mb-8">
            <ArrowLeft size={14}/> Obras
          </button>

          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <span className="text-[11px] uppercase tracking-[0.2em] font-semibold text-olive-700">{obra.codigo}</span>
                <span className="w-1 h-1 rounded-full bg-muted/50"/>
                <span className="text-xs uppercase tracking-wider text-muted capitalize">
                  {(obra.estado || '').replace('_',' ').toLowerCase()}
                </span>
              </div>
              <h1 className="hero-title text-5xl md:text-6xl mb-4">{obra.nombre}</h1>
              <p className="text-muted text-lg mb-2 flex items-center gap-2">
                <MapPin size={14}/> {obra.ciudad || obra.direccion}
              </p>
              {data?.cliente_nombre && (
                <p className="text-muted text-sm mb-6">
                  Cliente ·{' '}
                  {obra.cliente_id ? (
                    <Link to={`/clientes/${obra.cliente_id}`} className="text-navy hover:underline">
                      {data.cliente_nombre}
                    </Link>
                  ) : (
                    <span className="text-navy">{data.cliente_nombre}</span>
                  )}
                </p>
              )}
              {obra.descripcion && <p className="text-navy/80 text-base leading-relaxed max-w-xl mb-8">{obra.descripcion}</p>}

              <div className="inline-flex items-center gap-2 bg-white border border-border rounded-full px-4 py-2 mb-8">
                <span className={`w-2 h-2 rounded-full ${health.dot}`}/>
                <span className="text-sm font-medium">Estado: {health.txt}</span>
              </div>

              {/* Mega progress */}
              <div>
                <div className="flex justify-between items-baseline mb-2">
                  <span className="text-[11px] uppercase tracking-[0.15em] text-muted font-semibold">Avance del proyecto</span>
                  <span className="hero-title text-3xl">{Math.round(obra.progreso)}%</span>
                </div>
                <div className="h-2 bg-bone-200 rounded-full overflow-hidden">
                  <div className="h-full bg-navy transition-all duration-1000" style={{ width: `${obra.progreso}%` }}/>
                </div>
              </div>
            </div>

            {/* Visual */}
            <div className="flex items-center justify-center">
              <div className="relative">
                <div className="absolute inset-0 blur-3xl opacity-30" style={{ background: obra.color }}/>
                <div className="relative text-[14rem] leading-none select-none">{obra.icono}</div>
              </div>
            </div>
          </div>

          {/* Stats grid Apple-style */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-x-8 gap-y-6 mt-12 pt-12 border-t border-border">
            <BigStat label="Presupuesto" value={`${Math.round(presupuesto_pct)}%`} sub="consumido"/>
            <BigStat label="Equipo" value={data.obreros_total} sub={`${data.cuadrillas_activas} cuadrillas`}/>
            <BigStat label="Frentes" value={`${data.frentes_completados}/${data.frentes_total}`} sub="completados"/>
            <BigStat label="Días restantes" value={data.dias_restantes ?? '—'} sub="estimados"/>
            <BigStat label="Pendientes" value={data.ordenes_pendientes} sub="órdenes activas"/>
          </div>
        </div>
      </section>

      {/* Tabs */}
      <div className="sticky top-14 z-30 bg-white/85 backdrop-blur border-b border-border">
        <div className="px-8 max-w-[1400px] mx-auto flex gap-1 overflow-x-auto">
          {[
            { v: 'overview', l: 'Resumen' },
            { v: 'finanzas', l: `Finanzas` },
            { v: 'etapas', l: `Etapas` },
            { v: 'frentes', l: `Frentes` },
            { v: 'ordenes', l: `Órdenes` },
            { v: 'eventos', l: `Actividad` },
            { v: 'requerimientos', l: `Requerimientos` },
          ].map(t => (
            <button key={t.v} onClick={()=>setTab(t.v)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition whitespace-nowrap ${
                tab === t.v ? 'border-navy text-navy' : 'border-transparent text-muted hover:text-navy'
              }`}>
              {t.l}
            </button>
          ))}
        </div>
      </div>

      <div className="px-8 py-8 max-w-[1400px] mx-auto">
        {tab === 'overview' && <Overview frentes={frentes} eventos={eventos} ordenes={ordenes}/>}
        {tab === 'finanzas' && <FinanzasTab obraId={id} dashboard={data}/>}
        {tab === 'etapas' && <EtapasTab etapas={etapas} obraId={id} obra={obra} reload={load}/>}
        {tab === 'frentes' && <FrentesTab frentes={frentes} obraId={id} reload={load}/>}
        {tab === 'ordenes' && <OrdenesTab ordenes={ordenes} obraId={id} reload={load}/>}
        {tab === 'eventos' && <EventosTab eventos={eventos} obraId={id} reload={load}/>}
        {tab === 'requerimientos' && <RequerimientosTab obraId={id} obraCodigo={obra?.codigo}/>}
      </div>
    </div>
  )
}

// Sprint 21 — Finanzas tab: 2 cajas (blanco / negro) + consolidado, sin graficos.

function FinanzasTab({ obraId, dashboard }) {
  return <FinanzasBlancoNegroTab obraId={obraId} dashboard={dashboard}/>
}


function FlujoProyectadoTable({ items, fmtMoney }) {
  // Calcular saldo acumulado proyectado
  let saldo = 0
  const enriquecidos = items.map(it => {
    const monto = it.tipo === 'INGRESO' ? Number(it.monto) : -Number(it.monto)
    saldo += monto
    return { ...it, saldo_acum: saldo }
  })

  const ORIGEN_LABEL = {
    real: { txt: 'Real', cls: 'chip-muted' },
    cheque_pendiente: { txt: 'Cheque a vencer', cls: 'chip-warn' },
    etapa_estimada: { txt: 'Etapa estimada', cls: 'chip-navy' },
  }

  return (
    <div className="card overflow-hidden">
      <table className="w-full text-[12px]">
        <thead>
          <tr className="bg-bone-100/50 text-muted uppercase text-[10px] tracking-wide">
            <th className="text-left px-4 py-3 font-semibold">Fecha</th>
            <th className="text-left px-4 py-3 font-semibold">Concepto</th>
            <th className="text-left px-4 py-3 font-semibold">Origen</th>
            <th className="text-right px-4 py-3 font-semibold">Monto</th>
            <th className="text-right px-4 py-3 font-semibold">Saldo proyectado</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border/50">
          {enriquecidos.map((it, i) => {
            const isIngreso = it.tipo === 'INGRESO'
            const origen = ORIGEN_LABEL[it.origen] || { txt: it.origen, cls: 'chip-muted' }
            return (
              <tr key={i} className="hover:bg-bone-100/30 transition">
                <td className="px-4 py-3 whitespace-nowrap text-navy/80">
                  {new Date(it.fecha_efectiva).toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: '2-digit' })}
                </td>
                <td className="px-4 py-3 max-w-md truncate text-navy" title={it.concepto}>{it.concepto}</td>
                <td className="px-4 py-3"><span className={`chip ${origen.cls} text-[10px]`}>{origen.txt}</span></td>
                <td className={`px-4 py-3 text-right font-mono font-semibold whitespace-nowrap ${isIngreso ? 'text-olive-700' : 'text-leather'}`}>
                  {isIngreso ? '+' : '−'}{fmtMoney(it.monto)}
                </td>
                <td className={`px-4 py-3 text-right font-mono whitespace-nowrap ${it.saldo_acum >= 0 ? 'text-navy' : 'text-leather'}`}>
                  {fmtMoney(it.saldo_acum)}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────
// Etapas tab (Sprint 3 · T7)
// ─────────────────────────────────────────────────────────────────

function EtapasTab({ etapas, obraId, obra, reload }) {
  const [showNew, setShowNew] = useState(false)
  const [savingId, setSavingId] = useState(null)
  const [error, setError] = useState('')

  const fmtMoney = (n) => {
    if (!n) return '—'
    if (n >= 1e6) return `$${(n / 1e6).toFixed(2)}M`
    if (n >= 1e3) return `$${(n / 1e3).toFixed(0)}k`
    return `$${Math.round(n)}`
  }

  const cambiarEstado = async (etapa, nuevoEstado) => {
    setError('')
    setSavingId(etapa.id)
    try {
      const payload = {
        obra_id: etapa.obra_id,
        nombre: etapa.nombre,
        nro_etapa: etapa.nro_etapa,
        monto_contractual: etapa.monto_contractual,
        porcentaje_avance: etapa.porcentaje_avance,
        estado: nuevoEstado,
        fecha_estimada: etapa.fecha_estimada,
        fecha_cobro_real: nuevoEstado === 'COBRADA' && !etapa.fecha_cobro_real
          ? new Date().toISOString().slice(0, 10)
          : etapa.fecha_cobro_real,
        notas: etapa.notas,
      }
      await api.put(`/api/etapas/${etapa.id}`, payload)
      reload()
    } catch (e) {
      setError(e.response?.data?.detail || 'Error al actualizar estado')
    } finally {
      setSavingId(null)
    }
  }

  const totalContractual = etapas.reduce((s, e) => s + (parseFloat(e.monto_contractual) || 0), 0)
  const cobrado = etapas.filter(e => e.estado === 'COBRADA').reduce((s, e) => s + (parseFloat(e.monto_contractual) || 0), 0)

  return (
    <div className="space-y-5">
      <div className="flex items-end justify-between">
        <div>
          <h2 className="text-[11px] uppercase tracking-[0.2em] font-semibold text-olive-700 mb-1">Etapas de obra</h2>
          <div className="text-2xl font-semibold tracking-tight text-navy">
            {fmtMoney(cobrado)} <span className="text-muted text-base font-normal">de {fmtMoney(totalContractual)} cobrado</span>
          </div>
        </div>
        <button onClick={() => setShowNew(true)} className="btn btn-primary">
          <Plus size={13}/> Nueva etapa
        </button>
      </div>

      {showNew && (
        <NewEtapaModal
          obraId={obraId}
          siguienteNro={etapas.length === 0 ? 0 : Math.max(...etapas.map(e => e.nro_etapa)) + 1}
          onClose={() => setShowNew(false)}
          onSaved={() => { setShowNew(false); reload() }}
        />
      )}

      {error && (
        <div className="p-3 rounded-xl bg-danger/10 border border-danger/30 text-[12px] text-danger">{error}</div>
      )}

      {etapas.length === 0 ? (
        <Empty txt="Aún no hay etapas. Creá la primera (anticipo, etapa 1, etc.)"/>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="bg-bone-100/50 text-muted uppercase text-[10px] tracking-wide">
                <th className="text-left px-4 py-3 font-semibold w-12">Nº</th>
                <th className="text-left px-4 py-3 font-semibold">Nombre</th>
                <th className="text-right px-4 py-3 font-semibold">Monto</th>
                <th className="text-right px-4 py-3 font-semibold">% Obra</th>
                <th className="text-left px-4 py-3 font-semibold">Estado</th>
                <th className="text-left px-4 py-3 font-semibold">Fecha estim.</th>
                <th className="text-left px-4 py-3 font-semibold">Cobro real</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/50">
              {etapas.sort((a, b) => a.nro_etapa - b.nro_etapa).map(e => (
                <tr key={e.id} className="hover:bg-bone-100/30 transition">
                  <td className="px-4 py-3 font-mono text-navy/60">{e.nro_etapa}</td>
                  <td className="px-4 py-3 text-navy font-medium">{e.nombre}</td>
                  <td className="px-4 py-3 text-right font-mono text-navy/80 whitespace-nowrap">
                    {fmtMoney(parseFloat(e.monto_contractual))}
                  </td>
                  <td className="px-4 py-3 text-right text-muted whitespace-nowrap">
                    {e.porcentaje_avance ? `${parseFloat(e.porcentaje_avance).toFixed(0)}%` : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <select
                      value={e.estado}
                      onChange={(ev) => cambiarEstado(e, ev.target.value)}
                      disabled={savingId === e.id}
                      className={`rounded-full px-2.5 py-1 text-[10px] font-medium tracking-tight border-0 focus:outline-none focus:ring-2 focus:ring-navy/10 cursor-pointer ${ETAPA_ESTADO_CHIP[e.estado] || 'chip-muted'}`}
                    >
                      {ETAPA_ESTADOS.map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </td>
                  <td className="px-4 py-3 text-muted whitespace-nowrap text-[11px]">
                    {e.fecha_estimada ? new Date(e.fecha_estimada).toLocaleDateString('es-AR') : '—'}
                  </td>
                  <td className="px-4 py-3 text-muted whitespace-nowrap text-[11px]">
                    {e.fecha_cobro_real ? new Date(e.fecha_cobro_real).toLocaleDateString('es-AR') : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {obra?.tipo_facturacion && (
        <div className="text-[11px] text-muted">
          R5: si una etapa pasa a <strong>COBRADA</strong> con aportes de socio pendientes vinculados, el sistema crea automáticamente una nota importante para alertar.
        </div>
      )}
    </div>
  )
}

function NewEtapaModal({ obraId, siguienteNro, onClose, onSaved }) {
  const [nombre, setNombre] = useState('')
  const [nroEtapa, setNroEtapa] = useState(String(siguienteNro))
  const [monto, setMonto] = useState('')
  const [porcentaje, setPorcentaje] = useState('')
  const [fechaEst, setFechaEst] = useState('')
  const [notas, setNotas] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const formListo = nombre.trim() && nroEtapa !== '' && Number(nroEtapa) >= 0

  const submit = async () => {
    setError(''); setSubmitting(true)
    try {
      await api.post('/api/etapas', {
        obra_id: Number(obraId),
        nombre: nombre.trim(),
        nro_etapa: Number(nroEtapa),
        monto_contractual: monto ? Number(monto) : null,
        porcentaje_avance: porcentaje ? Number(porcentaje) : null,
        estado: 'PENDIENTE',
        fecha_estimada: fechaEst || null,
        notas: notas.trim() || null,
      })
      onSaved()
    } catch (e) {
      setError(e.response?.data?.detail || 'Error al guardar')
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-navy/30 backdrop-blur-sm z-50 grid place-items-center p-4 animate-fade-in" onClick={onClose}>
      <div className="card p-0 max-w-lg w-full overflow-hidden shadow-lift" onClick={e => e.stopPropagation()}>
        <div className="px-7 py-5 border-b border-border/60 flex items-center justify-between">
          <h2 className="hero-title text-2xl">Nueva etapa</h2>
          <button onClick={onClose} className="p-2 rounded-full text-muted hover:bg-bone-200/70 hover:text-navy transition">
            <X size={16}/>
          </button>
        </div>
        <div className="px-7 py-5 space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <span className="text-[10px] uppercase tracking-wide text-muted font-semibold block mb-1.5">Nº etapa <span className="text-danger">*</span></span>
              <input type="number" min="0" className="input-base" value={nroEtapa} onChange={e => setNroEtapa(e.target.value)}/>
            </div>
            <div className="col-span-2">
              <span className="text-[10px] uppercase tracking-wide text-muted font-semibold block mb-1.5">Nombre <span className="text-danger">*</span></span>
              <input className="input-base" value={nombre} onChange={e => setNombre(e.target.value)} placeholder="ej: Anticipo, Etapa 2 - Terminaciones"/>
            </div>
            <div className="col-span-2">
              <span className="text-[10px] uppercase tracking-wide text-muted font-semibold block mb-1.5">Monto contractual</span>
              <input type="number" min="0" step="0.01" className="input-base" value={monto} onChange={e => setMonto(e.target.value)} placeholder="0.00"/>
            </div>
            <div>
              <span className="text-[10px] uppercase tracking-wide text-muted font-semibold block mb-1.5">% obra</span>
              <input type="number" min="0" max="100" step="0.01" className="input-base" value={porcentaje} onChange={e => setPorcentaje(e.target.value)}/>
            </div>
            <div className="col-span-3">
              <span className="text-[10px] uppercase tracking-wide text-muted font-semibold block mb-1.5">Fecha estimada de cobro</span>
              <input type="date" className="input-base" value={fechaEst} onChange={e => setFechaEst(e.target.value)}/>
            </div>
            <div className="col-span-3">
              <span className="text-[10px] uppercase tracking-wide text-muted font-semibold block mb-1.5">Notas</span>
              <input className="input-base" value={notas} onChange={e => setNotas(e.target.value)}/>
            </div>
          </div>
          {error && <div className="p-3 rounded-xl bg-danger/10 border border-danger/30 text-[12px] text-danger">{error}</div>}
        </div>
        <div className="px-7 py-4 border-t border-border/60 flex justify-end gap-2 bg-bone-100/30">
          <button onClick={onClose} className="btn btn-ghost">Cancelar</button>
          <button onClick={submit} disabled={!formListo || submitting} className="btn btn-primary">
            {submitting ? <Loader2 size={13} className="animate-spin"/> : <Check size={13}/>}
            Crear etapa
          </button>
        </div>
      </div>
    </div>
  )
}

function BigStat({ label, value, sub }) {
  return (
    <div>
      <div className="stat-label mb-1">{label}</div>
      <div className="stat-value text-3xl">{value}</div>
      {sub && <div className="text-xs text-muted mt-1">{sub}</div>}
    </div>
  )
}

function Overview({ frentes, eventos, ordenes }) {
  const ordenesActivas = ordenes.filter(o => o.status !== 'completada').slice(0, 5)
  const eventosRecientes = eventos.slice(0, 6)
  return (
    <div className="grid lg:grid-cols-3 gap-5">
      <Section title="Frentes de trabajo" subtitle={`${frentes.filter(f=>f.estado==='completado').length} de ${frentes.length} completados`}>
        {frentes.length === 0 ? <Empty txt="Sin frentes"/> : (
          <ul className="space-y-3">
            {frentes.slice(0,8).map(f => (
              <li key={f.id}>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-sm font-medium">{f.nombre}</span>
                  <span className={ESTADO_FRENTE[f.estado].cls}>{Math.round(f.progreso)}%</span>
                </div>
                <div className="h-1 bg-bone-200 rounded-full overflow-hidden">
                  <div className="h-full bg-navy transition-all" style={{ width: `${f.progreso}%` }}/>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Órdenes activas" subtitle={`${ordenesActivas.length} pendientes`}>
        {ordenesActivas.length === 0 ? <Empty txt="Sin pendientes"/> : (
          <ul className="space-y-2">
            {ordenesActivas.map(o => (
              <li key={o.id} className="flex items-start gap-3 p-3 -mx-3 rounded-xl hover:bg-bone-100 transition">
                <span className={PRIORIDAD[o.prioridad]}>{o.prioridad}</span>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm">{o.titulo}</div>
                  <div className="text-xs text-muted truncate mt-0.5">{o.descripcion}</div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Actividad reciente" subtitle={`${eventos.length} eventos totales`}>
        {eventosRecientes.length === 0 ? <Empty txt="Sin actividad"/> : (
          <ul className="space-y-3">
            {eventosRecientes.map(e => (
              <li key={e.id} className={`flex gap-3 p-3 -mx-3 rounded-xl text-sm ${e.es_critico ? 'bg-danger/5' : 'hover:bg-bone-100'} transition`}>
                <span className={`w-7 h-7 rounded-full grid place-items-center text-xs shrink-0 ${e.es_critico ? 'bg-danger/15 text-danger' : 'bg-bone-200 text-navy'}`}>
                  {TIPO_EVENTO_ICON[e.tipo]}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="font-medium truncate">{e.titulo}</div>
                  <div className="text-xs text-muted truncate">{e.descripcion}</div>
                  <div className="text-[10px] text-muted/80 mt-0.5">
                    {new Date(e.fecha).toLocaleDateString()} · {e.canal}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  )
}

function Section({ title, subtitle, children }) {
  return (
    <div className="card p-6">
      <div className="mb-4">
        <h3 className="font-bold text-lg tracking-tight">{title}</h3>
        {subtitle && <p className="text-xs text-muted mt-0.5">{subtitle}</p>}
      </div>
      {children}
    </div>
  )
}

function Empty({ txt }) {
  return <p className="text-muted text-sm py-6 text-center">{txt}</p>
}

function FrentesTab({ frentes, obraId, reload }) {
  const [open, setOpen] = useState(false)
  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="hero-title text-2xl">Frentes de trabajo</h2>
          <p className="text-muted text-sm mt-1">Sub-mapas de la obra. Movés el slider para actualizar el avance.</p>
        </div>
        <button onClick={()=>setOpen(true)} className="btn-primary"><Plus size={14}/> Nuevo</button>
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {frentes.map(f => <FrenteCard key={f.id} frente={f} reload={reload}/>)}
      </div>
      {open && <NewFrenteModal obraId={obraId} onClose={()=>setOpen(false)} onSaved={()=>{ setOpen(false); reload() }}/>}
    </div>
  )
}

function FrenteCard({ frente, reload }) {
  const [progreso, setProgreso] = useState(frente.progreso)
  const e = ESTADO_FRENTE[frente.estado]

  const update = async (p) => {
    setProgreso(p)
    await api.patch(`/api/frentes/${frente.id}`, { ...frente, progreso: p })
    reload()
  }

  return (
    <div className="card p-5">
      <div className="flex items-start justify-between mb-2">
        <div>
          <div className="font-bold text-base">{frente.nombre}</div>
          <div className="text-[10px] uppercase tracking-wider text-muted mt-0.5">{frente.tipo}</div>
        </div>
        <span className={e.cls}>{e.txt}</span>
      </div>
      <div className="my-4">
        <div className="flex justify-between items-baseline mb-1">
          <span className="text-[11px] uppercase tracking-wider text-muted">Progreso</span>
          <span className="font-bold text-2xl tracking-tight">{Math.round(progreso)}%</span>
        </div>
        <input type="range" min="0" max="100" value={progreso}
          onChange={e => setProgreso(parseInt(e.target.value))}
          onMouseUp={e => update(parseInt(e.target.value))}
          onTouchEnd={e => update(parseInt(e.target.value))}
          className="w-full accent-navy" />
      </div>
    </div>
  )
}

function NewFrenteModal({ obraId, onClose, onSaved }) {
  const [form, setForm] = useState({
    nombre: '', tipo: 'estructura', icono: '⬛', estado: 'pendiente', progreso: 0,
  })
  const submit = async (e) => {
    e.preventDefault()
    await api.post('/api/frentes', { ...form, obra_id: parseInt(obraId), progreso: parseFloat(form.progreso)||0 })
    onSaved()
  }
  const TIPOS = ['cimientos','estructura','mamposteria','instalaciones','terminaciones']
  return (
    <Modal onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <h2 className="hero-title text-2xl">Nuevo frente</h2>
        <div><label className="label">Nombre</label><input className="input" value={form.nombre} onChange={e=>setForm({...form,nombre:e.target.value})} required/></div>
        <div><label className="label">Tipo</label>
          <select className="input" value={form.tipo} onChange={e=>setForm({...form,tipo:e.target.value})}>
            {TIPOS.map(t => <option key={t}>{t}</option>)}
          </select>
        </div>
        <div className="flex gap-2 justify-end pt-2">
          <button type="button" onClick={onClose} className="btn-ghost">Cancelar</button>
          <button className="btn-primary">Crear</button>
        </div>
      </form>
    </Modal>
  )
}

function OrdenesTab({ ordenes, obraId, reload }) {
  const [open, setOpen] = useState(false)
  const pend = ordenes.filter(o => o.status !== 'completada')
  const done = ordenes.filter(o => o.status === 'completada')

  const completar = async (id) => { await api.patch(`/api/ordenes/${id}/completar`); reload() }
  const iniciar = async (id) => { await api.patch(`/api/ordenes/${id}/iniciar`); reload() }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="hero-title text-2xl">Órdenes de trabajo</h2>
          <p className="text-muted text-sm mt-1">{pend.length} pendientes · {done.length} completadas</p>
        </div>
        <button onClick={()=>setOpen(true)} className="btn-primary"><Plus size={14}/> Nueva orden</button>
      </div>

      <div className="card divide-y divide-border">
        {pend.length === 0 ? (
          <div className="py-12 text-center text-muted text-sm">Sin órdenes pendientes</div>
        ) : pend.map(o => (
          <div key={o.id} className="p-5 flex items-center gap-4 hover:bg-bone-50 transition">
            <span className={PRIORIDAD[o.prioridad]}>{o.prioridad}</span>
            <div className="flex-1 min-w-0">
              <div className="font-semibold">{o.titulo}</div>
              <div className="text-sm text-muted truncate mt-0.5">{o.descripcion}</div>
              {o.fecha_limite && <div className="text-xs text-warn mt-1.5 flex items-center gap-1"><Clock size={11}/> {o.fecha_limite}</div>}
            </div>
            <div className="flex gap-2 shrink-0">
              {o.status === 'pendiente' && (
                <button onClick={()=>iniciar(o.id)} className="btn-ghost text-xs">Iniciar</button>
              )}
              <button onClick={()=>completar(o.id)} className="btn-accent text-xs"><Check size={12}/> Completar</button>
            </div>
          </div>
        ))}
      </div>

      {done.length > 0 && (
        <div className="card p-5">
          <h3 className="font-bold mb-4 text-sm uppercase tracking-wider text-muted">Completadas</h3>
          <ul className="space-y-2 text-sm">
            {done.slice(0,10).map(o => (
              <li key={o.id} className="flex items-center gap-3 text-muted">
                <Check size={14} className="text-olive"/>
                <span className="line-through">{o.titulo}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {open && <NewOrdenModal obraId={obraId} onClose={()=>setOpen(false)} onSaved={()=>{ setOpen(false); reload() }}/>}
    </div>
  )
}

function NewOrdenModal({ obraId, onClose, onSaved }) {
  const [form, setForm] = useState({
    titulo: '', descripcion: '', prioridad: 'normal', xp_reward: 10, fecha_limite: '',
  })
  const [cuadrillas, setCuadrillas] = useState([])
  const [cuadId, setCuadId] = useState('')

  useEffect(() => { api.get('/api/cuadrillas/').then(r => setCuadrillas(r.data)) }, [])

  const submit = async (e) => {
    e.preventDefault()
    await api.post('/api/ordenes/', {
      obra_id: parseInt(obraId),
      cuadrilla_id: cuadId ? parseInt(cuadId) : null,
      ...form,
      fecha_limite: form.fecha_limite || null,
      xp_reward: parseInt(form.xp_reward) || 10,
    })
    onSaved()
  }
  return (
    <Modal onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <h2 className="hero-title text-2xl">Nueva orden</h2>
        <div><label className="label">Título</label><input className="input" value={form.titulo} onChange={e=>setForm({...form,titulo:e.target.value})} required/></div>
        <div><label className="label">Descripción</label><textarea className="input" rows={2} value={form.descripcion} onChange={e=>setForm({...form,descripcion:e.target.value})}/></div>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="label">Prioridad</label>
            <select className="input" value={form.prioridad} onChange={e=>setForm({...form,prioridad:e.target.value})}>
              <option>baja</option><option>normal</option><option>alta</option><option>critica</option>
            </select>
          </div>
          <div><label className="label">Fecha límite</label><input className="input" type="date" value={form.fecha_limite} onChange={e=>setForm({...form,fecha_limite:e.target.value})}/></div>
        </div>
        <div><label className="label">Cuadrilla</label>
          <select className="input" value={cuadId} onChange={e=>setCuadId(e.target.value)}>
            <option value="">— Sin asignar —</option>
            {cuadrillas.map(c => <option key={c.id} value={c.id}>{c.nombre}</option>)}
          </select>
        </div>
        <div className="flex gap-2 justify-end pt-2">
          <button type="button" onClick={onClose} className="btn-ghost">Cancelar</button>
          <button className="btn-primary">Crear orden</button>
        </div>
      </form>
    </Modal>
  )
}

function EventosTab({ eventos, obraId, reload }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="hero-title text-2xl">Actividad</h2>
          <p className="text-muted text-sm mt-1">Cronología de eventos en la obra.</p>
        </div>
        <button onClick={()=>setOpen(true)} className="btn-primary"><Plus size={14}/> Reportar</button>
      </div>
      <div className="card divide-y divide-border">
        {eventos.map(e => (
          <div key={e.id} className={`p-5 flex gap-4 ${e.es_critico ? 'bg-danger/5' : ''}`}>
            <span className={`w-9 h-9 rounded-full grid place-items-center shrink-0 ${e.es_critico ? 'bg-danger/15 text-danger' : 'bg-bone-200 text-navy'}`}>
              {TIPO_EVENTO_ICON[e.tipo]}
            </span>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span className="font-semibold">{e.titulo}</span>
                {e.es_critico && <span className="chip-danger">Crítico</span>}
              </div>
              <div className="text-sm text-muted">{e.descripcion}</div>
              <div className="text-xs text-muted/80 mt-2">
                {new Date(e.fecha).toLocaleString()} · {e.canal}
              </div>
            </div>
          </div>
        ))}
      </div>
      {open && <NewEventoModal obraId={obraId} onClose={()=>setOpen(false)} onSaved={()=>{ setOpen(false); reload() }}/>}
    </div>
  )
}

function NewEventoModal({ obraId, onClose, onSaved }) {
  const [form, setForm] = useState({ titulo:'', descripcion:'', tipo:'avance', es_critico:false })
  const submit = async (e) => {
    e.preventDefault()
    await api.post('/api/eventos/', { ...form, obra_id: parseInt(obraId) })
    onSaved()
  }
  return (
    <Modal onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <h2 className="hero-title text-2xl">Reportar evento</h2>
        <div><label className="label">Tipo</label>
          <select className="input" value={form.tipo} onChange={e=>setForm({...form,tipo:e.target.value})}>
            {Object.keys(TIPO_EVENTO_ICON).map(k => <option key={k} value={k}>{k}</option>)}
          </select>
        </div>
        <div><label className="label">Título</label><input className="input" value={form.titulo} onChange={e=>setForm({...form,titulo:e.target.value})} required/></div>
        <div><label className="label">Descripción</label><textarea className="input" rows={3} value={form.descripcion} onChange={e=>setForm({...form,descripcion:e.target.value})}/></div>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={form.es_critico} onChange={e=>setForm({...form,es_critico:e.target.checked})} className="accent-danger"/>
          Marcar como crítico
        </label>
        <div className="flex gap-2 justify-end pt-2">
          <button type="button" onClick={onClose} className="btn-ghost">Cancelar</button>
          <button className="btn-primary">Reportar</button>
        </div>
      </form>
    </Modal>
  )
}

function Modal({ children, onClose }) {
  return (
    <div className="fixed inset-0 bg-navy/30 backdrop-blur-sm grid place-items-center z-50 p-4 animate-fade-in" onClick={onClose}>
      <div onClick={e=>e.stopPropagation()} className="card w-full max-w-md p-8 shadow-lift animate-scale-in">
        {children}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────
// Requerimientos tab (Sprint 17)
function RequerimientosTab({ obraId, obraCodigo }) {
  const [list, setList] = useState([])
  const [filtro, setFiltro] = useState('todos')  // todos | abierto | resuelto
  const [nuevo, setNuevo] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const r = await api.get(`/api/obras/${obraId}/requerimientos`)
      setList(r.data)
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => { load() }, [obraId])

  const crear = async (e) => {
    e.preventDefault()
    if (!nuevo.trim()) return
    setEnviando(true)
    try {
      await api.post('/api/requerimientos', { obra_id: Number(obraId), mensaje: nuevo.trim() })
      setNuevo('')
      load()
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al crear')
    } finally {
      setEnviando(false)
    }
  }
  const resolver = async (rid) => {
    await api.patch(`/api/requerimientos/${rid}/resolver`)
    load()
  }
  const reabrir = async (rid) => {
    await api.patch(`/api/requerimientos/${rid}/reabrir`)
    load()
  }
  const eliminar = async (rid) => {
    if (!confirm('¿Eliminar requerimiento?')) return
    await api.delete(`/api/requerimientos/${rid}`)
    load()
  }

  const filtrados = list.filter(r => filtro === 'todos' || r.estado === filtro)
  const abiertos = list.filter(r => r.estado === 'abierto').length
  const resueltos = list.length - abiertos

  return (
    <div className="space-y-6">
      <div className="grid md:grid-cols-3 gap-4">
        <Stat label="Abiertos" value={abiertos} accent="text-leather" />
        <Stat label="Resueltos" value={resueltos} accent="text-olive" />
        <Stat label="Total" value={list.length} />
      </div>

      <form onSubmit={crear} className="card p-5">
        <div className="text-xs text-muted mb-2">
          Anotá un imprevisto o pedido sobre <strong>{obraCodigo}</strong>. También se puede mandar
          por Telegram con <code className="bg-bone-200 px-1 rounded">/req {obraCodigo} &lt;mensaje&gt;</code>.
        </div>
        <div className="flex gap-2">
          <input
            className="input flex-1"
            placeholder="Ej: falta cemento, mando 5 bolsas mañana"
            value={nuevo}
            onChange={e => setNuevo(e.target.value)}
          />
          <button className="btn-primary" disabled={enviando || !nuevo.trim()}>
            <Plus size={14} /> {enviando ? 'Anotando…' : 'Anotar'}
          </button>
        </div>
      </form>

      <div className="flex gap-2 text-xs">
        {['todos', 'abierto', 'resuelto'].map(f => (
          <button
            key={f}
            onClick={() => setFiltro(f)}
            className={`px-3 py-1.5 rounded-full border transition ${
              filtro === f ? 'bg-navy text-bone border-navy' : 'border-border text-muted hover:text-navy'
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {loading && <div className="text-muted text-sm">Cargando…</div>}
      {!loading && filtrados.length === 0 && (
        <div className="text-muted text-sm py-8 text-center border border-dashed border-border rounded-xl">
          No hay requerimientos {filtro !== 'todos' ? `en estado "${filtro}"` : ''} todavía.
        </div>
      )}

      <div className="space-y-2">
        {filtrados.map(r => (
          <div key={r.id} className={`card p-4 flex items-start gap-3 ${
            r.estado === 'resuelto' ? 'opacity-60' : ''
          }`}>
            <div className={`mt-1 w-2 h-2 rounded-full shrink-0 ${
              r.estado === 'abierto' ? 'bg-leather' : 'bg-olive'
            }`}/>
            <div className="flex-1 min-w-0">
              <div className="text-sm whitespace-pre-wrap break-words">{r.mensaje}</div>
              <div className="text-[11px] text-muted mt-1.5 flex items-center gap-2 flex-wrap">
                <span>#{r.id}</span>
                <span>·</span>
                <span>{new Date(r.created_at).toLocaleString()}</span>
                <span>·</span>
                <span className={r.canal === 'whatsapp' ? 'flex items-center gap-1' : ''}>
                  {r.canal === 'whatsapp' && <MessageCircle size={10}/>}
                  {r.canal}
                </span>
                {r.resuelto_at && (
                  <>
                    <span>·</span>
                    <span className="text-olive">resuelto {new Date(r.resuelto_at).toLocaleString()}</span>
                  </>
                )}
              </div>
            </div>
            <div className="flex items-center gap-1 shrink-0">
              {r.estado === 'abierto' ? (
                <button onClick={()=>resolver(r.id)} className="btn-ghost text-xs" title="Marcar resuelto">
                  <Check size={12}/> Resolver
                </button>
              ) : (
                <button onClick={()=>reabrir(r.id)} className="btn-ghost text-xs" title="Reabrir">
                  <RotateCcw size={12}/> Reabrir
                </button>
              )}
              <button onClick={()=>eliminar(r.id)} className="text-muted/60 hover:text-danger p-2">
                <Trash2 size={12}/>
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function Stat({ label, value, accent }) {
  return (
    <div className="card p-4">
      <div className="text-[10px] tracking-[0.18em] uppercase text-muted font-semibold mb-1">{label}</div>
      <div className={`hero-title text-3xl ${accent || ''}`}>{value}</div>
    </div>
  )
}

// ─── Sprint 21: contabilidad blanco/negro por obra ──────────────────────

const fmtMoneyArs = (n) => {
  if (n == null) return '$0'
  const sign = n < 0 ? '-' : ''
  const abs = Math.abs(n)
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(2)}M`
  if (abs >= 1e3) return `${sign}$${(abs / 1e3).toFixed(0)}k`
  return `${sign}$${Math.round(abs)}`
}

const MEDIO_PAGO_LABEL = {
  EFECTIVO: 'Efectivo',
  TRANSFERENCIA: 'Transferencia',
  CHEQUE_PROPIO: 'Cheque propio',
  CHEQUE_TERCERO: 'Cheque 3°',
  DEPOSITO_BANCARIO: 'Depósito',
}

function FinanzasBlancoNegroTab({ obraId, dashboard }) {
  const [caja, setCaja] = useState('blanco')
  const [resumen, setResumen] = useState(null)
  const [movs, setMovs] = useState([])
  const [proyectado, setProyectado] = useState([])
  const [descalce, setDescalce] = useState(null)
  const [horizonte, setHorizonte] = useState(90)
  const [loading, setLoading] = useState(true)

  const load = () => {
    setLoading(true)
    return Promise.all([
      api.get(`/api/movimientos/obra/${obraId}/resumen-finanzas`),
      api.get(`/api/movimientos`, { params: { obra_id: obraId, limit: 500 } }),
      api.get(`/api/movimientos/obra/${obraId}/flujo-proyectado`, { params: { horizonte_dias: horizonte } }).catch(() => ({ data: [] })),
      api.get(`/api/movimientos/descalce-fiscal`, { params: { obra_id: obraId } }).catch(() => ({ data: [] })),
    ]).then(([r, m, p, d]) => {
      setResumen(r.data)
      setMovs(m.data)
      setProyectado(p.data)
      setDescalce(Array.isArray(d.data) && d.data.length > 0 ? d.data[0] : null)
      setLoading(false)
    })
  }
  useEffect(() => { load() }, [obraId, horizonte])

  if (loading || !resumen) return <div className="card p-10 text-center text-muted text-sm">Cargando…</div>

  const movsCaja = caja === 'consolidado' ? movs : movs.filter(m => m.legalidad === caja)
  const cajaResumen = caja === 'consolidado' ? null : resumen[caja]

  const marcarCobrado = async (mid, tipo) => {
    const nuevo = tipo === 'INGRESO' ? 'cobrado' : 'pagado'
    await api.patch(`/api/movimientos/${mid}/finanzas`, { cobro_pago_estado: nuevo })
    load()
  }
  const marcarPendiente = async (mid) => {
    await api.patch(`/api/movimientos/${mid}/finanzas`, { cobro_pago_estado: 'pendiente' })
    load()
  }
  const cambiarLegalidad = async (mid, actual) => {
    const nueva = actual === 'blanco' ? 'negro' : 'blanco'
    await api.patch(`/api/movimientos/${mid}/finanzas`, { legalidad: nueva })
    load()
  }

  return (
    <div className="space-y-6">
      <section className="grid md:grid-cols-4 gap-4">
        <BigStat label="Contrato" value={fmtMoneyArs(resumen.monto_contrato)}/>
        <BigStat label="Lo que tenés" value={fmtMoneyArs(resumen.lo_que_tenes)} sub="cobrado − pagado"/>
        <BigStat label="Lo que se debe" value={fmtMoneyArs(resumen.lo_que_se_debe)} sub="por cobrar − por pagar"/>
        <BigStat label="Saldo total" value={fmtMoneyArs(resumen.saldo_total)}/>
      </section>

      <div className="flex gap-1.5 text-sm">
        {[
          { v: 'blanco', l: 'Blanco', stats: resumen.blanco },
          { v: 'negro', l: 'Negro', stats: resumen.negro },
          { v: 'consolidado', l: 'Consolidado' },
        ].map(t => (
          <button
            key={t.v}
            onClick={() => setCaja(t.v)}
            className={`px-4 py-2 rounded-xl transition font-medium ${
              caja === t.v ? 'bg-navy text-bone' : 'text-navy/65 hover:bg-bone-200/60'
            }`}
          >
            {t.l}
            {t.stats && (
              <span className="ml-2 text-[11px] opacity-70">{fmtMoneyArs(t.stats.neto_efectivo)}</span>
            )}
          </button>
        ))}
      </div>

      {cajaResumen && (
        <section className="grid md:grid-cols-4 gap-3">
          <Stat label="Cobrado" value={fmtMoneyArs(cajaResumen.ingresos_cobrado)} accent="text-olive"/>
          <Stat label="Pagado" value={fmtMoneyArs(cajaResumen.egresos_pagado)} accent="text-leather"/>
          <Stat label="Por cobrar" value={fmtMoneyArs(cajaResumen.ingresos_pendiente)}/>
          <Stat label="Por pagar" value={fmtMoneyArs(cajaResumen.egresos_pendiente)}/>
          {caja === 'blanco' && (
            <>
              <Stat label="IVA total" value={fmtMoneyArs(cajaResumen.iva_total)}/>
              <Stat label="IIBB total" value={fmtMoneyArs(cajaResumen.iibb_total)}/>
              <Stat label="Gastos banco" value={fmtMoneyArs(cajaResumen.gastos_banco_total)}/>
              <Stat label="Neto efectivo" value={fmtMoneyArs(cajaResumen.neto_efectivo)}/>
            </>
          )}
        </section>
      )}

      <section className="card overflow-hidden">
        <table className="w-full text-[12px]">
          <thead>
            <tr className="bg-bone-100/50 text-muted uppercase text-[10px] tracking-wide">
              <th className="text-left px-3 py-3 font-semibold">Fecha</th>
              <th className="text-left px-3 py-3 font-semibold">Concepto</th>
              {caja === 'consolidado' && <th className="text-left px-3 py-3 font-semibold">Caja</th>}
              <th className="text-left px-3 py-3 font-semibold">Medio</th>
              <th className="text-right px-3 py-3 font-semibold">Monto</th>
              <th className="text-left px-3 py-3 font-semibold">Estado</th>
              <th className="text-right px-3 py-3 font-semibold">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/50">
            {movsCaja.map(m => {
              const isIng = m.tipo === 'INGRESO'
              const cobrado = m.cobro_pago_estado === 'cobrado' || m.cobro_pago_estado === 'pagado'
              return (
                <tr key={m.id} className="hover:bg-bone-100/30 transition">
                  <td className="px-3 py-2.5 whitespace-nowrap text-navy/80">
                    {new Date(m.fecha).toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: '2-digit' })}
                  </td>
                  <td className="px-3 py-2.5 max-w-xs truncate" title={m.concepto}>{m.concepto}</td>
                  {caja === 'consolidado' && (
                    <td className="px-3 py-2.5">
                      <span className={m.legalidad === 'blanco' ? 'chip-olive text-[10px]' : 'chip-danger text-[10px]'}>
                        {m.legalidad}
                      </span>
                    </td>
                  )}
                  <td className="px-3 py-2.5 text-muted">{MEDIO_PAGO_LABEL[m.medio_pago] || m.medio_pago}</td>
                  <td className={`px-3 py-2.5 text-right font-mono font-semibold ${isIng ? 'text-olive-700' : 'text-leather'}`}>
                    {isIng ? '+' : '−'}{fmtMoneyArs(Number(m.monto))}
                  </td>
                  <td className="px-3 py-2.5">
                    {cobrado ? (
                      <span className="chip-olive text-[10px]">{m.cobro_pago_estado}{m.fecha_cobro_pago ? ` · ${m.fecha_cobro_pago}` : ''}</span>
                    ) : (
                      <span className="chip-warn text-[10px]">pendiente</span>
                    )}
                  </td>
                  <td className="px-3 py-2.5 text-right whitespace-nowrap">
                    {cobrado ? (
                      <button onClick={() => marcarPendiente(m.id)} className="btn-ghost text-[11px]" title="Volver a pendiente">
                        <Clock size={10}/> Reabrir
                      </button>
                    ) : (
                      <button onClick={() => marcarCobrado(m.id, m.tipo)} className="btn-ghost text-[11px]">
                        <Check size={10}/> {isIng ? 'Cobrado' : 'Pagado'}
                      </button>
                    )}
                    <button
                      onClick={() => cambiarLegalidad(m.id, m.legalidad)}
                      className="btn-ghost text-[11px] ml-1"
                      title="Cambiar blanco/negro"
                    >
                      ⇄
                    </button>
                  </td>
                </tr>
              )
            })}
            {movsCaja.length === 0 && (
              <tr>
                <td colSpan={caja === 'consolidado' ? 7 : 6} className="px-4 py-8 text-center text-muted">
                  Sin movimientos en esta caja.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>

      {descalce && descalce.tiene_descalce && (
        <section className="card p-5 border-2 border-warn/30 bg-warn/5">
          <div className="flex items-start gap-3">
            <AlertCircle size={18} className="text-leather shrink-0 mt-0.5"/>
            <div className="flex-1">
              <h3 className="font-semibold text-navy mb-1">Descalce fiscal detectado</h3>
              <p className="text-[13px] text-navy/80 mb-2">
                Esta obra ({descalce.tipo_facturacion}) tiene <strong>{fmtMoneyArs(descalce.egresos_con_comprobante)}</strong> de egresos con factura
                pero solo <strong>{fmtMoneyArs(descalce.ingresos_con_comprobante)}</strong> de ingresos con factura.
              </p>
              <div className="text-xl font-bold text-leather">{fmtMoneyArs(descalce.descalce)}</div>
            </div>
          </div>
        </section>
      )}

      <section>
        <div className="flex items-end justify-between mb-3">
          <h2 className="text-sm font-semibold text-navy">Flujo proyectado</h2>
          <select
            value={horizonte}
            onChange={e => setHorizonte(Number(e.target.value))}
            className="input !py-1.5 !text-xs !w-auto"
          >
            <option value="30">Próximos 30 días</option>
            <option value="60">Próximos 60 días</option>
            <option value="90">Próximos 90 días</option>
            <option value="180">Próximos 6 meses</option>
            <option value="365">Próximos 12 meses</option>
          </select>
        </div>
        {proyectado.length === 0 ? (
          <Empty txt="Nada proyectado en el horizonte seleccionado."/>
        ) : (
          <FlujoProyectadoTable items={proyectado} fmtMoney={fmtMoneyArs}/>
        )}
      </section>
    </div>
  )
}
