import { useEffect, useRef, useState } from 'react'
import { Bot, Send, X, RefreshCw, Sparkles, Loader2 } from 'lucide-react'
import api from '../utils/api'
import { useAuth } from '../context/AuthContext'

const SUGERENCIAS = [
  '¿Cómo va todo en general?',
  '¿Qué obras están en rojo?',
  '¿Hay materiales con stock bajo?',
  'Mostrame las órdenes pendientes',
  'Ranking de cuadrillas por XP',
]

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
        { role: 'assistant', text: data.reply, tools: data.tools_used || [] },
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
              <Message key={i} m={m} />
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

function Message({ m }) {
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
    <div className="flex flex-col items-start gap-1 max-w-[90%]">
      <div
        className={`rounded-2xl rounded-bl-md px-4 py-2.5 text-[13px] leading-relaxed whitespace-pre-wrap ${
          m.error ? 'bg-danger/10 text-danger' : 'bg-bone-100 text-navy'
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
    </div>
  )
}
