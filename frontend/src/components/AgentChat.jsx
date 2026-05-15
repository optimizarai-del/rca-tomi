import { useEffect, useRef, useState } from 'react'
import { Bot, Send, X, RefreshCw, Sparkles, Loader2, Check, XCircle, ShieldAlert } from 'lucide-react'
import api from '../utils/api'
import { useAuth } from '../context/AuthContext'

const SUGERENCIAS = [
  '¿Cómo va todo en general?',
  '¿Qué obras están en rojo?',
  '¿Hay materiales con stock bajo?',
  'Mostrame las órdenes pendientes',
  'Ranking de cuadrillas por XP',
]

// Cuántas tools sensibles existen y qué nombre amigable mostrar.
// Si el backend agrega tools nuevas, el preview JSON sigue funcionando como fallback.
const TOOL_LABELS = {
  registrar_movimiento: 'Registrar movimiento financiero',
  registrar_aporte_socio: 'Registrar aporte de socio',
  registrar_devolucion_aporte: 'Registrar devolución de aporte',
  cargar_comprobante: 'Cargar comprobante AFIP',
  crear_obra: 'Crear obra',
  crear_cliente: 'Crear cliente',
  crear_etapa: 'Crear etapa',
  cambiar_estado_etapa: 'Cambiar estado de etapa',
  crear_orden: 'Crear orden de trabajo',
  cerrar_orden: 'Cerrar orden',
  reportar_evento: 'Reportar evento',
  enviar_whatsapp: 'Enviar mensaje WhatsApp',
}

export default function AgentChat() {
  const { user } = useAuth()
  const [open, setOpen] = useState(false)
  const [msgs, setMsgs] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const scrollRef = useRef(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [msgs, loading])

  if (!user) return null

  const send = async (text) => {
    const message = (text ?? input).trim()
    if (!message || loading) return
    setInput('')
    setMsgs((m) => [...m, { role: 'user', text: message }])
    setLoading(true)
    try {
      const { data } = await api.post('/api/agent/chat', { message })
      setMsgs((m) => [
        ...m,
        {
          role: 'assistant',
          text: data.reply,
          tools: data.tools_used || [],
          pending: data.pending_actions || [],
        },
      ])
    } catch (e) {
      setMsgs((m) => [
        ...m,
        {
          role: 'assistant',
          text:
            e.response?.data?.detail ||
            'Error de conexión con el agente. Revisá el backend y la API key.',
          error: true,
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleConfirm = async (actionId, confirm) => {
    // Marcar la action como "resolviendo" para deshabilitar los botones
    setMsgs((m) =>
      m.map((msg) => ({
        ...msg,
        pending: (msg.pending || []).map((p) =>
          p.action_id === actionId ? { ...p, resolving: true } : p,
        ),
      })),
    )
    try {
      const { data } = await api.post(`/api/agent/confirm/${actionId}`, { confirm })
      // Quitar la action confirmada/cancelada de pending (ya no muestra los botones)
      setMsgs((m) =>
        m.map((msg) => ({
          ...msg,
          pending: (msg.pending || []).filter((p) => p.action_id !== actionId),
        })),
      )
      // Agregar un mensaje de resultado del agente
      let resultText
      if (data.cancelled) {
        resultText = `❌ Acción cancelada (${TOOL_LABELS[data.tool_name] || data.tool_name}).`
      } else if (data.ok) {
        resultText = `✅ Acción confirmada y ejecutada.`
        if (data.result?.movimiento_id) {
          resultText += ` Movimiento #${data.result.movimiento_id} creado.`
        }
        if (data.result?.saldo_obra_actualizado != null) {
          const saldo = data.result.saldo_obra_actualizado
          const fmt = Math.abs(saldo) >= 1e6
            ? `$${(saldo / 1e6).toFixed(2)}M`
            : Math.abs(saldo) >= 1e3
            ? `$${(saldo / 1e3).toFixed(0)}k`
            : `$${saldo.toFixed(0)}`
          resultText += ` Nuevo saldo de la obra: ${fmt}.`
        }
      } else {
        resultText = `⚠️ La acción se intentó pero falló: ${data.result?.error || 'error desconocido'}`
      }
      setMsgs((m) => [...m, { role: 'assistant', text: resultText, system: true }])
    } catch (e) {
      // Restaurar el botón al estado normal si falló la llamada
      setMsgs((m) =>
        m.map((msg) => ({
          ...msg,
          pending: (msg.pending || []).map((p) =>
            p.action_id === actionId ? { ...p, resolving: false } : p,
          ),
        })),
      )
      setMsgs((m) => [
        ...m,
        {
          role: 'assistant',
          text:
            e.response?.data?.detail ||
            'Error confirmando la acción. Probá de nuevo.',
          error: true,
        },
      ])
    }
  }

  const reset = async () => {
    try {
      await api.post('/api/agent/reset')
    } catch {}
    setMsgs([])
  }

  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <>
      {/* Floating button */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed bottom-6 right-6 z-50 flex items-center gap-2 px-5 py-3 rounded-full
                     bg-navy text-bone shadow-lift hover:bg-navy-700 active:scale-[0.97]
                     transition-all"
          title="Abrir agente operario"
        >
          <Sparkles size={16} className="text-olive-300" />
          <span className="text-[13px] font-medium tracking-tight">Operario IA</span>
        </button>
      )}

      {/* Chat panel */}
      {open && (
        <div className="fixed bottom-6 right-6 z-50 w-[400px] max-w-[calc(100vw-2rem)]
                        h-[600px] max-h-[calc(100vh-3rem)] flex flex-col
                        bg-white rounded-3xl shadow-lift border border-border/70
                        animate-fade-in overflow-hidden">
          {/* Header */}
          <div className="flex items-center gap-3 px-5 py-4 border-b border-border/60 bg-bone-100/40">
            <div className="w-9 h-9 rounded-full bg-navy text-bone grid place-items-center">
              <Bot size={16} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-[13px] font-semibold text-navy tracking-tight">
                Operario IA
              </div>
              <div className="text-[11px] text-muted">
                {loading ? 'Pensando...' : `Conectado como ${user.name}`}
              </div>
            </div>
            <button
              onClick={reset}
              className="p-2 rounded-full text-muted hover:bg-bone-200/70 hover:text-navy transition"
              title="Reiniciar conversación"
            >
              <RefreshCw size={14} />
            </button>
            <button
              onClick={() => setOpen(false)}
              className="p-2 rounded-full text-muted hover:bg-bone-200/70 hover:text-navy transition"
              title="Cerrar"
            >
              <X size={14} />
            </button>
          </div>

          {/* Messages */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
            {msgs.length === 0 && (
              <div className="space-y-4">
                <div className="text-[13px] text-muted leading-relaxed">
                  Hola {user.name}. Soy tu operario del centro de mando. Puedo
                  consultar obras, cuadrillas, materiales, proveedores, órdenes y
                  finanzas. Probá una de estas:
                </div>
                <div className="flex flex-wrap gap-2">
                  {SUGERENCIAS.map((s) => (
                    <button
                      key={s}
                      onClick={() => send(s)}
                      className="text-[12px] px-3 py-1.5 rounded-full bg-bone-100 hover:bg-bone-200/70
                                 text-navy border border-border/60 transition"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {msgs.map((m, i) => (
              <Message key={i} m={m} onConfirm={handleConfirm} />
            ))}

            {loading && (
              <div className="flex items-center gap-2 text-[12px] text-muted">
                <Loader2 size={14} className="animate-spin" />
                pensando...
              </div>
            )}
          </div>

          {/* Composer */}
          <div className="p-3 border-t border-border/60 bg-white">
            <div className="flex items-end gap-2">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={onKey}
                placeholder="Preguntale al operario..."
                rows={1}
                className="flex-1 resize-none rounded-2xl bg-bone-100/70 px-4 py-2.5
                           text-[13px] text-navy placeholder:text-muted/70
                           focus:outline-none focus:ring-4 focus:ring-navy/5
                           max-h-32"
              />
              <button
                onClick={() => send()}
                disabled={!input.trim() || loading}
                className="p-3 rounded-full bg-navy text-bone hover:bg-navy-700
                           disabled:opacity-40 disabled:cursor-not-allowed
                           active:scale-[0.95] transition"
              >
                <Send size={14} />
              </button>
            </div>
            <div className="mt-1.5 text-[10px] text-muted/70 px-2">
              Enter para enviar · Shift+Enter para nueva línea
            </div>
          </div>
        </div>
      )}
    </>
  )
}

function Message({ m, onConfirm }) {
  if (m.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] bg-navy text-bone rounded-2xl rounded-br-md px-4 py-2.5 text-[13px] leading-relaxed whitespace-pre-wrap">
          {m.text}
        </div>
      </div>
    )
  }
  return (
    <div className="flex flex-col items-start gap-2 max-w-[95%] w-full">
      <div
        className={`rounded-2xl rounded-bl-md px-4 py-2.5 text-[13px] leading-relaxed whitespace-pre-wrap max-w-[90%] ${
          m.error ? 'bg-danger/10 text-danger' : m.system ? 'bg-olive/10 text-navy' : 'bg-bone-100 text-navy'
        }`}
      >
        {m.text}
      </div>
      {m.tools?.length > 0 && (
        <div className="flex flex-wrap gap-1 px-2">
          {m.tools.map((t, i) => (
            <span
              key={i}
              className="text-[10px] px-2 py-0.5 rounded-full bg-olive/10 text-olive-700 font-mono"
            >
              {t}
            </span>
          ))}
        </div>
      )}
      {m.pending?.length > 0 &&
        m.pending.map((p) => (
          <ConfirmableAction
            key={p.action_id}
            pending={p}
            onConfirm={onConfirm}
          />
        ))}
    </div>
  )
}

function ConfirmableAction({ pending, onConfirm }) {
  const label = TOOL_LABELS[pending.tool_name] || pending.tool_name
  const previewLines = Object.entries(pending.preview || {})
    .filter(([, v]) => v !== null && v !== undefined && v !== '')
    .map(([k, v]) => [k, typeof v === 'object' ? JSON.stringify(v) : String(v)])

  return (
    <div className="w-full bg-leather/5 border border-leather/30 rounded-2xl p-4 space-y-3">
      <div className="flex items-center gap-2">
        <ShieldAlert size={14} className="text-leather shrink-0" />
        <div className="text-[12px] font-semibold tracking-tight text-navy">
          Confirmación requerida
        </div>
      </div>
      <div className="text-[12px] text-navy/80">
        <span className="font-medium">{label}</span>
        <span className="text-muted ml-1 font-mono text-[11px]">#{pending.action_id}</span>
      </div>
      {previewLines.length > 0 && (
        <div className="bg-white rounded-xl border border-border/60 px-3 py-2 space-y-0.5">
          {previewLines.map(([k, v]) => (
            <div key={k} className="flex items-baseline gap-2 text-[11px]">
              <span className="text-muted/80 uppercase tracking-wide font-medium min-w-[90px]">
                {k}
              </span>
              <span className="text-navy break-all">{v}</span>
            </div>
          ))}
        </div>
      )}
      <div className="flex gap-2 pt-1">
        <button
          onClick={() => onConfirm(pending.action_id, true)}
          disabled={pending.resolving}
          className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-full
                     bg-navy text-bone text-[12px] font-medium tracking-tight
                     hover:bg-navy-700 active:scale-[0.97]
                     disabled:opacity-50 disabled:cursor-wait transition"
        >
          {pending.resolving ? (
            <Loader2 size={12} className="animate-spin" />
          ) : (
            <Check size={12} />
          )}
          Confirmar
        </button>
        <button
          onClick={() => onConfirm(pending.action_id, false)}
          disabled={pending.resolving}
          className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-full
                     bg-bone-200/80 text-navy text-[12px] font-medium tracking-tight
                     hover:bg-bone-200 active:scale-[0.97]
                     disabled:opacity-50 disabled:cursor-wait transition"
        >
          <XCircle size={12} />
          Cancelar
        </button>
      </div>
    </div>
  )
}
