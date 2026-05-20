import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, AlertCircle, Trash2, MapPin, ClipboardList, Truck, Calendar, Check } from 'lucide-react'
import api from '../utils/api'

export default function Materiales() {
  const nav = useNavigate()
  const [list, setList] = useState([])
  const [pendientes, setPendientes] = useState([])
  const [obras, setObras] = useState([])
  const [open, setOpen] = useState(false)
  const [filter, setFilter] = useState('todos')
  const [expanded, setExpanded] = useState(null)
  const [retirar, setRetirar] = useState(null)  // { stock_material_id, ... } | null

  const load = () => Promise.all([
    api.get('/api/stock/').then(r => setList(r.data)),
    api.get('/api/stock/pendientes?dias=180&incluir_sin_fecha=true').then(r => setPendientes(r.data)),
    api.get('/api/obras').then(r => setObras(r.data)),
  ])
  useEffect(() => { load() }, [])

  const agendar = async (sid, fecha) => {
    if (!fecha) return
    await api.patch(`/api/stock/${sid}/agendar-retiro`, { fecha_retirar: fecha })
    load()
  }

  const filtered = filter === 'criticos'
    ? list.filter(m => (m.stock_total_disponible || 0) <= (m.stock_minimo || 0))
    : list

  const grupos = filtered.reduce((acc, m) => {
    (acc[m.categoria || 'otros'] ||= []).push(m)
    return acc
  }, {})

  const eliminar = async (id) => {
    if (confirm('¿Eliminar material? Se borra el stock asociado.')) {
      await api.delete(`/api/materiales/${id}`); load()
    }
  }

  const criticos = list.filter(m => (m.stock_total_disponible || 0) <= (m.stock_minimo || 0)).length
  const totalPendiente = list.reduce((acc, m) => acc + (m.stock_pendiente_retiro || 0), 0)

  return (
    <div className="max-w-7xl mx-auto animate-fade-in">
      <header className="mb-12">
        <div className="hero-eyebrow">Inventario</div>
        <div className="flex items-end justify-between flex-wrap gap-4">
          <div>
            <h1 className="hero-title text-5xl md:text-6xl mb-3">Materiales</h1>
            <p className="hero-sub">Stock multi-ubicación. Carga vía WhatsApp; visualización acá.</p>
          </div>
          <div className="flex gap-2 flex-wrap">
            <button onClick={() => nav('/presupuestos')} className="btn-ghost">
              <ClipboardList size={14}/> Presupuesto materiales
            </button>
            <button onClick={()=>setOpen(true)} className="btn-primary">
              <Plus size={14}/> Nuevo material
            </button>
          </div>
        </div>
      </header>

      <div className="flex items-center gap-1.5 bg-white border border-border rounded-full p-1 mb-6 w-fit flex-wrap">
        <button onClick={()=>setFilter('todos')}
          className={`px-4 py-1.5 rounded-full text-[13px] font-medium transition ${filter==='todos'?'bg-navy text-bone':'text-navy/70 hover:bg-bone-200'}`}>
          Todos <span className="opacity-60 ml-1">{list.length}</span>
        </button>
        <button onClick={()=>setFilter('criticos')}
          className={`px-4 py-1.5 rounded-full text-[13px] font-medium transition flex items-center gap-1.5 ${filter==='criticos'?'bg-danger text-white':'text-danger hover:bg-danger/10'}`}>
          <AlertCircle size={12}/> Stock crítico <span className="opacity-60 ml-1">{criticos}</span>
        </button>
        {totalPendiente > 0 && (
          <span className="text-xs text-muted ml-2 px-2">
            Pendiente de retiro en proveedores: <span className="text-navy font-semibold">{totalPendiente.toFixed(0)}</span>
          </span>
        )}
      </div>

      {pendientes.length > 0 && (
        <PendientesRetiroCard
          pendientes={pendientes}
          obras={obras}
          onAgendar={agendar}
          onRetirar={(p) => setRetirar(p)}
        />
      )}

      <div className="space-y-6">
        {Object.entries(grupos).map(([cat, items]) => (
          <section key={cat} className="card p-6">
            <h2 className="hero-title text-xl capitalize mb-4">{cat}</h2>

            <div className="hidden md:grid grid-cols-12 gap-3 text-[10px] uppercase tracking-wider text-muted/70 font-semibold pb-2 border-b border-border">
              <div className="col-span-4">Material</div>
              <div className="col-span-2 text-right">Depósito</div>
              <div className="col-span-2 text-right">En obras</div>
              <div className="col-span-2 text-right">Pendiente retiro</div>
              <div className="col-span-1 text-right">Total disp.</div>
              <div className="col-span-1"></div>
            </div>

            <div className="divide-y divide-border">
              {items.map(m => {
                const critico = (m.stock_total_disponible || 0) <= (m.stock_minimo || 0)
                const enDeposito = (m.ubicaciones || [])
                  .filter(u => u.ubicacion_tipo === 'deposito_propio')
                  .reduce((a, u) => a + u.cantidad, 0)
                const enObras = (m.ubicaciones || [])
                  .filter(u => u.ubicacion_tipo === 'en_obra')
                  .reduce((a, u) => a + u.cantidad, 0)
                const isOpen = expanded === m.id
                return (
                  <div key={m.id} className="py-4">
                    <div
                      className="grid grid-cols-12 gap-3 items-center cursor-pointer"
                      onClick={() => setExpanded(isOpen ? null : m.id)}
                    >
                      <div className="col-span-4 flex items-center gap-3 min-w-0">
                        <div className="w-10 h-10 rounded-xl bg-bone-200 grid place-items-center text-lg shrink-0">
                          {m.icono}
                        </div>
                        <div className="min-w-0">
                          <div className="font-semibold flex items-center gap-2 flex-wrap">
                            {m.nombre}
                            {critico && <span className="chip-danger">Bajo stock</span>}
                          </div>
                          <div className="text-xs text-muted mt-0.5">
                            mín: {m.stock_minimo} · ${m.precio_unitario?.toLocaleString() || 0}/{m.unidad}
                          </div>
                        </div>
                      </div>
                      <div className="col-span-2 text-right tabular-nums">
                        <span className={enDeposito > 0 ? 'text-navy font-semibold' : 'text-muted/50'}>{enDeposito.toFixed(0)}</span>
                        <span className="text-muted/60 text-xs ml-1">{m.unidad}</span>
                      </div>
                      <div className="col-span-2 text-right tabular-nums">
                        <span className={enObras > 0 ? 'text-navy font-semibold' : 'text-muted/50'}>{enObras.toFixed(0)}</span>
                        <span className="text-muted/60 text-xs ml-1">{m.unidad}</span>
                      </div>
                      <div className="col-span-2 text-right tabular-nums">
                        <span className={m.stock_pendiente_retiro > 0 ? 'text-leather font-semibold' : 'text-muted/50'}>
                          {(m.stock_pendiente_retiro || 0).toFixed(0)}
                        </span>
                        <span className="text-muted/60 text-xs ml-1">{m.unidad}</span>
                      </div>
                      <div className="col-span-1 text-right">
                        <span className={`font-bold ${critico ? 'text-danger' : 'text-navy'}`}>
                          {(m.stock_total_disponible || 0).toFixed(0)}
                        </span>
                      </div>
                      <div className="col-span-1 flex justify-end">
                        <button
                          onClick={(e) => { e.stopPropagation(); eliminar(m.id) }}
                          className="text-muted/60 hover:text-danger p-2"
                          title="Eliminar"
                        >
                          <Trash2 size={14}/>
                        </button>
                      </div>
                    </div>

                    {isOpen && (m.ubicaciones?.length > 0) && (
                      <div className="mt-3 ml-13 pl-4 border-l-2 border-bone-200 space-y-1">
                        {m.ubicaciones.filter(u => u.cantidad > 0).map((u, i) => (
                          <div key={i} className="flex items-center gap-2 text-xs text-muted">
                            <MapPin size={11} className={
                              u.ubicacion_tipo === 'en_obra' ? 'text-olive' :
                              u.ubicacion_tipo === 'comprado_no_retirado' ? 'text-leather' :
                              'text-navy/60'
                            }/>
                            <span className="font-medium text-navy/80">{u.ubicacion_nombre}</span>
                            <span className="text-muted/70 capitalize">
                              ({u.ubicacion_tipo.replace(/_/g, ' ')})
                            </span>
                            <span className="ml-auto tabular-nums font-semibold text-navy">
                              {u.cantidad.toFixed(0)} {m.unidad}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </section>
        ))}
        {list.length === 0 && (
          <div className="card p-12 text-center text-muted">
            Sin materiales cargados todavía.
          </div>
        )}
      </div>

      {open && <NewMaterialModal onClose={()=>setOpen(false)} onSaved={()=>{ setOpen(false); load() }}/>}
      {retirar && (
        <MarcarRetiradoModal
          pendiente={retirar}
          obras={obras}
          onClose={() => setRetirar(null)}
          onSaved={() => { setRetirar(null); load() }}
        />
      )}
    </div>
  )
}

// ─── Sprint 14: Card de pendientes de retiro ──────────────────────────────

function PendientesRetiroCard({ pendientes, obras, onAgendar, onRetirar }) {
  const today = new Date(); today.setHours(0,0,0,0)
  const tag = (p) => {
    if (!p.fecha_retirar) return { cls: 'chip-muted', txt: 'sin fecha' }
    const f = new Date(p.fecha_retirar)
    const d = Math.round((f - today) / 86400000)
    if (d < 0) return { cls: 'chip-danger', txt: `vencido (-${-d}d)` }
    if (d === 0) return { cls: 'chip-warn', txt: 'HOY' }
    if (d === 1) return { cls: 'chip-warn', txt: 'mañana' }
    if (d <= 7) return { cls: 'chip-navy', txt: `en ${d}d` }
    return { cls: 'chip-olive', txt: `en ${d}d` }
  }

  return (
    <section className="card p-6 mb-6">
      <div className="flex items-center gap-2 mb-4">
        <Truck size={18} className="text-leather"/>
        <h2 className="hero-title text-xl">Pendientes de retiro</h2>
        <span className="text-xs text-muted ml-2">{pendientes.length} compras facturadas, mercadería en el proveedor.</span>
      </div>
      <div className="divide-y divide-border">
        {pendientes.map(p => {
          const t = tag(p)
          return (
            <div key={p.stock_material_id} className="py-3 flex items-center gap-3 flex-wrap">
              <div className="flex-1 min-w-0">
                <div className="font-semibold flex items-center gap-2 flex-wrap">
                  {p.material_nombre}
                  <span className={t.cls}>{t.txt}</span>
                </div>
                <div className="text-xs text-muted mt-0.5">
                  {p.cantidad.toFixed(0)} {p.unidad}
                  {p.proveedor_nombre && <> · {p.proveedor_nombre}</>}
                  {p.fecha_retirar && <> · {p.fecha_retirar}</>}
                </div>
              </div>
              <label className="flex items-center gap-1.5 text-xs">
                <Calendar size={12} className="text-muted"/>
                <input
                  type="date"
                  defaultValue={p.fecha_retirar || ''}
                  onBlur={e => {
                    if (e.target.value && e.target.value !== p.fecha_retirar) {
                      onAgendar(p.stock_material_id, e.target.value)
                    }
                  }}
                  className="input !py-1.5 !text-xs !w-auto"
                />
              </label>
              <button onClick={() => onRetirar(p)} className="btn-primary text-xs">
                <Check size={12}/> Marcar retirado
              </button>
            </div>
          )
        })}
      </div>
    </section>
  )
}

function MarcarRetiradoModal({ pendiente, obras, onClose, onSaved }) {
  const [form, setForm] = useState({
    cantidad: pendiente.cantidad,
    fecha_retiro: new Date().toISOString().slice(0, 10),
    forma_pago: 'TRANSFERENCIA',
    en_negro: false,
    destino_tipo: 'deposito_propio',
    destino_obra_id: '',
    notas: '',
  })
  const [saving, setSaving] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    if (form.cantidad <= 0) return alert('Cantidad debe ser > 0')
    if (form.cantidad > pendiente.cantidad) {
      return alert(`Máximo disponible: ${pendiente.cantidad}`)
    }
    setSaving(true)
    try {
      const payload = {
        cantidad: Number(form.cantidad),
        fecha_retiro: form.fecha_retiro,
        forma_pago: form.forma_pago,
        en_negro: form.en_negro,
        destino_tipo: form.destino_tipo,
        destino_obra_id: form.destino_tipo === 'en_obra' ? Number(form.destino_obra_id) : null,
        notas: form.notas || null,
      }
      await api.post(`/api/stock/${pendiente.stock_material_id}/retirar`, payload)
      onSaved()
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al registrar retiro')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-navy/30 backdrop-blur-sm grid place-items-center z-50 p-4 animate-fade-in" onClick={onClose}>
      <form onClick={e=>e.stopPropagation()} onSubmit={submit} className="card w-full max-w-lg p-8 space-y-4 shadow-lift animate-scale-in">
        <h2 className="hero-title text-2xl">Marcar retirado</h2>
        <div className="text-sm text-muted">
          {pendiente.material_nombre} · {pendiente.proveedor_nombre || 'proveedor'}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Cantidad retirada</label>
            <input className="input" type="number" step="any" min="0.01" max={pendiente.cantidad}
              value={form.cantidad} onChange={e=>setForm({...form, cantidad:e.target.value})} required/>
            <div className="text-xs text-muted mt-1">de {pendiente.cantidad.toFixed(0)} {pendiente.unidad}</div>
          </div>
          <div>
            <label className="label">Fecha retiro</label>
            <input className="input" type="date"
              value={form.fecha_retiro} onChange={e=>setForm({...form, fecha_retiro:e.target.value})} required/>
          </div>
          <div>
            <label className="label">Forma de pago</label>
            <select className="input" value={form.forma_pago} onChange={e=>setForm({...form, forma_pago:e.target.value})}>
              <option value="EFECTIVO">Efectivo</option>
              <option value="TRANSFERENCIA">Transferencia</option>
              <option value="CHEQUE_PROPIO">Cheque propio</option>
              <option value="CHEQUE_TERCERO">Cheque tercero</option>
              <option value="DEPOSITO_BANCARIO">Depósito bancario</option>
            </select>
          </div>
          <div>
            <label className="label">Régimen</label>
            <div className="flex items-center gap-3 pt-2">
              <label className="flex items-center gap-1.5 text-sm cursor-pointer">
                <input type="radio" checked={!form.en_negro} onChange={()=>setForm({...form, en_negro:false})}/>
                Blanco
              </label>
              <label className="flex items-center gap-1.5 text-sm cursor-pointer">
                <input type="radio" checked={form.en_negro} onChange={()=>setForm({...form, en_negro:true})}/>
                Negro
              </label>
            </div>
          </div>
          <div>
            <label className="label">Destino</label>
            <select className="input" value={form.destino_tipo}
              onChange={e=>setForm({...form, destino_tipo:e.target.value, destino_obra_id:''})}>
              <option value="deposito_propio">Depósito propio</option>
              <option value="en_obra">Directo a obra</option>
            </select>
          </div>
          {form.destino_tipo === 'en_obra' && (
            <div>
              <label className="label">Obra destino</label>
              <select className="input" value={form.destino_obra_id}
                onChange={e=>setForm({...form, destino_obra_id:e.target.value})} required>
                <option value="">— elegir —</option>
                {obras.map(o => <option key={o.id} value={o.id}>{o.codigo} · {o.nombre}</option>)}
              </select>
            </div>
          )}
        </div>

        <div>
          <label className="label">Notas (opcional)</label>
          <input className="input" value={form.notas} onChange={e=>setForm({...form, notas:e.target.value})}
            placeholder="Ej: cheque #4521 banco Galicia"/>
        </div>

        <p className="text-xs text-muted">
          La foto de factura se podrá adjuntar desde Telegram cuando esté listo el OCR (Sprint 18).
        </p>

        <div className="flex gap-2 justify-end pt-2">
          <button type="button" onClick={onClose} className="btn-ghost">Cancelar</button>
          <button className="btn-primary" disabled={saving}>
            <Check size={14}/> {saving ? 'Guardando…' : 'Registrar retiro'}
          </button>
        </div>
      </form>
    </div>
  )
}

function NewMaterialModal({ onClose, onSaved }) {
  const [form, setForm] = useState({
    nombre: '', categoria: 'cemento', unidad: 'bolsa', stock: 0, stock_minimo: 0, precio_unitario: 0, icono: '📦',
  })
  const submit = async (e) => {
    e.preventDefault()
    await api.post('/api/materiales/', {
      ...form,
      stock: parseFloat(form.stock)||0,
      stock_minimo: parseFloat(form.stock_minimo)||0,
      precio_unitario: parseFloat(form.precio_unitario)||0,
    })
    onSaved()
  }
  const CATS = ['cemento','hierro','ladrillo','áridos','instalaciones','terminaciones','herramientas','otros']
  return (
    <div className="fixed inset-0 bg-navy/30 backdrop-blur-sm grid place-items-center z-50 p-4 animate-fade-in" onClick={onClose}>
      <form onClick={e=>e.stopPropagation()} onSubmit={submit} className="card w-full max-w-md p-8 space-y-4 shadow-lift animate-scale-in">
        <h2 className="hero-title text-2xl">Nuevo material</h2>
        <div><label className="label">Nombre</label><input className="input" value={form.nombre} onChange={e=>setForm({...form,nombre:e.target.value})} required/></div>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="label">Categoría</label>
            <select className="input" value={form.categoria} onChange={e=>setForm({...form,categoria:e.target.value})}>
              {CATS.map(c => <option key={c}>{c}</option>)}
            </select>
          </div>
          <div><label className="label">Unidad</label><input className="input" value={form.unidad} onChange={e=>setForm({...form,unidad:e.target.value})}/></div>
          <div><label className="label">Stock inicial</label><input className="input" type="number" step="any" value={form.stock} onChange={e=>setForm({...form,stock:e.target.value})}/></div>
          <div><label className="label">Stock mínimo</label><input className="input" type="number" step="any" value={form.stock_minimo} onChange={e=>setForm({...form,stock_minimo:e.target.value})}/></div>
          <div className="col-span-2"><label className="label">Precio unitario</label><input className="input" type="number" step="any" value={form.precio_unitario} onChange={e=>setForm({...form,precio_unitario:e.target.value})}/></div>
        </div>
        <p className="text-xs text-muted">
          El stock inicial se carga en <strong>depósito propio</strong>. Movimientos posteriores (compras, retiros, consumos) van por el bot de WhatsApp.
        </p>
        <div className="flex gap-2 justify-end pt-2">
          <button type="button" onClick={onClose} className="btn-ghost">Cancelar</button>
          <button className="btn-primary">Crear</button>
        </div>
      </form>
    </div>
  )
}
