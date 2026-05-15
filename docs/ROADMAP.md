# 🗺️ Roadmap — RCA. Plataforma

> Plan de acción vivo. Última actualización: 2026-05-06.
> Rama de trabajo: `dev`. Producción: `main`.

---

## 🎯 Visión

Plataforma de gestión de obras de construcción con dos capas:

1. **Capa financiera seria** — modelo del documento *"Modelo de gestión de gastos de obra v1.0"*: clientes, régimen fiscal, etapas, movimientos (ingresos/egresos en tabla única), aportes de socios, comprobantes AFIP, retenciones, flujo de caja, descalce fiscal.
2. **Capa lúdica/operativa opcional** — cuadrillas con XP/nivel, frentes, órdenes (quests), feed de eventos. Conservada del modelo anterior, NO contamina los reportes financieros.

Ambas operadas por un **Operario IA conversacional** (Claude Sonnet 4.5 con tool-use) accesible vía chat web flotante y, en el futuro, por WhatsApp.

---

## ✅ Hecho

### Sprint 0 — Setup (cerrado)
- Clone del repo, refactor de puertos (backend 8010, frontend 5175 por choque con OPTIMIZAR).
- Scripts `setup.bat` / `setup.sh` para arrancar en otra PC en 1 comando.
- `start-backend.bat` / `start-frontend.bat` validan venv/node_modules y crean `.env`.
- Documentación: [SETUP.md](../SETUP.md) con guía PC nueva + troubleshooting.

### Sprint 1 — Operario IA (cerrado)
- Modelos `AgentSession` (historial por usuario) + `AgentAction` (audit log).
- Orchestrator con loop tool-use, Claude Sonnet 4.5, max 8 iteraciones, historial truncado a 30 mensajes.
- 11 tools de **solo lectura**: dashboard, obras, órdenes, cuadrillas, materiales, proveedores, eventos, finanzas, usuarios.
- Endpoints: `POST /api/agent/chat`, `POST /api/agent/reset`, `GET /api/agent/actions`.
- Frontend: `<AgentChat />` flotante (botón abajo-derecha) con sugerencias, indicador de tools usadas, reset de sesión.
- Permisos por rol heredados del JWT del usuario logueado.
- Persistencia de user_id por JWT `sub` claim — la sesión sobrevive entre logins.
- Fix `load_dotenv(override=True)` para vencer vars vacías del shell.
- Reload de uvicorn opcional (`RELOAD=1`) por bug en OneDrive.

### Sprint A+B — Modelo financiero (cerrado)
- **Tablas nuevas:** `regimenes_fiscales`, `clientes`, `etapas_obra`, `movimientos_obra` (central), `aportes_socios`, `comprobantes`, `retenciones_sufridas`, `notas_obra`.
- **Tablas modificadas:** `obras` (cliente_id, regimen_fiscal_id, tipo_facturacion, monto_contrato — sin `presupuesto_consumido`).
- **Tablas eliminadas:** `gastos` (reemplazada por `movimientos_obra` con `tipo=EGRESO`).
- **Enums nuevos:** TipoFacturacion (BLANCO/NEGRO/MIXTA/SIN_DEFINIR), EtapaEstado (PENDIENTE→COBRADA), TipoMovimiento (INGRESO/EGRESO), OrigenIngreso (6 valores), CategoriaEgreso (7 valores), MedioPago (efectivo/transferencia/cheque propio/cheque tercero/depósito), EstadoMovimiento (CONFIRMADO/A_REVISAR), TipoComprobante (FC_A/B, NC, ND...), EstadoFiscal, TipoRetencion. Rol nuevo `super_admin`.
- **Reglas implementadas:**
  - **R1** — saldo NO se filtra por estado (`SUM(INGRESO) - SUM(EGRESO)`).
  - **R2** — alta de aporte crea movimiento espejo INGRESO automáticamente.
  - **R3** — cheques propios "salen" en `fecha_vto_cheque` en el flujo proyectado.
  - **R4** — descalce fiscal por obra (egresos con factura > ingresos con factura).
  - **R5** — etapa pasada a COBRADA con aportes pendientes deja nota automática.
- **Routers nuevos:** `clientes`, `regimenes_fiscales`, `etapas`, `movimientos` (saldo, flujo-caja semanal, flujo-proyectado, cheques-a-vencer, descalce-fiscal), `aportes` (con devolución parcial/total), `comprobantes` (validación neto+IVA=total).
- **Agente IA:** 16 tools (5 nuevas) — `listar_clientes`, `listar_etapas`, `listar_movimientos`, `saldo_obra`, `flujo_caja_obra`, `aportes_pendientes`, `cheques_a_vencer`, `descalce_fiscal`. System prompt actualizado con contexto del modelo nuevo.
- **Frontend:**
  - HUD muestra saldo global, cheques a vencer, aportes pendientes (no más "presupuesto consumido").
  - `Finanzas.jsx` refactorizada: 4 big numbers (contratado / ingresos / egresos / saldo), alertas de aportes y cheques, breakdown por categoría y por obra, lista de movimientos con badges (FC, A_REVISAR, +/-).
  - `WorldMap.jsx` adaptada a `estado` y `monto_contrato`. Modal "Nueva obra" integra cliente + régimen fiscal + tipo de facturación.
  - `ObraDetail.jsx` toma cliente del dashboard.
- **Infra:**
  - `docker-compose.yml` para Postgres opcional (puerto 5433, evita choque con PG local).
  - `scripts/reset_db.py` — drop all + recreate + seed (funciona con SQLite o PG).
  - `.env.example` con `DATABASE_URL` para SQLite (default) o PG.
  - Seed nuevo realista: 2 obras (IDS Domingo Savio TOTAL_BLANCO $12.5M, SP San Pedro MIXTA $8.2M), 7 etapas, 13 movimientos, 1 aporte de socio + ingreso espejo, 1 cheque a vencer, 1 factura A con CAE.
- **Sistema de ramas:** `main` (estable) + `dev` (desarrollo).

---

## 🚧 En curso

> Nada activo en este momento. La rama `dev` está estable.

---

## 📋 Pendiente — orden propuesto

### Sprint 2 — Operario IA con escritura (recomendado siguiente)
**Goal:** que el agente pase de solo leer a *operar* la plataforma, con confirmación humana para acciones destructivas o financieras.

- [ ] Mecanismo genérico de **confirmación de tool-call**: tools sensibles devuelven `requires_confirmation=true` + payload preview, frontend pinta botones "Confirmar / Cancelar" en el chat.
- [ ] Tools de escritura nuevas:
  - [ ] `registrar_movimiento` (ingreso o egreso, validaciones de coherencia: cheque pide nro+banco+vto, TOTAL_BLANCO exige factura, etc.).
  - [ ] `registrar_aporte_socio` (dispara movimiento espejo automático).
  - [ ] `registrar_devolucion_aporte`.
  - [ ] `crear_etapa`, `cambiar_estado_etapa`.
  - [ ] `crear_orden`, `cerrar_orden` (suma XP a cuadrilla y usuario).
  - [ ] `reportar_evento` (avance, incidente, foto).
  - [ ] `cargar_comprobante` (datos AFIP estructurados).
  - [ ] `crear_cliente`, `crear_obra`.
  - [ ] `enviar_whatsapp` (notificación saliente — requiere integración WSP).
- [ ] Whitelist de tools que SIEMPRE piden confirmación (todo lo financiero, borrados, cambio de rol, mensajes salientes).
- [ ] Tabla `AgentAction` ya existe — extender para registrar `confirmed_by`, `confirmed_at`.
- [ ] Tests manuales: el agente NO inventa que hizo algo si la tool no fue confirmada.

### Sprint 3 — UI de gestión financiera (en paralelo a Sprint 2)
- [ ] Página dedicada **Clientes** — CRUD con régimen fiscal y obras asociadas.
- [ ] Página dedicada **Etapas** dentro de `ObraDetail` — tabla editable con drag-to-reorder de nro_etapa, cambio de estado con cascada de alertas.
- [ ] Vista **Flujo de caja** dentro de `ObraDetail`: gráfico de barras semanal + línea de saldo acumulado (recharts o nivo).
- [ ] Vista **Flujo proyectado** — incluye cheques a vencer y etapas estimadas.
- [ ] Página **Movimientos** con filtros avanzados (obra, tipo, categoría, medio de pago, fecha desde/hasta, estado, comprobante sí/no).
- [ ] Modal de **carga de movimiento** con UX progresiva: tipo → categoría/origen → medio de pago (campos condicionales: cheque pide datos extra) → comprobante opcional.
- [ ] Página **Aportes de socios** — listado con estado de devolución, botón "registrar devolución".
- [ ] Página **Comprobantes** — listado con filtros, validación de CAE.
- [ ] Reporte **Descalce fiscal** global + por obra (lo que ya devuelve el endpoint, falta UI).

### Sprint 4 — Integración WhatsApp bidireccional
- [ ] Reemplazar el parser keyword-based actual de `/api/whatsapp/inbound` por el orchestrator del agente IA. El mensaje de WhatsApp pasa al mismo `chat()` con `canal=whatsapp`.
- [ ] Adaptador para mensaje saliente (Twilio o WhatsApp Cloud API).
- [ ] Sistema de **comandos slash**: `/saldo`, `/cheques`, `/avance <obra> <%>`, `/gasto <obra> <monto> <concepto>` con foto del ticket adjunto.
- [ ] **Notificaciones automáticas push** desde el sistema:
  - [ ] Alerta cuando un cheque vence en N días.
  - [ ] Alerta cuando se registra un evento crítico (incidente).
  - [ ] Resumen semanal a admin (lunes 8 AM).
  - [ ] Aviso al capataz cuando se le asigna una orden.
- [ ] Magic links firmados para aprobaciones (gasto, factura) sin loguearse.

### Sprint 5 — Inteligencia avanzada
- [ ] **Vision IA con Claude**: tool `analizar_foto(url, contexto)` para:
  - [ ] OCR de tickets/facturas/remitos → autocompletar `Comprobante` + `MovimientoObra`.
  - [ ] Detección de cascos y elementos de seguridad en fotos de obra.
  - [ ] Estimación de avance comparando fotos del mismo frente día a día.
- [ ] **NLP multi-evento**: un mensaje largo de WhatsApp que describe varias cosas se parsea en N eventos/movimientos discretos (Claude tool-use con loop sobre extracción).
- [ ] **Asistente conversacional avanzado** `/preguntar`: tool genérica que combina varias fuentes ("¿en qué obra conviene priorizar gasto?", "¿qué cuadrilla está libre la semana próxima?").
- [ ] **Auto-asignación inteligente** de cuadrilla óptima a una orden nueva (especialidad + carga + eficiencia).

### Sprint 6 — Operacional / calidad de vida
- [ ] **Geolocalización del reporte** desde WhatsApp — confirmar que el capataz está físicamente en la obra.
- [ ] **Voice notes → transcripción** (Whisper) para capataces que prefieren hablar.
- [ ] **QR por obra** pegado en el portón → escaneo abre WhatsApp con obra preseleccionada.
- [ ] **Email-to-event** — reenviar mail al bot crea evento (útil para remitos).
- [ ] **PWA** — instalable como app de celular sin tienda.
- [ ] **API key por usuario** para integraciones externas (Excel, Sheets, n8n).
- [ ] **Multi-tenancy** — soporte para varias constructoras en el mismo deployment.

### Sprint 7 — Roles y permisos completos
- [ ] Reactivar jerarquía de roles más allá de `super_admin`:
  - [ ] `admin_finanzas` (acceso a fiscal pleno, sin RRHH).
  - [ ] `admin` (PM — todo menos finanzas detalladas).
  - [ ] `supervisor` (carga de movimientos básicos, ve sus obras).
  - [ ] `usuario_bot` (solo WhatsApp, sin web).
- [ ] Matriz de permisos por endpoint en código + tests.
- [ ] Tabla `Socio` propia (hoy se usa `User` con rol admin_finanzas como proxy para aportes).

### Sprint 8 — Producción
- [ ] Migración real a Postgres (compose ya está, falta verificar end-to-end con datos).
- [ ] Migraciones Alembic (hoy todo es `Base.metadata.create_all`).
- [ ] CI: tests de modelos + endpoints + smoke del agente.
- [ ] Deploy: Vercel (frontend) + Railway/Fly (backend) + RDS o Supabase (DB).
- [ ] Backups automáticos de la DB + storage de fotos/comprobantes (S3 o Supabase Storage).
- [ ] Monitoring básico (Sentry para errores, Plausible para uso).

---

## 🧱 Deuda técnica / pendientes menores

- [ ] Tabla `herramientas_en_obra` declarada en el doc pero no implementada (espera el módulo de patrimonio).
- [ ] El campo `User.onboarding_step` no se usa en la UI — definir si se elimina o se completa el flujo de onboarding.
- [ ] El frontend `Equipo.jsx` no tiene UI para invitar usuario con rol específico (hoy usa `Register`).
- [ ] Encoding de emojis en consola Windows (`reset_db.py` ya arreglado, revisar si hay más).
- [ ] El reload de uvicorn está apagado por bug de OneDrive — investigar si hay workaround estable.
- [ ] `seed.py` chequea si ya hay datos para no duplicar; el `reset_db.py` resuelve esto pero el flujo de "primera carga" del setup.bat puede fallar si la DB ya existe.

---

## 🔑 Decisiones técnicas tomadas

| Decisión | Razón |
|----------|-------|
| Mantener SQLAlchemy (no migrar a Prisma) | Backend Python ya funciona; cambiar ORM duplica trabajo sin beneficio claro |
| Integer PKs (no UUID del doc) | Sin breaking change en relaciones existentes; UUIDs se pueden agregar como campos públicos después |
| Eventos SQLAlchemy (no triggers PG) | Portable a SQLite, testeable, no atado a un motor |
| SQLite por default + PG opcional vía Docker | Onboarding de PC nueva sin Docker; producción con PG con 1 línea de cambio |
| Capa lúdica conservada | Diferencia visual del producto, no afecta finanzas |
| Reset total de DB (no migración de datos viejos) | Datos de prueba; el costo de migrar no se justifica |
| `super_admin` único hasta tener flujo claro de roles | Evita gating prematuro mientras itera la UI |
| Claude Sonnet 4.5 default, configurable vía `AGENT_MODEL` | Costo razonable, soporte tool-use sólido; user puede cambiar a 4.6 / Haiku |

---

## 📞 Cómo decidir qué hacer próximo

Cuando arranques la próxima sesión, mirá esta tabla y decidí:

| Si querés... | Andá a |
|--------------|--------|
| Que el agente *haga cosas* además de leer | **Sprint 2** |
| Una UI completa para gestión financiera | **Sprint 3** |
| Manejo full por WhatsApp con notificaciones | **Sprint 4** |
| OCR de tickets / Vision IA | **Sprint 5** |
| Llevar a producción real con varios usuarios | **Sprint 7 + 8** |

**Mi recomendación:** Sprint 2 primero. El cuello de botella más grande hoy es que el agente solo lee — desbloquea el valor real de la plataforma.
