import { useEffect, useState } from 'react'
import api from '../utils/api'

const COLORES = ['#1E2B5E','#3D4F1E','#8A9A5B','#6B4C30','#A8845F','#C4B99A','#4A5C95','#9CAB6B']

function fmtMoney(n) {
  if (!n) return '$0'
  if (n >= 1e6) return `$${(n / 1e6).toFixed(2)}M`
  if (n >= 1e3) return `$${(n / 1e3).toFixed(0)}k`
  return `$${n.toFixed(0)}`
}

export default function Finanzas() {
  const [obras, setObras] = useState([])
  const [gastos, setGastos] = useState([])
  const [resumen, setResumen] = useState([])

  useEffect(() => {
    Promise.all([
      api.get('/api/obras'),
      api.get('/api/gastos/'),
      api.get('/api/gastos/resumen'),
    ]).then(([o, g, r]) => { setObras(o.data); setGastos(g.data); setResumen(r.data) })
  }, [])

  const total = gastos.reduce((a, g) => a + g.monto, 0)
  const totalPres = obras.reduce((a, o) => a + (o.presupuesto_total || 0), 0)
  const totalCons = obras.reduce((a, o) => a + (o.presupuesto_consumido || 0), 0)
  const disponible = totalPres - totalCons

  return (
    <div className="max-w-7xl mx-auto animate-fade-in">
      <header className="mb-12">
        <div className="hero-eyebrow">Finanzas</div>
        <h1 className="hero-title text-5xl md:text-6xl mb-3">Presupuestos.</h1>
        <p className="hero-sub">Control completo del flujo financiero por proyecto.</p>
      </header>

      {/* Big numbers Apple-style */}
      <section className="grid md:grid-cols-3 gap-6 mb-10">
        <BigNumber label="Total comprometido" value={fmtMoney(totalPres)}/>
        <BigNumber label="Consumido" value={fmtMoney(totalCons)} sub={`${totalPres ? Math.round(totalCons/totalPres*100) : 0}%`} accent="leather"/>
        <BigNumber label="Disponible" value={fmtMoney(disponible)} accent="olive"/>
      </section>

      <div className="grid lg:grid-cols-2 gap-5 mb-6">
        {/* Categorías */}
        <div className="card p-6">
          <h2 className="hero-title text-xl mb-4">Por categoría</h2>
          <ul className="space-y-3">
            {resumen.map((r, i) => {
              const pct = total ? (r.total / total * 100) : 0
              return (
                <li key={r.categoria}>
                  <div className="flex items-center justify-between text-sm mb-1.5">
                    <span className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-sm" style={{ background: COLORES[i % COLORES.length] }}/>
                      {r.categoria}
                    </span>
                    <span className="font-semibold">{fmtMoney(r.total)}</span>
                  </div>
                  <div className="h-1 bg-bone-200 rounded-full overflow-hidden">
                    <div className="h-full transition-all duration-700" style={{ width: `${pct}%`, background: COLORES[i % COLORES.length] }}/>
                  </div>
                </li>
              )
            })}
            {resumen.length === 0 && <li className="text-muted text-sm">Sin gastos.</li>}
          </ul>
        </div>

        {/* Por obra */}
        <div className="card p-6">
          <h2 className="hero-title text-xl mb-4">Por obra</h2>
          <ul className="space-y-4">
            {obras.map(o => {
              const pct = o.presupuesto_total ? (o.presupuesto_consumido/o.presupuesto_total*100) : 0
              return (
                <li key={o.id}>
                  <div className="flex items-center justify-between text-sm mb-1.5">
                    <span className="font-medium">{o.nombre}</span>
                    <span className={pct > 90 ? 'text-warn font-bold' : 'text-muted text-xs'}>
                      {fmtMoney(o.presupuesto_consumido)} / {fmtMoney(o.presupuesto_total)}
                    </span>
                  </div>
                  <div className="h-1 bg-bone-200 rounded-full overflow-hidden">
                    <div className={`h-full transition-all duration-700 ${pct > 90 ? 'bg-warn' : 'bg-navy'}`}
                      style={{ width: `${Math.min(100,pct)}%` }}/>
                  </div>
                </li>
              )
            })}
          </ul>
        </div>
      </div>

      {/* Tabla de gastos */}
      <div className="card">
        <div className="px-6 py-4 border-b border-border">
          <h2 className="font-bold text-lg tracking-tight">Movimientos recientes</h2>
        </div>
        <div className="divide-y divide-border">
          {gastos.slice(0,20).map(g => {
            const obra = obras.find(o => o.id === g.obra_id)
            return (
              <div key={g.id} className="px-6 py-4 flex items-center gap-4 hover:bg-bone-50 transition">
                <div className="text-xs text-muted shrink-0 w-20">{g.fecha}</div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium">{g.descripcion}</div>
                  <div className="text-xs text-muted mt-0.5">
                    {obra?.nombre} · {g.categoria}
                  </div>
                </div>
                <div className="font-bold tracking-tight shrink-0">{fmtMoney(g.monto)}</div>
              </div>
            )
          })}
          {gastos.length === 0 && <div className="p-12 text-center text-muted">Sin movimientos.</div>}
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
      <div className={`hero-title text-4xl md:text-5xl mt-2 ${cls}`}>{value}</div>
      {sub && <div className="text-xs text-muted mt-1">{sub} del total</div>}
    </div>
  )
}
