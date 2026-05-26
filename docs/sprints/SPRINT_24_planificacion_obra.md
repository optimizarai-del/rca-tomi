# Sprint 24 — Planificación de obra asistida por IA

> Estado: ✅ cerrado · suite pytest **189/189** verde

## Requisitos

De las notas + foto 1 de la reunión 2026-05-20:

> Por obras un paso a paso desde el inicio que es la planificación de la obra. O ya te van a dar una base del plan, y de ahí vaya haciendo preguntas y respuestas para llegar a un buen armado de obra con sus tareas, materiales, etapas, etc.
>
> Se pasa una plan base y de ahí en base a las etapas que hay en la obra en curso o pendiente, le vaya haciendo un plan borrador para la implementación de lo proyectado. Que se pueda editar en el momento. **Que pregunte antes de unificarlo con el plan actual.**

Y foto 1 — checklist mental del agente:
- ¿Hay etapas definidas? cuántas → detalle de cada una.
- Qué trabajos hay que hacer, en qué orden, según manual de procedimiento.
- Cuánta gente, qué tiempos.
- Qué materiales, cuánta cantidad, cuándo se necesitan.

## Cómo se hizo

Implementación **MVP**: en vez de un chat conversacional multi-turno, el flujo es:
1. Usuario escribe un contexto descriptivo de la obra.
2. Backend llama a Claude con un system prompt estructurado que devuelve **JSON con etapas / frentes / materiales sugeridos**.
3. Frontend muestra el plan como **borrador editable** (estilo Google Docs).
4. Usuario edita inline (cambia montos, fechas, nombres, agrega/quita).
5. Click **Aplicar a la obra** → crea `EtapaObra` y `Frente` reales.
6. Antes de aplicar, **pide confirmación** (cumple "pregunte antes de unificarlo").

Sin chat ni sesiones multi-turno → simple, predecible, fácil de testear. Si después el flujo conversacional resulta valioso, se itera.

### T1 — Rama
Branch `sprint-24-planificacion-obra` desde `sprint-22-memoria-clientes`.

### T2 — Modelo

[backend/app/models.py](../../backend/app/models.py):

```python
class PlanObraEstado(str, Enum):
    borrador = "borrador"
    aplicado = "aplicado"
    descartado = "descartado"

class PlanObraBorrador(Base):
    id, is_demo, obra_id,
    prompt_input: Text,       # el contexto del usuario
    resultado_json: Text,     # JSON con etapas/frentes/materiales/notas
    estado: PlanObraEstado,
    model_used: String(60),   # "claude-sonnet-4-5" | "placeholder"
    created_by_id, created_at, aplicado_at
```

Migración Alembic [d7f9a1b3c5e6](../../backend/alembic/versions/d7f9a1b3c5e6_sprint_24_plan_obra.py).
`planes_obra_borrador` agregado a `_DEMO_TABLES`.

### T3 — Servicio `plan_obra.py`

[backend/app/plan_obra.py](../../backend/app/plan_obra.py):

- `SYSTEM_PROMPT` con esquema JSON estricto que el modelo debe devolver.
- `_build_user_prompt`: arma el contexto con datos de la obra (cliente, monto, fechas, m², pisos) + el texto del usuario.
- `_llm_plan`: llama al SDK de Anthropic con `messages.create`. Limpia wrappers `\`\`\`json` y parsea. Si falla por cualquier motivo (sin API key, SDK no instalado, JSON inválido, timeout) cae en `_placeholder_plan`.
- `_placeholder_plan`: plan determinístico de 4 etapas (Anticipo, Cimientos, Cerramientos, Terminaciones) + 5 frentes + 4 materiales clave. Sirve para dev sin API y para tests.
- `generar_plan(db, obra, contexto, user_id)`: persiste el `PlanObraBorrador`.
- `aplicar_plan(db, borrador)`: crea `EtapaObra` y `Frente` reales; marca estado `aplicado`. **No** crea Materiales — quedan como sugerencia visual.

### T4 — Endpoints

[backend/app/routers/plan_obra.py](../../backend/app/routers/plan_obra.py):

- `POST /api/obras/{oid}/plan/generar` (admin) — body `{contexto, model_override?}`. Crea borrador.
- `GET  /api/obras/{oid}/plan` — lista borradores de la obra (descendente).
- `GET  /api/obras/{oid}/plan/{plan_id}` — un borrador específico.
- `PUT  /api/obras/{oid}/plan/{plan_id}` (admin) — edita `resultado` antes de aplicar. Solo si estado=borrador.
- `POST /api/obras/{oid}/plan/{plan_id}/aplicar` (admin) — crea etapas y frentes reales.
- `POST /api/obras/{oid}/plan/{plan_id}/descartar` (admin) — marca descartado.
- `DELETE /api/obras/{oid}/plan/{plan_id}` (admin) — hard delete.

Todos los endpoints validan acceso a la obra via `scope_obras` (Sprint 13).

### T5 — Frontend

[frontend/src/pages/ObraDetail.jsx](../../frontend/src/pages/ObraDetail.jsx) suma:

- Tab **"Planificación IA"** al lado de Resumen.
- `PlanificacionTab`: form con textarea para el contexto + botón Generar. Lista de borradores existentes como chips clickeables (estado + fecha). Muestra el borrador activo.
- `PlanPreview`: editor inline con grid de inputs para cada etapa (nombre, nro, monto, %, fecha, notas) y cada frente (nombre, tipo, notas). Materiales sugeridos como tabla informativa. Notas generales editable.
- Botones por estado:
  - **borrador**: Guardar (si hay cambios), Descartar, **Aplicar a la obra** (con confirm).
  - **aplicado**: chip verde con timestamp.
  - **descartado**: chip muted.

### T6 — Tests

[backend/tests/test_plan_obra.py](../../backend/tests/test_plan_obra.py) — 15 casos. Todos forzando `ANTHROPIC_API_KEY=""` para usar placeholder (no se hacen llamadas reales).

- Servicio:
  - Placeholder genera estructura básica con sumatoria de porcentajes ~100.
  - Aplicar crea etapas + frentes y marca estado aplicado.
  - No se puede aplicar dos veces.
- Endpoints:
  - Generar (con contexto válido y corto → 422; obra inexistente → 404).
  - Listar borradores.
  - Editar resultado del borrador.
  - Aplicar (crea etapas + frentes reales; doble aplicar → 400).
  - Descartar.
  - Borrar.
  - No se puede editar un borrador aplicado (400).
  - Solo admin genera (supervisor → 403).
  - Supervisor con whitelist no ve obras fuera de scope (404).

Suite total: **189/189 verde**.

## Cómo se usa

### Crear un plan para una obra nueva

1. `/obra/IDS` → tab **Planificación IA**.
2. Escribir en el textarea: *"Casa unifamiliar 180m², 4 ambientes, una planta. Estructura tradicional, terminaciones medias. Cliente quiere terminar en 8 meses. Anticipo del 30% al firmar."*
3. **Generar borrador** → aparece el preview con etapas, frentes y materiales sugeridos.
4. Editar lo que haga falta inline (cambiar montos, fechas, agregar etapas, quitar lo que no aplique).
5. **Aplicar a la obra** → confirm → se crean las etapas y frentes reales en la obra.
6. Las etapas aparecen en el tab **Etapas**, los frentes en **Frentes**.

### Iterar sobre un plan

Cada **Generar** crea un borrador nuevo. Los anteriores quedan visibles como chips arriba (con su estado). Permite probar varias propuestas antes de aplicar la definitiva.

### Modo offline (sin API key)

Si `ANTHROPIC_API_KEY` está vacío, el sistema usa un **plan placeholder determinístico** de 4 etapas estándar. El campo `model_used` aparece como `"placeholder"` — visible en el header del borrador para que sepas que no es Claude.

## Deuda pendiente

- **Chat conversacional multi-turno**: hoy es 1 prompt → 1 respuesta. Si se quiere que el agente vaya preguntando ("¿cuánta gente en estructura?", "¿qué medidas?"), hay que sumar sesiones de chat tipo `AgentSession` con tag de planificación.
- **Detección de plan existente**: si la obra ya tiene etapas/frentes, no se avisa al aplicar. Quizás agregar warning "esta obra ya tiene N etapas, ¿agregar más o reemplazar?". Por ahora siempre **agrega** (additive).
- **Crear materiales automáticamente**: el plan sugiere materiales con cantidad, pero no se cargan a `/materiales`. Cuando el sprint de OCR (S18) o el de Recetas (S16) madure, conectar.
- **Cantidad/tiempos por etapa**: el modelo de `EtapaObra` no tiene "cuánta gente" ni "duración estimada" — el LLM los devuelve en `notas` como texto libre. Si emerge la necesidad, agregar columnas.
- **Histórico de prompts buenos**: cuando se acumulen contextos exitosos, sería útil sugerirlos al cargar uno nuevo (autocomplete por nombre de obra anterior).
