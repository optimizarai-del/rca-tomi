import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ClipboardList, CheckCircle2, FileText, Trash2, Filter } from 'lucide-react'
import api from '../utils/api'

const ESTADO_CHIP = {
  borrador: 'chip-warn',
  aprobado: 'chip-olive',
  cerrado: 'chip-muted',
}

const fmtMoney = (n) => {
  const abs = Math.abs(n || 0)
  if (abs >= 1e6) return `$${(n/1e6).toFixed(2)}M`
  if (abs >= 1e3) return `$${(n/1e3).toFixed(0)}k`
  return `$${Math.round(n||0).toLocaleString()}`
}

export default function Presupuestos() {
  const [params, setParams] = useSearchParams()
  const [list, setList] = useState([])
  const [obras, setObras] = useState([])
  const [selected, setSelected] = useState(null)

  const obraFiltro = params.get('obra') || ''
  const estadoFiltro = params.get('estado') || ''

  const load = async () => {
    const qs = new URLSearchParams()
    if (obraFiltro) qs.set('obra_id', obraFiltro)
    if (estadoFiltro) qs.set('estado', estadoFiltro)
    const r = await api.get(`/api/presupuestos/?${qs.toString()}`)
    setList(r.data)
    if (selected && !r.data.find(p => p.id === selected.id)) {
      setSelected(null)
    }
  }

  useEffect(() => {
    api.get('/api/obras/').then(r => setObras(r.data))
  }, [])
  useEffect(() => { load() }, [obraFiltro, estadoFiltro])

  const aprobar = async (p) => {
    if (!confirm(`Aprobar presupuesto "${p.nombre}"? No vas a poder agregar más items.`)) return
    const r = await api.post(`/api/presupuestos/${p.id}/aprobar`)
    setSelected(r.data)
    load()
  }

  const borrar = async (p) => {
    if (!confirm(`Borrar el presupuesto "${p.nombre}"?`)) return
    await api.delete(`/api/presupuestos/${p.id}`)
    setSelected(null)
    load()
  }

  const setFilter = (k, v) => {
    const next = new URLSearchParams(params)
    if (v) next.set(k, v); else next.delete(k)
    setParams(next)
  }

  const totalAprobado = list.filter(p => p.estado === 'aprobado').reduce((a, p) => a + (p.total_estimado || 0), 0)

  return (
    <div className="max-w-7xl mx-auto animate-fade-in">
      <header className="mb-12">
        <div className="hero-eyebrow">Materiales</div>
        <div className="flex items-end justify-between flex-wrap gap-4">
          <div>
            <h1 className="hero-title text-5xl md:text-6xl mb-3">Presupuestos.</h1>
            <p className="hero-sub">Cómputo de materiales por obra. Carga vía WhatsApp; aprobación acá.</p>
          </div>
        </div>
      </header>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
        <div className="card p-5">
          <div className="text-[10px] uppercase tracking-wider text-muted">Total</div>
          <div className="hero-title text-3xl">{list.length}</div>
        </div>
        <div className="card p-5">
          <div className="text-[10px] uppercase tracking-wider text-muted">Borradores</div>
          <div className="hero-title text-3xl text-leather">{list.filter(p=>p.estado==='borrador').length}</div>
        </div>
        <div className="card p-5">
          <div className="text-[10px] uppercase tracking-wider text-muted">Aprobado total</div>
          <div className="hero-title text-3xl text-olive">{fmtMoney(totalAprobado)}</div>
        </div>
      </div>

      <div className="flex items-center gap-3 mb-6 flex-wrap">
        <Filter size={14} className="text-muted"/>
        <select value={obraFiltro} onChange={e => setFilter('obra', e.target.value)} className="input max-w-xs">
          <option value="">Todas las obras</option>
          {obras.map(o => <option key={o.id} value={o.id}>{o.codigo} — {o.nombre}</option>)}
        </select>
        <div className="flex gap-1.5 bg-white border border-border rounded-full p-1">
          {['', 'borrador', 'aprobado', 'cerrado'].map(e => (
            <button key={e || 'todos'} onClick={() => setFilter('estado', e)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition capitalize ${estadoFiltro === e ? 'bg-navy text-bone' : 'text-navy/70 hover:bg-bone-200'}`}>
              {e || 'todos'}
            </button>
          ))}
        </div>
      </div>

      <div className="grid lg:grid-cols-[1fr_2fr] gap-6">
        <div className="space-y-3">
          {list.length === 0 && (
            <div className="card p-8 text-center text-muted text-sm">
              Sin presupuestos. Pedile al bot por WhatsApp:
              <pre className="mt-3 text-xs bg-bone-200 p-3 rounded text-left">
"crea presupuesto para obra IDS llamado &lsquo;cimientos&rsquo; con 100 cemento y 200 ladrillos"
              </pre>
            </div>
          )}
          {list.map(p => (
            <button key={p.id} onClick={() => setSelected(p)}
              className={`w-full text-left card p-4 transition ${selected?.id === p.id ? 'ring-2 ring-navy' : 'hover:shadow-soft'}`}>
              <div className="flex items-start justify-between gap-2 mb-1">
                <div className="font-semibold truncate">{p.nombre}</div>
                <span className={ESTADO_CHIP[p.estado] || 'chip-muted'}>{p.estado}</span>
              </div>
              <div className="text-xs text-muted">{p.obra_nombre}</div>
              <div className="mt-2 flex items-end justify-between">
                <div className="text-[11px] text-muted">{p.items?.length || 0} items</div>
                <div className="font-bold text-navy">{fmtMoney(p.total_estimado)}</div>
              </div>
            </button>
          ))}
        </div>

        <div>
          {selected ? (
            <PresupuestoDetail p={selected} onAprobar={() => aprobar(selected)} onBorrar={() => borrar(selected)}/>
          ) : (
            <div className="card p-12 text-center text-muted">
              <ClipboardList size={32} className="mx-auto mb-3 opacity-40"/>
              Elegí un presupuesto a la izquierda para ver el detalle.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function PresupuestoDetail({ p, onAprobar, onBorrar }) {
  return (
    <div className="card p-6 space-y-4">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="text-xs text-muted">{p.obra_nombre}</div>
          <h2 className="hero-title text-2xl">{p.nombre}</h2>
          <div className="mt-2 flex items-center gap-2 text-xs text-muted">
            <span className={ESTADO_CHIP[p.estado] || 'chip-muted'}>{p.estado}</span>
            <span>·</span>
            <span>creado {new Date(p.created_at).toLocaleDateString()}</span>
            {p.aprobado_at && <><span>·</span><span>aprobado {new Date(p.aprobado_at).toLocaleDateString()}</span></>}
          </div>
        </div>
        <div className="flex gap-2 flex-wrap">
          {p.estado === 'borrador' && (
            <>
              <button onClick={onAprobar} className="btn-primary">
                <CheckCircle2 size={14}/> Marcar aprobado
              </button>
              <button onClick={onBorrar} className="btn-ghost text-danger">
                <Trash2 size={14}/> Borrar
              </button>
            </>
          )}
        </div>
      </div>

      <div className="border-t border-border pt-4">
        <div className="grid grid-cols-12 gap-2 text-[10px] uppercase tracking-wider text-muted/70 font-semibold pb-2 border-b border-border">
          <div className="col-span-5">Material</div>
          <div className="col-span-2 text-right">Cantidad</div>
          <div className="col-span-2 text-right">Precio u.</div>
          <div className="col-span-3 text-right">Subtotal</div>
        </div>
        {(p.items || []).map(it => (
          <div key={it.id} className="grid grid-cols-12 gap-2 py-2 border-b border-border/40 text-sm">
            <div className="col-span-5 flex items-center gap-2">
              <FileText size={12} className="text-muted/60"/>
              {it.material_nombre}
            </div>
            <div className="col-span-2 text-right tabular-nums">{it.cantidad.toFixed(0)}</div>
            <div className="col-span-2 text-right tabular-nums">{fmtMoney(it.precio_unitario_estimado)}</div>
            <div className="col-span-3 text-right tabular-nums font-semibold">{fmtMoney(it.subtotal)}</div>
          </div>
        ))}
        {(!p.items || p.items.length === 0) && (
          <div className="py-6 text-center text-muted text-sm">Sin items.</div>
        )}
      </div>

      <div className="flex justify-end items-baseline gap-4 pt-2 border-t border-border">
        <span className="text-xs uppercase tracking-wider text-muted">Total estimado</span>
        <span className="hero-title text-3xl text-navy">{fmtMoney(p.total_estimado)}</span>
      </div>

      {p.notas && (
        <div className="text-xs text-muted bg-bone-200/50 p-3 rounded-xl">
          {p.notas}
        </div>
      )}
    </div>
  )
}
