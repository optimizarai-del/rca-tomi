import { useEffect, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Camera, Upload, Check, X, FileText, Loader2, AlertCircle, Trash2,
} from 'lucide-react'
import api from '../utils/api'

const ESTADOS = [
  { v: 'pendiente', l: 'Pendientes' },
  { v: 'confirmado', l: 'Confirmados' },
  { v: 'rechazado', l: 'Rechazados' },
  { v: 'error', l: 'Con error' },
]

export default function OcrPendientes() {
  const nav = useNavigate()
  const [tickets, setTickets] = useState(null)
  const [estado, setEstado] = useState('pendiente')
  const [obras, setObras] = useState([])
  const [proveedores, setProveedores] = useState([])
  const [openUpload, setOpenUpload] = useState(false)
  const [seleccionado, setSeleccionado] = useState(null)

  const load = () => Promise.all([
    api.get(`/api/ocr-tickets?estado=${estado}`).then(r => setTickets(r.data)),
    api.get('/api/obras').then(r => setObras(r.data)),
    api.get('/api/proveedores?incluir_inactivos=true').then(r => setProveedores(r.data)),
  ])
  useEffect(() => { load() }, [estado])

  return (
    <div className="max-w-6xl mx-auto animate-fade-in">
      <header className="mb-10 flex items-end justify-between gap-4 flex-wrap">
        <div>
          <div className="hero-eyebrow">OCR · Claude Vision</div>
          <h1 className="hero-title text-5xl md:text-6xl mb-2">Tickets OCR</h1>
          <p className="hero-sub">
            Borradores extraídos de fotos de facturas. Cuando confirmás un ticket,
            se crea el Comprobante + Movimiento de obra automáticamente.
          </p>
        </div>
        <button onClick={() => setOpenUpload(true)} className="btn-primary">
          <Upload size={14}/> Subir foto
        </button>
      </header>

      <div className="flex gap-2 text-xs mb-5">
        {ESTADOS.map(e => (
          <button
            key={e.v}
            onClick={() => setEstado(e.v)}
            className={`px-3 py-1.5 rounded-full border transition ${
              estado === e.v ? 'bg-navy text-bone border-navy' : 'border-border text-muted hover:text-navy'
            }`}
          >
            {e.l}
          </button>
        ))}
      </div>

      {tickets === null && <div className="text-muted text-sm">Cargando…</div>}
      {tickets && tickets.length === 0 && (
        <div className="card p-10 text-center text-muted text-sm">
          No hay tickets en estado "{estado}".
        </div>
      )}

      <div className="space-y-3">
        {tickets?.map(t => (
          <TicketCard
            key={t.id}
            t={t}
            obras={obras}
            proveedores={proveedores}
            isOpen={seleccionado === t.id}
            onToggle={() => setSeleccionado(seleccionado === t.id ? null : t.id)}
            onChanged={load}
          />
        ))}
      </div>

      {openUpload && (
        <UploadModal
          onClose={() => setOpenUpload(false)}
          onSaved={(tid) => { setOpenUpload(false); setEstado('pendiente'); setTimeout(() => setSeleccionado(tid), 200) }}
        />
      )}
    </div>
  )
}

function TicketCard({ t, obras, proveedores, isOpen, onToggle, onChanged }) {
  const r = t.resultado
  const total = r?.total || 0
  const estadoChip = {
    pendiente: 'chip-warn',
    confirmado: 'chip-olive',
    rechazado: 'chip-muted',
    error: 'chip-danger',
  }[t.estado] || 'chip-muted'

  const [obraId, setObraId] = useState('')
  const [proveedorId, setProveedorId] = useState('')
  const [esVenta, setEsVenta] = useState(false)
  const [legalidad, setLegalidad] = useState('blanco')
  const [medioPago, setMedioPago] = useState('TRANSFERENCIA')
  const [estadoCobroPago, setEstadoCobroPago] = useState('pendiente')
  const [enviando, setEnviando] = useState(false)

  const confirmar = async () => {
    if (!obraId) return alert('Elegí una obra')
    setEnviando(true)
    try {
      await api.post(`/api/ocr-tickets/${t.id}/confirmar`, {
        obra_id: Number(obraId),
        proveedor_id: proveedorId ? Number(proveedorId) : null,
        es_venta: esVenta,
        categoria_egreso: 'MATERIALES',
        legalidad,
        medio_pago: medioPago,
        cobro_pago_estado: estadoCobroPago,
      })
      onChanged()
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al confirmar')
    } finally {
      setEnviando(false)
    }
  }

  const rechazar = async () => {
    if (!confirm('¿Rechazar este ticket?')) return
    await api.post(`/api/ocr-tickets/${t.id}/rechazar`)
    onChanged()
  }

  const borrar = async () => {
    if (!confirm('¿Borrar definitivamente?')) return
    await api.delete(`/api/ocr-tickets/${t.id}`)
    onChanged()
  }

  return (
    <div className="card p-0 overflow-hidden">
      <button onClick={onToggle} className="w-full p-4 text-left flex items-center gap-3 hover:bg-bone-100/40">
        <FileText size={18} className="text-navy/60 shrink-0"/>
        <div className="flex-1 min-w-0">
          <div className="font-semibold flex items-center gap-2 flex-wrap">
            #{t.id} {r?.proveedor_nombre || '(sin proveedor)'}
            <span className={`${estadoChip} text-[10px]`}>{t.estado}</span>
            <span className="text-xs text-muted">modelo: {t.model_used || '—'}</span>
          </div>
          <div className="text-xs text-muted mt-0.5">
            {r?.tipo_documento && <>{r.tipo_documento} · </>}
            {r?.nro_comprobante && <>{r.nro_comprobante} · </>}
            {r?.fecha_emision && <>{r.fecha_emision} · </>}
            TOTAL ${total.toLocaleString()}
          </div>
        </div>
      </button>

      {isOpen && (
        <div className="border-t border-border p-5 grid md:grid-cols-2 gap-5 bg-bone-100/20">
          {/* Imagen */}
          <div>
            <div className="text-[10px] uppercase tracking-wider text-muted font-semibold mb-2">Imagen original</div>
            {t.imagen_url_cached ? (
              <img src={t.imagen_url_cached} alt="ticket" className="rounded-xl border border-border max-h-[400px] object-contain"/>
            ) : (
              <div className="card p-6 text-center text-muted text-xs">Sin imagen cacheada (URL de Telegram expirada).</div>
            )}
          </div>

          {/* Detalle parseado */}
          <div className="space-y-3">
            <div className="text-[10px] uppercase tracking-wider text-muted font-semibold">Datos extraídos</div>
            {r?.items?.length > 0 && (
              <div className="card p-3">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-muted uppercase text-[9px] tracking-wider">
                      <th className="text-left">Descripción</th>
                      <th className="text-right">Cant.</th>
                      <th className="text-right">P.U.</th>
                      <th className="text-right">Subt.</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/40">
                    {r.items.map((it, i) => (
                      <tr key={i}>
                        <td className="py-1 truncate max-w-[120px]" title={it.descripcion}>{it.descripcion}</td>
                        <td className="py-1 text-right">{it.cantidad}</td>
                        <td className="py-1 text-right">${it.precio_unitario}</td>
                        <td className="py-1 text-right font-semibold">${it.subtotal}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="grid grid-cols-2 gap-2 text-xs">
              <Field label="Neto gravado" value={r?.neto_gravado ? `$${r.neto_gravado.toLocaleString()}` : '—'}/>
              <Field label="IVA 21%" value={r?.iva_21 ? `$${r.iva_21.toLocaleString()}` : '—'}/>
              <Field label="IVA 10.5%" value={r?.iva_105 ? `$${r.iva_105.toLocaleString()}` : '—'}/>
              <Field label="TOTAL" value={total ? `$${total.toLocaleString()}` : '—'} highlight/>
              <Field label="Proveedor CUIT" value={r?.proveedor_cuit || '—'}/>
            </div>

            {r?.notas && (
              <div className="card p-2 text-[11px] text-muted">
                <strong>Notas:</strong> {r.notas}
              </div>
            )}

            {t.estado === 'pendiente' && (
              <div className="space-y-2 pt-3 border-t border-border">
                <div className="text-[10px] uppercase tracking-wider text-muted font-semibold">Confirmación</div>
                <div className="grid grid-cols-2 gap-2">
                  <select className="input !text-xs !py-1.5" value={obraId} onChange={e => setObraId(e.target.value)}>
                    <option value="">— elegí obra —</option>
                    {obras.map(o => <option key={o.id} value={o.id}>{o.codigo} · {o.nombre.slice(0, 30)}</option>)}
                  </select>
                  <select className="input !text-xs !py-1.5" value={proveedorId} onChange={e => setProveedorId(e.target.value)}>
                    <option value="">— proveedor (auto) —</option>
                    {proveedores.map(p => <option key={p.id} value={p.id}>{p.nombre}</option>)}
                  </select>
                  <select className="input !text-xs !py-1.5" value={legalidad} onChange={e => setLegalidad(e.target.value)}>
                    <option value="blanco">blanco</option>
                    <option value="negro">negro</option>
                  </select>
                  <select className="input !text-xs !py-1.5" value={medioPago} onChange={e => setMedioPago(e.target.value)}>
                    <option value="TRANSFERENCIA">Transferencia</option>
                    <option value="EFECTIVO">Efectivo</option>
                    <option value="CHEQUE_PROPIO">Cheque propio</option>
                  </select>
                  <select className="input !text-xs !py-1.5 col-span-2" value={estadoCobroPago} onChange={e => setEstadoCobroPago(e.target.value)}>
                    <option value="pendiente">pendiente</option>
                    <option value="pagado">pagado</option>
                    <option value="cobrado">cobrado (si es venta)</option>
                  </select>
                </div>
                <label className="flex items-center gap-1.5 text-xs text-muted">
                  <input type="checkbox" checked={esVenta} onChange={e => setEsVenta(e.target.checked)} className="rounded"/>
                  Es ingreso (venta) — default es egreso
                </label>
                <div className="flex gap-2 justify-end">
                  <button onClick={rechazar} className="btn-ghost text-xs"><X size={12}/> Rechazar</button>
                  <button onClick={confirmar} disabled={enviando || !obraId} className="btn-primary">
                    {enviando ? <Loader2 size={12} className="animate-spin"/> : <Check size={12}/>}
                    Confirmar
                  </button>
                </div>
              </div>
            )}

            {t.estado === 'confirmado' && (
              <div className="card p-3 text-xs bg-olive/10 border-olive/30">
                ✅ Confirmado · Comprobante #{t.comprobante_id} · Movimiento #{t.movimiento_obra_id}
              </div>
            )}

            {t.estado === 'error' && t.error_msg && (
              <div className="card p-3 text-xs bg-danger/10 border-danger/30">
                <AlertCircle size={12} className="inline mr-1"/> {t.error_msg}
              </div>
            )}

            <button onClick={borrar} className="text-muted/60 hover:text-danger text-xs flex items-center gap-1">
              <Trash2 size={11}/> Borrar definitivamente
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function Field({ label, value, highlight }) {
  return (
    <div className={`card p-2 ${highlight ? 'border-2 border-navy/30' : ''}`}>
      <div className="text-[9px] uppercase tracking-wider text-muted font-semibold">{label}</div>
      <div className={highlight ? 'text-lg font-semibold' : 'text-sm'}>{value}</div>
    </div>
  )
}

function UploadModal({ onClose, onSaved }) {
  const [file, setFile] = useState(null)
  const [imageUrl, setImageUrl] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    setError(''); setSending(true)
    try {
      const payload = {}
      if (file) {
        const b64 = await new Promise((resolve, reject) => {
          const reader = new FileReader()
          reader.onload = () => {
            const result = reader.result.toString()
            resolve(result.split(',', 2)[1])  // quitar header data:image/...;base64,
          }
          reader.onerror = reject
          reader.readAsDataURL(file)
        })
        payload.image_base64 = b64
      } else if (imageUrl) {
        payload.image_url = imageUrl
      } else {
        throw new Error('Subí un archivo o pegá una URL.')
      }
      const r = await api.post('/api/ocr-tickets/parse-now', payload)
      onSaved(r.data.id)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Error')
      setSending(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-navy/30 backdrop-blur-sm z-50 grid place-items-center p-4 animate-fade-in" onClick={onClose}>
      <form onSubmit={submit} onClick={e => e.stopPropagation()} className="card p-6 max-w-md w-full space-y-4 shadow-lift">
        <h2 className="hero-title text-2xl">Subir foto de ticket</h2>
        <label className="card p-6 border-2 border-dashed border-border hover:border-navy cursor-pointer block text-center">
          <Camera size={26} className="mx-auto text-muted mb-2"/>
          <div className="text-sm font-medium">{file ? file.name : 'Elegí archivo (JPG/PNG)'}</div>
          <input type="file" accept="image/*" className="hidden" onChange={e => setFile(e.target.files?.[0] || null)}/>
        </label>
        <div className="text-center text-xs text-muted">— o —</div>
        <div>
          <div className="text-[10px] uppercase tracking-wider text-muted font-semibold mb-1">URL pública</div>
          <input className="input" placeholder="https://…" value={imageUrl} onChange={e => setImageUrl(e.target.value)}/>
        </div>
        {error && <div className="text-xs text-danger">{error}</div>}
        <div className="flex gap-2 justify-end">
          <button type="button" onClick={onClose} className="btn-ghost">Cancelar</button>
          <button className="btn-primary" disabled={sending || (!file && !imageUrl)}>
            {sending ? <Loader2 size={13} className="animate-spin"/> : <Upload size={13}/>}
            Parsear
          </button>
        </div>
      </form>
    </div>
  )
}
