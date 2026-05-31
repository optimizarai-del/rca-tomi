import { useEffect, useState, useMemo } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  Upload, FileText, Plus, Trash2, Link2, X, ArrowLeft, AlertCircle,
  Check, ChevronRight,
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

// ─── Lista de extractos / página principal ──────────────────────────────

export default function Consolidacion() {
  const { id } = useParams()
  if (id) return <ExtractoDetalle id={Number(id)}/>
  return <ExtractosLista/>
}

function ExtractosLista() {
  const nav = useNavigate()
  const [list, setList] = useState(null)
  const [openUpload, setOpenUpload] = useState(false)

  const load = () => api.get('/api/extractos').then(r => setList(r.data))
  useEffect(() => { load() }, [])

  const eliminar = async (eid) => {
    if (!confirm('Eliminar extracto y todos sus movimientos?')) return
    await api.delete(`/api/extractos/${eid}`)
    load()
  }

  return (
    <div className="max-w-5xl mx-auto animate-fade-in">
      <header className="mb-10 flex items-end justify-between gap-4 flex-wrap">
        <div>
          <div className="hero-eyebrow">Finanzas</div>
          <h1 className="hero-title text-5xl md:text-6xl mb-2">Consolidación bancaria</h1>
          <p className="hero-sub">Importá tu extracto y matchealo contra los movimientos de obra para ver el flujo real.</p>
        </div>
        <button className="btn-primary" onClick={() => setOpenUpload(true)}>
          <Upload size={14}/> Importar extracto
        </button>
      </header>

      {list === null && <div className="text-muted text-sm">Cargando…</div>}
      {list && list.length === 0 && (
        <div className="card p-12 text-center text-muted">
          Sin extractos cargados. <button onClick={() => setOpenUpload(true)} className="text-navy underline">Importá el primero</button>.
        </div>
      )}

      <div className="space-y-2">
        {list?.map(e => (
          <button
            key={e.id}
            onClick={() => nav(`/consolidacion/${e.id}`)}
            className="card card-hover p-5 w-full text-left flex items-center gap-4"
          >
            <FileText size={20} className="text-navy/60 shrink-0"/>
            <div className="flex-1 min-w-0">
              <div className="font-semibold">{e.banco}{e.cuenta && ` · ${e.cuenta}`}</div>
              <div className="text-xs text-muted mt-0.5 flex items-center gap-2 flex-wrap">
                {e.periodo_desde && <span>{e.periodo_desde} → {e.periodo_hasta}</span>}
                <span>·</span>
                <span>{e.total_movs} movs</span>
                <span>·</span>
                <span>Débitos {fmtMoney(e.total_debe)}</span>
                <span>·</span>
                <span>Créditos {fmtMoney(e.total_haber)}</span>
              </div>
            </div>
            <button
              onClick={(ev) => { ev.stopPropagation(); eliminar(e.id) }}
              className="text-muted/50 hover:text-danger p-2"
            >
              <Trash2 size={14}/>
            </button>
            <ChevronRight size={16} className="text-muted shrink-0"/>
          </button>
        ))}
      </div>

      {openUpload && (
        <UploadModal
          onClose={() => setOpenUpload(false)}
          onSaved={(eid) => { setOpenUpload(false); nav(`/consolidacion/${eid}`) }}
        />
      )}
    </div>
  )
}

// ─── Modal de import CSV ─────────────────────────────────────────────────

function UploadModal({ onClose, onSaved }) {
  const [step, setStep] = useState('upload')  // upload → map → preview
  const [filename, setFilename] = useState('')
  const [rows, setRows] = useState([])  // arrays
  const [headers, setHeaders] = useState([])
  const [mapping, setMapping] = useState({ fecha: '', descripcion: '', debito: '', credito: '', saldo: '' })
  const [meta, setMeta] = useState({ banco: '', cuenta: '', periodo_desde: '', periodo_hasta: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const parseCSV = (text) => {
    // simple CSV — separa por \n y , (no soporta comas dentro de comillas en serio).
    const lines = text.split(/\r?\n/).filter(l => l.trim().length > 0)
    return lines.map(l => l.split(/[,;\t]/).map(s => s.trim().replace(/^"|"$/g, '')))
  }

  const onFile = async (file) => {
    setError('')
    setFilename(file.name)
    const text = await file.text()
    const all = parseCSV(text)
    if (all.length < 2) {
      setError('CSV vacío o sin headers.')
      return
    }
    setHeaders(all[0])
    setRows(all.slice(1))
    // sugerir mapping automático por nombre de header
    const guess = {}
    all[0].forEach((h, i) => {
      const lo = h.toLowerCase()
      if (!guess.fecha && /fecha|date/.test(lo)) guess.fecha = String(i)
      if (!guess.descripcion && /desc|concepto|detalle|mov/.test(lo)) guess.descripcion = String(i)
      if (!guess.debito && /deb|salida|egreso/.test(lo)) guess.debito = String(i)
      if (!guess.credito && /cred|cr.dito|haber|entrada|ingreso/.test(lo)) guess.credito = String(i)
      if (!guess.saldo && /saldo|balance/.test(lo)) guess.saldo = String(i)
    })
    setMapping(prev => ({ ...prev, ...guess }))
    setStep('map')
  }

  const buildMovimientos = () => {
    const parseNum = (v) => {
      if (!v) return 0
      const n = Number(String(v).replace(/\./g, '').replace(',', '.').replace(/[^\d.\-]/g, ''))
      return isNaN(n) ? 0 : n
    }
    const parseDate = (v) => {
      if (!v) return null
      // intenta YYYY-MM-DD, DD/MM/YYYY o DD-MM-YYYY
      const iso = /^\d{4}-\d{2}-\d{2}$/
      const dmy = /^(\d{1,2})[\/-](\d{1,2})[\/-](\d{2,4})$/
      if (iso.test(v)) return v
      const m = v.match(dmy)
      if (m) {
        const yr = m[3].length === 2 ? `20${m[3]}` : m[3]
        return `${yr}-${m[2].padStart(2, '0')}-${m[1].padStart(2, '0')}`
      }
      return null
    }
    return rows.map(r => ({
      fecha: parseDate(r[Number(mapping.fecha)]),
      descripcion: (r[Number(mapping.descripcion)] || '').slice(0, 500),
      debito: parseNum(r[Number(mapping.debito)]),
      credito: parseNum(r[Number(mapping.credito)]),
      saldo: mapping.saldo === '' ? null : parseNum(r[Number(mapping.saldo)]),
    })).filter(m => m.fecha && m.descripcion)
  }

  const importar = async () => {
    setError(''); setSaving(true)
    try {
      const movs = buildMovimientos()
      if (!movs.length) throw new Error('No quedaron movimientos válidos tras el parseo.')
      const payload = {
        banco: meta.banco.trim() || 'Banco',
        cuenta: meta.cuenta.trim() || null,
        periodo_desde: meta.periodo_desde || null,
        periodo_hasta: meta.periodo_hasta || null,
        archivo_nombre: filename || null,
        movimientos: movs,
      }
      const r = await api.post('/api/extractos', payload)
      onSaved(r.data.id)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Error importando')
      setSaving(false)
    }
  }

  const movs = step === 'preview' ? buildMovimientos() : []

  return (
    <div className="fixed inset-0 bg-navy/30 backdrop-blur-sm z-50 grid place-items-center p-4 animate-fade-in" onClick={onClose}>
      <div className="card w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col shadow-lift" onClick={e => e.stopPropagation()}>
        <div className="px-6 py-4 border-b border-border flex items-center justify-between">
          <h2 className="hero-title text-2xl">Importar extracto</h2>
          <button onClick={onClose} className="p-2 rounded-full text-muted hover:bg-bone-200/70"><X size={16}/></button>
        </div>
        <div className="px-6 py-5 overflow-y-auto flex-1 space-y-4">
          {step === 'upload' && (
            <div className="space-y-4">
              <p className="text-sm text-muted">
                Subí un CSV exportado de tu home banking. En el siguiente paso elegís qué columna corresponde a fecha, descripción, débito, crédito y saldo.
              </p>
              <label className="card p-8 border-2 border-dashed border-border hover:border-navy cursor-pointer block text-center">
                <Upload size={28} className="mx-auto text-muted mb-2"/>
                <div className="text-sm font-medium">Subir archivo CSV</div>
                <div className="text-xs text-muted mt-1">Separadores soportados: , ; tab</div>
                <input type="file" accept=".csv,.txt" className="hidden" onChange={e => e.target.files?.[0] && onFile(e.target.files[0])}/>
              </label>
              {error && <div className="text-xs text-danger">{error}</div>}
            </div>
          )}

          {step === 'map' && (
            <div className="space-y-4">
              <div className="text-xs text-muted">
                Archivo <strong>{filename}</strong> · {rows.length} filas detectadas.
              </div>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { k: 'fecha', l: 'Fecha *' },
                  { k: 'descripcion', l: 'Descripción *' },
                  { k: 'debito', l: 'Débito (salida)' },
                  { k: 'credito', l: 'Crédito (entrada)' },
                  { k: 'saldo', l: 'Saldo (opcional)' },
                ].map(f => (
                  <label key={f.k} className="flex flex-col gap-1">
                    <span className="text-[10px] uppercase tracking-wide text-muted font-semibold">{f.l}</span>
                    <select
                      className="input"
                      value={mapping[f.k]}
                      onChange={e => setMapping({ ...mapping, [f.k]: e.target.value })}
                    >
                      <option value="">— ninguna —</option>
                      {headers.map((h, i) => (
                        <option key={i} value={i}>col {i+1}: {h || '(sin nombre)'}</option>
                      ))}
                    </select>
                  </label>
                ))}
              </div>

              <div className="grid grid-cols-2 gap-3 pt-3 border-t border-border">
                <label className="flex flex-col gap-1">
                  <span className="text-[10px] uppercase tracking-wide text-muted font-semibold">Banco *</span>
                  <input className="input" value={meta.banco} onChange={e => setMeta({ ...meta, banco: e.target.value })} placeholder="Galicia, BBVA, Santander…"/>
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-[10px] uppercase tracking-wide text-muted font-semibold">Cuenta / alias</span>
                  <input className="input" value={meta.cuenta} onChange={e => setMeta({ ...meta, cuenta: e.target.value })} placeholder="Caja ahorro AR$ #1234"/>
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-[10px] uppercase tracking-wide text-muted font-semibold">Periodo desde</span>
                  <input className="input" type="date" value={meta.periodo_desde} onChange={e => setMeta({ ...meta, periodo_desde: e.target.value })}/>
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-[10px] uppercase tracking-wide text-muted font-semibold">Periodo hasta</span>
                  <input className="input" type="date" value={meta.periodo_hasta} onChange={e => setMeta({ ...meta, periodo_hasta: e.target.value })}/>
                </label>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button onClick={onClose} className="btn-ghost">Cancelar</button>
                <button
                  onClick={() => setStep('preview')}
                  disabled={!mapping.fecha || !mapping.descripcion || !meta.banco.trim()}
                  className="btn-primary"
                >
                  Previsualizar
                </button>
              </div>
            </div>
          )}

          {step === 'preview' && (
            <div className="space-y-3">
              <div className="text-sm">
                {movs.length} movimientos listos para importar.
              </div>
              <div className="card overflow-hidden">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="bg-bone-100/50 text-muted uppercase text-[10px] tracking-wide">
                      <th className="text-left px-2 py-2">Fecha</th>
                      <th className="text-left px-2 py-2">Descripción</th>
                      <th className="text-right px-2 py-2">Débito</th>
                      <th className="text-right px-2 py-2">Crédito</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/40">
                    {movs.slice(0, 30).map((m, i) => (
                      <tr key={i}>
                        <td className="px-2 py-1.5">{m.fecha}</td>
                        <td className="px-2 py-1.5 truncate max-w-xs" title={m.descripcion}>{m.descripcion}</td>
                        <td className="px-2 py-1.5 text-right font-mono text-leather">{m.debito ? fmtMoney(m.debito) : ''}</td>
                        <td className="px-2 py-1.5 text-right font-mono text-olive">{m.credito ? fmtMoney(m.credito) : ''}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {movs.length > 30 && <div className="text-xs text-muted text-center py-2">…y {movs.length - 30} más</div>}
              </div>
              {error && <div className="text-xs text-danger">{error}</div>}
              <div className="flex justify-end gap-2 pt-2">
                <button onClick={() => setStep('map')} className="btn-ghost">Atrás</button>
                <button onClick={importar} disabled={saving} className="btn-primary">
                  {saving ? 'Importando…' : `Importar ${movs.length} movs`}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Detalle del extracto + match ────────────────────────────────────────

function ExtractoDetalle({ id }) {
  const nav = useNavigate()
  const [data, setData] = useState(null)
  const [sugerencias, setSugerencias] = useState({})  // mbid → sug list
  const [resumen, setResumen] = useState(null)
  const [filtro, setFiltro] = useState('todos')

  const load = async () => {
    const [e, sug, c] = await Promise.all([
      api.get(`/api/extractos/${id}`),
      api.get(`/api/extractos/${id}/sugerencias`),
      api.get(`/api/extractos/${id}/consolidacion`),
    ])
    setData(e.data)
    const map = {}
    sug.data.forEach(s => { map[s.id] = s.sugerencias })
    setSugerencias(map)
    setResumen(c.data)
  }
  useEffect(() => { load() }, [id])

  if (!data) return <div className="p-8 text-muted">Cargando…</div>

  const matchear = async (mbid, moid) => {
    try {
      await api.post(`/api/movimientos-bancarios/${mbid}/match`, { movimiento_obra_id: moid })
      load()
    } catch (err) {
      alert(err.response?.data?.detail || 'Error')
    }
  }
  const desvincular = async (mbid) => {
    await api.delete(`/api/movimientos-bancarios/${mbid}/match`)
    load()
  }

  const movs = data.movimientos.filter(m => {
    if (filtro === 'sin_match') return !m.movimiento_obra_id
    if (filtro === 'conciliados') return !!m.movimiento_obra_id
    return true
  })

  return (
    <div className="max-w-6xl mx-auto animate-fade-in">
      <button onClick={() => nav('/consolidacion')} className="btn-ghost mb-4 text-sm">
        <ArrowLeft size={14}/> Volver
      </button>

      <header className="mb-6">
        <div className="hero-eyebrow">Extracto</div>
        <h1 className="hero-title text-4xl mb-2">{data.banco}{data.cuenta && ` · ${data.cuenta}`}</h1>
        <p className="text-muted text-sm">
          {data.periodo_desde && `${data.periodo_desde} → ${data.periodo_hasta} · `}
          {data.total_movs} movimientos · {data.archivo_nombre}
        </p>
      </header>

      {resumen && (
        <section className="grid md:grid-cols-4 gap-3 mb-6">
          <BigStat label="Débitos extracto" value={fmtMoney(resumen.total_debe_extracto)} accent="text-leather"/>
          <BigStat label="Conciliado (D)" value={fmtMoney(resumen.total_debe_obra_conciliado)}/>
          <BigStat label="Créditos extracto" value={fmtMoney(resumen.total_haber_extracto)} accent="text-olive"/>
          <BigStat label="Conciliado (H)" value={fmtMoney(resumen.total_haber_obra_conciliado)}/>
          <Stat label="Movs total" value={resumen.movs_total}/>
          <Stat label="Conciliados" value={resumen.movs_conciliados} accent="text-olive"/>
          <Stat label="Sin match" value={resumen.movs_sin_match} accent="text-leather"/>
          <Stat label="Δ Débitos" value={fmtMoney(resumen.diferencia_debe)}/>
        </section>
      )}

      <div className="flex gap-2 text-xs mb-4">
        {[
          { v: 'todos', l: `Todos (${data.movimientos.length})` },
          { v: 'sin_match', l: `Sin match (${data.movimientos.filter(m => !m.movimiento_obra_id).length})` },
          { v: 'conciliados', l: `Conciliados (${data.movimientos.filter(m => m.movimiento_obra_id).length})` },
        ].map(t => (
          <button
            key={t.v}
            onClick={() => setFiltro(t.v)}
            className={`px-3 py-1.5 rounded-full border transition ${
              filtro === t.v ? 'bg-navy text-bone border-navy' : 'border-border text-muted hover:text-navy'
            }`}
          >
            {t.l}
          </button>
        ))}
      </div>

      <div className="card overflow-hidden">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-bone-100/50 text-muted uppercase text-[10px] tracking-wide">
              <th className="text-left px-3 py-3">Fecha</th>
              <th className="text-left px-3 py-3">Descripción</th>
              <th className="text-right px-3 py-3">Débito</th>
              <th className="text-right px-3 py-3">Crédito</th>
              <th className="text-left px-3 py-3">Match</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/40">
            {movs.map(m => (
              <tr key={m.id}>
                <td className="px-3 py-2.5 whitespace-nowrap">{m.fecha}</td>
                <td className="px-3 py-2.5 max-w-md truncate" title={m.descripcion}>{m.descripcion}</td>
                <td className="px-3 py-2.5 text-right font-mono text-leather">{m.debito ? fmtMoney(Number(m.debito)) : ''}</td>
                <td className="px-3 py-2.5 text-right font-mono text-olive">{m.credito ? fmtMoney(Number(m.credito)) : ''}</td>
                <td className="px-3 py-2.5">
                  {m.movimiento_obra_id ? (
                    <span className="flex items-center gap-1.5 text-olive">
                      <Check size={12}/> #{m.movimiento_obra_id}
                      <button onClick={() => desvincular(m.id)} className="text-muted/60 hover:text-danger ml-1" title="Desvincular"><X size={11}/></button>
                    </span>
                  ) : (
                    <SugerenciaSelect sugerencias={sugerencias[m.id] || []} onMatch={(moid) => matchear(m.id, moid)}/>
                  )}
                </td>
              </tr>
            ))}
            {movs.length === 0 && (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-muted">Sin movimientos.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function SugerenciaSelect({ sugerencias, onMatch }) {
  const [val, setVal] = useState('')
  if (sugerencias.length === 0) return <span className="text-muted text-[11px]">sin sugerencias</span>
  return (
    <select
      value={val}
      onChange={e => {
        const v = e.target.value
        if (v) { onMatch(Number(v)); setVal('') }
      }}
      className="input !py-1 !text-[11px] !w-auto max-w-[260px]"
    >
      <option value="">{sugerencias.length} sugerencia{sugerencias.length > 1 ? 's' : ''}</option>
      {sugerencias.map(s => (
        <option key={s.movimiento_obra_id} value={s.movimiento_obra_id}>
          [{s.obra_codigo}] {s.concepto.slice(0, 40)} · {s.fecha} · {fmtMoney(s.monto)}
        </option>
      ))}
    </select>
  )
}

function BigStat({ label, value, accent }) {
  return (
    <div className="card p-4">
      <div className="text-[10px] tracking-[0.18em] uppercase text-muted font-semibold mb-1">{label}</div>
      <div className={`hero-title text-2xl ${accent || ''}`}>{value}</div>
    </div>
  )
}

function Stat({ label, value, accent }) {
  return (
    <div className="card p-3">
      <div className="text-[10px] tracking-[0.18em] uppercase text-muted font-semibold mb-1">{label}</div>
      <div className={`text-lg font-semibold ${accent || ''}`}>{value}</div>
    </div>
  )
}
