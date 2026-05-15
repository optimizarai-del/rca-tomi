# 📋 Plan de Acción — RCA. Plataforma

> Plan vivo con todas las tareas detalladas por sprint.
> Última actualización: 2026-05-07
> Rama de trabajo actual: `sprint-1` (creada desde `dev`)

---

## 🧭 Estado actual

Mirando [ROADMAP.md](ROADMAP.md) + commits + código real:

| Sprint | Estado | Resumen |
|---|---|---|
| **Sprint 0 — Setup** | ✅ Cerrado | Scripts `setup.bat`/`setup.sh`, puertos 8010/5175, `.env.example` |
| **Sprint 1 — Operario IA (lectura)** | ✅ Cerrado | 16 tools de solo lectura, sesión persistente, audit log, chat flotante |
| **Sprint A+B — Modelo financiero** | ✅ Cerrado | Tablas movimientos/etapas/aportes/comprobantes, reglas R1–R5, UI Finanzas |
| **Sprint 2 — Operario IA con escritura** | 🟡 **Próximo (recomendado)** | Que el agente **opere**, no solo lea |
| **Sprint 3 — UI gestión financiera** | ⬜ Pendiente | Páginas Clientes, Etapas, Movimientos, Aportes, Comprobantes |
| **Sprint 4 — WhatsApp bidireccional** | ⬜ Pendiente | Reemplazar parser por agente + notificaciones push |
| **Sprint 5 — Inteligencia avanzada** | ⬜ Pendiente | Vision IA, OCR de tickets, NLP multi-evento |
| **Sprint 6 — QoL operativo** | ⬜ Pendiente | Geo, voice notes, QR, PWA, multi-tenancy |
| **Sprint 7 — Roles completos** | ⬜ Pendiente | Reactivar jerarquía de roles + matriz de permisos |
| **Sprint 8 — Producción** | ⬜ Pendiente | Postgres, Alembic, CI/CD, deploy, backups, monitoring |

> La rama `dev` está estable, sin trabajo en curso. Acabamos de crear `sprint-1` desde `dev`. Aclaración: el nombre `sprint-1` es histórico — en realidad arrancamos **Sprint 2** según el roadmap, porque Sprint 1 ya está cerrado. Conviene renombrar a `sprint-2-agente-escritura` antes de empezar a commitear.

---

## 🚀 Sprint 2 — Operario IA con escritura (próximo a ejecutar)

**Objetivo:** que el agente IA pase de *leer* a *operar* la plataforma con confirmación humana para acciones sensibles.

### Tareas detalladas

### 1. Mecanismo genérico de confirmación de tool-call
- Agregar al [orchestrator.py](../backend/app/agent/orchestrator.py) un flag `requires_confirmation` por tool.
- Las tools sensibles devuelven `{requires_confirmation: true, payload_preview: {...}}` en vez de ejecutar.
- Frontend ([AgentChat.jsx](../frontend/src/components/AgentChat.jsx)) detecta el flag y pinta botones "Confirmar / Cancelar" inline en el chat.
- Al confirmar, se reenvía la tool-call al backend con `confirmed: true`.

### 2. Tools de escritura nuevas (en [tools.py](../backend/app/agent/tools.py))
- [ ] `registrar_movimiento` — crea un `MovimientoObra` (INGRESO o EGRESO). Validaciones: cheque pide nro+banco+vto, TOTAL_BLANCO exige factura.
- [ ] `registrar_aporte_socio` — crea `AporteSocio` + dispara movimiento espejo (R2 ya existe en el router).
- [ ] `registrar_devolucion_aporte` — devolución parcial o total + EGRESO espejo.
- [ ] `crear_etapa` — añade `EtapaObra` con monto + fecha estimada.
- [ ] `cambiar_estado_etapa` — pasa de PENDIENTE→...→COBRADA con cascada R5.
- [ ] `crear_orden` — quest operativa (capa lúdica).
- [ ] `cerrar_orden` — suma XP a cuadrilla y usuario.
- [ ] `reportar_evento` — avance/incidente/foto en el feed.
- [ ] `cargar_comprobante` — datos AFIP estructurados con validación neto+IVA=total.
- [ ] `crear_cliente` — alta de cliente con régimen fiscal.
- [ ] `crear_obra` — alta de obra ligada a cliente.
- [ ] `enviar_whatsapp` — notificación saliente (queda stub hasta Sprint 4).

### 3. Whitelist de tools que SIEMPRE piden confirmación
- Definir `ALWAYS_CONFIRM = {"registrar_movimiento", "registrar_aporte_socio", "registrar_devolucion_aporte", "cargar_comprobante", "crear_obra", "cambiar_estado_etapa", "enviar_whatsapp", ...}`.
- Cualquier tool destructiva (delete, update de estado fiscal) entra al set.

### 4. Extender tabla `AgentAction` para audit con confirmación
- Agregar columnas `confirmed_by` (FK a users) y `confirmed_at` (datetime).
- Registrar quién confirmó cada acción sensible (ahora solo registra el user dueño de la sesión).

### 5. Tests manuales
- El agente NO inventa que hizo algo si la tool no fue confirmada.
- Tools de escritura solo se ejecutan tras confirmación explícita.
- Si el usuario cancela, queda registrado en `AgentAction` con `ok=false`.

### 6. Actualizar system prompt del agente
- Hoy dice *"Sprint actual: solo lectura"*. Cambiarlo a "podés escribir, pero las acciones sensibles requieren confirmación humana".

### 7. Frontend — UI de confirmación en chat
- Componente `<ConfirmableMessage>` con preview del payload + botones.
- Animación sutil para destacar la acción pendiente.
- Estado `pendingConfirmation` en `AgentChat.jsx`.

---

## 🎨 Sprint 3 — UI de gestión financiera (puede ir en paralelo)

**Objetivo:** dar UI a las tablas/endpoints financieros que ya existen (Sprint A+B).

### Tareas detalladas

- [ ] **Página `/clientes`** — CRUD de clientes con régimen fiscal y obras asociadas.
- [ ] **Sección "Etapas" dentro de `/obra/:id`** — tabla editable, drag-to-reorder de `nro_etapa`, cambio de estado con cascada R5.
- [ ] **Vista "Flujo de caja"** dentro de `ObraDetail` — gráfico de barras semanal + línea de saldo acumulado (recharts o nivo). Endpoint existente: `GET /api/movimientos/obra/{oid}/flujo-caja`.
- [ ] **Vista "Flujo proyectado"** — incluye cheques a vencer + etapas estimadas. Endpoint: `GET /api/movimientos/obra/{oid}/flujo-proyectado`.
- [ ] **Página `/movimientos`** — filtros (obra, tipo, categoría, medio de pago, fecha desde/hasta, estado, comprobante sí/no).
- [ ] **Modal "Nuevo movimiento"** con UX progresiva: tipo → categoría/origen → medio de pago (cheque pide datos extra) → comprobante opcional.
- [ ] **Página `/aportes`** — listado de aportes con estado de devolución, botón "registrar devolución".
- [ ] **Página `/comprobantes`** — listado con filtros, validación de CAE y estado fiscal.
- [ ] **Reporte "Descalce fiscal"** global + por obra. Endpoint: `GET /api/movimientos/descalce-fiscal`. Falta UI.
- [ ] **Refactor del Sidebar** — agregar sección "Finanzas" con sub-items (Clientes / Movimientos / Aportes / Comprobantes / Descalce).

---

## 📱 Sprint 4 — Integración WhatsApp bidireccional

- [ ] **Reemplazar parser keyword-based** de `/api/whatsapp/inbound` por el orchestrator IA. El mensaje de WhatsApp pasa por `chat()` con `canal=whatsapp`.
- [ ] **Adaptador para mensaje saliente** — Twilio o WhatsApp Cloud API.
- [ ] **Sistema de comandos slash:** `/saldo`, `/cheques`, `/avance <obra> <%>`, `/gasto <obra> <monto> <concepto>` con foto adjunta.
- [ ] **Notificaciones automáticas push:**
  - [ ] Cheque vence en N días.
  - [ ] Evento crítico (incidente).
  - [ ] Resumen semanal a admin (lunes 8 AM).
  - [ ] Aviso al capataz cuando se le asigna una orden.
- [ ] **Magic links firmados** para aprobaciones (gasto, factura) sin loguearse.

---

## 🤖 Sprint 5 — Inteligencia avanzada

- [ ] **Vision IA con Claude** — tool `analizar_foto(url, contexto)`:
  - [ ] OCR de tickets/facturas/remitos → autocompleta `Comprobante` + `MovimientoObra`.
  - [ ] Detección de cascos en fotos de obra.
  - [ ] Estimación de avance comparando fotos día a día.
- [ ] **NLP multi-evento** — un mensaje largo de WhatsApp se parsea en N eventos/movimientos discretos.
- [ ] **Asistente conversacional avanzado** `/preguntar` — combina varias fuentes ("¿en qué obra conviene priorizar gasto?").
- [ ] **Auto-asignación inteligente** de cuadrilla óptima a una orden nueva (especialidad + carga + eficiencia).

---

## 🛠️ Sprint 6 — QoL operativo

- [ ] **Geolocalización** desde WhatsApp — confirmar que el capataz está físicamente en la obra.
- [ ] **Voice notes → transcripción** (Whisper).
- [ ] **QR por obra** pegado en el portón → escaneo abre WhatsApp con obra preseleccionada.
- [ ] **Email-to-event** — reenviar mail al bot crea evento.
- [ ] **PWA** — instalable como app de celular sin tienda.
- [ ] **API key por usuario** para integraciones externas (Excel, Sheets, n8n).
- [ ] **Multi-tenancy** — varias constructoras en el mismo deployment.

---

## 🔐 Sprint 7 — Roles y permisos completos

- [ ] Reactivar jerarquía de roles (hoy todos son `super_admin`):
  - [ ] `admin_finanzas` (fiscal pleno, sin RRHH).
  - [ ] `admin` (PM — todo menos finanzas detalladas).
  - [ ] `supervisor` (carga básica, ve sus obras).
  - [ ] `usuario_bot` (solo WhatsApp, sin web).
- [ ] **Matriz de permisos por endpoint** en código + tests.
- [ ] **Tabla `Socio` propia** (hoy se usa `User` con rol admin_finanzas como proxy).

---

## 🚢 Sprint 8 — Producción

- [ ] Migración real a Postgres (`docker-compose.yml` ya está, falta verificar end-to-end).
- [ ] **Migraciones Alembic** (hoy todo es `Base.metadata.create_all`).
- [ ] **CI**: tests de modelos + endpoints + smoke del agente.
- [ ] **Deploy:** Vercel (frontend) + Railway/Fly (backend) + RDS o Supabase (DB).
- [ ] **Backups automáticos** + storage de fotos/comprobantes (S3 o Supabase).
- [ ] **Monitoring** (Sentry para errores, Plausible para uso).

---

## 🧹 Deuda técnica menor (a limpiar a lo largo de los sprints)

- [ ] Tabla `herramientas_en_obra` declarada en el doc pero no implementada.
- [ ] `User.onboarding_step` no se usa en la UI — definir si se elimina o se completa.
- [ ] `Equipo.jsx` no tiene UI para invitar usuario con rol específico (hoy usa `Register`).
- [ ] Encoding de emojis en consola Windows.
- [ ] Reload de uvicorn apagado por bug de OneDrive.
- [ ] `seed.py` tiene check anti-duplicado que rompe el flujo de "primera carga" si la DB ya existe.

---

## 📞 Cómo decidir qué hacer próximo

| Si querés... | Andá a |
|--------------|--------|
| Que el agente *haga cosas* además de leer | **Sprint 2** |
| Una UI completa para gestión financiera | **Sprint 3** |
| Manejo full por WhatsApp con notificaciones | **Sprint 4** |
| OCR de tickets / Vision IA | **Sprint 5** |
| Llevar a producción real con varios usuarios | **Sprint 7 + 8** |

**Recomendación del roadmap:** Sprint 2 primero. El cuello de botella más grande hoy es que el agente solo lee — desbloquea el valor real de la plataforma.
