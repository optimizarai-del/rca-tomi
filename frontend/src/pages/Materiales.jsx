import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, AlertCircle, Trash2, MapPin, ClipboardList } from 'lucide-react'
import api from '../utils/api'

export default function Materiales() {
  const nav = useNavigate()
  const [list, setList] = useState([])
  const [open, setOpen] = useState(false)
  const [filter, setFilter] = useState('todos')
  const [expanded, setExpanded] = useState(null)

  const load = () => api.get('/api/stock/').then(r => setList(r.data))
  useEffect(() => { load() }, [])

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
            <h1 className="hero-title text-5xl md:text-6xl mb-3">Materiales.</h1>
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
