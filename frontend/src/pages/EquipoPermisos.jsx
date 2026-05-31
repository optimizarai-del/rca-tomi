import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Save, Check } from 'lucide-react'
import api from '../utils/api'

const SECCION_LABELS = {
  obras: 'Obras',
  ordenes: 'Órdenes',
  feed: 'Actividad',
  requerimientos: 'Requerimientos',
  cuadrillas: 'Cuadrillas',
  materiales: 'Materiales',
  presupuestos: 'Presupuestos',
  proveedores: 'Proveedores',
  finanzas: 'Finanzas',
  movimientos: 'Movimientos',
  aportes: 'Aportes',
  comprobantes: 'Comprobantes',
  consolidacion: 'Consolidación',
  tickets_ocr: 'Tickets OCR',
  clientes: 'Clientes',
  socios: 'Socios',
  equipo: 'Usuarios',
  mensajes: 'Mensajes',
}

const GRUPOS = {
  General: ['obras', 'ordenes', 'feed', 'requerimientos'],
  Recursos: ['cuadrillas', 'materiales', 'presupuestos', 'proveedores'],
  Finanzas: ['finanzas', 'movimientos', 'aportes', 'comprobantes', 'consolidacion', 'tickets_ocr', 'clientes', 'socios'],
  Administración: ['equipo', 'mensajes'],
}

export default function EquipoPermisos() {
  const { uid } = useParams()
  const nav = useNavigate()
  const [target, setTarget] = useState(null)
  const [permisos, setPermisos] = useState(null)
  const [obras, setObras] = useState([])
  const [allObras, setAllObras] = useState(true)
  const [obrasSeleccionadas, setObrasSeleccionadas] = useState(new Set())
  const [permitidas, setPermitidas] = useState(new Set())
  const [saving, setSaving] = useState(false)
  const [savedAt, setSavedAt] = useState(null)

  const load = async () => {
    const [u, p, o] = await Promise.all([
      api.get(`/api/users/`),
      api.get(`/api/users/${uid}/permisos`),
      api.get('/api/obras'),
    ])
    setTarget(u.data.find((x) => x.id === Number(uid)))
    setPermisos(p.data)
    setObras(o.data)
    setPermitidas(new Set(p.data.secciones_permitidas))
    if (p.data.obras_visibles_ids === null) {
      setAllObras(true)
      setObrasSeleccionadas(new Set())
    } else {
      setAllObras(false)
      setObrasSeleccionadas(new Set(p.data.obras_visibles_ids))
    }
  }

  useEffect(() => {
    load()
  }, [uid])

  const toggleSeccion = (sec) => {
    const nuevo = new Set(permitidas)
    nuevo.has(sec) ? nuevo.delete(sec) : nuevo.add(sec)
    setPermitidas(nuevo)
  }

  const toggleObra = (oid) => {
    const nuevo = new Set(obrasSeleccionadas)
    nuevo.has(oid) ? nuevo.delete(oid) : nuevo.add(oid)
    setObrasSeleccionadas(nuevo)
  }

  const guardar = async () => {
    setSaving(true)
    try {
      const payload = {
        secciones_permitidas: [...permitidas],
        obras_visibles_ids: allObras ? null : [...obrasSeleccionadas],
      }
      const r = await api.put(`/api/users/${uid}/permisos`, payload)
      setPermisos(r.data)
      setSavedAt(new Date())
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al guardar')
    } finally {
      setSaving(false)
    }
  }

  if (!permisos || !target) {
    return <div className="p-8 text-muted">Cargando…</div>
  }

  return (
    <div className="max-w-4xl mx-auto animate-fade-in">
      <header className="mb-10">
        <button onClick={() => nav('/equipo')} className="btn-ghost mb-4 text-sm">
          <ArrowLeft size={14} /> Volver
        </button>
        <div className="hero-eyebrow">Permisos</div>
        <h1 className="hero-title text-4xl md:text-5xl mb-2">
          {target.name} {target.last_name || ''}
        </h1>
        <p className="hero-sub">
          {target.email} · rol <strong>{target.role}</strong>
        </p>
        <p className="text-xs text-muted/70 mt-3">
          Los admins (super_admin / admin / admin_finanzas) tienen bypass — los permisos abajo
          solo aplican a roles operativos (supervisor, usuario_bot).
        </p>
      </header>

      <section className="card p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Secciones accesibles</h2>
        <div className="grid md:grid-cols-2 gap-6">
          {Object.entries(GRUPOS).map(([grupo, secs]) => (
            <div key={grupo}>
              <div className="section-label !mt-0 mb-2">{grupo}</div>
              <div className="space-y-1.5">
                {secs.map((sec) => (
                  <label
                    key={sec}
                    className="flex items-center gap-2 text-sm cursor-pointer hover:bg-bone-200/40 px-2 py-1.5 rounded-lg"
                  >
                    <input
                      type="checkbox"
                      checked={permitidas.has(sec)}
                      onChange={() => toggleSeccion(sec)}
                      className="rounded"
                    />
                    {SECCION_LABELS[sec] || sec}
                  </label>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="card p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Obras visibles</h2>
        <label className="flex items-center gap-2 text-sm mb-3 cursor-pointer">
          <input
            type="checkbox"
            checked={allObras}
            onChange={(e) => setAllObras(e.target.checked)}
            className="rounded"
          />
          <strong>Ver todas las obras</strong> (sin restricción)
        </label>

        {!allObras && (
          <div className="border-l-2 border-bone-300 pl-4 space-y-1.5 mt-3">
            <div className="text-xs text-muted mb-2">
              Seleccioná las obras que este usuario puede ver:
            </div>
            {obras.map((o) => (
              <label
                key={o.id}
                className="flex items-center gap-2 text-sm cursor-pointer hover:bg-bone-200/40 px-2 py-1.5 rounded-lg"
              >
                <input
                  type="checkbox"
                  checked={obrasSeleccionadas.has(o.id)}
                  onChange={() => toggleObra(o.id)}
                  className="rounded"
                />
                <span className="font-medium">{o.codigo}</span>
                <span className="text-muted">·</span>
                <span>{o.nombre}</span>
              </label>
            ))}
            {obras.length === 0 && <div className="text-xs text-muted">No hay obras cargadas</div>}
          </div>
        )}
      </section>

      <div className="flex items-center gap-3 justify-end">
        {savedAt && (
          <span className="text-xs text-muted flex items-center gap-1">
            <Check size={12} /> Guardado {savedAt.toLocaleTimeString()}
          </span>
        )}
        <button onClick={guardar} disabled={saving} className="btn-primary">
          <Save size={14} /> {saving ? 'Guardando…' : 'Guardar cambios'}
        </button>
      </div>
    </div>
  )
}
