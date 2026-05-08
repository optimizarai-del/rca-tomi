# Sprint 1 — Operario IA de solo lectura

> Commit: `8cde75b feat(agent): Sprint 1 — Operario IA con tool-use de solo lectura`
> Estado: ✅ cerrado

## Requisitos

La plataforma tenía 11 routers REST con CRUD completo, pero acceder a la información requería navegar por múltiples páginas. Un PM o admin que quería responder preguntas tipo *"¿qué obras están en rojo?"* o *"¿cómo va todo?"* tenía que abrir varias secciones manualmente.

**Objetivo:** un asistente conversacional embebido en la app que conteste preguntas usando datos reales (no inventando). En esta primera fase, **solo lectura** — el agente lee de la DB y responde, sin modificar nada.

## Cómo se hizo

### Modelo de datos

Se agregaron 2 tablas en `backend/app/models.py`:

- **`AgentSession`** — historial de conversación por usuario (sobrevive entre logins).
  - `messages_json: Text` — array JSON con el historial.
  - `last_message_at: DateTime`.
- **`AgentAction`** — audit log de cada tool ejecutada por el agente.
  - `user_id`, `tool_name`, `tool_input_json`, `tool_output_json`, `ok`, `error`, `canal`, `created_at`.

### Loop de tool-use

El núcleo está en `backend/app/agent/orchestrator.py`:

- Cliente `Anthropic` (lazy import — no rompe si la lib no está).
- Modelo configurable vía `AGENT_MODEL` (default `claude-sonnet-4-5`).
- Loop con `MAX_TOOL_ITERATIONS=8` y `MAX_HISTORY_MESSAGES=30`.
- En cada iteración:
  1. Llama a `client.messages.create(model, system, tools, messages)`.
  2. Si la respuesta tiene `stop_reason="tool_use"`, ejecuta cada tool, devuelve los resultados como `tool_result` y vuelve a iterar.
  3. Si no, captura el texto y termina.
- Persiste el historial truncado en `AgentSession.messages_json`.
- Cuida no cortar pares `tool_use`/`tool_result` al truncar.

### 16 tools de lectura

En `backend/app/agent/tools.py`:

| Tool | Devuelve |
|---|---|
| `dashboard_hud` | Big numbers globales (saldo, contratos, cheques, alertas). |
| `listar_obras` | Obras con cliente, régimen, estado, monto, saldo. |
| `obtener_obra` | Detalle: etapas, aportes pendientes, cheques, eventos. |
| `listar_clientes` | Clientes con CUIT, tipo, régimen, count de obras. |
| `listar_etapas` | Etapas de una obra con monto y estado. |
| `listar_movimientos` | Movimientos filtrables por tipo, categoría, estado. |
| `saldo_obra` | Saldo + ejecutado %. |
| `flujo_caja_obra` | Semanal con saldo acumulado. |
| `aportes_pendientes` | Aportes de socios sin devolver. |
| `cheques_a_vencer` | Cheques propios con vto en N días. |
| `descalce_fiscal` | Egresos c/factura > ingresos c/factura (admin/finanzas). |
| `alertas_stock_bajo` | Materiales bajo el mínimo. |
| `listar_proveedores` | Proveedores con rating. |
| `listar_cuadrillas` | Cuadrillas con XP/nivel. |
| `eventos_recientes` | Feed de eventos. |
| `listar_usuarios` | Usuarios del sistema (solo admin). |

Cada handler:
- Recibe `(input: dict, user: User, db: Session)`.
- Devuelve un dict serializable.
- Chequea permisos según `user.role` cuando aplica.

### System prompt

Define la personalidad del agente, contexto del modelo financiero, y reglas:
- Hablar en español rioplatense, conciso.
- Usar tools, no inventar datos.
- Si el usuario pide escribir, avisar que en este sprint es solo lectura.
- Formato de montos corto (`$12.3M`, `$450k`).

### Endpoints

En `backend/app/routers/agent.py`:

- `POST /api/agent/chat` — recibe `{message}`, devuelve `{reply, tools_used, session_id}`.
- `POST /api/agent/reset` — vacía el historial del usuario.
- `GET /api/agent/actions` — audit log de las acciones del usuario.

### Frontend

`frontend/src/components/AgentChat.jsx`:

- Botón flotante "Operario IA" abajo a la derecha en cualquier página autenticada.
- Panel rounded-3xl 400×600px con header, lista de mensajes, composer.
- Sugerencias clickeables para arrancar (`¿Cómo va todo?`, `¿Qué obras están en rojo?`).
- Cada mensaje del agente muestra los chips de las tools que invocó.
- Botón ↻ para reset de conversación.

## Cómo se usa

### Para un usuario final

1. Login en http://localhost:5175.
2. Click en el botón "Operario IA" abajo-derecha.
3. Escribir en lenguaje natural:
   - *"¿Cuál es el saldo de la obra IDS?"*
   - *"Mostrame los cheques a vencer en los próximos 60 días."*
   - *"¿Hay materiales con stock bajo?"*
4. El agente responde con datos reales y muestra qué tools usó.

### Para un dev (HTTP directo)

```bash
TOKEN=$(curl -s -X POST http://localhost:8010/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@rca.com","password":"demo1234"}' | jq -r .access_token)

curl -s -X POST http://localhost:8010/api/agent/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "qué obras tenés"}'
```

### Configuración

`backend/.env`:
```env
ANTHROPIC_API_KEY=sk-ant-api03-...   # obligatorio
AGENT_MODEL=claude-sonnet-4-5         # opcional, default
```

Sin la API key, el agente devuelve un mensaje de error claro pero no rompe el resto de la app.

## Tests realizados

- 16 tools probadas individualmente desde Python con datos del seed.
- Flujo end-to-end vía HTTP: login → chat → verificar respuesta con datos reales.
- Permisos: con un user `supervisor`, intentar `descalce_fiscal` → tool devuelve `error: "Requiere rol admin/finanzas"`.
- Reset: sesión nueva → enviar "qué viste antes?" → no recuerda nada.

## Estado y deuda

✅ **Funcional:** chat con 16 tools de lectura, audit log, sesiones persistentes.

⚠️ **Limitaciones de este sprint** (resueltas en Sprint 2):
- El agente solo **lee**. Si pedís *"registrá un gasto"*, te avisa que no puede.
- No hay confirmación humana (no aplica todavía porque no escribe).
- No mide tokens consumidos ni costos por sesión.

📌 **Puntos de extensión usados después:**
- El loop de tool-use es agnóstico al tipo de tool — Sprint 2 agregó tools de escritura sin tocar el orchestrator.
- `AgentAction` ya guardaba todo lo necesario para audit; Sprint 2 le sumó campos de confirmación.
