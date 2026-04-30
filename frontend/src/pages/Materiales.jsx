import { useEffect, useState } from 'react'
import { Plus, AlertCircle, ArrowDown, ArrowUp, Trash2 } from 'lucide-react'
import api from '../utils/api'

export default function Materiales() {
  const [list, setList] = useState([])
  const [open, setOpen] = useState(false)
  const [filter, setFilter] = useState('todos')

  const load = () => api.get('/api/materiales/').then(r => setList(r.data))
  useEffect(() => { load() }, [])

  const filtered = filter === 'criticos'
    ? list.filter(m => (m.stock || 0) <= (m.stock_minimo || 0))
    : list

  const grupos = filtered.reduce((acc, m) => {
    (acc[m.categoria || 'otros'] ||= []).push(m)
    return acc
  }, {})

  const movimiento = async (m, tipo) => {
    const cant = prompt(`Cantidad para ${tipo}:`)
    if (!cant) return
    await api.post(`/api/materiales/${m.id}/movimientos`, { tipo, cantidad: parseFloat(cant) })
    load()
  }
  const eliminar = async (id) => {
    if (confirm('¿Eliminar material?')) { await api.delete(`/api/materiales/${id}`); load() }
  }

  const criticos = list.filter(m => (m.stock || 0) <= (m.stock_minimo || 0)).length

  return (
    <div className="max-w-7xl mx-auto animate-fade-in">
      <header className="mb-12">
        <div className="hero-eyebrow">Inventario</div>
        <div className="flex items-end justify-between flex-wrap gap-4">
          <div>
            <h1 className="hero-title text-5xl md:text-6xl mb-3">Materiales.</h1>
            <p className="hero-sub">Stock organizado por categoría con alertas inteligentes.</p>
          </div>
          <button onClick={()=>setOpen(true)} className="btn-primary"><Plus size={14}/> Nuevo material</button>
        </div>
      </header>

      <div className="flex items-center gap-1.5 bg-white border border-border rounded-full p-1 mb-6 w-fit">
        <button onClick={()=>setFilter('todos')}
          className={`px-4 py-1.5 rounded-full text-[13px] font-medium transition ${filter==='todos'?'bg-navy text-bone':'text-navy/70 hover:bg-bone-200'}`}>
          Todos <span className="opacity-60 ml-1">{list.length}</span>
        </button>
        <button onClick={()=>setFilter('criticos')}
          className={`px-4 py-1.5 rounded-full text-[13px] font-medium transition flex items-center gap-1.5 ${filter==='criticos'?'bg-danger text-white':'text-danger hover:bg-danger/10'}`}>
          <AlertCircle size={12}/> Stock crítico <span className="opacity-60 ml-1">{criticos}</span>
        </button>
      </div>

      <div className="space-y-6">
        {Object.entries(grupos).map(([cat, items]) => (
          <section key={cat} className="card p-6">
            <h2 className="hero-title text-xl capitalize mb-4">{cat}</h2>
            <div className="divide-y divide-border">
              {items.map(m => {
                const critico = (m.stock || 0) <= (m.stock_minimo || 0)
                return (
                  <div key={m.id} className="py-4 flex items-center gap-4">
                    <div className="w-10 h-10 rounded-xl bg-bone-200 grid place-items-center text-lg shrink-0">{m.icono}</div>
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold flex items-center gap-2">
                        {m.nombre}
                        {critico && <span className="chip-danger">Bajo stock</span>}
                      </div>
                      <div className="text-xs text-muted mt-0.5">
                        Stock: <span className={critico ? 'text-danger font-semibold' : 'text-navy font-semibold'}>{m.stock} {m.unidad}</span>
                        <span className="mx-2">·</span>
                        Mín: {m.stock_minimo}
                        <span className="mx-2">·</span>
                        ${m.precio_unitario?.toLocaleString() || 0}/{m.unidad}
                      </div>
                    </div>
                    <div className="flex gap-1.5 shrink-0">
                      <button onClick={()=>movimiento(m,'ingreso')} className="btn-ghost text-xs">
                        <ArrowDown size={12}/> Ingreso
                      </button>
                      <button onClick={()=>movimiento(m,'consumo')} className="btn-ghost text-xs">
                        <ArrowUp size={12}/> Consumo
                      </button>
                      <button onClick={()=>eliminar(m.id)} className="text-muted/60 hover:text-danger p-2">
                        <Trash2 size={14}/>
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          </section>
        ))}
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
        <div className="flex gap-2 justify-end pt-2">
          <button type="button" onClick={onClose} className="btn-ghost">Cancelar</button>
          <button className="btn-primary">Crear</button>
        </div>
      </form>
    </div>
  )
}
