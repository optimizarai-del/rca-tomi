import { useEffect, useState } from 'react'
import { AlertCircle } from 'lucide-react'
import api from '../utils/api'

const TIPO_ICON = {
  avance: '◆', material_llegada: '◇', incidente: '!', inspeccion: '◉', foto: '◫', hito: '★', otro: '○',
}

export default function Feed() {
  const [list, setList] = useState([])
  const [obras, setObras] = useState([])

  useEffect(() => {
    Promise.all([
      api.get('/api/eventos/', { params: { limit: 100 } }),
      api.get('/api/obras'),
    ]).then(([e, o]) => { setList(e.data); setObras(o.data) })
  }, [])

  return (
    <div className="max-w-3xl mx-auto animate-fade-in">
      <header className="mb-12">
        <div className="hero-eyebrow">Tiempo real</div>
        <h1 className="hero-title text-5xl md:text-6xl mb-3">Actividad</h1>
        <p className="hero-sub">Cronología de todo lo que pasa en tus obras.</p>
      </header>

      <div className="card divide-y divide-border">
        {list.map(e => {
          const obra = obras.find(o => o.id === e.obra_id)
          return (
            <div key={e.id} className={`p-5 flex gap-4 ${e.es_critico ? 'bg-danger/5' : ''}`}>
              <span className={`w-9 h-9 rounded-full grid place-items-center shrink-0 text-sm ${
                e.es_critico ? 'bg-danger/15 text-danger' : 'bg-bone-200 text-navy'
              }`}>
                {TIPO_ICON[e.tipo]}
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-semibold">{e.titulo}</span>
                  {obra && <span className="chip-muted">{obra.nombre}</span>}
                  {e.es_critico && <span className="chip-danger">Crítico</span>}
                </div>
                <div className="text-sm text-muted mt-1">{e.descripcion}</div>
                <div className="text-xs text-muted/80 mt-2">
                  {new Date(e.fecha).toLocaleString()} · vía {e.canal}
                </div>
              </div>
              {e.es_critico && <AlertCircle size={16} className="text-danger shrink-0"/>}
            </div>
          )
        })}
        {list.length === 0 && (
          <div className="p-12 text-center text-muted">Sin actividad reciente.</div>
        )}
      </div>
    </div>
  )
}
