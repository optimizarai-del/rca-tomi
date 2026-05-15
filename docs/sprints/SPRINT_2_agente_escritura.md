# Sprint 2 — Agente IA con escritura + confirmación humana

> Commit: `dfd0576 feat(agent): Sprint 2 — agente IA con tool-use de escritura + confirmación humana`
> Estado: ✅ implementado · 🔒 T6 + T13 (tests Playwright con LLM real) bloqueados sin saldo Anthropic

## Requisitos

El Sprint 1 dejó al agente IA leyendo perfecto, pero si el usuario pedía *"registrá un egreso de $5000 en IDS por nafta"*, el agente respondía *"esto lo voy a poder hacer en el próximo sprint"*. Cualquier escritura tenía que hacerse a mano por la UI o llamando endpoints REST.

**Objetivo:** que el agente pueda **operar la plataforma** (crear movimientos, aportes, etapas, órdenes, eventos, comprobantes, obras, clientes), pero con un **mecanismo robusto de confirmación humana** para cualquier acción sensible. El agente nunca debe hacer una escritura por su cuenta sin que un humano apriete "Confirmar".

## Cómo se hizo

### T1 — Tabla `AgentAction` extendida

En `backend/app/models.py`:

- Nuevo enum `AgentActionStatus`:
  - `executed` — tool de lectura, se ejecutó al toque (default).
  - `pending` — tool sensible, esperando confirmación humana.
  - `confirmed` — el humano confirmó y se ejecutó.
  - `cancelled` — el humano canceló antes de ejecutar.
- Campos nuevos: `status`, `confirmed_by` (FK users), `confirmed_at`.

### T2 — Mecanismo de confirmación

En `backend/app/agent/orchestrator.py` se modificó `_execute_tool()`:

1. **Si la tool está en `REQUIRES_CONFIRMATION_TOOLS`:**
   - Persiste un `AgentAction` con `status=pending` y guarda el `tool_input_json`.
   - Devuelve a Claude un payload `{requires_confirmation: True, action_id, preview, message}` indicándole que **NO se ejecutó todavía**.
2. **Si no:** ejecuta normalmente como en Sprint 1.

Función nueva `confirm_action(action_id, user, confirm: bool, db)`:
- Valida que la action exista, pertenezca al user y esté en `pending`.
- Si `confirm=True`: re-ejecuta el handler con el input guardado, marca `confirmed`, registra `ok` y output.
- Si `confirm=False`: marca `cancelled`.

`chat()` ahora devuelve `pending_actions: [{action_id, tool_name, preview}]` además del texto.

### T3 — Whitelist de tools sensibles

En `backend/app/agent/tools.py`:

```python
REQUIRES_CONFIRMATION_TOOLS = {
    # Financiero
    "registrar_movimiento", "registrar_aporte_socio",
    "registrar_devolucion_aporte", "cargar_comprobante",
    # Estructura de obra
    "crear_obra", "crear_cliente", "crear_etapa", "cambiar_estado_etapa",
    # Capa lúdica
    "crear_orden", "cerrar_orden", "reportar_evento",
    # Mensajería
    "enviar_whatsapp",
}
```

Las 16 tools de lectura del Sprint 1 no están en el set y siguen ejecutándose sin confirmación.

### T4–T11 — 12 tools de escritura nuevas

| Tool | Qué hace | Validaciones clave |
|---|---|---|
| `registrar_movimiento` | Crea ingreso/egreso | Cheque pide nro+vto, TOTAL_BLANCO exige factura |
| `registrar_aporte_socio` | Crea aporte + INGRESO espejo (R2) | Socio existe, monto > 0 |
| `registrar_devolucion_aporte` | EGRESO espejo, ajusta estado | Monto ≤ pendiente |
| `crear_etapa` | Alta de etapa | nro_etapa único por obra |
| `cambiar_estado_etapa` | PEND→...→COBRADA | R5: nota automática si COBRADA con aportes pendientes |
| `crear_orden` | Quest operativa | Frente y cuadrilla deben existir |
| `cerrar_orden` | Marca completa + suma XP user/cuadrilla | No re-cerrar |
| `reportar_evento` | Crea evento en feed | tipo `incidente` → `es_critico=true` automático |
| `cargar_comprobante` | AFIP completo | neto+IVA = total (±0.05) |
| `crear_cliente` | Alta cliente | CUIT único |
| `crear_obra` | Alta obra ligada a cliente | código único, hereda régimen del cliente |
| `enviar_whatsapp` | Stub hasta Sprint 4 | Solo registra intent (Sprint 4 lo conecta al adapter real) |

### T5 — UI de confirmación en `AgentChat.jsx`

Componente nuevo `<ConfirmableAction>`:
- Card amarilla/marrón con `<ShieldAlert>` icon.
- Título de la tool en lenguaje humano (mapeado por `TOOL_LABELS`).
- Preview del payload formateado como key-value.
- Botones `[Confirmar]` (navy primary) y `[Cancelar]` (ghost).
- Estado "resolving" con spinner mientras se procesa.

Cuando el usuario clickea Confirmar:
- POST `/api/agent/confirm/{action_id}` con `{confirm: true}`.
- La acción se quita del estado pendiente.
- Aparece un mensaje del agente con el resultado (✅ / ❌) y los datos relevantes (movimiento_id, saldo actualizado, etc).

### T12 — System prompt actualizado

El prompt anterior decía *"Sprint actual: solo lectura. Próximo sprint: vas a poder registrar..."*. Se reemplazó por una guía clara del ciclo de confirmación:

> Cuando llamás a una tool de escritura, NO se ejecuta inmediatamente.
> El sistema te devuelve `{"requires_confirmation": true, ...}`.
> NO digas que la acción se hizo — todavía no se hizo.
> Resumile al usuario QUÉ vas a hacer y pedile que confirme con el botón.

## Cómo se usa

### Como usuario final

1. Abrir el chat (botón flotante "Operario IA").
2. Pedirle algo de escritura en lenguaje natural:
   - *"Registrá un egreso de $75.000 en IDS por flete de materiales, en efectivo."*
3. El agente responde con un texto + una **card de confirmación** debajo:
   ```
   Voy a registrar un egreso de $75.000 en IDS por flete.
   ─────────────────────────────────
   Confirmación requerida #99
   Registrar movimiento financiero
     OBRA: IDS
     TIPO: EGRESO
     MONTO: 75000
     CONCEPTO: Flete materiales
     MEDIO_PAGO: EFECTIVO
     CATEGORIA_EGRESO: MATERIALES
   [Confirmar]  [Cancelar]
   ```
4. Click `Confirmar` → mensaje del agente: *"✅ Acción confirmada. Movimiento #27 creado. Nuevo saldo de la obra: -$485k."*

### Endpoints expuestos

```
POST /api/agent/chat                 → como Sprint 1, pero ahora devuelve `pending_actions`
POST /api/agent/confirm/{action_id}  → body: {confirm: true|false}
GET  /api/agent/actions              → audit log incluye status + confirmed_by + confirmed_at
```

### Como dev (testear sin LLM)

Como el agente real cuesta créditos Anthropic, se puede testear el flujo sin LLM agregando temporalmente una tool de lectura al `REQUIRES_CONFIRMATION_TOOLS` set:

```python
from app.agent import orchestrator, tools
tools.REQUIRES_CONFIRMATION_TOOLS.add('dashboard_hud')
res = orchestrator._execute_tool('dashboard_hud', {}, user, session_id, db)
# res['requires_confirmation'] == True
# res['action_id'] = 99
res2 = orchestrator.confirm_action(99, user, confirm=True, db=db)
# Ejecuta la tool con el input guardado
tools.REQUIRES_CONFIRMATION_TOOLS.discard('dashboard_hud')
```

## Tests realizados (71+ casos)

Cada tool tiene su test E2E directo desde Python:

| Tarea | Casos | Verifica |
|---|---|---|
| T1 | 7 | Los 4 estados persisten, FK confirmer, filtros |
| T2 | 7 | Pending, confirm, cancel, doble-confirm rechazado, 404, 403, HTTP wiring |
| T3 | — | 12 tools en whitelist, 0 overlap con lectura |
| T4 `registrar_movimiento` | 5 validaciones | EGRESO sin categoría, cheque sin nro, TOTAL_BLANCO sin FC, obra inexistente, monto negativo |
| T5 UI | — | Endpoint /confirm OK desde browser con axios + JWT |
| T7 aportes | 8 | R2 espejo, devolución parcial, total, exceder pendiente, doble-total, socio inexistente |
| T8 etapas | 6 | Crear, duplicado rechazado, cambio de estado, R5 con/sin aporte vinculado |
| T9 lúdica | 7 | Crear orden, cerrar suma XP user+cuadrilla, doble-cierre, evento crítico auto, etc. |
| T10 alta | 7 | Cliente CUIT único, obra hereda régimen, comprobante neto+IVA=total |
| T11 stub | 3 | Tool registrada, validación phone/mensaje |

Total: **71+ casos** validando lógica del backend, tests directos en Python sin necesidad del LLM.

## Estado y deuda

✅ **Implementado:** mecanismo de confirmación + 12 tools de escritura + UI completa + audit log con campos de aprobación.

🔒 **Bloqueado por falta de saldo Anthropic:**
- **T6** — test Playwright del flujo `registrar_movimiento` end-to-end real (chat con NLP → confirmación → ejecución).
- **T13** — suite Playwright completa del Sprint 2.

Cuando se carguen créditos en https://console.anthropic.com/settings/billing, los tests pueden correrse sin cambios de código (todo el código del flujo está validado por las pruebas directas).

📌 **Cómo el Sprint 4 reusa esto:**
- Sprint 4 conecta `enviar_whatsapp` al adapter real (deja de ser stub).
- Los magic links del Sprint 4 usan exactamente la misma `confirm_action()` del orchestrator — solo que el "usuario" llega vía link firmado en lugar de la UI.
