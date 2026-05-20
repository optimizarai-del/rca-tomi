import { useEffect, useState } from 'react'
import { Send, Loader2, RefreshCw, MessageSquare, AlertCircle, CheckCircle2, Clock, EyeOff } from 'lucide-react'
import api from '../utils/api'

const NOTIF_LABELS = {
  manual: 'Manual',
  agente_ia: 'Agente IA',
  slash_response: 'Slash command',
  event_logged: 'Evento WhatsApp',
  cheque_venciendo: 'Cheque venciendo',
  evento_critico: 'Evento crítico',
  resumen_semanal: 'Resumen semanal',
  asignacion_orden: 'Asignación orden',
}

const STATUS_CHIP = {
  log_only: { txt: 'Log only', cls: 'chip-muted', icon: EyeOff },
  pending: { txt: 'Pendiente', cls: 'chip-warn', icon: Clock },
  sent: { txt: 'Enviado', cls: 'chip-olive', icon: CheckCircle2 },
  failed: { txt: 'Falló', cls: 'chip-danger', icon: AlertCircle },
}

const fmtDate = (s) => s ? new Date(s).toLocaleString('es-AR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—'

export default function Mensajes() {
  const [msgs, setMsgs] = useState([])
  const [loading, setLoading] = useState(true)
  const [filterType, setFilterType] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [running, setRunning] = useState(false)
  const [lastCheck, setLastCheck] = useState(null)

  const load = async () => {
    setLoading(true)
    const params = {}
    if (filterType) params.notification_type = filterType
    if (filterStatus) params.status = filterStatus
    const r = await api.get('/api/notifications/outbound', { params })
    setMsgs(r.data)
    setLoading(false)
  }
  useEffect(() => { load() }, [filterType, filterStatus])

  const runChecks = async () => {
    setRunning(true)
    try {
      const r = await api.post('/api/notifications/check', null, {
        params: { semanal_force: true, eventos_horas: 999, cheques_dias: 30 },
      })
      setLastCheck(r.data)
      await load()
    } catch (e) {
      setLastCheck({ error: e.response?.data?.detail || 'Error' })
    } finally {
      setRunning(false)
    }
  }

  // Counts globales (sin filtros aplicados)
  const total = msgs.length
  const byStatus = {
    log_only: msgs.filter(m => m.status === 'log_only').length,
    sent: msgs.filter(m => m.status === 'sent').length,
    failed: msgs.filter(m => m.status === 'failed').length,
    pending: msgs.filter(m => m.status === 'pending').length,
  }

  return (
    <div className="max-w-7xl mx-auto animate-fade-in">
      <header className="mb-10 flex items-end justify-between gap-6 flex-wrap">
        <div>
          <div className="hero-eyebrow">Administración</div>
          <h1 className="hero-title text-5xl md:text-6xl mb-3">Mensajes</h1>
          <p className="hero-sub">Log de WhatsApp salientes (notificaciones, respuestas a slash commands, mensajes del agente IA).</p>
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="btn btn-secondary"><RefreshCw size={13}/> Refrescar</button>
          <button onClick={runChecks} disabled={running} className="btn btn-primary">
            {running ? <Loader2 size={13} className="animate-spin"/> : <Send size={13}/>}
            Correr notificaciones
          </button>
        </div>
      </header>

      {lastCheck && !lastCheck.error && (
        <div className="card p-5 mb-6 bg-olive/5 border-olive/20">
          <div className="flex items-start gap-3">
            <CheckCircle2 size={18} className="text-olive-700 shrink-0 mt-0.5"/>
            <div className="flex-1">
              <div className="text-[13px] font-semibold text-navy mb-1">
                Checks ejecutados — {lastCheck.total_sent} enviados · {lastCheck.total_skipped_dedupe} deduplicados
              </div>
              <div className="text-[11px] text-muted space-y-0.5">
                {lastCheck.details?.map(d => (
                  <div key={d.type}>
                    <span className="font-mono">{d.type}</span>: {d.sent ?? 0} sent, {d.skipped_dedupe ?? 0} dedupe
                    {d.skipped_reason && <span className="ml-2 italic">({d.skipped_reason})</span>}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
      {lastCheck?.error && (
        <div className="card p-5 mb-6 bg-danger/5 border-danger/20 text-[12px] text-danger">
          Error: {lastCheck.error}
        </div>
      )}

      <section className="grid md:grid-cols-4 gap-4 mb-8">
        <BigStat label="Total" value={total} accent="navy"/>
        <BigStat label="Log only" value={byStatus.log_only} accent="navy"/>
        <BigStat label="Enviados" value={byStatus.sent} accent="olive"/>
        <BigStat label="Fallidos" value={byStatus.failed} accent="leather"/>
      </section>

      <section className="card p-5 mb-6">
        <div className="grid md:grid-cols-3 gap-3">
          <Field label="Tipo">
            <select className="select-base" value={filterType} onChange={e => setFilterType(e.target.value)}>
              <option value="">Todos</option>
              {Object.entries(NOTIF_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </Field>
          <Field label="Estado">
            <select className="select-base" value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
              <option value="">Todos</option>
              <option value="log_only">Log only</option>
              <option value="pending">Pendiente</option>
              <option value="sent">Enviado</option>
              <option value="failed">Falló</option>
            </select>
          </Field>
        </div>
      </section>

      <section className="card overflow-hidden">
        {loading ? (
          <div className="p-10 text-center text-muted text-sm">Cargando...</div>
        ) : msgs.length === 0 ? (
          <div className="p-12 text-center">
            <MessageSquare size={32} className="mx-auto text-muted/40 mb-3"/>
            <div className="text-muted text-sm">Aún no hay mensajes salientes.</div>
            <div className="text-[11px] text-muted/70 mt-1">
              Probá correr las notificaciones automáticas o mandá un slash command vía WhatsApp.
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-[12px]">
              <thead>
                <tr className="bg-bone-100/50 text-muted uppercase text-[10px] tracking-wide">
                  <th className="text-left px-4 py-3 font-semibold">Fecha</th>
                  <th className="text-left px-4 py-3 font-semibold">Destinatario</th>
                  <th className="text-left px-4 py-3 font-semibold">Tipo</th>
                  <th className="text-left px-4 py-3 font-semibold">Mensaje</th>
                  <th className="text-left px-4 py-3 font-semibold">Provider</th>
                  <th className="text-left px-4 py-3 font-semibold">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50">
                {msgs.map(m => {
                  const st = STATUS_CHIP[m.status] || STATUS_CHIP.pending
                  const Icon = st.icon
                  return (
                    <tr key={m.id} className="hover:bg-bone-100/30 transition">
                      <td className="px-4 py-3 whitespace-nowrap text-muted text-[11px]">{fmtDate(m.created_at)}</td>
                      <td className="px-4 py-3 whitespace-nowrap font-mono text-navy/80 text-[11px]">{m.destinatario}</td>
                      <td className="px-4 py-3 whitespace-nowrap text-[11px]">
                        <span className="text-muted">{NOTIF_LABELS[m.notification_type] || m.notification_type || '—'}</span>
                      </td>
                      <td className="px-4 py-3 max-w-md">
                        <div className="text-navy line-clamp-2 whitespace-pre-line text-[11px] leading-snug" title={m.mensaje}>
                          {m.mensaje}
                        </div>
                        {m.error && (
                          <div className="text-[10px] text-danger mt-0.5">⚠️ {m.error.slice(0, 80)}</div>
                        )}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-muted text-[10px] font-mono">{m.provider}</td>
                      <td className="px-4 py-3">
                        <span className={`chip ${st.cls} text-[10px] inline-flex items-center gap-1`}>
                          <Icon size={10}/> {st.txt}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}

function BigStat({ label, value, accent = 'navy' }) {
  const cls = { navy: 'text-navy', olive: 'text-olive-700', leather: 'text-leather' }[accent]
  return (
    <div className="card p-5">
      <div className="text-[10px] uppercase tracking-[0.18em] text-muted font-semibold mb-2">{label}</div>
      <div className={`text-3xl font-bold tracking-tight ${cls}`}>{value}</div>
    </div>
  )
}

function Field({ label, children }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-[10px] uppercase tracking-wide text-muted font-semibold">{label}</span>
      {children}
    </label>
  )
}
