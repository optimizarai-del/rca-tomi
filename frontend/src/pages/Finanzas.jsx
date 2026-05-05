import { useEffect, useState } from 'react'
import api from '../utils/api'

const COLORES = ['#1E2B5E','#3D4F1E','#8A9A5B','#6B4C30','#A8845F','#C4B99A','#4A5C95','#9CAB6B']

function fmtMoney(n) {
  if (!n && n !== 0) return '$0'
  if (Math.abs(n) >= 1e6) return `$${(n / 1e6).toFixed(2)}M`
  if (Math.abs(n) >= 1e3) return `$${(n / 1e3).toFixed(0)}k`
  return `$${n.toFixed(0)}`
}

const CATEGORIAS_LABELS = {
  MANO_DE_OBRA: 'Mano de obra',
  MATERIALES: 'Materiales',
  SUBCONTRATO: 'Subcontratos',
  SERVICIO_EXTERNO: 'Servicios',
  GASTO_DIRECTO_OBRA: 'Gasto directo',
  HERRAMIENTA_EQUIPO: 'Herramientas',
  APORTE_PRESTAMO: 'Aportes/préstamos',
}

export default function Finanzas() {
  const [obras, setObras] = useState([])
  const [movs, setMovs] = useState([])
  const [hud, setHud] = useState(null)
  const [cheques, setCheques] = useState([])

  useEffect(() => {
    Promise.all([
      api.get('/api/obras'),
      api.get('/api/movimientos?limit=100'),
      api.get('/api/dashboard/hud'),
      api.get('/api/movimientos/cheques-a-vencer?dias=60').catch(() => ({ data: [] })),
    ]).then(([o, m, h, c]) => {
      setObras(o.data); setMovs(m.data); setHud(h.data); setCheques(c.data || [])
    })
  }, [])

  // Egresos agrupados por categoría
  const egresos = movs.filter(m => m.tipo === 'EGRESO')
  const totalEg = egresos.reduce((a, m) => a + m.monto, 0)
  const porCat = {}
  egresos.forEach(m => {
    const k = m.categoria_egreso || 'OTRO'
    porCat[k] = (porCat[k] || 0) + m.monto
  })
  const resumenCat = Object.entries(porCat).sort((a, b) => b[1] - a[1])

  return (
    <div className="max-w-7xl mx-auto animate-fade-in">
      <header className="mb-12">
        <div className="hero-eyebrow">Finanzas</div>
        <h1 className="hero-title text-5xl md:text-6xl mb-3">Flujo de caja.</h1>
        <p className="hero-sub">Control financiero por obra: ingresos, egresos, aportes y cheques.</p>
      </header>

      {/* Big numbers — globales */}
      <section className="grid md:grid-cols-4 gap-5 mb-10">
        <BigNumber label="Contratado" value={fmtMoney(hud?.monto_contratos_total || 0)}/>
        <BigNumber label="Ingresos" value={fmtMoney(hud?.total_ingresos || 0)} accent="olive"/>
        <BigNumber label="Egresos" value={fmtMoney(hud?.total_egresos || 0)} accent="leather"/>
        <BigNumber
          label="Saldo global"
          value={fmtMoney(hud?.saldo_global || 0)}
          accent={hud?.saldo_global >= 0 ? 'olive' : 'leather'}
        />
      </section>

      {/* Alertas — aportes y cheques */}
      <section className="grid md:grid-cols-2 gap-5 mb-10">
        <div className="card p-6">
          <div className="flex items-center justify-between mb-2">
            <h2 className="hero-title text-xl">Aportes pendientes</h2>
            <span className="text-2xl font-bold text-leather">{fmtMoney(hud?.aportes_pendientes || 0)}</span>
          </div>
          <p className="text-xs text-muted">
            Plata que socios pusieron en obras y aún no se devolvió.
          </p>
        </div>
        <div className="card p-6">
          <div className="flex items-center justify-between mb-2">
            <h2 className="hero-title text-xl">Cheques a vencer</h2>
            <span className="text-2xl font-bold text-leather">{fmtMoney(hud?.cheques_a_vencer || 0)}</span>
          </div>
          <p className="text-xs text-muted">
            {cheques.length} cheque{cheques.length === 1 ? '' : 's'} propio{cheques.length === 1 ? '' : 's'} en los próximos 60 días.
          </p>
          {cheques.length > 0 && (
            <ul className="mt-3 space-y-1.5 text-xs">
              {cheques.slice(0, 4).map(c => (
                <li key={c.id} className="flex justify-between border-t border-border/50 pt-1.5">
                  <span>#{c.nro_cheque} · {c.banco}</span>
                  <span className="text-muted">{c.fecha_vto} ({c.dias_restantes}d) · {fmtMoney(c.monto)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      <div className="grid lg:grid-cols-2 gap-5 mb-6">
        {/* Egresos por categoría */}
        <div className="card p-6">
          <h2 className="hero-title text-xl mb-4">Egresos por categoría</h2>
          <ul className="space-y-3">
            {resumenCat.map(([cat, total], i) => {
              const pct = totalEg ? (total / totalEg * 100) : 0
              return (
                <li key={cat}>
                  <div className="flex items-center justify-between text-sm mb-1.5">
                    <span className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-sm" style={{ background: COLORES[i % COLORES.length] }}/>
                      {CATEGORIAS_LABELS[cat] || cat}
                    </span>
                    <span className="font-semibold">{fmtMoney(total)}</span>
                  </div>
                  <div className="h-1 bg-bone-200 rounded-full overflow-hidden">
                    <div className="h-full transition-all duration-700"
                         style={{ width: `${pct}%`, background: COLORES[i % COLORES.length] }}/>
                  </div>
                </li>
              )
            })}
            {resumenCat.length === 0 && <li className="text-muted text-sm">Sin egresos cargados.</li>}
          </ul>
        </div>

        {/* Por obra */}
        <div className="card p-6">
          <h2 className="hero-title text-xl mb-4">Por obra</h2>
          <ul className="space-y-4">
            {obras.map(o => {
              const ingObra = movs.filter(m => m.obra_id === o.id && m.tipo === 'INGRESO').reduce((a,m)=>a+m.monto,0)
              const egObra = movs.filter(m => m.obra_id === o.id && m.tipo === 'EGRESO').reduce((a,m)=>a+m.monto,0)
              const pct = o.monto_contrato ? (egObra / o.monto_contrato * 100) : 0
              return (
                <li key={o.id}>
                  <div className="flex items-center justify-between text-sm mb-1.5">
                    <span className="font-medium">{o.codigo} — {o.nombre}</span>
                    <span className={pct > 90 ? 'text-warn font-bold' : 'text-muted text-xs'}>
                      {fmtMoney(egObra)} / {fmtMoney(o.monto_contrato || 0)}
                    </span>
                  </div>
                  <div className="h-1 bg-bone-200 rounded-full overflow-hidden">
                    <div className={`h-full transition-all duration-700 ${pct > 90 ? 'bg-warn' : 'bg-navy'}`}
                         style={{ width: `${Math.min(100,pct)}%` }}/>
                  </div>
                  <div className="text-[11px] text-muted mt-1">
                    Saldo: <span className={ingObra-egObra>=0?'text-olive-700':'text-leather'}>{fmtMoney(ingObra - egObra)}</span>
                  </div>
                </li>
              )
            })}
          </ul>
        </div>
      </div>

      {/* Tabla de movimientos */}
      <div className="card">
        <div className="px-6 py-4 border-b border-border flex items-center justify-between">
          <h2 className="font-bold text-lg tracking-tight">Movimientos recientes</h2>
          <span className="text-xs text-muted">{movs.length} movimientos</span>
        </div>
        <div className="divide-y divide-border max-h-[600px] overflow-y-auto">
          {movs.slice(0, 50).map(m => {
            const obra = obras.find(o => o.id === m.obra_id)
            const isIng = m.tipo === 'INGRESO'
            return (
              <div key={m.id} className="px-6 py-4 flex items-center gap-4 hover:bg-bone-100/40 transition">
                <div className="text-xs text-muted shrink-0 w-20">{m.fecha}</div>
                <div className={`shrink-0 w-1.5 h-8 rounded ${isIng ? 'bg-olive' : 'bg-leather'}`}/>
                <div className="flex-1 min-w-0">
                  <div className="font-medium truncate">{m.concepto}</div>
                  <div className="text-xs text-muted mt-0.5 flex flex-wrap gap-2">
                    <span>{obra?.codigo}</span>
                    <span>·</span>
                    <span>{m.medio_pago}</span>
                    {m.categoria_egreso && <><span>·</span><span>{CATEGORIAS_LABELS[m.categoria_egreso] || m.categoria_egreso}</span></>}
                    {m.origen_ingreso && <><span>·</span><span>{m.origen_ingreso}</span></>}
                    {m.tiene_comprobante && <span className="chip-olive text-[10px] px-1.5 py-0.5 rounded">FC</span>}
                    {m.estado === 'A_REVISAR' && <span className="chip-warn text-[10px] px-1.5 py-0.5 rounded">A revisar</span>}
                  </div>
                </div>
                <div className={`font-bold tracking-tight shrink-0 ${isIng ? 'text-olive-700' : 'text-leather'}`}>
                  {isIng ? '+' : '−'} {fmtMoney(m.monto)}
                </div>
              </div>
            )
          })}
          {movs.length === 0 && <div className="p-12 text-center text-muted">Sin movimientos.</div>}
        </div>
      </div>
    </div>
  )
}

function BigNumber({ label, value, sub, accent }) {
  const cls = accent === 'olive' ? 'text-olive-700' : accent === 'leather' ? 'text-leather' : 'text-navy'
  return (
    <div className="card p-6">
      <div className="stat-label">{label}</div>
      <div className={`hero-title text-3xl md:text-4xl mt-2 ${cls}`}>{value}</div>
      {sub && <div className="text-xs text-muted mt-1">{sub}</div>}
    </div>
  )
}
