import { useEffect, useState } from 'react'
import { Check, Clock, Zap } from 'lucide-react'
import api from '../utils/api'

const PRIORIDAD = {
  baja: 'chip-muted', normal: 'chip-navy', alta: 'chip-warn', critica: 'chip-danger',
}

export default function Ordenes() {
  const [list, setList] = useState([])
  const [obras, setObras] = useState([])
  const [filtroObra, setFiltroObra] = useState('')

  const load = () => {
    const params = filtroObra ? { obra_id: filtroObra } : {}
    api.get('/api/ordenes/', { params }).then(r => setList(r.data))
  }
  useEffect(() => { api.get('/api/obras').then(r => setObras(r.data)) }, [])
  useEffect(() => { load() }, [filtroObra])

  const completar = async (id) => { await api.patch(`/api/ordenes/${id}/completar`); load() }
  const iniciar = async (id) => { await api.patch(`/api/ordenes/${id}/iniciar`); load() }

  const pendientes = list.filter(o => o.status !== 'completada')
  const completadas = list.filter(o => o.status === 'completada')

  return (
    <div className="max-w-6xl mx-auto animate-fade-in">
      <header className="mb-12">
        <div className="hero-eyebrow">Operaciones</div>
        <div className="flex items-end justify-between flex-wrap gap-4">
          <div>
            <h1 className="hero-title text-5xl md:text-6xl mb-3">Órdenes.</h1>
            <p className="hero-sub">Tareas activas en todas tus obras.</p>
          </div>
          <select className="input max-w-xs !rounded-full" value={filtroObra} onChange={e=>setFiltroObra(e.target.value)}>
            <option value="">Todas las obras</option>
            {obras.map(o => <option key={o.id} value={o.id}>{o.nombre}</option>)}
          </select>
        </div>
      </header>

      <div className="card mb-6">
        <div className="px-6 py-4 border-b border-border flex items-center justify-between">
          <h2 className="font-bold text-lg tracking-tight">Pendientes</h2>
          <span className="chip-navy">{pendientes.length}</span>
        </div>
        <div className="divide-y divide-border">
          {pendientes.length === 0 ? (
            <div className="py-12 text-center text-muted text-sm">Sin pendientes</div>
          ) : pendientes.map(o => {
            const obra = obras.find(ob => ob.id === o.obra_id)
            return (
              <div key={o.id} className="px-6 py-4 flex items-center gap-4 hover:bg-bone-50 transition">
                <span className={PRIORIDAD[o.prioridad]}>{o.prioridad}</span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold">{o.titulo}</div>
                  <div className="text-sm text-muted truncate mt-0.5">{o.descripcion}</div>
                  <div className="flex gap-3 mt-1.5 text-xs text-muted">
                    {obra && <span>{obra.nombre}</span>}
                    {o.fecha_limite && <span className="flex items-center gap-1"><Clock size={11}/> {o.fecha_limite}</span>}
                  </div>
                </div>
                <div className="flex gap-1.5 shrink-0">
                  {o.status === 'pendiente' && (
                    <button onClick={()=>iniciar(o.id)} className="btn-ghost text-xs">Iniciar</button>
                  )}
                  <button onClick={()=>completar(o.id)} className="btn-accent text-xs"><Check size={12}/> Completar</button>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {completadas.length > 0 && (
        <div className="card p-6">
          <h2 className="font-bold mb-4 text-sm uppercase tracking-wider text-muted">Completadas recientemente</h2>
          <ul className="space-y-2">
            {completadas.slice(0,15).map(o => (
              <li key={o.id} className="flex items-center gap-3 py-1 text-sm text-muted">
                <Check size={14} className="text-olive"/>
                <span className="line-through flex-1">{o.titulo}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
